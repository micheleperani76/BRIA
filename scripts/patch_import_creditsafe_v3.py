#!/usr/bin/env python3
# ==============================================================================
# PATCH v2: Import PDF Creditsafe - Nuova logica scarto/eliminazione
# ==============================================================================
# Versione: 2.0.0
# Data: 2026-02-13
# Descrizione: Modifica processa_pdf() in import_creditsafe.py
#
# MODIFICHE:
#   1. Aggiunge ricerca fallback per codice fiscale (oltre a P.IVA)
#   2. Se nessuna corrispondenza P.IVA/CF in DB -> ELIMINA PDF (no insert)
#   3. Se report PDF piu' vecchio di quello in DB -> ELIMINA PDF (no archiviazione)
#
# FIX v2: corretto check "gia' applicata" che dava falsi positivi in v1
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/patch_import_creditsafe_v3.py --dry-run
#   python3 scripts/patch_import_creditsafe_v3.py
# ==============================================================================

import sys
import shutil
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
if SCRIPT_DIR.name == 'scripts':
    BASE_DIR = SCRIPT_DIR.parent
else:
    BASE_DIR = SCRIPT_DIR

TARGET_FILE = BASE_DIR / 'app' / 'import_creditsafe.py'
BACKUP_DIR = BASE_DIR / 'backup'
NOW = datetime.now().strftime('%Y%m%d_%H%M%S')


def log(msg, livello='INFO'):
    simboli = {'INFO': ' ', 'OK': '+', 'ERR': '!', 'SKIP': '-', 'WARN': '?'}
    s = simboli.get(livello, ' ')
    print(f"  [{s}] {msg}")


def backup_file(filepath):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rel = str(filepath.relative_to(BASE_DIR)).replace('/', '__')
    dest = BACKUP_DIR / f"{rel}.bak_{NOW}"
    shutil.copy2(filepath, dest)
    log(f"Backup: {dest.name}", 'OK')
    return dest


# ==============================================================================
# PATCH 1: Aggiunge ricerca fallback per codice fiscale
# ==============================================================================

PATCH1_OLD = """    # Cerca cliente esistente per P.IVA
    cliente_esistente = None
    if dati.get('p_iva'):
        cliente_esistente = cerca_cliente_per_piva(conn, dati['p_iva'])
    
    if cliente_esistente:"""

PATCH1_NEW = """    # Cerca cliente esistente per P.IVA o Codice Fiscale
    cliente_esistente = None
    if dati.get('p_iva'):
        cliente_esistente = cerca_cliente_per_piva(conn, dati['p_iva'])
    if not cliente_esistente and dati.get('cod_fiscale'):
        # Fallback: cerca per codice fiscale
        cursor_cf = conn.cursor()
        cursor_cf.execute('SELECT * FROM clienti WHERE cod_fiscale = ?', (dati['cod_fiscale'],))
        cliente_esistente = cursor_cf.fetchone()
        if cliente_esistente:
            logger.info(f"  -> Trovato per CF: {dati['cod_fiscale']}")
    
    if cliente_esistente:"""

PATCH1_CHECK = "Fallback: cerca per codice fiscale"


# ==============================================================================
# PATCH 2: Blocco "INSERISCI nuovo cliente" -> SCARTA
# ==============================================================================

PATCH2_OLD = """    else:
        # INSERISCI nuovo cliente
        logger.info(f"  ->")
        cliente_id = inserisci_cliente(conn, dati, origine='creditsafe')
        logger.info(f"  ->")
    
    
    # NUOVA STRUTTURA: Salva PDF nella cartella creditsafe del cliente"""

PATCH2_NEW = """    else:
        # NESSUNA CORRISPONDENZA P.IVA/CF: elimina PDF senza creare cliente
        logger.info(f"  -> SCARTATO: nessuna corrispondenza P.IVA/CF in database")
        logger.info(f"     P.IVA: {dati.get('p_iva', 'N/D')} CF: {dati.get('cod_fiscale', 'N/D')}")
        logger.info(f"     PDF eliminato dalla coda di importazione")
        return True
    
    
    # NUOVA STRUTTURA: Salva PDF nella cartella creditsafe del cliente"""

PATCH2_CHECK = "NESSUNA CORRISPONDENZA"


# ==============================================================================
# PATCH 3: Report vecchio -> SCARTA (non archiviare)
# ==============================================================================

PATCH3_OLD = """        else:
            # Report vecchio: NON aggiornare dati, ma archivia comunque il PDF
            logger.info(f"  -> SKIP aggiornamento dati (report {data_report_nuova} < DB {data_report_attuale})")
            logger.info(f"     Il PDF viene comunque archiviato")"""

PATCH3_NEW = """        else:
            # Report vecchio: NON aggiornare, ELIMINA PDF
            logger.info(f"  -> SCARTATO: report PDF ({data_report_nuova}) piu' vecchio del DB ({data_report_attuale})")
            logger.info(f"     PDF eliminato, dati non aggiornati")
            return True"""

PATCH3_CHECK = "SCARTATO: report PDF"


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("  PATCH v2: Import Creditsafe - Logica scarto/eliminazione")
    print("=" * 60)
    print(f"  File: {TARGET_FILE}")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if dry_run:
        print("\n  *** MODALITA' DRY-RUN: nessuna modifica ***\n")
    print()

    # --- Verifica file ---
    if not TARGET_FILE.exists():
        log(f"File non trovato: {TARGET_FILE}", 'ERR')
        sys.exit(1)

    # --- Leggi contenuto ---
    contenuto = TARGET_FILE.read_text(encoding='utf-8')
    contenuto_originale = contenuto
    log(f"File letto: {len(contenuto)} caratteri, {contenuto.count(chr(10))} righe", 'INFO')

    patches = [
        ("PATCH 1: Ricerca fallback CF",       PATCH1_OLD, PATCH1_NEW, PATCH1_CHECK),
        ("PATCH 2: No match -> SCARTA PDF",    PATCH2_OLD, PATCH2_NEW, PATCH2_CHECK),
        ("PATCH 3: Report vecchio -> SCARTA",  PATCH3_OLD, PATCH3_NEW, PATCH3_CHECK),
    ]

    modifiche = 0
    errori = 0

    for nome, old, new, check in patches:
        print(f"\n--- {nome} ---")

        # Check gia' applicata (usa stringa SPECIFICA della patch)
        if check in contenuto:
            log(f"Gia' applicata (trovato '{check}')", 'SKIP')
            modifiche += 1
            continue

        # Cerca blocco originale
        if old not in contenuto:
            log(f"Blocco originale NON trovato!", 'ERR')
            # Mostra prima riga del blocco cercato per debug
            prima_riga = old.strip().split('\n')[0].strip()
            log(f"Cercavo: '{prima_riga}'", 'INFO')
            errori += 1
            continue

        count = contenuto.count(old)
        if count > 1:
            log(f"Blocco trovato {count} volte (attesa 1)!", 'ERR')
            errori += 1
            continue

        contenuto = contenuto.replace(old, new)
        log(f"Applicata", 'OK')
        modifiche += 1

    # ==================================================================
    # RIEPILOGO
    # ==================================================================
    print(f"\n{'=' * 60}")
    print(f"  RIEPILOGO: {modifiche} patch OK, {errori} errori")
    print(f"{'=' * 60}")

    if errori > 0:
        log(f"{errori} patch fallite - il file NON e' stato modificato", 'ERR')
        sys.exit(1)

    if contenuto == contenuto_originale:
        log("Nessuna modifica necessaria (tutte le patch gia' applicate)", 'SKIP')
        sys.exit(0)

    if dry_run:
        print("\n  MODIFICHE CHE VERRANNO APPLICATE:")
        if PATCH1_CHECK not in contenuto_originale:
            print("  1. Ricerca cliente anche per codice fiscale (fallback dopo P.IVA)")
        if PATCH2_CHECK not in contenuto_originale:
            print("  2. PDF senza corrispondenza P.IVA/CF -> eliminato (no insert)")
        if PATCH3_CHECK not in contenuto_originale:
            print("  3. PDF con data piu' vecchia -> eliminato (no archiviazione)")
        print(f"\n  Eseguire senza --dry-run per applicare.")
        return

    # --- Backup ---
    print()
    backup_path = backup_file(TARGET_FILE)

    # --- Applica ---
    TARGET_FILE.write_text(contenuto, encoding='utf-8')
    log("File scritto", 'OK')

    # --- Verifica post-applicazione ---
    print("\n--- VERIFICA POST-APPLICAZIONE ---")
    verifica = TARGET_FILE.read_text(encoding='utf-8')

    checks = [
        ('Ricerca CF fallback',               PATCH1_CHECK in verifica),
        ('Blocco SCARTATO (no match)',         PATCH2_CHECK in verifica),
        ('Blocco SCARTATO (report vecchio)',   PATCH3_CHECK in verifica),
        ('Funzione processa_pdf esiste',       'def processa_pdf(' in verifica),
        ('Funzione importa_tutti_pdf esiste',  'def importa_tutti_pdf(' in verifica),
        ('Funzione estrai_dati_azienda esiste','def estrai_dati_azienda(' in verifica),
        ('Import shutil presente',             'import shutil' in verifica),
        ('Regex data report presente',         'Richiesto' in verifica),
    ]

    # Check speciale: inserisci_cliente NON deve essere in processa_pdf
    idx_processa = verifica.find('def processa_pdf(')
    idx_importa = verifica.find('\ndef importa_tutti_pdf(')
    if idx_processa >= 0 and idx_importa >= 0:
        blocco = verifica[idx_processa:idx_importa]
        checks.append(('No inserisci_cliente in processa_pdf', 'inserisci_cliente' not in blocco))

    tutti_ok = True
    for nome_check, risultato in checks:
        if risultato:
            log(f"PASS: {nome_check}", 'OK')
        else:
            log(f"FAIL: {nome_check}", 'ERR')
            tutti_ok = False

    if tutti_ok:
        print(f"\n  {'=' * 56}")
        print(f"  PATCH APPLICATA CON SUCCESSO!")
        print(f"  {'=' * 56}")
        print(f"  Backup: {backup_path.name}")
        print(f"\n  Prossimo passo:")
        print(f"    ~/gestione_flotta/scripts/gestione_flotta.sh restart")
    else:
        log("VERIFICA FALLITA! Ripristinare dal backup:", 'ERR')
        print(f"    cp {backup_path} {TARGET_FILE}")
        sys.exit(1)


if __name__ == '__main__':
    main()
