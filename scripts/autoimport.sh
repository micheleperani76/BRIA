#!/bin/bash
# ==============================================================================
# GESTIONE FLOTTA - Script Autoimport per Crontab
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-12
# Descrizione: Importa automaticamente i PDF dalla cartella pdf/
#
# Installazione crontab:
#   crontab -e
#   # Import PDF ogni ora (minuto 5)
#   5 * * * * /home/michele/gestione_flotta/scripts/autoimport.sh
# ==============================================================================

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="python3"
LOG_FILE="$BASE_DIR/logs/autoimport.log"

# Crea directory log se non esiste
mkdir -p "$BASE_DIR/logs"

# Timestamp
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"

# Conta PDF da elaborare
PDF_COUNT=$(ls -1 "$BASE_DIR/pdf/"*.pdf 2>/dev/null | wc -l)

if [ "$PDF_COUNT" -gt 0 ]; then
    echo "Trovati $PDF_COUNT PDF da elaborare" >> "$LOG_FILE"
    
    # Esegui import
    cd "$BASE_DIR"
    $PYTHON main.py import >> "$LOG_FILE" 2>&1
    
    echo "Import completato" >> "$LOG_FILE"
else
    echo "Nessun PDF da elaborare" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
