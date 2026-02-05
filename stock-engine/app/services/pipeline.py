# =============================================================================
# STOCK ENGINE - Pipeline Service
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Orchestratore elaborazione stock.
# Sostituisce gli script bash (ayvens.sh, arval.sh, etc.)
#
# FLUSSO:
# 1. Trova file → 2. Importa → 3. Normalizza → 4. Match → 5. Arricchisci → 
# 6. Salva DB → 7. Genera Excel
# =============================================================================

import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

from flask import current_app

from app import db
from app.models.veicolo import Veicolo
from app.models.elaborazione import Elaborazione

from .importers import get_importer
from .normalizer import Normalizer
from .matcher import JatoMatcher
from .enricher import Enricher
from .exporter import ExcelExporter


class StockPipeline:
    """
    Pipeline elaborazione stock
    
    Orchestratore principale che esegue l'intero flusso di elaborazione:
    
    PRIMA (bash):  10 moduli sequenziali → 10 minuti
    DOPO (Python): pipeline unificata → 30-60 secondi
    """
    
    def __init__(self):
        """Inizializza pipeline con tutti i servizi"""
        self.normalizer = Normalizer()
        self.matcher = JatoMatcher()
        self.enricher = Enricher()
        self.exporter = ExcelExporter()
    
    def elabora(self, noleggiatore: str, file_path: Path = None) -> Dict:
        """
        Esegue elaborazione completa per un noleggiatore
        
        Args:
            noleggiatore: Nome noleggiatore (AYVENS, ARVAL, etc.)
            file_path: Path file input (opzionale, cerca automaticamente)
            
        Returns:
            dict: Statistiche elaborazione
        """
        noleggiatore = noleggiatore.upper()
        start_time = time.time()
        
        # Crea record elaborazione
        elaborazione = Elaborazione(noleggiatore=noleggiatore)
        db.session.add(elaborazione)
        db.session.commit()
        
        try:
            print(f"\n{'='*60}")
            print(f"ELABORAZIONE {noleggiatore}")
            print(f"{'='*60}")
            
            # STEP 1: Importa dati
            print(f"\n[1/6] Importazione dati...")
            importer = get_importer(noleggiatore)
            
            if file_path:
                veicoli_raw = importer.importa(file_path)
                elaborazione.file_origine = str(file_path)
            else:
                file_trovato = importer.trova_file_recente()
                if not file_trovato:
                    raise ValueError("Nessun file trovato da importare")
                veicoli_raw = importer.importa(file_trovato)
                elaborazione.file_origine = str(file_trovato)
            
            print(f"      ✔ {len(veicoli_raw)} veicoli importati")
            
            # STEP 2: Normalizza con glossario
            print(f"\n[2/6] Normalizzazione (glossario)...")
            veicoli_norm = self.normalizer.applica(veicoli_raw, noleggiatore)
            print(f"      ✔ Glossario applicato")
            
            # STEP 3: Match JATO
            print(f"\n[3/6] Match JATO...")
            veicoli_matched = self.matcher.match_batch(veicoli_norm)
            
            matched_count = sum(1 for v in veicoli_matched if v.get('match_status') == 'MATCHED')
            partial_count = sum(1 for v in veicoli_matched if v.get('match_status') == 'PARTIAL')
            no_match_count = sum(1 for v in veicoli_matched if v.get('match_status') == 'NO_MATCH')
            
            print(f"      ✔ Matched: {matched_count}")
            print(f"      ⚠ Partial: {partial_count}")
            print(f"      ✗ No match: {no_match_count}")
            
            # STEP 4: Arricchisci
            print(f"\n[4/6] Arricchimento dati...")
            veicoli_enriched = self.enricher.arricchisci(veicoli_matched)
            print(f"      ✔ Dati arricchiti")
            
            # STEP 5: Salva in database
            print(f"\n[5/6] Salvataggio database...")
            self._salva_veicoli(veicoli_enriched, elaborazione.id)
            print(f"      ✔ {len(veicoli_enriched)} veicoli salvati")
            
            # STEP 6: Genera Excel
            print(f"\n[6/6] Generazione Excel...")
            excel_path = self.exporter.genera_excel(noleggiatore, date.today())
            print(f"      ✔ File: {excel_path}")
            
            # Calcola durata
            durata = int(time.time() - start_time)
            
            # Completa elaborazione
            elaborazione.completa(
                veicoli_importati=len(veicoli_raw),
                veicoli_matched=matched_count,
                veicoli_partial=partial_count,
                veicoli_no_match=no_match_count,
                file_excel=str(excel_path),
                durata=durata
            )
            
            # Risultato
            result = {
                'noleggiatore': noleggiatore,
                'data': date.today().isoformat(),
                'veicoli_importati': len(veicoli_raw),
                'veicoli_matched': matched_count,
                'veicoli_partial': partial_count,
                'veicoli_no_match': no_match_count,
                'match_rate': round((matched_count / len(veicoli_raw)) * 100, 1) if veicoli_raw else 0,
                'durata_secondi': durata,
                'file_excel': str(excel_path),
                'stato': 'completata',
            }
            
            print(f"\n{'='*60}")
            print(f"✔ ELABORAZIONE COMPLETATA in {durata} secondi")
            print(f"  Match rate: {result['match_rate']}%")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            # Registra errore
            elaborazione.errore(str(e))
            
            print(f"\n{'='*60}")
            print(f"✗ ERRORE ELABORAZIONE: {e}")
            print(f"{'='*60}\n")
            
            raise
    
    def _salva_veicoli(self, veicoli: list, elaborazione_id: int):
        """
        Salva veicoli nel database (UPSERT)
        
        Args:
            veicoli: Lista veicoli da salvare
            elaborazione_id: ID elaborazione corrente
        """
        for v in veicoli:
            # Cerca veicolo esistente (stesso VIN, stessa data, stesso noleggiatore)
            esistente = Veicolo.query.filter_by(
                noleggiatore=v.get('noleggiatore'),
                vin=v.get('vin'),
                data_import=v.get('data_import', date.today())
            ).first()
            
            if esistente:
                # Aggiorna
                for key, value in v.items():
                    if hasattr(esistente, key) and key != 'id':
                        setattr(esistente, key, value)
                esistente.elaborazione_id = elaborazione_id
            else:
                # Inserisci nuovo
                veicolo = Veicolo(
                    noleggiatore=v.get('noleggiatore'),
                    vin=v.get('vin'),
                    data_import=v.get('data_import', date.today()),
                    
                    # Originali
                    marca_originale=v.get('marca_originale'),
                    modello_originale=v.get('modello_originale'),
                    description_originale=v.get('description_originale'),
                    fuel_originale=v.get('fuel_originale'),
                    
                    # Normalizzati
                    marca=v.get('marca'),
                    modello=v.get('modello'),
                    description=v.get('description'),
                    
                    # Tecnici
                    co2=v.get('co2'),
                    prezzo_listino=v.get('prezzo_listino'),
                    prezzo_accessori=v.get('prezzo_accessori'),
                    prezzo_totale=v.get('prezzo_totale'),
                    location=v.get('location'),
                    location_address=v.get('location_address'),
                    data_arrivo=v.get('data_arrivo'),
                    colore=v.get('colore'),
                    colore_interno=v.get('colore_interno'),
                    targa=v.get('targa'),
                    km=v.get('km'),
                    
                    # JATO
                    jato_code=v.get('jato_code'),
                    product_id=v.get('product_id'),
                    omologazione=v.get('omologazione'),
                    kw=v.get('kw'),
                    hp=v.get('hp'),
                    alimentazione=v.get('alimentazione'),
                    jato_product_description=v.get('jato_product_description'),
                    vehicle_set_description=v.get('vehicle_set_description'),
                    transmission=v.get('transmission'),
                    
                    # Match
                    match_status=v.get('match_status'),
                    match_score=v.get('match_score'),
                    match_note=v.get('match_note'),
                    match_details=v.get('match_details'),
                    
                    # Business
                    neopatentati=v.get('neopatentati', 'ND'),
                    
                    # Riferimento
                    elaborazione_id=elaborazione_id,
                )
                db.session.add(veicolo)
        
        db.session.commit()
    
    def elabora_tutti(self) -> Dict:
        """
        Elabora tutti i noleggiatori attivi
        
        Returns:
            dict: Risultati per ogni noleggiatore
        """
        noleggiatori = current_app.config.get('NOLEGGIATORI_ATTIVI', ['AYVENS'])
        risultati = {}
        
        for noleggiatore in noleggiatori:
            try:
                risultati[noleggiatore] = self.elabora(noleggiatore)
            except Exception as e:
                risultati[noleggiatore] = {
                    'stato': 'errore',
                    'errore': str(e)
                }
        
        return risultati
