# ==============================================================================
# LAYOUT CONFIG - Configurazione Layout Pagine
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-10
# Descrizione: Gestione layout pagina dettaglio cliente.
#              I layout sono salvati come file JSON nella cartella
#              impostazioni/layout/ e possono essere multipli.
#              Un file _config.json indica quale layout e' attivo.
# ==============================================================================

import json
import os
import re
from datetime import datetime
from pathlib import Path

# ==============================================================================
# PERCORSI
# ==============================================================================

# Base dir del progetto (parent di app/)
BASE_DIR = Path(__file__).parent.parent.absolute()
LAYOUT_DIR = BASE_DIR / 'impostazioni' / 'layout'
CONFIG_FILE = LAYOUT_DIR / '_config.json'
DEFAULT_FILE = LAYOUT_DIR / 'default.json'


# ==============================================================================
# CATALOGO QUADRI
# ==============================================================================
# Metadati per ogni quadro disponibile nella pagina dettaglio cliente.
# Il campo "template" indica il file satellite da includere.

CATALOGO_QUADRI = {
    "dati_aziendali":   {"nome": "Dati Aziendali",         "icona": "bi-building",          "template": "dettaglio/dati_aziendali/_riquadro.html"},
    "descrizione":      {"nome": "Descrizione / ATECO",    "icona": "bi-briefcase",         "template": "dettaglio/descrizione/_riquadro.html"},
    "capogruppo":       {"nome": "Capogruppo",             "icona": "bi-building",          "template": "dettaglio/capogruppo/_riquadro.html"},
    "collegamenti":     {"nome": "Collegamenti",           "icona": "bi-diagram-3",         "template": "dettaglio/collegamenti/_riquadro.html"},
    "contatti":         {"nome": "Contatti Generali",      "icona": "bi-telephone",         "template": "dettaglio/contatti/_riquadro.html"},
    "noleggiatori":     {"nome": "Noleggiatori",           "icona": "bi-buildings",         "template": "componenti/noleggiatori/_riquadro.html"},
    "documenti":        {"nome": "Documenti Cliente",      "icona": "bi-folder",            "template": "documenti_cliente.html"},
    "referenti":        {"nome": "Referenti",              "icona": "bi-people",            "template": "dettaglio/referenti/_riquadro.html"},
    "veicoli":          {"nome": "Veicoli Flotta",         "icona": "bi-car-front",         "template": "dettaglio/veicoli/_riquadro.html"},
    "consensi_crm":     {"nome": "Consensi / Alert CRM",   "icona": "bi-shield-check",      "template": "dettaglio/consensi_crm/_riquadro.html"},
    "storico":          {"nome": "Storico Modifiche",      "icona": "bi-clock-history",     "template": "dettaglio/storico/_riquadro.html"},
    "crm":              {"nome": "Dati CRM Zoho",          "icona": "bi-cloud-arrow-down",  "template": "componenti/crm/_riquadro.html"},
    "rating":           {"nome": "Rating / Score",         "icona": "bi-shield-check",      "template": "dettaglio/rating/_riquadro.html"},
    "fido":             {"nome": "Fido Consigliato",       "icona": "bi-credit-card",       "template": "dettaglio/fido/_riquadro.html"},
    "finanziari":       {"nome": "Dati Finanziari",        "icona": "bi-graph-up",          "template": "dettaglio/finanziari/_riquadro.html"},
    "commerciale":      {"nome": "Commerciale Assegnato",  "icona": "bi-person-badge",      "template": "dettaglio/commerciale/_riquadro.html"},
    "top_prospect":     {"nome": "Top Prospect",           "icona": "bi-trophy",            "template": "dettaglio/top_prospect/_riquadro.html"},
    "veicoli_rilevati": {"nome": "Veicoli Rilevati",       "icona": "bi-speedometer2",      "template": "dettaglio/veicoli_rilevati/_riquadro.html"},
    "info":             {"nome": "Info Date",              "icona": "bi-info-circle",       "template": "dettaglio/info/_riquadro.html"},
}


# ==============================================================================
# LAYOUT DI DEFAULT
# ==============================================================================
# Replica esattamente la disposizione attuale della pagina.
# Griglia a 12 colonne, auto-height per i quadri.
# Coordinate: x=posizione orizzontale, y=ordine verticale, w=larghezza

DEFAULT_LAYOUT = {
    "nome": "Layout Originale",
    "descrizione": "Layout di fabbrica - disposizione originale della pagina",
    "data_creazione": "2026-02-10T00:00:00",
    "creato_da": "Sistema",
    "versione_schema": 1,
    "colonne": 12,
    "quadri": [
        # === COLONNA SINISTRA (w=8) ===
        {"id": "dati_aziendali",   "x": 0, "y": 0,  "w": 8, "h": 4, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "descrizione",      "x": 0, "y": 4,  "w": 8, "h": 3, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "capogruppo",       "x": 0, "y": 7,  "w": 4, "h": 3, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "collegamenti",     "x": 4, "y": 7,  "w": 4, "h": 3, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "contatti",         "x": 0, "y": 10, "w": 8, "h": 3, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "noleggiatori",     "x": 0, "y": 13, "w": 8, "h": 3, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "documenti",        "x": 0, "y": 16, "w": 8, "h": 2, "visible": True,  "min_w": 6, "min_h": 2},
        {"id": "referenti",        "x": 0, "y": 18, "w": 12, "h": 4, "visible": True,  "min_w": 8, "min_h": 3},
        {"id": "veicoli",          "x": 0, "y": 22, "w": 12, "h": 5, "visible": True,  "min_w": 8, "min_h": 3},
        {"id": "consensi_crm",     "x": 0, "y": 27, "w": 12, "h": 3, "visible": True,  "min_w": 6, "min_h": 2},
        {"id": "storico",          "x": 0, "y": 30, "w": 12, "h": 4, "visible": True,  "min_w": 8, "min_h": 3},

        # === COLONNA DESTRA (w=4) ===
        {"id": "crm",              "x": 8, "y": 0,  "w": 4, "h": 3, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "rating",           "x": 8, "y": 3,  "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "fido",             "x": 8, "y": 5,  "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "finanziari",       "x": 8, "y": 7,  "w": 4, "h": 4, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "commerciale",      "x": 8, "y": 11, "w": 4, "h": 4, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "top_prospect",     "x": 8, "y": 15, "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "veicoli_rilevati", "x": 8, "y": 17, "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "info",             "x": 8, "y": 19, "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
    ]
}


# ==============================================================================
# FUNZIONI GESTIONE LAYOUT
# ==============================================================================

def _ensure_layout_dir():
    """Crea cartella layout se non esiste."""
    LAYOUT_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(nome):
    """
    Converte un nome in un filename sicuro.
    Rimuove caratteri speciali, sostituisce spazi con underscore.
    """
    # Rimuovi tutto tranne alfanumerici, spazi, trattini
    safe = re.sub(r'[^\w\s\-]', '', nome)
    # Spazi -> underscore
    safe = re.sub(r'\s+', '_', safe.strip())
    # Max 50 caratteri
    return safe[:50].lower()


def init_layout():
    """
    Inizializzazione: crea cartella, file default e config se mancanti.
    Da chiamare all'avvio del server.
    """
    _ensure_layout_dir()

    # Crea default.json se non esiste
    if not DEFAULT_FILE.exists():
        with open(DEFAULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_LAYOUT, f, indent=2, ensure_ascii=False)

    # Crea _config.json se non esiste
    if not CONFIG_FILE.exists():
        config = {"layout_attivo": "default"}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)


def get_layout_attivo_nome():
    """Restituisce il nome del file layout attivo (senza .json)."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('layout_attivo', 'default')
    except (FileNotFoundError, json.JSONDecodeError):
        return 'default'


def set_layout_attivo(nome_layout):
    """
    Imposta quale layout e' attivo.
    
    Args:
        nome_layout: nome del file (senza .json)
    
    Returns:
        bool: True se impostato, False se file non trovato
    """
    filepath = LAYOUT_DIR / f'{nome_layout}.json'
    if not filepath.exists():
        return False

    _ensure_layout_dir()
    config = {"layout_attivo": nome_layout}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return True


def get_layout_attivo():
    """
    Carica il layout attivo corrente.
    
    Returns:
        dict: layout completo (con quadri, nome, ecc.)
    """
    nome = get_layout_attivo_nome()
    layout = carica_layout(nome)
    if layout is None:
        # Fallback al default
        return DEFAULT_LAYOUT.copy()
    return layout


def carica_layout(nome_layout):
    """
    Carica un layout da file.
    
    Args:
        nome_layout: nome del file (senza .json)
    
    Returns:
        dict o None
    """
    filepath = LAYOUT_DIR / f'{nome_layout}.json'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def salva_layout(nome_display, descrizione, quadri, utente_nome='Admin'):
    """
    Salva un nuovo layout o sovrascrive uno esistente.
    
    Args:
        nome_display: nome leggibile (es. "Layout Compatto")
        descrizione: descrizione libera
        quadri: lista quadri con coordinate [{id, x, y, w, h, visible, min_w, min_h}, ...]
        utente_nome: chi salva
    
    Returns:
        dict: {"success": True, "filename": "layout_compatto", "filepath": "..."}
    """
    _ensure_layout_dir()

    filename = _sanitize_filename(nome_display)
    if not filename:
        return {"success": False, "error": "Nome non valido"}

    # Proteggi il default: non sovrascrivibile
    if filename == 'default':
        return {"success": False, "error": "Il layout 'default' non puo' essere sovrascritto"}

    layout = {
        "nome": nome_display,
        "descrizione": descrizione or "",
        "data_creazione": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        "creato_da": utente_nome,
        "versione_schema": 1,
        "colonne": 12,
        "quadri": quadri
    }

    filepath = LAYOUT_DIR / f'{filename}.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(layout, f, indent=2, ensure_ascii=False)

    return {"success": True, "filename": filename, "filepath": str(filepath)}


def lista_layout():
    """
    Elenca tutti i layout salvati.
    
    Returns:
        list: [{"filename": "default", "nome": "Layout Originale", "descrizione": "...", 
                "data_creazione": "...", "creato_da": "...", "attivo": True/False, 
                "eliminabile": True/False}, ...]
    """
    _ensure_layout_dir()
    attivo = get_layout_attivo_nome()
    risultati = []

    for filepath in sorted(LAYOUT_DIR.glob('*.json')):
        # Ignora _config.json
        if filepath.name.startswith('_'):
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            filename = filepath.stem  # senza .json
            risultati.append({
                "filename": filename,
                "nome": data.get("nome", filename),
                "descrizione": data.get("descrizione", ""),
                "data_creazione": data.get("data_creazione", ""),
                "creato_da": data.get("creato_da", ""),
                "attivo": filename == attivo,
                "eliminabile": filename != "default",
                "num_quadri_visibili": sum(1 for q in data.get("quadri", []) if q.get("visible", True)),
                "num_quadri_totali": len(data.get("quadri", [])),
            })
        except (json.JSONDecodeError, IOError):
            continue

    return risultati


def elimina_layout(nome_layout):
    """
    Elimina un layout salvato.
    
    Args:
        nome_layout: nome del file (senza .json)
    
    Returns:
        dict: {"success": True} o {"success": False, "error": "..."}
    """
    if nome_layout == 'default':
        return {"success": False, "error": "Il layout 'default' non puo' essere eliminato"}

    # Non eliminare il layout attivo
    if nome_layout == get_layout_attivo_nome():
        return {"success": False, "error": "Non puoi eliminare il layout attivo. Attiva un altro layout prima."}

    filepath = LAYOUT_DIR / f'{nome_layout}.json'
    if not filepath.exists():
        return {"success": False, "error": "Layout non trovato"}

    filepath.unlink()
    return {"success": True}


def duplica_layout(nome_sorgente, nuovo_nome, utente_nome='Admin'):
    """
    Duplica un layout esistente con un nuovo nome.
    
    Args:
        nome_sorgente: filename layout da copiare (senza .json)
        nuovo_nome: nome display del nuovo layout
        utente_nome: chi duplica
    
    Returns:
        dict: risultato salva_layout
    """
    sorgente = carica_layout(nome_sorgente)
    if sorgente is None:
        return {"success": False, "error": f"Layout sorgente '{nome_sorgente}' non trovato"}

    return salva_layout(
        nome_display=nuovo_nome,
        descrizione=f"Copia di '{sorgente.get('nome', nome_sorgente)}'",
        quadri=sorgente.get("quadri", []),
        utente_nome=utente_nome
    )


# ==============================================================================
# MAPPA QUADRI -> TEMPLATE (Fase 2)
# ==============================================================================

TEMPLATE_MAP = {
    'dati_aziendali':       'dettaglio/dati_aziendali/_content.html',
    'capogruppo':           'dettaglio/capogruppo/_content.html',
    'collegamenti':         'dettaglio/collegamenti/_riquadro.html',
    'contatti':             'dettaglio/contatti/_content.html',
    'crm':                  'componenti/crm/_riquadro.html',
    'rating':               'dettaglio/rating/_content.html',
    'fido':                 'dettaglio/fido/_content.html',
    'noleggiatori':         'componenti/noleggiatori/_riquadro.html',
    'flotta':               'dettaglio/flotta/_content.html',
    'referenti':            'dettaglio/referenti/_content.html',
    'descrizione':          'dettaglio/descrizione/_content.html',
    'finanziari':           'dettaglio/finanziari/_content.html',
    'documenti':            'documenti_cliente.html',
    'veicoli':              'dettaglio/veicoli/_content.html',
    'vetture_stock':        'dettaglio/vetture_stock/_content.html',
    'storico':              'dettaglio/storico/_content.html',
    'commerciale_storico':  'dettaglio/commerciale_storico/_content.html',
}


def get_layout_quadri():
    """
    Restituisce la lista dei quadri del layout attivo, arricchita con
    il percorso template, ordinata per (y, x).
    Il modal commerciale_storico viene escluso (renderizzato a parte).
    """
    layout = get_layout_attivo()
    quadri = layout.get('quadri', [])
    result = []
    for q in quadri:
        qid = q.get('id', '')
        # Il modal viene sempre renderizzato fuori dalla griglia
        if qid == 'commerciale_storico':
            continue
        tmpl = TEMPLATE_MAP.get(qid)
        if tmpl:
            result.append({
                'id': qid,
                'x': q.get('x', 0),
                'y': q.get('y', 0),
                'w': q.get('w', 12),
                'h': q.get('h', 1),
                'template': tmpl,
            })
    result.sort(key=lambda r: (r['y'], r['x']))
    return result
