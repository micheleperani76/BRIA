#!/bin/bash
# ==============================================================================
# PATCH - Registrazione Blueprint Trascrizione
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-03
# Descrizione: Aggiunge il blueprint trascrizione_bp a web_server.py
#              e il codice_utente alla sessione in auth.py
#
# Uso: bash scripts/patch_trascrizione.sh
# ==============================================================================

set -e

cd ~/gestione_flotta

echo "=================================================="
echo "  PATCH - Blueprint Trascrizione"
echo "=================================================="
echo ""

# ==============================================================================
# 1. BACKUP
# ==============================================================================
echo "[1/4] Backup file..."
cp app/web_server.py app/web_server.py.bak.trascrizione
cp app/auth.py app/auth.py.bak.trascrizione
echo "  OK"

# ==============================================================================
# 2. PATCH web_server.py - Aggiunge import e registrazione blueprint
# ==============================================================================
echo ""
echo "[2/4] Patch web_server.py..."

# Verifica che non sia gia stato applicato
if grep -q "trascrizione_bp" app/web_server.py; then
    echo "  SKIP - Blueprint trascrizione gia registrato"
else
    # Aggiungi import dopo l'ultima riga di import blueprint
    sed -i '/from app.routes_top_prospect import/a from app.routes_trascrizione import trascrizione_bp' app/web_server.py
    
    # Aggiungi registrazione dopo l'ultimo register_blueprint
    sed -i '/app.register_blueprint(top_prospect_bp)/a app.register_blueprint(trascrizione_bp)' app/web_server.py
    
    # Aggiungi MAX_CONTENT_LENGTH per upload grandi
    # Cerca se esiste gia
    if ! grep -q "MAX_CONTENT_LENGTH" app/web_server.py; then
        sed -i "/app.secret_key/a\\
# Limite upload (500 MB per trascrizione audio)\\
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024" app/web_server.py
    fi
    
    echo "  OK - Import e registrazione aggiunti"
fi

# ==============================================================================
# 3. PATCH auth.py - Aggiunge codice_utente alla sessione
# ==============================================================================
echo ""
echo "[3/4] Patch auth.py..."

if grep -q "codice_utente" app/auth.py; then
    echo "  SKIP - codice_utente gia presente in sessione"
else
    # Aggiungi codice_utente nella funzione imposta_sessione
    # Cerca la riga session['username'] e aggiungi dopo
    sed -i "/session\['username'\] = utente\['username'\]/a\\
    session['codice_utente'] = utente.get('codice_utente', '000000')" app/auth.py
    
    echo "  OK - codice_utente aggiunto alla sessione"
fi

# ==============================================================================
# 4. VERIFICA
# ==============================================================================
echo ""
echo "[4/4] Verifica..."

# Verifica import
if grep -q "from app.routes_trascrizione import trascrizione_bp" app/web_server.py; then
    echo "  OK - Import presente"
else
    echo "  ERRORE - Import mancante!"
fi

# Verifica registrazione
if grep -q "app.register_blueprint(trascrizione_bp)" app/web_server.py; then
    echo "  OK - Blueprint registrato"
else
    echo "  ERRORE - Blueprint non registrato!"
fi

# Verifica codice_utente
if grep -q "codice_utente" app/auth.py; then
    echo "  OK - codice_utente in sessione"
else
    echo "  ERRORE - codice_utente mancante!"
fi

# Verifica sintassi Python
echo ""
echo "Verifica sintassi Python..."
python3 -c "import ast; ast.parse(open('app/web_server.py').read()); print('  OK - web_server.py')"
python3 -c "import ast; ast.parse(open('app/auth.py').read()); print('  OK - auth.py')"

echo ""
echo "=================================================="
echo "  PATCH COMPLETATA"
echo "=================================================="
echo ""
echo "Prossimi passi:"
echo "  1. Riavvia il server Flask"
echo "  2. Effettua logout/login per aggiornare sessione"
echo "  3. Testa: curl http://localhost:5001/trascrizione/coda"
