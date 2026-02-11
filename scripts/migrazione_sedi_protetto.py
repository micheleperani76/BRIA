#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE: Aggiunta campo 'protetto' a sedi_cliente
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-11
# Descrizione: Aggiunge colonna protetto (INTEGER DEFAULT 0) alla tabella
#              sedi_cliente. Quando una sede viene modificata manualmente,
#              protetto = 1 impedisce sovrascrittura da import CRM/Creditsafe.
# ==============================================================================

import sqlite3
import sys
from pathlib import Path

# Path database
DB_PATH = Path(__file__).parent.parent / 'db' / 'gestionale.db'

def main():
    print("=" * 60)
    print("  MIGRAZIONE: sedi_cliente.protetto")
    print("=" * 60)
    print()
    
    if not DB_PATH.exists():
        print(f"ERRORE: Database non trovato: {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Verifica se la colonna esiste gia
    cursor.execute("PRAGMA table_info(sedi_cliente)")
    colonne = [col[1] for col in cursor.fetchall()]
    
    if 'protetto' in colonne:
        print("  Colonna 'protetto' gia presente. Nulla da fare.")
        conn.close()
        return
    
    # Aggiungi colonna
    print("  Aggiunta colonna 'protetto' INTEGER DEFAULT 0...")
    cursor.execute("ALTER TABLE sedi_cliente ADD COLUMN protetto INTEGER DEFAULT 0")
    conn.commit()
    
    # Verifica
    cursor.execute("PRAGMA table_info(sedi_cliente)")
    colonne = [col[1] for col in cursor.fetchall()]
    
    if 'protetto' in colonne:
        print("  OK - Colonna aggiunta con successo")
    else:
        print("  ERRORE - Colonna non trovata dopo ALTER TABLE")
        conn.close()
        sys.exit(1)
    
    conn.close()
    
    print()
    print("=" * 60)
    print("  MIGRAZIONE COMPLETATA")
    print("=" * 60)

if __name__ == '__main__':
    main()
