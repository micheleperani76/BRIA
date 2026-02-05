#!/usr/bin/env python3
# =============================================================================
# STOCK ENGINE - Scheduler
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Scheduler per elaborazione automatica mattutina.
# Esegue l'elaborazione di tutti i noleggiatori all'ora configurata.
# =============================================================================

import os
import sys
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Aggiungi parent directory al path per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.services.pipeline import StockPipeline

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('stock_scheduler')


def elaborazione_mattutina():
    """
    Job elaborazione mattutina
    
    Esegue l'elaborazione per tutti i noleggiatori attivi.
    """
    logger.info("=" * 60)
    logger.info("INIZIO ELABORAZIONE MATTUTINA")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        noleggiatori = app.config.get('NOLEGGIATORI_ATTIVI', ['AYVENS', 'ARVAL', 'LEASYS'])
        
        risultati = {}
        
        for noleggiatore in noleggiatori:
            logger.info(f"\nElaborazione {noleggiatore}...")
            
            try:
                pipeline = StockPipeline()
                result = pipeline.elabora(noleggiatore)
                risultati[noleggiatore] = result
                
                logger.info(f"  ✔ {noleggiatore}: {result['veicoli_importati']} veicoli, "
                           f"match rate {result['match_rate']}%")
                
            except Exception as e:
                logger.error(f"  ✗ {noleggiatore}: ERRORE - {str(e)}")
                risultati[noleggiatore] = {'stato': 'errore', 'errore': str(e)}
        
        # Riepilogo
        logger.info("\n" + "=" * 60)
        logger.info("RIEPILOGO ELABORAZIONE")
        logger.info("=" * 60)
        
        for noleggiatore, result in risultati.items():
            if result.get('stato') == 'errore':
                logger.info(f"  {noleggiatore}: ✗ ERRORE")
            else:
                logger.info(f"  {noleggiatore}: ✔ {result.get('veicoli_importati', 0)} veicoli")
        
        logger.info("=" * 60)
        logger.info("FINE ELABORAZIONE MATTUTINA")
        logger.info("=" * 60 + "\n")


def main():
    """Main function - avvia scheduler"""
    
    # Leggi configurazione ora
    ora_config = os.environ.get('SCHEDULER_ORA', '07:00')
    
    try:
        hour, minute = map(int, ora_config.split(':'))
    except ValueError:
        logger.error(f"Formato ora non valido: {ora_config}. Uso default 07:00")
        hour, minute = 7, 0
    
    logger.info("\n" + "=" * 60)
    logger.info("  STOCK ENGINE SCHEDULER")
    logger.info("=" * 60)
    logger.info(f"  Elaborazione programmata: {hour:02d}:{minute:02d}")
    logger.info(f"  Avviato: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60 + "\n")
    
    # Crea scheduler
    scheduler = BlockingScheduler()
    
    # Aggiungi job elaborazione mattutina
    scheduler.add_job(
        elaborazione_mattutina,
        CronTrigger(hour=hour, minute=minute),
        id='elaborazione_mattutina',
        name='Elaborazione Stock Mattutina',
        replace_existing=True
    )
    
    # Aggiungi job pulizia settimanale (domenica alle 03:00)
    scheduler.add_job(
        pulizia_settimanale,
        CronTrigger(day_of_week='sun', hour=3, minute=0),
        id='pulizia_settimanale',
        name='Pulizia Dati Vecchi',
        replace_existing=True
    )
    
    logger.info("Scheduler avviato. In attesa del prossimo job...")
    logger.info("Premi Ctrl+C per fermare.\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\nScheduler fermato.")


def pulizia_settimanale():
    """
    Job pulizia settimanale
    
    Rimuove dati più vecchi di STORICO_GIORNI.
    """
    logger.info("Avvio pulizia settimanale...")
    
    app = create_app()
    
    with app.app_context():
        from datetime import date, timedelta
        from app.models.veicolo import Veicolo
        
        giorni_storico = app.config.get('STORICO_GIORNI', 365)
        data_limite = date.today() - timedelta(days=giorni_storico)
        
        # Conta record da eliminare
        count = Veicolo.query.filter(Veicolo.data_import < data_limite).count()
        
        if count > 0:
            Veicolo.query.filter(Veicolo.data_import < data_limite).delete()
            db.session.commit()
            logger.info(f"  ✔ Eliminati {count} record più vecchi di {giorni_storico} giorni")
        else:
            logger.info("  ✔ Nessun record da eliminare")


if __name__ == '__main__':
    main()
