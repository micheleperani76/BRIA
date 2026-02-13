#!/usr/bin/env python3
# ==============================================================================
# CREDITSAFE SYNC CLIENTI - Popola portfolio monitoring
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Sincronizza clienti con Creditsafe API monitoring
#
# OPERAZIONI:
# 1. Rimuove aziende non piu' monitorate (es: A.T.I.B. test)
# 2. Per ogni cliente con stato_crm idoneo:
#    - Cerca azienda per P.IVA -> ottiene connect_id
#    - Aggiunge al portfolio monitoring
#    - Salva connect_id e portfolio_ref nel DB locale
# 3. Attiva regole di notifica sul portfolio
#
# CARATTERISTICHE:
# - Modalita' --dry-run (nessuna modifica a DB e API)
# - Salvataggio progresso (riprende da dove interrotto)
# - Rate limiting (1s tra richieste API)
# - Gestione errori singolo cliente (non blocca tutto)
# - Log dettagliato in logs/
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/creditsafe_sync_clienti.py --dry-run
#   python3 scripts/creditsafe_sync_clienti.py
#
# ==============================================================================

import sys
import json
import time
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
PROGRESS_FILE = LOG_DIR / 'creditsafe_sync_progresso.json'

# Portfolio Creditsafe (verificato con esplora.py)
PORTFOLIO_ID = '1762584'

# Clienti da monitorare
STATI_MONITORATI = ('Cliente', 'Prospetto Canale Tecnico', 'Cliente Canale Tecnico')

# Aziende da rimuovere dal portfolio (test precedenti)
AZIENDE_DA_RIMUOVERE = [
    {'connect_id': 'IT-0-BS183271', 'nome': 'A.T.I.B. SRL (test)'},
]

# Regole da attivare sul portfolio
# Codici da output creditsafe_esplora.py [3/5]
#
# 101 = International Score: param0=bande riduzione, param1=sotto banda, param2=return banda
#        -> param0="1" cattura qualsiasi variazione di 1+ bande
# 102 = Limit: param0=valuta, param1=riduzione %, param2=sotto valore
#        -> param1="1" cattura qualsiasi variazione di 1%+
# 1404 = Protesti (nessun parametro)
# 1406 = Company Status (nessun parametro)
# 105  = Address (nessun parametro)
# 107  = Director(s) (nessun parametro)

REGOLE_IT = [
    {"ruleCode": 101, "isActive": 1, "param0": "1", "param1": "", "param2": ""},
    {"ruleCode": 102, "isActive": 1, "param0": "Any", "param1": "1", "param2": ""},
    {"ruleCode": 1404, "isActive": 1},
    {"ruleCode": 1406, "isActive": 1},
    {"ruleCode": 105, "isActive": 1},
    {"ruleCode": 107, "isActive": 1},
]

# ==============================================================================
# LOGGING
# ==============================================================================

LOG_DIR.mkdir(exist_ok=True)

ts_log = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = LOG_DIR / f'creditsafe_sync_{ts_log}.log'

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
# PROGRESSO (per riprendere da interruzione)
# ==============================================================================

def carica_progresso():
    """Carica stato progresso da file JSON."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def salva_progresso(progresso):
    """Salva stato progresso su file JSON."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progresso, f, indent=2)


def cancella_progresso():
    """Cancella file progresso (sync completata)."""
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


# ==============================================================================
# FUNZIONI DB
# ==============================================================================

def get_clienti_da_monitorare(conn):
    """
    Recupera clienti da sincronizzare con Creditsafe.
    
    Returns:
        list: [(id, nome_cliente, p_iva, stato_crm), ...]
    """
    cursor = conn.cursor()
    placeholders = ','.join('?' for _ in STATI_MONITORATI)
    cursor.execute(f"""
        SELECT id, nome_cliente, p_iva, stato_crm
        FROM clienti
        WHERE stato_crm IN ({placeholders})
        AND p_iva IS NOT NULL AND p_iva != ''
        ORDER BY id
    """, STATI_MONITORATI)
    return cursor.fetchall()


def aggiorna_connect_id(conn, cliente_id, connect_id, portfolio_ref, dry_run=False):
    """
    Aggiorna connect_id e portfolio_ref nel DB.
    """
    if dry_run:
        return
    
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        UPDATE clienti 
        SET connect_id = ?,
            creditsafe_portfolio_ref = ?,
            creditsafe_api_sync_at = ?
        WHERE id = ?
    """, (connect_id, portfolio_ref, now, cliente_id))
    conn.commit()


# ==============================================================================
# STEP 1: PULIZIA PORTFOLIO
# ==============================================================================

def step1_pulizia_portfolio(api, dry_run=False):
    """Rimuove aziende test/non piu' monitorate dal portfolio."""
    
    print("\n" + "=" * 60)
    print("[STEP 1] Pulizia portfolio - Rimozione aziende non monitorate")
    print("=" * 60)
    
    rimossi = 0
    errori = 0
    
    for azienda in AZIENDE_DA_RIMUOVERE:
        cid = azienda['connect_id']
        nome = azienda['nome']
        
        if dry_run:
            logger.info(f"[DRY] Rimuoverei {nome} ({cid})")
            rimossi += 1
        else:
            try:
                result = api.remove_company_from_portfolio(PORTFOLIO_ID, cid)
                if result:
                    logger.info(f"[OK] Rimossa {nome} ({cid})")
                    rimossi += 1
                else:
                    logger.warning(f"[WARN] Rimozione fallita per {nome} ({cid})")
                    errori += 1
            except Exception as e:
                # Se non trovata, va bene lo stesso
                if '404' in str(e) or 'not found' in str(e).lower():
                    logger.info(f"[SKIP] {nome} ({cid}) - non presente nel portfolio")
                else:
                    logger.error(f"[ERR] Errore rimozione {nome}: {e}")
                    errori += 1
    
    print(f"\n  Rimossi: {rimossi} | Errori: {errori}")
    return rimossi, errori


# ==============================================================================
# STEP 2: SYNC CLIENTI
# ==============================================================================

def step2_sync_clienti(api, conn, clienti, dry_run=False):
    """
    Per ogni cliente: cerca per P.IVA, ottieni connect_id, aggiungi a portfolio.
    
    Salva progresso ogni 10 clienti per poter riprendere.
    """
    
    print("\n" + "=" * 60)
    print(f"[STEP 2] Sync clienti - {len(clienti)} da processare")
    print("=" * 60)
    
    # Carica progresso precedente
    progresso = carica_progresso()
    clienti_sincronizzati = set(progresso.get('clienti_ok', []))
    
    if clienti_sincronizzati:
        logger.info(f"Ripresa da interruzione precedente: {len(clienti_sincronizzati)} gia' sincronizzati")
    
    # Contatori
    ok = len(clienti_sincronizzati)
    skip_gia_sync = 0
    skip_non_trovato = 0
    skip_piva_invalida = 0
    errori = 0
    totale = len(clienti)
    
    for i, (cliente_id, nome, p_iva, stato_crm) in enumerate(clienti, 1):
        
        # Skip se gia' sincronizzato (ripresa da interruzione)
        if cliente_id in clienti_sincronizzati:
            skip_gia_sync += 1
            continue
        
        prefix = f"[{i}/{totale}]"
        
        # ---- A) Cerca per P.IVA ----
        try:
            if dry_run:
                logger.info(f"{prefix} [DRY] Cercherei P.IVA {p_iva} per: {nome}")
                # In dry-run simuliamo successo
                clienti_sincronizzati.add(cliente_id)
                ok += 1
                continue
            
            company = api.search_company_by_vat(p_iva)
            
            if company is None:
                logger.warning(f"{prefix} [SKIP] Non trovata su Creditsafe: {nome} (P.IVA: {p_iva})")
                skip_non_trovato += 1
                
                # Salva progresso anche per i non trovati (non riprovare)
                progresso.setdefault('clienti_non_trovati', []).append(cliente_id)
                clienti_sincronizzati.add(cliente_id)
                if i % 10 == 0:
                    progresso['clienti_ok'] = list(clienti_sincronizzati)
                    salva_progresso(progresso)
                continue
            
            connect_id = company.get('id', '')
            company_name = company.get('name', 'N/D')
            
            if not connect_id:
                logger.warning(f"{prefix} [SKIP] ConnectId vuoto per: {nome}")
                skip_non_trovato += 1
                clienti_sincronizzati.add(cliente_id)
                continue
            
        except Exception as e:
            logger.error(f"{prefix} [ERR] Errore ricerca {nome} (P.IVA: {p_iva}): {e}")
            errori += 1
            # Non aggiungo a sincronizzati: riprovera' al prossimo giro
            continue
        
        # ---- B) Aggiungi a portfolio ----
        try:
            api.add_company_to_portfolio(
                PORTFOLIO_ID,
                connect_id,
                reference=str(cliente_id)
            )
            logger.info(f"{prefix} [OK] {nome} -> {connect_id}")
            
        except Exception as e:
            err_str = str(e).lower()
            # Se gia' nel portfolio (409 Conflict), va bene lo stesso
            if 'already' in err_str or 'duplicate' in err_str or 'exists' in err_str or '409' in err_str or 'conflict' in err_str:
                logger.info(f"{prefix} [OK] {nome} -> {connect_id} (gia' nel portfolio)")
            else:
                logger.error(f"{prefix} [ERR] Errore aggiunta portfolio {nome}: {e}")
                errori += 1
                continue
        
        # ---- C) Aggiorna DB locale ----
        try:
            aggiorna_connect_id(conn, cliente_id, connect_id, PORTFOLIO_ID)
            ok += 1
            clienti_sincronizzati.add(cliente_id)
            
        except Exception as e:
            logger.error(f"{prefix} [ERR] Errore aggiornamento DB per {nome}: {e}")
            errori += 1
            continue
        
        # Salva progresso ogni 10 clienti
        if i % 10 == 0:
            progresso['clienti_ok'] = list(clienti_sincronizzati)
            salva_progresso(progresso)
            logger.info(f"--- Progresso salvato: {ok}/{totale} ---")
    
    # Salva progresso finale
    if not dry_run:
        progresso['clienti_ok'] = list(clienti_sincronizzati)
        progresso['completato'] = True
        progresso['data_completamento'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        salva_progresso(progresso)
    
    print(f"\n  OK: {ok} | Non trovati: {skip_non_trovato} | P.IVA invalida: {skip_piva_invalida} | Errori: {errori}")
    if skip_gia_sync > 0:
        print(f"  Saltati (gia' sincronizzati da run precedente): {skip_gia_sync}")
    
    return ok, skip_non_trovato, errori


# ==============================================================================
# STEP 3: ATTIVAZIONE REGOLE
# ==============================================================================

def step3_attiva_regole(api, dry_run=False):
    """Attiva regole di notifica sul portfolio."""
    
    print("\n" + "=" * 60)
    print("[STEP 3] Attivazione regole notifica sul portfolio")
    print("=" * 60)
    
    print("\n  Regole da attivare:")
    nomi_regole = {
        101: "International Score (variazione 1+ bande)",
        102: "Credit Limit (variazione 1%+)",
        1404: "Protesti",
        1406: "Company Status",
        105: "Address (indirizzo)",
        107: "Director(s) (amministratori)",
    }
    
    for regola in REGOLE_IT:
        code = regola['ruleCode']
        nome = nomi_regole.get(code, '?')
        params = {k: v for k, v in regola.items() if k.startswith('param') and v}
        param_str = f" [{params}]" if params else ""
        print(f"    [{code}] {nome}{param_str}")
    
    if dry_run:
        logger.info("[DRY] Regole NON attivate (dry-run)")
        return True
    
    try:
        api.set_portfolio_rules(PORTFOLIO_ID, 'IT', REGOLE_IT)
        logger.info("[OK] Regole IT attivate con successo")
        
        # Verifica
        regole_attive = api.get_portfolio_rules(PORTFOLIO_ID)
        if regole_attive:
            logger.info(f"[OK] Verifica: regole attive sul portfolio")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERR] Errore attivazione regole: {e}")
        return False


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv
    
    print("=" * 60)
    print("  CREDITSAFE SYNC CLIENTI")
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
    
    # ---- Conta clienti ----
    clienti = get_clienti_da_monitorare(conn)
    print(f"\n  Clienti da monitorare: {len(clienti)}")
    print(f"  Stati: {', '.join(STATI_MONITORATI)}")
    
    if not clienti:
        logger.warning("Nessun cliente trovato da monitorare")
        conn.close()
        return
    
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
    
    # ---- STEP 1: Pulizia portfolio ----
    step1_rimossi, step1_errori = step1_pulizia_portfolio(api, dry_run)
    
    # ---- STEP 2: Sync clienti ----
    step2_ok, step2_non_trovati, step2_errori = step2_sync_clienti(api, conn, clienti, dry_run)
    
    # ---- STEP 3: Attiva regole ----
    step3_ok = step3_attiva_regole(api, dry_run)
    
    # ---- Chiudi connessione ----
    conn.close()
    
    # ---- Riepilogo finale ----
    print("\n" + "=" * 60)
    print("  RIEPILOGO SYNC")
    print("=" * 60)
    print(f"  Pulizia portfolio: {step1_rimossi} rimossi, {step1_errori} errori")
    print(f"  Sync clienti: {step2_ok} OK, {step2_non_trovati} non trovati, {step2_errori} errori")
    print(f"  Regole attivate: {'SI' if step3_ok else 'NO'}")
    print(f"  Log completo: {log_file}")
    
    if not dry_run and step2_errori == 0:
        cancella_progresso()
        print(f"\n  File progresso cancellato (sync completata senza errori)")
    elif not dry_run and step2_errori > 0:
        print(f"\n  File progresso mantenuto: {PROGRESS_FILE}")
        print(f"  Riesegui lo script per riprovare i {step2_errori} errori")
    
    if dry_run:
        print(f"\n  DRY-RUN: nessuna modifica effettuata")
        print(f"  Riesegui senza --dry-run per procedere")
    
    # ---- Stima slot monitoring usati ----
    if not dry_run:
        print(f"\n  ATTENZIONE: slot monitoring usati ~ {step2_ok + 1}/2000")
        print(f"  (1 era A.T.I.B. test, ora rimossa -> slot potrebbe non liberarsi)")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
