#!/bin/bash
# ==============================================================================
# GESTIONE FLOTTA - Script Principale
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-12
# Descrizione: Script bash per gestione del sistema
# ==============================================================================

# Configurazione
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="python3"
PID_FILE="$BASE_DIR/logs/server.pid"
LOG_FILE="$BASE_DIR/logs/server.log"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni utilità
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  GESTIONE FLOTTA - $1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

# Funzione: mostra stato
show_status() {
    print_header "Stato Sistema"
    
    echo ""
    echo "Directory: $BASE_DIR"
    echo ""
    
    # Verifica server
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            print_ok "Server in esecuzione (PID: $PID)"
        else
            print_warning "Server non in esecuzione (PID file presente)"
        fi
    else
        print_warning "Server non avviato"
    fi
    
    # Conta file
    PDF_COUNT=$(ls -1 "$BASE_DIR/pdf/"*.pdf 2>/dev/null | wc -l)
    STORICO_COUNT=$(find "$BASE_DIR/storico_pdf" -name "*.pdf" 2>/dev/null | wc -l)
    
    echo ""
    echo "PDF da elaborare: $PDF_COUNT"
    echo "PDF in storico:   $STORICO_COUNT"
    
    # Dimensione DB
    if [ -f "$BASE_DIR/db/gestionale.db" ]; then
        DB_SIZE=$(du -h "$BASE_DIR/db/gestionale.db" | cut -f1)
        echo "Dimensione DB:    $DB_SIZE"
    fi
}

# Funzione: avvia server
start_server() {
    print_header "Avvio Server"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "Server già in esecuzione (PID: $PID)"
            return 1
        fi
    fi
    
    # Crea directory log se non esiste
    mkdir -p "$BASE_DIR/logs"
    
    # Avvia server in background
    cd "$BASE_DIR"
    nohup $PYTHON main.py server >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    sleep 2
    
    if ps -p $PID > /dev/null 2>&1; then
        print_ok "Server avviato (PID: $PID)"
        echo "Log: $LOG_FILE"
        echo "URL: http://localhost:5001"
    else
        print_error "Errore avvio server"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Funzione: ferma server
stop_server() {
    print_header "Arresto Server"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            sleep 2
            if ps -p $PID > /dev/null 2>&1; then
                kill -9 $PID
            fi
            print_ok "Server fermato (PID: $PID)"
        else
            print_warning "Server non in esecuzione"
        fi
        rm -f "$PID_FILE"
    else
        print_warning "Nessun server avviato"
    fi
}

# Funzione: riavvia server
restart_server() {
    stop_server
    sleep 1
    start_server
}

# Funzione: import PDF
import_pdf() {
    print_header "Import PDF Creditsafe"
    
    cd "$BASE_DIR"
    $PYTHON main.py import
}

# Funzione: inizializza DB
init_db() {
    print_header "Inizializzazione Database"
    
    cd "$BASE_DIR"
    $PYTHON main.py init
}

# Funzione: pulizia log
clean_logs() {
    print_header "Pulizia Log"
    
    cd "$BASE_DIR"
    $PYTHON main.py pulisci
}

# Funzione: mostra log
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        print_error "File log non trovato: $LOG_FILE"
    fi
}

# Menu interattivo
show_menu() {
    print_header "Menu Principale"
    
    echo ""
    echo "1) Avvia server"
    echo "2) Ferma server"
    echo "3) Riavvia server"
    echo "4) Stato sistema"
    echo "5) Import PDF"
    echo "6) Pulizia log"
    echo "7) Visualizza log"
    echo "8) Inizializza DB"
    echo ""
    echo "0) Esci"
    echo ""
    
    read -p "Scelta: " choice
    
    case $choice in
        1) start_server ;;
        2) stop_server ;;
        3) restart_server ;;
        4) show_status ;;
        5) import_pdf ;;
        6) clean_logs ;;
        7) show_logs ;;
        8) init_db ;;
        0) exit 0 ;;
        *) print_error "Scelta non valida" ;;
    esac
    
    echo ""
    read -p "Premi INVIO per continuare..."
    show_menu
}

# Main
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    import)
        import_pdf
        ;;
    clean)
        clean_logs
        ;;
    logs)
        show_logs
        ;;
    init)
        init_db
        ;;
    menu|"")
        show_menu
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|import|clean|logs|init|menu}"
        echo ""
        echo "Comandi:"
        echo "  start   - Avvia il server web"
        echo "  stop    - Ferma il server"
        echo "  restart - Riavvia il server"
        echo "  status  - Mostra stato sistema"
        echo "  import  - Importa PDF Creditsafe"
        echo "  clean   - Pulisce log vecchi"
        echo "  logs    - Visualizza log in tempo reale"
        echo "  init    - Inizializza database"
        echo "  menu    - Menu interattivo"
        exit 1
        ;;
esac
