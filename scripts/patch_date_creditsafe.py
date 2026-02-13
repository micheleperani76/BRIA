#!/usr/bin/env python3
# ==============================================================================
# PATCH: Fix confronto date import PDF Creditsafe
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Modifica processa_pdf() per NON sovrascrivere dati
#              se il PDF importato e' piu' vecchio di quello gia' nel DB.
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/patch_date_creditsafe.py --dry-run
#   python3 scripts/patch_date_creditsafe.py
# ==============================================================================

import sys
import shutil
from pathlib import Path
from datetime import datetime

TARGET_FILE = Path(__file__).parent.parent / 'app' / 'import_creditsafe.py'

# Testo ORIGINALE da cercare (esatto)
OLD_TEXT = '''    if cliente_esistente:
        # AGGIORNA cliente esistente
        logger.info(f"  ->")
        aggiorna_cliente_da_creditsafe(conn, cliente_esistente['id'], dati, logger)'''

# Testo NUOVO che sostituisce
NEW_TEXT = '''    if cliente_esistente:
        # AGGIORNA cliente esistente - SOLO se report piu' recente o dato vuoto
        data_report_nuova = dati.get('data_report_creditsafe', '')
        data_report_attuale = cliente_esistente['data_report_creditsafe'] if 'data_report_creditsafe' in cliente_esistente.keys() else None

        skip_aggiornamento = False
        if not data_report_attuale or not data_report_nuova:
            # Campo vuoto: aggiorna sempre
            logger.info(f"  -> Aggiornamento (data report mancante nel DB o nel PDF)")
        elif data_report_nuova >= data_report_attuale:
            # Report nuovo e' piu' recente o uguale: aggiorna
            logger.info(f"  -> Aggiornamento (report {data_report_nuova} >= DB {data_report_attuale})")
        else:
            # Report vecchio: NON aggiornare dati, ma archivia comunque il PDF
            logger.info(f"  -> SKIP aggiornamento dati (report {data_report_nuova} < DB {data_report_attuale})")
            logger.info(f"     Il PDF verra' comunque archiviato")
            skip_aggiornamento = True

        if not skip_aggiornamento:
            aggiorna_cliente_da_creditsafe(conn, cliente_esistente['id'], dati, logger)'''


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("  PATCH: Fix confronto date import PDF Creditsafe")
    print("=" * 60)

    if dry_run:
        print("\n  *** MODALITA' DRY-RUN ***\n")

    # Verifica file
    if not TARGET_FILE.exists():
        print(f"ERRORE: File non trovato: {TARGET_FILE}")
        sys.exit(1)

    print(f"  File: {TARGET_FILE}")

    # Leggi contenuto
    contenuto = TARGET_FILE.read_text(encoding='utf-8')

    # Verifica che il testo originale esista
    if OLD_TEXT not in contenuto:
        # Verifica se la patch e' gia' applicata
        if 'skip_aggiornamento' in contenuto:
            print("\n  SKIP: Patch gia' applicata (trovato 'skip_aggiornamento')")
            sys.exit(0)
        else:
            print("\n  ERRORE: Testo originale non trovato nel file!")
            print("  Il file potrebbe essere stato modificato manualmente.")
            print("  Verifica il blocco 'if cliente_esistente:' in processa_pdf()")
            sys.exit(1)

    # Conta occorrenze (deve essere 1)
    occorrenze = contenuto.count(OLD_TEXT)
    print(f"  Occorrenze testo originale: {occorrenze}")

    if occorrenze != 1:
        print(f"  ERRORE: Attesa 1 occorrenza, trovate {occorrenze}")
        sys.exit(1)

    if dry_run:
        print("\n  MODIFICHE PREVISTE:")
        print("  - processa_pdf(): aggiunto confronto data_report_creditsafe")
        print("  - Se PDF piu' vecchio del DB: skip aggiornamento dati")
        print("  - Se PDF piu' recente o data mancante: aggiorna normalmente")
        print("  - Il PDF viene comunque archiviato nella cartella cliente")
        print("\n  Eseguire senza --dry-run per applicare.")
        return

    # Backup
    backup_dir = TARGET_FILE.parent.parent / 'backup'
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"app__import_creditsafe.py.bak_{timestamp}"
    shutil.copy2(str(TARGET_FILE), str(backup_file))
    print(f"  Backup: {backup_file}")

    # Applica patch
    nuovo_contenuto = contenuto.replace(OLD_TEXT, NEW_TEXT)

    # Verifica encoding
    TARGET_FILE.write_text(nuovo_contenuto, encoding='utf-8')

    # Verifica
    verifica = TARGET_FILE.read_text(encoding='utf-8')
    if 'skip_aggiornamento' in verifica and OLD_TEXT not in verifica:
        print("\n  OK - Patch applicata con successo!")
        print("  Modificato: app/import_creditsafe.py")
        print("  Funzione: processa_pdf()")
        print("  Logica: confronto date prima di aggiornare dati cliente")
    else:
        print("\n  ERRORE: Verifica post-patch fallita!")
        print("  Ripristinare dal backup:")
        print(f"  cp {backup_file} {TARGET_FILE}")
        sys.exit(1)


if __name__ == "__main__":
    main()
