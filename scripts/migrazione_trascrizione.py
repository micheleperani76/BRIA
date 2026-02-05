#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE - Tabella coda_trascrizioni
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-03
# Descrizione: Crea la tabella coda_trascrizioni e le cartelle necessarie
# Eseguire una sola volta: python3 scripts/migrazione_trascrizione.py
# ==============================================================================

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Path base
BASE_DIR = Path(__file__).parent.parent.absolute()
DB_FILE = BASE_DIR / "db" / "gestionale.db"

# Cartelle da creare
CARTELLE = [
    BASE_DIR / "trascrizione" / "attesa",
    BASE_DIR / "trascrizione" / "lavorazione",
    BASE_DIR / "trascrizione" / "completati",
    BASE_DIR / "trascrizione" / "testi",
    BASE_DIR / "trascrizione" / "consumo",
]


def crea_tabella(conn):
    """Crea la tabella coda_trascrizioni se non esiste."""
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coda_trascrizioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Chi e dove
            utente_id INTEGER NOT NULL,
            codice_utente TEXT NOT NULL,
            nome_utente TEXT,
            cliente_id INTEGER,
            tipo TEXT NOT NULL DEFAULT 'dashboard',
            
            -- File audio
            nome_file_originale TEXT NOT NULL,
            nome_file_sistema TEXT NOT NULL,
            formato_originale TEXT,
            dimensione_bytes INTEGER DEFAULT 0,
            durata_secondi REAL,
            
            -- Stato coda
            stato TEXT DEFAULT 'attesa',
            priorita INTEGER DEFAULT 1,
            progresso_percentuale INTEGER DEFAULT 0,
            
            -- Configurazione elaborazione
            modello TEXT DEFAULT 'large-v3',
            lingua TEXT DEFAULT 'it',
            
            -- Date
            data_inserimento TEXT NOT NULL,
            data_inizio_elaborazione TEXT,
            data_completamento TEXT,
            
            -- Risultato
            percorso_testo TEXT,
            percorso_audio_finale TEXT,
            errore TEXT,
            
            -- Retention
            data_scadenza_audio TEXT,
            data_scadenza_testo TEXT,
            
            -- Foreign keys
            FOREIGN KEY (utente_id) REFERENCES utenti(id)
        )
    ''')
    
    # Indici per performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_coda_stato 
        ON coda_trascrizioni(stato)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_coda_utente 
        ON coda_trascrizioni(utente_id)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_coda_priorita_data 
        ON coda_trascrizioni(stato, priorita DESC, data_inserimento ASC)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_coda_scadenza_audio 
        ON coda_trascrizioni(data_scadenza_audio)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_coda_scadenza_testo 
        ON coda_trascrizioni(data_scadenza_testo)
    ''')
    
    conn.commit()
    return True


def crea_cartelle():
    """Crea le cartelle necessarie."""
    create = 0
    for cartella in CARTELLE:
        if not cartella.exists():
            cartella.mkdir(parents=True, exist_ok=True)
            print(f"  + Creata: {cartella}")
            create += 1
        else:
            print(f"  = Esiste: {cartella}")
    return create


def verifica_tabella(conn):
    """Verifica che la tabella sia stata creata correttamente."""
    cursor = conn.cursor()
    
    # Verifica esistenza
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='coda_trascrizioni'
    """)
    if not cursor.fetchone():
        return False
    
    # Verifica colonne
    cursor.execute("PRAGMA table_info(coda_trascrizioni)")
    colonne = [row[1] for row in cursor.fetchall()]
    
    colonne_attese = [
        'id', 'utente_id', 'codice_utente', 'nome_utente', 'cliente_id',
        'tipo', 'nome_file_originale', 'nome_file_sistema', 'formato_originale',
        'dimensione_bytes', 'durata_secondi', 'stato', 'priorita',
        'progresso_percentuale', 'modello', 'lingua', 'data_inserimento',
        'data_inizio_elaborazione', 'data_completamento', 'percorso_testo',
        'percorso_audio_finale', 'errore', 'data_scadenza_audio', 'data_scadenza_testo'
    ]
    
    mancanti = [c for c in colonne_attese if c not in colonne]
    if mancanti:
        print(f"  ! Colonne mancanti: {mancanti}")
        return False
    
    return True


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  MIGRAZIONE - Tabella coda_trascrizioni")
    print("=" * 60)
    print()
    
    # Verifica DB
    if not DB_FILE.exists():
        print(f"ERRORE: Database non trovato: {DB_FILE}")
        sys.exit(1)
    
    print(f"Database: {DB_FILE}")
    print()
    
    # Backup consigliato
    print("IMPORTANTE: Assicurati di avere un backup del database!")
    print()
    
    # Connessione
    conn = sqlite3.connect(str(DB_FILE))
    
    # 1. Crea tabella
    print("[1/3] Creazione tabella coda_trascrizioni...")
    try:
        crea_tabella(conn)
        print("  OK - Tabella creata/verificata")
    except Exception as e:
        print(f"  ERRORE: {e}")
        conn.close()
        sys.exit(1)
    
    # 2. Verifica tabella
    print()
    print("[2/3] Verifica struttura tabella...")
    if verifica_tabella(conn):
        print("  OK - Tutte le colonne presenti")
    else:
        print("  ERRORE - Struttura tabella non corretta")
        conn.close()
        sys.exit(1)
    
    # 3. Crea cartelle
    print()
    print("[3/3] Creazione cartelle...")
    create = crea_cartelle()
    
    conn.close()
    
    print()
    print("=" * 60)
    print(f"  MIGRAZIONE COMPLETATA")
    print(f"  Cartelle create: {create}")
    print("=" * 60)
    
    # Mostra stati possibili
    print()
    print("Stati coda_trascrizioni:")
    print("  attesa       - File in coda, in attesa di elaborazione")
    print("  lavorazione  - File in corso di trascrizione")
    print("  completato   - Trascrizione completata con successo")
    print("  errore       - Errore durante la trascrizione")
    print("  sospeso      - Sospeso (fuori orario o manualmente)")
