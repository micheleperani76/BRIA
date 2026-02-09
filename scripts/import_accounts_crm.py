#!/usr/bin/env python3
# ==============================================================================
# IMPORT ACCOUNTS CRM ZOHO → GESTIONE FLOTTA
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-09
# Descrizione: Importa anagrafica clienti dal CSV Zoho CRM
#
# LOGICA:
#   - Match per P.IVA (normalizzata, zero-padded a 11 cifre)
#   - Fallback match per Codice Fiscale
#   - Cliente ESISTENTE: aggiorna SOLO campi CRM (Creditsafe ha priorita')
#   - Cliente NUOVO: crea con tutti i dati CRM disponibili
#   - Popola tabelle satellite (consensi, finanziari, alert, metadata)
#   - Gestione sedi (operativa + fatturazione)
#
# USO:
#   cd ~/gestione_flotta
#   python3 scripts/import_accounts_crm.py percorso/file.csv --dry-run
#   python3 scripts/import_accounts_crm.py percorso/file.csv
#
# ==============================================================================

import csv
import sys
import shutil
import sqlite3
import re
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

# ID commerciale di default per nuovi clienti (Paolo Ciotti)
COMMERCIALE_DEFAULT_ID = 2

# Commerciali Consecution che NON sono "BR Car Service"
# Questi vengono salvati come dato consultativo
COMMERCIALI_CONSECUTION_EXTRA = [
    'Stefano Ostoni',
    'Stefano Pochini',
    'Valerio Romeo',
    'Valentina Castriotta',
]

# ==============================================================================
# HELPER ACCESSO COLONNE CSV
# ==============================================================================

def normalizza_chiavi_csv(righe):
    """
    Normalizza le chiavi del CSV per gestire eventuali corruzioni
    di accenti durante il trasferimento file via Chromium.
    Mappa chiavi ASCII-safe alle chiavi originali del CSV.
    """
    if not righe:
        return righe
    
    import unicodedata
    
    # Prendi le chiavi originali dal primo record
    chiavi_originali = list(righe[0].keys())
    
    # Mappa prevista (nome atteso → nome nel CSV)
    # Se il CSV ha chiavi con accenti intatti, le usa direttamente
    # Se corrotti, cerca la versione piu' simile
    chiavi_attese = {
        'Citta Sede Operativa': None,
        'Citta di fatturazione': None,
        'Citta di spedizione': None,
    }
    
    for chiave_orig in chiavi_originali:
        nfkd = unicodedata.normalize('NFKD', chiave_orig)
        chiave_ascii = ''.join(c for c in nfkd if not unicodedata.combining(c))
        
        for attesa in chiavi_attese:
            if chiave_ascii == attesa and chiave_orig != attesa:
                chiavi_attese[attesa] = chiave_orig
    
    # Se ci sono mapping da fare, rinomina le chiavi in tutti i record
    mapping_da_fare = {v: k for k, v in chiavi_attese.items() if v is not None}
    
    if not mapping_da_fare:
        return righe  # Nessuna correzione necessaria
    
    righe_corrette = []
    for row in righe:
        nuovo = {}
        for k, v in row.items():
            # Se la chiave va rinominata, usa il nome ASCII
            # Ma CONSERVA anche la chiave originale per compatibilita'
            if k in mapping_da_fare:
                nuovo[mapping_da_fare[k]] = v
            nuovo[k] = v
        righe_corrette.append(nuovo)
    
    return righe_corrette


# ==============================================================================
# MAPPING CAMPI CSV → DB
# ==============================================================================

# Campi CRM che aggiornano SEMPRE (anche su clienti esistenti)
CAMPI_CRM_AGGIORNA = {
    'ID record':                       'crm_id',
    'Stato Cliente':                   'stato_crm',
    'Origine Contatto':                'origine_contatto',
    'Azienda Tipo':                    'azienda_tipo_crm',
    'Profilazione per totale flotta':  'profilazione_flotta',
    'Totale Flotta':                   'totale_flotta_crm',
    'Flotta con CNS':                  'flotta_cns_crm',
    'Noleggiatore principale CNS 1':   'noleggiatore_principale_1',
    'Noleggiatore principale CNS 2':   'noleggiatore_principale_2',
    'Note concorrenza':                'note_concorrenza',
}

# Campi CRM per clienti NUOVI (creazione)
CAMPI_CRM_CREAZIONE = {
    'Nome Azienda':     'nome_cliente',
    'Email PEC':        'pec',
    'Telefono':         'telefono',
}

# Campi interi (da convertire)
CAMPI_INTERI = {'totale_flotta_crm', 'flotta_cns_crm'}


# ==============================================================================
# NORMALIZZAZIONE P.IVA / CF
# ==============================================================================

def normalizza_piva_crm(valore):
    """
    Normalizza P.IVA dal CSV CRM.
    Il CRM esporta senza prefisso IT e senza zero-padding.
    Es: '672420171' → 'IT00672420171'
        '2006580985' → 'IT02006580985'
    
    Returns:
        str: P.IVA normalizzata con IT + 11 cifre, o None
    """
    if not valore:
        return None
    
    v = str(valore).strip().upper().replace('IT', '').replace(' ', '')
    
    # Rimuovi caratteri non numerici
    v = re.sub(r'[^0-9]', '', v)
    
    if not v:
        return None
    
    # Zero-pad a 11 cifre
    if len(v) <= 11:
        v = v.zfill(11)
    
    # Valida: deve essere 11 cifre
    if len(v) == 11 and v.isdigit():
        return 'IT' + v
    
    return None


def normalizza_cf_crm(valore):
    """
    Normalizza Codice Fiscale dal CSV CRM.
    
    Returns:
        str: CF normalizzato (16 chars persona fisica o 11 cifre azienda), o None
    """
    if not valore:
        return None
    
    v = str(valore).strip().upper().replace(' ', '')
    
    if not v:
        return None
    
    # CF persona fisica: 16 caratteri alfanumerici
    if len(v) == 16 and re.match(r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$', v):
        return v
    
    # CF azienda: numerico, zero-pad a 11
    v_digits = re.sub(r'[^0-9]', '', v)
    if v_digits and len(v_digits) <= 11:
        return v_digits.zfill(11)
    
    return None


def piva_solo_cifre(piva_normalizzata):
    """Estrae solo le cifre da una P.IVA normalizzata (rimuove IT)."""
    if not piva_normalizzata:
        return None
    return piva_normalizzata.replace('IT', '').replace(' ', '')


# ==============================================================================
# RICERCA CLIENTE NEL DB
# ==============================================================================

def cerca_cliente(cursor, piva_crm, cf_crm):
    """
    Cerca cliente nel DB per P.IVA o CF.
    Gestisce le diverse forme di salvataggio (con/senza IT, con/senza zeri).
    
    Returns:
        dict: dati cliente o None
    """
    # Tentativo 1: Match per P.IVA (confronto cifre pure)
    if piva_crm:
        cifre = piva_solo_cifre(piva_crm)
        if cifre:
            # Cerca confrontando solo le cifre (ignora IT, spazi, zeri iniziali)
            cursor.execute("""
                SELECT * FROM clienti
                WHERE REPLACE(REPLACE(REPLACE(UPPER(COALESCE(p_iva,'')), 'IT', ''), ' ', ''), '0', '')
                    = REPLACE(?, '0', '')
                   OR REPLACE(REPLACE(UPPER(COALESCE(p_iva,'')), 'IT', ''), ' ', '') = ?
                   OR REPLACE(REPLACE(UPPER(COALESCE(p_iva,'')), 'IT', ''), ' ', '') = ?
                LIMIT 1
            """, (cifre, cifre, cifre.lstrip('0')))
            row = cursor.fetchone()
            if row:
                return dict(row)
    
    # Tentativo 2: Match per Codice Fiscale
    if cf_crm:
        cursor.execute("""
            SELECT * FROM clienti
            WHERE UPPER(COALESCE(cod_fiscale,'')) = ?
               OR UPPER(COALESCE(p_iva,'')) LIKE ?
            LIMIT 1
        """, (cf_crm, f'%{cf_crm}%'))
        row = cursor.fetchone()
        if row:
            return dict(row)
    
    return None


# ==============================================================================
# GESTIONE SEDI
# ==============================================================================

def gestisci_sedi(cursor, cliente_id, row, dry_run=False, stats=None):
    """
    Gestisce le sedi del cliente (operativa + fatturazione).
    
    Sede Operativa: da campi 'Indirizzo Sede Operativa', 'Citta Sede Operativa', ecc.
    Indirizzo Fatturazione: da campi 'Via fatturazione', 'Citta di fatturazione', ecc.
    """
    # --- Sede Operativa ---
    indirizzo_op = row.get('Indirizzo Sede Operativa', '').strip()
    if indirizzo_op:
        sede_op = {
            'indirizzo': indirizzo_op,
            'citta': (row.get('Citta Sede Operativa', '') or row.get('Città Sede Operativa', '')).strip(),
            'provincia': row.get('Provincia Sede Operativa', '').strip(),
            'cap': row.get('Cap Sede Operativa', '').strip(),
        }
        _upsert_sede(cursor, cliente_id, 'Operativa', sede_op, dry_run, stats)
    
    # --- Indirizzo Fatturazione ---
    indirizzo_fatt = row.get('Via fatturazione', '').strip()
    if indirizzo_fatt:
        sede_fatt = {
            'indirizzo': indirizzo_fatt,
            'citta': (row.get('Citta di fatturazione', '') or row.get('Città di fatturazione', '')).strip(),
            'provincia': row.get('Provincia di fatturazione', '').strip(),
            'cap': row.get('Cap', '').strip(),
        }
        _upsert_sede(cursor, cliente_id, 'Indirizzo Fatturazione', sede_fatt, dry_run, stats)


def _upsert_sede(cursor, cliente_id, tipo_sede, dati, dry_run=False, stats=None):
    """Crea o aggiorna una sede cliente."""
    # Cerca sede esistente
    cursor.execute("""
        SELECT id, indirizzo FROM sedi_cliente
        WHERE cliente_id = ? AND tipo_sede = ?
    """, (cliente_id, tipo_sede))
    esistente = cursor.fetchone()
    
    if esistente:
        # Aggiorna solo se indirizzo diverso
        if esistente['indirizzo'] != dati['indirizzo']:
            if not dry_run:
                cursor.execute("""
                    UPDATE sedi_cliente
                    SET indirizzo = ?, citta = ?, provincia = ?, cap = ?
                    WHERE id = ?
                """, (dati['indirizzo'], dati['citta'], dati['provincia'],
                      dati['cap'], esistente['id']))
            if stats is not None:
                stats['sedi_aggiornate'] += 1
    else:
        # Crea nuova sede
        if not dry_run:
            cursor.execute("""
                INSERT INTO sedi_cliente
                (cliente_id, tipo_sede, indirizzo, cap, citta, provincia)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cliente_id, tipo_sede, dati['indirizzo'],
                  dati['cap'], dati['citta'], dati['provincia']))
        if stats is not None:
            stats['sedi_create'] += 1


# ==============================================================================
# GESTIONE TABELLE SATELLITE
# ==============================================================================

def gestisci_consensi(cursor, cliente_id, row, dry_run=False):
    """Popola tabella clienti_consensi con dati GDPR dal CRM."""
    tipi = {
        'Newsletter':                                    'Newsletter',
        'Comunicazioni informative e commerciali':       'Comunicazioni',
        'Trasferimento dati a soggetti terzi':           'Trasferimento terzi',
        'Trattamento dati e consulenza':                 'Trattamento dati',
    }
    
    data_privacy = row.get('Data inserimento Privacy', '').strip() or None
    
    for campo_csv, tipo_consenso in tipi.items():
        valore = row.get(campo_csv, '').strip().lower()
        if not valore:
            continue
        
        # Verifica se esiste gia'
        cursor.execute("""
            SELECT id FROM clienti_consensi
            WHERE cliente_id = ? AND tipo_consenso = ? AND origine = 'CRM'
        """, (cliente_id, tipo_consenso))
        
        if cursor.fetchone():
            # Aggiorna
            if not dry_run:
                cursor.execute("""
                    UPDATE clienti_consensi
                    SET valore = ?, data_consenso = ?
                    WHERE cliente_id = ? AND tipo_consenso = ? AND origine = 'CRM'
                """, (valore, data_privacy, cliente_id, tipo_consenso))
        else:
            # Inserisci
            if not dry_run:
                cursor.execute("""
                    INSERT INTO clienti_consensi
                    (cliente_id, tipo_consenso, valore, data_consenso, origine)
                    VALUES (?, ?, ?, ?, 'CRM')
                """, (cliente_id, tipo_consenso, valore, data_privacy))


def gestisci_dati_finanziari(cursor, cliente_id, row, dry_run=False):
    """Popola tabella clienti_dati_finanziari con dati dal CRM."""
    anno = row.get('Anno di competenza', '').strip()
    fatturato = row.get('Fatturato annuo', '').strip()
    
    # Serve almeno l'anno e un dato
    if not anno or not fatturato:
        return
    
    try:
        anno_int = int(anno)
    except ValueError:
        return
    
    def safe_float(v):
        try:
            f = float(str(v).strip().replace(',', '.'))
            return f if f != 0 else None
        except (ValueError, TypeError):
            return None
    
    dati = {
        'fatturato': safe_float(fatturato),
        'iban': row.get('IBAN', '').strip() or None,
        'ebitda': safe_float(row.get('EBITDA', '')),
        'ricavi': safe_float(row.get('Ricavi', '')),
        'utile_perdita': safe_float(row.get("Utile (perdita) dell'esercizio", '')),
        'patrimonio_netto': safe_float(row.get('Patrimonio netto', '')),
    }
    
    # Almeno un dato valido?
    if not any(v for k, v in dati.items() if k != 'iban'):
        return
    
    # Verifica se esiste gia'
    cursor.execute("""
        SELECT id FROM clienti_dati_finanziari
        WHERE cliente_id = ? AND anno_riferimento = ?
    """, (cliente_id, anno_int))
    
    if cursor.fetchone():
        if not dry_run:
            cursor.execute("""
                UPDATE clienti_dati_finanziari
                SET fatturato = ?, iban = ?, ebitda = ?, ricavi = ?,
                    utile_perdita = ?, patrimonio_netto = ?,
                    fonte = 'CRM', data_import = ?
                WHERE cliente_id = ? AND anno_riferimento = ?
            """, (dati['fatturato'], dati['iban'], dati['ebitda'], dati['ricavi'],
                  dati['utile_perdita'], dati['patrimonio_netto'],
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  cliente_id, anno_int))
    else:
        if not dry_run:
            cursor.execute("""
                INSERT INTO clienti_dati_finanziari
                (cliente_id, anno_riferimento, fatturato, iban, ebitda, ricavi,
                 utile_perdita, patrimonio_netto, fonte, data_import)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CRM', ?)
            """, (cliente_id, anno_int, dati['fatturato'], dati['iban'],
                  dati['ebitda'], dati['ricavi'], dati['utile_perdita'],
                  dati['patrimonio_netto'],
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


def gestisci_alert(cursor, cliente_id, row, dry_run=False):
    """Popola tabella clienti_creditsafe_alert con flag rischio dal CRM."""
    tipi = {
        'Protesti':                                      'Protesti',
        'Protesti gravi':                                'Protesti gravi',
        'Pregiudizievoli':                               'Pregiudizievoli',
        'Pregiudizievoli gravi':                         'Pregiudizievoli gravi',
        'Procedure concorsuali':                         'Procedure concorsuali',
        'Cassa integrazione Guadagni Straordinaria':     'Cassa integrazione',
        'Ristrutturazione debito / concordati preventivi': 'Ristrutturazione debito',
    }
    
    for campo_csv, tipo_alert in tipi.items():
        valore = row.get(campo_csv, '').strip().lower()
        if not valore:
            continue
        
        # Verifica se esiste gia'
        cursor.execute("""
            SELECT id FROM clienti_creditsafe_alert
            WHERE cliente_id = ? AND tipo_alert = ? AND fonte = 'CRM'
        """, (cliente_id, tipo_alert))
        
        if cursor.fetchone():
            if not dry_run:
                cursor.execute("""
                    UPDATE clienti_creditsafe_alert
                    SET valore = ?, data_rilevazione = ?
                    WHERE cliente_id = ? AND tipo_alert = ? AND fonte = 'CRM'
                """, (valore, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                      cliente_id, tipo_alert))
        else:
            if not dry_run:
                cursor.execute("""
                    INSERT INTO clienti_creditsafe_alert
                    (cliente_id, tipo_alert, valore, data_rilevazione, fonte)
                    VALUES (?, ?, ?, ?, 'CRM')
                """, (cliente_id, tipo_alert, valore,
                      datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


def gestisci_metadata(cursor, cliente_id, row, dry_run=False):
    """Popola tabella clienti_crm_metadata con dati tecnici Zoho."""
    crm_id = row.get('ID record', '').strip()
    if not crm_id:
        return
    
    dati = {
        'crm_record_id': crm_id,
        'crm_creato_da': row.get('Creato da', '').strip() or None,
        'crm_ora_creazione': row.get('Ora creazione', '').strip() or None,
        'crm_struttura': row.get('Struttura', '').strip() or None,
        'crm_locked': row.get('Locked', '').strip() or None,
        'crm_old_owner': row.get('Old Owner', '').strip() or None,
        'data_ultimo_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    # Verifica se esiste gia'
    cursor.execute("""
        SELECT id FROM clienti_crm_metadata WHERE cliente_id = ?
    """, (cliente_id,))
    
    if cursor.fetchone():
        if not dry_run:
            cursor.execute("""
                UPDATE clienti_crm_metadata
                SET crm_record_id = ?, crm_creato_da = ?, crm_ora_creazione = ?,
                    crm_struttura = ?, crm_locked = ?, crm_old_owner = ?,
                    data_ultimo_sync = ?
                WHERE cliente_id = ?
            """, (dati['crm_record_id'], dati['crm_creato_da'],
                  dati['crm_ora_creazione'], dati['crm_struttura'],
                  dati['crm_locked'], dati['crm_old_owner'],
                  dati['data_ultimo_sync'], cliente_id))
    else:
        if not dry_run:
            cursor.execute("""
                INSERT INTO clienti_crm_metadata
                (cliente_id, crm_record_id, crm_creato_da, crm_ora_creazione,
                 crm_struttura, crm_locked, crm_old_owner, data_ultimo_sync)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cliente_id, dati['crm_record_id'], dati['crm_creato_da'],
                  dati['crm_ora_creazione'], dati['crm_struttura'],
                  dati['crm_locked'], dati['crm_old_owner'],
                  dati['data_ultimo_sync']))


# ==============================================================================
# GESTIONE COMMERCIALE CONSECUTION
# ==============================================================================

def get_commerciale_consecution(row):
    """
    Determina il commerciale Consecution dal CSV.
    'BR Car Service' → None (siamo noi, nessun dato consultativo)
    Altro nome → nome come dato consultativo
    """
    comm = row.get('Commerciale (Email)', '').strip()
    if not comm or comm == 'BR Car Service':
        return None
    return comm


# ==============================================================================
# IMPORT PRINCIPALE
# ==============================================================================

def importa_accounts(csv_path, dry_run=False):
    """
    Funzione principale di import Accounts CRM.
    
    Args:
        csv_path: Path al file CSV
        dry_run: Se True, non modifica il DB
        
    Returns:
        dict: statistiche import
    """
    stats = {
        'totale_csv': 0,
        'clienti_aggiornati': 0,
        'clienti_creati': 0,
        'clienti_errore': 0,
        'sedi_create': 0,
        'sedi_aggiornate': 0,
        'piva_non_valide': 0,
        'dettaglio_aggiornati': [],
        'dettaglio_creati': [],
        'dettaglio_errori': [],
    }
    
    # Leggi CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        righe = list(reader)
    
    stats['totale_csv'] = len(righe)
    print(f"\n  Record CSV letti: {stats['totale_csv']}")
    
    # Normalizza chiavi CSV (gestione accenti corrotti)
    righe = normalizza_chiavi_csv(righe)
    
    # Connessione DB
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        for i, row in enumerate(righe, 1):
            nome_azienda = row.get('Nome Azienda', '').strip()
            piva_raw = row.get('Partita IVA/CF', '').strip()
            cf_raw = row.get('Codice Fiscale', '').strip()
            
            # Normalizza identificativi
            piva_norm = normalizza_piva_crm(piva_raw)
            cf_norm = normalizza_cf_crm(cf_raw)
            
            if not piva_norm and not cf_norm:
                stats['piva_non_valide'] += 1
                stats['dettaglio_errori'].append(
                    f"  Riga {i}: [{nome_azienda}] - P.IVA/CF non validi "
                    f"(raw: PIVA=[{piva_raw}] CF=[{cf_raw}])")
                stats['clienti_errore'] += 1
                continue
            
            # Cerca cliente esistente
            cliente = cerca_cliente(cursor, piva_norm, cf_norm)
            
            if cliente:
                # ============================================================
                # CLIENTE ESISTENTE → Aggiorna solo campi CRM
                # ============================================================
                cliente_id = cliente['id']
                campi_modificati = []
                
                for campo_csv, campo_db in CAMPI_CRM_AGGIORNA.items():
                    valore_csv = row.get(campo_csv, '').strip()
                    if not valore_csv:
                        continue
                    
                    # Conversione tipo
                    if campo_db in CAMPI_INTERI:
                        try:
                            valore_csv = int(float(valore_csv))
                        except (ValueError, TypeError):
                            continue
                    
                    # Confronta con valore attuale
                    valore_attuale = cliente.get(campo_db)
                    if valore_attuale is not None:
                        valore_attuale = str(valore_attuale)
                    
                    if str(valore_csv) != (valore_attuale or ''):
                        campi_modificati.append(campo_db)
                        if not dry_run:
                            cursor.execute(
                                f"UPDATE clienti SET {campo_db} = ? WHERE id = ?",
                                (valore_csv, cliente_id))
                
                # Aggiorna PEC e telefono se nel DB sono vuoti
                for campo_csv, campo_db in [('Email PEC', 'pec'), ('Telefono', 'telefono')]:
                    valore_csv = row.get(campo_csv, '').strip()
                    valore_attuale = cliente.get(campo_db)
                    if valore_csv and not valore_attuale:
                        campi_modificati.append(campo_db)
                        if not dry_run:
                            cursor.execute(
                                f"UPDATE clienti SET {campo_db} = ? WHERE id = ?",
                                (valore_csv, cliente_id))
                
                # Commerciale Consecution (dato consultativo)
                comm_cons = get_commerciale_consecution(row)
                if comm_cons:
                    valore_attuale = cliente.get('commerciale_consecution')
                    if comm_cons != (valore_attuale or ''):
                        campi_modificati.append('commerciale_consecution')
                        if not dry_run:
                            cursor.execute(
                                "UPDATE clienti SET commerciale_consecution = ? WHERE id = ?",
                                (comm_cons, cliente_id))
                
                # Timestamp aggiornamento
                if campi_modificati and not dry_run:
                    cursor.execute(
                        "UPDATE clienti SET data_ultimo_aggiornamento = ? WHERE id = ?",
                        (now, cliente_id))
                
                stats['clienti_aggiornati'] += 1
                stats['dettaglio_aggiornati'].append(
                    f"  [{nome_azienda}] PIVA={piva_norm or cf_norm} "
                    f"→ {len(campi_modificati)} campi: {', '.join(campi_modificati) if campi_modificati else 'nessuna modifica'}")
                
                # Sedi
                gestisci_sedi(cursor, cliente_id, row, dry_run, stats)
                
                # Tabelle satellite
                gestisci_consensi(cursor, cliente_id, row, dry_run)
                gestisci_dati_finanziari(cursor, cliente_id, row, dry_run)
                gestisci_alert(cursor, cliente_id, row, dry_run)
                gestisci_metadata(cursor, cliente_id, row, dry_run)
            
            else:
                # ============================================================
                # CLIENTE NUOVO → Crea record completo
                # ============================================================
                dati_nuovo = {
                    'p_iva': piva_norm or piva_raw,
                    'cod_fiscale': cf_norm or cf_raw or None,
                    'data_ultimo_aggiornamento': now,
                    'commerciale_id': COMMERCIALE_DEFAULT_ID,
                }
                
                # Campi creazione
                for campo_csv, campo_db in CAMPI_CRM_CREAZIONE.items():
                    valore = row.get(campo_csv, '').strip()
                    if valore and valore != '0':
                        dati_nuovo[campo_db] = valore
                
                # Campi CRM
                for campo_csv, campo_db in CAMPI_CRM_AGGIORNA.items():
                    valore = row.get(campo_csv, '').strip()
                    if valore:
                        if campo_db in CAMPI_INTERI:
                            try:
                                valore = int(float(valore))
                            except (ValueError, TypeError):
                                continue
                        dati_nuovo[campo_db] = valore
                
                # Commerciale Consecution
                comm_cons = get_commerciale_consecution(row)
                if comm_cons:
                    dati_nuovo['commerciale_consecution'] = comm_cons
                
                if not dry_run:
                    campi = list(dati_nuovo.keys())
                    placeholders = ', '.join(['?' for _ in campi])
                    query = f"INSERT INTO clienti ({', '.join(campi)}) VALUES ({placeholders})"
                    cursor.execute(query, list(dati_nuovo.values()))
                    cliente_id = cursor.lastrowid
                else:
                    cliente_id = -1  # Placeholder per dry-run
                
                stats['clienti_creati'] += 1
                stats['dettaglio_creati'].append(
                    f"  [{nome_azienda}] PIVA={piva_norm or cf_norm} "
                    f"→ NUOVO (stato: {dati_nuovo.get('stato_crm', 'N/D')})")
                
                # Sedi (solo se non dry-run, serve cliente_id reale)
                if not dry_run:
                    gestisci_sedi(cursor, cliente_id, row, dry_run, stats)
                    gestisci_consensi(cursor, cliente_id, row, dry_run)
                    gestisci_dati_finanziari(cursor, cliente_id, row, dry_run)
                    gestisci_alert(cursor, cliente_id, row, dry_run)
                    gestisci_metadata(cursor, cliente_id, row, dry_run)
        
        # Commit
        if not dry_run:
            conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"\n  ERRORE durante l'import: {e}")
        import traceback
        traceback.print_exc()
        stats['clienti_errore'] += 1
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
    print(f"{prefisso}RIEPILOGO IMPORT ACCOUNTS CRM")
    print("="*60)
    print(f"  Record CSV:          {stats['totale_csv']}")
    print(f"  Clienti aggiornati:  {stats['clienti_aggiornati']}")
    print(f"  Clienti creati:      {stats['clienti_creati']}")
    print(f"  Errori:              {stats['clienti_errore']}")
    print(f"  P.IVA non valide:    {stats['piva_non_valide']}")
    print(f"  Sedi create:         {stats['sedi_create']}")
    print(f"  Sedi aggiornate:     {stats['sedi_aggiornate']}")
    
    if stats['dettaglio_aggiornati']:
        print(f"\n--- Clienti AGGIORNATI ({stats['clienti_aggiornati']}) ---")
        for d in stats['dettaglio_aggiornati'][:50]:  # Max 50
            print(d)
        if len(stats['dettaglio_aggiornati']) > 50:
            print(f"  ... e altri {len(stats['dettaglio_aggiornati'])-50}")
    
    if stats['dettaglio_creati']:
        print(f"\n--- Clienti NUOVI ({stats['clienti_creati']}) ---")
        for d in stats['dettaglio_creati'][:50]:
            print(d)
        if len(stats['dettaglio_creati']) > 50:
            print(f"  ... e altri {len(stats['dettaglio_creati'])-50}")
    
    if stats['dettaglio_errori']:
        print(f"\n--- ERRORI ({stats['clienti_errore']}) ---")
        for d in stats['dettaglio_errori']:
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
    log_file = LOG_DIR / f"import_accounts_{modalita}_{timestamp}.log"
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Import Accounts CRM - {'DRY-RUN' if dry_run else 'ESECUZIONE'}\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"File: {csv_path}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"Record CSV:          {stats['totale_csv']}\n")
        f.write(f"Clienti aggiornati:  {stats['clienti_aggiornati']}\n")
        f.write(f"Clienti creati:      {stats['clienti_creati']}\n")
        f.write(f"Errori:              {stats['clienti_errore']}\n")
        f.write(f"P.IVA non valide:    {stats['piva_non_valide']}\n")
        f.write(f"Sedi create:         {stats['sedi_create']}\n")
        f.write(f"Sedi aggiornate:     {stats['sedi_aggiornate']}\n\n")
        
        if stats['dettaglio_aggiornati']:
            f.write(f"--- Clienti AGGIORNATI ---\n")
            for d in stats['dettaglio_aggiornati']:
                f.write(d + '\n')
            f.write('\n')
        
        if stats['dettaglio_creati']:
            f.write(f"--- Clienti NUOVI ---\n")
            for d in stats['dettaglio_creati']:
                f.write(d + '\n')
            f.write('\n')
        
        if stats['dettaglio_errori']:
            f.write(f"--- ERRORI ---\n")
            for d in stats['dettaglio_errori']:
                f.write(d + '\n')
    
    print(f"  Log salvato: {log_file}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    # Argomenti
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/import_accounts_crm.py <file.csv> [--dry-run]")
        print()
        print("Esempio:")
        print("  python3 scripts/import_accounts_crm.py import_dati/Accounts_2026_02_09.csv --dry-run")
        print("  python3 scripts/import_accounts_crm.py import_dati/Accounts_2026_02_09.csv")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv
    
    print("="*60)
    print("IMPORT ACCOUNTS CRM ZOHO")
    print("="*60)
    print(f"  File CSV:  {csv_path}")
    print(f"  Database:  {DB_FILE}")
    print(f"  Data:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modalita': {'DRY-RUN (nessuna modifica)' if dry_run else 'IMPORT REALE'}")
    
    # Verifica file
    if not csv_path.exists():
        # Prova anche con path relativo a gestione_flotta
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
        backup_path = DB_FILE.parent / f"gestionale_backup_pre_import_accounts_{timestamp}.db"
        shutil.copy2(DB_FILE, backup_path)
        print(f"  Backup creato: {backup_path.name}")
    
    # Import
    print("\n" + "-"*60)
    print("ELABORAZIONE")
    print("-"*60)
    
    try:
        stats = importa_accounts(csv_path, dry_run)
        stampa_risultati(stats, dry_run)
        salva_log(stats, csv_path, dry_run)
    except Exception as e:
        print(f"\n  ERRORE FATALE: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
