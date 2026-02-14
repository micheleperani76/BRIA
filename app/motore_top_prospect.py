#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Motore Top Prospect
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-01-29
# Descrizione: Logica di business per la funzionalit&agrave; Top Prospect
#              - Analisi candidati basata su parametri configurabili
#              - Gestione stati (candidato, confermato, archiviato)
#              - Storico attivit&agrave;
#
# ARCHITETTURA:
#   - Parametri configurabili in config_top_prospect.py
#   - Analisi periodica o on-demand dei candidati
#   - Persistenza stato in tabella top_prospect
#   - Storico completo in top_prospect_attivita
#
# ==============================================================================

import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

from app.database import get_connection
from app.config_top_prospect import (
    PARAMETRI_CANDIDATURA,
    LIVELLI_PRIORITA,
    PRIORITA_DEFAULT,
    get_parametri_candidatura,
    get_livello_priorita,
    get_icona_stato
)

# Import connettore notifiche
try:
    from app.connettori_notifiche.top_prospect import (
        notifica_nuovi_candidati
    )
    _NOTIFICHE_TP = True
except ImportError:
    _NOTIFICHE_TP = False
# ==============================================================================
# FUNZIONI ANALISI CANDIDATI
# ==============================================================================

def calcola_variazione_percentuale(valore_attuale, valore_precedente):
    """
    Calcola la variazione percentuale tra due valori.
    
    Returns:
        float: Variazione percentuale (es: -5.2 per -5.2%)
        None: Se i dati non sono validi
    """
    if valore_precedente is None or valore_attuale is None:
        return None
    
    try:
        valore_attuale = float(valore_attuale)
        valore_precedente = float(valore_precedente)
        
        if valore_precedente == 0:
            # Se il precedente era 0, non possiamo calcolare variazione %
            return None if valore_attuale == 0 else 100.0
        
        variazione = ((valore_attuale - valore_precedente) / abs(valore_precedente)) * 100
        return round(variazione, 2)
    except (TypeError, ValueError):
        return None


def conta_veicoli_cliente(conn, cliente_id, veicoli_rilevati=None):
    """
    Conta i veicoli di un cliente considerando due fonti:
    1. Veicoli nel database (tabella veicoli)
    2. Campo veicoli_rilevati (inserito manualmente)
    
    Args:
        conn: Connessione database
        cliente_id: ID cliente
        veicoli_rilevati: Valore dal campo manuale (opzionale, se gia disponibile)
    
    Returns:
        dict: {
            'veicoli_db': int,        # Conteggio da tabella veicoli
            'veicoli_rilevati': int,  # Valore manuale
            'veicoli_max': int        # Il maggiore tra i due
        }
    """
    cursor = conn.cursor()
    
    # Conteggio veicoli nel database
    cursor.execute('''
        SELECT COUNT(*) FROM veicoli_attivi WHERE cliente_id = ?
    ''', (cliente_id,))
    result = cursor.fetchone()
    veicoli_db = result[0] if result else 0
    
    # Se veicoli_rilevati non fornito, recuperalo dal cliente
    if veicoli_rilevati is None:
        cursor.execute('''
            SELECT veicoli_rilevati FROM clienti WHERE id = ?
        ''', (cliente_id,))
        result = cursor.fetchone()
        veicoli_rilevati = result[0] if result and result[0] else 0
    
    # Assicura che sia un intero
    try:
        veicoli_rilevati = int(veicoli_rilevati) if veicoli_rilevati else 0
    except (TypeError, ValueError):
        veicoli_rilevati = 0
    
    return {
        'veicoli_db': veicoli_db,
        'veicoli_rilevati': veicoli_rilevati,
        'veicoli_max': max(veicoli_db, veicoli_rilevati)
    }


def analizza_cliente_per_candidatura(conn, cliente: Dict) -> Tuple[bool, Dict]:
    """
    Analizza un singolo cliente per verificare se soddisfa i criteri.
    
    Args:
        conn: Connessione database
        cliente: Dict con dati cliente
    
    Returns:
        Tuple[bool, Dict]: (soddisfa_criteri, dettagli_analisi)
    """
    parametri = get_parametri_candidatura()
    cliente_id = cliente.get('id')
    
    dettagli = {
        'cliente_id': cliente_id,
        'nome_cliente': cliente.get('nome_cliente') or cliente.get('ragione_sociale'),
        'criteri_soddisfatti': [],
        'criteri_non_soddisfatti': [],
        'dati': {}
    }
    
    # -------------------------------------------------------------------------
    # CRITERIO: Dipendenti
    # -------------------------------------------------------------------------
    dipendenti = cliente.get('dipendenti')
    dipendenti_min = parametri['dipendenti_min']
    
    dettagli['dati']['dipendenti'] = dipendenti
    dettagli['dati']['dipendenti_min'] = dipendenti_min
    
    if dipendenti is not None and dipendenti >= dipendenti_min:
        dettagli['criteri_soddisfatti'].append(f'Dipendenti: {dipendenti} >= {dipendenti_min}')
    else:
        dettagli['criteri_non_soddisfatti'].append(
            f'Dipendenti: {dipendenti if dipendenti else "N/D"} < {dipendenti_min}'
        )
    
    # -------------------------------------------------------------------------
    # CRITERIO: Veicoli (DB + Rilevati manualmente)
    # -------------------------------------------------------------------------
    # Il criterio e soddisfatto se ALMENO UNO tra:
    # - Veicoli nel database (tabella veicoli)
    # - Veicoli rilevati (campo manuale)
    # supera la soglia minima
    
    veicoli_rilevati_campo = cliente.get('veicoli_rilevati')
    dati_veicoli = conta_veicoli_cliente(conn, cliente_id, veicoli_rilevati_campo)
    
    veicoli_db = dati_veicoli['veicoli_db']
    veicoli_rilevati = dati_veicoli['veicoli_rilevati']
    veicoli_max = dati_veicoli['veicoli_max']
    veicoli_min = parametri['veicoli_min']
    
    dettagli['dati']['veicoli_db'] = veicoli_db
    dettagli['dati']['veicoli_rilevati'] = veicoli_rilevati
    dettagli['dati']['veicoli_max'] = veicoli_max
    dettagli['dati']['veicoli_min'] = veicoli_min
    
    if veicoli_max >= veicoli_min:
        # Criterio soddisfatto - specifica quale fonte
        if veicoli_db >= veicoli_min and veicoli_rilevati >= veicoli_min:
            dettagli['criteri_soddisfatti'].append(
                f'Veicoli: DB={veicoli_db}, Rilevati={veicoli_rilevati} (entrambi >= {veicoli_min})'
            )
        elif veicoli_db >= veicoli_min:
            dettagli['criteri_soddisfatti'].append(
                f'Veicoli: DB={veicoli_db} >= {veicoli_min} (Rilevati={veicoli_rilevati})'
            )
        else:
            dettagli['criteri_soddisfatti'].append(
                f'Veicoli: Rilevati={veicoli_rilevati} >= {veicoli_min} (DB={veicoli_db})'
            )
    else:
        dettagli['criteri_non_soddisfatti'].append(
            f'Veicoli: DB={veicoli_db}, Rilevati={veicoli_rilevati} (nessuno >= {veicoli_min})'
        )
    
    # -------------------------------------------------------------------------
    # CRITERIO: Variazione Valore Produzione
    # -------------------------------------------------------------------------
    valore_prod = cliente.get('valore_produzione')
    valore_prod_prec = cliente.get('valore_produzione_prec')
    var_valore_prod = calcola_variazione_percentuale(valore_prod, valore_prod_prec)
    var_min = parametri['variazione_valore_produzione_min']
    
    dettagli['dati']['valore_produzione'] = valore_prod
    dettagli['dati']['valore_produzione_prec'] = valore_prod_prec
    dettagli['dati']['var_valore_prod'] = var_valore_prod
    dettagli['dati']['var_valore_prod_min'] = var_min
    
    if var_valore_prod is not None:
        if var_valore_prod >= var_min:
            dettagli['criteri_soddisfatti'].append(
                f'Var. Valore Produzione: {var_valore_prod:+.1f}% >= {var_min}%'
            )
        else:
            dettagli['criteri_non_soddisfatti'].append(
                f'Var. Valore Produzione: {var_valore_prod:+.1f}% < {var_min}%'
            )
    else:
        dettagli['criteri_non_soddisfatti'].append('Var. Valore Produzione: dati bilancio mancanti')
    
    # -------------------------------------------------------------------------
    # CRITERIO: Variazione Patrimonio Netto
    # -------------------------------------------------------------------------
    patrimonio = cliente.get('patrimonio_netto')
    patrimonio_prec = cliente.get('patrimonio_netto_prec')
    var_patrimonio = calcola_variazione_percentuale(patrimonio, patrimonio_prec)
    var_patr_min = parametri['variazione_patrimonio_netto_min']
    
    dettagli['dati']['patrimonio_netto'] = patrimonio
    dettagli['dati']['patrimonio_netto_prec'] = patrimonio_prec
    dettagli['dati']['var_patrimonio'] = var_patrimonio
    dettagli['dati']['var_patrimonio_min'] = var_patr_min
    
    if var_patrimonio is not None:
        if var_patrimonio >= var_patr_min:
            dettagli['criteri_soddisfatti'].append(
                f'Var. Patrimonio Netto: {var_patrimonio:+.1f}% >= {var_patr_min}%'
            )
        else:
            dettagli['criteri_non_soddisfatti'].append(
                f'Var. Patrimonio Netto: {var_patrimonio:+.1f}% < {var_patr_min}%'
            )
    else:
        dettagli['criteri_non_soddisfatti'].append('Var. Patrimonio Netto: dati bilancio mancanti')
    
    # -------------------------------------------------------------------------
    # CRITERI OPZIONALI
    # -------------------------------------------------------------------------
    
    # Valore produzione minimo assoluto
    vp_min = parametri.get('valore_produzione_min')
    if vp_min is not None and valore_prod is not None:
        if valore_prod >= vp_min:
            dettagli['criteri_soddisfatti'].append(
                f'Valore Produzione: {valore_prod:,.0f} >= {vp_min:,.0f}'
            )
        else:
            dettagli['criteri_non_soddisfatti'].append(
                f'Valore Produzione: {valore_prod:,.0f} < {vp_min:,.0f}'
            )
    
    # Patrimonio netto minimo assoluto
    pn_min = parametri.get('patrimonio_netto_min')
    if pn_min is not None and patrimonio is not None:
        if patrimonio >= pn_min:
            dettagli['criteri_soddisfatti'].append(
                f'Patrimonio Netto: {patrimonio:,.0f} >= {pn_min:,.0f}'
            )
        else:
            dettagli['criteri_non_soddisfatti'].append(
                f'Patrimonio Netto: {patrimonio:,.0f} < {pn_min:,.0f}'
            )
    
    # Score massimo
    score_max = parametri.get('score_max')
    score_cliente = cliente.get('score')
    if score_max is not None and score_cliente:
        ordine_score = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
        score_ord = ordine_score.get(score_cliente.upper(), 99)
        max_ord = ordine_score.get(score_max.upper(), 99)
        
        if score_ord <= max_ord:
            dettagli['criteri_soddisfatti'].append(f'Score: {score_cliente} <= {score_max}')
        else:
            dettagli['criteri_non_soddisfatti'].append(f'Score: {score_cliente} > {score_max}')
    
    # -------------------------------------------------------------------------
    # RISULTATO FINALE
    # -------------------------------------------------------------------------
    # Soddisfa criteri se non ci sono criteri non soddisfatti tra quelli obbligatori
    # I criteri obbligatori sono: dipendenti, veicoli, var_valore_prod, var_patrimonio
    
    soddisfa = len(dettagli['criteri_non_soddisfatti']) == 0
    
    return soddisfa, dettagli


def esegui_analisi_candidati(conn, utente_id: int = None) -> Dict:
    """
    Esegue l'analisi completa di tutti i clienti per trovare nuovi candidati.
    
    Args:
        conn: Connessione database
        utente_id: ID utente che esegue l'analisi (per log)
    
    Returns:
        Dict: {
            'nuovi_candidati': [...],
            'totale_analizzati': int,
            'totale_candidati': int,
            'data_esecuzione': str
        }
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Recupera tutti i clienti con dati bilancio
    cursor.execute('''
        SELECT c.*, 
               (SELECT COUNT(*) FROM veicoli_attivi v WHERE v.cliente_id = c.id) as num_veicoli
        FROM clienti c
        WHERE c.dipendenti IS NOT NULL
          AND c.valore_produzione IS NOT NULL
          AND c.patrimonio_netto IS NOT NULL
    ''')
    
    clienti = [dict(row) for row in cursor.fetchall()]
    
    nuovi_candidati = []
    totale_analizzati = len(clienti)
    
    # Recupera clienti gia in top_prospect (escludi da analisi)
    cursor.execute('SELECT cliente_id FROM top_prospect WHERE stato IN ("candidato", "confermato")')
    clienti_esistenti = {row[0] for row in cursor.fetchall()}
    
    for cliente in clienti:
        cliente_id = cliente['id']
        
        # Salta se gia presente
        if cliente_id in clienti_esistenti:
            continue
        
        # Analizza
        soddisfa, dettagli = analizza_cliente_per_candidatura(conn, cliente)
        
        if soddisfa:
            # Inserisci come nuovo candidato
            cursor.execute('''
                INSERT INTO top_prospect 
                (cliente_id, stato, data_candidatura, 
                 snapshot_dipendenti, snapshot_veicoli, 
                 snapshot_var_valore_prod, snapshot_var_patrimonio,
                 data_creazione, data_ultimo_aggiornamento)
                VALUES (?, 'candidato', ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cliente_id, now,
                dettagli['dati'].get('dipendenti'),
                dettagli['dati'].get('veicoli_max'),  # Usa il max tra DB e Rilevati
                dettagli['dati'].get('var_valore_prod'),
                dettagli['dati'].get('var_patrimonio'),
                now, now
            ))
            
            tp_id = cursor.lastrowid
            
            # Registra attivita
            cursor.execute('''
                INSERT INTO top_prospect_attivita
                (top_prospect_id, tipo_attivita, descrizione, dettaglio_json, utente_id, data_ora)
                VALUES (?, 'candidatura', ?, ?, ?, ?)
            ''', (
                tp_id,
                f"Candidato automaticamente: soddisfa {len(dettagli['criteri_soddisfatti'])} criteri",
                json.dumps(dettagli, ensure_ascii=False),
                utente_id,
                now
            ))
            
            nuovi_candidati.append({
                'top_prospect_id': tp_id,
                'cliente_id': cliente_id,
                'nome_cliente': dettagli['nome_cliente'],
                'dettagli': dettagli
            })
    
    # Salva storico parametri
    cursor.execute('''
        INSERT INTO top_prospect_parametri_storico
        (parametri_json, clienti_analizzati, candidati_trovati, eseguito_da_id, data_esecuzione)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        json.dumps(get_parametri_candidatura(), ensure_ascii=False),
        totale_analizzati,
        len(nuovi_candidati),
        utente_id,
        now
    ))
    
    conn.commit()
    

    # Notifica nuovi candidati
    if _NOTIFICHE_TP and nuovi_candidati:
        try:
            notifica_nuovi_candidati(conn, nuovi_candidati)
        except Exception:
            pass

    return {
        'nuovi_candidati': nuovi_candidati,
        'totale_analizzati': totale_analizzati,
        'totale_candidati': len(nuovi_candidati),
        'data_esecuzione': now
    }


# ==============================================================================
# FUNZIONI GESTIONE STATI
# ==============================================================================

def conferma_top_prospect(conn, top_prospect_id: int, utente_id: int, 
                          priorita: int = None, note: str = None) -> bool:
    """
    Conferma un candidato come Top Prospect.
    
    Args:
        conn: Connessione database
        top_prospect_id: ID record top_prospect
        utente_id: ID utente che conferma
        priorita: Livello priorita (1-5), default da config
        note: Note opzionali
    
    Returns:
        bool: True se confermato con successo
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if priorita is None:
        priorita = PRIORITA_DEFAULT
    
    # Verifica che esista e sia candidato
    cursor.execute('''
        SELECT id, stato, cliente_id FROM top_prospect WHERE id = ?
    ''', (top_prospect_id,))
    
    row = cursor.fetchone()
    if not row:
        return False
    
    if row[1] != 'candidato':
        return False  # Gia confermato o archiviato
    
    # Aggiorna stato
    cursor.execute('''
        UPDATE top_prospect
        SET stato = 'confermato',
            priorita = ?,
            data_conferma = ?,
            confermato_da_id = ?,
            note_conferma = ?,
            data_ultimo_aggiornamento = ?
        WHERE id = ?
    ''', (priorita, now, utente_id, note, now, top_prospect_id))
    
    # Registra attivita
    livello = get_livello_priorita(priorita)
    cursor.execute('''
        INSERT INTO top_prospect_attivita
        (top_prospect_id, tipo_attivita, descrizione, utente_id, data_ora)
        VALUES (?, 'conferma', ?, ?, ?)
    ''', (
        top_prospect_id,
        f"Confermato come Top Prospect con priorita {livello['nome']}",
        utente_id,
        now
    ))
    
    conn.commit()
    return True


def archivia_top_prospect(conn, top_prospect_id: int, utente_id: int, 
                          note: str = None) -> bool:
    """
    Archivia un Top Prospect (rimuove icone e visibilita).
    
    Args:
        conn: Connessione database
        top_prospect_id: ID record top_prospect
        utente_id: ID utente che archivia
        note: Note opzionali
    
    Returns:
        bool: True se archiviato con successo
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Verifica che esista e sia confermato
    cursor.execute('''
        SELECT id, stato FROM top_prospect WHERE id = ?
    ''', (top_prospect_id,))
    
    row = cursor.fetchone()
    if not row or row[1] != 'confermato':
        return False
    
    # Aggiorna stato
    cursor.execute('''
        UPDATE top_prospect
        SET stato = 'archiviato',
            data_archiviazione = ?,
            archiviato_da_id = ?,
            note_archiviazione = ?,
            data_ultimo_aggiornamento = ?
        WHERE id = ?
    ''', (now, utente_id, note, now, top_prospect_id))
    
    # Registra attivita
    cursor.execute('''
        INSERT INTO top_prospect_attivita
        (top_prospect_id, tipo_attivita, descrizione, utente_id, data_ora)
        VALUES (?, 'archiviazione', ?, ?, ?)
    ''', (
        top_prospect_id,
        f"Archiviato{': ' + note if note else ''}",
        utente_id,
        now
    ))
    
    conn.commit()
    return True


def ripristina_top_prospect(conn, top_prospect_id: int, utente_id: int) -> bool:
    """
    Ripristina un Top Prospect archiviato.
    
    Returns:
        bool: True se ripristinato con successo
    """
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Verifica che esista e sia archiviato
    cursor.execute('''
        SELECT id, stato FROM top_prospect WHERE id = ?
    ''', (top_prospect_id,))
    
    row = cursor.fetchone()
    if not row or row[1] != 'archiviato':
        return False
    
    # Aggiorna stato
    cursor.execute('''
        UPDATE top_prospect
        SET stato = 'confermato',
            data_archiviazione = NULL,
            archiviato_da_id = NULL,
            note_archiviazione = NULL,
            data_ultimo_aggiornamento = ?
        WHERE id = ?
    ''', (now, top_prospect_id))
    
    # Registra attivita
    cursor.execute('''
        INSERT INTO top_prospect_attivita
        (top_prospect_id, tipo_attivita, descrizione, utente_id, data_ora)
        VALUES (?, 'ripristino', 'Ripristinato da archivio', ?, ?)
    ''', (top_prospect_id, utente_id, now))
    
    conn.commit()
    return True


def aggiorna_priorita(conn, top_prospect_id: int, nuova_priorita: int, 
                      utente_id: int) -> bool:
    """
    Aggiorna la priorita di un Top Prospect confermato.
    
    Returns:
        bool: True se aggiornato con successo
    """
    if nuova_priorita not in LIVELLI_PRIORITA:
        return False
    
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Verifica che esista e sia confermato
    cursor.execute('''
        SELECT id, stato, priorita FROM top_prospect WHERE id = ?
    ''', (top_prospect_id,))
    
    row = cursor.fetchone()
    if not row or row[1] != 'confermato':
        return False
    
    vecchia_priorita = row[2]
    
    # Aggiorna
    cursor.execute('''
        UPDATE top_prospect
        SET priorita = ?, data_ultimo_aggiornamento = ?
        WHERE id = ?
    ''', (nuova_priorita, now, top_prospect_id))
    
    # Registra attivita
    livello_vecchio = get_livello_priorita(vecchia_priorita)
    livello_nuovo = get_livello_priorita(nuova_priorita)
    
    cursor.execute('''
        INSERT INTO top_prospect_attivita
        (top_prospect_id, tipo_attivita, descrizione, dettaglio_json, utente_id, data_ora)
        VALUES (?, 'modifica_priorita', ?, ?, ?, ?)
    ''', (
        top_prospect_id,
        f"Priorita modificata: {livello_vecchio['nome']} -> {livello_nuovo['nome']}",
        json.dumps({'da': vecchia_priorita, 'a': nuova_priorita}),
        utente_id,
        now
    ))
    
    conn.commit()
    return True


def scarta_candidato(conn, top_prospect_id: int, utente_id: int, 
                     note: str = None) -> bool:
    """
    Scarta un candidato (non diventa Top Prospect).
    Lo elimina dalla tabella top_prospect.
    
    Returns:
        bool: True se scartato con successo
    """
    cursor = conn.cursor()
    
    # Verifica che esista e sia candidato
    cursor.execute('''
        SELECT id, stato FROM top_prospect WHERE id = ?
    ''', (top_prospect_id,))
    
    row = cursor.fetchone()
    if not row or row[1] != 'candidato':
        return False
    
    # Elimina (hard delete per candidati scartati)
    cursor.execute('DELETE FROM top_prospect WHERE id = ?', (top_prospect_id,))
    
    conn.commit()
    return True


# ==============================================================================
# FUNZIONI QUERY
# ==============================================================================

def get_candidati(conn) -> List[Dict]:
    """Restituisce lista candidati con dati cliente."""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tp.*, 
               c.nome_cliente, c.ragione_sociale, c.provincia, c.dipendenti,
               c.valore_produzione, c.valore_produzione_prec,
               c.patrimonio_netto, c.patrimonio_netto_prec,
               c.p_iva, c.cod_fiscale, c.veicoli_rilevati,
               (SELECT COUNT(*) FROM veicoli_attivi v WHERE v.cliente_id = c.id) as num_veicoli
        FROM top_prospect tp
        JOIN clienti c ON tp.cliente_id = c.id
        WHERE tp.stato = 'candidato'
        ORDER BY tp.data_candidatura DESC
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def get_top_prospect_confermati(conn, filtro_priorita: int = None) -> List[Dict]:
    """
    Restituisce lista Top Prospect confermati con dati cliente.
    Ordinati per priorita (1 prima) poi per nome.
    """
    cursor = conn.cursor()
    
    query = '''
        SELECT tp.*, 
               c.nome_cliente, c.ragione_sociale, c.provincia, c.dipendenti,
               c.p_iva, c.cod_fiscale, c.veicoli_rilevati,
               (SELECT COUNT(*) FROM veicoli_attivi v WHERE v.cliente_id = c.id) as num_veicoli,
               (SELECT data_appuntamento FROM top_prospect_appuntamenti 
                WHERE top_prospect_id = tp.id AND completato = 1 
                ORDER BY data_appuntamento DESC LIMIT 1) as ultimo_appuntamento,
               (SELECT data_appuntamento FROM top_prospect_appuntamenti 
                WHERE top_prospect_id = tp.id AND completato = 0 AND data_appuntamento >= date('now')
                ORDER BY data_appuntamento ASC LIMIT 1) as prossimo_appuntamento,
               (SELECT COUNT(*) FROM top_prospect_note 
                WHERE top_prospect_id = tp.id AND eliminato = 0) as note_count
        FROM top_prospect tp
        JOIN clienti c ON tp.cliente_id = c.id
        WHERE tp.stato = 'confermato'
    '''
    
    params = []
    if filtro_priorita:
        query += ' AND tp.priorita = ?'
        params.append(filtro_priorita)
    
    query += ' ORDER BY tp.priorita ASC, c.nome_cliente ASC'
    
    cursor.execute(query, params)
    
    return [dict(row) for row in cursor.fetchall()]


def get_top_prospect_archiviati(conn) -> List[Dict]:
    """Restituisce lista Top Prospect archiviati."""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tp.*, 
               c.nome_cliente, c.ragione_sociale, c.provincia,
               c.p_iva, c.cod_fiscale,
               u.cognome as archiviato_da_nome
        FROM top_prospect tp
        JOIN clienti c ON tp.cliente_id = c.id
        LEFT JOIN utenti u ON tp.archiviato_da_id = u.id
        WHERE tp.stato = 'archiviato'
        ORDER BY tp.data_archiviazione DESC
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def get_stato_top_prospect_cliente(conn, cliente_id: int) -> Optional[Dict]:
    """
    Restituisce lo stato Top Prospect di un cliente.
    
    Returns:
        Dict con stato e dettagli, o None se non e Top Prospect
    """
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, stato, priorita, data_conferma
        FROM top_prospect 
        WHERE cliente_id = ? AND stato IN ('candidato', 'confermato')
    ''', (cliente_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return {
        'top_prospect_id': row[0],
        'stato': row[1],
        'priorita': row[2],
        'data_conferma': row[3],
        'icona': get_icona_stato(row[1])
    }


def get_storico_attivita(conn, top_prospect_id: int, limite: int = 50) -> List[Dict]:
    """Restituisce lo storico attivita di un Top Prospect."""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tpa.*, u.nome, u.cognome
        FROM top_prospect_attivita tpa
        LEFT JOIN utenti u ON tpa.utente_id = u.id
        WHERE tpa.top_prospect_id = ?
        ORDER BY tpa.data_ora DESC
        LIMIT ?
    ''', (top_prospect_id, limite))
    
    return [dict(row) for row in cursor.fetchall()]


def get_prossimi_appuntamenti(conn, limite: int = 5, giorni: int = 30) -> List[Dict]:
    """
    Restituisce i prossimi appuntamenti per il banner.
    
    Args:
        conn: Connessione database
        limite: Numero massimo appuntamenti
        giorni: Giorni in avanti da considerare
    """
    cursor = conn.cursor()
    
    data_limite = (date.today() + timedelta(days=giorni)).strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT tpa.*, tp.cliente_id,
               c.nome_cliente, c.ragione_sociale
        FROM top_prospect_appuntamenti tpa
        JOIN top_prospect tp ON tpa.top_prospect_id = tp.id
        JOIN clienti c ON tp.cliente_id = c.id
        WHERE tpa.completato = 0
          AND tpa.data_appuntamento >= date('now')
          AND tpa.data_appuntamento <= ?
          AND tp.stato = 'confermato'
        ORDER BY tpa.data_appuntamento ASC, tpa.ora_appuntamento ASC
        LIMIT ?
    ''', (data_limite, limite))
    
    return [dict(row) for row in cursor.fetchall()]


# ==============================================================================
# FUNZIONI CONTEGGIO
# ==============================================================================

def get_conteggi_top_prospect(conn) -> Dict:
    """Restituisce i conteggi per le varie sezioni."""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT stato, COUNT(*) as count
        FROM top_prospect
        GROUP BY stato
    ''')
    
    conteggi = {'candidati': 0, 'confermati': 0, 'archiviati': 0}
    
    for row in cursor.fetchall():
        if row[0] == 'candidato':
            conteggi['candidati'] = row[1]
        elif row[0] == 'confermato':
            conteggi['confermati'] = row[1]
        elif row[0] == 'archiviato':
            conteggi['archiviati'] = row[1]
    
    return conteggi
