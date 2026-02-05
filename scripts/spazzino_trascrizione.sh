#!/bin/bash
# ==============================================================================
# SPAZZINO TRASCRIZIONE - Pulizia file orfani
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-04
# Descrizione: Elimina i file audio rimasti su disco senza un job attivo nel DB.
#              Controlla attesa/ e lavorazione/ e rimuove file che non hanno
#              un job corrispondente in stato 'attesa' o 'lavorazione'.
#
# Sicurezza:
#   - NON tocca file con job attivo (attesa/lavorazione)
#   - Modalita' dry-run di default (--esegui per cancellare davvero)
#   - Log dettagliato di ogni azione
#
# Uso:
#   bash spazzino_trascrizione.sh              # dry-run (solo report)
#   bash spazzino_trascrizione.sh --esegui     # cancella davvero
# ==============================================================================

set -e

# --- Configurazione ---
BASE_DIR="$HOME/gestione_flotta"
TRASCRIZIONE_DIR="$BASE_DIR/trascrizione"
DB="$BASE_DIR/db/gestionale.db"
DIR_ATTESA="$TRASCRIZIONE_DIR/attesa"
DIR_LAVORAZIONE="$TRASCRIZIONE_DIR/lavorazione"

# --- Modalita' ---
ESEGUI=false
if [ "$1" = "--esegui" ]; then
    ESEGUI=true
fi

echo "=============================================="
echo "  SPAZZINO TRASCRIZIONE"
echo "=============================================="
echo "  Data: $(date '+%Y-%m-%d %H:%M:%S')"
if $ESEGUI; then
    echo "  Modalita': ESECUZIONE (cancella file)"
else
    echo "  Modalita': DRY-RUN (solo report)"
fi
echo "=============================================="

# --- Verifica prerequisiti ---
if [ ! -f "$DB" ]; then
    echo "[ERRORE] Database non trovato: $DB"
    exit 1
fi

# --- Recupera job attivi dal DB ---
echo ""
echo "--- Job attivi nel DB (attesa/lavorazione) ---"

JOB_ATTIVI=$(sqlite3 "$DB" "SELECT nome_file_sistema FROM coda_trascrizioni WHERE stato IN ('attesa','lavorazione');" 2>/dev/null)

if [ -z "$JOB_ATTIVI" ]; then
    echo "  Nessun job attivo"
else
    echo "$JOB_ATTIVI" | while read f; do echo "  [ATTIVO] $f"; done
fi

# --- Funzione: controlla se un file e' orfano ---
is_orfano() {
    local nome_base="$1"
    # Rimuovi estensione per confronto (il .wav e' generato dalla conversione)
    local nome_senza_ext="${nome_base%.*}"
    
    # Cerca se esiste un job attivo con questo nome (con qualsiasi estensione)
    local trovato=$(echo "$JOB_ATTIVI" | grep -c "^${nome_senza_ext}\." 2>/dev/null || true)
    
    if [ "$trovato" -gt 0 ]; then
        return 1  # NON orfano (job attivo trovato)
    else
        return 0  # Orfano
    fi
}

# --- Scansione cartella ATTESA ---
echo ""
echo "--- Scansione: attesa/ ---"
ORFANI_ATTESA=0
BYTE_ATTESA=0

if [ -d "$DIR_ATTESA" ]; then
    for file in "$DIR_ATTESA"/*; do
        [ -f "$file" ] || continue
        nome=$(basename "$file")
        dimensione=$(stat -c%s "$file" 2>/dev/null || echo 0)
        
        if is_orfano "$nome"; then
            ORFANI_ATTESA=$((ORFANI_ATTESA + 1))
            BYTE_ATTESA=$((BYTE_ATTESA + dimensione))
            dim_mb=$(( dimensione / 1024 )) ; dim_mb="${dim_mb} KB"
            
            if $ESEGUI; then
                rm -f "$file"
                echo "  [ELIMINATO] $nome (${dim_mb} MB)"
            else
                echo "  [ORFANO]    $nome (${dim_mb} MB)"
            fi
        else
            echo "  [ATTIVO]    $nome (job in corso, non tocco)"
        fi
    done
else
    echo "  Cartella non trovata"
fi

if [ "$ORFANI_ATTESA" -eq 0 ]; then
    echo "  Nessun file orfano"
fi

# --- Scansione cartella LAVORAZIONE ---
echo ""
echo "--- Scansione: lavorazione/ ---"
ORFANI_LAVORAZIONE=0
BYTE_LAVORAZIONE=0

if [ -d "$DIR_LAVORAZIONE" ]; then
    for file in "$DIR_LAVORAZIONE"/*; do
        [ -f "$file" ] || continue
        nome=$(basename "$file")
        dimensione=$(stat -c%s "$file" 2>/dev/null || echo 0)
        
        if is_orfano "$nome"; then
            ORFANI_LAVORAZIONE=$((ORFANI_LAVORAZIONE + 1))
            BYTE_LAVORAZIONE=$((BYTE_LAVORAZIONE + dimensione))
            dim_mb=$(( dimensione / 1024 )) ; dim_mb="${dim_mb} KB"
            
            if $ESEGUI; then
                rm -f "$file"
                echo "  [ELIMINATO] $nome (${dim_mb} MB)"
            else
                echo "  [ORFANO]    $nome (${dim_mb} MB)"
            fi
        else
            echo "  [ATTIVO]    $nome (job in corso, non tocco)"
        fi
    done
else
    echo "  Cartella non trovata"
fi

if [ "$ORFANI_LAVORAZIONE" -eq 0 ]; then
    echo "  Nessun file orfano"
fi

# --- Riepilogo ---
TOTALE_ORFANI=$((ORFANI_ATTESA + ORFANI_LAVORAZIONE))
TOTALE_BYTE=$((BYTE_ATTESA + BYTE_LAVORAZIONE))
TOTALE_KB=$((TOTALE_BYTE / 1024))

echo ""
echo "=============================================="
echo "  RIEPILOGO"
echo "=============================================="
echo "  File orfani attesa:      $ORFANI_ATTESA"
echo "  File orfani lavorazione: $ORFANI_LAVORAZIONE"
echo "  Totale orfani:           $TOTALE_ORFANI"
echo "  Spazio:                  ${TOTALE_KB} KB"

if $ESEGUI; then
    echo ""
    echo "  [OK] File orfani eliminati"
else
    echo ""
    if [ "$TOTALE_ORFANI" -gt 0 ]; then
        echo "  Per eliminare: bash spazzino_trascrizione.sh --esegui"
    else
        echo "  Nessuna azione necessaria"
    fi
fi
echo "=============================================="
