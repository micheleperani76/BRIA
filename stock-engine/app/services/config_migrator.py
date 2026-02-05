# =============================================================================
# STOCK ENGINE - Config Migrator
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Servizio per migrazione configurazioni esistenti (glossario, pattern)
# dai file Excel nel database.
# =============================================================================

from pathlib import Path

import pandas as pd
from flask import current_app

from app import db
from app.models.glossario import Glossario
from app.models.pattern import PatternCarburante


def migrate_config_files(app=None):
    """
    Migra tutti i file di configurazione
    
    Args:
        app: Flask application (opzionale)
    """
    if app is None:
        app = current_app
    
    with app.app_context():
        config_dir = Path(app.config.get('DIR_IMPOSTAZIONI', '/home/michele/stock/impostazioni'))
        
        print(f"\n{'='*60}")
        print("MIGRAZIONE CONFIGURAZIONI")
        print(f"{'='*60}")
        print(f"Directory: {config_dir}")
        
        # Migra glossario
        glossario_path = config_dir / 'glossario_jato.xlsx'
        if glossario_path.exists():
            migrate_glossario(glossario_path)
        else:
            print(f"  ⚠ File glossario non trovato: {glossario_path}")
        
        # Migra pattern carburante
        pattern_path = config_dir / 'pattern_carburante.xlsx'
        if pattern_path.exists():
            migrate_pattern_carburante(pattern_path)
        else:
            print(f"  ⚠ File pattern non trovato: {pattern_path}")
        
        print(f"{'='*60}\n")


def migrate_glossario(xlsx_path: Path):
    """
    Migra glossario da file Excel
    
    Struttura attesa Excel:
    - Colonna: cerca | sostituisci | colonna | noleggiatore | note
    
    Args:
        xlsx_path: Path file Excel glossario
    """
    print(f"\nMigrazione glossario: {xlsx_path.name}")
    
    try:
        df = pd.read_excel(xlsx_path, sheet_name='Glossario')
    except Exception as e:
        # Prova senza specificare foglio
        df = pd.read_excel(xlsx_path)
    
    # Normalizza nomi colonne
    df.columns = [c.lower().strip() for c in df.columns]
    
    added = 0
    
    for _, row in df.iterrows():
        cerca = row.get('cerca') or row.get('search') or row.get('find')
        sostituisci = row.get('sostituisci') or row.get('replace') or row.get('substitute')
        
        if not cerca or not sostituisci:
            continue
        
        # Skip se pandas NaN
        if pd.isna(cerca) or pd.isna(sostituisci):
            continue
        
        # Verifica se esiste già
        existing = Glossario.query.filter_by(
            cerca=str(cerca).strip(),
            sostituisci=str(sostituisci).strip()
        ).first()
        
        if existing:
            continue
        
        glossario = Glossario(
            cerca=str(cerca).strip(),
            sostituisci=str(sostituisci).strip(),
            colonna=row.get('colonna') if not pd.isna(row.get('colonna', None)) else None,
            noleggiatore=row.get('noleggiatore') if not pd.isna(row.get('noleggiatore', None)) else None,
            note=row.get('note') if not pd.isna(row.get('note', None)) else None,
            attivo=True
        )
        
        db.session.add(glossario)
        added += 1
    
    db.session.commit()
    
    print(f"  ✔ Aggiunte {added} regole glossario")
    print(f"  Totale regole: {Glossario.query.count()}")


def migrate_pattern_carburante(xlsx_path: Path):
    """
    Migra pattern carburante da file Excel
    
    Struttura attesa Excel:
    - Colonna: pattern | fuel_type | priorita | note
    
    Args:
        xlsx_path: Path file Excel pattern
    """
    print(f"\nMigrazione pattern carburante: {xlsx_path.name}")
    
    try:
        df = pd.read_excel(xlsx_path, sheet_name='Pattern Carburante')
    except Exception as e:
        # Prova senza specificare foglio
        df = pd.read_excel(xlsx_path)
    
    # Normalizza nomi colonne
    df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
    
    added = 0
    
    for _, row in df.iterrows():
        pattern = row.get('pattern')
        fuel_type = row.get('fuel_type') or row.get('tipo') or row.get('alimentazione')
        
        if not pattern or not fuel_type:
            continue
        
        if pd.isna(pattern) or pd.isna(fuel_type):
            continue
        
        # Verifica se esiste già
        existing = PatternCarburante.query.filter_by(
            pattern=str(pattern).strip().upper()
        ).first()
        
        if existing:
            continue
        
        priorita = row.get('priorita', 10)
        if pd.isna(priorita):
            priorita = 10
        
        pc = PatternCarburante(
            pattern=str(pattern).strip().upper(),
            fuel_type=str(fuel_type).strip().upper(),
            priorita=int(priorita),
            note=row.get('note') if not pd.isna(row.get('note', None)) else None,
            attivo=True
        )
        
        db.session.add(pc)
        added += 1
    
    db.session.commit()
    
    print(f"  ✔ Aggiunti {added} pattern carburante")
    print(f"  Totale pattern: {PatternCarburante.query.count()}")


def export_glossario_to_excel(output_path: Path):
    """
    Esporta glossario corrente in Excel
    
    Args:
        output_path: Path file output
    """
    regole = Glossario.query.all()
    
    data = [{
        'cerca': r.cerca,
        'sostituisci': r.sostituisci,
        'colonna': r.colonna,
        'noleggiatore': r.noleggiatore,
        'attivo': r.attivo,
        'note': r.note,
    } for r in regole]
    
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False, sheet_name='Glossario')
    
    print(f"Glossario esportato: {output_path}")


def export_pattern_to_excel(output_path: Path):
    """
    Esporta pattern correnti in Excel
    
    Args:
        output_path: Path file output
    """
    patterns = PatternCarburante.query.order_by(PatternCarburante.priorita.desc()).all()
    
    data = [{
        'pattern': p.pattern,
        'fuel_type': p.fuel_type,
        'priorita': p.priorita,
        'attivo': p.attivo,
        'note': p.note,
    } for p in patterns]
    
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False, sheet_name='Pattern Carburante')
    
    print(f"Pattern esportati: {output_path}")
