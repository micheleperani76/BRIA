#!/bin/bash
# ==============================================================================
# PATCH: routes_sedi_cliente.py
# - Aggiunta tipo "Indirizzo Fatturazione"
# - Lettura campo protetto dal payload nel PUT
# Data: 2026-02-11
# ==============================================================================

FILE=~/gestione_flotta/app/routes_sedi_cliente.py

echo "=== PATCH routes_sedi_cliente.py ==="

# 1. Aggiungere "Indirizzo Fatturazione" dopo "Punto Vendita"
sed -i "s/    'Punto Vendita',/    'Punto Vendita',\n    'Indirizzo Fatturazione',/" "$FILE"
echo "[1/4] Aggiunto tipo sede 'Indirizzo Fatturazione'"

# 2. Aggiungere lettura campo protetto nel PUT (dopo la riga referente_id = int)
sed -i '/^        referente_id = int(referente_id)$/a\    \n    protetto = 1 if data.get('\''protetto'\'') else 0' "$FILE"
echo "[2/4] Aggiunta lettura protetto dal payload"

# 3. Aggiungere protetto nell'UPDATE SET (dopo referente_id = ?)
sed -i 's/                referente_id = ?$/                referente_id = ?,\n                protetto = ?/' "$FILE"
echo "[3/4] Aggiunto protetto nel SET dell'UPDATE"

# 4. Aggiungere protetto nei parametri (dopo referente_id,)
sed -i 's/              telefono or None, email or None, note or None, referente_id,$/              telefono or None, email or None, note or None, referente_id, protetto,/' "$FILE"
echo "[4/4] Aggiunto protetto nei parametri UPDATE"

# Verifiche
echo ""
echo "--- Verifica TIPI_SEDE ---"
grep -n "Fatturazione\|Punto Vendita\|Altro" "$FILE"
echo ""
echo "--- Verifica protetto nel PUT ---"
grep -n "protetto" "$FILE"
echo ""
echo "=== PATCH COMPLETATA ==="
