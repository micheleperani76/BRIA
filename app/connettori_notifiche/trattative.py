#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
CONNETTORE NOTIFICHE - TRATTATIVE
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: Connettore per notifiche trattative.
             - Nuova trattativa creata
             - Avanzamento stato trattativa
             Destinatari: tutti i supervisori nella catena gerarchica
             sopra al commerciale proprietario.

Uso:
    from app.connettori_notifiche.trattative import (
        notifica_nuova_trattativa,
        notifica_avanzamento_trattativa
    )
==============================================================================
"""

from app.motore_notifiche import pubblica_notifica


# ==============================================================================
# HELPER: CATENA SUPERVISORI
# ==============================================================================

def _risali_catena_supervisori(conn, utente_id):
    """
    Risale tutta la catena gerarchica e restituisce gli ID
    di tutti i supervisori sopra l'utente dato.
    
    Es: Prova(id=5) -> Michele(id=2) -> Paolo(id=1)
        Restituisce [2, 1]
    
    Args:
        conn: connessione DB
        utente_id: ID del commerciale di partenza
    
    Returns:
        list: lista di utente_id dei supervisori (dal piu' vicino al piu' lontano)
    """
    supervisori = []
    visitati = set()  # anti-loop
    corrente = utente_id
    
    while corrente and corrente not in visitati:
        visitati.add(corrente)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT supervisore_id FROM supervisioni
            WHERE subordinato_id = ? AND data_fine IS NULL
        """, (corrente,))
        rows = cursor.fetchall()
        
        if not rows:
            break
        
        for row in rows:
            sup_id = row['supervisore_id'] if isinstance(row, dict) else row[0]
            if sup_id and sup_id not in visitati:
                supervisori.append(sup_id)
                corrente = sup_id
    
    return supervisori


def _get_nome_cliente(conn, cliente_id):
    """Recupera denominazione cliente dal DB."""
    cursor = conn.cursor()
    cursor.execute("SELECT ragione_sociale FROM clienti WHERE id = ?", (cliente_id,))
    row = cursor.fetchone()
    if row:
        return row['ragione_sociale'] if isinstance(row, dict) else row[0]
    return 'Cliente'


# ==============================================================================
# NOTIFICHE TRATTATIVE
# ==============================================================================

def notifica_nuova_trattativa(conn, trattativa_id, commerciale_id, cliente_id, stato):
    """
    Genera notifica per nuova trattativa creata.
    Destinatari: tutti i supervisori sopra al commerciale.
    
    Args:
        conn: connessione DB
        trattativa_id: ID trattativa appena creata
        commerciale_id: ID del commerciale proprietario
        cliente_id: ID del cliente
        stato: stato iniziale della trattativa
    
    Returns:
        dict: risultato di pubblica_notifica (o None se nessun destinatario)
    """
    supervisori = _risali_catena_supervisori(conn, commerciale_id)
    
    if not supervisori:
        return None  # nessun supervisore, nessuna notifica
    
    nome_cliente = _get_nome_cliente(conn, cliente_id)
    
    # Recupera nome commerciale
    cursor = conn.cursor()
    cursor.execute("SELECT nome || ' ' || cognome FROM utenti WHERE id = ?", (commerciale_id,))
    row = cursor.fetchone()
    nome_commerciale = row['nome_completo'] if row else '?'
    
    return pubblica_notifica(
        conn=conn,
        categoria='TRATTATIVA',
        livello=1,  # INFO
        titolo='Nuova trattativa',
        messaggio=f'{nome_commerciale}\n{nome_cliente}',
        connettore='trattative',
        codice_evento=f'trattativa_nuova_{trattativa_id}',
        url_azione='/trattative',
        etichetta_azione='Vai alle trattative',
        destinatari_specifici=supervisori
    )


def notifica_avanzamento_trattativa(conn, trattativa_id, commerciale_id,
                                     cliente_id, nuovo_stato):
    """
    Genera notifica per avanzamento stato trattativa.
    Destinatari: tutti i supervisori sopra al commerciale.
    
    Args:
        conn: connessione DB
        trattativa_id: ID trattativa
        commerciale_id: ID del commerciale che ha avanzato
        cliente_id: ID del cliente
        nuovo_stato: nuovo stato della trattativa
    
    Returns:
        dict: risultato di pubblica_notifica (o None se nessun destinatario)
    """
    supervisori = _risali_catena_supervisori(conn, commerciale_id)
    
    if not supervisori:
        return None
    
    nome_cliente = _get_nome_cliente(conn, cliente_id)
    
    # Nome commerciale
    cursor = conn.cursor()
    cursor.execute("SELECT nome || ' ' || cognome AS nome_completo FROM utenti WHERE id = ?", (commerciale_id,))
    row = cursor.fetchone()
    nome_commerciale = row['nome_completo'] if row else '?'
    
    return pubblica_notifica(
        conn=conn,
        categoria='TRATTATIVA',
        livello=1,  # INFO
        titolo=f'Trattativa: {nuovo_stato}',
        messaggio=f'{nome_commerciale}\n{nome_cliente}',
        connettore='trattative',
        codice_evento=f'trattativa_avanz_{trattativa_id}_{nuovo_stato}',
        url_azione='/trattative',
        etichetta_azione='Vai alle trattative',
        destinatari_specifici=supervisori
    )
