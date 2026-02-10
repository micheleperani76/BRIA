#!/usr/bin/env python3
# ==============================================================================
# PATCH - Riquadro Descrizione in dettaglio.html
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-10
# Descrizione: Ridisegna il riquadro "Descrizione" nella pagina cliente
#              aggiungendo: SAE, RAE, ATECO 2007, desc ATECO 2007
#              e migliorando la visualizzazione desc_ateco e desc_attivita
#
# Uso: python3 scripts/patch_riquadro_descrizione.py
# ==============================================================================

import shutil
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================
TARGET = Path(__file__).parent.parent / 'templates' / 'dettaglio.html'

# Blocco VECCHIO da cercare (esattamente come nel file attuale)
BLOCCO_VECCHIO = """                    <div class="card-header py-2">
                        <i class="bi bi-briefcase"></i> Descrizione 
                    </div>
                    <div class="card-body py-2">
                        <div class="row g-2">
                            <div class="col-6">
                                <small class="text-muted">ATECO</small>
                                <div><code>{{ cliente.codice_ateco or '-' }}</code></div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Capitale Sociale</small>
                                <div>{% if cliente.capitale_sociale %}&euro; {{ cliente.capitale_sociale|format_numero }}{% else %}-{% endif %}</div>
                            </div>
                            <div class="col-12">
                                <small class="text-muted">Descrizione ATECO</small>
                                <div>{{ cliente.desc_ateco or '-' }}</div>
                            </div>
                            <div class="col-12">
                                <small class="text-muted">Descrizione </small>
                                <div>{{ cliente.desc_attivita or '-' }}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Dipendenti</small>
                                <div>{{ cliente.dipendenti or '-' }}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Stato</small>
                                <div>{% if cliente.stato %}<span class="badge {% if 'Attiv' in cliente.stato %}bg-success{% else %}bg-warning{% endif %}">{{ cliente.stato }}</span>{% else %}-{% endif %}</div>
                            </div>
                        </div>
                    </div>"""

# Blocco NUOVO
BLOCCO_NUOVO = """                    <div class="card-header py-2">
                        <i class="bi bi-briefcase"></i> Descrizione 
                    </div>
                    <div class="card-body py-2">
                        <div class="row g-2">
                            {# --- Riga 1: ATECO primario + Capitale Sociale --- #}
                            <div class="col-6">
                                <small class="text-muted">ATECO</small>
                                <div><code>{{ cliente.codice_ateco or '-' }}</code></div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Capitale Sociale</small>
                                <div>{% if cliente.capitale_sociale %}&euro; {{ cliente.capitale_sociale|format_numero }}{% else %}-{% endif %}</div>
                            </div>
                            {# --- Riga 2: Descrizione ATECO (testo completo) --- #}
                            <div class="col-12">
                                <small class="text-muted">Descrizione ATECO</small>
                                <div>{{ cliente.desc_ateco or '-' }}</div>
                            </div>
                            {# --- Riga 3: SAE + RAE --- #}
                            {% if cliente.codice_sae or cliente.codice_rae %}
                            <div class="col-6">
                                <small class="text-muted">Codice SAE</small>
                                <div><code>{{ cliente.codice_sae or '-' }}</code></div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Codice RAE</small>
                                <div><code>{{ cliente.codice_rae or '-' }}</code></div>
                            </div>
                            {% endif %}
                            {# --- Riga 4: ATECO 2007 (opzionale, solo se presente) --- #}
                            {% if cliente.codice_ateco_2007 %}
                            <div class="col-12">
                                <small class="text-muted">ATECO 2007</small>
                                <div><code>{{ cliente.codice_ateco_2007 }}</code> <span class="text-muted">{{ cliente.desc_ateco_2007 or '' }}</span></div>
                            </div>
                            {% endif %}
                            {# --- Riga 5: Descrizione attivita svolta (testo completo) --- #}
                            <div class="col-12">
                                <small class="text-muted">Descrizione attivit&agrave;</small>
                                <div>{{ cliente.desc_attivita or '-' }}</div>
                            </div>
                            {# --- Riga 6: Dipendenti + Stato --- #}
                            <div class="col-6">
                                <small class="text-muted">Dipendenti</small>
                                <div>{{ cliente.dipendenti or '-' }}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Stato</small>
                                <div>{% if cliente.stato %}<span class="badge {% if 'Attiv' in cliente.stato %}bg-success{% else %}bg-warning{% endif %}">{{ cliente.stato }}</span>{% else %}-{% endif %}</div>
                            </div>
                        </div>
                    </div>"""

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print("=" * 60)
    print("  PATCH - Riquadro Descrizione")
    print("=" * 60)
    print(f"  File: {TARGET}")
    print()

    if not TARGET.exists():
        print(f"ERRORE: File non trovato: {TARGET}")
        return False

    # Backup
    backup = TARGET.with_suffix('.html.bak.ateco')
    shutil.copy(str(TARGET), str(backup))
    print(f"  [1/3] Backup -> {backup.name}")

    # Leggi contenuto
    contenuto = TARGET.read_text(encoding='utf-8')

    # Verifica blocco vecchio presente
    if BLOCCO_VECCHIO not in contenuto:
        print("  [2/3] ERRORE: Blocco originale non trovato!")
        print("         Il template potrebbe essere stato gia modificato.")
        print("         Verificare manualmente.")
        return False

    # Verifica non gia patchato
    if 'codice_sae' in contenuto:
        print("  [2/3] SKIP - Patch gia applicata (codice_sae gia presente)")
        return True

    print("  [2/3] Blocco originale trovato")

    # Sostituisci
    contenuto_nuovo = contenuto.replace(BLOCCO_VECCHIO, BLOCCO_NUOVO)

    if contenuto_nuovo == contenuto:
        print("  [3/3] ERRORE: Sostituzione non avvenuta!")
        return False

    TARGET.write_text(contenuto_nuovo, encoding='utf-8')
    print("  [3/3] Riquadro Descrizione aggiornato")

    print()
    print("  Nuovi campi visualizzati:")
    print("    - Codice SAE / Codice RAE (se presenti)")
    print("    - ATECO 2007 + descrizione (se presente)")
    print("    - Descrizione attivita (testo completo)")
    print()
    print(f"  Backup in: {backup.name}")
    print("=" * 60)
    return True

if __name__ == '__main__':
    main()
