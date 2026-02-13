#!/usr/bin/env python3
# ==============================================================================
# CREDITSAFE API - Modulo integrazione
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Classe per interazione con Creditsafe Monitoring API
#
# Funzionalita':
# - Autenticazione JWT con cache token (1 ora)
# - Ricerca aziende per P.IVA
# - Gestione portfolio monitoring (CRUD)
# - Gestione event rules (regole notifica)
# - Recupero notification events (alert)
# - Rate limiting integrato
# - Retry con backoff su errori temporanei
#
# Credenziali: account_esterni/Credenziali_api_creditsafe.txt
# ==============================================================================

import re
import time
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# Endpoint
API_BASE_URL = "https://connect.creditsafe.com/v1"

# Percorso credenziali (relativo a gestione_flotta/)
CREDENZIALI_FILE = "account_esterni/Credenziali_api_creditsafe.txt"

# Token JWT dura 1 ora, rinnoviamo a 55 minuti per sicurezza
TOKEN_VALIDITY_MINUTES = 55

# Rate limiting: pausa tra richieste (secondi)
RATE_LIMIT_DELAY = 1.0

# Retry: tentativi massimi su errori temporanei
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # secondi, raddoppia ad ogni tentativo

# Logger
logger = logging.getLogger('creditsafe_api')


# ==============================================================================
# CLASSE PRINCIPALE
# ==============================================================================

class CreditsafeAPI:
    """
    Client per Creditsafe Connect API.
    
    Uso:
        api = CreditsafeAPI(base_dir='/home/michele/gestione_flotta')
        api.authenticate()
        
        # Ricerca azienda
        company = api.search_company_by_vat('12345678901')
        
        # Portfolio
        portfolios = api.list_portfolios()
        api.add_company_to_portfolio(portfolio_id, connect_id)
        
        # Eventi
        events = api.get_notification_events(portfolio_id)
    """
    
    def __init__(self, base_dir=None):
        """
        Inizializza client API.
        
        Args:
            base_dir: Path base gestione_flotta (default: auto-detect)
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Auto-detect: risali dalla posizione del modulo
            self.base_dir = Path(__file__).parent.parent
        
        self._token = None
        self._token_expires = None
        self._username = None
        self._password = None
        self._last_request_time = 0
    
    # ==========================================================================
    # CREDENZIALI
    # ==========================================================================
    
    def _load_credentials(self):
        """
        Carica credenziali dal file.
        
        Formato file:
            USERNAME = "user@example.com"
            PASSWORD = 'password_here'
        
        Returns:
            tuple: (username, password)
            
        Raises:
            FileNotFoundError: se il file non esiste
            ValueError: se il formato non e' valido
        """
        cred_path = self.base_dir / CREDENZIALI_FILE
        
        if not cred_path.exists():
            raise FileNotFoundError(
                f"File credenziali non trovato: {cred_path}\n"
                f"Creare il file con formato:\n"
                f'  USERNAME = "user@example.com"\n'
                f"  PASSWORD = 'password'"
            )
        
        contenuto = cred_path.read_text(encoding='utf-8').strip()
        
        username = None
        password = None
        
        for riga in contenuto.splitlines():
            riga = riga.strip()
            if not riga or riga.startswith('#'):
                continue
            
            # Parse USERNAME
            if riga.upper().startswith('USERNAME'):
                # Estrai valore tra virgolette (singole o doppie)
                m = re.search(r'=\s*["\'](.+?)["\']', riga)
                if m:
                    username = m.group(1)
            
            # Parse PASSWORD
            elif riga.upper().startswith('PASSWORD'):
                # Password puo' contenere virgolette, usiamo approccio diverso
                # Troviamo il delimitatore di apertura dopo il =
                m = re.search(r'=\s*(["\'])', riga)
                if m:
                    delim = m.group(1)
                    start = m.end()
                    # Cerca il delimitatore di chiusura (ultimo carattere)
                    # gestendo escape con backslash
                    raw_pwd = riga[start:]
                    # Rimuovi delimitatore finale
                    if raw_pwd.endswith(delim):
                        raw_pwd = raw_pwd[:-1]
                    # Gestisci escape
                    password = raw_pwd.replace("\\'", "'").replace('\\"', '"')
        
        if not username or not password:
            raise ValueError(
                f"Credenziali non valide in {cred_path}\n"
                f"Formato atteso:\n"
                f'  USERNAME = "user@example.com"\n'
                f"  PASSWORD = 'password'"
            )
        
        self._username = username
        self._password = password
        
        logger.debug(f"Credenziali caricate per: {username}")
        return username, password
    
    def test_credentials(self):
        """
        Testa se le credenziali sono valide.
        
        Returns:
            dict: {'valid': bool, 'username': str, 'error': str|None}
        """
        try:
            self._load_credentials()
            self.authenticate(force=True)
            return {
                'valid': True,
                'username': self._username,
                'error': None,
                'expires': self._token_expires.isoformat() if self._token_expires else None
            }
        except FileNotFoundError as e:
            return {'valid': False, 'username': None, 'error': f'File non trovato: {e}'}
        except ValueError as e:
            return {'valid': False, 'username': None, 'error': f'Formato non valido: {e}'}
        except requests.exceptions.HTTPError as e:
            return {'valid': False, 'username': self._username, 'error': f'Autenticazione fallita: {e}'}
        except Exception as e:
            return {'valid': False, 'username': self._username, 'error': str(e)}
    
    # ==========================================================================
    # AUTENTICAZIONE
    # ==========================================================================
    
    def authenticate(self, force=False):
        """
        Ottiene token JWT. Usa cache se ancora valido.
        
        Args:
            force: True per forzare rinnovo token
            
        Returns:
            str: Token JWT
            
        Raises:
            requests.exceptions.HTTPError: se autenticazione fallisce
        """
        # Cache: token ancora valido?
        if not force and self._token and self._token_expires:
            if datetime.now() < self._token_expires:
                logger.debug("Token JWT ancora valido (cache)")
                return self._token
        
        # Carica credenziali se non gia' caricate
        if not self._username or not self._password:
            self._load_credentials()
        
        logger.info(f"Autenticazione Creditsafe per {self._username}...")
        
        url = f"{API_BASE_URL}/authenticate"
        payload = {
            "username": self._username,
            "password": self._password
        }
        
        response = self._do_request('POST', url, json=payload, auth_required=False)
        
        self._token = response.get('token')
        self._token_expires = datetime.now() + timedelta(minutes=TOKEN_VALIDITY_MINUTES)
        
        logger.info(f"Token ottenuto, scade alle {self._token_expires.strftime('%H:%M:%S')}")
        return self._token
    
    def _get_headers(self):
        """Headers con token JWT."""
        if not self._token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
    
    # ==========================================================================
    # RICERCA AZIENDE
    # ==========================================================================
    
    def search_company_by_vat(self, vat_number, country="IT"):
        """
        Cerca azienda per P.IVA.
        
        Args:
            vat_number: P.IVA (11 cifre, senza prefisso IT)
            country: Codice paese (default: IT)
            
        Returns:
            dict|None: Dati azienda o None se non trovata
        """
        # Normalizza P.IVA
        vat_clean = str(vat_number).upper().replace('IT', '').replace(' ', '').strip()
        
        if not vat_clean or len(vat_clean) != 11 or not vat_clean.isdigit():
            logger.warning(f"P.IVA non valida: {vat_number}")
            return None
        
        url = f"{API_BASE_URL}/companies"
        params = {
            "countries": country,
            "vatNo": vat_clean
        }
        
        data = self._do_request('GET', url, params=params)
        
        companies = data.get('companies', [])
        if companies:
            company = companies[0]
            logger.info(f"Trovata: {company.get('name', 'N/D')} (connectId: {company.get('id', 'N/D')})")
            return company
        
        logger.info(f"Nessuna azienda trovata per P.IVA {vat_clean}")
        return None
    
    # ==========================================================================
    # ACCESSO ACCOUNT
    # ==========================================================================
    
    def get_access_info(self):
        """
        Verifica servizi disponibili nell'account.
        
        Returns:
            dict: Info accesso (paesi, sottoscrizioni, limiti)
        """
        url = f"{API_BASE_URL}/access"
        return self._do_request('GET', url)
    
    # ==========================================================================
    # PORTFOLIO MONITORING
    # ==========================================================================
    
    def list_portfolios(self):
        """
        Lista tutti i portfolio.
        
        Returns:
            list: Lista portfolio
        """
        url = f"{API_BASE_URL}/monitoring/portfolios"
        data = self._do_request('GET', url)
        return data.get('portfolios', data) if isinstance(data, dict) else data
    
    def create_portfolio(self, name, is_default=False):
        """
        Crea nuovo portfolio di monitoring.
        
        Args:
            name: Nome portfolio
            is_default: Se impostare come default
            
        Returns:
            dict: Dati portfolio creato (con portfolioId)
        """
        url = f"{API_BASE_URL}/monitoring/portfolios"
        payload = {
            "name": name,
            "isDefault": is_default
        }
        
        data = self._do_request('POST', url, json=payload)
        logger.info(f"Portfolio creato: {name}")
        return data
    
    def get_or_create_portfolio(self, name):
        """
        Recupera portfolio per nome, o lo crea se non esiste.
        
        Args:
            name: Nome portfolio
            
        Returns:
            dict: Dati portfolio (con 'id' o 'portfolioId')
        """
        portfolios = self.list_portfolios()
        
        for p in portfolios:
            p_name = p.get('name', '')
            if p_name == name:
                logger.info(f"Portfolio trovato: {name} (id: {p.get('portfolioId', p.get('id'))})")
                return p
        
        logger.info(f"Portfolio '{name}' non trovato, creazione...")
        return self.create_portfolio(name)
    
    def add_company_to_portfolio(self, portfolio_id, connect_id, reference=""):
        """
        Aggiunge azienda al portfolio monitoring.
        
        Args:
            portfolio_id: ID portfolio
            connect_id: ConnectId Creditsafe (es: IT001-X-12345678901)
            reference: Riferimento interno opzionale
            
        Returns:
            dict: Risposta API
        """
        url = f"{API_BASE_URL}/monitoring/portfolios/{portfolio_id}/companies"
        payload = {
            "id": connect_id,
            "personalReference": str(reference),
            "freeText": "",
            "personalLimit": ""
        }
        
        data = self._do_request('POST', url, json=payload)
        logger.info(f"Azienda aggiunta al portfolio: {connect_id}")
        return data
    
    def list_portfolio_companies(self, portfolio_id, page=1, page_size=50):
        """
        Lista aziende in un portfolio.
        
        Args:
            portfolio_id: ID portfolio
            page: Pagina (default: 1)
            page_size: Dimensione pagina (default: 50)
            
        Returns:
            dict: Risposta con lista aziende
        """
        url = f"{API_BASE_URL}/monitoring/portfolios/{portfolio_id}/companies"
        params = {
            "page": page,
            "pageSize": page_size
        }
        
        return self._do_request('GET', url, params=params)
    
    def remove_company_from_portfolio(self, portfolio_id, connect_id):
        """
        Rimuove azienda dal portfolio.
        
        Args:
            portfolio_id: ID portfolio
            connect_id: ConnectId Creditsafe
            
        Returns:
            bool: True se rimossa con successo
        """
        url = f"{API_BASE_URL}/monitoring/portfolios/{portfolio_id}/companies/{connect_id}"
        
        try:
            self._do_request('DELETE', url, expect_json=False)
            logger.info(f"Azienda rimossa dal portfolio: {connect_id}")
            return True
        except Exception as e:
            logger.error(f"Errore rimozione {connect_id}: {e}")
            return False
    
    # ==========================================================================
    # EVENT RULES (REGOLE NOTIFICA)
    # ==========================================================================
    
    def get_available_rules(self, country_code="IT"):
        """
        Ottiene regole disponibili per paese.
        
        Args:
            country_code: Codice paese (IT, XX per globali)
            
        Returns:
            list: Regole disponibili
        """
        url = f"{API_BASE_URL}/monitoring/eventRules/{country_code}"
        return self._do_request('GET', url)
    
    def get_portfolio_rules(self, portfolio_id):
        """
        Ottiene regole attive su un portfolio.
        
        Args:
            portfolio_id: ID portfolio
            
        Returns:
            list: Regole attive
        """
        url = f"{API_BASE_URL}/monitoring/portfolios/{portfolio_id}/eventRules"
        return self._do_request('GET', url)
    
    def set_portfolio_rules(self, portfolio_id, country_code, rules):
        """
        Attiva regole di notifica su portfolio.
        
        Args:
            portfolio_id: ID portfolio
            country_code: Codice paese (IT, XX)
            rules: Lista regole, es:
                [
                    {"ruleCode": 1801, "isActive": 1, "param0": "15"},
                    {"ruleCode": 3054, "isActive": 1}
                ]
                
        Returns:
            dict: Risposta API
        """
        url = f"{API_BASE_URL}/monitoring/portfolios/{portfolio_id}/eventRules/{country_code}"
        data = self._do_request('PUT', url, json=rules)
        logger.info(f"Regole aggiornate per portfolio {portfolio_id}, paese {country_code}: {len(rules)} regole")
        return data
    
    # ==========================================================================
    # NOTIFICATION EVENTS (ALERT)
    # ==========================================================================
    
    def get_notification_events(self, portfolio_id=None, page=1, page_size=50,
                                 is_processed=None, sort_order="desc"):
        """
        Recupera notifiche generate.
        
        Args:
            portfolio_id: Filtro portfolio (opzionale)
            page: Pagina
            page_size: Dimensione pagina
            is_processed: Filtro processati (True/False/None)
            sort_order: Ordinamento (asc/desc)
            
        Returns:
            dict: Risposta con notificationEvents e totalCount
        """
        url = f"{API_BASE_URL}/monitoring/notificationEvents"
        params = {
            "page": page,
            "pageSize": page_size,
            "sortOrder": sort_order
        }
        
        if portfolio_id:
            params["portfolioId"] = portfolio_id
        
        if is_processed is not None:
            params["isProcessed"] = str(is_processed).lower()
        
        return self._do_request('GET', url, params=params)
    
    def get_all_notification_events(self, portfolio_id=None, is_processed=None):
        """
        Recupera TUTTE le notifiche (paginazione automatica).
        
        Args:
            portfolio_id: Filtro portfolio (opzionale)
            is_processed: Filtro processati (opzionale)
            
        Returns:
            list: Tutti gli eventi
        """
        all_events = []
        page = 1
        page_size = 50
        
        while True:
            data = self.get_notification_events(
                portfolio_id=portfolio_id,
                page=page,
                page_size=page_size,
                is_processed=is_processed
            )
            
            events = data.get('notificationEvents', [])
            all_events.extend(events)
            
            total = data.get('totalCount', 0)
            
            if len(all_events) >= total or not events:
                break
            
            page += 1
        
        logger.info(f"Recuperati {len(all_events)} eventi totali")
        return all_events
    
    def mark_event_processed(self, event_id):
        """
        Marca notifica come elaborata.
        
        Args:
            event_id: ID evento
            
        Returns:
            dict: Risposta API
        """
        url = f"{API_BASE_URL}/monitoring/notificationEvents/{event_id}"
        payload = {"isProcessed": True}
        
        data = self._do_request('PATCH', url, json=payload)
        logger.debug(f"Evento {event_id} marcato come processato")
        return data
    
    def get_company_events(self, connect_id):
        """
        Ottiene storico eventi per azienda specifica.
        
        Args:
            connect_id: ConnectId Creditsafe
            
        Returns:
            dict: Risposta con eventi
        """
        url = f"{API_BASE_URL}/monitoring/companies/{connect_id}/events"
        return self._do_request('GET', url)
    
    # ==========================================================================
    # HTTP ENGINE (con rate limiting + retry)
    # ==========================================================================
    
    def _rate_limit(self):
        """Applica rate limiting tra richieste."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()
    
    def _do_request(self, method, url, params=None, json=None,
                     auth_required=True, expect_json=True):
        """
        Esegue richiesta HTTP con rate limiting e retry.
        
        Args:
            method: GET, POST, PUT, PATCH, DELETE
            url: URL completo
            params: Query parameters
            json: Body JSON
            auth_required: Se includere token Authorization
            expect_json: Se aspettarsi risposta JSON
            
        Returns:
            dict|str: Risposta API
            
        Raises:
            requests.exceptions.HTTPError: su errori non recuperabili
        """
        headers = self._get_headers() if auth_required else {"Content-Type": "application/json"}
        
        last_error = None
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._rate_limit()
                
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=30
                )
                
                # Token scaduto? Rinnova e riprova
                if response.status_code == 401 and auth_required and attempt == 1:
                    logger.warning("Token scaduto, rinnovo...")
                    self.authenticate(force=True)
                    headers = self._get_headers()
                    continue
                
                response.raise_for_status()
                
                if expect_json and response.text:
                    return response.json()
                elif response.status_code == 204:
                    return {}
                else:
                    return response.text
                    
            except requests.exceptions.HTTPError as e:
                last_error = e
                status = e.response.status_code if e.response is not None else 0
                
                # Errori non recuperabili: non ritentare
                if status in (400, 401, 403, 404, 409, 422):
                    logger.error(f"Errore {status} su {method} {url}: {e}")
                    try:
                        error_body = e.response.json()
                        logger.error(f"  Dettaglio: {error_body}")
                    except Exception:
                        pass
                    raise
                
                # Errori temporanei: ritenta con backoff
                wait = RETRY_BACKOFF * attempt
                logger.warning(f"Tentativo {attempt}/{MAX_RETRIES} fallito ({status}), riprovo tra {wait}s...")
                time.sleep(wait)
                
            except requests.exceptions.ConnectionError as e:
                last_error = e
                wait = RETRY_BACKOFF * attempt
                logger.warning(f"Errore connessione, tentativo {attempt}/{MAX_RETRIES}, riprovo tra {wait}s...")
                time.sleep(wait)
                
            except requests.exceptions.Timeout as e:
                last_error = e
                wait = RETRY_BACKOFF * attempt
                logger.warning(f"Timeout, tentativo {attempt}/{MAX_RETRIES}, riprovo tra {wait}s...")
                time.sleep(wait)
        
        # Tutti i tentativi falliti
        logger.error(f"Tutti i {MAX_RETRIES} tentativi falliti per {method} {url}")
        if last_error:
            raise last_error
        raise requests.exceptions.ConnectionError(f"Impossibile completare {method} {url}")


# ==============================================================================
# FUNZIONE HELPER STANDALONE
# ==============================================================================

def get_api_client(base_dir=None):
    """
    Crea e autentica un client API.
    Comodo per uso da script.
    
    Args:
        base_dir: Path base gestione_flotta
        
    Returns:
        CreditsafeAPI: Client autenticato
    """
    api = CreditsafeAPI(base_dir=base_dir)
    api.authenticate()
    return api
