#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
ROUTES REVISIONI - Blueprint Flask
==============================================================================
Versione: 1.0.0
Data: 2026-02-09
Descrizione: Pagina dedicata gestione revisioni veicoli.
             - Tabella completa con filtri e azioni
             - Filtrata per gerarchia commerciale
             - Pulsanti gestione inline (fatta/visione/reset)
             - Counter giorni mancanti colorato
             - Accesso controllato da permesso 'revisioni_view'

Route:
    GET  /revisioni                    - Pagina principale
    POST /revisioni/<id>/gestisci      - Azione revisione (fatta/visione/reset)
    GET  /revisioni/api/contatore      - Contatore badge sidebar
==============================================================================
"""

from flask import Blueprint, render_template, request, jsonify, session
import sqlite3
from functools import wraps
from datetime import datetime

from app.config import DB_FILE
from app.database_utenti import get_subordinati, ha_permesso
from app.connettori_notifiche.revisione import calcola_prossima_revisione


# ==============================================================================
# BLUEPRINT
# ==============================================================================

revisioni_bp = Blueprint('revisioni', __name__, url_prefix='/revisioni')


# ==============================================================================
# DECORATORI
# ==============================================================================

def _richiedi_login(f):
    """Verifica che l'utente sia autenticato."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def _get_conn():
    """Connessione DB con row_factory dict."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==============================================================================
# PAGINA PRINCIPALE
# ==============================================================================

@revisioni_bp.route('')
@_richiedi_login
def index():
    """
    Pagina gestione revisioni.
    Mostra tutti i veicoli con data immatricolazione,
    filtrati per gerarchia commerciale.
    """
    conn = _get_conn()
    
    if not ha_permesso(conn, session['user_id'], 'revisioni_view'):
        conn.close()
        from flask import abort
        abort(403)
    
    # Filtro dalla query string
    filtro_stato = request.args.get('stato', 'tutti')  # tutti, da_gestire, gestiti, scaduti
    
    cursor = conn.cursor()
    
    # Visibilita': admin e utenti con permesso revisioni vedono tutto,
    # commerciali vedono solo i propri veicoli e quelli dei subordinati
    cursor.execute("SELECT ruolo_base FROM utenti WHERE id = ?", (session['user_id'],))
    utente_row = cursor.fetchone()
    ruolo = dict(utente_row).get('ruolo_base', '') if utente_row else ''
    
    if ruolo == 'admin':
        # Admin vede tutto
        query = """
            SELECT v.id, v.targa, v.marca, v.modello, v.tipo,
                   v.data_immatricolazione, v.revisione_gestita,
                   v.data_revisione, v.note_revisione,
                   v.commerciale_id, v.cliente_id, v.nome_cliente, v.p_iva, v.cod_fiscale,
                   v.driver, v.driver_telefono, v.driver_email,
                   v.noleggiatore, v.scadenza
            FROM veicoli_attivi v
            WHERE v.data_immatricolazione IS NOT NULL
              AND v.data_immatricolazione != ''
            ORDER BY v.data_immatricolazione ASC
        """
        cursor.execute(query)
    else:
        # Commerciali: gerarchia. Operatori con permesso: tutto
        utenti_visibili = get_subordinati(conn, session['user_id'])
        
        # Se l'utente non ha veicoli assegnati (operatore), mostra tutto
        cursor.execute("SELECT COUNT(*) as n FROM veicoli_attivi WHERE commerciale_id IN ({})".format(
            ','.join(['?' for _ in utenti_visibili])), utenti_visibili)
        count = dict(cursor.fetchone()).get('n', 0)
        
        if count == 0:
            # Operatore senza veicoli propri: vede tutto
            query = """
                SELECT v.id, v.targa, v.marca, v.modello, v.tipo,
                       v.data_immatricolazione, v.revisione_gestita,
                       v.data_revisione, v.note_revisione,
                       v.commerciale_id, v.cliente_id, v.nome_cliente, v.p_iva, v.cod_fiscale,
                       v.driver, v.driver_telefono, v.driver_email,
                       v.noleggiatore, v.scadenza
                FROM veicoli_attivi v
                WHERE v.data_immatricolazione IS NOT NULL
                  AND v.data_immatricolazione != ''
                ORDER BY v.data_immatricolazione ASC
            """
            cursor.execute(query)
        else:
            # Commerciale: solo gerarchia
            placeholders = ','.join(['?' for _ in utenti_visibili])
            query = f"""
                SELECT v.id, v.targa, v.marca, v.modello, v.tipo,
                       v.data_immatricolazione, v.revisione_gestita,
                       v.data_revisione, v.note_revisione,
                       v.commerciale_id, v.cliente_id, v.nome_cliente, v.p_iva, v.cod_fiscale,
                       v.driver, v.driver_telefono, v.driver_email,
                       v.noleggiatore, v.scadenza
                FROM veicoli_attivi v
                WHERE v.data_immatricolazione IS NOT NULL
                  AND v.data_immatricolazione != ''
                  AND v.commerciale_id IN ({placeholders})
                ORDER BY v.data_immatricolazione ASC
            """
            cursor.execute(query, utenti_visibili)
    veicoli_raw = [dict(row) for row in cursor.fetchall()]
    
    # Arricchisci con calcolo revisione
    veicoli = []
    contatori = {'totale': 0, 'da_gestire': 0, 'gestiti': 0, 'scaduti': 0}
    
    for v in veicoli_raw:
        prossima, giorni = calcola_prossima_revisione(v['data_immatricolazione'])
        v['prossima_revisione'] = prossima
        v['giorni_revisione'] = giorni
        
        # Estrai nome modello dal campo tipo
        v['nome_modello'] = ''
        if v.get('tipo'):
            v['nome_modello'] = v['tipo'].split('/')[0].strip()
        
        # Nome commerciale
        cursor.execute(
            "SELECT nome || ' ' || cognome AS nome_completo FROM utenti WHERE id = ?",
            (v.get('commerciale_id'),)
        )
        row_comm = cursor.fetchone()
        v['nome_commerciale'] = dict(row_comm)['nome_completo'] if row_comm else '-'
        
        # Telefono azienda
        v['telefono_azienda'] = ''
        if v.get('cliente_id'):
            cursor.execute("SELECT telefono FROM clienti WHERE id = ?", (v['cliente_id'],))
            row_tel = cursor.fetchone()
            if row_tel:
                v['telefono_azienda'] = dict(row_tel).get('telefono', '') or ''
        
        # Referente principale
        v['referente_nome'] = ''
        v['referente_telefono'] = ''
        if v.get('cliente_id'):
            cursor.execute("""
                SELECT nome, cognome, telefono, cellulare 
                FROM referenti_clienti 
                WHERE cliente_id = ? AND principale = 1 
                LIMIT 1
            """, (v['cliente_id'],))
            row_ref = cursor.fetchone()
            if row_ref:
                ref = dict(row_ref)
                nome = (ref.get('nome') or '').strip()
                cognome = (ref.get('cognome') or '').strip()
                v['referente_nome'] = f"{nome} {cognome}".strip()
                v['referente_telefono'] = ref.get('cellulare') or ref.get('telefono') or ''
        
        # Stato revisione
        if v.get('revisione_gestita') == prossima:
            if v.get('data_revisione'):
                v['stato_revisione'] = 'fatta'
            else:
                v['stato_revisione'] = 'visione'
            contatori['gestiti'] += 1
        elif giorni is not None and giorni <= 0:
            v['stato_revisione'] = 'scaduta'
            contatori['scaduti'] += 1
            contatori['da_gestire'] += 1
        else:
            v['stato_revisione'] = 'attesa'
            contatori['da_gestire'] += 1
        
        contatori['totale'] += 1
        
        # Filtro stato
        if filtro_stato == 'da_gestire' and v['stato_revisione'] in ('fatta', 'visione'):
            continue
        elif filtro_stato == 'gestiti' and v['stato_revisione'] not in ('fatta', 'visione'):
            continue
        elif filtro_stato == 'scaduti' and v['stato_revisione'] != 'scaduta':
            continue
        
        veicoli.append(v)
    
    # Ordina per giorni mancanti (urgenti prima)
    veicoli.sort(key=lambda x: x.get('giorni_revisione') or 9999)
    
    conn.close()
    
    return render_template('revisioni/index.html',
                         veicoli=veicoli,
                         contatori=contatori,
                         filtro_stato=filtro_stato,
                         oggi=datetime.now().strftime('%Y-%m-%d'))


# ==============================================================================
# AZIONE REVISIONE
# ==============================================================================

@revisioni_bp.route('/<int:veicolo_id>/gestisci', methods=['POST'])
@_richiedi_login
def gestisci_revisione(veicolo_id):
    """Gestione revisione da pagina dedicata (fatta/visione/reset)."""
    conn_check = _get_conn()
    if not ha_permesso(conn_check, session['user_id'], 'revisioni_view'):
        conn_check.close()
        return jsonify({'success': False, 'error': 'Permesso negato'}), 403
    conn_check.close()
    
    data = request.get_json()
    if not data or not data.get('azione'):
        return jsonify({'success': False, 'error': 'Azione mancante'}), 400
    
    azione = data['azione']
    conn = _get_conn()
    
    try:
        if azione == 'fatta':
            conn.execute(
                """UPDATE veicoli 
                   SET revisione_gestita = ?, data_revisione = ?, note_revisione = ?
                   WHERE id = ?""",
                (data.get('scadenza'), data.get('data_revisione'), data.get('note'), veicolo_id)
            )
        elif azione == 'visione':
            conn.execute(
                """UPDATE veicoli 
                   SET revisione_gestita = ?, data_revisione = NULL, note_revisione = ?
                   WHERE id = ?""",
                (data.get('scadenza'), data.get('note'), veicolo_id)
            )
        elif azione == 'reset':
            conn.execute(
                """UPDATE veicoli 
                   SET revisione_gestita = NULL, data_revisione = NULL, note_revisione = NULL
                   WHERE id = ?""",
                (veicolo_id,)
            )
        else:
            return jsonify({'success': False, 'error': 'Azione non valida'}), 400
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API CONTATORE (per badge sidebar)
# ==============================================================================

@revisioni_bp.route('/api/contatore')
@_richiedi_login
def api_contatore():
    """Contatore revisioni da gestire (per badge sidebar)."""
    conn = _get_conn()
    
    utenti_visibili = get_subordinati(conn, session['user_id'])
    placeholders = ','.join(['?' for _ in utenti_visibili])
    
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT id, data_immatricolazione, revisione_gestita
        FROM veicoli_attivi
        WHERE data_immatricolazione IS NOT NULL
          AND data_immatricolazione != ''
          AND commerciale_id IN ({placeholders})
    """, utenti_visibili)
    
    da_gestire = 0
    for row in cursor.fetchall():
        v = dict(row)
        prossima, giorni = calcola_prossima_revisione(v['data_immatricolazione'])
        if prossima and v.get('revisione_gestita') != prossima and giorni is not None and giorni <= 60:
            da_gestire += 1
    
    conn.close()
    return jsonify({'contatore': da_gestire})
