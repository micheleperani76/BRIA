#!/bin/bash
# ==============================================================================
# DEPLOY - Pagina Veicoli Installato
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-09
# Descrizione: Installa blueprint, templates e sidebar per pagina Installato
#
# Uso:
#   cd ~/gestione_flotta
#   bash scripts/deploy_installato.sh --dry-run
#   bash scripts/deploy_installato.sh
# ==============================================================================

set -e
cd ~/gestione_flotta

DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "[DRY-RUN] Nessuna modifica applicata"
    echo ""
fi

echo "=================================================="
echo "  DEPLOY - Pagina Veicoli Installato"
echo "=================================================="
echo ""

ERRORI=0

# ==============================================================================
# 1. VERIFICA FILE SORGENTE
# ==============================================================================
echo "[1/6] Verifica file sorgente..."

for f in ~/Scaricati/routes_installato.py ~/Scaricati/installato_index.html ~/Scaricati/installato_storico.html; do
    if [ -f "$f" ]; then
        echo "  OK - $(basename $f)"
    else
        echo "  ERRORE - $f non trovato!"
        ERRORI=$((ERRORI+1))
    fi
done

if [ $ERRORI -gt 0 ]; then
    echo ""
    echo "ERRORE: File mancanti. Copia i file in ~/Scaricati/ e riprova."
    exit 1
fi

# ==============================================================================
# 2. BACKUP
# ==============================================================================
echo ""
echo "[2/6] Backup..."

TS=$(date +%Y%m%d_%H%M%S)

if [ "$DRY_RUN" = false ]; then
    cp app/web_server.py "app/web_server.py.bak_installato_${TS}"
    cp templates/base.html "templates/base.html.bak_installato_${TS}"
    echo "  OK - Backup creati (.bak_installato_${TS})"
else
    echo "  [DRY-RUN] Backup: web_server.py, base.html"
fi

# ==============================================================================
# 3. COPIA FILE
# ==============================================================================
echo ""
echo "[3/6] Copia file..."

if [ "$DRY_RUN" = false ]; then
    # Blueprint
    cp ~/Scaricati/routes_installato.py app/routes_installato.py
    echo "  OK - app/routes_installato.py"

    # Templates
    mkdir -p templates/installato
    cp ~/Scaricati/installato_index.html templates/installato/index.html
    cp ~/Scaricati/installato_storico.html templates/installato/storico.html
    echo "  OK - templates/installato/index.html"
    echo "  OK - templates/installato/storico.html"
else
    echo "  [DRY-RUN] cp routes_installato.py -> app/"
    echo "  [DRY-RUN] cp installato_index.html -> templates/installato/index.html"
    echo "  [DRY-RUN] cp installato_storico.html -> templates/installato/storico.html"
fi

# ==============================================================================
# 4. REGISTRA BLUEPRINT in web_server.py
# ==============================================================================
echo ""
echo "[4/6] Registrazione blueprint..."

WS="app/web_server.py"

# 4a. Import
if grep -q "installato_bp" "$WS"; then
    echo "  SKIP - Import installato_bp gia' presente"
else
    if [ "$DRY_RUN" = false ]; then
        LAST_IMPORT=$(grep -n "from app.routes_" "$WS" | tail -1 | cut -d: -f1)
        if [ -n "$LAST_IMPORT" ]; then
            sed -i "${LAST_IMPORT}a from app.routes_installato import installato_bp" "$WS"
            echo "  OK - Import aggiunto (riga $((LAST_IMPORT+1)))"
        else
            echo "  ERRORE - Non trovo import routes in web_server.py"
            ERRORI=$((ERRORI+1))
        fi
    else
        echo "  [DRY-RUN] Aggiungere: from app.routes_installato import installato_bp"
    fi
fi

# 4b. Registrazione
if grep -q "register_blueprint(installato_bp)" "$WS"; then
    echo "  SKIP - register_blueprint gia' presente"
else
    if [ "$DRY_RUN" = false ]; then
        LAST_REG=$(grep -n "register_blueprint" "$WS" | tail -1 | cut -d: -f1)
        if [ -n "$LAST_REG" ]; then
            sed -i "${LAST_REG}a app.register_blueprint(installato_bp)" "$WS"
            echo "  OK - Blueprint registrato (riga $((LAST_REG+1)))"
        else
            echo "  ERRORE - Non trovo register_blueprint in web_server.py"
            ERRORI=$((ERRORI+1))
        fi
    else
        echo "  [DRY-RUN] Aggiungere: app.register_blueprint(installato_bp)"
    fi
fi

# ==============================================================================
# 5. SIDEBAR in base.html
# ==============================================================================
echo ""
echo "[5/6] Aggiunta link sidebar..."

BASE="templates/base.html"

if grep -q '/installato' "$BASE"; then
    echo "  SKIP - Link /installato gia' presente in sidebar"
else
    if [ "$DRY_RUN" = false ]; then
        # Inserisci dopo "Dashboard Flotta" nella sezione Flotta
        sed -i '/<i class="bi bi-speedometer2"><\/i> <span>Dashboard Flotta<\/span>/,/<\/a>/{
            /<\/a>/a\
        <a href="/installato" class="nav-link {% if request.endpoint and request.endpoint.startswith('"'"'installato'"'"') %}active{% endif %}" data-tooltip="Installato">\
            <i class="bi bi-check-circle-fill"></i> <span>Installato</span>\
        </a>
        }' "$BASE"

        if grep -q '/installato' "$BASE"; then
            echo "  OK - Link Installato aggiunto in sidebar (dopo Dashboard Flotta)"
        else
            echo "  WARN - sed non ha matchato, provo metodo alternativo..."
            # Metodo alternativo: dopo la riga che contiene "Dashboard Flotta" + </a>
            RIGA_FLOTTA=$(grep -n "Dashboard Flotta" "$BASE" | head -1 | cut -d: -f1)
            if [ -n "$RIGA_FLOTTA" ]; then
                # Trova il prossimo </a> dopo quella riga
                RIGA_CHIUSURA=$(tail -n +"$RIGA_FLOTTA" "$BASE" | grep -n '</a>' | head -1 | cut -d: -f1)
                RIGA_INSERT=$((RIGA_FLOTTA + RIGA_CHIUSURA))
                sed -i "${RIGA_INSERT}a\\
        <a href=\"/installato\" class=\"nav-link {% if request.endpoint and request.endpoint.startswith('installato') %}active{% endif %}\" data-tooltip=\"Installato\">\\
            <i class=\"bi bi-check-circle-fill\"></i> <span>Installato</span>\\
        </a>" "$BASE"
                echo "  OK - Link aggiunto (metodo alternativo, riga $RIGA_INSERT)"
            else
                echo "  ERRORE - Impossibile aggiungere link sidebar"
                ERRORI=$((ERRORI+1))
            fi
        fi
    else
        echo "  [DRY-RUN] Aggiungere link /installato dopo Dashboard Flotta"
    fi
fi

# ==============================================================================
# 6. VERIFICA
# ==============================================================================
echo ""
echo "[6/6] Verifica..."

if [ "$DRY_RUN" = false ]; then
    # Verifica sintassi Python
    python3 -c "import ast; ast.parse(open('app/web_server.py').read()); print('  OK - web_server.py sintassi')"
    python3 -c "import ast; ast.parse(open('app/routes_installato.py').read()); print('  OK - routes_installato.py sintassi')"

    # Verifica file presenti
    [ -f "templates/installato/index.html" ] && echo "  OK - templates/installato/index.html" || echo "  ERRORE - template index mancante"
    [ -f "templates/installato/storico.html" ] && echo "  OK - templates/installato/storico.html" || echo "  ERRORE - template storico mancante"

    # Verifica registrazione
    grep -q "installato_bp" "$WS" && echo "  OK - Blueprint registrato" || echo "  ERRORE - Blueprint non registrato"
    grep -q '/installato' "$BASE" && echo "  OK - Link sidebar presente" || echo "  ERRORE - Link sidebar mancante"
else
    echo "  [DRY-RUN] Verifiche saltate"
fi

# ==============================================================================
# RIEPILOGO
# ==============================================================================
echo ""
echo "=================================================="
if [ $ERRORI -eq 0 ]; then
    if [ "$DRY_RUN" = true ]; then
        echo "  DRY-RUN completato. 0 errori."
        echo "  Per applicare: bash scripts/deploy_installato.sh"
    else
        echo "  DEPLOY COMPLETATO! 0 errori."
        echo ""
        echo "  Prossimi passi:"
        echo "    ~/gestione_flotta/scripts/gestione_flotta.sh restart"
        echo "    Testa: http://localhost:5001/installato"
    fi
else
    echo "  DEPLOY CON $ERRORI ERRORI. Controllare l'output."
fi
echo "=================================================="
