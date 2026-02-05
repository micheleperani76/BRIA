# =============================================================================
# STOCK ENGINE - API Stock
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Endpoint API per accesso ai dati stock veicoli.
# Usato dal programma principale per attingere ai dati elaborati.
# =============================================================================

from datetime import date, datetime
from flask import request, jsonify, current_app

from . import api_bp
from app.models.veicolo import Veicolo
from app.models.jato import JatoModel


@api_bp.route('/stock', methods=['GET'])
def get_all_stock():
    """
    GET /api/stock
    
    Restituisce tutti i veicoli dell'ultimo giorno disponibile.
    
    Query params:
    - noleggiatore: Filtro noleggiatore
    - data: Data specifica (YYYY-MM-DD)
    - page: Pagina (default 1)
    - per_page: Elementi per pagina (default 100)
    """
    noleggiatore = request.args.get('noleggiatore')
    data_str = request.args.get('data')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 100, type=int), 
                   current_app.config.get('API_MAX_PAGE_SIZE', 1000))
    
    query = Veicolo.query
    
    if noleggiatore:
        query = query.filter_by(noleggiatore=noleggiatore.upper())
    
    if data_str:
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
            query = query.filter_by(data_import=data)
        except ValueError:
            return jsonify({'error': 'Formato data non valido. Usa YYYY-MM-DD'}), 400
    else:
        # Ultima data disponibile
        ultima = Veicolo.query.order_by(Veicolo.data_import.desc()).first()
        if ultima:
            query = query.filter_by(data_import=ultima.data_import)
    
    # Paginazione
    pagination = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'data': [v.to_dict() for v in pagination.items],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
        }
    })


@api_bp.route('/stock/<noleggiatore>', methods=['GET'])
def get_stock_noleggiatore(noleggiatore):
    """
    GET /api/stock/ayvens
    
    Restituisce veicoli per un noleggiatore specifico.
    
    Query params:
    - data: Data specifica (YYYY-MM-DD, default oggi)
    - include_originali: Se true, include dati originali
    """
    data_str = request.args.get('data')
    include_originali = request.args.get('include_originali', 'false').lower() == 'true'
    
    if data_str:
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato data non valido'}), 400
    else:
        data = date.today()
    
    veicoli = Veicolo.get_by_noleggiatore_data(noleggiatore.upper(), data).all()
    
    return jsonify({
        'noleggiatore': noleggiatore.upper(),
        'data': data.isoformat(),
        'count': len(veicoli),
        'veicoli': [v.to_dict(include_originali=include_originali) for v in veicoli]
    })


@api_bp.route('/stock/search', methods=['GET'])
def search_stock():
    """
    GET /api/stock/search?marca=FIAT&modello=500
    
    Ricerca veicoli con filtri multipli.
    
    Query params:
    - marca: Filtro marca (LIKE)
    - modello: Filtro modello (LIKE)
    - alimentazione: Filtro alimentazione
    - neopatentati: Filtro neopatentati (SI/NO)
    - match_status: Filtro stato match (MATCHED/PARTIAL/NO_MATCH)
    - prezzo_min: Prezzo minimo
    - prezzo_max: Prezzo massimo
    - limit: Limite risultati (default 100)
    """
    filters = {
        'marca': request.args.get('marca'),
        'modello': request.args.get('modello'),
        'alimentazione': request.args.get('alimentazione'),
        'neopatentati': request.args.get('neopatentati'),
        'match_status': request.args.get('match_status'),
    }
    
    prezzo_min = request.args.get('prezzo_min', type=float)
    prezzo_max = request.args.get('prezzo_max', type=float)
    limit = min(request.args.get('limit', 100, type=int), 1000)
    
    query = Veicolo.query
    
    # Applica filtri LIKE
    for field, value in filters.items():
        if value:
            if field in ['marca', 'modello']:
                query = query.filter(getattr(Veicolo, field).ilike(f'%{value}%'))
            else:
                query = query.filter(getattr(Veicolo, field) == value.upper())
    
    # Filtri prezzo
    if prezzo_min:
        query = query.filter(Veicolo.prezzo_totale >= prezzo_min)
    if prezzo_max:
        query = query.filter(Veicolo.prezzo_totale <= prezzo_max)
    
    veicoli = query.limit(limit).all()
    
    return jsonify({
        'count': len(veicoli),
        'veicoli': [v.to_dict() for v in veicoli]
    })


@api_bp.route('/stock/<int:id>', methods=['GET'])
def get_veicolo(id):
    """
    GET /api/stock/123
    
    Restituisce dettagli singolo veicolo.
    """
    veicolo = Veicolo.query.get_or_404(id)
    return jsonify(veicolo.to_dict(include_originali=True))


@api_bp.route('/stock/statistics', methods=['GET'])
def get_statistics():
    """
    GET /api/stock/statistics
    
    Restituisce statistiche stock.
    
    Query params:
    - noleggiatore: Filtro noleggiatore
    - data: Data specifica
    """
    noleggiatore = request.args.get('noleggiatore')
    data_str = request.args.get('data')
    
    data = None
    if data_str:
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    stats = Veicolo.get_statistics(noleggiatore, data)
    
    return jsonify(stats)


@api_bp.route('/jato/search', methods=['GET'])
def search_jato():
    """
    GET /api/jato/search?marca=FIAT&modello=500
    
    Ricerca nel database JATO.
    """
    marca = request.args.get('marca', '')
    modello = request.args.get('modello', '')
    limit = min(request.args.get('limit', 50, type=int), 200)
    
    if not marca:
        return jsonify({'error': 'Parametro marca obbligatorio'}), 400
    
    query = JatoModel.query.filter(
        JatoModel.brand_normalized.ilike(f'%{marca.upper()}%')
    )
    
    if modello:
        query = query.filter(
            JatoModel.jato_product_description.ilike(f'%{modello}%')
        )
    
    risultati = query.limit(limit).all()
    
    return jsonify({
        'count': len(risultati),
        'modelli': [r.to_dict() for r in risultati]
    })
