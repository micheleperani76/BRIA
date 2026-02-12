# ==============================================================================
# ROUTES_NOLEGGIATORI_CLIENTE.PY - Gestione Noleggiatori per Cliente
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-01-26
# Descrizione: API per CRUD associazioni cliente-noleggiatore
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

def get_noleggiatori_cliente(cliente_id):
    """
    Ritorna tutti i noleggiatori associati a un cliente.
    Include il conteggio veicoli per ogni noleggiatore.
    
    Args:
        cliente_id: ID del cliente
    
    Returns:
        list: Lista di dict con noleggiatore, stato_relazione, note, conteggi veicoli
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            cn.id, cn.noleggiatore, cn.stato_relazione, cn.stato_crm, cn.note, cn.data_inserimento, cn.ordine,
            COALESCE(SUM(CASE WHEN v.tipo_veicolo = 'Installato' THEN 1 ELSE 0 END), 0) as veicoli_installato,
            COALESCE(SUM(CASE WHEN v.tipo_veicolo = 'Extra' OR v.tipo_veicolo IS NULL THEN 1 ELSE 0 END), 0) as veicoli_extra,
            COALESCE(COUNT(v.id), 0) as veicoli_totale
        FROM clienti_noleggiatori cn
        LEFT JOIN veicoli v ON v.cliente_id = cn.cliente_id AND v.noleggiatore = cn.noleggiatore
        WHERE cn.cliente_id = ?
        GROUP BY cn.id, cn.noleggiatore, cn.stato_relazione, cn.stato_crm, cn.note, cn.data_inserimento, cn.ordine
        ORDER BY cn.ordine, cn.noleggiatore
    """, (cliente_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_noleggiatori_da_veicoli(cliente_id):
    """
    Ritorna i noleggiatori estratti dai veicoli del cliente.
    Include lo stato automatico basato su tipo_veicolo e le note se presenti.
    
    Args:
        cliente_id: ID del cliente
    
    Returns:
        list: Lista di dict con noleggiatore, stato_auto, conteggi e note
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Raggruppa per noleggiatore e conta i tipi
    # Prende anche le note dalla tabella clienti_noleggiatori se esistono
    cursor.execute("""
        SELECT 
            v.noleggiatore,
            SUM(CASE WHEN v.tipo_veicolo = 'Installato' THEN 1 ELSE 0 END) as installato,
            SUM(CASE WHEN v.tipo_veicolo = 'Extra' OR v.tipo_veicolo IS NULL THEN 1 ELSE 0 END) as extra,
            COUNT(*) as totale,
            cn.note as note
        FROM veicoli v
        LEFT JOIN clienti_noleggiatori cn ON cn.cliente_id = v.cliente_id AND cn.noleggiatore = v.noleggiatore
        WHERE v.cliente_id = ? AND v.noleggiatore IS NOT NULL AND v.noleggiatore != ''
        GROUP BY v.noleggiatore
        ORDER BY v.noleggiatore
    """, (cliente_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        # Determina stato automatico
        if row['installato'] > 0:
            stato_auto = 'NOSTRI'  # Almeno un veicolo Installato = nostri
        else:
            stato_auto = 'ALTRO_BROKER'  # Tutti Extra = altro broker
        
        result.append({
            'noleggiatore': row['noleggiatore'],
            'stato_auto': stato_auto,
            'veicoli_installato': row['installato'],
            'veicoli_extra': row['extra'],
            'veicoli_totale': row['totale'],
            'note': row['note'] or ''
        })
    
    return result


def get_lista_noleggiatori():
    """
    Ritorna la lista di tutti i noleggiatori disponibili.
    Legge da file Excel impostazioni/noleggiatori.xlsx + quelli nel DB.
    
    Returns:
        list: Lista noleggiatori ordinata
    """
    from pathlib import Path
    import openpyxl
    
    predefiniti = []
    
    # Leggi da file Excel
    excel_path = Path(__file__).resolve().parent.parent / "impostazioni" / "noleggiatori.xlsx"
    if excel_path.exists():
        try:
            wb = openpyxl.load_workbook(str(excel_path), read_only=True)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0]:  # Codice
                    predefiniti.append(str(row[0]).strip().upper())
            wb.close()
        except Exception as e:
            logger.warning(f"Errore lettura noleggiatori.xlsx: {e}")
            # Fallback lista hardcoded
            predefiniti = ['ALD', 'ALPHABET', 'ARVAL', 'AYVENS', 'DRIVALIA',
                          'LEASEPLAN', 'LEASYS', 'RENT2GO', 'SIFA']
    else:
        # Fallback lista hardcoded
        predefiniti = ['ALD', 'ALPHABET', 'ARVAL', 'AYVENS', 'DRIVALIA',
                      'LEASEPLAN', 'LEASYS', 'RENT2GO', 'SIFA']
    
    # Aggiungi quelli esistenti nel DB
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT noleggiatore FROM veicoli 
        WHERE noleggiatore IS NOT NULL AND noleggiatore != ''
        UNION
        SELECT DISTINCT noleggiatore FROM clienti_noleggiatori
        WHERE noleggiatore IS NOT NULL AND noleggiatore != ''
    """)
    rows = cursor.fetchall()
    conn.close()
    
    db_noleggiatori = [row['noleggiatore'] for row in rows]
    
    # Unisci e ordina
    tutti = set(predefiniti + db_noleggiatori)
    return sorted(tutti)


# ==============================================================================
# ROUTE API
# ==============================================================================

@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/crm', methods=['PUT'])
@login_required
def api_update_crm_cliente(cliente_id):
    """
    PUT: Aggiorna lo stato CRM del cliente.
    """
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
    Include sia quelli manuali che quelli rilevati dai veicoli con stato automatico.
    """
    try:
        # Noleggiatori manuali (dalla tabella)
        manuali = get_noleggiatori_cliente(cliente_id)
        
        # Noleggiatori dai veicoli (riscontro automatico con stato)
        da_veicoli_raw = get_noleggiatori_da_veicoli(cliente_id)
        
        # Noleggiatori manuali gia' inseriti
        manuali_nomi = [n['noleggiatore'] for n in manuali]
        
        # Noleggiatori solo da veicoli (non ancora in tabella manuale)
        da_veicoli = [n for n in da_veicoli_raw if n['noleggiatore'] not in manuali_nomi]
        
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
    
    Body JSON:
        noleggiatore: nome noleggiatore
        stato_relazione: codice stato (es. NOSTRI, ALTRO_BROKER)
        data_inizio: data inizio relazione (opzionale)
        note: note (opzionale)
    """
    try:
        data = request.get_json()
        noleggiatore = data.get('noleggiatore', '').strip().upper()
        stato_crm = data.get('stato_crm', '')
        stato = data.get('stato_relazione', 'ALTRO_BROKER')
        note = data.get('note', '')
        
        if not noleggiatore:
            return jsonify({'success': False, 'error': 'Noleggiatore richiesto'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calcola prossimo ordine
        cursor.execute("SELECT COALESCE(MAX(ordine), -1) + 1 FROM clienti_noleggiatori WHERE cliente_id = ?", (cliente_id,))
        prossimo_ordine = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO clienti_noleggiatori (cliente_id, noleggiatore, stato_crm, stato_relazione, note, ordine)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cliente_id, noleggiatore, stato_crm or None, stato, note or None, prossimo_ordine))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Aggiunto noleggiatore {noleggiatore} al cliente {cliente_id}")
        
        return jsonify({
            'success': True,
            'id': new_id,
            'message': f'Noleggiatore {noleggiatore} aggiunto'
        })
        
    except Exception as e:
        if 'UNIQUE constraint' in str(e):
            return jsonify({'success': False, 'error': 'Noleggiatore gia\' presente per questo cliente'}), 400
        logger.error(f"Errore add noleggiatore: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@noleggiatori_cliente_bp.route('/api/cliente/<int:cliente_id>/noleggiatori/<int:noleg_id>', methods=['PUT'])
@login_required
def api_update_noleggiatore(cliente_id, noleg_id):
    """
    PUT: Aggiorna un noleggiatore del cliente.
    """
    try:
        data = request.get_json()
        stato_crm = data.get('stato_crm')
        stato = data.get('stato_relazione')
        note = data.get('note')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Costruisci query dinamica
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
    """
    DELETE: Rimuove un noleggiatore dal cliente.
    """
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
        noleggiatore_nome = data.get('noleggiatore', '').strip().upper()
        direzione = data.get('direzione', '')
        
        if direzione not in ('su', 'giu'):
            return jsonify({'success': False, 'error': 'Direzione non valida'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # === MATERIALIZZA: porta tutti i noleggiatori da veicoli in clienti_noleggiatori ===
        cursor.execute("""
            SELECT DISTINCT v.noleggiatore
            FROM veicoli v
            WHERE v.cliente_id = ? AND v.noleggiatore IS NOT NULL AND v.noleggiatore != ''
            AND v.noleggiatore NOT IN (
                SELECT cn.noleggiatore FROM clienti_noleggiatori cn WHERE cn.cliente_id = ?
            )
        """, (cliente_id, cliente_id))
        mancanti = cursor.fetchall()
        
        if mancanti:
            # Prossimo ordine disponibile
            cursor.execute("SELECT COALESCE(MAX(ordine), -1) + 1 FROM clienti_noleggiatori WHERE cliente_id = ?", (cliente_id,))
            prossimo = cursor.fetchone()[0] or 0
            
            for row in mancanti:
                nome = row['noleggiatore']
                # Determina stato da veicoli
                cursor.execute("""
                    SELECT SUM(CASE WHEN tipo_veicolo = 'Installato' THEN 1 ELSE 0 END) as inst
                    FROM veicoli WHERE cliente_id = ? AND noleggiatore = ?
                """, (cliente_id, nome))
                vrow = cursor.fetchone()
                stato = 'NOSTRI' if vrow and vrow['inst'] > 0 else 'ALTRO_BROKER'
                
                cursor.execute("""
                    INSERT INTO clienti_noleggiatori (cliente_id, noleggiatore, stato_relazione, ordine)
                    VALUES (?, ?, ?, ?)
                """, (cliente_id, nome, stato, prossimo))
                prossimo += 1
            
            conn.commit()
            logger.info(f"Materializzati {len(mancanti)} noleggiatori da veicoli per cliente {cliente_id}")
        
        # === Normalizza ordini (riempie buchi) ===
        cursor.execute("""
            SELECT id FROM clienti_noleggiatori 
            WHERE cliente_id = ? ORDER BY ordine, noleggiatore
        """, (cliente_id,))
        tutti = cursor.fetchall()
        for i, r in enumerate(tutti):
            cursor.execute("UPDATE clienti_noleggiatori SET ordine = ? WHERE id = ?", (i, r['id']))
        conn.commit()
        
        # === Trova il record da spostare ===
        if noleg_id:
            cursor.execute("SELECT id, ordine FROM clienti_noleggiatori WHERE id = ? AND cliente_id = ?",
                           (noleg_id, cliente_id))
        else:
            cursor.execute("SELECT id, ordine FROM clienti_noleggiatori WHERE noleggiatore = ? AND cliente_id = ?",
                           (noleggiatore_nome, cliente_id))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Record non trovato'}), 404
        
        noleg_id = row['id']
        ordine_corrente = row['ordine']
        
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
    GET: Ritorna la lista di tutti i noleggiatori disponibili.
    """
    try:
        return jsonify({
            'success': True,
            'noleggiatori': get_lista_noleggiatori(),
            'stati': get_stati_noleggiatore(),
            'stati_crm': get_stati_crm()
        })
    except Exception as e:
        logger.error(f"Errore lista noleggiatori: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
