#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Scansione Automatica Top Prospect
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-01-29
# Descrizione: Script per scansione periodica candidati Top Prospect
# Uso: Eseguire via cron ogni ora
# ==============================================================================

import sys
import os
import sqlite3
from datetime import datetime

# Aggiungi il percorso dell'app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_connection
from app.motore_top_prospect import esegui_analisi_candidati

LOG_FILE = os.path.expanduser('~/gestione_flotta/logs/scansione_tp.log')

def log_messaggio(messaggio):
    """Scrive un messaggio nel file di log."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    riga = f"[{timestamp}] {messaggio}\n"
    
    with open(LOG_FILE, 'a') as f:
        f.write(riga)
    
    print(riga.strip())

def main():
    log_messaggio("=== AVVIO SCANSIONE TOP PROSPECT ===")
    
    try:
        conn = get_connection()
        
        # Esegui analisi (utente_id=0 per sistema automatico)
        risultato = esegui_analisi_candidati(conn, utente_id=0)
        
        log_messaggio(f"Clienti analizzati: {risultato['totale_analizzati']}")
        log_messaggio(f"Nuovi candidati trovati: {risultato['totale_candidati']}")
        
        if risultato['nuovi_candidati']:
            for c in risultato['nuovi_candidati']:
                nome = c.get('ragione_sociale') or c.get('nome_cliente') or 'N/D'
                log_messaggio(f"  - Nuovo candidato: {nome}")
        
        conn.close()
        log_messaggio("=== SCANSIONE COMPLETATA ===")
        
    except Exception as e:
        log_messaggio(f"ERRORE: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
