# =============================================================================
# STOCK ENGINE - Configurazione
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
# =============================================================================

import os
from pathlib import Path
from datetime import timedelta

# Directory base del progetto
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Configurazione base"""
    
    # ==========================================================================
    # FLASK
    # ==========================================================================
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'stock-engine-secret-key-change-in-production'
    
    # ==========================================================================
    # DATABASE
    # ==========================================================================
    # SQLite (semplice, nessuna installazione richiesta)
    # Per PostgreSQL: postgresql://user:pass@localhost:5432/stock_engine
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{BASE_DIR / "instance" / "stock_engine.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }
    
    # ==========================================================================
    # PERCORSI FILE
    # ==========================================================================
    # Directory input (dove MEGA sincronizza i file)
    DIR_INPUT = Path(os.environ.get('DIR_INPUT') or '/home/michele/stock/elaborazione')
    
    # Directory output Excel
    DIR_OUTPUT = Path(os.environ.get('DIR_OUTPUT') or BASE_DIR / 'output' / 'stock')
    
    # Directory file JATO
    DIR_JATO = Path(os.environ.get('DIR_JATO') or '/home/michele/stock/mappati')
    
    # Directory impostazioni (glossario, pattern)
    DIR_IMPOSTAZIONI = Path(os.environ.get('DIR_IMPOSTAZIONI') or '/home/michele/stock/impostazioni')
    
    # ==========================================================================
    # ELABORAZIONE
    # ==========================================================================
    # Storico da mantenere (giorni)
    STORICO_GIORNI = 365
    
    # Soglia minima match score
    MIN_MATCH_SCORE = 25
    
    # Tolleranze matching
    KW_TOLERANCE = 3
    HP_TOLERANCE = 5
    CO2_TOLERANCE = 5
    
    # ==========================================================================
    # SCHEDULER
    # ==========================================================================
    # Ora elaborazione mattutina (formato HH:MM)
    SCHEDULER_ELABORAZIONE_ORA = os.environ.get('SCHEDULER_ORA') or '07:00'
    
    # Noleggiatori attivi
    NOLEGGIATORI_ATTIVI = ['AYVENS', 'ARVAL', 'LEASYS']
    
    # ==========================================================================
    # API
    # ==========================================================================
    # Limite risultati per pagina
    API_PAGE_SIZE = 100
    API_MAX_PAGE_SIZE = 1000
    
    # CORS - domini abilitati per il tuo programma principale
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')


class DevelopmentConfig(Config):
    """Configurazione sviluppo"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # True per vedere query SQL


class ProductionConfig(Config):
    """Configurazione produzione"""
    DEBUG = False
    
    # In produzione, SECRET_KEY deve essere impostata via env
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key:
            raise ValueError("SECRET_KEY deve essere impostata in produzione")
        return key


class TestingConfig(Config):
    """Configurazione test"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Mappa configurazioni
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Restituisce configurazione in base a FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
