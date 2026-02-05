# =============================================================================
# STOCK ENGINE - Enricher Service
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Servizio per arricchimento dati veicoli con informazioni aggiuntive.
# Sostituisce il modulo 03_arricchimento.py
# =============================================================================

from typing import List, Dict, Optional

from app import db
from app.models.jato import JatoModel


class Enricher:
    """
    Servizio arricchimento dati veicoli
    
    Aggiunge:
    - Calcolo neopatentati da omologazione
    - Dati JATO mancanti
    - Calcoli derivati (prezzo totale, etc.)
    """
    
    # Soglia kW/t per neopatentati
    # Neopatentati: max 55 kW/t (95 cv/t) per veicoli fino a 5 anni
    KW_T_SOGLIA = 55
    
    def arricchisci(self, veicoli: List[Dict]) -> List[Dict]:
        """
        Arricchisce lista veicoli
        
        Args:
            veicoli: Lista dizionari veicoli
            
        Returns:
            list: Veicoli arricchiti
        """
        risultati = []
        
        for veicolo in veicoli:
            veicolo_arricchito = self._arricchisci_veicolo(veicolo)
            risultati.append(veicolo_arricchito)
        
        return risultati
    
    def _arricchisci_veicolo(self, veicolo: Dict) -> Dict:
        """
        Arricchisce singolo veicolo
        
        Args:
            veicolo: Dizionario veicolo
            
        Returns:
            dict: Veicolo arricchito
        """
        result = veicolo.copy()
        
        # Calcola neopatentati
        result['neopatentati'] = self._calcola_neopatentati(veicolo)
        
        # Se abbiamo jato_code ma mancano dati, recuperali
        if veicolo.get('jato_code') and not veicolo.get('omologazione'):
            dati_jato = self._recupera_dati_jato(veicolo['jato_code'])
            if dati_jato:
                result.update(dati_jato)
        
        # Calcola prezzo totale se mancante
        if not result.get('prezzo_totale'):
            listino = result.get('prezzo_listino') or 0
            accessori = result.get('prezzo_accessori') or 0
            if listino > 0:
                result['prezzo_totale'] = listino + accessori
        
        # Sostituisci description con JATO se disponibile
        if result.get('jato_product_description'):
            result['description'] = result['jato_product_description']
        
        return result
    
    def _calcola_neopatentati(self, veicolo: Dict) -> str:
        """
        Calcola idoneità neopatentati
        
        La verifica si basa sull'omologazione JATO che contiene
        il rapporto potenza/peso.
        
        Args:
            veicolo: Dati veicolo
            
        Returns:
            str: 'SI', 'NO', o 'ND'
        """
        # Se abbiamo omologazione, usiamo quella
        omologazione = veicolo.get('omologazione', '')
        
        if omologazione:
            # Formato omologazione JATO può contenere info neopatentati
            # Esempio: "e11*2007/46*0123*05" o specifiche potenza/peso
            # Per ora usiamo calcolo basato su kW se disponibile
            pass
        
        # Calcolo basato su kW/t (se abbiamo i dati)
        kw = veicolo.get('kw')
        
        if kw:
            # Stima peso (non sempre disponibile)
            # Se kW < 70, probabilmente idoneo
            if kw <= 70:
                return 'SI'
            elif kw > 95:
                return 'NO'
            else:
                return 'ND'  # Caso ambiguo
        
        return 'ND'
    
    def _recupera_dati_jato(self, jato_code: str) -> Optional[Dict]:
        """
        Recupera dati JATO da codice
        
        Args:
            jato_code: Codice JATO
            
        Returns:
            dict: Dati JATO o None
        """
        jato = JatoModel.query.filter_by(jato_code=jato_code).first()
        
        if not jato:
            return None
        
        return {
            'product_id': jato.product_id,
            'omologazione': jato.homologation,
            'kw': jato.kw,
            'hp': jato.horsepower,
            'alimentazione': jato.alimentazione,
            'jato_product_description': jato.jato_product_description,
            'vehicle_set_description': jato.vehicle_set_description,
            'transmission': jato.transmission_description,
        }
