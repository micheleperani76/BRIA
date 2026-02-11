#!/usr/bin/env python3
# ==============================================================================
# MODULARIZZAZIONE DETTAGLIO.HTML - Fase 1 Layout Editor
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-10
# Descrizione: Estrae 14 blocchi inline da dettaglio.html in file satellite
#              e li sostituisce con {% include %}
#
# Uso:
#   python3 scripts/modularizza_dettaglio.py --dry-run   # Anteprima (DEFAULT)
#   python3 scripts/modularizza_dettaglio.py --esegui    # Esecuzione reale
# ==============================================================================

import os
import sys
import re
import shutil
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

BASE_DIR = Path(os.path.expanduser('~/gestione_flotta'))
TEMPLATE_FILE = BASE_DIR / 'templates' / 'dettaglio.html'
TEMPLATES_DIR = BASE_DIR / 'templates'
BACKUP_DIR = BASE_DIR / 'backup'

ESEGUI = '--esegui' in sys.argv
DRY_RUN = not ESEGUI  # Default: dry-run

# ==============================================================================
# DEFINIZIONE BLOCCHI DA ESTRARRE
# ==============================================================================
# Ogni blocco ha:
#   id:        identificativo univoco
#   marker:    testo univoco per trovare una riga DENTRO il blocco
#   type:      'card' | 'modal' | 'if_card' | 'if_section' | 'conditional_col'
#   satellite: percorso file satellite (relativo a templates/)
#
# Ordine: dal BASSO verso l'ALTO (cosi' le righe non shiftano durante le sostituzioni)
# ==============================================================================

BLOCKS = [
    # --- 14. Storico Modifiche (if-wrapped card) ---
    {
        'id': 'storico',
        'marker': 'collapse-storico',
        'type': 'if_card',
        'satellite': 'dettaglio/storico/_content.html',
    },
    # --- 13. Vetture proposte da stock ---
    {
        'id': 'vetture_stock',
        'marker': 'collapse-vetture-stock',
        'type': 'card',
        'satellite': 'dettaglio/vetture_stock/_content.html',
    },
    # --- 12. Veicoli (if-wrapped section con include interno) ---
    {
        'id': 'veicoli',
        'marker': 'bi-car-front"></i> Veicoli</span>',
        'type': 'if_card',
        'satellite': 'dettaglio/veicoli/_content.html',
    },
    # --- 11. Finanziari/Bilancio (dentro col-md-6, con if/else) ---
    {
        'id': 'finanziari',
        'marker': 'bi-bar-chart"></i> Bilancio',
        'type': 'conditional_col',
        'satellite': 'dettaglio/finanziari/_content.html',
    },
    # --- 10. Descrizione/ATECO (dentro col-md-6, card h-100) ---
    {
        'id': 'descrizione',
        'marker': 'bi-briefcase"></i> Descrizione',
        'type': 'card',
        'satellite': 'dettaglio/descrizione/_content.html',
    },
    # --- 9. Referenti (full-width card) ---
    {
        'id': 'referenti',
        'marker': 'bi-people"></i> Referenti',
        'type': 'card',
        'satellite': 'dettaglio/referenti/_content.html',
    },
    # --- 8. Info Date ---
    {
        'id': 'info',
        'marker': 'bi-info-circle"></i> Info',
        'type': 'card',
        'satellite': 'dettaglio/info/_content.html',
    },
    # --- 7. Flotta Riepilogo ---
    {
        'id': 'flotta',
        'marker': 'inputParcoPotenziale',
        'type': 'card',
        'satellite': 'dettaglio/flotta/_content.html',
    },
    # --- 6. Modal Storico Commerciali ---
    {
        'id': 'commerciale_storico',
        'marker': 'id="modalStoricoCommerciali"',
        'type': 'modal',
        'satellite': 'dettaglio/commerciale_storico/_content.html',
    },
    # --- 5. Fido Consigliato ---
    {
        'id': 'fido',
        'marker': 'bi-credit-card"></i> Fido Consigliato',
        'type': 'card',
        'satellite': 'dettaglio/fido/_content.html',
    },
    # --- 4. Rating ---
    {
        'id': 'rating',
        'marker': 'bi-shield-check me-2',
        'type': 'card',
        'satellite': 'dettaglio/rating/_content.html',
    },
    # --- 3. Contatti Generali ---
    {
        'id': 'contatti',
        'marker': 'bi-telephone"></i> Contatti Generali',
        'type': 'card',
        'satellite': 'dettaglio/contatti/_content.html',
    },
    # --- 2. Capogruppo ---
    {
        'id': 'capogruppo',
        'marker': '#modalCapogruppo',
        'type': 'card',
        'satellite': 'dettaglio/capogruppo/_content.html',
    },
    # --- 1. Dati Aziendali ---
    {
        'id': 'dati_aziendali',
        'marker': 'bi-building"></i> Dati Aziendali',
        'type': 'card',
        'satellite': 'dettaglio/dati_aziendali/_content.html',
    },
]

# Imposta satellite di default se non specificato
for b in BLOCKS:
    if 'satellite' not in b:
        b['satellite'] = f"dettaglio/{b['id']}/_content.html"


# ==============================================================================
# FUNZIONI DI RICERCA
# ==============================================================================

def find_marker(lines, marker, line_check=None):
    """Trova la riga che contiene il marker. Ritorna l'indice (0-based) o None."""
    for i, line in enumerate(lines):
        if marker.rstrip('\n') in line:
            # Se c'e' un check aggiuntivo sulla riga
            if line_check and line_check not in line:
                continue
            return i
    return None


def find_card_start(lines, from_idx):
    """
    Partendo da from_idx, cammina all'indietro per trovare l'apertura <div class="card...">
    Ritorna l'indice della riga di apertura.
    """
    i = from_idx
    while i >= 0:
        if re.search(r'<div\s+class="card[\s"]', lines[i]):
            return i
        i -= 1
    return None


def find_matching_close_div(lines, start_idx):
    """
    Partendo da start_idx (che contiene un <div>), conta le aperture/chiusure
    div per trovare il </div> corrispondente. Ritorna l'indice.
    """
    depth = 0
    i = start_idx
    while i < len(lines):
        line = lines[i]
        # Conta aperture <div...> (ma non commenti o stringhe)
        opens = len(re.findall(r'<div[\s>]', line))
        closes = len(re.findall(r'</div>', line))
        depth += opens - closes
        if depth == 0 and (opens > 0 or closes > 0):
            return i
        i += 1
    return None


def find_modal_start(lines, modal_id):
    """Trova l'apertura di un modal per id."""
    for i, line in enumerate(lines):
        if f'id="{modal_id}"' in line:
            # Cammina indietro per trovare <div class="modal
            j = i
            while j >= 0:
                if '<div class="modal' in lines[j]:
                    return j
                j -= 1
            return i
    return None


def find_if_wrapper(lines, card_start):
    """
    Verifica se prima di card_start c'e' un {% if %} wrapper.
    Ritorna (if_start, endif_end) oppure None.
    """
    # Cerca {% if %} nelle righe immediatamente precedenti (saltando righe vuote)
    check = card_start - 1
    while check >= 0 and lines[check].strip() == '':
        check -= 1

    if check >= 0 and re.search(r'\{%[-\s]+if\s+', lines[check]):
        if_start = check
        # Ora cerca {% endif %} dopo la card
        card_end = find_matching_close_div(lines, card_start)
        if card_end is None:
            return None
        j = card_end + 1
        while j < len(lines):
            if re.search(r'\{%[-\s]+endif\s*[-]?%\}', lines[j]):
                return (if_start, j)
            # Se troviamo un'altra card o contenuto significativo, stop
            if lines[j].strip() and not lines[j].strip().startswith('{%'):
                break
            j += 1
    return None


def find_conditional_col_boundaries(lines, marker):
    """
    Per il blocco finanziari che ha {% if %}...card...{% else %}...card...{% endif %}
    dentro un <div class="col-md-6">.
    Estrae tutto il contenuto DENTRO il col-md-6 (da {% if %} a {% endif %}).
    """
    marker_idx = find_marker(lines, marker)
    if marker_idx is None:
        return None, None

    # Il marker e' dentro una card che e' dentro un {% if %}
    # Camminiamo indietro per trovare il {% if %} che precede la prima card
    i = marker_idx
    while i >= 0:
        if re.search(r'\{%[-\s]+if\s+', lines[i]):
            break
        i -= 1

    if_start = i

    # Ora cerchiamo {% endif %} andando avanti
    j = marker_idx
    depth_if = 1
    while j < len(lines):
        j += 1
        if j >= len(lines):
            break
        if re.search(r'\{%[-\s]+if\s+', lines[j]):
            depth_if += 1
        if re.search(r'\{%[-\s]+endif\s*[-]?%\}', lines[j]):
            depth_if -= 1
            if depth_if == 0:
                return if_start, j

    return None, None


# ==============================================================================
# FUNZIONE PRINCIPALE DI ESTRAZIONE
# ==============================================================================

def extract_block(lines, block):
    """
    Trova e ritorna (start, end) del blocco da estrarre.
    start e end sono indici 0-based inclusivi.
    """
    bid = block['id']
    btype = block['type']
    marker = block['marker']
    line_check = block.get('marker_line_check')

    if btype == 'card':
        marker_idx = find_marker(lines, marker, line_check)
        if marker_idx is None:
            return None, None, f"Marker non trovato: {marker}"
        card_start = find_card_start(lines, marker_idx)
        if card_start is None:
            return None, None, f"Card start non trovata per {bid}"
        card_end = find_matching_close_div(lines, card_start)
        if card_end is None:
            return None, None, f"Card end non trovata per {bid}"
        return card_start, card_end, None

    elif btype == 'if_card':
        marker_idx = find_marker(lines, marker, line_check)
        if marker_idx is None:
            return None, None, f"Marker non trovato: {marker}"
        card_start = find_card_start(lines, marker_idx)
        if card_start is None:
            return None, None, f"Card start non trovata per {bid}"
        # Cerca if wrapper
        wrapper = find_if_wrapper(lines, card_start)
        if wrapper:
            return wrapper[0], wrapper[1], None
        else:
            # Nessun if wrapper, estrai solo la card
            card_end = find_matching_close_div(lines, card_start)
            if card_end is None:
                return None, None, f"Card end non trovata per {bid}"
            return card_start, card_end, None

    elif btype == 'modal':
        modal_id = block.get('marker')
        # Cerca id="modalStoricoCommerciali"
        modal_start = find_modal_start(lines, 'modalStoricoCommerciali')
        if modal_start is None:
            return None, None, f"Modal non trovato: {bid}"
        modal_end = find_matching_close_div(lines, modal_start)
        if modal_end is None:
            return None, None, f"Modal end non trovato per {bid}"
        return modal_start, modal_end, None

    elif btype == 'conditional_col':
        start, end = find_conditional_col_boundaries(lines, marker)
        if start is None:
            return None, None, f"Blocco condizionale non trovato per {bid}"
        return start, end, None

    return None, None, f"Tipo sconosciuto: {btype}"


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 60)
    print("  MODULARIZZAZIONE DETTAGLIO.HTML - Fase 1")
    print("=" * 60)
    print(f"  Modalita': {'DRY-RUN (anteprima)' if DRY_RUN else 'ESECUZIONE REALE'}")
    print(f"  File: {TEMPLATE_FILE}")
    print()

    # Verifica file
    if not TEMPLATE_FILE.exists():
        print(f"ERRORE: File non trovato: {TEMPLATE_FILE}")
        sys.exit(1)

    # Leggi file
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        original_lines = f.readlines()

    print(f"  File letto: {len(original_lines)} righe")
    print()

    # Fase 1: Analisi - trova tutti i blocchi PRIMA di modificare
    print("-" * 60)
    print("  FASE 1: ANALISI BLOCCHI")
    print("-" * 60)

    extractions = []
    errors = []

    for block in BLOCKS:
        start, end, err = extract_block(original_lines, block)
        if err:
            errors.append(f"  ERRORE {block['id']}: {err}")
            print(f"  ✗ {block['id']:25s} - {err}")
        else:
            num_lines = end - start + 1
            indent = len(original_lines[start]) - len(original_lines[start].lstrip())
            extractions.append({
                'block': block,
                'start': start,
                'end': end,
                'num_lines': num_lines,
                'indent': indent,
            })
            # Mostra info
            first_line_preview = original_lines[start].strip()[:60]
            print(f"  ✓ {block['id']:25s}  righe {start+1:4d}-{end+1:4d} ({num_lines:3d} righe)  [{first_line_preview}...]")

    print()

    if errors:
        print(f"  ATTENZIONE: {len(errors)} errori trovati:")
        for e in errors:
            print(e)
        print()
        if not DRY_RUN:
            print("  Correggi gli errori prima di eseguire. Uscita.")
            sys.exit(1)

    # Verifica sovrapposizioni
    print("-" * 60)
    print("  VERIFICA SOVRAPPOSIZIONI")
    print("-" * 60)
    sorted_ext = sorted(extractions, key=lambda x: x['start'])
    overlaps = False
    for i in range(len(sorted_ext) - 1):
        a = sorted_ext[i]
        b = sorted_ext[i + 1]
        if a['end'] >= b['start']:
            print(f"  ✗ SOVRAPPOSIZIONE: {a['block']['id']} ({a['start']+1}-{a['end']+1}) e {b['block']['id']} ({b['start']+1}-{b['end']+1})")
            overlaps = True
    if not overlaps:
        print(f"  ✓ Nessuna sovrapposizione tra i {len(extractions)} blocchi")
    elif not DRY_RUN:
        print("  ERRORE: Sovrapposizioni trovate. Uscita.")
        sys.exit(1)
    print()

    # Fase 2: Estrazione e sostituzione
    print("-" * 60)
    print(f"  FASE 2: {'ANTEPRIMA ESTRAZIONI' if DRY_RUN else 'ESECUZIONE ESTRAZIONI'}")
    print("-" * 60)

    # Ordina per start DECRESCENTE (dal basso verso l'alto)
    extractions.sort(key=lambda x: x['start'], reverse=True)

    working_lines = list(original_lines)
    created_files = []

    for ext in extractions:
        block = ext['block']
        start = ext['start']
        end = ext['end']
        indent = ext['indent']
        satellite_path = block['satellite']
        full_satellite = TEMPLATES_DIR / satellite_path

        # Estrai le righe
        extracted = working_lines[start:end + 1]

        # Calcola indentazione del satellite (rimuovi indentazione comune)
        min_indent = min(
            (len(line) - len(line.lstrip()) for line in extracted if line.strip()),
            default=0
        )
        # Normalizza: rimuovi l'indentazione comune
        normalized = []
        for line in extracted:
            if line.strip():
                normalized.append(line[min_indent:])
            else:
                normalized.append('\n')

        # Include statement con l'indentazione originale
        include_stmt = ' ' * indent + '{%% include "%s" %%}\n' % satellite_path

        # Mostra anteprima
        print(f"\n  [{block['id']}]")
        print(f"    Righe: {start+1}-{end+1} ({ext['num_lines']} righe)")
        print(f"    Satellite: {satellite_path}")
        print(f"    Include: {include_stmt.rstrip()}")
        print(f"    Prime 3 righe estratte:")
        for k, line in enumerate(normalized[:3]):
            print(f"      | {line.rstrip()}")

        if not DRY_RUN:
            # Crea directory
            full_satellite.parent.mkdir(parents=True, exist_ok=True)

            # Scrivi satellite
            with open(full_satellite, 'w', encoding='utf-8') as f:
                # Header
                f.write(f'{{# ==============================================================================\n')
                f.write(f'   {block["id"].upper().replace("_", " ")} - File satellite (estratto da dettaglio.html)\n')
                f.write(f'   Data estrazione: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
                f.write(f'   Generato da: modularizza_dettaglio.py\n')
                f.write(f'   ============================================================================== #}}\n')
                f.writelines(normalized)

            created_files.append(str(full_satellite))
            print(f"    ✓ Satellite creato")

            # Sostituisci nel file principale
            working_lines[start:end + 1] = [include_stmt]
            print(f"    ✓ Righe sostituite con include")
        else:
            print(f"    [DRY-RUN] Nessuna modifica")

    # Fase 3: Scrivi file modificato
    if not DRY_RUN:
        print()
        print("-" * 60)
        print("  FASE 3: SALVATAGGIO")
        print("-" * 60)

        # Backup
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = BACKUP_DIR / f'templates__dettaglio.html.bak_modularizza_{ts}'
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE_FILE, backup_file)
        print(f"  ✓ Backup: {backup_file}")

        # Scrivi file modificato
        with open(TEMPLATE_FILE, 'w', encoding='utf-8') as f:
            f.writelines(working_lines)
        print(f"  ✓ File modificato: {TEMPLATE_FILE}")
        print(f"    Righe originali: {len(original_lines)}")
        print(f"    Righe finali: {len(working_lines)}")
        print(f"    Righe rimosse: {len(original_lines) - len(working_lines)}")

    # Riepilogo
    print()
    print("=" * 60)
    print("  RIEPILOGO")
    print("=" * 60)
    print(f"  Blocchi analizzati: {len(BLOCKS)}")
    print(f"  Blocchi estratti: {len(extractions)}")
    print(f"  Errori: {len(errors)}")
    if not DRY_RUN:
        print(f"  File satellite creati: {len(created_files)}")
        for f in created_files:
            print(f"    - {f}")
    print()

    if DRY_RUN:
        print("  Per eseguire realmente:")
        print("    python3 scripts/modularizza_dettaglio.py --esegui")
    else:
        print("  Modularizzazione completata!")
        print("  Riavvia il server per verificare:")
        print("    ~/gestione_flotta/scripts/gestione_flotta.sh restart")
    print()


if __name__ == '__main__':
    main()
