# =============================================================================
# STOCK ENGINE - JATO Migrator
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Servizio per migrazione database JATO esistente (SQLite) nel nuovo sistema.
# =============================================================================

import sqlite3
from pathlib import Path
from datetime import datetime

from flask import current_app

from app import db
from app.models.jato import JatoModel


def migrate_jato_db(app=None):
    """
    Migra database JATO esistente nel nuovo sistema
    
    Args:
        app: Flask application (opzionale)
    """
    if app is None:
        app = current_app
    
    with app.app_context():
        # Path database JATO esistente
        jato_dir = Path(app.config.get('DIR_JATO', '/home/michele/stock/mappati'))
        jato_db_path = jato_dir / 'database_jato.db'
        
        if not jato_db_path.exists():
            raise FileNotFoundError(f"Database JATO non trovato: {jato_db_path}")
        
        print(f"\n{'='*60}")
        print("MIGRAZIONE DATABASE JATO")
        print(f"{'='*60}")
        print(f"Sorgente: {jato_db_path}")
        
        # Connessione al vecchio database
        conn = sqlite3.connect(str(jato_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Conta record
        cursor.execute("SELECT COUNT(*) FROM jato_models")
        total = cursor.fetchone()[0]
        print(f"Record da migrare: {total}")
        
        # Leggi tutti i record
        cursor.execute("SELECT * FROM jato_models")
        rows = cursor.fetchall()
        
        # Migra in batch
        batch_size = 1000
        migrated = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            
            for row in batch:
                # Crea record nel nuovo database
                jato = JatoModel(
                    product_id=row['product_id'],
                    jato_code=row['jato_code'],
                    brand_description=row['brand_description'],
                    jato_model=row['jato_model'],
                    jato_product_description=row['jato_product_description'],
                    vehicle_set_description=row['vehicle_set_description'],
                    alimentazione=row['alimentazione'],
                    kw=row['kw'],
                    horsepower=row['horsepower'],
                    homologation=row['homologation'],
                    transmission_description=row['transmission_description'],
                    powertrain_type=row['powertrain_type'],
                    co2_wltp=row.get('co2_wltp'),
                    source_sheet=row['source_sheet'],
                    # Campi normalizzati
                    brand_normalized=row['brand_description'].upper() if row['brand_description'] else None,
                    importato_il=datetime.utcnow()
                )
                
                # Usa merge per evitare duplicati
                db.session.merge(jato)
            
            db.session.commit()
            migrated += len(batch)
            
            # Progress
            progress = (migrated / total) * 100
            print(f"  Migrati: {migrated}/{total} ({progress:.1f}%)", end='\r')
        
        print(f"\n\n✔ Migrazione completata: {migrated} record")
        
        conn.close()
        
        # Statistiche
        stats = JatoModel.get_statistics()
        print(f"\nStatistiche database JATO:")
        print(f"  Modelli totali: {stats['totale_modelli']}")
        print(f"  Marche uniche: {stats['marche_uniche']}")
        print(f"{'='*60}\n")


def update_jato_from_file(xlsx_path: Path):
    """
    Aggiorna database JATO da file Excel
    
    Usare quando arriva un nuovo file JATO.
    
    Args:
        xlsx_path: Path file Excel JATO
    """
    import pandas as pd
    
    print(f"Aggiornamento JATO da: {xlsx_path}")
    
    # Leggi Excel
    df = pd.read_excel(xlsx_path)
    
    added = 0
    updated = 0
    
    for _, row in df.iterrows():
        product_id = row.get('Product ID') or row.get('product_id')
        
        if not product_id:
            continue
        
        existing = JatoModel.query.filter_by(product_id=product_id).first()
        
        if existing:
            # Aggiorna
            for col in df.columns:
                field = col.lower().replace(' ', '_')
                if hasattr(existing, field):
                    setattr(existing, field, row[col])
            updated += 1
        else:
            # Inserisci nuovo
            jato = JatoModel(
                product_id=product_id,
                jato_code=row.get('Jato Code') or row.get('jato_code'),
                brand_description=row.get('Brand Description') or row.get('brand_description'),
                jato_model=row.get('Jato Model') or row.get('jato_model'),
                jato_product_description=row.get('Jato Product Description') or row.get('jato_product_description'),
                vehicle_set_description=row.get('Vehicle Set Description') or row.get('vehicle_set_description'),
                alimentazione=row.get('Alimentazione') or row.get('alimentazione'),
                kw=row.get('KW') or row.get('kw'),
                horsepower=row.get('Horsepower') or row.get('horsepower'),
                homologation=row.get('Homologation') or row.get('homologation'),
                transmission_description=row.get('Transmission Description') or row.get('transmission_description'),
                importato_il=datetime.utcnow()
            )
            jato.brand_normalized = jato.brand_description.upper() if jato.brand_description else None
            db.session.add(jato)
            added += 1
    
    db.session.commit()
    
    print(f"  Aggiunti: {added}")
    print(f"  Aggiornati: {updated}")
