#!/usr/bin/env python3
# ==============================================================================
# DEPLOY: Upload Multi-File + Import CRM + Notifica
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Deploya i nuovi file e patcha admin.html e web_server.py
#
# FILE NUOVI:
#   app/routes_admin_upload.py
#   app/connettori_notifiche/aggiorna_crm.py
#   templates/admin/_upload_import.html
#   templates/admin/_upload_import_scripts.html
#   scripts/cron_promemoria_crm.py
#
# PATCH:
#   templates/admin.html - Sostituisce upload/import box + JS
#   app/web_server.py    - Registra blueprint admin_upload_bp
#
# USO:
#   python3 scripts/deploy_upload_multifile.py --dry-run
#   python3 scripts/deploy_upload_multifile.py
# ==============================================================================

import sys
import shutil
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.absolute()
SCARICATI = BASE_DIR / 'Scaricati'
BACKUP_DIR = BASE_DIR / 'backup'

DRY_RUN = '--dry-run' in sys.argv


def log(msg, livello='INFO'):
    simboli = {'INFO': ' ', 'OK': '+', 'ERR': '!', 'SKIP': '-', 'WARN': '~'}
    s = simboli.get(livello, ' ')
    print(f"  [{s}] {msg}")


def backup_file(filepath):
    """Crea backup di un file."""
    if not filepath.exists():
        return None
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_bak = filepath.name.replace('/', '__').replace('.', '_', filepath.name.count('.') - 1)
    bak = BACKUP_DIR / f"{filepath.parent.name}__{filepath.name}.bak_{ts}"
    if not DRY_RUN:
        shutil.copy2(str(filepath), str(bak))
    log(f"Backup: {bak.name}", 'OK')
    return bak


# ==============================================================================
# DEPLOY FILE NUOVI
# ==============================================================================

def deploy_nuovi_file():
    """Verifica che i nuovi file siano in Scaricati e li sposta."""
    print("\n--- DEPLOY FILE NUOVI ---")

    file_map = {
        'routes_admin_upload.py': BASE_DIR / 'app' / 'routes_admin_upload.py',
        'aggiorna_crm.py': BASE_DIR / 'app' / 'connettori_notifiche' / 'aggiorna_crm.py',
        '_upload_import.html': BASE_DIR / 'templates' / 'admin' / '_upload_import.html',
        '_upload_import_scripts.html': BASE_DIR / 'templates' / 'admin' / '_upload_import_scripts.html',
        'cron_promemoria_crm.py': BASE_DIR / 'scripts' / 'cron_promemoria_crm.py',
    }

    ok = 0
    for nome, destinazione in file_map.items():
        sorgente = SCARICATI / nome
        if not sorgente.exists():
            if destinazione.exists():
                log(f"{nome} gia' in posizione", 'SKIP')
                ok += 1
            else:
                log(f"{nome} NON trovato in Scaricati/ ne' in destinazione!", 'ERR')
            continue

        destinazione.parent.mkdir(parents=True, exist_ok=True)

        if destinazione.exists():
            backup_file(destinazione)

        if not DRY_RUN:
            shutil.move(str(sorgente), str(destinazione))
        log(f"{nome} -> {destinazione.relative_to(BASE_DIR)}", 'OK')
        ok += 1

    return ok == len(file_map)


# ==============================================================================
# PATCH admin.html
# ==============================================================================

def patch_admin_html():
    """Sostituisce upload/import box e JS con include satellite."""
    print("\n--- PATCH admin.html ---")

    filepath = BASE_DIR / 'templates' / 'admin.html'
    if not filepath.exists():
        log("admin.html non trovato!", 'ERR')
        return False

    content = filepath.read_text(encoding='utf-8')
    original = content

    # ---- PATCH 1: Sostituisci box Upload+Import (prima <div class="row g-4">) ----
    # Cerco il blocco che inizia con "Upload PDF Creditsafe" e finisce prima di "Pulizia Log"
    marker_inizio = '<i class="bi bi-cloud-upload"></i> Upload PDF Creditsafe'
    marker_fine = '<!-- Riga 2: Pulizia log e Crontab -->'

    # Se i marker non esistono, provo varianti
    if marker_inizio not in content:
        marker_inizio = 'Upload PDF Creditsafe'
    if marker_fine not in content:
        marker_fine = 'Pulizia Log'

    if marker_inizio not in content:
        # Gia' patchato?
        if '_upload_import.html' in content:
            log("PATCH 1: gia' applicata (include presente)", 'SKIP')
        else:
            log("PATCH 1: marker Upload non trovato!", 'ERR')
            return False
    else:
        # Trova la riga del row g-4 che contiene Upload
        lines = content.split('\n')
        idx_inizio = None
        idx_fine = None

        for i, line in enumerate(lines):
            if marker_inizio in line and idx_inizio is None:
                # Risali fino al <div class="row g-4"> che contiene questo
                j = i
                while j >= 0:
                    if 'row g-4' in lines[j] and '<div' in lines[j]:
                        idx_inizio = j
                        break
                    j -= 1
                if idx_inizio is None:
                    idx_inizio = i

            if idx_fine is None and idx_inizio is not None:
                if marker_fine in line:
                    idx_fine = i
                    break
                # Alternativa: cerca la chiusura </div> del row
                # dopo la chiusura di import-result

        if idx_inizio is None:
            log("PATCH 1: inizio blocco non trovato!", 'ERR')
            return False

        if idx_fine is None:
            # Cerca la fine del blocco import (</div> di chiusura row)
            depth = 0
            for i in range(idx_inizio, len(lines)):
                depth += lines[i].count('<div') - lines[i].count('</div')
                if depth <= 0 and i > idx_inizio:
                    idx_fine = i + 1
                    break

        if idx_fine is None:
            log("PATCH 1: fine blocco non trovato!", 'ERR')
            return False

        # Sostituisci
        nuovo_blocco = '{% include "admin/_upload_import.html" %}'
        lines_nuovo = lines[:idx_inizio] + [nuovo_blocco] + lines[idx_fine:]
        content = '\n'.join(lines_nuovo)
        log(f"PATCH 1: sostituito righe {idx_inizio+1}-{idx_fine} con include", 'OK')

    # ---- PATCH 2: Rimuovi vecchio JS upload/import (tieni crontab) ----
    # Cerco il blocco <script> che contiene "UPLOAD DRAG & DROP"
    if 'UPLOAD DRAG & DROP' in content:
        lines = content.split('\n')
        idx_script_start = None
        idx_crontab_start = None
        idx_script_end = None

        for i, line in enumerate(lines):
            if '<script>' in line and idx_script_start is None:
                # Verifica che il blocco script successivo contenga upload
                blocco = '\n'.join(lines[i:i+10])
                if 'UPLOAD' in blocco or 'drop-zone' in blocco or 'file-input' in blocco:
                    idx_script_start = i

            if idx_script_start is not None and 'CRONTAB' in line:
                idx_crontab_start = i
                break

        if idx_script_start is not None and idx_crontab_start is not None:
            # Rimuovi da <script> fino a prima di CRONTAB (tieni il commento CRONTAB)
            lines_nuovo = lines[:idx_script_start] + ['<script>', 'document.addEventListener(\'DOMContentLoaded\', function() {'] + lines[idx_crontab_start:]
            content = '\n'.join(lines_nuovo)
            log(f"PATCH 2: rimosso JS upload/import (righe {idx_script_start+1}-{idx_crontab_start})", 'OK')
        else:
            log("PATCH 2: blocco JS upload non identificato con precisione", 'WARN')
    elif '_upload_import_scripts.html' in content:
        log("PATCH 2: gia' applicata", 'SKIP')
    else:
        log("PATCH 2: JS upload non trovato (potrebbe essere gia' rimosso)", 'SKIP')

    # ---- PATCH 3: Rimuovi vecchio CSS #drop-zone ----
    if '#drop-zone:hover' in content and '#drop-zone-multi' not in content:
        content = re.sub(
            r'<style>\s*#drop-zone:hover\s*\{[^}]*\}\s*</style>',
            '',
            content,
            flags=re.DOTALL
        )
        log("PATCH 3: rimosso CSS #drop-zone:hover", 'OK')
    else:
        log("PATCH 3: CSS gia' rimosso o aggiornato", 'SKIP')

    # ---- PATCH 4: Aggiungi include script prima di endblock ----
    if '_upload_import_scripts.html' not in content:
        content = content.replace(
            '{% endblock %}',
            '{% include "admin/_upload_import_scripts.html" %}\n{% endblock %}'
        )
        log("PATCH 4: aggiunto include _upload_import_scripts.html", 'OK')
    else:
        log("PATCH 4: include script gia' presente", 'SKIP')

    # ---- SALVA ----
    if content != original:
        if not DRY_RUN:
            backup_file(filepath)
            filepath.write_text(content, encoding='utf-8')
        log(f"admin.html salvato ({len(content)} bytes)", 'OK')
        return True
    else:
        log("admin.html: nessuna modifica necessaria", 'SKIP')
        return True


# ==============================================================================
# PATCH web_server.py
# ==============================================================================

def patch_web_server():
    """Registra il nuovo blueprint admin_upload_bp."""
    print("\n--- PATCH web_server.py ---")

    filepath = BASE_DIR / 'app' / 'web_server.py'
    if not filepath.exists():
        log("web_server.py non trovato!", 'ERR')
        return False

    content = filepath.read_text(encoding='utf-8')
    original = content

    # PATCH 1: Aggiungi import del blueprint
    if 'admin_upload_bp' in content:
        log("PATCH 1: admin_upload_bp gia' importato", 'SKIP')
    else:
        # Cerca l'ultimo import di blueprint per aggiungere il nostro dopo
        # Pattern: from app.routes_xxx import xxx_bp
        match = re.search(
            r'(from app\.routes_installato import installato_bp)',
            content
        )
        if match:
            vecchio = match.group(1)
            nuovo = vecchio + '\nfrom app.routes_admin_upload import admin_upload_bp'
            content = content.replace(vecchio, nuovo, 1)
            log("PATCH 1: import admin_upload_bp aggiunto", 'OK')
        else:
            # Fallback: cerca qualsiasi import di blueprint
            match = re.search(r'(from app\.routes_\w+ import \w+_bp)', content)
            if match:
                vecchio = match.group(1)
                nuovo = vecchio + '\nfrom app.routes_admin_upload import admin_upload_bp'
                content = content.replace(vecchio, nuovo, 1)
                log("PATCH 1: import admin_upload_bp aggiunto (fallback)", 'OK')
            else:
                log("PATCH 1: punto di inserimento non trovato!", 'ERR')
                return False

    # PATCH 2: Registra blueprint
    if 'register_blueprint(admin_upload_bp)' in content:
        log("PATCH 2: blueprint gia' registrato", 'SKIP')
    else:
        match = re.search(
            r'(app\.register_blueprint\(installato_bp\))',
            content
        )
        if match:
            vecchio = match.group(1)
            nuovo = vecchio + '\napp.register_blueprint(admin_upload_bp)'
            content = content.replace(vecchio, nuovo, 1)
            log("PATCH 2: register_blueprint(admin_upload_bp) aggiunto", 'OK')
        else:
            # Fallback
            match = re.search(r'(app\.register_blueprint\(\w+_bp\))', content)
            if match:
                vecchio = match.group(1)
                nuovo = vecchio + '\napp.register_blueprint(admin_upload_bp)'
                content = content.replace(vecchio, nuovo, 1)
                log("PATCH 2: register_blueprint aggiunto (fallback)", 'OK')
            else:
                log("PATCH 2: punto di registrazione non trovato!", 'ERR')
                return False

    # ---- SALVA ----
    if content != original:
        if not DRY_RUN:
            backup_file(filepath)
            filepath.write_text(content, encoding='utf-8')
        log(f"web_server.py salvato ({len(content)} bytes)", 'OK')
        return True
    else:
        log("web_server.py: nessuna modifica necessaria", 'SKIP')
        return True


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 60)
    print("  DEPLOY: Upload Multi-File + Import CRM + Notifica")
    print("=" * 60)
    if DRY_RUN:
        print("  *** MODALITA' DRY-RUN ***")
    print(f"  Base: {BASE_DIR}")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    errori = 0

    # Step 1: Deploy file nuovi
    if not deploy_nuovi_file():
        log("Alcuni file nuovi mancanti", 'WARN')

    # Step 2: Patch admin.html
    if not patch_admin_html():
        errori += 1

    # Step 3: Patch web_server.py
    if not patch_web_server():
        errori += 1

    # Step 4: Cron
    print("\n--- CRONTAB ---")
    log("Aggiungi manualmente al crontab:", 'INFO')
    log("  0 8 * * 1 cd /home/michele/gestione_flotta && python3 scripts/cron_promemoria_crm.py >> logs/cron_promemoria.log 2>&1", 'INFO')

    # Riepilogo
    print(f"\n{'=' * 60}")
    if errori > 0:
        print(f"  ATTENZIONE: {errori} errori durante il deploy")
    elif DRY_RUN:
        print("  DRY-RUN completato. Eseguire senza --dry-run per applicare.")
    else:
        print("  DEPLOY COMPLETATO!")
        print("  Riavviare il server: ~/gestione_flotta/scripts/gestione_flotta.sh restart")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
