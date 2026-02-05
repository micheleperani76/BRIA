#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Modulo Configurazione Percorsi
# ==============================================================================
# Versione: 1.0
# Data: 2025-01-19
# Descrizione: Legge i percorsi da impostazioni/percorsi.conf
# ==============================================================================

from pathlib import Path

# ==============================================================================
# COSTANTI BASE (non modificabili)
# ==============================================================================

# Directory base del progetto (gestione_flotta/)
BASE_DIR = Path(__file__).parent.parent

# File configurazione percorsi
PERCORSI_CONF = BASE_DIR / "impostazioni" / "percorsi.conf"


# ==============================================================================
# FUNZIONI LETTURA CONFIGURAZIONE
# ==============================================================================

def leggi_percorsi_conf():
    """
    Legge il file percorsi.conf e ritorna un dizionario con i path.
    
    Returns:
        dict: Dizionario {chiave: Path} con tutti i percorsi configurati
    
    Raises:
        FileNotFoundError: Se il file percorsi.conf non esiste
    """
    if not PERCORSI_CONF.exists():
        raise FileNotFoundError(
            f"File configurazione non trovato: {PERCORSI_CONF}\n"
            f"Creare il file impostazioni/percorsi.conf"
        )
    
    percorsi = {}
    
    with open(PERCORSI_CONF, 'r', encoding='utf-8') as f:
        for linea in f:
            # Ignora commenti e righe vuote
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            
            # Parse chiave=valore
            if '=' in linea:
                chiave, valore = linea.split('=', 1)
                chiave = chiave.strip()
                valore = valore.strip()
                
                # Converti in Path
                if valore.startswith('/'):
                    # Path assoluto: usa così com'è
                    percorsi[chiave] = Path(valore)
                else:
                    # Path relativo: relativo a BASE_DIR
                    percorsi[chiave] = BASE_DIR / valore
    
    return percorsi


def get_percorso(chiave, default=None):
    """
    Ottiene un singolo percorso dalla configurazione.
    
    Args:
        chiave: Nome della chiave (es: 'DB_DIR', 'CLIENTI_DIR')
        default: Valore di default se la chiave non esiste
    
    Returns:
        Path: Il percorso configurato o il default
    """
    try:
        percorsi = leggi_percorsi_conf()
        return percorsi.get(chiave, default)
    except FileNotFoundError:
        return default


def inizializza_cartelle():
    """
    Crea tutte le cartelle configurate se non esistono.
    Utile all'avvio del programma.
    """
    try:
        percorsi = leggi_percorsi_conf()
        for chiave, path in percorsi.items():
            if chiave.endswith('_DIR'):
                path.mkdir(parents=True, exist_ok=True)
    except FileNotFoundError as e:
        print(f"ATTENZIONE: {e}")


# ==============================================================================
# CARICAMENTO PERCORSI ALL'IMPORT
# ==============================================================================

# Carica percorsi una sola volta all'import del modulo
try:
    _PERCORSI = leggi_percorsi_conf()
    
    # Espone come costanti del modulo
    DB_DIR = _PERCORSI.get('DB_DIR', BASE_DIR / 'db')
    EXPORTS_DIR = _PERCORSI.get('EXPORTS_DIR', BASE_DIR / 'exports')
    PDF_DIR = _PERCORSI.get('PDF_DIR', BASE_DIR / 'pdf')
    PDF_ERRORI_DIR = _PERCORSI.get('PDF_ERRORI_DIR', BASE_DIR / 'pdf_errori')
    CLIENTI_DIR = _PERCORSI.get('CLIENTI_DIR', BASE_DIR / 'clienti')
    
    # Sottocartelle clienti
    CLIENTI_CF_DIR = CLIENTI_DIR / 'CF'
    CLIENTI_PIVA_DIR = CLIENTI_DIR / 'PIVA'
    
    # File database
    DB_FILE = DB_DIR / 'gestionale.db'

except FileNotFoundError:
    # Fallback ai valori di default se il file non esiste
    print("ATTENZIONE: File percorsi.conf non trovato, uso valori di default")
    DB_DIR = BASE_DIR / 'db'
    EXPORTS_DIR = BASE_DIR / 'exports'
    PDF_DIR = BASE_DIR / 'pdf'
    PDF_ERRORI_DIR = BASE_DIR / 'pdf_errori'
    CLIENTI_DIR = BASE_DIR / 'clienti'
    CLIENTI_CF_DIR = CLIENTI_DIR / 'CF'
    CLIENTI_PIVA_DIR = CLIENTI_DIR / 'PIVA'
    DB_FILE = DB_DIR / 'gestionale.db'


# ==============================================================================
# FUNZIONI HELPER PER CLIENTI
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
        cliente: dict o Row con 'p_iva' e/o 'cod_fiscale'
    
    Returns:
        Path: es. Path('clienti/PIVA/04292180983')
    
    Raises:
        ValueError: Se il cliente non ha né P.IVA né CF
    """
    # Supporta sia dict che sqlite3.Row
    piva = cliente.get('p_iva') if hasattr(cliente, 'get') else cliente['p_iva']
    cf = cliente.get('cod_fiscale') if hasattr(cliente, 'get') else cliente['cod_fiscale']
    
    if piva:
        # Ha P.IVA: usa PIVA (senza prefisso IT)
        ident = pulisci_piva(piva)
        if ident:
            return CLIENTI_PIVA_DIR / ident
    
    if cf:
        # Solo CF
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
        cliente: dict o Row con 'p_iva' e/o 'cod_fiscale'
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
# TEST
# ==============================================================================

if __name__ == '__main__':
    print("=== Test Configurazione Percorsi ===")
    print(f"BASE_DIR:        {BASE_DIR}")
    print(f"PERCORSI_CONF:   {PERCORSI_CONF}")
    print()
    print("Percorsi configurati:")
    print(f"  DB_DIR:        {DB_DIR}")
    print(f"  DB_FILE:       {DB_FILE}")
    print(f"  EXPORTS_DIR:   {EXPORTS_DIR}")
    print(f"  PDF_DIR:       {PDF_DIR}")
    print(f"  PDF_ERRORI_DIR:{PDF_ERRORI_DIR}")
    print(f"  CLIENTI_DIR:   {CLIENTI_DIR}")
    print(f"  CLIENTI_CF:    {CLIENTI_CF_DIR}")
    print(f"  CLIENTI_PIVA:  {CLIENTI_PIVA_DIR}")
    print()
    
    # Test funzione cliente
    cliente_test = {'p_iva': 'IT01234567890', 'cod_fiscale': 'RSSMRA80A01H501U'}
    print(f"Cliente test: {cliente_test}")
    print(f"  Base path: {get_cliente_base_path(cliente_test)}")
    print(f"  Allegati:  {get_cliente_allegati_path(cliente_test)}")
    print(f"  Creditsafe:{get_cliente_creditsafe_path(cliente_test)}")
