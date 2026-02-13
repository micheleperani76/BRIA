#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
CONNETTORE NOTIFICHE - AGGIORNA CRM
==============================================================================
Versione: 1.0.0
Data: 2026-02-13
Descrizione: Genera notifica settimanale (ogni lunedi') per ricordare
             agli utenti abilitati di aggiornare i dati CRM Zoho.
             Destinatari: utenti con flag notifica_aggiorna_crm = 1.
             Toggle globale: ticker_config.promemoria_aggiorna_crm.

Uso:
    from app.connettori_notifiche.aggiorna_crm import notifica_aggiorna_crm
    # Oppure da cron:
    python3 -c "
    import sqlite3
    from app.connettori_notifiche.aggiorna_crm import notifica_aggiorna_crm
    conn = sqlite3.connect('db/gestionale.db')
    conn.row_factory = sqlite3.Row
    notifica_aggiorna_crm(conn)
    conn.close()
    "
==============================================================================
"""

from datetime import datetime

from app.motore_notifiche import pubblica_notifica


def notifica_aggiorna_crm(conn):
    """
    Genera notifica promemoria aggiornamento dati CRM.
    Controlla:
    1. Toggle globale (ticker_config.promemoria_aggiorna_crm)
    2. Utenti con flag notifica_aggiorna_crm = 1

    Args:
        conn: connessione DB SQLite (con row_factory)

    Returns:
        dict: risultato {'success': bool, 'destinatari': int, 'motivo': str}
    """
    cursor = conn.cursor()

    # 1. Verifica toggle globale
    cursor.execute(
        "SELECT valore FROM ticker_config WHERE chiave = 'promemoria_aggiorna_crm'")
    row = cursor.fetchone()
    if not row or row['valore'] != '1':
        return {
            'success': False,
            'destinatari': 0,
            'motivo': 'Toggle globale disattivato'
        }

    # 2. Trova utenti con flag
    cursor.execute("""
        SELECT id FROM utenti
        WHERE attivo = 1 AND notifica_aggiorna_crm = 1
    """)
    utenti = [r['id'] for r in cursor.fetchall()]

    if not utenti:
        return {
            'success': False,
            'destinatari': 0,
            'motivo': 'Nessun utente con flag notifica_aggiorna_crm'
        }

    # 3. Genera notifica con dedup settimanale
    oggi = datetime.now()
    # Codice evento con anno+settimana per dedup (1 per settimana)
    settimana = oggi.strftime('%Y-W%W')
    codice_evento = f'promemoria_crm_{settimana}'

    risultato = pubblica_notifica(
        conn=conn,
        categoria='SISTEMA',
        livello=2,  # AVVISO
        titolo='Aggiornare dati CRM',
        messaggio=(
            'Scaricare da Zoho CRM i file aggiornati e caricarli '
            'nella pagina Amministrazione:\n'
            '- Accounts_AAAA_MM_GG.csv (clienti)\n'
            '- Contacts_AAAA_MM_GG.csv (referenti)\n'
            '- Scadenze_AAAA_MM_GG.csv (veicoli installato)'
        ),
        connettore='aggiorna_crm',
        codice_evento=codice_evento,
        url_azione='/admin',
        etichetta_azione='Vai ad Amministrazione',
        destinatari_specifici=utenti,
    )

    return {
        'success': risultato.get('success', False) if isinstance(risultato, dict) else bool(risultato),
        'destinatari': len(utenti),
        'motivo': 'Notifica inviata'
    }
