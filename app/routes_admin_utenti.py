#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Route Admin Utenti
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-20
# Descrizione: Route per gestione utenti (CRUD, permessi, reset password)
# ==============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from .database_utenti import (
    get_connection,
    get_tutti_utenti,
    get_utente_by_id,
    crea_utente,
    reset_password,
    sblocca_utente,
    get_permessi_per_categoria,
    get_permessi_utente,
    assegna_permesso,
    assegna_permessi_default_ruolo,
    aggiungi_supervisione,
    rimuovi_supervisione,
    get_subordinati_diretti,
    get_supervisori_diretti,
    log_attivita
)
from .auth import login_required, permesso_richiesto
from datetime import datetime

# ==============================================================================
# BLUEPRINT
# ==============================================================================

admin_utenti_bp = Blueprint('admin_utenti', __name__, url_prefix='/admin/utenti')


# ==============================================================================
# LISTA UTENTI
# ==============================================================================

@admin_utenti_bp.route('/')
@login_required
@permesso_richiesto('admin_utenti')
def lista_utenti():
    """Lista di tutti gli utenti con info ultimo accesso e rete."""
    conn = get_connection()
    try:
        utenti = get_tutti_utenti(conn, solo_attivi=False)
        
        # Aggiungi info ultimo accesso con rete per ogni utente
        from .database_utenti import get_ultimo_accesso_con_rete
        for utente in utenti:
            utente['ultimo_accesso'] = get_ultimo_accesso_con_rete(conn, utente['id'])
        
        # Verifica se c'e una nuova password da mostrare
        nuova_password = session.pop('nuova_password', None)
        nuovo_username = session.pop('nuovo_username', None)
        
        return render_template('admin/utenti_lista.html', 
                             utenti=utenti,
                             nuova_password=nuova_password,
                             nuovo_username=nuovo_username)
    finally:
        conn.close()



# ==============================================================================
# NUOVO UTENTE
# ==============================================================================

@admin_utenti_bp.route('/nuovo', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def nuovo_utente():
    """Crea un nuovo utente."""
    username = request.form.get('username', '').strip().lower()
    ruolo_base = request.form.get('ruolo_base', 'operatore')
    
    # Validazione
    if not username:
        flash('Username obbligatorio.', 'danger')
        return redirect(url_for('admin_utenti.lista_utenti'))
    
    # Verifica caratteri validi
    import re
    if not re.match(r'^[a-z0-9._]+$', username):
        flash('Username puo contenere solo lettere minuscole, numeri, punti e underscore.', 'danger')
        return redirect(url_for('admin_utenti.lista_utenti'))
    
    conn = get_connection()
    try:
        risultato = crea_utente(conn, username, session.get('user_id'))
        
        if risultato:
            # Aggiorna ruolo se diverso da default
            if ruolo_base != 'operatore':
                cursor = conn.cursor()
                cursor.execute("UPDATE utenti SET ruolo_base = ? WHERE id = ?", 
                             (ruolo_base, risultato['id']))
                conn.commit()
            
            # Log attivita
            log_attivita(conn, session['user_id'], 'crea', 'utente', risultato['id'],
                        f"Creato utente {username}")
            
            
            # Assegna permessi default in base al ruolo
            assegna_permessi_default_ruolo(conn, risultato['id'], ruolo_base, session.get('user_id'))
            # Salva password in sessione per mostrarla
            session['nuova_password'] = risultato['password_temporanea']
            session['nuovo_username'] = username
            
            flash(f'Utente {username} creato con successo!', 'success')
        else:
            flash(f'Errore: username "{username}" gia esistente.', 'danger')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.lista_utenti'))


# ==============================================================================
# RESET PASSWORD
# ==============================================================================

@admin_utenti_bp.route('/reset-password', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def reset_password_utente():
    """Resetta la password di un utente."""
    utente_id = request.form.get('utente_id', type=int)
    
    if not utente_id:
        flash('ID utente non valido.', 'danger')
        return redirect(url_for('admin_utenti.lista_utenti'))
    
    conn = get_connection()
    try:
        # Verifica che l'utente esista e non sia admin di sistema
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if utente['non_modificabile']:
            flash('Non e possibile resettare la password di questo utente.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        nuova_pwd = reset_password(conn, utente_id, session.get('user_id'))
        
        if nuova_pwd:
            # Log attivita
            log_attivita(conn, session['user_id'], 'reset_pwd', 'utente', utente_id,
                        f"Reset password per {utente['username']}")
            
            # Salva password in sessione per mostrarla
            session['nuova_password'] = nuova_pwd
            session['nuovo_username'] = utente['username']
            
            flash(f'Password resettata per {utente["username"]}!', 'success')
        else:
            flash('Errore durante il reset della password.', 'danger')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.lista_utenti'))


# ==============================================================================
# SBLOCCA UTENTE
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/sblocca', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def sblocca_utente_route(utente_id):
    """Sblocca un utente bloccato."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            return jsonify({'success': False, 'error': 'Utente non trovato'})
        
        if sblocca_utente(conn, utente_id):
            log_attivita(conn, session['user_id'], 'sblocca', 'utente', utente_id,
                        f"Sbloccato utente {utente['username']}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Errore durante lo sblocco'})
    
    finally:
        conn.close()


# ==============================================================================
# DETTAGLIO/MODIFICA UTENTE
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>')
@login_required
@permesso_richiesto('admin_utenti')
def dettaglio_utente(utente_id):
    """Pagina dettaglio/modifica utente."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        # Carica permessi
        permessi_catalogo = get_permessi_per_categoria(conn)
        permessi_utente = {p['codice']: p['abilitato'] for p in get_permessi_utente(conn, utente_id)}
        
        # Carica supervisioni
        supervisori = get_supervisori_diretti(conn, utente_id)
        subordinati = get_subordinati_diretti(conn, utente_id)
        
        # Lista utenti per assegnare supervisioni
        tutti_utenti = get_tutti_utenti(conn, solo_attivi=True)
        
        # Lista commerciali dalla flotta (per campo nome_commerciale_flotta)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT commerciale FROM veicoli 
            WHERE commerciale IS NOT NULL AND commerciale != ''
            ORDER BY commerciale
        ''')
        commerciali_flotta = [row[0] for row in cursor.fetchall()]
        
        return render_template('admin/utente_dettaglio.html',
                             utente=utente,
                             permessi_catalogo=permessi_catalogo,
                             permessi_utente=permessi_utente,
                             supervisori=supervisori,
                             subordinati=subordinati,
                             tutti_utenti=tutti_utenti,
                             commerciali_flotta=commerciali_flotta)
    finally:
        conn.close()


# ==============================================================================
# SALVA PERMESSI
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/permessi', methods=['POST'])
@login_required
@permesso_richiesto('admin_permessi')
def salva_permessi(utente_id):
    """Salva i permessi di un utente."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if utente['non_modificabile']:
            flash('Non e possibile modificare i permessi di questo utente.', 'danger')
            return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        # Ottieni tutti i permessi dal catalogo
        permessi_catalogo = get_permessi_per_categoria(conn)
        
        # Per ogni permesso, verifica se e stato selezionato
        permessi_selezionati = request.form.getlist('permessi')
        
        for categoria, permessi in permessi_catalogo.items():
            for perm in permessi:
                abilitato = perm['codice'] in permessi_selezionati
                assegna_permesso(conn, utente_id, perm['codice'], abilitato, session.get('user_id'))
        
        log_attivita(conn, session['user_id'], 'modifica_permessi', 'utente', utente_id,
                    f"Modificati permessi per {utente['username']}")
        
        flash('Permessi salvati con successo!', 'success')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


# ==============================================================================
# MODIFICA NOME COMMERCIALE FLOTTA
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/commerciale-flotta', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def modifica_commerciale_flotta(utente_id):
    """Modifica il nome commerciale flotta di un utente."""
    nome_commerciale = request.form.get('nome_commerciale_flotta', '').strip().upper()
    
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if utente['non_modificabile']:
            flash('Non e possibile modificare questo utente.', 'danger')
            return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        # Aggiorna nome commerciale flotta
        from .database_utenti import set_nome_commerciale_utente
        set_nome_commerciale_utente(conn, utente_id, nome_commerciale if nome_commerciale else None)
        
        log_attivita(conn, session['user_id'], 'modifica_commerciale', 'utente', utente_id,
                    f"Commerciale flotta per {utente['username']}: {nome_commerciale or 'RIMOSSO'}")
        
        flash(f'Nome commerciale flotta aggiornato: {nome_commerciale or "(rimosso)"}', 'success')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


# ==============================================================================
# MODIFICA RUOLO
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/ruolo', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def modifica_ruolo(utente_id):
    """Modifica il ruolo base di un utente."""
    nuovo_ruolo = request.form.get('ruolo_base')
    
    if nuovo_ruolo not in ['admin', 'commerciale', 'operatore', 'viewer']:
        flash('Ruolo non valido.', 'danger')
        return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
    
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if utente['non_modificabile']:
            flash('Non e possibile modificare questo utente.', 'danger')
            return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        vecchio_ruolo = utente['ruolo_base']
        msg_trasferimento = ''
        
        # Se passa da commerciale ad altro ruolo: trasferisci clienti
        if vecchio_ruolo == 'commerciale' and nuovo_ruolo != 'commerciale':
            from .gestione_commerciali import gestisci_cambio_ruolo_commerciale
            
            result = gestisci_cambio_ruolo_commerciale(conn, utente_id, session.get('user_id'))
            
            if result['clienti_trasferiti'] > 0:
                msg_trasferimento = f" - {result['clienti_trasferiti']} clienti trasferiti a {result['destinazione_display']}"
        
        cursor = conn.cursor()
        cursor.execute("UPDATE utenti SET ruolo_base = ? WHERE id = ?", (nuovo_ruolo, utente_id))
        conn.commit()
        
        # Assegna automaticamente i permessi default per il nuovo ruolo
        assegna_permessi_default_ruolo(conn, utente_id, nuovo_ruolo, session.get('user_id'))
        
        log_attivita(conn, session['user_id'], 'modifica_ruolo', 'utente', utente_id,
                    f"Cambiato ruolo da {vecchio_ruolo} a {nuovo_ruolo} (permessi aggiornati){msg_trasferimento}")
        
        flash(f'Ruolo aggiornato a {nuovo_ruolo} con permessi!{msg_trasferimento}', 'success')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


# ==============================================================================
# MODIFICA USERNAME
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/modifica-username', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def modifica_username(utente_id):
    """Modifica lo username di un utente."""
    nuovo_username = request.form.get('nuovo_username', '').strip().lower()
    
    if not nuovo_username:
        flash('Username obbligatorio.', 'danger')
        return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
    
    # Validazione formato username
    import re
    if not re.match(r'^[a-z0-9._]+$', nuovo_username):
        flash('Username non valido. Solo lettere minuscole, numeri, punti e underscore.', 'danger')
        return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
    
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if utente['non_modificabile']:
            flash('Non e possibile modificare questo utente.', 'danger')
            return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        # Verifica che il nuovo username non sia gia in uso
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM utenti WHERE username = ? AND id != ?", (nuovo_username, utente_id))
        if cursor.fetchone():
            flash(f'Username "{nuovo_username}" gia in uso da un altro utente.', 'danger')
            return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        vecchio_username = utente['username']
        
        cursor.execute("UPDATE utenti SET username = ? WHERE id = ?", (nuovo_username, utente_id))
        conn.commit()
        
        log_attivita(conn, session['user_id'], 'modifica_username', 'utente', utente_id,
                    f"Username cambiato da {vecchio_username} a {nuovo_username}")
        
        flash(f'Username cambiato da "{vecchio_username}" a "{nuovo_username}"!', 'success')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


# ==============================================================================
# MODIFICA ANAGRAFICA
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/modifica-anagrafica', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def modifica_anagrafica(utente_id):
    """Modifica i dati anagrafici di un utente."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if utente['non_modificabile']:
            flash('Non e possibile modificare questo utente.', 'danger')
            return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        cursor = conn.cursor()
        modifiche = []
        
        # Campi modificabili
        campi = {
            'codice_utente': request.form.get('codice_utente', '').strip(),
            'nome': request.form.get('nome', '').strip(),
            'cognome': request.form.get('cognome', '').strip(),
            'data_nascita': request.form.get('data_nascita', '').strip(),
            'email': request.form.get('email', '').strip(),
            'cellulare': request.form.get('cellulare', '').strip()
        }
        
        # Verifica codice_utente unico se modificato
        if campi['codice_utente'] and campi['codice_utente'] != utente.get('codice_utente', ''):
            cursor.execute("SELECT id FROM utenti WHERE codice_utente = ? AND id != ?", 
                          (campi['codice_utente'], utente_id))
            if cursor.fetchone():
                flash(f'Codice utente "{campi["codice_utente"]}" gia in uso.', 'danger')
                return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        # Verifica email unica se modificata
        if campi['email'] and campi['email'] != (utente.get('email') or ''):
            cursor.execute("SELECT id FROM utenti WHERE email = ? AND id != ?", 
                          (campi['email'], utente_id))
            if cursor.fetchone():
                flash(f'Email "{campi["email"]}" gia in uso da un altro utente.', 'danger')
                return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        # Costruisci UPDATE dinamico solo per i campi con valori
        update_fields = []
        update_values = []
        
        for campo, valore in campi.items():
            if valore:  # Solo se il campo ha un valore
                vecchio_valore = utente.get(campo) or ''
                if valore != vecchio_valore:
                    update_fields.append(f"{campo} = ?")
                    update_values.append(valore)
                    modifiche.append(f"{campo}: {vecchio_valore} -> {valore}")
        
        if update_fields:
            update_values.append(utente_id)
            query = f"UPDATE utenti SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, update_values)
            conn.commit()
            
            log_attivita(conn, session['user_id'], 'modifica_anagrafica', 'utente', utente_id,
                        '; '.join(modifiche))
            
            flash('Dati anagrafici aggiornati con successo!', 'success')
        else:
            flash('Nessuna modifica effettuata.', 'info')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


# ==============================================================================
# ATTIVA/DISATTIVA UTENTE
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/toggle-attivo', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def toggle_attivo(utente_id):
    """Attiva o disattiva un utente."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            return jsonify({'success': False, 'error': 'Utente non trovato'})
        
        if utente['non_cancellabile']:
            return jsonify({'success': False, 'error': 'Non e possibile disattivare questo utente'})
        
        nuovo_stato = 0 if utente['attivo'] else 1
        clienti_trasferiti = 0
        destinazione = None
        
        # Se disattivo un commerciale: trasferisci clienti
        if nuovo_stato == 0 and utente['ruolo_base'] == 'commerciale':
            from .gestione_commerciali import gestisci_cambio_ruolo_commerciale
            
            result = gestisci_cambio_ruolo_commerciale(conn, utente_id, session.get('user_id'))
            clienti_trasferiti = result['clienti_trasferiti']
            destinazione = result['destinazione_display']
        
        cursor = conn.cursor()
        cursor.execute("UPDATE utenti SET attivo = ? WHERE id = ?", (nuovo_stato, utente_id))
        conn.commit()
        
        azione = 'attivato' if nuovo_stato else 'disattivato'
        msg_extra = f" - {clienti_trasferiti} clienti trasferiti a {destinazione}" if clienti_trasferiti > 0 else ""
        log_attivita(conn, session['user_id'], azione, 'utente', utente_id,
                    f"Utente {utente['username']} {azione}{msg_extra}")
        
        return jsonify({
            'success': True, 
            'attivo': nuovo_stato,
            'clienti_trasferiti': clienti_trasferiti,
            'destinazione': destinazione
        })
    
    finally:
        conn.close()


@admin_utenti_bp.route('/<int:utente_id>/toggle-attivo-form', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def toggle_attivo_form(utente_id):
    """Attiva o disattiva un utente (versione form con redirect)."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if utente['non_cancellabile']:
            flash('Non e possibile disattivare questo utente.', 'danger')
            return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
        
        nuovo_stato = 0 if utente['attivo'] else 1
        msg_trasferimento = ''
        
        # Se disattivo un commerciale: trasferisci clienti
        if nuovo_stato == 0 and utente['ruolo_base'] == 'commerciale':
            from .gestione_commerciali import gestisci_cambio_ruolo_commerciale
            
            result = gestisci_cambio_ruolo_commerciale(conn, utente_id, session.get('user_id'))
            
            if result['clienti_trasferiti'] > 0:
                msg_trasferimento = f" - {result['clienti_trasferiti']} clienti trasferiti a {result['destinazione_display']}"
        
        cursor = conn.cursor()
        cursor.execute("UPDATE utenti SET attivo = ? WHERE id = ?", (nuovo_stato, utente_id))
        conn.commit()
        
        azione = 'attivato' if nuovo_stato else 'disattivato'
        log_attivita(conn, session['user_id'], azione, 'utente', utente_id,
                    f"Utente {utente['username']} {azione}{msg_trasferimento}")
        
        flash(f'Utente {utente["username"]} {azione}!{msg_trasferimento}', 'success')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


@admin_utenti_bp.route('/<int:utente_id>/sblocca-form', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def sblocca_utente_form(utente_id):
    """Sblocca un utente (versione form con redirect)."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        if sblocca_utente(conn, utente_id):
            log_attivita(conn, session['user_id'], 'sblocca', 'utente', utente_id,
                        f"Sbloccato utente {utente['username']}")
            flash(f'Utente {utente["username"]} sbloccato!', 'success')
        else:
            flash('Errore durante lo sblocco.', 'danger')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


# ==============================================================================
# GESTIONE SUPERVISIONI
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/supervisione/aggiungi', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def aggiungi_supervisione_route(utente_id):
    """Aggiunge una supervisione."""
    tipo = request.form.get('tipo')  # 'supervisore' o 'subordinato'
    altro_id = request.form.get('altro_id', type=int)
    
    if not altro_id or tipo not in ['supervisore', 'subordinato']:
        flash('Dati non validi.', 'danger')
        return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
    
    conn = get_connection()
    try:
        if tipo == 'supervisore':
            # altro_id diventa supervisore di utente_id
            aggiungi_supervisione(conn, altro_id, utente_id)
        else:
            # utente_id diventa supervisore di altro_id
            aggiungi_supervisione(conn, utente_id, altro_id)
        
        flash('Supervisione aggiunta!', 'success')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))


@admin_utenti_bp.route('/<int:utente_id>/supervisione/rimuovi', methods=['POST'])
@login_required
@permesso_richiesto('admin_utenti')
def rimuovi_supervisione_route(utente_id):
    """Rimuove una supervisione."""
    tipo = request.form.get('tipo')
    altro_id = request.form.get('altro_id', type=int)
    
    if not altro_id or tipo not in ['supervisore', 'subordinato']:
        flash('Dati non validi.', 'danger')
        return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
    
    conn = get_connection()
    try:
        if tipo == 'supervisore':
            rimuovi_supervisione(conn, altro_id, utente_id)
        else:
            rimuovi_supervisione(conn, utente_id, altro_id)
        
        flash('Supervisione rimossa!', 'success')
    
    finally:
        conn.close()
    
    return redirect(url_for('admin_utenti.dettaglio_utente', utente_id=utente_id))
# ==============================================================================
# ROUTE LOG ACCESSI - Da aggiungere a routes_admin_utenti.py
# ==============================================================================


# ==============================================================================
# LOG ACCESSI UTENTE
# ==============================================================================

@admin_utenti_bp.route('/<int:utente_id>/log')
@login_required
@permesso_richiesto('admin_utenti')
def log_utente(utente_id):
    """Visualizza log accessi di un utente specifico."""
    conn = get_connection()
    try:
        utente = get_utente_by_id(conn, utente_id)
        if not utente:
            flash('Utente non trovato.', 'danger')
            return redirect(url_for('admin_utenti.lista_utenti'))
        
        # Parametri
        filtro_tipo = request.args.get('tipo', '')
        
        # Config
        from .database_utenti import get_config_retention, get_log_accessi_utente, get_statistiche_accessi_utente
        config = get_config_retention()
        
        # Log
        logs = get_log_accessi_utente(conn, utente_id, limite=200)
        
        # Filtra per tipo se specificato
        if filtro_tipo:
            logs = [l for l in logs if l['tipo_evento'] == filtro_tipo]
        
        # Statistiche
        statistiche = get_statistiche_accessi_utente(conn, utente_id)
        
        return render_template('admin/log_accessi.html',
                             utente=utente,
                             logs=logs,
                             totale=len(logs),
                             statistiche=statistiche,
                             retention_giorni=config['log_accessi_giorni'],
                             mostra_ip=config['mostra_ip'],
                             filtro_tipo=filtro_tipo,
                             pagine=1,
                             pagina_corrente=1)
    finally:
        conn.close()


# ==============================================================================
# LOG ACCESSI GLOBALE
# ==============================================================================

@admin_utenti_bp.route('/log')
@login_required
@permesso_richiesto('admin_utenti')
def log_globale():
    """Visualizza tutti i log accessi."""
    conn = get_connection()
    try:
        # Parametri
        pagina = request.args.get('pagina', 1, type=int)
        filtro_tipo = request.args.get('tipo', '')
        
        # Config
        from .database_utenti import get_config_retention, get_log_accessi_tutti
        config = get_config_retention()
        
        # Log con paginazione
        risultato = get_log_accessi_tutti(conn, pagina, filtro_tipo if filtro_tipo else None)
        
        return render_template('admin/log_accessi.html',
                             utente=None,
                             logs=risultato['log'],
                             totale=risultato['totale'],
                             statistiche=None,
                             retention_giorni=config['log_accessi_giorni'],
                             mostra_ip=config['mostra_ip'],
                             filtro_tipo=filtro_tipo,
                             pagine=risultato['pagine'],
                             pagina_corrente=risultato['pagina_corrente'])
    finally:
        conn.close()


# ==============================================================================
# STORICO ASSEGNAZIONI COMMERCIALI
# ==============================================================================

@admin_utenti_bp.route('/storico-assegnazioni')
@login_required
@permesso_richiesto('flotta_assegnazioni')
def storico_assegnazioni():
    """Visualizza lo storico delle assegnazioni commerciali raggruppato per cliente."""
    from .gestione_commerciali import (
        get_commerciali_tutti,
        get_commerciale_display,
        get_commerciali_assegnabili
    )
    
    conn = get_connection()
    try:
        # Parametri filtro
        pagina = request.args.get('pagina', 1, type=int)
        filtro_commerciale = request.args.get('commerciale', type=int)
        filtro_cliente = request.args.get('cliente', '').strip()
        
        per_pagina = 50
        cursor = conn.cursor()
        
        # Query raggruppata per cliente
        # Prendo l'ultimo record per ogni cliente e conto i cambiamenti
        query_base = '''
            SELECT 
                sa.cliente_piva,
                sa.cliente_nome,
                MAX(sa.data_ora) as ultima_modifica,
                COUNT(*) as num_cambi,
                (SELECT commerciale_nuovo_id FROM storico_assegnazioni 
                 WHERE cliente_piva = sa.cliente_piva 
                 ORDER BY data_ora DESC LIMIT 1) as commerciale_attuale_id
            FROM storico_assegnazioni sa
            WHERE 1=1
        '''
        params = []
        
        if filtro_commerciale:
            query_base += ' AND sa.cliente_piva IN (SELECT DISTINCT cliente_piva FROM storico_assegnazioni WHERE commerciale_nuovo_id = ? OR commerciale_precedente_id = ?)'
            params.extend([filtro_commerciale, filtro_commerciale])
        
        if filtro_cliente:
            query_base += ' AND (sa.cliente_piva LIKE ? OR sa.cliente_nome LIKE ?)'
            params.extend([f'%{filtro_cliente}%', f'%{filtro_cliente}%'])
        
        query_base += ' GROUP BY sa.cliente_piva'
        
        # Conta totale clienti per paginazione
        count_query = f'SELECT COUNT(*) as cnt FROM ({query_base})'
        cursor.execute(count_query, params)
        totale_clienti = cursor.fetchone()['cnt']
        
        # Calcola pagine
        pagine = (totale_clienti + per_pagina - 1) // per_pagina if totale_clienti > 0 else 1
        if pagina > pagine:
            pagina = pagine
        if pagina < 1:
            pagina = 1
        
        offset = (pagina - 1) * per_pagina
        
        # Query con paginazione
        query_finale = query_base + ' ORDER BY ultima_modifica DESC LIMIT ? OFFSET ?'
        params.extend([per_pagina, offset])
        
        cursor.execute(query_finale, params)
        
        clienti_storico = []
        for row in cursor.fetchall():
            clienti_storico.append({
                'cliente_piva': row['cliente_piva'],
                'cliente_nome': row['cliente_nome'] or row['cliente_piva'],
                'ultima_modifica': row['ultima_modifica'],
                'num_cambi': row['num_cambi'],
                'commerciale_attuale': get_commerciale_display(conn, row['commerciale_attuale_id']),
                'commerciale_attuale_id': row['commerciale_attuale_id']
            })
        
        # Conta totale assegnazioni
        cursor.execute('SELECT COUNT(*) as cnt FROM storico_assegnazioni')
        totale_assegnazioni = cursor.fetchone()['cnt']
        
        # Lista commerciali per dropdown filtro
        commerciali = get_commerciali_tutti(conn, solo_attivi=False)
        
        # Lista commerciali assegnabili per dropdown assegnazione
        commerciali_assegnabili = get_commerciali_assegnabili(conn)
        
        return render_template('admin/storico_assegnazioni.html',
                             clienti_storico=clienti_storico,
                             totale_clienti=totale_clienti,
                             totale_assegnazioni=totale_assegnazioni,
                             commerciali=commerciali,
                             commerciali_assegnabili=commerciali_assegnabili,
                             filtro_commerciale=filtro_commerciale,
                             filtro_cliente=filtro_cliente,
                             pagina_corrente=pagina,
                             pagine=pagine)
    finally:
        conn.close()


@admin_utenti_bp.route('/storico-assegnazioni/<piva>/dettaglio')
@login_required
@permesso_richiesto('flotta_assegnazioni')
def storico_assegnazioni_dettaglio(piva):
    """Restituisce lo storico completo di un cliente in JSON."""
    from .gestione_commerciali import get_commerciale_display
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Tutti i record per questo cliente, ordinati dal piu' recente
        cursor.execute('''
            SELECT sa.*, u_op.username as operatore_username
            FROM storico_assegnazioni sa
            LEFT JOIN utenti u_op ON sa.operatore_id = u_op.id
            WHERE sa.cliente_piva = ?
            ORDER BY sa.data_ora DESC
        ''', (piva,))
        
        storico = []
        for row in cursor.fetchall():
            storico.append({
                'id': row['id'],
                'data_ora': row['data_ora'],
                'da': get_commerciale_display(conn, row['commerciale_precedente_id']),
                'a': get_commerciale_display(conn, row['commerciale_nuovo_id']),
                'operatore': row['operatore_username'] or 'SYSTEM',
                'tipo': row['tipo'],
                'note': row['note']
            })
        
        # Info cliente
        cursor.execute('''
            SELECT cliente_nome FROM storico_assegnazioni 
            WHERE cliente_piva = ? LIMIT 1
        ''', (piva,))
        row = cursor.fetchone()
        cliente_nome = row['cliente_nome'] if row else piva
        
        return jsonify({
            'success': True,
            'cliente_piva': piva,
            'cliente_nome': cliente_nome,
            'storico': storico
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@admin_utenti_bp.route('/storico-assegnazioni/<piva>/assegna', methods=['POST'])
@login_required
@permesso_richiesto('flotta_assegnazioni')
def assegna_commerciale_cliente(piva):
    """API: Assegna un commerciale a un cliente."""
    from .gestione_commerciali import assegna_cliente, get_commerciale_display
    
    conn = get_connection()
    try:
        commerciale_id = request.form.get('commerciale_id', type=int)
        note = request.form.get('note', '').strip()
        
        if commerciale_id is None:
            return jsonify({'success': False, 'error': 'Commerciale non specificato'})
        
        # Recupera nome cliente dalla tabella clienti
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nome_cliente, ragione_sociale, commerciale_id 
            FROM clienti WHERE p_iva = ?
        ''', (piva,))
        row = cursor.fetchone()
        
        if row:
            cliente_nome = row['nome_cliente'] or row['ragione_sociale'] or piva
        else:
            # Prova dallo storico
            cursor.execute('''
                SELECT cliente_nome FROM storico_assegnazioni 
                WHERE cliente_piva = ? LIMIT 1
            ''', (piva,))
            row2 = cursor.fetchone()
            cliente_nome = row2['cliente_nome'] if row2 else piva
        
        # Esegui assegnazione
        operatore_id = session.get('user_id')
        success = assegna_cliente(
            conn, piva, cliente_nome, 
            commerciale_id if commerciale_id > 0 else None,
            operatore_id,
            note=note or 'Assegnazione da gestione storico'
        )
        
        if success:
            conn.commit()
            nuovo_display = get_commerciale_display(conn, commerciale_id) if commerciale_id > 0 else 'Non assegnato'
            return jsonify({
                'success': True, 
                'message': f'Cliente assegnato a {nuovo_display}',
                'nuovo_commerciale': nuovo_display
            })
        else:
            return jsonify({'success': False, 'error': 'Errore durante assegnazione'})
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


# ==============================================================================
# GESTIONE EX-COMMERCIALI CLIENTE
# ==============================================================================

@admin_utenti_bp.route('/ex-commerciali/<cliente_piva>')
@login_required
@permesso_richiesto('flotta_assegnazioni')
def get_ex_commerciali(cliente_piva):
    """API: Restituisce lista ex-commerciali di un cliente."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ec.*, u.username as inserito_da_username
            FROM ex_commerciali_cliente ec
            LEFT JOIN utenti u ON ec.inserito_da = u.id
            WHERE ec.cliente_piva = ?
            ORDER BY ec.data_fine DESC, ec.data_inizio DESC
        ''', (cliente_piva,))
        
        ex_commerciali = []
        for row in cursor.fetchall():
            ex_commerciali.append({
                'id': row['id'],
                'nome_commerciale': row['nome_commerciale'],
                'data_inizio': row['data_inizio'],
                'data_fine': row['data_fine'],
                'note': row['note'],
                'inserito_da': row['inserito_da_username'] or 'Sistema'
            })
        
        return jsonify({'success': True, 'ex_commerciali': ex_commerciali})
    finally:
        conn.close()


@admin_utenti_bp.route('/ex-commerciali/<cliente_piva>/aggiungi', methods=['POST'])
@login_required
@permesso_richiesto('flotta_assegnazioni')
def aggiungi_ex_commerciale(cliente_piva):
    """API: Aggiunge un ex-commerciale a un cliente."""
    nome = request.form.get('nome_commerciale', '').strip()
    data_inizio = request.form.get('data_inizio', '').strip() or None
    data_fine = request.form.get('data_fine', '').strip() or None
    note = request.form.get('note', '').strip() or None
    
    if not nome:
        return jsonify({'success': False, 'error': 'Nome commerciale obbligatorio'})
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ex_commerciali_cliente 
            (cliente_piva, nome_commerciale, data_inizio, data_fine, note, inserito_da, data_inserimento)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_piva, nome, data_inizio, data_fine, note, 
              session.get('user_id'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        
        return jsonify({'success': True, 'id': cursor.lastrowid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@admin_utenti_bp.route('/ex-commerciali/elimina/<int:ex_id>', methods=['POST'])
@login_required
@permesso_richiesto('flotta_assegnazioni')
def elimina_ex_commerciale(ex_id):
    """API: Elimina un ex-commerciale."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ex_commerciali_cliente WHERE id = ?', (ex_id,))
        conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()
