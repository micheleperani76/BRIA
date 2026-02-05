# =============================================================================
# STOCK ENGINE - Modello Veicolo
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Tabella principale che contiene tutti i veicoli stock importati
# dai vari noleggiatori, con dati originali e arricchiti JATO.
# =============================================================================

from datetime import datetime, date
from app import db


class Veicolo(db.Model):
    """
    Modello veicolo stock
    
    Contiene:
    - Dati originali dal noleggiatore
    - Dati normalizzati (dopo glossario)
    - Dati arricchiti da JATO
    - Metadati elaborazione
    """
    
    __tablename__ = 'veicoli'
    
    # ==========================================================================
    # CHIAVI E IDENTIFICATIVI
    # ==========================================================================
    id = db.Column(db.Integer, primary_key=True)
    
    # Noleggiatore di provenienza
    noleggiatore = db.Column(db.String(20), nullable=False, index=True)
    
    # VIN (Vehicle Identification Number) - può essere NULL per alcuni noleggiatori
    vin = db.Column(db.String(50), index=True)
    
    # Data import (per storico giornaliero)
    data_import = db.Column(db.Date, nullable=False, index=True, default=date.today)
    
    # ==========================================================================
    # DATI ORIGINALI NOLEGGIATORE (preservati per tracciabilità)
    # ==========================================================================
    marca_originale = db.Column(db.String(100))
    modello_originale = db.Column(db.String(200))
    description_originale = db.Column(db.Text)
    fuel_originale = db.Column(db.String(50))
    
    # ==========================================================================
    # DATI NORMALIZZATI (dopo applicazione glossario)
    # ==========================================================================
    marca = db.Column(db.String(100), index=True)
    modello = db.Column(db.String(200))
    description = db.Column(db.String(500))
    
    # ==========================================================================
    # DATI TECNICI ORIGINALI
    # ==========================================================================
    co2 = db.Column(db.Float)                    # g/km
    prezzo_listino = db.Column(db.Float)
    prezzo_accessori = db.Column(db.Float)
    prezzo_totale = db.Column(db.Float)
    
    # Location
    location = db.Column(db.String(200))
    location_address = db.Column(db.String(300))
    
    # Date
    data_arrivo = db.Column(db.Date)
    data_immatricolazione = db.Column(db.Date)
    
    # Altri campi originali (variano per noleggiatore)
    colore = db.Column(db.String(100))
    colore_interno = db.Column(db.String(100))
    targa = db.Column(db.String(20))
    km = db.Column(db.Integer)
    
    # Campo JSON per dati extra noleggiatore-specifici
    dati_extra = db.Column(db.JSON)
    
    # ==========================================================================
    # DATI JATO (arricchimento)
    # ==========================================================================
    jato_code = db.Column(db.String(50), index=True)
    product_id = db.Column(db.String(50))
    omologazione = db.Column(db.String(100))
    
    # Potenza
    kw = db.Column(db.Integer)
    hp = db.Column(db.Integer)
    
    # Alimentazione normalizzata
    alimentazione = db.Column(db.String(50), index=True)  # DIESEL, PETROL, ELECTRIC, etc.
    
    # Descrizione JATO (sostituisce description originale)
    jato_product_description = db.Column(db.String(300))
    vehicle_set_description = db.Column(db.String(300))
    
    # Trasmissione
    transmission = db.Column(db.String(100))
    powertrain = db.Column(db.String(50))
    
    # ==========================================================================
    # MATCH INFO
    # ==========================================================================
    match_status = db.Column(db.String(20), index=True)  # MATCHED, PARTIAL, NO_MATCH
    match_score = db.Column(db.Integer)
    match_note = db.Column(db.Text)
    match_details = db.Column(db.JSON)  # Dettagli scoring
    
    # ==========================================================================
    # CAMPI BUSINESS
    # ==========================================================================
    neopatentati = db.Column(db.String(5), default='ND')  # SI, NO, ND
    stato = db.Column(db.String(20), default='disponibile')  # disponibile, venduto, riservato
    
    # Promo/Note
    is_promo = db.Column(db.Boolean, default=False)
    note = db.Column(db.Text)
    
    # ==========================================================================
    # METADATA
    # ==========================================================================
    elaborato_il = db.Column(db.DateTime, default=datetime.utcnow)
    aggiornato_il = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Riferimento elaborazione
    elaborazione_id = db.Column(db.Integer, db.ForeignKey('elaborazioni.id'))
    
    # ==========================================================================
    # VINCOLI
    # ==========================================================================
    __table_args__ = (
        # Vincolo unicità: stesso veicolo (VIN) stesso giorno stesso noleggiatore
        db.UniqueConstraint('noleggiatore', 'vin', 'data_import', name='uq_veicolo_giornaliero'),
        # Indice composto per query frequenti
        db.Index('idx_noleggiatore_data', 'noleggiatore', 'data_import'),
        db.Index('idx_marca_modello', 'marca', 'modello'),
    )
    
    # ==========================================================================
    # METODI
    # ==========================================================================
    
    def to_dict(self, include_originali=False):
        """
        Converte veicolo in dizionario per API
        
        Args:
            include_originali: Se True, include anche dati originali
            
        Returns:
            dict: Rappresentazione veicolo
        """
        data = {
            'id': self.id,
            'noleggiatore': self.noleggiatore,
            'vin': self.vin,
            'data_import': self.data_import.isoformat() if self.data_import else None,
            
            # Dati normalizzati
            'marca': self.marca,
            'modello': self.modello,
            'description': self.description,
            
            # Tecnici
            'co2': self.co2,
            'prezzo_listino': self.prezzo_listino,
            'prezzo_totale': self.prezzo_totale,
            'location': self.location,
            'data_arrivo': self.data_arrivo.isoformat() if self.data_arrivo else None,
            'colore': self.colore,
            
            # JATO
            'jato_code': self.jato_code,
            'product_id': self.product_id,
            'omologazione': self.omologazione,
            'kw': self.kw,
            'hp': self.hp,
            'alimentazione': self.alimentazione,
            'jato_description': self.jato_product_description,
            
            # Match
            'match_status': self.match_status,
            'match_score': self.match_score,
            
            # Business
            'neopatentati': self.neopatentati,
            'stato': self.stato,
            'is_promo': self.is_promo,
        }
        
        if include_originali:
            data['originali'] = {
                'marca': self.marca_originale,
                'modello': self.modello_originale,
                'description': self.description_originale,
                'fuel': self.fuel_originale,
            }
        
        return data
    
    def to_excel_row(self):
        """
        Converte veicolo in riga per export Excel
        
        Returns:
            dict: Riga Excel con tutte le colonne
        """
        return {
            'VIN': self.vin,
            'Marca': self.marca,
            'Modello': self.modello,
            'Description': self.jato_product_description or self.description,
            'Alimentazione': self.alimentazione,
            'KW': self.kw,
            'HP': self.hp,
            'CO2': self.co2,
            'Prezzo Listino': self.prezzo_listino,
            'Prezzo Totale': self.prezzo_totale,
            'Location': self.location,
            'Data Arrivo': self.data_arrivo,
            'Colore': self.colore,
            'Neopatentati': self.neopatentati,
            'Jato Code': self.jato_code,
            'Product ID': self.product_id,
            'Omologazione': self.omologazione,
            'Match Status': self.match_status,
            'Match Score': self.match_score,
            'Stato': self.stato,
        }
    
    @classmethod
    def get_by_noleggiatore_data(cls, noleggiatore: str, data: date):
        """
        Recupera tutti i veicoli per noleggiatore e data
        
        Args:
            noleggiatore: Nome noleggiatore
            data: Data import
            
        Returns:
            Query: SQLAlchemy query
        """
        return cls.query.filter_by(
            noleggiatore=noleggiatore.upper(),
            data_import=data
        )
    
    @classmethod
    def get_statistics(cls, noleggiatore: str = None, data: date = None):
        """
        Statistiche veicoli
        
        Args:
            noleggiatore: Filtro noleggiatore (opzionale)
            data: Filtro data (opzionale)
            
        Returns:
            dict: Statistiche
        """
        query = cls.query
        
        if noleggiatore:
            query = query.filter_by(noleggiatore=noleggiatore.upper())
        if data:
            query = query.filter_by(data_import=data)
        
        total = query.count()
        matched = query.filter_by(match_status='MATCHED').count()
        partial = query.filter_by(match_status='PARTIAL').count()
        no_match = query.filter_by(match_status='NO_MATCH').count()
        
        return {
            'totale': total,
            'matched': matched,
            'partial': partial,
            'no_match': no_match,
            'match_rate': round((matched / total) * 100, 1) if total > 0 else 0
        }
    
    def __repr__(self):
        return f'<Veicolo {self.noleggiatore} {self.marca} {self.modello}>'
