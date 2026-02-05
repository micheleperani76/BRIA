#!/bin/bash
# ==============================================================================
# GESTIONE FLOTTA - Script Avvio Server per Crontab
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-12
# Descrizione: Avvia il server web (per @reboot in crontab)
#
# Installazione crontab:
#   crontab -e
#   @reboot /home/michele/gestione_flotta/scripts/avvia_server.sh
# ==============================================================================

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Attendi che il sistema sia pronto
sleep 10

# Avvia server
"$SCRIPT_DIR/gestione_flotta.sh" start
