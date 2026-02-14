# -*- coding: utf-8 -*-
"""
==============================================================================
ROUTES TOP PROSPECT - Blueprint Flask
==============================================================================
Versione: 1.0.0
Data: 2026-01-29
Descrizione: Route HTTP per il modulo Top Prospect

Route disponibili:
    GET  /top-prospect                     - Pagina principale
    GET  /top-prospect/api/candidati       - API lista candidati
    GET  /top-prospect/api/confermati      - API lista confermati
    GET  /top-prospect/api/archiviati      - API lista archiviati
    GET  /top-prospect/api/conteggi        - API conteggi per badge
    GET  /top-prospect/api/appuntamenti    - API prossimi appuntamenti (banner)
    POST /top-prospect/api/conferma/<id>   - API conferma candidato
    POST /top-prospect/api/archivia/<id>   - API archivia top prospect
    POST /top-prospect/api/ripristina/<id> - API ripristina da archivio
    POST /top-prospect/api/scarta/<id>     - API scarta candidato
    POST /top-prospect/api/priorita/<id>   - API modifica priorita
    POST /top-prospect/api/analizza        - API esegue analisi candidati
    GET  /top-prospect/api/<id>/storico    - API storico attivita
    GET  /top-prospect/api/<id>/note       - API lista note
    POST /top-prospect/api/<id>/note/crea  - API crea nota
    POST /top-prospect/api/<id>/note/<nid>/modifica - API modifica nota
    POST /top-prospect/api/<id>/note/<nid>/elimina  - API elimina nota
    GET  /top-prospect/api/<id>/appuntamenti       - API lista appuntamenti
    POST /top-prospect/api/<id>/appuntamenti/crea  - API crea appuntamento
    POST /top-prospect/api/<id>/appuntamenti/<aid>/modifica - API modifica appuntamento
    POST /top-prospect/api/<id>/appuntamenti/<aid>/completa - API segna completato
==============================================================================
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import sqlite3
import os
import json
import uuid
from pathlib import Path
from functools import wraps
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename

# Import moduli locali
from app.config import DB_FILE, CLIENTI_PIVA_DIR, CLIENTI_CF_DIR
from app.config_top_prospect import (
    PARAMETRI_CANDIDATURA,
    LIVELLI_PRIORITA,
    PRIORITA_DEFAULT,
    COLONNE_GRIGLIA,
    COLONNE_GRIGLIA_CANDIDATI,
    APPUNTAMENTI_BANNER_LIMIT,
    APPUNTAMENTI_GIORNI_AVANTI,
    PERMESSO_VISUALIZZA_TOP_PROSPECT,
    get_parametri_candidatura,
    get_livello_priorita,
    get_icona_stato
)
from app.motore_top_prospect import (
    esegui_analisi_candidati,
    conferma_top_prospect,
    archivia_top_prospect,
    ripristina_top_prospect,
    aggiorna_priorita,
    scarta_candidato,
    get_candidati,
    get_top_prospect_confermati,
    get_top_prospect_archiviati,
    get_stato_top_prospect_cliente,
    get_storico_attivita,
    get_prossimi_appuntamenti,
    get_conteggi_top_prospect,
    calcola_variazione_percentuale
)

# Import connettore notifiche
try:
    from app.connettori_notifiche.top_prospect import (
        notifica_top_prospect_confermato
    )
    _NOTIFICHE_TP = True
except ImportError:
    _NOTIFICHE_TP = False
from app.database_utenti import get_subordinati, get_utente_by_id, ha_permesso
from app.connettori_stato_cliente import get_car_policy_singolo
from app.google_calendar import get_calendar_service, get_hex_colore, COLORI_CALENDARIO
from app.gestione_commerciali import get_info_commerciale_bulk

# ==============================================================================
# BLUEPRINT
# ==============================================================================

top_prospect_bp = Blueprint('top_prospect', __name__, url_prefix='/top-prospect')


# ==============================================================================
# DECORATORI
# ==============================================================================

def login_required(f):
    """Richiede autenticazione"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Richiede ruolo admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('ruolo_base') != 'admin':
            return jsonify({'success': False, 'error': 'Accesso riservato agli amministratori'}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_db():
    """Restituisce connessione database"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_user_id():
    """Restituisce ID utente corrente"""
    return session.get('user_id', 0)


def puo_vedere_top_prospect(conn, user_id):
    """
    Verifica se l'utente puo vedere la pagina Top Prospect.
    Possono vedere:
    - Admin
    - Commerciali
    - Operatori con permesso specifico
    """
    ruolo = session.get('ruolo_base', '')
    
    if ruolo == 'admin':
        return True
    
    if ruolo == 'commerciale':
        return True
    
    # Operatori/Viewer solo con permesso specifico
    return ha_permesso(conn, user_id, PERMESSO_VISUALIZZA_TOP_PROSPECT)


def puo_accedere_cliente(conn, user_id, cliente_id):
    """
    Verifica se l'utente puo accedere ai dettagli di un cliente.
    - Admin: sempre
    - Commerciali: solo clienti propri o dei subordinati
    - Operatori esterni: mai (anche con permesso visualizza)
    """
    ruolo = session.get('ruolo_base', '')
    
    if ruolo == 'admin':
        return True
    
    if ruolo != 'commerciale':
        return False
    
    # Verifica se il cliente e assegnato all'utente o ai suoi subordinati
    subordinati = get_subordinati(conn, user_id)
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT commerciale_id FROM clienti 
        WHERE id = ?
    ''', (cliente_id,))
    
    row = cursor.fetchone()
    if row and row[0] in subordinati:
        return True
    
    return False


# ==============================================================================
# HELPER - APPUNTAMENTI GOOGLE CALENDAR
# ==============================================================================

def get_appuntamenti_google_calendar(conn, giorni=28):
    """
    Recupera gli appuntamenti da Google Calendar e li arricchisce con info commerciali.
    
    Args:
        conn: Connessione database
        giorni: Numero giorni in avanti da considerare
        
    Returns:
        Lista di appuntamenti con info commerciale
    """
    try:
        # Leggi eventi da Google Calendar
        calendar_service = get_calendar_service()
        eventi = calendar_service.get_eventi(max_results=50)
        
        if not eventi:
            return []
        
        # Carica mappa colore -> commerciale dal database
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, cognome, colore_calendario
            FROM utenti
            WHERE colore_calendario IS NOT NULL
        ''')
        
        mappa_colori = {}
        for row in cursor.fetchall():
            if row[3]:  # colore_calendario
                mappa_colori[row[3]] = {
                    'id': row[0],
                    'nome': row[1],
                    'cognome': row[2],
                    'nome_completo': f"{row[1]} {row[2]}"
                }
        
        # Arricchisci eventi con info commerciale
        appuntamenti = []
        for evento in eventi:
            colore_id = evento.get('colore_id')
            commerciale = mappa_colori.get(colore_id, {})
            
            # Formatta data per visualizzazione
            data_raw = evento.get('data', '')
            try:
                data_obj = datetime.strptime(data_raw, '%Y-%m-%d')
                data_formattata = data_obj.strftime('%d/%m')
            except:
                data_formattata = data_raw
            
            appuntamenti.append({
                'id': evento.get('id'),
                'titolo': evento.get('titolo', ''),
                'descrizione': evento.get('descrizione', ''),
                'data': data_raw,
                'data_formattata': data_formattata,
                'ora': evento.get('ora', ''),
                'colore_id': colore_id,
                'colore_hex': get_hex_colore(colore_id) if colore_id else '#6c757d',
                'commerciale_id': commerciale.get('id'),
                'commerciale_nome': commerciale.get('nome', ''),
                'link': evento.get('link', ''),
            })
        
        return appuntamenti
        
    except Exception as e:
        print(f"Errore lettura Google Calendar: {e}")
        return []


# ==============================================================================
# ROUTE PAGINA PRINCIPALE
# ==============================================================================

@top_prospect_bp.route('/')
@login_required
def pagina_principale():
    """Pagina principale Top Prospect"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Verifica permessi
        if not puo_vedere_top_prospect(conn, user_id):
            return redirect(url_for('index'))
        
        # Conteggi per badge
        conteggi = get_conteggi_top_prospect(conn)
        
        # Prossimi appuntamenti da Google Calendar
        appuntamenti = get_appuntamenti_google_calendar(conn, giorni=28)
        
        # Parametri correnti (per info admin)
        parametri = get_parametri_candidatura()
        
        # Verifica se e admin (per azioni speciali)
        is_admin = session.get('ruolo_base') == 'admin'
        
        # Link calendario Google (Top Prospect BR Car Service)
        calendario_url = "https://calendar.google.com/calendar/u/0?cid=NzgwNjMzNGFjYTdjODk5YzA2OThiMjIyODhhNDJhNDViYThkNDYxODYzZjVlZWY1YTlkOTdmMjkwZDUyYWNlZEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t"
        
        return render_template(
            'top_prospect.html',
            conteggi=conteggi,
            appuntamenti=appuntamenti,
            parametri=parametri,
            livelli_priorita=LIVELLI_PRIORITA,
            colonne_griglia=COLONNE_GRIGLIA,
            colonne_candidati=COLONNE_GRIGLIA_CANDIDATI,
            is_admin=is_admin,
            calendario_url=calendario_url
        )
    finally:
        conn.close()


# ==============================================================================
# API - LISTE
# ==============================================================================

@top_prospect_bp.route('/api/candidati')
@login_required
def api_candidati():
    """API lista candidati"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        if not puo_vedere_top_prospect(conn, user_id):
            return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
        
        candidati = get_candidati(conn)
        
        # Recupera info commerciali in bulk (funzione centralizzata)
        cliente_ids = [c.get('cliente_id') for c in candidati if c.get('cliente_id')]
        info_commerciali = get_info_commerciale_bulk(conn, cliente_ids)
        
        # Arricchisci con dati calcolati
        for c in candidati:
            # Variazioni percentuali
            c['var_valore_prod'] = calcola_variazione_percentuale(
                c.get('valore_produzione'), 
                c.get('valore_produzione_prec')
            )
            c['var_patrimonio'] = calcola_variazione_percentuale(
                c.get('patrimonio_netto'), 
                c.get('patrimonio_netto_prec')
            )
            
            # Flotta (max tra DB e rilevati)
            veicoli_db = c.get('num_veicoli', 0) or 0
            veicoli_riv = c.get('veicoli_rilevati', 0) or 0
            c['flotta'] = max(veicoli_db, veicoli_riv)
            
            # Nome visualizzato
            c['nome_display'] = c.get('ragione_sociale') or c.get('nome_cliente') or 'N/D'
            
            # Car Policy flag
            cliente_dict = {
                'id': c.get('cliente_id'),
                'p_iva': c.get('p_iva'),
                'cod_fiscale': c.get('cod_fiscale')
            }
            car_policy = get_car_policy_singolo(conn, cliente_dict)
            c['has_car_policy'] = car_policy.get('presente', False)
            
            # Info commerciale (da funzione centralizzata)
            comm_info = info_commerciali.get(c.get('cliente_id'))
            if comm_info:
                c['commerciale_nome'] = comm_info['display']
                c['commerciale_colore_hex'] = comm_info['colore_hex']
            else:
                c['commerciale_nome'] = 'N/D'
                c['commerciale_colore_hex'] = None
            
            # Permesso accesso link
            c['puo_accedere'] = puo_accedere_cliente(conn, user_id, c.get('cliente_id'))
        
        return jsonify({'success': True, 'candidati': candidati})
    finally:
        conn.close()


@top_prospect_bp.route('/api/confermati')
@login_required
def api_confermati():
    """API lista Top Prospect confermati"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        if not puo_vedere_top_prospect(conn, user_id):
            return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
        
        # Filtro priorita opzionale
        filtro_priorita = request.args.get('priorita', type=int)
        
        confermati = get_top_prospect_confermati(conn, filtro_priorita)
        
        # Recupera info commerciali in bulk (funzione centralizzata)
        cliente_ids = [tp.get('cliente_id') for tp in confermati if tp.get('cliente_id')]
        info_commerciali = get_info_commerciale_bulk(conn, cliente_ids)
        
        # Arricchisci con dati calcolati
        for tp in confermati:
            # Flotta (max tra DB e rilevati)
            veicoli_db = tp.get('num_veicoli', 0) or 0
            veicoli_riv = tp.get('veicoli_rilevati', 0) or 0
            tp['flotta'] = max(veicoli_db, veicoli_riv)
            
            # Nome visualizzato
            tp['nome_display'] = tp.get('ragione_sociale') or tp.get('nome_cliente') or 'N/D'
            
            # Livello priorita con colori
            tp['priorita_config'] = get_livello_priorita(tp.get('priorita', PRIORITA_DEFAULT))
            
            # Car Policy flag
            cliente_dict = {
                'id': tp.get('cliente_id'),
                'p_iva': tp.get('p_iva'),
                'cod_fiscale': tp.get('cod_fiscale')
            }
            car_policy = get_car_policy_singolo(conn, cliente_dict)
            tp['has_car_policy'] = car_policy.get('presente', False)
            
            # Info commerciale (da funzione centralizzata)
            comm_info = info_commerciali.get(tp.get('cliente_id'))
            if comm_info:
                tp['commerciale_nome'] = comm_info['display']
                tp['commerciale_colore_hex'] = comm_info['colore_hex']
            else:
                tp['commerciale_nome'] = 'N/D'
                tp['commerciale_colore_hex'] = None
            
            # Permesso accesso link
            tp['puo_accedere'] = puo_accedere_cliente(conn, user_id, tp.get('cliente_id'))
        
        return jsonify({'success': True, 'confermati': confermati})
    finally:
        conn.close()


@top_prospect_bp.route('/api/archiviati')
@login_required
def api_archiviati():
    """API lista Top Prospect archiviati"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        if not puo_vedere_top_prospect(conn, user_id):
            return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
        
        
        archiviati = get_top_prospect_archiviati(conn)
        
        for tp in archiviati:
            tp['nome_display'] = tp.get('ragione_sociale') or tp.get('nome_cliente') or 'N/D'
        
        return jsonify({'success': True, 'archiviati': archiviati})
    finally:
        conn.close()


@top_prospect_bp.route('/api/conteggi')
@login_required
def api_conteggi():
    """API conteggi per badge"""
    conn = get_db()
    
    try:
        conteggi = get_conteggi_top_prospect(conn)
        return jsonify({'success': True, 'conteggi': conteggi})
    finally:
        conn.close()


@top_prospect_bp.route('/api/appuntamenti')
@login_required
def api_appuntamenti_banner():
    """API prossimi appuntamenti per banner"""
    conn = get_db()
    
    try:
        appuntamenti = get_prossimi_appuntamenti(
            conn,
            limite=APPUNTAMENTI_BANNER_LIMIT,
            giorni=APPUNTAMENTI_GIORNI_AVANTI
        )
        return jsonify({'success': True, 'appuntamenti': appuntamenti})
    finally:
        conn.close()


# ==============================================================================
# API - AZIONI SU CANDIDATI/TOP PROSPECT
# ==============================================================================

@top_prospect_bp.route('/api/conferma/<int:tp_id>', methods=['POST'])
@login_required
@admin_required
def api_conferma(tp_id):
    """Conferma un candidato come Top Prospect"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        priorita = data.get('priorita', PRIORITA_DEFAULT)
        note = data.get('note', '')
        
        success = conferma_top_prospect(conn, tp_id, user_id, priorita, note)

        # Notifica conferma
        if success and _NOTIFICHE_TP:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.denominazione FROM top_prospect tp
                    JOIN clienti c ON c.id = tp.cliente_id
                    WHERE tp.id = ?
                ''', (tp_id,))
                row = cursor.fetchone()
                nome = row[0] if row else 'Cliente'
                notifica_top_prospect_confermato(conn, nome)
            except Exception:
                pass
        
        if success:
            return jsonify({'success': True, 'message': 'Top Prospect confermato'})
        else:
            return jsonify({'success': False, 'error': 'Impossibile confermare'}), 400
    finally:
        conn.close()


@top_prospect_bp.route('/api/archivia/<int:tp_id>', methods=['POST'])
@login_required
@admin_required
def api_archivia(tp_id):
    """Archivia un Top Prospect"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        note = data.get('note', '')
        
        success = archivia_top_prospect(conn, tp_id, user_id, note)
        
        if success:
            return jsonify({'success': True, 'message': 'Top Prospect archiviato'})
        else:
            return jsonify({'success': False, 'error': 'Impossibile archiviare'}), 400
    finally:
        conn.close()


@top_prospect_bp.route('/api/ripristina/<int:tp_id>', methods=['POST'])
@login_required
@admin_required
def api_ripristina(tp_id):
    """Ripristina un Top Prospect da archivio"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        success = ripristina_top_prospect(conn, tp_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Top Prospect ripristinato'})
        else:
            return jsonify({'success': False, 'error': 'Impossibile ripristinare'}), 400
    finally:
        conn.close()


@top_prospect_bp.route('/api/scarta/<int:tp_id>', methods=['POST'])
@login_required
@admin_required
def api_scarta(tp_id):
    """Scarta un candidato"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        note = data.get('note', '')
        
        success = scarta_candidato(conn, tp_id, user_id, note)
        
        if success:
            return jsonify({'success': True, 'message': 'Candidato scartato'})
        else:
            return jsonify({'success': False, 'error': 'Impossibile scartare'}), 400
    finally:
        conn.close()


@top_prospect_bp.route('/api/priorita/<int:tp_id>', methods=['POST'])
@login_required
@admin_required
def api_priorita(tp_id):
    """Modifica priorita di un Top Prospect"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        nuova_priorita = data.get('priorita')
        
        if nuova_priorita is None:
            return jsonify({'success': False, 'error': 'Priorita non specificata'}), 400
        
        success = aggiorna_priorita(conn, tp_id, int(nuova_priorita), user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Priorita aggiornata'})
        else:
            return jsonify({'success': False, 'error': 'Impossibile aggiornare priorita'}), 400
    finally:
        conn.close()


@top_prospect_bp.route('/api/analizza', methods=['POST'])
@login_required
@admin_required
def api_analizza():
    """Esegue analisi candidati"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        risultato = esegui_analisi_candidati(conn, user_id)
        
        return jsonify({
            'success': True,
            'totale_analizzati': risultato['totale_analizzati'],
            'nuovi_candidati': risultato['totale_candidati'],
            'data_esecuzione': risultato['data_esecuzione']
        })
    finally:
        conn.close()


# ==============================================================================
# API - STORICO ATTIVITA
# ==============================================================================

@top_prospect_bp.route('/api/<int:tp_id>/storico')
@login_required
def api_storico(tp_id):
    """API storico attivita di un Top Prospect"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        if not puo_vedere_top_prospect(conn, user_id):
            return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
        
        storico = get_storico_attivita(conn, tp_id)
        
        return jsonify({'success': True, 'storico': storico})
    finally:
        conn.close()


# ==============================================================================
# API - NOTE TOP PROSPECT
# ==============================================================================

@top_prospect_bp.route('/api/<int:tp_id>/note')
@login_required
def api_note_lista(tp_id):
    """API lista note di un Top Prospect"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        if not puo_vedere_top_prospect(conn, user_id):
            return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT n.*, u.cognome as autore_cognome
            FROM top_prospect_note n
            LEFT JOIN utenti u ON n.creato_da_id = u.id
            WHERE n.top_prospect_id = ? AND (n.eliminato = 0 OR n.eliminato IS NULL)
            ORDER BY n.fissata DESC, n.data_creazione DESC
        ''', (tp_id,))
        
        note = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'success': True, 'note': note})
    finally:
        conn.close()


@top_prospect_bp.route('/api/<int:tp_id>/note/crea', methods=['POST'])
@login_required
def api_nota_crea(tp_id):
    """Crea una nuova nota per un Top Prospect con possibilita di allegati"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Supporta sia JSON che form-data (per upload file)
        if request.content_type and 'multipart/form-data' in request.content_type:
            titolo = request.form.get('titolo', '').strip()
            testo = request.form.get('testo', '').strip()
            files = request.files.getlist('allegati')
        else:
            data = request.get_json() or {}
            titolo = data.get('titolo', '').strip()
            testo = data.get('testo', '').strip()
            files = []
        
        if not titolo:
            return jsonify({'success': False, 'error': 'Titolo obbligatorio'}), 400
        
        cursor = conn.cursor()
        
        # Recupera info cliente (piva o cf) dal Top Prospect
        cursor.execute('''
            SELECT c.p_iva, c.cod_fiscale, c.ragione_sociale
            FROM top_prospect tp
            JOIN clienti c ON tp.cliente_id = c.id
            WHERE tp.id = ?
        ''', (tp_id,))
        cliente_info = cursor.fetchone()
        
        if not cliente_info:
            return jsonify({'success': False, 'error': 'Top Prospect non trovato'}), 404
        
        piva = cliente_info[0]
        cf = cliente_info[1]
        
        # Gestisci upload file
        allegati_salvati = []
        if files:
            # Determina cartella cliente
            if piva:
                piva_clean = piva.upper().replace('IT', '').replace(' ', '').strip()
                cartella_cliente = Path(CLIENTI_PIVA_DIR) / piva_clean / 'top_prospect'
            elif cf:
                cartella_cliente = Path(CLIENTI_CF_DIR) / cf.upper().strip() / 'top_prospect'
            else:
                return jsonify({'success': False, 'error': 'Cliente senza P.IVA e CF'}), 400
            
            # Crea cartella se non esiste
            cartella_cliente.mkdir(parents=True, exist_ok=True)
            
            for file in files:
                if file and file.filename:
                    # Nome file sicuro con UUID per evitare collisioni
                    nome_originale = secure_filename(file.filename)
                    nome_base, estensione = os.path.splitext(nome_originale)
                    nome_univoco = f"{nome_base}_{uuid.uuid4().hex[:8]}{estensione}"
                    
                    percorso_file = cartella_cliente / nome_univoco
                    file.save(str(percorso_file))
                    
                    allegati_salvati.append({
                        'nome_originale': file.filename,
                        'nome_file': nome_univoco,
                        'percorso': str(percorso_file),
                        'dimensione': os.path.getsize(str(percorso_file)),
                        'data_upload': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        autore = session.get('cognome', session.get('username', 'Sistema'))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Converti allegati in JSON
        allegati_json = json.dumps(allegati_salvati) if allegati_salvati else None
        
        cursor.execute('''
            INSERT INTO top_prospect_note
            (top_prospect_id, titolo, testo, autore, creato_da_id, data_creazione, fissata, eliminato, allegati)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
        ''', (tp_id, titolo, testo or None, autore, user_id, now, allegati_json))
        
        nota_id = cursor.lastrowid
        
        # Registra attivita
        msg_allegati = f" con {len(allegati_salvati)} allegati" if allegati_salvati else ""
        cursor.execute('''
            INSERT INTO top_prospect_attivita
            (top_prospect_id, tipo_attivita, descrizione, utente_id, data_ora)
            VALUES (?, 'nota_creata', ?, ?, ?)
        ''', (tp_id, f"Nota creata: {titolo[:50]}{msg_allegati}", user_id, now))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'nota_id': nota_id,
            'allegati': len(allegati_salvati)
        })
    except Exception as e:
        print(f"Errore creazione nota: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


@top_prospect_bp.route('/api/<int:tp_id>/note/<int:nota_id>/allegato/<nome_file>')
@login_required
def api_scarica_allegato(tp_id, nota_id, nome_file):
    """Scarica un allegato di una nota"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        if not puo_vedere_top_prospect(conn, user_id):
            return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
        
        cursor = conn.cursor()
        
        # Recupera info nota e cliente
        cursor.execute('''
            SELECT n.allegati, c.p_iva, c.cod_fiscale
            FROM top_prospect_note n
            JOIN top_prospect tp ON n.top_prospect_id = tp.id
            JOIN clienti c ON tp.cliente_id = c.id
            WHERE n.id = ? AND n.top_prospect_id = ?
        ''', (nota_id, tp_id))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Nota non trovata'}), 404
        
        allegati_json, piva, cf = row
        
        if not allegati_json:
            return jsonify({'success': False, 'error': 'Nessun allegato'}), 404
        
        # Cerca il file negli allegati
        allegati = json.loads(allegati_json)
        file_trovato = None
        for a in allegati:
            if a.get('nome_file') == nome_file:
                file_trovato = a
                break
        
        if not file_trovato:
            return jsonify({'success': False, 'error': 'File non trovato'}), 404
        
        # Determina cartella
        if piva:
            piva_clean = piva.upper().replace('IT', '').replace(' ', '').strip()
            cartella = Path(CLIENTI_PIVA_DIR) / piva_clean / 'top_prospect'
        elif cf:
            cartella = Path(CLIENTI_CF_DIR) / cf.upper().strip() / 'top_prospect'
        else:
            return jsonify({'success': False, 'error': 'Percorso non valido'}), 404
        
        return send_from_directory(
            str(cartella),
            nome_file,
            as_attachment=True,
            download_name=file_trovato.get('nome_originale', nome_file)
        )
        
    except Exception as e:
        print(f"Errore download allegato: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


@top_prospect_bp.route('/api/<int:tp_id>/note/<int:nota_id>/modifica', methods=['POST'])
@login_required
def api_nota_modifica(tp_id, nota_id):
    """Modifica una nota con gestione allegati"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Supporta sia JSON che FormData
        if request.is_json:
            data = request.get_json() or {}
            titolo = data.get('titolo', '').strip()
            testo = data.get('testo', '').strip()
            fissata = data.get('fissata', 0)
            allegati_da_eliminare = []
            nuovi_files = []
        else:
            titolo = request.form.get('titolo', '').strip()
            testo = request.form.get('testo', '').strip()
            fissata = request.form.get('fissata', 0)
            try:
                fissata = int(fissata)
            except:
                fissata = 0
            # Lista allegati da eliminare
            allegati_da_eliminare_json = request.form.get('allegati_da_eliminare', '[]')
            try:
                allegati_da_eliminare = json.loads(allegati_da_eliminare_json)
            except:
                allegati_da_eliminare = []
            # Nuovi file
            nuovi_files = request.files.getlist('nuovi_allegati')
        
        if not titolo:
            return jsonify({'success': False, 'error': 'Titolo obbligatorio'}), 400
        
        cursor = conn.cursor()
        
        # Recupera allegati esistenti e info cliente
        cursor.execute('''
            SELECT n.allegati, c.p_iva, c.cod_fiscale
            FROM top_prospect_note n
            JOIN top_prospect tp ON n.top_prospect_id = tp.id
            JOIN clienti c ON tp.cliente_id = c.id
            WHERE n.id = ? AND n.top_prospect_id = ?
        ''', (nota_id, tp_id))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Nota non trovata'}), 404
        
        allegati_json_esistenti, piva, cf = row
        
        # Parse allegati esistenti
        allegati_attuali = []
        if allegati_json_esistenti:
            try:
                allegati_attuali = json.loads(allegati_json_esistenti)
            except:
                allegati_attuali = []
        
        # Determina cartella cliente
        if piva:
            piva_clean = piva.upper().replace('IT', '').replace(' ', '').strip()
            cartella_cliente = Path(CLIENTI_PIVA_DIR) / piva_clean / 'top_prospect'
        elif cf:
            cartella_cliente = Path(CLIENTI_CF_DIR) / cf.upper().strip() / 'top_prospect'
        else:
            cartella_cliente = None
        
        # Rimuovi allegati da eliminare
        allegati_aggiornati = []
        for a in allegati_attuali:
            if a.get('nome_file') not in allegati_da_eliminare:
                allegati_aggiornati.append(a)
            else:
                # Elimina file fisico
                if cartella_cliente:
                    percorso_file = cartella_cliente / a.get('nome_file')
                    if percorso_file.exists():
                        try:
                            percorso_file.unlink()
                        except:
                            pass  # Ignora errori di eliminazione
        
        # Aggiungi nuovi allegati
        if nuovi_files and cartella_cliente:
            cartella_cliente.mkdir(parents=True, exist_ok=True)
            
            for file in nuovi_files:
                if file and file.filename:
                    nome_originale = secure_filename(file.filename)
                    nome_base, estensione = os.path.splitext(nome_originale)
                    nome_univoco = f"{nome_base}_{uuid.uuid4().hex[:8]}{estensione}"
                    
                    percorso_file = cartella_cliente / nome_univoco
                    file.save(str(percorso_file))
                    
                    allegati_aggiornati.append({
                        'nome_originale': file.filename,
                        'nome_file': nome_univoco,
                        'percorso': str(percorso_file),
                        'dimensione': os.path.getsize(str(percorso_file)),
                        'data_upload': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        # Aggiorna nota nel database
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        allegati_json_nuovo = json.dumps(allegati_aggiornati) if allegati_aggiornati else None
        
        cursor.execute('''
            UPDATE top_prospect_note
            SET titolo = ?, testo = ?, fissata = ?, allegati = ?,
                modificato_da_id = ?, data_modifica = ?
            WHERE id = ? AND top_prospect_id = ?
        ''', (titolo, testo or None, fissata, allegati_json_nuovo, 
              user_id, now, nota_id, tp_id))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'allegati_rimossi': len(allegati_da_eliminare),
            'allegati_aggiunti': len(nuovi_files) if nuovi_files else 0,
            'allegati_totali': len(allegati_aggiornati)
        })
    except Exception as e:
        print(f"Errore modifica nota: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


@top_prospect_bp.route('/api/<int:tp_id>/note/<int:nota_id>/elimina', methods=['POST'])
@login_required
def api_nota_elimina(tp_id, nota_id):
    """Elimina (soft delete) una nota"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        eliminato_da = session.get('cognome', session.get('username', 'Sistema'))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE top_prospect_note
            SET eliminato = 1, data_eliminazione = ?, eliminato_da = ?
            WHERE id = ? AND top_prospect_id = ?
        ''', (now, eliminato_da, nota_id, tp_id))
        
        conn.commit()
        
        return jsonify({'success': True})
    finally:
        conn.close()


# ==============================================================================
# API - APPUNTAMENTI TOP PROSPECT
# ==============================================================================

@top_prospect_bp.route('/api/<int:tp_id>/appuntamenti')
@login_required
def api_appuntamenti_lista(tp_id):
    """API lista appuntamenti di un Top Prospect - legge da Google Calendar"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        if not puo_vedere_top_prospect(conn, user_id):
            return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
        
        cursor = conn.cursor()
        
        # Recupera nome azienda del Top Prospect
        cursor.execute('''
            SELECT c.ragione_sociale, c.nome_cliente
            FROM top_prospect tp
            JOIN clienti c ON tp.cliente_id = c.id
            WHERE tp.id = ?
        ''', (tp_id,))
        tp_info = cursor.fetchone()
        
        if not tp_info:
            return jsonify({'success': False, 'error': 'Top Prospect non trovato'}), 404
        
        nome_azienda = tp_info[1] or tp_info[0]  # nome_cliente o ragione_sociale
        
        # Prova a leggere da Google Calendar
        appuntamenti = []
        google_ok = False
        
        try:
            calendar_service = get_calendar_service()
            # Leggi eventi dei prossimi 365 giorni e ultimi 90 giorni
            data_inizio = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            data_fine = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
            
            eventi = calendar_service.get_eventi(
                data_inizio=data_inizio,
                data_fine=data_fine,
                max_results=100
            )
            
            # Filtra eventi per nome azienda
            for evento in eventi:
                if evento.get('titolo', '').strip().upper() == nome_azienda.strip().upper():
                    appuntamenti.append({
                        'id': evento.get('id'),
                        'google_event_id': evento.get('id'),
                        'data_appuntamento': evento.get('data', ''),
                        'ora_appuntamento': evento.get('ora', ''),
                        'tipo_appuntamento': 'google',
                        'note': evento.get('descrizione', ''),
                        'completato': 0,
                        'esito': None,
                        'fonte': 'google'
                    })
            
            google_ok = True
            
        except Exception as e:
            print(f"Errore lettura Google Calendar: {e}")
            # Fallback: leggi dal DB locale
            google_ok = False
        
        # Se Google Calendar non disponibile, usa DB locale
        if not google_ok:
            cursor.execute('''
                SELECT a.*, u.cognome as creato_da_cognome
                FROM top_prospect_appuntamenti a
                LEFT JOIN utenti u ON a.creato_da_id = u.id
                WHERE a.top_prospect_id = ?
                ORDER BY a.data_appuntamento DESC, a.ora_appuntamento DESC
            ''', (tp_id,))
            
            appuntamenti = [dict(row) for row in cursor.fetchall()]
            for app in appuntamenti:
                app['fonte'] = 'locale'
        
        # Ordina per data (piu' recenti prima)
        appuntamenti.sort(key=lambda x: (x.get('data_appuntamento', ''), x.get('ora_appuntamento', '')), reverse=True)
        
        return jsonify({
            'success': True, 
            'appuntamenti': appuntamenti,
            'fonte': 'google' if google_ok else 'locale'
        })
    finally:
        conn.close()


@top_prospect_bp.route('/api/<int:tp_id>/appuntamenti/crea', methods=['POST'])
@login_required
def api_appuntamento_crea(tp_id):
    """Crea un nuovo appuntamento su Google Calendar e nel DB locale"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        data_app = data.get('data_appuntamento', '').strip()
        ora_app = data.get('ora_appuntamento', '').strip()
        tipo = data.get('tipo_appuntamento', 'visita')
        note = data.get('note', '').strip()
        
        if not data_app:
            return jsonify({'success': False, 'error': 'Data obbligatoria'}), 400
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.cursor()
        
        # Recupera info Top Prospect (nome azienda, cliente_id)
        cursor.execute('''
            SELECT tp.id, tp.cliente_id, c.ragione_sociale, c.nome_cliente
            FROM top_prospect tp
            JOIN clienti c ON tp.cliente_id = c.id
            WHERE tp.id = ?
        ''', (tp_id,))
        tp_info = cursor.fetchone()
        
        if not tp_info:
            return jsonify({'success': False, 'error': 'Top Prospect non trovato'}), 404
        
        cliente_id = tp_info[1]
        nome_azienda = tp_info[3] or tp_info[2]  # nome_cliente o ragione_sociale
        
        # Recupera commerciale assegnato e il suo colore
        cursor.execute('''
            SELECT u.id, u.nome, u.colore_calendario
            FROM clienti c
            JOIN utenti u ON c.commerciale_id = u.id
            WHERE c.id = ?
        ''', (cliente_id,))
        comm_info = cursor.fetchone()
        
        colore_id = 1  # Default: Lavanda
        commerciale_nome = None
        if comm_info:
            commerciale_nome = comm_info[1]
            if comm_info[2]:
                colore_id = comm_info[2]
        
        # Calcola ora fine (default +1 ora)
        ora_inizio = ora_app if ora_app else '09:00'
        try:
            h, m = map(int, ora_inizio.split(':'))
            ora_fine = f"{(h+1) % 24:02d}:{m:02d}"
        except:
            ora_fine = '10:00'
        
        # Crea evento su Google Calendar
        google_event_id = None
        try:
            calendar_service = get_calendar_service()
            result = calendar_service.crea_evento(
                titolo=nome_azienda,
                data=data_app,
                ora_inizio=ora_inizio,
                ora_fine=ora_fine,
                descrizione=note or f"Appuntamento {tipo}",
                colore_id=colore_id
            )
            if result:
                google_event_id = result.get('id')
        except Exception as e:
            print(f"Errore creazione evento Google Calendar: {e}")
            # Continua comunque - salva nel DB locale
        
        # Salva nel DB locale
        cursor.execute('''
            INSERT INTO top_prospect_appuntamenti
            (top_prospect_id, data_appuntamento, ora_appuntamento, tipo_appuntamento,
             note, completato, sincronizzato_google, google_event_id, creato_da_id, data_creazione)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
        ''', (tp_id, data_app, ora_app or None, tipo, note or None, 
              1 if google_event_id else 0, google_event_id, user_id, now))
        
        app_id = cursor.lastrowid
        
        # Registra attivita
        cursor.execute('''
            INSERT INTO top_prospect_attivita
            (top_prospect_id, tipo_attivita, descrizione, utente_id, data_ora)
            VALUES (?, 'appuntamento_creato', ?, ?, ?)
        ''', (tp_id, f"Appuntamento {tipo} per il {data_app}" + 
              (f" (sync Google)" if google_event_id else ""), user_id, now))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'appuntamento_id': app_id,
            'google_event_id': google_event_id,
            'sincronizzato': google_event_id is not None
        })
    except Exception as e:
        print(f"Errore creazione appuntamento: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


@top_prospect_bp.route('/api/<int:tp_id>/appuntamenti/<int:app_id>/modifica', methods=['POST'])
@login_required
def api_appuntamento_modifica(tp_id, app_id):
    """Modifica un appuntamento"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        data_app = data.get('data_appuntamento', '').strip()
        ora_app = data.get('ora_appuntamento', '').strip()
        tipo = data.get('tipo_appuntamento', 'visita')
        note = data.get('note', '').strip()
        esito = data.get('esito', '').strip()
        
        if not data_app:
            return jsonify({'success': False, 'error': 'Data obbligatoria'}), 400
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE top_prospect_appuntamenti
            SET data_appuntamento = ?, ora_appuntamento = ?, tipo_appuntamento = ?,
                note = ?, esito = ?, modificato_da_id = ?, data_modifica = ?
            WHERE id = ? AND top_prospect_id = ?
        ''', (data_app, ora_app or None, tipo, note or None, esito or None, 
              user_id, now, app_id, tp_id))
        
        conn.commit()
        
        return jsonify({'success': True})
    finally:
        conn.close()


@top_prospect_bp.route('/api/<int:tp_id>/appuntamenti/<int:app_id>/completa', methods=['POST'])
@login_required
def api_appuntamento_completa(tp_id, app_id):
    """Segna un appuntamento come completato"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        esito = data.get('esito', '').strip()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE top_prospect_appuntamenti
            SET completato = 1, esito = ?, modificato_da_id = ?, data_modifica = ?
            WHERE id = ? AND top_prospect_id = ?
        ''', (esito or None, user_id, now, app_id, tp_id))
        
        # Registra attivita
        cursor.execute('''
            INSERT INTO top_prospect_attivita
            (top_prospect_id, tipo_attivita, descrizione, utente_id, data_ora)
            VALUES (?, 'appuntamento_completato', ?, ?, ?)
        ''', (tp_id, f"Appuntamento completato{': ' + esito[:50] if esito else ''}", user_id, now))
        
        conn.commit()
        
        return jsonify({'success': True})
    finally:
        conn.close()


# ==============================================================================
# API - STATO TOP PROSPECT PER CLIENTE (per indicatori)
# ==============================================================================

@top_prospect_bp.route('/api/cliente/<int:cliente_id>/stato')
@login_required
def api_stato_cliente(cliente_id):
    """Restituisce lo stato Top Prospect di un cliente"""
    conn = get_db()
    
    try:
        stato = get_stato_top_prospect_cliente(conn, cliente_id)
        
        if stato:
            return jsonify({'success': True, 'is_top_prospect': True, **stato})
        else:
            return jsonify({'success': True, 'is_top_prospect': False})
    finally:
        conn.close()


# ==============================================================================
# API - CANDIDATURA MANUALE
# ==============================================================================


# ==============================================================================
# API - CANDIDATURA MANUALE
# ==============================================================================

@top_prospect_bp.route('/api/cerca-clienti')
@login_required
def api_cerca_clienti():
    """API ricerca clienti per candidatura manuale - solo propri clienti"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 3:
            return jsonify({'success': True, 'clienti': []})
        
        # Ottieni lista clienti accessibili (propri + subordinati)
        subordinati = get_subordinati(conn, user_id)
        
        cursor = conn.cursor()
        search_pattern = f'%{query}%'
        
        # Costruisci filtro commerciale (admin vede tutti)
        # Admin vede tutti, altri solo propri clienti
        is_admin = session.get("ruolo_base") == "admin"
        if is_admin:
            filtro_commerciale = ""
            params = [search_pattern, search_pattern, search_pattern]
        elif subordinati:
            placeholders = ",".join(["?" for _ in subordinati])
            filtro_commerciale = f"AND (c.commerciale_id IN ({placeholders}) OR c.commerciale_id IS NULL)"
            params = [search_pattern, search_pattern, search_pattern] + list(subordinati)
        else:
            filtro_commerciale = "AND 1=0"  # Nessun accesso
            params = [search_pattern, search_pattern, search_pattern]
        
        cursor.execute(f'''
            SELECT c.id, 
                   COALESCE(c.ragione_sociale, c.nome_cliente) as nome,
                   c.p_iva, c.provincia, c.dipendenti, c.veicoli_rilevati,
                   (SELECT COUNT(*) FROM veicoli_attivi v WHERE v.cliente_id = c.id) as veicoli_db,
                   COALESCE(u.cognome, '') as commerciale,
                   (SELECT id FROM top_prospect tp WHERE tp.cliente_id = c.id AND tp.stato = 'confermato') as tp_confermato,
                   (SELECT id FROM top_prospect tp WHERE tp.cliente_id = c.id AND tp.stato = 'candidato') as tp_candidato
            FROM clienti c
            LEFT JOIN utenti u ON c.commerciale_id = u.id
            WHERE (c.nome_cliente LIKE ? OR c.ragione_sociale LIKE ? OR c.p_iva LIKE ?)
              {filtro_commerciale}
            ORDER BY COALESCE(c.ragione_sociale, c.nome_cliente)
            LIMIT 20
        ''', params)
        
        clienti = []
        for row in cursor.fetchall():
            veicoli = max(row['veicoli_db'] or 0, row['veicoli_rilevati'] or 0)
            clienti.append({
                'id': row['id'],
                'nome': row['nome'],
                'p_iva': row['p_iva'],
                'provincia': row['provincia'],
                'dipendenti': row['dipendenti'],
                'veicoli': veicoli,
                'commerciale': row['commerciale'],
                'is_top_prospect': row['tp_confermato'] is not None,
                'is_candidato': row['tp_candidato'] is not None
            })
        
        return jsonify({'success': True, 'clienti': clienti})
    finally:
        conn.close()


@top_prospect_bp.route('/api/candidatura-manuale', methods=['POST'])
@login_required
def api_candidatura_manuale():
    """Propone un cliente come Top Prospect (va nei candidati proposti)"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json() or {}
        cliente_id = data.get('cliente_id')
        note = data.get('note', '')
        
        if not cliente_id:
            return jsonify({'success': False, 'error': 'Cliente non specificato'}), 400
        
        # Verifica che il cliente sia accessibile all'utente
        if not puo_accedere_cliente(conn, user_id, cliente_id):
            return jsonify({'success': False, 'error': 'Non puoi proporre questo cliente'}), 403
        
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Verifica che il cliente esista
        cursor.execute('SELECT id, nome_cliente, ragione_sociale FROM clienti WHERE id = ?', (cliente_id,))
        cliente = cursor.fetchone()
        if not cliente:
            return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404
        
        # Verifica che non sia gia Top Prospect
        cursor.execute('SELECT id, stato FROM top_prospect WHERE cliente_id = ?', (cliente_id,))
        esistente = cursor.fetchone()
        if esistente:
            return jsonify({'success': False, 'error': f'Cliente gia presente come {esistente["stato"]}'}), 400
        
        # Inserisci come CANDIDATO (non confermato) con origine manuale
        cursor.execute('''
            INSERT INTO top_prospect 
            (cliente_id, stato, priorita, data_candidatura, origine,
             note_conferma, data_creazione, data_ultimo_aggiornamento)
            VALUES (?, 'candidato', 4, ?, 'manuale', ?, ?, ?)
        ''', (cliente_id, now, f'Proposto da utente: {note}' if note else 'Proposto manualmente', now, now))
        
        tp_id = cursor.lastrowid
        
        # Registra attivita
        nome_cliente = cliente['ragione_sociale'] or cliente['nome_cliente']
        cursor.execute('''
            INSERT INTO top_prospect_attivita
            (top_prospect_id, tipo_attivita, descrizione, utente_id, data_ora)
            VALUES (?, 'candidatura_manuale', ?, ?, ?)
        ''', (tp_id, f'Proposto manualmente come Top Prospect: {nome_cliente}', user_id, now))
        
        conn.commit()
        
        return jsonify({'success': True, 'top_prospect_id': tp_id})
    finally:
        conn.close()


@top_prospect_bp.route('/api/clienti-disponibili')
@login_required
def api_clienti_disponibili():
    """API lista clienti disponibili per candidatura manuale (precaricati)"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Admin vede tutti, altri solo propri clienti + subordinati
        is_admin = session.get('ruolo_base') == 'admin'
        
        cursor = conn.cursor()
        
        if is_admin:
            # Admin vede tutti i clienti
            cursor.execute('''
                SELECT c.id, 
                       COALESCE(c.ragione_sociale, c.nome_cliente) as nome,
                       c.p_iva, c.provincia, c.dipendenti, c.veicoli_rilevati,
                       (SELECT COUNT(*) FROM veicoli_attivi v WHERE v.cliente_id = c.id) as veicoli_db,
                       COALESCE(u.cognome, '') as commerciale,
                       (SELECT id FROM top_prospect tp WHERE tp.cliente_id = c.id AND tp.stato = 'confermato') as tp_confermato,
                       (SELECT id FROM top_prospect tp WHERE tp.cliente_id = c.id AND tp.stato = 'candidato') as tp_candidato
                FROM clienti c
                LEFT JOIN utenti u ON c.commerciale_id = u.id
                ORDER BY COALESCE(c.ragione_sociale, c.nome_cliente)
            ''')
        else:
            # Altri utenti: solo propri clienti + subordinati
            subordinati = get_subordinati(conn, user_id)
            if not subordinati:
                return jsonify({'success': True, 'clienti': []})
            
            placeholders = ','.join(['?' for _ in subordinati])
            cursor.execute(f'''
                SELECT c.id, 
                       COALESCE(c.ragione_sociale, c.nome_cliente) as nome,
                       c.p_iva, c.provincia, c.dipendenti, c.veicoli_rilevati,
                       (SELECT COUNT(*) FROM veicoli_attivi v WHERE v.cliente_id = c.id) as veicoli_db,
                       COALESCE(u.cognome, '') as commerciale,
                       (SELECT id FROM top_prospect tp WHERE tp.cliente_id = c.id AND tp.stato = 'confermato') as tp_confermato,
                       (SELECT id FROM top_prospect tp WHERE tp.cliente_id = c.id AND tp.stato = 'candidato') as tp_candidato
                FROM clienti c
                LEFT JOIN utenti u ON c.commerciale_id = u.id
                WHERE c.commerciale_id IN ({placeholders})
                ORDER BY COALESCE(c.ragione_sociale, c.nome_cliente)
            ''', subordinati)
        
        clienti = []
        for row in cursor.fetchall():
            veicoli = max(row['veicoli_db'] or 0, row['veicoli_rilevati'] or 0)
            clienti.append({
                'id': row['id'],
                'nome': row['nome'],
                'piva': row['p_iva'],
                'provincia': row['provincia'],
                'dipendenti': row['dipendenti'],
                'veicoli': veicoli,
                'commerciale': row['commerciale'],
                'is_top_prospect': row['tp_confermato'] is not None,
                'is_candidato': row['tp_candidato'] is not None
            })
        
        return jsonify({'success': True, 'clienti': clienti})
    finally:
        conn.close()


# ==============================================================================
# API - PARAMETRI CONFIGURAZIONE
# ==============================================================================

@top_prospect_bp.route('/api/parametri', methods=['GET'])
@login_required
def api_get_parametri():
    """Restituisce i parametri di configurazione Top Prospect"""
    conn = get_db()
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT chiave, valore FROM config_top_prospect')
        
        parametri = {}
        for row in cursor.fetchall():
            chiave = row['chiave']
            valore = row['valore']
            # Converti in numero se possibile
            if valore and valore.lstrip('-').isdigit():
                parametri[chiave] = int(valore)
            elif valore:
                parametri[chiave] = valore
            else:
                parametri[chiave] = None
        
        return jsonify({'success': True, 'parametri': parametri})
    finally:
        conn.close()


@top_prospect_bp.route('/api/parametri', methods=['POST'])
@login_required
@admin_required
def api_salva_parametri():
    """Salva i parametri di configurazione Top Prospect (solo admin)"""
    conn = get_db()
    
    try:
        data = request.get_json() or {}
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Mappa dei parametri da salvare
        parametri_validi = [
            'variazione_valore_produzione_min',
            'variazione_patrimonio_netto_min', 
            'dipendenti_min',
            'veicoli_min',
            'valore_produzione_min',
            'patrimonio_netto_min',
            'score_max'
        ]
        
        for chiave in parametri_validi:
            if chiave in data:
                valore = str(data[chiave]) if data[chiave] not in [None, ''] else ''
                cursor.execute('''
                    UPDATE config_top_prospect 
                    SET valore = ?, data_modifica = ?
                    WHERE chiave = ?
                ''', (valore, now, chiave))
        
        conn.commit()
        return jsonify({'success': True})
    finally:
        conn.close()


# ==============================================================================
# API - GESTIONE CONDIVISIONE CALENDARIO (SOLO ADMIN)
# ==============================================================================

@top_prospect_bp.route('/api/calendario/condivisioni')
@login_required
def api_calendario_lista_condivisioni():
    """API lista account con accesso al calendario (solo admin)"""
    if session.get('ruolo_base') != 'admin':
        return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
    
    try:
        calendar_service = get_calendar_service()
        result = calendar_service.lista_condivisioni()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@top_prospect_bp.route('/api/calendario/condividi', methods=['POST'])
@login_required
def api_calendario_condividi():
    """API condivide calendario con un account (solo admin)"""
    if session.get('ruolo_base') != 'admin':
        return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
    
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        ruolo = data.get('ruolo', 'reader')  # reader o writer
        
        if not email:
            return jsonify({'success': False, 'error': 'Email obbligatoria'}), 400
        
        # Valida formato email base
        if '@' not in email or '.' not in email:
            return jsonify({'success': False, 'error': 'Email non valida'}), 400
        
        calendar_service = get_calendar_service()
        result = calendar_service.condividi_calendario(email, ruolo)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@top_prospect_bp.route('/api/calendario/rimuovi-condivisione', methods=['POST'])
@login_required
def api_calendario_rimuovi_condivisione():
    """API rimuove accesso calendario a un account (solo admin)"""
    if session.get('ruolo_base') != 'admin':
        return jsonify({'success': False, 'error': 'Accesso non autorizzato'}), 403
    
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'error': 'Email obbligatoria'}), 400
        
        calendar_service = get_calendar_service()
        result = calendar_service.rimuovi_condivisione(email)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
