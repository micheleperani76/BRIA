#!/usr/bin/env python3
# ==============================================================================
# CREDITSAFE POLLING ALERT - Aggiornamento automatico dati clienti
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Legge alert da Creditsafe API e aggiorna dati nel DB
#
# OPERAZIONI:
# 1. Autentica API
# 2. Scarica eventi non processati dal portfolio
# 3. Per ogni evento:
#    a. Salva in clienti_creditsafe_alert
#    b. Aggiorna dati cliente in base al rule_code
#    c. Registra in storico_modifiche
#    d. Marca evento come processato su API
#
# REGOLE GESTITE:
# 102  = Credit Limit    -> aggiorna clienti.credito
# 101  = Score (banda)   -> aggiorna clienti.score
# 1404 = Protesti         -> aggiorna clienti.protesti
# 1406 = Company Status   -> aggiorna clienti.stato
# 105  = Address          -> aggiorna indirizzo + indirizzo_protetto = 1
# 107  = Directors        -> imposta amministratore_variato = 1
#
# SCHEDULING (crontab):
# 0 20 * * 4 cd /home/michele/gestione_flotta && python3 scripts/creditsafe_polling_alert.py >> logs/creditsafe_polling.log 2>&1
#
# USO MANUALE:
#   cd ~/gestione_flotta
#   python3 scripts/creditsafe_polling_alert.py --dry-run
#   python3 scripts/creditsafe_polling_alert.py
#
# ==============================================================================

import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()

if SCRIPT_DIR.name == 'scripts':
    BASE_DIR = SCRIPT_DIR.parent
else:
    BASE_DIR = SCRIPT_DIR

DB_FILE = BASE_DIR / 'db' / 'gestionale.db'
LOG_DIR = BASE_DIR / 'logs'

# Portfolio Creditsafe
PORTFOLIO_ID = '1762584'

# Origine per storico_modifiche
ORIGINE_STORICO = 'Creditsafe API Alert'


# ==============================================================================
# LOGGING
# ==============================================================================

LOG_DIR.mkdir(exist_ok=True)

ts_log = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = LOG_DIR / f'creditsafe_polling_{ts_log}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ==============================================================================
# MAPPING REGOLE -> AZIONI DB
# ==============================================================================

def applica_regola_102(conn, cliente_id, old_value, new_value):
    """Credit Limit: aggiorna clienti.credito"""
    registra_e_aggiorna(conn, cliente_id, 'credito', old_value, new_value)


def applica_regola_101(conn, cliente_id, old_value, new_value):
    """International Score: aggiorna clienti.score"""
    registra_e_aggiorna(conn, cliente_id, 'score', old_value, new_value)


def applica_regola_1404(conn, cliente_id, old_value, new_value):
    """Protesti: aggiorna clienti.protesti"""
    registra_e_aggiorna(conn, cliente_id, 'protesti', old_value, new_value)


def applica_regola_1406(conn, cliente_id, old_value, new_value):
    """Company Status: aggiorna clienti.stato"""
    registra_e_aggiorna(conn, cliente_id, 'stato', old_value, new_value)


def applica_regola_105(conn, cliente_id, old_value, new_value):
    """
    Address: aggiorna indirizzo e imposta indirizzo_protetto = 1.
    Creditsafe e' la fonte di verita' per l'indirizzo.
    Il new_value contiene l'indirizzo completo come stringa.
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Recupera indirizzo attuale
    cursor.execute('SELECT indirizzo FROM clienti WHERE id = ?', (cliente_id,))
    row = cursor.fetchone()
    valore_precedente = row[0] if row else ''
    
    # Aggiorna indirizzo + flag protetto
    cursor.execute("""
        UPDATE clienti 
        SET indirizzo = ?,
            indirizzo_protetto = 1,
            creditsafe_api_sync_at = ?
        WHERE id = ?
    """, (new_value, now, cliente_id))
    
    # Storico
    cursor.execute("""
        INSERT INTO storico_modifiche 
        (tabella, record_id, campo_modificato, valore_precedente, valore_nuovo, data_modifica, origine)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('clienti', cliente_id, 'indirizzo', str(valore_precedente), str(new_value), now, ORIGINE_STORICO))
    
    logger.info(f"  Indirizzo aggiornato + indirizzo_protetto=1")


def applica_regola_107(conn, cliente_id, old_value, new_value):
    """
    Directors: imposta flag amministratore_variato = 1.
    L'alert non contiene i nuovi dati, solo il segnale di cambiamento.
    Il flag si resetta quando si importa un nuovo PDF Creditsafe.
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        UPDATE clienti 
        SET amministratore_variato = 1,
            creditsafe_api_sync_at = ?
        WHERE id = ?
    """, (now, cliente_id))
    
    # Storico
    cursor.execute("""
        INSERT INTO storico_modifiche 
        (tabella, record_id, campo_modificato, valore_precedente, valore_nuovo, data_modifica, origine)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('clienti', cliente_id, 'amministratore_variato', '0', '1', now, ORIGINE_STORICO))
    
    logger.info(f"  Flag amministratore_variato = 1")


# Mapping rule_code -> funzione
REGOLE_HANDLER = {
    102:  applica_regola_102,
    101:  applica_regola_101,
    1404: applica_regola_1404,
    1406: applica_regola_1406,
    105:  applica_regola_105,
    107:  applica_regola_107,
}

REGOLE_NOMI = {
    102:  'Credit Limit',
    101:  'International Score',
    1404: 'Protesti',
    1406: 'Company Status',
    105:  'Address',
    107:  'Directors',
}


# ==============================================================================
# FUNZIONI DB
# ==============================================================================

def registra_e_aggiorna(conn, cliente_id, campo, old_value, new_value):
    """
    Aggiorna un singolo campo del cliente e registra nello storico.
    Usata per regole semplici (102, 101, 1404, 1406).
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Recupera valore attuale dal DB (potrebbe differire da old_value dell'alert)
    cursor.execute(f'SELECT {campo} FROM clienti WHERE id = ?', (cliente_id,))
    row = cursor.fetchone()
    valore_db_attuale = row[0] if row else ''
    
    # Aggiorna
    cursor.execute(f"""
        UPDATE clienti 
        SET {campo} = ?,
            creditsafe_api_sync_at = ?
        WHERE id = ?
    """, (new_value, now, cliente_id))
    
    # Storico (usa il valore reale dal DB, non dall'alert)
    cursor.execute("""
        INSERT INTO storico_modifiche 
        (tabella, record_id, campo_modificato, valore_precedente, valore_nuovo, data_modifica, origine)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('clienti', cliente_id, campo, str(valore_db_attuale), str(new_value), now, ORIGINE_STORICO))
    
    logger.info(f"  {campo}: {valore_db_attuale} -> {new_value}")


def trova_cliente_per_connect_id(conn, connect_id):
    """Trova cliente_id dal connect_id."""
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome_cliente FROM clienti WHERE connect_id = ?', (connect_id,))
    return cursor.fetchone()


def salva_alert_db(conn, cliente_id, evento, dry_run=False):
    """
    Salva evento nella tabella clienti_creditsafe_alert.
    """
    if dry_run:
        return
    
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Tipo alert leggibile
    rule_code = evento.get('ruleCode', 0)
    tipo_alert = REGOLE_NOMI.get(rule_code, f'Regola {rule_code}')
    
    cursor.execute("""
        INSERT INTO clienti_creditsafe_alert 
        (cliente_id, tipo_alert, valore, data_rilevazione, fonte,
         connect_id, event_id, event_date, rule_code, rule_description,
         old_value, new_value, is_processed, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        cliente_id,
        tipo_alert,
        evento.get('newValue', ''),
        evento.get('eventDate', ''),
        'Creditsafe API',
        evento.get('companyId', ''),
        evento.get('eventId', str(evento.get('id', ''))),
        evento.get('eventDate', ''),
        rule_code,
        evento.get('ruleName', evento.get('ruleDescription', '')),
        evento.get('oldValue', ''),
        evento.get('newValue', ''),
        now
    ))


# ==============================================================================
# POLLING PRINCIPALE
# ==============================================================================

def esegui_polling(api, conn, dry_run=False):
    """
    Scarica e processa tutti gli eventi non processati.
    
    Returns:
        tuple: (processati, errori, sconosciuti)
    """
    
    print("\n" + "=" * 60)
    print("[POLLING] Scaricamento eventi non processati")
    print("=" * 60)
    
    # Scarica tutti gli eventi non processati
    try:
        eventi = api.get_all_notification_events(
            portfolio_id=PORTFOLIO_ID,
            is_processed=False
        )
    except Exception as e:
        logger.error(f"Errore scaricamento eventi: {e}")
        return 0, 1, 0
    
    if not eventi:
        logger.info("Nessun evento da processare")
        return 0, 0, 0
    
    logger.info(f"Trovati {len(eventi)} eventi da processare")
    
    processati = 0
    errori = 0
    sconosciuti = 0
    
    for i, evento in enumerate(eventi, 1):
        # Estrai dati evento
        connect_id = evento.get('companyId', '')
        rule_code = evento.get('ruleCode', 0)
        event_id = evento.get('eventId', str(evento.get('id', '')))
        old_value = evento.get('oldValue', '')
        new_value = evento.get('newValue', '')
        rule_name = REGOLE_NOMI.get(rule_code, f'Regola {rule_code}')
        
        prefix = f"[{i}/{len(eventi)}]"
        logger.info(f"{prefix} Evento: {rule_name} (code={rule_code}) per {connect_id}")
        logger.info(f"  old={old_value} -> new={new_value}")
        
        # Trova cliente nel DB
        cliente = trova_cliente_per_connect_id(conn, connect_id)
        
        if not cliente:
            logger.warning(f"{prefix} [SKIP] Cliente non trovato per connect_id: {connect_id}")
            sconosciuti += 1
            # Marca come processato su API anche se non trovato (evita loop)
            if not dry_run:
                try:
                    api.mark_event_processed(event_id)
                except Exception:
                    pass
            continue
        
        cliente_id, nome_cliente = cliente
        logger.info(f"  Cliente: {nome_cliente} (id={cliente_id})")
        
        if dry_run:
            logger.info(f"{prefix} [DRY] Aggiornerei {rule_name} per {nome_cliente}")
            processati += 1
            continue
        
        try:
            # A) Salva alert nel DB
            salva_alert_db(conn, cliente_id, evento)
            
            # B) Applica modifica al DB
            handler = REGOLE_HANDLER.get(rule_code)
            if handler:
                handler(conn, cliente_id, old_value, new_value)
            else:
                logger.warning(f"  Regola {rule_code} non gestita, solo salvato alert")
            
            # C) Commit modifiche
            conn.commit()
            
            # D) Marca come processato su API
            try:
                api.mark_event_processed(event_id)
            except Exception as e:
                logger.warning(f"  Errore mark_processed su API (dati DB gia' aggiornati): {e}")
            
            processati += 1
            logger.info(f"{prefix} [OK] Processato")
            
        except Exception as e:
            logger.error(f"{prefix} [ERR] Errore processamento: {e}")
            conn.rollback()
            errori += 1
    
    return processati, errori, sconosciuti


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv
    
    print("=" * 60)
    print("  CREDITSAFE POLLING ALERT")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'ESECUZIONE REALE'}")
    print(f"  Portfolio ID: {PORTFOLIO_ID}")
    print(f"  Log: {log_file}")
    print("=" * 60)
    
    # ---- Verifica DB ----
    if not DB_FILE.exists():
        logger.error(f"Database non trovato: {DB_FILE}")
        sys.exit(1)
    
    # ---- Connessione DB ----
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    
    # ---- Inizializza API ----
    print("\n  Inizializzazione API Creditsafe...")
    sys.path.insert(0, str(BASE_DIR))
    
    try:
        from app.creditsafe_api import get_api_client
        api = get_api_client(str(BASE_DIR))
        api.authenticate()
        print("  [OK] Autenticazione riuscita")
    except Exception as e:
        logger.error(f"Errore autenticazione: {e}")
        conn.close()
        sys.exit(1)
    
    # ---- Polling ----
    processati, errori, sconosciuti = esegui_polling(api, conn, dry_run)
    
    # ---- Chiudi connessione ----
    conn.close()
    
    # ---- Riepilogo ----
    print("\n" + "=" * 60)
    print("  RIEPILOGO POLLING")
    print("=" * 60)
    print(f"  Processati: {processati}")
    print(f"  Errori: {errori}")
    print(f"  Clienti non trovati: {sconosciuti}")
    print(f"  Log: {log_file}")
    
    if dry_run:
        print(f"\n  DRY-RUN: nessuna modifica effettuata")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
