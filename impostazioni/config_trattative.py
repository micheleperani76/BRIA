# -*- coding: utf-8 -*-
"""
==============================================================================
CONFIGURAZIONE TRATTATIVE
==============================================================================
Versione: 1.0
Data: 2026-01-28
Descrizione: Parametri configurabili per il modulo Trattative
==============================================================================
"""

# ==============================================================================
# RETENTION (CONSERVAZIONE DATI)
# ==============================================================================

# Anni di conservazione delle trattative chiuse
# Le trattative piu' vecchie potranno essere eliminate da admin
RETENTION_ANNI = 10

# ==============================================================================
# STATI
# ==============================================================================

# Stati che indicano chiusura trattativa
STATI_CHIUSURA = ['Approvato', 'Approvato con riserve', 'Bocciato', 'Perso']

# Stato default per nuove trattative
STATO_DEFAULT = 'Preso in carico'

# ==============================================================================
# PERMESSI
# ==============================================================================

# Ruoli che possono eliminare trattative storiche (oltre retention)
RUOLI_ELIMINA_STORICHE = ['ADMIN']

# Ruoli che possono vedere tutte le trattative (non solo proprie)
RUOLI_VEDE_TUTTE = ['ADMIN', 'OPERATORE']
