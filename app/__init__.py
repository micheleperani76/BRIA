#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Package App
# ==============================================================================
# Versione: 1.0.0
# Data: 2025-01-12
# ==============================================================================

from .config import *
from .database import init_database, get_connection
from .utils import setup_logger
from .import_creditsafe import importa_tutti_pdf

__version__ = '1.0.0'
__author__ = 'Gestione Flotta'
