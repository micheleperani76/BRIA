# ==============================================================================
# ROUTES_LAYOUT.PY - API Gestione Layout Pagine
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-10
# Descrizione: Blueprint per gestione layout pagina dettaglio cliente.
#              Salvataggio multiplo su file JSON, attivazione, duplicazione,
#              eliminazione layout.
#
# ROUTE:
#   GET  /admin/layout-editor          Pagina editor visuale (solo admin)
#   GET  /api/layout/lista             Lista layout salvati
#   GET  /api/layout/<nome>            Carica un layout specifico
#   GET  /api/layout/attivo            Carica il layout attivo
#   POST /api/layout/salva             Salva nuovo layout
#   POST /api/layout/attiva/<nome>     Imposta layout attivo
#   POST /api/layout/duplica           Duplica un layout
#   POST /api/layout/elimina/<nome>    Elimina un layout
#   GET  /api/layout/catalogo          Catalogo quadri disponibili
# ==============================================================================

from flask import Blueprint, request, jsonify, render_template, session
from app.auth import login_required, admin_required
from app.layout_config import (
    CATALOGO_QUADRI,
    DEFAULT_LAYOUT,
    init_layout,
    get_layout_attivo,
    get_layout_attivo_nome,
    set_layout_attivo,
    carica_layout,
    salva_layout,
    lista_layout,
    elimina_layout,
    duplica_layout,
)

layout_bp = Blueprint('layout', __name__)


# ==============================================================================
# PAGINA EDITOR (admin)
# ==============================================================================

@layout_bp.route('/admin/layout-editor')
@login_required
@admin_required
def pagina_editor():
    """Pagina editor visuale layout."""
    layouts = lista_layout()
    attivo_nome = get_layout_attivo_nome()
    attivo = get_layout_attivo()

    return render_template('admin/layout_editor.html',
                           layouts=layouts,
                           layout_attivo=attivo,
                           layout_attivo_nome=attivo_nome,
                           catalogo=CATALOGO_QUADRI)


# ==============================================================================
# API: Lista layout
# ==============================================================================

@layout_bp.route('/api/layout/lista')
@login_required
def api_lista_layout():
    """Restituisce la lista di tutti i layout salvati."""
    return jsonify({
        'success': True,
        'layouts': lista_layout(),
        'attivo': get_layout_attivo_nome()
    })


# ==============================================================================
# API: Carica layout attivo
# ==============================================================================

@layout_bp.route('/api/layout/attivo')
@login_required
def api_layout_attivo():
    """Restituisce il layout attualmente attivo."""
    layout = get_layout_attivo()
    return jsonify({
        'success': True,
        'layout': layout,
        'filename': get_layout_attivo_nome()
    })


# ==============================================================================
# API: Carica layout specifico
# ==============================================================================

@layout_bp.route('/api/layout/<nome>')
@login_required
def api_carica_layout(nome):
    """Carica un layout specifico per nome file."""
    layout = carica_layout(nome)
    if layout is None:
        return jsonify({'success': False, 'error': 'Layout non trovato'}), 404

    return jsonify({
        'success': True,
        'layout': layout,
        'filename': nome,
        'attivo': nome == get_layout_attivo_nome()
    })


# ==============================================================================
# API: Salva layout
# ==============================================================================

@layout_bp.route('/api/layout/salva', methods=['POST'])
@login_required
@admin_required
def api_salva_layout():
    """
    Salva un layout (nuovo o sovrascrittura).
    
    JSON body:
    {
        "nome": "Layout Compatto",
        "descrizione": "Descrizione opzionale",
        "quadri": [{id, x, y, w, h, visible, min_w, min_h}, ...]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400

    nome = data.get('nome', '').strip()
    if not nome:
        return jsonify({'success': False, 'error': 'Nome layout obbligatorio'}), 400

    quadri = data.get('quadri', [])
    if not quadri:
        return jsonify({'success': False, 'error': 'Lista quadri vuota'}), 400

    # Nome utente da sessione
    utente_nome = session.get('nome_display', session.get('username', 'Admin'))

    risultato = salva_layout(
        nome_display=nome,
        descrizione=data.get('descrizione', ''),
        quadri=quadri,
        utente_nome=utente_nome
    )

    if risultato['success']:
        return jsonify(risultato)
    else:
        return jsonify(risultato), 400


# ==============================================================================
# API: Attiva layout
# ==============================================================================

@layout_bp.route('/api/layout/attiva/<nome>', methods=['POST'])
@login_required
@admin_required
def api_attiva_layout(nome):
    """Imposta un layout come attivo."""
    if set_layout_attivo(nome):
        return jsonify({
            'success': True,
            'message': f'Layout "{nome}" attivato',
            'attivo': nome
        })
    else:
        return jsonify({
            'success': False,
            'error': f'Layout "{nome}" non trovato'
        }), 404


# ==============================================================================
# API: Duplica layout
# ==============================================================================

@layout_bp.route('/api/layout/duplica', methods=['POST'])
@login_required
@admin_required
def api_duplica_layout():
    """
    Duplica un layout esistente.
    
    JSON body:
    {
        "sorgente": "default",
        "nuovo_nome": "Copia Layout Originale"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400

    sorgente = data.get('sorgente', '').strip()
    nuovo_nome = data.get('nuovo_nome', '').strip()

    if not sorgente or not nuovo_nome:
        return jsonify({'success': False, 'error': 'Sorgente e nuovo nome obbligatori'}), 400

    utente_nome = session.get('nome_display', session.get('username', 'Admin'))

    risultato = duplica_layout(sorgente, nuovo_nome, utente_nome)

    if risultato['success']:
        return jsonify(risultato)
    else:
        return jsonify(risultato), 400


# ==============================================================================
# API: Elimina layout
# ==============================================================================

@layout_bp.route('/api/layout/elimina/<nome>', methods=['POST'])
@login_required
@admin_required
def api_elimina_layout(nome):
    """Elimina un layout salvato."""
    risultato = elimina_layout(nome)

    if risultato['success']:
        return jsonify(risultato)
    else:
        return jsonify(risultato), 400


# ==============================================================================
# API: Catalogo quadri
# ==============================================================================

@layout_bp.route('/api/layout/catalogo')
@login_required
def api_catalogo_quadri():
    """Restituisce il catalogo di tutti i quadri disponibili."""
    return jsonify({
        'success': True,
        'catalogo': CATALOGO_QUADRI
    })
