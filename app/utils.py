#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Modulo Utilities
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-12
# Descrizione: Funzioni di utilità generali
# ==============================================================================

import os
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from .config import LOGS_DIR, LOG_RETENTION_DAYS, LOG_FORMAT, LOG_DATE_FORMAT, PROVINCE_REGIONI

# ==============================================================================
# LOGGING
# ==============================================================================

def setup_logger(nome, livello=logging.INFO):
    """
    Configura e ritorna un logger con output su file e console.
    I file di log vengono creati nella cartella logs/ con data nel nome.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    data_oggi = datetime.now().strftime('%Y-%m-%d')
    log_file = LOGS_DIR / f"{nome}_{data_oggi}.log"
    
    logger = logging.getLogger(nome)
    logger.setLevel(livello)
    
    # Evita duplicazione handlers
    if logger.handlers:
        return logger
    
    # Handler file
    fh = logging.FileHandler(str(log_file), encoding='utf-8')
    fh.setLevel(livello)
    fh.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(fh)
    
    # Handler console
    ch = logging.StreamHandler()
    ch.setLevel(livello)
    ch.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(ch)
    
    return logger


def pulisci_log_vecchi():
    """Rimuove i file di log più vecchi di LOG_RETENTION_DAYS giorni."""
    if not LOGS_DIR.exists():
        return 0
    
    data_limite = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    rimossi = 0
    
    for log_file in LOGS_DIR.glob('*.log'):
        try:
            # Estrai data dal nome file (formato: nome_YYYY-MM-DD.log)
            match = re.search(r'(\d{4}-\d{2}-\d{2})\.log$', log_file.name)
            if match:
                data_file = datetime.strptime(match.group(1), '%Y-%m-%d')
                if data_file < data_limite:
                    log_file.unlink()
                    rimossi += 1
        except Exception:
            pass
    
    return rimossi


# ==============================================================================
# CONVERSIONE NUMERI
# ==============================================================================

def pulisci_numero(valore):
    """
    Converte una stringa numerica italiana in float.
    Es: "1.234,56" -> 1234.56
    Es: "-1.234,56" -> -1234.56
    """
    if not valore:
        return None
    
    try:
        # Gestisce segno negativo
        negativo = '-' in str(valore)
        
        # Rimuove tutto tranne numeri, virgole e punti
        pulito = re.sub(r'[^\d.,]', '', str(valore))
        
        # Rimuove punti delle migliaia e converte virgola decimale
        pulito = pulito.replace('.', '').replace(',', '.')
        
        risultato = float(pulito)
        return -risultato if negativo else risultato
    except (ValueError, AttributeError):
        return None


def formatta_numero(valore, decimali=2):
    """
    Formatta un numero in stile italiano.
    Es: 1234.56 -> "1.234,56"
    """
    if valore is None:
        return "-"
    
    try:
        # Formatta con separatore migliaia
        if decimali == 0:
            formatted = f"{int(valore):,}".replace(",", ".")
        else:
            formatted = f"{valore:,.{decimali}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except (ValueError, TypeError):
        return str(valore)


def formatta_euro(valore):
    """Formatta un valore come Euro."""
    if valore is None:
        return "-"
    return f"&euro; {formatta_numero(valore)}"


# ==============================================================================
# ESTRAZIONE PROVINCE
# ==============================================================================

def estrai_provincia(indirizzo):
    """
    Estrae la sigla della provincia da un indirizzo.
    Cerca le ultime 2 lettere maiuscole che corrispondono a una provincia italiana.
    """
    if not indirizzo:
        return None
    
    # Pattern: cerca 2 lettere maiuscole alla fine o tra parentesi
    patterns = [
        r'\(([A-Z]{2})\)\s*$',           # (BS) alla fine
        r'\s([A-Z]{2})\s*$',              # BS alla fine
        r'\s([A-Z]{2})\s+\d{5}',          # BS 25100
        r',\s*([A-Z]{2})\s*[,\n]',        # , BS,
    ]
    
    for pattern in patterns:
        match = re.search(pattern, str(indirizzo).upper())
        if match:
            sigla = match.group(1)
            if sigla in PROVINCE_REGIONI:
                return sigla
    
    # Fallback: cerca qualsiasi sigla provincia nel testo
    for sigla in PROVINCE_REGIONI.keys():
        if re.search(rf'\b{sigla}\b', str(indirizzo).upper()):
            return sigla
    
    return None


def get_regione(provincia):
    """Ritorna la regione data una sigla provincia."""
    return PROVINCE_REGIONI.get(provincia)


# ==============================================================================
# GESTIONE FILE PDF
# ==============================================================================

def get_lettera_iniziale(nome_file):
    """
    Determina la cartella (lettera) in cui salvare un file.
    Basato sulla prima lettera del nome dell'azienda.
    """
    if not nome_file:
        return "0-9"
    
    # Estrai prima lettera significativa
    nome_pulito = re.sub(r'^[^a-zA-Z]*', '', nome_file)
    
    if nome_pulito:
        lettera = nome_pulito[0].upper()
        if lettera.isalpha():
            return lettera
    
    return "0-9"


def sposta_in_storico(file_origine, storico_dir):
    """
    Copia un file nella cartella storico organizzata per lettera.
    Ritorna il percorso di destinazione.
    """
    import shutil
    
    if not file_origine.exists():
        return None
    
    lettera = get_lettera_iniziale(file_origine.name)
    cartella_dest = storico_dir / lettera
    cartella_dest.mkdir(parents=True, exist_ok=True)
    
    dest_path = cartella_dest / file_origine.name
    
    # Se esiste già, aggiungi timestamp
    if dest_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_base = dest_path.stem
        ext = dest_path.suffix
        dest_path = cartella_dest / f"{nome_base}_{timestamp}{ext}"
    
    shutil.copy(str(file_origine), str(dest_path))
    return dest_path


# ==============================================================================
# VALIDAZIONE
# ==============================================================================

def valida_piva(piva):
    """Valida una Partita IVA italiana."""
    if not piva:
        return False
    
    # Rimuovi prefisso e spazi
    piva = str(piva).upper().replace('IT', '').replace(' ', '').strip()
    
    # Deve essere di 11 cifre
    if not re.match(r'^\d{11}$', piva):
        return False
    
    return True


def valida_cf(cf):
    """Valida un Codice Fiscale italiano (persona o società)."""
    if not cf:
        return False
    
    cf = str(cf).upper().replace(' ', '').strip()
    
    # CF numerico (società) - 11 cifre
    if re.match(r'^\d{11}$', cf):
        return True
    
    # CF alfanumerico (persona) - 16 caratteri
    if re.match(r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$', cf):
        return True
    
    return False


def valida_email(email):
    """Valida un indirizzo email/PEC."""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email)))


# ==============================================================================
# PULIZIA TESTO
# ==============================================================================

def pulisci_testo(testo):
    """Pulisce un testo rimuovendo spazi multipli e caratteri speciali."""
    if not testo:
        return None
    
    # Rimuove caratteri non stampabili
    testo = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(testo))
    
    # Sostituisce spazi multipli con uno singolo
    testo = re.sub(r'\s+', ' ', testo)
    
    # Strip
    testo = testo.strip()
    
    return testo if testo else None


def normalizza_nome_azienda(nome):
    """Normalizza il nome di un'azienda per confronti."""
    if not nome:
        return None
    
    nome = str(nome).upper()
    
    # Rimuove forme giuridiche comuni
    forme = ['S.R.L.', 'SRL', 'S.P.A.', 'SPA', 'S.N.C.', 'SNC', 
             'S.A.S.', 'SAS', 'S.S.', 'DI ', 'DI']
    
    for forma in forme:
        nome = nome.replace(forma, '')
    
    # Rimuove punteggiatura e spazi multipli
    nome = re.sub(r'[^\w\s]', '', nome)
    nome = re.sub(r'\s+', ' ', nome)
    
    return nome.strip()


# ==============================================================================
# DATE
# ==============================================================================

def parse_data(data_str, formati=None):
    """
    Tenta di parsare una data da vari formati.
    Ritorna un oggetto datetime o None.
    """
    if not data_str:
        return None
    
    if formati is None:
        formati = [
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d.%m.%Y',
            '%Y/%m/%d',
        ]
    
    for fmt in formati:
        try:
            return datetime.strptime(str(data_str).strip(), fmt)
        except ValueError:
            continue
    
    return None


def formatta_data(data, formato='%d/%m/%Y'):
    """Formatta una data nel formato specificato."""
    if not data:
        return "-"
    
    if isinstance(data, str):
        data = parse_data(data)
    
    if data:
        return data.strftime(formato)
    
    return "-"


def giorni_mancanti(data_scadenza):
    """Calcola i giorni mancanti a una scadenza."""
    if not data_scadenza:
        return None
    
    if isinstance(data_scadenza, str):
        data_scadenza = parse_data(data_scadenza)
    
    if not data_scadenza:
        return None
    
    oggi = datetime.now().date()
    if isinstance(data_scadenza, datetime):
        data_scadenza = data_scadenza.date()
    
    return (data_scadenza - oggi).days
