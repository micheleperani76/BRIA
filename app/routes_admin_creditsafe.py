#!/usr/bin/env python3
# ==============================================================================
# ROUTES ADMIN CREDITSAFE - Gestione credenziali API
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Blueprint per gestione credenziali API Creditsafe
#              dalla pagina Amministrazione.
#
# Route:
#   POST /admin/creditsafe/test     - Test connessione API
#   POST /admin/creditsafe/salva    - Salva nuove credenziali
#   GET  /admin/creditsafe/stato    - Stato credenziali (AJAX)
# ==============================================================================

import re
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, session

from app.auth import login_required, permesso_richiesto
from app.config import BASE_DIR

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

CREDENZIALI_FILE = BASE_DIR / 'account_esterni' / 'Credenziali_api_creditsafe.txt'

logger = logging.getLogger('admin_creditsafe')

# ==============================================================================
# BLUEPRINT
# ==============================================================================

creditsafe_admin_bp = Blueprint('creditsafe_admin', __name__)


# ==============================================================================
# ROUTE: STATO CREDENZIALI
# ==============================================================================

@creditsafe_admin_bp.route('/admin/creditsafe/stato', methods=['GET'])
@login_required
@permesso_richiesto('admin_sistema')
def creditsafe_stato():
    """Ritorna stato attuale delle credenziali (senza password)."""
    try:
        if not CREDENZIALI_FILE.exists():
            return jsonify({
                'configurato': False,
                'username': None,
                'errore': 'File credenziali non trovato'
            })

        contenuto = CREDENZIALI_FILE.read_text(encoding='utf-8').strip()
        username = None

        for riga in contenuto.splitlines():
            riga = riga.strip()
            if riga.upper().startswith('USERNAME'):
                m = re.search(r'=\s*["\'](.+?)["\']', riga)
                if m:
                    username = m.group(1)

        return jsonify({
            'configurato': username is not None,
            'username': username,
            'file': str(CREDENZIALI_FILE),
            'errore': None
        })

    except Exception as e:
        logger.error(f"Errore lettura stato credenziali: {e}")
        return jsonify({
            'configurato': False,
            'username': None,
            'errore': str(e)
        })


# ==============================================================================
# ROUTE: TEST CONNESSIONE
# ==============================================================================

@creditsafe_admin_bp.route('/admin/creditsafe/test', methods=['POST'])
@login_required
@permesso_richiesto('admin_sistema')
def creditsafe_test():
    """Testa le credenziali API attuali."""
    try:
        from app.creditsafe_api import CreditsafeAPI

        api = CreditsafeAPI(base_dir=str(BASE_DIR))
        result = api.test_credentials()

        if result['valid']:
            # Prova anche a leggere info accesso
            try:
                access = api.get_access_info()
                # Cerca info monitoring
                monitoring_info = None
                if isinstance(access, dict):
                    for key, val in access.items():
                        if 'monitoring' in str(key).lower() or 'monitoring' in str(val).lower():
                            monitoring_info = val
                            break

                result['accesso'] = {
                    'monitoring': monitoring_info,
                    'raw_keys': list(access.keys()) if isinstance(access, dict) else None
                }
            except Exception as e:
                result['accesso'] = {'errore': str(e)}

        return jsonify(result)

    except Exception as e:
        logger.error(f"Errore test credenziali: {e}")
        return jsonify({
            'valid': False,
            'username': None,
            'error': str(e)
        })


# ==============================================================================
# ROUTE: SALVA CREDENZIALI
# ==============================================================================

@creditsafe_admin_bp.route('/admin/creditsafe/salva', methods=['POST'])
@login_required
@permesso_richiesto('admin_sistema')
def creditsafe_salva():
    """Salva nuove credenziali API."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'ok': False, 'errore': 'Dati mancanti'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username:
            return jsonify({'ok': False, 'errore': 'Username obbligatorio'}), 400
        if not password:
            return jsonify({'ok': False, 'errore': 'Password obbligatoria'}), 400

        # Validazione email base
        if '@' not in username:
            return jsonify({'ok': False, 'errore': 'Username deve essere un indirizzo email'}), 400

        # Prepara contenuto file
        # Escape singole virgolette nella password per formato file
        pwd_escaped = password.replace("\\", "\\\\").replace("'", "\\'")
        contenuto = f'USERNAME = "{username}"\nPASSWORD = \'{pwd_escaped}\'\n'

        # Backup file esistente
        if CREDENZIALI_FILE.exists():
            from datetime import datetime
            backup_dir = BASE_DIR / 'backup'
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"account_esterni__Credenziali_api_creditsafe.txt.bak_{timestamp}"
            import shutil
            shutil.copy2(str(CREDENZIALI_FILE), str(backup_file))
            logger.info(f"Backup credenziali: {backup_file}")

        # Crea cartella se non esiste
        CREDENZIALI_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Salva
        CREDENZIALI_FILE.write_text(contenuto, encoding='utf-8')
        logger.info(f"Credenziali API salvate per: {username}")

        # Test immediato
        test_ok = False
        test_errore = None
        try:
            from app.creditsafe_api import CreditsafeAPI
            api = CreditsafeAPI(base_dir=str(BASE_DIR))
            result = api.test_credentials()
            test_ok = result.get('valid', False)
            test_errore = result.get('error')
        except Exception as e:
            test_errore = str(e)

        # Log attivita'
        try:
            from app.database import get_connection
            conn = get_connection()
            conn.execute('''
                INSERT INTO log_attivita (utente_id, azione, dettaglio, data_ora)
                VALUES (?, ?, ?, datetime('now'))
            ''', (
                session.get('user_id'),
                'creditsafe_credenziali_aggiornate',
                f'Username: {username}, Test: {"OK" if test_ok else "FALLITO"}'
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

        return jsonify({
            'ok': True,
            'test_ok': test_ok,
            'test_errore': test_errore,
            'messaggio': 'Credenziali salvate' + (' e verificate con successo' if test_ok else ' ma il test di connessione ha fallito')
        })

    except Exception as e:
        logger.error(f"Errore salvataggio credenziali: {e}")
        return jsonify({'ok': False, 'errore': str(e)}), 500


# ==============================================================================
# ROUTE: CONTATORI MONITORING
# ==============================================================================

@creditsafe_admin_bp.route('/admin/creditsafe/contatori', methods=['GET'])
@login_required
@permesso_richiesto('admin_sistema')
def creditsafe_contatori():
    """Ritorna contatori monitoring e info polling."""
    try:
        from app.creditsafe_api import CreditsafeAPI
        from datetime import datetime, timedelta

        api = CreditsafeAPI(base_dir=str(BASE_DIR))
        api.authenticate()
        info = api.get_access_info()

        # Parsing contatori
        contatori = {}
        monitoring = info.get('countryAccess', {}).get('creditsafeConnectMonitoring', [])
        for s in monitoring:
            nome = s.get('name', '')
            contatori[nome] = {
                'used': s.get('used', 0),
                'paid': s.get('paid', 0),
                'expire': s.get('expireDate', '')
            }

        # Ultimo polling (cerca ultimo log)
        import glob
        log_pattern = str(BASE_DIR / 'logs' / 'creditsafe_polling_*.log')
        logs = sorted(glob.glob(log_pattern))
        ultimo_polling = None
        if logs:
            ultimo_log = Path(logs[-1])
            # Estrai data dal nome file: creditsafe_polling_YYYYMMDD_HHMMSS.log
            try:
                ts_str = ultimo_log.stem.replace('creditsafe_polling_', '')
                dt = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                ultimo_polling = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                pass

        # Prossimo polling (prossimo giovedi ore 20:00)
        now = datetime.now()
        days_ahead = (3 - now.weekday()) % 7  # 3 = giovedi
        if days_ahead == 0 and now.hour >= 20:
            days_ahead = 7
        prossimo = (now + timedelta(days=days_ahead)).replace(hour=20, minute=0, second=0)

        return jsonify({
            'ok': True,
            'contatori': contatori,
            'ultimo_polling': ultimo_polling,
            'prossimo_polling': prossimo.strftime('%Y-%m-%d %H:%M')
        })

    except Exception as e:
        logger.error(f"Errore lettura contatori: {e}")
        return jsonify({'ok': False, 'errore': str(e)})
