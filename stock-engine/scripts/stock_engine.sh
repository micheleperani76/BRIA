#!/bin/bash
# ==============================================================================
# STOCK ENGINE - Script Gestione Server
# ==============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
# Autore: Michele + Claude
#
# Uso:
#   ./stock_engine.sh start      # Avvia server
#   ./stock_engine.sh stop       # Ferma server
#   ./stock_engine.sh restart    # Riavvia server
#   ./stock_engine.sh status     # Stato server
#   ./stock_engine.sh logs       # Mostra log
#   ./stock_engine.sh elabora    # Lancia elaborazione manuale
#   ./stock_engine.sh init       # Prima installazione
# ==============================================================================

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Directory progetto
APP_DIR="$BASE_DIR"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
PID_FILE="$APP_DIR/stock_engine.pid"
SCHEDULER_PID_FILE="$APP_DIR/scheduler.pid"

# Configurazione server
HOST="0.0.0.0"
PORT="5000"

# Log files
APP_LOG="$LOG_DIR/app.log"
SCHEDULER_LOG="$LOG_DIR/scheduler.log"
ERROR_LOG="$LOG_DIR/error.log"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================================================
# FUNZIONI UTILITY
# ==============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

check_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        log_error "Virtual environment non trovato: $VENV_DIR"
        log_info "Esegui: $0 init"
        exit 1
    fi
}

activate_venv() {
    source "$VENV_DIR/bin/activate"
}

is_running() {
    local pid_file="$1"
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

get_pid() {
    local pid_file="$1"
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file"
    fi
}

# ==============================================================================
# FUNZIONE: INIT (Prima installazione)
# ==============================================================================
do_init() {
    log_header "INIZIALIZZAZIONE STOCK ENGINE"
    
    cd "$APP_DIR"
    
    # Crea directory necessarie
    log_info "Creazione directory..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$APP_DIR/output/stock"
    mkdir -p "$APP_DIR/instance"
    
    # Crea virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "Creazione virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Attiva venv e installa dipendenze
    activate_venv
    
    log_info "Installazione dipendenze Python..."
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
    
    # Crea file .env se non esiste
    if [[ ! -f "$APP_DIR/.env" ]]; then
        log_info "Creazione file .env..."
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        log_warn "Modifica $APP_DIR/.env con i tuoi percorsi!"
    fi
    
    # Inizializza database
    log_info "Inizializzazione database..."
    cd "$APP_DIR"
    export FLASK_APP=run.py
    flask init-db
    
    log_info "Importazione database JATO..."
    flask import-jato || log_warn "Importazione JATO fallita (file non trovato?)"
    
    log_info "Importazione configurazioni..."
    flask import-config || log_warn "Importazione config fallita (file non trovati?)"
    
    log_header "INIZIALIZZAZIONE COMPLETATA"
    log_info "Modifica $APP_DIR/.env con i tuoi percorsi"
    log_info "Poi esegui: $0 start"
}

# ==============================================================================
# FUNZIONE: START
# ==============================================================================
do_start() {
    log_header "AVVIO STOCK ENGINE"
    
    check_venv
    cd "$APP_DIR"
    
    # Carica variabili ambiente
    if [[ -f "$APP_DIR/.env" ]]; then
        export $(grep -v '^#' "$APP_DIR/.env" | xargs)
    fi
    
    # Controlla se già in esecuzione
    if is_running "$PID_FILE"; then
        log_warn "Server già in esecuzione (PID: $(get_pid $PID_FILE))"
        return 1
    fi
    
    activate_venv
    
    # Avvia server Flask/Gunicorn
    log_info "Avvio server web su $HOST:$PORT..."
    
    export FLASK_APP=run.py
    export FLASK_ENV=production
    
    nohup gunicorn \
        --bind "$HOST:$PORT" \
        --workers 2 \
        --timeout 120 \
        --access-logfile "$APP_LOG" \
        --error-logfile "$ERROR_LOG" \
        --capture-output \
        --pid "$PID_FILE" \
        'app:create_app()' \
        >> "$APP_LOG" 2>&1 &
    
    sleep 2
    
    if is_running "$PID_FILE"; then
        log_info "Server avviato (PID: $(get_pid $PID_FILE))"
        log_info "URL: http://localhost:$PORT"
        log_info "API: http://localhost:$PORT/api"
    else
        log_error "Avvio server fallito! Controlla $ERROR_LOG"
        return 1
    fi
    
    # Avvia scheduler
    log_info "Avvio scheduler..."
    
    nohup python scheduler/run_scheduler.py \
        >> "$SCHEDULER_LOG" 2>&1 &
    echo $! > "$SCHEDULER_PID_FILE"
    
    sleep 1
    
    if is_running "$SCHEDULER_PID_FILE"; then
        log_info "Scheduler avviato (PID: $(get_pid $SCHEDULER_PID_FILE))"
    else
        log_warn "Avvio scheduler fallito! Controlla $SCHEDULER_LOG"
    fi
    
    log_header "STOCK ENGINE AVVIATO"
}

# ==============================================================================
# FUNZIONE: STOP
# ==============================================================================
do_stop() {
    log_header "ARRESTO STOCK ENGINE"
    
    # Ferma server
    if is_running "$PID_FILE"; then
        local pid=$(get_pid "$PID_FILE")
        log_info "Arresto server (PID: $pid)..."
        kill "$pid" 2>/dev/null
        sleep 2
        
        # Force kill se necessario
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "Force kill server..."
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        log_info "Server arrestato"
    else
        log_info "Server non in esecuzione"
    fi
    
    # Ferma scheduler
    if is_running "$SCHEDULER_PID_FILE"; then
        local pid=$(get_pid "$SCHEDULER_PID_FILE")
        log_info "Arresto scheduler (PID: $pid)..."
        kill "$pid" 2>/dev/null
        rm -f "$SCHEDULER_PID_FILE"
        log_info "Scheduler arrestato"
    else
        log_info "Scheduler non in esecuzione"
    fi
    
    log_header "STOCK ENGINE ARRESTATO"
}

# ==============================================================================
# FUNZIONE: RESTART
# ==============================================================================
do_restart() {
    do_stop
    sleep 2
    do_start
}

# ==============================================================================
# FUNZIONE: STATUS
# ==============================================================================
do_status() {
    log_header "STATO STOCK ENGINE"
    
    echo ""
    
    # Server
    if is_running "$PID_FILE"; then
        echo -e "Server:    ${GREEN}● ATTIVO${NC} (PID: $(get_pid $PID_FILE))"
        echo -e "           URL: http://localhost:$PORT"
    else
        echo -e "Server:    ${RED}○ FERMO${NC}"
    fi
    
    # Scheduler
    if is_running "$SCHEDULER_PID_FILE"; then
        echo -e "Scheduler: ${GREEN}● ATTIVO${NC} (PID: $(get_pid $SCHEDULER_PID_FILE))"
    else
        echo -e "Scheduler: ${RED}○ FERMO${NC}"
    fi
    
    echo ""
    
    # Health check
    if is_running "$PID_FILE"; then
        echo "Health check API:"
        curl -s "http://localhost:$PORT/api/health" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  (non raggiungibile)"
    fi
    
    echo ""
}

# ==============================================================================
# FUNZIONE: LOGS
# ==============================================================================
do_logs() {
    local log_type="${1:-app}"
    
    case "$log_type" in
        app)
            log_info "Log applicazione ($APP_LOG):"
            tail -50 "$APP_LOG" 2>/dev/null || echo "Log non disponibile"
            ;;
        scheduler)
            log_info "Log scheduler ($SCHEDULER_LOG):"
            tail -50 "$SCHEDULER_LOG" 2>/dev/null || echo "Log non disponibile"
            ;;
        error)
            log_info "Log errori ($ERROR_LOG):"
            tail -50 "$ERROR_LOG" 2>/dev/null || echo "Log non disponibile"
            ;;
        follow)
            log_info "Log in tempo reale (Ctrl+C per uscire):"
            tail -f "$APP_LOG" "$SCHEDULER_LOG" 2>/dev/null
            ;;
        *)
            log_error "Tipo log non valido: $log_type"
            echo "Uso: $0 logs [app|scheduler|error|follow]"
            ;;
    esac
}

# ==============================================================================
# FUNZIONE: ELABORA (manuale)
# ==============================================================================
do_elabora() {
    local noleggiatore="${1:-}"
    
    check_venv
    cd "$APP_DIR"
    
    if [[ -f "$APP_DIR/.env" ]]; then
        export $(grep -v '^#' "$APP_DIR/.env" | xargs)
    fi
    
    activate_venv
    export FLASK_APP=run.py
    
    if [[ -z "$noleggiatore" ]]; then
        log_header "ELABORAZIONE TUTTI I NOLEGGIATORI"
        flask elabora AYVENS
        flask elabora ARVAL
        flask elabora LEASYS
    else
        log_header "ELABORAZIONE $noleggiatore"
        flask elabora "$noleggiatore"
    fi
}

# ==============================================================================
# FUNZIONE: HELP
# ==============================================================================
do_help() {
    echo ""
    echo "STOCK ENGINE - Gestione Server"
    echo ""
    echo "Uso: $0 <comando> [opzioni]"
    echo ""
    echo "Comandi:"
    echo "  init              Prima installazione (crea venv, DB, etc.)"
    echo "  start             Avvia server e scheduler"
    echo "  stop              Ferma server e scheduler"
    echo "  restart           Riavvia tutto"
    echo "  status            Mostra stato servizi"
    echo "  logs [tipo]       Mostra log (app|scheduler|error|follow)"
    echo "  elabora [noleg]   Lancia elaborazione (AYVENS|ARVAL|LEASYS|tutti)"
    echo "  help              Mostra questo messaggio"
    echo ""
    echo "Esempi:"
    echo "  $0 init                    # Prima installazione"
    echo "  $0 start                   # Avvia tutto"
    echo "  $0 elabora AYVENS          # Elabora solo AYVENS"
    echo "  $0 logs follow             # Log in tempo reale"
    echo ""
}

# ==============================================================================
# MAIN
# ==============================================================================
case "${1:-}" in
    init)
        do_init
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    status)
        do_status
        ;;
    logs)
        do_logs "$2"
        ;;
    elabora)
        do_elabora "$2"
        ;;
    help|--help|-h)
        do_help
        ;;
    *)
        if [[ -n "$1" ]]; then
            log_error "Comando sconosciuto: $1"
        fi
        do_help
        exit 1
        ;;
esac
