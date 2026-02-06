#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE TICKER FASE 4 - Festivita' + Config Deposito Bilancio
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-06
# Descrizione:
#   - Crea tabella ticker_festivita (fisse italiane + personalizzabili)
#   - Aggiunge config: auto_deposito_bilancio
#   - Popola festivita' fisse italiane
# ==============================================================================

import sqlite3
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.expanduser('~/gestione_flotta')
DB_PATH = os.path.join(BASE_DIR, 'db', 'gestionale.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'db', 'backup')

def backup_db():
    """Backup database prima della migrazione."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_DIR, f'gestionale_pre_ticker_fase4_{ts}.db')
    shutil.copy2(DB_PATH, dest)
    print(f'  Backup: {dest}')
    return dest

def migra():
    """Esegue la migrazione Fase 4."""
    
    print('=' * 60)
    print('  MIGRAZIONE TICKER FASE 4')
    print('=' * 60)
    print()
    
    # === BACKUP ===
    print('[1/4] Backup database...')
    backup_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # === TABELLA FESTIVITA ===
    print()
    print('[2/4] Creazione tabella ticker_festivita...')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ticker_festivita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            giorno INTEGER NOT NULL,
            mese INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'fissa',
            attiva INTEGER NOT NULL DEFAULT 1,
            creata_il TEXT DEFAULT (datetime('now', 'localtime')),
            note TEXT DEFAULT NULL
        )
    ''')
    
    # Indice per ricerca rapida per mese/giorno
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_festivita_data
        ON ticker_festivita(mese, giorno)
    ''')
    
    print('  OK - Tabella ticker_festivita creata')
    
    # === POPOLA FESTIVITA FISSE ITALIANE ===
    print()
    print('[3/4] Inserimento festivita fisse italiane...')
    
    festivita_fisse = [
        ('Capodanno', 1, 1, 'fissa'),
        ('Epifania', 6, 1, 'fissa'),
        ('Anniversario della Liberazione', 25, 4, 'fissa'),
        ('Festa del Lavoro', 1, 5, 'fissa'),
        ('Festa della Repubblica', 2, 6, 'fissa'),
        ('Ferragosto', 15, 8, 'fissa'),
        ('Tutti i Santi', 1, 11, 'fissa'),
        ('Immacolata Concezione', 8, 12, 'fissa'),
        ('Natale', 25, 12, 'fissa'),
        ('Santo Stefano', 26, 12, 'fissa'),
    ]
    
    # Controlla se gia' popolata
    cur.execute('SELECT COUNT(*) FROM ticker_festivita')
    conteggio = cur.fetchone()[0]
    
    if conteggio == 0:
        for nome, giorno, mese, tipo in festivita_fisse:
            cur.execute('''
                INSERT INTO ticker_festivita (nome, giorno, mese, tipo)
                VALUES (?, ?, ?, ?)
            ''', (nome, giorno, mese, tipo))
        print(f'  OK - {len(festivita_fisse)} festivita inserite')
    else:
        print(f'  SKIP - Tabella gia popolata ({conteggio} record)')
    
    # === NUOVE CONFIG ===
    print()
    print('[4/4] Aggiunta config deposito bilancio...')
    
    nuove_config = [
        ('auto_deposito_bilancio', '1', 'Genera reminder deposito bilancio CCIAA'),
    ]
    
    for chiave, valore, desc in nuove_config:
        cur.execute('SELECT COUNT(*) FROM ticker_config WHERE chiave = ?', (chiave,))
        if cur.fetchone()[0] == 0:
            cur.execute('''
                INSERT INTO ticker_config (chiave, valore, descrizione)
                VALUES (?, ?, ?)
            ''', (chiave, valore, desc))
            print(f'  OK - Config "{chiave}" aggiunta')
        else:
            print(f'  SKIP - Config "{chiave}" gia presente')
    
    conn.commit()
    
    # === VERIFICA ===
    print()
    print('--- Verifica finale ---')
    
    cur.execute('SELECT COUNT(*) FROM ticker_festivita')
    print(f'  Festivita: {cur.fetchone()[0]} record')
    
    cur.execute('SELECT COUNT(*) FROM ticker_config')
    print(f'  Config ticker: {cur.fetchone()[0]} parametri')
    
    cur.execute("SELECT nome, giorno, mese FROM ticker_festivita WHERE tipo='fissa' ORDER BY mese, giorno")
    for r in cur.fetchall():
        print(f'    {r["giorno"]:2d}/{r["mese"]:02d} - {r["nome"]}')
    
    conn.close()
    
    print()
    print('=' * 60)
    print('  MIGRAZIONE FASE 4 COMPLETATA')
    print('=' * 60)

if __name__ == '__main__':
    migra()
