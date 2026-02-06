#!/bin/bash
# ==============================================================================
# PATCH TOPBAR TICKER + CAMPANELLA SOLO ALTO
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-06
# Descrizione: Aggiunge topbar ticker, rimuove posizioni basso campanella,
#              aggiunge padding-top al contenuto in base.html
#
# USO: bash patch_topbar.sh
# PREREQUISITO: _topbar.html deve essere in ~/gestione_flotta/Scaricati/
# ==============================================================================

BASE_DIR="$HOME/gestione_flotta"
BACKUP_DIR="$BASE_DIR/backup"
CAMP="$BASE_DIR/templates/notifiche/_campanella.html"
BASE="$BASE_DIR/templates/base.html"

# Colori
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}  PATCH TOPBAR TICKER + CAMPANELLA                         ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""

# ==============================================================================
# 0. VERIFICA FILE ESISTENTI
# ==============================================================================
echo -e "${YELLOW}[0/5]${NC} Verifica file..."

ERRORI=0
for f in "$CAMP" "$BASE"; do
    if [ ! -f "$f" ]; then
        echo -e "${RED}  ERRORE: $(basename $f) non trovato!${NC}"
        ERRORI=1
    fi
done

if [ ! -f "$BASE_DIR/Scaricati/_topbar.html" ]; then
    echo -e "${RED}  ERRORE: _topbar.html non trovato in Scaricati/${NC}"
    echo "  Scaricalo prima e mettilo in ~/gestione_flotta/Scaricati/"
    ERRORI=1
fi

if [ "$ERRORI" = "1" ]; then
    exit 1
fi
echo -e "${GREEN}  OK${NC} - Tutti i file trovati"

# ==============================================================================
# 1. BACKUP
# ==============================================================================
echo ""
echo -e "${YELLOW}[1/5]${NC} Backup file..."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cp "$CAMP" "$BACKUP_DIR/templates__notifiche___campanella.html.bak_${TIMESTAMP}"
echo -e "${GREEN}  OK${NC} - _campanella.html"

cp "$BASE" "$BACKUP_DIR/templates__base.html.bak_${TIMESTAMP}"
echo -e "${GREEN}  OK${NC} - base.html"

# ==============================================================================
# 2. DEPLOY _topbar.html
# ==============================================================================
echo ""
echo -e "${YELLOW}[2/5]${NC} Deploy _topbar.html..."

mkdir -p "$BASE_DIR/templates/componenti"
mv "$BASE_DIR/Scaricati/_topbar.html" "$BASE_DIR/templates/componenti/"
echo -e "${GREEN}  OK${NC} - Deployato in templates/componenti/"

# ==============================================================================
# 3. PATCH _campanella.html (Python per precisione su blocchi multi-linea)
# ==============================================================================
echo ""
echo -e "${YELLOW}[3/5]${NC} Patch _campanella.html..."

python3 - "$CAMP" << 'PYEOF'
import re, sys

fp = sys.argv[1]
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()

mod = 0

# 1. Widget default top: 16px -> 3px (centra 44px bell nella topbar 50px)
old = 'top: 16px;\n        right: 20px;'
if old in c:
    c = c.replace(old, 'top: 3px;\n        right: 20px;', 1)
    mod += 1

# 2-3. Posizioni top widget: 16px -> 3px
for o, n in [
    ('.pos-top-right    { top: 16px;', '.pos-top-right    { top: 3px;'),
    ('.pos-top-left     { top: 16px;', '.pos-top-left     { top: 3px;'),
]:
    if o in c:
        c = c.replace(o, n)
        mod += 1

# 4-5. Rimuovi posizioni bottom widget CSS
for pat in [
    r'[ \t]*\.notifiche-widget\.pos-bottom-right\s*\{[^}]+\}\s*\n',
    r'[ \t]*\.notifiche-widget\.pos-bottom-left\s*\{[^}]+\}\s*\n',
]:
    c2 = re.sub(pat, '', c)
    if c2 != c: c = c2; mod += 1

# 6. Rimuovi dropdown bottom (blocco multi-linea)
c2 = re.sub(
    r'[ \t]*\.notifiche-widget\.pos-bottom-right\s+\.notifiche-dropdown,\s*\n'
    r'[ \t]*\.notifiche-widget\.pos-bottom-left\s+\.notifiche-dropdown\s*\{[^}]+\}\s*\n',
    '', c
)
if c2 != c: c = c2; mod += 1

# 7. Rimuovi corner hints bottom CSS
for pat in [
    r'[ \t]*\.notifiche-corner-hint\.pos-bottom-right\s*\{[^}]+\}\s*\n',
    r'[ \t]*\.notifiche-corner-hint\.pos-bottom-left\s*\{[^}]+\}\s*\n',
]:
    c2 = re.sub(pat, '', c)
    if c2 != c: c = c2; mod += 1

# 8. Rimuovi corner hints bottom HTML
for pat in [
    r'<div class="notifiche-corner-hint pos-bottom-right"[^>]*></div>\s*\n',
    r'<div class="notifiche-corner-hint pos-bottom-left"[^>]*></div>\s*\n',
]:
    c2 = re.sub(pat, '', c)
    if c2 != c: c = c2; mod += 1

# 9-10. Corner hint top positions: 10px -> 3px
for o, n in [
    ('.pos-top-right    { top: 10px;', '.pos-top-right    { top: 3px;'),
    ('.pos-top-left     { top: 10px;', '.pos-top-left     { top: 3px;'),
]:
    if o in c:
        c = c.replace(o, n)
        mod += 1

# 11. Array JS: rimuovi posizioni bottom
for o, n in [
    ("const cornersIds = ['corner-tr', 'corner-tl', 'corner-br', 'corner-bl'];",
     "const cornersIds = ['corner-tr', 'corner-tl'];"),
    ("const posizioni = ['pos-top-right', 'pos-top-left', 'pos-bottom-right', 'pos-bottom-left'];",
     "const posizioni = ['pos-top-right', 'pos-top-left'];"),
]:
    if o in c:
        c = c.replace(o, n)
        mod += 1

# 12. Fix responsive: rimuovi bottom dai selettori combinati
for pat, repl in [
    (r'(\.notifiche-widget\.pos-top-right\s+\.notifiche-dropdown),\s*\n\s*'
     r'\.notifiche-widget\.pos-bottom-right\s+\.notifiche-dropdown\s*\{',
     r'\1 {'),
    (r'(\.notifiche-widget\.pos-top-left\s+\.notifiche-dropdown),\s*\n\s*'
     r'\.notifiche-widget\.pos-bottom-left\s+\.notifiche-dropdown\s*\{',
     r'\1 {'),
]:
    c2 = re.sub(pat, repl, c)
    if c2 != c: c = c2; mod += 1

# Scrivi risultato
with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)

print(f'  Modifiche applicate: {mod}')
if mod == 0:
    print('  ATTENZIONE: nessuna modifica (file gia patchato?)')
PYEOF

echo -e "${GREEN}  OK${NC} - _campanella.html patchata"

# ==============================================================================
# 4. PATCH base.html
# ==============================================================================
echo ""
echo -e "${YELLOW}[4/5]${NC} Patch base.html..."

# 4a. Aggiungi include _topbar.html PRIMA della campanella
if grep -q '_topbar.html' "$BASE"; then
    echo -e "${YELLOW}  SKIP${NC} - Include topbar gia presente"
else
    sed -i 's|{% include "notifiche/_campanella.html" %}|{% include "componenti/_topbar.html" %}\n    {% include "notifiche/_campanella.html" %}|' "$BASE"
    echo -e "${GREEN}  OK${NC} - Include topbar aggiunto"
fi

# 4b. Aggiungi padding-top a .main-content
if grep -q 'padding-top:.*calc.*50px' "$BASE"; then
    echo -e "${YELLOW}  SKIP${NC} - padding-top gia presente"
else
    sed -i '/\.main-content {/,/padding: 2rem;/ {
        /padding: 2rem;/ a\
            padding-top: calc(2rem + 50px);
    }' "$BASE"
    echo -e "${GREEN}  OK${NC} - padding-top aggiunto a .main-content"
fi

# ==============================================================================
# 5. VERIFICA
# ==============================================================================
echo ""
echo -e "${YELLOW}[5/5]${NC} Verifica..."

[ -f "$BASE_DIR/templates/componenti/_topbar.html" ] && \
    echo -e "${GREEN}  OK${NC} - _topbar.html in templates/componenti/" || \
    echo -e "${RED}  ERRORE${NC} - _topbar.html mancante!"

grep -q '_topbar.html' "$BASE" && \
    echo -e "${GREEN}  OK${NC} - Include topbar in base.html" || \
    echo -e "${RED}  ERRORE${NC} - Include topbar mancante!"

grep -q 'padding-top' "$BASE" && \
    echo -e "${GREEN}  OK${NC} - padding-top in base.html" || \
    echo -e "${RED}  ERRORE${NC} - padding-top mancante!"

grep -q 'pos-bottom' "$CAMP" && \
    echo -e "${YELLOW}  WARN${NC} - Ancora riferimenti pos-bottom in campanella" || \
    echo -e "${GREEN}  OK${NC} - Posizioni bottom rimosse da campanella"

file -i "$CAMP" | grep -q 'utf-8' && \
    echo -e "${GREEN}  OK${NC} - Encoding campanella OK" || \
    echo -e "${YELLOW}  WARN${NC} - Verificare encoding campanella"

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${GREEN}  PATCH COMPLETATA                                         ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""
echo "Riavvia il server:"
echo "  ~/gestione_flotta/scripts/gestione_flotta.sh restart"
echo ""
