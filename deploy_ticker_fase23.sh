#!/bin/bash
# ==============================================================================
# DEPLOY FASE 2+3 - WIDGET TICKER + PAGINA GESTIONE
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-06
# Descrizione: Aggiorna widget topbar (5 animazioni + polling)
#              e installa pagina gestione completa con satellite files.
#
# File deployati:
#   templates/componenti/_topbar.html     -> Widget aggiornato (Fase 2)
#   templates/ticker/gestione.html        -> Pagina principale (Fase 3)
#   templates/ticker/_styles.html         -> CSS
#   templates/ticker/_preview.html        -> Preview live
#   templates/ticker/_griglia.html        -> Griglia messaggi
#   templates/ticker/_modal_nuovo.html    -> Modal creazione/modifica
#   templates/ticker/_scripts.html        -> JavaScript
#
# USO: bash deploy_ticker_fase23.sh
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
echo -e "${BLUE}  DEPLOY FASE 2+3 - WIDGET + PAGINA GESTIONE               ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""

# ==============================================================================
# 0. VERIFICA FILE
# ==============================================================================
echo -e "${YELLOW}[0/4]${NC} Verifica file in Scaricati/..."

ERRORI=0
LISTA="_topbar.html gestione.html _styles.html _preview.html _griglia.html _modal_nuovo.html _scripts.html"

for f in $LISTA; do
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
echo -e "${GREEN}  OK${NC} - Tutti i 7 file presenti"

# ==============================================================================
# 1. BACKUP
# ==============================================================================
echo ""
echo -e "${YELLOW}[1/4]${NC} Backup..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Backup topbar
if [ -f "$BASE_DIR/templates/componenti/_topbar.html" ]; then
    cp "$BASE_DIR/templates/componenti/_topbar.html" \
       "$BACKUP_DIR/templates__componenti___topbar.html.bak_${TIMESTAMP}"
    echo -e "${GREEN}  OK${NC} - _topbar.html v1 backuppata"
fi

# Backup gestione (se esiste il placeholder)
if [ -f "$BASE_DIR/templates/ticker/gestione.html" ]; then
    cp "$BASE_DIR/templates/ticker/gestione.html" \
       "$BACKUP_DIR/templates__ticker__gestione.html.bak_${TIMESTAMP}"
    echo -e "${GREEN}  OK${NC} - gestione.html placeholder backuppato"
fi

# ==============================================================================
# 2. DEPLOY FILES
# ==============================================================================
echo ""
echo -e "${YELLOW}[2/4]${NC} Deploy file..."

# Fase 2: Widget topbar
cp "$SCARICATI/_topbar.html" "$BASE_DIR/templates/componenti/"
echo -e "${GREEN}  OK${NC} - templates/componenti/_topbar.html (v2 con polling)"

# Fase 3: Pagina gestione + satellite
mkdir -p "$BASE_DIR/templates/ticker"

cp "$SCARICATI/gestione.html"    "$BASE_DIR/templates/ticker/"
echo -e "${GREEN}  OK${NC} - templates/ticker/gestione.html"

cp "$SCARICATI/_styles.html"     "$BASE_DIR/templates/ticker/"
echo -e "${GREEN}  OK${NC} - templates/ticker/_styles.html"

cp "$SCARICATI/_preview.html"    "$BASE_DIR/templates/ticker/"
echo -e "${GREEN}  OK${NC} - templates/ticker/_preview.html"

cp "$SCARICATI/_griglia.html"    "$BASE_DIR/templates/ticker/"
echo -e "${GREEN}  OK${NC} - templates/ticker/_griglia.html"

cp "$SCARICATI/_modal_nuovo.html" "$BASE_DIR/templates/ticker/"
echo -e "${GREEN}  OK${NC} - templates/ticker/_modal_nuovo.html"

cp "$SCARICATI/_scripts.html"    "$BASE_DIR/templates/ticker/"
echo -e "${GREEN}  OK${NC} - templates/ticker/_scripts.html"

# ==============================================================================
# 3. VERIFICA STRUTTURA
# ==============================================================================
echo ""
echo -e "${YELLOW}[3/4]${NC} Verifica struttura..."

# Widget
[ -f "$BASE_DIR/templates/componenti/_topbar.html" ] && \
    echo -e "${GREEN}  OK${NC} - Widget topbar v2" || \
    echo -e "${RED}  ERRORE${NC} - Widget topbar mancante!"

# Satellite files
for f in gestione.html _styles.html _preview.html _griglia.html _modal_nuovo.html _scripts.html; do
    if [ -f "$BASE_DIR/templates/ticker/$f" ]; then
        echo -e "${GREEN}  OK${NC} - ticker/$f"
    else
        echo -e "${RED}  ERRORE${NC} - ticker/$f mancante!"
    fi
done

# ==============================================================================
# 4. ENCODING CHECK
# ==============================================================================
echo ""
echo -e "${YELLOW}[4/4]${NC} Verifica encoding..."

ENCODING_OK=1
for f in "$BASE_DIR/templates/componenti/_topbar.html" "$BASE_DIR/templates/ticker/"*.html; do
    BASENAME=$(basename "$f")
    # Cerca caratteri UTF-8 corrotti
    if grep -P '[\xc3\xc2][\x80-\xbf]' "$f" > /dev/null 2>&1; then
        echo -e "${YELLOW}  WARN${NC} - $BASENAME potrebbe avere encoding corrotto"
        ENCODING_OK=0
    fi
done

if [ "$ENCODING_OK" = "1" ]; then
    echo -e "${GREEN}  OK${NC} - Encoding pulito (entity HTML)"
fi

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${GREEN}  DEPLOY FASE 2+3 COMPLETATO                               ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""
echo "Riavvia il server:"
echo "  ~/gestione_flotta/scripts/gestione_flotta.sh restart"
echo ""
echo "Poi testa:"
echo "  - Pagina gestione: http://localhost:5001/ticker/gestione"
echo "  - Crea un messaggio di test e guarda la preview"
echo "  - Il ticker in alto iniziera' il polling dopo 10-60 sec"
echo ""
