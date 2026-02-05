#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MIGRAZIONE DATABASE - MODULO TRATTATIVE
==============================================================================
Versione: 1.0
Data: 2026-01-27
Descrizione: Crea le tabelle per il motore trattative

Tabelle create:
- trattative: tabella principale
- trattative_avanzamenti: storico avanzamenti (timeline)

Uso:
    python3 migrazione_trattative.py [--dry-run]
==============================================================================
"""

import sqlite3
import os
import sys
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================
DB_PATH = os.path.expanduser('~/gestione_flotta/db/gestionale.db')
BACKUP_DIR = os.path.expanduser('~/gestione_flotta/db/backup')

# ==============================================================================
# SQL CREAZIONE TABELLE
# ==============================================================================

SQL_TRATTATIVE = """
CREATE TABLE IF NOT EXISTS trattative (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Collegamento cliente (obbligatorio)
    cliente_id INTEGER NOT NULL,
    
    -- Commerciale proprietario della trattativa
    commerciale_id INTEGER NOT NULL,
    
    -- Dati trattativa
    noleggiatore TEXT,
    marca TEXT,
    descrizione_veicolo TEXT,
    tipologia_veicolo TEXT,
    tipo_trattativa TEXT,
    num_pezzi INTEGER DEFAULT 1,
    
    -- Stato attuale (ultimo stato)
    stato TEXT DEFAULT 'Preso in carico',
    
    -- Date
    data_inizio DATE NOT NULL,
    data_chiusura DATE,
    
    -- Note generali
    note TEXT,
    
    -- Audit trail
    creato_da INTEGER NOT NULL,
    creato_il DATETIME DEFAULT CURRENT_TIMESTAMP,
    modificato_da INTEGER,
    modificato_il DATETIME,
    
    -- Foreign keys
    FOREIGN KEY (cliente_id) REFERENCES clienti(id) ON DELETE RESTRICT,
    FOREIGN KEY (commerciale_id) REFERENCES utenti(id),
    FOREIGN KEY (creato_da) REFERENCES utenti(id),
    FOREIGN KEY (modificato_da) REFERENCES utenti(id)
);
"""

SQL_TRATTATIVE_AVANZAMENTI = """
CREATE TABLE IF NOT EXISTS trattative_avanzamenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Collegamento trattativa
    trattativa_id INTEGER NOT NULL,
    
    -- Dati avanzamento
    stato TEXT NOT NULL,
    note_avanzamento TEXT,
    
    -- Timestamp e autore
    data_avanzamento DATETIME DEFAULT CURRENT_TIMESTAMP,
    registrato_da INTEGER NOT NULL,
    
    -- Foreign keys
    FOREIGN KEY (trattativa_id) REFERENCES trattative(id) ON DELETE CASCADE,
    FOREIGN KEY (registrato_da) REFERENCES utenti(id)
);
"""

SQL_INDICI = """
-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_trattative_cliente ON trattative(cliente_id);
CREATE INDEX IF NOT EXISTS idx_trattative_commerciale ON trattative(commerciale_id);
CREATE INDEX IF NOT EXISTS idx_trattative_stato ON trattative(stato);
CREATE INDEX IF NOT EXISTS idx_trattative_data_inizio ON trattative(data_inizio);
CREATE INDEX IF NOT EXISTS idx_trattative_noleggiatore ON trattative(noleggiatore);
CREATE INDEX IF NOT EXISTS idx_avanzamenti_trattativa ON trattative_avanzamenti(trattativa_id);
CREATE INDEX IF NOT EXISTS idx_avanzamenti_data ON trattative_avanzamenti(data_avanzamento);
"""

# ==============================================================================
# FUNZIONI
# ==============================================================================

def backup_database():
    """Crea backup del database prima della migrazione"""
    if not os.path.exists(DB_PATH):
        print(f"[ERRORE] Database non trovato: {DB_PATH}")
        return False
    
    # Crea directory backup se non esiste
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Nome file backup con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'gestionale_pre_trattative_{timestamp}.db')
    
    # Copia database
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"[OK] Backup creato: {backup_path}")
    return True


def verifica_tabelle_esistenti(conn):
    """Verifica se le tabelle esistono gia'"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('trattative', 'trattative_avanzamenti')
    """)
    
    esistenti = [row[0] for row in cursor.fetchall()]
    return esistenti


def crea_tabelle(conn, dry_run=False):
    """Crea le tabelle per il modulo trattative"""
    cursor = conn.cursor()
    
    # Verifica tabelle esistenti
    esistenti = verifica_tabelle_esistenti(conn)
    
    if esistenti:
        print(f"[INFO] Tabelle gia' esistenti: {', '.join(esistenti)}")
        print("[INFO] Le tabelle non verranno ricreate (IF NOT EXISTS)")
    
    if dry_run:
        print("\n[DRY-RUN] SQL che verrebbe eseguito:")
        print("-" * 60)
        print(SQL_TRATTATIVE)
        print("-" * 60)
        print(SQL_TRATTATIVE_AVANZAMENTI)
        print("-" * 60)
        print(SQL_INDICI)
        print("-" * 60)
        return True
    
    try:
        # Crea tabella trattative
        print("[*] Creazione tabella 'trattative'...")
        cursor.executescript(SQL_TRATTATIVE)
        print("[OK] Tabella 'trattative' creata/verificata")
        
        # Crea tabella avanzamenti
        print("[*] Creazione tabella 'trattative_avanzamenti'...")
        cursor.executescript(SQL_TRATTATIVE_AVANZAMENTI)
        print("[OK] Tabella 'trattative_avanzamenti' creata/verificata")
        
        # Crea indici
        print("[*] Creazione indici...")
        cursor.executescript(SQL_INDICI)
        print("[OK] Indici creati/verificati")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"[ERRORE] Creazione tabelle fallita: {e}")
        conn.rollback()
        return False


def verifica_struttura(conn):
    """Verifica la struttura delle tabelle create"""
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("VERIFICA STRUTTURA TABELLE")
    print("=" * 60)
    
    for tabella in ['trattative', 'trattative_avanzamenti']:
        cursor.execute(f"PRAGMA table_info({tabella})")
        colonne = cursor.fetchall()
        
        if colonne:
            print(f"\n[{tabella}]")
            print(f"{'Col':<4} {'Nome':<25} {'Tipo':<15} {'NotNull':<8} {'Default':<20}")
            print("-" * 72)
            for col in colonne:
                cid, name, tipo, notnull, default, pk = col
                print(f"{cid:<4} {name:<25} {tipo:<15} {notnull:<8} {str(default):<20}")
        else:
            print(f"\n[ERRORE] Tabella '{tabella}' non trovata!")
    
    # Conta indici
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE 'idx_trattative%' OR name LIKE 'idx_avanzamenti%'
    """)
    indici = cursor.fetchall()
    print(f"\n[INFO] Indici creati: {len(indici)}")
    for idx in indici:
        print(f"  - {idx[0]}")


def main():
    """Funzione principale"""
    print("=" * 60)
    print("MIGRAZIONE DATABASE - MODULO TRATTATIVE")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check dry-run
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("\n[MODO DRY-RUN] Nessuna modifica verra' applicata\n")
    
    # Verifica esistenza database
    if not os.path.exists(DB_PATH):
        print(f"[ERRORE] Database non trovato: {DB_PATH}")
        sys.exit(1)
    
    # Backup (solo se non dry-run)
    if not dry_run:
        print("\n[1/3] Creazione backup...")
        if not backup_database():
            print("[ERRORE] Backup fallito, migrazione annullata")
            sys.exit(1)
    
    # Connessione
    print("\n[2/3] Connessione al database...")
    conn = sqlite3.connect(DB_PATH)
    print("[OK] Connesso")
    
    # Creazione tabelle
    print("\n[3/3] Creazione tabelle...")
    if not crea_tabelle(conn, dry_run):
        conn.close()
        sys.exit(1)
    
    # Verifica (solo se non dry-run)
    if not dry_run:
        verifica_struttura(conn)
    
    conn.close()
    
    print("\n" + "=" * 60)
    if dry_run:
        print("DRY-RUN COMPLETATO - Nessuna modifica applicata")
        print("Esegui senza --dry-run per applicare le modifiche")
    else:
        print("MIGRAZIONE COMPLETATA CON SUCCESSO!")
    print("=" * 60)


if __name__ == '__main__':
    main()
