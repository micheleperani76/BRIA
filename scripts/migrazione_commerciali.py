#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE SISTEMA COMMERCIALI
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-21
# Descrizione: Migra il database per il nuovo sistema commerciali basato su ID
#
# OPERAZIONI:
# 1. Backup database
# 2. Aggiunge colonna commerciale_id a veicoli
# 3. Aggiunge colonna commerciale_id a clienti
# 4. Ricrea tabella storico_assegnazioni con nuova struttura
# 5. Aggiunge permesso clienti_assegnabili al catalogo
# 6. Assegna permesso ai commerciali esistenti
# 7. Migra dati da stringhe a ID
#
# USO:
#   python3 migrazione_commerciali.py --dry-run    # Solo verifica
#   python3 migrazione_commerciali.py              # Esegue migrazione
# ==============================================================================

import sys
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# Path base (cerca di determinarlo automaticamente)
SCRIPT_DIR = Path(__file__).parent.absolute()

# Se eseguito da scripts/, risali di un livello
if SCRIPT_DIR.name == 'scripts':
    BASE_DIR = SCRIPT_DIR.parent
else:
    BASE_DIR = SCRIPT_DIR

DB_FILE = BASE_DIR / 'db' / 'gestionale.db'
BACKUP_DIR = BASE_DIR / 'db'
LOG_DIR = BASE_DIR / 'logs'

# Mappatura commerciali: STRINGA -> ID utente
# Basata sulla verifica del 2025-01-21
MAPPING_COMMERCIALI = {
    'PELUCCHI': 4,  # c.pelucchi
    'PERANI': 3,    # m.perani
    'ZUBANI': 5,    # f.zubani
}

# ID commerciali che devono ricevere il permesso clienti_assegnabili
# (tutti i commerciali attivi)
COMMERCIALI_IDS = [2, 3, 4, 5, 7]  # p.ciotti, m.perani, c.pelucchi, f.zubani, prova


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def log(msg, level='INFO'):
    """Stampa messaggio con timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")


def backup_database():
    """Crea backup del database."""
    if not DB_FILE.exists():
        log(f"Database non trovato: {DB_FILE}", 'ERROR')
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = BACKUP_DIR / f"gestionale_backup_pre_commerciali_{timestamp}.db"
    
    shutil.copy(str(DB_FILE), str(backup_file))
    log(f"Backup creato: {backup_file}")
    
    return backup_file


def get_connection():
    """Apre connessione al database."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def colonna_esiste(conn, tabella, colonna):
    """Verifica se una colonna esiste in una tabella."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabella})")
    colonne = [row['name'] for row in cursor.fetchall()]
    return colonna in colonne


def permesso_esiste(conn, codice):
    """Verifica se un permesso esiste nel catalogo."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM permessi_catalogo WHERE codice = ?", (codice,))
    return cursor.fetchone() is not None


# ==============================================================================
# STEP 1: AGGIUNTA COLONNE
# ==============================================================================

def step1_aggiungi_colonne(conn, dry_run=False):
    """Aggiunge colonna commerciale_id a veicoli e clienti."""
    log("STEP 1: Aggiunta colonne commerciale_id")
    
    cursor = conn.cursor()
    modifiche = 0
    
    # Veicoli
    if colonna_esiste(conn, 'veicoli', 'commerciale_id'):
        log("  - veicoli.commerciale_id: gia' presente")
    else:
        log("  - veicoli.commerciale_id: da aggiungere")
        if not dry_run:
            cursor.execute("ALTER TABLE veicoli ADD COLUMN commerciale_id INTEGER")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_veicoli_commerciale_id ON veicoli(commerciale_id)")
            log("  - veicoli.commerciale_id: AGGIUNTA")
        modifiche += 1
    
    # Clienti
    if colonna_esiste(conn, 'clienti', 'commerciale_id'):
        log("  - clienti.commerciale_id: gia' presente")
    else:
        log("  - clienti.commerciale_id: da aggiungere")
        if not dry_run:
            cursor.execute("ALTER TABLE clienti ADD COLUMN commerciale_id INTEGER")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clienti_commerciale_id ON clienti(commerciale_id)")
            log("  - clienti.commerciale_id: AGGIUNTA")
        modifiche += 1
    
    if not dry_run:
        conn.commit()
    
    return modifiche


# ==============================================================================
# STEP 2: RICREAZIONE STORICO_ASSEGNAZIONI
# ==============================================================================

def step2_aggiorna_storico_assegnazioni(conn, dry_run=False):
    """Aggiorna struttura tabella storico_assegnazioni."""
    log("STEP 2: Aggiornamento tabella storico_assegnazioni")
    
    cursor = conn.cursor()
    
    # Verifica struttura attuale
    cursor.execute("PRAGMA table_info(storico_assegnazioni)")
    colonne_attuali = {row['name'] for row in cursor.fetchall()}
    
    colonne_nuove = {'commerciale_precedente_id', 'commerciale_nuovo_id', 'tipo'}
    mancanti = colonne_nuove - colonne_attuali
    
    if not mancanti:
        log("  - Struttura gia' aggiornata")
        return 0
    
    log(f"  - Colonne mancanti: {mancanti}")
    
    if dry_run:
        log("  - [DRY-RUN] Avrebbe ricreato la tabella")
        return 1
    
    # Salva dati esistenti
    cursor.execute("SELECT * FROM storico_assegnazioni")
    dati_esistenti = [dict(row) for row in cursor.fetchall()]
    log(f"  - Salvati {len(dati_esistenti)} record esistenti")
    
    # Rinomina tabella vecchia
    cursor.execute("ALTER TABLE storico_assegnazioni RENAME TO storico_assegnazioni_old")
    
    # Crea nuova tabella
    cursor.execute('''
        CREATE TABLE storico_assegnazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Identificativo cliente
            cliente_piva TEXT,
            cliente_nome TEXT,
            
            -- Commerciali (per ID)
            commerciale_precedente_id INTEGER,
            commerciale_nuovo_id INTEGER,
            
            -- Chi ha fatto l'operazione
            operatore_id INTEGER NOT NULL DEFAULT 0,
            
            -- Quando
            data_ora TEXT NOT NULL,
            
            -- Note opzionali
            note TEXT,
            
            -- Tipo operazione
            tipo TEXT DEFAULT 'manuale'
        )
    ''')
    
    # Indici
    cursor.execute("CREATE INDEX idx_storico_cliente_piva ON storico_assegnazioni(cliente_piva)")
    cursor.execute("CREATE INDEX idx_storico_data ON storico_assegnazioni(data_ora)")
    cursor.execute("CREATE INDEX idx_storico_nuovo ON storico_assegnazioni(commerciale_nuovo_id)")
    
    # Migra dati esistenti (se compatibili)
    for record in dati_esistenti:
        # Cerca di mappare i nomi commerciali vecchi a ID
        prec_id = None
        nuovo_id = None
        
        if record.get('commerciale_precedente'):
            prec_str = record['commerciale_precedente'].upper().strip()
            prec_id = MAPPING_COMMERCIALI.get(prec_str)
        
        if record.get('commerciale_nuovo'):
            nuovo_str = record['commerciale_nuovo'].upper().strip()
            nuovo_id = MAPPING_COMMERCIALI.get(nuovo_str)
        
        cursor.execute('''
            INSERT INTO storico_assegnazioni 
            (cliente_piva, cliente_nome, commerciale_precedente_id, commerciale_nuovo_id,
             operatore_id, data_ora, note, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.get('cliente_piva'),
            record.get('cliente_nome'),
            prec_id,
            nuovo_id,
            record.get('utente_id', 0),
            record.get('data_ora'),
            record.get('note'),
            'legacy'  # Marca come record legacy
        ))
    
    # Rimuovi tabella vecchia
    cursor.execute("DROP TABLE storico_assegnazioni_old")
    
    conn.commit()
    log(f"  - Tabella ricreata e migrati {len(dati_esistenti)} record")
    
    return 1


# ==============================================================================
# STEP 3: AGGIUNTA PERMESSO
# ==============================================================================

def step3_aggiungi_permesso(conn, dry_run=False):
    """Aggiunge permesso clienti_assegnabili al catalogo."""
    log("STEP 3: Aggiunta permesso clienti_assegnabili")
    
    cursor = conn.cursor()
    
    if permesso_esiste(conn, 'clienti_assegnabili'):
        log("  - Permesso gia' presente nel catalogo")
        return 0
    
    log("  - Permesso da aggiungere")
    
    if not dry_run:
        cursor.execute('''
            INSERT INTO permessi_catalogo (codice, descrizione, categoria, ordine)
            VALUES ('clienti_assegnabili', 'Puo'' ricevere clienti in gestione', 'clienti', 45)
        ''')
        conn.commit()
        log("  - Permesso AGGIUNTO")
    
    return 1


# ==============================================================================
# STEP 4: ASSEGNAZIONE PERMESSO AI COMMERCIALI
# ==============================================================================

def step4_assegna_permesso_commerciali(conn, dry_run=False):
    """Assegna permesso clienti_assegnabili ai commerciali esistenti."""
    log("STEP 4: Assegnazione permesso ai commerciali")
    
    cursor = conn.cursor()
    
    # Trova ID del permesso
    cursor.execute("SELECT id FROM permessi_catalogo WHERE codice = 'clienti_assegnabili'")
    row = cursor.fetchone()
    
    if not row:
        log("  - ERRORE: Permesso non trovato nel catalogo!", 'ERROR')
        return 0
    
    permesso_id = row['id']
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    assegnati = 0
    
    for utente_id in COMMERCIALI_IDS:
        # Verifica se utente esiste
        cursor.execute("SELECT username FROM utenti WHERE id = ?", (utente_id,))
        utente = cursor.fetchone()
        
        if not utente:
            log(f"  - Utente ID {utente_id}: non trovato, saltato")
            continue
        
        # Verifica se ha gia' il permesso
        cursor.execute('''
            SELECT abilitato FROM utenti_permessi
            WHERE utente_id = ? AND permesso_id = ?
        ''', (utente_id, permesso_id))
        
        esistente = cursor.fetchone()
        
        if esistente:
            if esistente['abilitato']:
                log(f"  - {utente['username']}: gia' abilitato")
            else:
                log(f"  - {utente['username']}: da riabilitare")
                if not dry_run:
                    cursor.execute('''
                        UPDATE utenti_permessi SET abilitato = 1, data_assegnazione = ?
                        WHERE utente_id = ? AND permesso_id = ?
                    ''', (now, utente_id, permesso_id))
                assegnati += 1
        else:
            log(f"  - {utente['username']}: da assegnare")
            if not dry_run:
                cursor.execute('''
                    INSERT INTO utenti_permessi (utente_id, permesso_id, abilitato, data_assegnazione)
                    VALUES (?, ?, 1, ?)
                ''', (utente_id, permesso_id, now))
            assegnati += 1
    
    if not dry_run:
        conn.commit()
    
    log(f"  - Totale assegnazioni: {assegnati}")
    return assegnati


# ==============================================================================
# STEP 5: MIGRAZIONE DATI
# ==============================================================================

def step5_migra_dati(conn, dry_run=False):
    """Migra dati commerciale da stringa a ID."""
    log("STEP 5: Migrazione dati commerciale (stringa -> ID)")
    
    cursor = conn.cursor()
    
    # Conta veicoli da migrare
    cursor.execute('''
        SELECT COUNT(DISTINCT p_iva) as num FROM veicoli
        WHERE commerciale IS NOT NULL 
          AND commerciale != ''
          AND (commerciale_id IS NULL OR commerciale_id = 0)
    ''')
    da_migrare = cursor.fetchone()['num']
    
    log(f"  - Clienti da migrare: {da_migrare}")
    
    if da_migrare == 0:
        log("  - Nessuna migrazione necessaria")
        return 0
    
    # Elenca valori distinti
    cursor.execute('''
        SELECT DISTINCT commerciale FROM veicoli
        WHERE commerciale IS NOT NULL 
          AND commerciale != ''
          AND (commerciale_id IS NULL OR commerciale_id = 0)
    ''')
    valori = [row['commerciale'] for row in cursor.fetchall()]
    log(f"  - Valori trovati: {valori}")
    
    migrati = 0
    errori = 0
    
    for comm_str in valori:
        comm_upper = comm_str.upper().strip()
        comm_id = MAPPING_COMMERCIALI.get(comm_upper)
        
        if comm_id is None:
            log(f"  - ATTENZIONE: '{comm_str}' non mappato!", 'WARN')
            errori += 1
            continue
        
        # Conta veicoli con questo commerciale
        cursor.execute('''
            SELECT COUNT(*) as num FROM veicoli
            WHERE UPPER(commerciale) = ?
              AND (commerciale_id IS NULL OR commerciale_id = 0)
        ''', (comm_upper,))
        num_veicoli = cursor.fetchone()['num']
        
        log(f"  - {comm_str} -> ID {comm_id}: {num_veicoli} veicoli")
        
        if not dry_run:
            # Aggiorna veicoli
            cursor.execute('''
                UPDATE veicoli SET commerciale_id = ?
                WHERE UPPER(commerciale) = ?
                  AND (commerciale_id IS NULL OR commerciale_id = 0)
            ''', (comm_id, comm_upper))
            
            # Aggiorna anche clienti
            cursor.execute('''
                UPDATE clienti SET commerciale_id = ?
                WHERE p_iva IN (
                    SELECT DISTINCT p_iva FROM veicoli WHERE UPPER(commerciale) = ?
                )
                AND (commerciale_id IS NULL OR commerciale_id = 0)
            ''', (comm_id, comm_upper))
        
        migrati += num_veicoli
    
    if not dry_run:
        conn.commit()
    
    log(f"  - Migrati: {migrati} veicoli")
    if errori:
        log(f"  - Errori: {errori}", 'WARN')
    
    return migrati


# ==============================================================================
# STEP 6: VERIFICA FINALE
# ==============================================================================

def step6_verifica(conn):
    """Verifica finale della migrazione."""
    log("STEP 6: Verifica finale")
    
    cursor = conn.cursor()
    
    # Conta veicoli per commerciale_id
    cursor.execute('''
        SELECT 
            commerciale_id,
            COUNT(*) as num_veicoli,
            COUNT(DISTINCT p_iva) as num_clienti
        FROM veicoli
        WHERE commerciale_id IS NOT NULL
        GROUP BY commerciale_id
    ''')
    
    log("  - Distribuzione per commerciale_id:")
    for row in cursor.fetchall():
        cursor.execute("SELECT nome, cognome FROM utenti WHERE id = ?", (row['commerciale_id'],))
        utente = cursor.fetchone()
        nome = f"{utente['nome']} {utente['cognome']}" if utente else f"ID {row['commerciale_id']}"
        log(f"    * {nome}: {row['num_clienti']} clienti, {row['num_veicoli']} veicoli")
    
    # Conta veicoli senza commerciale_id
    cursor.execute('''
        SELECT COUNT(*) as num FROM veicoli
        WHERE commerciale IS NOT NULL 
          AND commerciale != ''
          AND (commerciale_id IS NULL OR commerciale_id = 0)
    ''')
    non_migrati = cursor.fetchone()['num']
    
    if non_migrati > 0:
        log(f"  - ATTENZIONE: {non_migrati} veicoli non migrati!", 'WARN')
    else:
        log("  - Tutti i veicoli sono stati migrati correttamente")
    
    # Verifica permessi
    cursor.execute('''
        SELECT COUNT(*) as num FROM utenti_permessi up
        JOIN permessi_catalogo pc ON up.permesso_id = pc.id
        WHERE pc.codice = 'clienti_assegnabili' AND up.abilitato = 1
    ''')
    num_assegnabili = cursor.fetchone()['num']
    log(f"  - Commerciali con permesso assegnabile: {num_assegnabili}")
    
    return non_migrati == 0


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Funzione principale."""
    
    # Parse argomenti
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    print("")
    print("=" * 70)
    print("  MIGRAZIONE SISTEMA COMMERCIALI")
    print("=" * 70)
    print(f"  Database: {DB_FILE}")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'ESECUZIONE REALE'}")
    print("=" * 70)
    print("")
    
    # Verifica database
    if not DB_FILE.exists():
        log(f"Database non trovato: {DB_FILE}", 'ERROR')
        sys.exit(1)
    
    # Backup (solo se non dry-run)
    if not dry_run:
        backup = backup_database()
        if not backup:
            log("Backup fallito, interruzione", 'ERROR')
            sys.exit(1)
    else:
        log("[DRY-RUN] Backup saltato")
    
    print("")
    
    # Connessione
    conn = get_connection()
    
    try:
        # Esegui step
        step1_aggiungi_colonne(conn, dry_run)
        print("")
        
        step2_aggiorna_storico_assegnazioni(conn, dry_run)
        print("")
        
        step3_aggiungi_permesso(conn, dry_run)
        print("")
        
        step4_assegna_permesso_commerciali(conn, dry_run)
        print("")
        
        step5_migra_dati(conn, dry_run)
        print("")
        
        step6_verifica(conn)
        
    except Exception as e:
        log(f"ERRORE: {e}", 'ERROR')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()
    
    print("")
    print("=" * 70)
    if dry_run:
        print("  DRY-RUN COMPLETATO")
        print("  Esegui senza --dry-run per applicare le modifiche")
    else:
        print("  MIGRAZIONE COMPLETATA CON SUCCESSO")
    print("=" * 70)
    print("")


if __name__ == '__main__':
    main()
