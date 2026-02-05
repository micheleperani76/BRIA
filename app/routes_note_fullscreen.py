# ==============================================================================
# ROUTE NOTE FULLSCREEN - Da aggiungere a web_server.py
# ==============================================================================
# Inserire queste route PRIMA della route run_server()
# ==============================================================================

# ------------------------------------------------------------------------------
# ROUTE: Note Fullscreen
# ------------------------------------------------------------------------------

@app.route('/cliente/<int:cliente_id>/note')
def note_fullscreen(cliente_id):
    """Vista fullscreen per gestione note cliente."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Recupera cliente
    cursor.execute('SELECT * FROM clienti WHERE id = ?', (cliente_id,))
    cliente = cursor.fetchone()
    
    if not cliente:
        conn.close()
        return "Cliente non trovato", 404
    
    cliente = dict(cliente)
    
    # Recupera note ordinate (pinnate prima, poi per data)
    cursor.execute('''
        SELECT n.*, 
               (SELECT GROUP_CONCAT(a.id || '::' || a.nome_originale, '|||') 
                FROM allegati_note_clienti a WHERE a.nota_id = n.id) as allegati_raw
        FROM note_clienti n
        WHERE n.cliente_id = ?
        ORDER BY n.fissata DESC, n.data_creazione DESC
    ''', (cliente_id,))
    
    note_rows = cursor.fetchall()
    note_cliente = []
    
    for row in note_rows:
        nota = dict(row)
        # Parse allegati
        nota['allegati'] = []
        if nota.get('allegati_raw'):
            for a in nota['allegati_raw'].split('|||'):
                if '::' in a:
                    aid, nome = a.split('::', 1)
                    nota['allegati'].append({'id': int(aid), 'nome_originale': nome})
        del nota['allegati_raw']
        note_cliente.append(nota)
    
    # Nota attiva (da parametro o prima disponibile)
    nota_id = request.args.get('nota', type=int)
    nota_attiva = None
    nota_attiva_id = None
    
    if nota_id:
        for n in note_cliente:
            if n['id'] == nota_id:
                nota_attiva = n
                nota_attiva_id = nota_id
                break
    elif note_cliente:
        nota_attiva = note_cliente[0]
        nota_attiva_id = note_cliente[0]['id']
    
    # Lista commerciali per dropdown autore
    cursor.execute('''
        SELECT DISTINCT commerciale FROM clienti 
        WHERE commerciale IS NOT NULL AND commerciale != ''
        ORDER BY commerciale
    ''')
    commerciali = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('note_fullscreen.html',
                         cliente=cliente,
                         note_cliente=note_cliente,
                         nota_attiva=nota_attiva,
                         nota_attiva_id=nota_attiva_id,
                         commerciali=commerciali)


# API note sono ora in routes_note_clienti.py
