# =============================================================================
# STOCK ENGINE - Modello Elaborazione
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Tabella che contiene il log di tutte le elaborazioni eseguite,
# con statistiche e riferimento al file Excel generato.
# =============================================================================

from datetime import datetime
from app import db


class Elaborazione(db.Model):
    """
    Log elaborazioni stock
    
    Tiene traccia di ogni elaborazione eseguita con:
    - Statistiche (veicoli importati, matched, etc.)
    - Durata
    - File output generato
    - Eventuali errori
    """
    
    __tablename__ = 'elaborazioni'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Noleggiatore elaborato
    noleggiatore = db.Column(db.String(20), nullable=False, index=True)
    
    # Timestamp
    data_elaborazione = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # File origine
    file_origine = db.Column(db.String(255))
    file_origine_size = db.Column(db.Integer)  # bytes
    
    # Statistiche
    veicoli_importati = db.Column(db.Integer, default=0)
    veicoli_matched = db.Column(db.Integer, default=0)
    veicoli_partial = db.Column(db.Integer, default=0)
    veicoli_no_match = db.Column(db.Integer, default=0)
    match_rate = db.Column(db.Float)
    
    # Performance
    durata_secondi = db.Column(db.Integer)
    
    # Stato
    stato = db.Column(db.String(20), default='in_corso')  # in_corso, completata, errore
    
    # Errore (se stato = 'errore')
    errore = db.Column(db.Text)
    
    # File output
    file_excel_output = db.Column(db.String(255))
    
    # Relazione con veicoli
    veicoli = db.relationship('Veicolo', backref='elaborazione', lazy='dynamic')
    
    # ==========================================================================
    # METODI
    # ==========================================================================
    
    def completa(self, veicoli_importati: int, veicoli_matched: int, 
                 veicoli_partial: int = 0, veicoli_no_match: int = 0,
                 file_excel: str = None, durata: int = None):
        """
        Marca elaborazione come completata
        
        Args:
            veicoli_importati: Numero veicoli importati
            veicoli_matched: Numero veicoli con match JATO
            veicoli_partial: Numero veicoli con match parziale
            veicoli_no_match: Numero veicoli senza match
            file_excel: Path file Excel generato
            durata: Durata in secondi
        """
        self.stato = 'completata'
        self.veicoli_importati = veicoli_importati
        self.veicoli_matched = veicoli_matched
        self.veicoli_partial = veicoli_partial
        self.veicoli_no_match = veicoli_no_match
        self.match_rate = round((veicoli_matched / veicoli_importati) * 100, 1) if veicoli_importati > 0 else 0
        self.file_excel_output = file_excel
        self.durata_secondi = durata
        
        db.session.commit()
    
    def errore(self, messaggio: str):
        """
        Marca elaborazione come fallita
        
        Args:
            messaggio: Messaggio errore
        """
        self.stato = 'errore'
        self.errore = messaggio
        db.session.commit()
    
    def to_dict(self):
        """Converte in dizionario"""
        return {
            'id': self.id,
            'noleggiatore': self.noleggiatore,
            'data': self.data_elaborazione.isoformat() if self.data_elaborazione else None,
            'file_origine': self.file_origine,
            'veicoli_importati': self.veicoli_importati,
            'veicoli_matched': self.veicoli_matched,
            'veicoli_partial': self.veicoli_partial,
            'veicoli_no_match': self.veicoli_no_match,
            'match_rate': self.match_rate,
            'durata_secondi': self.durata_secondi,
            'stato': self.stato,
            'errore': self.errore,
            'file_excel': self.file_excel_output,
        }
    
    @classmethod
    def ultima_elaborazione(cls, noleggiatore: str):
        """
        Recupera ultima elaborazione per un noleggiatore
        
        Args:
            noleggiatore: Nome noleggiatore
            
        Returns:
            Elaborazione o None
        """
        return cls.query.filter_by(
            noleggiatore=noleggiatore.upper(),
            stato='completata'
        ).order_by(cls.data_elaborazione.desc()).first()
    
    @classmethod
    def ultime_elaborazioni(cls, limit: int = 10):
        """
        Recupera ultime elaborazioni
        
        Args:
            limit: Numero massimo risultati
            
        Returns:
            list: Lista elaborazioni
        """
        return cls.query.order_by(
            cls.data_elaborazione.desc()
        ).limit(limit).all()
    
    def __repr__(self):
        return f'<Elaborazione {self.noleggiatore} {self.data_elaborazione}>'
