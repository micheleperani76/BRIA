#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MIGRAZIONE DATABASE - MODULO TICKER BROADCASTING
==============================================================================
Versione: 1.0
Data: 2026-02-06
Descrizione: Crea le tabelle per il sistema ticker broadcasting

Tabelle create:
- ticker_messaggi: messaggi con scheduling e animazioni
- ticker_config: configurazione sistema
- ticker_log: log visualizzazioni

Uso:
    python3 migrazione_ticker.py [--dry-run]
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

SQL_TICKER_MESSAGGI = """
CREATE TABLE IF NOT EXISTS ticker_messaggi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Contenuto
    testo TEXT NOT NULL,
    icona TEXT DEFAULT '',
    colore_testo TEXT DEFAULT '#000000',
    
    -- Animazione
    animazione TEXT DEFAULT 'scroll-rtl',
    durata_secondi INTEGER DEFAULT 8,
    velocita TEXT DEFAULT 'normale',
    
    -- Scheduling
    data_inizio TEXT NOT NULL,
    data_fine TEXT,
    ora_inizio TEXT DEFAULT '00:00',
    ora_fine TEXT DEFAULT '23:59',
    giorni_settimana TEXT DEFAULT '1,2,3,4,5,6,7',
    ricorrenza TEXT DEFAULT 'nessuna',
    
    -- Priorita e frequenza
    priorita INTEGER DEFAULT 5,
    peso INTEGER DEFAULT 1,
    
    -- Destinatari
    destinatari TEXT DEFAULT 'TUTTI',
    
    -- Approvazione
    stato TEXT DEFAULT 'bozza',
    creato_da INTEGER NOT NULL,
    approvato_da INTEGER,
    data_approvazione TEXT,
    nota_rifiuto TEXT,
    
    -- Tipo
    tipo TEXT DEFAULT 'manuale',
    codice_auto TEXT,
    
    -- Audit
    data_creazione TEXT DEFAULT (datetime('now', 'localtime')),
    data_modifica TEXT,
    
    FOREIGN KEY (creato_da) REFERENCES utenti(id),
    FOREIGN KEY (approvato_da) REFERENCES utenti(id)
);
"""

SQL_TICKER_CONFIG = """
CREATE TABLE IF NOT EXISTS ticker_config (
    chiave TEXT PRIMARY KEY,
    valore TEXT NOT NULL,
    descrizione TEXT
);
"""

SQL_TICKER_LOG = """
CREATE TABLE IF NOT EXISTS ticker_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    messaggio_id INTEGER NOT NULL,
    utente_id INTEGER NOT NULL,
    data_visualizzazione TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (messaggio_id) REFERENCES ticker_messaggi(id)
);
"""

# ==============================================================================
# INDICI
# ==============================================================================

SQL_INDICI = [
    "CREATE INDEX IF NOT EXISTS idx_ticker_stato ON ticker_messaggi(stato);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_date ON ticker_messaggi(data_inizio, data_fine);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_tipo ON ticker_messaggi(tipo);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_codice ON ticker_messaggi(codice_auto);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_creato_da ON ticker_messaggi(creato_da);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_destinatari ON ticker_messaggi(destinatari);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_log_msg ON ticker_log(messaggio_id);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_log_data ON ticker_log(data_visualizzazione);",
    "CREATE INDEX IF NOT EXISTS idx_ticker_log_utente ON ticker_log(utente_id);",
]

# ==============================================================================
# CONFIGURAZIONE DEFAULT
# ==============================================================================

CONFIG_DEFAULT = [
    ('messaggi_ora', '4', 'Messaggi massimi per ora'),
    ('pausa_minima_sec', '120', 'Pausa minima tra messaggi (secondi)'),
    ('pausa_massima_sec', '600', 'Pausa massima tra messaggi (secondi)'),
    ('attivo', '1', 'Sistema ticker attivo (1=si, 0=no)'),
    ('auto_compleanni', '1', 'Genera automaticamente auguri compleanno'),
    ('auto_festivita', '1', 'Genera automaticamente messaggi festivita'),
    ('auto_gomme', '1', 'Genera automaticamente promemoria cambio gomme'),
    ('durata_default', '8', 'Durata default animazione (secondi)'),
    ('animazione_default', 'scroll-rtl', 'Animazione default per nuovi messaggi'),
]

# ==============================================================================
# FUNZIONI MIGRAZIONE
# ==============================================================================

def backup_database():
    """Crea backup del database prima della migrazione."""
    if not os.path.exists(DB_PATH):
        print("  ERRORE: Database non trovato!")
        sys.exit(1)
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'gestionale_pre_ticker_{ts}.db')
    
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"  OK - Backup: {backup_path}")
    return backup_path


def tabella_esiste(cursor, nome):
    """Verifica se una tabella esiste gia."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (nome,)
    )
    return cursor.fetchone() is not None


def crea_tabelle(conn, dry_run=False):
    """Crea le 3 tabelle del modulo ticker."""
    cursor = conn.cursor()
    
    tabelle = [
        ('ticker_messaggi', SQL_TICKER_MESSAGGI),
        ('ticker_config', SQL_TICKER_CONFIG),
        ('ticker_log', SQL_TICKER_LOG),
    ]
    
    for nome, sql in tabelle:
        if tabella_esiste(cursor, nome):
            print(f"  SKIP - {nome} gia esistente")
        else:
            if dry_run:
                print(f"  [DRY-RUN] Creerebbe {nome}")
            else:
                cursor.execute(sql)
                print(f"  OK - {nome} creata")
    
    if not dry_run:
        conn.commit()


def crea_indici(conn, dry_run=False):
    """Crea gli indici di performance."""
    cursor = conn.cursor()
    creati = 0
    
    for sql in SQL_INDICI:
        if dry_run:
            print(f"  [DRY-RUN] {sql[:60]}...")
        else:
            cursor.execute(sql)
            creati += 1
    
    if not dry_run:
        conn.commit()
        print(f"  OK - {creati} indici creati/verificati")


def inserisci_config_default(conn, dry_run=False):
    """Inserisce configurazione default (senza sovrascrivere)."""
    cursor = conn.cursor()
    inseriti = 0
    
    for chiave, valore, descrizione in CONFIG_DEFAULT:
        cursor.execute(
            "SELECT chiave FROM ticker_config WHERE chiave = ?",
            (chiave,)
        )
        if cursor.fetchone():
            print(f"  SKIP - {chiave} gia presente")
        else:
            if dry_run:
                print(f"  [DRY-RUN] Inserirebbe {chiave} = {valore}")
            else:
                cursor.execute(
                    "INSERT INTO ticker_config (chiave, valore, descrizione) VALUES (?, ?, ?)",
                    (chiave, valore, descrizione)
                )
                inseriti += 1
    
    if not dry_run:
        conn.commit()
        print(f"  OK - {inseriti} configurazioni inserite")


def verifica(conn):
    """Verifica che la migrazione sia corretta."""
    cursor = conn.cursor()
    errori = 0
    
    # Verifica tabelle
    for tab in ['ticker_messaggi', 'ticker_config', 'ticker_log']:
        if tabella_esiste(cursor, tab):
            cursor.execute(f"SELECT COUNT(*) FROM {tab}")
            count = cursor.fetchone()[0]
            print(f"  OK - {tab} ({count} record)")
        else:
            print(f"  ERRORE - {tab} NON TROVATA!")
            errori += 1
    
    # Verifica config
    cursor.execute("SELECT COUNT(*) FROM ticker_config")
    config_count = cursor.fetchone()[0]
    if config_count >= len(CONFIG_DEFAULT):
        print(f"  OK - Configurazione completa ({config_count} parametri)")
    else:
        print(f"  WARN - Configurazione parziale ({config_count}/{len(CONFIG_DEFAULT)})")
    
    return errori == 0


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv
    
    print("")
    print("=" * 60)
    print("  MIGRAZIONE TICKER BROADCASTING")
    if dry_run:
        print("  *** MODALITA DRY-RUN (nessuna modifica) ***")
    print("=" * 60)
    print("")
    
    # 1. Backup
    print("[1/5] Backup database...")
    if not dry_run:
        backup_database()
    else:
        print("  [DRY-RUN] Salterebbe backup")
    
    # 2. Connessione
    print("")
    print("[2/5] Connessione database...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"  OK - {DB_PATH}")
    
    # 3. Creazione tabelle
    print("")
    print("[3/5] Creazione tabelle...")
    crea_tabelle(conn, dry_run)
    
    # 4. Indici
    print("")
    print("[4/5] Creazione indici...")
    crea_indici(conn, dry_run)
    
    # 5. Config default
    print("")
    print("[5/5] Configurazione default...")
    inserisci_config_default(conn, dry_run)
    
    # Verifica
    if not dry_run:
        print("")
        print("Verifica finale...")
        ok = verifica(conn)
        
        print("")
        print("=" * 60)
        if ok:
            print("  MIGRAZIONE COMPLETATA CON SUCCESSO")
        else:
            print("  MIGRAZIONE COMPLETATA CON ERRORI")
        print("=" * 60)
    else:
        print("")
        print("=" * 60)
        print("  DRY-RUN COMPLETATO - Nessuna modifica al database")
        print("  Rilancia senza --dry-run per applicare")
        print("=" * 60)
    
    conn.close()
    print("")


if __name__ == '__main__':
    main()
