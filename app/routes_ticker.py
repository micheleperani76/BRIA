# -*- coding: utf-8 -*-
"""
==============================================================================
ROUTES TICKER BROADCASTING - Blueprint Flask
==============================================================================
Versione: 1.0.0
Data: 2026-02-06
Descrizione: API HTTP per il sistema ticker broadcasting

Route disponibili:
    GET  /ticker/api/prossimo          - Prossimo messaggio per widget
    POST /ticker/api/visto/<id>        - Registra visualizzazione
    GET  /ticker/api/lista             - Lista messaggi (gestione)
    POST /ticker/api/crea              - Crea messaggio
    POST /ticker/api/<id>/modifica     - Modifica messaggio
    POST /ticker/api/<id>/elimina      - Elimina messaggio
    POST /ticker/api/<id>/approva      - Approva messaggio (admin)
    POST /ticker/api/<id>/rifiuta      - Rifiuta messaggio (admin)
    POST /ticker/api/<id>/invia        - Invia per approvazione
    GET  /ticker/api/config            - Leggi configurazione (admin)
    POST /ticker/api/config            - Salva configurazione (admin)
    GET  /ticker/api/statistiche       - Statistiche (admin)
    GET  /ticker/gestione              - Pagina gestione ticker
==============================================================================
"""

from flask import Blueprint, render_template, request, jsonify, session
import sqlite3
from functools import wraps

from app.config import DB_FILE
from app.motore_ticker import (
    get_prossimo_messaggio,
    calcola_prossimo_check,
    registra_visualizzazione,
    crea_messaggio,
    modifica_messaggio,
    elimina_messaggio,
    approva_messaggio,
    rifiuta_messaggio,
    invia_per_approvazione,
    lista_messaggi,
    get_messaggio,
    scadenza_messaggi,
    get_statistiche,
    pulisci_log_vecchi
)
from app.config_ticker import (
    get_all_config,
    set_config,
    is_ticker_attivo,
    get_animazioni_dropdown,
    get_velocita_dropdown,
    get_destinatari_dropdown,
    ANIMAZIONI, VELOCITA, STATI_MESSAGGIO, TIPI_MESSAGGIO,
    RICORRENZE, DESTINATARI_PREDEFINITI, GIORNI_SETTIMANA
)


# ==============================================================================
# BLUEPRINT
# ==============================================================================

ticker_bp = Blueprint('ticker', __name__, url_prefix='/ticker')


# ==============================================================================
# DECORATORI
# ==============================================================================

def _richiedi_login(f):
    """Verifica che l'utente sia autenticato."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'errore': 'Non autenticato'}), 401
        return f(*args, **kwargs)
    return decorated


def _richiedi_admin(f):
    """Verifica ruolo admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'errore': 'Non autenticato'}), 401
        if session.get('ruolo_base') != 'admin':
            return jsonify({'errore': 'Accesso negato'}), 403
        return f(*args, **kwargs)
    return decorated


def _get_conn():
    """Connessione DB con row_factory dict."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==============================================================================
# API WIDGET - Prossimo messaggio (polling dalla topbar)
# ==============================================================================

@ticker_bp.route('/api/prossimo')
@_richiedi_login
def api_prossimo():
    """
    Restituisce il prossimo messaggio da mostrare nel ticker.
    Il frontend chiama questa API a intervalli variabili.
    """
    try:
        conn = _get_conn()
        
        # Scadenza automatica messaggi vecchi
        scadenza_messaggi(conn)
        
        user_id = session['user_id']
        ruolo = session.get('ruolo_base', 'operatore')
        
        msg = get_prossimo_messaggio(conn, user_id, ruolo)
        prossimo_sec = calcola_prossimo_check(conn)
        
        if msg:
            # Font config
            from app.config_ticker import get_config
            font_size = get_config(conn, 'font_size', '0.88rem')
            font_family = get_config(conn, 'font_family', 'inherit')

            result = {
                'success': True,
                'messaggio': {
                    'id': msg['id'],
                    'testo': msg['testo'],
                    'icona': msg.get('icona', ''),
                    'colore_testo': msg.get('colore_testo', '#000000'),
                    'animazione': msg.get('animazione', 'scroll-rtl'),
                    'durata_secondi': msg.get('durata_secondi', 8),
                    'velocita': msg.get('velocita', 'normale'),
                },
                'prossimo_check_sec': prossimo_sec,
                'font_size': font_size,
                'font_family': font_family
            }
        else:
            # Font config
            from app.config_ticker import get_config
            font_size = get_config(conn, 'font_size', '0.88rem')
            font_family = get_config(conn, 'font_family', 'inherit')

            result = {
                'success': True,
                'messaggio': None,
                'prossimo_check_sec': prossimo_sec,
                'font_size': font_size,
                'font_family': font_family
            }
        
        conn.close()
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/visto/<int:msg_id>', methods=['POST'])
@_richiedi_login
def api_visto(msg_id):
    """Registra che il messaggio e' stato mostrato all'utente."""
    try:
        conn = _get_conn()
        registra_visualizzazione(conn, msg_id, session['user_id'])
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


# ==============================================================================
# API GESTIONE - CRUD messaggi
# ==============================================================================

@ticker_bp.route('/api/lista')
@_richiedi_login
def api_lista():
    """Lista messaggi con filtri."""
    try:
        conn = _get_conn()
        
        filtri = {}
        if request.args.get('stato'):
            filtri['stato'] = request.args['stato']
        if request.args.get('tipo'):
            filtri['tipo'] = request.args['tipo']
        if request.args.get('destinatari'):
            filtri['destinatari'] = request.args['destinatari']
        if request.args.get('cerca'):
            filtri['cerca'] = request.args['cerca']
        
        # Non-admin vedono solo i propri messaggi + approvati
        if session.get('ruolo_base') != 'admin':
            if not filtri.get('stato'):
                # Mostra propri + tutti gli approvati
                pass  # Il filtro verra' applicato nel template
            filtri['creato_da'] = session['user_id']
        
        limite = int(request.args.get('limite', 50))
        offset = int(request.args.get('offset', 0))
        
        messaggi, totale = lista_messaggi(conn, filtri, limite, offset)
        conn.close()
        
        return jsonify({
            'success': True,
            'messaggi': messaggi,
            'totale': totale,
            'limite': limite,
            'offset': offset
        })
    
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/<int:msg_id>')
@_richiedi_login
def api_dettaglio(msg_id):
    """Dettaglio singolo messaggio."""
    try:
        conn = _get_conn()
        msg = get_messaggio(conn, msg_id)
        conn.close()
        
        if not msg:
            return jsonify({'success': False, 'errore': 'Messaggio non trovato'}), 404
        
        return jsonify({'success': True, 'messaggio': msg})
    
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/crea', methods=['POST'])
@_richiedi_login
def api_crea():
    """Crea un nuovo messaggio ticker."""
    try:
        dati = request.get_json() or request.form.to_dict()
        
        if not dati.get('testo'):
            return jsonify({'success': False, 'errore': 'Testo obbligatorio'}), 400
        
        if not dati.get('data_inizio'):
            return jsonify({'success': False, 'errore': 'Data inizio obbligatoria'}), 400
        
        conn = _get_conn()
        is_admin = session.get('ruolo_base') == 'admin'
        msg_id = crea_messaggio(conn, dati, session['user_id'], is_admin)
        conn.close()
        
        if msg_id:
            return jsonify({
                'success': True,
                'id': msg_id,
                'stato': 'approvato' if is_admin else 'bozza'
            })
        else:
            return jsonify({'success': False, 'errore': 'Errore creazione'}), 500
    
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/<int:msg_id>/modifica', methods=['POST'])
@_richiedi_login
def api_modifica(msg_id):
    """Modifica un messaggio esistente."""
    try:
        dati = request.get_json() or request.form.to_dict()
        
        conn = _get_conn()
        
        # Verifica permessi: solo creatore o admin
        msg = get_messaggio(conn, msg_id)
        if not msg:
            conn.close()
            return jsonify({'success': False, 'errore': 'Messaggio non trovato'}), 404
        
        is_admin = session.get('ruolo_base') == 'admin'
        if msg['creato_da'] != session['user_id'] and not is_admin:
            conn.close()
            return jsonify({'success': False, 'errore': 'Non autorizzato'}), 403
        
        ok = modifica_messaggio(conn, msg_id, dati, session['user_id'])
        conn.close()
        
        return jsonify({'success': ok})
    
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/<int:msg_id>/elimina', methods=['POST'])
@_richiedi_login
def api_elimina(msg_id):
    """Elimina un messaggio."""
    try:
        conn = _get_conn()
        
        # Verifica permessi
        msg = get_messaggio(conn, msg_id)
        if not msg:
            conn.close()
            return jsonify({'success': False, 'errore': 'Messaggio non trovato'}), 404
        
        is_admin = session.get('ruolo_base') == 'admin'
        if msg['creato_da'] != session['user_id'] and not is_admin:
            conn.close()
            return jsonify({'success': False, 'errore': 'Non autorizzato'}), 403
        
        ok = elimina_messaggio(conn, msg_id)
        conn.close()
        
        return jsonify({'success': ok})
    
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


# ==============================================================================
# API APPROVAZIONE (solo admin)
# ==============================================================================

@ticker_bp.route('/api/<int:msg_id>/approva', methods=['POST'])
@_richiedi_admin
def api_approva(msg_id):
    """Approva un messaggio in attesa."""
    try:
        conn = _get_conn()
        ok = approva_messaggio(conn, msg_id, session['user_id'])
        conn.close()
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/<int:msg_id>/rifiuta', methods=['POST'])
@_richiedi_admin
def api_rifiuta(msg_id):
    """Rifiuta un messaggio con nota opzionale."""
    try:
        dati = request.get_json() or request.form.to_dict()
        nota = dati.get('nota', '')
        
        conn = _get_conn()
        ok = rifiuta_messaggio(conn, msg_id, session['user_id'], nota)
        conn.close()
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/<int:msg_id>/invia', methods=['POST'])
@_richiedi_login
def api_invia(msg_id):
    """Invia messaggio per approvazione (da bozza a in_attesa)."""
    try:
        conn = _get_conn()
        ok = invia_per_approvazione(conn, msg_id, session['user_id'])
        conn.close()
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


# ==============================================================================
# API CONFIGURAZIONE (solo admin)
# ==============================================================================

@ticker_bp.route('/api/config')
@_richiedi_admin
def api_get_config():
    """Leggi tutta la configurazione ticker."""
    try:
        conn = _get_conn()
        config = get_all_config(conn)
        conn.close()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


@ticker_bp.route('/api/config', methods=['POST'])
@_richiedi_admin
def api_set_config():
    """Salva parametri di configurazione."""
    try:
        dati = request.get_json() or request.form.to_dict()
        
        conn = _get_conn()
        aggiornati = 0
        for chiave, valore in dati.items():
            if set_config(conn, chiave, valore):
                aggiornati += 1
        conn.close()
        
        return jsonify({'success': True, 'aggiornati': aggiornati})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


# ==============================================================================
# API STATISTICHE (solo admin)
# ==============================================================================

@ticker_bp.route('/api/statistiche')
@_richiedi_admin
def api_statistiche():
    """Statistiche sistema ticker."""
    try:
        conn = _get_conn()
        stats = get_statistiche(conn)
        conn.close()
        return jsonify({'success': True, 'statistiche': stats})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500


# ==============================================================================
# PAGINA GESTIONE
# ==============================================================================

@ticker_bp.route('/gestione')
@_richiedi_login
def pagina_gestione():
    """Pagina principale gestione messaggi ticker."""
    conn = _get_conn()
    
    is_admin = session.get('ruolo_base') == 'admin'
    config = get_all_config(conn) if is_admin else {}
    
    # Conteggio in attesa (per badge admin)
    in_attesa = 0
    if is_admin:
        stats = get_statistiche(conn)
        in_attesa = stats.get('in_attesa', 0)
    
    conn.close()
    
    return render_template(
        'ticker/gestione.html',
        is_admin=is_admin,
        config=config,
        in_attesa=in_attesa,
        animazioni=ANIMAZIONI,
        velocita=VELOCITA,
        stati=STATI_MESSAGGIO,
        tipi=TIPI_MESSAGGIO,
        ricorrenze=RICORRENZE,
        destinatari_predefiniti=DESTINATARI_PREDEFINITI,
        giorni_settimana=GIORNI_SETTIMANA,
    )


# ==============================================================================
# REGISTRAZIONE BLUEPRINT
# ==============================================================================

def register_ticker_routes(app):
    """Registra il blueprint nell'app Flask."""
    app.register_blueprint(ticker_bp)

# ============================================================
# API FESTIVITA
# ============================================================

@ticker_bp.route('/api/festivita', methods=['GET'])
def api_festivita_lista():
    """Lista tutte le festivita"""
    try:
        conn = get_db()
        cur = conn.execute('SELECT id, nome, giorno, mese, tipo, attiva FROM ticker_festivita ORDER BY mese, giorno')
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({'success': True, 'festivita': rows})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500

@ticker_bp.route('/api/festivita', methods=['POST'])
def api_festivita_aggiungi():
    """Aggiungi festivita personalizzata"""
    if session.get('ruolo_base') != 'admin':
        return jsonify({'success': False, 'errore': 'Non autorizzato'}), 403
    try:
        data = request.get_json()
        nome = data.get('nome', '').strip()
        giorno = int(data.get('giorno', 0))
        mese = int(data.get('mese', 0))
        if not nome or giorno < 1 or giorno > 31 or mese < 1 or mese > 12:
            return jsonify({'success': False, 'errore': 'Dati non validi'}), 400
        conn = get_db()
        conn.execute('INSERT INTO ticker_festivita (nome, giorno, mese, tipo, attiva) VALUES (?, ?, ?, ?, 1)',
                     (nome, giorno, mese, 'personalizzata'))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500

@ticker_bp.route('/api/festivita/<int:fid>', methods=['DELETE'])
def api_festivita_elimina(fid):
    """Elimina festivita personalizzata"""
    if session.get('ruolo_base') != 'admin':
        return jsonify({'success': False, 'errore': 'Non autorizzato'}), 403
    try:
        conn = get_db()
        conn.execute('DELETE FROM ticker_festivita WHERE id = ? AND tipo = ?', (fid, 'personalizzata'))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500

@ticker_bp.route('/api/festivita/<int:fid>/toggle', methods=['POST'])
def api_festivita_toggle(fid):
    """Attiva/disattiva festivita"""
    if session.get('ruolo_base') != 'admin':
        return jsonify({'success': False, 'errore': 'Non autorizzato'}), 403
    try:
        conn = get_db()
        conn.execute('UPDATE ticker_festivita SET attiva = CASE WHEN attiva = 1 THEN 0 ELSE 1 END WHERE id = ?', (fid,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'errore': str(e)}), 500
