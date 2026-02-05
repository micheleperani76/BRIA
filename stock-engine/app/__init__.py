# =============================================================================
# STOCK ENGINE - Flask Application Factory
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
# =============================================================================

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

from .config import get_config

# Estensioni Flask (inizializzate senza app)
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=None):
    """
    Application Factory Pattern
    
    Args:
        config_class: Classe configurazione (opzionale)
        
    Returns:
        Flask app configurata
    """
    app = Flask(__name__)
    
    # Carica configurazione
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Inizializza estensioni
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    
    # Crea directory necessarie
    _ensure_directories(app)
    
    # Configura SQLite ottimizzazioni
    _configure_sqlite(app)
    
    # Registra blueprints
    _register_blueprints(app)
    
    # Comandi CLI
    _register_commands(app)
    
    return app


def _ensure_directories(app):
    """Crea directory necessarie se non esistono"""
    from pathlib import Path
    
    dirs = [
        app.config.get('DIR_OUTPUT'),
        Path(app.instance_path),
    ]
    
    for d in dirs:
        if d:
            Path(d).mkdir(parents=True, exist_ok=True)


def _configure_sqlite(app):
    """Configura ottimizzazioni SQLite"""
    
    @app.before_request
    def configure_sqlite_connection():
        """Esegue PRAGMA per ogni connessione"""
        if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
            from sqlalchemy import event
            from sqlalchemy.engine import Engine
            
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                # WAL mode per concorrenza
                cursor.execute("PRAGMA journal_mode=WAL")
                # Cache più grande per performance
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB
                # Sync normale (buon compromesso sicurezza/velocità)
                cursor.execute("PRAGMA synchronous=NORMAL")
                # Foreign keys
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()


def _register_blueprints(app):
    """Registra tutti i blueprints"""
    
    # API REST
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Web interface (opzionale)
    from .web import web_bp
    app.register_blueprint(web_bp)


def _register_commands(app):
    """Registra comandi CLI personalizzati"""
    
    @app.cli.command('init-db')
    def init_db():
        """Inizializza database con tabelle e dati base"""
        from .models import init_database
        init_database(app)
        print("✔ Database inizializzato")
    
    @app.cli.command('import-jato')
    def import_jato():
        """Importa database JATO da file SQLite esistente"""
        from .services.jato_migrator import migrate_jato_db
        migrate_jato_db(app)
        print("✔ Database JATO importato")
    
    @app.cli.command('import-config')
    def import_config():
        """Importa glossario e pattern da file Excel"""
        from .services.config_migrator import migrate_config_files
        migrate_config_files(app)
        print("✔ Configurazioni importate")
    
    @app.cli.command('elabora')
    @app.cli.argument('noleggiatore')
    def elabora(noleggiatore):
        """Esegue elaborazione per un noleggiatore"""
        from .services.pipeline import StockPipeline
        
        pipeline = StockPipeline()
        result = pipeline.elabora(noleggiatore.upper())
        
        print(f"\n{'='*60}")
        print(f"ELABORAZIONE {noleggiatore.upper()} COMPLETATA")
        print(f"{'='*60}")
        print(f"Veicoli importati: {result['veicoli_importati']}")
        print(f"Veicoli matched:   {result['veicoli_matched']}")
        print(f"Match rate:        {result['match_rate']:.1f}%")
        print(f"Durata:            {result['durata_secondi']} secondi")
        print(f"File Excel:        {result['file_excel']}")
        print(f"{'='*60}\n")
    
    @app.cli.command('cleanup')
    def cleanup():
        """Pulisce dati più vecchi di STORICO_GIORNI"""
        from .services.maintenance import cleanup_old_data
        deleted = cleanup_old_data(app.config['STORICO_GIORNI'])
        print(f"✔ Eliminati {deleted} record vecchi")
