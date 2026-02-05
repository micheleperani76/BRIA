#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Configurazione Trascrizione Audio
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-03
# Descrizione: Legge impostazioni/trascrizione.conf e espone costanti
# ==============================================================================

from pathlib import Path

# ==============================================================================
# PERCORSI BASE
# ==============================================================================

BASE_DIR = Path(__file__).parent.parent.absolute()
CONF_FILE = BASE_DIR / "impostazioni" / "trascrizione.conf"


# ==============================================================================
# LETTURA CONFIGURAZIONE
# ==============================================================================

def _leggi_conf():
    """
    Legge trascrizione.conf e ritorna dizionario chiave=valore.
    Converte automaticamente i tipi (int, float, bool, lista).
    """
    config = {}
    
    if not CONF_FILE.exists():
        print(f"ATTENZIONE: File {CONF_FILE} non trovato, uso valori default")
        return config
    
    with open(CONF_FILE, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            if '=' in linea:
                chiave, valore = linea.split('=', 1)
                chiave = chiave.strip()
                valore = valore.strip()
                
                # Conversione automatica tipi
                if valore.lower() in ('true', 'si', 'yes'):
                    config[chiave] = True
                elif valore.lower() in ('false', 'no'):
                    config[chiave] = False
                elif ',' in valore:
                    # Lista separata da virgola
                    config[chiave] = [v.strip() for v in valore.split(',')]
                else:
                    # Prova int, poi float, poi stringa
                    try:
                        config[chiave] = int(valore)
                    except ValueError:
                        try:
                            config[chiave] = float(valore)
                        except ValueError:
                            config[chiave] = valore
    
    return config


# ==============================================================================
# CARICAMENTO CONFIGURAZIONE
# ==============================================================================

_CONF = _leggi_conf()

# --- Modelli ---
MODELLO = _CONF.get('MODELLO', 'large-v3')
MODELLO_VELOCE = _CONF.get('MODELLO_VELOCE', 'large-v3-turbo')
LINGUA_DEFAULT = _CONF.get('LINGUA_DEFAULT', 'it')
DEVICE = _CONF.get('DEVICE', 'cpu')
COMPUTE_TYPE = _CONF.get('COMPUTE_TYPE', 'int8')

# --- Orari ---
ORARIO_INIZIO = _CONF.get('ORARIO_INIZIO', 7)
ORARIO_STOP = _CONF.get('ORARIO_STOP', 4)

# --- Soglie ---
SOGLIA_GRANDE_MB = _CONF.get('SOGLIA_GRANDE_MB', 150)
SOGLIA_GRANDE_BYTES = SOGLIA_GRANDE_MB * 1024 * 1024
MAX_UPLOAD_MB = _CONF.get('MAX_UPLOAD_MB', 500)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
SOGLIA_CODA_TURBO = _CONF.get('SOGLIA_CODA_TURBO', 3)

# --- Retention ---
RETENTION_AUDIO_GIORNI = _CONF.get('RETENTION_AUDIO_GIORNI', 180)
RETENTION_CONSUMO_GIORNI = _CONF.get('RETENTION_CONSUMO_GIORNI', 21)

# --- Formati ---
FORMATI_AUDIO = _CONF.get('FORMATI_AUDIO', 
    ['aac', 'mp3', 'm4a', 'wav', 'ogg', 'opus', 'wma', 'flac', 'amr', 'webm', '3gp', 'mp4', 'caf'])
if isinstance(FORMATI_AUDIO, str):
    FORMATI_AUDIO = [f.strip() for f in FORMATI_AUDIO.split(',')]

# --- Worker ---
POLLING_SECONDI = _CONF.get('POLLING_SECONDI', 30)
NUM_THREADS = int(_CONF.get('NUM_THREADS', 4))
AGGIORNAMENTO_PROGRESSO = _CONF.get('AGGIORNAMENTO_PROGRESSO', 15)

# --- Fix sistema ---
LD_PRELOAD = _CONF.get('LD_PRELOAD', '/usr/lib/x86_64-linux-gnu/libgomp.so.1')

# --- Cartelle ---
TRASCRIZIONE_DIR = BASE_DIR / "trascrizione"
DIR_ATTESA = TRASCRIZIONE_DIR / "attesa"
DIR_LAVORAZIONE = TRASCRIZIONE_DIR / "lavorazione"
DIR_COMPLETATI = TRASCRIZIONE_DIR / "completati"
DIR_TESTI = TRASCRIZIONE_DIR / "testi"
DIR_CONSUMO = TRASCRIZIONE_DIR / "consumo"

# Database
DB_FILE = BASE_DIR / "db" / "gestionale.db"


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def get_dir_consumo_utente(codice_utente):
    """
    Ritorna il path della cartella consumo per un utente.
    Crea la struttura se non esiste.
    
    Args:
        codice_utente: Codice utente a 6 cifre (es. '000001')
    
    Returns:
        Path: es. trascrizione/consumo/000001/
    """
    user_dir = DIR_CONSUMO / str(codice_utente)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_dir_consumo_data(codice_utente, data=None):
    """
    Ritorna il path della sottocartella data per un utente.
    
    Args:
        codice_utente: Codice utente a 6 cifre
        data: datetime o None (default: oggi)
    
    Returns:
        Path: es. trascrizione/consumo/000001/03-02-2026/
    """
    from datetime import datetime as dt
    if data is None:
        data = dt.now()
    
    data_str = data.strftime('%d-%m-%Y')
    data_dir = get_dir_consumo_utente(codice_utente) / data_str
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def is_formato_valido(nome_file):
    """
    Verifica se il formato del file audio e' accettato.
    
    Args:
        nome_file: Nome del file (es. 'registrazione.aac')
    
    Returns:
        bool: True se il formato e' valido
    """
    estensione = Path(nome_file).suffix.lower().lstrip('.')
    return estensione in FORMATI_AUDIO


def get_estensione(nome_file):
    """Ritorna l'estensione senza punto, minuscolo."""
    return Path(nome_file).suffix.lower().lstrip('.')


def is_orario_accettazione():
    """
    Verifica se siamo nell'orario di accettazione file.
    
    Orario accettazione: ORARIO_INIZIO (7) - ORARIO_STOP_ACCETTAZIONE (19)
    L'accettazione si ferma alle 19, l'elaborazione va fino a ORARIO_STOP (4).
    
    Returns:
        bool: True se si accettano file
    """
    from datetime import datetime as dt
    ora = dt.now().hour
    # Accettazione: dalle 7 alle 19
    return 7 <= ora < 19


def is_orario_elaborazione():
    """
    Verifica se siamo nell'orario di elaborazione.
    
    Elaborazione: ORARIO_INIZIO (7) - ORARIO_STOP (4)
    Cioe' dalle 7:00 alle 4:00 del giorno dopo.
    
    Returns:
        bool: True se si puo' elaborare
    """
    from datetime import datetime as dt
    ora = dt.now().hour
    
    if ORARIO_INIZIO <= ORARIO_STOP:
        # Caso semplice (es. 7-20)
        return ORARIO_INIZIO <= ora < ORARIO_STOP
    else:
        # Caso che attraversa mezzanotte (es. 7-4)
        return ora >= ORARIO_INIZIO or ora < ORARIO_STOP


def stima_tempo_trascrizione(durata_secondi, modello=None):
    """
    Stima il tempo di trascrizione in secondi.
    Approssimativo: durata_audio * fattore.
    
    Args:
        durata_secondi: Durata audio in secondi
        modello: Nome modello (default: MODELLO)
    
    Returns:
        int: Tempo stimato in secondi
    """
    if modello is None:
        modello = MODELLO
    
    if 'turbo' in modello:
        # Turbo e' circa 6x piu veloce
        fattore = 0.5
    else:
        # large-v3 su CPU int8: circa 3x il tempo reale
        fattore = 1.5
    
    return int(durata_secondi * fattore)


def inizializza_cartelle():
    """Crea tutte le cartelle necessarie per la trascrizione."""
    for d in [DIR_ATTESA, DIR_LAVORAZIONE, DIR_COMPLETATI, DIR_TESTI, DIR_CONSUMO]:
        d.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == '__main__':
    print("=== Configurazione Trascrizione ===")
    print(f"CONF_FILE:        {CONF_FILE}")
    print(f"MODELLO:          {MODELLO}")
    print(f"MODELLO_VELOCE:   {MODELLO_VELOCE}")
    print(f"LINGUA:           {LINGUA_DEFAULT}")
    print(f"DEVICE:           {DEVICE}")
    print(f"COMPUTE_TYPE:     {COMPUTE_TYPE}")
    print(f"ORARIO:           {ORARIO_INIZIO}:00 - {ORARIO_STOP}:00")
    print(f"SOGLIA_GRANDE:    {SOGLIA_GRANDE_MB} MB")
    print(f"MAX_UPLOAD:       {MAX_UPLOAD_MB} MB")
    print(f"RETENTION AUDIO:  {RETENTION_AUDIO_GIORNI} giorni")
    print(f"RETENTION CONSUMO:{RETENTION_CONSUMO_GIORNI} giorni")
    print(f"FORMATI:          {FORMATI_AUDIO}")
    print(f"LD_PRELOAD:       {LD_PRELOAD}")
    print()
    print("Cartelle:")
    for d in [DIR_ATTESA, DIR_LAVORAZIONE, DIR_COMPLETATI, DIR_TESTI, DIR_CONSUMO]:
        esiste = "OK" if d.exists() else "DA CREARE"
        print(f"  {d} [{esiste}]")
    print()
    print(f"Orario accettazione: {is_orario_accettazione()}")
    print(f"Orario elaborazione: {is_orario_elaborazione()}")
