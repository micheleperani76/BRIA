#!/usr/bin/env python3
# ==============================================================================
# PATCH: Fix bug documenti cliente - _scripts_comuni.html
# ==============================================================================
# Data: 2026-02-12
# Fix 1: refreshDocumenti() - aggiunta casi contratti/ordini/quotazioni
# Fix 2: eseguiUpload() - mappatura container ID corretta
# ==============================================================================

import sys

TARGET = '/home/michele/gestione_flotta/templates/documenti_cliente/shared/_scripts_comuni.html'

# Leggi file
with open(TARGET, 'r', encoding='utf-8') as f:
    content = f.read()

original = content
fix_count = 0

# ==============================================================================
# FIX 1: refreshDocumenti() - aggiungere casi per contratti/ordini/quotazioni
# ==============================================================================

OLD_REFRESH = """    // === REFRESH LISTA DOCUMENTI (chiama la funzione specifica) ===
    function refreshDocumenti(tipo) {
        if (tipo === 'car-policy' && typeof window.caricaCarPolicy === 'function') {
            window.caricaCarPolicy();
        } else if (typeof window.caricaDocumenti === 'function') {
            window.caricaDocumenti(tipo);
        }
    }"""

NEW_REFRESH = """    // === REFRESH LISTA DOCUMENTI (chiama la funzione specifica) ===
    function refreshDocumenti(tipo) {
        if (tipo === 'car-policy' && typeof window.caricaCarPolicy === 'function') {
            window.caricaCarPolicy();
        } else if (tipo === 'contratti' && typeof window.caricaContratti === 'function') {
            window.caricaContratti();
        } else if (tipo === 'ordini' && typeof window.caricaOrdini === 'function') {
            window.caricaOrdini();
        } else if (tipo === 'quotazioni' && typeof window.caricaQuotazioni === 'function') {
            window.caricaQuotazioni();
        } else if (typeof window.caricaDocumenti === 'function') {
            window.caricaDocumenti(tipo);
        }
    }"""

if OLD_REFRESH in content:
    content = content.replace(OLD_REFRESH, NEW_REFRESH)
    fix_count += 1
    print("[OK] Fix 1: refreshDocumenti() - aggiunti casi contratti/ordini/quotazioni")
else:
    print("[!!] Fix 1: blocco refreshDocumenti() NON trovato - verificare manualmente")

# ==============================================================================
# FIX 2: eseguiUpload() - mappatura container ID corretta
# ==============================================================================

OLD_CONTAINER = """        const container = tipo === 'car-policy' 
            ? document.getElementById('car-policy-file-list')
            : document.getElementById('lista-' + tipo);"""

NEW_CONTAINER = """        const containerMap = {
            'car-policy': 'car-policy-file-list',
            'contratti': 'contratti-file-list',
            'ordini': 'ordini-file-list',
            'quotazioni': 'quotazioni-file-list'
        };
        const container = document.getElementById(containerMap[tipo] || 'lista-' + tipo);"""

if OLD_CONTAINER in content:
    content = content.replace(OLD_CONTAINER, NEW_CONTAINER)
    fix_count += 1
    print("[OK] Fix 2: eseguiUpload() - mappatura container corretta")
else:
    print("[!!] Fix 2: blocco container NON trovato - verificare manualmente")

# ==============================================================================
# SALVATAGGIO
# ==============================================================================

if fix_count > 0:
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n==> File salvato con {fix_count} fix applicati")
else:
    print("\n==> Nessun fix applicato, file non modificato")

if fix_count < 2:
    print("ATTENZIONE: non tutti i fix sono stati applicati!")
    sys.exit(1)
