#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Configurazione Centralizzata
# ==============================================================================
# Versione: 2.0.0
# Data: 2025-01-19
# Descrizione: Tutte le configurazioni del sistema in un unico posto
# Novità v2.0: Lettura percorsi da impostazioni/percorsi.conf
#              Nuova struttura cartelle clienti (clienti/CF/ e clienti/PIVA/)
# ==============================================================================

import os
from pathlib import Path

# ==============================================================================
# PERCORSI BASE
# ==============================================================================

# Cartella principale del programma
BASE_DIR = Path(__file__).parent.parent.absolute()

# File configurazione percorsi
PERCORSI_CONF = BASE_DIR / "impostazioni" / "percorsi.conf"


def _leggi_percorsi_conf():
    """
    Legge il file percorsi.conf e ritorna un dizionario con i path.
    Se il file non esiste, ritorna dizionario vuoto (usa default).
    """
    percorsi = {}
    
    if not PERCORSI_CONF.exists():
        return percorsi
    
    try:
        with open(PERCORSI_CONF, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith('#'):
                    continue
                if '=' in linea:
                    chiave, valore = linea.split('=', 1)
                    chiave = chiave.strip()
                    valore = valore.strip()
                    # Path assoluto o relativo
                    if valore.startswith('/'):
                        percorsi[chiave] = Path(valore)
                    else:
                        percorsi[chiave] = BASE_DIR / valore
    except Exception:
        pass
    
    return percorsi


# Carica percorsi da file conf
_PERCORSI = _leggi_percorsi_conf()

# Sottocartelle (da percorsi.conf o default)
DB_DIR = _PERCORSI.get('DB_DIR', BASE_DIR / "db")
PDF_DIR = _PERCORSI.get('PDF_DIR', BASE_DIR / "pdf")
PDF_ERRORI_DIR = _PERCORSI.get('PDF_ERRORI_DIR', BASE_DIR / "pdf_errori")
EXPORTS_DIR = _PERCORSI.get('EXPORTS_DIR', BASE_DIR / "exports")
CLIENTI_DIR = _PERCORSI.get('CLIENTI_DIR', BASE_DIR / "clienti")
LOGS_DIR = BASE_DIR / "logs"
TEMPLATES_DIR = BASE_DIR / "templates"
SCRIPTS_DIR = BASE_DIR / "scripts"
IMPOSTAZIONI_DIR = BASE_DIR / "impostazioni"

# Sottocartelle clienti
CLIENTI_CF_DIR = CLIENTI_DIR / "CF"
CLIENTI_PIVA_DIR = CLIENTI_DIR / "PIVA"

# DEPRECATO: Mantenuto per retrocompatibilità, verrà rimosso
STORICO_PDF_DIR = BASE_DIR / "storico_pdf"

# ==============================================================================
# DATABASE
# ==============================================================================

DB_FILE = DB_DIR / "gestionale.db"


# ==============================================================================
# FUNZIONI HELPER PATH CLIENTI
# ==============================================================================

def pulisci_piva(piva):
    """
    Pulisce una P.IVA rimuovendo prefisso IT e spazi.
    
    Args:
        piva: P.IVA nel formato DB (es: 'IT01234567890')
    
    Returns:
        str: P.IVA pulita (es: '01234567890') o None
    """
    if not piva:
        return None
    return piva.upper().replace('IT', '').replace(' ', '').strip() or None


def get_cliente_base_path(cliente):
    """
    Ritorna il path base della cartella cliente.
    
    Args:
        cliente: dict o sqlite3.Row con 'p_iva' e/o 'cod_fiscale'
    
    Returns:
        Path: es. Path('clienti/PIVA/04292180983')
    
    Raises:
        ValueError: Se il cliente non ha né P.IVA né CF
    """
    # Supporta sia dict che sqlite3.Row
    if hasattr(cliente, 'keys'):
        piva = cliente.get('p_iva')
        cf = cliente.get('cod_fiscale')
    else:
        piva = cliente['p_iva'] if 'p_iva' in cliente.keys() else None
        cf = cliente['cod_fiscale'] if 'cod_fiscale' in cliente.keys() else None
    
    if piva:
        ident = pulisci_piva(piva)
        if ident:
            return CLIENTI_PIVA_DIR / ident
    
    if cf:
        return CLIENTI_CF_DIR / cf.upper().strip()
    
    raise ValueError("Cliente senza P.IVA e senza CF non ammesso")


def get_cliente_allegati_path(cliente):
    """Ritorna path cartella allegati_note del cliente."""
    return get_cliente_base_path(cliente) / 'allegati_note'


def get_cliente_creditsafe_path(cliente):
    """Ritorna path cartella creditsafe del cliente."""
    return get_cliente_base_path(cliente) / 'creditsafe'


def ensure_cliente_folders(cliente, sottocartelle=None):
    """
    Crea tutte le cartelle standard per un cliente.
    
    Args:
        cliente: dict o sqlite3.Row con 'p_iva' e/o 'cod_fiscale'
        sottocartelle: lista sottocartelle da creare (default: allegati_note, creditsafe)
    
    Returns:
        Path: Il path base del cliente
    """
    if sottocartelle is None:
        sottocartelle = ['allegati_note', 'creditsafe']
    
    base = get_cliente_base_path(cliente)
    
    for subdir in sottocartelle:
        (base / subdir).mkdir(parents=True, exist_ok=True)
    
    return base

# ==============================================================================
# SERVER WEB
# ==============================================================================

WEB_HOST = "0.0.0.0"
WEB_PORT = 5001
WEB_DEBUG = True

# ==============================================================================
# LOGGING
# ==============================================================================

LOG_RETENTION_DAYS = 7  # Giorni di retention per i file di log
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==============================================================================
# IMPORT CREDITSAFE
# ==============================================================================

# Estensioni file accettate
PDF_EXTENSIONS = ['.pdf', '.PDF']

# Pattern per estrazione dati (compilati una volta sola)
import re

PATTERNS = {
    # Identificativi azienda
    'ragione_sociale': re.compile(r'Denominazione\s+(.+?)(?:\n|Indirizzo)', re.DOTALL),
    'numero_registrazione': re.compile(r'N\.\s*Reg\.\s*Imprese\s*[:\s]*([A-Z]{2}\d+)'),
    'partita_iva': re.compile(r'P\.?\s*IVA\s*[:\s]*(\d{11})'),
    'codice_fiscale': re.compile(r'C\.?\s*F\.?\s*[:\s]*(\d{11}|[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])'),
    
    # Indirizzo e contatti
    'indirizzo': re.compile(r'Indirizzo\s+(.+?)(?:\n\n|\nTelefono)', re.DOTALL),
    'telefono': re.compile(r'Telefono\s+([+\d\s\-]+)'),
    'pec': re.compile(r'PEC\s+([\w\.\-]+@[\w\.\-]+)'),
    
    # Dati societari
    'forma_giuridica': re.compile(r'Forma\s+Giuridica\s+(.+?)(?:\n|Data)'),
    'data_costituzione': re.compile(r'Data\s+di\s+costituzione\s+(\d{2}/\d{2}/\d{4})'),
    'capitale_sociale': re.compile(r'Capitale\s+sociale\s+[&euro;\s]*([\d.,]+)'),
    'dipendenti': re.compile(r'N\.\s*Dipendenti\s*[:\s]*(\d+)'),
    
    # Attivita
    'codice_ateco': re.compile(r'Codice\s+ATECO\s+2007\s+([\d.]+)'),
    'desc_ateco': re.compile(r'Codice\s+ATECO\s+2007\s+[\d.]+\s+(.+?)(?:\n|$)'),
    'desc_attivita': re.compile(r'Descrizione\s+attivita\s+(.+?)(?:\n\n|Codice)', re.DOTALL),
    
    # Capogruppo
    'capogruppo_nome': re.compile(r'Capogruppo\s+(.+?)(?:\n|P\.IVA)', re.DOTALL),
    'capogruppo_cf': re.compile(r'Capogruppo\s+.+?(?:P\.IVA|C\.F\.)\s*[:\s]*(\d{11}|[A-Z0-9]+)'),
    
    # Legale rappresentante
    'legale_rappresentante': re.compile(r'Legale\s+rappresentante\s+(.+?)(?:\n|Codice)', re.DOTALL),
    
    # Rating e rischio
    'score': re.compile(r'Valutazione\s+del\s+credito\s*[:\s]*([A-E])'),
    'punteggio_rischio': re.compile(r'Punteggio\s+di\s+rischio\s+(\d+)'),
    'credito': re.compile(r'Fido\s+consigliato\s+[&euro;\s]*([\d.,]+)'),
    'stato': re.compile(r'Stato\s+(.+?)(?:\n|$)'),
    
    # Protesti
    'protesti': re.compile(r'Protesti\s+(.+?)(?:\n|&euro;)'),
    'importo_protesti': re.compile(r'Protesti\s+.+?&euro;\s*([\d.,]+)'),
    
    # Bilancio - pattern multiriga migliorati
    'anni_bilancio': re.compile(r'Dati\s+finanziari\s+chiave\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})'),
    'anni_bilancio_alt': re.compile(r'31/12/(\d{4})\s+31/12/(\d{4})'),
}

# ==============================================================================
# PROVINCE E REGIONI ITALIANE
# ==============================================================================

PROVINCE_REGIONI = {
    # Abruzzo
    'AQ': 'Abruzzo', 'CH': 'Abruzzo', 'PE': 'Abruzzo', 'TE': 'Abruzzo',
    # Basilicata
    'MT': 'Basilicata', 'PZ': 'Basilicata',
    # Calabria
    'CS': 'Calabria', 'CZ': 'Calabria', 'KR': 'Calabria', 'RC': 'Calabria', 'VV': 'Calabria',
    # Campania
    'AV': 'Campania', 'BN': 'Campania', 'CE': 'Campania', 'NA': 'Campania', 'SA': 'Campania',
    # Emilia-Romagna
    'BO': 'Emilia-Romagna', 'FC': 'Emilia-Romagna', 'FE': 'Emilia-Romagna', 'MO': 'Emilia-Romagna',
    'PC': 'Emilia-Romagna', 'PR': 'Emilia-Romagna', 'RA': 'Emilia-Romagna', 'RE': 'Emilia-Romagna', 'RN': 'Emilia-Romagna',
    # Friuli-Venezia Giulia
    'GO': 'Friuli-Venezia Giulia', 'PN': 'Friuli-Venezia Giulia', 'TS': 'Friuli-Venezia Giulia', 'UD': 'Friuli-Venezia Giulia',
    # Lazio
    'FR': 'Lazio', 'LT': 'Lazio', 'RI': 'Lazio', 'RM': 'Lazio', 'VT': 'Lazio',
    # Liguria
    'GE': 'Liguria', 'IM': 'Liguria', 'SP': 'Liguria', 'SV': 'Liguria',
    # Lombardia
    'BG': 'Lombardia', 'BS': 'Lombardia', 'CO': 'Lombardia', 'CR': 'Lombardia', 'LC': 'Lombardia',
    'LO': 'Lombardia', 'MB': 'Lombardia', 'MI': 'Lombardia', 'MN': 'Lombardia', 'PV': 'Lombardia',
    'SO': 'Lombardia', 'VA': 'Lombardia',
    # Marche
    'AN': 'Marche', 'AP': 'Marche', 'FM': 'Marche', 'MC': 'Marche', 'PU': 'Marche',
    # Molise
    'CB': 'Molise', 'IS': 'Molise',
    # Piemonte
    'AL': 'Piemonte', 'AT': 'Piemonte', 'BI': 'Piemonte', 'CN': 'Piemonte', 'NO': 'Piemonte',
    'TO': 'Piemonte', 'VB': 'Piemonte', 'VC': 'Piemonte',
    # Puglia
    'BA': 'Puglia', 'BAT': 'Puglia', 'BR': 'Puglia', 'FG': 'Puglia', 'LE': 'Puglia', 'TA': 'Puglia',
    # Sardegna
    'CA': 'Sardegna', 'NU': 'Sardegna', 'OR': 'Sardegna', 'SS': 'Sardegna', 'SU': 'Sardegna',
    # Sicilia
    'AG': 'Sicilia', 'CL': 'Sicilia', 'CT': 'Sicilia', 'EN': 'Sicilia', 'ME': 'Sicilia',
    'PA': 'Sicilia', 'RG': 'Sicilia', 'SR': 'Sicilia', 'TP': 'Sicilia',
    # Toscana
    'AR': 'Toscana', 'FI': 'Toscana', 'GR': 'Toscana', 'LI': 'Toscana', 'LU': 'Toscana',
    'MS': 'Toscana', 'PI': 'Toscana', 'PO': 'Toscana', 'PT': 'Toscana', 'SI': 'Toscana',
    # Trentino-Alto Adige
    'BZ': 'Trentino-Alto Adige', 'TN': 'Trentino-Alto Adige',
    # Umbria
    'PG': 'Umbria', 'TR': 'Umbria',
    # Valle d'Aosta
    'AO': "Valle d'Aosta",
    # Veneto
    'BL': 'Veneto', 'PD': 'Veneto', 'RO': 'Veneto', 'TV': 'Veneto', 'VE': 'Veneto', 'VI': 'Veneto', 'VR': 'Veneto',
}

# Lista regioni per dropdown
REGIONI = sorted(set(PROVINCE_REGIONI.values()))

# ==============================================================================
# COLORI SCORE
# ==============================================================================

SCORE_COLORS = {
    'A': {'bg': 'success', 'text': 'Molto basso'},
    'B': {'bg': 'info', 'text': 'Basso'},
    'C': {'bg': 'warning', 'text': 'Medio'},
    'D': {'bg': 'danger', 'text': 'Alto'},
    'E': {'bg': 'dark', 'text': 'Molto alto'},
}

# ==============================================================================
# ALIMENTAZIONI VEICOLI (colori badge)
# ==============================================================================

ALIMENTAZIONI_COLORS = {
    'ELETTRICA': 'success',
    'IBRIDA': 'info',
    'METANO': 'primary',
    'GPL': 'secondary',
    'DIESEL': 'warning',
    'BENZINA': 'danger',
}
