#!/usr/bin/env python3
# ==============================================================================
# ROUTES - Pagina Veicoli Installato
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-09
# Descrizione: Blueprint per la pagina dedicata veicoli INSTALLATO
#              (gestiti da BR Car Service)
# ==============================================================================

from flask import Blueprint, render_template, request
from app.database import get_connection
from app.auth import login_required

installato_bp = Blueprint('installato', __name__, url_prefix='/installato')


@installato_bp.route('/')
@login_required
def pagina_installato():
    """Pagina principale veicoli Installato con statistiche e filtri."""
    conn = get_connection()
    cursor = conn.cursor()

    # Filtri
    filtro_noleggiatore = request.args.get('noleggiatore', '')
    filtro_stato = request.args.get('stato', '')  # attivo/scaduto
    filtro_commerciale = request.args.get('commerciale', '')
    cerca = request.args.get('q', '').strip()

    # ==========================================
    # STATISTICHE
    # ==========================================

    # Totale installato
    cursor.execute("SELECT COUNT(*) FROM veicoli_attivi WHERE tipo_veicolo = 'Installato'")
    totale = cursor.fetchone()[0]

    # Attivi (scadenza >= oggi)
    cursor.execute("""
        SELECT COUNT(*) FROM veicoli_attivi
        WHERE tipo_veicolo = 'Installato' AND scadenza >= date('now')
    """)
    attivi = cursor.fetchone()[0]

    # In gestione (scadenza < oggi o NULL)
    in_gestione = totale - attivi

    # Canone totale
    cursor.execute("""
        SELECT COALESCE(SUM(canone), 0) FROM veicoli_attivi
        WHERE tipo_veicolo = 'Installato'
    """)
    canone_totale = cursor.fetchone()[0]

    # Per noleggiatore
    cursor.execute("""
        SELECT COALESCE(noleggiatore, 'Non specificato') as nol,
               COUNT(*) as num,
               COALESCE(SUM(canone), 0) as canone_sum
        FROM veicoli_attivi
        WHERE tipo_veicolo = 'Installato'
        GROUP BY noleggiatore
        ORDER BY num DESC
    """)
    per_noleggiatore = [dict(row) for row in cursor.fetchall()]

    # Per commerciale
    cursor.execute("""
        SELECT COALESCE(u.cognome, 'Non assegnato') as commerciale_nome,
               v.commerciale_id,
               COUNT(*) as num,
               COALESCE(SUM(v.canone), 0) as canone_sum
        FROM veicoli_attivi v
        LEFT JOIN utenti u ON v.commerciale_id = u.id
        WHERE v.tipo_veicolo = 'Installato'
        GROUP BY v.commerciale_id
        ORDER BY num DESC
    """)
    per_commerciale = [dict(row) for row in cursor.fetchall()]

    # Lista noleggiatori per filtro
    cursor.execute("""
        SELECT DISTINCT COALESCE(n.nome_display, v.noleggiatore) as nome_noleggiatore
        FROM veicoli_attivi v
        LEFT JOIN noleggiatori n ON n.id = v.noleggiatore_id
        WHERE v.tipo_veicolo = 'Installato' AND v.noleggiatore IS NOT NULL
        ORDER BY nome_noleggiatore
    """)
    noleggiatori_lista = [row[0] for row in cursor.fetchall()]

    # Lista commerciali per filtro
    cursor.execute("""
        SELECT DISTINCT u.id, u.cognome
        FROM veicoli_attivi v
        JOIN utenti u ON v.commerciale_id = u.id
        WHERE v.tipo_veicolo = 'Installato'
        ORDER BY u.cognome
    """)
    commerciali_lista = [dict(row) for row in cursor.fetchall()]

    # ==========================================
    # QUERY VEICOLI con filtri
    # ==========================================
    query = """
        SELECT v.*,
               c.nome_cliente,
               c.ragione_sociale,
               COALESCE(u.cognome, '') as commerciale_nome,
               (SELECT COUNT(*) FROM note_veicoli WHERE veicolo_id = v.id AND eliminato = 0) as num_note
        FROM veicoli_attivi v
        LEFT JOIN clienti c ON v.cliente_id = c.id
        LEFT JOIN utenti u ON v.commerciale_id = u.id
        WHERE v.tipo_veicolo = 'Installato'
    """
    params = []

    if filtro_noleggiatore:
        query += " AND v.noleggiatore = ?"
        params.append(filtro_noleggiatore)

    if filtro_stato == 'attivo':
        query += " AND v.scadenza >= date('now')"
    elif filtro_stato == 'scaduto':
        query += " AND (v.scadenza < date('now') OR v.scadenza IS NULL)"

    if filtro_commerciale:
        try:
            query += " AND v.commerciale_id = ?"
            params.append(int(filtro_commerciale))
        except ValueError:
            pass

    if cerca:
        query += """ AND (
            v.targa LIKE ? OR v.marca LIKE ? OR v.modello LIKE ?
            OR v.driver LIKE ? OR c.nome_cliente LIKE ?
        )"""
        like = f'%{cerca}%'
        params.extend([like] * 5)

    query += " ORDER BY v.noleggiatore, v.scadenza"
    cursor.execute(query, params)
    veicoli = [dict(row) for row in cursor.fetchall()]

    # ==========================================
    # STORICO count
    # ==========================================
    cursor.execute("SELECT COUNT(*) FROM storico_installato")
    totale_storico = cursor.fetchone()[0]

    conn.close()

    # Date per colorazione scadenze nel template
    from datetime import datetime, timedelta
    oggi = datetime.now().strftime('%Y-%m-%d')
    fra_90 = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

    return render_template('installato/index.html',
                         veicoli=veicoli,
                         now_str=oggi,
                         prossimi_90=fra_90,
                         totale=totale,
                         attivi=attivi,
                         in_gestione=in_gestione,
                         canone_totale=canone_totale,
                         per_noleggiatore=per_noleggiatore,
                         per_commerciale=per_commerciale,
                         noleggiatori_lista=noleggiatori_lista,
                         commerciali_lista=commerciali_lista,
                         totale_storico=totale_storico,
                         filtro_noleggiatore=filtro_noleggiatore,
                         filtro_stato=filtro_stato,
                         filtro_commerciale=filtro_commerciale,
                         cerca=cerca)


@installato_bp.route('/storico')
@login_required
def pagina_storico():
    """Pagina storico veicoli dismessi INSTALLATO."""
    conn = get_connection()
    cursor = conn.cursor()

    cerca = request.args.get('q', '').strip()
    filtro_noleggiatore = request.args.get('noleggiatore', '')

    query = """
        SELECT s.*,
               c.nome_cliente,
               c.ragione_sociale
        FROM storico_installato s
        LEFT JOIN clienti c ON s.cliente_id = c.id
        WHERE 1=1
    """
    params = []

    if filtro_noleggiatore:
        query += " AND s.noleggiatore = ?"
        params.append(filtro_noleggiatore)

    if cerca:
        query += " AND (s.targa LIKE ? OR s.marca LIKE ? OR c.nome_cliente LIKE ?)"
        like = f'%{cerca}%'
        params.extend([like] * 3)

    query += " ORDER BY s.scadenza DESC"
    cursor.execute(query, params)
    veicoli = [dict(row) for row in cursor.fetchall()]

    # Noleggiatori per filtro
    cursor.execute("""
        SELECT DISTINCT COALESCE(n.nome_display, s.noleggiatore) as nome_noleggiatore
        FROM storico_installato s
        LEFT JOIN noleggiatori n ON n.codice = UPPER(REPLACE(s.noleggiatore, ' ', '_'))
        WHERE s.noleggiatore IS NOT NULL 
        ORDER BY nome_noleggiatore
    """)
    noleggiatori_lista = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template('installato/storico.html',
                         veicoli=veicoli,
                         noleggiatori_lista=noleggiatori_lista,
                         filtro_noleggiatore=filtro_noleggiatore,
                         cerca=cerca)
