#!/bin/bash
# ==============================================================================
# raccolta_file_ia.sh - Sync GitHub + Backup fine sessione
# Versione: 4.1
# Data: 2026-02-05
# Descrizione: Sync automatico con GitHub e backup ZIP locale
# ==============================================================================

# === CONFIGURAZIONE ===
BASE_DIR="$HOME/gestione_flotta"
BACKUP_DIR="$HOME"
DRY_RUN=false
SKIP_BACKUP=false
SKIP_GIT=false

# === PARSING ARGOMENTI ===
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run|-n) DRY_RUN=true ;;
        --no-backup) SKIP_BACKUP=true ;;
        --no-git) SKIP_GIT=true ;;
        --solo-git) SKIP_BACKUP=true ;;
        --solo-backup) SKIP_GIT=true ;;
        --help|-h)
            echo "Uso: $0 [opzioni]"
            echo ""
            echo "  --dry-run, -n    Simula senza pushare/creare backup"
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

# =============================================
# === INIZIO ===
# =============================================
echo "=========================================="
echo "  Gestione Flotta - Fine sessione v4.1"
echo "=========================================="

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
if ! $SKIP_GIT; then
    echo "  [x] Sync GitHub"
fi
if ! $SKIP_BACKUP; then
    echo "  [x] Backup ZIP"
fi
echo "=========================================="
echo ""
echo "Fine operazioni."
