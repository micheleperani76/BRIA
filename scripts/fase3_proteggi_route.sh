#!/bin/bash
# ==============================================================================
# FASE 3 - Protezione TUTTE le route
# ==============================================================================
# Data: 2025-01-20
# ==============================================================================

WEB_SERVER="$HOME/gestione_flotta/app/web_server.py"

echo ""
echo "============================================================"
echo "  FASE 3 - Protezione Route"
echo "============================================================"
echo ""

# Backup
cp "$WEB_SERVER" "$WEB_SERVER.bak_fase3_$(date +%H%M%S)"
echo "✓ Backup creato"

# Verifica che l'import admin_required esista, altrimenti lo aggiungo
if ! grep -q "admin_required" "$WEB_SERVER"; then
    sed -i "s/from app.auth import auth_context_processor, login_required/from app.auth import auth_context_processor, login_required, admin_required, permesso_richiesto/" "$WEB_SERVER"
    echo "✓ Import admin_required e permesso_richiesto aggiunti"
fi

echo ""
echo "Aggiungo @login_required alle route..."
echo ""

# ==============================================================================
# ROUTE GIÀ PROTETTE (verifica e salta se già presenti)
# ==============================================================================
# /dashboard, /clienti, /flotta, /statistiche, /admin - già fatte

# ==============================================================================
# ROUTE DA PROTEGGERE CON @login_required
# ==============================================================================

# Cliente dettaglio
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>')$" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>')$/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id> protetta"
fi

# Cliente evernote
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/evernote')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/evernote')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/evernote protetta"
fi

# Flotta cerca
if ! grep -A1 "@app.route('/flotta/cerca')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/flotta\/cerca')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /flotta/cerca protetta"
fi

# Flotta cliente
if ! grep -A1 "@app.route('/flotta/cliente/" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/flotta\/cliente\//a\\@login_required" "$WEB_SERVER"
    echo "✓ /flotta/cliente/<nome> protetta"
fi

# Flotta per noleggiatore
if ! grep -A1 "@app.route('/flotta/per-noleggiatore')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/flotta\/per-noleggiatore')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /flotta/per-noleggiatore protetta"
fi

# Flotta per commerciale
if ! grep -A1 "@app.route('/flotta/per-commerciale')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/flotta\/per-commerciale')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /flotta/per-commerciale protetta"
fi

# Flotta gestione commerciali
if ! grep -A1 "@app.route('/flotta/gestione-commerciali')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/flotta\/gestione-commerciali')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /flotta/gestione-commerciali protetta"
fi

# Flotta assegna commerciali POST
if ! grep -A1 "@app.route('/flotta/assegna-commerciali'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/flotta\/assegna-commerciali'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /flotta/assegna-commerciali protetta"
fi

# Veicolo dettaglio
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>')$" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>')$/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id> protetta"
fi

# Veicolo costi-km
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/costi-km'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/costi-km'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/costi-km protetta"
fi

# Veicolo driver
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/driver'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/driver'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/driver protetta"
fi

# Veicolo nota nuova
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/nota/nuova'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/nota\/nuova'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/nota/nuova protetta"
fi

# Veicolo nota modifica
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/nota/modifica'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/nota\/modifica'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/nota/modifica protetta"
fi

# Veicolo nota elimina
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/nota/elimina'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/nota\/elimina'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/nota/elimina protetta"
fi

# Veicolo salva-km
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/salva-km'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/salva-km'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/salva-km protetta"
fi

# Veicolo salva-targa
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/salva-targa'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/salva-targa'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/salva-targa protetta"
fi

# Veicolo franchigia-km
if ! grep -A1 "@app.route('/veicolo/<int:veicolo_id>/franchigia-km'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/veicolo\/<int:veicolo_id>\/franchigia-km'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /veicolo/<id>/franchigia-km protetta"
fi

# Export excel
if ! grep -A1 "@app.route('/export/excel')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/export\/excel')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /export/excel protetta"
fi

# Cerca identificativo
if ! grep -A1 "@app.route('/cerca/" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cerca\//a\\@login_required" "$WEB_SERVER"
    echo "✓ /cerca/<id> protetta"
fi

# Cliente note (fullscreen)
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/note')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/note')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/note protetta"
fi

# ==============================================================================
# ROUTE CLIENTE - operazioni varie
# ==============================================================================

# Cliente nota nuova
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/nota/nuova'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/nota\/nuova'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/nota/nuova protetta"
fi

# Cliente nota modifica
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/nota/modifica'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/nota\/modifica'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/nota/modifica protetta"
fi

# Cliente nota elimina
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/nota/elimina'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/nota\/elimina'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/nota/elimina protetta"
fi

# Cliente nota fissa
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/nota/fissa'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/nota\/fissa'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/nota/fissa protetta"
fi

# Cliente note cerca
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/note/cerca')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/note\/cerca')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/note/cerca protetta"
fi

# Cliente allegato elimina
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/allegato/elimina'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/allegato\/elimina'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/allegato/elimina protetta"
fi

# Cliente referente nuovo
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/referente/nuovo'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/referente\/nuovo'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/referente/nuovo protetta"
fi

# Cliente referente modifica
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/referente/<int:referente_id>/modifica'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/referente\/<int:referente_id>\/modifica'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/referente/<id>/modifica protetta"
fi

# Cliente referente elimina
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/referente/<int:referente_id>/elimina'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/referente\/<int:referente_id>\/elimina'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/referente/<id>/elimina protetta"
fi

# Cliente contatti modifica
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/contatti/modifica'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/contatti\/modifica'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/contatti/modifica protetta"
fi

# Cliente indirizzo modifica
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/indirizzo/modifica'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/indirizzo\/modifica'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/indirizzo/modifica protetta"
fi

# Cliente capogruppo modifica
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/capogruppo/modifica'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/capogruppo\/modifica'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/capogruppo/modifica protetta"
fi

# Cliente sdibic modifica
if ! grep -A1 "@app.route('/cliente/<int:cliente_id>/sdibic/modifica'" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/cliente\/<int:cliente_id>\/sdibic\/modifica'/a\\@login_required" "$WEB_SERVER"
    echo "✓ /cliente/<id>/sdibic/modifica protetta"
fi

# ==============================================================================
# ROUTE API - protezione
# ==============================================================================

# API cliente
if ! grep -A1 "@app.route('/api/cliente/<identificativo>')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/api\/cliente\/<identificativo>')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /api/cliente/<id> protetta"
fi

# API cerca
if ! grep -A1 "@app.route('/api/cerca')" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/api\/cerca')/a\\@login_required" "$WEB_SERVER"
    echo "✓ /api/cerca protetta"
fi

# API noleggiatore assistenza
if ! grep -A1 "@app.route('/api/noleggiatore-assistenza/" "$WEB_SERVER" | grep -q "@login_required"; then
    sed -i "/@app.route('\/api\/noleggiatore-assistenza\//a\\@login_required" "$WEB_SERVER"
    echo "✓ /api/noleggiatore-assistenza protetta"
fi

# ==============================================================================
# ROUTE ADMIN - protezione speciale con admin_required
# ==============================================================================

echo ""
echo "Aggiungo protezione admin alle route /admin/..."
echo ""

# Admin import-pdf POST
if ! grep -A1 "@app.route('/admin/import-pdf'" "$WEB_SERVER" | grep -q "@login_required\|@admin_required"; then
    sed -i "/@app.route('\/admin\/import-pdf'/a\\@login_required\\
@permesso_richiesto('admin_sistema')" "$WEB_SERVER"
    echo "✓ /admin/import-pdf protetta (admin)"
fi

# Admin pulisci-log POST
if ! grep -A1 "@app.route('/admin/pulisci-log'" "$WEB_SERVER" | grep -q "@login_required\|@admin_required"; then
    sed -i "/@app.route('\/admin\/pulisci-log'/a\\@login_required\\
@permesso_richiesto('admin_sistema')" "$WEB_SERVER"
    echo "✓ /admin/pulisci-log protetta (admin)"
fi

# Admin upload-pdf POST
if ! grep -A1 "@app.route('/admin/upload-pdf'" "$WEB_SERVER" | grep -q "@login_required\|@admin_required"; then
    sed -i "/@app.route('\/admin\/upload-pdf'/a\\@login_required\\
@permesso_richiesto('admin_sistema')" "$WEB_SERVER"
    echo "✓ /admin/upload-pdf protetta (admin)"
fi

# Admin import-pdf-async POST
if ! grep -A1 "@app.route('/admin/import-pdf-async'" "$WEB_SERVER" | grep -q "@login_required\|@admin_required"; then
    sed -i "/@app.route('\/admin\/import-pdf-async'/a\\@login_required\\
@permesso_richiesto('admin_sistema')" "$WEB_SERVER"
    echo "✓ /admin/import-pdf-async protetta (admin)"
fi

# Admin import-status
if ! grep -A1 "@app.route('/admin/import-status')" "$WEB_SERVER" | grep -q "@login_required\|@admin_required"; then
    sed -i "/@app.route('\/admin\/import-status')/a\\@login_required\\
@permesso_richiesto('admin_sistema')" "$WEB_SERVER"
    echo "✓ /admin/import-status protetta (admin)"
fi

# Admin crontab
if ! grep -A1 "@app.route('/admin/crontab'" "$WEB_SERVER" | grep -q "@login_required\|@admin_required"; then
    sed -i "/@app.route('\/admin\/crontab'/a\\@login_required\\
@permesso_richiesto('admin_sistema')" "$WEB_SERVER"
    echo "✓ /admin/crontab protetta (admin)"
fi

# Aggiorna la route /admin principale per richiedere permesso admin_sistema
# Prima rimuovo @login_required se c'è e aggiungo la versione con permesso
sed -i "/@app.route('\/admin')$/{n;s/@login_required/@login_required\n@permesso_richiesto('admin_sistema')/}" "$WEB_SERVER"
echo "✓ /admin protetta con permesso admin_sistema"

echo ""
echo "============================================================"
echo "  PROTEZIONE COMPLETATA"
echo "============================================================"
echo ""
echo "  Riavvia il server:"
echo "  kill \$(pgrep -f web_server.py)"
echo "  cd ~/gestione_flotta && nohup python3 -m app.web_server &"
echo ""
echo "  Oppure:"
echo "  ./scripts/avvia_server.sh start"
echo ""
