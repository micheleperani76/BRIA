#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
ROUTES TRASCRIZIONE - Blueprint Flask
==============================================================================
Versione: 1.0.0
Data: 2026-02-03
Descrizione: Route HTTP per il modulo Trascrizione Audio

Route disponibili:
    POST /trascrizione/upload              - Upload file audio
    GET  /trascrizione/coda                - Stato coda (visibile a tutti)
    GET  /trascrizione/mie                 - Le mie trascrizioni a consumo
    GET  /trascrizione/mie/<id>/testo      - Scarica testo trascrizione
    POST /trascrizione/sposta/<id>         - Sposta trascrizione su cliente
    POST /trascrizione/rinomina/<id>       - Rinomina file trascrizione
    POST /trascrizione/elimina/<id>        - Elimina trascrizione consumo
    GET  /trascrizione/api/cerca-clienti   - Ricerca clienti per spostamento
==============================================================================
"""

from flask import (render_template, 
    Blueprint, request, jsonify, session, send_file, abort
)
import sqlite3
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# Import moduli locali
from app.auth import login_required
from app.config_percorsi import DB_FILE, get_cliente_base_path, pulisci_piva
from app.config_trascrizione import (
    FORMATI_AUDIO, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB,
    SOGLIA_GRANDE_BYTES, RETENTION_AUDIO_GIORNI, RETENTION_CONSUMO_GIORNI,
    DIR_ATTESA, DIR_CONSUMO,
    is_formato_valido, get_estensione, get_dir_consumo_data,
    is_orario_accettazione, stima_tempo_trascrizione,
    MODELLO, MODELLO_VELOCE, SOGLIA_CODA_TURBO
)
from app.gestione_commerciali import get_clienti_visibili_ids


# ==============================================================================
# BLUEPRINT
# ==============================================================================

trascrizione_bp = Blueprint('trascrizione', __name__, url_prefix='/trascrizione')


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def get_db():
    """Connessione database con Row factory."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def get_codice_utente(user_id):
    """
    Recupera il codice_utente a 6 cifre dal DB.
    
    Args:
        user_id: ID utente dalla sessione
    
    Returns:
        str: Codice utente (es. '000001') o '000000' se non trovato
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT codice_utente FROM utenti WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['codice_utente'] if row else '000000'


def get_nome_display(user_id):
    """Ritorna nome abbreviato per la coda (es. 'P. Ciotti')."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, cognome, username FROM utenti WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return 'Utente'
    nome = row['nome'] or ''
    cognome = row['cognome'] or ''
    if nome and cognome:
        return f"{nome[0]}. {cognome}"
    return row['username'] or 'Utente'


def get_durata_ffprobe(file_path):
    """Ottiene durata audio con ffprobe (per stima tempo)."""
    import subprocess
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', str(file_path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0


# ==============================================================================
# ROUTE: Upload audio
# ==============================================================================

@trascrizione_bp.route('/upload', methods=['POST'])
@login_required
def upload_audio():
    """
    Upload di un file audio per trascrizione.
    
    Parametri form:
        file: File audio
        tipo: 'cliente' o 'dashboard'
        cliente_id: ID cliente (solo se tipo='cliente')
    
    Returns:
        JSON con id job e posizione in coda
    """
    user_id = session['user_id']
    codice_utente = get_codice_utente(user_id)
    nome_utente = session.get('nome_completo', session.get('username', 'Utente'))
    
    # --- Validazioni ---
    
    # Verifica file presente
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun file selezionato'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'Nessun file selezionato'}), 400
    
    # Verifica formato
    nome_originale = secure_filename(file.filename)
    if not is_formato_valido(nome_originale):
        estensione = get_estensione(nome_originale)
        return jsonify({
            'success': False,
            'error': f'Formato .{estensione} non supportato. Formati accettati: {", ".join(FORMATI_AUDIO)}'
        }), 400
    
    # Verifica dimensione
    file.seek(0, 2)  # Vai alla fine
    dimensione = file.tell()
    file.seek(0)     # Torna all'inizio
    
    if dimensione > MAX_UPLOAD_BYTES:
        return jsonify({
            'success': False,
            'error': f'File troppo grande ({dimensione // (1024*1024)} MB). Massimo: {MAX_UPLOAD_MB} MB'
        }), 400
    
    if dimensione == 0:
        return jsonify({'success': False, 'error': 'Il file e\' vuoto'}), 400
    
    # --- Parametri tipo ---
    
    tipo = request.form.get('tipo', 'dashboard')
    cliente_id = None
    
    if tipo == 'cliente':
        cliente_id = request.form.get('cliente_id')
        if not cliente_id:
            return jsonify({'success': False, 'error': 'Cliente non specificato'}), 400
        
        # Verifica che il cliente esista e sia visibile
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, p_iva FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()
        
        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    # --- Salvataggio file ---
    
    # Nome univoco sistema (UUID)
    formato = get_estensione(nome_originale)
    nome_sistema = f"{uuid.uuid4().hex}.{formato}"
    
    # Salva in cartella attesa
    percorso_attesa = DIR_ATTESA / nome_sistema
    file.save(str(percorso_attesa))
    
    # Calcola durata per stima tempo
    durata = get_durata_ffprobe(percorso_attesa)
    
    # --- Priorita e modello ---
    
    priorita = 1  # Normale
    if dimensione > SOGLIA_GRANDE_BYTES:
        priorita = 0  # Bassa (file grande)
    
    # Conta coda per scelta modello
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM coda_trascrizioni WHERE stato = 'attesa'")
    n_coda = cursor.fetchone()[0]
    
    if priorita == 0 or n_coda >= SOGLIA_CODA_TURBO:
        modello = MODELLO_VELOCE
    else:
        modello = MODELLO
    
    # --- Retention ---
    
    now = datetime.now()
    data_scadenza_audio = None
    data_scadenza_testo = None
    
    if tipo == 'cliente':
        data_scadenza_audio = (now + timedelta(days=RETENTION_AUDIO_GIORNI)).strftime('%Y-%m-%d')
    else:
        data_scadenza_testo = (now + timedelta(days=RETENTION_CONSUMO_GIORNI)).strftime('%Y-%m-%d')
    
    # --- Inserimento in coda ---
    
    cursor.execute('''
        INSERT INTO coda_trascrizioni (
            utente_id, codice_utente, nome_utente, cliente_id, tipo,
            nome_file_originale, nome_file_sistema, formato_originale,
            dimensione_bytes, durata_secondi,
            stato, priorita, modello,
            data_inserimento,
            data_scadenza_audio, data_scadenza_testo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'attesa', ?, ?, ?, ?, ?)
    ''', (
        user_id, codice_utente, nome_utente, cliente_id, tipo,
        nome_originale, nome_sistema, formato,
        dimensione, durata,
        priorita, modello,
        now.isoformat(),
        data_scadenza_audio, data_scadenza_testo
    ))
    
    job_id = cursor.lastrowid
    
    # Posizione in coda
    cursor.execute('''
        SELECT COUNT(*) FROM coda_trascrizioni 
        WHERE stato = 'attesa' AND id < ?
    ''', (job_id,))
    posizione = cursor.fetchone()[0] + 1
    
    conn.commit()
    conn.close()
    
    # Stima tempo
    tempo_stimato = stima_tempo_trascrizione(durata, modello) if durata > 0 else 0
    
    # Messaggio avviso per dashboard
    avviso_audio = ''
    if tipo == 'dashboard':
        avviso_audio = 'Il file audio non verra\' conservato dopo la trascrizione.'
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'posizione_coda': posizione,
        'tempo_stimato_secondi': tempo_stimato,
        'modello': modello,
        'priorita': 'normale' if priorita == 1 else 'bassa (file grande)',
        'avviso': avviso_audio
    })


# ==============================================================================
# ROUTE: Stato coda (visibile a tutti)
# ==============================================================================

@trascrizione_bp.route('/coda', methods=['GET'])
@login_required
def stato_coda():
    """
    Ritorna lo stato della coda di trascrizione.
    Tutti vedono chi sta trascrivendo e chi e' in coda,
    ma NON il contenuto o il cliente associato.
    
    Returns:
        JSON con job in lavorazione e coda
    """
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    
    risultato = {
        'in_lavorazione': None,
        'coda': [],
        'mio_job': None,
        'totale_coda': 0
    }
    
    # Job in lavorazione
    cursor.execute('''
        SELECT id, utente_id, nome_utente, durata_secondi, 
               progresso_percentuale, data_inizio_elaborazione, modello
        FROM coda_trascrizioni
        WHERE stato = 'lavorazione'
        ORDER BY data_inizio_elaborazione DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    if row:
        row = dict(row)
        
        # Calcola tempo restante stimato
        tempo_restante = 0
        if row['durata_secondi'] and row['progresso_percentuale'] < 100:
            tempo_totale = stima_tempo_trascrizione(row['durata_secondi'], row['modello'])
            progresso = max(row['progresso_percentuale'], 1) / 100.0
            tempo_trascorso = tempo_totale * progresso
            tempo_restante = max(0, int(tempo_totale - tempo_trascorso))
        
        risultato['in_lavorazione'] = {
            'nome_utente': row['nome_utente'] or 'Utente',
            'progresso': row['progresso_percentuale'],
            'tempo_restante_min': max(1, tempo_restante // 60),
            'is_mio': row['utente_id'] == user_id,
            'id': row['id'],
            'priorita': row.get('priorita', 1)
        }
    
    # Coda attesa
    cursor.execute('''
        SELECT id, utente_id, nome_utente, durata_secondi, modello, priorita
        FROM coda_trascrizioni
        WHERE stato = 'attesa'
        ORDER BY priorita DESC, data_inserimento ASC
    ''')
    
    posizione = 0
    tempo_cumulativo = 0
    
    # Aggiungi tempo restante del job in lavorazione
    if risultato['in_lavorazione']:
        tempo_cumulativo = risultato['in_lavorazione']['tempo_restante_min'] * 60
    
    for row in cursor.fetchall():
        posizione += 1
        row = dict(row)
        
        tempo_job = stima_tempo_trascrizione(
            row['durata_secondi'] or 0, row['modello']
        )
        
        entry = {
            'posizione': posizione,
            'nome_utente': row['nome_utente'] or 'Utente',
            'is_mio': row['utente_id'] == user_id,
            'id': row['id'],
            'priorita': row.get('priorita', 1)
        }
        
        # Se e' il job dell'utente corrente, segna posizione e tempo attesa totale
        if row['utente_id'] == user_id and risultato['mio_job'] is None:
            attesa_totale = tempo_cumulativo + tempo_job
            attesa_min = max(1, attesa_totale // 60)
            
            # Formatta in modo leggibile
            if attesa_min < 60:
                tempo_formattato = f"~{attesa_min} minuti"
            elif attesa_min < 1440:
                ore = attesa_min // 60
                minuti = attesa_min % 60
                if minuti > 0:
                    tempo_formattato = f"~{ore}h {minuti}min"
                else:
                    tempo_formattato = f"~{ore} ore"
            else:
                giorni = attesa_min // 1440
                ore = (attesa_min % 1440) // 60
                tempo_formattato = f"~{giorni}g {ore}h"
            
            risultato['mio_job'] = {
                'id': row['id'],
                'posizione': posizione,
                'tempo_stimato_min': attesa_min,
                'tempo_formattato': tempo_formattato
            }
        
        # Accumula tempo per i job successivi
        tempo_cumulativo += tempo_job
        
        risultato['coda'].append(entry)
    
    risultato['totale_coda'] = posizione
    
    conn.close()
    return jsonify(risultato)


# ==============================================================================
# ROUTE: Le mie trascrizioni a consumo
# ==============================================================================

@trascrizione_bp.route('/mie', methods=['GET'])
@login_required
def mie_trascrizioni():
    """
    Ritorna le trascrizioni a consumo dell'utente corrente.
    Ordinate per data decrescente.
    Sono PRIVATE: solo l'utente proprietario le vede.
    
    Returns:
        JSON con lista trascrizioni
    """
    user_id = session['user_id']
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, nome_file_originale, formato_originale,
               dimensione_bytes, durata_secondi,
               stato, progresso_percentuale, modello,
               data_inserimento, data_completamento,
               percorso_testo, data_scadenza_testo, errore
        FROM coda_trascrizioni
        WHERE utente_id = ?
          AND tipo = 'dashboard'
          AND stato IN ('completato', 'lavorazione', 'attesa', 'errore')
        ORDER BY data_inserimento DESC
        LIMIT 100
    ''', (user_id,))
    
    trascrizioni = []
    for row in cursor.fetchall():
        row = dict(row)
        
        # Verifica se il file testo esiste ancora
        testo_disponibile = False
        if row['percorso_testo']:
            testo_disponibile = Path(row['percorso_testo']).exists()
        
        # Calcola giorni residui retention
        giorni_residui = None
        if row['data_scadenza_testo']:
            try:
                scadenza = datetime.strptime(row['data_scadenza_testo'], '%Y-%m-%d')
                giorni_residui = (scadenza - datetime.now()).days
                if giorni_residui < 0:
                    giorni_residui = 0
                    testo_disponibile = False
            except ValueError:
                pass
        
        # Formatta durata
        durata_display = ''
        if row['durata_secondi']:
            m = int(row['durata_secondi'] // 60)
            s = int(row['durata_secondi'] % 60)
            durata_display = f"{m}m {s}s"
        
        # Formatta dimensione
        dim_mb = round(row['dimensione_bytes'] / (1024 * 1024), 1) if row['dimensione_bytes'] else 0
        
        trascrizioni.append({
            'id': row['id'],
            'nome_file': row['nome_file_originale'],
            'formato': row['formato_originale'],
            'dimensione_mb': dim_mb,
            'durata': durata_display,
            'stato': row['stato'],
            'progresso': row['progresso_percentuale'],
            'modello': row['modello'],
            'data_inserimento': row['data_inserimento'],
            'data_completamento': row['data_completamento'],
            'testo_disponibile': testo_disponibile,
            'giorni_residui': giorni_residui,
            'errore': row['errore']
        })
    
    conn.close()
    return jsonify({'success': True, 'trascrizioni': trascrizioni})


# ==============================================================================
# ROUTE: Scarica testo trascrizione
# ==============================================================================

@trascrizione_bp.route('/mie/<int:job_id>/testo', methods=['GET'])
@login_required
def scarica_testo(job_id):
    """
    Scarica il testo di una trascrizione.
    Solo il proprietario puo' accedere.
    
    Args:
        job_id: ID del job
    
    Returns:
        File di testo o JSON con contenuto
    """
    user_id = session['user_id']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT percorso_testo, nome_file_originale, utente_id
        FROM coda_trascrizioni
        WHERE id = ? AND stato = 'completato'
    ''', (job_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'success': False, 'error': 'Trascrizione non trovata'}), 404
    
    # Verifica proprieta'
    if row['utente_id'] != user_id:
        return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
    
    percorso = Path(row['percorso_testo'])
    if not percorso.exists():
        return jsonify({'success': False, 'error': 'File testo non piu\' disponibile'}), 404
    
    # Se richiesto come download
    if request.args.get('download') == '1':
        nome_download = Path(row['nome_file_originale']).stem + '.txt'
        return send_file(str(percorso), as_attachment=True, download_name=nome_download)
    
    # Altrimenti ritorna contenuto JSON
    try:
        with open(percorso, 'r', encoding='utf-8') as f:
            contenuto = f.read()
    except Exception as e:
        return jsonify({'success': False, 'error': f'Errore lettura: {e}'}), 500
    
    return jsonify({
        'success': True,
        'testo': contenuto,
        'nome_file': row['nome_file_originale']
    })


# ==============================================================================
# ROUTE: Sposta trascrizione su cliente
# ==============================================================================

@trascrizione_bp.route('/sposta/<int:job_id>', methods=['POST'])
@login_required
def sposta_su_cliente(job_id):
    """
    Sposta una trascrizione a consumo su un cliente.
    Il file .txt viene copiato nella cartella trascrizioni del cliente
    e rimosso dal consumo.
    
    Parametri JSON:
        cliente_id: ID del cliente destinazione
        nuovo_nome: (opzionale) Nuovo nome per il file
    
    Returns:
        JSON con esito operazione
    """
    user_id = session['user_id']
    data = request.get_json() or {}
    
    cliente_id = data.get('cliente_id')
    nuovo_nome = data.get('nuovo_nome', '').strip()
    
    if not cliente_id:
        return jsonify({'success': False, 'error': 'Cliente non specificato'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verifica job
    cursor.execute('''
        SELECT id, utente_id, percorso_testo, nome_file_originale, 
               durata_secondi, data_completamento
        FROM coda_trascrizioni
        WHERE id = ? AND tipo = 'dashboard' AND stato = 'completato'
    ''', (job_id,))
    
    job = cursor.fetchone()
    if not job:
        conn.close()
        return jsonify({'success': False, 'error': 'Trascrizione non trovata'}), 404
    
    # Verifica proprieta'
    if job['utente_id'] != user_id:
        conn.close()
        return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
    
    # Verifica file esiste
    percorso_testo = Path(job['percorso_testo'])
    if not percorso_testo.exists():
        conn.close()
        return jsonify({'success': False, 'error': 'File testo non piu\' disponibile'}), 404
    
    # Verifica cliente esiste e utente lo puo' vedere
    cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
    cliente = cursor.fetchone()
    if not cliente:
        conn.close()
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
    
    cliente_dict = dict(cliente)
    visibili = get_clienti_visibili_ids(conn, user_id)
    if visibili is not None and cliente_dict.get('p_iva') not in visibili:
        conn.close()
        return jsonify({'success': False, 'error': 'Non hai accesso a questo cliente'}), 403
    
    # Calcola destinazione cliente
    try:
        base_path = get_cliente_base_path(cliente_dict)
    except ValueError:
        conn.close()
        return jsonify({'success': False, 'error': 'Cliente senza P.IVA/CF'}), 400
    
    trascrizioni_dir = base_path / 'trascrizioni'
    trascrizioni_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome file destinazione
    if nuovo_nome:
        # Usa nome personalizzato
        nome_safe = secure_filename(nuovo_nome)
        if not nome_safe.endswith('.txt'):
            nome_safe += '.txt'
    else:
        # Usa nome originale con timestamp
        nome_orig = Path(job['nome_file_originale']).stem
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        nome_safe = f"{timestamp}_{nome_orig}.txt"
    
    dest_testo = trascrizioni_dir / nome_safe
    
    # Evita sovrascrittura
    counter = 1
    while dest_testo.exists():
        stem = Path(nome_safe).stem
        dest_testo = trascrizioni_dir / f"{stem}_{counter}.txt"
        counter += 1
    
    # Sposta il file
    try:
        shutil.copy2(str(percorso_testo), str(dest_testo))
        percorso_testo.unlink()  # Rimuovi dal consumo
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': f'Errore spostamento: {e}'}), 500
    
    # Aggiorna record DB
    now = datetime.now()
    cursor.execute('''
        UPDATE coda_trascrizioni SET
            tipo = 'cliente',
            cliente_id = ?,
            percorso_testo = ?,
            data_scadenza_testo = NULL,
            data_scadenza_audio = ?
        WHERE id = ?
    ''', (
        cliente_id,
        str(dest_testo),
        (now + timedelta(days=RETENTION_AUDIO_GIORNI)).strftime('%Y-%m-%d'),
        job_id
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'messaggio': f'Trascrizione spostata su {cliente_dict.get("nome_cliente", "cliente")}',
        'destinazione': str(dest_testo.name)
    })


# ==============================================================================
# ROUTE: Rinomina trascrizione
# ==============================================================================

@trascrizione_bp.route('/rinomina/<int:job_id>', methods=['POST'])
@login_required
def rinomina_trascrizione(job_id):
    """
    Rinomina il file di una trascrizione a consumo.
    
    Parametri JSON:
        nuovo_nome: Nuovo nome (senza estensione)
    """
    user_id = session['user_id']
    data = request.get_json() or {}
    
    nuovo_nome = data.get('nuovo_nome', '').strip()
    if not nuovo_nome:
        return jsonify({'success': False, 'error': 'Nome non specificato'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, utente_id, percorso_testo
        FROM coda_trascrizioni
        WHERE id = ? AND tipo = 'dashboard' AND stato = 'completato'
    ''', (job_id,))
    
    job = cursor.fetchone()
    if not job:
        conn.close()
        return jsonify({'success': False, 'error': 'Trascrizione non trovata'}), 404
    
    if job['utente_id'] != user_id:
        conn.close()
        return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
    
    percorso_vecchio = Path(job['percorso_testo'])
    if not percorso_vecchio.exists():
        conn.close()
        return jsonify({'success': False, 'error': 'File non piu\' disponibile'}), 404
    
    # Nuovo path
    nome_safe = secure_filename(nuovo_nome)
    if not nome_safe.endswith('.txt'):
        nome_safe += '.txt'
    
    percorso_nuovo = percorso_vecchio.parent / nome_safe
    
    # Evita sovrascrittura
    counter = 1
    while percorso_nuovo.exists() and percorso_nuovo != percorso_vecchio:
        stem = Path(nome_safe).stem
        percorso_nuovo = percorso_vecchio.parent / f"{stem}_{counter}.txt"
        counter += 1
    
    try:
        percorso_vecchio.rename(percorso_nuovo)
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': f'Errore rinomina: {e}'}), 500
    
    # Aggiorna DB
    cursor.execute(
        "UPDATE coda_trascrizioni SET percorso_testo = ? WHERE id = ?",
        (str(percorso_nuovo), job_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'nuovo_nome': percorso_nuovo.name
    })


# ==============================================================================
# ROUTE: Elimina trascrizione consumo
# ==============================================================================

@trascrizione_bp.route('/elimina/<int:job_id>', methods=['POST'])
@login_required
def elimina_trascrizione(job_id):
    """
    Elimina una trascrizione a consumo.
    Solo il proprietario puo' eliminare.
    """
    user_id = session['user_id']
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, utente_id, percorso_testo, tipo
        FROM coda_trascrizioni
        WHERE id = ? AND tipo = 'dashboard'
    ''', (job_id,))
    
    job = cursor.fetchone()
    if not job:
        conn.close()
        return jsonify({'success': False, 'error': 'Trascrizione non trovata'}), 404
    
    if job['utente_id'] != user_id:
        conn.close()
        return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
    
    # Elimina file testo se esiste
    if job['percorso_testo']:
        percorso = Path(job['percorso_testo'])
        if percorso.exists():
            percorso.unlink()
    
    # Aggiorna stato nel DB (soft delete - manteniamo il record per audit)
    cursor.execute('''
        UPDATE coda_trascrizioni SET
            stato = 'eliminato',
            percorso_testo = NULL
        WHERE id = ?
    ''', (job_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'messaggio': 'Trascrizione eliminata'})


# ==============================================================================
# ROUTE: Salta la coda (priorita' massima)
# ==============================================================================

@trascrizione_bp.route('/priorita/<int:job_id>', methods=['POST'])
@login_required
def salta_coda(job_id):
    """
    Imposta priorita' massima (2) su un job in attesa.
    Solo admin o proprietario del job.
    """
    user_id = session['user_id']
    ruolo = session.get('ruolo_base', 'viewer')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, utente_id, stato, priorita FROM coda_trascrizioni WHERE id = ?', (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        return jsonify({'success': False, 'error': 'Job non trovato'}), 404
    
    if job['stato'] != 'attesa':
        conn.close()
        return jsonify({'success': False, 'error': 'Solo job in attesa possono essere prioritizzati'}), 400
    
    if job['utente_id'] != user_id and ruolo != 'admin':
        conn.close()
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    
    cursor.execute('UPDATE coda_trascrizioni SET priorita = 2 WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'messaggio': 'Job spostato in testa alla coda'})

# ==============================================================================
# ROUTE: Ricerca clienti per spostamento (con visibilita)
# ==============================================================================

@trascrizione_bp.route('/api/cerca-clienti', methods=['GET'])
@login_required
def cerca_clienti_per_spostamento():
    """
    Ricerca clienti visibili all'utente corrente.
    Usato nel modal di spostamento trascrizione su cliente.
    
    Parametri query:
        q: Termine di ricerca (min 2 caratteri)
        limit: Max risultati (default 10)
    
    Returns:
        JSON con lista clienti filtrata per visibilita'
    """
    import re
    
    user_id = session['user_id']
    q = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 10)), 30)
    
    if not q or len(q) < 2:
        return jsonify({'success': False, 'error': 'Termine troppo corto'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Parametri ricerca
    search_param = f'%{q}%'
    q_normalized = re.sub(r'[.\-&\'\s]+', '', q.lower())
    search_normalized = f'%{q_normalized}%'
    
    # Lista clienti visibili
    visibili = get_clienti_visibili_ids(conn, user_id)
    
    # Query base
    query = """
        SELECT c.id, c.nome_cliente, c.ragione_sociale, c.p_iva, c.cod_fiscale
        FROM clienti c
        WHERE (
            c.nome_cliente LIKE ?
            OR c.ragione_sociale LIKE ?
            OR c.p_iva LIKE ?
            OR c.cod_fiscale LIKE ?
            OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                c.nome_cliente, '.', ''), ' ', ''), '-', ''), '&', ''), char(39), '')) LIKE ?
        )
    """
    params = [search_param, search_param, search_param, search_param, search_normalized]
    
    # Filtro visibilita'
    if visibili is not None:
        if not visibili:
            conn.close()
            return jsonify({'success': True, 'clienti': []})
        
        placeholders = ','.join('?' * len(visibili))
        query += f" AND c.p_iva IN ({placeholders})"
        params.extend(visibili)
    
    query += " ORDER BY c.nome_cliente LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    clienti = []
    for row in cursor.fetchall():
        row = dict(row)
        display = row['nome_cliente'] or row['ragione_sociale'] or 'N/D'
        piva = row['p_iva'] or row['cod_fiscale'] or ''
        
        clienti.append({
            'id': row['id'],
            'nome': display,
            'piva': piva
        })
    
    conn.close()
    return jsonify({'success': True, 'clienti': clienti})


# ==============================================================================
# ROUTE: Pagina principale trascrizioni
# ==============================================================================

@trascrizione_bp.route('/', methods=['GET'])
@login_required
def pagina_trascrizione():
    """Pagina principale trascrizioni con upload e lista."""
    return render_template('trascrizione.html')


# ==============================================================================
# ROUTE TRASCRIZIONI CLIENTE (per riquadro documenti)
# ==============================================================================

@trascrizione_bp.route('/cliente/<int:cliente_id>/lista', methods=['GET'])
@login_required
def trascrizioni_cliente_lista(cliente_id):
    """Lista file trascrizione di un cliente."""
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB
    import urllib.parse

    try:
        # Recupera cliente
        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'})

        base_path = get_cliente_base_path(dict(cliente))
        trascrizioni_dir = base_path / 'trascrizioni'

        if not trascrizioni_dir.exists():
            return jsonify({'success': True, 'files': []})

        files = []
        for f in sorted(trascrizioni_dir.glob('*.txt'), reverse=True):
            stat = f.stat()
            # Dimensione leggibile
            size = stat.st_size
            if size < 1024:
                dim = f"{size} B"
            elif size < 1024 * 1024:
                dim = f"{size / 1024:.1f} KB"
            else:
                dim = f"{size / (1024*1024):.1f} MB"

            # Data dal nome file (formato: 2026-02-03_1630_xxx.txt)
            nome = f.name
            data_str = ''
            if len(nome) > 16 and nome[4] == '-' and nome[7] == '-':
                try:
                    data_str = f"{nome[8:10]}/{nome[5:7]}/{nome[0:4]} {nome[11:13]}:{nome[13:15]}"
                except:
                    pass
            if not data_str:
                from datetime import datetime
                data_str = datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M')

            files.append({
                'nome': f.stem,
                'nome_codificato': urllib.parse.quote(f.name, safe=''),
                'data': data_str,
                'dimensione': dim
            })

        return jsonify({'success': True, 'files': files})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@trascrizione_bp.route('/cliente/<int:cliente_id>/conta', methods=['GET'])
@login_required
def trascrizioni_cliente_conta(cliente_id):
    """Conta trascrizioni di un cliente (per badge)."""
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB

    try:
        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return jsonify({'success': False, 'count': 0})

        base_path = get_cliente_base_path(dict(cliente))
        trascrizioni_dir = base_path / 'trascrizioni'

        if not trascrizioni_dir.exists():
            return jsonify({'success': True, 'count': 0})

        count = len(list(trascrizioni_dir.glob('*.txt')))
        return jsonify({'success': True, 'count': count})

    except Exception:
        return jsonify({'success': True, 'count': 0})


@trascrizione_bp.route('/cliente/<int:cliente_id>/testo/<path:nome_file>', methods=['GET'])
@login_required
def trascrizioni_cliente_testo(cliente_id, nome_file):
    """Legge il testo di una trascrizione cliente."""
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB
    import urllib.parse

    try:
        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'})

        base_path = get_cliente_base_path(dict(cliente))
        nome_decodificato = urllib.parse.unquote(nome_file)
        file_path = base_path / 'trascrizioni' / nome_decodificato

        # Sicurezza: verifica che il file sia dentro la cartella trascrizioni
        if not str(file_path.resolve()).startswith(str((base_path / 'trascrizioni').resolve())):
            return jsonify({'success': False, 'error': 'Percorso non valido'})

        if not file_path.exists():
            return jsonify({'success': False, 'error': 'File non trovato'})

        testo = file_path.read_text(encoding='utf-8')
        return jsonify({'success': True, 'nome': file_path.stem, 'testo': testo})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@trascrizione_bp.route('/cliente/<int:cliente_id>/scarica/<path:nome_file>', methods=['GET'])
@login_required
def trascrizioni_cliente_scarica(cliente_id, nome_file):
    """Scarica file trascrizione cliente."""
    from flask import send_file
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB
    import urllib.parse

    try:
        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return "Cliente non trovato", 404

        base_path = get_cliente_base_path(dict(cliente))
        nome_decodificato = urllib.parse.unquote(nome_file)
        file_path = base_path / 'trascrizioni' / nome_decodificato

        if not str(file_path.resolve()).startswith(str((base_path / 'trascrizioni').resolve())):
            return "Percorso non valido", 403

        if not file_path.exists():
            return "File non trovato", 404

        return send_file(str(file_path), as_attachment=True, download_name=file_path.name)

    except Exception as e:
        return f"Errore: {e}", 500


@trascrizione_bp.route('/cliente/<int:cliente_id>/elimina/<path:nome_file>', methods=['DELETE'])
@login_required
def trascrizioni_cliente_elimina(cliente_id, nome_file):
    """Elimina una trascrizione dalla cartella cliente."""
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB
    import urllib.parse

    try:
        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'})

        base_path = get_cliente_base_path(dict(cliente))
        nome_decodificato = urllib.parse.unquote(nome_file)
        file_path = base_path / 'trascrizioni' / nome_decodificato

        if not str(file_path.resolve()).startswith(str((base_path / 'trascrizioni').resolve())):
            return jsonify({'success': False, 'error': 'Percorso non valido'})

        if not file_path.exists():
            return jsonify({'success': False, 'error': 'File non trovato'})

        file_path.unlink()
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# ROUTE: Rinomina file trascrizione cliente
# ==============================================================================

@trascrizione_bp.route('/cliente/<int:cliente_id>/rinomina-file', methods=['POST'])
@login_required
def trascrizioni_cliente_rinomina_file(cliente_id):
    """Rinomina un file trascrizione nella cartella cliente."""
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB
    import urllib.parse
    import re

    try:
        data = request.get_json()
        nome_vecchio = data.get('nome_vecchio', '')
        nome_nuovo = data.get('nome_nuovo', '').strip()

        if not nome_vecchio or not nome_nuovo:
            return jsonify({'success': False, 'error': 'Nome non valido'})

        # Sanitizza il nuovo nome
        nome_nuovo = re.sub(r'[<>:"/\\|?*]', '_', nome_nuovo)
        if not nome_nuovo.lower().endswith('.txt'):
            nome_nuovo += '.txt'

        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'})

        base_path = get_cliente_base_path(dict(cliente))
        trascrizioni_dir = base_path / 'trascrizioni'

        nome_decodificato = urllib.parse.unquote(nome_vecchio)
        file_vecchio = trascrizioni_dir / nome_decodificato
        file_nuovo = trascrizioni_dir / nome_nuovo

        # Validazione sicurezza path
        if not str(file_vecchio.resolve()).startswith(str(trascrizioni_dir.resolve())):
            return jsonify({'success': False, 'error': 'Percorso non valido'})
        if not str(file_nuovo.resolve()).startswith(str(trascrizioni_dir.resolve())):
            return jsonify({'success': False, 'error': 'Percorso non valido'})

        if not file_vecchio.exists():
            return jsonify({'success': False, 'error': 'File non trovato'})

        if file_nuovo.exists() and file_nuovo != file_vecchio:
            return jsonify({'success': False, 'error': 'Esiste gia\' un file con questo nome'})

        file_vecchio.rename(file_nuovo)

        # Rinomina anche eventuale file audio associato
        for ext in ['.aac', '.mp3', '.m4a', '.wav', '.ogg', '.opus', '.wma', '.flac']:
            audio_vecchio = file_vecchio.with_suffix(ext)
            if audio_vecchio.exists():
                audio_nuovo = file_nuovo.with_suffix(ext)
                audio_vecchio.rename(audio_nuovo)
                break

        return jsonify({'success': True, 'nuovo_nome': nome_nuovo})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# ROUTE: Modifica testo trascrizione cliente
# ==============================================================================

@trascrizione_bp.route('/cliente/<int:cliente_id>/modifica/<path:nome_file>', methods=['POST'])
@login_required
def trascrizioni_cliente_modifica(cliente_id, nome_file):
    """Modifica e salva il testo di una trascrizione."""
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB
    import urllib.parse

    try:
        data = request.get_json()
        testo_nuovo = data.get('testo', '')

        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'})

        base_path = get_cliente_base_path(dict(cliente))
        nome_decodificato = urllib.parse.unquote(nome_file)
        file_path = base_path / 'trascrizioni' / nome_decodificato

        # Validazione sicurezza path
        if not str(file_path.resolve()).startswith(str((base_path / 'trascrizioni').resolve())):
            return jsonify({'success': False, 'error': 'Percorso non valido'})

        if not file_path.exists():
            return jsonify({'success': False, 'error': 'File non trovato'})

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(testo_nuovo)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# ROUTE: Cerca nel testo delle trascrizioni cliente
# ==============================================================================

@trascrizione_bp.route('/cliente/<int:cliente_id>/cerca', methods=['GET'])
@login_required
def trascrizioni_cliente_cerca(cliente_id):
    """Cerca nel testo di tutte le trascrizioni del cliente."""
    from app.config import get_cliente_base_path, DB_FILE as MAIN_DB
    import urllib.parse

    try:
        query = request.args.get('q', '').strip().lower()
        if not query:
            return jsonify({'success': False, 'error': 'Query vuota'})

        conn = sqlite3.connect(str(MAIN_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clienti WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        conn.close()

        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'})

        base_path = get_cliente_base_path(dict(cliente))
        trascrizioni_dir = base_path / 'trascrizioni'

        if not trascrizioni_dir.exists():
            return jsonify({'success': True, 'files': []})

        risultati = []
        for f in sorted(trascrizioni_dir.iterdir(), reverse=True):
            if f.suffix.lower() != '.txt':
                continue
            try:
                contenuto = f.read_text(encoding='utf-8').lower()
                if query in contenuto:
                    stat = f.stat()
                    dim = stat.st_size
                    if dim < 1024:
                        dim_str = f"{dim} B"
                    else:
                        dim_str = f"{dim / 1024:.1f} KB"

                    from datetime import datetime
                    data_mod = datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M')

                    risultati.append({
                        'nome': f.name,
                        'nome_display': f.name,
                        'nome_codificato': urllib.parse.quote(f.name, safe=''),
                        'data': data_mod,
                        'dimensione': dim_str
                    })
            except Exception:
                continue

        return jsonify({'success': True, 'files': risultati})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==============================================================================
# ROUTE: Elimina job in coda (non ancora elaborato)
# ==============================================================================

@trascrizione_bp.route('/elimina-coda/<int:job_id>', methods=['POST'])
@login_required
def elimina_job_coda(job_id):
    """
    Elimina un job ancora in attesa dalla coda.
    Solo il proprietario o admin possono eliminare.
    Rimuove anche il file audio dalla cartella attesa.
    """
    from app.config_trascrizione import DIR_ATTESA

    user_id = session['user_id']
    ruolo = session.get('ruolo_base', 'viewer')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, utente_id, nome_file_sistema, stato
        FROM coda_trascrizioni WHERE id = ?
    ''', (job_id,))

    job = cursor.fetchone()

    if not job:
        conn.close()
        return jsonify({'success': False, 'error': 'Job non trovato'}), 404

    if job['stato'] != 'attesa':
        conn.close()
        return jsonify({'success': False, 'error': 'Solo job in attesa possono essere eliminati'}), 400

    if job['utente_id'] != user_id and ruolo != 'admin':
        conn.close()
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

    # Elimina file audio dalla cartella attesa
    nome_sistema = job['nome_file_sistema']
    file_attesa = DIR_ATTESA / nome_sistema
    if file_attesa.exists():
        file_attesa.unlink()

    # Segna come eliminato nel DB
    cursor.execute('''
        UPDATE coda_trascrizioni SET stato = 'eliminato' WHERE id = ?
    ''', (job_id,))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'messaggio': 'Job rimosso dalla coda'})
