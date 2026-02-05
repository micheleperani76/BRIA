# =============================================================================
# STOCK ENGINE - Web Blueprint
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
# =============================================================================

from flask import Blueprint, render_template
from datetime import date

from app.models.veicolo import Veicolo
from app.models.elaborazione import Elaborazione

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def dashboard():
    """Dashboard principale"""
    
    # Statistiche
    stats = {
        'veicoli_totali': Veicolo.query.count(),
        'veicoli_oggi': Veicolo.query.filter_by(data_import=date.today()).count(),
    }
    
    # Ultime elaborazioni
    ultime_elaborazioni = Elaborazione.ultime_elaborazioni(5)
    
    # Statistiche per noleggiatore (oggi)
    noleggiatori = ['AYVENS', 'ARVAL', 'LEASYS']
    stats_noleggiatori = {}
    
    for n in noleggiatori:
        stats_noleggiatori[n] = Veicolo.get_statistics(n, date.today())
    
    return render_template(
        'dashboard.html',
        stats=stats,
        elaborazioni=ultime_elaborazioni,
        stats_noleggiatori=stats_noleggiatori,
        oggi=date.today()
    )
