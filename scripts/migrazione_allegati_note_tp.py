#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE - Aggiunge colonna allegati alle note Top Prospect
# ==============================================================================
# Data: 2026-01-29
# Descrizione: Aggiunge supporto allegati alle note Top Prospect
# ==============================================================================

import sqlite3
import os

DB_PATH = 'db/gestionale.db'

def log(msg):
    print(f"[MIGRAZIONE] {msg}")

def main():
    if not os.path.exists(DB_PATH):
        log(f"ERRORE: Database non trovato: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verifica se la colonna esiste gia
        cursor.execute("PRAGMA table_info(top_prospect_note)")
        colonne = [col[1] for col in cursor.fetchall()]
        
        if 'allegati' in colonne:
            log("Colonna 'allegati' gia presente - nessuna modifica necessaria")
            return True
        
        # Aggiungi colonna allegati (JSON con lista file)
        log("Aggiunta colonna 'allegati' alla tabella top_prospect_note...")
        cursor.execute('''
            ALTER TABLE top_prospect_note 
            ADD COLUMN allegati TEXT DEFAULT NULL
        ''')
        
        conn.commit()
        log("OK - Colonna 'allegati' aggiunta con successo")
        
        # Verifica
        cursor.execute("PRAGMA table_info(top_prospect_note)")
        colonne = [col[1] for col in cursor.fetchall()]
        log(f"Colonne tabella: {', '.join(colonne)}")
        
        return True
        
    except Exception as e:
        log(f"ERRORE: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
