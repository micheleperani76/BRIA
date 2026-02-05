#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Route Autenticazione
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-20
# Descrizione: Route per login, logout, cambio password, completa profilo
# ==============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .database_utenti import (
    get_connection,
    get_utente_by_username,
    verifica_password,
    cambia_password,
    completa_profilo_utente,
    aggiorna_ultimo_accesso,
    incrementa_tentativi_falliti,
    resetta_tentativi_falliti,
    carica_permessi_utente,
    log_accesso,
    valida_email_dominio
)
from .auth import (
    inizializza_sessione,
    aggiorna_sessione_password_cambiata,
    aggiorna_sessione_profilo_completato,
    termina_sessione,
    get_client_ip,
    get_user_agent
)
import configparser
from pathlib import Path

# ==============================================================================
# BLUEPRINT
# ==============================================================================

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ==============================================================================
# FUNZIONI UTILITÃ&euro;
# ==============================================================================

def get_dominio_email_richiesto():
    """Restituisce il dominio email richiesto se la validazione e attiva."""
    try:
        base_path = Path(__file__).parent.parent
        config_path = base_path / 'impostazioni' / 'email_config.conf'
        
        if not config_path.exists():
            return None
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        if config.getboolean('validazione', 'validazione_dominio_attiva', fallback=False):
            return config.get('validazione', 'dominio_consentito', fallback=None)
        
        return None
    except:
        return None


# ==============================================================================
# ROUTE: LOGIN
# ==============================================================================

@auth_bp.route('/login', methods=['GET'])
def login():
    """Pagina di login."""
    # Se gia loggato, redirect a dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    return render_template('auth/login.html')


@auth_bp.route('/login', methods=['POST'])
def login_submit():
    """Gestisce il submit del form login."""
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    
    # Validazione input
    if not username or not password:
        flash('Inserisci username e password.', 'danger')
        return redirect(url_for('auth.login'))
    
    conn = get_connection()
    ip = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Cerca utente
        utente = get_utente_by_username(conn, username)
        
        if not utente:
            # Log tentativo fallito
            log_accesso(conn, None, 'login_fallito', ip, user_agent, 
                       'Username non trovato', username)
            flash('Credenziali non valide.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Verifica se bloccato
        if utente['bloccato']:
            log_accesso(conn, utente['id'], 'login_bloccato', ip, user_agent,
                       'Utente bloccato per troppi tentativi')
            flash('Account bloccato per troppi tentativi. Contatta l\'amministratore.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Verifica password
        if not verifica_password(utente['password_hash'], password):
            incrementa_tentativi_falliti(conn, username)
            log_accesso(conn, utente['id'], 'login_fallito', ip, user_agent,
                       'Password errata')
            
            tentativi_rimasti = 5 - utente['tentativi_falliti'] - 1
            if tentativi_rimasti > 0:
                flash(f'Credenziali non valide. Tentativi rimasti: {tentativi_rimasti}', 'danger')
            else:
                flash('Account bloccato per troppi tentativi. Contatta l\'amministratore.', 'danger')
            
            return redirect(url_for('auth.login'))
        
        # Login riuscito!
        resetta_tentativi_falliti(conn, utente['id'])
        aggiorna_ultimo_accesso(conn, utente['id'])
        
        # Carica permessi
        permessi = carica_permessi_utente(conn, utente['id'])
        
        # Inizializza sessione
        inizializza_sessione(utente, permessi)
        
        # Log accesso
        log_accesso(conn, utente['id'], 'login_ok', ip, user_agent)
        
        # Redirect in base allo stato utente
        if utente['pwd_temporanea']:
            return redirect(url_for('auth.cambio_password'))
        elif not utente['profilo_completo']:
            return redirect(url_for('auth.completa_profilo'))
        else:
            # flash benvenuto rimosso
            return redirect(url_for('dashboard'))
    
    finally:
        conn.close()


# ==============================================================================
# ROUTE: LOGOUT
# ==============================================================================

@auth_bp.route('/logout')
def logout():
    """Logout utente."""
    if 'user_id' in session:
        conn = get_connection()
        try:
            log_accesso(conn, session['user_id'], 'logout', get_client_ip(), get_user_agent())
        finally:
            conn.close()
    
    termina_sessione()
    flash('Logout effettuato con successo.', 'success')
    return redirect(url_for('auth.login'))


# ==============================================================================
# ROUTE: CAMBIO PASSWORD
# ==============================================================================

@auth_bp.route('/cambio-password', methods=['GET'])
def cambio_password():
    """Pagina cambio password obbligatorio."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Se non deve cambiare password, redirect
    if not session.get('pwd_temporanea'):
        return redirect(url_for('dashboard'))
    
    return render_template('auth/cambio_password.html')


@auth_bp.route('/cambio-password', methods=['POST'])
def cambio_password_submit():
    """Gestisce il cambio password."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    nuova_password = request.form.get('nuova_password', '')
    conferma_password = request.form.get('conferma_password', '')
    
    # Validazione
    if not nuova_password or not conferma_password:
        flash('Compila tutti i campi.', 'danger')
        return redirect(url_for('auth.cambio_password'))
    
    if len(nuova_password) < 8:
        flash('La password deve essere di almeno 8 caratteri.', 'danger')
        return redirect(url_for('auth.cambio_password'))
    
    if nuova_password != conferma_password:
        flash('Le password non corrispondono.', 'danger')
        return redirect(url_for('auth.cambio_password'))
    
    conn = get_connection()
    try:
        # Cambia password
        if cambia_password(conn, session['user_id'], nuova_password):
            aggiorna_sessione_password_cambiata()
            
            log_accesso(conn, session['user_id'], 'cambio_pwd', get_client_ip(), get_user_agent())
            
            flash('Password cambiata con successo!', 'success')
            
            # Se profilo non completo, vai a completare
            if not session.get('profilo_completo'):
                return redirect(url_for('auth.completa_profilo'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Errore durante il cambio password. Riprova.', 'danger')
            return redirect(url_for('auth.cambio_password'))
    
    finally:
        conn.close()


# ==============================================================================
# ROUTE: COMPLETA PROFILO
# ==============================================================================

@auth_bp.route('/completa-profilo', methods=['GET'])
def completa_profilo():
    """Pagina completamento profilo obbligatorio."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Se deve ancora cambiare password, redirect
    if session.get('pwd_temporanea'):
        return redirect(url_for('auth.cambio_password'))
    
    # Se profilo gia completo, redirect
    if session.get('profilo_completo'):
        return redirect(url_for('dashboard'))
    
    dominio = get_dominio_email_richiesto()
    return render_template('auth/completa_profilo.html', dominio_richiesto=dominio)


@auth_bp.route('/completa-profilo', methods=['POST'])
def completa_profilo_submit():
    """Gestisce il completamento profilo."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    nome = request.form.get('nome', '').strip()
    cognome = request.form.get('cognome', '').strip()
    cellulare = request.form.get('cellulare', '').strip()
    email = request.form.get('email', '').strip().lower()
    
    # Validazione campi obbligatori
    if not nome or not cognome or not cellulare or not email:
        flash('Tutti i campi sono obbligatori.', 'danger')
        return redirect(url_for('auth.completa_profilo'))
    
    # Validazione email
    email_valida, messaggio = valida_email_dominio(email)
    if not email_valida:
        flash(messaggio, 'danger')
        return redirect(url_for('auth.completa_profilo'))
    
    conn = get_connection()
    try:
        # Completa profilo
        successo, errore = completa_profilo_utente(conn, session['user_id'], nome, cognome, cellulare, email)
        if successo:
            aggiorna_sessione_profilo_completato(nome, cognome)
            
            log_accesso(conn, session['user_id'], 'profilo_completato', get_client_ip(), get_user_agent(),
                       f'Email: {email}')
            
            flash(f'Benvenuto {nome}! Profilo completato con successo.', 'success')
            return redirect(url_for('dashboard'))
        else:
            if errore:
                flash(errore, 'danger')
            else:
                flash('Errore durante il salvataggio. Riprova.', 'danger')
            return redirect(url_for('auth.completa_profilo'))
    
    finally:
        conn.close()


# ==============================================================================
# ROUTE: PROFILO PERSONALE
# ==============================================================================

@auth_bp.route('/profilo', methods=['GET'])
def profilo():
    """Pagina profilo personale dell'utente."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_connection()
    try:
        from .database_utenti import get_utente_by_id, get_permessi_utente
        
        utente = get_utente_by_id(conn, session['user_id'])
        if not utente:
            flash('Errore nel caricamento del profilo.', 'danger')
            return redirect(url_for('dashboard'))
        
        # Carica permessi con descrizione
        permessi_utente = []
        if utente['ruolo_base'] != 'admin':
            permessi = get_permessi_utente(conn, session['user_id'])
            permessi_utente = [p for p in permessi if p['abilitato']]
        
        dominio = get_dominio_email_richiesto()
        
        return render_template('auth/profilo.html', 
                             utente=utente,
                             permessi_utente=permessi_utente,
                             dominio_richiesto=dominio)
    finally:
        conn.close()


@auth_bp.route('/profilo/salva', methods=['POST'])
def profilo_salva():
    """Salva le modifiche al profilo personale."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    nome = request.form.get('nome', '').strip()
    cognome = request.form.get('cognome', '').strip()
    email = request.form.get('email', '').strip().lower()
    cellulare = request.form.get('cellulare', '').strip()
    data_nascita = request.form.get('data_nascita', '').strip()
    
    # Validazione campi obbligatori
    if not nome or not cognome or not email or not cellulare:
        flash('Nome, cognome, email e cellulare sono obbligatori.', 'danger')
        return redirect(url_for('auth.profilo'))
    
    # Validazione email
    email_valida, messaggio = valida_email_dominio(email)
    if not email_valida:
        flash(messaggio, 'danger')
        return redirect(url_for('auth.profilo'))
    
    conn = get_connection()
    try:
        # Verifica unicità email e cellulare
        from .database_utenti import verifica_unicita_contatti
        valido, errore = verifica_unicita_contatti(conn, session['user_id'], email, cellulare)
        if not valido:
            flash(errore, 'danger')
            return redirect(url_for('auth.profilo'))
        
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE utenti SET
                nome = ?,
                cognome = ?,
                email = ?,
                cellulare = ?,
                data_nascita = ?
            WHERE id = ?
        ''', (nome, cognome, email, cellulare, data_nascita or None, session['user_id']))
        conn.commit()
        
        # Aggiorna sessione
        session['nome'] = nome
        session['cognome'] = cognome
        session['nome_completo'] = f"{nome} {cognome}".strip()
        
        log_accesso(conn, session['user_id'], 'modifica_profilo', get_client_ip(), get_user_agent())
        
        flash('Profilo aggiornato con successo!', 'success')
    finally:
        conn.close()
    
    return redirect(url_for('auth.profilo'))


@auth_bp.route('/cambio-password-volontario', methods=['GET'])
def cambio_password_volontario():
    """Pagina cambio password volontario (non obbligato)."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    return render_template('auth/cambio_password.html', volontario=True)


@auth_bp.route('/cambio-password-volontario', methods=['POST'])
def cambio_password_volontario_submit():
    """Gestisce il cambio password volontario."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    password_attuale = request.form.get('password_attuale', '')
    nuova_password = request.form.get('nuova_password', '')
    conferma_password = request.form.get('conferma_password', '')
    
    if not password_attuale or not nuova_password or not conferma_password:
        flash('Compila tutti i campi.', 'danger')
        return redirect(url_for('auth.cambio_password_volontario'))
    
    if len(nuova_password) < 8:
        flash('La password deve essere di almeno 8 caratteri.', 'danger')
        return redirect(url_for('auth.cambio_password_volontario'))
    
    if nuova_password != conferma_password:
        flash('Le password non corrispondono.', 'danger')
        return redirect(url_for('auth.cambio_password_volontario'))
    
    conn = get_connection()
    try:
        # Verifica password attuale
        utente = get_utente_by_username(conn, session['username'])
        if not utente or not verifica_password(password_attuale, utente['password_hash']):
            flash('Password attuale non corretta.', 'danger')
            return redirect(url_for('auth.cambio_password_volontario'))
        
        # Cambia password
        if cambia_password(conn, session['user_id'], nuova_password):
            log_accesso(conn, session['user_id'], 'cambio_pwd_volontario', get_client_ip(), get_user_agent())
            flash('Password cambiata con successo!', 'success')
            return redirect(url_for('auth.profilo'))
        else:
            flash('Errore durante il cambio password.', 'danger')
            return redirect(url_for('auth.cambio_password_volontario'))
    finally:
        conn.close()


# ==============================================================================
# ROUTE LEGACY (redirect)
# ==============================================================================

# Per retrocompatibilita con eventuali link vecchi
@auth_bp.route('/')
def auth_index():
    return redirect(url_for('auth.login'))
