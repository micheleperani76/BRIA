#!/bin/bash
# ==============================================================================
# STOCK ENGINE - Script Avvio Server per Crontab
# ==============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
# Descrizione: Avvia il server web (per @reboot in crontab)
#
# Installazione crontab:
#   crontab -e
#   @reboot /home/michele/stock-engine/scripts/avvia_server.sh
# ==============================================================================

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Log avvio
LOG_FILE="$BASE_DIR/logs/startup.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Avvio Stock Engine..." >> "$LOG_FILE"

# Attendi che il sistema sia pronto
sleep 15

# Avvia server
"$SCRIPT_DIR/stock_engine.sh" start >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - Avvio completato" >> "$LOG_FILE"
