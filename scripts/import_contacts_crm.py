#!/usr/bin/env python3
# ==============================================================================
# IMPORT CONTACTS CRM ZOHO -> GESTIONE FLOTTA (REFERENTI)
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Importa referenti aziendali dal CSV Contacts Zoho CRM
#
# LOGICA:
#   - Match per Nome Azienda.id -> clienti.crm_id -> cliente_id
#   - Dedup per nome+cognome+cliente_id (no duplicati)
#   - Aggiorna campi vuoti se referente gia' presente
#   - NON sovrascrive: note manuali, ruolo modificato manualmente
#
# PREREQUISITI:
#   - Import Accounts deve essere gia' stato eseguito (clienti con crm_id)
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/import_contacts_crm.py import_dati/Contacts_XXXX.csv --dry-run
#   python3 scripts/import_contacts_crm.py import_dati/Contacts_XXXX.csv
#
# ==============================================================================

import csv
import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
if SCRIPT_DIR.name == 'scripts':
    BASE_DIR = SCRIPT_DIR.parent
else:
    BASE_DIR = SCRIPT_DIR

DB_FILE = BASE_DIR / 'db' / 'gestionale.db'
LOG_DIR = BASE_DIR / 'logs'
BACKUP_DIR = BASE_DIR / 'backup'

# Mapping CSV -> DB
CAMPO_NOME = 'Nome'
CAMPO_COGNOME = 'Cognome'
CAMPO_EMAIL = 'E-mail'
CAMPO_CELLULARE = 'Cellulare'
CAMPO_TELEFONO = 'Telefono'
CAMPO_AZIENDA_ID = 'Nome Azienda.id'
CAMPO_AZIENDA_NOME = 'Nome Azienda'
CAMPO_RUOLO = 'Ruolo in azienda'
CAMPO_CRM_ID = 'ID record'


# ==============================================================================
# NORMALIZZAZIONE
# ==============================================================================

def normalizza_chiavi_csv(righe):
    """
    Normalizza chiavi CSV per gestire corruzioni accenti via Chromium.
    """
    if not righe:
        return righe

    chiavi_originali = list(righe[0].keys())
    mappa = {}

    # Mapping accenti corrotti -> puliti
    correzioni = {
        'Attivit': 'Attivit',
        'Propriet': 'Propriet',
        'Citt': 'Citt',
    }

    for chiave in chiavi_originali:
        pulita = chiave
        for corrotta, corretta in correzioni.items():
            if corrotta in chiave:
                pulita = chiave
                break
        mappa[chiave] = pulita

    # Se non serve normalizzare, ritorna cosi' com'e'
    if all(k == v for k, v in mappa.items()):
        return righe

    righe_pulite = []
    for riga in righe:
        nuova = {}
        for chiave, valore in riga.items():
            nuova[mappa.get(chiave, chiave)] = valore
        righe_pulite.append(nuova)

    return righe_pulite


def pulisci_telefono(valore):
    """Pulisce numero di telefono."""
    if not valore:
        return None
    v = str(valore).strip()
    if not v:
        return None
    return v


def pulisci_testo(valore):
    """Pulisce testo generico."""
    if not valore:
        return None
    v = str(valore).strip()
    return v if v else None


# ==============================================================================
# IMPORT PRINCIPALE
# ==============================================================================

def importa_contacts(csv_path, dry_run=False):
    """
    Funzione principale di import Contacts CRM.

    Args:
        csv_path: Path al file CSV
        dry_run: Se True, non modifica il DB

    Returns:
        dict: statistiche import
    """
    stats = {
        'totale_csv': 0,
        'referenti_inseriti': 0,
        'referenti_aggiornati': 0,
        'referenti_duplicati': 0,
        'aziende_non_trovate': 0,
        'errori': 0,
        'dettaglio_inseriti': [],
        'dettaglio_aggiornati': [],
        'dettaglio_non_trovate': [],
        'dettaglio_errori': [],
    }

    # Leggi CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        righe = list(reader)

    stats['totale_csv'] = len(righe)
    print(f"\n  Record CSV letti: {stats['totale_csv']}")

    # Normalizza chiavi
    righe = normalizza_chiavi_csv(righe)

    # Connessione DB
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        for i, row in enumerate(righe, 1):
            nome = pulisci_testo(row.get(CAMPO_NOME, ''))
            cognome = pulisci_testo(row.get(CAMPO_COGNOME, ''))
            azienda_crm_id = pulisci_testo(row.get(CAMPO_AZIENDA_ID, ''))
            azienda_nome = pulisci_testo(row.get(CAMPO_AZIENDA_NOME, ''))

            # Skip righe senza nome o cognome
            if not nome and not cognome:
                stats['errori'] += 1
                stats['dettaglio_errori'].append(
                    f"Riga {i}: nome e cognome vuoti")
                continue

            # Skip righe senza azienda
            if not azienda_crm_id:
                stats['errori'] += 1
                stats['dettaglio_errori'].append(
                    f"Riga {i}: {nome} {cognome} - azienda CRM ID vuoto")
                continue

            # Cerca cliente per crm_id
            cursor.execute(
                "SELECT id, ragione_sociale FROM clienti WHERE crm_id = ?",
                (azienda_crm_id,))
            cliente = cursor.fetchone()

            if not cliente:
                stats['aziende_non_trovate'] += 1
                stats['dettaglio_non_trovate'].append(
                    f"{nome} {cognome} -> {azienda_nome} ({azienda_crm_id})")
                continue

            cliente_id = cliente['id']
            ragione_sociale = cliente['ragione_sociale'] or azienda_nome

            # Prepara dati referente
            email = pulisci_testo(row.get(CAMPO_EMAIL, ''))
            cellulare = pulisci_telefono(row.get(CAMPO_CELLULARE, ''))
            telefono = pulisci_telefono(row.get(CAMPO_TELEFONO, ''))
            ruolo = pulisci_testo(row.get(CAMPO_RUOLO, ''))

            # Dedup: cerca referente gia' presente (nome+cognome+cliente_id)
            cursor.execute("""
                SELECT id, email_principale, cellulare, telefono, ruolo
                FROM referenti_clienti
                WHERE cliente_id = ?
                  AND UPPER(COALESCE(nome,'')) = UPPER(?)
                  AND UPPER(COALESCE(cognome,'')) = UPPER(?)
            """, (cliente_id, nome or '', cognome or ''))
            esistente = cursor.fetchone()

            if esistente:
                # Aggiorna solo campi vuoti nel DB
                aggiornamenti = []
                valori = []

                if email and not esistente['email_principale']:
                    aggiornamenti.append("email_principale = ?")
                    valori.append(email)
                if cellulare and not esistente['cellulare']:
                    aggiornamenti.append("cellulare = ?")
                    valori.append(cellulare)
                if telefono and not esistente['telefono']:
                    aggiornamenti.append("telefono = ?")
                    valori.append(telefono)
                if ruolo and not esistente['ruolo']:
                    aggiornamenti.append("ruolo = ?")
                    valori.append(ruolo)

                if aggiornamenti:
                    aggiornamenti.append("data_modifica = ?")
                    valori.append(now)
                    valori.append(esistente['id'])

                    if not dry_run:
                        query = f"UPDATE referenti_clienti SET {', '.join(aggiornamenti)} WHERE id = ?"
                        cursor.execute(query, valori)

                    stats['referenti_aggiornati'] += 1
                    campi_agg = [a.split(' =')[0] for a in aggiornamenti if a != 'data_modifica = ?']
                    stats['dettaglio_aggiornati'].append(
                        f"{nome} {cognome} [{ragione_sociale}] campi: {', '.join(campi_agg)}")
                else:
                    stats['referenti_duplicati'] += 1
            else:
                # Inserisci nuovo referente
                if not dry_run:
                    cursor.execute("""
                        INSERT INTO referenti_clienti
                        (cliente_id, nome, cognome, email_principale, cellulare,
                         telefono, ruolo, note, data_creazione)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (cliente_id, nome, cognome, email, cellulare,
                          telefono, ruolo or 'Referente',
                          'Import da CRM Contacts', now))

                stats['referenti_inseriti'] += 1
                stats['dettaglio_inseriti'].append(
                    f"{nome} {cognome} [{ragione_sociale}] ruolo={ruolo or 'Referente'}")

        if not dry_run:
            conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"\n  ERRORE: {e}")
        raise
    finally:
        conn.close()

    return stats


# ==============================================================================
# STAMPA RISULTATI
# ==============================================================================

def stampa_risultati(stats, dry_run=False):
    """Stampa riepilogo import."""
    modalita = "DRY-RUN" if dry_run else "IMPORT"

    print(f"\n  {'=' * 50}")
    print(f"  RISULTATO {modalita}")
    print(f"  {'=' * 50}")
    print(f"  Record CSV:           {stats['totale_csv']}")
    print(f"  Referenti inseriti:   {stats['referenti_inseriti']}")
    print(f"  Referenti aggiornati: {stats['referenti_aggiornati']}")
    print(f"  Duplicati (skip):     {stats['referenti_duplicati']}")
    print(f"  Aziende non trovate:  {stats['aziende_non_trovate']}")
    print(f"  Errori:               {stats['errori']}")

    if stats['dettaglio_inseriti']:
        print(f"\n  --- Inseriti ---")
        for d in stats['dettaglio_inseriti'][:20]:
            print(f"    + {d}")
        if len(stats['dettaglio_inseriti']) > 20:
            print(f"    ... e altri {len(stats['dettaglio_inseriti']) - 20}")

    if stats['dettaglio_aggiornati']:
        print(f"\n  --- Aggiornati ---")
        for d in stats['dettaglio_aggiornati'][:20]:
            print(f"    ~ {d}")

    if stats['dettaglio_non_trovate']:
        print(f"\n  --- Aziende non trovate ---")
        for d in stats['dettaglio_non_trovate'][:10]:
            print(f"    ? {d}")

    if stats['dettaglio_errori']:
        print(f"\n  --- Errori ---")
        for d in stats['dettaglio_errori'][:10]:
            print(f"    ! {d}")

    print(f"\n  {'=' * 50}")
    if dry_run:
        print("  Per eseguire l'import reale, rilanciare senza --dry-run")
    else:
        print("  Import completato e committato nel database.")


# ==============================================================================
# SALVA LOG
# ==============================================================================

def salva_log(stats, csv_path, dry_run=False):
    """Salva log import su file."""
    LOG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    modalita = 'dryrun' if dry_run else 'import'
    log_file = LOG_DIR / f"import_contacts_{modalita}_{timestamp}.log"

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Import Contacts CRM - {'DRY-RUN' if dry_run else 'ESECUZIONE'}\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"File: {csv_path}\n")
        f.write(f"{'=' * 60}\n\n")
        f.write(f"Record CSV:           {stats['totale_csv']}\n")
        f.write(f"Referenti inseriti:   {stats['referenti_inseriti']}\n")
        f.write(f"Referenti aggiornati: {stats['referenti_aggiornati']}\n")
        f.write(f"Duplicati (skip):     {stats['referenti_duplicati']}\n")
        f.write(f"Aziende non trovate:  {stats['aziende_non_trovate']}\n")
        f.write(f"Errori:               {stats['errori']}\n\n")

        if stats['dettaglio_inseriti']:
            f.write("--- Referenti INSERITI ---\n")
            for d in stats['dettaglio_inseriti']:
                f.write(f"  + {d}\n")
            f.write('\n')

        if stats['dettaglio_aggiornati']:
            f.write("--- Referenti AGGIORNATI ---\n")
            for d in stats['dettaglio_aggiornati']:
                f.write(f"  ~ {d}\n")
            f.write('\n')

        if stats['dettaglio_non_trovate']:
            f.write("--- Aziende NON TROVATE ---\n")
            for d in stats['dettaglio_non_trovate']:
                f.write(f"  ? {d}\n")
            f.write('\n')

        if stats['dettaglio_errori']:
            f.write("--- ERRORI ---\n")
            for d in stats['dettaglio_errori']:
                f.write(f"  ! {d}\n")

    print(f"  Log salvato: {log_file}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/import_contacts_crm.py <file.csv> [--dry-run]")
        print()
        print("Esempio:")
        print("  python3 scripts/import_contacts_crm.py import_dati/Contacts_2026_02_13.csv --dry-run")
        print("  python3 scripts/import_contacts_crm.py import_dati/Contacts_2026_02_13.csv")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("IMPORT CONTACTS CRM ZOHO (REFERENTI)")
    print("=" * 60)
    print(f"  File CSV:  {csv_path}")
    print(f"  Database:  {DB_FILE}")
    print(f"  Data:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'IMPORT REALE'}")

    # Verifica file
    if not csv_path.exists():
        print(f"\n  ERRORE: File non trovato: {csv_path}")
        sys.exit(1)

    if not DB_FILE.exists():
        print(f"\n  ERRORE: Database non trovato: {DB_FILE}")
        sys.exit(1)

    # Backup DB (solo in modalita' reale)
    if not dry_run:
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = BACKUP_DIR / f"gestionale.db.bak_contacts_{timestamp}"
        shutil.copy2(str(DB_FILE), str(backup_file))
        print(f"  Backup DB: {backup_file.name}")

    # Import
    stats = importa_contacts(str(csv_path), dry_run=dry_run)

    # Risultati
    stampa_risultati(stats, dry_run)

    # Log
    salva_log(stats, csv_path, dry_run)


if __name__ == '__main__':
    main()
