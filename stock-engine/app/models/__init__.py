# =============================================================================
# STOCK ENGINE - Modelli Database
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
# =============================================================================

from .veicolo import Veicolo
from .jato import JatoModel
from .glossario import Glossario
from .pattern import PatternCarburante
from .elaborazione import Elaborazione

__all__ = [
    'Veicolo',
    'JatoModel', 
    'Glossario',
    'PatternCarburante',
    'Elaborazione'
]


def init_database(app):
    """
    Inizializza database con tabelle e indici
    
    Args:
        app: Flask application
    """
    from app import db
    
    with app.app_context():
        # Crea tutte le tabelle
        db.create_all()
        
        # Ottimizzazioni SQLite aggiuntive
        if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
            db.session.execute(db.text("PRAGMA journal_mode=WAL"))
            db.session.execute(db.text("PRAGMA synchronous=NORMAL"))
            db.session.commit()
        
        print("  ✔ Tabelle create")
        print("  ✔ Indici creati")
        print("  ✔ Ottimizzazioni SQLite applicate")
