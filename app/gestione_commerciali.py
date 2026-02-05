#!/usr/bin/env python3
# ==============================================================================
# GESTIONE COMMERCIALI - Modulo Centralizzato
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-21
# Descrizione: Gestione centralizzata di tutto cio' che riguarda i commerciali
#
# QUESTO MODULO GESTISCE:
# - Lista commerciali per dropdown (assegnazione)
# - Lista commerciali per report (con clienti)
# - Conversione ID <-> Nome display
# - Verifica permessi e visibilita'
# - Registrazione storico assegnazioni
# - Logiche cambio ruolo
#
# REGOLA: MAI query dirette sui commerciali altrove - usare SEMPRE questo modulo
# ==============================================================================

from datetime import datetime

# ==============================================================================
# COSTANTI
# ==============================================================================

# Permesso richiesto per ricevere clienti in assegnazione
PERMESSO_ASSEGNABILE = 'clienti_assegnabili'

# ID operatore per operazioni automatiche (SYSTEM)
OPERATORE_SYSTEM = 0

# Tipi di operazione nello storico
TIPO_MANUALE = 'manuale'
TIPO_CAMBIO_RUOLO = 'cambio_ruolo'
TIPO_IMPORT = 'import'
TIPO_MIGRAZIONE = 'migrazione'


# ==============================================================================
# FUNZIONI DI FORMATTAZIONE
# ==============================================================================

def format_nome_commerciale(nome, cognome):
    """
    Formatta nome e cognome per display uniforme.
    
    Args:
        nome: "Michele" o "michele" o None
        cognome: "Perani" o "PERANI" o None
    
    Returns:
        str: "M. Perani" oppure solo cognome se nome manca
    
    Examples:
        >>> format_nome_commerciale("Michele", "Perani")
        'M. Perani'
        >>> format_nome_commerciale("paolo", "CIOTTI")
        'P. Ciotti'
        >>> format_nome_commerciale(None, "Rossi")
        'Rossi'
        >>> format_nome_commerciale("", "")
        'Non specificato'
    """
    if not cognome:
        return 'Non specificato'
    
    # Normalizza cognome: prima lettera maiuscola, resto minuscolo
    cognome_fmt = cognome.strip().capitalize()
    
    if not nome:
        return cognome_fmt
    
    # Iniziale nome + cognome
    iniziale = nome.strip()[0].upper()
    return f"{iniziale}. {cognome_fmt}"


def get_commerciale_display(conn, commerciale_id):
    """
    Restituisce il nome display di un commerciale dato il suo ID.
    
    Args:
        conn: Connessione database
        commerciale_id: ID utente (int) oppure None
    
    Returns:
        str: "M. Perani" oppure "Non assegnato" se None/0
    """
    if not commerciale_id:
        return 'Non assegnato'
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT nome, cognome FROM utenti WHERE id = ?
    ''', (commerciale_id,))
    
    row = cursor.fetchone()
    if not row:
        return 'Non assegnato'
    
    return format_nome_commerciale(row['nome'], row['cognome'])


def get_commerciale_display_bulk(conn, commerciale_ids):
    """
    Restituisce un dizionario ID -> nome display per piu' commerciali.
    Ottimizzato per evitare query multiple.
    
    Args:
        conn: Connessione database
        commerciale_ids: Lista di ID utenti
    
    Returns:
        dict: {id: "M. Perani", ...}
    """
    if not commerciale_ids:
        return {}
    
    # Rimuovi None e duplicati
    ids_validi = list(set(id for id in commerciale_ids if id))
    
    if not ids_validi:
        return {}
    
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(ids_validi))
    cursor.execute(f'''
        SELECT id, nome, cognome FROM utenti WHERE id IN ({placeholders})
    ''', ids_validi)
    
    result = {}
    for row in cursor.fetchall():
        result[row['id']] = format_nome_commerciale(row['nome'], row['cognome'])
    
    return result


# ==============================================================================
# FUNZIONI LISTA COMMERCIALI
# ==============================================================================

def get_commerciali_assegnabili(conn):
    """
    Lista commerciali per dropdown di assegnazione clienti.
    
    Criteri:
    - Utente attivo
    - Ha permesso 'clienti_assegnabili' abilitato
    - NON e' admin (ruolo_base != 'admin')
    
    Returns:
        list: [
            {'id': 2, 'display': 'P. Ciotti', 'username': 'p.ciotti', 'cognome': 'Ciotti'},
            {'id': 3, 'display': 'M. Perani', 'username': 'm.perani', 'cognome': 'Perani'},
            ...
        ]
        Ordinati per cognome
    """
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.id, u.username, u.nome, u.cognome
        FROM utenti u
        JOIN utenti_permessi up ON u.id = up.utente_id
        JOIN permessi_catalogo pc ON up.permesso_id = pc.id
        WHERE pc.codice = ?
          AND up.abilitato = 1
          AND u.attivo = 1
          AND u.ruolo_base != 'admin'
        ORDER BY u.cognome, u.nome
    ''', (PERMESSO_ASSEGNABILE,))
    
    result = []
    for row in cursor.fetchall():
        result.append({
            'id': row['id'],
            'display': format_nome_commerciale(row['nome'], row['cognome']),
            'username': row['username'],
            'cognome': row['cognome'] or ''
        })
    
    return result


def get_commerciali_con_clienti(conn):
    """
    Lista commerciali per report/statistiche.
    Solo chi ha almeno 1 cliente assegnato (tramite veicoli).
    
    Returns:
        list: [
            {'id': 3, 'display': 'M. Perani', 'num_clienti': 45, 'num_veicoli': 120},
            ...
        ]
        Ordinati per cognome
    """
    cursor = conn.cursor()
    
    # Query che conta clienti e veicoli per commerciale_id
    cursor.execute('''
        SELECT 
            u.id,
            u.nome,
            u.cognome,
            COUNT(DISTINCT v.p_iva) as num_clienti,
            COUNT(v.id) as num_veicoli
        FROM utenti u
        JOIN veicoli v ON v.commerciale_id = u.id
        WHERE u.attivo = 1
        GROUP BY u.id
        HAVING num_clienti > 0
        ORDER BY u.cognome, u.nome
    ''')
    
    result = []
    for row in cursor.fetchall():
        result.append({
            'id': row['id'],
            'display': format_nome_commerciale(row['nome'], row['cognome']),
            'num_clienti': row['num_clienti'],
            'num_veicoli': row['num_veicoli']
        })
    
    return result


def get_commerciali_tutti(conn, solo_attivi=True):
    """
    Lista tutti i commerciali (utenti con ruolo commerciale).
    
    Args:
        conn: Connessione database
        solo_attivi: Se True, solo utenti attivi
    
    Returns:
        list: [{'id': 2, 'display': 'P. Ciotti', 'username': 'p.ciotti', 'attivo': 1}, ...]
    """
    cursor = conn.cursor()
    
    query = '''
        SELECT id, username, nome, cognome, attivo
        FROM utenti
        WHERE ruolo_base = 'commerciale'
    '''
    
    if solo_attivi:
        query += ' AND attivo = 1'
    
    query += ' ORDER BY cognome, nome'
    
    cursor.execute(query)
    
    result = []
    for row in cursor.fetchall():
        result.append({
            'id': row['id'],
            'display': format_nome_commerciale(row['nome'], row['cognome']),
            'username': row['username'],
            'attivo': row['attivo']
        })
    
    return result


# ==============================================================================
# FUNZIONI VISIBILITA' E PERMESSI
# ==============================================================================

def get_clienti_visibili_ids(conn, user_id):
    """
    Restituisce lista P.IVA clienti che l'utente puo' vedere.
    
    Logica:
    - Admin: tutti
    - Commerciale: solo i suoi (commerciale_id = user_id)
    - Supervisore: suoi + quelli dei subordinati
    - Operatore con permesso clienti_visualizza: tutti
    
    Args:
        conn: Connessione database
        user_id: ID utente
    
    Returns:
        list: ['01234567890', '09876543210', ...] oppure None se vede tutti
    """
    cursor = conn.cursor()
    
    # Recupera info utente
    cursor.execute('''
        SELECT ruolo_base FROM utenti WHERE id = ?
    ''', (user_id,))
    
    row = cursor.fetchone()
    if not row:
        return []  # Utente non esiste
    
    ruolo = row['ruolo_base']
    
    # Admin vede tutto
    if ruolo == 'admin':
        return None  # None significa "tutti"
    
    # Verifica se ha permesso visualizza tutti (operatore backend)
    cursor.execute('''
        SELECT 1 FROM utenti_permessi up
        JOIN permessi_catalogo pc ON up.permesso_id = pc.id
        WHERE up.utente_id = ?
          AND pc.codice = 'clienti_visualizza_tutti'
          AND up.abilitato = 1
    ''', (user_id,))
    
    if cursor.fetchone():
        return None  # Vede tutti
    
    # Commerciale: suoi clienti + quelli dei subordinati
    ids_da_includere = [user_id]
    
    # Cerca subordinati attivi
    cursor.execute('''
        SELECT subordinato_id FROM supervisioni
        WHERE supervisore_id = ?
          AND data_fine IS NULL
    ''', (user_id,))
    
    for sub in cursor.fetchall():
        ids_da_includere.append(sub['subordinato_id'])
    
    # Recupera P.IVA clienti di questi commerciali
    placeholders = ','.join('?' * len(ids_da_includere))
    cursor.execute(f'''
        SELECT DISTINCT p_iva FROM veicoli
        WHERE commerciale_id IN ({placeholders})
          AND p_iva IS NOT NULL
    ''', ids_da_includere)
    
    return [row['p_iva'] for row in cursor.fetchall()]


def puo_vedere_cliente(conn, user_id, cliente_piva):
    """
    Verifica se l'utente puo' vedere un cliente specifico.
    
    Args:
        conn: Connessione database
        user_id: ID utente
        cliente_piva: P.IVA cliente
    
    Returns:
        bool: True se puo' vedere
    """
    visibili = get_clienti_visibili_ids(conn, user_id)
    
    if visibili is None:
        return True  # Vede tutti
    
    return cliente_piva in visibili


def get_commerciale_cliente(conn, cliente_piva):
    """
    Restituisce l'ID del commerciale assegnato a un cliente.
    
    Args:
        conn: Connessione database
        cliente_piva: P.IVA cliente
    
    Returns:
        int o None: ID commerciale oppure None se non assegnato
    """
    cursor = conn.cursor()
    
    # Cerca nei veicoli (fonte principale)
    cursor.execute('''
        SELECT commerciale_id FROM veicoli
        WHERE p_iva = ? AND commerciale_id IS NOT NULL
        LIMIT 1
    ''', (cliente_piva,))
    
    row = cursor.fetchone()
    return row['commerciale_id'] if row else None


# ==============================================================================
# FUNZIONI STORICO ASSEGNAZIONI
# ==============================================================================

def registra_assegnazione(conn, cliente_piva, cliente_nome,
                          commerciale_precedente_id, commerciale_nuovo_id,
                          operatore_id, note=None, tipo=TIPO_MANUALE):
    """
    Registra un'assegnazione nello storico.
    
    Args:
        conn: Connessione database
        cliente_piva: P.IVA cliente
        cliente_nome: Nome cliente (per leggibilita')
        commerciale_precedente_id: ID commerciale precedente (None se era non assegnato)
        commerciale_nuovo_id: ID nuovo commerciale (None se diventa non assegnato)
        operatore_id: ID utente che ha fatto l'operazione (0 = SYSTEM)
        note: Note opzionali
        tipo: Tipo operazione ('manuale', 'cambio_ruolo', 'import', 'migrazione')
    
    Returns:
        int: ID del record storico creato
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO storico_assegnazioni 
        (cliente_piva, cliente_nome, commerciale_precedente_id, commerciale_nuovo_id,
         operatore_id, data_ora, note, tipo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (cliente_piva, cliente_nome, commerciale_precedente_id, commerciale_nuovo_id,
          operatore_id, now, note, tipo))
    
    conn.commit()
    return cursor.lastrowid


def get_storico_cliente(conn, cliente_piva, limite=50):
    """
    Restituisce storico assegnazioni di un cliente.
    
    Args:
        conn: Connessione database
        cliente_piva: P.IVA cliente
        limite: Numero massimo record
    
    Returns:
        list: [
            {
                'data_ora': '2025-01-21 10:30:00',
                'da': 'M. Perani',
                'a': 'C. Pelucchi',
                'operatore': 'admin',
                'tipo': 'manuale',
                'note': '...'
            },
            ...
        ]
    """
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            sa.data_ora,
            sa.commerciale_precedente_id,
            sa.commerciale_nuovo_id,
            sa.operatore_id,
            sa.tipo,
            sa.note,
            u_op.username as operatore_username
        FROM storico_assegnazioni sa
        LEFT JOIN utenti u_op ON sa.operatore_id = u_op.id
        WHERE sa.cliente_piva = ?
        ORDER BY sa.data_ora DESC
        LIMIT ?
    ''', (cliente_piva, limite))
    
    result = []
    for row in cursor.fetchall():
        result.append({
            'data_ora': row['data_ora'],
            'da': get_commerciale_display(conn, row['commerciale_precedente_id']),
            'a': get_commerciale_display(conn, row['commerciale_nuovo_id']),
            'operatore': row['operatore_username'] or 'SYSTEM',
            'tipo': row['tipo'],
            'note': row['note']
        })
    
    return result


def get_storico_assegnazioni(conn, filtro_commerciale_id=None, 
                              filtro_operatore_id=None, limite=100):
    """
    Recupera lo storico assegnazioni con filtri opzionali.
    
    Args:
        conn: Connessione database
        filtro_commerciale_id: Filtra per commerciale (nuovo o precedente)
        filtro_operatore_id: Filtra per operatore
        limite: Numero massimo record
    
    Returns:
        list: Lista di dict con storico
    """
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            sa.*,
            u_op.username as operatore_username
        FROM storico_assegnazioni sa
        LEFT JOIN utenti u_op ON sa.operatore_id = u_op.id
        WHERE 1=1
    '''
    params = []
    
    if filtro_commerciale_id:
        query += ' AND (sa.commerciale_nuovo_id = ? OR sa.commerciale_precedente_id = ?)'
        params.extend([filtro_commerciale_id, filtro_commerciale_id])
    
    if filtro_operatore_id:
        query += ' AND sa.operatore_id = ?'
        params.append(filtro_operatore_id)
    
    query += ' ORDER BY sa.data_ora DESC LIMIT ?'
    params.append(limite)
    
    cursor.execute(query, params)
    
    result = []
    for row in cursor.fetchall():
        result.append({
            'id': row['id'],
            'cliente_piva': row['cliente_piva'],
            'cliente_nome': row['cliente_nome'],
            'data_ora': row['data_ora'],
            'da': get_commerciale_display(conn, row['commerciale_precedente_id']),
            'a': get_commerciale_display(conn, row['commerciale_nuovo_id']),
            'operatore': row['operatore_username'] or 'SYSTEM',
            'tipo': row['tipo'],
            'note': row['note']
        })
    
    return result


# ==============================================================================
# FUNZIONI ASSEGNAZIONE CLIENTI
# ==============================================================================

def assegna_cliente(conn, cliente_piva, cliente_nome, nuovo_commerciale_id, 
                    operatore_id, note=None):
    """
    Assegna un cliente a un commerciale.
    Aggiorna veicoli e clienti, registra nello storico.
    
    Args:
        conn: Connessione database
        cliente_piva: P.IVA cliente
        cliente_nome: Nome cliente
        nuovo_commerciale_id: ID nuovo commerciale (None per rimuovere assegnazione)
        operatore_id: ID utente che fa l'operazione
        note: Note opzionali
    
    Returns:
        dict: {'successo': True, 'veicoli_aggiornati': N, 'messaggio': '...'}
    """
    cursor = conn.cursor()
    
    # Trova commerciale precedente
    commerciale_precedente_id = get_commerciale_cliente(conn, cliente_piva)
    
    # Se non cambia nulla, esci
    if commerciale_precedente_id == nuovo_commerciale_id:
        return {
            'successo': True,
            'veicoli_aggiornati': 0,
            'messaggio': 'Nessuna modifica necessaria'
        }
    
    # Aggiorna veicoli
    cursor.execute('''
        UPDATE veicoli SET commerciale_id = ? WHERE p_iva = ?
    ''', (nuovo_commerciale_id, cliente_piva))
    
    veicoli_aggiornati = cursor.rowcount
    
    # Aggiorna anche tabella clienti se presente
    cursor.execute('''
        UPDATE clienti SET commerciale_id = ?, data_ultimo_aggiornamento = ?
        WHERE p_iva = ?
    ''', (nuovo_commerciale_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cliente_piva))
    
    # Registra nello storico
    registra_assegnazione(
        conn, cliente_piva, cliente_nome,
        commerciale_precedente_id, nuovo_commerciale_id,
        operatore_id, note, TIPO_MANUALE
    )
    
    conn.commit()
    
    # Prepara messaggio
    nuovo_display = get_commerciale_display(conn, nuovo_commerciale_id)
    
    return {
        'successo': True,
        'veicoli_aggiornati': veicoli_aggiornati,
        'messaggio': f'Cliente assegnato a {nuovo_display}'
    }


def trasferisci_clienti_commerciale(conn, da_commerciale_id, a_commerciale_id,
                                     operatore_id, tipo=TIPO_MANUALE):
    """
    Trasferisce TUTTI i clienti da un commerciale a un altro.
    Usato per cambio ruolo o trasferimento massivo.
    
    Args:
        conn: Connessione database
        da_commerciale_id: ID commerciale sorgente
        a_commerciale_id: ID commerciale destinazione (None = non assegnato)
        operatore_id: ID utente che fa l'operazione
        tipo: Tipo operazione
    
    Returns:
        dict: {'successo': True, 'clienti_trasferiti': N, 'dettagli': [...]}
    """
    cursor = conn.cursor()
    
    # Trova tutti i clienti del commerciale sorgente
    cursor.execute('''
        SELECT DISTINCT p_iva FROM veicoli
        WHERE commerciale_id = ? AND p_iva IS NOT NULL
    ''', (da_commerciale_id,))
    
    clienti = [row['p_iva'] for row in cursor.fetchall()]
    
    if not clienti:
        return {
            'successo': True,
            'clienti_trasferiti': 0,
            'dettagli': []
        }
    
    dettagli = []
    
    for piva in clienti:
        # Recupera nome cliente
        cursor.execute('''
            SELECT nome_cliente FROM clienti WHERE p_iva = ?
        ''', (piva,))
        row = cursor.fetchone()
        nome = row['nome_cliente'] if row else piva
        
        # Aggiorna veicoli
        cursor.execute('''
            UPDATE veicoli SET commerciale_id = ? WHERE p_iva = ?
        ''', (a_commerciale_id, piva))
        
        # Aggiorna clienti
        cursor.execute('''
            UPDATE clienti SET commerciale_id = ?, data_ultimo_aggiornamento = ?
            WHERE p_iva = ?
        ''', (a_commerciale_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), piva))
        
        # Registra nello storico
        registra_assegnazione(
            conn, piva, nome,
            da_commerciale_id, a_commerciale_id,
            operatore_id, f'Trasferimento massivo da {get_commerciale_display(conn, da_commerciale_id)}',
            tipo
        )
        
        dettagli.append({'piva': piva, 'nome': nome})
    
    conn.commit()
    
    return {
        'successo': True,
        'clienti_trasferiti': len(clienti),
        'dettagli': dettagli
    }


# ==============================================================================
# FUNZIONI CAMBIO RUOLO
# ==============================================================================

def conta_clienti_commerciale(conn, commerciale_id):
    """
    Conta quanti clienti ha un commerciale.
    
    Returns:
        int: Numero clienti
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(DISTINCT p_iva) as num FROM veicoli
        WHERE commerciale_id = ? AND p_iva IS NOT NULL
    ''', (commerciale_id,))
    
    return cursor.fetchone()['num']


def get_supervisore_di(conn, utente_id):
    """
    Trova il supervisore attivo di un utente.
    
    Returns:
        dict o None: {'id': X, 'display': 'P. Ciotti'} oppure None
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.supervisore_id, u.nome, u.cognome
        FROM supervisioni s
        JOIN utenti u ON s.supervisore_id = u.id
        WHERE s.subordinato_id = ?
          AND s.data_fine IS NULL
          AND u.attivo = 1
        LIMIT 1
    ''', (utente_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return {
        'id': row['supervisore_id'],
        'display': format_nome_commerciale(row['nome'], row['cognome'])
    }


def puo_cambiare_ruolo_da_commerciale(conn, utente_id):
    """
    Verifica se un commerciale puo' cambiare ruolo e cosa succedera'.
    
    Returns:
        dict: {
            'puo_cambiare': True,
            'clienti_assegnati': 45,
            'ha_supervisore': True,
            'supervisore_id': 2,
            'supervisore_display': 'P. Ciotti',
            'destinazione': 'P. Ciotti' oppure 'Non assegnato',
            'messaggio': '45 clienti verranno trasferiti a P. Ciotti'
        }
    """
    num_clienti = conta_clienti_commerciale(conn, utente_id)
    supervisore = get_supervisore_di(conn, utente_id)
    
    result = {
        'puo_cambiare': True,
        'clienti_assegnati': num_clienti,
        'ha_supervisore': supervisore is not None,
        'supervisore_id': supervisore['id'] if supervisore else None,
        'supervisore_display': supervisore['display'] if supervisore else None,
    }
    
    if num_clienti == 0:
        result['destinazione'] = None
        result['messaggio'] = 'Nessun cliente da trasferire'
    elif supervisore:
        result['destinazione'] = supervisore['display']
        result['messaggio'] = f'{num_clienti} clienti verranno trasferiti a {supervisore["display"]}'
    else:
        result['destinazione'] = 'Non assegnato'
        result['messaggio'] = f'Attenzione: {num_clienti} clienti diventeranno non assegnati'
    
    return result


def gestisci_cambio_ruolo_commerciale(conn, utente_id, operatore_id):
    """
    Gestisce il trasferimento clienti quando un commerciale cambia ruolo.
    
    Logica:
    1. Conta clienti assegnati
    2. Se ha supervisore: trasferisce a lui
    3. Se non ha supervisore: clienti vanno a "non assegnato"
    4. Registra tutto nello storico
    
    Args:
        conn: Connessione database
        utente_id: ID del commerciale che cambia ruolo
        operatore_id: ID di chi sta facendo l'operazione
    
    Returns:
        dict: {
            'successo': True,
            'clienti_trasferiti': 45,
            'destinazione_id': 2 oppure None,
            'destinazione_display': 'P. Ciotti' oppure 'Non assegnato'
        }
    """
    info = puo_cambiare_ruolo_da_commerciale(conn, utente_id)
    
    if info['clienti_assegnati'] == 0:
        return {
            'successo': True,
            'clienti_trasferiti': 0,
            'destinazione_id': None,
            'destinazione_display': None
        }
    
    # Trasferisci clienti
    dest_id = info['supervisore_id']  # None se non ha supervisore
    
    result = trasferisci_clienti_commerciale(
        conn, utente_id, dest_id,
        operatore_id, TIPO_CAMBIO_RUOLO
    )
    
    return {
        'successo': result['successo'],
        'clienti_trasferiti': result['clienti_trasferiti'],
        'destinazione_id': dest_id,
        'destinazione_display': info['destinazione']
    }


# ==============================================================================
# FUNZIONI MIGRAZIONE (da stringhe legacy a ID)
# ==============================================================================

def get_id_da_cognome_legacy(conn, cognome):
    """
    Per migrazione: converte cognome legacy (PELUCCHI) in ID utente.
    
    Args:
        conn: Connessione database
        cognome: Cognome in maiuscolo (es: "PELUCCHI")
    
    Returns:
        int o None: ID utente oppure None se non trovato
    """
    if not cognome:
        return None
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM utenti
        WHERE UPPER(cognome) = UPPER(?)
          AND ruolo_base = 'commerciale'
        LIMIT 1
    ''', (cognome.strip(),))
    
    row = cursor.fetchone()
    return row['id'] if row else None


def migra_commerciali_veicoli(conn, mapping, operatore_id=OPERATORE_SYSTEM, dry_run=False):
    """
    Migra il campo commerciale (stringa) a commerciale_id (integer).
    
    Args:
        conn: Connessione database
        mapping: {'PELUCCHI': 4, 'PERANI': 3, 'ZUBANI': 5}
        operatore_id: ID operatore (0 = SYSTEM)
        dry_run: Se True, non esegue modifiche
    
    Returns:
        dict: {
            'migrati': 150,
            'errori': 0,
            'non_trovati': ['ROSSI', ...],
            'dettagli': [{'piva': '...', 'da': 'PELUCCHI', 'a_id': 4}, ...]
        }
    """
    cursor = conn.cursor()
    
    # Trova tutti i veicoli con commerciale stringa ma senza commerciale_id
    cursor.execute('''
        SELECT DISTINCT p_iva, commerciale FROM veicoli
        WHERE commerciale IS NOT NULL 
          AND commerciale != ''
          AND (commerciale_id IS NULL OR commerciale_id = 0)
    ''')
    
    result = {
        'migrati': 0,
        'errori': 0,
        'non_trovati': [],
        'dettagli': []
    }
    
    for row in cursor.fetchall():
        piva = row['p_iva']
        comm_str = row['commerciale'].upper().strip()
        
        # Cerca nel mapping
        comm_id = mapping.get(comm_str)
        
        if comm_id is None:
            # Prova ricerca automatica per cognome
            comm_id = get_id_da_cognome_legacy(conn, comm_str)
        
        if comm_id is None:
            if comm_str not in result['non_trovati']:
                result['non_trovati'].append(comm_str)
            result['errori'] += 1
            continue
        
        result['dettagli'].append({
            'piva': piva,
            'da': comm_str,
            'a_id': comm_id
        })
        
        if not dry_run:
            # Aggiorna veicoli
            cursor.execute('''
                UPDATE veicoli SET commerciale_id = ? WHERE p_iva = ?
            ''', (comm_id, piva))
            
            # Aggiorna clienti
            cursor.execute('''
                UPDATE clienti SET commerciale_id = ? WHERE p_iva = ?
            ''', (comm_id, piva))
            
            # Recupera nome cliente per storico
            cursor.execute('SELECT nome_cliente FROM clienti WHERE p_iva = ?', (piva,))
            nome_row = cursor.fetchone()
            nome = nome_row['nome_cliente'] if nome_row else piva
            
            # Registra nello storico
            registra_assegnazione(
                conn, piva, nome,
                None, comm_id,  # precedente None perche' era stringa
                operatore_id,
                f'Migrazione da stringa legacy: {comm_str}',
                TIPO_MIGRAZIONE
            )
        
        result['migrati'] += 1
    
    if not dry_run:
        conn.commit()
    
    return result


# ==============================================================================
# FUNZIONI HELPER PER VERIFICHE
# ==============================================================================

def ha_permesso_assegnabile(conn, utente_id):
    """
    Verifica se un utente ha il permesso di ricevere clienti.
    
    Returns:
        bool: True se ha il permesso abilitato
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM utenti_permessi up
        JOIN permessi_catalogo pc ON up.permesso_id = pc.id
        WHERE up.utente_id = ?
          AND pc.codice = ?
          AND up.abilitato = 1
    ''', (utente_id, PERMESSO_ASSEGNABILE))
    
    return cursor.fetchone() is not None


def abilita_permesso_assegnabile(conn, utente_id, assegnato_da_id):
    """
    Abilita il permesso di ricevere clienti per un utente.
    
    Returns:
        bool: True se abilitato con successo
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Trova ID permesso
    cursor.execute('''
        SELECT id FROM permessi_catalogo WHERE codice = ?
    ''', (PERMESSO_ASSEGNABILE,))
    
    perm_row = cursor.fetchone()
    if not perm_row:
        return False
    
    permesso_id = perm_row['id']
    
    # Inserisci o aggiorna
    cursor.execute('''
        INSERT INTO utenti_permessi (utente_id, permesso_id, abilitato, data_assegnazione, assegnato_da)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(utente_id, permesso_id) DO UPDATE SET
            abilitato = 1,
            data_assegnazione = excluded.data_assegnazione,
            assegnato_da = excluded.assegnato_da
    ''', (utente_id, permesso_id, now, assegnato_da_id))
    
    conn.commit()
    return True


def disabilita_permesso_assegnabile(conn, utente_id):
    """
    Disabilita il permesso di ricevere clienti per un utente.
    
    Returns:
        bool: True se disabilitato
    """
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE utenti_permessi SET abilitato = 0
        WHERE utente_id = ?
          AND permesso_id = (SELECT id FROM permessi_catalogo WHERE codice = ?)
    ''', (utente_id, PERMESSO_ASSEGNABILE))
    
    conn.commit()
    return cursor.rowcount > 0


# ==============================================================================
# FUNZIONI CENTRALIZZATE INFO COMMERCIALE (con colore)
# ==============================================================================
# REGOLA ARCHITETTURALE: Queste funzioni sono l'UNICA fonte per ottenere
# le informazioni del commerciale (incluso colore). Tutte le altre parti
# del codice DEVONO usare queste funzioni invece di query dirette.
# ==============================================================================

# Import lazy per evitare import circolari
def _get_hex_colore(colore_id):
    """Import lazy di get_hex_colore da google_calendar."""
    from app.google_calendar import get_hex_colore
    return get_hex_colore(colore_id)


def get_info_commerciale(conn, commerciale_id):
    """
    Restituisce tutte le info di un commerciale dato il suo ID utente.
    
    QUESTA E' LA FUNZIONE CENTRALIZZATA per ottenere info commerciale.
    Usare SEMPRE questa invece di query dirette.
    
    Args:
        conn: Connessione database
        commerciale_id: ID utente (int) oppure None
    
    Returns:
        dict: {
            'id': 3,
            'nome': 'Michele',
            'cognome': 'Perani',
            'display': 'M. Perani',
            'colore_id': 7,
            'colore_hex': '#039be5'
        }
        oppure None se commerciale_id non valido
    """
    if not commerciale_id:
        return None
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nome, cognome, colore_calendario
        FROM utenti 
        WHERE id = ?
    ''', (commerciale_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    colore_id = row['colore_calendario']
    
    return {
        'id': row['id'],
        'nome': row['nome'],
        'cognome': row['cognome'],
        'display': format_nome_commerciale(row['nome'], row['cognome']),
        'colore_id': colore_id,
        'colore_hex': _get_hex_colore(colore_id) if colore_id else None
    }


def get_info_commerciale_cliente(conn, cliente_id):
    """
    Restituisce le info del commerciale assegnato a un cliente.
    
    QUESTA E' LA FUNZIONE CENTRALIZZATA per ottenere il commerciale di un cliente.
    Gestisce sia il campo nuovo (commerciale_id) che quello legacy (commerciale stringa).
    
    Args:
        conn: Connessione database
        cliente_id: ID cliente
    
    Returns:
        dict: {
            'id': 3 oppure None,
            'nome': 'Michele',
            'cognome': 'Perani',
            'display': 'M. Perani',
            'colore_id': 7 oppure None,
            'colore_hex': '#039be5' oppure None,
            'fonte': 'commerciale_id' oppure 'commerciale_legacy'
        }
        oppure None se nessun commerciale assegnato
    """
    if not cliente_id:
        return None
    
    cursor = conn.cursor()
    
    # Prima provo con commerciale_id (campo nuovo)
    cursor.execute('''
        SELECT c.commerciale_id, c.commerciale,
               u.id as utente_id, u.nome, u.cognome, u.colore_calendario
        FROM clienti c
        LEFT JOIN utenti u ON c.commerciale_id = u.id
        WHERE c.id = ?
    ''', (cliente_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    # Se ho commerciale_id valido, uso quello
    if row['utente_id']:
        colore_id = row['colore_calendario']
        return {
            'id': row['utente_id'],
            'nome': row['nome'],
            'cognome': row['cognome'],
            'display': format_nome_commerciale(row['nome'], row['cognome']),
            'colore_id': colore_id,
            'colore_hex': _get_hex_colore(colore_id) if colore_id else None,
            'fonte': 'commerciale_id'
        }
    
    # Fallback: campo legacy commerciale (stringa)
    commerciale_legacy = row['commerciale']
    if commerciale_legacy:
        # Provo a trovare l'utente per cognome
        cursor.execute('''
            SELECT id, nome, cognome, colore_calendario
            FROM utenti
            WHERE UPPER(cognome) = UPPER(?)
              AND ruolo_base = 'commerciale'
              AND attivo = 1
            LIMIT 1
        ''', (commerciale_legacy.strip(),))
        
        utente_row = cursor.fetchone()
        if utente_row:
            colore_id = utente_row['colore_calendario']
            return {
                'id': utente_row['id'],
                'nome': utente_row['nome'],
                'cognome': utente_row['cognome'],
                'display': format_nome_commerciale(utente_row['nome'], utente_row['cognome']),
                'colore_id': colore_id,
                'colore_hex': _get_hex_colore(colore_id) if colore_id else None,
                'fonte': 'commerciale_legacy'
            }
        else:
            # Utente non trovato ma ho la stringa
            return {
                'id': None,
                'nome': None,
                'cognome': commerciale_legacy,
                'display': commerciale_legacy,
                'colore_id': None,
                'colore_hex': None,
                'fonte': 'commerciale_legacy'
            }
    
    return None


def get_info_commerciale_bulk(conn, cliente_ids):
    """
    Restituisce le info commerciale per piu' clienti in una sola query.
    Ottimizzato per evitare N+1 queries.
    
    Args:
        conn: Connessione database
        cliente_ids: Lista di ID clienti
    
    Returns:
        dict: {cliente_id: info_commerciale, ...}
    """
    if not cliente_ids:
        return {}
    
    # Rimuovi duplicati e None
    ids_validi = list(set(id for id in cliente_ids if id))
    if not ids_validi:
        return {}
    
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(ids_validi))
    
    # Query principale
    cursor.execute(f'''
        SELECT c.id as cliente_id, c.commerciale_id, c.commerciale,
               u.id as utente_id, u.nome, u.cognome, u.colore_calendario
        FROM clienti c
        LEFT JOIN utenti u ON c.commerciale_id = u.id
        WHERE c.id IN ({placeholders})
    ''', ids_validi)
    
    # Prima passata: clienti con commerciale_id
    risultati = {}
    clienti_legacy = []
    
    for row in cursor.fetchall():
        cliente_id = row['cliente_id']
        
        if row['utente_id']:
            # Ha commerciale_id valido
            colore_id = row['colore_calendario']
            risultati[cliente_id] = {
                'id': row['utente_id'],
                'nome': row['nome'],
                'cognome': row['cognome'],
                'display': format_nome_commerciale(row['nome'], row['cognome']),
                'colore_id': colore_id,
                'colore_hex': _get_hex_colore(colore_id) if colore_id else None,
                'fonte': 'commerciale_id'
            }
        elif row['commerciale']:
            # Segna per ricerca legacy
            clienti_legacy.append((cliente_id, row['commerciale']))
        else:
            risultati[cliente_id] = None
    
    # Seconda passata: cerca utenti per cognome legacy
    if clienti_legacy:
        cognomi = list(set(c[1].strip().upper() for c in clienti_legacy if c[1]))
        if cognomi:
            placeholders = ','.join('?' * len(cognomi))
            cursor.execute(f'''
                SELECT id, nome, cognome, colore_calendario
                FROM utenti
                WHERE UPPER(cognome) IN ({placeholders})
                  AND ruolo_base = 'commerciale'
                  AND attivo = 1
            ''', cognomi)
            
            mappa_cognomi = {}
            for row in cursor.fetchall():
                mappa_cognomi[row['cognome'].upper()] = row
        else:
            mappa_cognomi = {}
        
        for cliente_id, commerciale_str in clienti_legacy:
            cognome_upper = commerciale_str.strip().upper()
            utente_row = mappa_cognomi.get(cognome_upper)
            
            if utente_row:
                colore_id = utente_row['colore_calendario']
                risultati[cliente_id] = {
                    'id': utente_row['id'],
                    'nome': utente_row['nome'],
                    'cognome': utente_row['cognome'],
                    'display': format_nome_commerciale(utente_row['nome'], utente_row['cognome']),
                    'colore_id': colore_id,
                    'colore_hex': _get_hex_colore(colore_id) if colore_id else None,
                    'fonte': 'commerciale_legacy'
                }
            else:
                risultati[cliente_id] = {
                    'id': None,
                    'nome': None,
                    'cognome': commerciale_str,
                    'display': commerciale_str,
                    'colore_id': None,
                    'colore_hex': None,
                    'fonte': 'commerciale_legacy'
                }
    
    return risultati
