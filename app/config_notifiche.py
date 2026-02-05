#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
GESTIONE FLOTTA - Configurazione Sistema Notifiche
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: Legge impostazioni/notifiche.conf e categorie_notifiche.xlsx

File gestiti:
- impostazioni/notifiche.conf       (parametri hub)
- impostazioni/categorie_notifiche.xlsx  (categorie + livelli)

Uso:
    from app.config_notifiche import (
        # Parametri generali
        NOTIFICHE_ATTIVO, POLLING_SECONDI, MAX_NOTIFICHE_DROPDOWN,
        LIVELLO_MINIMO_CAMPANELLA, CAMPANELLA_ATTIVA,
        # Deduplicazione
        DEDUP_ATTIVA, DEDUP_FINESTRA_ORE,
        # Pulizia
        PULIZIA_LETTE_GIORNI, PULIZIA_NON_LETTE_GIORNI,
        # Funzioni categorie
        get_categorie, get_categoria, get_colore_categoria,
        get_icona_categoria, get_livelli,
        # Funzioni canali
        get_config_email_smtp, get_config_telegram,
        # Utility
        invalida_cache_notifiche
    )
==============================================================================
"""

import os
import pandas as pd
from pathlib import Path
from functools import lru_cache


# ==============================================================================
# PERCORSI BASE
# ==============================================================================

BASE_DIR = Path(__file__).parent.parent.absolute()
CONF_FILE = BASE_DIR / "impostazioni" / "notifiche.conf"
CATEGORIE_FILE = BASE_DIR / "impostazioni" / "categorie_notifiche.xlsx"


# ==============================================================================
# LETTURA FILE .CONF
# ==============================================================================

def _leggi_conf():
    """
    Legge notifiche.conf e ritorna dizionario chiave=valore.
    Converte automaticamente i tipi (int, float, bool, lista).
    """
    config = {}
    
    if not CONF_FILE.exists():
        print(f"[WARN] File {CONF_FILE} non trovato, uso valori default")
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
                elif valore == '':
                    config[chiave] = ''
                elif ',' in valore:
                    config[chiave] = [v.strip() for v in valore.split(',') if v.strip()]
                else:
                    try:
                        config[chiave] = int(valore)
                    except ValueError:
                        try:
                            config[chiave] = float(valore)
                        except ValueError:
                            config[chiave] = valore
    
    return config


# ==============================================================================
# LETTURA FILE EXCEL
# ==============================================================================

def _leggi_excel(filepath, foglio=0, colonne_richieste=None):
    """
    Legge un foglio Excel e restituisce lista di dizionari.
    """
    if not os.path.exists(filepath):
        print(f"[WARN] File non trovato: {filepath}")
        return []
    
    try:
        df = pd.read_excel(filepath, sheet_name=foglio)
        
        if colonne_richieste:
            mancanti = set(colonne_richieste) - set(df.columns)
            if mancanti:
                print(f"[WARN] Colonne mancanti in {filepath} foglio {foglio}: {mancanti}")
        
        if 'Ordine' in df.columns:
            df = df.sort_values('Ordine')
        
        return df.to_dict('records')
        
    except Exception as e:
        print(f"[ERRORE] Lettura {filepath} foglio {foglio}: {e}")
        return []


# ==============================================================================
# CARICAMENTO CONFIGURAZIONE
# ==============================================================================

_CONF = _leggi_conf()

# --- Parametri generali ---
NOTIFICHE_ATTIVO = _CONF.get('NOTIFICHE_ATTIVO', True)
LIVELLO_MINIMO_CAMPANELLA = _CONF.get('LIVELLO_MINIMO_CAMPANELLA', 1)
MAX_NOTIFICHE_DROPDOWN = _CONF.get('MAX_NOTIFICHE_DROPDOWN', 15)
NOTIFICHE_PER_PAGINA = _CONF.get('NOTIFICHE_PER_PAGINA', 50)
POLLING_SECONDI = _CONF.get('POLLING_SECONDI', 30)

# --- Deduplicazione ---
DEDUP_ATTIVA = _CONF.get('DEDUP_ATTIVA', True)
DEDUP_FINESTRA_ORE = _CONF.get('DEDUP_FINESTRA_ORE', 24)

# --- Pulizia automatica ---
PULIZIA_LETTE_GIORNI = _CONF.get('PULIZIA_LETTE_GIORNI', 90)
PULIZIA_NON_LETTE_GIORNI = _CONF.get('PULIZIA_NON_LETTE_GIORNI', 180)
PULIZIA_ARCHIVIATE_GIORNI = _CONF.get('PULIZIA_ARCHIVIATE_GIORNI', 30)

# --- Campanella ---
CAMPANELLA_ATTIVA = _CONF.get('CAMPANELLA_ATTIVA', True)
CAMPANELLA_BADGE = _CONF.get('CAMPANELLA_BADGE', True)
CAMPANELLA_SUONO = _CONF.get('CAMPANELLA_SUONO', False)

# --- Database ---
DB_FILE = BASE_DIR / "db" / "gestionale.db"


# ==============================================================================
# FUNZIONI CATEGORIE (da Excel)
# ==============================================================================

@lru_cache(maxsize=1)
def get_categorie():
    """
    Restituisce lista categorie notifiche con icone e colori.
    
    Returns:
        Lista di dict: [{'Codice': 'TASK', 'Etichetta': 'Task Interni', 
                         'Icona_Bootstrap': 'bi-list-task', 'Colore_Hex': '#0d6efd', ...}, ...]
    """
    return _leggi_excel(
        str(CATEGORIE_FILE), 
        foglio='Categorie',
        colonne_richieste=['Codice', 'Etichetta', 'Icona_Bootstrap', 'Colore_Hex']
    )


@lru_cache(maxsize=1)
def _mappa_categorie():
    """Cache interna: Codice -> dict completo"""
    return {c['Codice']: c for c in get_categorie() if 'Codice' in c}


def get_categoria(codice):
    """
    Restituisce il dict completo per una categoria.
    
    Args:
        codice: Codice categoria (es. 'TASK', 'SISTEMA')
    
    Returns:
        Dict o None se non trovata
    """
    return _mappa_categorie().get(codice)


def get_colore_categoria(codice):
    """
    Restituisce il colore esadecimale di una categoria.
    
    Args:
        codice: Codice categoria
    
    Returns:
        str: es. '#0d6efd', default '#6c757d'
    """
    cat = get_categoria(codice)
    return cat.get('Colore_Hex', '#6c757d') if cat else '#6c757d'


def get_icona_categoria(codice):
    """
    Restituisce la classe Bootstrap Icons di una categoria.
    
    Args:
        codice: Codice categoria
    
    Returns:
        str: es. 'bi-list-task', default 'bi-bell'
    """
    cat = get_categoria(codice)
    return cat.get('Icona_Bootstrap', 'bi-bell') if cat else 'bi-bell'


def get_etichetta_categoria(codice):
    """
    Restituisce l'etichetta leggibile di una categoria.
    
    Args:
        codice: Codice categoria
    
    Returns:
        str: es. 'Task Interni', default codice stesso
    """
    cat = get_categoria(codice)
    return cat.get('Etichetta', codice) if cat else codice


def get_categorie_codici():
    """
    Restituisce lista dei soli codici categoria.
    
    Returns:
        Lista: ['TASK', 'TRASCRIZIONE', 'SCADENZA_CONTRATTO', ...]
    """
    return [c['Codice'] for c in get_categorie() if 'Codice' in c]


# ==============================================================================
# FUNZIONI LIVELLI (da Excel foglio 2)
# ==============================================================================

@lru_cache(maxsize=1)
def get_livelli():
    """
    Restituisce lista livelli notifica.
    
    Returns:
        Lista di dict: [{'Codice_Numerico': 0, 'Nome': 'DEBUG', ...}, ...]
    """
    return _leggi_excel(
        str(CATEGORIE_FILE),
        foglio='Livelli',
        colonne_richieste=['Codice_Numerico', 'Nome', 'Colore_Hex']
    )


@lru_cache(maxsize=1)
def _mappa_livelli():
    """Cache interna: Codice_Numerico -> dict"""
    risultato = {}
    for liv in get_livelli():
        codice = liv.get('Codice_Numerico')
        if codice is not None:
            risultato[int(codice)] = liv
    return risultato


def get_livello(codice_numerico):
    """
    Restituisce il dict completo per un livello.
    
    Args:
        codice_numerico: 0, 1, 2 o 3
    
    Returns:
        Dict o None
    """
    return _mappa_livelli().get(int(codice_numerico))


def get_colore_livello(codice_numerico):
    """
    Restituisce il colore di un livello.
    
    Args:
        codice_numerico: 0, 1, 2 o 3
    
    Returns:
        str: es. '#dc3545', default '#0dcaf0'
    """
    liv = get_livello(codice_numerico)
    return liv.get('Colore_Hex', '#0dcaf0') if liv else '#0dcaf0'


def get_nome_livello(codice_numerico):
    """
    Restituisce il nome di un livello.
    
    Args:
        codice_numerico: 0, 1, 2 o 3
    
    Returns:
        str: es. 'ALLARME', default 'INFO'
    """
    liv = get_livello(codice_numerico)
    return liv.get('Nome', 'INFO') if liv else 'INFO'


def get_icona_livello(codice_numerico):
    """
    Restituisce icona Bootstrap di un livello.
    
    Args:
        codice_numerico: 0, 1, 2 o 3
    
    Returns:
        str: es. 'bi-exclamation-octagon'
    """
    liv = get_livello(codice_numerico)
    return liv.get('Icona_Bootstrap', 'bi-info-circle') if liv else 'bi-info-circle'


# ==============================================================================
# FUNZIONI CANALI USCITA (per fasi future)
# ==============================================================================

def get_config_email_smtp():
    """
    Restituisce configurazione canale email SMTP.
    Password letta dalla variabile d'ambiente indicata nel .conf.
    
    Returns:
        Dict con parametri SMTP o None se non attivo
    """
    if not _CONF.get('EMAIL_SMTP_ATTIVO', False):
        return None
    
    pwd_env = _CONF.get('SMTP_PASSWORD_ENV', 'SMTP_PASSWORD')
    
    return {
        'server': _CONF.get('SMTP_SERVER', ''),
        'port': _CONF.get('SMTP_PORT', 465),
        'from': _CONF.get('SMTP_FROM', ''),
        'user': _CONF.get('SMTP_USER', ''),
        'password': os.environ.get(pwd_env, ''),
        'livello_minimo': _CONF.get('EMAIL_LIVELLO_MINIMO', 3),
        'categorie': _CONF.get('EMAIL_CATEGORIE', []),
    }


def get_config_telegram():
    """
    Restituisce configurazione canale Telegram.
    Token letto dalla variabile d'ambiente indicata nel .conf.
    
    Returns:
        Dict con parametri Telegram o None se non attivo
    """
    if not _CONF.get('TELEGRAM_ATTIVO', False):
        return None
    
    token_env = _CONF.get('TELEGRAM_TOKEN_ENV', 'TELEGRAM_BOT_TOKEN')
    
    return {
        'token': os.environ.get(token_env, ''),
        'bot_name': _CONF.get('TELEGRAM_BOT_NAME', 'BRCarServiceBot'),
        'livello_minimo': _CONF.get('TELEGRAM_LIVELLO_MINIMO', 2),
        'categorie': _CONF.get('TELEGRAM_CATEGORIE', []),
        'ora_inizio': _CONF.get('TELEGRAM_ORA_INIZIO', '07:30'),
        'ora_fine': _CONF.get('TELEGRAM_ORA_FINE', '20:00'),
        'accoda_fuori_orario': _CONF.get('TELEGRAM_ACCODA_FUORI_ORARIO', True),
        'max_per_ora': _CONF.get('TELEGRAM_MAX_PER_ORA', 20),
        'formato': _CONF.get('TELEGRAM_FORMATO', 'html'),
    }


# ==============================================================================
# UTILITY
# ==============================================================================

def invalida_cache_notifiche():
    """Invalida tutte le cache per ricaricare dati da Excel."""
    get_categorie.cache_clear()
    _mappa_categorie.cache_clear()
    get_livelli.cache_clear()
    _mappa_livelli.cache_clear()


def ricarica_conf():
    """Ricarica il file .conf (per runtime reload)."""
    global _CONF, NOTIFICHE_ATTIVO, POLLING_SECONDI, MAX_NOTIFICHE_DROPDOWN
    global LIVELLO_MINIMO_CAMPANELLA, CAMPANELLA_ATTIVA, CAMPANELLA_BADGE
    global DEDUP_ATTIVA, DEDUP_FINESTRA_ORE
    global PULIZIA_LETTE_GIORNI, PULIZIA_NON_LETTE_GIORNI, PULIZIA_ARCHIVIATE_GIORNI
    
    _CONF = _leggi_conf()
    
    NOTIFICHE_ATTIVO = _CONF.get('NOTIFICHE_ATTIVO', True)
    LIVELLO_MINIMO_CAMPANELLA = _CONF.get('LIVELLO_MINIMO_CAMPANELLA', 1)
    MAX_NOTIFICHE_DROPDOWN = _CONF.get('MAX_NOTIFICHE_DROPDOWN', 15)
    POLLING_SECONDI = _CONF.get('POLLING_SECONDI', 30)
    DEDUP_ATTIVA = _CONF.get('DEDUP_ATTIVA', True)
    DEDUP_FINESTRA_ORE = _CONF.get('DEDUP_FINESTRA_ORE', 24)
    PULIZIA_LETTE_GIORNI = _CONF.get('PULIZIA_LETTE_GIORNI', 90)
    PULIZIA_NON_LETTE_GIORNI = _CONF.get('PULIZIA_NON_LETTE_GIORNI', 180)
    PULIZIA_ARCHIVIATE_GIORNI = _CONF.get('PULIZIA_ARCHIVIATE_GIORNI', 30)
    CAMPANELLA_ATTIVA = _CONF.get('CAMPANELLA_ATTIVA', True)
    CAMPANELLA_BADGE = _CONF.get('CAMPANELLA_BADGE', True)
    
    invalida_cache_notifiche()


# ==============================================================================
# TEST STANDALONE
# ==============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("CONFIGURAZIONE SISTEMA NOTIFICHE")
    print("=" * 60)
    
    print(f"\nCONF_FILE:   {CONF_FILE} {'[OK]' if CONF_FILE.exists() else '[MANCANTE]'}")
    print(f"EXCEL_FILE:  {CATEGORIE_FILE} {'[OK]' if CATEGORIE_FILE.exists() else '[MANCANTE]'}")
    
    print(f"\n--- Parametri generali ---")
    print(f"ATTIVO:           {NOTIFICHE_ATTIVO}")
    print(f"POLLING:          {POLLING_SECONDI}s")
    print(f"MAX DROPDOWN:     {MAX_NOTIFICHE_DROPDOWN}")
    print(f"LIVELLO MIN:      {LIVELLO_MINIMO_CAMPANELLA}")
    print(f"CAMPANELLA:       {CAMPANELLA_ATTIVA}")
    
    print(f"\n--- Deduplicazione ---")
    print(f"DEDUP:            {DEDUP_ATTIVA}")
    print(f"FINESTRA:         {DEDUP_FINESTRA_ORE} ore")
    
    print(f"\n--- Pulizia ---")
    print(f"LETTE:            {PULIZIA_LETTE_GIORNI} giorni")
    print(f"NON LETTE:        {PULIZIA_NON_LETTE_GIORNI} giorni")
    print(f"ARCHIVIATE:       {PULIZIA_ARCHIVIATE_GIORNI} giorni")
    
    print(f"\n--- Categorie ({len(get_categorie())}) ---")
    for cat in get_categorie():
        print(f"  {cat.get('Codice', '?'):25s} {cat.get('Icona_Bootstrap', ''):25s} {cat.get('Colore_Hex', '')}")
    
    print(f"\n--- Livelli ({len(get_livelli())}) ---")
    for liv in get_livelli():
        print(f"  {int(liv.get('Codice_Numerico', 0)):d} = {liv.get('Nome', '?'):10s} {liv.get('Colore_Hex', '')}")
    
    print(f"\n--- Canali uscita ---")
    print(f"Email SMTP:       {'ATTIVO' if get_config_email_smtp() else 'SPENTO'}")
    print(f"Telegram:         {'ATTIVO' if get_config_telegram() else 'SPENTO'}")
    
    print("\n" + "=" * 60)
