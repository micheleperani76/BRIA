#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DATABASE - Import CRM Zoho
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-09
# Descrizione: Prepara il database per l'import dei dati CRM Zoho
#
# OPERAZIONI:
# 1. Backup database
# 2. ALTER TABLE clienti (13 nuovi campi)
# 3. ALTER TABLE veicoli (4 nuovi campi)
# 4. CREATE TABLE clienti_consensi
# 5. CREATE TABLE clienti_dati_finanziari
# 6. CREATE TABLE clienti_creditsafe_alert
# 7. CREATE TABLE clienti_crm_metadata
# 8. CREATE TABLE storico_installato
# 9. Creazione indici
# 10. Verifica finale
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/migrazione_crm_zoho.py --dry-run    # Solo verifica
#   python3 scripts/migrazione_crm_zoho.py               # Esegue migrazione
#
# ==============================================================================

import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()

# Se eseguito da scripts/, risali di un livello
if SCRIPT_DIR.name == 'scripts':
    BASE_DIR = SCRIPT_DIR.parent
else:
    BASE_DIR = SCRIPT_DIR

DB_FILE = BASE_DIR / 'db' / 'gestionale.db'

# ==============================================================================
# DEFINIZIONI MIGRAZIONE
# ==============================================================================

# Nuovi campi tabella clienti (13 campi)
CAMPI_CLIENTI = [
    ('crm_id',                    'TEXT'),
    ('stato_crm',                 'TEXT'),
    ('origine_contatto',          'TEXT'),
    ('azienda_tipo_crm',          'TEXT'),
    ('profilazione_flotta',       'TEXT'),
    ('commerciale_consecution',   'TEXT'),
    ('pec',                       'TEXT'),
    ('telefono',                  'TEXT'),
    ('totale_flotta_crm',         'INTEGER'),
    ('flotta_cns_crm',            'INTEGER'),
    ('noleggiatore_principale_1', 'TEXT'),
    ('noleggiatore_principale_2', 'TEXT'),
    ('note_concorrenza',          'TEXT'),
]

# Nuovi campi tabella veicoli (4 campi)
CAMPI_VEICOLI = [
    ('co2',              'REAL'),
    ('stato_targa',      'TEXT'),
    ('crm_id',           'TEXT'),
    ('crm_azienda_id',   'TEXT'),
]

# Indici da creare
INDICI = [
    ('idx_clienti_crm_id',         'clienti',             'crm_id'),
    ('idx_clienti_stato_crm',      'clienti',             'stato_crm'),
    ('idx_veicoli_crm_id',         'veicoli',             'crm_id'),
    ('idx_veicoli_stato_targa',    'veicoli',             'stato_targa'),
    ('idx_consensi_cliente',       'clienti_consensi',    'cliente_id'),
    ('idx_finanziari_cliente',     'clienti_dati_finanziari', 'cliente_id'),
    ('idx_alert_cliente',          'clienti_creditsafe_alert', 'cliente_id'),
    ('idx_metadata_cliente',       'clienti_crm_metadata', 'cliente_id'),
    ('idx_storico_inst_cliente',   'storico_installato',  'cliente_id'),
    ('idx_storico_inst_targa',     'storico_installato',  'targa'),
    ('idx_storico_inst_retention', 'storico_installato',  'data_scadenza_retention'),
]

# DDL tabelle satellite
TABELLE_SATELLITE = {
    'clienti_consensi': '''
        CREATE TABLE clienti_consensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            tipo_consenso TEXT NOT NULL,
            valore TEXT NOT NULL,
            data_consenso TEXT,
            data_revoca TEXT,
            origine TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clienti(id)
        )
    ''',
    'clienti_dati_finanziari': '''
        CREATE TABLE clienti_dati_finanziari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            anno_riferimento INTEGER NOT NULL,
            fatturato REAL,
            iban TEXT,
            ebitda REAL,
            ricavi REAL,
            utile_perdita REAL,
            patrimonio_netto REAL,
            fonte TEXT,
            data_import TEXT,
            UNIQUE(cliente_id, anno_riferimento),
            FOREIGN KEY (cliente_id) REFERENCES clienti(id)
        )
    ''',
    'clienti_creditsafe_alert': '''
        CREATE TABLE clienti_creditsafe_alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            tipo_alert TEXT NOT NULL,
            valore TEXT NOT NULL,
            data_rilevazione TEXT,
            fonte TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clienti(id)
        )
    ''',
    'clienti_crm_metadata': '''
        CREATE TABLE clienti_crm_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL UNIQUE,
            crm_record_id TEXT,
            crm_creato_da TEXT,
            crm_ora_creazione TEXT,
            crm_struttura TEXT,
            crm_locked TEXT,
            crm_old_owner TEXT,
            data_ultimo_sync TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clienti(id)
        )
    ''',
}

TABELLA_STORICO = '''
    CREATE TABLE storico_installato (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Dati veicolo (copia da veicoli al momento della dismissione)
        cliente_id INTEGER,
        p_iva TEXT,
        targa TEXT,
        marca TEXT,
        modello TEXT,
        alimentazione TEXT,
        co2 REAL,
        noleggiatore TEXT,
        canone REAL,
        durata INTEGER,
        km INTEGER,
        inizio TEXT,
        scadenza TEXT,
        data_immatricolazione TEXT,
        driver TEXT,
        driver_telefono TEXT,
        driver_email TEXT,
        
        -- Dati CRM
        crm_id TEXT,
        crm_azienda_id TEXT,
        stato_targa TEXT,
        
        -- Motivo dismissione (da CRM se disponibile)
        motivo_dismissione TEXT,
        fase_affare TEXT,
        motivazione_chiuso_perso TEXT,
        soluzione_alternativa TEXT,
        
        -- Gestione storico
        data_dismissione TEXT NOT NULL,
        data_scadenza_retention TEXT NOT NULL,
        note TEXT,
        
        FOREIGN KEY (cliente_id) REFERENCES clienti(id)
    )
'''


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def log(msg, level='INFO'):
    """Stampa messaggio con timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    simbolo = {'INFO': ' ', 'OK': '+', 'SKIP': '-', 'WARN': '!', 'ERROR': 'X'}
    s = simbolo.get(level, ' ')
    print(f"  [{s}] {msg}")


def backup_database():
    """Crea backup del database prima della migrazione."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_FILE.parent / f"gestionale_backup_pre_crm_{timestamp}.db"
    shutil.copy2(DB_FILE, backup_path)
    print(f"\n  Backup creato: {backup_path.name}")
    print(f"  Dimensione: {backup_path.stat().st_size / 1024 / 1024:.1f} MB")
    return backup_path


def colonna_esiste(cursor, tabella, colonna):
    """Verifica se una colonna esiste in una tabella."""
    cursor.execute(f"PRAGMA table_info({tabella})")
    colonne = [col[1] for col in cursor.fetchall()]
    return colonna in colonne


def tabella_esiste(cursor, tabella):
    """Verifica se una tabella esiste."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (tabella,))
    return cursor.fetchone() is not None


def indice_esiste(cursor, nome_indice):
    """Verifica se un indice esiste."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name=?
    """, (nome_indice,))
    return cursor.fetchone() is not None


# ==============================================================================
# STEP DI MIGRAZIONE
# ==============================================================================

def step1_alter_clienti(cursor, dry_run=False):
    """Aggiunge 13 nuovi campi alla tabella clienti."""
    print("\n" + "="*60)
    print("[STEP 1] ALTER TABLE clienti - 13 nuovi campi CRM")
    print("="*60)
    
    aggiunti = 0
    skippati = 0
    
    for campo, tipo in CAMPI_CLIENTI:
        if colonna_esiste(cursor, 'clienti', campo):
            log(f"{campo} ({tipo}) - gia' presente", 'SKIP')
            skippati += 1
        else:
            if dry_run:
                log(f"{campo} ({tipo}) - DA AGGIUNGERE", 'INFO')
            else:
                cursor.execute(f"ALTER TABLE clienti ADD COLUMN {campo} {tipo}")
                log(f"{campo} ({tipo}) - aggiunto", 'OK')
            aggiunti += 1
    
    print(f"\n  Risultato: {aggiunti} da aggiungere, {skippati} gia' presenti")
    return aggiunti


def step2_alter_veicoli(cursor, dry_run=False):
    """Aggiunge 4 nuovi campi alla tabella veicoli."""
    print("\n" + "="*60)
    print("[STEP 2] ALTER TABLE veicoli - 4 nuovi campi CRM")
    print("="*60)
    
    aggiunti = 0
    skippati = 0
    
    for campo, tipo in CAMPI_VEICOLI:
        if colonna_esiste(cursor, 'veicoli', campo):
            log(f"{campo} ({tipo}) - gia' presente", 'SKIP')
            skippati += 1
        else:
            if dry_run:
                log(f"{campo} ({tipo}) - DA AGGIUNGERE", 'INFO')
            else:
                cursor.execute(f"ALTER TABLE veicoli ADD COLUMN {campo} {tipo}")
                log(f"{campo} ({tipo}) - aggiunto", 'OK')
            aggiunti += 1
    
    print(f"\n  Risultato: {aggiunti} da aggiungere, {skippati} gia' presenti")
    return aggiunti


def step3_tabelle_satellite(cursor, dry_run=False):
    """Crea 4 tabelle satellite per dati CRM."""
    print("\n" + "="*60)
    print("[STEP 3] CREATE TABLE - 4 tabelle satellite CRM")
    print("="*60)
    
    create = 0
    skippate = 0
    
    for nome, ddl in TABELLE_SATELLITE.items():
        if tabella_esiste(cursor, nome):
            log(f"{nome} - gia' presente", 'SKIP')
            skippate += 1
        else:
            if dry_run:
                log(f"{nome} - DA CREARE", 'INFO')
            else:
                cursor.execute(ddl)
                log(f"{nome} - creata", 'OK')
            create += 1
    
    print(f"\n  Risultato: {create} da creare, {skippate} gia' presenti")
    return create


def step4_tabella_storico(cursor, dry_run=False):
    """Crea tabella storico_installato per veicoli dismessi."""
    print("\n" + "="*60)
    print("[STEP 4] CREATE TABLE storico_installato")
    print("="*60)
    
    if tabella_esiste(cursor, 'storico_installato'):
        log("storico_installato - gia' presente", 'SKIP')
        return 0
    
    if dry_run:
        log("storico_installato - DA CREARE", 'INFO')
    else:
        cursor.execute(TABELLA_STORICO)
        log("storico_installato - creata", 'OK')
    
    return 1


def step5_indici(cursor, dry_run=False):
    """Crea indici per performance."""
    print("\n" + "="*60)
    print("[STEP 5] CREATE INDEX - Indici di performance")
    print("="*60)
    
    creati = 0
    skippati = 0
    
    for nome, tabella, colonna in INDICI:
        if indice_esiste(cursor, nome):
            log(f"{nome} su {tabella}({colonna}) - gia' presente", 'SKIP')
            skippati += 1
        else:
            if dry_run:
                log(f"{nome} su {tabella}({colonna}) - DA CREARE", 'INFO')
            else:
                cursor.execute(f"CREATE INDEX {nome} ON {tabella}({colonna})")
                log(f"{nome} su {tabella}({colonna}) - creato", 'OK')
            creati += 1
    
    print(f"\n  Risultato: {creati} da creare, {skippati} gia' presenti")
    return creati


# ==============================================================================
# VERIFICA FINALE
# ==============================================================================

def verifica_finale(cursor):
    """Verifica che tutte le migrazioni siano andate a buon fine."""
    print("\n" + "="*60)
    print("VERIFICA FINALE")
    print("="*60)
    
    errori = []
    ok = 0
    
    # 1. Verifica campi clienti
    for campo, _ in CAMPI_CLIENTI:
        if colonna_esiste(cursor, 'clienti', campo):
            ok += 1
        else:
            errori.append(f"Campo clienti.{campo} mancante")
    
    # 2. Verifica campi veicoli
    for campo, _ in CAMPI_VEICOLI:
        if colonna_esiste(cursor, 'veicoli', campo):
            ok += 1
        else:
            errori.append(f"Campo veicoli.{campo} mancante")
    
    # 3. Verifica tabelle satellite
    for nome in TABELLE_SATELLITE:
        if tabella_esiste(cursor, nome):
            ok += 1
        else:
            errori.append(f"Tabella {nome} mancante")
    
    # 4. Verifica storico_installato
    if tabella_esiste(cursor, 'storico_installato'):
        ok += 1
    else:
        errori.append("Tabella storico_installato mancante")
    
    # 5. Verifica indici
    for nome, _, _ in INDICI:
        if indice_esiste(cursor, nome):
            ok += 1
        else:
            errori.append(f"Indice {nome} mancante")
    
    # Riepilogo
    print(f"\n  Verifiche OK: {ok}")
    
    if errori:
        print(f"  ERRORI: {len(errori)}")
        for e in errori:
            log(e, 'ERROR')
        return False
    
    print("\n  MIGRAZIONE COMPLETATA CON SUCCESSO!")
    return True


# ==============================================================================
# RIEPILOGO DB
# ==============================================================================

def mostra_riepilogo(cursor):
    """Mostra riepilogo stato database dopo migrazione."""
    print("\n" + "="*60)
    print("RIEPILOGO DATABASE")
    print("="*60)
    
    # Conta colonne clienti
    cursor.execute("PRAGMA table_info(clienti)")
    n_col_clienti = len(cursor.fetchall())
    
    # Conta colonne veicoli
    cursor.execute("PRAGMA table_info(veicoli)")
    n_col_veicoli = len(cursor.fetchall())
    
    # Conta record
    cursor.execute("SELECT COUNT(*) FROM clienti")
    n_clienti = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM veicoli")
    n_veicoli = cursor.fetchone()[0]
    
    # Conta tabelle
    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    n_tabelle = cursor.fetchone()[0]
    
    print(f"  Tabelle totali:     {n_tabelle}")
    print(f"  Colonne clienti:    {n_col_clienti}")
    print(f"  Colonne veicoli:    {n_col_veicoli}")
    print(f"  Record clienti:     {n_clienti}")
    print(f"  Record veicoli:     {n_veicoli}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    # Determina modalita'
    dry_run = '--dry-run' in sys.argv
    
    print("="*60)
    print("MIGRAZIONE DATABASE - Import CRM Zoho")
    print("="*60)
    print(f"  Database:  {DB_FILE}")
    print(f"  Data:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'ESECUZIONE REALE'}")
    
    # Verifica esistenza database
    if not DB_FILE.exists():
        print(f"\n  ERRORE: Database non trovato: {DB_FILE}")
        sys.exit(1)
    
    # Backup (solo in modalita' reale)
    if not dry_run:
        print("\n" + "-"*60)
        print("BACKUP DATABASE")
        print("-"*60)
        backup_database()
    else:
        print("\n  [DRY-RUN] Backup saltato")
    
    # Connessione
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Esegui step
        tot_modifiche = 0
        tot_modifiche += step1_alter_clienti(cursor, dry_run)
        tot_modifiche += step2_alter_veicoli(cursor, dry_run)
        tot_modifiche += step3_tabelle_satellite(cursor, dry_run)
        tot_modifiche += step4_tabella_storico(cursor, dry_run)
        tot_modifiche += step5_indici(cursor, dry_run)
        
        if dry_run:
            print("\n" + "="*60)
            print(f"DRY-RUN COMPLETATO - {tot_modifiche} modifiche da applicare")
            print("="*60)
            print("\n  Per eseguire la migrazione reale:")
            print("  python3 scripts/migrazione_crm_zoho.py")
        else:
            # Commit
            conn.commit()
            
            # Verifica
            if verifica_finale(cursor):
                mostra_riepilogo(cursor)
            else:
                print("\n  ATTENZIONE: Verifica finale con errori!")
                print("  Controllare manualmente lo stato del DB")
        
    except Exception as e:
        conn.rollback()
        print(f"\n  ERRORE durante la migrazione: {e}")
        print("  Database ripristinato (rollback)")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
