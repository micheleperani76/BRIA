#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
CONNETTORE NOTIFICHE - REVISIONE VEICOLI
==============================================================================
Versione: 1.0.0
Data: 2026-02-06
Descrizione: Controlla scadenze revisione veicoli e genera notifiche.
             - Prima revisione: 5 anni dalla data immatricolazione
             - Successive: ogni 2 anni
             - Notifica a 60 giorni (INFO) e 30 giorni (AVVISO)
             - Solo giorni lavorativi (lun-ven)
             - Dedup settimanale (una notifica a settimana per veicolo)
             - Stop quando revisione_gestita = prossima scadenza

Uso:
    from app.connettori_notifiche.revisione import (
        calcola_prossima_revisione,
        check_revisioni
    )
==============================================================================
"""

from datetime import datetime
from app.motore_notifiche import pubblica_notifica


# ==============================================================================
# CALCOLO PROSSIMA REVISIONE
# ==============================================================================

def calcola_prossima_revisione(data_immatricolazione):
    """
    Calcola la data della prossima revisione.
    
    Regole italiane:
    - Prima revisione: 5 anni dalla data immatricolazione
    - Successive: ogni 2 anni
    
    Args:
        data_immatricolazione: stringa formato 'YYYY-MM-DD'
    
    Returns:
        tuple: (data_prossima_str, giorni_mancanti) o (None, None)
    """
    if not data_immatricolazione:
        return None, None
    
    try:
        imm = datetime.strptime(str(data_immatricolazione).strip(), '%Y-%m-%d')
    except (ValueError, TypeError):
        return None, None
    
    oggi = datetime.now().date()
    
    # Prima revisione: 5 anni
    try:
        prossima = imm.date().replace(year=imm.year + 5)
    except ValueError:
        # 29 febbraio -> 28 febbraio
        prossima = imm.date().replace(year=imm.year + 5, day=28)
    
    # Se gia' passata, aggiungi 2 anni fino a trovare la prossima futura
    while prossima < oggi:
        try:
            prossima = prossima.replace(year=prossima.year + 2)
        except ValueError:
            prossima = prossima.replace(year=prossima.year + 2, day=28)
    
    giorni = (prossima - oggi).days
    return prossima.strftime('%Y-%m-%d'), giorni


# ==============================================================================
# CHECK REVISIONI (per cron)
# ==============================================================================

def check_revisioni(conn):
    """
    Controlla tutti i veicoli e genera UNA notifica raggruppata per commerciale.
    Da chiamare dal cron giornaliero.
    
    Logica:
    - Solo giorni lavorativi (lun-ven)
    - Raggruppa per commerciale_id
    - Una sola notifica con conteggio veicoli
    - Link a pagina /revisioni
    - Dedup settimanale via codice_evento
    
    Args:
        conn: connessione DB (con row_factory)
    
    Returns:
        dict: {'controllati': N, 'notificati': N, 'motivo': '...'}
    """
    oggi = datetime.now()
    
    # Solo giorni lavorativi (lunedi=0, venerdi=4)
    if oggi.weekday() > 4:
        return {'controllati': 0, 'notificati': 0, 'motivo': 'Weekend'}
    
    cursor = conn.cursor()
    
    # Veicoli con data immatricolazione
    cursor.execute("""
        SELECT v.id, v.targa, v.marca, v.modello, v.tipo,
               v.data_immatricolazione, v.revisione_gestita,
               v.commerciale_id, v.nome_cliente
        FROM veicoli_attivi v
        WHERE v.data_immatricolazione IS NOT NULL
          AND v.data_immatricolazione != ''
          AND v.commerciale_id IS NOT NULL
    """)
    
    colonne = [desc[0] for desc in cursor.description]
    veicoli = [dict(zip(colonne, row)) for row in cursor.fetchall()]
    
    controllati = 0
    # Raggruppa per commerciale
    per_commerciale = {}
    
    for v in veicoli:
        controllati += 1
        
        prossima, giorni = calcola_prossima_revisione(v['data_immatricolazione'])
        
        if not prossima or giorni is None:
            continue
        
        # Skip se gia' gestita per questa scadenza
        if v.get('revisione_gestita') == prossima:
            continue
        
        # Solo entro 60 giorni
        if giorni > 60:
            continue
        
        comm_id = v['commerciale_id']
        if comm_id not in per_commerciale:
            per_commerciale[comm_id] = {'scaduti': 0, 'urgenti': 0, 'attenzione': 0, 'targhe': []}
        
        if giorni <= 0:
            per_commerciale[comm_id]['scaduti'] += 1
        elif giorni <= 30:
            per_commerciale[comm_id]['urgenti'] += 1
        else:
            per_commerciale[comm_id]['attenzione'] += 1
        
        per_commerciale[comm_id]['targhe'].append(v.get('targa', '?'))
    
    # Invia una notifica per commerciale
    notificati = 0
    settimana = oggi.strftime('%Y-W%W')
    
    for comm_id, info in per_commerciale.items():
        totale = info['scaduti'] + info['urgenti'] + info['attenzione']
        if totale == 0:
            continue
        
        # Livello: il peggiore
        if info['scaduti'] > 0:
            livello = 3
        elif info['urgenti'] > 0:
            livello = 2
        else:
            livello = 1
        
        # Messaggio
        parti = []
        if info['scaduti'] > 0:
            parti.append(f"{info['scaduti']} scadute")
        if info['urgenti'] > 0:
            parti.append(f"{info['urgenti']} entro 30gg")
        if info['attenzione'] > 0:
            parti.append(f"{info['attenzione']} entro 60gg")
        
        dettaglio = ', '.join(parti)
        targhe_txt = ', '.join(info['targhe'][:5])
        if len(info['targhe']) > 5:
            targhe_txt += f' e altre {len(info["targhe"]) - 5}'
        
        risultato = pubblica_notifica(
            conn=conn,
            categoria='SCADENZA_CONTRATTO',
            livello=livello,
            titolo=f'Revisioni: {totale} veicoli da gestire',
            messaggio=f'{dettaglio}\nTarghe: {targhe_txt}',
            connettore='revisione',
            codice_evento=f'revisioni_gruppo_{comm_id}_{settimana}',
            url_azione='/revisioni',
            etichetta_azione='Apri pagina Revisioni',
            destinatari_specifici=[comm_id]
        )
        
        if risultato and risultato.get('ok'):
            notificati += 1
    
    return {'controllati': controllati, 'notificati': notificati}


# ==============================================================================
# TEST STANDALONE
# ==============================================================================

if __name__ == '__main__':
    # Test calcolo
    print("Test calcolo prossima revisione:")
    test_cases = [
        '2020-03-15',  # 5 anni = 2025-03-15, gia' passata -> 2027-03-15
        '2021-06-01',  # 5 anni = 2026-06-01
        '2019-01-10',  # 5 anni = 2024-01-10, passata -> 2026-01-10, passata -> 2028-01-10
        '2023-02-28',  # 5 anni = 2028-02-28
    ]
    for data in test_cases:
        prossima, giorni = calcola_prossima_revisione(data)
        print(f"  Immatricolazione: {data} -> Prossima: {prossima} (tra {giorni} giorni)")
