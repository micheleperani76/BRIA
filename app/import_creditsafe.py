#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Import PDF Creditsafe
# ==============================================================================
# Versione: 2.3.2
# Data: 2026-02-10
# Descrizione: Estrazione dati da PDF Creditsafe e inserimento nel database
# Correzioni v1.0.2: Fix regex ATECO, descrizione attivita, capogruppo
# Correzioni v1.0.3: Cancellazione vecchio PDF quando importa nuovo report
# Correzioni v1.0.4: Fix indirizzi troncati da layout PDF a due colonne
# Correzioni v1.0.5: Ricomposizione indirizzi con lista province ufficiale
# Correzioni v1.0.6: Parsing indirizzo in componenti (via, civico, cap, citta, provincia)
# Correzioni v1.0.7: Fix ricomposizione con testo mescolato (es: "25020 C" + "...IGOLE BS")
# Correzioni v2.1.0: Fix accento attivita/attività, euro €/&euro;, valori negativi bilancio
# Correzioni v2.2.0: Fix capogruppo cross-page, header creditsafe, ATECO 2025
# Correzioni v2.3.0: Estrazione completa ATECO (SAE, RAE, ATECO 2007, desc multilinea)
# Correzioni v2.3.1: Data report da footer PDF (non piu datetime.now)
# Correzioni v2.3.2: Data report spostata in estrai_dati_azienda (usata anche da riacquisisci)
# ==============================================================================
#
# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                    ⚠️  REMINDER CRITICI - LEGGERE PRIMA  ⚠️               ║
# ╠════════════════════════════════════════════════════════════════════════════╣
# ║                                                                          ║
# ║  1. LAYOUT PDF CREDITSAFE - PAGINE SPEZZATE                             ║
# ║     I PDF Creditsafe hanno riquadri che si spezzano tra due pagine.      ║
# ║     Es: "Capogruppo" con titolo a fine pag.1 e dati a inizio pag.2.     ║
# ║     La funzione _rimuovi_header_footer_pagine() rimuove sia i footer    ║
# ║     ("Azienda:... Richiesto da:...", "Pagina X di Y") sia gli header    ║
# ║     ("creditsafe" logo text) per unire le pagine in un flusso continuo. ║
# ║     LE PRIME 2-3 PAGINE contengono TUTTI i dati che importiamo.         ║
# ║     Devono essere trattate come UN UNICO BLOCCO di testo.               ║
# ║                                                                          ║
# ║  2. ENCODING UTF-8 - CARATTERI SPECIALI                                 ║
# ║     I file trasferiti via browser corrompono UTF-8 (€ → â‚¬, à → Ã ).    ║
# ║     Dopo ogni trasferimento, correggere con sed hexadecimal patterns.    ║
# ║     Le regex devono accettare ENTRAMBE le varianti accento/non-accento:  ║
# ║     "attività" e "attivita", "€" e "&euro;", ecc.                       ║
# ║                                                                          ║
# ║  3. REGOLA AUREA - VERIFICHE POST-MODIFICA                              ║
# ║     Quando si riscrive il file, SEMPRE verificare che:                   ║
# ║     - I footer E header pagine vengano rimossi (creditsafe logo)         ║
# ║     - La regex capogruppo gestisca contenuto cross-page                  ║
# ║     - Le regex ATECO accettino sia "2007" sia "2025" (cambiano!)         ║
# ║     - SAE/RAE/ATECO 2007 vengano estratti quando presenti              ║
# ║     - desc_ateco pulisca rumore layout 2 colonne (Di cui cancellate)   ║
# ║     - desc_attivita sia multilinea (re.DOTALL)                         ║
# ║     - I pattern € accettino sia "€" sia "&euro;"                         ║
# ║                                                                          ║
# ╚════════════════════════════════════════════════════════════════════════════╝
#

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

# Moduli locali
from .config import (
    PDF_DIR, PATTERNS, PDF_EXTENSIONS, PROVINCE_REGIONI,
    CLIENTI_DIR, get_cliente_creditsafe_path, pulisci_piva
)
from .database import get_connection, cerca_cliente_per_piva, inserisci_cliente, aggiorna_cliente_da_creditsafe
from .utils import setup_logger, pulisci_numero, pulisci_testo

# ==============================================================================
# RICOMPOSIZIONE RIGHE SPEZZATE DA LAYOUT PDF
# ==============================================================================

# Set delle sigle province per ricerca veloce
_SIGLE_PROVINCE = set(PROVINCE_REGIONI.keys())

def _ricomponi_righe_spezzate(testo):
    """
    Ricompone le righe spezzate dal layout a due colonne dei PDF Creditsafe.
    In particolare, gestisce indirizzi che vengono spezzati su più righe.
    
    Usa la lista ufficiale delle province italiane per riconoscere dove finisce
    l'indirizzo e ricomporre correttamente le righe spezzate.
    
    Gestisce anche il caso in cui la continuazione è mescolata con altro testo,
    estraendo solo la parte finale che termina con una provincia valida.
    
    Es: "25014 CASTENED" + "OLO BS" -> "25014 CASTENEDOLO BS"
    Es: "25020 C" + "...altro testo... IGOLE BS" -> "25020 CIGOLE BS"
    """
    if not testo:
        return testo
    
    righe = testo.split('\n')
    risultato = []
    i = 0
    vocali = set('AEIOU')
    
    # Costruisci pattern per trovare continuazione indirizzo (parole + provincia alla fine)
    province_pattern = '|'.join(sorted(_SIGLE_PROVINCE, key=len, reverse=True))
    
    while i < len(righe):
        riga = righe[i]
        
        # Controlla se la riga sembra avere un indirizzo troncato
        # Pattern: finisce con CAP + parola/lettera (senza provincia valida)
        if i + 1 < len(righe):
            prossima = righe[i + 1].strip()
            
            # Verifica se la riga corrente finisce con CAP + parola incompleta
            riga_finisce_con_cap_parola = re.search(r'\d{5}\s+[A-Z]+$', riga)
            
            if riga_finisce_con_cap_parola and len(prossima) > 0:
                # Estrai l'ultima parola della riga corrente (dopo il CAP)
                # per verificare se è una citta completa o troncata
                m_cap = re.search(r'\d{5}\s+([A-Z]+)$', riga)
                if m_cap:
                    ultima_parola_riga = m_cap.group(1)
                    
                    # Controlla se l'ultima parola è gia una provincia valida
                    if ultima_parola_riga not in _SIGLE_PROVINCE:
                        # Cerca nella riga successiva una sequenza che finisce con provincia
                        # Se la parola troncata è molto corta (1-2 lettere), cerca solo una parola
                        # Altrimenti potrebbe essere una citta multi-parola
                        if len(ultima_parola_riga) <= 2:
                            # Parola molto corta: cerca solo UNA parola + provincia
                            m_cont = re.search(r'([A-Z]+)\s+(' + province_pattern + r')$', prossima)
                        else:
                            # Parola più lunga: potrebbe essere multi-parola (es: PAVONE DEL MELLA)
                            m_cont = re.search(r'([A-Z]+(?:\s+[A-Z]+)*)\s+(' + province_pattern + r')$', prossima)
                        
                        if m_cont:
                            continuazione_citta = m_cont.group(1)  # Es: "IGOLE" o "DEL MELLA"
                            provincia = m_cont.group(2)  # Es: "BS"
                            
                            # Determina se serve spazio tra la parola troncata e la continuazione
                            ultima_lettera = ultima_parola_riga[-1].upper()
                            prima_lettera_cont = continuazione_citta[0].upper()
                            
                            # Se l'ultima lettera è vocale, probabilmente è parola completa -> spazio
                            # Se è consonante, probabilmente è parola troncata -> no spazio
                            if ultima_lettera in vocali:
                                riga = riga + ' ' + continuazione_citta + ' ' + provincia
                            else:
                                riga = riga + continuazione_citta + ' ' + provincia
                            
                            # Non incrementiamo i perche la riga successiva contiene altro testo
                            # che potrebbe essere necessario (es: ragione sociale)
        
        risultato.append(riga)
        i += 1
    
    return '\n'.join(risultato)


# ==============================================================================
# PARSING INDIRIZZO IN COMPONENTI
# ==============================================================================

def _parsa_indirizzo(indirizzo_completo):
    """
    Parsa un indirizzo completo nei suoi componenti.
    
    Formato atteso: "VIA NOME VIA 123, 25020 CITTA PROVINCIA"
    - Prima della virgola: via + civico
    - Dopo la virgola: CAP (5 cifre) + citta + provincia (2 lettere)
    
    Ritorna un dizionario con: via, civico, cap, citta, provincia
    """
    risultato = {
        'via': None,
        'civico': None,
        'cap': None,
        'citta': None,
        'provincia': None
    }
    
    if not indirizzo_completo:
        return risultato
    
    indirizzo = indirizzo_completo.strip()
    
    # Dividi per virgola
    if ',' in indirizzo:
        parte_via, parte_citta = indirizzo.split(',', 1)
        parte_via = parte_via.strip()
        parte_citta = parte_citta.strip()
    else:
        # Prova a dividere per CAP se non c'è virgola
        m = re.match(r'^(.+?)\s+(\d{5})\s+(.+)$', indirizzo)
        if m:
            parte_via = m.group(1).strip()
            parte_citta = m.group(2) + ' ' + m.group(3)
        else:
            return risultato
    
    # --- PARSING PARTE VIA (prima della virgola) ---
    # Estrai numero civico (ultimo numero nella stringa, opzionalmente con lettere/slash/numeri)
    # Es: "VIA ROMA 123" -> via="VIA ROMA", civico="123"
    # Es: "VIA ROMA 123/A" -> via="VIA ROMA", civico="123/A"
    # Es: "VIA ROMA 36/38" -> via="VIA ROMA", civico="36/38"
    m = re.match(r'^(.+?)\s+(\d+[A-Za-z0-9/\-]*)\s*$', parte_via)
    if m:
        risultato['via'] = m.group(1).strip()
        risultato['civico'] = m.group(2).strip()
    else:
        # Nessun civico trovato, tutta la stringa è la via
        risultato['via'] = parte_via
    
    # --- PARSING PARTE CITTA (dopo la virgola) ---
    # Formato: "25020 CASTENEDOLO BS" o "25020 PAVONE DEL MELLA BS"
    
    # Estrai CAP (5 cifre all'inizio)
    m = re.match(r'^(\d{5})\s+(.+)$', parte_citta)
    if m:
        risultato['cap'] = m.group(1)
        resto = m.group(2).strip()
        
        # Estrai provincia (ultime 2 lettere maiuscole se sono una provincia valida)
        parole = resto.split()
        if parole:
            ultima = parole[-1].upper()
            # Provincia: 2 lettere (tutte) o 3 lettere (BAT)
            if len(ultima) in (2, 3) and ultima in _SIGLE_PROVINCE:
                risultato['provincia'] = ultima
                # Citta è tutto tranne l'ultima parola (provincia)
                risultato['citta'] = ' '.join(parole[:-1])
            else:
                # Nessuna provincia riconosciuta, tutto è citta
                risultato['citta'] = resto
    else:
        # Nessun CAP trovato
        risultato['citta'] = parte_citta
    
    return risultato


# ==============================================================================
# ESTRAZIONE TESTO DA PDF
# ==============================================================================

def _rimuovi_header_footer_pagine(testo):
    """
    Rimuove header e footer delle pagine Creditsafe per unire le pagine
    in un flusso continuo di testo. CRITICO per riquadri cross-page
    (es: Capogruppo spezzato tra pag.1 e pag.2).
    
    Rimuove:
    - Header: riga "creditsafe" (logo testuale a inizio ogni pagina)
    - Footer: "Azienda: ... Richiesto da: ..." 
    - Footer: "Pagina X di Y"
    """
    if not testo:
        return testo
    
    righe = testo.split('\n')
    righe_pulite = []
    
    for riga in righe:
        riga_stripped = riga.strip()
        # Salta header "creditsafe" (logo testuale a inizio pagina)
        # Può apparire come "creditsafe" da solo o con variazioni minori
        if re.match(r'^creditsafe\s*$', riga_stripped, re.IGNORECASE):
            continue
        # Salta righe footer "Azienda: ... Richiesto da: ..."
        # NOTA: alcuni PDF non hanno spazio dopo "Azienda:" (es: "Azienda:COPAN...")
        if re.match(r'^Azienda:\s*.+Richiesto\s*(da|il):', riga_stripped):
            continue
        # Salta righe "Pagina X di Y"
        if re.match(r'^Pagina\s+\d+\s+di\s+\d+', riga_stripped):
            continue
        righe_pulite.append(riga)
    
    return '\n'.join(righe_pulite)


def estrai_testo_da_pdf(pdf_path):
    """
    Estrae il testo da un file PDF Creditsafe usando pdfplumber.
    Ritorna il testo concatenato di tutte le pagine.
    """
    try:
        import pdfplumber
        
        testi = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    testi.append(text)
        
        testo_completo = '\n'.join(testi) if testi else None
        return _rimuovi_header_footer_pagine(_ricomponi_righe_spezzate(testo_completo))
        
    except ImportError:
        print("ERRORE: pdfplumber non installato. Esegui: pip3 install pdfplumber --break-system-packages")
        return None
    except Exception as e:
        print(f"Errore estrazione PDF: {e}")
        return None


def crea_pdf_visualizzabile(pdf_path, output_path):
    """
    Copia il PDF nello storico per visualizzazione.
    I PDF Creditsafe sono gia in formato PDF valido.
    """
    try:
        shutil.copy(str(pdf_path), str(output_path))
        return True
    except Exception as e:
        print(f"Errore copia PDF: {e}")
        return False
    
    return False


# ==============================================================================
# GESTIONE PDF STORICO
# ==============================================================================

def cancella_vecchio_pdf(storico_dir, numero_registrazione=None, p_iva=None, ragione_sociale=None, logger=None):
    """
    Cerca e cancella il vecchio PDF dello stesso cliente nello storico.
    Cerca per numero_registrazione, p_iva o ragione_sociale nel nome del file.
    Ritorna True se ha cancellato un file, False altrimenti.
    """
    if not storico_dir.exists():
        return False
    
    file_cancellati = 0
    
    # Pattern da cercare nel nome del file
    patterns_ricerca = []
    
    if numero_registrazione:
        # Es: BS183271 nel nome file
        patterns_ricerca.append(numero_registrazione)
    
    if p_iva:
        # Normalizza P.IVA (rimuovi IT)
        piva_norm = str(p_iva).upper().replace('IT', '').strip()
        if piva_norm:
            patterns_ricerca.append(piva_norm)
    
    if ragione_sociale:
        # Normalizza ragione sociale per match nel filename
        # Es: "A.T.I.B. S.R.L." -> cerca "A.T.I.B." o simile
        rs_norm = ragione_sociale.replace(' ', '_').replace('.', '.')
        patterns_ricerca.append(rs_norm[:20])  # Primi 20 caratteri
    
    if not patterns_ricerca:
        return False
    
    # Cerca in tutte le sottocartelle A-Z dello storico
    for lettera_dir in storico_dir.iterdir():
        if not lettera_dir.is_dir():
            continue
        
        for pdf_file in lettera_dir.glob('*.pdf'):
            nome_file = pdf_file.name.upper()
            
            # Verifica se uno dei pattern è presente nel nome
            for pattern in patterns_ricerca:
                if pattern.upper() in nome_file:
                    try:
                        pdf_file.unlink()
                        file_cancellati += 1
                        if logger:
                            logger.info(f"  ->")
                    except Exception as e:
                        if logger:
                            logger.warning(f"  ->")
                    break  # Esci dal loop patterns, passa al prossimo file
    
    return file_cancellati > 0


# ==============================================================================
# ESTRAZIONE DATI
# ==============================================================================

def estrai_dati_azienda(testo):
    """
    Estrae i dati aziendali dal testo del PDF Creditsafe.
    Ritorna un dizionario con tutti i campi estratti.
    """
    dati = {}
    
    if not testo:
        return dati
    
    # --- IDENTIFICATIVI ---
    
    # Numero registrazione (formato: Numero registrazione:BS183271 o CCIAA/REA BS183271)
    m = re.search(r'(?:Numero\s+registrazione|CCIAA/REA)[:\s]*([A-Z]{2}\d+)', testo)
    if m:
        dati['numero_registrazione'] = m.group(1)
    
    # Partita IVA (formato: Partita IVA 00552060980)
    m = re.search(r'Partita\s+IVA\s+(\d{11})', testo)
    if m:
        dati['p_iva'] = 'IT' + m.group(1)
    
    # Codice Fiscale (formato: Codice Fiscale 00297880171)
    m = re.search(r'Codice\s+Fiscale\s+(\d{11}|[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])', testo)
    if m:
        dati['cod_fiscale'] = m.group(1)
    
    # Ragione sociale (formato: Ragione sociale A.T.I.B. S.R.L. Indirizzo)
    m = re.search(r'Ragione\s+sociale\s+(.+?)\s+Indirizzo', testo)
    if m:
        dati['ragione_sociale'] = pulisci_testo(m.group(1))
    
    # --- INDIRIZZO E CONTATTI ---
    
    # Indirizzo (formato: Indirizzo VIA QUINZANESE , 25020 DELLO BS)
    m = re.search(r'Indirizzo\s+([A-Z0-9][^\n]+?)(?:\s+Numero|\s*$)', testo, re.MULTILINE)
    if m:
        dati['indirizzo'] = pulisci_testo(m.group(1))
        
        # Parsa indirizzo nei componenti: via, civico, cap, citta, provincia
        componenti = _parsa_indirizzo(dati['indirizzo'])
        if componenti['via']:
            dati['via'] = componenti['via']
        if componenti['civico']:
            dati['civico'] = componenti['civico']
        if componenti['cap']:
            dati['cap'] = componenti['cap']
        if componenti['citta']:
            dati['citta'] = componenti['citta']
        if componenti['provincia']:
            dati['provincia'] = componenti['provincia']
    
    # Telefono (formato: Numero di telefono 0309771711)
    m = re.search(r'Numero\s+di\s+telefono\s+([+\d\s\-/]+)', testo)
    if m:
        dati['telefono'] = pulisci_testo(m.group(1))
    
    # PEC (formato: Indirizzo mail PEC xxx@yyy.it o PEC xxx@yyy.it)
    m = re.search(r'(?:Indirizzo\s+mail\s+)?PEC\s+([\w\.\-]+@[\w\.\-]+\.\w+)', testo, re.IGNORECASE)
    if m:
        dati['pec'] = m.group(1).upper()
    
    # --- DATI SOCIETARI ---
    
    # Forma giuridica (formato: Forma giuridica SOCIETA' A RESPONSABILITA' LIMITATA)
    m = re.search(r'Forma\s+giuridica\s+(.+?)(?:\n|Codice)', testo)
    if m:
        dati['forma_giuridica'] = pulisci_testo(m.group(1))
    
    # Data costituzione (formato: Data di costituzione 15/01/1972)
    m = re.search(r'Data\s+di\s+costituzione\s+(\d{2}/\d{2}/\d{4})', testo)
    if m:
        dati['data_costituzione'] = m.group(1)
    
    # Capitale sociale (formato: Capitale Sociale €1.550.000)
    m = re.search(r'Capitale\s+[Ss]ociale\s+(?:€|&euro;)?\s*([\d.,]+)', testo)
    if m:
        dati['capitale_sociale'] = pulisci_numero(m.group(1))
    
    # Dipendenti (formato: Numero medio dipendenti 114)
    m = re.search(r'Numero\s+medio\s+dipendenti\s+(\d+)', testo)
    if m:
        dati['dipendenti'] = int(m.group(1))
    
    # --- ATTIVITA E CODICI ATECO ---
    # Layout PDF Creditsafe: sezione "Informazioni settore industriale"
    # Struttura a 2 colonne con possibili campi:
    #   Codice ateco 2025/2007 XXXXXX | N° di società nel macro settore XXXXX
    #   Descrizione ateco 2025/2007 ... | Di cui cancellate XXXXX
    #   Codice SAE XXX              | Codice RAE XXX
    #   Codice ateco 2007 XXXXXX    (opzionale, presente solo se diverso da 2025)
    #   Descrizione ateco 2007 ...  (opzionale)
    #   Descrizione attività svolta ... (multilinea)
    
    # Codice ATECO primario (il primo che appare: 2025 o 2007)
    # Cattura anche l'anno per sapere quale versione e'
    m = re.search(r'Codice\s+ateco\s+(\d{4})\s+([\d.]+)', testo, re.IGNORECASE)
    if m:
        dati['codice_ateco'] = m.group(2)
    
    # Descrizione ATECO primario (2025 o primo che appare)
    # ATTENZIONE: il layout a 2 colonne mescola "Di cui cancellate" sulla stessa riga
    # Cattura tutto fino a Codice SAE/ateco 2007/Descrizione attivita, poi pulisce il rumore
    m = re.search(
        r'Descrizione\s+ateco\s+\d{4}\s+(.+?)(?=Codice\s+SAE|Codice\s+ateco\s+2007|Descrizione\s+attivit|Capogruppo|Dati\s+finanziari)',
        testo, re.IGNORECASE | re.DOTALL
    )
    if m:
        desc = m.group(1)
        # Rimuovi rumore layout 2 colonne
        desc = re.sub(r'Di\s+cui\s+cancellate\s+[\d.,]+', '', desc)
        desc = re.sub(r"N..\s+di\s+societ.\s+nel\s+macro\s*\n?\s*settore\s+[\d.,]+", '', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()
        # Safety net: tronca a 300 caratteri
        if len(desc) > 300:
            desc = desc[:300].rsplit(' ', 1)[0]
        dati['desc_ateco'] = pulisci_testo(desc)
    
    # Codice SAE (stesso layout: "Codice SAE 430 Codice RAE 830" su stessa riga)
    m = re.search(r'Codice\s+SAE\s+(\d+)', testo)
    if m:
        dati['codice_sae'] = m.group(1)
    
    # Codice RAE
    m = re.search(r'Codice\s+RAE\s+(\d+)', testo)
    if m:
        dati['codice_rae'] = m.group(1)
    
    # Codice ATECO 2007 (opzionale - presente solo se c'e' anche il 2025)
    m = re.search(r'Codice\s+ateco\s+2007\s+([\d.]+)', testo, re.IGNORECASE)
    if m:
        dati['codice_ateco_2007'] = m.group(1)
    
    # Descrizione ATECO 2007 (opzionale)
    m = re.search(
        r'Descrizione\s+ateco\s+2007\s+(.+?)(?=Descrizione\s+attivit|Codice|Capogruppo|Dati\s+finanziari|\n)',
        testo, re.IGNORECASE
    )
    if m:
        dati['desc_ateco_2007'] = pulisci_testo(m.group(1).strip())
    
    # Descrizione attivita svolta (MULTILINEA - può andare su più righe)
    # Termina a: Capogruppo, Dati finanziari, o fine testo
    m = re.search(
        r'Descrizione\s+attivit.\s+svolta\s+(.+?)(?=Capogruppo|Dati\s+finanziari|$)',
        testo, re.DOTALL
    )
    if m:
        desc = re.sub(r'\s+', ' ', m.group(1)).strip()
        # Safety net: tronca a 500 caratteri
        if len(desc) > 500:
            desc = desc[:500].rsplit(' ', 1)[0]
        dati['desc_attivita'] = pulisci_testo(desc)
    else:
        # Fallback: formato alternativo senza "svolta"
        m = re.search(
            r'Descrizione\s+attivit.\s+([A-Z][A-Z\s]+?)(?=Capogruppo|Codice|Dati\s+finanziari|\n)',
            testo
        )
        if m:
            dati['desc_attivita'] = pulisci_testo(m.group(1).strip())
    
    # --- DATA REPORT CREDITSAFE ---
    # Estratta dal footer/header PDF: "Richiesto il: 4:58 lunedì 9º febbraio 2026"
    # NOTA: nel testo pulito sopravvive la versione header (pagina 1)
    _mesi_it = {
        'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
        'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
        'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
    }
    m = re.search(r'Richiesto\s+il\s*:\s*\d{1,2}:\d{2}\s+\w+\s+(\d{1,2}).?\s+(\w+)\s+(\d{4})', testo)
    if m:
        try:
            _g = int(m.group(1))
            _m = _mesi_it.get(m.group(2).lower(), 0)
            _a = int(m.group(3))
            if _m:
                dati['data_report_creditsafe'] = f'{_a:04d}-{_m:02d}-{_g:02d}'
        except (ValueError, TypeError):
            pass
    
    # --- CAPOGRUPPO ---
    # Formato PDF:
    # Capogruppo
    # Nome Nazione Codice Fiscale
    # GIANGIULIO STEFANIA (IT) GNGSFN59L42E897P
    #
    # ATTENZIONE: Il riquadro Capogruppo si spezza spesso tra pagina 1 e 2!
    # Dopo _rimuovi_header_footer_pagine() il testo dovrebbe essere continuo,
    # ma usiamo \s+ (non \s) per tollerare newline/spazi residui tra header e dati.
    
    # Pattern principale: Capogruppo > intestazioni > NOME (NAZIONE) CF
    m = re.search(
        r'Capogruppo\s+Nome\s+Nazione\s+Codice\s+Fiscale\s+'
        r'([A-Z][A-Z\s]+?)\s+\(([A-Z]{2})\)\s+([A-Z0-9]{16})',
        testo
    )
    if m:
        dati['capogruppo_nome'] = pulisci_testo(m.group(1))
        dati['capogruppo_cf'] = m.group(3)
    else:
        # Fallback 1: senza intestazioni (layout diverso)
        m = re.search(
            r'Capogruppo\s+([A-Z][A-Z\s]+?)\s+\(([A-Z]{2})\)\s+([A-Z0-9]{16})',
            testo
        )
        if m:
            dati['capogruppo_nome'] = pulisci_testo(m.group(1))
            dati['capogruppo_cf'] = m.group(3)
        else:
            # Fallback 2: CF non standard (meno di 16 caratteri, es. aziende estere)
            m = re.search(
                r'Capogruppo\s+(?:Nome\s+Nazione\s+Codice\s+Fiscale\s+)?'
                r'([A-Z][A-Z\s]+?)\s+\([A-Z]{2}\)\s+([A-Z0-9]+)',
                testo
            )
            if m:
                dati['capogruppo_nome'] = pulisci_testo(m.group(1))
                dati['capogruppo_cf'] = m.group(2)
    
    
    # --- RATING E RISCHIO ---
    # Formato normale: "80 A €730.000 Attiva"
    # Formato N/D: "N/D E €0 -"
    
    # Pattern 1: con punteggio numerico
    m = re.search(r'(?:rischio|pagamento)\s*\n?\s*(\d+)\s+([A-E])\s+(?:€|&euro;)?([\d.,]+)\s+(Attiv[ao]|Inattiv[ao]|Cessat[ao])', testo)
    if m:
        dati['punteggio_rischio'] = int(m.group(1))
        dati['score'] = m.group(2)
        dati['credito'] = pulisci_numero(m.group(3))
        dati['stato'] = m.group(4).title()
    else:
        # Pattern 2: N/D come punteggio (aziende in scioglimento)
        m = re.search(r'N/?D\s+([A-E])\s+(?:€|&euro;)?([\d.,]+)', testo)
        if m:
            dati['punteggio_rischio'] = None
            dati['score'] = m.group(1)
            dati['credito'] = pulisci_numero(m.group(2))
        else:
            # Pattern 3: Score Internazionale separato
            m = re.search(r'Score\s+Internazionale\s+([A-E])', testo)
            if m:
                dati['score'] = m.group(1)
            else:
                # Pattern 4: generico
                m = re.search(r'\b(\d{1,3})\s+([A-E])\s+(?:€|&euro;)?([\d.,]+)', testo)
                if m:
                    dati['punteggio_rischio'] = int(m.group(1))
                    dati['score'] = m.group(2)
                    dati['credito'] = pulisci_numero(m.group(3))
    
    # Stato (se non gia trovato)
    if 'stato' not in dati:
        # Cerca SCIOGLIMENTO prima
        if re.search(r'SCIOGLIMENTO', testo):
            dati['stato'] = 'Scioglimento'
        else:
            m = re.search(r'\b(Attiv[ao]|Inattiv[ao]|Cessat[ao]|In liquidazione)\b', testo, re.IGNORECASE)
            if m:
                dati['stato'] = m.group(1).title()
    
    # --- PROTESTI ---
    
    m = re.search(r'Protesti\s+(Nessun|S[ìi]|\d+)', testo, re.IGNORECASE)
    if m:
        dati['protesti'] = m.group(1)
    
    m = re.search(r'Protesti\s+.+?(?:€|&euro;)\s*([\d.,]+)', testo)
    if m:
        dati['importo_protesti'] = pulisci_numero(m.group(1))
    
    # --- DATI FINANZIARI (BILANCIO) ---
    # Formato PDF: "Voce VALORE1 PERC% VALORE2 PERC% VALORE3"
    # Es: "Utile (Perdita) dell'esercizio 185.016 36%  287.270 116%  133.137"
    
    # Anni bilancio
    m = re.search(r'Dati\s+finanziari\s+chiave\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})', testo)
    if m:
        # Estrai solo l'anno dalla data
        dati['anno_bilancio'] = int(m.group(1).split('/')[-1])
        dati['anno_bilancio_prec'] = int(m.group(2).split('/')[-1])
    else:
        # Cerca formato alternativo con solo anni
        m = re.search(r'Dati\s+finanziari\s+chiave\s+(\d{4})\s+(\d{4})', testo)
        if m:
            dati['anno_bilancio'] = int(m.group(1))
            dati['anno_bilancio_prec'] = int(m.group(2))
    
    # Valore produzione
    # Pattern: "Totale valore della produzione 7.448.309 8%  6.895.310 99%" (anche negativo)
    m = re.search(
        r'Totale\s+valore\s+della\s+produzione\s+([-\d.,]+)\s+\d+%\s*[^\d-]*([-\d.,]+)',
        testo
    )
    if m:
        dati['valore_produzione'] = pulisci_numero(m.group(1))
        dati['valore_produzione_prec'] = pulisci_numero(m.group(2))
    
    # Patrimonio netto
    # Pattern: "Patrimonio netto 784.925 31%  599.910 45%" (anche negativo: -98.612)
    m = re.search(
        r'Patrimonio\s+netto\s+([-\d.,]+)\s+\d+%\s*[^\d-]*([-\d.,]+)',
        testo
    )
    if m:
        dati['patrimonio_netto'] = pulisci_numero(m.group(1))
        dati['patrimonio_netto_prec'] = pulisci_numero(m.group(2))
    
    # Utile/Perdita
    # Pattern: "Utile (Perdita) dell'esercizio 185.016 36%  287.270 116%"
    m = re.search(
        r"Utile\s*\(?Perdita\)?\s*dell.esercizio\s+([-\d.,]+)\s+\d+%\s*[^\d]*([-\d.,]+)",
        testo
    )
    if m:
        dati['utile'] = pulisci_numero(m.group(1))
        dati['utile_prec'] = pulisci_numero(m.group(2))
    
    # Debiti totali
    # Pattern: "Totale debiti 5.524.362 16%  4.778.927 74%"
    m = re.search(
        r'Totale\s+debiti\s+([\d.,]+)\s+\d+%\s*[^\d]*([\d.,]+)',
        testo
    )
    if m:
        dati['debiti'] = pulisci_numero(m.group(1))
        dati['debiti_prec'] = pulisci_numero(m.group(2))
    
    return dati


def estrai_nome_da_filename(filename):
    """Estrae il nome dell'azienda dal nome del file PDF."""
    # Rimuove estensione
    nome = Path(filename).stem
    
    # Rimuove la parte finale (IT + P.IVA + data)
    nome = re.sub(r'_IT\d?[A-Z]{2}\d+_\d+$', '', nome)
    
    # Sostituisce underscore con spazi
    nome = nome.replace('_', ' ')
    
    # Pulisce spazi multipli
    nome = re.sub(r'\s+', ' ', nome).strip()
    
    return nome


# ==============================================================================
# PROCESSO IMPORT
# ==============================================================================

def processa_pdf(pdf_path, conn, logger):
    """
    Processa un singolo file PDF Creditsafe.
    - Estrae i dati
    - Inserisce o aggiorna nel database
    - Cancella eventuale vecchio PDF dello stesso cliente
    - Sposta il file nello storico
    """
    nome_file = pdf_path.name
    
    logger.info(f"Elaborazione: {nome_file}")
    
    # Estrai testo
    testo = estrai_testo_da_pdf(pdf_path)
    
    if not testo:
        logger.warning(f"  Impossibile estrarre testo da {nome_file}")
        return False
    
    # Estrai dati
    dati = estrai_dati_azienda(testo)
    
    if not dati:
        logger.warning(f"  Nessun dato estratto da {nome_file}")
        return False
    
    # Aggiungi nome da filename se non presente
    if not dati.get('ragione_sociale'):
        dati['ragione_sociale'] = estrai_nome_da_filename(nome_file)
    
    dati['nome_cliente'] = dati.get('ragione_sociale', estrai_nome_da_filename(nome_file))
    dati['file_pdf'] = nome_file
    # Data report: gia estratta da estrai_dati_azienda() dal testo PDF
    # Fallback: data odierna se non trovata
    if not dati.get('data_report_creditsafe'):
        dati['data_report_creditsafe'] = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"  P.IVA: {dati.get('p_iva', 'N/D')}")
    logger.info(f"  Ragione sociale: {dati.get('ragione_sociale', 'N/D')}")
    logger.info(f"  Score: {dati.get('score', 'N/D')}")
    
    # Cerca cliente esistente per P.IVA
    cliente_esistente = None
    if dati.get('p_iva'):
        cliente_esistente = cerca_cliente_per_piva(conn, dati['p_iva'])
    
    if cliente_esistente:
        # AGGIORNA cliente esistente - SOLO se il report e' piu' recente o il dato e' vuoto
        data_report_nuova = dati.get('data_report_creditsafe', '')
        data_report_attuale = cliente_esistente['data_report_creditsafe'] if 'data_report_creditsafe' in cliente_esistente.keys() else None
        
        if not data_report_attuale or not data_report_nuova:
            # Campo vuoto: aggiorna sempre
            logger.info(f"  -> Aggiornamento (data report mancante nel DB o nel PDF)")
            aggiorna_cliente_da_creditsafe(conn, cliente_esistente['id'], dati, logger)
            # Reset flag amministratore variato (PDF nuovo = fonte aggiornata)
            conn.cursor().execute("UPDATE clienti SET amministratore_variato = 0 WHERE id = ?", (cliente_esistente["id"],))
        elif data_report_nuova >= data_report_attuale:
            # Report nuovo e' piu' recente o uguale: aggiorna
            logger.info(f"  -> Aggiornamento (report {data_report_nuova} >= DB {data_report_attuale})")
            aggiorna_cliente_da_creditsafe(conn, cliente_esistente['id'], dati, logger)
            # Reset flag amministratore variato (PDF nuovo = fonte aggiornata)
            conn.cursor().execute("UPDATE clienti SET amministratore_variato = 0 WHERE id = ?", (cliente_esistente["id"],))
        else:
            # Report vecchio: NON aggiornare dati, ma archivia comunque il PDF
            logger.info(f"  -> SKIP aggiornamento dati (report {data_report_nuova} < DB {data_report_attuale})")
            logger.info(f"     Il PDF viene comunque archiviato")
    else:
        # INSERISCI nuovo cliente
        logger.info(f"  ->")
        cliente_id = inserisci_cliente(conn, dati, origine='creditsafe')
        logger.info(f"  ->")
    
    
    # NUOVA STRUTTURA: Salva PDF nella cartella creditsafe del cliente
    try:
        # Costruisci dati cliente per ottenere il path
        cliente_per_path = {
            'p_iva': dati.get('p_iva'),
            'cod_fiscale': dati.get('cod_fiscale')
        }
        
        # Ottieni cartella creditsafe del cliente
        creditsafe_dir = get_cliente_creditsafe_path(cliente_per_path)
        creditsafe_dir.mkdir(parents=True, exist_ok=True)
        
        # Cancella eventuali vecchi PDF nella cartella del cliente
        for old_pdf in creditsafe_dir.glob('*.pdf'):
            try:
                old_pdf.unlink()
                logger.info(f"  -> Cancellato vecchio PDF: {old_pdf.name}")
            except Exception as e:
                logger.warning(f"  ! Errore cancellazione {old_pdf.name}: {e}")
        
        # Copia il nuovo PDF
        dest_path = creditsafe_dir / pdf_path.name
        shutil.copy(str(pdf_path), str(dest_path))
        
        # Aggiorna path nel DB (path relativo)
        path_relativo = str(dest_path).replace(str(CLIENTI_DIR.parent) + '/', '')
        cursor = conn.cursor()
        if cliente_esistente:
            cursor.execute('UPDATE clienti SET file_pdf = ? WHERE id = ?', 
                          (path_relativo, cliente_esistente['id']))
        else:
            cursor.execute('UPDATE clienti SET file_pdf = ? WHERE id = ?',
                          (path_relativo, cliente_id))
        conn.commit()
        
        logger.info(f"  -> PDF archiviato in: {creditsafe_dir.name}/{pdf_path.name}")
        
    except ValueError as e:
        # Cliente senza P.IVA e CF, fallback
        logger.warning(f"  ! {e} - PDF non archiviato nella cartella cliente")
    
    return True

def importa_tutti_pdf():
    """
    Importa tutti i PDF dalla cartella pdf/.
    Funzione principale per import batch.
    - PDF elaborati ->
    - Vecchi PDF dello stesso cliente ->
    - PDF con errori ->
    - Log errori ->
    """
    logger = setup_logger('import_creditsafe')
    
    logger.info("=" * 60)
    logger.info("IMPORT PDF CREDITSAFE")
    logger.info("=" * 60)
    
    # Assicura cartelle esistano
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    CLIENTI_DIR.mkdir(parents=True, exist_ok=True)
    CLIENTI_DIR.joinpath("PIVA").mkdir(parents=True, exist_ok=True)
    CLIENTI_DIR.joinpath("CF").mkdir(parents=True, exist_ok=True)
    
    # Cartella per PDF con errori
    PDF_ERRORI_DIR = PDF_DIR.parent / 'pdf_errori'
    PDF_ERRORI_DIR.mkdir(parents=True, exist_ok=True)
    
    # Log errori separato
    LOGS_DIR = PDF_DIR.parent / 'logs'
    errori_log_path = LOGS_DIR / 'errori_import.log'
    
    # Cerca PDF
    pdf_files = []
    for ext in PDF_EXTENSIONS:
        pdf_files.extend(PDF_DIR.glob(f'*{ext}'))
    
    if not pdf_files:
        logger.info("Nessun PDF da elaborare")
        return {'elaborati': 0, 'errori': 0}
    
    logger.info(f"Trovati {len(pdf_files)} file da elaborare")
    
    # Connessione database
    conn = get_connection()
    
    elaborati = 0
    errori = 0
    lista_errori = []
    
    for pdf_path in sorted(pdf_files):
        try:
            if processa_pdf(pdf_path, conn, logger):
                elaborati += 1
                # Rimuovi il file dalla cartella pdf/ dopo elaborazione riuscita
                pdf_path.unlink()
            else:
                errori += 1
                motivo = "Impossibile estrarre dati"
                lista_errori.append((pdf_path.name, motivo))
                # Sposta in cartella errori
                dest_errore = PDF_ERRORI_DIR / pdf_path.name
                shutil.move(str(pdf_path), str(dest_errore))
                logger.warning(f"  ->")
        except Exception as e:
            logger.error(f"  ERRORE: {e}")
            errori += 1
            lista_errori.append((pdf_path.name, str(e)))
            # Sposta in cartella errori
            try:
                dest_errore = PDF_ERRORI_DIR / pdf_path.name
                shutil.move(str(pdf_path), str(dest_errore))
                logger.warning(f"  ->")
            except:
                pass
    
    conn.close()
    
    # Scrivi log errori se ce ne sono
    if lista_errori:
        with open(errori_log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"IMPORT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n")
            for nome_file, motivo in lista_errori:
                f.write(f"FILE: {nome_file}\n")
                f.write(f"ERRORE: {motivo}\n")
                f.write(f"-" * 40 + "\n")
    
    logger.info("-" * 60)
    logger.info(f"Completato: {elaborati} elaborati, {errori} errori")
    if errori > 0:
        logger.info(f"File con errori spostati in: pdf_errori/")
        logger.info(f"Dettagli errori in: logs/errori_import.log")
    logger.info("=" * 60)
    
    return {'elaborati': elaborati, 'errori': errori}


def importa_pdf_singolo(pdf_path):
    """
    Importa un singolo PDF.
    Usato per import asincrono con progress bar.
    Uniformato a importa_tutti_pdf() per gestione errori e log.
    
    Args:
        pdf_path: Percorso al file PDF (stringa o Path)
    
    Returns:
        dict con 'success' (bool), 'error' (str opzionale), 'cliente' (str opzionale)
    """
    logger = setup_logger('import_creditsafe')
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        return {'success': False, 'error': 'File non trovato'}
    
    # Cartella per PDF con errori
    PDF_ERRORI_DIR = PDF_DIR.parent / 'pdf_errori'
    PDF_ERRORI_DIR.mkdir(parents=True, exist_ok=True)
    
    # Log errori separato (come importa_tutti_pdf)
    LOGS_DIR = PDF_DIR.parent / 'logs'
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    errori_log_path = LOGS_DIR / 'errori_import.log'
    
    def scrivi_log_errore(nome_file, motivo):
        """Scrive errore nel log file."""
        try:
            with open(errori_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"IMPORT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n")
                f.write(f"FILE: {nome_file}\n")
                f.write(f"ERRORE: {motivo}\n")
                f.write(f"-" * 40 + "\n")
        except:
            pass
    
    # Connessione database
    conn = get_connection()
    
    try:
        logger.info(f"Elaboro: {pdf_path.name}")
        
        if processa_pdf(pdf_path, conn, logger):
            # Successo - rimuovi file
            pdf_path.unlink()
            conn.close()
            return {'success': True, 'cliente': pdf_path.stem}
        else:
            # Errore elaborazione - sposta in pdf_errori
            motivo = "Impossibile estrarre dati"
            dest_errore = PDF_ERRORI_DIR / pdf_path.name
            shutil.move(str(pdf_path), str(dest_errore))
            logger.warning(f"  ->")
            scrivi_log_errore(pdf_path.name, motivo)
            conn.close()
            return {'success': False, 'error': motivo}
            
    except Exception as e:
        logger.error(f"Errore: {e}")
        conn.close()
        # Sposta in cartella errori
        try:
            dest_errore = PDF_ERRORI_DIR / pdf_path.name
            shutil.move(str(pdf_path), str(dest_errore))
            logger.warning(f"  ->")
        except:
            pass
        scrivi_log_errore(pdf_path.name, str(e))
        return {'success': False, 'error': str(e)}


# ==============================================================================
# MAIN (per test standalone)
# ==============================================================================

if __name__ == '__main__':
    risultato = importa_tutti_pdf()
    print(f"\nRisultato: {risultato}")
# ==============================================================================
# FUNZIONE IMPORT CON PROGRESS - Da aggiungere a import_creditsafe.py
# ==============================================================================
# Aggiungi questa funzione dopo importa_tutti_pdf()
# ==============================================================================

def importa_tutti_pdf_con_progress(status_dict):
    """
    Importa tutti i PDF dalla cartella pdf/ con aggiornamento progress.
    status_dict viene aggiornato in tempo reale per il polling.
    """
    logger = setup_logger('import_creditsafe')
    
    logger.info("=" * 60)
    logger.info("IMPORT PDF CREDITSAFE (con progress)")
    logger.info("=" * 60)
    
    # Assicura cartelle esistano
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    CLIENTI_DIR.mkdir(parents=True, exist_ok=True)
    CLIENTI_DIR.joinpath("PIVA").mkdir(parents=True, exist_ok=True)
    CLIENTI_DIR.joinpath("CF").mkdir(parents=True, exist_ok=True)
    
    # Cartella per PDF con errori
    PDF_ERRORI_DIR = PDF_DIR.parent / 'pdf_errori'
    PDF_ERRORI_DIR.mkdir(parents=True, exist_ok=True)
    
    # Cerca PDF
    pdf_files = list(PDF_DIR.glob('*.pdf'))
    
    if not pdf_files:
        logger.info("Nessun PDF da elaborare")
        return {'elaborati': 0, 'errori': 0}
    
    status_dict['total'] = len(pdf_files)
    logger.info(f"Trovati {len(pdf_files)} file da elaborare")
    
    # Connessione database
    conn = get_connection()
    
    elaborati = 0
    errori = 0
    
    for pdf_path in sorted(pdf_files):
        try:
            if processa_pdf(pdf_path, conn, logger):
                elaborati += 1
                pdf_path.unlink()
            else:
                errori += 1
                dest_errore = PDF_ERRORI_DIR / pdf_path.name
                shutil.move(str(pdf_path), str(dest_errore))
        except Exception as e:
            logger.error(f"  ERRORE: {e}")
            errori += 1
            try:
                dest_errore = PDF_ERRORI_DIR / pdf_path.name
                shutil.move(str(pdf_path), str(dest_errore))
            except:
                pass
        
        # Aggiorna status per il polling
        status_dict['elaborati'] = elaborati
        status_dict['errori'] = errori
    
    conn.close()
    
    logger.info("-" * 60)
    logger.info(f"Completato: {elaborati} elaborati, {errori} errori")
    logger.info("=" * 60)
    
    return {'elaborati': elaborati, 'errori': errori}
