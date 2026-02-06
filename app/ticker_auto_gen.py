#!/usr/bin/env python3
# ==============================================================================
# TICKER AUTO-GEN - Generatore automatico messaggi
# ==============================================================================
# Versione: 1.0
# Data: 2026-02-06
#
# Genera messaggi automatici nel ticker per:
#   1. COMPLEANNI
#      - Da -5 a -1 giorni: reminder a TUTTI ("Il compleanno di X e' il GG/MM")
#      - Il giorno stesso: auguri al FESTEGGIATO (dopo login, ripetuto random)
#      - Se weekend/festivita: spostato al primo giorno lavorativo successivo
#
#   2. FESTIVITA NAZIONALI
#      - Da -7 a -5 giorni prima: reminder a TUTTI ("Il GG/MM sara' [festa]")
#
#   3. CAMBIO GOMME
#      - Da -30 giorni prima della scadenza: ogni giorno a TUTTI
#      - Date: 15 ottobre (invernali), 15 aprile (estive)
#
#   4. DEPOSITO BILANCIO
#      - Da -30 giorni prima della scadenza ordinaria (30 maggio)
#      - Reminder giornaliero a TUTTI
#
# USO:
#   python3 app/ticker_auto_gen.py          (esecuzione diretta)
#   Oppure via cron: 0 0 * * * cd ~/gestione_flotta && python3 app/ticker_auto_gen.py
#
# ==============================================================================

import sqlite3
import os
import sys
from datetime import datetime, date, timedelta

BASE_DIR = os.path.expanduser('~/gestione_flotta')
DB_PATH = os.path.join(BASE_DIR, 'db', 'gestionale.db')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# ==============================================================================
# CONFIGURAZIONE SCADENZE FISSE
# ==============================================================================

# Cambio gomme: giorno, mese
GOMME_INVERNALI = (15, 10)   # 15 ottobre
GOMME_ESTIVE = (15, 4)       # 15 aprile

# Deposito bilancio: scadenza ordinaria
DEPOSITO_BILANCIO_GIORNO = 30
DEPOSITO_BILANCIO_MESE = 5   # 30 maggio

# ==============================================================================
# UTILITY
# ==============================================================================

def log(msg):
    """Scrive nel log e stdout."""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linea = f'[{ts}] {msg}'
    print(linea)
    
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, 'ticker_auto_gen.log')
    with open(log_file, 'a') as f:
        f.write(linea + '\n')


def get_db():
    """Connessione database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_config_bool(conn, chiave, default=True):
    """Legge configurazione booleana."""
    cur = conn.cursor()
    cur.execute('SELECT valore FROM ticker_config WHERE chiave = ?', (chiave,))
    row = cur.fetchone()
    if row:
        return row['valore'] == '1'
    return default


def messaggio_esiste_oggi(conn, tipo_auto, riferimento):
    """Controlla se un messaggio automatico e' gia' stato creato oggi."""
    oggi = date.today().isoformat()
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM ticker_messaggi
        WHERE tipo = 'automatico'
        AND codice_auto LIKE ?
        AND date(data_creazione) = ?
    ''', (f'%{tipo_auto}:{riferimento}%', oggi))
    return cur.fetchone()[0] > 0


def crea_messaggio_auto(conn, testo, icona, destinatari, data_inizio, data_fine,
                        ora_inizio='08:00', ora_fine='18:00', giorni='1,2,3,4,5',
                        animazione='scroll-rtl', durata=8, velocita='normale',
                        priorita=5, peso=1, codice_auto=''):
    """Crea un messaggio automatico approvato."""
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO ticker_messaggi
        (testo, icona, colore_testo, animazione, durata_secondi, velocita,
         data_inizio, data_fine, ora_inizio, ora_fine, giorni_settimana,
         destinatari, priorita, peso, tipo, stato, ricorrenza, codice_auto,
         creato_da, approvato_da, data_approvazione)
        VALUES (?, ?, '#000000', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'automatico',
                'approvato', 'nessuna', ?, 1, 1, datetime('now', 'localtime'))
    ''', (testo, icona, animazione, durata, velocita,
          data_inizio, data_fine, ora_inizio, ora_fine, giorni,
          destinatari, priorita, peso, codice_auto))
    conn.commit()
    return cur.lastrowid


def calcola_pasqua(anno):
    """Calcola la data di Pasqua (algoritmo di Gauss)."""
    a = anno % 19
    b = anno // 100
    c = anno % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mese = (h + l - 7 * m + 114) // 31
    giorno = ((h + l - 7 * m + 114) % 31) + 1
    return date(anno, mese, giorno)


def get_festivita_fisse(conn, anno):
    """Ritorna lista date festivita (fisse + Pasqua/Pasquetta)."""
    cur = conn.cursor()
    cur.execute('''
        SELECT nome, giorno, mese FROM ticker_festivita
        WHERE attiva = 1
    ''')
    
    festivita = {}
    for r in cur.fetchall():
        try:
            d = date(anno, r['mese'], r['giorno'])
            festivita[d] = r['nome']
        except ValueError:
            pass
    
    # Aggiungi Pasqua e Pasquetta (mobili)
    pasqua = calcola_pasqua(anno)
    pasquetta = pasqua + timedelta(days=1)
    festivita[pasqua] = 'Pasqua'
    festivita[pasquetta] = 'Lunedi dell\'Angelo'
    
    return festivita


def e_giorno_lavorativo(data_check, festivita_dict):
    """Controlla se una data e' un giorno lavorativo."""
    if data_check.weekday() >= 5:  # sabato=5, domenica=6
        return False
    if data_check in festivita_dict:
        return False
    return True


def primo_giorno_lavorativo_dopo(data_check, festivita_dict):
    """Trova il primo giorno lavorativo dal giorno dato in poi."""
    d = data_check
    while not e_giorno_lavorativo(d, festivita_dict):
        d += timedelta(days=1)
    return d


# ==============================================================================
# GENERATORE 1: COMPLEANNI
# ==============================================================================

def genera_compleanni(conn, oggi, festivita_dict):
    """
    Genera messaggi compleanni:
    - Da -5 a -1: reminder a TUTTI
    - Giorno stesso (o primo lavorativo): auguri al FESTEGGIATO
    """
    log('--- Generatore COMPLEANNI ---')
    
    cur = conn.cursor()
    cur.execute('''
        SELECT id, nome, cognome, data_nascita
        FROM utenti
        WHERE attivo = 1 AND data_nascita IS NOT NULL AND data_nascita != ''
    ''')
    utenti = cur.fetchall()
    
    creati = 0
    
    for u in utenti:
        try:
            dn = datetime.strptime(u['data_nascita'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue
        
        nome_completo = f"{u['nome'] or ''} {u['cognome'] or ''}".strip()
        if not nome_completo:
            continue
        
        # Data compleanno quest'anno
        try:
            compleanno = date(oggi.year, dn.month, dn.day)
        except ValueError:
            # 29 febbraio in anno non bisestile
            compleanno = date(oggi.year, 3, 1)
        
        # Se il compleanno cade in weekend/festivita, lo spostiamo
        giorno_auguri = primo_giorno_lavorativo_dopo(compleanno, festivita_dict)
        
        diff = (compleanno - oggi).days
        
        # REMINDER: da -5 a -1 giorni prima del compleanno
        if 1 <= diff <= 5:
            rif = f'compleanno_reminder:{u["id"]}:{compleanno.isoformat()}'
            if not messaggio_esiste_oggi(conn, 'compleanno_reminder', f'{u["id"]}:{compleanno.isoformat()}'):
                data_compl_fmt = compleanno.strftime('%d/%m')
                testo = f'Il compleanno di {nome_completo} e\' il {data_compl_fmt}!'
                
                crea_messaggio_auto(
                    conn, testo=testo, icona='calendar-heart',
                    destinatari='TUTTI',
                    data_inizio=oggi.isoformat(),
                    data_fine=oggi.isoformat(),
                    animazione='scroll-rtl', durata=10,
                    priorita=4, peso=1,
                    codice_auto=f'auto:compleanno_reminder:{u["id"]}:{compleanno.isoformat()}'
                )
                creati += 1
                log(f'  Reminder compleanno: {nome_completo} ({data_compl_fmt})')
        
        # AUGURI: il giorno stesso (o primo lavorativo)
        if oggi == giorno_auguri:
            rif = f'compleanno_auguri:{u["id"]}:{compleanno.isoformat()}'
            if not messaggio_esiste_oggi(conn, 'compleanno_auguri', f'{u["id"]}:{compleanno.isoformat()}'):
                eta = oggi.year - dn.year
                testo = f'Buon Compleanno {nome_completo}! Auguri!'
                
                crea_messaggio_auto(
                    conn, testo=testo, icona='balloon-heart',
                    destinatari=f'UTENTE:{u["id"]}',
                    data_inizio=oggi.isoformat(),
                    data_fine=oggi.isoformat(),
                    ora_inizio='00:00', ora_fine='23:59',
                    giorni='1,2,3,4,5,6,7',
                    animazione='fade', durata=8,
                    priorita=9, peso=5,
                    codice_auto=f'auto:compleanno_auguri:{u["id"]}:{compleanno.isoformat()}'
                )
                creati += 1
                log(f'  Auguri compleanno: {nome_completo} ({eta} anni)')
    
    log(f'  Compleanni: {creati} messaggi creati')
    return creati


# ==============================================================================
# GENERATORE 2: FESTIVITA NAZIONALI
# ==============================================================================

def genera_festivita(conn, oggi, festivita_dict):
    """
    Genera reminder festivita:
    - Da -7 a -5 giorni prima: "Il GG/MM sara' [nome festa]"
    """
    log('--- Generatore FESTIVITA ---')
    
    creati = 0
    
    for data_festa, nome_festa in festivita_dict.items():
        diff = (data_festa - oggi).days
        
        # Reminder da 7 a 5 giorni prima
        if 5 <= diff <= 7:
            rif = f'festivita:{nome_festa}:{data_festa.isoformat()}'
            if not messaggio_esiste_oggi(conn, 'festivita', f'{nome_festa}:{data_festa.isoformat()}'):
                data_fmt = data_festa.strftime('%d/%m')
                testo = f'Il {data_fmt} sara\' {nome_festa}'
                
                crea_messaggio_auto(
                    conn, testo=testo, icona='calendar-event',
                    destinatari='TUTTI',
                    data_inizio=oggi.isoformat(),
                    data_fine=oggi.isoformat(),
                    animazione='slide-up', durata=7,
                    priorita=3, peso=1,
                    codice_auto=f'auto:festivita:{nome_festa}:{data_festa.isoformat()}'
                )
                creati += 1
                log(f'  Festivita: {nome_festa} ({data_fmt})')
    
    log(f'  Festivita: {creati} messaggi creati')
    return creati


# ==============================================================================
# GENERATORE 3: CAMBIO GOMME
# ==============================================================================

def genera_cambio_gomme(conn, oggi, festivita_dict):
    """
    Reminder cambio gomme:
    - Da -30 giorni prima: ogni giorno a TUTTI
    - 15 ottobre (invernali), 15 aprile (estive)
    """
    log('--- Generatore CAMBIO GOMME ---')
    
    creati = 0
    
    scadenze = [
        (date(oggi.year, GOMME_INVERNALI[1], GOMME_INVERNALI[0]), 'invernali'),
        (date(oggi.year, GOMME_ESTIVE[1], GOMME_ESTIVE[0]), 'estive'),
    ]
    
    for data_scad, tipo_gomme in scadenze:
        diff = (data_scad - oggi).days
        
        if 0 <= diff <= 30:
            rif = f'gomme:{tipo_gomme}:{data_scad.isoformat()}'
            if not messaggio_esiste_oggi(conn, 'gomme', f'{tipo_gomme}:{data_scad.isoformat()}'):
                data_fmt = data_scad.strftime('%d/%m')
                if diff == 0:
                    testo = f'Oggi {data_fmt}: ultimo giorno per il cambio gomme {tipo_gomme}!'
                    priorita = 8
                elif diff <= 7:
                    testo = f'Mancano {diff} giorni al cambio gomme {tipo_gomme} ({data_fmt})'
                    priorita = 6
                else:
                    testo = f'Promemoria: cambio gomme {tipo_gomme} entro il {data_fmt} - mancano {diff} giorni'
                    priorita = 4
                
                crea_messaggio_auto(
                    conn, testo=testo, icona='gear-wide-connected',
                    destinatari='TUTTI',
                    data_inizio=oggi.isoformat(),
                    data_fine=oggi.isoformat(),
                    animazione='scroll-rtl', durata=10,
                    priorita=priorita, peso=2,
                    codice_auto=f'auto:gomme:{tipo_gomme}:{data_scad.isoformat()}'
                )
                creati += 1
                log(f'  Gomme {tipo_gomme}: {diff} giorni alla scadenza')
    
    log(f'  Cambio gomme: {creati} messaggi creati')
    return creati


# ==============================================================================
# GENERATORE 4: DEPOSITO BILANCIO
# ==============================================================================

def genera_deposito_bilancio(conn, oggi, festivita_dict):
    """
    Reminder deposito bilancio CCIAA:
    - Scadenza ordinaria: 30 maggio (approvazione entro 30 aprile)
    - Da -30 giorni: reminder giornaliero a TUTTI
    """
    log('--- Generatore DEPOSITO BILANCIO ---')
    
    creati = 0
    
    data_scad = date(oggi.year, DEPOSITO_BILANCIO_MESE, DEPOSITO_BILANCIO_GIORNO)
    diff = (data_scad - oggi).days
    
    if 0 <= diff <= 30:
        rif = f'deposito_bilancio:{data_scad.isoformat()}'
        if not messaggio_esiste_oggi(conn, 'deposito_bilancio', data_scad.isoformat()):
            data_fmt = data_scad.strftime('%d/%m')
            if diff == 0:
                testo = f'Oggi {data_fmt}: scadenza deposito bilancio CCIAA!'
                priorita = 9
            elif diff <= 7:
                testo = f'Deposito bilancio CCIAA: mancano {diff} giorni (scadenza {data_fmt})'
                priorita = 7
            else:
                testo = f'Promemoria: deposito bilancio CCIAA entro il {data_fmt} - mancano {diff} giorni'
                priorita = 5
            
            crea_messaggio_auto(
                conn, testo=testo, icona='bank',
                destinatari='TUTTI',
                data_inizio=oggi.isoformat(),
                data_fine=oggi.isoformat(),
                animazione='scroll-rtl', durata=10,
                priorita=priorita, peso=2,
                codice_auto=f'auto:deposito_bilancio:{data_scad.isoformat()}'
            )
            creati += 1
            log(f'  Deposito bilancio: {diff} giorni alla scadenza')
    
    log(f'  Deposito bilancio: {creati} messaggi creati')
    return creati


# ==============================================================================
# PULIZIA MESSAGGI SCADUTI
# ==============================================================================

def pulisci_scaduti(conn, oggi):
    """Segna come scaduti i messaggi automatici con data_fine passata."""
    cur = conn.cursor()
    cur.execute('''
        UPDATE ticker_messaggi
        SET stato = 'scaduto'
        WHERE stato = 'approvato'
        AND data_fine IS NOT NULL
        AND data_fine < ?
    ''', (oggi.isoformat(),))
    scaduti = cur.rowcount
    conn.commit()
    if scaduti > 0:
        log(f'  Pulizia: {scaduti} messaggi scaduti')
    return scaduti


# ==============================================================================
# MAIN
# ==============================================================================

def esegui():
    """Esecuzione principale."""
    log('=' * 60)
    log('TICKER AUTO-GEN - Inizio generazione')
    log('=' * 60)
    
    oggi = date.today()
    log(f'Data: {oggi.isoformat()} ({["Lun","Mar","Mer","Gio","Ven","Sab","Dom"][oggi.weekday()]})')
    
    conn = get_db()
    
    # Carica festivita per l'anno corrente
    festivita_dict = get_festivita_fisse(conn, oggi.year)
    log(f'Festivita caricate: {len(festivita_dict)}')
    
    totale = 0
    
    # === COMPLEANNI ===
    if get_config_bool(conn, 'auto_compleanni', True):
        totale += genera_compleanni(conn, oggi, festivita_dict)
    else:
        log('--- Compleanni: DISATTIVATO ---')
    
    # === FESTIVITA ===
    if get_config_bool(conn, 'auto_festivita', True):
        totale += genera_festivita(conn, oggi, festivita_dict)
    else:
        log('--- Festivita: DISATTIVATO ---')
    
    # === CAMBIO GOMME ===
    if get_config_bool(conn, 'auto_gomme', True):
        totale += genera_cambio_gomme(conn, oggi, festivita_dict)
    else:
        log('--- Cambio gomme: DISATTIVATO ---')
    
    # === DEPOSITO BILANCIO ===
    if get_config_bool(conn, 'auto_deposito_bilancio', True):
        totale += genera_deposito_bilancio(conn, oggi, festivita_dict)
    else:
        log('--- Deposito bilancio: DISATTIVATO ---')
    
    # === PULIZIA ===
    pulisci_scaduti(conn, oggi)
    
    conn.close()
    
    log('')
    log(f'TOTALE: {totale} messaggi generati')
    log('=' * 60)
    
    return totale


if __name__ == '__main__':
    esegui()
