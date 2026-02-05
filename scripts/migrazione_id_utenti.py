#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE ID UTENTI - Allineamento ID = codice_utente
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-21
#
# Questa migrazione:
# 1. Cambia gli ID utenti per farli corrispondere al codice_utente numerico
# 2. Aggiorna tutte le FK nelle tabelle collegate
# 3. Rimuove la colonna codice_utente (ridondante)
#
# USO:
#   python3 migrazione_id_utenti.py --dry-run   # Verifica
#   python3 migrazione_id_utenti.py             # Esegue
# ==============================================================================

import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

BASE_DIR = Path(__file__).parent.parent.absolute()
DB_FILE = BASE_DIR / 'db' / 'gestionale.db'

# Mappatura: vecchio_id -> nuovo_id (basato su codice_utente)
MAPPATURA = {}

# ==============================================================================
# HELPER
# ==============================================================================

def log(msg, level='INFO'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")

def backup_database():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = DB_FILE.parent / f"gestionale_backup_pre_id_{timestamp}.db"
    shutil.copy(DB_FILE, backup)
    log(f"Backup: {backup.name}")
    return backup

# ==============================================================================
# MIGRAZIONE
# ==============================================================================

def leggi_mappatura(conn):
    """Legge utenti attuali e crea mappatura vecchio_id -> nuovo_id."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, codice_utente, username FROM utenti ORDER BY id")
    
    global MAPPATURA
    MAPPATURA = {}
    
    log("Mappatura ID:")
    for row in cursor.fetchall():
        vecchio_id = row['id']
        codice = row['codice_utente']
        username = row['username']
        
        # Nuovo ID = valore numerico del codice_utente
        nuovo_id = int(codice)
        MAPPATURA[vecchio_id] = nuovo_id
        
        log(f"  {username}: {vecchio_id} -> {nuovo_id}")
    
    return MAPPATURA

def migra_tutte_fk(conn, dry_run=False):
    """Aggiorna tutte le FK verso utenti."""
    log("STEP 1: Aggiornamento FK")
    
    cursor = conn.cursor()
    
    # Lista di tutte le FK da aggiornare
    fk_list = [
        ('veicoli', 'commerciale_id'),
        ('clienti', 'commerciale_id'),
        ('supervisioni', 'supervisore_id'),
        ('supervisioni', 'subordinato_id'),
        ('utenti_permessi', 'utente_id'),
        ('utenti_permessi', 'assegnato_da'),
        ('storico_assegnazioni', 'operatore_id'),
        ('storico_assegnazioni', 'commerciale_precedente_id'),
        ('storico_assegnazioni', 'commerciale_nuovo_id'),
        ('log_accessi', 'utente_id'),
        ('log_attivita', 'utente_id'),
        ('storico_export', 'utente_id'),
    ]
    
    for tabella, colonna in fk_list:
        try:
            # Verifica se tabella esiste
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabella,))
            if not cursor.fetchone():
                log(f"  {tabella}.{colonna}: tabella non esiste, skip")
                continue
            
            # Conta record
            cursor.execute(f"SELECT COUNT(*) FROM {tabella} WHERE {colonna} IS NOT NULL")
            count = cursor.fetchone()[0]
            
            if count == 0:
                log(f"  {tabella}.{colonna}: nessun record")
                continue
            
            log(f"  {tabella}.{colonna}: {count} record")
            
            if dry_run:
                continue
            
            # Aggiorna
            for vecchio_id, nuovo_id in MAPPATURA.items():
                cursor.execute(f'''
                    UPDATE {tabella} SET {colonna} = ? WHERE {colonna} = ?
                ''', (nuovo_id, vecchio_id))
            
        except Exception as e:
            log(f"  {tabella}.{colonna}: ERRORE {e}", 'WARN')
    
    if not dry_run:
        conn.commit()

def migra_utenti(conn, dry_run=False):
    """Ricrea tabella utenti con nuovi ID."""
    cursor = conn.cursor()
    
    log("STEP 2: Ricreazione tabella utenti")
    
    # Leggi dati attuali
    cursor.execute("SELECT * FROM utenti ORDER BY id")
    utenti = [dict(row) for row in cursor.fetchall()]
    log(f"  Trovati {len(utenti)} utenti")
    
    if dry_run:
        log("  [DRY-RUN] Avrebbe ricreato la tabella")
        return
    
    # Rinomina tabella vecchia
    cursor.execute("ALTER TABLE utenti RENAME TO utenti_old")
    
    # Crea nuova tabella SENZA codice_utente
    cursor.execute('''
        CREATE TABLE utenti (
            id INTEGER PRIMARY KEY,
            
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            
            nome TEXT,
            cognome TEXT,
            email TEXT,
            cellulare TEXT,
            
            ruolo_base TEXT DEFAULT 'operatore',
            
            attivo INTEGER DEFAULT 1,
            pwd_temporanea INTEGER DEFAULT 1,
            profilo_completo INTEGER DEFAULT 0,
            bloccato INTEGER DEFAULT 0,
            tentativi_falliti INTEGER DEFAULT 0,
            
            non_cancellabile INTEGER DEFAULT 0,
            non_modificabile INTEGER DEFAULT 0,
            
            data_creazione TEXT,
            data_ultimo_accesso TEXT,
            data_ultimo_cambio_pwd TEXT,
            creato_da INTEGER,
            
            nome_commerciale_flotta TEXT
        )
    ''')
    
    # Inserisci con nuovi ID
    for u in utenti:
        vecchio_id = u['id']
        nuovo_id = MAPPATURA[vecchio_id]
        
        # creato_da va mappato
        creato_da = u['creato_da']
        if creato_da and creato_da in MAPPATURA:
            creato_da = MAPPATURA[creato_da]
        
        cursor.execute('''
            INSERT INTO utenti (
                id, username, password_hash,
                nome, cognome, email, cellulare,
                ruolo_base, attivo, pwd_temporanea, profilo_completo,
                bloccato, tentativi_falliti,
                non_cancellabile, non_modificabile,
                data_creazione, data_ultimo_accesso, data_ultimo_cambio_pwd,
                creato_da, nome_commerciale_flotta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nuovo_id, u['username'], u['password_hash'],
            u['nome'], u['cognome'], u['email'], u['cellulare'],
            u['ruolo_base'], u['attivo'], u['pwd_temporanea'], u['profilo_completo'],
            u['bloccato'], u['tentativi_falliti'],
            u['non_cancellabile'], u['non_modificabile'],
            u['data_creazione'], u['data_ultimo_accesso'], u['data_ultimo_cambio_pwd'],
            creato_da, u['nome_commerciale_flotta']
        ))
    
    # Ricrea indici
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_utenti_username ON utenti(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_utenti_attivo ON utenti(attivo)')
    
    # Elimina tabella vecchia
    cursor.execute("DROP TABLE utenti_old")
    
    conn.commit()
    log("  Tabella utenti ricreata")

def verifica_finale(conn):
    """Verifica integrità dopo migrazione."""
    log("STEP 3: Verifica finale")
    
    cursor = conn.cursor()
    
    # Mostra utenti con nuovi ID
    cursor.execute("SELECT id, username, nome, cognome FROM utenti ORDER BY id")
    log("  Utenti:")
    for row in cursor.fetchall():
        log(f"    {row['id']:06d} - {row['username']} ({row['nome']} {row['cognome']})")
    
    # Verifica commerciale_id in veicoli
    cursor.execute('''
        SELECT commerciale_id, COUNT(*) as num 
        FROM veicoli 
        WHERE commerciale_id IS NOT NULL 
        GROUP BY commerciale_id
    ''')
    log("  Veicoli per commerciale_id:")
    for row in cursor.fetchall():
        cursor.execute("SELECT username FROM utenti WHERE id = ?", (row['commerciale_id'],))
        u = cursor.fetchone()
        nome = u['username'] if u else '???'
        log(f"    {row['commerciale_id']:06d} ({nome}): {row['num']} veicoli")

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    print("=" * 55)
    print("  MIGRAZIONE ID UTENTI")
    print("=" * 55)
    print(f"  Database: {DB_FILE}")
    print(f"  Modalita: {'DRY-RUN' if dry_run else 'ESECUZIONE REALE'}")
    print("=" * 55)
    print()
    
    if not DB_FILE.exists():
        log("Database non trovato!", 'ERROR')
        sys.exit(1)
    
    # Backup
    if not dry_run:
        backup_database()
    else:
        log("[DRY-RUN] Backup saltato")
    
    print()
    
    # Connessione
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    
    try:
        # Leggi mappatura
        leggi_mappatura(conn)
        print()
        
        # Prima aggiorna le FK (prima di ricreare utenti)
        migra_tutte_fk(conn, dry_run)
        print()
        
        # Poi ricrea tabella utenti
        migra_utenti(conn, dry_run)
        print()
        
        # Verifica
        if not dry_run:
            verifica_finale(conn)
        
    except Exception as e:
        log(f"ERRORE: {e}", 'ERROR')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()
    
    print()
    print("=" * 55)
    if dry_run:
        print("  DRY-RUN COMPLETATO")
    else:
        print("  MIGRAZIONE COMPLETATA!")
        print("  Riavvia il server: ./scripts/avvia_server.sh")
    print("=" * 55)

if __name__ == '__main__':
    main()
