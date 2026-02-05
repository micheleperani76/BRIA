#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Route Documenti Cliente
# ==============================================================================
# Versione: 2.0.0
# Data: 2025-01-20
# Descrizione: Gestione documenti cliente (Car Policy, Contratti, Quotazioni, Documenti)
#              - Car Policy con modal grande, file fissabili, conversione PDF
# ==============================================================================

import os
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from app.config import BASE_DIR, CLIENTI_DIR, CLIENTI_PIVA_DIR, CLIENTI_CF_DIR
from app.database import get_connection

# ==============================================================================
# BLUEPRINT
# ==============================================================================

documenti_cliente_bp = Blueprint('documenti_cliente', __name__)

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# Tipi di documenti gestiti
TIPI_DOCUMENTO = {
    'car-policy': {
        'nome': 'Car Policy',
        'multiplo': True,
        'cartella': 'car-policy'
    },
    'contratti': {
        'nome': 'Contratti',
        'multiplo': True,
        'cartella': 'contratti'
    },
    'ordini': {
        'nome': 'Ordini',
        'multiplo': True,
        'cartella': 'ordini'
    },
    'quotazioni': {
        'nome': 'Quotazioni',
        'multiplo': True,
        'cartella': 'quotazioni'
    },
    'documenti': {
        'nome': 'Documenti',
        'multiplo': True,
        'cartella': 'documenti'
    }
}

# Estensioni consentite
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'png', 'jpg', 'jpeg', 'zip', 'odt'}

# Estensioni che richiedono conversione in PDF
CONVERTIBLE_EXTENSIONS = {'doc', 'docx', 'odt'}

# Estensioni consentite per Car Policy (solo questi)
CAR_POLICY_EXTENSIONS = {'pdf', 'doc', 'docx', 'odt', 'xls', 'xlsx'}


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def allowed_file(filename):
    """Verifica se l'estensione del file e' consentita."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_file_for_type(filename, tipo_doc):
    """Verifica se l'estensione e' consentita per il tipo di documento."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    
    if tipo_doc == 'car-policy':
        return ext in CAR_POLICY_EXTENSIONS
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    """Restituisce l'estensione del file in minuscolo."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def convert_to_pdf(filepath):
    """
    Converte un file doc/docx/odt in PDF usando LibreOffice headless.
    
    Args:
        filepath: Path del file da convertire
    
    Returns:
        tuple: (success: bool, pdf_path: Path or None, error: str or None)
    """
    filepath = Path(filepath)
    ext = get_file_extension(filepath.name)
    
    if ext not in CONVERTIBLE_EXTENSIONS:
        return False, None, f"Estensione {ext} non convertibile"
    
    try:
        result = subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', str(filepath.parent),
            str(filepath)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            return False, None, f"Errore LibreOffice: {result.stderr}"
        
        pdf_name = filepath.stem + '.pdf'
        pdf_path = filepath.parent / pdf_name
        
        if pdf_path.exists():
            return True, pdf_path, None
        else:
            return False, None, "PDF non generato"
    
    except subprocess.TimeoutExpired:
        return False, None, "Timeout conversione (>60s)"
    except Exception as e:
        return False, None, str(e)


def get_cliente_by_id(cliente_id):
    """Recupera i dati del cliente dal database."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cur = conn.cursor()
    cur.execute("SELECT id, p_iva, cod_fiscale, ragione_sociale FROM clienti WHERE id = ?", (cliente_id,))
    cliente = cur.fetchone()
    conn.close()
    return cliente


def get_cliente_doc_path(cliente, tipo_doc):
    """Ritorna il path della cartella documenti per un cliente."""
    if tipo_doc not in TIPI_DOCUMENTO:
        raise ValueError(f"Tipo documento non valido: {tipo_doc}")
    
    if cliente.get('p_iva'):
        piva = cliente['p_iva'].upper().replace('IT', '').replace(' ', '').strip()
        base_path = CLIENTI_PIVA_DIR / piva
    elif cliente.get('cod_fiscale'):
        base_path = CLIENTI_CF_DIR / cliente['cod_fiscale'].upper().strip()
    else:
        raise ValueError("Cliente senza P.IVA e senza CF")
    
    cartella = TIPI_DOCUMENTO[tipo_doc]['cartella']
    return base_path / cartella


def ensure_doc_folder(cliente, tipo_doc):
    """Crea la cartella documenti se non esiste."""
    path = get_cliente_doc_path(cliente, tipo_doc)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ==============================================================================
# FUNZIONI CAR POLICY META (file fissati)
# ==============================================================================

def get_car_policy_meta(cliente_id):
    """Recupera i metadati car policy per un cliente."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cur = conn.cursor()
    cur.execute("""
        SELECT nome_file, fissato, data_fissato 
        FROM car_policy_meta 
        WHERE cliente_id = ?
    """, (cliente_id,))
    rows = cur.fetchall()
    conn.close()
    
    # Ritorna dict nome_file -> info
    return {row['nome_file']: row for row in rows}


def set_file_fissato(cliente_id, nome_file, fissato):
    """Imposta lo stato fissato di un file."""
    conn = get_connection()
    cur = conn.cursor()
    
    if fissato:
        # Inserisci o aggiorna
        cur.execute("""
            INSERT INTO car_policy_meta (cliente_id, nome_file, fissato, data_fissato)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(cliente_id, nome_file) DO UPDATE SET
                fissato = 1,
                data_fissato = ?
        """, (cliente_id, nome_file, datetime.now().isoformat(), datetime.now().isoformat()))
    else:
        # Aggiorna a non fissato
        cur.execute("""
            UPDATE car_policy_meta 
            SET fissato = 0, data_fissato = NULL
            WHERE cliente_id = ? AND nome_file = ?
        """, (cliente_id, nome_file))
    
    conn.commit()
    conn.close()


def elimina_car_policy_meta(cliente_id, nome_file):
    """Elimina i metadati di un file."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM car_policy_meta 
        WHERE cliente_id = ? AND nome_file = ?
    """, (cliente_id, nome_file))
    conn.commit()
    conn.close()


def aggiorna_nome_file_meta(cliente_id, vecchio_nome, nuovo_nome):
    """Aggiorna il nome file nei metadati dopo rinomina."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE car_policy_meta 
        SET nome_file = ?
        WHERE cliente_id = ? AND nome_file = ?
    """, (nuovo_nome, cliente_id, vecchio_nome))
    conn.commit()
    conn.close()


# ==============================================================================
# FUNZIONI DOCUMENTI
# ==============================================================================

def get_documenti_cliente(cliente, tipo_doc):
    """Elenca i documenti di un certo tipo per un cliente."""
    try:
        path = get_cliente_doc_path(cliente, tipo_doc)
        if not path.exists():
            return []
        
        # Recupera metadati se car-policy
        meta = {}
        if tipo_doc == 'car-policy':
            meta = get_car_policy_meta(cliente['id'])
        
        documenti = []
        for f in sorted(path.iterdir()):
            if f.is_file() and not f.name.startswith('_'):
                stat = f.stat()
                file_meta = meta.get(f.name, {})
                documenti.append({
                    'nome': f.name,
                    'nome_originale': '_'.join(f.name.split('_')[1:]) if '_' in f.name else f.name,
                    'dimensione': stat.st_size,
                    'dimensione_fmt': format_size(stat.st_size),
                    'data_modifica': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                    'path_relativo': str(f.relative_to(CLIENTI_DIR)),
                    'fissato': file_meta.get('fissato', 0),
                    'data_fissato': file_meta.get('data_fissato')
                })
        return documenti
    except Exception:
        return []


def format_size(size_bytes):
    """Formatta dimensione file in formato leggibile."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def conta_documenti_cliente(cliente, tipo_doc):
    """Conta i documenti di un certo tipo per un cliente."""
    return len(get_documenti_cliente(cliente, tipo_doc))


def ha_documenti(cliente, tipo_doc):
    """Verifica se il cliente ha almeno un documento del tipo specificato."""
    return conta_documenti_cliente(cliente, tipo_doc) > 0


# ==============================================================================
# ROUTE: LISTA DOCUMENTI
# ==============================================================================

@documenti_cliente_bp.route('/api/cliente/<int:cliente_id>/documenti/<tipo_doc>')
def api_lista_documenti(cliente_id, tipo_doc):
    """API per ottenere lista documenti di un cliente."""
    if tipo_doc not in TIPI_DOCUMENTO:
        return jsonify({'success': False, 'error': 'Tipo documento non valido'}), 400
    
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    documenti = get_documenti_cliente(cliente, tipo_doc)
    
    return jsonify({
        'success': True,
        'tipo': tipo_doc,
        'nome_tipo': TIPI_DOCUMENTO[tipo_doc]['nome'],
        'documenti': documenti,
        'count': len(documenti)
    })


# ==============================================================================
# ROUTE: VERIFICA DUPLICATI
# ==============================================================================

@documenti_cliente_bp.route('/api/cliente/<int:cliente_id>/documenti/<tipo_doc>/verifica', methods=['POST'])
def api_verifica_duplicato(cliente_id, tipo_doc):
    """API per verificare se esistono duplicati prima dell'upload."""
    if tipo_doc not in TIPI_DOCUMENTO:
        return jsonify({'success': False, 'error': 'Tipo documento non valido'}), 400
    
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    if not data or 'nome_file' not in data:
        return jsonify({'success': False, 'error': 'Nome file non specificato'}), 400
    
    nome_file = data['nome_file']
    nome_sicuro = secure_filename(nome_file)
    nome_base = Path(nome_sicuro).stem
    ext = get_file_extension(nome_sicuro)
    
    try:
        doc_path = get_cliente_doc_path(cliente, tipo_doc)
        if not doc_path.exists():
            return jsonify({'success': True, 'duplicati': []})
        
        duplicati = []
        
        for f in doc_path.iterdir():
            if f.is_file():
                nome_originale = '_'.join(f.name.split('_')[1:]) if '_' in f.name else f.name
                nome_base_esistente = Path(nome_originale).stem
                
                if nome_base_esistente.lower() == nome_base.lower():
                    duplicati.append({
                        'nome': f.name,
                        'nome_originale': nome_originale,
                        'ext': get_file_extension(f.name)
                    })
        
        if ext in CONVERTIBLE_EXTENSIONS:
            pdf_nome_base = nome_base
            for f in doc_path.iterdir():
                if f.is_file():
                    nome_originale = '_'.join(f.name.split('_')[1:]) if '_' in f.name else f.name
                    if nome_originale.lower() == f"{pdf_nome_base}.pdf".lower():
                        if not any(d['nome'] == f.name for d in duplicati):
                            duplicati.append({
                                'nome': f.name,
                                'nome_originale': nome_originale,
                                'ext': 'pdf'
                            })
        
        return jsonify({
            'success': True,
            'duplicati': duplicati,
            'genera_pdf': ext in CONVERTIBLE_EXTENSIONS
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: UPLOAD DOCUMENTO
# ==============================================================================

@documenti_cliente_bp.route('/api/cliente/<int:cliente_id>/documenti/<tipo_doc>/upload', methods=['POST'])
def api_upload_documento(cliente_id, tipo_doc):
    """API per caricare un documento."""
    if tipo_doc not in TIPI_DOCUMENTO:
        return jsonify({'success': False, 'error': 'Tipo documento non valido'}), 400
    
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun file inviato'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nome file vuoto'}), 400
    
    if not allowed_file_for_type(file.filename, tipo_doc):
        if tipo_doc == 'car-policy':
            return jsonify({'success': False, 'error': 'Car Policy accetta solo: PDF, DOC, DOCX, ODT'}), 400
        return jsonify({'success': False, 'error': 'Tipo file non consentito'}), 400
    
    sovrascrivi = request.form.get('sovrascrivi', '').split(',')
    sovrascrivi = [s.strip() for s in sovrascrivi if s.strip()]
    
    try:
        doc_path = ensure_doc_folder(cliente, tipo_doc)
        
        nome_sicuro = secure_filename(file.filename)
        nome_univoco = f"{uuid.uuid4().hex[:8]}_{nome_sicuro}"
        filepath = doc_path / nome_univoco
        
        for nome_da_eliminare in sovrascrivi:
            file_da_eliminare = doc_path / nome_da_eliminare
            if file_da_eliminare.exists():
                file_da_eliminare.unlink()
                if tipo_doc == 'car-policy':
                    elimina_car_policy_meta(cliente_id, nome_da_eliminare)
        
        file.save(str(filepath))
        
        risultato = {
            'success': True,
            'message': 'Documento caricato con successo',
            'documento': {
                'nome': nome_univoco,
                'nome_originale': nome_sicuro,
                'path_relativo': str(filepath.relative_to(CLIENTI_DIR))
            }
        }
        
        return jsonify(risultato)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: ELIMINA DOCUMENTO
# ==============================================================================

@documenti_cliente_bp.route('/api/cliente/<int:cliente_id>/documenti/<tipo_doc>/elimina', methods=['POST'])
def api_elimina_documento(cliente_id, tipo_doc):
    """API per eliminare un documento."""
    if tipo_doc not in TIPI_DOCUMENTO:
        return jsonify({'success': False, 'error': 'Tipo documento non valido'}), 400
    
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    if not data or 'nome_file' not in data:
        return jsonify({'success': False, 'error': 'Nome file non specificato'}), 400
    
    nome_file = data['nome_file']
    
    try:
        doc_path = get_cliente_doc_path(cliente, tipo_doc)
        filepath = doc_path / nome_file
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File non trovato'}), 404
        
        if not filepath.is_file():
            return jsonify({'success': False, 'error': 'Non e\' un file'}), 400
        
        filepath.unlink()
        
        # Elimina anche metadati se car-policy
        if tipo_doc == 'car-policy':
            elimina_car_policy_meta(cliente_id, nome_file)
        
        return jsonify({
            'success': True,
            'message': 'Documento eliminato con successo'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: RINOMINA DOCUMENTO
# ==============================================================================

@documenti_cliente_bp.route('/api/cliente/<int:cliente_id>/documenti/<tipo_doc>/rinomina', methods=['POST'])
def api_rinomina_documento(cliente_id, tipo_doc):
    """API per rinominare un documento."""
    if tipo_doc not in TIPI_DOCUMENTO:
        return jsonify({'success': False, 'error': 'Tipo documento non valido'}), 400
    
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    if not data or 'nome_file' not in data or 'nuovo_nome' not in data:
        return jsonify({'success': False, 'error': 'Parametri mancanti (nome_file, nuovo_nome)'}), 400
    
    nome_file = data['nome_file']
    nuovo_nome = data['nuovo_nome'].strip()
    
    if not nuovo_nome:
        return jsonify({'success': False, 'error': 'Nuovo nome non valido'}), 400
    
    try:
        doc_path = get_cliente_doc_path(cliente, tipo_doc)
        filepath = doc_path / nome_file
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File non trovato'}), 404
        
        if not filepath.is_file():
            return jsonify({'success': False, 'error': 'Non e\' un file'}), 400
        
        if '_' in nome_file:
            uuid_prefix = nome_file.split('_')[0]
        else:
            uuid_prefix = uuid.uuid4().hex[:8]
        
        ext_originale = get_file_extension(nome_file)
        ext_nuovo = get_file_extension(nuovo_nome)
        
        if not ext_nuovo:
            nuovo_nome = f"{nuovo_nome}.{ext_originale}"
        
        nuovo_nome_sicuro = secure_filename(nuovo_nome)
        nuovo_nome_completo = f"{uuid_prefix}_{nuovo_nome_sicuro}"
        nuovo_filepath = doc_path / nuovo_nome_completo
        
        if nuovo_filepath.exists():
            return jsonify({'success': False, 'error': 'Esiste gia\' un file con questo nome'}), 400
        
        filepath.rename(nuovo_filepath)
        
        # Aggiorna metadati se car-policy
        if tipo_doc == 'car-policy':
            aggiorna_nome_file_meta(cliente_id, nome_file, nuovo_nome_completo)
        
        return jsonify({
            'success': True,
            'message': 'Documento rinominato con successo',
            'documento': {
                'nome': nuovo_nome_completo,
                'nome_originale': nuovo_nome_sicuro
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: FISSA/SFISSA FILE (solo car-policy)
# ==============================================================================

@documenti_cliente_bp.route('/api/cliente/<int:cliente_id>/documenti/car-policy/fissa', methods=['POST'])
def api_fissa_file(cliente_id):
    """API per fissare/sfissare un file car-policy."""
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    if not data or 'nome_file' not in data:
        return jsonify({'success': False, 'error': 'Nome file non specificato'}), 400
    
    nome_file = data['nome_file']
    
    try:
        # Verifica che il file esista
        doc_path = get_cliente_doc_path(cliente, 'car-policy')
        filepath = doc_path / nome_file
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File non trovato'}), 404
        
        # Recupera stato attuale
        meta = get_car_policy_meta(cliente_id)
        file_meta = meta.get(nome_file, {})
        attualmente_fissato = file_meta.get('fissato', 0)
        
        # Toggle
        nuovo_stato = 0 if attualmente_fissato else 1
        set_file_fissato(cliente_id, nome_file, nuovo_stato)
        
        return jsonify({
            'success': True,
            'fissato': nuovo_stato,
            'message': 'File fissato' if nuovo_stato else 'File sfissato'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: CONVERTI FILE IN PDF (manuale)
# ==============================================================================

@documenti_cliente_bp.route('/api/cliente/<int:cliente_id>/documenti/car-policy/converti-pdf', methods=['POST'])
def api_converti_pdf(cliente_id):
    """API per convertire manualmente un file doc/docx/odt in PDF."""
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    if not data or 'nome_file' not in data:
        return jsonify({'success': False, 'error': 'Nome file non specificato'}), 400
    
    nome_file = data['nome_file']
    
    try:
        doc_path = get_cliente_doc_path(cliente, 'car-policy')
        filepath = doc_path / nome_file
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File non trovato'}), 404
        
        ext = get_file_extension(nome_file)
        if ext not in CONVERTIBLE_EXTENSIONS:
            return jsonify({
                'success': False, 
                'error': f'Formato {ext.upper()} non convertibile. Usa DOC, DOCX o ODT.'
            }), 400
        
        # Converti in PDF
        success, pdf_path, error = convert_to_pdf(filepath)
        
        if not success:
            return jsonify({
                'success': False,
                'error': error or 'Conversione fallita'
            }), 500
        
        # Rinomina il PDF con uuid prefix
        pdf_nome_univoco = f"{uuid.uuid4().hex[:8]}_{pdf_path.stem}.pdf"
        pdf_path_nuovo = doc_path / pdf_nome_univoco
        pdf_path.rename(pdf_path_nuovo)
        
        return jsonify({
            'success': True,
            'message': 'File convertito in PDF con successo',
            'pdf': {
                'nome': pdf_nome_univoco,
                'nome_originale': f"{pdf_path.stem}.pdf"
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: DOWNLOAD/VISUALIZZA DOCUMENTO
# ==============================================================================

@documenti_cliente_bp.route('/cliente/<int:cliente_id>/documento/<tipo_doc>/<nome_file>')
def download_documento(cliente_id, tipo_doc, nome_file):
    """Serve un documento per download/visualizzazione."""
    if tipo_doc not in TIPI_DOCUMENTO:
        return "Tipo documento non valido", 400
    
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return "Cliente non trovato", 404
    
    try:
        doc_path = get_cliente_doc_path(cliente, tipo_doc)
        filepath = doc_path / nome_file
        
        if not filepath.exists() or not filepath.is_file():
            return "File non trovato", 404
        
        return send_from_directory(str(doc_path), nome_file)
    
    except Exception as e:
        return f"Errore: {str(e)}", 500


# ==============================================================================
# FUNZIONE REGISTRAZIONE BLUEPRINT
# ==============================================================================

def register_documenti_cliente_routes(app):
    """Registra il blueprint nell'app Flask."""
    app.register_blueprint(documenti_cliente_bp)
    
    @app.context_processor
    def inject_documenti_helpers():
        return {
            'ha_car_policy': lambda cliente: ha_documenti(cliente, 'car-policy'),
            'conta_car_policy': lambda cliente: conta_documenti_cliente(cliente, 'car-policy'),
            'get_documenti_tipo': get_documenti_cliente,
            'TIPI_DOCUMENTO': TIPI_DOCUMENTO
        }
