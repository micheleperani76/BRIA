#!/usr/bin/env python3
# ==============================================================================
# ROUTE GESTIONE COMMERCIALI - Blueprint
# ==============================================================================
# Versione: 2.3.0
# Data: 2025-01-21
# Descrizione: Route per gestione assegnazioni commerciali (sistema basato su ID)
# Changelog:
#   v2.0.0 - Aggiunta route flotta_per_commerciale con commerciale_id
#   v2.1.0 - Aggiunto filtro visibilita' basato su subordinati
#   v2.2.0 - Visualizzazione gerarchica ad albero subordinati
#   v2.3.0 - Riepilogo globale visibile a tutti + dettaglio filtrato
# ==============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.auth import login_required
from app.database import get_connection
from app.database_utenti import ha_permesso, get_subordinati
from app.gestione_commerciali import (
    get_commerciali_assegnabili, get_commerciale_display,
    get_commerciali_con_clienti, assegna_cliente
)

# ==============================================================================
# BLUEPRINT
# ==============================================================================

flotta_commerciali_bp = Blueprint('flotta_commerciali', __name__)


# ==============================================================================
# FUNZIONI HELPER PER GERARCHIA
# ==============================================================================

def get_subordinati_diretti_ids(conn, utente_id):
    """Restituisce solo i subordinati diretti (non ricorsivi) di un utente."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT subordinato_id 
        FROM supervisioni 
        WHERE supervisore_id = ? AND data_fine IS NULL
    ''', (utente_id,))
    return [row['subordinato_id'] for row in cursor.fetchall()]


def costruisci_albero_commerciali(conn, root_id, commerciali_visibili, dati_commerciali, livello=0, gia_mostrati=None):
    """
    Costruisce l'albero gerarchico dei commerciali.
    """
    if gia_mostrati is None:
        gia_mostrati = set()
    
    risultato = []
    
    if root_id in gia_mostrati:
        return risultato
    
    if commerciali_visibili is not None and root_id not in commerciali_visibili:
        return risultato
    
    gia_mostrati.add(root_id)
    
    if root_id in dati_commerciali:
        risultato.append({
            'id': root_id,
            'livello': livello,
            'dati': dati_commerciali[root_id]
        })
    
    subordinati = get_subordinati_diretti_ids(conn, root_id)
    
    for sub_id in subordinati:
        sub_albero = costruisci_albero_commerciali(
            conn, sub_id, commerciali_visibili, 
            dati_commerciali, livello + 1, gia_mostrati
        )
        risultato.extend(sub_albero)
    
    return risultato


# ==============================================================================
# ROUTE: REPORT PER COMMERCIALE
# ==============================================================================

@flotta_commerciali_bp.route('/flotta/per-commerciale')
@login_required
def flotta_per_commerciale():
    """Report raggruppato per commerciale con riepilogo globale e dettaglio filtrato."""
    
    conn = get_connection()
    cursor = conn.cursor()
    
    user_id = session.get('user_id')
    
    cursor.execute("SELECT ruolo_base FROM utenti WHERE id = ?", (user_id,))
    utente = cursor.fetchone()
    is_admin = utente and utente['ruolo_base'] == 'admin'
    
    puo_gestire_assegnazioni = ha_permesso(conn, user_id, 'flotta_assegnazioni')
    
    # =========================================================================
    # RIEPILOGO GLOBALE (visibile a TUTTI)
    # =========================================================================
    
    cursor.execute('''
        SELECT commerciale_id, 
               COUNT(*) as veicoli,
               COUNT(DISTINCT p_iva) as clienti,
               COALESCE(SUM(canone), 0) as canone
        FROM veicoli
        GROUP BY commerciale_id
        ORDER BY CASE WHEN commerciale_id IS NULL OR commerciale_id = 0 THEN 1 ELSE 0 END, commerciale_id
    ''')
    
    riepilogo_globale = []
    totale_veicoli_globale = 0
    totale_clienti_globale = 0
    totale_canone_globale = 0
    
    for row in cursor.fetchall():
        r = dict(row)
        comm_id = r['commerciale_id']
        r['commerciale'] = get_commerciale_display(conn, comm_id) if comm_id else None
        totale_veicoli_globale += r['veicoli']
        totale_clienti_globale += r['clienti']
        totale_canone_globale += r['canone']
        riepilogo_globale.append(r)
    
    for r in riepilogo_globale:
        r['percentuale'] = (r['canone'] / totale_canone_globale * 100) if totale_canone_globale > 0 else 0
    
    # =========================================================================
    # DETTAGLIO FILTRATO PER SUBORDINATI
    # =========================================================================
    
    if is_admin:
        commerciali_visibili = None
    else:
        commerciali_visibili = get_subordinati(conn, user_id)
    
    # Dati per commerciali visibili
    if commerciali_visibili is not None:
        placeholders = ','.join('?' * len(commerciali_visibili))
        cursor.execute(f'''
            SELECT commerciale_id, 
                   COUNT(*) as veicoli,
                   COUNT(DISTINCT p_iva) as clienti,
                   COALESCE(SUM(canone), 0) as canone
            FROM veicoli
            WHERE commerciale_id IN ({placeholders})
            GROUP BY commerciale_id
        ''', commerciali_visibili)
    else:
        cursor.execute('''
            SELECT commerciale_id, 
                   COUNT(*) as veicoli,
                   COUNT(DISTINCT p_iva) as clienti,
                   COALESCE(SUM(canone), 0) as canone
            FROM veicoli
            WHERE commerciale_id IS NOT NULL AND commerciale_id != 0
            GROUP BY commerciale_id
        ''')
    
    dati_commerciali = {}
    totale_veicoli = 0
    totale_clienti = 0
    totale_canone = 0
    
    for row in cursor.fetchall():
        comm_id = row['commerciale_id']
        if comm_id:
            dati_commerciali[comm_id] = {
                'commerciale_id': comm_id,
                'commerciale': get_commerciale_display(conn, comm_id),
                'veicoli': row['veicoli'],
                'clienti': row['clienti'],
                'canone': row['canone'],
            }
            totale_veicoli += row['veicoli']
            totale_clienti += row['clienti']
            totale_canone += row['canone']
    
    # Costruisci albero
    if is_admin:
        cursor.execute('''
            SELECT DISTINCT u.id 
            FROM utenti u
            WHERE u.ruolo_base = 'commerciale' AND u.attivo = 1
            AND u.id NOT IN (
                SELECT subordinato_id FROM supervisioni 
                WHERE data_fine IS NULL 
                AND supervisore_id IN (SELECT id FROM utenti WHERE ruolo_base = 'commerciale')
            )
        ''')
        radici = [row['id'] for row in cursor.fetchall()]
        if not radici:
            radici = list(dati_commerciali.keys())
    else:
        radici = [user_id]
    
    albero = []
    gia_mostrati = set()
    
    for radice_id in radici:
        albero_parziale = costruisci_albero_commerciali(
            conn, radice_id, commerciali_visibili,
            dati_commerciali, livello=0, gia_mostrati=gia_mostrati
        )
        albero.extend(albero_parziale)
    
    for item in albero:
        item['dati']['percentuale'] = (item['dati']['canone'] / totale_canone * 100) if totale_canone > 0 else 0
    
    # Dettaglio clienti
    dettaglio_commerciali = {}
    
    for item in albero:
        comm_id = item['id']
        comm_display = item['dati']['commerciale']
        
        cursor.execute('''
            SELECT p_iva, 
                   MAX(NOME_CLIENTE) as nome,
                   COUNT(*) as veicoli,
                   COALESCE(SUM(canone), 0) as canone,
                   GROUP_CONCAT(DISTINCT noleggiatore) as noleggiatori
            FROM veicoli
            WHERE commerciale_id = ?
            GROUP BY p_iva
            ORDER BY nome
        ''', (comm_id,))
        
        clienti = []
        for row in cursor.fetchall():
            c = dict(row)
            if not c['nome']:
                c['nome'] = c['p_iva'] or 'Sconosciuto'
            c['noleggiatori'] = c['noleggiatori'].split(',') if c['noleggiatori'] else []
            clienti.append(c)
        
        cursor.execute('''
            SELECT noleggiatore, COUNT(*) as num
            FROM veicoli
            WHERE commerciale_id = ?
            GROUP BY noleggiatore
            ORDER BY num DESC
        ''', (comm_id,))
        noleggiatori_count = {row['noleggiatore']: row['num'] for row in cursor.fetchall() if row['noleggiatore']}
        
        dettaglio_commerciali[comm_display] = {
            'clienti': clienti,
            'veicoli': item['dati']['veicoli'],
            'canone': item['dati']['canone'],
            'noleggiatori': noleggiatori_count,
            'commerciale_id': comm_id,
            'livello': item['livello'],
        }
    
    # Non assegnato
    senza_commerciale = 0
    if is_admin or puo_gestire_assegnazioni:
        cursor.execute('''
            SELECT COUNT(*) as veicoli,
                   COUNT(DISTINCT p_iva) as clienti,
                   COALESCE(SUM(canone), 0) as canone
            FROM veicoli
            WHERE commerciale_id IS NULL OR commerciale_id = 0
        ''')
        row = cursor.fetchone()
        if row and row['veicoli'] > 0:
            senza_commerciale = row['clienti']
            
            totale_veicoli += row['veicoli']
            totale_clienti += row['clienti']
            totale_canone += row['canone']
            
            albero.append({
                'id': None,
                'livello': 0,
                'dati': {
                    'commerciale_id': None,
                    'commerciale': None,
                    'veicoli': row['veicoli'],
                    'clienti': row['clienti'],
                    'canone': row['canone'],
                    'percentuale': (row['canone'] / totale_canone * 100) if totale_canone > 0 else 0,
                }
            })
            
            cursor.execute('''
                SELECT p_iva, 
                       MAX(NOME_CLIENTE) as nome,
                       COUNT(*) as veicoli,
                       COALESCE(SUM(canone), 0) as canone,
                       GROUP_CONCAT(DISTINCT noleggiatore) as noleggiatori
                FROM veicoli
                WHERE commerciale_id IS NULL OR commerciale_id = 0
                GROUP BY p_iva
                ORDER BY nome
            ''')
            
            clienti_na = []
            for row in cursor.fetchall():
                c = dict(row)
                if not c['nome']:
                    c['nome'] = c['p_iva'] or 'Sconosciuto'
                c['noleggiatori'] = c['noleggiatori'].split(',') if c['noleggiatori'] else []
                clienti_na.append(c)
            
            cursor.execute('''
                SELECT noleggiatore, COUNT(*) as num
                FROM veicoli
                WHERE commerciale_id IS NULL OR commerciale_id = 0
                GROUP BY noleggiatore
                ORDER BY num DESC
            ''')
            noleggiatori_na = {row['noleggiatore']: row['num'] for row in cursor.fetchall() if row['noleggiatore']}
            
            dettaglio_commerciali['Non assegnato'] = {
                'clienti': clienti_na,
                'veicoli': albero[-1]['dati']['veicoli'],
                'canone': albero[-1]['dati']['canone'],
                'noleggiatori': noleggiatori_na,
                'commerciale_id': None,
                'livello': 0,
            }
    
    conn.close()
    
    return render_template('flotta_commerciale.html',
                         riepilogo_globale=riepilogo_globale,
                         totale_veicoli_globale=totale_veicoli_globale,
                         totale_clienti_globale=totale_clienti_globale,
                         totale_canone_globale=totale_canone_globale,
                         albero=albero,
                         dettaglio_commerciali=dettaglio_commerciali,
                         totale_veicoli=totale_veicoli,
                         totale_clienti=totale_clienti,
                         totale_canone=totale_canone,
                         senza_commerciale=senza_commerciale,
                         puo_gestire_assegnazioni=puo_gestire_assegnazioni)


# ==============================================================================
# ROUTE: GESTIONE ASSEGNAZIONI
# ==============================================================================

@flotta_commerciali_bp.route('/flotta/gestione-commerciali')
@login_required
def gestione_commerciali():
    """Pagina gestione massiva assegnazione commerciali."""
    
    conn = get_connection()
    user_id = session.get('user_id')
    if not ha_permesso(conn, user_id, 'flotta_assegnazioni'):
        conn.close()
        flash('Non hai il permesso per accedere a questa pagina.', 'danger')
        return redirect(url_for('flotta_commerciali.flotta_per_commerciale'))
    
    da = request.args.get('da', '')
    q = request.args.get('q', '')
    
    cursor = conn.cursor()
    
    commerciali_assegnabili = get_commerciali_assegnabili(conn)
    commerciali_filtro = get_commerciali_con_clienti(conn)
    
    where_parts = ["1=1"]
    params = []
    
    if da == '0':
        where_parts.append("(commerciale_id IS NULL OR commerciale_id = 0)")
    elif da:
        where_parts.append("commerciale_id = ?")
        params.append(int(da))
    
    if q:
        where_parts.append("NOME_CLIENTE LIKE ?")
        params.append(f'%{q}%')
    
    where_clause = " AND ".join(where_parts)
    
    cursor.execute(f'''
        SELECT 
            p_iva,
            NOME_CLIENTE as nome, 
            COUNT(*) as veicoli, 
            COALESCE(SUM(canone), 0) as canone,
            commerciale_id,
            GROUP_CONCAT(DISTINCT noleggiatore) as noleggiatori
        FROM veicoli
        WHERE p_iva IS NOT NULL AND {where_clause}
        GROUP BY p_iva
        ORDER BY NOME_CLIENTE
    ''', params)
    
    clienti = []
    for row in cursor.fetchall():
        clienti.append({
            'piva': row['p_iva'],
            'nome': row['nome'],
            'veicoli': row['veicoli'],
            'canone': row['canone'],
            'commerciale_id': row['commerciale_id'],
            'commerciale_display': get_commerciale_display(conn, row['commerciale_id']),
            'noleggiatori': row['noleggiatori'].split(',') if row['noleggiatori'] else []
        })
    
    conn.close()
    
    return render_template('flotta_gestione_commerciali.html',
                         commerciali_assegnabili=commerciali_assegnabili,
                         commerciali_filtro=commerciali_filtro,
                         clienti=clienti,
                         da=da,
                         q=q)


@flotta_commerciali_bp.route('/flotta/assegna-commerciali', methods=['POST'])
@login_required
def assegna_commerciali():
    """Assegna commerciale a piu clienti con registrazione storico."""
    
    conn = get_connection()
    user_id = session.get('user_id')
    if not ha_permesso(conn, user_id, 'flotta_assegnazioni'):
        conn.close()
        flash('Non hai il permesso per gestire le assegnazioni.', 'danger')
        return redirect(url_for('flotta_commerciali.flotta_per_commerciale'))
    
    clienti_piva = request.form.getlist('clienti[]')
    commerciale_id = request.form.get('commerciale_id', '')
    note = request.form.get('note', '').strip() or None
    
    if not clienti_piva:
        conn.close()
        return redirect(url_for('flotta_commerciali.gestione_commerciali', error='Nessun cliente selezionato'))
    
    if commerciale_id == '':
        conn.close()
        return redirect(url_for('flotta_commerciali.gestione_commerciali', error='Commerciale non specificato'))
    
    nuovo_commerciale_id = int(commerciale_id) if commerciale_id != '0' else None
    
    cursor = conn.cursor()
    totale_veicoli = 0
    
    for piva in clienti_piva:
        cursor.execute('SELECT nome_cliente FROM clienti WHERE p_iva = ?', (piva,))
        row = cursor.fetchone()
        nome = row['nome_cliente'] if row else piva
        
        result = assegna_cliente(
            conn, piva, nome,
            nuovo_commerciale_id,
            user_id, note
        )
        totale_veicoli += result.get('veicoli_aggiornati', 0)
    
    dest_display = get_commerciale_display(conn, nuovo_commerciale_id)
    conn.close()
    
    return redirect(url_for('flotta_commerciali.gestione_commerciali', 
                          success=f'Assegnati {len(clienti_piva)} clienti ({totale_veicoli} veicoli) a {dest_display}'))
