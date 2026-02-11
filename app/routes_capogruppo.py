# ==============================================================================
# ROUTES_CAPOGRUPPO.PY - API CRUD per Capogruppo Cliente (multi-record)
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-11
# Descrizione: Gestione multi-capogruppo per i clienti
#              - Lista capogruppo per cliente
#              - Aggiungi / Modifica / Elimina
#              - Protezione singola per record
# ==============================================================================

from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.auth import login_required
from datetime import datetime

capogruppo_bp = Blueprint('capogruppo', __name__)


# ==============================================================================
# API: Lista capogruppo cliente
# ==============================================================================

@capogruppo_bp.route('/api/cliente/<int:cliente_id>/capogruppo', methods=['GET'])
@login_required
def api_lista_capogruppo(cliente_id):
    """Ritorna tutti i capogruppo di un cliente."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, nome, codice_fiscale, protetto, data_inserimento, data_modifica
            FROM capogruppo_clienti
            WHERE cliente_id = ?
            ORDER BY data_inserimento ASC
        ''', (cliente_id,))

        capogruppo = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'capogruppo': capogruppo})

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# API: Aggiungi capogruppo
# ==============================================================================

@capogruppo_bp.route('/api/cliente/<int:cliente_id>/capogruppo', methods=['POST'])
@login_required
def api_aggiungi_capogruppo(cliente_id):
    """Aggiunge un nuovo capogruppo al cliente."""
    data = request.get_json()

    nome = data.get('nome', '').strip()
    codice_fiscale = data.get('codice_fiscale', '').strip().upper()

    if not nome:
        return jsonify({'success': False, 'error': 'Nome obbligatorio'})

    conn = get_connection()
    cursor = conn.cursor()

    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO capogruppo_clienti
            (cliente_id, nome, codice_fiscale, protetto, data_inserimento, data_modifica)
            VALUES (?, ?, ?, 0, ?, ?)
        ''', (cliente_id, nome, codice_fiscale or None, now, now))

        new_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'id': new_id})

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# API: Modifica capogruppo (protetto = 1 automatico)
# ==============================================================================

@capogruppo_bp.route('/api/cliente/<int:cliente_id>/capogruppo/<int:cg_id>', methods=['PUT'])
@login_required
def api_modifica_capogruppo(cliente_id, cg_id):
    """Modifica un capogruppo esistente. Imposta protetto dal payload."""
    data = request.get_json()

    nome = data.get('nome', '').strip()
    codice_fiscale = data.get('codice_fiscale', '').strip().upper()
    protetto = 1 if data.get('protetto') else 0

    if not nome:
        return jsonify({'success': False, 'error': 'Nome obbligatorio'})

    conn = get_connection()
    cursor = conn.cursor()

    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE capogruppo_clienti SET
                nome = ?,
                codice_fiscale = ?,
                protetto = ?,
                data_modifica = ?
            WHERE id = ? AND cliente_id = ?
        ''', (nome, codice_fiscale or None, protetto, now, cg_id, cliente_id))

        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# API: Elimina capogruppo
# ==============================================================================

@capogruppo_bp.route('/api/cliente/<int:cliente_id>/capogruppo/<int:cg_id>', methods=['DELETE'])
@login_required
def api_elimina_capogruppo(cliente_id, cg_id):
    """Elimina un capogruppo."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Verifica che non sia protetto
        cursor.execute('''
            SELECT protetto FROM capogruppo_clienti
            WHERE id = ? AND cliente_id = ?
        ''', (cg_id, cliente_id))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Capogruppo non trovato'})

        if row['protetto']:
            conn.close()
            return jsonify({'success': False, 'error': 'Impossibile eliminare: record protetto da sovrascrittura. Rimuovi prima la protezione.'})

        cursor.execute('''
            DELETE FROM capogruppo_clienti WHERE id = ? AND cliente_id = ?
        ''', (cg_id, cliente_id))

        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})
