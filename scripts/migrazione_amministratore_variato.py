#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DATABASE - Campo amministratore_variato
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Aggiunge campo amministratore_variato alla tabella clienti
#              per tracciare alert Creditsafe regola 107 (cambio amministratori)
#
# OPERAZIONI:
# 1. Backup database
# 2. ALTER TABLE clienti: aggiunge amministratore_variato INTEGER DEFAULT 0
# 3. Verifica finale
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/migrazione_amministratore_variato.py --dry-run
#   python3 scripts/migrazione_amministratore_variato.py
#
# ==============================================================================

import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()

if SCRIPT_DIR.name == 'scripts':
    BASE_DIR = SCRIPT_DIR.parent
else:
    BASE_DIR = SCRIPT_DIR

DB_FILE = BASE_DIR / 'db' / 'gestionale.db'
BACKUP_DIR = BASE_DIR / 'backup'


# ==============================================================================
# UTILITY
# ==============================================================================

def log(msg, livello='INFO'):
    """Stampa messaggio con livello."""
    print(f"  [{livello}] {msg}")


def colonna_esiste(conn, tabella, colonna):
    """Verifica se una colonna esiste in una tabella."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabella})")
    colonne = [row[1] for row in cursor.fetchall()]
    return colonna in colonne


# ==============================================================================
# MIGRAZIONE
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("  MIGRAZIONE: Campo amministratore_variato")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'ESECUZIONE REALE'}")
    print("=" * 60)

    # Verifica database
    if not DB_FILE.exists():
        print(f"\n  ERRORE: Database non trovato: {DB_FILE}")
        sys.exit(1)

    print(f"\n  Database: {DB_FILE}")
    print(f"  Dimensione: {DB_FILE.stat().st_size / 1024 / 1024:.1f} MB")

    # ---- STEP 1: Backup ----
    print("\n" + "-" * 60)
    print("[STEP 1] Backup database")
    print("-" * 60)

    if dry_run:
        log("Backup saltato (dry-run)", 'DRY')
    else:
        BACKUP_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = BACKUP_DIR / f"db__gestionale.db.bak_{ts}"
        shutil.copy2(DB_FILE, backup_file)
        log(f"Backup creato: {backup_file}", 'OK')

    # ---- STEP 2: ALTER TABLE ----
    print("\n" + "-" * 60)
    print("[STEP 2] ALTER TABLE clienti - amministratore_variato")
    print("-" * 60)

    conn = sqlite3.connect(str(DB_FILE))

    if colonna_esiste(conn, 'clienti', 'amministratore_variato'):
        log("Campo amministratore_variato gia' presente, nulla da fare", 'SKIP')
        conn.close()
        print("\n" + "=" * 60)
        print("  MIGRAZIONE: nulla da fare (campo gia' esistente)")
        print("=" * 60)
        return

    if dry_run:
        log("amministratore_variato INTEGER DEFAULT 0 - DA AGGIUNGERE", 'DRY')
    else:
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE clienti ADD COLUMN amministratore_variato INTEGER DEFAULT 0")
        conn.commit()
        log("amministratore_variato INTEGER DEFAULT 0 - aggiunto", 'OK')

    # ---- STEP 3: Verifica ----
    print("\n" + "-" * 60)
    print("[STEP 3] Verifica")
    print("-" * 60)

    if not dry_run:
        if colonna_esiste(conn, 'clienti', 'amministratore_variato'):
            log("Colonna verificata nel DB", 'OK')

            # Verifica valore default
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clienti WHERE amministratore_variato = 0")
            count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM clienti")
            total = cursor.fetchone()[0]
            log(f"Tutti i {total} clienti hanno valore default 0", 'OK')
        else:
            log("ERRORE: colonna non trovata dopo ALTER!", 'ERRORE')
            conn.close()
            sys.exit(1)
    else:
        log("Verifica saltata (dry-run)", 'DRY')

    conn.close()

    # ---- Riepilogo ----
    print("\n" + "=" * 60)
    if dry_run:
        print("  DRY-RUN COMPLETATO")
        print("  Riesegui senza --dry-run per applicare")
    else:
        print("  MIGRAZIONE COMPLETATA CON SUCCESSO")
        print("  Campo: clienti.amministratore_variato INTEGER DEFAULT 0")
    print("=" * 60)


if __name__ == '__main__':
    main()
