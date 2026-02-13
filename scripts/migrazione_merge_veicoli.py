#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DATABASE - Merge Veicoli (Extra -> Installato)
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Aggiunge colonne per soft-delete merge veicoli duplicati.
#              Quando un Extra viene assorbito da un Installato con stessa targa,
#              l'Extra viene marcato con merged_in_veicolo_id + data_merge
#              e non appare piu' nelle query operative.
#
# COLONNE AGGIUNTE a 'veicoli':
#   - merged_in_veicolo_id  INTEGER  (ID veicolo che ha assorbito questo)
#   - data_merge             TEXT     (Timestamp del merge YYYY-MM-DD HH:MM:SS)
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/migrazione_merge_veicoli.py --dry-run
#   python3 scripts/migrazione_merge_veicoli.py
# ==============================================================================

import sys
import sqlite3
import shutil
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

COLONNE_NUOVE = [
    ('merged_in_veicolo_id', 'INTEGER', None),
    ('data_merge',           'TEXT',    None),
]


def log(msg, livello='INFO'):
    simboli = {'INFO': ' ', 'OK': '+', 'SKIP': '-', 'ERR': '!'}
    s = simboli.get(livello, ' ')
    print(f"  [{s}] {msg}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("  MIGRAZIONE - Merge Veicoli (Extra -> Installato)")
    print("=" * 60)
    if dry_run:
        print("  *** MODALITA' DRY-RUN ***")
    print(f"  Database: {DB_FILE}")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not DB_FILE.exists():
        print(f"ERRORE: Database non trovato: {DB_FILE}")
        sys.exit(1)

    # Backup
    if not dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = BACKUP_DIR / f"gestionale_pre_merge_{ts}.db"
        shutil.copy2(DB_FILE, backup_path)
        log(f"Backup: {backup_path.name}", 'OK')
    print()

    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()

    # Leggi colonne esistenti
    cursor.execute("PRAGMA table_info(veicoli)")
    colonne_esistenti = {row[1] for row in cursor.fetchall()}

    # Step 1: Aggiungi colonne
    print("[1/3] Aggiunta colonne a tabella veicoli...")
    aggiunte = 0
    for nome, tipo, default in COLONNE_NUOVE:
        if nome in colonne_esistenti:
            log(f"{nome} - gia' presente", 'SKIP')
        else:
            sql = f"ALTER TABLE veicoli ADD COLUMN {nome} {tipo}"
            if default is not None:
                sql += f" DEFAULT {default}"
            if not dry_run:
                cursor.execute(sql)
            log(f"{nome} {tipo} - aggiunta", 'OK')
            aggiunte += 1

    # Step 2: Indice
    print()
    print("[2/3] Creazione indice...")
    if not dry_run:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_veicoli_merged 
            ON veicoli(merged_in_veicolo_id)
        """)
    log("idx_veicoli_merged creato", 'OK')

    if not dry_run:
        conn.commit()

    # Step 3: Verifica
    print()
    print("[3/3] Verifica struttura...")
    cursor.execute("PRAGMA table_info(veicoli)")
    colonne_dopo = {row[1] for row in cursor.fetchall()}

    ok = True
    for nome, _, _ in COLONNE_NUOVE:
        if nome in colonne_dopo:
            log(f"{nome} - presente", 'OK')
        else:
            if dry_run:
                log(f"{nome} - sara' aggiunta", 'OK')
            else:
                log(f"{nome} - NON trovata!", 'ERR')
                ok = False

    conn.close()

    print()
    print("=" * 60)
    if dry_run:
        print(f"  DRY-RUN completato. {aggiunte} colonne da aggiungere.")
        print("  Eseguire senza --dry-run per applicare.")
    elif ok:
        print("  MIGRAZIONE COMPLETATA!")
        print("  Riavviare: ~/gestione_flotta/scripts/gestione_flotta.sh restart")
    else:
        print("  ERRORE durante la migrazione!")
    print("=" * 60)


if __name__ == '__main__':
    main()
