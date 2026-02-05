#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Route Export e Stampa
# ==============================================================================
# Versione: 2.0.0
# Data: 2026-01-30
# Descrizione: Route Flask per sistema export Excel/CSV/Stampa
#              - Tab Clienti: configuratore campi
#              - Tab Top Prospect: confermati con campi fissi
#              - Tab Trattative: filtri multipli
# 
# INTEGRAZIONE: Aggiungere a web_server.py:
#   from app.routes_export import register_export_routes
#   register_export_routes(app)
# ==============================================================================

from flask import render_template, request, jsonify, send_file, session
from pathlib import Path
from datetime import datetime

from .export_excel import (
    # Clienti
    CAMPI_PRINCIPALI, CAMPI_SECONDARI, TUTTI_CAMPI,
    get_dati_export, genera_excel, genera_nome_export,
    get_storico_export, pulisci_export_vecchi,
    # Top Prospect
    CAMPI_TOP_PROSPECT, CAMPI_TOP_PROSPECT_DICT,
    get_dati_top_prospect, genera_export_top_prospect,
    # Trattative
    CAMPI_TRATTATIVE, CAMPI_TRATTATIVE_DICT,
    get_dati_trattative, genera_export_trattative,
    # Generici
    genera_csv_generico
)
from .config import BASE_DIR, DB_FILE

# Import per filtri trattative
try:
    from .config_trattative import get_tipi_trattativa, get_stati_trattativa, get_noleggiatori_dropdown
except ImportError:
    def get_tipi_trattativa():
        return []
    def get_stati_trattativa():
        return []
    def get_noleggiatori_dropdown():
        return []

# Import per lista commerciali
try:
    from .gestione_commerciali import get_commerciali_tutti
    from .database_utenti import get_subordinati
except ImportError:
    def get_commerciali_tutti(conn, solo_attivi=True):
        return []
    def get_subordinati(conn, user_id):
        return [user_id]

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# REGISTRAZIONE ROUTE
# ==============================================================================

def register_export_routes(app):
    """
    Registra tutte le route per l'export Excel/CSV/Stampa.
    Chiamare questa funzione da web_server.py passando l'app Flask.
    """
    
    @app.route('/export/configuratore')
    def export_configuratore():
        """Pagina configurazione export - 3 tab."""
        import sqlite3
        
        # Pulisci export vecchi ad ogni accesso (leggero)
        pulisci_export_vecchi(EXPORTS_DIR)
        
        # Recupera dati per filtri Trattative
        tipi_trattativa = get_tipi_trattativa()
        stati_trattativa = get_stati_trattativa()
        noleggiatori = get_noleggiatori_dropdown()
        
        # Lista commerciali per filtro
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        commerciali = get_commerciali_tutti(conn, solo_attivi=True)
        
        # Verifica se utente e' admin
        user_id = session.get('user_id')
        is_admin = session.get('is_admin', False)
        
        # Se non admin, filtra commerciali visibili
        if not is_admin and user_id:
            ids_visibili = get_subordinati(conn, user_id)
            commerciali = [c for c in commerciali if c['id'] in ids_visibili]
        
        conn.close()
        
        return render_template('export_excel.html',
            # Tab Clienti
            campi_principali=CAMPI_PRINCIPALI,
            campi_secondari=CAMPI_SECONDARI,
            # Tab Top Prospect
            campi_top_prospect=CAMPI_TOP_PROSPECT,
            # Tab Trattative
            campi_trattative=CAMPI_TRATTATIVE,
            tipi_trattativa=tipi_trattativa,
            stati_trattativa=stati_trattativa,
            noleggiatori=noleggiatori,
            commerciali=commerciali,
            is_admin=is_admin
        )
    
    
    @app.route('/export/genera', methods=['POST'])
    def export_genera():
        """Genera file Excel con i campi configurati."""
        try:
            data = request.get_json()
            campi = data.get('campi', [])
            nome_file = data.get('nome_file', '')
            
            if not campi:
                return jsonify({'success': False, 'error': 'Nessun campo selezionato'})
            
            # Costruisci ordinamento
            ordinamento = []
            for campo in campi:
                if campo.get('order'):
                    ordinamento.append((campo['id'], campo['order']))
            
            # Usa nome personalizzato o genera automatico
            if nome_file:
                # Sanitizza nome file
                import re
                nome_file = re.sub(r'[^\w\-_\. ]', '', nome_file)
                if not nome_file.lower().endswith('.xlsx'):
                    nome_file += '.xlsx'
                filename = nome_file
            else:
                filename = genera_nome_export()
            
            output_path = EXPORTS_DIR / filename
            
            # Genera Excel
            genera_excel(
                db_path=DB_FILE,
                campi_selezionati=campi,
                output_path=output_path,
                ordinamento=ordinamento if ordinamento else None
            )
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': f'Export generato: {filename}'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    
    @app.route('/export/anteprima', methods=['POST'])
    def export_anteprima():
        """Genera anteprima dati per i campi selezionati."""
        try:
            data = request.get_json()
            campi = data.get('campi', [])
            limit = data.get('limit', 20)
            
            if not campi:
                return jsonify({'success': False, 'error': 'Nessun campo selezionato'})
            
            # Costruisci ordinamento
            ordinamento = []
            for campo in campi:
                if campo.get('order'):
                    ordinamento.append((campo['id'], campo['order']))
            
            # Estrai dati
            dati = get_dati_export(
                db_path=DB_FILE,
                campi_selezionati=campi,
                ordinamento=ordinamento if ordinamento else None
            )
            
            # Prepara risposta
            headers = [TUTTI_CAMPI.get(c['id'], {}).get('label', c['id']) for c in campi]
            rows = []
            
            for record in dati[:limit]:
                row = []
                for campo in campi:
                    valore = record.get(campo['id'])
                    campo_info = TUTTI_CAMPI.get(campo['id'], {})
                    
                    # Formatta per visualizzazione
                    if valore is None:
                        row.append('')
                    elif campo_info.get('tipo') == 'euro':
                        row.append(f"&euro; {valore:,.2f}" if valore else '&euro; 0')
                    elif campo_info.get('tipo') == 'number':
                        row.append(f"{int(valore):,}" if valore else '0')
                    else:
                        row.append(str(valore))
                
                rows.append(row)
            
            return jsonify({
                'success': True,
                'headers': headers,
                'rows': rows,
                'total': len(dati)
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    
    @app.route('/export/storico')
    def export_storico():
        """Lista export salvati nello storico."""
        files = get_storico_export(EXPORTS_DIR)
        return jsonify({'files': files})
    
    
    @app.route('/export/download/<filename>')
    def export_download(filename):
        """Download file export."""
        file_path = EXPORTS_DIR / filename
        
        if not file_path.exists():
            return "File non trovato", 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    
    # Aggiorna anche la vecchia route /export/excel per reindirizzare
    @app.route('/export/excel')
    def export_excel_redirect():
        """Reindirizza alla nuova pagina configuratore."""
        from flask import redirect
        return redirect('/export/configuratore')
    
    
    # ==========================================================================
    # ROUTE TOP PROSPECT
    # ==========================================================================
    
    @app.route('/export/top-prospect/anteprima', methods=['POST'])
    def export_top_prospect_anteprima():
        """Anteprima dati Top Prospect confermati."""
        try:
            user_id = session.get('user_id')
            is_admin = session.get('is_admin', False)
            
            # Se admin, vede tutto
            if is_admin:
                user_id = None
            
            dati = get_dati_top_prospect(DB_FILE, user_id)
            
            # Prepara risposta
            headers = [c['label'] for c in CAMPI_TOP_PROSPECT]
            rows = []
            
            limit = request.get_json().get('limit', 20) if request.is_json else 20
            
            for record in dati[:limit]:
                row = [record.get(c['id'], '') for c in CAMPI_TOP_PROSPECT]
                rows.append(row)
            
            return jsonify({
                'success': True,
                'headers': headers,
                'rows': rows,
                'total': len(dati)
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    
    @app.route('/export/top-prospect/genera', methods=['POST'])
    def export_top_prospect_genera():
        """Genera export Top Prospect confermati."""
        try:
            data = request.get_json()
            nome_file = data.get('nome_file', '')
            formato = data.get('formato', 'xlsx')
            
            user_id = session.get('user_id')
            is_admin = session.get('is_admin', False)
            
            # Se admin, vede tutto
            if is_admin:
                user_id = None
            
            # Genera nome file
            if nome_file:
                import re
                nome_file = re.sub(r'[^\w\-_\. ]', '', nome_file)
                if not nome_file.lower().endswith(f'.{formato}'):
                    nome_file += f'.{formato}'
                filename = nome_file
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"top_prospect_{timestamp}.{formato}"
            
            output_path = EXPORTS_DIR / filename
            
            # Genera export
            genera_export_top_prospect(
                db_path=DB_FILE,
                output_path=output_path,
                user_id=user_id,
                formato=formato
            )
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': f'Export generato: {filename}'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    
    # ==========================================================================
    # ROUTE TRATTATIVE
    # ==========================================================================
    
    @app.route('/export/trattative/anteprima', methods=['POST'])
    def export_trattative_anteprima():
        """Anteprima dati Trattative con filtri."""
        try:
            data = request.get_json() or {}
            
            user_id = session.get('user_id')
            is_admin = session.get('is_admin', False)
            
            # Costruisci filtri
            filtri = {}
            
            if data.get('tipo_trattativa'):
                filtri['tipo_trattativa'] = data['tipo_trattativa']
            
            if data.get('stato'):
                filtri['stato'] = data['stato']
            
            if data.get('noleggiatore'):
                filtri['noleggiatore'] = data['noleggiatore']
            
            if data.get('commerciale_id'):
                filtri['commerciale_id'] = int(data['commerciale_id'])
            
            if data.get('data_da'):
                filtri['data_da'] = data['data_da']
            
            if data.get('data_a'):
                filtri['data_a'] = data['data_a']
            
            if data.get('solo_aperte'):
                filtri['solo_aperte'] = True
            
            if data.get('solo_chiuse'):
                filtri['solo_chiuse'] = True
            
            # Se admin, vede tutto (a meno che non filtri per commerciale specifico)
            if is_admin and not filtri.get('commerciale_id'):
                user_id = None
            
            dati = get_dati_trattative(DB_FILE, user_id, filtri)
            
            # Prepara risposta
            headers = [c['label'] for c in CAMPI_TRATTATIVE]
            rows = []
            
            limit = data.get('limit', 20)
            
            for record in dati[:limit]:
                row = []
                for c in CAMPI_TRATTATIVE:
                    valore = record.get(c['id'], '')
                    # Formatta per visualizzazione
                    if c['tipo'] == 'euro' and valore:
                        row.append(f"&euro; {valore:,.2f}")
                    else:
                        row.append(valore)
                rows.append(row)
            
            return jsonify({
                'success': True,
                'headers': headers,
                'rows': rows,
                'total': len(dati)
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    
    @app.route('/export/trattative/genera', methods=['POST'])
    def export_trattative_genera():
        """Genera export Trattative con filtri."""
        try:
            data = request.get_json()
            nome_file = data.get('nome_file', '')
            formato = data.get('formato', 'xlsx')
            
            user_id = session.get('user_id')
            is_admin = session.get('is_admin', False)
            
            # Costruisci filtri
            filtri = {}
            
            if data.get('tipo_trattativa'):
                filtri['tipo_trattativa'] = data['tipo_trattativa']
            
            if data.get('stato'):
                filtri['stato'] = data['stato']
            
            if data.get('noleggiatore'):
                filtri['noleggiatore'] = data['noleggiatore']
            
            if data.get('commerciale_id'):
                filtri['commerciale_id'] = int(data['commerciale_id'])
            
            if data.get('data_da'):
                filtri['data_da'] = data['data_da']
            
            if data.get('data_a'):
                filtri['data_a'] = data['data_a']
            
            if data.get('solo_aperte'):
                filtri['solo_aperte'] = True
            
            if data.get('solo_chiuse'):
                filtri['solo_chiuse'] = True
            
            # Se admin, vede tutto (a meno che non filtri per commerciale specifico)
            if is_admin and not filtri.get('commerciale_id'):
                user_id = None
            
            # Genera nome file
            if nome_file:
                import re
                nome_file = re.sub(r'[^\w\-_\. ]', '', nome_file)
                if not nome_file.lower().endswith(f'.{formato}'):
                    nome_file += f'.{formato}'
                filename = nome_file
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"trattative_{timestamp}.{formato}"
            
            output_path = EXPORTS_DIR / filename
            
            # Genera export
            genera_export_trattative(
                db_path=DB_FILE,
                output_path=output_path,
                user_id=user_id,
                filtri=filtri,
                formato=formato
            )
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': f'Export generato: {filename}'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    
    @app.route('/export/download-csv/<filename>')
    def export_download_csv(filename):
        """Download file CSV."""
        file_path = EXPORTS_DIR / filename
        
        if not file_path.exists():
            return "File non trovato", 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
