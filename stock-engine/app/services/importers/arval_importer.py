# =============================================================================
# STOCK ENGINE - ARVAL Importer
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Importer specifico per file stock ARVAL.
# NOTA: ARVAL ha una struttura diversa da AYVENS (colonne D, E, F).
# =============================================================================

from typing import List, Dict
from datetime import datetime

from .base_importer import BaseImporter


class ArvalImporter(BaseImporter):
    """
    Importer per file stock ARVAL
    
    File ARVAL caratteristiche:
    - Formato: XLSX (principale)
    - Colonne chiave: MARCA (D), MODELLO (E), VERSIONE (F)
    - VERSIONE viene svuotata dopo normalizzazione per evitare duplicati
    """
    
    NOLEGGIATORE = 'ARVAL'
    
    # Pattern file ARVAL
    FILE_PATTERNS = [
        'arval*',
        '*arval*stock*',
        'stock*arval*',
    ]
    
    # ARVAL usa principalmente XLSX
    EXTENSIONS_PRIORITY = ['.xlsx', '.csv']
    
    def get_column_mapping(self) -> Dict[str, str]:
        """
        Mapping colonne ARVAL → campi database
        
        ARVAL ha struttura diversa:
        - MARCA in colonna D
        - MODELLO in colonna E
        - VERSIONE in colonna F (da svuotare dopo normalizzazione)
        """
        return {
            # Identificazione
            'VIN': 'vin',
            'TARGA': 'targa',
            
            # Marca/Modello (ARVAL usa MODELLO + VERSIONE)
            'MARCA': 'marca_originale',
            'MODELLO': 'modello_originale',
            'VERSIONE': 'versione_originale',
            
            # Verranno normalizzati
            'MARCA': 'marca',
            'MODELLO': 'modello',
            
            # Tecnici
            'ALIMENTAZIONE': 'fuel_originale',
            'CO2': 'co2',
            'KW': 'kw',
            'CV': 'hp',
            
            # Prezzi
            'PREZZO_LISTINO': 'prezzo_listino',
            'PREZZO_OPTIONAL': 'prezzo_accessori',
            
            # Location
            'DEPOSITO': 'location',
            'INDIRIZZO_DEPOSITO': 'location_address',
            
            # Date
            'DATA_ARRIVO_PREVISTA': 'data_arrivo',
            'DATA_IMMATRICOLAZIONE': 'data_immatricolazione',
            
            # Colori
            'COLORE_ESTERNO': 'colore',
            'COLORE_INTERNO': 'colore_interno',
            
            # Altri
            'KM': 'km',
            'CARROZZERIA': 'body_type',
            'CAMBIO': 'transmission',
            
            # Comments (campo speciale ARVAL)
            'COMMENTS': 'note',
        }
    
    def get_required_columns(self) -> List[str]:
        """Colonne obbligatorie per ARVAL"""
        return [
            'MARCA',
            'MODELLO',
        ]
    
    def post_process_row(self, row: Dict) -> Dict:
        """
        Post-processing specifico ARVAL
        
        IMPORTANTE: Gestisce la concatenazione MODELLO + VERSIONE
        """
        # Converti date
        row = self._converti_date(row)
        
        # ARVAL: Costruisci description da MODELLO + VERSIONE
        modello = row.get('modello_originale', '') or ''
        versione = row.get('versione_originale', '') or ''
        
        if versione and versione not in modello:
            row['description_originale'] = f"{modello} {versione}".strip()
            row['description'] = row['description_originale']
        else:
            row['description_originale'] = modello
            row['description'] = modello
        
        # Assicurati che marca sia uppercase
        if row.get('marca'):
            row['marca'] = row['marca'].upper().strip()
        
        # Preserva originali
        if row.get('marca') and not row.get('marca_originale'):
            row['marca_originale'] = row['marca']
        
        return row
    
    def _converti_date(self, row: Dict) -> Dict:
        """Converte stringhe date in oggetti date"""
        date_fields = ['data_arrivo', 'data_immatricolazione']
        
        for field in date_fields:
            value = row.get(field)
            if value and isinstance(value, str):
                # Prova vari formati
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        row[field] = datetime.strptime(value, fmt).date()
                        break
                    except ValueError:
                        continue
        
        return row
