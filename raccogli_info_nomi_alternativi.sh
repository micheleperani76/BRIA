#!/bin/bash
# ==============================================================================
# RACCOLTA INFO - Nomi Alternativi / Keyword Ricerca
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-12
# Scopo: Raccoglie tutte le info necessarie a Claude per completare le patch
# Uso: bash raccogli_info_nomi_alternativi.sh
# Output: ~/gestione_flotta/info_nomi_alternativi.md
# ==============================================================================

BASE=~/gestione_flotta
OUT="$BASE/info_nomi_alternativi.md"

echo "Raccolta info in corso..."
echo ""

cat > "$OUT" << 'HEADER'
# Info Raccolta - Nomi Alternativi
## Generato da raccogli_info_nomi_alternativi.sh
HEADER

echo "Data: $(date '+%Y-%m-%d %H:%M:%S')" >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 1. STRUTTURA _riquadro.html dati_aziendali (wrapper include)
# ==============================================================================
echo "---" >> "$OUT"
echo "## 1. File _riquadro.html dati_aziendali (se esiste)" >> "$OUT"
echo '```' >> "$OUT"
FILE1="$BASE/templates/dettaglio/dati_aziendali/_riquadro.html"
if [ -f "$FILE1" ]; then
    cat "$FILE1" >> "$OUT"
else
    echo "FILE NON TROVATO: $FILE1" >> "$OUT"
    echo "Cerco come viene incluso in dettaglio.html:" >> "$OUT"
    grep -n "dati_aziendali" "$BASE/templates/dettaglio.html" 2>/dev/null >> "$OUT"
fi
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 2. Card-header attuale _content.html (prime 15 righe)
# ==============================================================================
echo "---" >> "$OUT"
echo "## 2. Card-header _content.html dati_aziendali (prime 15 righe)" >> "$OUT"
echo '```html' >> "$OUT"
head -15 "$BASE/templates/dettaglio/dati_aziendali/_content.html" 2>/dev/null >> "$OUT" || echo "FILE NON TROVATO" >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 3. Include modal e scripts in dettaglio.html
# ==============================================================================
echo "---" >> "$OUT"
echo "## 3. Include modal/scripts in dettaglio.html" >> "$OUT"
echo '```' >> "$OUT"
grep -n "include.*_modal\|include.*_scripts\|block modals\|block scripts\|endblock" "$BASE/templates/dettaglio.html" 2>/dev/null >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 4. Tutti gli include in dettaglio.html
# ==============================================================================
echo "---" >> "$OUT"
echo "## 4. Tutti gli include in dettaglio.html" >> "$OUT"
echo '```' >> "$OUT"
grep -n "include" "$BASE/templates/dettaglio.html" 2>/dev/null >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 5. Ultime 40 righe di dettaglio.html (dove stanno modal e scripts)
# ==============================================================================
echo "---" >> "$OUT"
echo "## 5. Ultime 40 righe di dettaglio.html" >> "$OUT"
TOTALE=$(wc -l < "$BASE/templates/dettaglio.html" 2>/dev/null)
echo "Totale righe: $TOTALE" >> "$OUT"
echo '```html' >> "$OUT"
tail -40 "$BASE/templates/dettaglio.html" 2>/dev/null >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 6. Punto innesto API in web_server.py (route referente-principale e dintorni)
# ==============================================================================
echo "---" >> "$OUT"
echo "## 6. Route API esistenti per innesto (web_server.py)" >> "$OUT"
echo '```' >> "$OUT"
grep -n "def api_referente_principale\|def api_parco_potenziale\|def api_veicoli_rilevati\|def api_cerca_cliente\|def api_cerca_utenti" "$BASE/app/web_server.py" 2>/dev/null >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 7. Query ricerca principale (lista clienti) - WHERE con LIKE
# ==============================================================================
echo "---" >> "$OUT"
echo "## 7. Ricerca principale - blocco WHERE (web_server.py)" >> "$OUT"
echo "Cerco la query con search_normalized nella route principale..." >> "$OUT"
echo '```python' >> "$OUT"
# Trovo la riga con la prima occorrenza di search_normalized e stampo contesto
grep -n "search_normalized" "$BASE/app/web_server.py" 2>/dev/null | head -20 >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

echo "---" >> "$OUT"
echo "## 8. Contesto query ricerca principale (30 righe attorno a prima occorrenza)" >> "$OUT"
echo '```python' >> "$OUT"
RIGA=$(grep -n "search_normalized" "$BASE/app/web_server.py" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$RIGA" ]; then
    START=$((RIGA - 10))
    END=$((RIGA + 20))
    [ $START -lt 1 ] && START=1
    sed -n "${START},${END}p" "$BASE/app/web_server.py" >> "$OUT"
fi
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 9. Query /api/cerca completa
# ==============================================================================
echo "---" >> "$OUT"
echo "## 9. Funzione api_cerca_cliente completa" >> "$OUT"
echo '```python' >> "$OUT"
RIGA_API=$(grep -n "def api_cerca_cliente" "$BASE/app/web_server.py" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$RIGA_API" ]; then
    # Stampo 80 righe dalla definizione
    sed -n "${RIGA_API},$((RIGA_API + 80))p" "$BASE/app/web_server.py" >> "$OUT"
fi
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 10. get_search_matches_per_cliente (per aggiungere badge Alias)
# ==============================================================================
echo "---" >> "$OUT"
echo "## 10. Funzione get_search_matches_per_cliente" >> "$OUT"
echo '```' >> "$OUT"
RIGA_MATCH=$(grep -n "def get_search_matches_per_cliente" "$BASE/app/web_server.py" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$RIGA_MATCH" ]; then
    sed -n "${RIGA_MATCH},$((RIGA_MATCH + 100))p" "$BASE/app/web_server.py" >> "$OUT"
else
    echo "Funzione non trovata in web_server.py" >> "$OUT"
    grep -rn "def get_search_matches" "$BASE/app/" 2>/dev/null >> "$OUT"
fi
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 11. Tabella esistente? Check rapido
# ==============================================================================
echo "---" >> "$OUT"
echo "## 11. Check tabella clienti_nomi_alternativi nel DB" >> "$OUT"
echo '```' >> "$OUT"
sqlite3 "$BASE/db/gestionale.db" ".tables" 2>/dev/null | tr ' ' '\n' | grep -i "nomi\|alter" >> "$OUT" || echo "(nessuna tabella trovata)" >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
# 12. Badge ricerca smart (index) - template
# ==============================================================================
echo "---" >> "$OUT"
echo "## 12. Badge ricerca nella tabella index (grep alias/nomi/badge)" >> "$OUT"
echo '```' >> "$OUT"
grep -n "badge.*Alias\|badge.*Driver\|badge.*Sede\|badge.*Nota\|badge.*Contatto\|badge.*Targa\|badge.*Capogr\|search_matches_per_cliente" "$BASE/templates/index/_tabella.html" 2>/dev/null | head -20 >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# ==============================================================================
echo "---" >> "$OUT"
echo "## Fine raccolta" >> "$OUT"

echo ""
echo "========================================"
echo "  File generato: $OUT"
echo "  Righe: $(wc -l < "$OUT")"
echo "========================================"
echo ""
echo "Carica questo file nella chat con Claude."
