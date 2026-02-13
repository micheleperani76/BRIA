#!/usr/bin/env python3
# ==============================================================================
# CRON: Promemoria Aggiornamento CRM (ogni lunedi')
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-13
# Crontab: 0 8 * * 1 /home/michele/gestione_flotta/scripts/cron_promemoria_crm.py
# ==============================================================================

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Setup path
BASE_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(BASE_DIR))

DB_FILE = BASE_DIR / 'db' / 'gestionale.db'

def main():
    oggi = datetime.now()
    print(f"[{oggi.strftime('%Y-%m-%d %H:%M:%S')}] Promemoria CRM - {oggi.strftime('%A')}")

    # Verifica che sia lunedi' (0=Mon in weekday())
    if oggi.weekday() != 0:
        print("  Non e' lunedi', skip.")
        return

    if not DB_FILE.exists():
        print(f"  ERRORE: DB non trovato: {DB_FILE}")
        return

    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row

    try:
        from app.connettori_notifiche.aggiorna_crm import notifica_aggiorna_crm
        risultato = notifica_aggiorna_crm(conn)
        print(f"  Risultato: {risultato}")
    except Exception as e:
        print(f"  ERRORE: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
