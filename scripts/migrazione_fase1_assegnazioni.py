#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DATABASE - Fase 1: Sistema Assegnazioni
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-21
# Descrizione: Aggiunge tabelle e campi per gestione assegnazioni commerciali
# ==============================================================================
#
# ESEGUIRE CON:
#   cd ~/gestione_flotta
#   python3 scripts/migrazione_fase1_assegnazioni.py
#
# ==============================================================================

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Percorso database
DB_PATH = Path(__file__).parent.parent / 'db' / 'gestionale.db'

def backup_database():
    """Crea backup del database prima della migrazione."""
    import shutil
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'gestionale_backup_{timestamp}.db'
    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ Backup creato: {backup_path.name}")
    return backup_path

def migrazione_step1_campo_commerciale(cursor):
    """Aggiunge campo nome_commerciale_flotta alla tabella utenti."""
    print("\n[STEP 1] Aggiunta campo nome_commerciale_flotta...")
    
    # Verifica se il campo esiste già
    cursor.execute("PRAGMA table_info(utenti)")
    colonne = [col[1] for col in cursor.fetchall()]
    
    if 'nome_commerciale_flotta' in colonne:
        print("  → Campo già esistente, skip")
        return False
    
    cursor.execute('''
        ALTER TABLE utenti 
        ADD COLUMN nome_commerciale_flotta TEXT
    ''')
    print("  ✓ Campo nome_commerciale_flotta aggiunto")
    return True

def migrazione_step2_tabella_storico_assegnazioni(cursor):
    """Crea tabella storico_assegnazioni."""
    print("\n[STEP 2] Creazione tabella storico_assegnazioni...")
    
    # Verifica se la tabella esiste già
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='storico_assegnazioni'
    """)
    if cursor.fetchone():
        print("  → Tabella già esistente, skip")
        return False
    
    cursor.execute('''
        CREATE TABLE storico_assegnazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Dati assegnazione
            cliente_nome TEXT NOT NULL,
            cliente_piva TEXT,
            commerciale_precedente TEXT,
            commerciale_nuovo TEXT NOT NULL,
            
            -- Chi ha fatto l'assegnazione
            utente_id INTEGER NOT NULL,
            
            -- Quando
            data_ora TEXT NOT NULL,
            
            -- Note opzionali
            note TEXT,
            
            FOREIGN KEY (utente_id) REFERENCES utenti(id)
        )
    ''')
    
    # Indici
    cursor.execute('''
        CREATE INDEX idx_storico_assegnazioni_cliente 
        ON storico_assegnazioni(cliente_nome)
    ''')
    cursor.execute('''
        CREATE INDEX idx_storico_assegnazioni_data 
        ON storico_assegnazioni(data_ora)
    ''')
    cursor.execute('''
        CREATE INDEX idx_storico_assegnazioni_utente 
        ON storico_assegnazioni(utente_id)
    ''')
    cursor.execute('''
        CREATE INDEX idx_storico_assegnazioni_commerciale 
        ON storico_assegnazioni(commerciale_nuovo)
    ''')
    
    print("  ✓ Tabella storico_assegnazioni creata con indici")
    return True

def migrazione_step3_tabella_storico_export(cursor):
    """Crea tabella storico_export."""
    print("\n[STEP 3] Creazione tabella storico_export...")
    
    # Verifica se la tabella esiste già
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='storico_export'
    """)
    if cursor.fetchone():
        print("  → Tabella già esistente, skip")
        return False
    
    cursor.execute('''
        CREATE TABLE storico_export (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Chi ha esportato
            utente_id INTEGER NOT NULL,
            
            -- Cosa ha esportato
            tipo_export TEXT NOT NULL,
            filtri_applicati TEXT,
            num_record INTEGER,
            nome_file TEXT,
            
            -- Quando
            data_ora TEXT NOT NULL,
            
            FOREIGN KEY (utente_id) REFERENCES utenti(id)
        )
    ''')
    
    # Indici
    cursor.execute('''
        CREATE INDEX idx_storico_export_utente 
        ON storico_export(utente_id)
    ''')
    cursor.execute('''
        CREATE INDEX idx_storico_export_data 
        ON storico_export(data_ora)
    ''')
    cursor.execute('''
        CREATE INDEX idx_storico_export_tipo 
        ON storico_export(tipo_export)
    ''')
    
    print("  ✓ Tabella storico_export creata con indici")
    return True

def migrazione_step4_permesso_assegnazioni(cursor):
    """Aggiunge permesso flotta_assegnazioni al catalogo."""
    print("\n[STEP 4] Aggiunta permesso flotta_assegnazioni...")
    
    # Verifica se il permesso esiste già
    cursor.execute("""
        SELECT id FROM permessi_catalogo 
        WHERE codice = 'flotta_assegnazioni'
    """)
    if cursor.fetchone():
        print("  → Permesso già esistente, skip")
        return False
    
    cursor.execute('''
        INSERT INTO permessi_catalogo (codice, descrizione, categoria, ordine, attivo)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        'flotta_assegnazioni',
        'Gestire assegnazioni commerciali (visualizza e modifica)',
        'flotta',
        140,
        1
    ))
    
    print("  ✓ Permesso flotta_assegnazioni aggiunto al catalogo")
    return True

def verifica_finale(cursor):
    """Verifica che tutte le modifiche siano state applicate."""
    print("\n" + "="*60)
    print("VERIFICA FINALE")
    print("="*60)
    
    errori = []
    
    # 1. Campo nome_commerciale_flotta
    cursor.execute("PRAGMA table_info(utenti)")
    colonne = [col[1] for col in cursor.fetchall()]
    if 'nome_commerciale_flotta' in colonne:
        print("✓ Campo nome_commerciale_flotta presente in utenti")
    else:
        errori.append("Campo nome_commerciale_flotta mancante")
    
    # 2. Tabella storico_assegnazioni
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='storico_assegnazioni'
    """)
    if cursor.fetchone():
        print("✓ Tabella storico_assegnazioni presente")
    else:
        errori.append("Tabella storico_assegnazioni mancante")
    
    # 3. Tabella storico_export
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='storico_export'
    """)
    if cursor.fetchone():
        print("✓ Tabella storico_export presente")
    else:
        errori.append("Tabella storico_export mancante")
    
    # 4. Permesso flotta_assegnazioni
    cursor.execute("""
        SELECT id FROM permessi_catalogo 
        WHERE codice = 'flotta_assegnazioni'
    """)
    if cursor.fetchone():
        print("✓ Permesso flotta_assegnazioni presente")
    else:
        errori.append("Permesso flotta_assegnazioni mancante")
    
    if errori:
        print("\n⚠ ERRORI RILEVATI:")
        for e in errori:
            print(f"  ✗ {e}")
        return False
    
    print("\n✓ MIGRAZIONE COMPLETATA CON SUCCESSO!")
    return True

def main():
    print("="*60)
    print("MIGRAZIONE DATABASE - Fase 1: Sistema Assegnazioni")
    print("="*60)
    print(f"Database: {DB_PATH}")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verifica esistenza database
    if not DB_PATH.exists():
        print(f"\n✗ ERRORE: Database non trovato: {DB_PATH}")
        sys.exit(1)
    
    # Backup
    print("\n" + "-"*60)
    backup_database()
    
    # Connessione
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Esegui migrazioni
        print("\n" + "-"*60)
        print("ESECUZIONE MIGRAZIONI")
        print("-"*60)
        
        migrazione_step1_campo_commerciale(cursor)
        migrazione_step2_tabella_storico_assegnazioni(cursor)
        migrazione_step3_tabella_storico_export(cursor)
        migrazione_step4_permesso_assegnazioni(cursor)
        
        # Commit
        conn.commit()
        
        # Verifica
        verifica_finale(cursor)
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ ERRORE durante la migrazione: {e}")
        print("  Database ripristinato (rollback)")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
