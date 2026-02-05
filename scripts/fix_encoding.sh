#!/bin/bash
# ==============================================================================
# FIX ENCODING UTF-8 - Gestione Flotta
# ==============================================================================
# Versione: 3.2
# Data: 2025-01-22
# 
# SCOPO: Correggere automaticamente gli errori di encoding
# USA PERL per gestire pattern binari in modo affidabile
#
# USO:
#   cd ~/gestione_flotta
#   ./scripts/fix_encoding.sh              # Corregge tutto
#   ./scripts/fix_encoding.sh --diagnosi   # Solo analisi
# ==============================================================================

set -e
shopt -s nullglob

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directory base
BASE_DIR="${HOME}/gestione_flotta"
cd "$BASE_DIR" || { echo -e "${RED}Errore: directory $BASE_DIR non trovata${NC}"; exit 1; }

# Parametri
DIAGNOSI=0
for arg in "$@"; do
    [ "$arg" = "--diagnosi" ] && DIAGNOSI=1
done

echo ""
echo "=============================================="
echo "  FIX ENCODING v3.2 - Gestione Flotta"
echo "=============================================="
[ $DIAGNOSI -eq 1 ] && echo -e "  ${CYAN}MODALITA DIAGNOSI${NC}"
echo ""

FILES_FIXED=0

# ==============================================================================
# FUNZIONE: Fix file con PERL (gestisce pattern binari correttamente)
# ==============================================================================
fix_file_perl() {
    local f="$1"
    [ ! -f "$f" ] && return
    
    local modified=0
    local tmpfile=$(mktemp)
    cp "$f" "$tmpfile"
    
    # ------------------------------------------------------------------
    # EURO TRIPLO ENCODING -> &euro;
    # Pattern: C3 83 C2 A2 C3 A2 E2 82 AC C5 A1 C3 82 C2 AC
    # ------------------------------------------------------------------
    perl -i -pe 's/\xc3\x83\xc2\xa2\xc3\xa2\xe2\x82\xac\xc5\xa1\xc3\x82\xc2\xac/\&euro;/g' "$f"
    
    # ------------------------------------------------------------------
    # EURO TRIPLO VARIANTE (senza ultimi byte)
    # Pattern: C3 83 C2 A2 C3 A2 E2 82 AC ...
    # ------------------------------------------------------------------
    perl -i -pe 's/\xc3\x83\xc2\xa2\xc3\xa2\xe2\x82\xac[\xc5\xc3][\xa1\x82][\xc3]?[\x82]?[\xc2]?[\xac]?/\&euro;/g' "$f"
    
    # ------------------------------------------------------------------
    # EURO DOPPIO ENCODING -> &euro;  
    # Pattern: C3 A2 E2 82 AC + residui vari
    # ------------------------------------------------------------------
    perl -i -pe 's/\xc3\xa2\xe2\x82\xac[\xc2]?[\xac]?/\&euro;/g' "$f"
    
    # ------------------------------------------------------------------
    # EURO UTF-8 PURO -> &euro;
    # Pattern: E2 82 AC
    # ------------------------------------------------------------------
    perl -i -pe 's/\xe2\x82\xac/\&euro;/g' "$f"
    
    # ------------------------------------------------------------------
    # LETTERE ACCENTATE - DOPPIO ENCODING
    # ------------------------------------------------------------------
    # a grave: C3 83 C2 A0 -> C3 A0
    perl -i -pe 's/\xc3\x83\xc2\xa0/\xc3\xa0/g' "$f"
    # e grave: C3 83 C2 A8 -> C3 A8
    perl -i -pe 's/\xc3\x83\xc2\xa8/\xc3\xa8/g' "$f"
    # e acuto: C3 83 C2 A9 -> C3 A9
    perl -i -pe 's/\xc3\x83\xc2\xa9/\xc3\xa9/g' "$f"
    # i grave: C3 83 C2 AC -> C3 AC
    perl -i -pe 's/\xc3\x83\xc2\xac/\xc3\xac/g' "$f"
    # o grave: C3 83 C2 B2 -> C3 B2
    perl -i -pe 's/\xc3\x83\xc2\xb2/\xc3\xb2/g' "$f"
    # u grave: C3 83 C2 B9 -> C3 B9
    perl -i -pe 's/\xc3\x83\xc2\xb9/\xc3\xb9/g' "$f"
    
    # ------------------------------------------------------------------
    # LETTERE ACCENTATE - TRIPLO ENCODING
    # ------------------------------------------------------------------
    perl -i -pe 's/\xc3\x83\xc6\x92\xc3\x82\xc2\xa0/\xc3\xa0/g' "$f"
    perl -i -pe 's/\xc3\x83\xc6\x92\xc3\x82\xc2\xa8/\xc3\xa8/g' "$f"
    perl -i -pe 's/\xc3\x83\xc6\x92\xc3\x82\xc2\xac/\xc3\xac/g' "$f"
    perl -i -pe 's/\xc3\x83\xc6\x92\xc3\x82\xc2\xb2/\xc3\xb2/g' "$f"
    perl -i -pe 's/\xc3\x83\xc6\x92\xc3\x82\xc2\xb9/\xc3\xb9/g' "$f"
    
    # ------------------------------------------------------------------
    # SIMBOLI SPECIALI
    # ------------------------------------------------------------------
    # <= corrotto -> &le;
    perl -i -pe 's/\xc3\xa2\xe2\x80\xb0\xc2\xa4/\&le;/g' "$f"
    # >= corrotto -> &ge;
    perl -i -pe 's/\xc3\xa2\xe2\x80\xb0\xc2\xa5/\&ge;/g' "$f"
    
    # ------------------------------------------------------------------
    # PULIZIA RESIDUI
    # ------------------------------------------------------------------
    perl -i -pe 's/\xc5\xa1\xc3\x82\xc2\xac//g' "$f"
    perl -i -pe 's/\xc5\xa1[\xc3]?[\x82]?[\xc2]?[\xac]?//g' "$f"
    
    # Verifica se il file e stato modificato
    if ! cmp -s "$tmpfile" "$f"; then
        echo -e "  ${GREEN}[FIX]${NC} $f"
        ((FILES_FIXED++)) || true
    fi
    
    rm -f "$tmpfile"
}

# ==============================================================================
# ESECUZIONE
# ==============================================================================

if [ $DIAGNOSI -eq 1 ]; then
    echo "[DIAGNOSI] Ricerca pattern problematici..."
    echo ""
    
    # Cerca Euro UTF-8 (da convertire)
    echo "Euro UTF-8 (E2 82 AC):"
    grep -rl $'\xe2\x82\xac' templates/ app/ 2>/dev/null | while read f; do
        echo -e "  ${YELLOW}$f${NC}"
    done
    
    # Cerca Euro corrotto
    echo ""
    echo "Euro corrotto (C3 A2 ...):"
    grep -rl $'\xc3\xa2\xe2\x82\xac' templates/ app/ 2>/dev/null | while read f; do
        echo -e "  ${YELLOW}$f${NC}"
    done
    
    # Cerca doppio encoding accenti
    echo ""
    echo "Accenti doppio encoding (C3 83 C2):"
    grep -rl $'\xc3\x83\xc2' templates/ app/ 2>/dev/null | while read f; do
        echo -e "  ${YELLOW}$f${NC}"
    done
    
else
    echo "[1/4] templates/*.html..."
    for f in templates/*.html; do
        fix_file_perl "$f"
    done
    
    echo ""
    echo "[2/4] templates/**/*.html..."
    for f in templates/**/*.html; do
        fix_file_perl "$f"
    done
    
    echo ""
    echo "[3/4] app/*.py..."
    for f in app/*.py; do
        fix_file_perl "$f"
    done
    
    echo ""
    echo "[4/4] Scaricati/..."
    for f in Scaricati/*.html Scaricati/*.py; do
        fix_file_perl "$f"
    done
fi

# ==============================================================================
# VERIFICA FINALE
# ==============================================================================

echo ""
echo "=============================================="
echo "  VERIFICA FINALE"
echo "=============================================="

# Conta residui
R1=$(grep -rl $'\xc3\x83\xc2' templates/ app/ 2>/dev/null | wc -l || echo "0")
R2=$(grep -rl $'\xc3\xa2\xe2\x82\xac' templates/ app/ 2>/dev/null | wc -l || echo "0")
R3=$(grep -rl $'\xe2\x82\xac' templates/ app/ 2>/dev/null | wc -l || echo "0")
REMAINING=$((R1 + R2 + R3))

if [ "$REMAINING" -eq 0 ]; then
    echo -e "${GREEN}OK! Tutti i problemi risolti.${NC}"
    EURO_COUNT=$(grep -r '&euro;' templates/ app/ 2>/dev/null | wc -l || echo "0")
    echo "Simboli &euro; nel progetto: $EURO_COUNT"
else
    echo -e "${YELLOW}Ancora $REMAINING file con problemi${NC}"
    [ "$R1" -gt 0 ] && echo "  - Accenti doppio encoding: $R1"
    [ "$R2" -gt 0 ] && echo "  - Euro corrotto: $R2"
    [ "$R3" -gt 0 ] && echo "  - Euro UTF-8: $R3"
fi

echo ""
echo "=============================================="
echo -e "  ${GREEN}COMPLETATO${NC} - $FILES_FIXED file corretti"
echo "=============================================="
echo ""

[ $FILES_FIXED -gt 0 ] && echo "Riavvia: ./scripts/gestione_flotta.sh restart" && echo ""
