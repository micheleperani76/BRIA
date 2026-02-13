#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DATABASE - Upload Multi-File e Notifica CRM
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Aggiunge flag utente per notifica aggiornamento CRM
#              e configurazione globale toggle promemoria.
#
# OPERAZIONI:
#   1. ALTER TABLE utenti ADD COLUMN notifica_aggiorna_crm (flag per utente)
#   2. INSERT config promemoria CRM in ticker_config (toggle globale ON/OFF)
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/migrazione_upload_multifile.py --dry-run
#   python3 scripts/migrazione_upload_multifile.py
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


def log(msg, livello='INFO'):
    simboli = {'INFO': ' ', 'OK': '+', 'ERR': '!', 'SKIP': '-'}
    s = simboli.get(livello, ' ')
    print(f"  [{s}] {msg}")


# ==============================================================================
# MIGRAZIONI
# ==============================================================================

def migra_flag_utente(cursor, dry_run):
    """Aggiunge colonna notifica_aggiorna_crm alla tabella utenti."""
    # Verifica se esiste gia'
    cursor.execute("PRAGMA table_info(utenti)")
    colonne = [row[1] for row in cursor.fetchall()]

    if 'notifica_aggiorna_crm' in colonne:
        log("Colonna notifica_aggiorna_crm gia' presente", 'SKIP')
        return True

    if dry_run:
        log("ALTER TABLE utenti ADD COLUMN notifica_aggiorna_crm INTEGER DEFAULT 0", 'OK')
        return True

    cursor.execute("ALTER TABLE utenti ADD COLUMN notifica_aggiorna_crm INTEGER DEFAULT 0")
    log("Colonna notifica_aggiorna_crm aggiunta", 'OK')

    # Attiva di default per gli admin
    cursor.execute("""
        UPDATE utenti SET notifica_aggiorna_crm = 1
        WHERE ruolo_base = 'admin' AND attivo = 1
    """)
    n = cursor.rowcount
    log(f"Flag attivato per {n} utenti admin", 'OK')

    return True


def migra_config_promemoria(cursor, dry_run):
    """Aggiunge configurazione promemoria CRM in ticker_config."""
    # Verifica schema ticker_config
    cursor.execute("PRAGMA table_info(ticker_config)")
    colonne = [row[1] for row in cursor.fetchall()]

    if not colonne:
        log("Tabella ticker_config non trovata!", 'ERR')
        return False

    # Verifica se esiste gia' la config
    cursor.execute("""
        SELECT chiave FROM ticker_config WHERE chiave = 'promemoria_aggiorna_crm'
    """)
    if cursor.fetchone():
        log("Config promemoria_aggiorna_crm gia' presente", 'SKIP')
        return True

    if dry_run:
        log("INSERT ticker_config: promemoria_aggiorna_crm = 1 (attivo)", 'OK')
        return True

    # Determina le colonne disponibili nella tabella
    col_names = colonne

    if 'chiave' in col_names and 'valore' in col_names:
        cursor.execute("""
            INSERT INTO ticker_config (chiave, valore)
            VALUES ('promemoria_aggiorna_crm', '1')
        """)
        log("Config promemoria_aggiorna_crm inserita (attivo)", 'OK')
        return True
    else:
        log(f"Schema ticker_config non compatibile: {col_names}", 'ERR')
        return False


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("  MIGRAZIONE: Upload Multi-File e Notifica CRM")
    print("=" * 60)
    print(f"  Database: {DB_FILE}")
    print(f"  Data:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("\n  *** MODALITA' DRY-RUN ***\n")
    print()

    if not DB_FILE.exists():
        log(f"Database non trovato: {DB_FILE}", 'ERR')
        sys.exit(1)

    # Backup (solo in modalita' reale)
    if not dry_run:
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = BACKUP_DIR / f"gestionale.db.bak_migrazione_multifile_{timestamp}"
        shutil.copy2(str(DB_FILE), str(backup_file))
        log(f"Backup: {backup_file.name}", 'OK')

    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()

    errori = 0

    print("--- STEP 1: Flag utente notifica_aggiorna_crm ---")
    if not migra_flag_utente(cursor, dry_run):
        errori += 1

    print("\n--- STEP 2: Config toggle promemoria CRM ---")
    if not migra_config_promemoria(cursor, dry_run):
        errori += 1

    if errori > 0:
        log(f"{errori} errori - rollback", 'ERR')
        conn.rollback()
        sys.exit(1)

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 60}")
    if dry_run:
        print("  DRY-RUN completato. Eseguire senza --dry-run per applicare.")
    else:
        print("  MIGRAZIONE COMPLETATA!")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
