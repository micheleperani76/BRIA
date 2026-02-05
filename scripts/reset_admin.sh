#!/bin/bash
# ==============================================================================
# RESET PASSWORD ADMIN - Emergenza
# ==============================================================================
# Versione: 1.1.0
# Data: 2025-01-20
#
# Questo script resetta la password dell'utente ADMIN di sistema.
# Da usare SOLO in caso di emergenza (password persa).
#
# USO:
#   ./scripts/reset_admin.sh
#
# ==============================================================================

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Percorsi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DB_FILE="$BASE_DIR/db/gestionale.db"

clear
echo ""
echo "============================================================"
echo "  RESET PASSWORD ADMIN - Emergenza"
echo "============================================================"
echo ""
echo -e "  ${YELLOW}⚠️  ATTENZIONE: Questo script resetta la password${NC}"
echo "      dell'utente ADMIN di sistema."
echo ""
echo "  Usare SOLO se la password è stata persa!"
echo ""

# Verifica che il database esista
if [ ! -f "$DB_FILE" ]; then
    echo -e "  ${RED}❌ Errore: Database non trovato!${NC}"
    echo "     Percorso: $DB_FILE"
    echo ""
    exit 1
fi

# Verifica che l'utente admin esista
ADMIN_ESISTE=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM utenti WHERE username = 'admin';")
if [ "$ADMIN_ESISTE" -eq 0 ]; then
    echo -e "  ${RED}❌ Errore: utente admin non trovato nel database!${NC}"
    echo ""
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Utente admin trovato nel database"
echo ""

# Conferma
echo -n "  Sei sicuro? Scrivi 'RESET' per confermare: "
read -r CONFERMA

if [ "$CONFERMA" != "RESET" ]; then
    echo ""
    echo "  Operazione annullata."
    echo ""
    exit 0
fi

echo ""
echo "------------------------------------------------------------"
echo ""

# Genera password temporanea (12 caratteri alfanumerici)
NUOVA_PWD=$(cat /dev/urandom | tr -dc 'a-zA-Z2-9' | head -c 12)

# Genera hash con Python (werkzeug)
PWD_HASH=$(python3 -c "
from werkzeug.security import generate_password_hash
print(generate_password_hash('$NUOVA_PWD'))
")

if [ -z "$PWD_HASH" ]; then
    echo -e "  ${RED}❌ Errore: impossibile generare hash password${NC}"
    echo ""
    exit 1
fi

# Aggiorna database
sqlite3 "$DB_FILE" "UPDATE utenti SET password_hash = '$PWD_HASH', pwd_temporanea = 1, tentativi_falliti = 0, bloccato = 0 WHERE username = 'admin';"

# Verifica che la password sia stata aggiornata
VERIFICA=$(sqlite3 "$DB_FILE" "SELECT password_hash FROM utenti WHERE username = 'admin';")

if [ "$VERIFICA" == "$PWD_HASH" ]; then
    # Log operazione
    DATA_ORA=$(date '+%Y-%m-%d %H:%M:%S')
    sqlite3 "$DB_FILE" "INSERT INTO log_accessi (username_tentativo, azione, dettaglio, data_ora) VALUES ('admin', 'reset_pwd_emergenza', 'Reset via script bash', '$DATA_ORA');"
    
    echo -e "  ${GREEN}✅ PASSWORD RESETTATA CON SUCCESSO${NC}"
    echo ""
    echo "  ========================================================"
    echo -e "  Username:                  ${GREEN}admin${NC}"
    echo -e "  Nuova password temporanea: ${GREEN}$NUOVA_PWD${NC}"
    echo "  ========================================================"
    echo ""
    echo -e "  ${YELLOW}⚠️  Cambiare la password al primo accesso!${NC}"
    echo ""
else
    echo -e "  ${RED}❌ Errore durante l'aggiornamento della password!${NC}"
    echo ""
    exit 1
fi
