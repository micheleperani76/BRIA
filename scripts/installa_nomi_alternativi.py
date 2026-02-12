#!/usr/bin/env python3
# ==============================================================================
# INSTALLAZIONE - Nomi Alternativi / Keyword Ricerca Cliente
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-12
# Descrizione: Installa la feature completa dei nomi alternativi:
#   1. Crea tabella DB
#   2. Crea file satellite (modal + scripts)
#   3. Patcha card-header dati_aziendali
#   4. Patcha dettaglio.html (include modal + scripts)
#   5. Patcha web_server.py (API + ricerca smart + badge)
#   6. Patcha template index (badge Alias)
#
# Uso: python3 installa_nomi_alternativi.py --dry-run    (verifica senza modifiche)
#       python3 installa_nomi_alternativi.py              (installa tutto)
# ==============================================================================

import sys
import os
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================
BASE_DIR = Path(os.path.expanduser('~/gestione_flotta'))
DB_PATH = BASE_DIR / 'db' / 'gestionale.db'
BACKUP_DIR = BASE_DIR / 'backup'

DRY_RUN = '--dry-run' in sys.argv
NOW = datetime.now().strftime('%Y%m%d_%H%M%S')

CONTATORI = {'ok': 0, 'skip': 0, 'errore': 0}

# ==============================================================================
# UTILITY
# ==============================================================================

def log(msg, livello='INFO'):
    prefix = "[DRY-RUN] " if DRY_RUN else ""
    simbolo = {'OK': '\033[92m OK \033[0m', 'SKIP': '\033[93mSKIP\033[0m', 
               'ERR': '\033[91m ERR\033[0m', 'INFO': '    '}
    print(f"  {simbolo.get(livello, '    ')} {prefix}{msg}")


def backup_file(filepath):
    """Crea backup con naming convention del progetto."""
    if not filepath.exists():
        return
    rel = str(filepath.relative_to(BASE_DIR)).replace('/', '__')
    dest = BACKUP_DIR / f"{rel}.bak_{NOW}"
    if not DRY_RUN:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, dest)
    log(f"Backup: {dest.name}", 'INFO')


def str_replace_in_file(filepath, old, new, description=""):
    """Sostituzione chirurgica in un file. Ritorna True se OK."""
    if not filepath.exists():
        log(f"File non trovato: {filepath}", 'ERR')
        CONTATORI['errore'] += 1
        return False
    
    contenuto = filepath.read_text(encoding='utf-8')
    
    if old not in contenuto:
        log(f"Blocco non trovato in {filepath.name}: {description}", 'ERR')
        CONTATORI['errore'] += 1
        return False
    
    if contenuto.count(old) > 1:
        log(f"ATTENZIONE: blocco trovato {contenuto.count(old)} volte in {filepath.name}", 'ERR')
        CONTATORI['errore'] += 1
        return False
    
    if new in contenuto:
        log(f"Patch gia' applicata in {filepath.name}: {description}", 'SKIP')
        CONTATORI['skip'] += 1
        return True
    
    if not DRY_RUN:
        backup_file(filepath)
        filepath.write_text(contenuto.replace(old, new), encoding='utf-8')
    
    log(f"{filepath.name}: {description}", 'OK')
    CONTATORI['ok'] += 1
    return True


def insert_before_in_file(filepath, marker, new_content, description=""):
    """Inserisce contenuto PRIMA di un marker. Ritorna True se OK."""
    if not filepath.exists():
        log(f"File non trovato: {filepath}", 'ERR')
        CONTATORI['errore'] += 1
        return False
    
    contenuto = filepath.read_text(encoding='utf-8')
    
    if marker not in contenuto:
        log(f"Marker non trovato in {filepath.name}: {description}", 'ERR')
        CONTATORI['errore'] += 1
        return False
    
    # Controlla se gia' presente
    check = new_content.strip().split('\n')[0].strip()
    if check in contenuto:
        log(f"Patch gia' applicata in {filepath.name}: {description}", 'SKIP')
        CONTATORI['skip'] += 1
        return True
    
    if not DRY_RUN:
        backup_file(filepath)
        filepath.write_text(contenuto.replace(marker, new_content + '\n' + marker), encoding='utf-8')
    
    log(f"{filepath.name}: {description}", 'OK')
    CONTATORI['ok'] += 1
    return True


def insert_after_in_file(filepath, marker, new_content, description=""):
    """Inserisce contenuto DOPO un marker. Ritorna True se OK."""
    if not filepath.exists():
        log(f"File non trovato: {filepath}", 'ERR')
        CONTATORI['errore'] += 1
        return False
    
    contenuto = filepath.read_text(encoding='utf-8')
    
    if marker not in contenuto:
        log(f"Marker non trovato in {filepath.name}: {description}", 'ERR')
        CONTATORI['errore'] += 1
        return False
    
    check = new_content.strip().split('\n')[1].strip() if '\n' in new_content.strip() else new_content.strip()
    if check in contenuto:
        log(f"Patch gia' applicata in {filepath.name}: {description}", 'SKIP')
        CONTATORI['skip'] += 1
        return True
    
    if not DRY_RUN:
        backup_file(filepath)
        filepath.write_text(contenuto.replace(marker, marker + '\n' + new_content), encoding='utf-8')
    
    log(f"{filepath.name}: {description}", 'OK')
    CONTATORI['ok'] += 1
    return True


# ==============================================================================
# STEP 1: MIGRAZIONE DATABASE
# ==============================================================================

def step_1_database():
    print("\n[1/7] Migrazione Database")
    print("-" * 40)
    
    if not DB_PATH.exists():
        log(f"Database non trovato: {DB_PATH}", 'ERR')
        CONTATORI['errore'] += 1
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    
    # Check se tabella esiste gia'
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clienti_nomi_alternativi'")
    if cursor.fetchone():
        log("Tabella clienti_nomi_alternativi gia' esistente", 'SKIP')
        CONTATORI['skip'] += 1
        conn.close()
        return
    
    if DRY_RUN:
        log("CREATE TABLE clienti_nomi_alternativi", 'OK')
        log("CREATE INDEX idx_nomi_alt_cliente", 'OK')
        log("CREATE INDEX idx_nomi_alt_nome", 'OK')
        CONTATORI['ok'] += 3
        conn.close()
        return
    
    # Backup DB
    backup_db = BACKUP_DIR / f"db__gestionale.db.bak_{NOW}"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, backup_db)
    log(f"Backup DB: {backup_db.name}", 'INFO')
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clienti_nomi_alternativi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            nome_alternativo TEXT NOT NULL,
            data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            creato_da INTEGER,
            FOREIGN KEY (cliente_id) REFERENCES clienti(id) ON DELETE CASCADE,
            FOREIGN KEY (creato_da) REFERENCES utenti(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nomi_alt_cliente ON clienti_nomi_alternativi(cliente_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nomi_alt_nome ON clienti_nomi_alternativi(nome_alternativo COLLATE NOCASE)")
    conn.commit()
    conn.close()
    
    log("Tabella clienti_nomi_alternativi creata", 'OK')
    log("Indici creati (2)", 'OK')
    CONTATORI['ok'] += 3


# ==============================================================================
# STEP 2: FILE SATELLITE (modal + scripts)
# ==============================================================================

def step_2_file_satellite():
    print("\n[2/7] File Satellite (modal + scripts)")
    print("-" * 40)
    
    cartella = BASE_DIR / 'templates' / 'dettaglio' / 'nomi_alternativi'
    
    if not DRY_RUN:
        cartella.mkdir(parents=True, exist_ok=True)
    
    # --- _modal.html ---
    modal_path = cartella / '_modal.html'
    if modal_path.exists():
        log("_modal.html gia' presente", 'SKIP')
        CONTATORI['skip'] += 1
    else:
        modal_content = """{# ==============================================================================
   NOMI ALTERNATIVI - Modal gestione
   Versione: 1.0.0
   Data: 2026-02-12
   Cartella: templates/dettaglio/nomi_alternativi/
   Descrizione: Modal per aggiungere/rimuovere nomi alternativi e keyword
                speciali per la ricerca smart del cliente
   ============================================================================== #}

<div class="modal fade" id="modalNomiAlternativi" tabindex="-1" aria-labelledby="modalNomiAlternativiLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header py-2">
                <h6 class="modal-title" id="modalNomiAlternativiLabel">
                    <i class="bi bi-tags"></i> Nomi Alternativi / Keyword
                </h6>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Chiudi"></button>
            </div>
            <div class="modal-body">
                <p class="text-muted small mb-3">
                    Aggiungi nomi alternativi, sigle, abbreviazioni o keyword speciali per trovare questa azienda nella ricerca smart.
                </p>

                {# --- Form aggiunta --- #}
                <div class="input-group mb-3">
                    <input type="text" class="form-control" id="inputNomeAlternativo" 
                           placeholder="Es: FIAT, Stellantis, ex-FCA..." maxlength="200"
                           onkeydown="if(event.key==='Enter'){event.preventDefault(); aggiungiNomeAlternativo();}">
                    <button class="btn btn-success" type="button" onclick="aggiungiNomeAlternativo()">
                        <i class="bi bi-plus-lg"></i> Aggiungi
                    </button>
                </div>

                {# --- Lista nomi esistenti --- #}
                <div id="listaNomiAlternativi">
                    <div class="text-center text-muted py-3" id="nomiAlternativiVuoto">
                        <i class="bi bi-inbox"></i> Nessun nome alternativo
                    </div>
                </div>
            </div>
            <div class="modal-footer py-2">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Chiudi</button>
            </div>
        </div>
    </div>
</div>
"""
        if not DRY_RUN:
            modal_path.write_text(modal_content, encoding='utf-8')
        log("_modal.html creato", 'OK')
        CONTATORI['ok'] += 1

    # --- _scripts.html ---
    scripts_path = cartella / '_scripts.html'
    if scripts_path.exists():
        log("_scripts.html gia' presente", 'SKIP')
        CONTATORI['skip'] += 1
    else:
        scripts_content = """{# ==============================================================================
   NOMI ALTERNATIVI - Scripts dedicati
   Versione: 1.0.0
   Data: 2026-02-12
   Cartella: templates/dettaglio/nomi_alternativi/
   ============================================================================== #}

<script>
// =====================================================
// NOMI ALTERNATIVI - CRUD
// =====================================================

const CLIENTE_ID_NOMI_ALT = {{ cliente.id }};

/**
 * Carica lista nomi alternativi dal server
 */
function caricaNomiAlternativi() {
    fetch('/api/cliente/' + CLIENTE_ID_NOMI_ALT + '/nomi-alternativi')
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            renderNomiAlternativi(data.nomi);
            var badge = document.getElementById('badgeNomiAlternativi');
            if (badge) {
                if (data.nomi.length > 0) {
                    badge.textContent = data.nomi.length;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
        }
    })
    .catch(function(err) { console.error('Errore caricamento nomi alternativi:', err); });
}

/**
 * Renderizza lista nomi nel modal
 */
function renderNomiAlternativi(nomi) {
    var container = document.getElementById('listaNomiAlternativi');
    
    if (!nomi || nomi.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-3"><i class="bi bi-inbox"></i> Nessun nome alternativo</div>';
        return;
    }
    
    var html = '<ul class="list-group list-group-flush">';
    nomi.forEach(function(n) {
        html += '<li class="list-group-item d-flex justify-content-between align-items-center py-2">';
        html += '<span><i class="bi bi-tag me-2 text-muted"></i>' + escapeHtmlNA(n.nome_alternativo) + '</span>';
        html += '<button class="btn btn-outline-danger btn-sm" onclick="rimuoviNomeAlternativo(' + n.id + ')" title="Rimuovi">';
        html += '<i class="bi bi-trash"></i>';
        html += '</button>';
        html += '</li>';
    });
    html += '</ul>';
    
    container.innerHTML = html;
}

/**
 * Aggiunge un nuovo nome alternativo
 */
function aggiungiNomeAlternativo() {
    var input = document.getElementById('inputNomeAlternativo');
    var valore = input.value.trim();
    
    if (!valore) {
        input.classList.add('is-invalid');
        setTimeout(function() { input.classList.remove('is-invalid'); }, 2000);
        return;
    }
    
    fetch('/api/cliente/' + CLIENTE_ID_NOMI_ALT + '/nomi-alternativi', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({nome_alternativo: valore})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            input.value = '';
            caricaNomiAlternativi();
        } else {
            alert(data.error || 'Errore durante il salvataggio');
        }
    })
    .catch(function(err) {
        console.error('Errore:', err);
        alert('Errore di comunicazione con il server');
    });
}

/**
 * Rimuove un nome alternativo
 */
function rimuoviNomeAlternativo(id) {
    if (!confirm('Rimuovere questo nome alternativo?')) return;
    
    fetch('/api/cliente/' + CLIENTE_ID_NOMI_ALT + '/nomi-alternativi/' + id, {
        method: 'DELETE'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            caricaNomiAlternativi();
        } else {
            alert(data.error || 'Errore durante la rimozione');
        }
    })
    .catch(function(err) {
        console.error('Errore:', err);
        alert('Errore di comunicazione con il server');
    });
}

/**
 * Escape HTML per evitare XSS
 */
function escapeHtmlNA(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// Carica al click sul modal
document.getElementById('modalNomiAlternativi').addEventListener('show.bs.modal', function() {
    caricaNomiAlternativi();
});

// Carica anche all'apertura pagina (per il badge)
document.addEventListener('DOMContentLoaded', function() {
    caricaNomiAlternativi();
});
</script>
"""
        if not DRY_RUN:
            scripts_path.write_text(scripts_content, encoding='utf-8')
        log("_scripts.html creato", 'OK')
        CONTATORI['ok'] += 1


# ==============================================================================
# STEP 3: PATCH CARD-HEADER DATI AZIENDALI
# ==============================================================================

def step_3_card_header():
    print("\n[3/7] Patch card-header Dati Aziendali")
    print("-" * 40)
    
    filepath = BASE_DIR / 'templates' / 'dettaglio' / 'dati_aziendali' / '_content.html'
    
    old = '''    <div class="card-header py-2">
        <i class="bi bi-building"></i> Dati Aziendali
    </div>'''
    
    new = '''    <div class="card-header py-2 d-flex justify-content-between align-items-center">
        <span><i class="bi bi-building"></i> Dati Aziendali</span>
        <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-1" data-bs-toggle="modal" data-bs-target="#modalNomiAlternativi" title="Nomi alternativi / Keyword ricerca">
            <i class="bi bi-tags"></i> <small>Alias</small>
            <span class="badge bg-primary rounded-pill ms-1" id="badgeNomiAlternativi" style="display: none; font-size: 0.6rem;">0</span>
        </button>
    </div>'''
    
    str_replace_in_file(filepath, old, new, "Aggiunto pulsante Alias nel card-header")


# ==============================================================================
# STEP 4: INCLUDE IN DETTAGLIO.HTML (modal + scripts)
# ==============================================================================

def step_4_include_dettaglio():
    print("\n[4/7] Include modal + scripts in dettaglio.html")
    print("-" * 40)
    
    filepath = BASE_DIR / 'templates' / 'dettaglio.html'
    
    if not filepath.exists():
        log(f"File non trovato: {filepath}", 'ERR')
        CONTATORI['errore'] += 1
        return
    
    contenuto = filepath.read_text(encoding='utf-8')
    modificato = False
    
    # --- 4a: Include modal (nel block content, prima dell'ultimo endblock content) ---
    # Cerco il pattern: la riga con _griglia_layout include e inserisco il modal dopo
    modal_include = '{% include "dettaglio/nomi_alternativi/_modal.html" %}'
    
    if modal_include in contenuto:
        log("Include _modal.html gia' presente", 'SKIP')
        CONTATORI['skip'] += 1
    else:
        # Inserisco dopo l'include della griglia layout
        griglia_marker = '{% include "dettaglio/_griglia_layout.html" %}'
        if griglia_marker in contenuto:
            contenuto = contenuto.replace(
                griglia_marker,
                griglia_marker + '\n\n        {# --- Modal Nomi Alternativi --- #}\n        ' + modal_include
            )
            modificato = True
            log("Include _modal.html aggiunto dopo _griglia_layout", 'OK')
            CONTATORI['ok'] += 1
        else:
            log("Marker _griglia_layout.html non trovato!", 'ERR')
            CONTATORI['errore'] += 1
    
    # --- 4b: Include scripts (nel block scripts, prima del </script> finale) ---
    scripts_include = '{% include "dettaglio/nomi_alternativi/_scripts.html" %}'
    
    if scripts_include in contenuto:
        log("Include _scripts.html gia' presente", 'SKIP')
        CONTATORI['skip'] += 1
    else:
        # Cerco l'ultimo </script> seguito da {% endblock %}
        marker_scripts = '</script>\n{% endblock %}'
        if marker_scripts in contenuto:
            contenuto = contenuto.replace(
                marker_scripts,
                '</script>\n\n{# --- Scripts Nomi Alternativi --- #}\n' + scripts_include + '\n\n{% endblock %}'
            )
            modificato = True
            log("Include _scripts.html aggiunto nel block scripts", 'OK')
            CONTATORI['ok'] += 1
        else:
            log("Marker </script> + endblock non trovato!", 'ERR')
            CONTATORI['errore'] += 1
    
    if modificato and not DRY_RUN:
        backup_file(filepath)
        filepath.write_text(contenuto, encoding='utf-8')


# ==============================================================================
# STEP 5: API ROUTES IN WEB_SERVER.PY
# ==============================================================================

def step_5_api_routes():
    print("\n[5/7] API Routes nomi alternativi in web_server.py")
    print("-" * 40)
    
    filepath = BASE_DIR / 'app' / 'web_server.py'
    
    api_block = """

# ==============================================================================
# API: Nomi Alternativi / Keyword Ricerca Cliente
# ==============================================================================

@app.route('/api/cliente/<int:cliente_id>/nomi-alternativi', methods=['GET'])
@login_required
def api_nomi_alternativi_lista(cliente_id):
    \"\"\"Lista nomi alternativi di un cliente.\"\"\"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nome_alternativo, data_creazione 
        FROM clienti_nomi_alternativi 
        WHERE cliente_id = ? 
        ORDER BY nome_alternativo COLLATE NOCASE
    ''', (cliente_id,))
    nomi = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'nomi': nomi})


@app.route('/api/cliente/<int:cliente_id>/nomi-alternativi', methods=['POST'])
@login_required
def api_nomi_alternativi_aggiungi(cliente_id):
    \"\"\"Aggiunge un nome alternativo a un cliente.\"\"\"
    data = request.get_json()
    nome = data.get('nome_alternativo', '').strip()
    
    if not nome:
        return jsonify({'success': False, 'error': 'Nome alternativo vuoto'}), 400
    if len(nome) > 200:
        return jsonify({'success': False, 'error': 'Nome troppo lungo (max 200 caratteri)'}), 400
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Controlla duplicato (case insensitive)
    cursor.execute('''
        SELECT id FROM clienti_nomi_alternativi 
        WHERE cliente_id = ? AND LOWER(nome_alternativo) = LOWER(?)
    ''', (cliente_id, nome))
    if cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'Nome alternativo gia\\' presente'})
    
    try:
        cursor.execute('''
            INSERT INTO clienti_nomi_alternativi (cliente_id, nome_alternativo, creato_da)
            VALUES (?, ?, ?)
        ''', (cliente_id, nome, session.get('user_id')))
        conn.commit()
        
        try:
            cursor.execute('''
                INSERT INTO log_attivita (utente_id, azione, dettaglio, ip_address)
                VALUES (?, 'AGGIUNGI_NOME_ALTERNATIVO', ?, ?)
            ''', (session.get('user_id'), 
                  'Cliente ID {}: aggiunto \"{}\"'.format(cliente_id, nome),
                  request.remote_addr))
            conn.commit()
        except:
            pass
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cliente/<int:cliente_id>/nomi-alternativi/<int:nome_id>', methods=['DELETE'])
@login_required
def api_nomi_alternativi_rimuovi(cliente_id, nome_id):
    \"\"\"Rimuove un nome alternativo.\"\"\"
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT nome_alternativo FROM clienti_nomi_alternativi 
        WHERE id = ? AND cliente_id = ?
    ''', (nome_id, cliente_id))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Nome alternativo non trovato'}), 404
    
    nome_rimosso = row['nome_alternativo']
    
    try:
        cursor.execute('DELETE FROM clienti_nomi_alternativi WHERE id = ?', (nome_id,))
        conn.commit()
        
        try:
            cursor.execute('''
                INSERT INTO log_attivita (utente_id, azione, dettaglio, ip_address)
                VALUES (?, 'RIMUOVI_NOME_ALTERNATIVO', ?, ?)
            ''', (session.get('user_id'),
                  'Cliente ID {}: rimosso \"{}\"'.format(cliente_id, nome_rimosso),
                  request.remote_addr))
            conn.commit()
        except:
            pass
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
"""
    
    # Inserisco PRIMA della route api_referente_principale
    marker = """@app.route('/api/cliente/<int:cliente_id>/referente-principale')"""
    
    insert_before_in_file(filepath, marker, api_block, "API CRUD nomi alternativi")


# ==============================================================================
# STEP 6: PATCH RICERCA SMART /api/cerca
# ==============================================================================

def step_6_ricerca_smart():
    print("\n[6/7] Patch ricerca smart (/api/cerca + get_search_matches)")
    print("-" * 40)
    
    filepath = BASE_DIR / 'app' / 'web_server.py'
    
    # --- 6a: Patch query /api/cerca ---
    old_query = """           OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(c.ragione_sociale, '.', ''), ' ', ''), '-', ''), '&', ''), char(39), '')) LIKE ?
        ORDER BY c.nome_cliente LIMIT ?
    \"\"\", (search_param, search_param, search_param, search_param, 
          search_normalized, search_normalized, limit))"""
    
    new_query = """           OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(c.ragione_sociale, '.', ''), ' ', ''), '-', ''), '&', ''), char(39), '')) LIKE ?
           -- Ricerca in nomi alternativi / keyword
           OR c.id IN (SELECT na.cliente_id FROM clienti_nomi_alternativi na WHERE na.nome_alternativo LIKE ? OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(na.nome_alternativo, '.', ''), ' ', ''), '-', ''), '&', ''), char(39), '')) LIKE ?)
        ORDER BY c.nome_cliente LIMIT ?
    \"\"\", (search_param, search_param, search_param, search_param, 
          search_normalized, search_normalized,
          search_param, search_normalized, limit))"""
    
    str_replace_in_file(filepath, old_query, new_query, "Subquery nomi alternativi in /api/cerca")
    
    # --- 6b: Patch get_search_matches_per_cliente - aggiunta match alias ---
    old_match = """        # Note (titolo + testo)
        cursor.execute(f\"\"\"
            SELECT n.cliente_id, n.titolo
            FROM note_clienti n
            WHERE n.cliente_id IN ({placeholders})
            AND (n.titolo LIKE ? OR n.testo LIKE ?)
        \"\"\", ids_list + [search_param, search_param])"""
    
    new_match = """        # Nomi alternativi / Alias
        cursor.execute(f\"\"\"
            SELECT na.cliente_id, na.nome_alternativo
            FROM clienti_nomi_alternativi na
            WHERE na.cliente_id IN ({placeholders})
            AND na.nome_alternativo LIKE ?
        \"\"\", ids_list + [search_param])
        for row in cursor.fetchall():
            cid, alias = row[0], row[1]
            if alias:
                if 'alias' not in matches_per_cliente[cid]:
                    matches_per_cliente[cid]['alias'] = []
                matches_per_cliente[cid]['alias'].append(alias)
                if 'alias' not in matches_globali:
                    matches_globali['alias'] = []
                if alias not in matches_globali['alias']:
                    matches_globali['alias'].append(alias)
        
        # Note (titolo + testo)
        cursor.execute(f\"\"\"
            SELECT n.cliente_id, n.titolo
            FROM note_clienti n
            WHERE n.cliente_id IN ({placeholders})
            AND (n.titolo LIKE ? OR n.testo LIKE ?)
        \"\"\", ids_list + [search_param, search_param])"""
    
    str_replace_in_file(filepath, old_match, new_match, "Match alias in get_search_matches_per_cliente")


# ==============================================================================
# STEP 7: BADGE ALIAS NEL TEMPLATE INDEX
# ==============================================================================

def step_7_badge_index():
    print("\n[7/7] Badge Alias nel template index")
    print("-" * 40)
    
    filepath = BASE_DIR / 'templates' / 'index' / '_tabella.html'
    
    # Aggiungo badge alias dopo il badge Nota
    old_badge = """                        {% elif tipo == 'note' %}
                        <span class="badge bg-info" style="font-size: 0.65rem;" title="Trovato in nota"><i class="bi bi-chat-text"></i> Nota</span>"""
    
    new_badge = """                        {% elif tipo == 'note' %}
                        <span class="badge bg-info" style="font-size: 0.65rem;" title="Trovato in nota"><i class="bi bi-chat-text"></i> Nota</span>
                        {% elif tipo == 'alias' %}
                        <span class="badge bg-purple" style="font-size: 0.65rem; background-color: #6f42c1;" title="Alias: {{ valori|join(', ') }}"><i class="bi bi-tags"></i> Alias</span>"""
    
    str_replace_in_file(filepath, old_badge, new_badge, "Aggiunto badge Alias viola")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print()
    print("=" * 60)
    print("  INSTALLAZIONE: Nomi Alternativi / Keyword Ricerca")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if DRY_RUN:
        print("  MODALITA': DRY-RUN (nessuna modifica)")
    else:
        print("  MODALITA': INSTALLAZIONE REALE")
    print("=" * 60)
    
    step_1_database()
    step_2_file_satellite()
    step_3_card_header()
    step_4_include_dettaglio()
    step_5_api_routes()
    step_6_ricerca_smart()
    step_7_badge_index()
    
    print()
    print("=" * 60)
    print(f"  RISULTATO:  {CONTATORI['ok']} OK  |  {CONTATORI['skip']} SKIP  |  {CONTATORI['errore']} ERRORI")
    print("=" * 60)
    
    if CONTATORI['errore'] > 0:
        print("\n  \033[91mATTENZIONE: Ci sono errori! Verificare i log sopra.\033[0m")
        print("  I backup sono in: ~/gestione_flotta/backup/")
    elif not DRY_RUN:
        print("\n  \033[92mInstallazione completata con successo!\033[0m")
        print("  Riavvia il server: ~/gestione_flotta/scripts/gestione_flotta.sh restart")
    else:
        print("\n  Esegui senza --dry-run per applicare le modifiche.")
    
    print()


if __name__ == '__main__':
    main()
