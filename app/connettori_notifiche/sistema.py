#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
CONNETTORE NOTIFICHE - SISTEMA
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: Connettore per notifiche di sistema (avvio, errori, manutenzione).
             Primo connettore implementato come riferimento per gli altri.

Uso:
    from app.connettori_notifiche.sistema import (
        notifica_avvio_sistema,
        notifica_errore_sistema,
        notifica_manutenzione,
        notifica_test
    )
==============================================================================
"""

from app.motore_notifiche import pubblica_notifica


# ==============================================================================
# NOTIFICHE DI SISTEMA
# ==============================================================================

def notifica_avvio_sistema(conn):
    """
    Genera notifica di avvio/riavvio del sistema.
    Destinatari: ADMIN (via regola DB).
    """
    return pubblica_notifica(
        conn=conn,
        categoria='SISTEMA',
        livello=1,  # INFO
        titolo='Sistema avviato',
        messaggio='Il sistema Gestione Flotta e\' stato avviato correttamente.',
        connettore='sistema',
        codice_evento='avvio_sistema',
        url_azione='/admin',
        etichetta_azione='Pannello admin'
    )


def notifica_errore_sistema(conn, descrizione, dettagli=None):
    """
    Genera notifica di errore di sistema.
    
    Args:
        conn: connessione DB
        descrizione: breve descrizione dell'errore
        dettagli: messaggio dettagliato (opzionale)
    """
    return pubblica_notifica(
        conn=conn,
        categoria='SISTEMA',
        livello=3,  # ALLARME
        titolo=f'Errore: {descrizione}',
        messaggio=dettagli,
        connettore='sistema',
        codice_evento=None,  # errori non deduplicati
        url_azione='/admin',
        etichetta_azione='Pannello admin'
    )


def notifica_manutenzione(conn, messaggio, data_prevista=None):
    """
    Genera notifica di manutenzione programmata.
    Destinatari: TUTTI (inviata a tutti gli utenti attivi).
    
    Args:
        conn: connessione DB
        messaggio: dettagli manutenzione
        data_prevista: data/ora prevista (stringa leggibile)
    """
    titolo = 'Manutenzione programmata'
    if data_prevista:
        titolo += f' - {data_prevista}'
    
    return pubblica_notifica(
        conn=conn,
        categoria='SISTEMA',
        livello=2,  # AVVISO
        titolo=titolo,
        messaggio=messaggio,
        connettore='sistema',
        codice_evento=f'manutenzione_{data_prevista}' if data_prevista else None,
        destinatari_specifici=None  # regole DB decideranno (ADMIN per default)
    )


def notifica_test(conn, destinatario_id=None):
    """
    Genera notifica di test per verificare il sistema.
    
    Args:
        conn: connessione DB
        destinatario_id: utente specifico (se None, va agli ADMIN)
    """
    destinatari = [destinatario_id] if destinatario_id else None
    
    return pubblica_notifica(
        conn=conn,
        categoria='SISTEMA',
        livello=1,  # INFO
        titolo='Notifica di test',
        messaggio='Questa e\' una notifica di test del sistema.',
        connettore='sistema',
        codice_evento=None,  # test non deduplicati
        url_azione='/',
        etichetta_azione='Home',
        destinatari_specifici=destinatari
    )
