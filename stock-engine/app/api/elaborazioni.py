# =============================================================================
# STOCK ENGINE - API Elaborazioni
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Endpoint API per gestione elaborazioni.
# Permette di lanciare e monitorare elaborazioni.
# =============================================================================

from flask import request, jsonify

from . import api_bp
from app.models.elaborazione import Elaborazione
from app.services.pipeline import StockPipeline


@api_bp.route('/elaborazioni', methods=['GET'])
def get_elaborazioni():
    """
    GET /api/elaborazioni
    
    Restituisce lista ultime elaborazioni.
    
    Query params:
    - noleggiatore: Filtro noleggiatore
    - limit: Limite risultati (default 20)
    """
    noleggiatore = request.args.get('noleggiatore')
    limit = min(request.args.get('limit', 20, type=int), 100)
    
    query = Elaborazione.query
    
    if noleggiatore:
        query = query.filter_by(noleggiatore=noleggiatore.upper())
    
    elaborazioni = query.order_by(
        Elaborazione.data_elaborazione.desc()
    ).limit(limit).all()
    
    return jsonify({
        'count': len(elaborazioni),
        'elaborazioni': [e.to_dict() for e in elaborazioni]
    })


@api_bp.route('/elaborazioni/<int:id>', methods=['GET'])
def get_elaborazione(id):
    """
    GET /api/elaborazioni/123
    
    Restituisce dettagli singola elaborazione.
    """
    elaborazione = Elaborazione.query.get_or_404(id)
    return jsonify(elaborazione.to_dict())


@api_bp.route('/elaborazioni/ultima/<noleggiatore>', methods=['GET'])
def get_ultima_elaborazione(noleggiatore):
    """
    GET /api/elaborazioni/ultima/ayvens
    
    Restituisce ultima elaborazione completata per un noleggiatore.
    """
    elaborazione = Elaborazione.ultima_elaborazione(noleggiatore)
    
    if not elaborazione:
        return jsonify({'error': f'Nessuna elaborazione trovata per {noleggiatore}'}), 404
    
    return jsonify(elaborazione.to_dict())


@api_bp.route('/elabora/<noleggiatore>', methods=['POST'])
def elabora(noleggiatore):
    """
    POST /api/elabora/ayvens
    
    Lancia elaborazione per un noleggiatore.
    
    ATTENZIONE: Operazione sincrona, può richiedere 30-60 secondi.
    Per elaborazioni asincrone, usare il task scheduler.
    
    Returns:
        dict: Risultato elaborazione
    """
    try:
        pipeline = StockPipeline()
        result = pipeline.elabora(noleggiatore.upper())
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Errore elaborazione: {str(e)}'}), 500


@api_bp.route('/elabora/tutti', methods=['POST'])
def elabora_tutti():
    """
    POST /api/elabora/tutti
    
    Lancia elaborazione per tutti i noleggiatori attivi.
    
    ATTENZIONE: Operazione lunga, può richiedere diversi minuti.
    """
    try:
        pipeline = StockPipeline()
        risultati = pipeline.elabora_tutti()
        return jsonify(risultati)
        
    except Exception as e:
        return jsonify({'error': f'Errore: {str(e)}'}), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /api/health
    
    Health check endpoint.
    """
    from app.models.veicolo import Veicolo
    from app.models.jato import JatoModel
    
    try:
        # Verifica connessione DB
        veicoli_count = Veicolo.query.count()
        jato_count = JatoModel.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': {
                'veicoli': veicoli_count,
                'jato_models': jato_count,
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
