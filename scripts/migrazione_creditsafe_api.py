#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DATABASE - Creditsafe API Monitoring
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Descrizione: Prepara il database per l'integrazione con Creditsafe API
#
# OPERAZIONI:
# 1. ALTER TABLE clienti: aggiunge connect_id + creditsafe_api_sync_at
# 2. ALTER TABLE clienti_creditsafe_alert: aggiunge colonne per eventi API
# 3. Creazione indici per performance
# 4. Verifica finale
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/migrazione_creditsafe_api.py --dry-run    # Solo verifica
#   python3 scripts/migrazione_creditsafe_api.py               # Esegue migrazione
#
# ==============================================================================

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

# ==============================================================================
# DEFINIZIONI MIGRAZIONE
# ==============================================================================

# Nuovi campi tabella clienti
CAMPI_CLIENTI = [
    ('connect_id',               'TEXT'),       # ID univoco Creditsafe (es: IT001-X-12345678901)
    ('creditsafe_api_sync_at',   'TEXT'),       # Data ultima sincronizzazione API
    ('creditsafe_portfolio_ref', 'TEXT'),       # Riferimento interno nel portfolio
]

# Nuovi campi tabella clienti_creditsafe_alert (per eventi API)
CAMPI_ALERT = [
    ('connect_id',       'TEXT'),               # ID Creditsafe azienda
    ('event_id',         'TEXT'),               # ID univoco evento Creditsafe
    ('event_date',       'TEXT'),               # Data evento
    ('rule_code',        'INTEGER'),            # Codice regola (1801, 1802, 3054...)
    ('rule_description', 'TEXT'),               # Descrizione regola
    ('old_value',        'TEXT'),               # Valore precedente
    ('new_value',        'TEXT'),               # Valore nuovo
    ('is_processed',     'INTEGER DEFAULT 0'),  # 0=da gestire, 1=gestito
    ('processed_at',     'TEXT'),               # Data gestione
    ('processed_by_id',  'INTEGER'),            # Utente che ha gestito
]

# Indici da creare
INDICI = [
    ('idx_clienti_connect_id',      'clienti',                  'connect_id'),
    ('idx_alert_connect_id',        'clienti_creditsafe_alert', 'connect_id'),
    ('idx_alert_event_id',          'clienti_creditsafe_alert', 'event_id'),
    ('idx_alert_rule_code',         'clienti_creditsafe_alert', 'rule_code'),
    ('idx_alert_is_processed',      'clienti_creditsafe_alert', 'is_processed'),
    ('idx_alert_event_date',        'clienti_creditsafe_alert', 'event_date'),
]


# ==============================================================================
# UTILITY
# ==============================================================================

def log(msg, livello='INFO'):
    """Stampa messaggio con livello."""
    print(f"  [{livello}] {msg}")


def colonna_esiste(conn, tabella, colonna):
    """Verifica se una colonna esiste in una tabella."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabella})")
    colonne = [row[1] for row in cursor.fetchall()]
    return colonna in colonne


def tabella_esiste(conn, tabella):
    """Verifica se una tabella esiste."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (tabella,))
    return cursor.fetchone() is not None


def indice_esiste(conn, nome_indice):
    """Verifica se un indice esiste."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name=?
    """, (nome_indice,))
    return cursor.fetchone() is not None


# ==============================================================================
# STEP 1: COLONNE TABELLA CLIENTI
# ==============================================================================

def step1_alter_clienti(conn, dry_run=False):
    """Aggiunge colonne API Creditsafe alla tabella clienti."""
    print("\n" + "=" * 60)
    print("[STEP 1] ALTER TABLE clienti - Colonne Creditsafe API")
    print("=" * 60)

    cursor = conn.cursor()
    aggiunti = 0
    skippati = 0

    for campo, tipo in CAMPI_CLIENTI:
        if colonna_esiste(conn, 'clienti', campo):
            log(f"{campo} ({tipo}) - gia' presente", 'SKIP')
            skippati += 1
        else:
            if dry_run:
                log(f"{campo} ({tipo}) - DA AGGIUNGERE", 'DRY')
            else:
                cursor.execute(f"ALTER TABLE clienti ADD COLUMN {campo} {tipo}")
                log(f"{campo} ({tipo}) - aggiunto", 'OK')
            aggiunti += 1

    if not dry_run and aggiunti > 0:
        conn.commit()

    print(f"\n  Risultato: {aggiunti} da aggiungere, {skippati} gia' presenti")
    return aggiunti


# ==============================================================================
# STEP 2: COLONNE TABELLA ALERT
# ==============================================================================

def step2_alter_alert(conn, dry_run=False):
    """Aggiunge colonne eventi API alla tabella clienti_creditsafe_alert."""
    print("\n" + "=" * 60)
    print("[STEP 2] ALTER TABLE clienti_creditsafe_alert - Colonne eventi API")
    print("=" * 60)

    cursor = conn.cursor()

    # Verifica che la tabella esista
    if not tabella_esiste(conn, 'clienti_creditsafe_alert'):
        log("ERRORE: tabella clienti_creditsafe_alert non trovata!", 'ERR')
        log("Eseguire prima migrazione_crm_zoho.py", 'ERR')
        return -1

    aggiunti = 0
    skippati = 0

    for campo, tipo in CAMPI_ALERT:
        # Estrai nome campo senza DEFAULT
        nome_campo = campo.strip()
        if colonna_esiste(conn, 'clienti_creditsafe_alert', nome_campo):
            log(f"{nome_campo} ({tipo}) - gia' presente", 'SKIP')
            skippati += 1
        else:
            if dry_run:
                log(f"{nome_campo} ({tipo}) - DA AGGIUNGERE", 'DRY')
            else:
                cursor.execute(f"ALTER TABLE clienti_creditsafe_alert ADD COLUMN {nome_campo} {tipo}")
                log(f"{nome_campo} ({tipo}) - aggiunto", 'OK')
            aggiunti += 1

    if not dry_run and aggiunti > 0:
        conn.commit()

    print(f"\n  Risultato: {aggiunti} da aggiungere, {skippati} gia' presenti")
    return aggiunti


# ==============================================================================
# STEP 3: INDICI
# ==============================================================================

def step3_indici(conn, dry_run=False):
    """Crea indici per performance query API."""
    print("\n" + "=" * 60)
    print("[STEP 3] Creazione indici Creditsafe API")
    print("=" * 60)

    cursor = conn.cursor()
    creati = 0
    skippati = 0

    for nome_indice, tabella, colonna in INDICI:
        if indice_esiste(conn, nome_indice):
            log(f"{nome_indice} su {tabella}.{colonna} - gia' presente", 'SKIP')
            skippati += 1
        else:
            if dry_run:
                log(f"{nome_indice} su {tabella}.{colonna} - DA CREARE", 'DRY')
            else:
                cursor.execute(f"CREATE INDEX {nome_indice} ON {tabella}({colonna})")
                log(f"{nome_indice} su {tabella}.{colonna} - creato", 'OK')
            creati += 1

    if not dry_run and creati > 0:
        conn.commit()

    print(f"\n  Risultato: {creati} da creare, {skippati} gia' presenti")
    return creati


# ==============================================================================
# STEP 4: VERIFICA FINALE
# ==============================================================================

def step4_verifica(conn):
    """Verifica che tutte le colonne e indici siano presenti."""
    print("\n" + "=" * 60)
    print("[STEP 4] Verifica finale")
    print("=" * 60)

    errori = 0

    # Verifica colonne clienti
    for campo, _ in CAMPI_CLIENTI:
        if colonna_esiste(conn, 'clienti', campo):
            log(f"clienti.{campo} - OK", 'OK')
        else:
            log(f"clienti.{campo} - MANCANTE!", 'ERR')
            errori += 1

    # Verifica colonne alert
    for campo, _ in CAMPI_ALERT:
        nome_campo = campo.strip()
        if colonna_esiste(conn, 'clienti_creditsafe_alert', nome_campo):
            log(f"clienti_creditsafe_alert.{nome_campo} - OK", 'OK')
        else:
            log(f"clienti_creditsafe_alert.{nome_campo} - MANCANTE!", 'ERR')
            errori += 1

    # Verifica indici
    for nome_indice, _, _ in INDICI:
        if indice_esiste(conn, nome_indice):
            log(f"indice {nome_indice} - OK", 'OK')
        else:
            log(f"indice {nome_indice} - MANCANTE!", 'ERR')
            errori += 1

    print(f"\n  Errori trovati: {errori}")
    return errori


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 60)
    print("  MIGRAZIONE: Creditsafe API Monitoring")
    print("  Data: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 60)

    # Dry run?
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("\n  *** MODALITA' DRY-RUN: nessuna modifica al database ***\n")
    else:
        print()

    # Verifica database
    if not DB_FILE.exists():
        print(f"ERRORE: Database non trovato: {DB_FILE}")
        sys.exit(1)

    print(f"  Database: {DB_FILE}")
    print(f"  Dimensione: {DB_FILE.stat().st_size / 1024 / 1024:.1f} MB")

    # Backup (solo se non dry-run)
    if not dry_run:
        backup_dir = BASE_DIR / 'backup'
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"gestionale.db.bak_{timestamp}_pre_creditsafe_api"
        print(f"  Backup: {backup_file}")
        shutil.copy2(str(DB_FILE), str(backup_file))
        log("Backup completato", 'OK')

    # Connessione
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row

    try:
        # Step 1: Colonne clienti
        r1 = step1_alter_clienti(conn, dry_run)

        # Step 2: Colonne alert
        r2 = step2_alter_alert(conn, dry_run)
        if r2 == -1:
            print("\n  MIGRAZIONE INTERROTTA: tabella alert mancante")
            conn.close()
            sys.exit(1)

        # Step 3: Indici
        r3 = step3_indici(conn, dry_run)

        # Step 4: Verifica
        if not dry_run:
            errori = step4_verifica(conn)
        else:
            errori = 0

        # Riepilogo
        print("\n" + "=" * 60)
        if dry_run:
            print("  DRY-RUN COMPLETATO")
            print(f"  Colonne clienti da aggiungere: {r1}")
            print(f"  Colonne alert da aggiungere:   {r2}")
            print(f"  Indici da creare:              {r3}")
        else:
            print("  MIGRAZIONE COMPLETATA")
            print(f"  Colonne clienti aggiunte: {r1}")
            print(f"  Colonne alert aggiunte:   {r2}")
            print(f"  Indici creati:            {r3}")
            print(f"  Errori verifica:          {errori}")
        print("=" * 60)

    except Exception as e:
        print(f"\n  ERRORE CRITICO: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
