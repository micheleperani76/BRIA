#!/bin/bash
# ==============================================================================
# DEPLOY FASE 1 - TICKER BROADCASTING
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-06
# Descrizione: Deploy backend ticker: migrazione DB, config, motore, routes,
#              registrazione blueprint in web_server.py, link in sidebar.
#
# File deployati:
#   scripts/migrazione_ticker.py   -> Migrazione DB (3 tabelle)
#   app/config_ticker.py           -> Configurazione
#   app/motore_ticker.py           -> Logica business
#   app/routes_ticker.py           -> Blueprint Flask API
#
# Patch applicate:
#   app/web_server.py              -> Import + registrazione blueprint
#   templates/base.html            -> Link ticker in sidebar
#
# USO: bash deploy_ticker_fase1.sh
# PREREQUISITI: tutti i file in ~/gestione_flotta/Scaricati/
# ==============================================================================

BASE_DIR="$HOME/gestione_flotta"
BACKUP_DIR="$BASE_DIR/backup"
SCARICATI="$BASE_DIR/Scaricati"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}  DEPLOY FASE 1 - TICKER BROADCASTING                      ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""

# ==============================================================================
# 0. VERIFICA FILE IN SCARICATI
# ==============================================================================
echo -e "${YELLOW}[0/7]${NC} Verifica file in Scaricati/..."

ERRORI=0
for f in migrazione_ticker.py config_ticker.py motore_ticker.py routes_ticker.py; do
    if [ ! -f "$SCARICATI/$f" ]; then
        echo -e "${RED}  MANCA: $f${NC}"
        ERRORI=1
    fi
done

if [ "$ERRORI" = "1" ]; then
    echo ""
    echo "Scarica tutti i file e mettili in ~/gestione_flotta/Scaricati/"
    exit 1
fi
echo -e "${GREEN}  OK${NC} - Tutti i file presenti"

# ==============================================================================
# 1. BACKUP
# ==============================================================================
echo ""
echo -e "${YELLOW}[1/7]${NC} Backup..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

cp "$BASE_DIR/app/web_server.py" "$BACKUP_DIR/app__web_server.py.bak_${TIMESTAMP}"
echo -e "${GREEN}  OK${NC} - web_server.py"

cp "$BASE_DIR/templates/base.html" "$BACKUP_DIR/templates__base.html.bak_${TIMESTAMP}"
echo -e "${GREEN}  OK${NC} - base.html"

# ==============================================================================
# 2. DEPLOY FILE PYTHON
# ==============================================================================
echo ""
echo -e "${YELLOW}[2/7]${NC} Deploy file Python..."

cp "$SCARICATI/migrazione_ticker.py" "$BASE_DIR/scripts/"
echo -e "${GREEN}  OK${NC} - scripts/migrazione_ticker.py"

cp "$SCARICATI/config_ticker.py" "$BASE_DIR/app/"
echo -e "${GREEN}  OK${NC} - app/config_ticker.py"

cp "$SCARICATI/motore_ticker.py" "$BASE_DIR/app/"
echo -e "${GREEN}  OK${NC} - app/motore_ticker.py"

cp "$SCARICATI/routes_ticker.py" "$BASE_DIR/app/"
echo -e "${GREEN}  OK${NC} - app/routes_ticker.py"

# ==============================================================================
# 3. CREA CARTELLA TEMPLATE TICKER (vuota, per Fase 3)
# ==============================================================================
echo ""
echo -e "${YELLOW}[3/7]${NC} Crea struttura cartelle..."

mkdir -p "$BASE_DIR/templates/ticker"
echo -e "${GREEN}  OK${NC} - templates/ticker/"

# Placeholder gestione.html minimo per non avere errore 500
if [ ! -f "$BASE_DIR/templates/ticker/gestione.html" ]; then
    cat > "$BASE_DIR/templates/ticker/gestione.html" << 'TMPL'
{% extends "base.html" %}
{% block title %}Gestione Ticker{% endblock %}
{% block content %}
<div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="bi bi-megaphone me-2"></i>Gestione Ticker Broadcasting</h2>
        <a href="/ticker/api/statistiche" class="btn btn-outline-secondary btn-sm">
            <i class="bi bi-bar-chart me-1"></i>Statistiche
        </a>
    </div>
    
    <div class="alert alert-info">
        <i class="bi bi-info-circle me-2"></i>
        <strong>Fase 1 completata:</strong> Backend attivo. 
        La pagina di gestione completa (griglia + preview) arrivera' nella Fase 3.
        <br>Nel frattempo le API sono gia' funzionanti.
    </div>
    
    <!-- Info API disponibili -->
    <div class="card">
        <div class="card-header">
            <i class="bi bi-plug me-2"></i>API disponibili
        </div>
        <div class="card-body">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Metodo</th>
                        <th>Endpoint</th>
                        <th>Descrizione</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td><span class="badge bg-success">GET</span></td>
                        <td><code>/ticker/api/prossimo</code></td>
                        <td>Prossimo messaggio per il widget</td></tr>
                    <tr><td><span class="badge bg-primary">POST</span></td>
                        <td><code>/ticker/api/crea</code></td>
                        <td>Crea nuovo messaggio</td></tr>
                    <tr><td><span class="badge bg-success">GET</span></td>
                        <td><code>/ticker/api/lista</code></td>
                        <td>Lista messaggi con filtri</td></tr>
                    <tr><td><span class="badge bg-success">GET</span></td>
                        <td><code>/ticker/api/config</code></td>
                        <td>Configurazione (admin)</td></tr>
                    <tr><td><span class="badge bg-success">GET</span></td>
                        <td><code>/ticker/api/statistiche</code></td>
                        <td>Statistiche (admin)</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    {% if is_admin and in_attesa > 0 %}
    <div class="alert alert-warning mt-3">
        <i class="bi bi-clock me-2"></i>
        <strong>{{ in_attesa }}</strong> messaggi in attesa di approvazione.
    </div>
    {% endif %}
</div>
{% endblock %}
TMPL
    echo -e "${GREEN}  OK${NC} - gestione.html placeholder creato"
else
    echo -e "${YELLOW}  SKIP${NC} - gestione.html gia presente"
fi

# ==============================================================================
# 4. REGISTRA BLUEPRINT IN web_server.py
# ==============================================================================
echo ""
echo -e "${YELLOW}[4/7]${NC} Registrazione blueprint in web_server.py..."

WS="$BASE_DIR/app/web_server.py"

# 4a. Import
if grep -q "ticker_bp" "$WS"; then
    echo -e "${YELLOW}  SKIP${NC} - Import ticker_bp gia presente"
else
    # Trova l'ultimo import di blueprint e aggiungi dopo
    LAST_IMPORT=$(grep -n "from app.routes_" "$WS" | tail -1 | cut -d: -f1)
    if [ -n "$LAST_IMPORT" ]; then
        sed -i "${LAST_IMPORT}a from app.routes_ticker import ticker_bp" "$WS"
        echo -e "${GREEN}  OK${NC} - Import aggiunto (riga $((LAST_IMPORT+1)))"
    else
        echo -e "${RED}  ERRORE${NC} - Non trovo import routes in web_server.py"
        exit 1
    fi
fi

# 4b. Registrazione
if grep -q "register_blueprint(ticker_bp)" "$WS"; then
    echo -e "${YELLOW}  SKIP${NC} - register_blueprint gia presente"
else
    LAST_REG=$(grep -n "register_blueprint" "$WS" | tail -1 | cut -d: -f1)
    if [ -n "$LAST_REG" ]; then
        sed -i "${LAST_REG}a app.register_blueprint(ticker_bp)" "$WS"
        echo -e "${GREEN}  OK${NC} - Blueprint registrato (riga $((LAST_REG+1)))"
    else
        echo -e "${RED}  ERRORE${NC} - Non trovo register_blueprint in web_server.py"
        exit 1
    fi
fi

# ==============================================================================
# 5. LINK SIDEBAR IN base.html
# ==============================================================================
echo ""
echo -e "${YELLOW}[5/7]${NC} Aggiunta link ticker in sidebar..."

BASE="$BASE_DIR/templates/base.html"

if grep -q '/ticker/gestione' "$BASE"; then
    echo -e "${YELLOW}  SKIP${NC} - Link ticker gia presente in sidebar"
else
    # Aggiungi prima di "Amministrazione" per renderlo visibile a tutti
    # Lo inseriamo nella sezione "Sistema", dopo "Statistiche"
    sed -i '/<i class="bi bi-graph-up"><\/i> <span>Statistiche<\/span>/a\
        </a>\
        <a href="/ticker/gestione" class="nav-link {% if request.endpoint == '"'"'ticker.pagina_gestione'"'"' %}active{% endif %}" data-tooltip="Ticker">\
            <i class="bi bi-megaphone"></i> <span>Ticker</span>' "$BASE"
    
    # Verifica se il sed ha funzionato
    if grep -q '/ticker/gestione' "$BASE"; then
        echo -e "${GREEN}  OK${NC} - Link ticker aggiunto in sidebar (sezione Sistema)"
    else
        echo -e "${YELLOW}  WARN${NC} - Sed non ha matchato. Aggiunta manuale necessaria."
        echo "  Aggiungi in base.html nella sidebar:"
        echo '  <a href="/ticker/gestione" class="nav-link" data-tooltip="Ticker">'
        echo '      <i class="bi bi-megaphone"></i> <span>Ticker</span>'
        echo '  </a>'
    fi
fi

# ==============================================================================
# 6. MIGRAZIONE DATABASE
# ==============================================================================
echo ""
echo -e "${YELLOW}[6/7]${NC} Migrazione database..."

cd "$BASE_DIR"
python3 scripts/migrazione_ticker.py

# ==============================================================================
# 7. VERIFICA FINALE
# ==============================================================================
echo ""
echo -e "${YELLOW}[7/7]${NC} Verifica finale..."

# File Python
for f in app/config_ticker.py app/motore_ticker.py app/routes_ticker.py; do
    if [ -f "$BASE_DIR/$f" ]; then
        python3 -c "import ast; ast.parse(open('$BASE_DIR/$f').read())" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  OK${NC} - $f (sintassi OK)"
        else
            echo -e "${RED}  ERRORE${NC} - $f (errore sintassi!)"
        fi
    else
        echo -e "${RED}  ERRORE${NC} - $f mancante!"
    fi
done

# web_server.py sintassi
python3 -c "import ast; ast.parse(open('$WS').read())" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  OK${NC} - web_server.py (sintassi OK)"
else
    echo -e "${RED}  ERRORE${NC} - web_server.py (errore sintassi!)"
fi

# Blueprint registrato
grep -q "ticker_bp" "$WS" && \
    echo -e "${GREEN}  OK${NC} - Blueprint registrato" || \
    echo -e "${RED}  ERRORE${NC} - Blueprint non registrato!"

# Link sidebar
grep -q '/ticker/gestione' "$BASE" && \
    echo -e "${GREEN}  OK${NC} - Link sidebar presente" || \
    echo -e "${YELLOW}  WARN${NC} - Link sidebar da aggiungere manualmente"

# Template
[ -f "$BASE_DIR/templates/ticker/gestione.html" ] && \
    echo -e "${GREEN}  OK${NC} - Template gestione presente" || \
    echo -e "${RED}  ERRORE${NC} - Template gestione mancante!"

# Tabelle DB
python3 -c "
import sqlite3
conn = sqlite3.connect('$BASE_DIR/db/gestionale.db')
tables = [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ticker_%'\").fetchall()]
conn.close()
for t in ['ticker_messaggi', 'ticker_config', 'ticker_log']:
    if t in tables:
        print(f'  OK - Tabella {t}')
    else:
        print(f'  ERRORE - Tabella {t} mancante!')
"

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${GREEN}  DEPLOY FASE 1 COMPLETATO                                 ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""
echo "Prossimi passi:"
echo "  1. Riavvia il server: ~/gestione_flotta/scripts/gestione_flotta.sh restart"
echo "  2. Testa le API:"
echo "     curl http://localhost:5001/ticker/api/prossimo"
echo "     curl http://localhost:5001/ticker/api/config"
echo "  3. Verifica pagina: http://localhost:5001/ticker/gestione"
echo ""
