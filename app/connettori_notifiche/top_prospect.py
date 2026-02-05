#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
CONNETTORE NOTIFICHE - TOP PROSPECT
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: Connettore per notifiche Top Prospect.
             - Nuovi candidati identificati dall'analisi
             - Candidato confermato come Top Prospect

Uso:
    from app.connettori_notifiche.top_prospect import (
        notifica_nuovi_candidati,
        notifica_top_prospect_confermato
    )
==============================================================================
"""

from app.motore_notifiche import pubblica_notifica


# ==============================================================================
# NOTIFICHE TOP PROSPECT
# ==============================================================================

def notifica_nuovi_candidati(conn, nuovi_candidati):
    """
    Genera notifica quando l'analisi trova nuovi candidati Top Prospect.
    Destinatari: TUTTI (via regole DB).
    
    Args:
        conn: connessione DB
        nuovi_candidati: lista di dict con 'nome_cliente' e 'top_prospect_id'
    
    Returns:
        dict: risultato di pubblica_notifica
    """
    if not nuovi_candidati:
        return {'ok': False, 'motivo': 'Nessun candidato'}
    
    n = len(nuovi_candidati)
    
    if n == 1:
        nome = nuovi_candidati[0].get('nome_cliente', 'Cliente')
        titolo = 'Nuovo Top Prospect candidato'
        messaggio = nome
    else:
        nomi = [c.get('nome_cliente', '?') for c in nuovi_candidati[:5]]
        titolo = f'{n} nuovi Top Prospect candidati'
        messaggio = ', '.join(nomi)
        if n > 5:
            messaggio += f' e altri {n - 5}'
    
    return pubblica_notifica(
        conn=conn,
        categoria='TOP_PROSPECT',
        livello=2,  # AVVISO
        titolo=titolo,
        messaggio=messaggio,
        connettore='top_prospect',
        codice_evento=None,
        url_azione='/top-prospect',
        etichetta_azione='Vai ai Top Prospect',
        destinatari_specifici=None
    )


def notifica_top_prospect_confermato(conn, nome_cliente):
    """
    Genera notifica quando un candidato viene confermato.
    Destinatari: TUTTI (via regole DB).
    
    Args:
        conn: connessione DB
        nome_cliente: nome del cliente confermato
    
    Returns:
        dict: risultato di pubblica_notifica
    """
    return pubblica_notifica(
        conn=conn,
        categoria='TOP_PROSPECT',
        livello=1,  # INFO
        titolo='Top Prospect confermato',
        messaggio=nome_cliente,
        connettore='top_prospect',
        codice_evento=None,
        url_azione='/top-prospect',
        etichetta_azione='Vai ai Top Prospect',
        destinatari_specifici=None
    )
