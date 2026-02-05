# =============================================================================
# STOCK ENGINE - AYVENS Importer
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Importer specifico per file stock AYVENS.
# Gestisce la struttura specifica dei file CSV/XLSX AYVENS.
# =============================================================================

from typing import List, Dict
from datetime import datetime

from .base_importer import BaseImporter


class AyvensImporter(BaseImporter):
    """
    Importer per file stock AYVENS
    
    File AYVENS caratteristiche:
    - Formato: CSV (preferito) o XLSX
    - Separatore: punto e virgola (;)
    - Decimale: virgola (,)
    - Colonne principali: MAKENAME, MODELNAME, DESCRIPTION, etc.
    """
    
    NOLEGGIATORE = 'AYVENS'
    
    # Pattern file AYVENS
    FILE_PATTERNS = [
        'stockReport*',
        '*stock*',
        'ayvens*stock*',
    ]
    
    # AYVENS preferisce CSV (XLSX può avere problemi di shift)
    EXTENSIONS_PRIORITY = ['.csv', '.xlsx']
    
    def get_column_mapping(self) -> Dict[str, str]:
        """
        Mapping colonne AYVENS → campi database
        
        Basato sulla struttura reale dei file AYVENS.
        """
        return {
            # Identificazione
            'VIN': 'vin',
            'VEHICLEID': 'vehicle_id',
            
            # Marca/Modello (originali)
            'MAKENAME': 'marca_originale',
            'MODELNAME': 'modello_originale',
            'DESCRIPTION': 'description_originale',
            
            # Marca/Modello (verranno normalizzati)
            'MAKENAME': 'marca',
            'MODELNAME': 'modello',
            'DESCRIPTION': 'description',
            
            # Tecnici
            'ENGINEDESCRIPTION': 'fuel_originale',
            'CO2EMISSION': 'co2',
            'KW': 'kw',
            'HP': 'hp',
            
            # Prezzi
            'PREZZO_ACCESSORI': 'prezzo_accessori',
            'PREZZO_LISTINO': 'prezzo_listino',
            'PREZZO_TOTALE': 'prezzo_totale',
            
            # Location
            'LOCATION': 'location',
            'LOCATION_ADDRESS': 'location_address',
            
            # Date
            'ESTIMATEDDELIVERYDATE': 'data_arrivo',
            'CATALOGFROM': 'data_catalogo',
            
            # Colori
            'EXTERIORCOLORGROUP': 'colore',
            'INTERIORCOLORGROUP': 'colore_interno',
            
            # Altri
            'TARGA': 'targa',
            'KM': 'km',
            'BODYSTYLE': 'body_type',
            'DOORS': 'doors',
            'TRANSMISSION': 'transmission',
        }
    
    def get_required_columns(self) -> List[str]:
        """Colonne obbligatorie per AYVENS"""
        return [
            'MAKENAME',
            'MODELNAME',
            'DESCRIPTION',
        ]
    
    def post_process_row(self, row: Dict) -> Dict:
        """
        Post-processing specifico AYVENS
        
        - Converte date
        - Pulisce valori
        - Calcola campi derivati
        """
        # Converti date
        row = self._converti_date(row)
        
        # Pulisci description (rimuovi caratteri speciali)
        if row.get('description'):
            row['description'] = self._pulisci_description(row['description'])
        
        # Assicurati che marca sia uppercase
        if row.get('marca'):
            row['marca'] = row['marca'].upper().strip()
        
        # Preserva originali
        if row.get('marca') and not row.get('marca_originale'):
            row['marca_originale'] = row['marca']
        if row.get('modello') and not row.get('modello_originale'):
            row['modello_originale'] = row['modello']
        if row.get('description') and not row.get('description_originale'):
            row['description_originale'] = row['description']
        
        return row
    
    def _converti_date(self, row: Dict) -> Dict:
        """Converte stringhe date in oggetti date"""
        date_fields = ['data_arrivo', 'data_catalogo']
        
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
    
    def _pulisci_description(self, desc: str) -> str:
        """
        Pulisce description rimuovendo caratteri speciali
        
        AYVENS usa caratteri come § • – nelle description
        """
        if not desc:
            return desc
        
        # Caratteri da rimuovere/sostituire
        replacements = {
            '§': ' ',
            '•': ' ',
            '–': '-',
            '—': '-',
            '_': ' ',
            '  ': ' ',  # Doppi spazi
        }
        
        result = desc
        for old, new in replacements.items():
            result = result.replace(old, new)
        
        return result.strip()
