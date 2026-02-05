# -*- coding: utf-8 -*-
"""
==============================================================================
ROUTES NOTIFICHE - Blueprint Flask
==============================================================================
Versione: 1.0.0
Data: 2026-02-04
Descrizione: API HTTP per il sistema notifiche (campanella, dropdown, azioni)

Route disponibili:
    GET  /notifiche/api/contatore        - Conteggio non lette (polling campanella)
    GET  /notifiche/api/recenti          - Notifiche recenti per dropdown
    POST /notifiche/api/<id>/letta       - Segna una notifica come letta
    POST /notifiche/api/tutte-lette      - Segna tutte come lette
    POST /notifiche/api/<id>/archivia    - Archivia una notifica
    POST /notifiche/api/test             - Genera notifica di test (admin)
==============================================================================
"""

from flask import Blueprint, request, jsonify, session
import sqlite3
from functools import wraps

from app.config import DB_FILE
from app.motore_notifiche import (
    get_contatore_non_lette,
    get_notifiche_utente,
    segna_letta,
    segna_tutte_lette,
    archivia_notifica,
    get_statistiche_notifiche,
    _dict_factory
)
from app.config_notifiche import NOTIFICHE_ATTIVO


# ==============================================================================
# BLUEPRINT
# ==============================================================================

notifiche_bp = Blueprint('notifiche', __name__, url_prefix='/notifiche')


# ==============================================================================
# DECORATORI
# ==============================================================================

def _richiedi_login(f):
    """Verifica che l'utente sia autenticato (versione leggera per API)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'errore': 'Non autenticato'}), 401
        return f(*args, **kwargs)
    return decorated


def _richiedi_admin(f):
    """Verifica ruolo admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'errore': 'Non autenticato'}), 401
        if session.get('ruolo') != 'admin':
            return jsonify({'errore': 'Accesso negato'}), 403
        return f(*args, **kwargs)
    return decorated


def _get_conn():
    """Connessione DB con row_factory dict"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==============================================================================
# API - CONTATORE (polling campanella)
# ==============================================================================

@notifiche_bp.route('/api/contatore')
@_richiedi_login
def api_contatore():
    """
    Restituisce il conteggio notifiche non lette.
    Chiamata ogni N secondi dal JavaScript della campanella.
    
    Returns:
        JSON: {"contatore": 5}
    """
    if not NOTIFICHE_ATTIVO:
        return jsonify({'contatore': 0})
    
    conn = _get_conn()
    try:
        contatore = get_contatore_non_lette(conn, session['user_id'])
        return jsonify({'contatore': contatore})
    finally:
        conn.close()


# ==============================================================================
# API - NOTIFICHE RECENTI (dropdown)
# ==============================================================================

@notifiche_bp.route('/api/recenti')
@_richiedi_login
def api_recenti():
    """
    Restituisce le notifiche recenti per il dropdown della campanella.
    
    Query params:
        solo_non_lette: 1/0 (default 0)
        limite: numero max (default da config)
        categoria: filtro categoria
    
    Returns:
        JSON: {"notifiche": [...], "contatore": N}
    """
    if not NOTIFICHE_ATTIVO:
        return jsonify({'notifiche': [], 'contatore': 0})
    
    solo_non_lette = request.args.get('solo_non_lette', '0') == '1'
    limite = request.args.get('limite', None, type=int)
    categoria = request.args.get('categoria', None)
    
    conn = _get_conn()
    try:
        notifiche = get_notifiche_utente(
            conn, session['user_id'],
            solo_non_lette=solo_non_lette,
            limite=limite,
            categoria=categoria
        )
        contatore = get_contatore_non_lette(conn, session['user_id'])
        
        return jsonify({
            'notifiche': notifiche,
            'contatore': contatore
        })
    finally:
        conn.close()


# ==============================================================================
# API - SEGNA LETTA
# ==============================================================================

@notifiche_bp.route('/api/<int:notifica_id>/letta', methods=['POST'])
@_richiedi_login
def api_segna_letta(notifica_id):
    """
    Segna una notifica specifica come letta.
    
    Returns:
        JSON: {"ok": true, "contatore": N}
    """
    conn = _get_conn()
    try:
        segna_letta(conn, session['user_id'], notifica_id)
        contatore = get_contatore_non_lette(conn, session['user_id'])
        return jsonify({'ok': True, 'contatore': contatore})
    finally:
        conn.close()


# ==============================================================================
# API - SEGNA TUTTE LETTE
# ==============================================================================

@notifiche_bp.route('/api/tutte-lette', methods=['POST'])
@_richiedi_login
def api_tutte_lette():
    """
    Segna tutte le notifiche come lette.
    
    Body (opzionale):
        {"categoria": "TASK"}  per filtrare
    
    Returns:
        JSON: {"ok": true, "aggiornate": N, "contatore": 0}
    """
    data = request.get_json(silent=True) or {}
    categoria = data.get('categoria')
    
    conn = _get_conn()
    try:
        aggiornate = segna_tutte_lette(conn, session['user_id'], categoria)
        contatore = get_contatore_non_lette(conn, session['user_id'])
        return jsonify({'ok': True, 'aggiornate': aggiornate, 'contatore': contatore})
    finally:
        conn.close()


# ==============================================================================
# API - ARCHIVIA
# ==============================================================================

@notifiche_bp.route('/api/<int:notifica_id>/archivia', methods=['POST'])
@_richiedi_login
def api_archivia(notifica_id):
    """
    Archivia una notifica (sparisce dal dropdown).
    
    Returns:
        JSON: {"ok": true, "contatore": N}
    """
    conn = _get_conn()
    try:
        archivia_notifica(conn, session['user_id'], notifica_id)
        contatore = get_contatore_non_lette(conn, session['user_id'])
        return jsonify({'ok': True, 'contatore': contatore})
    finally:
        conn.close()


# ==============================================================================
# API - TEST (solo admin)
# ==============================================================================

@notifiche_bp.route('/api/test', methods=['POST'])
@_richiedi_admin
def api_test():
    """
    Genera una notifica di test per l'utente corrente.
    Solo admin.
    
    Returns:
        JSON: {"ok": true, "notifica_id": N}
    """
    from app.connettori_notifiche.sistema import notifica_test
    
    conn = _get_conn()
    try:
        risultato = notifica_test(conn, destinatario_id=session['user_id'])
        return jsonify(risultato)
    finally:
        conn.close()


# ==============================================================================
# API - STATISTICHE (solo admin)
# ==============================================================================

@notifiche_bp.route('/api/statistiche')
@_richiedi_admin
def api_statistiche():
    """
    Statistiche sistema notifiche per pannello admin.
    
    Returns:
        JSON con conteggi vari
    """
    conn = _get_conn()
    try:
        stats = get_statistiche_notifiche(conn)
        return jsonify(stats)
    finally:
        conn.close()
