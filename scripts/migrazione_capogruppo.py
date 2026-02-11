#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE: Tabella capogruppo_clienti (multi-capogruppo)
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-11
# Descrizione: Crea tabella capogruppo_clienti per supportare piu' capogruppo
#              per cliente. Migra dati esistenti da clienti.capogruppo_nome/cf.
#              I vecchi campi restano nel DB per compatibilita' ma non saranno
#              piu' usati dal frontend.
# ==============================================================================

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'db' / 'gestionale.db'

def main():
    print("=" * 60)
    print("  MIGRAZIONE: capogruppo_clienti (multi-capogruppo)")
    print("=" * 60)
    print()
    
    if not DB_PATH.exists():
        print(f"ERRORE: Database non trovato: {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # === STEP 1: Crea tabella ===
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='capogruppo_clienti'")
    if cursor.fetchone():
        print("  [1/3] Tabella 'capogruppo_clienti' gia' presente. Skip creazione.")
    else:
        print("  [1/3] Creazione tabella 'capogruppo_clienti'...")
        cursor.execute('''
            CREATE TABLE capogruppo_clienti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                codice_fiscale TEXT,
                protetto INTEGER DEFAULT 0,
                data_inserimento TEXT DEFAULT (datetime('now')),
                data_modifica TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (cliente_id) REFERENCES clienti(id)
            )
        ''')
        cursor.execute('CREATE INDEX idx_capogruppo_cliente ON capogruppo_clienti(cliente_id)')
        conn.commit()
        print("  OK - Tabella + indice creati")
    
    # === STEP 2: Migra dati esistenti ===
    print("  [2/3] Migrazione dati esistenti da clienti.capogruppo_nome...")
    
    # Conta quanti hanno capogruppo
    cursor.execute('''
        SELECT id, capogruppo_nome, capogruppo_cf, capogruppo_protetto
        FROM clienti
        WHERE capogruppo_nome IS NOT NULL AND capogruppo_nome != '' AND capogruppo_nome != '-'
    ''')
    clienti_con_capogruppo = cursor.fetchall()
    
    migrati = 0
    saltati = 0
    for c in clienti_con_capogruppo:
        # Verifica se gia' migrato
        cursor.execute('''
            SELECT id FROM capogruppo_clienti
            WHERE cliente_id = ? AND nome = ?
        ''', (c['id'], c['capogruppo_nome']))
        
        if cursor.fetchone():
            saltati += 1
            continue
        
        cursor.execute('''
            INSERT INTO capogruppo_clienti (cliente_id, nome, codice_fiscale, protetto)
            VALUES (?, ?, ?, ?)
        ''', (c['id'], c['capogruppo_nome'], c['capogruppo_cf'], c['capogruppo_protetto'] or 0))
        migrati += 1
    
    conn.commit()
    print(f"  OK - Migrati: {migrati}, Gia' presenti: {saltati}")
    
    # === STEP 3: Verifica ===
    print("  [3/3] Verifica...")
    cursor.execute("SELECT COUNT(*) as n FROM capogruppo_clienti")
    totale = cursor.fetchone()['n']
    print(f"  Totale record in capogruppo_clienti: {totale}")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("  MIGRAZIONE COMPLETATA")
    print("=" * 60)

if __name__ == '__main__':
    main()
