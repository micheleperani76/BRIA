#!/bin/bash
# ==============================================================================
# DEPLOY FASE 4 - MESSAGGI AUTOMATICI TICKER
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-06
#
# File deployati:
#   scripts/migrazione_ticker_fase4.py   -> Migrazione DB
#   app/ticker_auto_gen.py               -> Generatore automatico
#
# Operazioni:
#   1. Deploy file
#   2. Esegui migrazione (tabella festivita + config)
#   3. Patch config modal (toggle deposito bilancio)
#   4. Configura cron giornaliero
#   5. Test esecuzione
# ==============================================================================

BASE_DIR="$HOME/gestione_flotta"
SCARICATI="$BASE_DIR/Scaricati"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}  DEPLOY FASE 4 - MESSAGGI AUTOMATICI TICKER               ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""

# ==============================================================================
# 0. VERIFICA FILE
# ==============================================================================
echo -e "${YELLOW}[0/5]${NC} Verifica file..."

ERRORI=0
for f in migrazione_ticker_fase4.py ticker_auto_gen.py; do
    if [ ! -f "$SCARICATI/$f" ]; then
        echo -e "${RED}  MANCA: $f${NC}"
        ERRORI=1
    fi
done

if [ "$ERRORI" = "1" ]; then
    echo "Metti i file in ~/gestione_flotta/Scaricati/"
    exit 1
fi
echo -e "${GREEN}  OK${NC} - File presenti"

# ==============================================================================
# 1. DEPLOY FILE
# ==============================================================================
echo ""
echo -e "${YELLOW}[1/5]${NC} Deploy file..."

cp "$SCARICATI/migrazione_ticker_fase4.py" "$BASE_DIR/scripts/"
echo -e "${GREEN}  OK${NC} - scripts/migrazione_ticker_fase4.py"

cp "$SCARICATI/ticker_auto_gen.py" "$BASE_DIR/app/"
echo -e "${GREEN}  OK${NC} - app/ticker_auto_gen.py"

# ==============================================================================
# 2. MIGRAZIONE DB
# ==============================================================================
echo ""
echo -e "${YELLOW}[2/5]${NC} Esecuzione migrazione..."
echo ""

cd "$BASE_DIR"
python3 scripts/migrazione_ticker_fase4.py

# ==============================================================================
# 3. PATCH CONFIG MODAL - Aggiungi toggle deposito bilancio
# ==============================================================================
echo ""
echo -e "${YELLOW}[3/5]${NC} Patch config modal..."

GESTIONE="$BASE_DIR/templates/ticker/gestione.html"

# Controlla se il toggle deposito_bilancio esiste gia
if grep -q "cfg-auto-deposito" "$GESTIONE" 2>/dev/null; then
    echo -e "${GREEN}  SKIP${NC} - Toggle deposito bilancio gia presente"
else
    # Aggiungi toggle dopo quello delle gomme
    sed -i '/<label class="form-check-label" for="cfg-auto-gomme">Cambio gomme<\/label>/a\
                </div>\
                <div class="form-check form-switch mb-2">\
                    <input class="form-check-input" type="checkbox" id="cfg-auto-deposito" checked>\
                    <label class="form-check-label" for="cfg-auto-deposito">Deposito bilancio CCIAA</label>' "$GESTIONE"
    
    echo -e "${GREEN}  OK${NC} - Toggle deposito bilancio aggiunto nel modal config"
fi

# ==============================================================================
# 3b. PATCH SCRIPTS - Aggiungi lettura/salvataggio config deposito
# ==============================================================================
echo ""
echo -e "${YELLOW}[3b/5]${NC} Patch scripts ticker..."

SCRIPTS="$BASE_DIR/templates/ticker/_scripts.html"

# Aggiungi lettura config deposito bilancio nella funzione apriConfig
if grep -q "cfg-auto-deposito" "$SCRIPTS" 2>/dev/null; then
    echo -e "${GREEN}  SKIP${NC} - Script gia patchato"
else
    # Aggiungi setChk per deposito dopo la riga di auto_gomme
    sed -i "/setChk('cfg-auto-gomme', c.auto_gomme);/a\\
                setChk('cfg-auto-deposito', c.auto_deposito_bilancio);" "$SCRIPTS"
    
    # Aggiungi salvataggio deposito nella funzione salvaConfig
    sed -i "/auto_gomme: document.getElementById('cfg-auto-gomme').checked ? '1' : '0'/a\\
            ,auto_deposito_bilancio: document.getElementById('cfg-auto-deposito').checked ? '1' : '0'" "$SCRIPTS"
    
    echo -e "${GREEN}  OK${NC} - Script aggiornato per deposito bilancio"
fi

# ==============================================================================
# 4. CONFIGURA CRON
# ==============================================================================
echo ""
echo -e "${YELLOW}[4/5]${NC} Configurazione cron..."

CRON_CMD="5 0 * * * cd $BASE_DIR && python3 app/ticker_auto_gen.py >> logs/ticker_auto_gen.log 2>&1"

# Controlla se gia presente
if crontab -l 2>/dev/null | grep -q "ticker_auto_gen.py"; then
    echo -e "${GREEN}  SKIP${NC} - Cron gia configurato"
else
    # Aggiungi al crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo -e "${GREEN}  OK${NC} - Cron aggiunto (ogni giorno alle 00:05)"
fi

echo "  Cron attuale:"
crontab -l 2>/dev/null | grep ticker_auto_gen || echo "  (nessuno)"

# ==============================================================================
# 5. TEST ESECUZIONE
# ==============================================================================
echo ""
echo -e "${YELLOW}[5/5]${NC} Test esecuzione generatore..."
echo ""

cd "$BASE_DIR"
python3 app/ticker_auto_gen.py

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${GREEN}  DEPLOY FASE 4 COMPLETATO                                 ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""
echo "Riavvia il server per le modifiche al modal:"
echo "  ~/gestione_flotta/scripts/gestione_flotta.sh restart"
echo ""
echo "Il cron generera messaggi automatici ogni giorno alle 00:05."
echo "Per test manuale: python3 app/ticker_auto_gen.py"
echo ""
