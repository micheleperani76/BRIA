# -*- coding: utf-8 -*-
"""
==============================================================================
MOTORE TICKER BROADCASTING
==============================================================================
Versione: 1.0.0
Data: 2026-02-06
Descrizione: Logica centrale del sistema ticker broadcasting.
             Selezione messaggi, scheduling temporale, weighted random,
             rate limiting, CRUD messaggi.
==============================================================================
"""

import random
from datetime import datetime, timedelta
from app.config_ticker import (
    get_config_int, get_config_bool, is_ticker_attivo,
    STATI_MESSAGGIO
)


# ==============================================================================
# SELEZIONE MESSAGGIO (per il widget topbar)
# ==============================================================================

def get_prossimo_messaggio(conn, user_id, ruolo=None):
    """
    Seleziona il prossimo messaggio da mostrare nel ticker.
    
    Algoritmo:
    1. Filtra messaggi approvati + in periodo valido
    2. Filtra per destinatari (TUTTI, ruolo, utente specifico)
    3. Verifica rate limit (messaggi/ora)
    4. Weighted random selection basata su priorita/peso
    
    Args:
        conn: connessione SQLite
        user_id: ID utente corrente
        ruolo: ruolo_base utente (admin, commerciale, operatore)
    
    Returns:
        dict: messaggio selezionato o None
    """
    if not is_ticker_attivo(conn):
        return None
    
    # Verifica rate limit
    max_ora = get_config_int(conn, 'messaggi_ora', 4)
    if _messaggi_ultima_ora(conn, user_id) >= max_ora:
        return None
    
    now = datetime.now()
    oggi = now.strftime('%Y-%m-%d')
    ora_corrente = now.strftime('%H:%M')
    giorno_settimana = str(now.isoweekday())  # 1=lun, 7=dom
    
    cursor = conn.cursor()
    
    # Query: messaggi approvati nel periodo valido
    cursor.execute("""
        SELECT id, testo, icona, colore_testo, animazione,
               durata_secondi, velocita, priorita, peso, destinatari
        FROM ticker_messaggi
        WHERE stato = 'approvato'
          AND data_inizio <= ?
          AND (data_fine IS NULL OR data_fine >= ?)
          AND ora_inizio <= ?
          AND ora_fine >= ?
          AND giorni_settimana LIKE ?
    """, (oggi, oggi, ora_corrente, ora_corrente, f'%{giorno_settimana}%'))
    
    candidati = []
    for row in cursor.fetchall():
        msg = dict(zip(
            ['id', 'testo', 'icona', 'colore_testo', 'animazione',
             'durata_secondi', 'velocita', 'priorita', 'peso', 'destinatari'],
            row
        ))
        
        # Filtra per destinatari
        if _messaggio_visibile(msg['destinatari'], user_id, ruolo):
            candidati.append(msg)
    
    if not candidati:
        return None
    
    # Weighted random selection
    return _selezione_pesata(candidati)


def calcola_prossimo_check(conn):
    """
    Calcola quanti secondi attendere prima del prossimo check.
    Valore random tra pausa_minima e pausa_massima.
    
    Returns:
        int: secondi di attesa
    """
    pausa_min = get_config_int(conn, 'pausa_minima_sec', 120)
    pausa_max = get_config_int(conn, 'pausa_massima_sec', 600)
    return random.randint(pausa_min, pausa_max)


# ==============================================================================
# FILTRO DESTINATARI
# ==============================================================================

def _messaggio_visibile(destinatari, user_id, ruolo):
    """
    Verifica se un messaggio e' visibile per un utente.
    
    Formati supportati:
    - TUTTI
    - RUOLO:ADMIN, RUOLO:COMMERCIALE, RUOLO:OPERATORE
    - UTENTE:123
    - Combinati: RUOLO:COMMERCIALE,UTENTE:42
    """
    if not destinatari or destinatari.strip() == 'TUTTI':
        return True
    
    parti = [p.strip() for p in destinatari.split(',')]
    
    for parte in parti:
        if parte == 'TUTTI':
            return True
        
        if parte.startswith('RUOLO:'):
            ruolo_richiesto = parte[6:].lower()
            if ruolo and ruolo.lower() == ruolo_richiesto:
                return True
        
        if parte.startswith('UTENTE:'):
            try:
                uid = int(parte[7:])
                if uid == user_id:
                    return True
            except (ValueError, TypeError):
                pass
    
    return False


# ==============================================================================
# WEIGHTED RANDOM SELECTION
# ==============================================================================

def _selezione_pesata(candidati):
    """
    Seleziona un messaggio con probabilita proporzionale a priorita * peso.
    
    Args:
        candidati: lista di dizionari messaggio
    
    Returns:
        dict: messaggio selezionato
    """
    if not candidati:
        return None
    
    if len(candidati) == 1:
        return candidati[0]
    
    # Calcola pesi: priorita * peso
    pesi = []
    for msg in candidati:
        p = (msg.get('priorita', 5) or 5) * (msg.get('peso', 1) or 1)
        pesi.append(max(p, 1))
    
    # Weighted random
    totale = sum(pesi)
    r = random.uniform(0, totale)
    accumulatore = 0
    
    for i, peso in enumerate(pesi):
        accumulatore += peso
        if r <= accumulatore:
            return candidati[i]
    
    return candidati[-1]


# ==============================================================================
# RATE LIMITING
# ==============================================================================

def _messaggi_ultima_ora(conn, user_id):
    """
    Conta quanti messaggi sono stati mostrati all'utente nell'ultima ora.
    
    Returns:
        int: conteggio
    """
    un_ora_fa = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM ticker_log
        WHERE utente_id = ? AND data_visualizzazione >= ?
    """, (user_id, un_ora_fa))
    
    return cursor.fetchone()[0]


def registra_visualizzazione(conn, messaggio_id, user_id):
    """
    Registra che un messaggio e' stato mostrato a un utente.
    
    Args:
        conn: connessione SQLite
        messaggio_id: ID messaggio
        user_id: ID utente
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ticker_log (messaggio_id, utente_id)
            VALUES (?, ?)
        """, (messaggio_id, user_id))
        conn.commit()
    except Exception:
        pass


# ==============================================================================
# CRUD MESSAGGI
# ==============================================================================

def crea_messaggio(conn, dati, user_id, is_admin=False):
    """
    Crea un nuovo messaggio ticker.
    
    Admin: stato = 'approvato' (bypass approvazione)
    Utente: stato = 'bozza'
    
    Args:
        conn: connessione SQLite
        dati: dizionario con campi messaggio
        user_id: ID creatore
        is_admin: True se admin
    
    Returns:
        int: ID messaggio creato, o None
    """
    try:
        stato = 'approvato' if is_admin else 'bozza'
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ticker_messaggi (
                testo, icona, colore_testo,
                animazione, durata_secondi, velocita,
                data_inizio, data_fine, ora_inizio, ora_fine,
                giorni_settimana, ricorrenza,
                priorita, peso, destinatari,
                stato, creato_da,
                approvato_da, data_approvazione,
                tipo, codice_auto, data_creazione
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dati.get('testo', ''),
            dati.get('icona', ''),
            dati.get('colore_testo', '#000000'),
            dati.get('animazione', 'scroll-rtl'),
            dati.get('durata_secondi', 8),
            dati.get('velocita', 'normale'),
            dati.get('data_inizio', now[:10]),
            dati.get('data_fine'),
            dati.get('ora_inizio', '00:00'),
            dati.get('ora_fine', '23:59'),
            dati.get('giorni_settimana', '1,2,3,4,5,6,7'),
            dati.get('ricorrenza', 'nessuna'),
            dati.get('priorita', 5),
            dati.get('peso', 1),
            dati.get('destinatari', 'TUTTI'),
            stato,
            user_id,
            user_id if is_admin else None,
            now if is_admin else None,
            dati.get('tipo', 'manuale'),
            dati.get('codice_auto'),
            now,
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"[ERRORE] crea_messaggio: {e}")
        return None


def modifica_messaggio(conn, messaggio_id, dati, user_id):
    """
    Modifica un messaggio esistente.
    
    Args:
        conn: connessione SQLite
        messaggio_id: ID messaggio
        dati: campi da aggiornare
        user_id: ID utente che modifica
    
    Returns:
        bool: True se modificato
    """
    try:
        campi_ammessi = [
            'testo', 'icona', 'colore_testo',
            'animazione', 'durata_secondi', 'velocita',
            'data_inizio', 'data_fine', 'ora_inizio', 'ora_fine',
            'giorni_settimana', 'ricorrenza',
            'priorita', 'peso', 'destinatari'
        ]
        
        set_parts = []
        params = []
        
        for campo in campi_ammessi:
            if campo in dati:
                set_parts.append(f"{campo} = ?")
                params.append(dati[campo])
        
        if not set_parts:
            return False
        
        # Aggiungi data modifica
        set_parts.append("data_modifica = ?")
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        params.append(messaggio_id)
        
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE ticker_messaggi SET {', '.join(set_parts)} WHERE id = ?",
            params
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"[ERRORE] modifica_messaggio: {e}")
        return False


def elimina_messaggio(conn, messaggio_id):
    """
    Elimina un messaggio (hard delete).
    
    Args:
        conn: connessione SQLite
        messaggio_id: ID messaggio
    
    Returns:
        bool: True se eliminato
    """
    try:
        cursor = conn.cursor()
        # Elimina log collegati
        cursor.execute("DELETE FROM ticker_log WHERE messaggio_id = ?", (messaggio_id,))
        # Elimina messaggio
        cursor.execute("DELETE FROM ticker_messaggi WHERE id = ?", (messaggio_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


def approva_messaggio(conn, messaggio_id, admin_id):
    """Approva un messaggio in attesa."""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ticker_messaggi 
            SET stato = 'approvato', approvato_da = ?, data_approvazione = ?,
                data_modifica = ?
            WHERE id = ? AND stato IN ('bozza', 'in_attesa')
        """, (admin_id, now, now, messaggio_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


def rifiuta_messaggio(conn, messaggio_id, admin_id, nota=None):
    """Rifiuta un messaggio con nota opzionale."""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ticker_messaggi 
            SET stato = 'rifiutato', approvato_da = ?, data_approvazione = ?,
                nota_rifiuto = ?, data_modifica = ?
            WHERE id = ? AND stato IN ('bozza', 'in_attesa')
        """, (admin_id, now, nota, now, messaggio_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


def invia_per_approvazione(conn, messaggio_id, user_id):
    """Cambia stato da bozza a in_attesa."""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ticker_messaggi 
            SET stato = 'in_attesa', data_modifica = ?
            WHERE id = ? AND stato = 'bozza' AND creato_da = ?
        """, (now, messaggio_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False


# ==============================================================================
# QUERY LISTA
# ==============================================================================

def lista_messaggi(conn, filtri=None, limite=50, offset=0):
    """
    Lista messaggi con filtri.
    
    Args:
        conn: connessione SQLite
        filtri: dict con stato, tipo, destinatari, cerca, creato_da
        limite: max risultati
        offset: offset paginazione
    
    Returns:
        tuple: (lista_messaggi, totale)
    """
    if filtri is None:
        filtri = {}
    
    where = []
    params = []
    
    if filtri.get('stato'):
        where.append("m.stato = ?")
        params.append(filtri['stato'])
    
    if filtri.get('tipo'):
        where.append("m.tipo = ?")
        params.append(filtri['tipo'])
    
    if filtri.get('destinatari'):
        where.append("m.destinatari LIKE ?")
        params.append(f"%{filtri['destinatari']}%")
    
    if filtri.get('cerca'):
        where.append("m.testo LIKE ?")
        params.append(f"%{filtri['cerca']}%")
    
    if filtri.get('creato_da'):
        where.append("m.creato_da = ?")
        params.append(filtri['creato_da'])
    
    where_sql = " AND ".join(where) if where else "1=1"
    
    cursor = conn.cursor()
    
    # Conteggio totale
    cursor.execute(f"SELECT COUNT(*) FROM ticker_messaggi m WHERE {where_sql}", params)
    totale = cursor.fetchone()[0]
    
    # Query con join utenti per nome creatore
    cursor.execute(f"""
        SELECT m.*, 
               u.nome as creatore_nome, u.cognome as creatore_cognome,
               ua.nome as approvatore_nome, ua.cognome as approvatore_cognome
        FROM ticker_messaggi m
        LEFT JOIN utenti u ON m.creato_da = u.id
        LEFT JOIN utenti ua ON m.approvato_da = ua.id
        WHERE {where_sql}
        ORDER BY m.priorita DESC, m.data_creazione DESC
        LIMIT ? OFFSET ?
    """, params + [limite, offset])
    
    messaggi = [dict(zip(
        [desc[0] for desc in cursor.description], row
    )) for row in cursor.fetchall()]
    
    return messaggi, totale


def get_messaggio(conn, messaggio_id):
    """
    Recupera un singolo messaggio completo.
    
    Returns:
        dict o None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, 
               u.nome as creatore_nome, u.cognome as creatore_cognome
        FROM ticker_messaggi m
        LEFT JOIN utenti u ON m.creato_da = u.id
        WHERE m.id = ?
    """, (messaggio_id,))
    
    row = cursor.fetchone()
    if row:
        return dict(zip([desc[0] for desc in cursor.description], row))
    return None


# ==============================================================================
# SCADENZA AUTOMATICA
# ==============================================================================

def scadenza_messaggi(conn):
    """
    Imposta come 'scaduto' i messaggi con data_fine superata.
    Da eseguire periodicamente (cron o all'avvio).
    
    Returns:
        int: numero messaggi scaduti
    """
    try:
        oggi = datetime.now().strftime('%Y-%m-%d')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ticker_messaggi 
            SET stato = 'scaduto', data_modifica = datetime('now', 'localtime')
            WHERE stato = 'approvato'
              AND data_fine IS NOT NULL
              AND data_fine < ?
        """, (oggi,))
        conn.commit()
        return cursor.rowcount
    except Exception:
        return 0


# ==============================================================================
# STATISTICHE
# ==============================================================================

def get_statistiche(conn):
    """
    Statistiche sistema ticker per pannello admin.
    
    Returns:
        dict con conteggi e info
    """
    cursor = conn.cursor()
    
    stats = {}
    
    # Conteggi per stato
    cursor.execute("""
        SELECT stato, COUNT(*) FROM ticker_messaggi GROUP BY stato
    """)
    stats['per_stato'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Conteggi per tipo
    cursor.execute("""
        SELECT tipo, COUNT(*) FROM ticker_messaggi GROUP BY tipo
    """)
    stats['per_tipo'] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Visualizzazioni oggi
    oggi = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) FROM ticker_log
        WHERE data_visualizzazione >= ?
    """, (oggi,))
    stats['visualizzazioni_oggi'] = cursor.fetchone()[0]
    
    # Visualizzazioni ultima settimana
    settimana_fa = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) FROM ticker_log
        WHERE data_visualizzazione >= ?
    """, (settimana_fa,))
    stats['visualizzazioni_settimana'] = cursor.fetchone()[0]
    
    # Messaggi attivi ora
    now = datetime.now()
    cursor.execute("""
        SELECT COUNT(*) FROM ticker_messaggi
        WHERE stato = 'approvato'
          AND data_inizio <= ?
          AND (data_fine IS NULL OR data_fine >= ?)
    """, (oggi, oggi))
    stats['attivi_ora'] = cursor.fetchone()[0]
    
    # In attesa approvazione
    cursor.execute("""
        SELECT COUNT(*) FROM ticker_messaggi WHERE stato = 'in_attesa'
    """)
    stats['in_attesa'] = cursor.fetchone()[0]
    
    return stats


# ==============================================================================
# PULIZIA
# ==============================================================================

def pulisci_log_vecchi(conn, giorni=90):
    """
    Rimuove log visualizzazioni piu vecchi di N giorni.
    
    Returns:
        int: record eliminati
    """
    try:
        limite = (datetime.now() - timedelta(days=giorni)).strftime('%Y-%m-%d')
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM ticker_log WHERE data_visualizzazione < ?",
            (limite,)
        )
        conn.commit()
        return cursor.rowcount
    except Exception:
        return 0
