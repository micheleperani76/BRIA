#!/bin/bash
# ==============================================================================
# PATCH - Template Trascrizione (Fase 3)
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-03
# Descrizione: 
#   1. Aggiunge route pagina /trascrizione al blueprint
#   2. Aggiunge link sidebar in base.html
#   3. Aggiunge widget FAB (microfono flottante) in base.html
#
# Uso: bash scripts/patch_trascrizione_fase3.sh
# ==============================================================================

set -e

cd ~/gestione_flotta

echo "=================================================="
echo "  PATCH FASE 3 - Template Trascrizione"
echo "=================================================="
echo ""

# ==============================================================================
# 1. BACKUP
# ==============================================================================
echo "[1/4] Backup..."
cp app/routes_trascrizione.py app/routes_trascrizione.py.bak.fase3
cp templates/base.html templates/base.html.bak.fase3
echo "  OK"

# ==============================================================================
# 2. AGGIUNTA ROUTE PAGINA al blueprint
# ==============================================================================
echo ""
echo "[2/4] Aggiunta route pagina /trascrizione..."

if grep -q "def pagina_trascrizione" app/routes_trascrizione.py; then
    echo "  SKIP - Route pagina gia presente"
else
    # Aggiungi import render_template se mancante
    if ! grep -q "render_template" app/routes_trascrizione.py; then
        sed -i 's/from flask import (/from flask import (render_template, /' app/routes_trascrizione.py
    fi
    
    # Aggiungi route pagina in cima alle route (dopo il commento ROUTE: Upload)
    cat >> app/routes_trascrizione.py << 'ROUTE_PAGINA'


# ==============================================================================
# ROUTE: Pagina principale trascrizioni
# ==============================================================================

@trascrizione_bp.route('/', methods=['GET'])
@login_required
def pagina_trascrizione():
    """Pagina principale trascrizioni con upload e lista."""
    return render_template('trascrizione.html')
ROUTE_PAGINA
    
    echo "  OK - Route pagina aggiunta"
fi

# ==============================================================================
# 3. LINK SIDEBAR in base.html
# ==============================================================================
echo ""
echo "[3/4] Aggiunta link sidebar..."

if grep -q "trascrizione" templates/base.html; then
    echo "  SKIP - Link trascrizione gia presente"
else
    # Inserisci dopo "Esporta e Stampa"
    sed -i '/<i class="bi bi-file-earmark-spreadsheet"><\/i> <span>Esporta e Stampa<\/span>/a\
        </a>\
        <a href="/trascrizione" class="nav-link {% if request.endpoint == '"'"'trascrizione.pagina_trascrizione'"'"' %}active{% endif %}" data-tooltip="Trascrizioni">\
            <i class="bi bi-mic"></i> <span>Trascrizioni</span>' templates/base.html
    
    echo "  OK - Link sidebar aggiunto"
fi

# ==============================================================================
# 4. WIDGET FAB in base.html
# ==============================================================================
echo ""
echo "[4/4] Aggiunta widget FAB..."

if grep -q "fab-trascrizione" templates/base.html; then
    echo "  SKIP - Widget FAB gia presente"
else
    # Inserisci include del FAB prima di </body>
    sed -i '/<\/body>/i\
    {% include "trascrizione/_fab.html" %}' templates/base.html
    
    echo "  OK - Widget FAB aggiunto"
fi

# ==============================================================================
# VERIFICA
# ==============================================================================
echo ""
echo "Verifica..."

# Verifica route
if grep -q "def pagina_trascrizione" app/routes_trascrizione.py; then
    echo "  OK - Route pagina presente"
else
    echo "  ERRORE - Route pagina mancante!"
fi

# Verifica sidebar
if grep -q "Trascrizioni" templates/base.html; then
    echo "  OK - Link sidebar presente"
else
    echo "  ERRORE - Link sidebar mancante!"
fi

# Verifica FAB
if grep -q "fab-trascrizione" templates/base.html; then
    echo "  OK - Widget FAB presente"
else
    echo "  ERRORE - Widget FAB mancante!"
fi

# Verifica sintassi Python
python3 -c "import ast; ast.parse(open('app/routes_trascrizione.py').read()); print('  OK - routes_trascrizione.py sintassi OK')"

# Verifica template
if [ -f "templates/trascrizione.html" ]; then
    echo "  OK - templates/trascrizione.html presente"
else
    echo "  ERRORE - templates/trascrizione.html mancante!"
fi

echo ""
echo "=================================================="
echo "  PATCH FASE 3 COMPLETATA"
echo "=================================================="
echo ""
echo "Prossimi passi:"
echo "  1. Riavvia il server Flask"
echo "  2. Vai a http://localhost:5001/trascrizione"
echo "  3. Vedrai upload + lista trascrizioni"
