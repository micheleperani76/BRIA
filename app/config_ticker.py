# -*- coding: utf-8 -*-
"""
==============================================================================
CONFIGURAZIONE TICKER BROADCASTING
==============================================================================
Versione: 1.0.0
Data: 2026-02-06
Descrizione: Lettura configurazione sistema ticker da tabella ticker_config.
             Pattern identico a config_trattative.py.
==============================================================================
"""

import sqlite3
from functools import lru_cache

# ==============================================================================
# COSTANTI
# ==============================================================================

# Animazioni supportate
ANIMAZIONI = [
    {'codice': 'scroll-rtl', 'nome': 'Scorrimento destra-sinistra'},
    {'codice': 'scroll-ltr', 'nome': 'Scorrimento sinistra-destra'},
    {'codice': 'slide-up',   'nome': 'Sale dal basso'},
    {'codice': 'slide-down', 'nome': 'Scende dall\'alto'},
    {'codice': 'fade',       'nome': 'Dissolvenza'},
]

# Velocita supportate
VELOCITA = [
    {'codice': 'lenta',   'nome': 'Lenta',   'fattore': 1.5},
    {'codice': 'normale', 'nome': 'Normale', 'fattore': 1.0},
    {'codice': 'veloce',  'nome': 'Veloce',  'fattore': 0.6},
]

# Stati messaggio
STATI_MESSAGGIO = ['bozza', 'in_attesa', 'approvato', 'rifiutato', 'scaduto']

# Tipi messaggio
TIPI_MESSAGGIO = ['manuale', 'automatico', 'sistema']

# Ricorrenze
RICORRENZE = ['nessuna', 'annuale', 'mensile']

# Destinatari predefiniti
DESTINATARI_PREDEFINITI = [
    {'codice': 'TUTTI',             'nome': 'Tutti gli utenti'},
    {'codice': 'RUOLO:ADMIN',       'nome': 'Solo amministratori'},
    {'codice': 'RUOLO:COMMERCIALE', 'nome': 'Solo commerciali'},
    {'codice': 'RUOLO:OPERATORE',   'nome': 'Solo operatori'},
]

# Giorni settimana
GIORNI_SETTIMANA = [
    {'num': '1', 'nome': 'Lun', 'nome_lungo': 'Lunedi'},
    {'num': '2', 'nome': 'Mar', 'nome_lungo': 'Martedi'},
    {'num': '3', 'nome': 'Mer', 'nome_lungo': 'Mercoledi'},
    {'num': '4', 'nome': 'Gio', 'nome_lungo': 'Giovedi'},
    {'num': '5', 'nome': 'Ven', 'nome_lungo': 'Venerdi'},
    {'num': '6', 'nome': 'Sab', 'nome_lungo': 'Sabato'},
    {'num': '7', 'nome': 'Dom', 'nome_lungo': 'Domenica'},
]


# ==============================================================================
# LETTURA CONFIGURAZIONE DA DB
# ==============================================================================

def get_config(conn, chiave, default=None):
    """
    Legge un singolo parametro di configurazione.
    
    Args:
        conn: connessione SQLite
        chiave: nome parametro
        default: valore default se non trovato
    
    Returns:
        Valore come stringa, o default
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT valore FROM ticker_config WHERE chiave = ?",
            (chiave,)
        )
        row = cursor.fetchone()
        if row:
            return row[0] if not isinstance(row, dict) else row['valore']
        return default
    except Exception:
        return default


def get_config_int(conn, chiave, default=0):
    """Legge parametro come intero."""
    val = get_config(conn, chiave)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return default


def get_config_bool(conn, chiave, default=False):
    """Legge parametro come booleano."""
    val = get_config(conn, chiave)
    if val is not None:
        return val in ('1', 'true', 'True', 'si', 'yes')
    return default


def get_all_config(conn):
    """
    Legge tutta la configurazione ticker.
    
    Returns:
        dict: {chiave: {'valore': ..., 'descrizione': ...}}
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT chiave, valore, descrizione FROM ticker_config ORDER BY chiave")
        result = {}
        for row in cursor.fetchall():
            if isinstance(row, dict) or hasattr(row, 'keys'):
                result[row['chiave']] = {
                    'valore': row['valore'],
                    'descrizione': row['descrizione']
                }
            else:
                result[row[0]] = {'valore': row[1], 'descrizione': row[2]}
        return result
    except Exception:
        return {}


def set_config(conn, chiave, valore):
    """
    Aggiorna un parametro di configurazione.
    
    Args:
        conn: connessione SQLite
        chiave: nome parametro
        valore: nuovo valore (stringa)
    
    Returns:
        bool: True se aggiornato
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ticker_config SET valore = ? WHERE chiave = ?",
            (str(valore), chiave)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


# ==============================================================================
# UTILITY
# ==============================================================================

def get_animazioni_dropdown():
    """Lista per dropdown animazioni."""
    return [(a['codice'], a['nome']) for a in ANIMAZIONI]


def get_velocita_dropdown():
    """Lista per dropdown velocita."""
    return [(v['codice'], v['nome']) for v in VELOCITA]


def get_destinatari_dropdown():
    """Lista per dropdown destinatari."""
    return [(d['codice'], d['nome']) for d in DESTINATARI_PREDEFINITI]


def get_fattore_velocita(codice_velocita):
    """
    Restituisce il fattore moltiplicativo per la velocita.
    
    Args:
        codice_velocita: 'lenta', 'normale', 'veloce'
    
    Returns:
        float: fattore (1.5=lenta, 1.0=normale, 0.6=veloce)
    """
    for v in VELOCITA:
        if v['codice'] == codice_velocita:
            return v['fattore']
    return 1.0


def is_ticker_attivo(conn):
    """Verifica se il sistema ticker e' attivo."""
    return get_config_bool(conn, 'attivo', True)
