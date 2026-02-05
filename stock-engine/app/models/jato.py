# =============================================================================
# STOCK ENGINE - Modello JATO
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Tabella che contiene i dati del database JATO, usata per il matching
# e l'arricchimento dei veicoli stock.
# =============================================================================

from app import db


class JatoModel(db.Model):
    """
    Modello veicolo JATO (database di riferimento)
    
    Contiene tutti i modelli veicolo con specifiche tecniche
    usate per il matching e l'arricchimento.
    """
    
    __tablename__ = 'jato_models'
    
    # ==========================================================================
    # CHIAVI
    # ==========================================================================
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), unique=True, index=True)
    jato_code = db.Column(db.String(50), index=True)
    
    # ==========================================================================
    # IDENTIFICAZIONE VEICOLO
    # ==========================================================================
    brand_description = db.Column(db.String(100), index=True)  # FIAT, BMW, etc.
    jato_model = db.Column(db.String(100))  # 500, X1, etc.
    jato_product_description = db.Column(db.String(300))  # Nome completo modello
    vehicle_set_description = db.Column(db.String(300))  # Variante/allestimento
    
    # ==========================================================================
    # SPECIFICHE TECNICHE
    # ==========================================================================
    alimentazione = db.Column(db.String(50), index=True)  # Diesel, Petrol, Electric, etc.
    kw = db.Column(db.Integer)
    horsepower = db.Column(db.Integer)
    
    # Omologazione (importante per neopatentati)
    homologation = db.Column(db.String(100))
    
    # Trasmissione
    transmission_description = db.Column(db.String(100))
    powertrain_type = db.Column(db.String(50))
    
    # Emissioni
    co2_wltp = db.Column(db.Float)
    
    # Carrozzeria
    body_type = db.Column(db.String(50))
    doors = db.Column(db.Integer)
    
    # ==========================================================================
    # CAMPI NORMALIZZATI (per ricerche veloci)
    # ==========================================================================
    brand_normalized = db.Column(db.String(100), index=True)  # UPPERCASE senza accenti
    description_normalized = db.Column(db.Text)  # Per full-text search
    
    # ==========================================================================
    # METADATA
    # ==========================================================================
    source_sheet = db.Column(db.String(50))  # Foglio Excel origine
    importato_il = db.Column(db.DateTime)
    
    # ==========================================================================
    # INDICI
    # ==========================================================================
    __table_args__ = (
        db.Index('idx_jato_brand_model', 'brand_description', 'jato_model'),
        db.Index('idx_jato_fuel_kw', 'alimentazione', 'kw'),
    )
    
    # ==========================================================================
    # METODI
    # ==========================================================================
    
    def to_dict(self):
        """Converte in dizionario"""
        return {
            'product_id': self.product_id,
            'jato_code': self.jato_code,
            'brand': self.brand_description,
            'model': self.jato_model,
            'description': self.jato_product_description,
            'vehicle_set': self.vehicle_set_description,
            'alimentazione': self.alimentazione,
            'kw': self.kw,
            'hp': self.horsepower,
            'homologation': self.homologation,
            'transmission': self.transmission_description,
            'co2': self.co2_wltp,
        }
    
    @classmethod
    def search_by_brand(cls, brand: str, limit: int = 100):
        """
        Cerca modelli per marca
        
        Args:
            brand: Marca da cercare
            limit: Numero massimo risultati
            
        Returns:
            list: Lista modelli trovati
        """
        return cls.query.filter(
            cls.brand_description.ilike(f'%{brand}%')
        ).limit(limit).all()
    
    @classmethod
    def search_candidates(cls, brand: str, kw: int = None, hp: int = None, 
                         fuel: str = None, kw_tolerance: int = 3, hp_tolerance: int = 5):
        """
        Cerca candidati per matching
        
        Args:
            brand: Marca veicolo
            kw: Potenza kW (opzionale)
            hp: Potenza HP (opzionale)
            fuel: Tipo alimentazione (opzionale)
            kw_tolerance: Tolleranza kW
            hp_tolerance: Tolleranza HP
            
        Returns:
            list: Lista candidati
        """
        query = cls.query.filter(
            cls.brand_normalized.ilike(f'%{brand.upper()}%')
        )
        
        # Filtro alimentazione se specificato
        if fuel:
            query = query.filter(cls.alimentazione.ilike(f'%{fuel}%'))
        
        # Filtro potenza se specificato
        if kw:
            query = query.filter(
                cls.kw.between(kw - kw_tolerance, kw + kw_tolerance)
            )
        elif hp:
            query = query.filter(
                cls.horsepower.between(hp - hp_tolerance, hp + hp_tolerance)
            )
        
        return query.limit(200).all()
    
    @classmethod
    def get_statistics(cls):
        """Statistiche database JATO"""
        from sqlalchemy import func
        
        total = cls.query.count()
        
        brands = db.session.query(
            cls.brand_description,
            func.count(cls.id)
        ).group_by(cls.brand_description).all()
        
        fuels = db.session.query(
            cls.alimentazione,
            func.count(cls.id)
        ).group_by(cls.alimentazione).all()
        
        return {
            'totale_modelli': total,
            'marche_uniche': len(brands),
            'per_marca': {b[0]: b[1] for b in brands if b[0]},
            'per_alimentazione': {f[0]: f[1] for f in fuels if f[0]},
        }
    
    def __repr__(self):
        return f'<JatoModel {self.brand_description} {self.jato_product_description}>'
