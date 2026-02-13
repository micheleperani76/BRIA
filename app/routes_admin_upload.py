# ==============================================================================
# ROUTES_ADMIN_UPLOAD.PY - Upload Multi-File e Import CRM + Creditsafe
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Gestisce upload multi-tipo (PDF+CSV), import con priorita',
#              toggle promemoria CRM, flag utenti per notifica.
#
# Route:
#   POST /admin/upload-files       Upload multi-file (PDF + CSV)
#   POST /admin/import-all-async   Import combinato con priorita'
#   GET  /admin/import-all-status  Polling progress multi-fase
#   POST /admin/toggle-promemoria-crm  Toggle ON/OFF globale
#   POST /admin/flag-notifica-crm  Assegna/rimuovi flag utente
#   GET  /admin/upload-info        Info file in attesa
# ==============================================================================

import sys
import re
import threading
from pathlib import Path
from datetime import datetime

from flask import Blueprint, request, jsonify
from app.database import get_connection
from app.auth import login_required

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

BASE_DIR = Path(__file__).parent.parent.absolute()
PDF_DIR = BASE_DIR / 'pdf'
IMPORT_DIR = BASE_DIR / 'import_dati'
SCRIPTS_DIR = BASE_DIR / 'scripts'

# Pattern riconoscimento file
FILE_PATTERNS = {
    'accounts':  re.compile(r'^Accounts[_\s].*\.csv$', re.IGNORECASE),
    'scadenze':  re.compile(r'^Scadenze[_\s].*\.csv$', re.IGNORECASE),
    'contacts':  re.compile(r'^Contacts[_\s].*\.csv$', re.IGNORECASE),
    'creditsafe': re.compile(r'^.*\.pdf$', re.IGNORECASE),
}

# Ordine priorita' import
ORDINE_IMPORT = ['accounts', 'scadenze', 'contacts', 'creditsafe']

# Label per UI
LABEL_TIPO = {
    'accounts': 'Accounts CRM (Clienti)',
    'scadenze': 'Scadenze CRM (Veicoli)',
    'contacts': 'Contacts CRM (Referenti)',
    'creditsafe': 'PDF Creditsafe',
    'sconosciuto': 'File non riconosciuto',
}

ICONA_TIPO = {
    'accounts': 'bi-building',
    'scadenze': 'bi-car-front',
    'contacts': 'bi-person-lines-fill',
    'creditsafe': 'bi-file-pdf',
    'sconosciuto': 'bi-question-circle',
}

COLORE_TIPO = {
    'accounts': 'primary',
    'scadenze': 'success',
    'contacts': 'info',
    'creditsafe': 'danger',
    'sconosciuto': 'secondary',
}

# ==============================================================================
# BLUEPRINT
# ==============================================================================

admin_upload_bp = Blueprint('admin_upload', __name__)

# Stato import globale (per polling)
import_all_status = {
    'running': False,
    'fase_corrente': '',
    'fase_num': 0,
    'fase_totale': 0,
    'current': 0,
    'total': 0,
    'current_file': '',
    'fasi_completate': [],
    'risultati': {},
    'errori_globali': [],
}


# ==============================================================================
# UTILITY
# ==============================================================================

def classifica_file(filename):
    """Classifica un file in base al pattern del nome."""
    for tipo, pattern in FILE_PATTERNS.items():
        if pattern.match(filename):
            return tipo
    return 'sconosciuto'


def conta_file_in_attesa():
    """Conta i file in attesa per tipo."""
    conteggi = {
        'accounts': 0,
        'scadenze': 0,
        'contacts': 0,
        'creditsafe': 0,
    }

    # CSV in import_dati/
    if IMPORT_DIR.exists():
        for f in IMPORT_DIR.glob('*.csv'):
            tipo = classifica_file(f.name)
            if tipo in conteggi:
                conteggi[tipo] += 1

    # PDF in pdf/
    if PDF_DIR.exists():
        conteggi['creditsafe'] = len(list(PDF_DIR.glob('*.pdf')))

    return conteggi


# ==============================================================================
# ROUTE: INFO FILE IN ATTESA
# ==============================================================================

@admin_upload_bp.route('/admin/upload-info')
@login_required
def upload_info():
    """Info file in attesa di elaborazione."""
    conteggi = conta_file_in_attesa()
    totale = sum(conteggi.values())

    dettaglio = []
    for tipo in ORDINE_IMPORT:
        if conteggi.get(tipo, 0) > 0:
            # Lista nomi file
            if tipo == 'creditsafe':
                nomi = sorted([f.name for f in PDF_DIR.glob('*.pdf')])
            else:
                nomi = sorted([
                    f.name for f in IMPORT_DIR.glob('*.csv')
                    if classifica_file(f.name) == tipo
                ])
            dettaglio.append({
                'tipo': tipo,
                'label': LABEL_TIPO[tipo],
                'icona': ICONA_TIPO[tipo],
                'colore': COLORE_TIPO[tipo],
                'conteggio': conteggi[tipo],
                'file': nomi,
            })

    return jsonify({
        'success': True,
        'totale': totale,
        'conteggi': conteggi,
        'dettaglio': dettaglio,
    })


# ==============================================================================
# ROUTE: UPLOAD MULTI-FILE
# ==============================================================================

@admin_upload_bp.route('/admin/upload-files', methods=['POST'])
@login_required
def upload_files():
    """Upload multi-file: PDF + CSV con smistamento automatico."""
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun file ricevuto'}), 400

    files = request.files.getlist('files[]')
    risultati = {
        'uploaded': [],
        'rejected': [],
        'per_tipo': {},
    }

    for file in files:
        if file.filename == '' or not file.filename:
            continue

        filename = file.filename
        tipo = classifica_file(filename)

        if tipo == 'sconosciuto':
            risultati['rejected'].append({
                'nome': filename,
                'motivo': 'Tipo file non riconosciuto. Accettati: PDF Creditsafe, Accounts_*.csv, Scadenze_*.csv, Contacts_*.csv',
            })
            continue

        try:
            # Destinazione
            if tipo == 'creditsafe':
                dest_dir = PDF_DIR
            else:
                dest_dir = IMPORT_DIR

            dest_dir.mkdir(parents=True, exist_ok=True)
            filepath = dest_dir / filename

            # Se esiste gia', sovrascrivi (CSV aggiornati)
            if tipo != 'creditsafe' and filepath.exists():
                filepath.unlink()

            # Per PDF, gestisci duplicati
            if tipo == 'creditsafe' and filepath.exists():
                base = filepath.stem
                i = 1
                while filepath.exists():
                    filepath = dest_dir / f"{base}_{i}.pdf"
                    i += 1

            file.save(str(filepath))

            risultati['uploaded'].append({
                'nome': filepath.name,
                'tipo': tipo,
                'label': LABEL_TIPO[tipo],
                'icona': ICONA_TIPO[tipo],
                'colore': COLORE_TIPO[tipo],
                'size_kb': round(filepath.stat().st_size / 1024),
            })

            # Conteggio per tipo
            if tipo not in risultati['per_tipo']:
                risultati['per_tipo'][tipo] = 0
            risultati['per_tipo'][tipo] += 1

        except Exception as e:
            risultati['rejected'].append({
                'nome': filename,
                'motivo': str(e),
            })

    return jsonify({
        'success': True,
        'count': len(risultati['uploaded']),
        'rejected_count': len(risultati['rejected']),
        'risultati': risultati,
    })


# ==============================================================================
# ROUTE: IMPORT COMBINATO ASINCRONO
# ==============================================================================

@admin_upload_bp.route('/admin/import-all-async', methods=['POST'])
@login_required
def import_all_async():
    """Avvia import multi-fase con priorita'."""
    global import_all_status

    if import_all_status['running']:
        return jsonify({'success': False, 'error': 'Import gia\' in corso'}), 400

    conteggi = conta_file_in_attesa()
    totale = sum(conteggi.values())

    if totale == 0:
        return jsonify({'success': False, 'error': 'Nessun file da elaborare'}), 400

    # Determina fasi da eseguire
    fasi = []
    for tipo in ORDINE_IMPORT:
        if conteggi.get(tipo, 0) > 0:
            fasi.append(tipo)

    # Reset stato
    import_all_status = {
        'running': True,
        'fase_corrente': '',
        'fase_num': 0,
        'fase_totale': len(fasi),
        'current': 0,
        'total': 0,
        'current_file': '',
        'fasi_completate': [],
        'risultati': {},
        'errori_globali': [],
    }

    def run_import_all():
        global import_all_status

        try:
            # Backup DB prima di qualsiasi import
            import shutil as _shutil
            _db = BASE_DIR / 'db' / 'gestionale.db'
            _bak_dir = BASE_DIR / 'backup'
            _bak_dir.mkdir(exist_ok=True)
            _ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            _shutil.copy2(str(_db), str(_bak_dir / f'gestionale.db.bak_import_all_{_ts}'))
            import_all_status['backup'] = f'gestionale.db.bak_import_all_{_ts}'

            for fase_idx, tipo in enumerate(fasi):
                import_all_status['fase_corrente'] = tipo
                import_all_status['fase_num'] = fase_idx + 1

                if tipo == 'creditsafe':
                    _importa_fase_creditsafe()
                elif tipo == 'accounts':
                    _importa_fase_csv('accounts')
                elif tipo == 'scadenze':
                    _importa_fase_csv('scadenze')
                elif tipo == 'contacts':
                    _importa_fase_csv('contacts')

                import_all_status['fasi_completate'].append(tipo)

        except Exception as e:
            import_all_status['errori_globali'].append(
                f"Errore generale: {str(e)}")
        finally:
            import_all_status['running'] = False
            import_all_status['fase_corrente'] = ''
            import_all_status['current_file'] = ''

    thread = threading.Thread(target=run_import_all)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'fasi': fasi,
        'fasi_label': [LABEL_TIPO[f] for f in fasi],
        'totale_file': totale,
        'message': 'Import avviato',
    })


def _importa_fase_csv(tipo):
    """Importa una fase CSV (accounts, scadenze, contacts)."""
    global import_all_status

    # Trova il file CSV
    if not IMPORT_DIR.exists():
        import_all_status['risultati'][tipo] = {
            'success': False, 'error': 'Cartella import_dati non trovata'}
        return

    pattern_map = {
        'accounts': 'Accounts',
        'scadenze': 'Scadenze',
        'contacts': 'Contacts',
    }
    prefisso = pattern_map[tipo]

    csv_files = sorted([
        f for f in IMPORT_DIR.glob('*.csv')
        if classifica_file(f.name) == tipo
    ], key=lambda f: f.name, reverse=True)

    if not csv_files:
        import_all_status['risultati'][tipo] = {
            'success': True, 'message': 'Nessun file trovato'}
        return

    # Prendi il piu' recente
    csv_file = csv_files[0]
    import_all_status['current_file'] = csv_file.name
    import_all_status['current'] = 0
    import_all_status['total'] = 1

    # Aggiungi scripts/ al path
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    try:
        if tipo == 'accounts':
            from import_accounts_crm import importa_accounts
            stats = importa_accounts(str(csv_file), dry_run=False)
            import_all_status['risultati']['accounts'] = {
                'success': True,
                'aggiornati': stats.get('clienti_aggiornati', 0),
                'creati': stats.get('clienti_creati', 0),
                'errori': stats.get('clienti_errore', 0),
                'totale_csv': stats.get('totale_csv', 0),
            }

        elif tipo == 'scadenze':
            from import_scadenze_crm import importa_scadenze
            stats = importa_scadenze(str(csv_file), dry_run=False)
            import_all_status['risultati']['scadenze'] = {
                'success': True,
                'creati': stats.get('attivi_creati', 0), 'aggiornati_scad': stats.get('attivi_aggiornati', 0),
                'storicizzati': stats.get('storicizzati', 0),
                'errori': stats.get('errori', 0),
                'totale_csv': stats.get('totale_csv', 0),
            }

        elif tipo == 'contacts':
            from import_contacts_crm import importa_contacts
            stats = importa_contacts(str(csv_file), dry_run=False)
            import_all_status['risultati']['contacts'] = {
                'success': True,
                'inseriti': stats.get('referenti_inseriti', 0),
                'aggiornati': stats.get('referenti_aggiornati', 0),
                'duplicati': stats.get('referenti_duplicati', 0),
                'errori': stats.get('errori', 0),
                'totale_csv': stats.get('totale_csv', 0),
            }

        import_all_status['current'] = 1

        # Sposta CSV in archivio dopo import
        archivio = IMPORT_DIR / 'elaborati'
        archivio.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = archivio / f"{csv_file.stem}_{timestamp}{csv_file.suffix}"
        csv_file.rename(dest)

    except Exception as e:
        import_all_status['risultati'][tipo] = {
            'success': False,
            'error': str(e),
        }
        import_all_status['errori_globali'].append(
            f"{LABEL_TIPO[tipo]}: {str(e)}")


def _importa_fase_creditsafe():
    """Importa fase PDF Creditsafe."""
    global import_all_status

    pdf_files = sorted(PDF_DIR.glob('*.pdf')) if PDF_DIR.exists() else []
    if not pdf_files:
        import_all_status['risultati']['creditsafe'] = {
            'success': True, 'message': 'Nessun PDF'}
        return

    import_all_status['total'] = len(pdf_files)
    import_all_status['current'] = 0

    completati = 0
    errori = 0

    try:
        from app.import_creditsafe import importa_pdf_singolo

        for i, pdf_path in enumerate(pdf_files):
            import_all_status['current'] = i + 1
            import_all_status['current_file'] = pdf_path.name

            try:
                risultato = importa_pdf_singolo(str(pdf_path))
                if risultato.get('success'):
                    completati += 1
                else:
                    errori += 1
            except Exception as e:
                errori += 1

    except Exception as e:
        import_all_status['errori_globali'].append(
            f"Creditsafe: {str(e)}")

    import_all_status['risultati']['creditsafe'] = {
        'success': True,
        'completati': completati,
        'errori': errori,
        'totale': len(pdf_files),
    }


# ==============================================================================
# ROUTE: POLLING STATO IMPORT
# ==============================================================================

@admin_upload_bp.route('/admin/import-all-status')
@login_required
def import_all_status_route():
    """Polling stato import multi-fase."""
    global import_all_status

    stato = dict(import_all_status)
    # Aggiungi label leggibili
    if stato['fase_corrente']:
        stato['fase_corrente_label'] = LABEL_TIPO.get(
            stato['fase_corrente'], stato['fase_corrente'])
    stato['fasi_completate_label'] = [
        LABEL_TIPO.get(f, f) for f in stato.get('fasi_completate', [])
    ]

    return jsonify(stato)


# ==============================================================================
# ROUTE: TOGGLE PROMEMORIA CRM
# ==============================================================================

@admin_upload_bp.route('/admin/toggle-promemoria-crm', methods=['POST'])
@login_required
def toggle_promemoria_crm():
    """Toggle ON/OFF globale promemoria aggiornamento CRM."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT valore FROM ticker_config WHERE chiave = 'promemoria_aggiorna_crm'")
        row = cursor.fetchone()

        if row:
            nuovo = '0' if row['valore'] == '1' else '1'
            cursor.execute(
                "UPDATE ticker_config SET valore = ? WHERE chiave = 'promemoria_aggiorna_crm'",
                (nuovo,))
        else:
            nuovo = '1'
            cursor.execute(
                "INSERT INTO ticker_config (chiave, valore, descrizione) VALUES (?, ?, ?)",
                ('promemoria_aggiorna_crm', '1',
                 'Promemoria settimanale aggiornamento dati CRM'))

        conn.commit()
        return jsonify({'success': True, 'attivo': nuovo == '1'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# ROUTE: FLAG NOTIFICA CRM PER UTENTE
# ==============================================================================

@admin_upload_bp.route('/admin/flag-notifica-crm', methods=['POST'])
@login_required
def flag_notifica_crm():
    """Attiva/disattiva flag notifica CRM per un utente."""
    data = request.get_json()
    utente_id = data.get('utente_id')
    attivo = data.get('attivo', True)

    if not utente_id:
        return jsonify({'success': False, 'error': 'utente_id richiesto'}), 400

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE utenti SET notifica_aggiorna_crm = ? WHERE id = ?",
            (1 if attivo else 0, utente_id))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404

        return jsonify({'success': True, 'utente_id': utente_id, 'attivo': attivo})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ==============================================================================
# ROUTE: INFO PROMEMORIA CRM (per admin.html)
# ==============================================================================

@admin_upload_bp.route('/admin/promemoria-crm-info')
@login_required
def promemoria_crm_info():
    """Info stato promemoria CRM: toggle globale + utenti con flag."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Toggle globale
        cursor.execute(
            "SELECT valore FROM ticker_config WHERE chiave = 'promemoria_aggiorna_crm'")
        row = cursor.fetchone()
        attivo_globale = row['valore'] == '1' if row else False

        # Utenti con flag
        cursor.execute("""
            SELECT id, username, nome, cognome, ruolo_base, notifica_aggiorna_crm
            FROM utenti WHERE attivo = 1
            ORDER BY ruolo_base, cognome, nome
        """)
        utenti = []
        for u in cursor.fetchall():
            utenti.append({
                'id': u['id'],
                'username': u['username'],
                'nome_completo': f"{u['nome'] or ''} {u['cognome'] or ''}".strip()
                                 or u['username'],
                'ruolo': u['ruolo_base'],
                'flag_crm': bool(u['notifica_aggiorna_crm']),
            })

        return jsonify({
            'success': True,
            'attivo_globale': attivo_globale,
            'utenti': utenti,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()
