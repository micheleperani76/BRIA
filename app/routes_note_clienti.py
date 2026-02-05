#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Motore Note Clienti
# ==============================================================================
# Versione: 2.0.0
# Data: 2025-01-21
# Descrizione: Unico punto di gestione per tutte le operazioni sulle note clienti
#              Usato sia dalla vista compatta (dettaglio) che fullscreen
# ==============================================================================

from flask import Blueprint, request, jsonify, session, redirect, url_for, send_file
from datetime import datetime
from pathlib import Path
import uuid
from werkzeug.utils import secure_filename

from app.database import get_connection
from app.auth import login_required
from app.config_percorsi import get_cliente_allegati_path, CLIENTI_DIR

# Blueprint
note_clienti_bp = Blueprint('note_clienti', __name__, url_prefix='/api/note-clienti')

# Estensioni permesse per allegati
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==============================================================================
# CRUD NOTE
# ==============================================================================

@note_clienti_bp.route('/<int:cliente_id>/lista')
@login_required
def lista_note(cliente_id):
    """Lista note attive di un cliente."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT n.*, 
                   u_crea.cognome as creato_da_nome,
                   u_mod.cognome as modificato_da_nome
            FROM note_clienti n
            LEFT JOIN utenti u_crea ON n.creato_da_id = u_crea.id
            LEFT JOIN utenti u_mod ON n.modificato_da_id = u_mod.id
            WHERE n.cliente_id = ? AND (n.eliminato = 0 OR n.eliminato IS NULL)
            ORDER BY n.fissata DESC, n.data_creazione DESC
        ''', (cliente_id,))
        
        note = []
        for row in cursor.fetchall():
            nota = dict(row)
            # Carica allegati
            cursor.execute('''
                SELECT id, nome_originale, nome_salvato, percorso, dimensione, tipo_mime
                FROM allegati_note WHERE nota_cliente_id = ?
            ''', (nota['id'],))
            nota['allegati'] = [dict(a) for a in cursor.fetchall()]
            note.append(nota)
        
        return jsonify({'success': True, 'note': note})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/<int:cliente_id>/crea', methods=['POST'])
@login_required
def crea_nota(cliente_id):
    """Crea una nuova nota."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Dati dal form o JSON
        if request.is_json:
            data = request.get_json()
            titolo = data.get('titolo', 'Nuova nota')
            testo = data.get('testo', '')
        else:
            titolo = request.form.get('titolo', 'Nuova nota').strip()
            testo = request.form.get('testo', '').strip()
        
        if not titolo:
            return jsonify({'success': False, 'error': 'Titolo obbligatorio'})
        
        # Autore da sessione
        user_id = session.get('user_id')
        autore = session.get('cognome', session.get('username', 'Sistema'))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO note_clienti 
            (cliente_id, titolo, testo, autore, data_creazione, creato_da_id, fissata, eliminato)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        ''', (cliente_id, titolo, testo or None, autore, now, user_id))
        
        nota_id = cursor.lastrowid
        
        # Gestisci allegati se presenti
        if not request.is_json:
            files = request.files.getlist('allegati')
            if files and files[0].filename:
                _salva_allegati(cursor, cliente_id, nota_id, files, autore, now)
        
        conn.commit()
        return jsonify({'success': True, 'nota_id': nota_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/<int:cliente_id>/<int:nota_id>/modifica', methods=['POST'])
@login_required
def modifica_nota(cliente_id, nota_id):
    """Modifica una nota esistente."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Dati dal form o JSON
        if request.is_json:
            data = request.get_json()
            titolo = data.get('titolo', '')
            testo = data.get('testo', '')
            fissata = data.get('fissata', 0)
        else:
            titolo = request.form.get('titolo', '').strip()
            testo = request.form.get('testo', '').strip()
            fissata = request.form.get('fissata', 0)
        
        if not titolo:
            return jsonify({'success': False, 'error': 'Titolo obbligatorio'})
        
        # Chi modifica
        user_id = session.get('user_id')
        autore_modifica = session.get('cognome', session.get('username', 'Sistema'))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Aggiorna nota - NON modifica autore originale
        cursor.execute('''
            UPDATE note_clienti 
            SET titolo = ?, testo = ?, fissata = ?, data_modifica = ?, modificato_da_id = ?
            WHERE id = ? AND cliente_id = ? AND (eliminato = 0 OR eliminato IS NULL)
        ''', (titolo, testo or None, fissata, now, user_id, nota_id, cliente_id))
        
        # Gestisci nuovi allegati se presenti
        if not request.is_json:
            files = request.files.getlist('allegati')
            if files and files[0].filename:
                _salva_allegati(cursor, cliente_id, nota_id, files, autore_modifica, now)
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/<int:cliente_id>/<int:nota_id>/elimina', methods=['POST'])
@login_required
def elimina_nota(cliente_id, nota_id):
    """Soft delete - sposta nel cestino."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        username = session.get('cognome', session.get('username', 'Sistema'))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            UPDATE note_clienti 
            SET eliminato = 1, data_eliminazione = ?, eliminato_da = ?
            WHERE id = ? AND cliente_id = ?
        ''', (now, username, nota_id, cliente_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Nota non trovata'})
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/<int:cliente_id>/<int:nota_id>/fissa', methods=['POST'])
@login_required
def fissa_nota(cliente_id, nota_id):
    """Toggle fissa/sfissa nota."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Leggi stato attuale
        cursor.execute('SELECT fissata FROM note_clienti WHERE id = ? AND cliente_id = ?', (nota_id, cliente_id))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Nota non trovata'})
        
        nuovo_stato = 0 if row['fissata'] else 1
        
        cursor.execute('''
            UPDATE note_clienti SET fissata = ? WHERE id = ? AND cliente_id = ?
        ''', (nuovo_stato, nota_id, cliente_id))
        
        conn.commit()
        return jsonify({'success': True, 'fissata': nuovo_stato})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


# ==============================================================================
# CESTINO
# ==============================================================================

@note_clienti_bp.route('/<int:cliente_id>/cestino')
@login_required
def lista_cestino(cliente_id):
    """Lista note nel cestino."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, titolo, testo, autore, data_creazione, data_eliminazione, eliminato_da
            FROM note_clienti 
            WHERE cliente_id = ? AND eliminato = 1
            ORDER BY data_eliminazione DESC
        ''', (cliente_id,))
        
        note = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'note': note})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/<int:cliente_id>/<int:nota_id>/ripristina', methods=['POST'])
@login_required
def ripristina_nota(cliente_id, nota_id):
    """Ripristina nota dal cestino."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE note_clienti 
            SET eliminato = 0, data_eliminazione = NULL, eliminato_da = NULL
            WHERE id = ? AND cliente_id = ?
        ''', (nota_id, cliente_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Nota non trovata'})
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/<int:cliente_id>/<int:nota_id>/elimina-definitivo', methods=['POST'])
@login_required
def elimina_definitivo(cliente_id, nota_id):
    """Elimina definitivamente nota e allegati."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Elimina file allegati fisici
        cursor.execute('SELECT percorso FROM allegati_note WHERE nota_cliente_id = ?', (nota_id,))
        for row in cursor.fetchall():
            try:
                percorso = Path(row['percorso'])
                if percorso.exists():
                    percorso.unlink()
                # Rimuovi cartella se vuota
                if percorso.parent.exists() and not any(percorso.parent.iterdir()):
                    percorso.parent.rmdir()
            except Exception as e:
                print(f"Errore eliminazione file: {e}")
        
        # Elimina record allegati
        cursor.execute('DELETE FROM allegati_note WHERE nota_cliente_id = ?', (nota_id,))
        
        # Elimina nota
        cursor.execute('DELETE FROM note_clienti WHERE id = ? AND cliente_id = ?', (nota_id, cliente_id))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


# ==============================================================================
# ALLEGATI
# ==============================================================================

@note_clienti_bp.route('/<int:cliente_id>/<int:nota_id>/allegati', methods=['POST'])
@login_required
def carica_allegati(cliente_id, nota_id):
    """Carica allegati per una nota."""
    if 'allegati' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun file'})
    
    files = request.files.getlist('allegati')
    if not files or not files[0].filename:
        return jsonify({'success': False, 'error': 'Nessun file selezionato'})
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Verifica nota esiste
        cursor.execute('SELECT id FROM note_clienti WHERE id = ? AND cliente_id = ?', (nota_id, cliente_id))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': 'Nota non trovata'})
        
        autore = session.get('cognome', session.get('username', 'Sistema'))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        allegati_salvati = _salva_allegati(cursor, cliente_id, nota_id, files, autore, now)
        
        conn.commit()
        return jsonify({'success': True, 'allegati': allegati_salvati})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/allegato/<int:allegato_id>/elimina', methods=['POST'])
@login_required
def elimina_allegato(allegato_id):
    """Elimina un allegato."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Recupera percorso
        cursor.execute('SELECT percorso FROM allegati_note WHERE id = ?', (allegato_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Allegato non trovato'})
        
        # Elimina file fisico
        try:
            percorso = Path(row['percorso'])
            if percorso.exists():
                percorso.unlink()
        except Exception as e:
            print(f"Errore eliminazione file: {e}")
        
        # Elimina record
        cursor.execute('DELETE FROM allegati_note WHERE id = ?', (allegato_id,))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@note_clienti_bp.route('/allegato/<int:allegato_id>/scarica')
@login_required
def scarica_allegato(allegato_id):
    """Scarica un allegato."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT percorso, nome_originale FROM allegati_note WHERE id = ?', (allegato_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'error': 'Allegato non trovato'})
        
        percorso = Path(row['percorso'])
        if not percorso.exists():
            return jsonify({'success': False, 'error': 'File non trovato'})
        
        return send_file(str(percorso), download_name=row['nome_originale'], as_attachment=True)
    finally:
        conn.close()


# ==============================================================================
# FUNZIONI HELPER PRIVATE
# ==============================================================================

def _salva_allegati(cursor, cliente_id, nota_id, files, autore, now):
    """Salva allegati su disco e nel DB. Restituisce lista allegati salvati."""
    # Recupera dati cliente per path
    cursor.execute('SELECT p_iva, cod_fiscale FROM clienti WHERE id = ?', (cliente_id,))
    cliente = cursor.fetchone()
    
    if cliente:
        cliente_allegati_dir = get_cliente_allegati_path(dict(cliente))
        nota_dir = cliente_allegati_dir / f"nota_{nota_id}"
    else:
        nota_dir = CLIENTI_DIR / f"id_{cliente_id}" / "allegati_note" / f"nota_{nota_id}"
    
    nota_dir.mkdir(parents=True, exist_ok=True)
    
    allegati_salvati = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            nome_originale = secure_filename(file.filename)
            nome_salvato = f"{uuid.uuid4().hex[:8]}_{nome_originale}"
            percorso = nota_dir / nome_salvato
            
            file.save(str(percorso))
            
            cursor.execute('''
                INSERT INTO allegati_note 
                (nota_cliente_id, nome_originale, nome_salvato, percorso, dimensione, tipo_mime, data_upload, caricato_da)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nota_id, nome_originale, nome_salvato, str(percorso),
                  percorso.stat().st_size, file.content_type, now, autore))
            
            allegati_salvati.append({
                'id': cursor.lastrowid,
                'nome_originale': nome_originale,
                'dimensione': percorso.stat().st_size
            })
    
    return allegati_salvati


# ==============================================================================
# ROUTE LEGACY (compatibilita con vecchie chiamate)
# ==============================================================================

def register_note_clienti_legacy_routes(app):
    """
    Registra route legacy per compatibilita con codice esistente.
    Queste route processano direttamente i form POST dalla vista ristretta.
    """
    
    # -------------------------------------------------------------------------
    # FORM POST - Vista piccola (dettaglio.html)
    # -------------------------------------------------------------------------
    
    @app.route('/cliente/<int:cliente_id>/nota/nuova', methods=['POST'])
    @login_required
    def legacy_nuova_nota(cliente_id):
        """Crea nota da form POST (vista ristretta)."""
        import logging
        logger = logging.getLogger('web_server')
        
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            titolo = request.form.get('titolo', '').strip()
            testo = request.form.get('testo', '').strip()
            
            logger.info(f"Creazione nota: cliente={cliente_id}, titolo={titolo}")
            
            if not titolo:
                logger.warning("Titolo vuoto, nota non creata")
                return redirect(url_for('dettaglio_cliente', cliente_id=cliente_id))
            
            user_id = session.get('user_id')
            autore = session.get('cognome', session.get('username', 'Sistema'))
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Inserimento nota: autore={autore}, user_id={user_id}")
            
            cursor.execute('''
                INSERT INTO note_clienti 
                (cliente_id, titolo, testo, autore, data_creazione, creato_da_id, fissata, eliminato)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            ''', (cliente_id, titolo, testo or None, autore, now, user_id))
            
            nota_id = cursor.lastrowid
            logger.info(f"Nota creata con ID: {nota_id}")
            
            # Gestisci allegati
            files = request.files.getlist('allegati')
            if files and files[0].filename:
                _salva_allegati(cursor, cliente_id, nota_id, files, autore, now)
            
            conn.commit()
            logger.info(f"Commit OK per nota {nota_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"ERRORE creazione nota: {e}", exc_info=True)
        finally:
            conn.close()
        
        return redirect(url_for('dettaglio_cliente', cliente_id=cliente_id))
    
    @app.route('/cliente/<int:cliente_id>/nota/modifica', methods=['POST'])
    @login_required
    def legacy_modifica_nota(cliente_id):
        """Modifica nota da form POST (vista ristretta)."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            nota_id = request.form.get('nota_id')
            titolo = request.form.get('titolo', '').strip()
            testo = request.form.get('testo', '').strip()
            
            if not nota_id or not titolo:
                return redirect(url_for('dettaglio_cliente', cliente_id=cliente_id))
            
            user_id = session.get('user_id')
            autore_modifica = session.get('cognome', session.get('username', 'Sistema'))
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                UPDATE note_clienti 
                SET titolo = ?, testo = ?, data_modifica = ?, modificato_da_id = ?
                WHERE id = ? AND cliente_id = ? AND (eliminato = 0 OR eliminato IS NULL)
            ''', (titolo, testo or None, now, user_id, nota_id, cliente_id))
            
            # Gestisci nuovi allegati
            files = request.files.getlist('allegati')
            if files and files[0].filename:
                _salva_allegati(cursor, cliente_id, int(nota_id), files, autore_modifica, now)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Errore modifica nota: {e}")
        finally:
            conn.close()
        
        return redirect(url_for('dettaglio_cliente', cliente_id=cliente_id))
    
    @app.route('/cliente/<int:cliente_id>/nota/elimina', methods=['POST'])
    @login_required  
    def legacy_elimina_nota(cliente_id):
        """Soft delete nota da form POST (vista ristretta)."""
        nota_id = request.form.get('nota_id')
        if nota_id:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                username = session.get('cognome', session.get('username', 'Sistema'))
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    UPDATE note_clienti 
                    SET eliminato = 1, data_eliminazione = ?, eliminato_da = ?
                    WHERE id = ? AND cliente_id = ?
                ''', (now, username, nota_id, cliente_id))
                conn.commit()
            finally:
                conn.close()
        return redirect(url_for('dettaglio_cliente', cliente_id=cliente_id))
    
    @app.route('/cliente/<int:cliente_id>/nota/fissa', methods=['POST'])
    @login_required
    def legacy_fissa_nota(cliente_id):
        """Toggle fissa/sfissa nota da form POST."""
        nota_id = request.form.get('nota_id')
        nuovo_stato = 0
        if nota_id:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT fissata FROM note_clienti WHERE id = ?', (nota_id,))
                row = cursor.fetchone()
                if row:
                    nuovo_stato = 0 if row['fissata'] else 1
                    cursor.execute('UPDATE note_clienti SET fissata = ? WHERE id = ?', (nuovo_stato, nota_id))
                    conn.commit()
            finally:
                conn.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'fissata': nuovo_stato})
        return redirect(url_for('dettaglio_cliente', cliente_id=cliente_id))
    
    # API vecchie (fullscreen)
    @app.route('/api/cliente/<int:cliente_id>/nota/nuova', methods=['POST'])
    @login_required
    def legacy_api_crea_nota(cliente_id):
        return crea_nota(cliente_id)
    
    @app.route('/api/cliente/<int:cliente_id>/nota/<int:nota_id>/salva', methods=['POST'])
    @login_required
    def legacy_api_salva_nota(cliente_id, nota_id):
        return modifica_nota(cliente_id, nota_id)
    
    @app.route('/api/cliente/<int:cliente_id>/nota/<int:nota_id>/elimina', methods=['POST'])
    @login_required
    def legacy_api_elimina_nota(cliente_id, nota_id):
        return elimina_nota(cliente_id, nota_id)
    
    @app.route('/api/cliente/<int:cliente_id>/note/eliminate')
    @login_required
    def legacy_api_cestino(cliente_id):
        return lista_cestino(cliente_id)
    
    @app.route('/api/nota/<int:nota_id>/ripristina', methods=['POST'])
    @login_required
    def legacy_api_ripristina(nota_id):
        # Trova cliente_id dalla nota
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT cliente_id FROM note_clienti WHERE id = ?', (nota_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute('''
                    UPDATE note_clienti 
                    SET eliminato = 0, data_eliminazione = NULL, eliminato_da = NULL
                    WHERE id = ?
                ''', (nota_id,))
                conn.commit()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Nota non trovata'})
        finally:
            conn.close()
    
    @app.route('/api/nota/<int:nota_id>/elimina-definitivo', methods=['POST'])
    @login_required
    def legacy_api_elimina_definitivo(nota_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT cliente_id FROM note_clienti WHERE id = ?', (nota_id,))
            row = cursor.fetchone()
            if row:
                cliente_id = row['cliente_id']
                # Chiama la funzione unificata
                cursor.execute('SELECT percorso FROM allegati_note WHERE nota_cliente_id = ?', (nota_id,))
                for r in cursor.fetchall():
                    try:
                        p = Path(r['percorso'])
                        if p.exists():
                            p.unlink()
                    except:
                        pass
                cursor.execute('DELETE FROM allegati_note WHERE nota_cliente_id = ?', (nota_id,))
                cursor.execute('DELETE FROM note_clienti WHERE id = ?', (nota_id,))
                conn.commit()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Nota non trovata'})
        finally:
            conn.close()
    
    @app.route('/api/cliente/<int:cliente_id>/nota/<int:nota_id>/allegato', methods=['POST'])
    @login_required
    def legacy_api_carica_allegato(cliente_id, nota_id):
        return carica_allegati(cliente_id, nota_id)
    
    @app.route('/api/allegato/<int:allegato_id>/elimina', methods=['POST'])
    @login_required
    def legacy_api_elimina_allegato(allegato_id):
        return elimina_allegato(allegato_id)
