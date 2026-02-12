# ==============================================================================
# ROUTES_NOLEGGIATORI_CLIENTE.PY - Gestione Noleggiatori per Cliente
# ==============================================================================
# Versione: 2.0.0
# Data: 2026-02-12
# Descrizione: API per CRUD associazioni cliente-noleggiatore
# Refactoring: usa tabella anagrafica 'noleggiatori' con FK noleggiatore_id
# ==============================================================================

from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.config_stati import get_stati_noleggiatore, get_stati_crm
from app.auth import login_required
import logging

logger = logging.getLogger(__name__)

# Blueprint
noleggiatori_cliente_bp = Blueprint('noleggiatori_cliente', __name__)


# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def normalizza_nome(nome):
    """Normalizza un nome noleggiatore al codice univoco."""
    if not nome:
        return None
    MAPPA = {
        'arval': 'ARVAL', 'arval tech': 'ARVAL_TECH',
        'ald': 'ALD', 'ayvens': 'AYVENS', 'drivalia': 'DRIVALIA',
        'leaseplan': 'LEASEPLAN', 'leasys': 'LEASYS',
        'rent2go': 'RENT2GO', 'sifa': 'SIFA', u'sif\u00e0': 'SIFA',
        'alphabet': 'ALPHABET', 'volkswagen leasing': 'VOLKSWAGEN_LEASING',
    }
    chiave = nome.strip().lower()
    return MAPPA.get(chiave, chiave.upper().replace(' ', '_'))


def trova_o_crea_noleggiatore(cursor, nome):
    """
    Trova un noleggiatore per nome (case-insensitive) o lo crea.
    Ritorna l'id del noleggiatore.
    """
    codice = normalizza_nome(nome)
    
    # Cerca per codice
    cursor.execute("SELECT id FROM noleggiatori WHERE codice = ?", (codice,))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Non trovato: crea nuovo
    cursor.execute("SELECT COALESCE(MAX(ordine), 0) + 1 FROM noleggiatori")
    prossimo_ordine = cursor.fetchone()[0]
    
    cursor.execute("""
        INSERT INTO noleggiatori (codice, nome_display, ordine, origine)
        VALUES (?, ?, ?, 'IMPORT')
    """, (codice, nome.strip(), prossimo_ordine))
    
    logger.info(f"Creato nuovo noleggiatore: {codice} ({nome})")
    return cursor.lastrowid


def get_noleggiatori_cliente(cliente_id):
    """
    Ritorna tutti i noleggiatori associati a un cliente.
    Include il conteggio veicoli per ogni noleggiatore.
    Usa JOIN su tabella anagrafica noleggiatori.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            cn.id, cn.noleggiatore_id, cn.stato_relazione, cn.stato_crm, 
            cn.note, cn.data_inserimento, cn.ordine,
            n.codice as noleggiatore_codice,
            n.nome_display as noleggiatore,
            n.colore as noleggiatore_colore,
            COALESCE(SUM(CASE WHEN v.tipo_veicolo = 'Installato' THEN 1 ELSE 0 END), 0) as veicoli_installato,
            COALESCE(SUM(CASE WHEN v.tipo_veicolo = 'Extra' OR v.tipo_veicolo IS NULL THEN 1 ELSE 0 END), 0) as veicoli_extra,
            COALESCE(COUNT(v.id), 0) as veicoli_totale
        FROM clienti_noleggiatori cn
        JOIN noleggiatori n ON n.id = cn.noleggiatore_id
        LEFT JOIN veicoli v ON v.cliente_id = cn.cliente_id AND v.noleggiatore_id = cn.noleggiatore_id
        WHERE cn.cliente_id = ?
        GROUP BY cn.id, cn.noleggiatore_id, cn.stato_relazione, cn.stato_crm, 
                 cn.note, cn.data_inserimento, cn.ordine,
                 n.codice, n.nome_display, n.colore
        ORDER BY cn.ordine, n.nome_display
    """, (cliente_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_noleggiatori_da_veicoli(cliente_id):
    """
    Ritorna i noleggiatori estratti dai veicoli del cliente
    che NON hanno ancora un record in clienti_noleggiatori.
    Usa JOIN su tabella anagrafica noleggiatori.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            n.id as noleggiatore_id,
            n.codice as noleggiatore_codice,
            n.nome_display as noleggiatore,
            n.colore as noleggiatore_colore,
            SUM(CASE WHEN v.tipo_veicolo = 'Installato' THEN 1 ELSE 0 END) as installato,
            SUM(CASE WHEN v.tipo_veicolo = 'Extra' OR v.tipo_veicolo IS NULL THEN 1 ELSE 0 END) as extra,
            COUNT(*) as totale
        FROM veicoli v
        JOIN noleggiatori n ON n.id = v.noleggiatore_id
        WHERE v.cliente_id = ? 
            AND v.noleggiatore_id IS NOT NULL
            AND v.noleggiatore_id NOT IN (
                SELECT cn.noleggiatore_id FROM clienti_noleggiatori cn 
                WHERE cn.cliente_id = ? AND cn.noleggiatore_id IS NOT NULL
            )
        GROUP BY n.id, n.codice, n.nome_display, n.colore
        ORDER BY n.nome_display
    """, (cliente_id, cliente_id))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        if row['installato'] > 0:
            stato_auto = 'NOSTRI'
        else:
            stato_auto = 'ALTRO_BROKER'
        
        result.append({
            'noleggiatore_id': row['noleggiatore_id'],
            'noleggiatore_codice': row['noleggiatore_codice'],
            'noleggiatore': row['noleggiatore'],
            'noleggiatore_colore': row['noleggiatore_colore'],
            'stato_auto': stato_auto,
            'veicoli_installato': row['installato'],
            'veicoli_extra': row['extra'],
            'veicoli_totale': row['totale'],
            'note': ''
        })
    
    return result


def get_lista_noleggiatori():
    """
    Ritorna la lista di tutti i noleggiatori dalla tabella anagrafica.
    Non usa piu' il file xlsx.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, codice, nome_display, colore, ordine
        FROM noleggiatori 
        WHERE attivo = 1
        ORDER BY ordine, nome_display
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ==============================================================================
# ROUTE API
# ==============================================================================

@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/crm', methods=['PUT'])
@login_required
def api_update_crm_cliente(cliente_id):
    """PUT: Aggiorna lo stato CRM del cliente."""
    try:
        data = request.get_json()
        stato_crm = data.get('stato_crm', '')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE clienti SET stato_crm = ? WHERE id = ?
        """, (stato_crm or None, cliente_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Aggiornato stato_crm cliente {cliente_id}: {stato_crm}")
        
        return jsonify({'success': True, 'message': 'Stato CRM aggiornato'})
        
    except Exception as e:
        logger.error(f"Errore update CRM cliente: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/noleggiatori', methods=['GET'])
@login_required
def api_get_noleggiatori(cliente_id):
    """
    GET: Ritorna i noleggiatori del cliente.
    Include sia quelli manuali che quelli rilevati dai veicoli.
    """
    try:
        manuali = get_noleggiatori_cliente(cliente_id)
        da_veicoli = get_noleggiatori_da_veicoli(cliente_id)
        
        return jsonify({
            'success': True,
            'manuali': manuali,
            'da_veicoli': da_veicoli,
            'stati_disponibili': get_stati_noleggiatore(),
            'stati_crm': get_stati_crm()
        })
    except Exception as e:
        logger.error(f"Errore get noleggiatori cliente {cliente_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/noleggiatori', methods=['POST'])
@login_required
def api_add_noleggiatore(cliente_id):
    """
    POST: Aggiunge un noleggiatore al cliente.
    Accetta sia noleggiatore_id (preferito) che noleggiatore (stringa, retrocompatibile).
    """
    try:
        data = request.get_json()
        noleggiatore_id = data.get('noleggiatore_id')
        noleggiatore_nome = data.get('noleggiatore', '').strip()
        stato_crm = data.get('stato_crm', '')
        stato = data.get('stato_relazione', 'ALTRO_BROKER')
        note = data.get('note', '')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Risolvi noleggiatore_id
        if not noleggiatore_id and noleggiatore_nome:
            noleggiatore_id = trova_o_crea_noleggiatore(cursor, noleggiatore_nome)
            conn.commit()
        
        if not noleggiatore_id:
            conn.close()
            return jsonify({'success': False, 'error': 'Noleggiatore richiesto'}), 400
        
        # Calcola prossimo ordine
        cursor.execute("SELECT COALESCE(MAX(ordine), -1) + 1 FROM clienti_noleggiatori WHERE cliente_id = ?", (cliente_id,))
        prossimo_ordine = cursor.fetchone()[0]
        
        # Recupera nome per retrocompatibilita' (campo stringa vecchio)
        if not noleggiatore_nome:
            cursor.execute("SELECT nome_display FROM noleggiatori WHERE id = ?", (noleggiatore_id,))
            row = cursor.fetchone()
            noleggiatore_nome = row['nome_display'] if row else ''
        
        cursor.execute("""
            INSERT INTO clienti_noleggiatori 
                (cliente_id, noleggiatore_id, noleggiatore, stato_crm, stato_relazione, note, ordine)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cliente_id, noleggiatore_id, noleggiatore_nome, stato_crm or None, stato, note or None, prossimo_ordine))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Aggiunto noleggiatore id={noleggiatore_id} al cliente {cliente_id}")
        
        return jsonify({
            'success': True,
            'id': new_id,
            'message': f'Noleggiatore {noleggiatore_nome} aggiunto'
        })
        
    except Exception as e:
        if 'UNIQUE constraint' in str(e):
            return jsonify({'success': False, 'error': 'Noleggiatore gia presente per questo cliente'}), 400
        logger.error(f"Errore add noleggiatore: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/noleggiatori/<int:noleg_id>', methods=['PUT'])
@login_required
def api_update_noleggiatore(cliente_id, noleg_id):
    """PUT: Aggiorna un noleggiatore del cliente."""
    try:
        data = request.get_json()
        stato_crm = data.get('stato_crm')
        stato = data.get('stato_relazione')
        note = data.get('note')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if stato_crm is not None:
            updates.append("stato_crm = ?")
            params.append(stato_crm or None)
        if stato is not None:
            updates.append("stato_relazione = ?")
            params.append(stato)
        if note is not None:
            updates.append("note = ?")
            params.append(note or None)
        
        if updates:
            params.extend([noleg_id, cliente_id])
            cursor.execute(f"""
                UPDATE clienti_noleggiatori 
                SET {', '.join(updates)}
                WHERE id = ? AND cliente_id = ?
            """, params)
            conn.commit()
        
        conn.close()
        
        return jsonify({'success': True, 'message': 'Noleggiatore aggiornato'})
        
    except Exception as e:
        logger.error(f"Errore update noleggiatore: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/noleggiatori/<int:noleg_id>', methods=['DELETE'])
@login_required
def api_delete_noleggiatore(cliente_id, noleg_id):
    """DELETE: Rimuove un noleggiatore dal cliente."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM clienti_noleggiatori 
            WHERE id = ? AND cliente_id = ?
        """, (noleg_id, cliente_id))
        
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        
        if deleted:
            return jsonify({'success': True, 'message': 'Noleggiatore rimosso'})
        else:
            return jsonify({'success': False, 'error': 'Noleggiatore non trovato'}), 404
        
    except Exception as e:
        logger.error(f"Errore delete noleggiatore: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/noleggiatori/riordina', methods=['POST'])
@login_required
def api_riordina_noleggiatore(cliente_id):
    """
    POST: Sposta un noleggiatore su o giu nella lista.
    Materializza automaticamente tutti i noleggiatori da veicoli se necessario.
    """
    try:
        data = request.get_json()
        noleg_id = data.get('noleg_id')
        noleggiatore_id = data.get('noleggiatore_id')
        noleggiatore_nome = data.get('noleggiatore', '').strip()
        direzione = data.get('direzione', '')
        
        if direzione not in ('su', 'giu'):
            return jsonify({'success': False, 'error': 'Direzione non valida'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # === MATERIALIZZA: porta tutti i noleggiatori da veicoli in clienti_noleggiatori ===
        cursor.execute("""
            SELECT DISTINCT v.noleggiatore_id
            FROM veicoli v
            WHERE v.cliente_id = ? AND v.noleggiatore_id IS NOT NULL
            AND v.noleggiatore_id NOT IN (
                SELECT cn.noleggiatore_id FROM clienti_noleggiatori cn 
                WHERE cn.cliente_id = ? AND cn.noleggiatore_id IS NOT NULL
            )
        """, (cliente_id, cliente_id))
        mancanti = cursor.fetchall()
        
        if mancanti:
            cursor.execute("SELECT COALESCE(MAX(ordine), -1) + 1 FROM clienti_noleggiatori WHERE cliente_id = ?", (cliente_id,))
            prossimo = cursor.fetchone()[0] or 0
            
            for row in mancanti:
                nol_id = row['noleggiatore_id']
                # Determina stato da veicoli
                cursor.execute("""
                    SELECT SUM(CASE WHEN tipo_veicolo = 'Installato' THEN 1 ELSE 0 END) as inst
                    FROM veicoli WHERE cliente_id = ? AND noleggiatore_id = ?
                """, (cliente_id, nol_id))
                vrow = cursor.fetchone()
                stato = 'NOSTRI' if vrow and vrow['inst'] > 0 else 'ALTRO_BROKER'
                
                # Recupera nome per campo retrocompatibile
                cursor.execute("SELECT nome_display FROM noleggiatori WHERE id = ?", (nol_id,))
                nol_nome = cursor.fetchone()['nome_display']
                
                cursor.execute("""
                    INSERT INTO clienti_noleggiatori 
                        (cliente_id, noleggiatore_id, noleggiatore, stato_relazione, ordine)
                    VALUES (?, ?, ?, ?, ?)
                """, (cliente_id, nol_id, nol_nome, stato, prossimo))
                prossimo += 1
            
            conn.commit()
            logger.info(f"Materializzati {len(mancanti)} noleggiatori per cliente {cliente_id}")
        
        # === Normalizza ordini ===
        cursor.execute("""
            SELECT id FROM clienti_noleggiatori 
            WHERE cliente_id = ? ORDER BY ordine, id
        """, (cliente_id,))
        tutti = cursor.fetchall()
        for i, r in enumerate(tutti):
            cursor.execute("UPDATE clienti_noleggiatori SET ordine = ? WHERE id = ?", (i, r['id']))
        conn.commit()
        
        # === Trova il record da spostare ===
        if noleg_id:
            cursor.execute("SELECT id, ordine FROM clienti_noleggiatori WHERE id = ? AND cliente_id = ?",
                           (noleg_id, cliente_id))
        elif noleggiatore_id:
            cursor.execute("SELECT id, ordine FROM clienti_noleggiatori WHERE noleggiatore_id = ? AND cliente_id = ?",
                           (noleggiatore_id, cliente_id))
        elif noleggiatore_nome:
            # Fallback stringa (retrocompatibilita')
            nol_id_lookup = trova_o_crea_noleggiatore(cursor, noleggiatore_nome)
            conn.commit()
            cursor.execute("SELECT id, ordine FROM clienti_noleggiatori WHERE noleggiatore_id = ? AND cliente_id = ?",
                           (nol_id_lookup, cliente_id))
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Noleggiatore non identificato'}), 400
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Record non trovato'}), 404
        
        noleg_id = row['id']
        ordine_corrente = row['ordine'] if row['ordine'] is not None else 0
        
        # === Trova il vicino ===
        if direzione == 'su':
            cursor.execute("""
                SELECT id, ordine FROM clienti_noleggiatori 
                WHERE cliente_id = ? AND ordine < ?
                ORDER BY ordine DESC LIMIT 1
            """, (cliente_id, ordine_corrente))
        else:
            cursor.execute("""
                SELECT id, ordine FROM clienti_noleggiatori 
                WHERE cliente_id = ? AND ordine > ?
                ORDER BY ordine ASC LIMIT 1
            """, (cliente_id, ordine_corrente))
        
        vicino = cursor.fetchone()
        
        if not vicino:
            conn.close()
            return jsonify({'success': True, 'message': 'Gia al limite'})
        
        # === Scambia ordini ===
        cursor.execute("UPDATE clienti_noleggiatori SET ordine = ? WHERE id = ?",
                       (vicino['ordine'], noleg_id))
        cursor.execute("UPDATE clienti_noleggiatori SET ordine = ? WHERE id = ?",
                       (ordine_corrente, vicino['id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Ordine aggiornato'})
        
    except Exception as e:
        logger.error(f"Errore riordina noleggiatore: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noleggiatori_cliente_bp.route('/api/noleggiatori/lista', methods=['GET'])
@login_required
def api_lista_noleggiatori():
    """
    GET: Ritorna la lista di tutti i noleggiatori dalla tabella anagrafica.
    """
    try:
        noleggiatori = get_lista_noleggiatori()
        return jsonify({
            'success': True,
            'noleggiatori': noleggiatori,
            'stati': get_stati_noleggiatore(),
            'stati_crm': get_stati_crm()
        })
    except Exception as e:
        logger.error(f"Errore lista noleggiatori: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
