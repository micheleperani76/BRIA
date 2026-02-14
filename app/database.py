#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Modulo Database
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-12
# Descrizione: Gestione database SQLite unificato (clienti + veicoli + creditsafe)
# ==============================================================================

import sqlite3
from datetime import datetime
from pathlib import Path
from .config import DB_FILE, DB_DIR

# ==============================================================================
# INIZIALIZZAZIONE DATABASE
# ==============================================================================

def init_database():
    """
    Crea il database e le tabelle se non esistono.
    Ritorna la connessione al database.
    """
    # Assicura che la cartella esista
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # =========================================================================
    # TABELLA CLIENTI (dati unificati flotta + creditsafe)
    # =========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Identificativi (chiave di match)
            nome_cliente TEXT NOT NULL,
            p_iva TEXT,
            cod_fiscale TEXT,
            numero_registrazione TEXT UNIQUE,
            
            -- Dati operativi flotta (NON sovrascritti da Creditsafe)
            commerciale TEXT,
            
            -- Dati Creditsafe (sovrascritti ad ogni import)
            ragione_sociale TEXT,
            indirizzo TEXT,
            via TEXT,
            civico TEXT,
            cap TEXT,
            citta TEXT,
            provincia TEXT,
            indirizzo_protetto INTEGER DEFAULT 0,
            telefono TEXT,
            pec TEXT,
            forma_giuridica TEXT,
            data_costituzione TEXT,
            desc_attivita TEXT,
            codice_ateco TEXT,
            desc_ateco TEXT,
            capogruppo_nome TEXT,
            capogruppo_cf TEXT,
            legale_rappresentante TEXT,
            capitale_sociale REAL,
            dipendenti INTEGER,
            
            -- Rating e Rischio
            score TEXT,
            punteggio_rischio INTEGER,
            credito REAL,
            stato TEXT,
            protesti TEXT,
            importo_protesti REAL,
            
            -- Bilancio anno corrente
            anno_bilancio INTEGER,
            valore_produzione REAL,
            patrimonio_netto REAL,
            utile REAL,
            debiti REAL,
            
            -- Bilancio anno precedente
            anno_bilancio_prec INTEGER,
            valore_produzione_prec REAL,
            patrimonio_netto_prec REAL,
            utile_prec REAL,
            debiti_prec REAL,
            
            -- Metadati
            file_pdf TEXT,
            data_report_creditsafe TEXT,
            data_import_flotta TEXT,
            data_import_creditsafe TEXT,
            data_ultimo_aggiornamento TEXT
        )
    ''')
    
    # =========================================================================
    # TABELLA VEICOLI (dati flotta)
    # =========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veicoli (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            p_iva TEXT,
            
            -- Dati veicolo
            noleggiatore TEXT,
            targa TEXT,
            marca TEXT,
            modello TEXT,
            tipo TEXT,
            alimentazione TEXT,
            
            -- Contratto
            durata INTEGER,
            inizio TEXT,
            scadenza TEXT,
            data_fine_aggiornata TEXT,
            km INTEGER,
            franchigia REAL,
            canone REAL,
            
            -- Assegnazione
            driver TEXT,
            contratto TEXT,
            commerciale TEXT,
            
            FOREIGN KEY (cliente_id) REFERENCES clienti(id)
        )
    ''')
    
    # =========================================================================
    # TABELLA STORICO MODIFICHE
    # =========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS storico_modifiche (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tabella TEXT,
            record_id INTEGER,
            campo_modificato TEXT,
            valore_precedente TEXT,
            valore_nuovo TEXT,
            data_modifica TEXT,
            origine TEXT
        )
    ''')
    
    # =========================================================================
    # TABELLA NOLEGGIATORI (anagrafica unica)
    # =========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS noleggiatori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codice TEXT NOT NULL UNIQUE,
            nome_display TEXT NOT NULL,
            colore TEXT DEFAULT '#6c757d',
            link_assistenza TEXT,
            ordine INTEGER DEFAULT 0,
            note TEXT,
            attivo INTEGER DEFAULT 1,
            origine TEXT DEFAULT 'PREDEFINITO',
            data_inserimento TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    
    # =========================================================================
    # INDICI
    # =========================================================================
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clienti_piva ON clienti(p_iva)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clienti_cf ON clienti(cod_fiscale)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clienti_nome ON clienti(nome_cliente)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clienti_nreg ON clienti(numero_registrazione)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_veicoli_piva ON veicoli(p_iva)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_veicoli_cliente ON veicoli(cliente_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_veicoli_targa ON veicoli(targa)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_storico_data ON storico_modifiche(data_modifica)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_noleggiatori_codice ON noleggiatori(codice)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_veicoli_noleggiatore_id ON veicoli(noleggiatore_id)')
    
    conn.commit()
    return conn


def get_connection():
    """Ottiene una connessione al database."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


# ==============================================================================
# FUNZIONI CLIENTI
# ==============================================================================

def normalizza_piva(piva):
    """Normalizza una P.IVA rimuovendo prefissi e zeri iniziali."""
    if not piva:
        return None
    # Rimuove prefisso IT e spazi
    piva = str(piva).upper().replace('IT', '').replace(' ', '').strip()
    # Rimuove zeri iniziali se troppo lunga
    if len(piva) > 11:
        piva = piva.lstrip('0')
    return piva if piva else None


def cerca_cliente_per_piva(conn, piva):
    """Cerca un cliente per P.IVA (con normalizzazione)."""
    piva_norm = normalizza_piva(piva)
    if not piva_norm:
        return None
    
    cursor = conn.cursor()
    
    # Cerca con P.IVA normalizzata
    cursor.execute('''
        SELECT * FROM clienti 
        WHERE REPLACE(REPLACE(UPPER(p_iva), 'IT', ''), ' ', '') = ?
           OR REPLACE(REPLACE(UPPER(p_iva), 'IT', ''), ' ', '') LIKE ?
    ''', (piva_norm, f'%{piva_norm}%'))
    
    return cursor.fetchone()


def cerca_cliente_per_nome(conn, nome):
    """Cerca un cliente per nome (match parziale)."""
    if not nome:
        return None
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM clienti 
        WHERE nome_cliente LIKE ? OR ragione_sociale LIKE ?
        LIMIT 1
    ''', (f'%{nome}%', f'%{nome}%'))
    
    return cursor.fetchone()


def inserisci_cliente(conn, dati, origine='import'):
    """Inserisce un nuovo cliente nel database."""
    cursor = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dati['data_ultimo_aggiornamento'] = now
    
    if origine == 'flotta':
        dati['data_import_flotta'] = now
    elif origine == 'creditsafe':
        dati['data_import_creditsafe'] = now
    
    # Costruisci query dinamica
    campi = list(dati.keys())
    placeholders = ', '.join(['?' for _ in campi])
    query = f"INSERT INTO clienti ({', '.join(campi)}) VALUES ({placeholders})"
    
    cursor.execute(query, list(dati.values()))
    conn.commit()
    
    return cursor.lastrowid


def aggiorna_cliente_da_creditsafe(conn, cliente_id, dati_creditsafe, logger=None):
    """
    Aggiorna un cliente esistente con i dati Creditsafe.
    NON sovrascrive: commerciale (viene dalla flotta)
    SOVRASCRIVE: tutti i dati aziendali, rating, bilancio
    """
    cursor = conn.cursor()
    
    # Recupera dati attuali per storico
    cursor.execute('SELECT * FROM clienti WHERE id = ?', (cliente_id,))
    cliente_attuale = cursor.fetchone()
    
    if not cliente_attuale:
        return False
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Campi da aggiornare (escluso commerciale)
    campi_aggiornabili = [
        'ragione_sociale', 'indirizzo', 'via', 'civico', 'cap', 'citta', 'provincia',
        'telefono', 'pec', 'forma_giuridica',
        'data_costituzione', 'desc_attivita', 'codice_ateco', 'desc_ateco',
        'codice_sae', 'codice_rae', 'codice_ateco_2007', 'desc_ateco_2007',
        'capogruppo_nome', 'capogruppo_cf',
        'capitale_sociale', 'dipendenti', 'score', 'punteggio_rischio',
        'credito', 'stato', 'protesti', 'importo_protesti',
        'anno_bilancio', 'valore_produzione', 'patrimonio_netto', 'utile', 'debiti',
        'anno_bilancio_prec', 'valore_produzione_prec', 'patrimonio_netto_prec', 
        'utile_prec', 'debiti_prec', 'file_pdf', 'data_report_creditsafe'
    ]
    
    # Se indirizzo è protetto, escludi i campi indirizzo dall'aggiornamento
    if cliente_attuale['indirizzo_protetto']:
        campi_indirizzo = ['indirizzo', 'via', 'civico', 'cap', 'citta', 'provincia']
        campi_aggiornabili = [c for c in campi_aggiornabili if c not in campi_indirizzo]
        if logger:
            logger.info(f"  Indirizzo protetto, non sovrascritto")
    
    # Se capogruppo e protetto, escludi i campi capogruppo dall'aggiornamento
    if cliente_attuale['capogruppo_protetto']:
        campi_capogruppo = ['capogruppo_nome', 'capogruppo_cf']
        campi_aggiornabili = [c for c in campi_aggiornabili if c not in campi_capogruppo]
        if logger:
            logger.info(f"  Capogruppo protetto, non sovrascritto")
    
    # Aggiorna P.IVA e CF solo se vuoti nel record attuale
    if not cliente_attuale['p_iva'] and dati_creditsafe.get('p_iva'):
        campi_aggiornabili.append('p_iva')
    if not cliente_attuale['cod_fiscale'] and dati_creditsafe.get('cod_fiscale'):
        campi_aggiornabili.append('cod_fiscale')
    if not cliente_attuale['numero_registrazione'] and dati_creditsafe.get('numero_registrazione'):
        campi_aggiornabili.append('numero_registrazione')
    
    # Costruisci update
    set_parts = []
    values = []
    
    for campo in campi_aggiornabili:
        if campo in dati_creditsafe and dati_creditsafe[campo] is not None:
            # Registra modifica nello storico se valore cambiato
            valore_precedente = cliente_attuale[campo] if campo in cliente_attuale.keys() else None
            valore_nuovo = dati_creditsafe[campo]
            
            if str(valore_precedente) != str(valore_nuovo):
                cursor.execute('''
                    INSERT INTO storico_modifiche 
                    (tabella, record_id, campo_modificato, valore_precedente, valore_nuovo, data_modifica, origine)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('clienti', cliente_id, campo, str(valore_precedente), str(valore_nuovo), now, 'creditsafe'))
            
            set_parts.append(f"{campo} = ?")
            values.append(valore_nuovo)
    
    if set_parts:
        set_parts.append("data_import_creditsafe = ?")
        values.append(now)
        set_parts.append("data_ultimo_aggiornamento = ?")
        values.append(now)
        values.append(cliente_id)
        
        query = f"UPDATE clienti SET {', '.join(set_parts)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        
        if logger:
            logger.info(f"  Aggiornati {len(set_parts)-2} campi per cliente ID {cliente_id}")
    
    # --- SYNC CAPOGRUPPO verso tabella capogruppo_clienti ---
    cg_nome = dati_creditsafe.get('capogruppo_nome')
    cg_cf = dati_creditsafe.get('capogruppo_cf')
    if cg_nome and cg_nome.strip():
        try:
            # Cerca record esistente (match per CF se presente, altrimenti per nome)
            if cg_cf and cg_cf.strip():
                cursor.execute('''
                    SELECT id, protetto FROM capogruppo_clienti
                    WHERE cliente_id = ? AND UPPER(TRIM(codice_fiscale)) = UPPER(TRIM(?))
                ''', (cliente_id, cg_cf))
            else:
                cursor.execute('''
                    SELECT id, protetto FROM capogruppo_clienti
                    WHERE cliente_id = ? AND UPPER(TRIM(nome)) = UPPER(TRIM(?))
                ''', (cliente_id, cg_nome))
            
            esistente = cursor.fetchone()
            
            if esistente:
                if not esistente['protetto']:
                    cursor.execute('''
                        UPDATE capogruppo_clienti 
                        SET nome = ?, codice_fiscale = ?, data_modifica = ?
                        WHERE id = ?
                    ''', (cg_nome.strip(), (cg_cf or '').strip(), now, esistente['id']))
                    if logger:
                        logger.info(f"  Capogruppo aggiornato in capogruppo_clienti: {cg_nome}")
                else:
                    if logger:
                        logger.info(f"  Capogruppo protetto in capogruppo_clienti, skip")
            else:
                cursor.execute('''
                    INSERT INTO capogruppo_clienti (cliente_id, nome, codice_fiscale, protetto)
                    VALUES (?, ?, ?, 0)
                ''', (cliente_id, cg_nome.strip(), (cg_cf or '').strip()))
                if logger:
                    logger.info(f"  Capogruppo inserito in capogruppo_clienti: {cg_nome}")
            
            conn.commit()
        except Exception as e:
            if logger:
                logger.warning(f"  Errore sync capogruppo_clienti: {e}")
    
    return True


# ==============================================================================
# FUNZIONI VEICOLI
# ==============================================================================

def inserisci_veicolo(conn, dati):
    """Inserisce un nuovo veicolo nel database."""
    cursor = conn.cursor()
    
    # Cerca cliente_id se abbiamo P.IVA
    if dati.get('p_iva'):
        cliente = cerca_cliente_per_piva(conn, dati['p_iva'])
        if cliente:
            dati['cliente_id'] = cliente['id']
    
    campi = list(dati.keys())
    placeholders = ', '.join(['?' for _ in campi])
    query = f"INSERT INTO veicoli ({', '.join(campi)}) VALUES ({placeholders})"
    
    cursor.execute(query, list(dati.values()))
    conn.commit()
    
    return cursor.lastrowid


def aggiorna_commerciale_cliente(conn, nome_cliente, nuovo_commerciale):
    """Aggiorna il commerciale per tutti i veicoli di un cliente."""
    cursor = conn.cursor()
    
    # Aggiorna veicoli
    cursor.execute('''
        UPDATE veicoli SET commerciale = ? WHERE p_iva IN (
            SELECT p_iva FROM veicoli_attivi WHERE NOME_CLIENTE = ?
        )
    ''', (nuovo_commerciale, nome_cliente))
    
    # Aggiorna anche tabella clienti se esiste
    cursor.execute('''
        UPDATE clienti SET commerciale = ?, data_ultimo_aggiornamento = ?
        WHERE nome_cliente = ?
    ''', (nuovo_commerciale, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), nome_cliente))
    
    conn.commit()
    return cursor.rowcount


# ==============================================================================
# FUNZIONI STATISTICHE
# ==============================================================================

def get_statistiche_generali(conn):
    """Ritorna statistiche generali del database."""
    cursor = conn.cursor()
    
    stats = {}
    
    # Clienti
    cursor.execute('SELECT COUNT(*) FROM clienti')
    stats['totale_clienti'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clienti WHERE score IS NOT NULL')
    stats['clienti_con_creditsafe'] = cursor.fetchone()[0]
    
    # Veicoli
    cursor.execute('SELECT COUNT(*) FROM veicoli_attivi')
    stats['totale_veicoli'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COALESCE(SUM(canone), 0) FROM veicoli_attivi')
    stats['canone_totale'] = cursor.fetchone()[0]
    
    # Score distribution
    cursor.execute('''
        SELECT score, COUNT(*) as count FROM clienti 
        WHERE score IS NOT NULL GROUP BY score ORDER BY score
    ''')
    stats['distribuzione_score'] = {row['score']: row['count'] for row in cursor.fetchall()}
    
    # Commerciali
    cursor.execute('''
        SELECT COALESCE(commerciale, 'Non assegnato') as comm, COUNT(DISTINCT p_iva) as clienti
        FROM veicoli_attivi GROUP BY commerciale ORDER BY commerciale
    ''')
    stats['per_commerciale'] = [dict(row) for row in cursor.fetchall()]
    
    return stats


# ==============================================================================
# MANUTENZIONE
# ==============================================================================

def pulisci_log_vecchi(conn, giorni=7):
    """Rimuove record dallo storico piu vecchi di N giorni."""
    from datetime import timedelta
    
    data_limite = (datetime.now() - timedelta(days=giorni)).strftime('%Y-%m-%d')
    
    cursor = conn.cursor()
    cursor.execute('DELETE FROM storico_modifiche WHERE data_modifica < ?', (data_limite,))
    conn.commit()
    
    return cursor.rowcount


def backup_database(percorso_backup=None):
    """Crea un backup del database."""
    import shutil
    from datetime import datetime
    
    if not percorso_backup:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        percorso_backup = DB_DIR / f"gestionale_backup_{timestamp}.db"
    
    shutil.copy(str(DB_FILE), str(percorso_backup))
    return percorso_backup
