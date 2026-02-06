# -*- coding: utf-8 -*-
"""
==============================================================================
MOTORE TRATTATIVE - CRUD e Business Logic
==============================================================================
Versione: 1.0
Data: 2026-01-27
Descrizione: Funzioni CRUD e business logic per il modulo Trattative.
             Motore autonomo riutilizzabile da qualsiasi parte del programma.

Uso:
    from app.motore_trattative import (
        # CRUD Trattative
        crea_trattativa,
        get_trattativa,
        get_trattative_cliente,
        modifica_trattativa,
        elimina_trattativa,
        
        # Avanzamenti
        aggiungi_avanzamento,
        get_avanzamenti,
        
        # Ricerca e filtri
        cerca_trattative,
        get_trattative_aperte,
        
        # Statistiche
        conta_per_stato,
        get_statistiche_commerciale
    )
==============================================================================
"""

import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple

# Import per visibilita' gerarchica
try:
    from app.database_utenti import get_subordinati
    from app.config_trattative import get_stati_chiusi
except ImportError:
    # Fallback se importato standalone
    def get_subordinati(conn, user_id):
        return [user_id]


# ==============================================================================
# Import connettore notifiche
try:
    from app.connettori_notifiche.trattative import (
        notifica_nuova_trattativa,
        notifica_avanzamento_trattativa
    )
    _NOTIFICHE_TR = True
except ImportError:
    _NOTIFICHE_TR = False

# COSTANTI
# ==============================================================================

# get_stati_chiusi() ora viene letto da Excel tramite get_stati_chiusi()
STATO_DEFAULT = 'Preso in carico'


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def _dict_factory(cursor, row):
    """Converte righe SQLite in dizionari"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _get_conn_dict(conn):
    """Restituisce connessione con row_factory dict"""
    conn.row_factory = _dict_factory
    return conn


def _oggi():
    """Restituisce data odierna in formato ISO"""
    return date.today().isoformat()


def _ora():
    """Restituisce datetime corrente in formato ISO"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ==============================================================================
# CRUD - CREAZIONE TRATTATIVA
# ==============================================================================

def crea_trattativa(conn, dati: Dict[str, Any], user_id: int) -> Optional[int]:
    """
    Crea una nuova trattativa.
    
    Args:
        conn: connessione SQLite
        dati: dizionario con i dati della trattativa
            - cliente_id (obbligatorio)
            - noleggiatore
            - marca
            - descrizione_veicolo
            - tipologia_veicolo
            - tipo_trattativa
            - num_pezzi
            - stato (default: 'Preso in carico')
            - note
        user_id: ID utente che crea
    
    Returns:
        ID della trattativa creata, None se errore
    """
    try:
        cursor = conn.cursor()
        
        # Valori di default
        stato = dati.get('stato', STATO_DEFAULT)
        data_inizio = dati.get('data_inizio', _oggi())
        
        # Snapshot nome commerciale
        cursor.execute("SELECT nome || ' ' || cognome FROM utenti WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        commerciale_nome_snapshot = row[0] if row else "Sconosciuto"
        
        # Gestione affidamento a commerciale controllato
        commerciale_assegnato = dati.get("commerciale_assegnato")
        if commerciale_assegnato:
            commerciale_assegnato = int(commerciale_assegnato)
        if commerciale_assegnato and commerciale_assegnato != user_id:
            # Trattativa affidata a un subordinato
            commerciale_id_finale = commerciale_assegnato
            assegnato_da = user_id
            affidato = 1
            # Aggiorno snapshot con nome del commerciale assegnato
            cursor.execute("SELECT nome || ' ' || cognome FROM utenti WHERE id = ?", (commerciale_assegnato,))
            row2 = cursor.fetchone()
            commerciale_nome_snapshot = row2[0] if row2 else commerciale_nome_snapshot
        else:
            commerciale_id_finale = user_id
            assegnato_da = None
            affidato = 0
        
        cursor.execute("""
            INSERT INTO trattative (
                cliente_id, commerciale_id, noleggiatore, marca,
                descrizione_veicolo, tipologia_veicolo, tipo_trattativa,
                num_pezzi, stato, data_inizio, note,
                creato_da, creato_il, commerciale_nome_snapshot,
                provvigione, q_percentuale, mesi, km_totali,
                assegnato_da, affidato
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dati['cliente_id'],
            commerciale_id_finale,
            dati.get('noleggiatore'),
            dati.get('marca'),
            dati.get('descrizione_veicolo'),
            dati.get('tipologia_veicolo'),
            dati.get('tipo_trattativa'),
            dati.get('num_pezzi', 1),
            stato,
            data_inizio,
            dati.get('note'),
            user_id,
            _ora(),
            commerciale_nome_snapshot,
            dati.get('provvigione'),
            dati.get('q_percentuale'),
            dati.get('mesi'),
            dati.get('km_totali'),
            assegnato_da,
            affidato
        ))
        trattativa_id = cursor.lastrowid
        
        # Registra primo avanzamento automatico
        cursor.execute("""
            INSERT INTO trattative_avanzamenti (
                trattativa_id, stato, note_avanzamento,
                data_avanzamento, registrato_da
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            trattativa_id,
            stato,
            'Trattativa aperta',
            _ora(),
            user_id
        ))
        
        conn.commit()

        # Notifica supervisori
        if _NOTIFICHE_TR:
            try:
                notifica_nuova_trattativa(conn, trattativa_id, commerciale_id_finale, dati['cliente_id'], stato)
            except Exception:
                pass

        return trattativa_id
        
    except Exception as e:
        print(f"[ERRORE] crea_trattativa: {e}")
        conn.rollback()
        return None


# ==============================================================================
# CRUD - LETTURA TRATTATIVA
# ==============================================================================

def get_trattativa(conn, trattativa_id: int) -> Optional[Dict]:
    """
    Recupera una singola trattativa con dati cliente.
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
    
    Returns:
        Dizionario con dati trattativa + cliente, None se non trovata
    """
    conn = _get_conn_dict(conn)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            t.*,
            c.ragione_sociale,
            c.p_iva,
            c.cod_fiscale,
            u.nome || ' ' || u.cognome AS commerciale_nome,
            ua.nome || ' ' || ua.cognome AS assegnato_da_nome
        FROM trattative t
        LEFT JOIN clienti c ON t.cliente_id = c.id
        LEFT JOIN utenti u ON t.commerciale_id = u.id
        LEFT JOIN utenti ua ON t.assegnato_da = ua.id
        WHERE t.id = ?
    """, (trattativa_id,))
    
    return cursor.fetchone()


def get_trattative_cliente(conn, cliente_id: int, solo_aperte: bool = False) -> List[Dict]:
    """
    Recupera tutte le trattative di un cliente (escluse cancellate).
    
    Args:
        conn: connessione SQLite
        cliente_id: ID cliente
        solo_aperte: se True, esclude trattative chiuse
    
    Returns:
        Lista di dizionari
    """
    conn = _get_conn_dict(conn)
    cursor = conn.cursor()
    
    sql = """
        SELECT t.*, u.nome || ' ' || u.cognome AS commerciale_nome,
            ua.nome || ' ' || ua.cognome AS assegnato_da_nome
        FROM trattative t
        LEFT JOIN utenti u ON t.commerciale_id = u.id
        LEFT JOIN utenti ua ON t.assegnato_da = ua.id
        WHERE t.cliente_id = ? AND (t.cancellata IS NULL OR t.cancellata = 0)
    """
    params = [cliente_id]
    
    if solo_aperte:
        placeholders = ','.join('?' * len(get_stati_chiusi()))
        sql += f" AND t.stato NOT IN ({placeholders})"
        params.extend(get_stati_chiusi())
    
    sql += " ORDER BY t.data_inizio DESC"
    
    cursor.execute(sql, params)
    return cursor.fetchall()


def get_trattative_commerciale(conn, commerciale_id: int, 
                                includi_subordinati: bool = True) -> List[Dict]:
    """
    Recupera trattative di un commerciale (e subordinati).
    
    Args:
        conn: connessione SQLite
        commerciale_id: ID commerciale
        includi_subordinati: se True, include anche subordinati
    
    Returns:
        Lista di dizionari
    """
    conn = _get_conn_dict(conn)
    cursor = conn.cursor()
    
    # Ottieni lista ID da includere
    if includi_subordinati:
        ids_visibili = get_subordinati(conn, commerciale_id)
    else:
        ids_visibili = [commerciale_id]
    
    placeholders = ','.join('?' * len(ids_visibili))
    
    cursor.execute(f"""
        SELECT 
            t.*,
            c.ragione_sociale,
            c.p_iva,
            u.nome || ' ' || u.cognome AS commerciale_nome,
            ua.nome || ' ' || ua.cognome AS assegnato_da_nome
        FROM trattative t
        LEFT JOIN clienti c ON t.cliente_id = c.id
        LEFT JOIN utenti u ON t.commerciale_id = u.id
        LEFT JOIN utenti ua ON t.assegnato_da = ua.id
        WHERE t.commerciale_id IN ({placeholders})
        ORDER BY t.data_inizio DESC
    """, ids_visibili)
    
    return cursor.fetchall()


# ==============================================================================
# CRUD - MODIFICA TRATTATIVA
# ==============================================================================

def modifica_trattativa(conn, trattativa_id: int, dati: Dict[str, Any], 
                        user_id: int) -> bool:
    """
    Modifica una trattativa esistente.
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
        dati: dizionario con campi da modificare
        user_id: ID utente che modifica
    
    Returns:
        True se successo, False se errore
    """
    try:
        cursor = conn.cursor()
        
        # Campi modificabili
        campi_ammessi = [
            'noleggiatore', 'marca', 'descrizione_veicolo',
            'tipologia_veicolo', 'tipo_trattativa', 'num_pezzi',
            'note', 'data_chiusura'
        ]
        
        # Costruisci UPDATE dinamico
        updates = []
        params = []
        
        for campo in campi_ammessi:
            if campo in dati:
                updates.append(f"{campo} = ?")
                params.append(dati[campo])
        
        if not updates:
            return True  # Nulla da modificare
        
        # Aggiungi audit
        updates.append("modificato_da = ?")
        updates.append("modificato_il = ?")
        params.extend([user_id, _ora()])
        
        # Aggiungi ID per WHERE
        params.append(trattativa_id)
        
        sql = f"UPDATE trattative SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"[ERRORE] modifica_trattativa: {e}")
        conn.rollback()
        return False


def elimina_trattativa(conn, trattativa_id: int, user_id: int) -> bool:
    """
    Soft delete di una trattativa (marca come cancellata, non elimina fisicamente).
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
        user_id: ID utente che cancella
    
    Returns:
        True se successo, False se errore
    """
    try:
        cursor = conn.cursor()
        
        # Verifica esistenza e che non sia gia' cancellata
        cursor.execute("SELECT id FROM trattative WHERE id = ? AND (cancellata IS NULL OR cancellata = 0)", (trattativa_id,))
        if not cursor.fetchone():
            return False
        
        # Soft delete: marca come cancellata
        cursor.execute("""
            UPDATE trattative 
            SET cancellata = 1, 
                data_cancellazione = datetime('now', 'localtime'),
                cancellata_da = ?
            WHERE id = ?
        """, (user_id, trattativa_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"[ERRORE] elimina_trattativa: {e}")
        conn.rollback()
        return False


def ripristina_trattativa(conn, trattativa_id: int, user_id: int) -> bool:
    """
    Ripristina una trattativa cancellata (solo admin).
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
        user_id: ID utente che ripristina (per log)
    
    Returns:
        True se successo, False se errore
    """
    try:
        cursor = conn.cursor()
        
        # Verifica esistenza e che sia cancellata
        cursor.execute("SELECT id FROM trattative WHERE id = ? AND cancellata = 1", (trattativa_id,))
        if not cursor.fetchone():
            return False
        
        # Ripristina
        cursor.execute("""
            UPDATE trattative 
            SET cancellata = 0, 
                data_cancellazione = NULL,
                cancellata_da = NULL
            WHERE id = ?
        """, (trattativa_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"[ERRORE] ripristina_trattativa: {e}")
        conn.rollback()
        return False


def riapri_trattativa(conn, trattativa_id: int, user_id: int) -> bool:
    """
    Riapre una trattativa chiusa riportandola allo stato 'Preso in carico' (solo admin).
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
        user_id: ID utente che riapre (per log)
    
    Returns:
        True se successo, False se errore
    """
    try:
        cursor = conn.cursor()
        
        # Verifica esistenza e che sia chiusa (non cancellata)
        stati_chiusi = get_stati_chiusi()
        cursor.execute("""
            SELECT id, stato FROM trattative 
            WHERE id = ? AND (cancellata IS NULL OR cancellata = 0)
        """, (trattativa_id,))
        row = cursor.fetchone()
        
        if not row:
            return False
        
        if row['stato'] not in stati_chiusi:
            return False  # Non e' una trattativa chiusa
        
        # Riapri: riporta a stato iniziale
        cursor.execute("""
            UPDATE trattative 
            SET stato = 'Preso in carico',
                data_chiusura = NULL,
                modificato_da = ?,
                modificato_il = datetime('now', 'localtime')
            WHERE id = ?
        """, (user_id, trattativa_id))
        
        # Registra avanzamento
        cursor.execute("""
            INSERT INTO trattative_avanzamenti (
                trattativa_id, stato, note_avanzamento,
                data_avanzamento, registrato_da
            ) VALUES (?, ?, ?, datetime('now', 'localtime'), ?)
        """, (trattativa_id, 'Preso in carico', 'Trattativa riaperta da admin', user_id))
        conn.commit()
        return True
        
    except Exception as e:
        print(f"[ERRORE] riapri_trattativa: {e}")
        conn.rollback()
        return False



# ==============================================================================
# AVANZAMENTI
# ==============================================================================

def aggiungi_avanzamento(conn, trattativa_id: int, nuovo_stato: str,
                         note: str, user_id: int) -> bool:
    """
    Registra un nuovo avanzamento e aggiorna stato trattativa.
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
        nuovo_stato: nuovo stato da registrare
        note: note avanzamento
        user_id: ID utente che registra
    
    Returns:
        True se successo, False se errore
    """
    try:
        cursor = conn.cursor()
        ora = _ora()
        
        # Registra avanzamento
        cursor.execute("""
            INSERT INTO trattative_avanzamenti (
                trattativa_id, stato, note_avanzamento,
                data_avanzamento, registrato_da
            ) VALUES (?, ?, ?, ?, ?)
        """, (trattativa_id, nuovo_stato, note, ora, user_id))
        
        # Aggiorna stato trattativa
        update_data = {
            'stato': nuovo_stato,
            'modificato_da': user_id,
            'modificato_il': _ora()
        }
        
        # Se stato di chiusura, imposta data_chiusura
        if nuovo_stato in get_stati_chiusi():
            update_data['data_chiusura'] = _oggi()
        
        cursor.execute("""
            UPDATE trattative 
            SET stato = ?, modificato_da = ?, modificato_il = ?,
                data_chiusura = CASE WHEN ? IN ({}) THEN ? ELSE data_chiusura END
            WHERE id = ?
        """.format(','.join('?' * len(get_stati_chiusi()))), (
            nuovo_stato, user_id, ora,
            nuovo_stato, *get_stati_chiusi(), _oggi(),
            trattativa_id
        ))
        
        conn.commit()

        # Notifica supervisori avanzamento
        if _NOTIFICHE_TR:
            try:
                cursor.execute('SELECT commerciale_id, cliente_id FROM trattative WHERE id = ?', (trattativa_id,))
                tr_row = cursor.fetchone()
                if tr_row:
                    _comm_id = tr_row['commerciale_id'] if isinstance(tr_row, dict) else tr_row[0]
                    _cli_id = tr_row['cliente_id'] if isinstance(tr_row, dict) else tr_row[1]
                    notifica_avanzamento_trattativa(conn, trattativa_id, _comm_id, _cli_id, nuovo_stato)
            except Exception:
                pass

        return True
        
    except Exception as e:
        print(f"[ERRORE] aggiungi_avanzamento: {e}")
        conn.rollback()
        return False


def get_avanzamenti(conn, trattativa_id: int) -> List[Dict]:
    """
    Recupera storico avanzamenti di una trattativa.
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
    
    Returns:
        Lista di dizionari ordinata cronologicamente
    """
    conn = _get_conn_dict(conn)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            a.*,
            u.nome || ' ' || u.cognome AS registrato_da_nome
        FROM trattative_avanzamenti a
        LEFT JOIN utenti u ON a.registrato_da = u.id
        WHERE a.trattativa_id = ?
        ORDER BY a.data_avanzamento ASC
    """, (trattativa_id,))
    
    return cursor.fetchall()


# ==============================================================================
# RICERCA E FILTRI
# ==============================================================================

def cerca_trattative(conn, filtri: Dict[str, Any], user_id: int,
                     limite: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
    """
    Cerca trattative con filtri multipli e visibilita' gerarchica.
    Esclude automaticamente le trattative cancellate.
    
    Args:
        conn: connessione SQLite
        filtri: dizionario filtri
            - stato: stringa o lista di stati
            - noleggiatore: codice noleggiatore
            - cliente_id: ID cliente specifico
            - cliente_search: ricerca testuale ragione sociale
            - commerciale_id: ID commerciale specifico
            - data_da: data inizio minima
            - data_a: data inizio massima
            - solo_aperte: bool, esclude chiuse
            - solo_cancellate: bool, mostra SOLO cancellate (per griglia admin)
        user_id: ID utente per visibilita'
        limite: max risultati
        offset: offset paginazione
    
    Returns:
        Tupla (lista risultati, conteggio totale)
    """
    conn = _get_conn_dict(conn)
    cursor = conn.cursor()
    
    # Visibilita' gerarchica
    ids_visibili = get_subordinati(conn, user_id)
    
    # Base query
    where_clauses = []
    params = []
    
    # Filtro visibilita' (sempre applicato)
    placeholders = ','.join('?' * len(ids_visibili))
    where_clauses.append(f"t.commerciale_id IN ({placeholders})")
    params.extend(ids_visibili)
    
    # Filtro cancellate (default: escludi cancellate)
    if filtri.get('solo_cancellate'):
        where_clauses.append("t.cancellata = 1")
    else:
        where_clauses.append("(t.cancellata IS NULL OR t.cancellata = 0)")
    
    # Filtro stato
    if 'stato' in filtri and filtri['stato']:
        if isinstance(filtri['stato'], list):
            ph = ','.join('?' * len(filtri['stato']))
            where_clauses.append(f"t.stato IN ({ph})")
            params.extend(filtri['stato'])
        else:
            where_clauses.append("t.stato = ?")
            params.append(filtri['stato'])
    
    # Filtro solo aperte
    if filtri.get('solo_aperte'):
        ph = ','.join('?' * len(get_stati_chiusi()))
        where_clauses.append(f"t.stato NOT IN ({ph})")
        params.extend(get_stati_chiusi())
    
    # Filtro solo chiuse
    if filtri.get('solo_chiuse'):
        ph = ','.join('?' * len(get_stati_chiusi()))
        where_clauses.append(f"t.stato IN ({ph})")
        params.extend(get_stati_chiusi())
    
    # Filtro noleggiatore
    if filtri.get('noleggiatore'):
        where_clauses.append("t.noleggiatore = ?")
        params.append(filtri['noleggiatore'])
    
    # Filtro cliente_id
    if filtri.get('cliente_id'):
        where_clauses.append("t.cliente_id = ?")
        params.append(filtri['cliente_id'])
    
    # Filtro ricerca cliente
    if filtri.get('cliente_search'):
        where_clauses.append("c.ragione_sociale LIKE ?")
        params.append(f"%{filtri['cliente_search']}%")
    
    # Filtro commerciale specifico
    if filtri.get('commerciale_id'):
        where_clauses.append("t.commerciale_id = ?")
        params.append(filtri['commerciale_id'])
    
    # Filtro data
    if filtri.get('data_da'):
        where_clauses.append("t.data_inizio >= ?")
        params.append(filtri['data_da'])
    
    if filtri.get('data_a'):
        where_clauses.append("t.data_inizio <= ?")
        params.append(filtri['data_a'])
    
    # Costruisci WHERE
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Query conteggio totale
    count_sql = f"""
        SELECT COUNT(*) 
        FROM trattative t
        LEFT JOIN clienti c ON t.cliente_id = c.id
        WHERE {where_sql}
    """
    cursor.execute(count_sql, params)
    totale = cursor.fetchone()['COUNT(*)']
    
    # Query risultati
    select_sql = f"""
        SELECT 
            t.*,
            c.ragione_sociale,
            c.p_iva,
            u.nome || ' ' || u.cognome AS commerciale_nome,
            ua.nome || ' ' || ua.cognome AS assegnato_da_nome
        FROM trattative t
        LEFT JOIN clienti c ON t.cliente_id = c.id
        LEFT JOIN utenti u ON t.commerciale_id = u.id
        LEFT JOIN utenti ua ON t.assegnato_da = ua.id
        WHERE {where_sql}
        ORDER BY t.data_inizio DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limite, offset])
    cursor.execute(select_sql, params)
    
    return cursor.fetchall(), totale


def get_trattative_aperte(conn, commerciale_id: int = None) -> List[Dict]:
    """
    Recupera tutte le trattative aperte.
    
    Args:
        conn: connessione SQLite
        commerciale_id: se specificato, filtra per commerciale
    
    Returns:
        Lista di dizionari
    """
    filtri = {'solo_aperte': True}
    if commerciale_id:
        filtri['commerciale_id'] = commerciale_id
    
    # Usa user_id=0 per admin (vede tutto)
    user_id = commerciale_id if commerciale_id else 0
    risultati, _ = cerca_trattative(conn, filtri, user_id, limite=1000)
    return risultati


# ==============================================================================
# STATISTICHE
# ==============================================================================

def conta_per_stato(conn, commerciale_id: int = None, 
                    includi_subordinati: bool = True) -> Dict[str, int]:
    """
    Conta trattative raggruppate per stato (escluse cancellate).
    
    Args:
        conn: connessione SQLite
        commerciale_id: se specificato, filtra per commerciale
        includi_subordinati: se True, include subordinati
    
    Returns:
        Dizionario stato -> conteggio
    """
    cursor = conn.cursor()
    
    sql = "SELECT stato, COUNT(*) as cnt FROM trattative WHERE (cancellata IS NULL OR cancellata = 0)"
    params = []
    
    if commerciale_id:
        if includi_subordinati:
            ids = get_subordinati(conn, commerciale_id)
        else:
            ids = [commerciale_id]
        
        placeholders = ','.join('?' * len(ids))
        sql += f" AND commerciale_id IN ({placeholders})"
        params.extend(ids)
    
    sql += " GROUP BY stato"
    
    cursor.execute(sql, params)
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_statistiche_commerciale(conn, commerciale_id: int) -> Dict[str, Any]:
    """
    Recupera statistiche complete per un commerciale.
    
    Args:
        conn: connessione SQLite
        commerciale_id: ID commerciale
    
    Returns:
        Dizionario con statistiche
    """
    per_stato = conta_per_stato(conn, commerciale_id)
    
    # Calcoli derivati
    aperte = sum(v for k, v in per_stato.items() if k not in get_stati_chiusi())
    chiuse = sum(v for k, v in per_stato.items() if k in get_stati_chiusi())
    vinte = per_stato.get('Approvato', 0) + per_stato.get('Approvato con riserve', 0)
    perse = per_stato.get('Bocciato', 0) + per_stato.get('Perso', 0)
    
    return {
        'per_stato': per_stato,
        'totale': sum(per_stato.values()),
        'aperte': aperte,
        'chiuse': chiuse,
        'vinte': vinte,
        'perse': perse,
        'tasso_successo': round(vinte / chiuse * 100, 1) if chiuse > 0 else 0
    }


# ==============================================================================
# FUNZIONI UTILITY
# ==============================================================================

def trattativa_appartiene_a(conn, trattativa_id: int, user_id: int) -> bool:
    """
    Verifica se un utente puo' vedere/modificare una trattativa.
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
        user_id: ID utente
    
    Returns:
        True se l'utente ha accesso
    """
    cursor = conn.cursor()
    
    # Ottieni commerciale della trattativa
    cursor.execute(
        "SELECT commerciale_id FROM trattative WHERE id = ?", 
        (trattativa_id,)
    )
    row = cursor.fetchone()
    if not row:
        return False
    
    commerciale_trattativa = row[0]
    
    # Verifica se e' nella gerarchia
    ids_visibili = get_subordinati(conn, user_id)
    return commerciale_trattativa in ids_visibili


def trasferisci_trattative_cliente(conn, cliente_id: int, 
                                    nuovo_commerciale_id: int, user_id: int) -> int:
    """
    Trasferisce tutte le trattative di un cliente a un nuovo commerciale.
    Usato quando si riassegna un cliente.
    
    Args:
        conn: connessione SQLite
        cliente_id: ID cliente
        nuovo_commerciale_id: nuovo commerciale assegnatario
        user_id: ID utente che effettua il trasferimento
    
    Returns:
        Numero di trattative trasferite
    """
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE trattative 
            SET commerciale_id = ?, modificato_da = ?, modificato_il = ?
            WHERE cliente_id = ?
        """, (nuovo_commerciale_id, user_id, _ora(), cliente_id))
        
        trasferite = cursor.rowcount
        conn.commit()
        return trasferite
        
    except Exception as e:
        print(f"[ERRORE] trasferisci_trattative_cliente: {e}")
        conn.rollback()
        return 0


# ==============================================================================
# VERIFICA CANCELLABILITA'
# ==============================================================================

def trattativa_cancellabile(conn, trattativa_id: int, is_admin: bool = False, stato: str = None) -> bool:
    """
    Verifica se una trattativa puo' essere cancellata.
    
    Logica:
    - Trattativa CHIUSA: nessuno puo' cancellarla
    - Admin + trattativa APERTA: puo' sempre cancellarla
    - Non-admin: solo se ha un solo avanzamento (quello iniziale)
    
    Args:
        conn: connessione SQLite
        trattativa_id: ID trattativa
        is_admin: True se l'utente e' admin
        stato: stato attuale della trattativa (opzionale, se None lo recupera)
    
    Returns:
        True se cancellabile, False altrimenti
    """
    # Recupera stato se non fornito
    if stato is None:
        cursor = conn.cursor()
        cursor.execute("SELECT stato FROM trattative WHERE id = ?", (trattativa_id,))
        row = cursor.fetchone()
        stato = row['stato'] if row else None
    
    # Verifica se trattativa chiusa (nessuno puo' cancellarla)
    stati_chiusi = get_stati_chiusi()
    if stato in stati_chiusi:
        return is_admin  # Admin puo' cancellare anche le chiuse
    
    # Admin puo' sempre cancellare trattative aperte
    if is_admin:
        return True
    
    # Non-admin: solo se ha 1 solo avanzamento
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM trattative_avanzamenti WHERE trattativa_id = ?",
        (trattativa_id,)
    )
    row = cursor.fetchone()
    num_avanzamenti = row['COUNT(*)'] if row else 0
    return num_avanzamenti <= 1
