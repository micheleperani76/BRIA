#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MOTORE NOTIFICHE - Hub Centralizzato
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: Cuore del sistema notifiche. Tutti i connettori chiamano
             pubblica_notifica() per generare notifiche.
             Il motore gestisce: inserimento, dedup, risoluzione destinatari,
             lettura, archiviazione, conteggio.

Funzione pubblica principale:
    pubblica_notifica(conn, categoria, livello, titolo, messaggio,
                      connettore, codice_evento, url_azione, etichetta_azione,
                      destinatari_specifici, data_scadenza)

Uso:
    from app.motore_notifiche import (
        pubblica_notifica,
        get_notifiche_utente,
        get_contatore_non_lette,
        segna_letta,
        segna_tutte_lette,
        archivia_notifica
    )
==============================================================================
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


# ==============================================================================
# IMPORT CONFIGURAZIONE
# ==============================================================================

try:
    from app.config_notifiche import (
        NOTIFICHE_ATTIVO, DEDUP_ATTIVA, DEDUP_FINESTRA_ORE,
        LIVELLO_MINIMO_CAMPANELLA, MAX_NOTIFICHE_DROPDOWN,
        get_colore_categoria, get_icona_categoria, get_etichetta_categoria,
        get_colore_livello, get_nome_livello, get_icona_livello
    )
except ImportError:
    # Fallback per test standalone
    NOTIFICHE_ATTIVO = True
    DEDUP_ATTIVA = True
    DEDUP_FINESTRA_ORE = 24
    LIVELLO_MINIMO_CAMPANELLA = 1
    MAX_NOTIFICHE_DROPDOWN = 15
    def get_colore_categoria(c): return '#6c757d'
    def get_icona_categoria(c): return 'bi-bell'
    def get_etichetta_categoria(c): return c
    def get_colore_livello(l): return '#0dcaf0'
    def get_nome_livello(l): return 'INFO'
    def get_icona_livello(l): return 'bi-info-circle'


# ==============================================================================
# HELPER
# ==============================================================================

def _dict_factory(cursor, row):
    """Converte righe SQLite in dizionari"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _ensure_dict(conn):
    """Imposta row_factory a dict se non gia' impostato"""
    conn.row_factory = _dict_factory
    return conn


def _now():
    """Timestamp corrente formato ISO"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ==============================================================================
# RISOLUZIONE DESTINATARI
# ==============================================================================

def _risolvi_destinatari(conn, categoria, connettore, destinatari_specifici=None):
    """
    Risolve la lista di utente_id che devono ricevere la notifica.
    
    Logica:
    1. Se destinatari_specifici e' fornito, usa quelli
    2. Altrimenti, consulta notifiche_regole per la categoria
    3. Risolve le regole: TUTTI, RUOLO:xxx, PROPRIETARIO, SUPERVISORE
    
    Args:
        conn: connessione DB
        categoria: codice categoria notifica
        connettore: nome connettore che genera la notifica
        destinatari_specifici: lista utente_id espliciti (opzionale)
    
    Returns:
        set di utente_id unici
    """
    cursor = conn.cursor()
    destinatari = set()
    
    # --- Destinatari specifici (passati dal connettore) ---
    if destinatari_specifici:
        destinatari.update(destinatari_specifici)
    
    # --- Regole dalla tabella notifiche_regole ---
    cursor.execute("""
        SELECT destinazione FROM notifiche_regole
        WHERE categoria = ? AND attiva = 1
        AND (connettore IS NULL OR connettore = ?)
    """, (categoria, connettore))
    
    regole = cursor.fetchall()
    
    for regola in regole:
        dest = regola['destinazione'] if isinstance(regola, dict) else regola[0]
        
        if dest == 'TUTTI':
            # Tutti gli utenti attivi
            cursor.execute("SELECT id FROM utenti WHERE attivo = 1")
            destinatari.update(r['id'] if isinstance(r, dict) else r[0] for r in cursor.fetchall())
        
        elif dest.startswith('RUOLO:'):
            ruolo = dest.split(':', 1)[1].lower()
            if ruolo == 'admin':
                cursor.execute("""
                    SELECT id FROM utenti 
                    WHERE attivo = 1 AND ruolo_base = 'admin'
                """)
            else:
                cursor.execute("""
                    SELECT id FROM utenti 
                    WHERE attivo = 1 AND ruolo_base = ?
                """, (ruolo,))
            destinatari.update(r['id'] if isinstance(r, dict) else r[0] for r in cursor.fetchall())
        
        elif dest == 'PROPRIETARIO':
            # Gia' risolto tramite destinatari_specifici
            # Il connettore deve passarli esplicitamente
            pass
        
        elif dest == 'SUPERVISORE':
            # Risolvi supervisori dei destinatari specifici
            if destinatari_specifici:
                for uid in destinatari_specifici:
                    cursor.execute("""
                        SELECT supervisore_id FROM supervisioni
                        WHERE subordinato_id = ? AND data_fine IS NULL
                    """, (uid,))
                    destinatari.update(
                        r['supervisore_id'] if isinstance(r, dict) else r[0] 
                        for r in cursor.fetchall()
                    )
    
    return destinatari


# ==============================================================================
# DEDUPLICAZIONE
# ==============================================================================

def _e_duplicata(conn, codice_evento):
    """
    Verifica se una notifica con lo stesso codice_evento esiste gia'
    entro la finestra temporale di dedup.
    
    Returns:
        True se duplicata (da ignorare), False se nuova
    """
    if not DEDUP_ATTIVA or not codice_evento:
        return False
    
    cursor = conn.cursor()
    soglia = (datetime.now() - timedelta(hours=DEDUP_FINESTRA_ORE)).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM notifiche
        WHERE codice_evento = ? AND data_creazione >= ? AND attiva = 1
    """, (codice_evento, soglia))
    
    row = cursor.fetchone()
    count = row['cnt'] if isinstance(row, dict) else row[0]
    return count > 0


# ==============================================================================
# FUNZIONE PRINCIPALE: PUBBLICA NOTIFICA
# ==============================================================================

def pubblica_notifica(conn, categoria, livello, titolo, messaggio=None,
                      connettore='sistema', codice_evento=None,
                      url_azione=None, etichetta_azione=None,
                      destinatari_specifici=None, data_scadenza=None,
                      ricorrente=False):
    """
    Pubblica una nuova notifica nell'hub centralizzato.
    
    Questa e' la UNICA funzione che i connettori devono chiamare.
    
    Args:
        conn: connessione DB (con row_factory dict)
        categoria: codice categoria (es. 'TASK', 'SISTEMA', 'TRATTATIVA')
        livello: 0=DEBUG, 1=INFO, 2=AVVISO, 3=ALLARME
        titolo: titolo breve della notifica
        messaggio: testo dettagliato (opzionale)
        connettore: nome del connettore che genera (es. 'task', 'sistema')
        codice_evento: codice univoco per deduplicazione (opzionale)
        url_azione: URL relativo da aprire (es. '/clienti/123')
        etichetta_azione: testo del link (es. 'Vai al cliente')
        destinatari_specifici: lista di utente_id espliciti
        data_scadenza: data dopo la quale eliminare (formato 'YYYY-MM-DD')
        ricorrente: True se la notifica si ripete periodicamente
    
    Returns:
        dict: {'ok': True, 'notifica_id': N, 'destinatari': M}
              {'ok': False, 'motivo': '...'}
    """
    if not NOTIFICHE_ATTIVO:
        return {'ok': False, 'motivo': 'Sistema notifiche disattivato'}
    
    _ensure_dict(conn)
    cursor = conn.cursor()
    
    # --- Deduplicazione ---
    if _e_duplicata(conn, codice_evento):
        return {'ok': False, 'motivo': f'Duplicata: {codice_evento}'}
    
    # --- Inserisci notifica ---
    try:
        cursor.execute("""
            INSERT INTO notifiche 
            (categoria, livello, titolo, messaggio, url_azione, etichetta_azione,
             connettore, codice_evento, data_creazione, data_scadenza, ricorrente, attiva)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            categoria, livello, titolo, messaggio,
            url_azione, etichetta_azione,
            connettore, codice_evento,
            _now(), data_scadenza,
            1 if ricorrente else 0
        ))
        
        notifica_id = cursor.lastrowid
        
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'motivo': f'Errore inserimento: {e}'}
    
    # --- Risolvi destinatari ---
    destinatari = _risolvi_destinatari(conn, categoria, connettore, destinatari_specifici)
    
    if not destinatari:
        # Notifica senza destinatari: la teniamo comunque come log
        conn.commit()
        return {'ok': True, 'notifica_id': notifica_id, 'destinatari': 0}
    
    # --- Inserisci destinatari ---
    inseriti = 0
    for utente_id in destinatari:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO notifiche_destinatari 
                (notifica_id, utente_id, letta, archiviata)
                VALUES (?, ?, 0, 0)
            """, (notifica_id, utente_id))
            inseriti += cursor.rowcount
        except Exception:
            pass  # UNIQUE constraint, ignora
    
    conn.commit()
    
    return {'ok': True, 'notifica_id': notifica_id, 'destinatari': inseriti}


# ==============================================================================
# LETTURA NOTIFICHE
# ==============================================================================

def get_contatore_non_lette(conn, utente_id):
    """
    Conta le notifiche non lette per un utente.
    Usata dal polling della campanella.
    
    Args:
        conn: connessione DB
        utente_id: ID utente
    
    Returns:
        int: numero notifiche non lette
    """
    _ensure_dict(conn)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM notifiche_destinatari nd
        JOIN notifiche n ON n.id = nd.notifica_id
        WHERE nd.utente_id = ?
        AND nd.letta = 0
        AND nd.archiviata = 0
        AND n.attiva = 1
        AND n.livello >= ?
    """, (utente_id, LIVELLO_MINIMO_CAMPANELLA))
    
    row = cursor.fetchone()
    return row['cnt'] if row else 0


def get_notifiche_utente(conn, utente_id, solo_non_lette=False, 
                         limite=None, offset=0, categoria=None):
    """
    Recupera le notifiche per un utente con arricchimento dati.
    
    Args:
        conn: connessione DB
        utente_id: ID utente
        solo_non_lette: True per filtrare solo non lette
        limite: max risultati (default: MAX_NOTIFICHE_DROPDOWN)
        offset: per paginazione
        categoria: filtro per categoria specifica
    
    Returns:
        Lista di dict arricchiti con colori/icone
    """
    _ensure_dict(conn)
    cursor = conn.cursor()
    
    if limite is None:
        limite = MAX_NOTIFICHE_DROPDOWN
    
    # Query base
    sql = """
        SELECT 
            n.id, n.categoria, n.livello, n.titolo, n.messaggio,
            n.url_azione, n.etichetta_azione, n.connettore,
            n.data_creazione, n.data_scadenza,
            nd.letta, nd.data_lettura, nd.archiviata
        FROM notifiche_destinatari nd
        JOIN notifiche n ON n.id = nd.notifica_id
        WHERE nd.utente_id = ?
        AND nd.archiviata = 0
        AND n.attiva = 1
        AND n.livello >= ?
    """
    params = [utente_id, LIVELLO_MINIMO_CAMPANELLA]
    
    if solo_non_lette:
        sql += " AND nd.letta = 0"
    
    if categoria:
        sql += " AND n.categoria = ?"
        params.append(categoria)
    
    sql += " ORDER BY n.data_creazione DESC LIMIT ? OFFSET ?"
    params.extend([limite, offset])
    
    cursor.execute(sql, params)
    notifiche = cursor.fetchall()
    
    # Arricchisci con colori/icone da config
    risultato = []
    for n in notifiche:
        enriched = dict(n)
        enriched['colore_categoria'] = get_colore_categoria(n['categoria'])
        enriched['icona_categoria'] = get_icona_categoria(n['categoria'])
        enriched['etichetta_categoria'] = get_etichetta_categoria(n['categoria'])
        enriched['colore_livello'] = get_colore_livello(n['livello'])
        enriched['nome_livello'] = get_nome_livello(n['livello'])
        enriched['icona_livello'] = get_icona_livello(n['livello'])
        enriched['tempo_fa'] = _tempo_fa(n['data_creazione'])
        risultato.append(enriched)
    
    return risultato


def _tempo_fa(data_str):
    """
    Converte una data in formato leggibile 'tempo fa'.
    
    Args:
        data_str: data formato 'YYYY-MM-DD HH:MM:SS'
    
    Returns:
        str: es. '5 min fa', '2 ore fa', 'ieri', '3 giorni fa'
    """
    try:
        data = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return ''
    
    delta = datetime.now() - data
    secondi = int(delta.total_seconds())
    
    if secondi < 60:
        return 'adesso'
    elif secondi < 3600:
        minuti = secondi // 60
        return f'{minuti} min fa'
    elif secondi < 86400:
        ore = secondi // 3600
        return f'{ore} {"ora" if ore == 1 else "ore"} fa'
    elif secondi < 172800:
        return 'ieri'
    elif secondi < 604800:
        giorni = secondi // 86400
        return f'{giorni} giorni fa'
    else:
        return data.strftime('%d/%m/%Y')


# ==============================================================================
# AZIONI UTENTE
# ==============================================================================

def segna_letta(conn, utente_id, notifica_id):
    """
    Segna una notifica come letta per un utente.
    
    Returns:
        bool: True se aggiornata, False se non trovata
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE notifiche_destinatari 
        SET letta = 1, data_lettura = ?
        WHERE utente_id = ? AND notifica_id = ? AND letta = 0
    """, (_now(), utente_id, notifica_id))
    
    conn.commit()
    return cursor.rowcount > 0


def segna_tutte_lette(conn, utente_id, categoria=None):
    """
    Segna tutte le notifiche come lette per un utente.
    
    Args:
        conn: connessione DB
        utente_id: ID utente
        categoria: se specificato, solo quella categoria
    
    Returns:
        int: numero di notifiche aggiornate
    """
    cursor = conn.cursor()
    
    if categoria:
        cursor.execute("""
            UPDATE notifiche_destinatari 
            SET letta = 1, data_lettura = ?
            WHERE utente_id = ? AND letta = 0
            AND notifica_id IN (
                SELECT id FROM notifiche WHERE categoria = ? AND attiva = 1
            )
        """, (_now(), utente_id, categoria))
    else:
        cursor.execute("""
            UPDATE notifiche_destinatari 
            SET letta = 1, data_lettura = ?
            WHERE utente_id = ? AND letta = 0
        """, (_now(), utente_id))
    
    aggiornate = cursor.rowcount
    conn.commit()
    return aggiornate


def archivia_notifica(conn, utente_id, notifica_id):
    """
    Archivia una notifica per un utente (sparisce dal dropdown).
    
    Returns:
        bool: True se archiviata
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE notifiche_destinatari 
        SET archiviata = 1, data_archiviazione = ?
        WHERE utente_id = ? AND notifica_id = ? AND archiviata = 0
    """, (_now(), utente_id, notifica_id))
    
    conn.commit()
    return cursor.rowcount > 0


# ==============================================================================
# PULIZIA
# ==============================================================================

def pulisci_notifiche_scadute(conn):
    """
    Rimuove notifiche con data_scadenza passata.
    Da chiamare periodicamente (cron o all'avvio).
    
    Returns:
        int: numero notifiche disattivate
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE notifiche SET attiva = 0
        WHERE data_scadenza IS NOT NULL 
        AND data_scadenza < ? 
        AND attiva = 1
    """, (_now(),))
    
    disattivate = cursor.rowcount
    conn.commit()
    return disattivate


def pulisci_notifiche_vecchie(conn, giorni_lette=90, giorni_non_lette=180, giorni_archiviate=30):
    """
    Pulizia periodica notifiche vecchie.
    Elimina fisicamente le notifiche e i loro destinatari.
    
    Returns:
        dict: {'lette': N, 'archiviate': M}
    """
    cursor = conn.cursor()
    risultato = {'lette': 0, 'archiviate': 0}
    
    # Elimina destinatari archiviati vecchi
    if giorni_archiviate > 0:
        soglia = (datetime.now() - timedelta(days=giorni_archiviate)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            DELETE FROM notifiche_destinatari
            WHERE archiviata = 1 AND data_archiviazione < ?
        """, (soglia,))
        risultato['archiviate'] = cursor.rowcount
    
    # Elimina destinatari letti vecchi
    if giorni_lette > 0:
        soglia = (datetime.now() - timedelta(days=giorni_lette)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            DELETE FROM notifiche_destinatari
            WHERE letta = 1 AND data_lettura < ?
        """, (soglia,))
        risultato['lette'] = cursor.rowcount
    
    # Elimina notifiche orfane (senza destinatari)
    cursor.execute("""
        DELETE FROM notifiche
        WHERE id NOT IN (SELECT DISTINCT notifica_id FROM notifiche_destinatari)
        AND data_creazione < ?
    """, ((datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),))
    
    conn.commit()
    return risultato


# ==============================================================================
# STATISTICHE (per admin)
# ==============================================================================

def get_statistiche_notifiche(conn):
    """
    Statistiche generali per il pannello admin.
    
    Returns:
        dict con conteggi vari
    """
    _ensure_dict(conn)
    cursor = conn.cursor()
    
    stats = {}
    
    # Totale notifiche attive
    cursor.execute("SELECT COUNT(*) as cnt FROM notifiche WHERE attiva = 1")
    stats['totale_attive'] = cursor.fetchone()['cnt']
    
    # Per categoria
    cursor.execute("""
        SELECT categoria, COUNT(*) as cnt 
        FROM notifiche WHERE attiva = 1 
        GROUP BY categoria ORDER BY cnt DESC
    """)
    stats['per_categoria'] = {r['categoria']: r['cnt'] for r in cursor.fetchall()}
    
    # Non lette totali
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM notifiche_destinatari 
        WHERE letta = 0 AND archiviata = 0
    """)
    stats['non_lette_totale'] = cursor.fetchone()['cnt']
    
    # Ultime 24 ore
    soglia = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM notifiche 
        WHERE data_creazione >= ? AND attiva = 1
    """, (soglia,))
    stats['ultime_24h'] = cursor.fetchone()['cnt']
    
    return stats


# ==============================================================================
# TEST STANDALONE
# ==============================================================================

if __name__ == '__main__':
    import os
    
    DB_PATH = os.path.expanduser('~/gestione_flotta/db/gestionale.db')
    
    print("=" * 60)
    print("TEST MOTORE NOTIFICHE")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    
    # Test: pubblica notifica di test
    print("\n1. Test pubblica_notifica (SISTEMA)...")
    risultato = pubblica_notifica(
        conn=conn,
        categoria='SISTEMA',
        livello=1,
        titolo='Test motore notifiche',
        messaggio='Notifica di test generata dal motore',
        connettore='sistema',
        codice_evento='test_motore_001'
    )
    print(f"   Risultato: {risultato}")
    
    # Test: contatore
    print("\n2. Test contatore non lette (utente 1)...")
    cnt = get_contatore_non_lette(conn, 1)
    print(f"   Non lette: {cnt}")
    
    # Test: lista notifiche
    print("\n3. Test get_notifiche_utente (utente 1)...")
    notifiche = get_notifiche_utente(conn, 1, limite=5)
    print(f"   Trovate: {len(notifiche)}")
    for n in notifiche:
        print(f"   - [{n['nome_livello']}] {n['titolo']} ({n['tempo_fa']})")
    
    # Test: statistiche
    print("\n4. Statistiche...")
    stats = get_statistiche_notifiche(conn)
    print(f"   Attive: {stats['totale_attive']}")
    print(f"   Non lette: {stats['non_lette_totale']}")
    print(f"   Ultime 24h: {stats['ultime_24h']}")
    print(f"   Per categoria: {stats['per_categoria']}")
    
    # Test: dedup
    print("\n5. Test deduplicazione...")
    risultato2 = pubblica_notifica(
        conn=conn,
        categoria='SISTEMA',
        livello=1,
        titolo='Test duplicato',
        connettore='sistema',
        codice_evento='test_motore_001'
    )
    print(f"   Risultato (deve essere duplicata): {risultato2}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("TEST COMPLETATI")
    print("=" * 60)
