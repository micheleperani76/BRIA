# =============================================================================
# STOCK ENGINE - Modello Pattern Carburante
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Tabella che contiene i pattern per identificare il tipo di alimentazione
# dalla descrizione del veicolo (es. "180D" → DIESEL, "TSI" → PETROL).
# =============================================================================

from app import db


class PatternCarburante(db.Model):
    """
    Pattern per identificazione alimentazione
    
    Esempio:
    - pattern: "180D"
    - fuel_type: "DIESEL"
    - priorita: 10 (più alto = verificato prima)
    """
    
    __tablename__ = 'pattern_carburante'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Pattern da cercare (es. "TDI", "180D", "PHEV")
    pattern = db.Column(db.String(50), nullable=False, unique=True)
    
    # Tipo alimentazione risultante
    fuel_type = db.Column(db.String(30), nullable=False)  # DIESEL, PETROL, ELECTRIC, HYBRID, PLUGIN, GPL, METHANE
    
    # Priorità (pattern più specifici hanno priorità più alta)
    # Es: "HYBRID-G" (20) viene verificato prima di "HYBRID" (10)
    priorita = db.Column(db.Integer, default=10)
    
    # Note
    note = db.Column(db.Text)
    
    # Stato
    attivo = db.Column(db.Boolean, default=True)
    
    # ==========================================================================
    # METODI
    # ==========================================================================
    
    @classmethod
    def get_all_patterns(cls):
        """
        Recupera tutti i pattern attivi ordinati per priorità
        
        Returns:
            list: Pattern ordinati per priorità decrescente
        """
        return cls.query.filter_by(attivo=True).order_by(
            cls.priorita.desc()
        ).all()
    
    @classmethod
    def identifica_fuel(cls, description: str) -> str:
        """
        Identifica tipo alimentazione da descrizione
        
        Args:
            description: Descrizione veicolo
            
        Returns:
            str: Tipo alimentazione o None
        """
        import re
        
        if not description:
            return None
        
        description_upper = description.upper()
        
        # Carica pattern ordinati per priorità
        patterns = cls.get_all_patterns()
        
        for p in patterns:
            # Cerca pattern come parola intera o parte di parola
            if re.search(r'\b' + re.escape(p.pattern.upper()) + r'\b', description_upper):
                return p.fuel_type
            # Cerca anche senza word boundary per pattern come "180D"
            if p.pattern.upper() in description_upper:
                return p.fuel_type
        
        return None
    
    @classmethod
    def normalizza_fuel(cls, fuel_raw: str) -> str:
        """
        Normalizza nome alimentazione
        
        Args:
            fuel_raw: Nome alimentazione grezzo
            
        Returns:
            str: Nome normalizzato
        """
        if not fuel_raw:
            return None
        
        fuel = fuel_raw.upper()
        
        # Mapping normalizzazione
        mapping = {
            'ELECTRIC': ['ELECTRIC', 'ELETTRIC', 'BEV', 'EV'],
            'PLUGIN': ['PLUG', 'PHEV', 'PLUG-IN'],
            'HYBRID': ['HYBRID', 'IBRIDA', 'MHEV', 'HEV', 'MILD'],
            'DIESEL': ['DIESEL', 'TDI', 'CDI', 'HDI', 'GASOLIO', 'D'],
            'PETROL': ['PETROL', 'BENZINA', 'GASOLINE', 'TSI', 'TFSI', 'TURBO'],
            'GPL': ['GPL', 'LPG'],
            'METHANE': ['METHAN', 'METANO', 'CNG'],
        }
        
        for normalized, variants in mapping.items():
            for variant in variants:
                if variant in fuel:
                    return normalized
        
        return fuel
    
    def to_dict(self):
        """Converte in dizionario"""
        return {
            'id': self.id,
            'pattern': self.pattern,
            'fuel_type': self.fuel_type,
            'priorita': self.priorita,
            'note': self.note,
            'attivo': self.attivo,
        }
    
    def __repr__(self):
        return f'<PatternCarburante {self.pattern} → {self.fuel_type}>'
