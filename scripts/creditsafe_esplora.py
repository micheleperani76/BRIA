#!/usr/bin/env python3
# ==============================================================================
# CREDITSAFE API - Script esplorativo
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Testa connessione API e mappa regole/eventi disponibili
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/creditsafe_esplora.py
#
# OPERAZIONI:
# 1. Test autenticazione
# 2. Info accesso account (limiti, servizi)
# 3. Lista regole disponibili IT + XX (globali)
# 4. Lista portfolio esistenti
# 5. Test ricerca azienda (opzionale, con P.IVA di test)
#
# ==============================================================================

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup path
SCRIPT_DIR = Path(__file__).parent.absolute()
if SCRIPT_DIR.name == 'scripts':
    BASE_DIR = SCRIPT_DIR.parent
else:
    BASE_DIR = SCRIPT_DIR

sys.path.insert(0, str(BASE_DIR))

from app.creditsafe_api import CreditsafeAPI

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# P.IVA di test (BR Car Service stessa o un cliente noto)
# Lasciare vuoto per saltare il test ricerca
PIVA_TEST = ""

# File output per salvare risultati
OUTPUT_DIR = BASE_DIR / 'logs'
OUTPUT_FILE = OUTPUT_DIR / f"creditsafe_esplora_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 70)
    print("  CREDITSAFE API - ESPLORAZIONE")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    risultati = {
        'data_esplorazione': datetime.now().isoformat(),
        'errori': []
    }
    
    # --- 1. AUTENTICAZIONE ---
    print("\n[1/5] Test autenticazione...")
    
    api = CreditsafeAPI(base_dir=BASE_DIR)
    
    try:
        token = api.authenticate()
        print(f"  OK - Token ottenuto ({len(token)} caratteri)")
        print(f"  Username: {api._username}")
        risultati['autenticazione'] = 'OK'
    except Exception as e:
        print(f"  ERRORE: {e}")
        risultati['autenticazione'] = f'ERRORE: {e}'
        risultati['errori'].append(f'Autenticazione: {e}')
        print("\n  Impossibile proseguire senza autenticazione.")
        salva_risultati(risultati)
        sys.exit(1)
    
    # --- 2. INFO ACCESSO ---
    print("\n[2/5] Verifica accesso account...")
    
    try:
        access = api.get_access_info()
        risultati['accesso'] = access
        
        # Mostra info utili
        if isinstance(access, dict):
            # Cerca sottoscrizioni
            print("  Servizi disponibili:")
            
            # La struttura varia, proviamo diverse chiavi
            for key in ['subscriptions', 'countryAccess', 'access']:
                if key in access:
                    print(f"  [{key}]:")
                    val = access[key]
                    if isinstance(val, list):
                        for item in val[:10]:
                            print(f"    - {json.dumps(item, indent=6, ensure_ascii=False)[:200]}")
                    elif isinstance(val, dict):
                        for k, v in list(val.items())[:10]:
                            print(f"    {k}: {v}")
            
            # Se non ha trovato nulla di strutturato, stampa tutto
            if not any(k in access for k in ['subscriptions', 'countryAccess', 'access']):
                print(f"  Risposta completa:")
                print(f"  {json.dumps(access, indent=2, ensure_ascii=False)[:1000]}")
        else:
            print(f"  Risposta: {str(access)[:500]}")
            
    except Exception as e:
        print(f"  ERRORE: {e}")
        risultati['errori'].append(f'Accesso: {e}')
    
    # --- 3. REGOLE DISPONIBILI ---
    print("\n[3/5] Regole di notifica disponibili...")
    
    for country in ['IT', 'XX']:
        print(f"\n  Regole {country}:")
        try:
            rules = api.get_available_rules(country)
            risultati[f'regole_{country}'] = rules
            
            if isinstance(rules, list):
                print(f"  Trovate {len(rules)} regole:")
                for rule in rules:
                    code = rule.get('ruleCode', rule.get('code', 'N/D'))
                    name = rule.get('ruleName', rule.get('name', rule.get('description', 'N/D')))
                    params = rule.get('parameters', rule.get('params', []))
                    print(f"    [{code}] {name}")
                    if params:
                        print(f"         Parametri: {params}")
            elif isinstance(rules, dict):
                rule_list = rules.get('eventRules', rules.get('rules', []))
                print(f"  Trovate {len(rule_list)} regole:")
                risultati[f'regole_{country}'] = rule_list
                for rule in rule_list:
                    code = rule.get('ruleCode', rule.get('code', 'N/D'))
                    name = rule.get('ruleName', rule.get('name', rule.get('description', 'N/D')))
                    print(f"    [{code}] {name}")
            else:
                print(f"  Risposta: {str(rules)[:500]}")
                
        except Exception as e:
            print(f"  ERRORE regole {country}: {e}")
            risultati['errori'].append(f'Regole {country}: {e}')
    
    # --- 4. PORTFOLIO ESISTENTI ---
    print("\n[4/5] Portfolio esistenti...")
    
    try:
        portfolios = api.list_portfolios()
        risultati['portfolios'] = portfolios
        
        if isinstance(portfolios, list):
            if portfolios:
                print(f"  Trovati {len(portfolios)} portfolio:")
                for p in portfolios:
                    pid = p.get('portfolioId', p.get('id', 'N/D'))
                    pname = p.get('name', 'N/D')
                    pcount = p.get('totalCompanies', p.get('companiesCount', '?'))
                    print(f"    - {pname} (id: {pid}, aziende: {pcount})")
                    
                    # Se ha un portfolio, prova a leggere le regole attive
                    try:
                        active_rules = api.get_portfolio_rules(pid)
                        risultati[f'portfolio_{pid}_rules'] = active_rules
                        if active_rules:
                            print(f"      Regole attive: {json.dumps(active_rules, ensure_ascii=False)[:200]}")
                    except Exception as e:
                        print(f"      Regole attive: errore ({e})")
                    
                    # Prova a leggere eventuali eventi
                    try:
                        events = api.get_notification_events(portfolio_id=pid, page_size=5)
                        risultati[f'portfolio_{pid}_events'] = events
                        ev_list = events.get('notificationEvents', [])
                        total = events.get('totalCount', 0)
                        print(f"      Eventi: {total} totali, mostro ultimi {len(ev_list)}:")
                        for ev in ev_list:
                            print(f"        - [{ev.get('ruleCode', '?')}] {ev.get('companyName', 'N/D')}: "
                                  f"{ev.get('ruleDescription', 'N/D')} "
                                  f"({ev.get('oldValue', '?')} -> {ev.get('newValue', '?')}) "
                                  f"data: {ev.get('eventDate', 'N/D')}")
                    except Exception as e:
                        print(f"      Eventi: errore ({e})")
            else:
                print("  Nessun portfolio trovato (da creare)")
        else:
            print(f"  Risposta: {str(portfolios)[:500]}")
            
    except Exception as e:
        print(f"  ERRORE: {e}")
        risultati['errori'].append(f'Portfolio: {e}')
    
    # --- 5. TEST RICERCA (opzionale) ---
    if PIVA_TEST:
        print(f"\n[5/5] Test ricerca azienda (P.IVA: {PIVA_TEST})...")
        
        try:
            company = api.search_company_by_vat(PIVA_TEST)
            risultati['test_ricerca'] = company
            
            if company:
                print(f"  Trovata: {company.get('name', 'N/D')}")
                print(f"  ConnectId: {company.get('id', 'N/D')}")
                print(f"  Stato: {company.get('status', 'N/D')}")
                addr = company.get('address', {})
                if isinstance(addr, dict):
                    print(f"  Indirizzo: {addr.get('simpleValue', 'N/D')}")
                print(f"  Risposta completa:")
                print(f"  {json.dumps(company, indent=2, ensure_ascii=False)[:1000]}")
            else:
                print("  Nessun risultato")
                
        except Exception as e:
            print(f"  ERRORE: {e}")
            risultati['errori'].append(f'Ricerca: {e}')
    else:
        print("\n[5/5] Test ricerca: saltato (PIVA_TEST vuota)")
        print("  Per testare, modifica PIVA_TEST nello script")
    
    # --- SALVATAGGIO RISULTATI ---
    salva_risultati(risultati)
    
    # --- RIEPILOGO ---
    print("\n" + "=" * 70)
    print("  RIEPILOGO")
    print("=" * 70)
    print(f"  Autenticazione: {risultati.get('autenticazione', 'N/D')}")
    print(f"  Errori: {len(risultati.get('errori', []))}")
    if risultati.get('errori'):
        for err in risultati['errori']:
            print(f"    - {err}")
    print(f"  Output salvato in: {OUTPUT_FILE}")
    print("=" * 70)


def salva_risultati(risultati):
    """Salva risultati in file JSON per analisi successiva."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Converti oggetti non serializzabili
        def default_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(risultati, f, indent=2, ensure_ascii=False, default=default_serializer)
        
        print(f"\n  Risultati salvati in: {OUTPUT_FILE}")
    except Exception as e:
        print(f"\n  Errore salvataggio risultati: {e}")


if __name__ == "__main__":
    main()
