# -*- coding: utf-8 -*-
"""
==============================================================================
GESTIONE FLOTTA - Modulo Google Calendar
==============================================================================
Versione: 1.0.0
Data: 2026-01-29
Descrizione: Integrazione con Google Calendar API per gestione appuntamenti
             Top Prospect

Funzionalita':
    - Creazione eventi con colore commerciale
    - Lettura eventi per banner
    - Modifica/eliminazione eventi
    - Gestione colori per commerciali

Colori Google Calendar disponibili:
    1=Lavanda, 2=Salvia, 3=Uva, 4=Fenicottero, 5=Banana,
    6=Mandarino, 7=Pavone, 9=Mirtillo, 10=Basilico, 11=Pomodoro
    (8=Grafite escluso)
==============================================================================
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Google API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# Percorso credenziali (relativo alla root del progetto)
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'impostazioni', 'google_calendar', 'br-car-service-flotta-088acae78b97.json'
)

# ID del calendario Top Prospect
CALENDAR_ID = '7806334aca7c899c0698b22288a42a45ba8d461863f5eef5a9d97f290d52aced@group.calendar.google.com'

# Scope necessari per l'API
SCOPES = ['https://www.googleapis.com/auth/calendar']

# ==============================================================================
# COLORI GOOGLE CALENDAR
# ==============================================================================

# Mappa colori disponibili (ID Google -> info)
# Escluso 8 (Grafite) come richiesto
COLORI_CALENDARIO = {
    1:  {'nome': 'Lavanda',     'hex': '#7986cb', 'disponibile': True},
    2:  {'nome': 'Salvia',      'hex': '#33b679', 'disponibile': True},
    3:  {'nome': 'Uva',         'hex': '#8e24aa', 'disponibile': True},
    4:  {'nome': 'Fenicottero', 'hex': '#e67c73', 'disponibile': True},
    5:  {'nome': 'Banana',      'hex': '#f6bf26', 'disponibile': True},   # Cristian
    6:  {'nome': 'Mandarino',   'hex': '#f4511e', 'disponibile': True},
    7:  {'nome': 'Pavone',      'hex': '#039be5', 'disponibile': True},   # Michele
    9:  {'nome': 'Mirtillo',    'hex': '#3f51b5', 'disponibile': True},
    10: {'nome': 'Basilico',    'hex': '#0b8043', 'disponibile': True},   # Fausto
    11: {'nome': 'Pomodoro',    'hex': '#d50000', 'disponibile': True},   # Paolo
}

# Assegnazioni iniziali commerciali (user_id -> color_id)
COLORI_INIZIALI_COMMERCIALI = {
    # Questi verranno settati nella migrazione DB
    # Michele = 7 (Pavone/Blu)
    # Paolo = 11 (Pomodoro/Rosso)
    # Cristian = 5 (Banana/Giallo)
    # Fausto = 10 (Basilico/Verde)
}

# Colore di default per nuovi commerciali (cicla tra i disponibili)
COLORE_DEFAULT = 1  # Lavanda


# ==============================================================================
# CLASSE PRINCIPALE
# ==============================================================================

class GoogleCalendarService:
    """
    Servizio per interagire con Google Calendar API.
    """
    
    def __init__(self):
        """Inizializza il servizio Google Calendar."""
        self._service = None
        self._credentials = None
    
    def _get_credentials(self):
        """Carica le credenziali dal file JSON."""
        if self._credentials is None:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"File credenziali non trovato: {CREDENTIALS_PATH}"
                )
            self._credentials = service_account.Credentials.from_service_account_file(
                CREDENTIALS_PATH, scopes=SCOPES
            )
        return self._credentials
    
    def _get_service(self):
        """Ottiene il servizio Calendar API (singleton)."""
        if self._service is None:
            credentials = self._get_credentials()
            self._service = build('calendar', 'v3', credentials=credentials)
        return self._service
    
    # ==========================================================================
    # GESTIONE EVENTI
    # ==========================================================================
    
    def crea_evento(
        self,
        titolo: str,
        data: str,
        ora_inizio: str = '09:00',
        ora_fine: str = '10:00',
        descrizione: str = '',
        colore_id: int = COLORE_DEFAULT,
        location: str = ''
    ) -> Optional[Dict]:
        """
        Crea un nuovo evento sul calendario.
        
        Args:
            titolo: Titolo dell'evento (es. nome azienda)
            data: Data in formato 'YYYY-MM-DD'
            ora_inizio: Ora inizio in formato 'HH:MM'
            ora_fine: Ora fine in formato 'HH:MM'
            descrizione: Descrizione/note dell'evento
            colore_id: ID colore Google Calendar (1-11, escluso 8)
            location: Luogo dell'appuntamento
            
        Returns:
            Dict con i dati dell'evento creato, o None se errore
        """
        try:
            service = self._get_service()
            
            # Costruisci datetime
            start_datetime = f"{data}T{ora_inizio}:00"
            end_datetime = f"{data}T{ora_fine}:00"
            
            # Valida colore
            if colore_id not in COLORI_CALENDARIO:
                colore_id = COLORE_DEFAULT
            
            event = {
                'summary': titolo,
                'description': descrizione,
                'location': location,
                'start': {
                    'dateTime': start_datetime,
                    'timeZone': 'Europe/Rome',
                },
                'end': {
                    'dateTime': end_datetime,
                    'timeZone': 'Europe/Rome',
                },
                'colorId': str(colore_id),
            }
            
            result = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event
            ).execute()
            
            return {
                'id': result.get('id'),
                'titolo': result.get('summary'),
                'link': result.get('htmlLink'),
                'data_inizio': result.get('start', {}).get('dateTime'),
                'data_fine': result.get('end', {}).get('dateTime'),
            }
            
        except HttpError as e:
            print(f"Errore Google Calendar API: {e}")
            return None
        except Exception as e:
            print(f"Errore creazione evento: {e}")
            return None
    
    def modifica_evento(
        self,
        event_id: str,
        titolo: str = None,
        data: str = None,
        ora_inizio: str = None,
        ora_fine: str = None,
        descrizione: str = None,
        colore_id: int = None,
        location: str = None
    ) -> Optional[Dict]:
        """
        Modifica un evento esistente.
        
        Args:
            event_id: ID dell'evento Google Calendar
            Altri parametri: solo quelli da modificare
            
        Returns:
            Dict con i dati aggiornati, o None se errore
        """
        try:
            service = self._get_service()
            
            # Recupera evento esistente
            event = service.events().get(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            
            # Aggiorna solo i campi forniti
            if titolo is not None:
                event['summary'] = titolo
            if descrizione is not None:
                event['description'] = descrizione
            if location is not None:
                event['location'] = location
            if colore_id is not None and colore_id in COLORI_CALENDARIO:
                event['colorId'] = str(colore_id)
            
            # Aggiorna data/ora se fornite
            if data is not None or ora_inizio is not None:
                # Estrai data/ora esistenti
                existing_start = event.get('start', {}).get('dateTime', '')
                existing_date = existing_start[:10] if existing_start else datetime.now().strftime('%Y-%m-%d')
                existing_time = existing_start[11:16] if len(existing_start) > 16 else '09:00'
                
                new_date = data if data else existing_date
                new_time = ora_inizio if ora_inizio else existing_time
                
                event['start'] = {
                    'dateTime': f"{new_date}T{new_time}:00",
                    'timeZone': 'Europe/Rome',
                }
            
            if data is not None or ora_fine is not None:
                existing_end = event.get('end', {}).get('dateTime', '')
                existing_date = existing_end[:10] if existing_end else datetime.now().strftime('%Y-%m-%d')
                existing_time = existing_end[11:16] if len(existing_end) > 16 else '10:00'
                
                new_date = data if data else existing_date
                new_time = ora_fine if ora_fine else existing_time
                
                event['end'] = {
                    'dateTime': f"{new_date}T{new_time}:00",
                    'timeZone': 'Europe/Rome',
                }
            
            result = service.events().update(
                calendarId=CALENDAR_ID,
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                'id': result.get('id'),
                'titolo': result.get('summary'),
                'link': result.get('htmlLink'),
            }
            
        except HttpError as e:
            print(f"Errore modifica evento: {e}")
            return None
        except Exception as e:
            print(f"Errore generico modifica: {e}")
            return None
    
    def elimina_evento(self, event_id: str) -> bool:
        """
        Elimina un evento dal calendario.
        
        Args:
            event_id: ID dell'evento Google Calendar
            
        Returns:
            True se eliminato, False se errore
        """
        try:
            service = self._get_service()
            service.events().delete(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            return True
        except HttpError as e:
            print(f"Errore eliminazione evento: {e}")
            return False
        except Exception as e:
            print(f"Errore generico eliminazione: {e}")
            return False
    
    def get_eventi(
        self,
        data_inizio: str = None,
        data_fine: str = None,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Recupera gli eventi dal calendario.
        
        Args:
            data_inizio: Data inizio ricerca (default: oggi)
            data_fine: Data fine ricerca (default: +28 giorni)
            max_results: Numero massimo risultati
            
        Returns:
            Lista di eventi con info principali
        """
        try:
            service = self._get_service()
            
            # Default: da oggi a +28 giorni
            if data_inizio is None:
                data_inizio = datetime.now().strftime('%Y-%m-%d')
            if data_fine is None:
                data_fine = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
            
            time_min = f"{data_inizio}T00:00:00Z"
            time_max = f"{data_fine}T23:59:59Z"
            
            result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            eventi = []
            for event in result.get('items', []):
                start = event.get('start', {})
                start_datetime = start.get('dateTime', start.get('date', ''))
                
                # Estrai data e ora
                if 'T' in start_datetime:
                    data = start_datetime[:10]
                    ora = start_datetime[11:16]
                else:
                    data = start_datetime
                    ora = ''
                
                eventi.append({
                    'id': event.get('id'),
                    'titolo': event.get('summary', ''),
                    'descrizione': event.get('description', ''),
                    'data': data,
                    'ora': ora,
                    'colore_id': int(event.get('colorId', 0)) if event.get('colorId') else None,
                    'location': event.get('location', ''),
                    'link': event.get('htmlLink', ''),
                })
            
            return eventi
            
        except HttpError as e:
            print(f"Errore lettura eventi: {e}")
            return []
        except Exception as e:
            print(f"Errore generico lettura: {e}")
            return []
    
    def test_connessione(self) -> Dict:
        """
        Testa la connessione al calendario.
        
        Returns:
            Dict con stato connessione e info calendario
        """
        try:
            service = self._get_service()
            
            # Prova a leggere info calendario
            calendar = service.calendars().get(calendarId=CALENDAR_ID).execute()
            
            return {
                'success': True,
                'nome_calendario': calendar.get('summary', ''),
                'descrizione': calendar.get('description', ''),
                'timezone': calendar.get('timeZone', ''),
            }
            
        except HttpError as e:
            return {
                'success': False,
                'errore': f"Errore API: {e}",
            }
        except FileNotFoundError as e:
            return {
                'success': False,
                'errore': f"Credenziali non trovate: {e}",
            }
        except Exception as e:
            return {
                'success': False,
                'errore': f"Errore generico: {e}",
            }
    
    def condividi_calendario(self, email: str, ruolo: str = 'reader') -> Dict:
        """
        Condivide il calendario con un altro account Google.
        
        Args:
            email: Email dell'account da aggiungere
            ruolo: Livello di accesso:
                   - 'reader' = puo' solo vedere
                   - 'writer' = puo' modificare eventi
                   - 'owner' = proprietario (sconsigliato)
            
        Returns:
            Dict con esito operazione
        """
        try:
            service = self._get_service()
            
            # Valida ruolo
            ruoli_validi = ['reader', 'writer']
            if ruolo not in ruoli_validi:
                ruolo = 'reader'
            
            # Crea regola ACL
            rule = {
                'scope': {
                    'type': 'user',
                    'value': email
                },
                'role': ruolo
            }
            
            result = service.acl().insert(
                calendarId=CALENDAR_ID,
                body=rule
            ).execute()
            
            return {
                'success': True,
                'email': email,
                'ruolo': ruolo,
                'id': result.get('id')
            }
            
        except HttpError as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower():
                return {
                    'success': False,
                    'errore': f"L'utente {email} ha gia' accesso al calendario"
                }
            return {
                'success': False,
                'errore': f"Errore API: {e}"
            }
        except Exception as e:
            return {
                'success': False,
                'errore': f"Errore: {e}"
            }
    
    def rimuovi_condivisione(self, email: str) -> Dict:
        """
        Rimuove l'accesso al calendario per un account.
        
        Args:
            email: Email dell'account da rimuovere
            
        Returns:
            Dict con esito operazione
        """
        try:
            service = self._get_service()
            
            rule_id = f"user:{email}"
            
            service.acl().delete(
                calendarId=CALENDAR_ID,
                ruleId=rule_id
            ).execute()
            
            return {
                'success': True,
                'email': email,
                'messaggio': 'Accesso rimosso'
            }
            
        except HttpError as e:
            return {
                'success': False,
                'errore': f"Errore API: {e}"
            }
        except Exception as e:
            return {
                'success': False,
                'errore': f"Errore: {e}"
            }
    
    def lista_condivisioni(self) -> Dict:
        """
        Elenca tutti gli account che hanno accesso al calendario.
        
        Returns:
            Dict con lista utenti e loro ruoli
        """
        try:
            service = self._get_service()
            
            result = service.acl().list(calendarId=CALENDAR_ID).execute()
            
            utenti = []
            for rule in result.get('items', []):
                scope = rule.get('scope', {})
                if scope.get('type') == 'user':
                    utenti.append({
                        'email': scope.get('value'),
                        'ruolo': rule.get('role'),
                        'id': rule.get('id')
                    })
            
            return {
                'success': True,
                'utenti': utenti
            }
            
        except HttpError as e:
            return {
                'success': False,
                'errore': f"Errore API: {e}"
            }
        except Exception as e:
            return {
                'success': False,
                'errore': f"Errore: {e}"
            }


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def get_colori_disponibili() -> Dict:
    """Restituisce la mappa dei colori disponibili."""
    return COLORI_CALENDARIO.copy()


def get_nome_colore(colore_id: int) -> str:
    """Restituisce il nome del colore dato l'ID."""
    if colore_id in COLORI_CALENDARIO:
        return COLORI_CALENDARIO[colore_id]['nome']
    return 'Sconosciuto'


def get_hex_colore(colore_id: int) -> str:
    """Restituisce il codice hex del colore dato l'ID."""
    if colore_id in COLORI_CALENDARIO:
        return COLORI_CALENDARIO[colore_id]['hex']
    return '#666666'


def assegna_colore_automatico(colori_usati: List[int]) -> int:
    """
    Assegna automaticamente un colore non ancora usato.
    Se tutti usati, ritorna il primo disponibile.
    
    Args:
        colori_usati: Lista degli ID colore gia' assegnati
        
    Returns:
        ID del colore da assegnare
    """
    for colore_id in COLORI_CALENDARIO.keys():
        if colore_id not in colori_usati:
            return colore_id
    # Tutti usati, ritorna il primo
    return list(COLORI_CALENDARIO.keys())[0]


# ==============================================================================
# SINGLETON GLOBALE
# ==============================================================================

_calendar_service = None

def get_calendar_service() -> GoogleCalendarService:
    """Restituisce l'istanza singleton del servizio calendario."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
    return _calendar_service


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == '__main__':
    print("Test connessione Google Calendar...")
    service = get_calendar_service()
    result = service.test_connessione()
    
    if result['success']:
        print(f"Connessione OK!")
        print(f"  Calendario: {result['nome_calendario']}")
        print(f"  Timezone: {result['timezone']}")
        
        print("\nEventi prossimi 28 giorni:")
        eventi = service.get_eventi()
        if eventi:
            for e in eventi:
                print(f"  - {e['data']} {e['ora']}: {e['titolo']}")
        else:
            print("  Nessun evento")
    else:
        print(f"Errore connessione: {result['errore']}")
