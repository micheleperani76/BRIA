# -*- coding: utf-8 -*-
"""
==============================================================================
ROUTES TRATTATIVE - Blueprint Flask
==============================================================================
Versione: 1.0
Data: 2026-01-27
Descrizione: Route HTTP per il modulo Trattative

Route disponibili:
    GET  /trattative                - Lista trattative (pagina principale)
    GET  /trattative/api/lista      - API lista trattative (JSON)
    GET  /trattative/api/<id>       - API dettaglio trattativa
    POST /trattative/api/crea       - API crea trattativa
    POST /trattative/api/<id>/modifica  - API modifica trattativa
    POST /trattative/api/<id>/avanzamento - API nuovo avanzamento
    POST /trattative/api/<id>/elimina    - API elimina trattativa
    GET  /trattative/api/clienti/search  - API ricerca clienti
==============================================================================
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from functools import wraps

# Import moduli locali
from app.config import DB_FILE
from app.config_trattative import (
    get_stati_chiusi,
    get_stati_dropdown,
    get_tipi_dropdown,
    get_tipologie_dropdown,
    get_noleggiatori_dropdown,
    get_colori_stati,
    get_percentuali_stati
)
from app.motore_trattative import (
    crea_trattativa,
    get_trattativa,
    get_trattative_cliente,
    modifica_trattativa,
    elimina_trattativa,
    ripristina_trattativa,
    aggiungi_avanzamento,
    get_avanzamenti,
    cerca_trattative,
    conta_per_stato,
    trattativa_appartiene_a,
    trattativa_cancellabile,
    riapri_trattativa
)
from app.database_utenti import get_subordinati, get_utente_by_id

# ==============================================================================
# BLUEPRINT
# ==============================================================================

trattative_bp = Blueprint('trattative', __name__, url_prefix='/trattative')


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


def get_db():
    """Restituisce connessione database"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_user_id():
    """Restituisce ID utente corrente"""
    return session.get('user_id', 0)


# ==============================================================================
# ROUTE PAGINA PRINCIPALE
# ==============================================================================

@trattative_bp.route('/')
@login_required
def lista_trattative():
    """Pagina principale lista trattative"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Dati per dropdown
        stati = get_stati_dropdown()
        tipi = get_tipi_dropdown()
        tipologie = get_tipologie_dropdown()
        noleggiatori = get_noleggiatori_dropdown()
        colori_stati = get_colori_stati()
        
        # Statistiche per badge
        stats_per_stato = conta_per_stato(conn, user_id)
        
        # Lista commerciali visibili (per filtro supervisore)
        subordinati_ids = get_subordinati(conn, user_id)
        commerciali = []
        for sub_id in subordinati_ids:
            utente = get_utente_by_id(conn, sub_id)
            if utente:
                commerciali.append({
                    'id': sub_id,
                    'nome': f"{utente.get('nome', '')} {utente.get('cognome', '')}"
                })
        
        # Clienti disponibili (propri e dei subordinati)
        placeholders = ",".join("?" * len(subordinati_ids))
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT DISTINCT c.id, COALESCE(c.ragione_sociale, c.nome_cliente) as ragione_sociale, COALESCE(c.p_iva, c.cod_fiscale) as p_iva, c.commerciale_id
            FROM clienti c
            
            WHERE c.commerciale_id IN ({placeholders})
            ORDER BY COALESCE(c.ragione_sociale, c.nome_cliente) COLLATE NOCASE
        """, subordinati_ids)
        clienti_disponibili = [dict(row) for row in cursor.fetchall()]
        
        # Clienti con trattative (per filtro)
        cursor.execute("""
            SELECT DISTINCT c.id, COALESCE(c.ragione_sociale, c.nome_cliente) as ragione_sociale,
                   COALESCE(c.p_iva, c.cod_fiscale) as p_iva
            FROM clienti c
            INNER JOIN trattative t ON c.id = t.cliente_id
            ORDER BY COALESCE(c.ragione_sociale, c.nome_cliente) COLLATE NOCASE
        """)
        clienti_con_trattative = [dict(row) for row in cursor.fetchall()]
        
        # Parametri da URL per precompilare modal (da scheda cliente)
        precompila_cliente_id = request.args.get('cliente_id', type=int)
        precompila_commerciale_id = request.args.get('commerciale_id', type=int)
        apri_modal = request.args.get('apri_modal') == '1'
        
        return render_template(
            'trattative.html',
            stati=stati,
            tipi=tipi,
            tipologie=tipologie,
            noleggiatori=noleggiatori,
            colori_stati=colori_stati,
            stats_per_stato=stats_per_stato,
            stati_chiusi=get_stati_chiusi(),
            commerciali=commerciali,
            clienti_disponibili=clienti_disponibili,
            clienti_con_trattative=clienti_con_trattative,
            mostra_filtro_commerciale=len(subordinati_ids) > 1,
            precompila_cliente_id=precompila_cliente_id,
            precompila_commerciale_id=precompila_commerciale_id,
            apri_modal=apri_modal
        )
    finally:
        conn.close()


# ==============================================================================
# API - LISTA TRATTATIVE
# ==============================================================================

@trattative_bp.route('/api/lista')
@login_required
def api_lista():
    """API lista trattative con filtri"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Parametri filtro da query string
        filtri = {}
        
        if request.args.get('stato'):
            filtri['stato'] = request.args.get('stato')
        
        if request.args.get('noleggiatore'):
            filtri['noleggiatore'] = request.args.get('noleggiatore')
        
        if request.args.get('cliente_search'):
            filtri['cliente_search'] = request.args.get('cliente_search')
        
        if request.args.get('cliente_id'):
            filtri['cliente_id'] = int(request.args.get('cliente_id'))
        
        if request.args.get('commerciale_id'):
            filtri['commerciale_id'] = int(request.args.get('commerciale_id'))
        
        if request.args.get('data_da'):
            filtri['data_da'] = request.args.get('data_da')
        
        if request.args.get('data_a'):
            filtri['data_a'] = request.args.get('data_a')
        
        if request.args.get('solo_aperte') == '1':
            filtri['solo_aperte'] = True
        if request.args.get('solo_chiuse') == '1':
            filtri['solo_chiuse'] = True
        
        # Paginazione
        limite = int(request.args.get('limite', 50))
        offset = int(request.args.get('offset', 0))
        
        # Esegui ricerca
        trattative_rows, totale = cerca_trattative(conn, filtri, user_id, limite, offset)
        trattative = [dict(t) for t in trattative_rows]
        
        # Verifica se utente e' admin
        is_admin = session.get('ruolo_base') == 'admin'
        
        # Aggiungi colori stati
        colori = get_colori_stati()
        percentuali = get_percentuali_stati()
        for t in trattative:
            t['stato_colore'] = colori.get(t.get('stato', ''), '#6c757d')
            t['cancellabile'] = trattativa_cancellabile(conn, t['id'], is_admin=is_admin, stato=t.get('stato'))
            t['percentuale'] = percentuali.get(t.get('stato', ''), 0)
        
        return jsonify({
            'success': True,
            'trattative': trattative,
            'totale': totale,
            'limite': limite,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - DETTAGLIO TRATTATIVA
# ==============================================================================

@trattative_bp.route('/api/<int:trattativa_id>')
@login_required
def api_dettaglio(trattativa_id):
    """API dettaglio singola trattativa con avanzamenti"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Verifica permessi
        if not trattativa_appartiene_a(conn, trattativa_id, user_id):
            return jsonify({'success': False, 'error': 'Accesso negato'}), 403
        
        # Recupera trattativa
        trattativa = get_trattativa(conn, trattativa_id)
        if not trattativa:
            return jsonify({'success': False, 'error': 'Trattativa non trovata'}), 404
        
        # Recupera avanzamenti
        avanzamenti_rows = get_avanzamenti(conn, trattativa_id)
        avanzamenti = [dict(a) for a in avanzamenti_rows]
        
        # Aggiungi colore stato
        colori = get_colori_stati()
        percentuali = get_percentuali_stati()
        trattativa['stato_colore'] = colori.get(trattativa.get('stato', ''), '#6c757d')
        
        for av in avanzamenti:
            av['stato_colore'] = colori.get(av.get('stato', ''), '#6c757d')
        
        return jsonify({
            'success': True,
            'trattativa': trattativa,
            'avanzamenti': avanzamenti
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - CREA TRATTATIVA
# ==============================================================================

@trattative_bp.route('/api/crea', methods=['POST'])
@login_required
def api_crea():
    """API crea nuova trattativa"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        data = request.get_json()
        
        # Validazione campi obbligatori
        if not data.get('cliente_id'):
            return jsonify({'success': False, 'error': 'Cliente obbligatorio'}), 400
        
        # Prepara dati
        dati = {
            'cliente_id': int(data['cliente_id']),
            'noleggiatore': data.get('noleggiatore'),
            'marca': data.get('marca'),
            'descrizione_veicolo': data.get('descrizione_veicolo'),
            'tipologia_veicolo': data.get('tipologia_veicolo'),
            'tipo_trattativa': data.get('tipo_trattativa'),
            'num_pezzi': int(data.get('num_pezzi', 1)),
            'stato': data.get('stato', 'Preso in carico'),
            'note': data.get('note'),
            'commerciale_assegnato': data.get('commerciale_assegnato'),
        }
        
        # Crea trattativa
        trattativa_id = crea_trattativa(conn, dati, user_id)
        
        if trattativa_id:
            return jsonify({
                'success': True,
                'trattativa_id': trattativa_id,
                'message': 'Trattativa creata con successo'
            })
        else:
            return jsonify({'success': False, 'error': 'Errore creazione trattativa'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - MODIFICA TRATTATIVA
# ==============================================================================

@trattative_bp.route('/api/<int:trattativa_id>/modifica', methods=['POST'])
@login_required
def api_modifica(trattativa_id):
    """API modifica trattativa esistente"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Verifica permessi
        if not trattativa_appartiene_a(conn, trattativa_id, user_id):
            return jsonify({'success': False, 'error': 'Accesso negato'}), 403
        
        data = request.get_json()
        
        # Prepara dati (solo campi presenti)
        dati = {}
        campi = ['noleggiatore', 'marca', 'descrizione_veicolo', 
                 'tipologia_veicolo', 'tipo_trattativa', 'num_pezzi', 'note']
        
        for campo in campi:
            if campo in data:
                dati[campo] = data[campo]
        
        # Modifica
        if modifica_trattativa(conn, trattativa_id, dati, user_id):
            return jsonify({
                'success': True,
                'message': 'Trattativa modificata con successo'
            })
        else:
            return jsonify({'success': False, 'error': 'Errore modifica'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - NUOVO AVANZAMENTO
# ==============================================================================

@trattative_bp.route('/api/<int:trattativa_id>/avanzamento', methods=['POST'])
@login_required
def api_avanzamento(trattativa_id):
    """API registra nuovo avanzamento"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Verifica permessi
        if not trattativa_appartiene_a(conn, trattativa_id, user_id):
            return jsonify({'success': False, 'error': 'Accesso negato'}), 403
        
        data = request.get_json()
        
        # Validazione
        if not data.get('stato'):
            return jsonify({'success': False, 'error': 'Stato obbligatorio'}), 400
        
        # Registra avanzamento
        if aggiungi_avanzamento(conn, trattativa_id, data['stato'], 
                                data.get('note', ''), user_id):
            return jsonify({
                'success': True,
                'message': 'Avanzamento registrato con successo'
            })
        else:
            return jsonify({'success': False, 'error': 'Errore registrazione'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - ELIMINA TRATTATIVA
# ==============================================================================

@trattative_bp.route('/api/<int:trattativa_id>/elimina', methods=['POST'])
@login_required
def api_elimina(trattativa_id):
    """API elimina trattativa"""
    conn = get_db()
    user_id = get_current_user_id()
    is_admin = session.get('ruolo_base') == 'admin'
    
    try:
        # Verifica permessi visibilita'
        if not trattativa_appartiene_a(conn, trattativa_id, user_id):
            return jsonify({'success': False, 'error': 'Accesso negato'}), 403
        
        # Recupera stato trattativa
        cursor = conn.cursor()
        cursor.execute("SELECT stato FROM trattative WHERE id = ?", (trattativa_id,))
        row = cursor.fetchone()
        stato = row['stato'] if row else None
        
        # Verifica cancellabilita'
        if not trattativa_cancellabile(conn, trattativa_id, is_admin=is_admin, stato=stato):
            # Messaggio diverso se chiusa o se ha avanzamenti
            stati_chiusi = get_stati_chiusi()
            if stato in stati_chiusi:
                return jsonify({'success': False, 'error': 'Trattativa chiusa: non eliminabile'}), 403
            else:
                return jsonify({'success': False, 'error': 'Trattativa non eliminabile: ha avanzamenti registrati'}), 403
        
        # Elimina
        if elimina_trattativa(conn, trattativa_id, user_id):
            return jsonify({
                'success': True,
                'message': 'Trattativa eliminata con successo'
            })
        else:
            return jsonify({'success': False, 'error': 'Errore eliminazione'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - RICERCA CLIENTI (per autocomplete)
# ==============================================================================

@trattative_bp.route('/api/clienti/search')
@login_required
def api_clienti_search():
    """API ricerca clienti per autocomplete"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify({'success': True, 'clienti': []})
        
        # Ottieni clienti visibili (stessa logica gerarchia)
        subordinati_ids = get_subordinati(conn, user_id)
        placeholders = ','.join('?' * len(subordinati_ids))
        
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT DISTINCT c.id, COALESCE(c.ragione_sociale, c.nome_cliente) as ragione_sociale, COALESCE(c.p_iva, c.cod_fiscale) as p_iva, c.commerciale_id
            FROM clienti c
            
            WHERE (c.ragione_sociale LIKE ? OR c.p_iva LIKE ?)
            AND (ac.commerciale_id IN ({placeholders}) OR ac.commerciale_id IS NULL)
            ORDER BY COALESCE(c.ragione_sociale, c.nome_cliente) COLLATE NOCASE
            LIMIT 20
        """, (f'%{query}%', f'%{query}%', *subordinati_ids))
        
        clienti = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'clienti': clienti
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - TRATTATIVE CLIENTE (per widget in dettaglio cliente)
# ==============================================================================

@trattative_bp.route('/api/cliente/<int:cliente_id>')
@login_required
def api_trattative_cliente(cliente_id):
    """API trattative di un cliente specifico"""
    conn = get_db()
    
    try:
        solo_aperte = request.args.get('solo_aperte') == '1'
        trattative = get_trattative_cliente(conn, cliente_id, solo_aperte)
        
        # Verifica se utente e' admin
        is_admin = session.get('ruolo_base') == 'admin'
        
        # Aggiungi colori stati
        colori = get_colori_stati()
        percentuali = get_percentuali_stati()
        for t in trattative:
            t['stato_colore'] = colori.get(t.get('stato', ''), '#6c757d')
            t['cancellabile'] = trattativa_cancellabile(conn, t['id'], is_admin=is_admin, stato=t.get('stato'))
            t['percentuale'] = percentuali.get(t.get('stato', ''), 0)
        
        return jsonify({
            'success': True,
            'trattative': trattative
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - CLIENTI PER COMMERCIALE (per dropdown modal nuova)
# ==============================================================================

@trattative_bp.route('/api/clienti/per_commerciale/<int:commerciale_id>')
@login_required
def api_clienti_per_commerciale(commerciale_id):
    """API restituisce clienti assegnati a un commerciale specifico"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Verifica che il commerciale richiesto sia visibile all'utente
        subordinati_ids = get_subordinati(conn, user_id)
        
        if commerciale_id not in subordinati_ids:
            return jsonify({'success': False, 'error': 'Accesso negato'}), 403
        
        # Recupera solo i clienti di quel commerciale
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, 
                   COALESCE(c.ragione_sociale, c.nome_cliente) as ragione_sociale, 
                   COALESCE(c.p_iva, c.cod_fiscale) as p_iva
            FROM clienti c
            WHERE c.commerciale_id = ?
            ORDER BY COALESCE(c.ragione_sociale, c.nome_cliente) COLLATE NOCASE
        """, (commerciale_id,))
        
        clienti = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'clienti': clienti,
            'commerciale_id': commerciale_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - LISTA TRATTATIVE CANCELLATE (solo per admin)
# ==============================================================================

@trattative_bp.route('/api/lista_cancellate')
@login_required
def api_lista_cancellate():
    """API lista trattative cancellate (visibile a tutti, ripristinabile solo da admin)"""
    conn = get_db()
    user_id = get_current_user_id()
    
    try:
        # Parametri paginazione
        limite = int(request.args.get('limite', 10))
        offset = int(request.args.get('offset', 0))
        
        # Filtro cliente (opzionale)
        filtri = {'solo_cancellate': True}
        if request.args.get('cliente_id'):
            filtri['cliente_id'] = int(request.args.get('cliente_id'))
        
        # Esegui ricerca
        trattative_rows, totale = cerca_trattative(conn, filtri, user_id, limite, offset)
        trattative = [dict(t) for t in trattative_rows]
        
        # Aggiungi colori stati
        colori = get_colori_stati()
        for t in trattative:
            t['stato_colore'] = colori.get(t.get('stato', ''), '#6c757d')
        
        return jsonify({
            'success': True,
            'trattative': trattative,
            'totale': totale,
            'limite': limite,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - RIPRISTINA TRATTATIVA (solo admin)
# ==============================================================================

@trattative_bp.route('/api/<int:trattativa_id>/ripristina', methods=['POST'])
@login_required
def api_ripristina(trattativa_id):
    """API ripristina trattativa cancellata (solo admin)"""
    conn = get_db()
    user_id = get_current_user_id()
    is_admin = session.get('ruolo_base') == 'admin'
    
    try:
        # Solo admin puo' ripristinare
        if not is_admin:
            return jsonify({'success': False, 'error': 'Solo gli amministratori possono ripristinare trattative'}), 403
        
        # Ripristina
        if ripristina_trattativa(conn, trattativa_id, user_id):
            return jsonify({
                'success': True,
                'message': 'Trattativa ripristinata con successo'
            })
        else:
            return jsonify({'success': False, 'error': 'Trattativa non trovata o non cancellata'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# API - RIAPRI TRATTATIVA CHIUSA (solo admin)
# ==============================================================================

@trattative_bp.route('/api/<int:trattativa_id>/riapri', methods=['POST'])
@login_required
def api_riapri(trattativa_id):
    """API riapre trattativa chiusa (solo admin)"""
    conn = get_db()
    user_id = get_current_user_id()
    is_admin = session.get('ruolo_base') == 'admin'
    
    try:
        # Solo admin puo' riaprire
        if not is_admin:
            return jsonify({'success': False, 'error': 'Solo gli amministratori possono riaprire trattative chiuse'}), 403
        
        # Riapri
        if riapri_trattativa(conn, trattativa_id, user_id):
            return jsonify({
                'success': True,
                'message': 'Trattativa riaperta con successo'
            })
        else:
            return jsonify({'success': False, 'error': 'Trattativa non trovata o non chiusa'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()
