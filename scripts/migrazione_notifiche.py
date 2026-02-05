#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MIGRAZIONE DATABASE - SISTEMA NOTIFICHE
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: Crea le tabelle per il sistema notifiche centralizzato

Tabelle create:
- notifiche:              notifiche generate dai connettori
- notifiche_destinatari:  chi deve ricevere (stato letta/archiviata)
- notifiche_preferenze:   preferenze utente per categoria
- notifiche_regole:       regole di distribuzione (chi riceve cosa)

Uso:
    python3 scripts/migrazione_notifiche.py [--dry-run]
==============================================================================
"""

import sqlite3
import os
import sys
import shutil
from datetime import datetime


# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

DB_PATH = os.path.expanduser('~/gestione_flotta/db/gestionale.db')
BACKUP_DIR = os.path.expanduser('~/gestione_flotta/db/backup')


# ==============================================================================
# SQL CREAZIONE TABELLE
# ==============================================================================

SQL_NOTIFICHE = """
CREATE TABLE IF NOT EXISTS notifiche (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Contenuto
    categoria TEXT NOT NULL,
    livello INTEGER DEFAULT 1,
    titolo TEXT NOT NULL,
    messaggio TEXT,
    
    -- Azione collegata (opzionale)
    url_azione TEXT,
    etichetta_azione TEXT,
    
    -- Origine
    connettore TEXT NOT NULL,
    codice_evento TEXT,
    
    -- Temporalita'
    data_creazione TEXT NOT NULL,
    data_scadenza TEXT,
    ricorrente INTEGER DEFAULT 0,
    
    -- Stato globale
    attiva INTEGER DEFAULT 1
);
"""

SQL_NOTIFICHE_DESTINATARI = """
CREATE TABLE IF NOT EXISTS notifiche_destinatari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notifica_id INTEGER NOT NULL,
    utente_id INTEGER NOT NULL,
    
    -- Stato per questo utente
    letta INTEGER DEFAULT 0,
    data_lettura TEXT,
    archiviata INTEGER DEFAULT 0,
    data_archiviazione TEXT,
    
    FOREIGN KEY (notifica_id) REFERENCES notifiche(id) ON DELETE CASCADE,
    FOREIGN KEY (utente_id) REFERENCES utenti(id),
    UNIQUE(notifica_id, utente_id)
);
"""

SQL_NOTIFICHE_PREFERENZE = """
CREATE TABLE IF NOT EXISTS notifiche_preferenze (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utente_id INTEGER NOT NULL,
    
    -- Quale categoria
    categoria TEXT NOT NULL,
    
    -- Canali abilitati per questa categoria
    campanella INTEGER DEFAULT 1,
    email INTEGER DEFAULT 0,
    telegram INTEGER DEFAULT 0,
    
    -- Livello minimo per ricevere (0=tutto, 1=INFO+, 2=AVVISO+, 3=solo ALLARME)
    livello_minimo INTEGER DEFAULT 0,
    
    -- Silenziato temporaneamente
    silenziato INTEGER DEFAULT 0,
    
    FOREIGN KEY (utente_id) REFERENCES utenti(id),
    UNIQUE(utente_id, categoria)
);
"""

SQL_NOTIFICHE_REGOLE = """
CREATE TABLE IF NOT EXISTS notifiche_regole (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Quale categoria e connettore
    categoria TEXT NOT NULL,
    connettore TEXT,
    
    -- A chi inviare
    destinazione TEXT NOT NULL,
    
    -- Filtro opzionale
    condizione TEXT,
    
    -- Stato
    attiva INTEGER DEFAULT 1,
    note TEXT,
    
    creato_il TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

SQL_INDICI = """
-- Indici notifiche
CREATE INDEX IF NOT EXISTS idx_notifiche_categoria ON notifiche(categoria);
CREATE INDEX IF NOT EXISTS idx_notifiche_livello ON notifiche(livello);
CREATE INDEX IF NOT EXISTS idx_notifiche_data ON notifiche(data_creazione);
CREATE INDEX IF NOT EXISTS idx_notifiche_connettore ON notifiche(connettore);
CREATE INDEX IF NOT EXISTS idx_notifiche_codice_evento ON notifiche(codice_evento);
CREATE INDEX IF NOT EXISTS idx_notifiche_attiva ON notifiche(attiva);

-- Indici destinatari
CREATE INDEX IF NOT EXISTS idx_notdest_utente ON notifiche_destinatari(utente_id);
CREATE INDEX IF NOT EXISTS idx_notdest_notifica ON notifiche_destinatari(notifica_id);
CREATE INDEX IF NOT EXISTS idx_notdest_letta ON notifiche_destinatari(letta);
CREATE INDEX IF NOT EXISTS idx_notdest_archiviata ON notifiche_destinatari(archiviata);

-- Indici preferenze
CREATE INDEX IF NOT EXISTS idx_notpref_utente ON notifiche_preferenze(utente_id);
CREATE INDEX IF NOT EXISTS idx_notpref_categoria ON notifiche_preferenze(categoria);

-- Indici regole
CREATE INDEX IF NOT EXISTS idx_notregole_categoria ON notifiche_regole(categoria);
CREATE INDEX IF NOT EXISTS idx_notregole_attiva ON notifiche_regole(attiva);
"""


# ==============================================================================
# REGOLE DEFAULT
# ==============================================================================

# Destinazione:
#   'TUTTI'               -> tutti gli utenti attivi
#   'RUOLO:ADMIN'         -> solo admin
#   'RUOLO:COMMERCIALE'   -> solo commerciali
#   'PROPRIETARIO'        -> solo il proprietario dell'entita' (passato come destinatario specifico)
#   'SUPERVISORE'         -> supervisore del commerciale coinvolto

REGOLE_DEFAULT = [
    # categoria, connettore, destinazione, condizione, note
    ('TASK',                'task',         'PROPRIETARIO',     None, 'Task assegnato a utente specifico'),
    ('TASK',                'task',         'RUOLO:ADMIN',      None, 'Admin vede tutti i task'),
    ('TRASCRIZIONE',        'trascrizione', 'PROPRIETARIO',     None, 'Chi ha caricato il file'),
    ('SCADENZA_CONTRATTO',  'scadenze',     'PROPRIETARIO',     None, 'Commerciale assegnato al cliente'),
    ('SCADENZA_CONTRATTO',  'scadenze',     'RUOLO:ADMIN',      None, 'Admin vede tutte le scadenze'),
    ('SCADENZA_DOCUMENTO',  'scadenze',     'PROPRIETARIO',     None, 'Commerciale assegnato al cliente'),
    ('DOCUMENTO',           'documenti',    'PROPRIETARIO',     None, 'Commerciale assegnato al cliente'),
    ('CALENDARIO',          'calendario',   'PROPRIETARIO',     None, 'Chi ha l\'evento in calendario'),
    ('STAGIONALE',          'stagionali',   'TUTTI',            None, 'Avvisi stagionali a tutti'),
    ('COMPLEANNO',          'compleanni',   'PROPRIETARIO',     None, 'Commerciale assegnato al cliente'),
    ('ASSEGNAZIONE',        'assegnazioni', 'PROPRIETARIO',     None, 'Nuovo commerciale assegnato'),
    ('ASSEGNAZIONE',        'assegnazioni', 'RUOLO:ADMIN',      None, 'Admin vede tutte le assegnazioni'),
    ('TRATTATIVA',          'trattative',   'PROPRIETARIO',     None, 'Commerciale proprietario trattativa'),
    ('TOP_PROSPECT',        'top_prospect', 'PROPRIETARIO',     None, 'Commerciale assegnato al prospect'),
    ('TOP_PROSPECT',        'top_prospect', 'RUOLO:ADMIN',      None, 'Admin vede tutti i prospect'),
    ('EMAIL',               'email_imap',   'PROPRIETARIO',     None, 'Proprietario casella email'),
    ('SISTEMA',             'sistema',      'RUOLO:ADMIN',      None, 'Solo admin vede notifiche sistema'),
]


# ==============================================================================
# FUNZIONI
# ==============================================================================

def backup_database():
    """Crea backup del database prima della migrazione"""
    if not os.path.exists(DB_PATH):
        print(f"[ERRORE] Database non trovato: {DB_PATH}")
        return False
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'gestionale_pre_notifiche_{timestamp}.db')
    
    shutil.copy2(DB_PATH, backup_path)
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    print(f"[OK] Backup creato: {backup_path} ({size_mb:.1f} MB)")
    return True


def verifica_tabelle_esistenti(conn):
    """Verifica se le tabelle esistono gia'"""
    cursor = conn.cursor()
    
    nomi = ['notifiche', 'notifiche_destinatari', 'notifiche_preferenze', 'notifiche_regole']
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ({})
    """.format(','.join(f"'{n}'" for n in nomi)))
    
    esistenti = [row[0] for row in cursor.fetchall()]
    return esistenti


def crea_tabelle(conn, dry_run=False):
    """Crea le 4 tabelle per il sistema notifiche"""
    cursor = conn.cursor()
    
    esistenti = verifica_tabelle_esistenti(conn)
    
    if esistenti:
        print(f"[INFO] Tabelle gia' esistenti: {', '.join(esistenti)}")
        print("[INFO] Le tabelle non verranno ricreate (IF NOT EXISTS)")
    
    if dry_run:
        print("\n[DRY-RUN] SQL che verrebbe eseguito:")
        print("-" * 60)
        for nome, sql in [('notifiche', SQL_NOTIFICHE), 
                          ('notifiche_destinatari', SQL_NOTIFICHE_DESTINATARI),
                          ('notifiche_preferenze', SQL_NOTIFICHE_PREFERENZE),
                          ('notifiche_regole', SQL_NOTIFICHE_REGOLE)]:
            print(f"\n--- {nome} ---")
            print(sql)
        print("-" * 60)
        print(f"\nIndici:")
        print(SQL_INDICI)
        print("-" * 60)
        print(f"\nRegole default: {len(REGOLE_DEFAULT)} righe")
        for r in REGOLE_DEFAULT:
            print(f"  {r[0]:25s} -> {r[2]:20s} ({r[4]})")
        return True
    
    try:
        # Abilita foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Crea tabelle
        print("[*] Creazione tabella 'notifiche'...")
        cursor.executescript(SQL_NOTIFICHE)
        print("[OK] Tabella 'notifiche' creata/verificata")
        
        print("[*] Creazione tabella 'notifiche_destinatari'...")
        cursor.executescript(SQL_NOTIFICHE_DESTINATARI)
        print("[OK] Tabella 'notifiche_destinatari' creata/verificata")
        
        print("[*] Creazione tabella 'notifiche_preferenze'...")
        cursor.executescript(SQL_NOTIFICHE_PREFERENZE)
        print("[OK] Tabella 'notifiche_preferenze' creata/verificata")
        
        print("[*] Creazione tabella 'notifiche_regole'...")
        cursor.executescript(SQL_NOTIFICHE_REGOLE)
        print("[OK] Tabella 'notifiche_regole' creata/verificata")
        
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


def inserisci_regole_default(conn, dry_run=False):
    """Inserisce le regole di distribuzione default"""
    cursor = conn.cursor()
    
    # Conta regole esistenti
    cursor.execute("SELECT COUNT(*) FROM notifiche_regole")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"[INFO] Tabella notifiche_regole contiene gia' {count} regole, salto inserimento")
        return True
    
    if dry_run:
        print(f"\n[DRY-RUN] Verrebbero inserite {len(REGOLE_DEFAULT)} regole default")
        return True
    
    try:
        for categoria, connettore, destinazione, condizione, note in REGOLE_DEFAULT:
            cursor.execute("""
                INSERT INTO notifiche_regole 
                (categoria, connettore, destinazione, condizione, attiva, note)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (categoria, connettore, destinazione, condizione, note))
        
        conn.commit()
        print(f"[OK] Inserite {len(REGOLE_DEFAULT)} regole default")
        return True
        
    except Exception as e:
        print(f"[ERRORE] Inserimento regole fallito: {e}")
        conn.rollback()
        return False


def verifica_struttura(conn):
    """Verifica la struttura delle tabelle create"""
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("VERIFICA STRUTTURA TABELLE")
    print("=" * 60)
    
    tabelle = ['notifiche', 'notifiche_destinatari', 'notifiche_preferenze', 'notifiche_regole']
    
    for tabella in tabelle:
        cursor.execute(f"PRAGMA table_info({tabella})")
        colonne = cursor.fetchall()
        
        if colonne:
            print(f"\n[OK] {tabella} ({len(colonne)} colonne):")
            for col in colonne:
                nullable = "" if col[3] else "NULL"
                default = f" DEFAULT={col[4]}" if col[4] is not None else ""
                pk = " PK" if col[5] else ""
                print(f"     {col[1]:25s} {col[2]:10s} {nullable:4s}{default}{pk}")
        else:
            print(f"\n[ERRORE] {tabella}: TABELLA NON TROVATA!")
    
    # Conta indici
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE 'idx_not%'
    """)
    indici = cursor.fetchall()
    print(f"\nIndici notifiche: {len(indici)}")
    for idx in indici:
        print(f"  {idx[0]}")
    
    # Conta regole
    cursor.execute("SELECT COUNT(*) FROM notifiche_regole")
    n_regole = cursor.fetchone()[0]
    print(f"\nRegole distribuzione: {n_regole}")
    
    if n_regole > 0:
        cursor.execute("SELECT categoria, destinazione, note FROM notifiche_regole ORDER BY categoria")
        for row in cursor.fetchall():
            print(f"  {row[0]:25s} -> {row[1]:20s} ({row[2]})")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 60)
    print("MIGRAZIONE DATABASE - SISTEMA NOTIFICHE")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Data:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Controlla argomenti
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("\n*** MODALITA' DRY-RUN: nessuna modifica effettuata ***\n")
    
    # Verifica database
    if not os.path.exists(DB_PATH):
        print(f"[ERRORE] Database non trovato: {DB_PATH}")
        sys.exit(1)
    
    # Step 1: Backup
    print("\n--- STEP 1: BACKUP ---")
    if not dry_run:
        if not backup_database():
            print("[ERRORE] Backup fallito, migrazione annullata")
            sys.exit(1)
    else:
        print("[DRY-RUN] Backup saltato")
    
    # Connessione
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Step 2: Crea tabelle
        print("\n--- STEP 2: CREAZIONE TABELLE ---")
        if not crea_tabelle(conn, dry_run):
            print("[ERRORE] Creazione tabelle fallita")
            sys.exit(1)
        
        # Step 3: Regole default
        print("\n--- STEP 3: REGOLE DEFAULT ---")
        if not inserisci_regole_default(conn, dry_run):
            print("[ERRORE] Inserimento regole fallito")
            sys.exit(1)
        
        # Step 4: Verifica
        if not dry_run:
            verifica_struttura(conn)
        
        print("\n" + "=" * 60)
        if dry_run:
            print("DRY-RUN completato. Nessuna modifica effettuata.")
            print("Eseguire senza --dry-run per applicare le modifiche.")
        else:
            print("MIGRAZIONE COMPLETATA CON SUCCESSO!")
        print("=" * 60)
        
    finally:
        conn.close()


if __name__ == '__main__':
    main()
