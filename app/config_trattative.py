# -*- coding: utf-8 -*-
"""
==============================================================================
CONFIG TRATTATIVE - Lettura configurazione da Excel
==============================================================================
Versione: 1.0
Data: 2026-01-27
Descrizione: Carica configurazioni dropdown da file Excel

File Excel gestiti:
- stati_trattativa.xlsx
- tipi_trattativa.xlsx  
- tipologie_veicolo.xlsx
- noleggiatori.xlsx (esistente)

Uso:
    from app.config_trattative import (
        get_stati_trattativa,
        get_tipi_trattativa,
        get_tipologie_veicolo,
        get_noleggiatori_dropdown,
        get_colore_stato
    )
==============================================================================
"""

import os
import pandas as pd
from functools import lru_cache

# ==============================================================================
# CONFIGURAZIONE PERCORSI
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPOSTAZIONI_DIR = os.path.join(BASE_DIR, 'impostazioni')

# File Excel
FILE_STATI = os.path.join(IMPOSTAZIONI_DIR, 'stati_trattativa.xlsx')
FILE_TIPI = os.path.join(IMPOSTAZIONI_DIR, 'tipi_trattativa.xlsx')
FILE_TIPOLOGIE = os.path.join(IMPOSTAZIONI_DIR, 'tipologie_veicolo.xlsx')
FILE_NOLEGGIATORI = os.path.join(IMPOSTAZIONI_DIR, 'noleggiatori.xlsx')


# ==============================================================================
# FUNZIONI DI LETTURA EXCEL
# ==============================================================================

def _leggi_excel(filepath, colonne_richieste=None):
    """
    Legge un file Excel e restituisce lista di dizionari.
    
    Args:
        filepath: percorso file Excel
        colonne_richieste: lista colonne da verificare (opzionale)
    
    Returns:
        Lista di dizionari con i dati
    """
    if not os.path.exists(filepath):
        print(f"[WARN] File non trovato: {filepath}")
        return []
    
    try:
        df = pd.read_excel(filepath)
        
        # Verifica colonne richieste
        if colonne_richieste:
            mancanti = set(colonne_richieste) - set(df.columns)
            if mancanti:
                print(f"[WARN] Colonne mancanti in {filepath}: {mancanti}")
        
        # Ordina per colonna 'Ordine' se presente
        if 'Ordine' in df.columns:
            df = df.sort_values('Ordine')
        
        return df.to_dict('records')
        
    except Exception as e:
        print(f"[ERRORE] Lettura {filepath}: {e}")
        return []


def _invalida_cache():
    """Invalida tutte le cache per ricaricare i dati"""
    get_stati_trattativa.cache_clear()
    get_tipi_trattativa.cache_clear()
    get_tipologie_veicolo.cache_clear()
    get_noleggiatori_dropdown.cache_clear()
    get_colori_stati.cache_clear()


# ==============================================================================
# FUNZIONI PUBBLICHE - STATI TRATTATIVA
# ==============================================================================

@lru_cache(maxsize=1)
def get_stati_trattativa():
    """
    Restituisce lista stati trattativa con colori.
    
    Returns:
        Lista di dict: [{'Codice': 'PRESO_IN_CARICO', 'Etichetta': 'Preso in carico', 'Colore': '#6c757d', ...}, ...]
    """
    return _leggi_excel(FILE_STATI, ['Codice', 'Etichetta', 'Colore'])


def get_stati_dropdown():
    """
    Restituisce lista per dropdown (solo Codice ed Etichetta).
    
    Returns:
        Lista di tuple: [('PRESO_IN_CARICO', 'Preso in carico'), ...]
    """
    stati = get_stati_trattativa()
    return [(s.get('Codice', ''), s.get('Etichetta', '')) for s in stati]


@lru_cache(maxsize=1)
def get_colori_stati():
    """
    Restituisce dizionario Etichetta -> Colore per CSS.
    
    Returns:
        Dict: {'Preso in carico': '#6c757d', 'Approvato': '#28a745', ...}
    """
    stati = get_stati_trattativa()
    return {s.get('Etichetta', ''): s.get('Colore', '#6c757d') for s in stati}


def get_colore_stato(stato_etichetta):
    """
    Restituisce il colore per uno stato specifico.
    
    Args:
        stato_etichetta: etichetta dello stato (es. 'Preso in carico')
    
    Returns:
        Codice colore esadecimale (es. '#6c757d')
    """
    colori = get_colori_stati()
    return colori.get(stato_etichetta, '#6c757d')


# ==============================================================================
# FUNZIONI PUBBLICHE - TIPI TRATTATIVA
# ==============================================================================

@lru_cache(maxsize=1)
def get_tipi_trattativa():
    """
    Restituisce lista tipi trattativa.
    
    Returns:
        Lista di dict: [{'Codice': 'NUOVO_CONTRATTO', 'Etichetta': 'Nuovo contratto', ...}, ...]
    """
    return _leggi_excel(FILE_TIPI, ['Codice', 'Etichetta'])


def get_tipi_dropdown():
    """
    Restituisce lista per dropdown.
    
    Returns:
        Lista di tuple: [('NUOVO_CONTRATTO', 'Nuovo contratto'), ...]
    """
    tipi = get_tipi_trattativa()
    return [(t.get('Codice', ''), t.get('Etichetta', '')) for t in tipi]


# ==============================================================================
# FUNZIONI PUBBLICHE - TIPOLOGIE VEICOLO
# ==============================================================================

@lru_cache(maxsize=1)
def get_tipologie_veicolo():
    """
    Restituisce lista tipologie veicolo.
    
    Returns:
        Lista di dict: [{'Codice': 'VETTURA', 'Etichetta': 'Vettura', ...}, ...]
    """
    return _leggi_excel(FILE_TIPOLOGIE, ['Codice', 'Etichetta'])


def get_tipologie_dropdown():
    """
    Restituisce lista per dropdown.
    
    Returns:
        Lista di tuple: [('VETTURA', 'Vettura'), ...]
    """
    tipologie = get_tipologie_veicolo()
    return [(t.get('Codice', ''), t.get('Etichetta', '')) for t in tipologie]


# ==============================================================================
# FUNZIONI PUBBLICHE - NOLEGGIATORI
# ==============================================================================

@lru_cache(maxsize=1)
def get_noleggiatori_dropdown():
    """
    Restituisce lista noleggiatori per dropdown.
    Usa il file noleggiatori.xlsx esistente.
    
    Returns:
        Lista di tuple: [('ALD', 'ALD Automotive'), ...]
    """
    noleggiatori = _leggi_excel(FILE_NOLEGGIATORI, ['Codice', 'Nome'])
    return [(n.get('Codice', ''), n.get('Nome', '')) for n in noleggiatori]


def get_noleggiatori_con_colori():
    """
    Restituisce noleggiatori con colori per badge.
    
    Returns:
        Dict: {'ALD': {'nome': 'ALD Automotive', 'colore': '#e31937'}, ...}
    """
    noleggiatori = _leggi_excel(FILE_NOLEGGIATORI, ['Codice', 'Nome', 'Colore'])
    return {
        n.get('Codice', ''): {
            'nome': n.get('Nome', ''),
            'colore': n.get('Colore', '#6c757d')
        }
        for n in noleggiatori
    }


# ==============================================================================
# FUNZIONE UTILITY - RICARICA CONFIGURAZIONE
# ==============================================================================

def ricarica_configurazione():
    """
    Ricarica tutte le configurazioni da Excel.
    Utile dopo modifiche ai file senza riavviare il server.
    
    Returns:
        Dict con conteggi elementi caricati
    """
    _invalida_cache()
    
    return {
        'stati': len(get_stati_trattativa()),
        'tipi': len(get_tipi_trattativa()),
        'tipologie': len(get_tipologie_veicolo()),
        'noleggiatori': len(get_noleggiatori_dropdown())
    }


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("TEST CONFIG TRATTATIVE")
    print("=" * 60)
    
    print(f"\nPercorso impostazioni: {IMPOSTAZIONI_DIR}")
    
    print("\n--- STATI TRATTATIVA ---")
    for s in get_stati_trattativa():
        print(f"  {s.get('Codice')}: {s.get('Etichetta')} ({s.get('Colore')})")
    
    print("\n--- TIPI TRATTATIVA ---")
    for t in get_tipi_dropdown():
        print(f"  {t[0]}: {t[1]}")
    
    print("\n--- TIPOLOGIE VEICOLO ---")
    for t in get_tipologie_dropdown():
        print(f"  {t[0]}: {t[1]}")
    
    print("\n--- NOLEGGIATORI ---")
    for n in get_noleggiatori_dropdown():
        print(f"  {n[0]}: {n[1]}")
    
    print("\n--- RIEPILOGO ---")
    stats = ricarica_configurazione()
    print(f"  Stati: {stats['stati']}")
    print(f"  Tipi: {stats['tipi']}")
    print(f"  Tipologie: {stats['tipologie']}")
    print(f"  Noleggiatori: {stats['noleggiatori']}")

def get_percentuali_stati():
    """
    Restituisce dizionario Etichetta -> Percentuale avanzamento.
    
    Returns:
        Dict: {'Preso in carico': 10, 'Approvato': 100, ...}
    """
    stati = get_stati_trattativa()
    return {s.get('Etichetta', ''): s.get('Percentuale', 0) for s in stati}

def get_percentuale_stato(stato_etichetta):
    """
    Restituisce la percentuale per uno stato specifico.
    
    Args:
        stato_etichetta: etichetta dello stato (es. 'Preso in carico')
    
    Returns:
        int: percentuale (0-100)
    """
    percentuali = get_percentuali_stati()
    return percentuali.get(stato_etichetta, 0)


def get_stati_chiusi():
    """
    Restituisce lista etichette degli stati marcati come 'chiusi' nell'Excel.
    Legge la colonna 'Chiusa' e restituisce gli stati con valore 'si'.
    
    Returns:
        Lista di stringhe: ['Bocciato', 'Perso', 'Pratica caricata', ...]
    """
    stati = get_stati_trattativa()
    chiusi = []
    for s in stati:
        val_chiusa = str(s.get('Chiusa', '')).strip().lower()
        if val_chiusa in ('si', 'sì', 'yes', '1', 'true'):
            chiusi.append(s.get('Etichetta', ''))
    return chiusi
