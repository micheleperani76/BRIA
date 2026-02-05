#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Route Documenti Strutturati
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-19
# Descrizione: Gestione documenti cliente con scadenze e logica per forma giuridica
# ==============================================================================

import os
import uuid
from pathlib import Path
from datetime import datetime, date
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from app.config import BASE_DIR, CLIENTI_DIR, CLIENTI_PIVA_DIR, CLIENTI_CF_DIR
from app.database import get_connection

# ==============================================================================
# BLUEPRINT
# ==============================================================================

documenti_strutturati_bp = Blueprint('documenti_strutturati', __name__)

# ==============================================================================
# CONFIGURAZIONE TIPI DOCUMENTO
# ==============================================================================

# Tipi documento con logica scadenza
TIPI_DOCUMENTO_STRUTTURATI = {
    'identita_lr': {
        'nome': "Carta d'Identita",
        'ha_scadenza': True,
        'gruppo': 'legale_rappresentante',
        'guida': "Scadenza sul RETRO (CIE) o FRONTE in basso (cartacea). Validita 10 anni."
    },
    'codice_fiscale_lr': {
        'nome': 'Codice Fiscale / Tessera Sanitaria',
        'ha_scadenza': True,
        'gruppo': 'legale_rappresentante',
        'guida': "Scadenza sul FRONTE della Tessera Sanitaria, in basso a destra sotto il codice a barre."
    },
    'patente_lr': {
        'nome': 'Patente di Guida',
        'ha_scadenza': True,
        'gruppo': 'legale_rappresentante',
        'guida': "Scadenza sul FRONTE, campo 4b. Verificare categoria abilitata."
    },
    'visura_camerale': {
        'nome': 'Visura Camerale',
        'ha_scadenza': True,
        'validita_mesi': 6,
        'guida': "Validita 6 mesi dalla data del documento. Data in alto a destra."
    },
    'bilancio': {
        'nome': 'Bilancio + Nota Integrativa',
        'ha_scadenza': True,
        'guida': "Ultimo bilancio depositato completo di nota integrativa."
    },
    'certificato_bilancio': {
        'nome': 'Certificato Deposito Bilancio',
        'ha_scadenza': False,
        'legato_a': 'bilancio',
        'guida': "Certificato di avvenuto deposito del bilancio."
    },
    'modello_unico': {
        'nome': 'Modello Unico',
        'ha_scadenza': True,
        'guida': "Modello Unico ultimo anno fiscale."
    },
    'attestato_unico': {
        'nome': 'Attestato Presentazione Unico',
        'ha_scadenza': False,
        'legato_a': 'modello_unico',
        'guida': "Attestato di avvenuta presentazione dell'Unico all'Agenzia delle Entrate (2 pagine)."
    },
    'atto_costitutivo': {
        'nome': 'Atto Costitutivo',
        'ha_scadenza': False,
        'solo_neo': True,
        'guida': "Richiesto solo per aziende neo costituite (meno di 12 mesi)."
    },
    'privacy': {
        'nome': 'Privacy Firmata',
        'ha_scadenza': False,
        'richiede_noleggiatore': True,
        'guida': "Modulo Privacy con Timbro e Firma. Selezionare il noleggiatore."
    },
    'utenza': {
        'nome': 'Utenza Intestata',
        'ha_scadenza': False,
        'guida': "Prima pagina di una utenza luce, gas, telefono o altro intestata."
    }
}

# Documenti richiesti per forma giuridica
DOCUMENTI_PER_FORMA = {
    'SOCIETA_CAPITALI': [
        'identita_lr', 'codice_fiscale_lr', 'patente_lr',
        'visura_camerale', 'bilancio', 'certificato_bilancio',
        'atto_costitutivo', 'privacy'
    ],
    'SOCIETA_PERSONE': [
        'identita_lr', 'codice_fiscale_lr', 'patente_lr',
        'visura_camerale', 'modello_unico', 'attestato_unico',
        'atto_costitutivo', 'privacy'
    ],
    'DITTA_INDIVIDUALE': [
        'identita_lr', 'codice_fiscale_lr', 'patente_lr',
        'visura_camerale', 'modello_unico', 'attestato_unico',
        'privacy', 'utenza'
    ],
    'PRIVATO': [
        'identita_lr', 'codice_fiscale_lr', 'patente_lr',
        'privacy', 'utenza'
    ]
}

# Mapping forma giuridica DB -> categoria
MAPPING_FORMA_GIURIDICA = {
    "SOCIETA' A RESPONSABILITA' LIMITATA": 'SOCIETA_CAPITALI',
    "SOCIETA' A RESPONSABILITA' LIMITATA SEMPLIFICATA": 'SOCIETA_CAPITALI',
    "SRL": 'SOCIETA_CAPITALI',
    "SRLS": 'SOCIETA_CAPITALI',
    "S.R.L.": 'SOCIETA_CAPITALI',
    "SOCIETA' PER AZIONI": 'SOCIETA_CAPITALI',
    "SPA": 'SOCIETA_CAPITALI',
    "S.P.A.": 'SOCIETA_CAPITALI',
    "SOCIETA' COOPERATIVA A RESPONSABILITA' LIMITATA": 'SOCIETA_CAPITALI',
    "SCARL": 'SOCIETA_CAPITALI',
    "SOCIETA' IN ACCOMANDITA SEMPLICE": 'SOCIETA_PERSONE',
    "SAS": 'SOCIETA_PERSONE',
    "S.A.S.": 'SOCIETA_PERSONE',
    "SOCIETA' IN NOME COLLETTIVO": 'SOCIETA_PERSONE',
    "SNC": 'SOCIETA_PERSONE',
    "S.N.C.": 'SOCIETA_PERSONE',
    "DITTA INDIVIDUALE": 'DITTA_INDIVIDUALE',
    "IMPRESA INDIVIDUALE": 'DITTA_INDIVIDUALE',
    "LIBERO PROFESSIONISTA": 'DITTA_INDIVIDUALE',
    "AGENTE DI COMMERCIO": 'DITTA_INDIVIDUALE',
    "PRIVATO": 'PRIVATO',
    "PERSONA FISICA": 'PRIVATO'
}

# Noleggiatori disponibili (esclusi ALD e Leaseplan fusi in Ayvens)
NOLEGGIATORI_PRIVACY = ['ARVAL', 'LEASYS', 'AYVENS', 'ALPHABET', 'SANTANDER']

# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def get_connection_dict():
    """Connessione DB con row_factory dict."""
    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    return conn


def get_cliente_by_id(cliente_id):
    """Recupera i dati del cliente dal database."""
    conn = get_connection_dict()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, p_iva, cod_fiscale, ragione_sociale, forma_giuridica, 
               data_costituzione, banca, iban 
        FROM clienti WHERE id = ?
    """, (cliente_id,))
    cliente = cur.fetchone()
    conn.close()
    return cliente


def get_categoria_cliente(cliente):
    """Determina la categoria del cliente in base alla forma giuridica."""
    forma = cliente.get('forma_giuridica', '') or ''
    forma_upper = forma.upper().strip()
    
    # Cerca match esatto
    if forma_upper in MAPPING_FORMA_GIURIDICA:
        return MAPPING_FORMA_GIURIDICA[forma_upper]
    
    # Cerca match parziale
    for key, cat in MAPPING_FORMA_GIURIDICA.items():
        if key in forma_upper or forma_upper in key:
            return cat
    
    # Default: Societa di Capitali (caso piu comune)
    return 'SOCIETA_CAPITALI'


def is_neo_costituita(cliente):
    """Verifica se l'azienda e' neo costituita (meno di 12 mesi)."""
    data_cost = cliente.get('data_costituzione')
    if not data_cost:
        return False
    
    try:
        if isinstance(data_cost, str):
            # Prova diversi formati data
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    data_cost = datetime.strptime(data_cost, fmt).date()
                    break
                except ValueError:
                    continue
        
        if isinstance(data_cost, date):
            oggi = date.today()
            delta = oggi - data_cost
            return delta.days < 365
    except Exception:
        pass
    
    return False


def get_cliente_doc_path(cliente):
    """Ritorna il path della cartella documenti strutturati per un cliente."""
    if cliente.get('p_iva'):
        piva = cliente['p_iva'].upper().replace('IT', '').replace(' ', '').strip()
        base_path = CLIENTI_PIVA_DIR / piva
    elif cliente.get('cod_fiscale'):
        base_path = CLIENTI_CF_DIR / cliente['cod_fiscale'].upper().strip()
    else:
        raise ValueError("Cliente senza P.IVA e senza CF")
    
    return base_path / 'documenti_strutturati'


def ensure_doc_folder(cliente):
    """Crea la cartella documenti strutturati se non esiste."""
    path = get_cliente_doc_path(cliente)
    path.mkdir(parents=True, exist_ok=True)
    return path


def calcola_giorni_scadenza(data_scadenza):
    """Calcola i giorni alla scadenza (negativo se scaduto)."""
    if not data_scadenza:
        return None
    
    try:
        if isinstance(data_scadenza, str):
            data_scadenza = datetime.strptime(data_scadenza, '%Y-%m-%d').date()
        
        oggi = date.today()
        delta = data_scadenza - oggi
        return delta.days
    except Exception:
        return None


# ==============================================================================
# ROUTE: INFO DOCUMENTI CLIENTE
# ==============================================================================

@documenti_strutturati_bp.route('/api/cliente/<int:cliente_id>/documenti-strutturati/info')
def api_info_documenti(cliente_id):
    """
    Ritorna informazioni sui documenti richiesti e caricati per il cliente.
    Include: categoria, documenti richiesti, stato di ogni documento.
    """
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    categoria = get_categoria_cliente(cliente)
    neo_costituita = is_neo_costituita(cliente)
    documenti_richiesti = DOCUMENTI_PER_FORMA.get(categoria, [])
    
    # Recupera documenti caricati dal DB
    conn = get_connection_dict()
    cur = conn.cursor()
    cur.execute("""
        SELECT tipo_documento, nome_file, nome_originale, data_documento, 
               data_scadenza, data_caricamento, noleggiatore, note
        FROM documenti_cliente 
        WHERE cliente_id = ?
    """, (cliente_id,))
    docs_db = {row['tipo_documento']: row for row in cur.fetchall()}
    conn.close()
    
    # Costruisci lista documenti con stato
    documenti = []
    for tipo in documenti_richiesti:
        config = TIPI_DOCUMENTO_STRUTTURATI.get(tipo, {})
        
        # Salta atto costitutivo se non neo costituita
        if tipo == 'atto_costitutivo' and not neo_costituita:
            continue
        
        doc_info = {
            'tipo': tipo,
            'nome': config.get('nome', tipo),
            'guida': config.get('guida', ''),
            'ha_scadenza': config.get('ha_scadenza', False),
            'richiede_noleggiatore': config.get('richiede_noleggiatore', False),
            'gruppo': config.get('gruppo', 'azienda'),
            'caricato': False,
            'file': None,
            'data_documento': None,
            'data_scadenza': None,
            'giorni_scadenza': None,
            'stato': 'mancante',  # mancante, ok, in_scadenza, scaduto
            'noleggiatore': None
        }
        
        if tipo in docs_db:
            row = docs_db[tipo]
            doc_info['caricato'] = True
            doc_info['file'] = row['nome_file']
            doc_info['nome_originale'] = row['nome_originale']
            doc_info['data_documento'] = row['data_documento']
            doc_info['data_scadenza'] = row['data_scadenza']
            doc_info['data_caricamento'] = row['data_caricamento']
            doc_info['noleggiatore'] = row['noleggiatore']
            
            # Calcola stato scadenza
            if config.get('ha_scadenza') and row['data_scadenza']:
                giorni = calcola_giorni_scadenza(row['data_scadenza'])
                doc_info['giorni_scadenza'] = giorni
                
                if giorni is not None:
                    if giorni < 0:
                        doc_info['stato'] = 'scaduto'
                    elif giorni <= 30:
                        doc_info['stato'] = 'in_scadenza'
                    else:
                        doc_info['stato'] = 'ok'
            else:
                doc_info['stato'] = 'ok'
        
        documenti.append(doc_info)
    
    # Info banca/IBAN
    banca_iban = {
        'banca': cliente.get('banca') or '',
        'iban': cliente.get('iban') or '',
        'completo': bool(cliente.get('banca') and cliente.get('iban'))
    }
    
    return jsonify({
        'success': True,
        'cliente_id': cliente_id,
        'ragione_sociale': cliente.get('ragione_sociale', ''),
        'forma_giuridica': cliente.get('forma_giuridica', ''),
        'categoria': categoria,
        'neo_costituita': neo_costituita,
        'documenti': documenti,
        'banca_iban': banca_iban,
        'noleggiatori_disponibili': NOLEGGIATORI_PRIVACY
    })


# ==============================================================================
# ROUTE: UPLOAD DOCUMENTO STRUTTURATO
# ==============================================================================

@documenti_strutturati_bp.route('/api/cliente/<int:cliente_id>/documenti-strutturati/upload', methods=['POST'])
def api_upload_documento_strutturato(cliente_id):
    """
    Upload di un documento strutturato con metadati (scadenza, noleggiatore, ecc.)
    
    Form data:
        - file: il file PDF
        - tipo_documento: tipo da TIPI_DOCUMENTO_STRUTTURATI
        - data_scadenza: (opzionale) data scadenza YYYY-MM-DD
        - noleggiatore: (opzionale) per documenti privacy
    """
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    # Verifica file
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun file caricato'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nessun file selezionato'}), 400
    
    # Verifica estensione (solo PDF)
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Solo file PDF ammessi'}), 400
    
    # Verifica tipo documento
    tipo_doc = request.form.get('tipo_documento', '')
    if tipo_doc not in TIPI_DOCUMENTO_STRUTTURATI:
        return jsonify({'success': False, 'error': f'Tipo documento non valido: {tipo_doc}'}), 400
    
    config = TIPI_DOCUMENTO_STRUTTURATI[tipo_doc]
    
    # Verifica data scadenza se richiesta
    data_scadenza = request.form.get('data_scadenza', '').strip() or None
    if config.get('ha_scadenza') and not data_scadenza:
        return jsonify({'success': False, 'error': 'Data scadenza obbligatoria per questo documento'}), 400
    
    # Verifica noleggiatore se richiesto
    noleggiatore = request.form.get('noleggiatore', '').strip() or None
    if config.get('richiede_noleggiatore') and not noleggiatore:
        return jsonify({'success': False, 'error': 'Selezionare un noleggiatore'}), 400
    
    try:
        # Crea cartella
        doc_path = ensure_doc_folder(cliente)
        
        # Nome file univoco
        nome_sicuro = secure_filename(file.filename)
        nome_univoco = f"{tipo_doc}_{uuid.uuid4().hex[:8]}_{nome_sicuro}"
        filepath = doc_path / nome_univoco
        
        # Se esiste gia' un documento di questo tipo, elimina il vecchio file
        conn = get_connection_dict()
        cur = conn.cursor()
        cur.execute("SELECT nome_file FROM documenti_cliente WHERE cliente_id = ? AND tipo_documento = ?",
                    (cliente_id, tipo_doc))
        old_doc = cur.fetchone()
        
        if old_doc:
            old_file = doc_path / old_doc['nome_file']
            if old_file.exists():
                old_file.unlink()
            # Aggiorna record esistente
            cur.execute("""
                UPDATE documenti_cliente 
                SET nome_file = ?, nome_originale = ?, data_documento = ?, 
                    data_scadenza = ?, data_caricamento = ?, noleggiatore = ?
                WHERE cliente_id = ? AND tipo_documento = ?
            """, (
                nome_univoco, nome_sicuro, date.today().isoformat(),
                data_scadenza, datetime.now().isoformat(), noleggiatore,
                cliente_id, tipo_doc
            ))
        else:
            # Inserisci nuovo record
            cur.execute("""
                INSERT INTO documenti_cliente 
                (cliente_id, tipo_documento, nome_file, nome_originale, data_documento, 
                 data_scadenza, data_caricamento, noleggiatore)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cliente_id, tipo_doc, nome_univoco, nome_sicuro, 
                date.today().isoformat(), data_scadenza, 
                datetime.now().isoformat(), noleggiatore
            ))
        
        conn.commit()
        conn.close()
        
        # Salva file
        file.save(str(filepath))
        
        return jsonify({
            'success': True,
            'message': 'Documento caricato con successo',
            'documento': {
                'tipo': tipo_doc,
                'nome': nome_univoco,
                'nome_originale': nome_sicuro,
                'data_scadenza': data_scadenza,
                'noleggiatore': noleggiatore
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: ELIMINA DOCUMENTO STRUTTURATO
# ==============================================================================

@documenti_strutturati_bp.route('/api/cliente/<int:cliente_id>/documenti-strutturati/elimina', methods=['POST'])
def api_elimina_documento_strutturato(cliente_id):
    """Elimina un documento strutturato (file + record DB)."""
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    tipo_doc = data.get('tipo_documento', '')
    
    if tipo_doc not in TIPI_DOCUMENTO_STRUTTURATI:
        return jsonify({'success': False, 'error': 'Tipo documento non valido'}), 400
    
    try:
        doc_path = get_cliente_doc_path(cliente)
        
        # Recupera info file
        conn = get_connection_dict()
        cur = conn.cursor()
        cur.execute("SELECT nome_file FROM documenti_cliente WHERE cliente_id = ? AND tipo_documento = ?",
                    (cliente_id, tipo_doc))
        doc = cur.fetchone()
        
        if doc:
            # Elimina file
            filepath = doc_path / doc['nome_file']
            if filepath.exists():
                filepath.unlink()
            
            # Elimina record DB
            cur.execute("DELETE FROM documenti_cliente WHERE cliente_id = ? AND tipo_documento = ?",
                        (cliente_id, tipo_doc))
            conn.commit()
        
        conn.close()
        
        return jsonify({'success': True, 'message': 'Documento eliminato'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: DOWNLOAD DOCUMENTO STRUTTURATO
# ==============================================================================

@documenti_strutturati_bp.route('/cliente/<int:cliente_id>/documento-strutturato/<tipo_doc>')
def download_documento_strutturato(cliente_id, tipo_doc):
    """Serve un documento strutturato per download/visualizzazione."""
    if tipo_doc not in TIPI_DOCUMENTO_STRUTTURATI:
        return "Tipo documento non valido", 400
    
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return "Cliente non trovato", 404
    
    try:
        doc_path = get_cliente_doc_path(cliente)
        
        # Recupera nome file dal DB
        conn = get_connection_dict()
        cur = conn.cursor()
        cur.execute("SELECT nome_file FROM documenti_cliente WHERE cliente_id = ? AND tipo_documento = ?",
                    (cliente_id, tipo_doc))
        doc = cur.fetchone()
        conn.close()
        
        if not doc:
            return "Documento non trovato", 404
        
        filepath = doc_path / doc['nome_file']
        if not filepath.exists():
            return "File non trovato", 404
        
        return send_from_directory(str(doc_path), doc['nome_file'])
    
    except Exception as e:
        return f"Errore: {str(e)}", 500


# ==============================================================================
# ROUTE: AGGIORNA BANCA/IBAN
# ==============================================================================

@documenti_strutturati_bp.route('/api/cliente/<int:cliente_id>/banca-iban', methods=['POST'])
def api_aggiorna_banca_iban(cliente_id):
    """Aggiorna i campi Banca e IBAN del cliente."""
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    banca = data.get('banca', '').strip()
    iban = data.get('iban', '').strip().upper().replace(' ', '')
    
    # Validazione: entrambi obbligatori
    if not banca or not iban:
        return jsonify({'success': False, 'error': 'Banca e IBAN sono entrambi obbligatori'}), 400
    
    # Validazione IBAN base (IT + 25 caratteri)
    if not iban.startswith('IT') or len(iban) != 27:
        return jsonify({'success': False, 'error': 'IBAN italiano non valido (deve essere IT + 25 caratteri)'}), 400
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE clienti SET banca = ?, iban = ? WHERE id = ?",
                    (banca, iban, cliente_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Dati bancari aggiornati',
            'banca': banca,
            'iban': iban
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# ROUTE: AGGIORNA NOTE GARANTE / ALTRI
# ==============================================================================

@documenti_strutturati_bp.route('/api/cliente/<int:cliente_id>/note-documenti', methods=['POST'])
def api_aggiorna_note_documenti(cliente_id):
    """Aggiorna note garante o altri documenti (campi testo libero)."""
    cliente = get_cliente_by_id(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    data = request.get_json()
    campo = data.get('campo', '')  # 'garante' o 'altri'
    valore = data.get('valore', '').strip()
    
    if campo not in ['garante', 'altri']:
        return jsonify({'success': False, 'error': 'Campo non valido'}), 400
    
    try:
        # Salva in documenti_cliente come tipo speciale (senza file)
        tipo_doc = f'nota_{campo}'
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Verifica se esiste
        cur.execute("SELECT id FROM documenti_cliente WHERE cliente_id = ? AND tipo_documento = ?",
                    (cliente_id, tipo_doc))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE documenti_cliente SET note = ?, data_caricamento = ?
                WHERE cliente_id = ? AND tipo_documento = ?
            """, (valore, datetime.now().isoformat(), cliente_id, tipo_doc))
        else:
            cur.execute("""
                INSERT INTO documenti_cliente (cliente_id, tipo_documento, nome_file, note, data_caricamento)
                VALUES (?, ?, '', ?, ?)
            """, (cliente_id, tipo_doc, valore, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Note salvate'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==============================================================================
# FUNZIONE REGISTRAZIONE BLUEPRINT
# ==============================================================================

def register_documenti_strutturati_routes(app):
    """Registra il blueprint nell'app Flask."""
    app.register_blueprint(documenti_strutturati_bp)
