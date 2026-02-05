#!/usr/bin/env python3
# =============================================================================
# STOCK ENGINE - Entry Point
# =============================================================================
# Versione: 1.0.0
# Data: 28 gennaio 2026
#
# Uso sviluppo:   python run.py
# Uso produzione: gunicorn -w 2 -b 0.0.0.0:5000 'app:create_app()'
# =============================================================================

import os
from app import create_app

# Crea applicazione
app = create_app()

if __name__ == '__main__':
    # Modalità sviluppo
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print("\n" + "=" * 60)
    print("  STOCK ENGINE v1.0.0")
    print("  Sistema Elaborazione Stock Veicoli")
    print("=" * 60)
    print(f"\n  Modalità: {'SVILUPPO' if debug else 'PRODUZIONE'}")
    print(f"  Server:   http://localhost:5000")
    print(f"  API:      http://localhost:5000/api")
    print("\n" + "=" * 60 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug
    )
