#!/bin/bash
# ==============================================================================
# STEP 2: Sostituzione FROM veicoli -> FROM veicoli_attivi
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-13
# Uso:
#   bash patch_veicoli_attivi.sh --dry-run    # Solo mostra cosa farebbe
#   bash patch_veicoli_attivi.sh              # Esegue le sostituzioni
# ==============================================================================

set -e

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

BASE=~/gestione_flotta
APP="$BASE/app"
BACKUP="$BASE/backup"
TS=$(date +%Y%m%d_%H%M%S)

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
fi

# File SEMPLICI: tutte le FROM veicoli -> FROM veicoli_attivi (nessuna eccezione)
SIMPLE_FILES=(
    "$APP/routes_installato.py"
    "$APP/routes_noleggiatori_cliente.py"
    "$APP/routes_revisioni.py"
    "$APP/routes_top_prospect.py"
    "$APP/routes_admin_utenti.py"
    "$APP/routes_flotta_commerciali.py"
    "$APP/database.py"
    "$APP/export_excel.py"
    "$APP/motore_top_prospect.py"
    "$APP/connettori_notifiche/revisione.py"
)

# File COMPLESSO: web_server.py ha eccezioni
WS="$APP/web_server.py"

# ==============================================================================
# FUNZIONI
# ==============================================================================

backup_file() {
    local filepath="$1"
    local relpath="${filepath#$BASE/}"
    local bname=$(echo "$relpath" | sed 's|/|__|g')
    local dest="$BACKUP/${bname}.bak_${TS}"
    
    if $DRY_RUN; then
        echo "  [DRY-RUN] backup: $bname"
    else
        cp "$filepath" "$dest"
        echo "  Backup: $bname"
    fi
}

count_matches() {
    local filepath="$1"
    local pattern="$2"
    grep -c "$pattern" "$filepath" 2>/dev/null || echo 0
}

# ==============================================================================
# MAIN
# ==============================================================================

echo "============================================================"
echo "  STEP 2: FROM veicoli -> FROM veicoli_attivi"
if $DRY_RUN; then
    echo "  Modalita: DRY-RUN (nessuna modifica)"
else
    echo "  Modalita: ESECUZIONE"
fi
echo "  Timestamp: $TS"
echo "============================================================"

# -------------------------------------------------------
# FASE 1: BACKUP
# -------------------------------------------------------
echo ""
echo "[FASE 1] Backup file..."

for f in "${SIMPLE_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        backup_file "$f"
    else
        echo "  ATTENZIONE: $f non trovato, skip"
    fi
done
backup_file "$WS"

# -------------------------------------------------------
# FASE 2: FILE SEMPLICI (nessuna eccezione)
# -------------------------------------------------------
echo ""
echo "[FASE 2] Replace nei file semplici..."

for f in "${SIMPLE_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        continue
    fi
    
    fname=$(basename "$f")
    c_from=$(count_matches "$f" 'FROM veicoli[^_]')
    c_join=$(count_matches "$f" 'JOIN veicoli[^_]')
    
    # Conta anche FROM veicoli a fine riga (il pattern [^_] non li cattura)
    c_eol=$(grep -c 'FROM veicoli$' "$f" 2>/dev/null || echo 0)
    c_total=$((c_from + c_join + c_eol))
    
    if [[ $c_total -eq 0 ]]; then
        echo "  $fname: nessuna occorrenza, skip"
        continue
    fi
    
    if $DRY_RUN; then
        echo "  $fname: $c_total occorrenze da sostituire:"
        grep -n 'FROM veicoli[^_]\|FROM veicoli$\|JOIN veicoli[^_]\|JOIN veicoli$' "$f" 2>/dev/null | sed 's/^/    /'
    else
        sed -i 's/FROM veicoli\b/FROM veicoli_attivi/g' "$f"
        sed -i 's/JOIN veicoli\b/JOIN veicoli_attivi/g' "$f"
        echo "  $fname: $c_total sostituzioni applicate"
    fi
done

# -------------------------------------------------------
# FASE 3: web_server.py (CON ECCEZIONI)
# -------------------------------------------------------
echo ""
echo "[FASE 3] web_server.py (con eccezioni)..."

c_ws_from=$(count_matches "$WS" 'FROM veicoli[^_]')
c_ws_eol=$(grep -c 'FROM veicoli$' "$WS" 2>/dev/null || echo 0)
c_ws_join=$(count_matches "$WS" 'JOIN veicoli[^_]')
echo "  Occorrenze trovate: FROM=$c_ws_from + EOL=$c_ws_eol + JOIN=$c_ws_join"

if $DRY_RUN; then
    echo ""
    echo "  PIANO:"
    echo "  3a. Sostituzione globale FROM/JOIN veicoli -> veicoli_attivi"
    echo "  3b. Revert eccezioni (devono restare su tabella veicoli):"
    echo "      - SELECT */id FROM veicoli WHERE id = ? con param (veicolo_id,)"
    echo "      - Merge route con param (sopravvive_id,) e (assorbito_id,)"
    echo "      - Ricerca targa: WHERE UPPER(targa)"
    echo ""
    echo "  Righe che saranno ECCEZIONI (restano FROM veicoli):"
    grep -n "FROM veicoli.*WHERE id = ?.*veicolo_id\|FROM veicoli.*sopravvive_id\|FROM veicoli.*assorbito_id\|FROM veicoli.*UPPER(targa)" "$WS" 2>/dev/null | sed 's/^/    /'
else
    # 3a. Sostituzione globale
    sed -i 's/FROM veicoli\b/FROM veicoli_attivi/g' "$WS"
    sed -i 's/JOIN veicoli\b/JOIN veicoli_attivi/g' "$WS"
    echo "  3a. Sostituzione globale completata"
    
    # 3b. Revert eccezioni
    # Eccezione 1: scheda singolo veicolo / verifica esistenza (param veicolo_id)
    # Queste query cercano un veicolo per ID e devono trovare anche i merged
    sed -i "s/FROM veicoli_attivi WHERE id = ?', (veicolo_id,)/FROM veicoli WHERE id = ?', (veicolo_id,)/g" "$WS"
    echo "  3b-1. Revert: SELECT per id con (veicolo_id,)"
    
    # Eccezione 2: merge route - sopravvive_id
    sed -i "s/FROM veicoli_attivi WHERE id = ? AND merged_in_veicolo_id IS NULL', (sopravvive_id,)/FROM veicoli WHERE id = ? AND merged_in_veicolo_id IS NULL', (sopravvive_id,)/g" "$WS"
    echo "  3b-2. Revert: merge route (sopravvive_id)"
    
    # Eccezione 3: merge route - assorbito_id
    sed -i "s/FROM veicoli_attivi WHERE id = ? AND merged_in_veicolo_id IS NULL', (assorbito_id,)/FROM veicoli WHERE id = ? AND merged_in_veicolo_id IS NULL', (assorbito_id,)/g" "$WS"
    echo "  3b-3. Revert: merge route (assorbito_id)"
    
    # Eccezione 4: ricerca per targa (deve trovare anche merged per evitare duplicati)
    sed -i 's/FROM veicoli_attivi WHERE UPPER(targa)/FROM veicoli WHERE UPPER(targa)/g' "$WS"
    echo "  3b-4. Revert: ricerca per targa UPPER(targa)"
fi

# -------------------------------------------------------
# FASE 4: PULIZIA FILTRI RIDONDANTI
# -------------------------------------------------------
echo ""
echo "[FASE 4] Pulizia filtri AND merged_in_veicolo_id IS NULL ridondanti..."

# Conta filtri ridondanti PRIMA della pulizia
c_redundant_v=$(grep -c 'veicoli_attivi.*AND v\.merged_in_veicolo_id IS NULL' "$WS" 2>/dev/null || echo 0)
c_redundant=$(grep -c 'veicoli_attivi.*AND merged_in_veicolo_id IS NULL' "$WS" 2>/dev/null || echo 0)
c_redundant_total=$((c_redundant_v + c_redundant))

if [[ $c_redundant_total -eq 0 ]]; then
    if $DRY_RUN; then
        echo "  [DRY-RUN] Nessun filtro ridondante da pulire (valutazione pre-replace)"
        echo "  NOTA: i filtri diventano ridondanti DOPO il replace, quindi in dry-run non si vedono"
    else
        echo "  Nessun filtro ridondante trovato"
    fi
else
    if $DRY_RUN; then
        echo "  [DRY-RUN] $c_redundant_total filtri ridondanti da rimuovere:"
        grep -n 'veicoli_attivi.*merged_in_veicolo_id IS NULL' "$WS" 2>/dev/null | sed 's/^/    /'
    else
        # Rimuovi solo su righe che contengono veicoli_attivi (le eccezioni usano veicoli, non toccate)
        sed -i '/veicoli_attivi/s/ AND v\.merged_in_veicolo_id IS NULL//g' "$WS"
        sed -i '/veicoli_attivi/s/ AND merged_in_veicolo_id IS NULL//g' "$WS"
        echo "  $c_redundant_total filtri ridondanti rimossi"
    fi
fi

# -------------------------------------------------------
# FASE 5: VERIFICA FINALE
# -------------------------------------------------------
echo ""
echo "[FASE 5] Verifica finale..."
echo ""

# 5a. Cerca residui FROM veicoli (non _attivi) nei file Python attivi
echo "  --- Residui FROM/JOIN veicoli (senza _attivi) ---"
echo "  (Queste devono essere SOLO le eccezioni documentate)"
echo ""

found_residui=false
for f in "${SIMPLE_FILES[@]}" "$WS"; do
    if [[ ! -f "$f" ]]; then continue; fi
    fname=$(basename "$f")
    
    residui=$(grep -n 'FROM veicoli[^_]\|FROM veicoli$\|JOIN veicoli[^_]\|JOIN veicoli$' "$f" 2>/dev/null | grep -v 'INSERT\|UPDATE\|DELETE' || true)
    
    if [[ -n "$residui" ]]; then
        found_residui=true
        echo "  $fname:"
        echo "$residui" | sed 's/^/    /'
        echo ""
    fi
done

if ! $found_residui; then
    echo "  Nessun residuo trovato (tutti i file semplici puliti)"
fi

# 5b. Conta sostituzioni effettuate
echo ""
echo "  --- Conteggio veicoli_attivi per file ---"
for f in "${SIMPLE_FILES[@]}" "$WS"; do
    if [[ ! -f "$f" ]]; then continue; fi
    fname=$(basename "$f")
    c=$(grep -c 'veicoli_attivi' "$f" 2>/dev/null || echo 0)
    if [[ $c -gt 0 ]]; then
        echo "  $fname: $c occorrenze veicoli_attivi"
    fi
done

# 5c. Verifica nessun filtro ridondante rimasto
echo ""
echo "  --- Filtri merged_in_veicolo_id residui ---"
c_still=$(grep -rn 'merged_in_veicolo_id' "$APP"/*.py "$APP"/connettori_notifiche/*.py 2>/dev/null | grep -v '.bak\|__pycache__' || true)
if [[ -n "$c_still" ]]; then
    echo "  Righe con merged_in_veicolo_id (verificare se eccezioni valide):"
    echo "$c_still" | sed 's/^/    /'
else
    echo "  Nessun filtro merged_in_veicolo_id residuo"
fi

echo ""
echo "============================================================"
if $DRY_RUN; then
    echo "  DRY-RUN COMPLETATO - Nessuna modifica applicata"
    echo "  Eseguire senza --dry-run per applicare"
else
    echo "  SOSTITUZIONE COMPLETATA"
    echo ""
    echo "  Prossimi passi:"
    echo "  1. Riavviare: ~/gestione_flotta/scripts/gestione_flotta.sh restart"
    echo "  2. Testare: scheda cliente IT03481990178"
    echo "  3. Testare: dashboard flotta, statistiche, scadenze"
    echo "  4. Verificare: scheda veicolo singolo (anche merged per audit)"
fi
echo "============================================================"
