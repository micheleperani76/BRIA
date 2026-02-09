#!/usr/bin/env python3
# ==============================================================================
# IMPORT SCADENZE CRM ZOHO → GESTIONE FLOTTA (VEICOLI INSTALLATO)
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-09
# Descrizione: Importa veicoli INSTALLATO dal CSV Scadenze Zoho CRM
#
# LOGICA:
#   - Match per Targa (prioritario) o crm_id (fallback)
#   - Categorizzazione: Stato Targa + Data fine → ATTIVO/IN_GESTIONE/DISMESSO/ANOMALO
#   - Circolanti → tabella veicoli (tipo_veicolo = 'Installato')
#   - Archiviati → tabella storico_installato (retention 5 anni)
#   - EXTRA che diventa Circolante nel CRM → propone cambio a INSTALLATO
#   - NON sovrascrive: note, driver, km_attuali, dati inseriti da noi
#
# PREREQUISITI:
#   - FASE 1 (import Accounts) deve essere gia' stata eseguita
#   - Lo script migrazione_crm_zoho.py deve essere gia' stato eseguito
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/import_scadenze_crm.py percorso/file.csv --dry-run
#   python3 scripts/import_scadenze_crm.py percorso/file.csv
#
# ==============================================================================

import csv
import sys
import shutil
import sqlite3
import re
from datetime import datetime, timedelta
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

# Retention storico dismessi: 5 anni
RETENTION_ANNI = 5


# ==============================================================================
# NORMALIZZAZIONE
# ==============================================================================

def normalizza_piva_crm(valore):
    """Normalizza P.IVA dal CSV CRM (zero-pad a 11 cifre + IT)."""
    if not valore:
        return None
    v = re.sub(r'[^0-9]', '', str(valore).strip())
    if not v:
        return None
    if len(v) <= 11:
        v = v.zfill(11)
    if len(v) == 11:
        return 'IT' + v
    return None


def normalizza_cf_crm(valore):
    """Normalizza CF dal CSV CRM."""
    if not valore:
        return None
    v = str(valore).strip().upper().replace(' ', '')
    if len(v) == 16 and re.match(r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$', v):
        return v
    v_digits = re.sub(r'[^0-9]', '', v)
    if v_digits and len(v_digits) <= 11:
        return v_digits.zfill(11)
    return None


def normalizza_targa(targa):
    """Normalizza targa: uppercase, rimuovi spazi."""
    if not targa:
        return None
    return str(targa).strip().upper().replace(' ', '')


def safe_float(valore):
    """Converte a float in modo sicuro, None se vuoto/zero."""
    try:
        f = float(str(valore).strip().replace(',', '.'))
        return f if f != 0 else None
    except (ValueError, TypeError):
        return None


def safe_int(valore):
    """Converte a int in modo sicuro, None se vuoto/zero."""
    try:
        i = int(float(str(valore).strip().replace(',', '.')))
        return i if i != 0 else None
    except (ValueError, TypeError):
        return None


def safe_date(valore):
    """Valida una data YYYY-MM-DD, None se vuota o invalida."""
    if not valore or not str(valore).strip():
        return None
    v = str(valore).strip()
    try:
        datetime.strptime(v, '%Y-%m-%d')
        return v
    except ValueError:
        return None


# ==============================================================================
# CATEGORIZZAZIONE VEICOLO
# ==============================================================================

def categorizza_veicolo(stato_targa, data_fine_str):
    """
    Determina la categoria del veicolo in base a Stato Targa + Data fine.
    
    Returns:
        str: 'ATTIVO', 'IN_GESTIONE', 'DISMESSO', 'ANOMALO'
    """
    oggi = datetime.now().date()
    
    data_fine = None
    if data_fine_str:
        try:
            data_fine = datetime.strptime(data_fine_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    stato = (stato_targa or '').strip()
    
    if stato == 'Circolante':
        if data_fine and data_fine >= oggi:
            return 'ATTIVO'
        else:
            return 'IN_GESTIONE'
    elif stato == 'Archiviata':
        if data_fine and data_fine >= oggi:
            return 'ANOMALO'
        else:
            return 'DISMESSO'
    else:
        # Stato sconosciuto → tratta come dismesso per sicurezza
        return 'DISMESSO'


# ==============================================================================
# RICERCA NEL DB
# ==============================================================================

def cerca_cliente_per_piva(cursor, piva_crm, cf_crm):
    """Cerca cliente nel DB per P.IVA o CF."""
    if piva_crm:
        cifre = piva_crm.replace('IT', '').replace(' ', '')
        cursor.execute("""
            SELECT id FROM clienti
            WHERE REPLACE(REPLACE(UPPER(COALESCE(p_iva,'')), 'IT', ''), ' ', '') = ?
               OR REPLACE(REPLACE(UPPER(COALESCE(p_iva,'')), 'IT', ''), ' ', '') = ?
            LIMIT 1
        """, (cifre, cifre.lstrip('0')))
        row = cursor.fetchone()
        if row:
            return row['id']
    
    if cf_crm:
        cursor.execute("""
            SELECT id FROM clienti
            WHERE UPPER(COALESCE(cod_fiscale,'')) = ?
            LIMIT 1
        """, (cf_crm,))
        row = cursor.fetchone()
        if row:
            return row['id']
    
    return None


def cerca_veicolo_per_targa(cursor, targa):
    """Cerca veicolo nel DB per targa (match esatto normalizzato)."""
    if not targa:
        return None
    cursor.execute("""
        SELECT * FROM veicoli
        WHERE UPPER(REPLACE(targa, ' ', '')) = ?
        LIMIT 1
    """, (targa,))
    row = cursor.fetchone()
    return dict(row) if row else None


def cerca_veicolo_per_crm_id(cursor, crm_id):
    """Cerca veicolo nel DB per crm_id (per sync successivi)."""
    if not crm_id:
        return None
    cursor.execute("SELECT * FROM veicoli WHERE crm_id = ? LIMIT 1", (crm_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


# ==============================================================================
# IMPORT VEICOLO CIRCOLANTE (→ tabella veicoli)
# ==============================================================================

def importa_veicolo_circolante(cursor, row, cliente_id, categoria, veicolo_db, dry_run=False):
    """
    Importa o aggiorna un veicolo circolante nella tabella veicoli.
    
    Returns:
        dict: {azione: 'creato'|'aggiornato'|'voltura', dettaglio: str}
    """
    targa = normalizza_targa(row.get('Targa', ''))
    crm_id = row.get('ID record', '').strip()
    
    # Dati dal CSV
    dati_crm = {
        'noleggiatore': row.get('NLT', '').strip() or None,
        'marca': row.get('Casa', '').strip() or None,
        'modello': row.get('Modello', '').strip() or None,
        'alimentazione': row.get('Alimentazione', '').strip() or None,
        'canone': safe_float(row.get('Canone', '')),
        'durata': safe_int(row.get('Durata', '')),
        'km': safe_int(row.get('KM', '')),
        'inizio': safe_date(row.get('Data inizio', '')),
        'scadenza': safe_date(row.get('Data fine', '')),
        'data_immatricolazione': safe_date(row.get('Data immatricolazione', '')),
        'co2': safe_float(row.get('CO\u2082', '') or row.get('CO2', '')),
        'stato_targa': row.get('Stato Targa', '').strip() or None,
        'crm_id': crm_id or None,
        'crm_azienda_id': row.get('Azienda.id', '').strip() or None,
    }
    
    if veicolo_db:
        # ==============================================================
        # VEICOLO ESISTENTE → Aggiorna campi CRM
        # ==============================================================
        veicolo_id = veicolo_db['id']
        tipo_attuale = veicolo_db.get('tipo_veicolo', 'Extra')
        
        # Se era EXTRA → proposta VOLTURA
        if tipo_attuale != 'Installato':
            if not dry_run:
                cursor.execute(
                    "UPDATE veicoli SET tipo_veicolo = 'Installato' WHERE id = ?",
                    (veicolo_id,))
            azione = 'voltura'
        else:
            azione = 'aggiornato'
        
        # Aggiorna campi CRM (NON sovrascrivere: driver, note, km_attuali)
        campi_update = []
        valori_update = []
        
        for campo_db, valore in dati_crm.items():
            if valore is not None:
                campi_update.append(f"{campo_db} = ?")
                valori_update.append(valore)
        
        # Assicura tipo_veicolo = Installato
        campi_update.append("tipo_veicolo = ?")
        valori_update.append('Installato')
        
        # cliente_id (potrebbe essere NULL se importato da broker)
        campi_update.append("cliente_id = ?")
        valori_update.append(cliente_id)
        
        # p_iva
        piva = normalizza_piva_crm(row.get('Partita IVA', ''))
        if piva:
            campi_update.append("p_iva = ?")
            valori_update.append(piva)
        
        if campi_update and not dry_run:
            valori_update.append(veicolo_id)
            cursor.execute(
                f"UPDATE veicoli SET {', '.join(campi_update)} WHERE id = ?",
                valori_update)
        
        return {'azione': azione, 'dettaglio': f"{len(campi_update)} campi"}
    
    else:
        # ==============================================================
        # VEICOLO NUOVO → Crea record INSTALLATO
        # ==============================================================
        piva = normalizza_piva_crm(row.get('Partita IVA', ''))
        
        dati_insert = {
            'cliente_id': cliente_id,
            'p_iva': piva,
            'targa': targa,
            'tipo_veicolo': 'Installato',
        }
        dati_insert.update({k: v for k, v in dati_crm.items() if v is not None})
        
        if not dry_run:
            campi = list(dati_insert.keys())
            placeholders = ', '.join(['?' for _ in campi])
            cursor.execute(
                f"INSERT INTO veicoli ({', '.join(campi)}) VALUES ({placeholders})",
                list(dati_insert.values()))
        
        return {'azione': 'creato', 'dettaglio': 'nuovo INSTALLATO'}


# ==============================================================================
# IMPORT VEICOLO ARCHIVIATO (→ tabella storico_installato)
# ==============================================================================

def importa_veicolo_storico(cursor, row, cliente_id, categoria, dry_run=False):
    """
    Inserisce veicolo archiviato nella tabella storico_installato.
    Se il veicolo era nella tabella veicoli, lo sposta.
    
    Returns:
        dict: {azione: 'storicizzato'|'gia_storico', dettaglio: str}
    """
    targa = normalizza_targa(row.get('Targa', ''))
    crm_id = row.get('ID record', '').strip()
    
    # Verifica se gia' in storico
    cursor.execute(
        "SELECT id FROM storico_installato WHERE targa = ? OR crm_id = ?",
        (targa, crm_id))
    if cursor.fetchone():
        return {'azione': 'gia_storico', 'dettaglio': 'gia in storico_installato'}
    
    # Calcola data retention
    now_str = datetime.now().strftime('%Y-%m-%d')
    retention_str = (datetime.now() + timedelta(days=RETENTION_ANNI * 365)).strftime('%Y-%m-%d')
    
    piva = normalizza_piva_crm(row.get('Partita IVA', ''))
    
    dati = {
        'cliente_id': cliente_id,
        'p_iva': piva,
        'targa': targa,
        'marca': row.get('Casa', '').strip() or None,
        'modello': row.get('Modello', '').strip() or None,
        'alimentazione': row.get('Alimentazione', '').strip() or None,
        'co2': safe_float(row.get('CO\u2082', '') or row.get('CO2', '')),
        'noleggiatore': row.get('NLT', '').strip() or None,
        'canone': safe_float(row.get('Canone', '')),
        'durata': safe_int(row.get('Durata', '')),
        'km': safe_int(row.get('KM', '')),
        'inizio': safe_date(row.get('Data inizio', '')),
        'scadenza': safe_date(row.get('Data fine', '')),
        'data_immatricolazione': safe_date(row.get('Data immatricolazione', '')),
        'crm_id': crm_id or None,
        'crm_azienda_id': row.get('Azienda.id', '').strip() or None,
        'stato_targa': row.get('Stato Targa', '').strip() or None,
        'fase_affare': row.get('Fase Affare', '').strip() or None,
        'motivazione_chiuso_perso': row.get('Motivazione - Chiuso Perso', '').strip() or None,
        'soluzione_alternativa': row.get('Soluzione alternativa scelta', '').strip() or None,
        'data_dismissione': now_str,
        'data_scadenza_retention': retention_str,
    }
    
    # Se il veicolo era nella tabella veicoli, recupera dati driver
    veicolo_db = cerca_veicolo_per_targa(cursor, targa)
    if veicolo_db:
        dati['driver'] = veicolo_db.get('driver')
        # Rimuovi dalla tabella veicoli
        if not dry_run:
            cursor.execute("DELETE FROM veicoli WHERE id = ?", (veicolo_db['id'],))
    
    # Inserisci in storico
    if not dry_run:
        campi = [k for k, v in dati.items() if v is not None]
        valori = [v for v in dati.values() if v is not None]
        placeholders = ', '.join(['?' for _ in campi])
        cursor.execute(
            f"INSERT INTO storico_installato ({', '.join(campi)}) VALUES ({placeholders})",
            valori)
    
    spostato = ' (spostato da veicoli)' if veicolo_db else ''
    return {'azione': 'storicizzato', 'dettaglio': f'→ storico_installato{spostato}'}


# ==============================================================================
# IMPORT PRINCIPALE
# ==============================================================================

def importa_scadenze(csv_path, dry_run=False):
    """
    Funzione principale di import Scadenze CRM.
    """
    stats = {
        'totale_csv': 0,
        'attivi_creati': 0,
        'attivi_aggiornati': 0,
        'volture': 0,
        'storicizzati': 0,
        'gia_storico': 0,
        'cliente_non_trovato': 0,
        'targa_vuota': 0,
        'errori': 0,
        'cat_attivo': 0,
        'cat_in_gestione': 0,
        'cat_dismesso': 0,
        'cat_anomalo': 0,
        'dettaglio': [],
        'dettaglio_errori': [],
    }
    
    # Leggi CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        righe = list(reader)
    
    stats['totale_csv'] = len(righe)
    print(f"\n  Record CSV letti: {stats['totale_csv']}")
    
    # Connessione DB
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        for i, row in enumerate(righe, 1):
            targa_raw = row.get('Targa', '').strip()
            targa = normalizza_targa(targa_raw)
            azienda = row.get('Azienda', '').strip()
            stato_targa = row.get('Stato Targa', '').strip()
            data_fine = row.get('Data fine', '').strip()
            crm_id = row.get('ID record', '').strip()
            
            # Validazione targa
            if not targa:
                stats['targa_vuota'] += 1
                stats['dettaglio_errori'].append(
                    f"  Riga {i}: [{azienda}] - Targa vuota")
                stats['errori'] += 1
                continue
            
            # Categorizza
            categoria = categorizza_veicolo(stato_targa, data_fine)
            stats[f'cat_{categoria.lower()}'] += 1
            
            # Cerca cliente per P.IVA/CF
            piva_crm = normalizza_piva_crm(row.get('Partita IVA', ''))
            cf_crm = normalizza_cf_crm(row.get('Codice Fiscale', ''))
            cliente_id = cerca_cliente_per_piva(cursor, piva_crm, cf_crm)
            
            if not cliente_id:
                stats['cliente_non_trovato'] += 1
                stats['dettaglio_errori'].append(
                    f"  Riga {i}: [{targa}] [{azienda}] - Cliente non trovato "
                    f"(PIVA={piva_crm}, CF={cf_crm})")
                stats['errori'] += 1
                continue
            
            # ============================================================
            # CIRCOLANTE → tabella veicoli
            # ============================================================
            if categoria in ('ATTIVO', 'IN_GESTIONE'):
                # Cerca veicolo esistente per targa o crm_id
                veicolo_db = cerca_veicolo_per_targa(cursor, targa)
                if not veicolo_db:
                    veicolo_db = cerca_veicolo_per_crm_id(cursor, crm_id)
                
                risultato = importa_veicolo_circolante(
                    cursor, row, cliente_id, categoria, veicolo_db, dry_run)
                
                if risultato['azione'] == 'creato':
                    stats['attivi_creati'] += 1
                elif risultato['azione'] == 'voltura':
                    stats['volture'] += 1
                else:
                    stats['attivi_aggiornati'] += 1
                
                stats['dettaglio'].append(
                    f"  [{targa}] {azienda[:30]:30s} {categoria:12s} "
                    f"→ {risultato['azione']} ({risultato['dettaglio']})")
            
            # ============================================================
            # ARCHIVIATA → tabella storico_installato
            # ============================================================
            else:
                risultato = importa_veicolo_storico(
                    cursor, row, cliente_id, categoria, dry_run)
                
                if risultato['azione'] == 'storicizzato':
                    stats['storicizzati'] += 1
                else:
                    stats['gia_storico'] += 1
                
                stats['dettaglio'].append(
                    f"  [{targa}] {azienda[:30]:30s} {categoria:12s} "
                    f"→ {risultato['azione']} ({risultato['dettaglio']})")
        
        # Commit
        if not dry_run:
            conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"\n  ERRORE durante l'import: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()
    
    return stats


# ==============================================================================
# OUTPUT RISULTATI
# ==============================================================================

def stampa_risultati(stats, dry_run=False):
    """Stampa riepilogo import."""
    prefisso = "[DRY-RUN] " if dry_run else ""
    
    print("\n" + "="*60)
    print(f"{prefisso}RIEPILOGO IMPORT SCADENZE CRM")
    print("="*60)
    
    print(f"\n  --- Categorizzazione ---")
    print(f"  ATTIVO (Circolante + contratto in corso): {stats['cat_attivo']}")
    print(f"  IN_GESTIONE (Circolante + scaduto):       {stats['cat_in_gestione']}")
    print(f"  DISMESSO (Archiviata + scaduto):          {stats['cat_dismesso']}")
    print(f"  ANOMALO (Archiviata + in corso):          {stats['cat_anomalo']}")
    
    print(f"\n  --- Azioni su tabella veicoli ---")
    print(f"  Veicoli creati (INSTALLATO):  {stats['attivi_creati']}")
    print(f"  Veicoli aggiornati:           {stats['attivi_aggiornati']}")
    print(f"  Volture (EXTRA → INSTALLATO): {stats['volture']}")
    
    print(f"\n  --- Azioni su storico_installato ---")
    print(f"  Storicizzati:                 {stats['storicizzati']}")
    print(f"  Gia' in storico:              {stats['gia_storico']}")
    
    print(f"\n  --- Errori ---")
    print(f"  Clienti non trovati:          {stats['cliente_non_trovato']}")
    print(f"  Targhe vuote:                 {stats['targa_vuota']}")
    print(f"  Totale errori:                {stats['errori']}")
    
    if stats['dettaglio']:
        print(f"\n--- Dettaglio operazioni ({len(stats['dettaglio'])}) ---")
        for d in stats['dettaglio'][:80]:
            print(d)
        if len(stats['dettaglio']) > 80:
            print(f"  ... e altri {len(stats['dettaglio'])-80}")
    
    if stats['dettaglio_errori']:
        print(f"\n--- ERRORI ({stats['errori']}) ---")
        for d in stats['dettaglio_errori'][:30]:
            print(d)
    
    print()
    if dry_run:
        print("  Nessuna modifica applicata (dry-run).")
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
    log_file = LOG_DIR / f"import_scadenze_{modalita}_{timestamp}.log"
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Import Scadenze CRM - {'DRY-RUN' if dry_run else 'ESECUZIONE'}\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"File: {csv_path}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"Record CSV:              {stats['totale_csv']}\n")
        f.write(f"ATTIVO:                  {stats['cat_attivo']}\n")
        f.write(f"IN_GESTIONE:             {stats['cat_in_gestione']}\n")
        f.write(f"DISMESSO:                {stats['cat_dismesso']}\n")
        f.write(f"ANOMALO:                 {stats['cat_anomalo']}\n\n")
        f.write(f"Veicoli creati:          {stats['attivi_creati']}\n")
        f.write(f"Veicoli aggiornati:      {stats['attivi_aggiornati']}\n")
        f.write(f"Volture:                 {stats['volture']}\n")
        f.write(f"Storicizzati:            {stats['storicizzati']}\n")
        f.write(f"Gia' in storico:         {stats['gia_storico']}\n")
        f.write(f"Errori:                  {stats['errori']}\n\n")
        
        if stats['dettaglio']:
            f.write("--- Dettaglio ---\n")
            for d in stats['dettaglio']:
                f.write(d + '\n')
            f.write('\n')
        
        if stats['dettaglio_errori']:
            f.write("--- ERRORI ---\n")
            for d in stats['dettaglio_errori']:
                f.write(d + '\n')
    
    print(f"  Log salvato: {log_file}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/import_scadenze_crm.py <file.csv> [--dry-run]")
        print()
        print("Esempio:")
        print("  python3 scripts/import_scadenze_crm.py import_dati/Scadenze_2026_02_09.csv --dry-run")
        print("  python3 scripts/import_scadenze_crm.py import_dati/Scadenze_2026_02_09.csv")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv
    
    print("="*60)
    print("IMPORT SCADENZE CRM ZOHO (VEICOLI INSTALLATO)")
    print("="*60)
    print(f"  File CSV:  {csv_path}")
    print(f"  Database:  {DB_FILE}")
    print(f"  Data:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'IMPORT REALE'}")
    
    # Verifica file
    if not csv_path.exists():
        csv_path2 = BASE_DIR / csv_path
        if csv_path2.exists():
            csv_path = csv_path2
        else:
            print(f"\n  ERRORE: File non trovato: {csv_path}")
            sys.exit(1)
    
    # Verifica DB
    if not DB_FILE.exists():
        print(f"\n  ERRORE: Database non trovato: {DB_FILE}")
        sys.exit(1)
    
    # Backup (solo in modalita' reale)
    if not dry_run:
        print("\n" + "-"*60)
        print("BACKUP DATABASE")
        print("-"*60)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = DB_FILE.parent / f"gestionale_backup_pre_import_scadenze_{timestamp}.db"
        shutil.copy2(DB_FILE, backup_path)
        print(f"  Backup creato: {backup_path.name}")
    
    # Import
    print("\n" + "-"*60)
    print("ELABORAZIONE")
    print("-"*60)
    
    try:
        stats = importa_scadenze(csv_path, dry_run)
        stampa_risultati(stats, dry_run)
        salva_log(stats, csv_path, dry_run)
    except Exception as e:
        print(f"\n  ERRORE FATALE: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
