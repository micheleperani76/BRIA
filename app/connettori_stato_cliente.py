#!/usr/bin/env python3
# ==============================================================================
# CONNETTORI STATO CLIENTE - Modulo Indicatori Lista Clienti
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-22
# Descrizione: Connettore centralizzato per recuperare lo stato degli indicatori
#              da mostrare nella lista clienti. NON duplica logica, si interfaccia
#              con i meccanismi esistenti.
#
# ARCHITETTURA:
#   - Ogni indicatore e' registrato in INDICATORI_REGISTRY
#   - Funzioni get_*_singolo() per singolo cliente
#   - Funzioni get_*_bulk() per lista clienti (efficienza)
#   - Interfaccia uniforme: get_indicatori_clienti_bulk()
#
# COME AGGIUNGERE UN NUOVO INDICATORE:
#   1. Creare funzione get_NOME_singolo(conn, cliente) -> dict
#   2. Creare funzione get_NOME_bulk(conn, clienti) -> {cliente_id: dict}
#   3. Registrare in INDICATORI_REGISTRY con registra_indicatore()
#
# POSIZIONI RISERVATE:
#   1 - Car Policy
#   2 - Documenti Scadenza
#   3 - Trattativa (futuro)
#   4-6 - Riservate espansioni future
#   7 - Referente principale (gestito nel template, non qui)
#   8 - Dettaglio (sempre presente, gestito nel template)
#
# ==============================================================================

from datetime import datetime, date
from pathlib import Path

# Import configurazione percorsi
from app.config import CLIENTI_DIR, CLIENTI_PIVA_DIR, CLIENTI_CF_DIR, pulisci_piva
from app.database import get_connection

# ==============================================================================
# REGISTRY INDICATORI
# ==============================================================================
# Ogni indicatore ha:
#   - nome: identificativo univoco
#   - icona: classe Bootstrap Icons (o icona_base + stati per tipo 'stato')
#   - posizione: ordine nella colonna azioni (1 = prima a sinistra)
#   - tipo: 'presenza' (appare/non appare) o 'stato' (colori diversi)
#   - stati: dizionario {stato: {icona, colore, tooltip}} per tipo 'stato'
#   - tooltip: tooltip fisso per tipo 'presenza'
#   - colore: classe colore per tipo 'presenza'
#   - get_singolo: funzione per singolo cliente
#   - get_bulk: funzione per lista clienti (efficienza)
#   - attivo: True/False (False = predisposto ma non attivo)
# ==============================================================================

INDICATORI_REGISTRY = {}


def registra_indicatore(nome, config):
    """Registra un indicatore nel registry."""
    INDICATORI_REGISTRY[nome] = config


# ==============================================================================
# INDICATORE: CAR POLICY
# ==============================================================================
# Tipo: presenza (appare solo se il cliente ha almeno 1 car policy)
# Fonte: filesystem (cartella car-policy del cliente)
# ==============================================================================

def _get_cliente_carpolicy_path(cliente):
    """Costruisce il path della cartella car-policy per un cliente."""
    # Priorita: P.IVA > Codice Fiscale
    # Usa pulisci_piva per rimuovere prefisso IT e spazi
    piva = cliente.get('p_iva', '')
    cf = cliente.get('cod_fiscale', '').strip() if cliente.get('cod_fiscale') else ''
    
    # Pulisci P.IVA (rimuove IT, spazi, ecc.)
    piva_clean = pulisci_piva(piva)
    
    if piva_clean:
        return CLIENTI_PIVA_DIR / piva_clean / 'car-policy'
    elif cf:
        cf_clean = ''.join(c for c in cf if c.isalnum())
        return CLIENTI_CF_DIR / cf_clean / 'car-policy'
    return None


def _has_files_in_folder(folder_path):
    """Verifica se una cartella contiene almeno un file."""
    if not folder_path or not folder_path.exists():
        return False
    try:
        for f in folder_path.iterdir():
            if f.is_file() and not f.name.startswith('_'):
                return True
    except Exception:
        pass
    return False


def get_car_policy_singolo(conn, cliente):
    """
    Verifica se un cliente ha car policy.
    
    Returns:
        dict: {'presente': True/False}
    """
    path = _get_cliente_carpolicy_path(cliente)
    return {'presente': _has_files_in_folder(path)}


def get_car_policy_bulk(conn, clienti):
    """
    Verifica car policy per una lista di clienti.
    
    Args:
        conn: connessione DB (non usata ma mantenuta per interfaccia uniforme)
        clienti: lista di dizionari cliente
    
    Returns:
        dict: {cliente_id: {'presente': True/False}}
    """
    risultati = {}
    for cliente in clienti:
        cliente_id = cliente.get('id')
        if cliente_id:
            risultati[cliente_id] = get_car_policy_singolo(conn, cliente)
    return risultati


# Registrazione indicatore Car Policy
registra_indicatore('car_policy', {
    'nome': 'Car Policy',
    'icona': 'bi-file-earmark-text',
    'posizione': 1,
    'tipo': 'presenza',
    'tooltip': 'Car Policy presente',
    'colore': 'text-primary',
    'get_singolo': get_car_policy_singolo,
    'get_bulk': get_car_policy_bulk,
    'attivo': True
})


# ==============================================================================
# INDICATORE: DOCUMENTI SCADENZA
# ==============================================================================
# Tipo: stato (colore variabile: verde/giallo/rosso)
# Fonte: tabella documenti_cliente nel DB
# Logica scadenza (IMPORTATA da routes_documenti_strutturati):
#   - giorni < 0: scaduto (rosso)
#   - giorni <= 30: in_scadenza (giallo)
#   - giorni > 30: ok (verde)
#   - nessun documento con scadenza: null (non mostrare)
# ==============================================================================

def _calcola_giorni_scadenza(data_scadenza):
    """
    Calcola i giorni alla scadenza.
    NOTA: Logica identica a routes_documenti_strutturati.calcola_giorni_scadenza()
    """
    if not data_scadenza:
        return None
    try:
        if isinstance(data_scadenza, str):
            data_scadenza = datetime.strptime(data_scadenza, '%Y-%m-%d').date()
        oggi = date.today()
        delta = data_scadenza - oggi
        return delta.days
    except Exception:
        return None


def _calcola_stato_da_giorni(giorni):
    """
    Determina lo stato in base ai giorni alla scadenza.
    NOTA: Soglie identiche a routes_documenti_strutturati
    """
    if giorni is None:
        return None
    if giorni < 0:
        return 'scaduto'
    elif giorni <= 30:
        return 'in_scadenza'
    else:
        return 'ok'


def get_documenti_scadenza_singolo(conn, cliente):
    """
    Calcola lo stato documenti per un singolo cliente.
    
    Returns:
        dict: {
            'stato': 'ok'|'in_scadenza'|'scaduto'|None,
            'giorni_min': int|None (giorni al documento piu' urgente)
        }
    """
    cliente_id = cliente.get('id')
    if not cliente_id:
        return {'stato': None, 'giorni_min': None}
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data_scadenza 
        FROM documenti_cliente 
        WHERE cliente_id = ? AND data_scadenza IS NOT NULL AND data_scadenza != ''
    """, (cliente_id,))
    
    rows = cursor.fetchall()
    
    if not rows:
        return {'stato': None, 'giorni_min': None}
    
    # Trova il documento con scadenza piu' urgente
    giorni_min = None
    
    for row in rows:
        data_scad = row[0] if isinstance(row, tuple) else row['data_scadenza']
        giorni = _calcola_giorni_scadenza(data_scad)
        
        if giorni is not None:
            if giorni_min is None or giorni < giorni_min:
                giorni_min = giorni
    
    stato_peggiore = _calcola_stato_da_giorni(giorni_min)
    
    return {
        'stato': stato_peggiore,
        'giorni_min': giorni_min
    }


def get_documenti_scadenza_bulk(conn, clienti):
    """
    Calcola lo stato documenti per una lista di clienti in modo efficiente.
    Una sola query per tutti i clienti.
    
    Returns:
        dict: {cliente_id: {'stato': ..., 'giorni_min': ...}}
    """
    if not clienti:
        return {}
    
    cliente_ids = [c.get('id') for c in clienti if c.get('id')]
    if not cliente_ids:
        return {}
    
    # Query bulk: recupera tutte le scadenze per tutti i clienti
    placeholders = ','.join(['?' for _ in cliente_ids])
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT cliente_id, data_scadenza 
        FROM documenti_cliente 
        WHERE cliente_id IN ({placeholders}) 
          AND data_scadenza IS NOT NULL 
          AND data_scadenza != ''
    """, cliente_ids)
    
    # Raggruppa scadenze per cliente
    scadenze_per_cliente = {}
    for row in cursor.fetchall():
        cid = row[0] if isinstance(row, tuple) else row['cliente_id']
        data_scad = row[1] if isinstance(row, tuple) else row['data_scadenza']
        
        if cid not in scadenze_per_cliente:
            scadenze_per_cliente[cid] = []
        scadenze_per_cliente[cid].append(data_scad)
    
    # Calcola stato per ogni cliente
    risultati = {}
    for cliente_id in cliente_ids:
        if cliente_id not in scadenze_per_cliente:
            risultati[cliente_id] = {'stato': None, 'giorni_min': None}
            continue
        
        giorni_min = None
        for data_scad in scadenze_per_cliente[cliente_id]:
            giorni = _calcola_giorni_scadenza(data_scad)
            if giorni is not None:
                if giorni_min is None or giorni < giorni_min:
                    giorni_min = giorni
        
        stato = _calcola_stato_da_giorni(giorni_min)
        risultati[cliente_id] = {
            'stato': stato,
            'giorni_min': giorni_min
        }
    
    return risultati


# Registrazione indicatore Documenti Scadenza
registra_indicatore('documenti_scadenza', {
    'nome': 'Stato Documenti',
    'icona_base': 'bi-file-earmark-medical',
    'posizione': 2,
    'tipo': 'stato',
    'stati': {
        'ok': {
            'icona': 'bi-file-earmark-check',
            'colore': 'text-success',
            'tooltip': 'Documenti in regola'
        },
        'in_scadenza': {
            'icona': 'bi-file-earmark-excel',
            'colore': 'text-warning',
            'tooltip': 'Documenti in scadenza'
        },
        'scaduto': {
            'icona': 'bi-file-earmark-x',
            'colore': 'text-danger',
            'tooltip': 'Documenti scaduti'
        }
    },
    'get_singolo': get_documenti_scadenza_singolo,
    'get_bulk': get_documenti_scadenza_bulk,
    'attivo': True
})


# ==============================================================================
# INDICATORE: TRATTATIVA IN CORSO (PREDISPOSTO - NON ATTIVO)
# ==============================================================================
# Tipo: presenza (appare solo se c'e' una trattativa attiva)
# Fonte: FUTURO - tabella quotazioni/trattative
# Stato: predisposto, restituisce sempre False, attivo=False
# ==============================================================================

def get_trattativa_singolo(conn, cliente):
    """
    Verifica se un cliente ha una trattativa in corso (non chiusa, non cancellata).
    Usa config_trattative per determinare quali stati sono 'chiusi'.
    
    Returns:
        dict: {'presente': True/False, 'count': int}
    """
    from app.config_trattative import get_stati_chiusi
    
    cliente_id = cliente.get('id')
    if not cliente_id:
        return {'presente': False, 'count': 0}
    
    # Recupera stati chiusi da Excel
    stati_chiusi = get_stati_chiusi()
    
    cursor = conn.cursor()
    
    if stati_chiusi:
        # Escludi trattative con stati chiusi e cancellate
        placeholders = ','.join('?' * len(stati_chiusi))
        cursor.execute(f"""
            SELECT COUNT(*) FROM trattative 
            WHERE cliente_id = ? 
              AND stato NOT IN ({placeholders})
              AND (cancellata IS NULL OR cancellata = 0)
        """, [cliente_id] + stati_chiusi)
    else:
        # Nessuno stato chiuso configurato, conta tutte non cancellate
        cursor.execute("""
            SELECT COUNT(*) FROM trattative 
            WHERE cliente_id = ? AND (cancellata IS NULL OR cancellata = 0)
        """, (cliente_id,))
    
    count = cursor.fetchone()[0]
    return {'presente': count > 0, 'count': count}


def get_trattativa_bulk(conn, clienti):
    """
    Verifica trattative in corso per una lista di clienti (escluse cancellate).
    Query bulk efficiente per performance.
    
    Returns:
        dict: {cliente_id: {'presente': True/False, 'count': int}}
    """
    from app.config_trattative import get_stati_chiusi
    
    if not clienti:
        return {}
    
    clienti_ids = [c.get('id') for c in clienti if c.get('id')]
    if not clienti_ids:
        return {}
    
    # Inizializza risultati
    risultati = {cid: {'presente': False, 'count': 0} for cid in clienti_ids}
    
    # Recupera stati chiusi da Excel
    stati_chiusi = get_stati_chiusi()
    
    cursor = conn.cursor()
    placeholders_clienti = ','.join('?' * len(clienti_ids))
    
    if stati_chiusi:
        # Escludi trattative con stati chiusi e cancellate
        placeholders_stati = ','.join('?' * len(stati_chiusi))
        cursor.execute(f"""
            SELECT cliente_id, COUNT(*) as cnt
            FROM trattative 
            WHERE cliente_id IN ({placeholders_clienti}) 
              AND stato NOT IN ({placeholders_stati})
              AND (cancellata IS NULL OR cancellata = 0)
            GROUP BY cliente_id
        """, clienti_ids + stati_chiusi)
    else:
        # Nessuno stato chiuso configurato, conta tutte non cancellate
        cursor.execute(f"""
            SELECT cliente_id, COUNT(*) as cnt
            FROM trattative 
            WHERE cliente_id IN ({placeholders_clienti})
              AND (cancellata IS NULL OR cancellata = 0)
            GROUP BY cliente_id
        """, clienti_ids)
    
    for row in cursor.fetchall():
        cid = row[0]
        cnt = row[1]
        if cid in risultati:
            risultati[cid] = {'presente': cnt > 0, 'count': cnt}
    
    return risultati


# ==============================================================================
# INDICATORE: COLLEGAMENTI CLIENTI
# ==============================================================================

def get_collegamenti_singolo(conn, cliente):
    """Verifica se un cliente ha collegamenti attivi."""
    cliente_id = cliente.get('id')
    if not cliente_id:
        return {'presente': False}
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM collegamenti_clienti
        WHERE (cliente_a_id = ? OR cliente_b_id = ?) AND attivo = 1
    ''', (cliente_id, cliente_id))
    
    count = cursor.fetchone()[0]
    return {'presente': count > 0}


def get_collegamenti_bulk(conn, clienti):
    """Verifica collegamenti per una lista di clienti."""
    if not clienti:
        return {}
    
    clienti_ids = [c.get('id') for c in clienti if c.get('id')]
    if not clienti_ids:
        return {}
    
    risultati = {cid: {'presente': False} for cid in clienti_ids}
    
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(clienti_ids))
    
    cursor.execute(f'''
        SELECT DISTINCT cliente_a_id as cid FROM collegamenti_clienti
        WHERE cliente_a_id IN ({placeholders}) AND attivo = 1
        UNION
        SELECT DISTINCT cliente_b_id as cid FROM collegamenti_clienti
        WHERE cliente_b_id IN ({placeholders}) AND attivo = 1
    ''', clienti_ids + clienti_ids)
    
    for row in cursor.fetchall():
        if row[0] in risultati:
            risultati[row[0]] = {'presente': True}
    
    return risultati


registra_indicatore('collegamenti', {
    'nome': 'Collegamenti',
    'icona': 'bi-diagram-3',
    'posizione': 3,
    'tipo': 'presenza',
    'tooltip': 'Ha collegamenti con altri clienti',
    'colore': 'text-success',
    'get_singolo': get_collegamenti_singolo,
    'get_bulk': get_collegamenti_bulk,
    'attivo': True
})

# Registrazione indicatore Trattativa (ATTIVO)
registra_indicatore('trattativa', {
    'nome': 'Trattativa in corso',
    'icona': 'bi-briefcase',
    'posizione': 4,
    'tipo': 'presenza',
    'tooltip': 'Trattativa in corso',
    'colore': 'text-info',
    'get_singolo': get_trattativa_singolo,
    'get_bulk': get_trattativa_bulk,
    'attivo': True  # ATTIVATO
})

# ==============================================================================
# INDICATORE: TOP PROSPECT
# ==============================================================================
# Tipo: stato (grigio = candidato, oro = confermato)
# Posizione: 6 (ultima prima di referente e dettaglio)

def get_top_prospect_singolo(conn, cliente):
    """
    Verifica se un cliente è Top Prospect.
    
    Returns:
        dict: {
            'presente': True/False,
            'stato': 'candidato'/'confermato'/None,
            'priorita': int/None
        }
    """
    cliente_id = cliente.get('id')
    if not cliente_id:
        return {'presente': False, 'stato': None, 'priorita': None}
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stato, priorita 
        FROM top_prospect 
        WHERE cliente_id = ? AND stato IN ('candidato', 'confermato')
    ''', (cliente_id,))
    
    row = cursor.fetchone()
    if row:
        return {
            'presente': True,
            'stato': row['stato'],
            'priorita': row['priorita']
        }
    
    return {'presente': False, 'stato': None, 'priorita': None}


def get_top_prospect_bulk(conn, clienti):
    """
    Recupera stato Top Prospect per lista clienti.
    """
    if not clienti:
        return {}
    
    cliente_ids = [c.get('id') for c in clienti if c.get('id')]
    if not cliente_ids:
        return {}
    
    # Inizializza tutti a False
    risultati = {cid: {'presente': False, 'stato': None, 'priorita': None} for cid in cliente_ids}
    
    cursor = conn.cursor()
    placeholders = ','.join(['?' for _ in cliente_ids])
    cursor.execute(f'''
        SELECT cliente_id, stato, priorita 
        FROM top_prospect 
        WHERE cliente_id IN ({placeholders}) AND stato IN ('candidato', 'confermato')
    ''', cliente_ids)
    
    for row in cursor.fetchall():
        risultati[row['cliente_id']] = {
            'presente': True,
            'stato': row['stato'],
            'priorita': row['priorita']
        }
    
    return risultati


registra_indicatore('top_prospect', {
    'nome': 'Top Prospect',
    'icona': 'bi-trophy',
    'posizione': 6,
    'tipo': 'stato',
    'tooltip': 'Top Prospect',
    'colore': 'text-warning',
    'get_singolo': get_top_prospect_singolo,
    'get_bulk': get_top_prospect_bulk,
    'attivo': True
})


# ==============================================================================
# SLOT RISERVATI PER FUTURE ESPANSIONI (posizioni 4-6)
# ==============================================================================
# Esempi possibili:
#   - posizione 4: "Preventivo da confermare"
#   - posizione 5: "Contratto in scadenza"
#   - posizione 6: "Richiesta assistenza aperta"
#
# Per aggiungere un nuovo indicatore:
#   1. Creare funzione get_NOME_singolo(conn, cliente) -> dict
#   2. Creare funzione get_NOME_bulk(conn, clienti) -> {cliente_id: dict}
#   3. Chiamare registra_indicatore('nome', {...})
# ==============================================================================


# ==============================================================================
# FUNZIONE PRINCIPALE: RECUPERO BULK TUTTI GLI INDICATORI
# ==============================================================================

def get_indicatori_clienti_bulk(conn, clienti, indicatori_richiesti=None):
    """
    Recupera tutti gli indicatori per una lista di clienti.
    
    Args:
        conn: connessione database
        clienti: lista di dizionari cliente (devono avere 'id', 'p_iva', 'cod_fiscale')
        indicatori_richiesti: lista nomi indicatori (None = tutti gli attivi)
    
    Returns:
        dict: {
            cliente_id: {
                'car_policy': {'presente': True/False},
                'documenti_scadenza': {'stato': ..., 'giorni_min': ...},
                ...
            }
        }
    
    Esempio uso nel template Jinja2:
        {% set ind = indicatori_cliente[cliente.id] %}
        {% if ind.car_policy.presente %}
            <i class="bi bi-file-earmark-text text-primary" title="Car Policy presente"></i>
        {% endif %}
        {% if ind.documenti_scadenza.stato == 'scaduto' %}
            <i class="bi bi-file-earmark-x text-danger" title="Documenti scaduti"></i>
        {% endif %}
    """
    if not clienti:
        return {}
    
    # Determina quali indicatori recuperare
    if indicatori_richiesti is None:
        # Tutti gli indicatori attivi
        indicatori_da_usare = {
            nome: config 
            for nome, config in INDICATORI_REGISTRY.items() 
            if config.get('attivo', True)
        }
    else:
        indicatori_da_usare = {
            nome: INDICATORI_REGISTRY[nome] 
            for nome in indicatori_richiesti 
            if nome in INDICATORI_REGISTRY
        }
    
    # Inizializza risultati
    risultati = {c.get('id'): {} for c in clienti if c.get('id')}
    
    # Recupera ogni indicatore con la sua funzione bulk
    for nome, config in indicatori_da_usare.items():
        get_bulk_fn = config.get('get_bulk')
        if get_bulk_fn:
            dati_indicatore = get_bulk_fn(conn, clienti)
            for cliente_id, valore in dati_indicatore.items():
                if cliente_id in risultati:
                    risultati[cliente_id][nome] = valore
    
    return risultati


def get_indicatori_cliente_singolo(conn, cliente, indicatori_richiesti=None):
    """
    Recupera tutti gli indicatori per un singolo cliente.
    Utile per aggiornamenti AJAX o pagina dettaglio.
    
    Returns:
        dict: {
            'car_policy': {'presente': True/False},
            'documenti_scadenza': {'stato': ..., 'giorni_min': ...},
            ...
        }
    """
    if indicatori_richiesti is None:
        indicatori_da_usare = {
            nome: config 
            for nome, config in INDICATORI_REGISTRY.items() 
            if config.get('attivo', True)
        }
    else:
        indicatori_da_usare = {
            nome: INDICATORI_REGISTRY[nome] 
            for nome in indicatori_richiesti 
            if nome in INDICATORI_REGISTRY
        }
    
    risultati = {}
    for nome, config in indicatori_da_usare.items():
        get_singolo_fn = config.get('get_singolo')
        if get_singolo_fn:
            risultati[nome] = get_singolo_fn(conn, cliente)
    
    return risultati


# ==============================================================================
# FUNZIONI HELPER PER CONFIGURAZIONE
# ==============================================================================

def get_config_indicatori():
    """
    Ritorna la configurazione di tutti gli indicatori registrati.
    Utile per il frontend (icone, colori, tooltip).
    
    Returns:
        dict: copia del registry senza funzioni (serializzabile JSON)
    """
    config = {}
    for nome, ind in INDICATORI_REGISTRY.items():
        config[nome] = {k: v for k, v in ind.items() if not callable(v)}
    return config


def get_indicatori_ordinati():
    """
    Ritorna lista indicatori ordinata per posizione.
    Utile per rendering ordinato nel template.
    
    Returns:
        list: [(nome, config), ...] ordinata per posizione
    """
    return sorted(
        [(nome, {k: v for k, v in config.items() if not callable(v)}) 
         for nome, config in INDICATORI_REGISTRY.items()],
        key=lambda x: x[1].get('posizione', 99)
    )


def get_indicatori_attivi_ordinati():
    """
    Ritorna solo gli indicatori attivi, ordinati per posizione.
    
    Returns:
        list: [(nome, config), ...] solo attivi, ordinati
    """
    return [
        (nome, config) 
        for nome, config in get_indicatori_ordinati() 
        if config.get('attivo', True)
    ]


# ==============================================================================
# CONTEXT PROCESSOR PER JINJA2
# ==============================================================================

def indicatori_context_processor():
    """
    Context processor da registrare nell'app Flask.
    Inietta configurazione indicatori nel template.
    
    Uso in app Flask:
        from app.connettori_stato_cliente import indicatori_context_processor
        app.context_processor(indicatori_context_processor)
    
    Disponibile nei template:
        {{ INDICATORI_CONFIG }}
        {{ INDICATORI_ORDINATI }}
    """
    return {
        'INDICATORI_CONFIG': get_config_indicatori(),
        'INDICATORI_ORDINATI': get_indicatori_ordinati(),
        'INDICATORI_ATTIVI': get_indicatori_attivi_ordinati()
    }
