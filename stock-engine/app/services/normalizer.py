# =============================================================================
# STOCK ENGINE - Normalizer Service
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Servizio per normalizzazione dati con applicazione glossario.
# Sostituisce il modulo 00_applica_glossario.py
# =============================================================================

import re
from typing import List, Dict

from app.models.glossario import Glossario


class Normalizer:
    """
    Servizio normalizzazione dati veicoli
    
    Applica:
    - Regole glossario (sostituzioni termini)
    - Normalizzazione caratteri speciali
    - Standardizzazione formato
    """
    
    def __init__(self):
        """Inizializza normalizer"""
        self._cache_glossario = {}
    
    def applica(self, veicoli: List[Dict], noleggiatore: str) -> List[Dict]:
        """
        Applica normalizzazione a lista veicoli
        
        Args:
            veicoli: Lista dizionari veicoli
            noleggiatore: Nome noleggiatore
            
        Returns:
            list: Veicoli normalizzati
        """
        # Carica regole glossario (con cache)
        regole = self._get_regole(noleggiatore)
        
        risultati = []
        
        for veicolo in veicoli:
            veicolo_norm = self._normalizza_veicolo(veicolo, regole)
            risultati.append(veicolo_norm)
        
        return risultati
    
    def _get_regole(self, noleggiatore: str) -> List[Dict]:
        """
        Recupera regole glossario (con cache)
        
        Args:
            noleggiatore: Nome noleggiatore
            
        Returns:
            list: Regole glossario
        """
        if noleggiatore not in self._cache_glossario:
            regole = Glossario.get_regole(noleggiatore)
            self._cache_glossario[noleggiatore] = [
                {
                    'cerca': r.cerca,
                    'sostituisci': r.sostituisci,
                    'colonna': r.colonna,
                    'pattern': re.compile(r'\b' + re.escape(r.cerca) + r'\b', re.IGNORECASE)
                }
                for r in regole
            ]
        
        return self._cache_glossario[noleggiatore]
    
    def _normalizza_veicolo(self, veicolo: Dict, regole: List[Dict]) -> Dict:
        """
        Normalizza singolo veicolo
        
        Args:
            veicolo: Dizionario veicolo
            regole: Regole glossario
            
        Returns:
            dict: Veicolo normalizzato
        """
        # Copia per non modificare originale
        result = veicolo.copy()
        
        # Campi da normalizzare
        campi = ['marca', 'modello', 'description']
        
        for campo in campi:
            valore = result.get(campo)
            if valore and isinstance(valore, str):
                # Applica regole glossario
                valore_norm = self._applica_regole(valore, regole, campo)
                
                # Normalizzazione aggiuntiva
                valore_norm = self._normalizza_testo(valore_norm)
                
                result[campo] = valore_norm
        
        return result
    
    def _applica_regole(self, testo: str, regole: List[Dict], campo: str) -> str:
        """
        Applica regole glossario a un testo
        
        IMPORTANTE: Match su parola intera per evitare sostituzioni parziali
        come "ALFA" → "ALFA ROMEO" → "ALFA ROMEO ROMEO"
        
        Args:
            testo: Testo da normalizzare
            regole: Lista regole
            campo: Nome campo (per filtrare regole)
            
        Returns:
            str: Testo normalizzato
        """
        risultato = testo
        
        for regola in regole:
            # Applica solo se regola è per questo campo o per tutti
            if regola['colonna'] and regola['colonna'] != campo:
                continue
            
            # Applica sostituzione con pattern precompilato
            risultato = regola['pattern'].sub(regola['sostituisci'], risultato)
        
        return risultato
    
    def _normalizza_testo(self, testo: str) -> str:
        """
        Normalizzazione base del testo
        
        - Rimuove doppi spazi
        - Rimuove caratteri speciali comuni
        - Trim
        
        Args:
            testo: Testo da normalizzare
            
        Returns:
            str: Testo normalizzato
        """
        if not testo:
            return testo
        
        # Caratteri da sostituire
        replacements = {
            '§': ' ',
            '•': ' ',
            '–': '-',
            '—': '-',
            '_': ' ',
            '°': ' ',
            '\t': ' ',
            '\n': ' ',
        }
        
        result = testo
        for old, new in replacements.items():
            result = result.replace(old, new)
        
        # Rimuovi spazi multipli
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def invalida_cache(self):
        """Invalida cache glossario (da chiamare dopo modifiche)"""
        self._cache_glossario = {}
