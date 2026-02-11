#!/bin/bash
# ==============================================================================
# PATCH - Layout Config: aggiunta TEMPLATE_MAP + get_layout_quadri()
# ==============================================================================
# Data: 2026-02-10
# Uso: bash scripts/patch_layout_fase2.sh
# ==============================================================================

set -e
cd ~/gestione_flotta

echo "=================================================="
echo "  PATCH FASE 2 - Rendering dinamico layout"
echo "=================================================="
echo ""

# ==============================================================================
# 1. BACKUP
# ==============================================================================
echo "[1/5] Backup..."
TS=$(date +%Y%m%d_%H%M%S)
cp app/layout_config.py backup/app__layout_config.py.bak_fase2_${TS}
cp app/web_server.py backup/app__web_server.py.bak_fase2_${TS}
cp templates/dettaglio.html backup/templates__dettaglio.html.bak_fase2_${TS}
echo "  OK - 3 backup creati"

# ==============================================================================
# 2. AGGIUNTA TEMPLATE_MAP + get_layout_quadri() a layout_config.py
# ==============================================================================
echo ""
echo "[2/5] Patch layout_config.py..."

if grep -q "TEMPLATE_MAP" app/layout_config.py; then
    echo "  SKIP - TEMPLATE_MAP gia presente"
else
    cat >> app/layout_config.py << 'LAYOUT_PATCH'


# ==============================================================================
# MAPPA QUADRI -> TEMPLATE (Fase 2)
# ==============================================================================

TEMPLATE_MAP = {
    'dati_aziendali':       'dettaglio/dati_aziendali/_content.html',
    'capogruppo':           'dettaglio/capogruppo/_content.html',
    'collegamenti':         'dettaglio/collegamenti/_riquadro.html',
    'contatti':             'dettaglio/contatti/_content.html',
    'crm':                  'componenti/crm/_riquadro.html',
    'rating':               'dettaglio/rating/_content.html',
    'fido':                 'dettaglio/fido/_content.html',
    'noleggiatori':         'componenti/noleggiatori/_riquadro.html',
    'flotta':               'dettaglio/flotta/_content.html',
    'info':                 'dettaglio/info/_content.html',
    'referenti':            'dettaglio/referenti/_content.html',
    'descrizione':          'dettaglio/descrizione/_content.html',
    'finanziari':           'dettaglio/finanziari/_content.html',
    'documenti':            'documenti_cliente.html',
    'veicoli':              'dettaglio/veicoli/_content.html',
    'vetture_stock':        'dettaglio/vetture_stock/_content.html',
    'storico':              'dettaglio/storico/_content.html',
    'commerciale_storico':  'dettaglio/commerciale_storico/_content.html',
}


def get_layout_quadri():
    """
    Restituisce la lista dei quadri del layout attivo, arricchita con
    il percorso template, ordinata per (y, x).
    Il modal commerciale_storico viene escluso (renderizzato a parte).
    """
    layout = get_active_layout()
    quadri = layout.get('quadri', [])
    result = []
    for q in quadri:
        qid = q.get('id', '')
        # Il modal viene sempre renderizzato fuori dalla griglia
        if qid == 'commerciale_storico':
            continue
        tmpl = TEMPLATE_MAP.get(qid)
        if tmpl:
            result.append({
                'id': qid,
                'x': q.get('x', 0),
                'y': q.get('y', 0),
                'w': q.get('w', 12),
                'h': q.get('h', 1),
                'template': tmpl,
            })
    result.sort(key=lambda r: (r['y'], r['x']))
    return result
LAYOUT_PATCH
    echo "  OK - TEMPLATE_MAP + get_layout_quadri() aggiunti"
fi

# ==============================================================================
# 3. PATCH web_server.py - import get_layout_quadri
# ==============================================================================
echo ""
echo "[3/5] Patch web_server.py (import)..."

if grep -q "get_layout_quadri" app/web_server.py; then
    echo "  SKIP - import gia presente"
else
    # Aggiungi import dopo la riga che importa init_layout
    sed -i '/from app.layout_config import init_layout/s/$/, get_layout_quadri/' app/web_server.py
    echo "  OK - import get_layout_quadri aggiunto"
fi

# ==============================================================================
# 4. PATCH web_server.py - passare layout_quadri a render_template
# ==============================================================================
echo ""
echo "[4/5] Patch web_server.py (render_template)..."

if grep -q "layout_quadri" app/web_server.py; then
    echo "  SKIP - layout_quadri gia presente in render_template"
else
    # Cerchiamo la riga "alert_crm=alert_crm)" dentro _render_dettaglio_cliente
    # e aggiungiamo layout_quadri prima della parentesi chiusa
    sed -i "s/alert_crm=alert_crm)/alert_crm=alert_crm,\n                         layout_quadri=get_layout_quadri())/" app/web_server.py
    echo "  OK - layout_quadri aggiunto a render_template"
fi

# ==============================================================================
# 5. PATCH dettaglio.html - sostituisci griglia statica
# ==============================================================================
echo ""
echo "[5/5] Patch dettaglio.html (griglia dinamica)..."

if grep -q "griglia_layout" templates/dettaglio.html; then
    echo "  SKIP - griglia dinamica gia presente"
else
    # Trova le righe di inizio e fine della griglia statica
    # Inizio: '<div class="row g-3">' (la prima occorrenza dopo l'header)
    # Fine: '{% include "dettaglio/storico/_content.html" %}'
    
    INIZIO=$(grep -n '<div class="row g-3">' templates/dettaglio.html | head -1 | cut -d: -f1)
    FINE=$(grep -n 'dettaglio/storico/_content.html' templates/dettaglio.html | head -1 | cut -d: -f1)
    
    if [ -z "$INIZIO" ] || [ -z "$FINE" ]; then
        echo "  ERRORE: Non trovo i marker della griglia statica"
        echo "  Inizio: ${INIZIO:-NON TROVATO}"
        echo "  Fine: ${FINE:-NON TROVATO}"
        exit 1
    fi
    
    echo "  Griglia statica: righe ${INIZIO}-${FINE}"
    
    # Sostituisci il blocco
    # 1. Cancella dalla riga INIZIO alla riga FINE
    # 2. Inserisci la nuova include alla riga INIZIO
    sed -i "${INIZIO},${FINE}d" templates/dettaglio.html
    sed -i "$((INIZIO-1))a\\        {% include \"dettaglio/_griglia_layout.html\" %}" templates/dettaglio.html
    
    echo "  OK - Griglia statica sostituita con include dinamico"
fi

echo ""
echo "=================================================="
echo "  PATCH COMPLETATA"
echo "=================================================="
echo ""
echo "  Prossimi passi:"
echo "    1. Copia _griglia_layout.html in templates/dettaglio/"
echo "    2. ~/gestione_flotta/scripts/gestione_flotta.sh restart"
echo "    3. Verifica pagina dettaglio nel browser"
echo ""
