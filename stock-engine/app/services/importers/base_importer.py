# =============================================================================
# STOCK ENGINE - Base Importer
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Classe base astratta per gli importers dei vari noleggiatori.
# Contiene logica comune: ricerca file, validazione, conversione.
# =============================================================================

import os
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import date
from typing import List, Dict, Optional, Tuple
import pandas as pd

from flask import current_app


class BaseImporter(ABC):
    """
    Classe base astratta per importazione dati noleggiatori
    
    Ogni noleggiatore ha un importer specifico che estende questa classe
    e implementa i metodi astratti per la mappatura colonne.
    """
    
    # Nome noleggiatore (da sovrascrivere nelle sottoclassi)
    NOLEGGIATORE: str = None
    
    # Pattern file da cercare (es. "stockReport*.csv")
    FILE_PATTERNS: List[str] = []
    
    # Estensioni accettate in ordine di priorità
    EXTENSIONS_PRIORITY: List[str] = ['.csv', '.xlsx']
    
    # Separatore CSV (default punto e virgola italiano)
    CSV_SEPARATOR: str = ';'
    
    # Decimale CSV (default virgola italiana)
    CSV_DECIMAL: str = ','
    
    # Encoding da provare
    ENCODINGS: List[str] = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    def __init__(self):
        """Inizializza importer"""
        self.errors = []
        self.warnings = []
    
    # ==========================================================================
    # METODI ASTRATTI (da implementare nelle sottoclassi)
    # ==========================================================================
    
    @abstractmethod
    def get_column_mapping(self) -> Dict[str, str]:
        """
        Restituisce mapping colonne file → campi database
        
        Returns:
            dict: {colonna_file: campo_db}
            
        Esempio:
            {
                'MAKENAME': 'marca_originale',
                'MODELNAME': 'modello_originale',
                'DESCRIPTION': 'description_originale',
                ...
            }
        """
        pass
    
    @abstractmethod
    def get_required_columns(self) -> List[str]:
        """
        Restituisce lista colonne obbligatorie
        
        Returns:
            list: Nomi colonne che devono essere presenti
        """
        pass
    
    @abstractmethod
    def post_process_row(self, row: Dict) -> Dict:
        """
        Post-processing riga dopo mappatura
        
        Args:
            row: Dizionario con dati riga
            
        Returns:
            dict: Riga processata
        """
        pass
    
    # ==========================================================================
    # METODI COMUNI
    # ==========================================================================
    
    def trova_file_recente(self, directory: Path = None) -> Optional[Path]:
        """
        Trova il file più recente da importare
        
        Args:
            directory: Directory dove cercare (default da config)
            
        Returns:
            Path: Percorso file trovato o None
        """
        if directory is None:
            directory = Path(current_app.config['DIR_INPUT'])
        
        if not directory.exists():
            self.errors.append(f"Directory non trovata: {directory}")
            return None
        
        # Cerca file per ogni pattern
        files_found = []
        
        for pattern in self.FILE_PATTERNS:
            for ext in self.EXTENSIONS_PRIORITY:
                # Costruisci pattern completo
                search_pattern = pattern.replace('*', '**/*')
                if not search_pattern.endswith(ext):
                    search_pattern = search_pattern.rstrip('*') + f'*{ext}'
                
                for file_path in directory.glob(search_pattern):
                    if file_path.is_file():
                        stat = file_path.stat()
                        files_found.append({
                            'path': file_path,
                            'ext': ext,
                            'mtime': stat.st_mtime,
                            'size': stat.st_size
                        })
        
        if not files_found:
            self.errors.append(f"Nessun file trovato per pattern: {self.FILE_PATTERNS}")
            return None
        
        # Ordina per priorità estensione e poi per data modifica
        ext_priority = {ext: i for i, ext in enumerate(self.EXTENSIONS_PRIORITY)}
        files_found.sort(key=lambda x: (ext_priority.get(x['ext'], 99), -x['mtime']))
        
        return files_found[0]['path']
    
    def leggi_file(self, file_path: Path) -> pd.DataFrame:
        """
        Legge file CSV o XLSX in DataFrame
        
        Args:
            file_path: Percorso file
            
        Returns:
            DataFrame: Dati letti
            
        Raises:
            ValueError: Se file non leggibile
        """
        ext = file_path.suffix.lower()
        
        if ext == '.csv':
            return self._leggi_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            return self._leggi_excel(file_path)
        else:
            raise ValueError(f"Estensione non supportata: {ext}")
    
    def _leggi_csv(self, file_path: Path) -> pd.DataFrame:
        """
        Legge file CSV con gestione encoding e decimali
        
        NOTA IMPORTANTE: Gestisce formato italiano (decimale = virgola)
        per evitare shift colonne.
        """
        df = None
        encoding_usato = None
        
        for enc in self.ENCODINGS:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=enc,
                    sep=self.CSV_SEPARATOR,
                    decimal=self.CSV_DECIMAL,
                    on_bad_lines='skip',
                    low_memory=False
                )
                encoding_usato = enc
                break
            except Exception:
                continue
        
        if df is None:
            raise ValueError(f"Impossibile leggere CSV con encoding: {self.ENCODINGS}")
        
        # Valida struttura
        self._valida_struttura(df)
        
        return df
    
    def _leggi_excel(self, file_path: Path) -> pd.DataFrame:
        """Legge file Excel"""
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            self._valida_struttura(df)
            return df
        except Exception as e:
            raise ValueError(f"Errore lettura Excel: {e}")
    
    def _valida_struttura(self, df: pd.DataFrame):
        """
        Valida struttura DataFrame
        
        Args:
            df: DataFrame da validare
            
        Raises:
            ValueError: Se struttura non valida
        """
        # Verifica colonne obbligatorie
        required = self.get_required_columns()
        missing = []
        
        df_columns_upper = [c.upper() for c in df.columns]
        
        for col in required:
            if col.upper() not in df_columns_upper:
                missing.append(col)
        
        if missing:
            raise ValueError(f"Colonne mancanti: {missing}")
        
        # Verifica almeno 1 riga dati
        if len(df) == 0:
            raise ValueError("File vuoto (0 righe)")
    
    def importa(self, file_path: Path = None) -> List[Dict]:
        """
        Importa dati da file
        
        Args:
            file_path: Percorso file (opzionale, cerca automaticamente)
            
        Returns:
            list: Lista dizionari con dati veicoli
        """
        # Trova file se non specificato
        if file_path is None:
            file_path = self.trova_file_recente()
            if file_path is None:
                raise ValueError("Nessun file trovato da importare")
        
        # Leggi file
        df = self.leggi_file(file_path)
        
        # Mappa colonne
        mapping = self.get_column_mapping()
        
        # Converti in lista dizionari
        veicoli = []
        
        for idx, row in df.iterrows():
            veicolo = {
                'noleggiatore': self.NOLEGGIATORE,
                'data_import': date.today(),
                'riga_excel': idx + 2,  # +2 perché Excel parte da 1 e ha header
            }
            
            # Applica mapping
            for col_file, campo_db in mapping.items():
                # Trova colonna (case insensitive)
                col_found = None
                for c in df.columns:
                    if c.upper() == col_file.upper():
                        col_found = c
                        break
                
                if col_found:
                    value = row[col_found]
                    # Gestisci NaN
                    if pd.isna(value):
                        value = None
                    elif isinstance(value, str):
                        value = value.strip()
                    veicolo[campo_db] = value
            
            # Post-processing specifico noleggiatore
            veicolo = self.post_process_row(veicolo)
            
            veicoli.append(veicolo)
        
        return veicoli
    
    def get_file_info(self, file_path: Path) -> Dict:
        """
        Ottiene informazioni sul file
        
        Args:
            file_path: Percorso file
            
        Returns:
            dict: Informazioni file
        """
        stat = file_path.stat()
        return {
            'nome': file_path.name,
            'path': str(file_path),
            'size': stat.st_size,
            'modified': stat.st_mtime,
        }
