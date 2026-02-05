#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
CONNETTORE NOTIFICHE - TRASCRIZIONE
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: Connettore per notifiche del sistema di trascrizione audio.
             Notifica l'utente quando una trascrizione e' completata o fallita.

Uso:
    from app.connettori_notifiche.trascrizione import (
        notifica_trascrizione_completata,
        notifica_trascrizione_errore
    )
==============================================================================
"""

from app.motore_notifiche import pubblica_notifica


# ==============================================================================
# NOTIFICHE TRASCRIZIONE
# ==============================================================================

def notifica_trascrizione_completata(conn, job):
    """
    Genera notifica di trascrizione completata con successo.
    Destinatario: l'utente che ha inserito il job.
    
    Args:
        conn: connessione DB (con row_factory dict)
        job: dict del job dalla tabella coda_trascrizioni
    
    Returns:
        dict: risultato di pubblica_notifica
    """
    utente_id = job.get('utente_id')
    nome_file = job.get('nome_file_originale', 'file audio')
    tipo = job.get('tipo', 'dashboard')
    cliente_id = job.get('cliente_id')
    job_id = job.get('id')
    
    # Titolo e messaggio differenziati per tipo
    if tipo == 'cliente' and cliente_id:
        titolo = 'Trascrizione completata'
        messaggio = f'La trascrizione di "{nome_file}" e\' pronta.'
        url_azione = f'/clienti/{cliente_id}/documenti'
        etichetta_azione = 'Vai ai documenti'
    else:
        titolo = 'Trascrizione completata'
        messaggio = f'La trascrizione di "{nome_file}" e\' pronta.'
        url_azione = '/trascrizione'
        etichetta_azione = 'Vai alle trascrizioni'
    
    # Destinatari: l'utente che ha caricato il file
    destinatari = [utente_id] if utente_id else None
    
    return pubblica_notifica(
        conn=conn,
        categoria='TRASCRIZIONE',
        livello=1,  # INFO
        titolo=titolo,
        messaggio=messaggio,
        connettore='trascrizione',
        codice_evento=f'trascrizione_ok_{job_id}',
        url_azione=url_azione,
        etichetta_azione=etichetta_azione,
        destinatari_specifici=destinatari
    )


def notifica_trascrizione_errore(conn, job, errore_desc=None):
    """
    Genera notifica di errore trascrizione.
    Destinatario: l'utente che ha inserito il job.
    
    Args:
        conn: connessione DB (con row_factory dict)
        job: dict del job dalla tabella coda_trascrizioni
        errore_desc: descrizione dell'errore (opzionale)
    
    Returns:
        dict: risultato di pubblica_notifica
    """
    utente_id = job.get('utente_id')
    nome_file = job.get('nome_file_originale', 'file audio')
    job_id = job.get('id')
    
    titolo = 'Errore trascrizione'
    messaggio = f'La trascrizione di "{nome_file}" e\' fallita.'
    if errore_desc:
        messaggio += f' Motivo: {errore_desc}'
    
    # Destinatari: l'utente che ha caricato + admin (via regole DB)
    destinatari = [utente_id] if utente_id else None
    
    return pubblica_notifica(
        conn=conn,
        categoria='TRASCRIZIONE',
        livello=2,  # AVVISO
        titolo=titolo,
        messaggio=messaggio,
        connettore='trascrizione',
        codice_evento=f'trascrizione_err_{job_id}',
        url_azione='/trascrizione',
        etichetta_azione='Vai alle trascrizioni',
        destinatari_specifici=destinatari
    )
