#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Modulo Identificativo Cliente (P.IVA / CF)
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-13
# 
# Questo modulo gestisce l'identificazione univoca dei clienti usando:
# - P.IVA per le aziende (formato IT + 11 cifre)
# - Codice Fiscale per le persone fisiche (16 caratteri)
#
# Copia questo file in: ~/gestione_flotta/app/utils_identificativo.py
# ==============================================================================

import re
from pathlib import Path
from datetime import datetime

# ==============================================================================
# NORMALIZZAZIONE IDENTIFICATIVI
# ==============================================================================

def normalizza_piva(piva):
    """
    Normalizza P.IVA: uppercase, rimuove spazi, aggiunge prefisso IT.
    
    Args:
        piva: stringa P.IVA in qualsiasi formato
        
    Returns:
        str: P.IVA normalizzata (es. 'IT00552060980') o None se non valida
    """
    if not piva:
        return None
    
    piva = str(piva).upper().strip().replace(' ', '')
    
    # Rimuove prefisso IT se presente
    if piva.startswith('IT'):
        piva = piva[2:]
    
    # Rimuove eventuali zeri iniziali in eccesso (>11 cifre)
    if len(piva) > 11:
        piva = piva.lstrip('0')
    
    # Valida: deve essere 11 cifre
    if len(piva) == 11 and piva.isdigit():
        return 'IT' + piva
    
    return None


def normalizza_cf(cf):
    """
    Normalizza Codice Fiscale: uppercase, rimuove spazi.
    
    Args:
        cf: stringa CF in qualsiasi formato
        
    Returns:
        str: CF normalizzato o None se non valido
    """
    if not cf:
        return None
    
    cf = str(cf).upper().strip().replace(' ', '')
    
    # CF azienda: 11 cifre (uguale a P.IVA senza prefisso)
    if len(cf) == 11 and cf.isdigit():
        return cf
    
    # CF persona fisica: 16 caratteri alfanumerici (pattern: AAABBB00A00A000A)
    if len(cf) == 16:
        pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        if re.match(pattern, cf):
            return cf
    
    return None


def get_identificativo_cliente(cliente):
    """
    Ritorna l'identificativo univoco del cliente.
    
    Priorità:
    1. P.IVA (per aziende) - formato IT + 11 cifre
    2. CF (per persone fisiche) - 16 caratteri
    
    Questo garantisce:
    - Aziende sempre con P.IVA (inizia con IT)
    - Persone fisiche sempre con CF (16 caratteri)
    - Nessuna commistione tra i due tipi
    
    Args:
        cliente: dict con chiavi 'p_iva' e/o 'cod_fiscale'
        
    Returns:
        str: identificativo (es. 'IT00552060980' o 'RSSMRA80A01F205X')
        None: se non disponibile né P.IVA né CF
    """
    if not isinstance(cliente, dict):
        return None
    
    # Prima prova P.IVA (per aziende)
    piva = normalizza_piva(cliente.get('p_iva'))
    if piva:
        return piva
    
    # Poi prova CF (per persone fisiche)
    cf = normalizza_cf(cliente.get('cod_fiscale'))
    if cf:
        return cf
    
    return None


def get_identificativo_or_id(cliente):
    """
    Ritorna identificativo P.IVA/CF oppure ID numerico come fallback.
    Usato per retrocompatibilità con vecchi link.
    
    Args:
        cliente: dict con dati cliente
        
    Returns:
        str: identificativo o ID numerico come stringa
    """
    ident = get_identificativo_cliente(cliente)
    if ident:
        return ident
    
    if isinstance(cliente, dict) and 'id' in cliente:
        return f"id_{cliente['id']}"
    
    return None


def is_piva(identificativo):
    """Verifica se l'identificativo è una P.IVA."""
    if not identificativo:
        return False
    return str(identificativo).upper().startswith('IT')


def is_cf_persona(identificativo):
    """Verifica se l'identificativo è un CF persona fisica (16 caratteri)."""
    if not identificativo:
        return False
    ident = str(identificativo).upper()
    return len(ident) == 16 and ident.isalnum()


def get_tipo_identificativo(identificativo):
    """
    Ritorna il tipo di identificativo.
    
    Returns:
        str: 'PIVA', 'CF', 'ID', o 'UNKNOWN'
    """
    if not identificativo:
        return 'UNKNOWN'
    
    ident = str(identificativo).upper()
    
    if ident.startswith('IT') and len(ident) == 13:
        return 'PIVA'
    if ident.startswith('ID_'):
        return 'ID'
    if len(ident) == 16 and ident.isalnum():
        return 'CF'
    if len(ident) == 11 and ident.isdigit():
        return 'CF_AZIENDA'
    
    return 'UNKNOWN'


# ==============================================================================
# RICERCA CLIENTE
# ==============================================================================

def cerca_cliente_per_identificativo(cursor, identificativo):
    """
    Cerca un cliente per P.IVA, CF o ID numerico.
    
    Args:
        cursor: cursor database SQLite
        identificativo: P.IVA (con/senza IT), CF, o ID numerico
        
    Returns:
        dict: dati cliente o None se non trovato
    """
    if not identificativo:
        return None
    
    identificativo = str(identificativo).strip()
    
    # 1. Prova come ID numerico puro (es. "123")
    if identificativo.isdigit() and len(identificativo) < 10:
        cursor.execute('SELECT * FROM clienti WHERE id = ?', (int(identificativo),))
        row = cursor.fetchone()
        if row:
            return dict(row)
    
    # 2. Prova come ID con prefisso (es. "id_123")
    if identificativo.lower().startswith('id_'):
        try:
            id_num = int(identificativo[3:])
            cursor.execute('SELECT * FROM clienti WHERE id = ?', (id_num,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        except ValueError:
            pass
    
    identificativo = identificativo.upper()
    
    # 3. Prova come P.IVA (con o senza prefisso IT)
    piva_cerca = identificativo.replace('IT', '')
    if len(piva_cerca) == 11 and piva_cerca.isdigit():
        # Cerca sia con IT che senza
        cursor.execute("""
            SELECT * FROM clienti 
            WHERE REPLACE(REPLACE(UPPER(COALESCE(p_iva, '')), 'IT', ''), ' ', '') = ?
        """, (piva_cerca,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    
    # 4. Prova come CF persona fisica (16 caratteri)
    if len(identificativo) == 16 and identificativo.isalnum():
        cursor.execute("""
            SELECT * FROM clienti 
            WHERE UPPER(REPLACE(COALESCE(cod_fiscale, ''), ' ', '')) = ?
        """, (identificativo,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    
    # 5. Prova come CF azienda (11 cifre, uguale a P.IVA senza IT)
    if len(identificativo) == 11 and identificativo.isdigit():
        cursor.execute("""
            SELECT * FROM clienti 
            WHERE REPLACE(COALESCE(cod_fiscale, ''), ' ', '') = ?
               OR REPLACE(REPLACE(UPPER(COALESCE(p_iva, '')), 'IT', ''), ' ', '') = ?
        """, (identificativo, identificativo))
        row = cursor.fetchone()
        if row:
            return dict(row)
    
    return None


# ==============================================================================
# GESTIONE CARTELLE ALLEGATI
# ==============================================================================

def get_cartella_allegati_cliente(base_dir, cliente):
    """
    Ritorna il percorso cartella allegati per un cliente.
    
    Struttura: {base_dir}/clienti/{PIVA o CF}/
    
    Esempi:
    - Azienda:  allegati_note/clienti/IT00552060980/
    - Persona:  allegati_note/clienti/RSSMRA80A01F205X/
    - Fallback: allegati_note/clienti/id_123/
    
    Args:
        base_dir: Path cartella base allegati (es. allegati_note/clienti/)
        cliente: dict con dati cliente
        
    Returns:
        Path: percorso cartella
    """
    ident = get_identificativo_cliente(cliente)
    
    if not ident:
        # Fallback a ID se non c'è P.IVA/CF
        ident = f"id_{cliente.get('id', 'unknown')}"
    
    return Path(base_dir) / ident


def get_cartella_nota_cliente(base_dir, cliente, nota_id=None, data_nota=None):
    """
    Ritorna il percorso cartella per una specifica nota cliente.
    
    Struttura: {base_dir}/clienti/{PIVA}/{YYYYMMDD_HHMMSS}_{nota_id}/
    
    Args:
        base_dir: Path cartella base allegati
        cliente: dict con dati cliente
        nota_id: ID della nota (opzionale)
        data_nota: datetime della nota (opzionale, usa now() se None)
        
    Returns:
        Path: percorso cartella nota
    """
    cliente_dir = get_cartella_allegati_cliente(base_dir, cliente)
    
    # Se esiste già una cartella per questa nota, usala
    if nota_id and cliente_dir.exists():
        for subdir in cliente_dir.iterdir():
            if subdir.is_dir() and subdir.name.endswith(f'_{nota_id}'):
                return subdir
    
    # Crea nuova cartella con timestamp
    if data_nota:
        timestamp = data_nota.strftime('%Y%m%d_%H%M%S')
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    suffix = f'_{nota_id}' if nota_id else ''
    return cliente_dir / f'{timestamp}{suffix}'


def trova_cartella_nota_esistente(base_dir, cliente, nota_id):
    """
    Cerca una cartella nota esistente per ID, indipendentemente dal timestamp.
    
    Args:
        base_dir: Path cartella base allegati
        cliente: dict con dati cliente  
        nota_id: ID della nota
        
    Returns:
        Path: percorso cartella se esiste, None altrimenti
    """
    cliente_dir = get_cartella_allegati_cliente(base_dir, cliente)
    
    if not cliente_dir.exists():
        return None
    
    for subdir in cliente_dir.iterdir():
        if subdir.is_dir() and subdir.name.endswith(f'_{nota_id}'):
            return subdir
    
    # Cerca anche nelle vecchie strutture (cartella = nota_id)
    old_dir = Path(base_dir) / str(nota_id)
    if old_dir.exists():
        return old_dir
    
    return None


# ==============================================================================
# UTILITY URL
# ==============================================================================

def url_cliente(cliente, base_url='/cerca/'):
    """
    Genera l'URL per la pagina cliente.
    
    Args:
        cliente: dict con dati cliente
        base_url: URL base (default '/c/')
        
    Returns:
        str: URL completo (es. '/c/IT00552060980')
    """
    ident = get_identificativo_cliente(cliente)
    if ident:
        return f"{base_url}{ident}"
    
    # Fallback a vecchio URL con ID
    if isinstance(cliente, dict) and 'id' in cliente:
        return f"/cliente/{cliente['id']}"
    
    return None


def url_api_cliente(cliente, base_url='/api/cliente/'):
    """
    Genera l'URL API per il cliente.
    
    Returns:
        str: URL API (es. '/api/cliente/IT00552060980')
    """
    ident = get_identificativo_cliente(cliente)
    if ident:
        return f"{base_url}{ident}"
    return None


# ==============================================================================
# TEST / DEBUG
# ==============================================================================

def test_identificativi():
    """Test delle funzioni di normalizzazione."""
    
    test_cases = [
        # P.IVA
        {'p_iva': '00552060980', 'cod_fiscale': None},  # Senza IT
        {'p_iva': 'IT00552060980', 'cod_fiscale': None},  # Con IT
        {'p_iva': 'it 0055206 0980', 'cod_fiscale': None},  # Spazi e lowercase
        
        # CF persona
        {'p_iva': None, 'cod_fiscale': 'RSSMRA80A01F205X'},
        {'p_iva': None, 'cod_fiscale': 'rssmra80a01f205x'},  # lowercase
        
        # Entrambi (P.IVA ha priorità)
        {'p_iva': 'IT00552060980', 'cod_fiscale': 'RSSMRA80A01F205X'},
        
        # Nessuno
        {'p_iva': None, 'cod_fiscale': None, 'id': 123},
        
        # Non validi
        {'p_iva': '123', 'cod_fiscale': 'ABC'},
    ]
    
    print("Test normalizzazione identificativi:")
    print("-" * 60)
    
    for i, test in enumerate(test_cases, 1):
        ident = get_identificativo_cliente(test)
        tipo = get_tipo_identificativo(ident) if ident else 'NONE'
        print(f"{i}. P.IVA={test.get('p_iva')}, CF={test.get('cod_fiscale')}")
        print(f"   → {ident} ({tipo})")
        print()


if __name__ == '__main__':
    test_identificativi()
