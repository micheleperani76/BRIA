# =============================================================================
# STOCK ENGINE - API Export
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Endpoint API per export/download file Excel.
# =============================================================================

from pathlib import Path
from datetime import date, datetime
from flask import request, jsonify, send_file, current_app

from . import api_bp
from app.services.exporter import ExcelExporter


@api_bp.route('/export/excel/<noleggiatore>', methods=['GET'])
def download_excel(noleggiatore):
    """
    GET /api/export/excel/ayvens
    
    Scarica file Excel per un noleggiatore.
    
    Query params:
    - data: Data specifica (YYYY-MM-DD, default oggi)
    - regenerate: Se true, rigenera file anche se esiste
    
    Returns:
        File Excel in download
    """
    data_str = request.args.get('data')
    regenerate = request.args.get('regenerate', 'false').lower() == 'true'
    
    if data_str:
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato data non valido. Usa YYYY-MM-DD'}), 400
    else:
        data = date.today()
    
    # Percorso file atteso
    output_dir = Path(current_app.config['DIR_OUTPUT'])
    filename = f"{noleggiatore.lower()}_stock_{data.strftime('%d-%m-%Y')}.xlsx"
    filepath = output_dir / filename
    
    # Se file esiste e non richiesta rigenerazione, servi file esistente
    if filepath.exists() and not regenerate:
        return send_file(
            filepath,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    # Genera file
    try:
        exporter = ExcelExporter()
        filepath = exporter.genera_excel(noleggiatore.upper(), data)
        
        return send_file(
            filepath,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filepath.name
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Errore generazione Excel: {str(e)}'}), 500


@api_bp.route('/export/list', methods=['GET'])
def list_exports():
    """
    GET /api/export/list
    
    Lista file Excel disponibili.
    
    Query params:
    - noleggiatore: Filtro noleggiatore
    """
    noleggiatore = request.args.get('noleggiatore', '').lower()
    
    output_dir = Path(current_app.config['DIR_OUTPUT'])
    
    if not output_dir.exists():
        return jsonify({'files': []})
    
    files = []
    pattern = f"{noleggiatore}*.xlsx" if noleggiatore else "*.xlsx"
    
    for f in output_dir.glob(pattern):
        stat = f.stat()
        files.append({
            'filename': f.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'download_url': f'/api/export/download/{f.name}'
        })
    
    # Ordina per data modifica (più recenti prima)
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return jsonify({
        'count': len(files),
        'files': files
    })


@api_bp.route('/export/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    GET /api/export/download/ayvens_stock_28-01-2026.xlsx
    
    Download diretto file per nome.
    """
    output_dir = Path(current_app.config['DIR_OUTPUT'])
    filepath = output_dir / filename
    
    if not filepath.exists():
        return jsonify({'error': 'File non trovato'}), 404
    
    # Security: verifica che il file sia nella directory output
    try:
        filepath.resolve().relative_to(output_dir.resolve())
    except ValueError:
        return jsonify({'error': 'Accesso non consentito'}), 403
    
    return send_file(
        filepath,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
