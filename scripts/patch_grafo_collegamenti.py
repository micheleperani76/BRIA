#!/usr/bin/env python3
# ==============================================================================
# PATCH: Aggiunge API /api/cliente/<id>/grafo-collegamenti
# ==============================================================================
# Versione: 1.1.0
# Data: 2026-02-11
# Descrizione: Endpoint per grafo D3.js multi-livello
#              - Livello 1: collegamenti diretti (verde)
#              - Livello 2: collegamenti dei collegati (giallo)
#              - Livello 3: stesso capogruppo (azzurro, automatico)
#
# Uso: python3 scripts/patch_grafo_collegamenti.py
# ==============================================================================

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ROUTES_FILE = BASE_DIR / 'app' / 'routes_collegamenti_clienti.py'

CODICE_API_GRAFO = '''

# ==============================================================================
# ROUTE: API GRAFO COLLEGAMENTI (multi-livello per D3.js)
# ==============================================================================

@collegamenti_bp.route('/api/cliente/<int:cliente_id>/grafo-collegamenti')
@login_required
def api_grafo_collegamenti(cliente_id):
    """
    Ritorna nodi e archi per il grafo D3.js force-directed.
    Livello 1: collegamenti diretti del cliente (verde)
    Livello 2: collegamenti dei collegati (giallo)
    Livello 3: clienti con stesso capogruppo (azzurro, automatico)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Nodo centrale
        cursor.execute("SELECT id, COALESCE(ragione_sociale, nome_cliente) as nome FROM clienti WHERE id = ?", (cliente_id,))
        row_centro = cursor.fetchone()
        if not row_centro:
            conn.close()
            return jsonify({'success': False, 'error': 'Cliente non trovato'})

        nodi = {cliente_id: {'id': cliente_id, 'nome': row_centro['nome'], 'livello': 0}}
        archi = []
        archi_set = set()  # Per evitare duplicati

        # === LIVELLO 1: collegamenti diretti ===
        cursor.execute("""
            SELECT 
                cc.tipo_relazione,
                cc.cliente_a_id,
                cc.cliente_b_id,
                CASE WHEN cc.cliente_a_id = ? THEN cc.cliente_b_id ELSE cc.cliente_a_id END as altro_id,
                c.ragione_sociale as altro_nome
            FROM collegamenti_clienti cc
            JOIN clienti c ON c.id = CASE WHEN cc.cliente_a_id = ? THEN cc.cliente_b_id ELSE cc.cliente_a_id END
            WHERE (cc.cliente_a_id = ? OR cc.cliente_b_id = ?)
            AND cc.attivo = 1
        """, (cliente_id, cliente_id, cliente_id, cliente_id))

        collegati_livello1 = []
        for row in cursor.fetchall():
            altro_id = row['altro_id']
            collegati_livello1.append(altro_id)

            if altro_id not in nodi:
                nodi[altro_id] = {'id': altro_id, 'nome': row['altro_nome'] or 'N/D', 'livello': 1}

            usa_inverso = (row['cliente_b_id'] == cliente_id)
            desc = get_descrizione_per_vista(row['tipo_relazione'], usa_inverso=usa_inverso)

            arco_key = tuple(sorted([cliente_id, altro_id]))
            if arco_key not in archi_set:
                archi_set.add(arco_key)
                archi.append({
                    'source': cliente_id,
                    'target': altro_id,
                    'relazione': desc,
                    'livello': 1
                })

        # === LIVELLO 2: collegamenti dei collegati ===
        for collegato_id in collegati_livello1:
            cursor.execute("""
                SELECT 
                    cc.tipo_relazione,
                    cc.cliente_a_id,
                    cc.cliente_b_id,
                    CASE WHEN cc.cliente_a_id = ? THEN cc.cliente_b_id ELSE cc.cliente_a_id END as altro_id,
                    c.ragione_sociale as altro_nome
                FROM collegamenti_clienti cc
                JOIN clienti c ON c.id = CASE WHEN cc.cliente_a_id = ? THEN cc.cliente_b_id ELSE cc.cliente_a_id END
                WHERE (cc.cliente_a_id = ? OR cc.cliente_b_id = ?)
                AND cc.attivo = 1
            """, (collegato_id, collegato_id, collegato_id, collegato_id))

            for row in cursor.fetchall():
                altro_id = row['altro_id']
                if altro_id == cliente_id:
                    continue

                if altro_id not in nodi:
                    nodi[altro_id] = {'id': altro_id, 'nome': row['altro_nome'] or 'N/D', 'livello': 2}

                usa_inverso = (row['cliente_b_id'] == collegato_id)
                desc = get_descrizione_per_vista(row['tipo_relazione'], usa_inverso=usa_inverso)

                arco_key = tuple(sorted([collegato_id, altro_id]))
                if arco_key not in archi_set:
                    archi_set.add(arco_key)
                    archi.append({
                        'source': collegato_id,
                        'target': altro_id,
                        'relazione': desc,
                        'livello': 2
                    })

        # === LIVELLO 3: stesso capogruppo (automatico, solo per CF/PIVA) ===
        cursor.execute("""
            SELECT id, nome, codice_fiscale
            FROM capogruppo_clienti
            WHERE cliente_id = ?
            AND codice_fiscale IS NOT NULL AND TRIM(codice_fiscale) != ''
        """, (cliente_id,))
        capogruppo_miei = cursor.fetchall()

        for cg in capogruppo_miei:
            cg_nome = cg['nome']
            cg_cf = cg['codice_fiscale'].strip()

            # Match SOLO per CF/PIVA (dato univoco, no omonimie)
            cursor.execute("""
                SELECT DISTINCT cg2.cliente_id, 
                       COALESCE(c.ragione_sociale, c.nome_cliente) as nome_cliente,
                       cg2.nome as cg_nome
                FROM capogruppo_clienti cg2
                JOIN clienti c ON c.id = cg2.cliente_id
                WHERE UPPER(TRIM(cg2.codice_fiscale)) = UPPER(TRIM(?))
                AND cg2.cliente_id != ?
            """, (cg_cf, cliente_id))

            for row in cursor.fetchall():
                altro_id = row['cliente_id']

                if altro_id not in nodi:
                    nodi[altro_id] = {'id': altro_id, 'nome': row['nome_cliente'] or 'N/D', 'livello': 3}

                arco_key = tuple(sorted([cliente_id, altro_id]))
                if arco_key not in archi_set:
                    archi_set.add(arco_key)
                    archi.append({
                        'source': cliente_id,
                        'target': altro_id,
                        'relazione': 'Capogruppo: ' + cg_nome,
                        'livello': 3
                    })

        conn.close()

        return jsonify({
            'success': True,
            'nodi': list(nodi.values()),
            'archi': archi
        })

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})
'''

def main():
    print("=" * 60)
    print("  PATCH: API Grafo Collegamenti (con capogruppo)")
    print("=" * 60)

    if not ROUTES_FILE.exists():
        print(f"ERRORE: File non trovato: {ROUTES_FILE}")
        sys.exit(1)

    contenuto = ROUTES_FILE.read_text(encoding='utf-8')

    if 'grafo-collegamenti' in contenuto:
        print("  SKIP - API grafo gia' presente")
        return

    contenuto += CODICE_API_GRAFO

    ROUTES_FILE.write_text(contenuto, encoding='utf-8')
    print("  OK - API /api/cliente/<id>/grafo-collegamenti aggiunta (con capogruppo)")

if __name__ == '__main__':
    main()
