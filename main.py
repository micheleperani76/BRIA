#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Entry Point Principale
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-12
# Descrizione: Script principale per avviare il sistema
# ==============================================================================

import sys
import argparse
from pathlib import Path

# Aggiungi la directory corrente al path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import WEB_PORT, BASE_DIR
from app.database import init_database
from app.utils import setup_logger, pulisci_log_vecchi
from app.import_creditsafe import importa_tutti_pdf

def cmd_server(args):
    """Avvia il server web."""
    from app.web_server import run_server
    run_server(host=args.host, port=args.port, debug=args.debug)

def cmd_import(args):
    """Importa PDF Creditsafe."""
    print("=" * 60)
    print("IMPORT PDF CREDITSAFE")
    print("=" * 60)
    
    risultato = importa_tutti_pdf()
    
    print("-" * 60)
    print(f"Elaborati: {risultato['elaborati']}")
    print(f"Errori:    {risultato['errori']}")
    print("=" * 60)

def cmd_init(args):
    """Inizializza il database."""
    print("Inizializzazione database...")
    conn = init_database()
    conn.close()
    print("✓ Database inizializzato correttamente")

def cmd_pulisci(args):
    """Pulisce log vecchi."""
    print("Pulizia log vecchi...")
    rimossi = pulisci_log_vecchi()
    print(f"✓ Rimossi {rimossi} file di log")

def cmd_info(args):
    """Mostra informazioni sul sistema."""
    from app.config import DB_FILE, PDF_DIR, STORICO_PDF_DIR, LOGS_DIR
    
    print("=" * 60)
    print("GESTIONE FLOTTA - Informazioni Sistema")
    print("=" * 60)
    print(f"Cartella base:  {BASE_DIR}")
    print(f"Database:       {DB_FILE}")
    print(f"PDF input:      {PDF_DIR}")
    print(f"PDF storico:    {STORICO_PDF_DIR}")
    print(f"Log:            {LOGS_DIR}")
    print("-" * 60)
    
    # Conta file
    pdf_input = len(list(PDF_DIR.glob('*.pdf'))) if PDF_DIR.exists() else 0
    pdf_storico = sum(1 for _ in STORICO_PDF_DIR.rglob('*.pdf')) if STORICO_PDF_DIR.exists() else 0
    log_files = len(list(LOGS_DIR.glob('*.log'))) if LOGS_DIR.exists() else 0
    db_size = DB_FILE.stat().st_size / 1024 if DB_FILE.exists() else 0
    
    print(f"PDF da elaborare:  {pdf_input}")
    print(f"PDF in storico:    {pdf_storico}")
    print(f"File di log:       {log_files}")
    print(f"Dimensione DB:     {db_size:.1f} KB")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(
        description='Gestione Flotta - Sistema gestione clienti e veicoli',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Esempi:
  python main.py server              # Avvia server web
  python main.py server -p 8080      # Avvia su porta 8080
  python main.py import              # Importa PDF Creditsafe
  python main.py init                # Inizializza database
  python main.py pulisci             # Pulisce log vecchi
  python main.py info                # Mostra info sistema
        '''
    )
    
    subparsers = parser.add_subparsers(dest='comando', help='Comandi disponibili')
    
    # Comando: server
    p_server = subparsers.add_parser('server', help='Avvia il server web')
    p_server.add_argument('--host', default='0.0.0.0', help='Host (default: 0.0.0.0)')
    p_server.add_argument('-p', '--port', type=int, default=WEB_PORT, help=f'Porta (default: {WEB_PORT})')
    p_server.add_argument('--debug', action='store_true', help='Modalità debug')
    p_server.set_defaults(func=cmd_server)
    
    # Comando: import
    p_import = subparsers.add_parser('import', help='Importa PDF Creditsafe')
    p_import.set_defaults(func=cmd_import)
    
    # Comando: init
    p_init = subparsers.add_parser('init', help='Inizializza il database')
    p_init.set_defaults(func=cmd_init)
    
    # Comando: pulisci
    p_pulisci = subparsers.add_parser('pulisci', help='Pulisce log vecchi')
    p_pulisci.set_defaults(func=cmd_pulisci)
    
    # Comando: info
    p_info = subparsers.add_parser('info', help='Mostra informazioni sistema')
    p_info.set_defaults(func=cmd_info)
    
    args = parser.parse_args()
    
    if args.comando is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)

if __name__ == '__main__':
    main()
