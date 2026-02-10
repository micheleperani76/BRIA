#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Riacquisizione PDF Creditsafe Archiviati
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-10
# Descrizione: Riprocessa TUTTI i PDF Creditsafe già archiviati nelle cartelle
#              clienti/PIVA/*/creditsafe/*.pdf per aggiornare il database con
#              le regex corrette (v2.2.0).
#
# Uso:
#   python3 scripts/riacquisisci_creditsafe.py --dry-run     # Simulazione
#   python3 scripts/riacquisisci_creditsafe.py                # Esecuzione reale
#   python3 scripts/riacquisisci_creditsafe.py --solo-vuoti   # Solo campi vuoti
#
# NOTA: Lo script NON sposta/cancella PDF. Rilegge quelli già archiviati
#       e aggiorna solo i dati estratti nel database.
# ==============================================================================

import os
import sys
import re
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE PERCORSI
# ==============================================================================

# Rileva la cartella base del progetto (parent di scripts/)
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent if SCRIPT_DIR.name == 'scripts' else SCRIPT_DIR

# Aggiunge la cartella base al path per import moduli app/
sys.path.insert(0, str(BASE_DIR))

# Import moduli del progetto
from app.config import (
    DB_FILE, CLIENTI_DIR, CLIENTI_PIVA_DIR, CLIENTI_CF_DIR,
    PROVINCE_REGIONI, pulisci_piva
)
from app.import_creditsafe import estrai_testo_da_pdf, estrai_dati_azienda, estrai_nome_da_filename
from app.database import get_connection, cerca_cliente_per_piva, aggiorna_cliente_da_creditsafe
from app.utils import setup_logger

# ==============================================================================
# FUNZIONI PRINCIPALI
# ==============================================================================

def trova_tutti_pdf_archiviati():
    """
    Cerca tutti i PDF Creditsafe archiviati nelle cartelle clienti.
    Cerca in: clienti/PIVA/*/creditsafe/*.pdf
              clienti/CF/*/creditsafe/*.pdf
    
    Returns:
        list[dict]: Lista di {path: Path, piva: str, tipo: 'PIVA'|'CF', ident: str}
    """
    pdf_trovati = []
    
    # Cerca in PIVA/
    if CLIENTI_PIVA_DIR.exists():
        for cliente_dir in sorted(CLIENTI_PIVA_DIR.iterdir()):
            if not cliente_dir.is_dir():
                continue
            creditsafe_dir = cliente_dir / 'creditsafe'
            if creditsafe_dir.exists():
                for pdf_file in creditsafe_dir.glob('*.pdf'):
                    pdf_trovati.append({
                        'path': pdf_file,
                        'tipo': 'PIVA',
                        'ident': cliente_dir.name,  # es: '01740560170'
                        'piva_db': f'IT{cliente_dir.name}'  # formato DB
                    })
    
    # Cerca in CF/
    if CLIENTI_CF_DIR.exists():
        for cliente_dir in sorted(CLIENTI_CF_DIR.iterdir()):
            if not cliente_dir.is_dir():
                continue
            creditsafe_dir = cliente_dir / 'creditsafe'
            if creditsafe_dir.exists():
                for pdf_file in creditsafe_dir.glob('*.pdf'):
                    pdf_trovati.append({
                        'path': pdf_file,
                        'tipo': 'CF',
                        'ident': cliente_dir.name,
                        'piva_db': None
                    })
    
    return pdf_trovati


def riacquisisci_pdf(pdf_info, conn, logger, dry_run=False, solo_vuoti=False):
    """
    Riprocessa un singolo PDF archiviato e aggiorna il database.
    
    Args:
        pdf_info: dict con path, tipo, ident, piva_db
        conn: connessione database
        logger: logger
        dry_run: se True, non modifica il database
        solo_vuoti: se True, aggiorna solo i campi attualmente vuoti nel DB
    
    Returns:
        dict: {ok: bool, campi_aggiornati: int, dettaglio: str}
    """
    pdf_path = pdf_info['path']
    nome_file = pdf_path.name
    
    # --- 1. Estrai testo dal PDF ---
    testo = estrai_testo_da_pdf(pdf_path)
    if not testo:
        return {'ok': False, 'motivo': 'testo_vuoto', 'dettaglio': f'Impossibile estrarre testo da {nome_file}'}
    
    # --- 2. Estrai dati con le regex aggiornate ---
    dati = estrai_dati_azienda(testo)
    if not dati:
        return {'ok': False, 'motivo': 'dati_vuoti', 'dettaglio': f'Nessun dato estratto da {nome_file}'}
    
    # Completa con nome da filename se mancante
    if not dati.get('ragione_sociale'):
        dati['ragione_sociale'] = estrai_nome_da_filename(nome_file)
    dati['nome_cliente'] = dati.get('ragione_sociale', estrai_nome_da_filename(nome_file))
    
    # Mantieni il path PDF attuale (non cambiarlo, è già archiviato correttamente)
    path_relativo = str(pdf_path).replace(str(CLIENTI_DIR.parent) + '/', '')
    dati['file_pdf'] = path_relativo
    
    # --- 3. Trova il cliente nel database ---
    cliente = None
    
    # Prima prova con la P.IVA dalla cartella
    if pdf_info['piva_db']:
        cliente = cerca_cliente_per_piva(conn, pdf_info['piva_db'])
    
    # Fallback: usa la P.IVA estratta dal PDF
    if not cliente and dati.get('p_iva'):
        cliente = cerca_cliente_per_piva(conn, dati['p_iva'])
    
    if not cliente:
        return {
            'ok': False, 
            'motivo': 'cliente_non_trovato',
            'dettaglio': f'Nessun cliente trovato per {pdf_info["tipo"]}/{pdf_info["ident"]} - PDF: {nome_file}'
        }
    
    cliente_id = cliente['id']
    nome_cli = cliente['nome_cliente'] or cliente['ragione_sociale'] or '???'
    
    # --- 4. Modalità solo_vuoti: filtra dati ---
    if solo_vuoti:
        dati_filtrati = {}
        for campo, valore in dati.items():
            if valore is not None:
                valore_attuale = cliente[campo] if campo in cliente.keys() else None
                if not valore_attuale or str(valore_attuale).strip() == '':
                    dati_filtrati[campo] = valore
        dati = dati_filtrati
        
        if not dati:
            return {
                'ok': True, 
                'motivo': 'nessun_campo_vuoto',
                'dettaglio': f'[{nome_cli}] Tutti i campi già popolati, niente da aggiornare'
            }
    
    # --- 5. Riepilogo campi estratti (per log) ---
    campi_chiave = {
        'capogruppo_nome': dati.get('capogruppo_nome', ''),
        'capogruppo_cf': dati.get('capogruppo_cf', ''),
        'codice_ateco': dati.get('codice_ateco', ''),
        'desc_ateco': dati.get('desc_ateco', ''),
        'score': dati.get('score', ''),
        'indirizzo': dati.get('indirizzo', ''),
    }
    
    campi_estratti = [f"{k}={v}" for k, v in campi_chiave.items() if v]
    
    # --- 6. Aggiorna database ---
    if not dry_run:
        # Non aggiornare data_report_creditsafe per non perdere la data originale
        # a meno che non sia vuota
        if cliente['data_report_creditsafe']:
            dati.pop('data_report_creditsafe', None)
        
        aggiorna_cliente_da_creditsafe(conn, cliente_id, dati, logger)
    
    return {
        'ok': True,
        'motivo': 'aggiornato',
        'dettaglio': f'[{nome_cli}] ID={cliente_id} → {", ".join(campi_estratti[:4])}'
    }


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Riacquisizione massiva PDF Creditsafe archiviati',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  %(prog)s --dry-run          Simulazione senza modifiche al DB
  %(prog)s                    Esecuzione reale, aggiorna tutti i clienti
  %(prog)s --solo-vuoti       Aggiorna solo i campi attualmente vuoti
  %(prog)s --dry-run -v       Simulazione con dettaglio verboso
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulazione: mostra cosa farebbe senza modificare il DB')
    parser.add_argument('--solo-vuoti', action='store_true',
                        help='Aggiorna solo i campi attualmente vuoti nel database')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Mostra dettaglio per ogni PDF processato')
    
    args = parser.parse_args()
    
    # Setup logger
    logger = setup_logger('riacquisisci_creditsafe')
    
    modalita = "DRY-RUN" if args.dry_run else "ESECUZIONE REALE"
    filtro = " (SOLO CAMPI VUOTI)" if args.solo_vuoti else ""
    
    print("=" * 70)
    print(f"  RIACQUISIZIONE PDF CREDITSAFE ARCHIVIATI - {modalita}{filtro}")
    print("=" * 70)
    logger.info(f"{'=' * 60}")
    logger.info(f"RIACQUISIZIONE CREDITSAFE - {modalita}{filtro}")
    logger.info(f"{'=' * 60}")
    
    # --- 1. Trova tutti i PDF archiviati ---
    print("\n📁 Ricerca PDF archiviati...")
    pdf_list = trova_tutti_pdf_archiviati()
    
    n_piva = sum(1 for p in pdf_list if p['tipo'] == 'PIVA')
    n_cf = sum(1 for p in pdf_list if p['tipo'] == 'CF')
    
    print(f"   Trovati: {len(pdf_list)} PDF ({n_piva} in PIVA/, {n_cf} in CF/)")
    logger.info(f"Trovati {len(pdf_list)} PDF archiviati ({n_piva} PIVA, {n_cf} CF)")
    
    if not pdf_list:
        print("\n⚠️  Nessun PDF trovato. Niente da fare.")
        return
    
    # --- 2. Connessione database ---
    conn = get_connection()
    
    # Conta clienti con capogruppo vuoto (prima)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM clienti WHERE file_pdf IS NOT NULL AND (capogruppo_nome IS NULL OR capogruppo_nome = '')")
    n_capogruppo_vuoti_prima = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM clienti WHERE file_pdf IS NOT NULL AND (codice_ateco IS NULL OR codice_ateco = '')")
    n_ateco_vuoti_prima = cursor.fetchone()[0]
    
    print(f"\n📊 Stato DB prima della riacquisizione:")
    print(f"   Clienti con capogruppo vuoto: {n_capogruppo_vuoti_prima}")
    print(f"   Clienti con ATECO vuoto:      {n_ateco_vuoti_prima}")
    
    # --- 3. Processa ogni PDF ---
    print(f"\n🔄 Elaborazione {len(pdf_list)} PDF...\n")
    
    stats = {
        'aggiornati': 0,
        'nessun_campo_vuoto': 0,
        'testo_vuoto': 0,
        'dati_vuoti': 0,
        'cliente_non_trovato': 0,
        'errori': 0,
    }
    errori_dettaglio = []
    
    for i, pdf_info in enumerate(pdf_list, 1):
        try:
            risultato = riacquisisci_pdf(pdf_info, conn, logger, 
                                         dry_run=args.dry_run, 
                                         solo_vuoti=args.solo_vuoti)
            
            if risultato['ok']:
                if risultato['motivo'] == 'aggiornato':
                    stats['aggiornati'] += 1
                    if args.verbose:
                        print(f"  ✅ {i:4d}/{len(pdf_list)} {risultato['dettaglio']}")
                elif risultato['motivo'] == 'nessun_campo_vuoto':
                    stats['nessun_campo_vuoto'] += 1
                    if args.verbose:
                        print(f"  ⏭️  {i:4d}/{len(pdf_list)} {risultato['dettaglio']}")
            else:
                stats[risultato['motivo']] = stats.get(risultato['motivo'], 0) + 1
                errori_dettaglio.append(risultato['dettaglio'])
                if args.verbose:
                    print(f"  ❌ {i:4d}/{len(pdf_list)} {risultato['dettaglio']}")
            
            # Progress ogni 50
            if not args.verbose and i % 50 == 0:
                print(f"  ... {i}/{len(pdf_list)} elaborati ({stats['aggiornati']} aggiornati)")
                
        except Exception as e:
            stats['errori'] += 1
            msg = f"ERRORE su {pdf_info['path'].name}: {e}"
            errori_dettaglio.append(msg)
            logger.error(msg)
            if args.verbose:
                print(f"  💥 {i:4d}/{len(pdf_list)} {msg}")
    
    # --- 4. Stato DB dopo ---
    if not args.dry_run:
        cursor.execute("SELECT COUNT(*) FROM clienti WHERE file_pdf IS NOT NULL AND (capogruppo_nome IS NULL OR capogruppo_nome = '')")
        n_capogruppo_vuoti_dopo = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clienti WHERE file_pdf IS NOT NULL AND (codice_ateco IS NULL OR codice_ateco = '')")
        n_ateco_vuoti_dopo = cursor.fetchone()[0]
    
    conn.close()
    
    # --- 5. Riepilogo finale ---
    print("\n" + "=" * 70)
    print(f"  RIEPILOGO {modalita}")
    print("=" * 70)
    print(f"  PDF totali elaborati:     {len(pdf_list)}")
    print(f"  ✅ Aggiornati:             {stats['aggiornati']}")
    if args.solo_vuoti:
        print(f"  ⏭️  Già completi:           {stats['nessun_campo_vuoto']}")
    print(f"  ❌ Testo non estraibile:   {stats['testo_vuoto']}")
    print(f"  ❌ Dati non estratti:       {stats['dati_vuoti']}")
    print(f"  ❌ Cliente non trovato:     {stats['cliente_non_trovato']}")
    print(f"  💥 Errori:                  {stats['errori']}")
    
    if not args.dry_run:
        print(f"\n  📊 Miglioramenti:")
        print(f"     Capogruppo vuoti: {n_capogruppo_vuoti_prima} → {n_capogruppo_vuoti_dopo} ({n_capogruppo_vuoti_prima - n_capogruppo_vuoti_dopo} recuperati)")
        print(f"     ATECO vuoti:      {n_ateco_vuoti_prima} → {n_ateco_vuoti_dopo} ({n_ateco_vuoti_prima - n_ateco_vuoti_dopo} recuperati)")
    
    if errori_dettaglio:
        print(f"\n  ⚠️  Dettaglio problemi ({len(errori_dettaglio)}):")
        for err in errori_dettaglio[:20]:  # Max 20
            print(f"     - {err}")
        if len(errori_dettaglio) > 20:
            print(f"     ... e altri {len(errori_dettaglio) - 20}")
    
    print("=" * 70)
    
    # Log riepilogo
    logger.info(f"Completato: {stats['aggiornati']} aggiornati, "
                f"{stats['testo_vuoto']+stats['dati_vuoti']+stats['cliente_non_trovato']} problemi, "
                f"{stats['errori']} errori")
    
    if args.dry_run:
        print("\n⚠️  Questa era una SIMULAZIONE. Nessuna modifica al database.")
        print("   Per eseguire realmente: python3 scripts/riacquisisci_creditsafe.py\n")


if __name__ == '__main__':
    main()
