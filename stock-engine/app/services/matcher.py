# =============================================================================
# STOCK ENGINE - JATO Matcher Service
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Servizio per matching veicoli con database JATO.
# Implementa l'algoritmo di scoring multi-campo.
# Sostituisce il modulo 02_match_jato.py
# =============================================================================

import re
from typing import List, Dict, Optional, Tuple

from app import db
from app.models.jato import JatoModel
from app.models.pattern import PatternCarburante


class JatoMatcher:
    """
    Servizio matching veicoli JATO
    
    STRATEGIA MATCH:
    1. STEP 1 (HARD): MARCA + pattern carburante + kW/HP
    2. STEP 2 (SCORING): Vehicle Set (40pt) > Product (30pt) > Fuel (15pt) > Body (10pt)
    3. STEP 3 (BONUS/PENALITÀ): Parole ripetute (+10) - Parole extra (-2/cad)
    4. STEP 4 (SELEZIONE): Best match con gestione duplicati (PARTIAL)
    """
    
    # Soglia minima match score
    MIN_MATCH_SCORE = 25
    
    # Tolleranze
    KW_TOLERANCE = 3
    HP_TOLERANCE = 5
    CO2_TOLERANCE = 5
    
    # Punteggi scoring
    SCORE_VEHICLE_SET = 40
    SCORE_PRODUCT_DESC = 30
    SCORE_FUEL = 15
    SCORE_BODY = 10
    BONUS_PAROLE_RIPETUTE = 10
    PENALITA_PAROLA_EXTRA = -2
    
    # Stop words da ignorare
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'door', 'doors', 'euro', 'cv', 'kw', 'hp', 'ps',
        '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'i', 'ii', 'iii', 'iv', 'v'
    }
    
    def __init__(self):
        """Inizializza matcher"""
        self._cache_patterns = None
    
    def match_batch(self, veicoli: List[Dict]) -> List[Dict]:
        """
        Match batch di veicoli
        
        Args:
            veicoli: Lista dizionari veicoli
            
        Returns:
            list: Veicoli con dati match
        """
        risultati = []
        
        for veicolo in veicoli:
            veicolo_matched = self.match_singolo(veicolo)
            risultati.append(veicolo_matched)
        
        return risultati
    
    def match_singolo(self, veicolo: Dict) -> Dict:
        """
        Match singolo veicolo
        
        Args:
            veicolo: Dizionario veicolo
            
        Returns:
            dict: Veicolo con dati match aggiunti
        """
        result = veicolo.copy()
        
        marca = veicolo.get('marca', '')
        description = veicolo.get('description', '')
        co2 = veicolo.get('co2')
        
        # Estrai kW/HP dalla description
        kw = self._extract_kw(description)
        hp = self._extract_hp(description)
        
        # Identifica alimentazione da description
        fuel = self._identifica_fuel(description)
        
        # STEP 1: Query candidati
        candidati = self._query_candidati(marca, kw, hp, fuel, co2)
        
        if not candidati:
            result.update({
                'match_status': 'NO_MATCH',
                'match_score': 0,
                'match_note': 'Nessun candidato trovato',
            })
            return result
        
        # STEP 2-4: Trova best match
        best = self._trova_best_match(veicolo, candidati)
        
        if best:
            result.update({
                'jato_code': best.get('jato_code'),
                'product_id': best.get('product_id'),
                'omologazione': best.get('homologation'),
                'kw': best.get('kw'),
                'hp': best.get('horsepower'),
                'alimentazione': best.get('alimentazione'),
                'jato_product_description': best.get('jato_product_description'),
                'vehicle_set_description': best.get('vehicle_set_description'),
                'transmission': best.get('transmission_description'),
                'match_status': best.get('match_status', 'MATCHED'),
                'match_score': best.get('match_score'),
                'match_note': best.get('match_note'),
                'match_details': best.get('match_details'),
            })
        else:
            result.update({
                'match_status': 'NO_MATCH',
                'match_score': 0,
                'match_note': 'Nessun match sopra soglia minima',
            })
        
        return result
    
    def _query_candidati(self, marca: str, kw: int = None, hp: int = None,
                         fuel: str = None, co2: float = None) -> List[Dict]:
        """
        Query candidati JATO
        
        Args:
            marca: Marca veicolo
            kw: Potenza kW
            hp: Potenza HP
            fuel: Tipo alimentazione
            co2: Emissioni CO2
            
        Returns:
            list: Lista candidati
        """
        query = JatoModel.query.filter(
            JatoModel.brand_normalized.ilike(f'%{marca.upper()}%')
        )
        
        # Filtro alimentazione
        if fuel:
            query = query.filter(JatoModel.alimentazione.ilike(f'%{fuel}%'))
        
        # Filtro potenza
        if kw:
            query = query.filter(
                JatoModel.kw.between(kw - self.KW_TOLERANCE, kw + self.KW_TOLERANCE)
            )
        elif hp:
            query = query.filter(
                JatoModel.horsepower.between(hp - self.HP_TOLERANCE, hp + self.HP_TOLERANCE)
            )
        
        candidati = query.limit(200).all()
        
        return [c.to_dict() for c in candidati]
    
    def _trova_best_match(self, veicolo: Dict, candidati: List[Dict]) -> Optional[Dict]:
        """
        Trova miglior match tra candidati
        
        Args:
            veicolo: Veicolo da matchare
            candidati: Lista candidati JATO
            
        Returns:
            dict: Best match o None
        """
        description = veicolo.get('description', '')
        keywords_veicolo = self._extract_keywords(description)
        
        scored = []
        
        for candidato in candidati:
            score, details = self._calcola_score(keywords_veicolo, candidato, veicolo)
            
            if score >= self.MIN_MATCH_SCORE:
                scored.append({
                    'candidato': candidato,
                    'score': score,
                    'details': details,
                })
        
        if not scored:
            return None
        
        # Ordina per score decrescente
        scored.sort(key=lambda x: x['score'], reverse=True)
        
        # Gestione duplicati (stesso score)
        if len(scored) >= 2 and scored[0]['score'] == scored[1]['score']:
            return self._gestisci_duplicato(scored[0], scored[1])
        
        # Best match unico
        best = scored[0]
        result = best['candidato'].copy()
        result['match_score'] = best['score']
        result['match_details'] = best['details']
        result['match_status'] = 'MATCHED'
        
        return result
    
    def _calcola_score(self, keywords_veicolo: set, candidato: Dict, 
                       veicolo: Dict) -> Tuple[int, Dict]:
        """
        Calcola score per un candidato
        
        Args:
            keywords_veicolo: Set parole chiave veicolo
            candidato: Candidato JATO
            veicolo: Veicolo originale
            
        Returns:
            tuple: (score, details)
        """
        score = 0
        details = {}
        
        # Keywords candidato
        kw_vehicle_set = self._extract_keywords(candidato.get('vehicle_set', ''))
        kw_product = self._extract_keywords(candidato.get('description', ''))
        
        # SCORE: Vehicle Set match
        match_vs = keywords_veicolo & kw_vehicle_set
        if match_vs:
            bonus_vs = min(len(match_vs) * 10, self.SCORE_VEHICLE_SET)
            score += bonus_vs
            details['vehicle_set'] = list(match_vs)
        
        # SCORE: Product description match
        match_prod = keywords_veicolo & kw_product
        if match_prod:
            bonus_prod = min(len(match_prod) * 8, self.SCORE_PRODUCT_DESC)
            score += bonus_prod
            details['product'] = list(match_prod)
        
        # SCORE: Fuel match
        fuel_veicolo = self._identifica_fuel(veicolo.get('description', ''))
        fuel_candidato = candidato.get('alimentazione', '')
        if fuel_veicolo and fuel_candidato:
            if self._normalize_fuel(fuel_veicolo) == self._normalize_fuel(fuel_candidato):
                score += self.SCORE_FUEL
                details['fuel'] = True
        
        # BONUS: Parole ripetute (segnale forte)
        parole_ripetute = self._conta_parole_ripetute(veicolo.get('description', ''))
        if parole_ripetute > 0:
            score += min(parole_ripetute * 5, self.BONUS_PAROLE_RIPETUTE)
            details['ripetute'] = parole_ripetute
        
        # PENALITÀ: Parole extra nel candidato
        parole_extra = kw_product - keywords_veicolo
        if parole_extra:
            penalita = len(parole_extra) * abs(self.PENALITA_PAROLA_EXTRA)
            score = max(0, score - penalita)
            details['extra'] = list(parole_extra)[:5]
        
        return score, details
    
    def _gestisci_duplicato(self, primo: Dict, secondo: Dict) -> Dict:
        """
        Gestisce caso di duplicato (stesso score)
        
        Sceglie la versione "base" (description più corta)
        
        Args:
            primo: Primo candidato
            secondo: Secondo candidato
            
        Returns:
            dict: Candidato scelto con status PARTIAL
        """
        desc1 = primo['candidato'].get('description', '')
        desc2 = secondo['candidato'].get('description', '')
        
        # Scegli il più corto (versione base)
        if len(desc1) <= len(desc2):
            scelto = primo
        else:
            scelto = secondo
        
        result = scelto['candidato'].copy()
        result['match_score'] = scelto['score']
        result['match_details'] = scelto['details']
        result['match_status'] = 'PARTIAL'
        result['match_note'] = 'Duplicato ambiguo, scelta versione base'
        
        return result
    
    def _extract_keywords(self, text: str) -> set:
        """Estrae parole chiave da testo"""
        if not text:
            return set()
        
        text = text.upper()
        text = re.sub(r'[^\w\s\-]', ' ', text)
        words = text.split()
        
        keywords = set()
        for word in words:
            if word.lower() in self.STOP_WORDS:
                continue
            if len(word) < 2:
                continue
            if word.isdigit():
                continue
            keywords.add(word)
        
        return keywords
    
    def _extract_kw(self, description: str) -> Optional[int]:
        """Estrae kW da description (esclude KWH batteria)"""
        if not description:
            return None
        
        # Pattern kW che esclude KWH
        match = re.search(r'(\d+)\s*kw(?!h)', description, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_hp(self, description: str) -> Optional[int]:
        """Estrae HP/CV da description"""
        if not description:
            return None
        
        match = re.search(r'(\d+)\s*(?:cv|hp|ps)', description, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _identifica_fuel(self, description: str) -> Optional[str]:
        """Identifica tipo alimentazione da description"""
        if not description:
            return None
        
        return PatternCarburante.identifica_fuel(description)
    
    def _normalize_fuel(self, fuel: str) -> str:
        """Normalizza nome alimentazione per confronto"""
        return PatternCarburante.normalizza_fuel(fuel)
    
    def _conta_parole_ripetute(self, description: str) -> int:
        """Conta parole ripetute (segnale di enfasi)"""
        if not description:
            return 0
        
        words = description.upper().split()
        counts = {}
        for word in words:
            if word.lower() not in self.STOP_WORDS and len(word) > 2:
                counts[word] = counts.get(word, 0) + 1
        
        return sum(1 for c in counts.values() if c > 1)
