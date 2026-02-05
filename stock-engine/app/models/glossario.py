# =============================================================================
# STOCK ENGINE - Modello Glossario
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Tabella che contiene le regole di normalizzazione (glossario)
# per uniformare i termini dei noleggiatori prima del match JATO.
# =============================================================================

from app import db


class Glossario(db.Model):
    """
    Regole glossario per normalizzazione termini
    
    Esempio:
    - cerca: "ALFA"
    - sostituisci: "ALFA ROMEO"
    - colonna: "marca"
    - noleggiatore: None (tutti) o "AYVENS"
    """
    
    __tablename__ = 'glossario'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Noleggiatore (NULL = tutti)
    noleggiatore = db.Column(db.String(20), index=True)
    
    # Regola
    cerca = db.Column(db.String(100), nullable=False)
    sostituisci = db.Column(db.String(100), nullable=False)
    
    # Colonna target (marca, modello, description)
    colonna = db.Column(db.String(50))
    
    # Stato
    attivo = db.Column(db.Boolean, default=True)
    
    # Note
    note = db.Column(db.Text)
    
    # Metadata
    creato_il = db.Column(db.DateTime, default=db.func.now())
    
    # ==========================================================================
    # METODI
    # ==========================================================================
    
    @classmethod
    def get_regole(cls, noleggiatore: str = None, colonna: str = None):
        """
        Recupera regole glossario attive
        
        Args:
            noleggiatore: Filtro noleggiatore (opzionale)
            colonna: Filtro colonna (opzionale)
            
        Returns:
            list: Lista regole
        """
        query = cls.query.filter_by(attivo=True)
        
        if noleggiatore:
            # Regole specifiche per noleggiatore + regole globali
            query = query.filter(
                db.or_(
                    cls.noleggiatore == noleggiatore.upper(),
                    cls.noleggiatore.is_(None)
                )
            )
        
        if colonna:
            query = query.filter_by(colonna=colonna)
        
        return query.all()
    
    @classmethod
    def applica_glossario(cls, testo: str, noleggiatore: str = None, colonna: str = None) -> str:
        """
        Applica regole glossario a un testo
        
        IMPORTANTE: Match su parola intera per evitare sostituzioni parziali
        
        Args:
            testo: Testo da normalizzare
            noleggiatore: Noleggiatore di riferimento
            colonna: Colonna di riferimento
            
        Returns:
            str: Testo normalizzato
        """
        import re
        
        if not testo:
            return testo
        
        regole = cls.get_regole(noleggiatore, colonna)
        risultato = testo
        
        for regola in regole:
            # Pattern per match parola intera (word boundary)
            pattern = r'\b' + re.escape(regola.cerca) + r'\b'
            risultato = re.sub(pattern, regola.sostituisci, risultato, flags=re.IGNORECASE)
        
        return risultato
    
    def to_dict(self):
        """Converte in dizionario"""
        return {
            'id': self.id,
            'noleggiatore': self.noleggiatore,
            'cerca': self.cerca,
            'sostituisci': self.sostituisci,
            'colonna': self.colonna,
            'attivo': self.attivo,
            'note': self.note,
        }
    
    def __repr__(self):
        return f'<Glossario {self.cerca} → {self.sostituisci}>'
