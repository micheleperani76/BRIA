# ==============================================================================
# ROUTES_SEDI_CLIENTE.PY - API CRUD per Sedi Cliente
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-01-26
# Descrizione: Gestione sedi aggiuntive per i clienti (operative, filiali, ecc.)
# ==============================================================================

from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.auth import login_required
from datetime import datetime

sedi_bp = Blueprint('sedi', __name__)

# ==============================================================================
# TIPI SEDE DISPONIBILI
# ==============================================================================

TIPI_SEDE = [
    'Operativa',
    'Filiale',
    'Magazzino',
    'Deposito',
    'Ufficio',
    'Stabilimento',
    'Punto Vendita',
    'Altro'
]


def get_tipi_sede():
    """Ritorna la lista dei tipi sede disponibili."""
    return TIPI_SEDE


# ==============================================================================
# API: Lista sedi cliente
# ==============================================================================

@sedi_bp.route('/api/cliente/<int:cliente_id>/sedi', methods=['GET'])
@login_required
def api_lista_sedi(cliente_id):
    """Ritorna tutte le sedi di un cliente con dati referente."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Sedi con join referente
        cursor.execute('''
            SELECT s.*, 
                   r.id as ref_id, 
                   r.nome || ' ' || COALESCE(r.cognome, '') as ref_nome,
                   r.ruolo as ref_ruolo,
                   r.cellulare as ref_cellulare, r.telefono as ref_telefono,
                   r.email_principale as ref_email
            FROM sedi_cliente s
            LEFT JOIN referenti_clienti r ON s.referente_id = r.id
            WHERE s.cliente_id = ?
            ORDER BY s.tipo_sede, s.denominazione
        ''', (cliente_id,))
        
        sedi = [dict(row) for row in cursor.fetchall()]
        
        # Lista referenti per dropdown (nome + cognome)
        cursor.execute('''
            SELECT id, nome || ' ' || COALESCE(cognome, '') as nome, ruolo, cellulare, telefono, email_principale as email
            FROM referenti_clienti 
            WHERE cliente_id = ?
            ORDER BY principale DESC, nome
        ''', (cliente_id,))
        
        referenti = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'sedi': sedi,
            'referenti': referenti,
            'tipi_sede': TIPI_SEDE
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# API: Aggiungi sede
# ==============================================================================

@sedi_bp.route('/api/cliente/<int:cliente_id>/sedi', methods=['POST'])
@login_required
def api_aggiungi_sede(cliente_id):
    """Aggiunge una nuova sede al cliente."""
    data = request.get_json()
    
    tipo_sede = data.get('tipo_sede', 'Operativa')
    denominazione = data.get('denominazione', '').strip()
    indirizzo = data.get('indirizzo', '').strip()
    cap = data.get('cap', '').strip()
    citta = data.get('citta', '').strip().upper()
    provincia = data.get('provincia', '').strip().upper()
    telefono = data.get('telefono', '').strip()
    email = data.get('email', '').strip()
    note = data.get('note', '').strip()
    referente_id = data.get('referente_id')
    
    if referente_id == '' or referente_id == 'null':
        referente_id = None
    elif referente_id:
        referente_id = int(referente_id)
    
    if not indirizzo and not citta:
        return jsonify({'success': False, 'error': 'Indirizzo o citta obbligatorio'})
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO sedi_cliente 
            (cliente_id, tipo_sede, denominazione, indirizzo, cap, citta, provincia, telefono, email, note, referente_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, tipo_sede, denominazione or None, indirizzo or None, 
              cap or None, citta or None, provincia or None, 
              telefono or None, email or None, note or None, referente_id))
        
        sede_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': sede_id})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# API: Modifica sede
# ==============================================================================

@sedi_bp.route('/api/cliente/<int:cliente_id>/sedi/<int:sede_id>', methods=['PUT'])
@login_required
def api_modifica_sede(cliente_id, sede_id):
    """Modifica una sede esistente."""
    data = request.get_json()
    
    tipo_sede = data.get('tipo_sede', 'Operativa')
    denominazione = data.get('denominazione', '').strip()
    indirizzo = data.get('indirizzo', '').strip()
    cap = data.get('cap', '').strip()
    citta = data.get('citta', '').strip().upper()
    provincia = data.get('provincia', '').strip().upper()
    telefono = data.get('telefono', '').strip()
    email = data.get('email', '').strip()
    note = data.get('note', '').strip()
    referente_id = data.get('referente_id')
    
    if referente_id == '' or referente_id == 'null':
        referente_id = None
    elif referente_id:
        referente_id = int(referente_id)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE sedi_cliente SET
                tipo_sede = ?,
                denominazione = ?,
                indirizzo = ?,
                cap = ?,
                citta = ?,
                provincia = ?,
                telefono = ?,
                email = ?,
                note = ?,
                referente_id = ?
            WHERE id = ? AND cliente_id = ?
        ''', (tipo_sede, denominazione or None, indirizzo or None,
              cap or None, citta or None, provincia or None,
              telefono or None, email or None, note or None, referente_id,
              sede_id, cliente_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# API: Elimina sede
# ==============================================================================

@sedi_bp.route('/api/cliente/<int:cliente_id>/sedi/<int:sede_id>', methods=['DELETE'])
@login_required
def api_elimina_sede(cliente_id, sede_id):
    """Elimina una sede."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM sedi_cliente WHERE id = ? AND cliente_id = ?
        ''', (sede_id, cliente_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})
