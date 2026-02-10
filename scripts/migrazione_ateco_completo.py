#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DB - Colonne ATECO complete
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-10
# Descrizione: Aggiunge 4 nuove colonne alla tabella clienti per
#              estrazione ATECO completa dai PDF Creditsafe
#
# Nuove colonne:
#   - codice_sae TEXT        (Codice SAE)
#   - codice_rae TEXT        (Codice RAE)
#   - codice_ateco_2007 TEXT (Codice ATECO versione 2007, opzionale)
#   - desc_ateco_2007 TEXT   (Descrizione ATECO 2007, opzionale)
#
# Uso: python3 scripts/migrazione_ateco_completo.py
# ==============================================================================

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================
DB_PATH = Path(__file__).parent.parent / 'db' / 'gestionale.db'

NUOVE_COLONNE = [
    ('codice_sae',        'TEXT', None),
    ('codice_rae',        'TEXT', None),
    ('codice_ateco_2007', 'TEXT', None),
    ('desc_ateco_2007',   'TEXT', None),
]

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("=" * 60)
    print("  MIGRAZIONE DB - Colonne ATECO complete")
    print("=" * 60)
    print(f"  Database: {DB_PATH}")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not DB_PATH.exists():
        print(f"ERRORE: Database non trovato: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Leggi colonne esistenti
    cursor.execute("PRAGMA table_info(clienti)")
    colonne_esistenti = {row[1] for row in cursor.fetchall()}

    aggiunte = 0
    gia_presenti = 0

    for nome_col, tipo, default in NUOVE_COLONNE:
        if nome_col in colonne_esistenti:
            print(f"  SKIP  {nome_col} - gia presente")
            gia_presenti += 1
        else:
            sql = f"ALTER TABLE clienti ADD COLUMN {nome_col} {tipo}"
            if default is not None:
                sql += f" DEFAULT {default}"
            cursor.execute(sql)
            print(f"  AGGIUNTA  {nome_col} {tipo}")
            aggiunte += 1

    conn.commit()
    conn.close()

    print()
    print(f"  Risultato: {aggiunte} aggiunte, {gia_presenti} gia presenti")
    print("=" * 60)

if __name__ == '__main__':
    main()
