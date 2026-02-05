#!/bin/bash
# ==============================================================================
# raccolta_file_ia.sh - Raccoglie file per aggiornamento progetto IA
# Versione: 3.0
# Data: 2026-01-30
# Novita v3: Backup ZIP automatico con data incrementale
# ==============================================================================

# === CONFIGURAZIONE ===
BASE_DIR="$HOME/gestione_flotta"
DEST_DIR="$BASE_DIR/file_per_ia"
BACKUP_DIR="$HOME"
DRY_RUN=false
SKIP_BACKUP=false

# Evita errori se glob non trova file
shopt -s nullglob

# === PARSING ARGOMENTI ===
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run|-n) DRY_RUN=true ;;
        --no-backup) SKIP_BACKUP=true ;;
        --help|-h)
            echo "Uso: $0 [opzioni]"
            echo "  --dry-run, -n    Simula senza copiare"
            echo "  --no-backup      Salta creazione backup ZIP"
            echo "  --help, -h       Mostra questo aiuto"
            exit 0
            ;;
    esac
    shift
done

if $DRY_RUN; then
    echo "=== MODALITA' DRY-RUN: nessun file verra' copiato ==="
    echo ""
fi

# === FUNZIONI ===
copia_file() {
    local src="$1"
    local prefisso="$2"
    local nome=$(basename "$src")
    
    # Salta file backup/bak
    if [[ "$nome" == *bak* || "$nome" == *backup* || "$nome" == *.bak ]]; then
        echo "  [SKIP backup] $nome"
        return
    fi
    
    # Costruisce nome con prefisso
    local nome_nuovo="${prefisso}__${nome}"
    
    if $DRY_RUN; then
        echo "  [COPIA] $nome_nuovo"
    else
        cp "$src" "$DEST_DIR/$nome_nuovo"
        echo "  [OK] $nome_nuovo"
    fi
}

crea_backup_zip() {
    echo ""
    echo "=========================================="
    echo "  Creazione Backup ZIP"
    echo "=========================================="
    
    # Genera nome con data e ora
    local DATA=$(date +%Y-%m-%d_%H%M)
    local NOME_ZIP="gestione_flotta_backup_${DATA}.zip"
    local PERCORSO_ZIP="$BACKUP_DIR/$NOME_ZIP"
    
    if $DRY_RUN; then
        echo "[DRY-RUN] Creerebbe: $PERCORSO_ZIP"
        return
    fi
    
    echo "Creazione backup in corso..."
    echo "Destinazione: $PERCORSO_ZIP"
    echo ""
    
    # Crea ZIP escludendo file non necessari
    cd "$HOME"
    zip -r "$PERCORSO_ZIP" gestione_flotta/ \
        -x "gestione_flotta/file_per_ia/*" \
        -x "gestione_flotta/backup/*" \
        -x "gestione_flotta/__pycache__/*" \
        -x "gestione_flotta/app/__pycache__/*" \
        -x "gestione_flotta/logs/*" \
        -x "gestione_flotta/Scaricati/*" \
        -x "*.pyc" \
        -x "*.bak" \
        -x "*.bak_*" \
        > /dev/null 2>&1
    
    if [[ $? -eq 0 ]]; then
        local DIMENSIONE=$(du -h "$PERCORSO_ZIP" | cut -f1)
        echo "[OK] Backup creato: $NOME_ZIP ($DIMENSIONE)"
        
        # Mostra ultimi backup
        echo ""
        echo "Ultimi backup disponibili:"
        ls -lht "$BACKUP_DIR"/gestione_flotta_backup_*.zip 2>/dev/null | head -5
    else
        echo "[ERRORE] Creazione backup fallita"
    fi
}

# === INIZIO ===
echo "=========================================="
echo "  Raccolta file per progetto IA v3.0"
echo "=========================================="
echo ""

# Crea cartella destinazione
if ! $DRY_RUN; then
    rm -rf "$DEST_DIR"
    mkdir -p "$DEST_DIR"
    echo "[+] Creata cartella: $DEST_DIR"
else
    echo "[DRY-RUN] Creerebbe cartella: $DEST_DIR"
fi
echo ""

# 1. File dalla root (solo file, no cartelle)
echo ">>> Root gestione_flotta/"
for f in "$BASE_DIR"/*.py "$BASE_DIR"/*.sh "$BASE_DIR"/*.md "$BASE_DIR"/*.txt; do
    [[ -f "$f" ]] && copia_file "$f" "root"
done
echo ""

# 2. Cartella app/ (escluso __pycache__)
echo ">>> app/"
for f in "$BASE_DIR/app"/*.py "$BASE_DIR/app"/*.conf; do
    [[ -f "$f" ]] && copia_file "$f" "app"
done
echo ""

# 3. Cartella documentazione/
echo ">>> documentazione/"
for f in "$BASE_DIR/documentazione"/*; do
    [[ -f "$f" ]] && copia_file "$f" "documentazione"
done
echo ""

# 4. Cartella impostazioni/
echo ">>> impostazioni/"
for f in "$BASE_DIR/impostazioni"/*; do
    [[ -f "$f" ]] && copia_file "$f" "impostazioni"
done
echo ""

# 5. Cartella scripts/
echo ">>> scripts/"
for f in "$BASE_DIR/scripts"/*; do
    [[ -f "$f" ]] && copia_file "$f" "scripts"
done
echo ""

# 6. Cartella templates/ (ricorsiva con prefisso percorso)
echo ">>> templates/ (tutte le sottocartelle)"
find "$BASE_DIR/templates" -type f ! -name "*bak*" ! -name "*backup*" | while read f; do
    # Estrae percorso relativo e lo converte in prefisso
    rel_path="${f#$BASE_DIR/}"
    dir_path=$(dirname "$rel_path")
    prefisso="${dir_path//\//__}"
    copia_file "$f" "$prefisso"
done
echo ""

# 7. Genera tree.txt automatico
echo ">>> Generazione tree.txt..."
if ! $DRY_RUN; then
    tree -a "$BASE_DIR" --noreport -I "__pycache__|file_per_ia|*.pyc" > "$DEST_DIR/documentazione__tree.txt"
    echo "  [OK] documentazione__tree.txt"
else
    echo "  [GENERA] documentazione__tree.txt"
fi
echo ""

# === RIEPILOGO RACCOLTA ===
echo "=========================================="
if $DRY_RUN; then
    echo "DRY-RUN completato. Usa senza --dry-run per copiare."
else
    CONTEGGIO=$(ls -1 "$DEST_DIR" 2>/dev/null | wc -l)
    echo "Raccolta completata! File copiati: $CONTEGGIO"
    echo "Cartella: $DEST_DIR"
fi
echo "=========================================="

# === BACKUP ZIP ===
if ! $SKIP_BACKUP; then
    crea_backup_zip
fi

echo ""
echo "Fine operazioni."
