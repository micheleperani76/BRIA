#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE: Creazione VIEW veicoli_attivi
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-13
# Scopo: Creare VIEW che esclude veicoli merged (merged_in_veicolo_id IS NOT NULL)
#
# Uso:
#   python3 scripts/migrazione_view_veicoli_attivi.py --dry-run
#   python3 scripts/migrazione_view_veicoli_attivi.py
# ==============================================================================

import sqlite3
import sys
import os
import shutil
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

DB_PATH = os.path.expanduser("~/gestione_flotta/db/gestionale.db")
BACKUP_DIR = os.path.expanduser("~/gestione_flotta/backup")

# ==============================================================================
# FUNZIONI
# ==============================================================================

def backup_database():
    """Crea backup del database prima della migrazione."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"db__gestionale.db.bak_{timestamp}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    shutil.copy2(DB_PATH, backup_path)
    
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    print(f"  Backup creato: {backup_path} ({size_mb:.1f} MB)")
    return backup_path


def verifica_prerequisiti(conn):
    """Verifica che le colonne merge esistano nella tabella veicoli."""
    cursor = conn.cursor()
    
    # Verifica colonna merged_in_veicolo_id
    cursor.execute("PRAGMA table_info(veicoli)")
    colonne = [row[1] for row in cursor.fetchall()]
    
    if 'merged_in_veicolo_id' not in colonne:
        print("  ERRORE: Colonna merged_in_veicolo_id non trovata!")
        print("  Eseguire prima la migrazione merge veicoli.")
        return False
    
    if 'data_merge' not in colonne:
        print("  ERRORE: Colonna data_merge non trovata!")
        return False
    
    print("  OK - Colonne merge presenti (merged_in_veicolo_id, data_merge)")
    return True


def view_esiste(conn):
    """Controlla se la VIEW esiste gia'."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='veicoli_attivi'")
    return cursor.fetchone() is not None


def crea_view(conn, dry_run=False):
    """Crea la VIEW veicoli_attivi."""
    sql = """
    CREATE VIEW IF NOT EXISTS veicoli_attivi AS 
    SELECT * FROM veicoli WHERE merged_in_veicolo_id IS NULL
    """
    
    if dry_run:
        print(f"  [DRY-RUN] SQL da eseguire:")
        print(f"  {sql.strip()}")
        return True
    
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    print("  VIEW veicoli_attivi creata con successo")
    return True


def verifica_view(conn):
    """Verifica che la VIEW funzioni correttamente."""
    cursor = conn.cursor()
    
    # Conta totali
    cursor.execute("SELECT COUNT(*) FROM veicoli")
    totali = cursor.fetchone()[0]
    
    # Conta merged
    cursor.execute("SELECT COUNT(*) FROM veicoli WHERE merged_in_veicolo_id IS NOT NULL")
    merged = cursor.fetchone()[0]
    
    # Conta attivi dalla VIEW
    cursor.execute("SELECT COUNT(*) FROM veicoli_attivi")
    attivi = cursor.fetchone()[0]
    
    # Verifica coerenza
    attesi = totali - merged
    ok = (attivi == attesi)
    
    print(f"  Veicoli totali (tabella):  {totali}")
    print(f"  Veicoli merged:            {merged}")
    print(f"  Veicoli attivi (VIEW):     {attivi}")
    print(f"  Attesi (totali - merged):  {attesi}")
    print(f"  Coerenza: {'OK' if ok else 'ERRORE!'}")
    
    if merged > 0:
        print()
        print("  Dettaglio veicoli merged:")
        cursor.execute("""
            SELECT id, targa, tipo_veicolo, merged_in_veicolo_id, data_merge 
            FROM veicoli WHERE merged_in_veicolo_id IS NOT NULL
        """)
        for row in cursor.fetchall():
            print(f"    ID {row[0]} | Targa: {row[1]} | Tipo: {row[2]} | Merged in: {row[3]} | Data: {row[4]}")
    
    return ok


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    dry_run = '--dry-run' in sys.argv
    
    print("=" * 60)
    print("  MIGRAZIONE: Creazione VIEW veicoli_attivi")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'ESECUZIONE'}")
    print(f"  Database: {DB_PATH}")
    print("=" * 60)
    print()
    
    # Verifica esistenza DB
    if not os.path.exists(DB_PATH):
        print(f"ERRORE: Database non trovato: {DB_PATH}")
        sys.exit(1)
    
    # Step 1: Backup
    print("[1/4] Backup database...")
    if dry_run:
        print("  [DRY-RUN] Backup saltato")
    else:
        backup_database()
    print()
    
    # Connessione
    conn = sqlite3.connect(DB_PATH)
    
    # Step 2: Verifica prerequisiti
    print("[2/4] Verifica prerequisiti...")
    if not verifica_prerequisiti(conn):
        conn.close()
        sys.exit(1)
    
    # Verifica se VIEW esiste gia'
    if view_esiste(conn):
        print("  NOTA: VIEW veicoli_attivi esiste gia'!")
        print("  Procedo con verifica...")
        print()
        print("[4/4] Verifica VIEW...")
        if verifica_view(conn):
            print()
            print("  VIEW gia' presente e funzionante. Nessuna azione necessaria.")
        conn.close()
        sys.exit(0)
    print()
    
    # Step 3: Creazione VIEW
    print("[3/4] Creazione VIEW veicoli_attivi...")
    if not crea_view(conn, dry_run):
        conn.close()
        sys.exit(1)
    print()
    
    # Step 4: Verifica
    print("[4/4] Verifica VIEW...")
    if dry_run:
        print("  [DRY-RUN] Verifica saltata (VIEW non creata)")
        # Mostra comunque i conteggi attesi
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM veicoli")
        totali = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM veicoli WHERE merged_in_veicolo_id IS NOT NULL")
        merged = cursor.fetchone()[0]
        print(f"  Veicoli totali: {totali}")
        print(f"  Veicoli merged: {merged}")
        print(f"  Attesi nella VIEW: {totali - merged}")
    else:
        if not verifica_view(conn):
            print("  ATTENZIONE: Verifica fallita!")
            conn.close()
            sys.exit(1)
    
    conn.close()
    
    print()
    print("=" * 60)
    print("  MIGRAZIONE COMPLETATA" if not dry_run else "  DRY-RUN COMPLETATO")
    print("=" * 60)


if __name__ == "__main__":
    main()
