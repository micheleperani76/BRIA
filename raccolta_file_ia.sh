#!/bin/bash
# ==============================================================================
# raccolta_file_ia.sh - Raccoglie file per aggiornamento progetto IA
# Versione: 4.0
# Data: 2026-02-05
# Novita v4: Sync automatico con GitHub + backup ZIP
# ==============================================================================

# === CONFIGURAZIONE ===
BASE_DIR="$HOME/gestione_flotta"
DEST_DIR="$BASE_DIR/file_per_ia"
BACKUP_DIR="$HOME"
DRY_RUN=false
SKIP_BACKUP=false
SKIP_GIT=false
SKIP_RACCOLTA=false

# Evita errori se glob non trova file
shopt -s nullglob

# === PARSING ARGOMENTI ===
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run|-n) DRY_RUN=true ;;
        --no-backup) SKIP_BACKUP=true ;;
        --no-git) SKIP_GIT=true ;;
        --solo-git) SKIP_BACKUP=true; SKIP_RACCOLTA=true ;;
        --solo-backup) SKIP_GIT=true; SKIP_RACCOLTA=true ;;
        --help|-h)
            echo "Uso: $0 [opzioni]"
            echo ""
            echo "  --dry-run, -n    Simula senza copiare/pushare"
            echo "  --no-backup      Salta creazione backup ZIP"
            echo "  --no-git         Salta sync GitHub"
            echo "  --solo-git       Esegue solo il sync GitHub"
            echo "  --solo-backup    Esegue solo il backup ZIP"
            echo "  --help, -h       Mostra questo aiuto"
            exit 0
            ;;
    esac
    shift
done

if $DRY_RUN; then
    echo "=== MODALITA' DRY-RUN: nessuna operazione reale ==="
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
        -x "gestione_flotta/.git/*" \
        -x "gestione_flotta/clienti/*" \
        -x "gestione_flotta/db/*" \
        -x "gestione_flotta/account_esterni/*" \
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

sync_github() {
    echo ""
    echo "=========================================="
    echo "  Sync GitHub"
    echo "=========================================="
    
    cd "$BASE_DIR"
    
    # Verifica che sia un repo git
    if [[ ! -d ".git" ]]; then
        echo "[ERRORE] Non e' un repository git. Esegui prima: git init"
        return 1
    fi
    
    # Mostra stato
    local MODIFICATI=$(git status --porcelain 2>/dev/null | wc -l)
    
    if [[ "$MODIFICATI" -eq 0 ]]; then
        echo "[INFO] Nessuna modifica da sincronizzare."
        return 0
    fi
    
    echo "File modificati: $MODIFICATI"
    echo ""
    
    # Mostra riepilogo modifiche
    echo "Riepilogo:"
    git status --short | head -20
    if [[ "$MODIFICATI" -gt 20 ]]; then
        echo "  ... e altri $((MODIFICATI - 20)) file"
    fi
    echo ""
    
    if $DRY_RUN; then
        echo "[DRY-RUN] Farebbe: git add + commit + push"
        return 0
    fi
    
    # Chiedi messaggio di commit (o usa default con data)
    local DATA_ORA=$(date '+%Y-%m-%d %H:%M')
    local MSG_DEFAULT="Aggiornamento $DATA_ORA"
    
    read -p "Messaggio commit [$MSG_DEFAULT]: " MSG_CUSTOM
    local MSG="${MSG_CUSTOM:-$MSG_DEFAULT}"
    
    # Esegui commit e push
    echo ""
    git add .
    git commit -m "$MSG"
    
    echo ""
    echo "Push in corso..."
    if git push 2>&1; then
        echo ""
        echo "[OK] Sync GitHub completato!"
        echo "     Repo: $(git remote get-url origin 2>/dev/null)"
        echo "     Commit: $(git log --oneline -1)"
    else
        echo ""
        echo "[ERRORE] Push fallito. Verifica connessione e credenziali."
        echo "  Suggerimento: controlla il token su https://github.com/settings/tokens"
        return 1
    fi
}

# =============================================
# === INIZIO ===
# =============================================
echo "=========================================="
echo "  Gestione Flotta - Fine sessione v4.0"
echo "=========================================="
echo ""

# === RACCOLTA FILE PER IA ===
if ! $SKIP_RACCOLTA; then

    echo ">>> FASE 1: Raccolta file per progetto IA"
    echo "------------------------------------------"
    
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
    
    # 2b. Cartella app/connettori_notifiche/
    echo ">>> app/connettori_notifiche/"
    for f in "$BASE_DIR/app/connettori_notifiche"/*.py; do
        [[ -f "$f" ]] && copia_file "$f" "app__connettori_notifiche"
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
        rel_path="${f#$BASE_DIR/}"
        dir_path=$(dirname "$rel_path")
        prefisso="${dir_path//\//__}"
        copia_file "$f" "$prefisso"
    done
    echo ""
    
    # 7. Genera tree.txt automatico
    echo ">>> Generazione tree.txt..."
    if ! $DRY_RUN; then
        tree -a "$BASE_DIR" --noreport -I "__pycache__|file_per_ia|*.pyc|.git" > "$DEST_DIR/documentazione__tree.txt"
        echo "  [OK] documentazione__tree.txt"
    else
        echo "  [GENERA] documentazione__tree.txt"
    fi
    echo ""
    
    # === RIEPILOGO RACCOLTA ===
    echo "------------------------------------------"
    if $DRY_RUN; then
        echo "DRY-RUN raccolta completato."
    else
        CONTEGGIO=$(ls -1 "$DEST_DIR" 2>/dev/null | wc -l)
        echo "Raccolta completata! File copiati: $CONTEGGIO"
        echo "Cartella: $DEST_DIR"
    fi

fi

# === SYNC GITHUB ===
if ! $SKIP_GIT; then
    sync_github
fi

# === BACKUP ZIP ===
if ! $SKIP_BACKUP; then
    crea_backup_zip
fi

# === RIEPILOGO FINALE ===
echo ""
echo "=========================================="
echo "  Riepilogo operazioni"
echo "=========================================="
if ! $SKIP_RACCOLTA; then
    echo "  [x] Raccolta file IA"
fi
if ! $SKIP_GIT; then
    echo "  [x] Sync GitHub"
fi
if ! $SKIP_BACKUP; then
    echo "  [x] Backup ZIP"
fi
echo "=========================================="
echo ""
echo "Fine operazioni."
