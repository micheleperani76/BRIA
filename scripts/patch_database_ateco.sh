#!/bin/bash
# ==============================================================================
# PATCH - Aggiunta campi ATECO a database.py
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-10
# Descrizione: Aggiunge codice_sae, codice_rae, codice_ateco_2007, desc_ateco_2007
#              alla lista campi_aggiornabili in aggiorna_cliente_da_creditsafe()
#
# Uso: bash scripts/patch_database_ateco.sh
# ==============================================================================

set -e
cd ~/gestione_flotta

TARGET="app/database.py"

echo "=================================================="
echo "  PATCH - Campi ATECO in database.py"
echo "=================================================="
echo ""

# ==============================================================================
# 1. BACKUP
# ==============================================================================
echo "[1/3] Backup..."
cp "$TARGET" "${TARGET}.bak.ateco"
echo "  OK -> ${TARGET}.bak.ateco"

# ==============================================================================
# 2. VERIFICA PRE-PATCH
# ==============================================================================
echo ""
echo "[2/3] Verifica..."

# Controlla che la riga da modificare esista
if ! grep -q "'desc_ateco'," "$TARGET"; then
    echo "  ERRORE: Pattern 'desc_ateco,' non trovato in $TARGET"
    echo "  Patch non applicabile. Verificare manualmente."
    exit 1
fi

# Controlla che non sia gia patchato
if grep -q "'codice_sae'" "$TARGET"; then
    echo "  SKIP - Patch gia applicata (codice_sae gia presente)"
    exit 0
fi
echo "  OK - Pattern trovato, patch applicabile"

# ==============================================================================
# 3. APPLICA PATCH
# ==============================================================================
echo ""
echo "[3/3] Applica patch..."

# Aggiunge i 4 nuovi campi dopo 'desc_ateco' nella lista campi_aggiornabili
# Riga originale:  'desc_attivita', 'codice_ateco', 'desc_ateco',
# Riga modificata: 'desc_attivita', 'codice_ateco', 'desc_ateco',
#                   'codice_sae', 'codice_rae', 'codice_ateco_2007', 'desc_ateco_2007',
sed -i "s/'desc_ateco',/'desc_ateco',\n        'codice_sae', 'codice_rae', 'codice_ateco_2007', 'desc_ateco_2007',/" "$TARGET"

# Verifica
if grep -q "'codice_sae'" "$TARGET"; then
    echo "  OK - 4 nuovi campi aggiunti a campi_aggiornabili"
else
    echo "  ERRORE - Patch non applicata correttamente!"
    echo "  Ripristino backup..."
    cp "${TARGET}.bak.ateco" "$TARGET"
    exit 1
fi

echo ""
echo "=================================================="
echo "  PATCH COMPLETATA"
echo "=================================================="
echo ""
echo "  Campi aggiunti: codice_sae, codice_rae,"
echo "                  codice_ateco_2007, desc_ateco_2007"
echo ""
echo "  Backup in: ${TARGET}.bak.ateco"
echo "=================================================="
