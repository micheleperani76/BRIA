# =============================================================================
# STOCK ENGINE - Importers
# =============================================================================

from .base_importer import BaseImporter
from .ayvens_importer import AyvensImporter
from .arval_importer import ArvalImporter

__all__ = [
    'BaseImporter',
    'AyvensImporter',
    'ArvalImporter',
]


def get_importer(noleggiatore: str):
    """
    Factory per ottenere l'importer corretto
    
    Args:
        noleggiatore: Nome noleggiatore
        
    Returns:
        Importer specifico
    """
    importers = {
        'AYVENS': AyvensImporter,
        'ARVAL': ArvalImporter,
        # 'LEASYS': LeasysImporter,  # TODO
    }
    
    noleggiatore = noleggiatore.upper()
    
    if noleggiatore not in importers:
        raise ValueError(f"Noleggiatore non supportato: {noleggiatore}")
    
    return importers[noleggiatore]()
