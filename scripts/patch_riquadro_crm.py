#!/usr/bin/env python3
# ==============================================================================
# PATCH - Riquadro Dati CRM nella Scheda Cliente
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-02-09
# Descrizione: Aggiunge il riquadro dati CRM Zoho nella scheda cliente
#
# Operazioni:
#   1. Aggiunge query satellite in web_server.py (_render_dettaglio_cliente)
#   2. Aggiunge include in dettaglio.html (colonna destra, prima del rating)
#
# PREREQUISITO: il file templates/componenti/crm/_riquadro.html deve esistere
#
# Uso: python3 scripts/patch_riquadro_crm.py [--dry-run]
# ==============================================================================

import sys
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
WEB_SERVER = BASE_DIR / 'app' / 'web_server.py'
DETTAGLIO = BASE_DIR / 'templates' / 'dettaglio.html'
TEMPLATE_CRM = BASE_DIR / 'templates' / 'componenti' / 'crm' / '_riquadro.html'

dry_run = '--dry-run' in sys.argv

def log(msg):
    print(f"  {msg}")


def patch_web_server():
    """Aggiunge query satellite e parametri template in _render_dettaglio_cliente."""
    contenuto = WEB_SERVER.read_text(encoding='utf-8')
    
    if 'consensi_crm' in contenuto:
        log("SKIP - web_server.py gia' patchato")
        return False
    
    # === PATCH 1: Aggiungere query satellite ===
    # Cerco il punto dopo top_prospect_info (prima di conn.close)
    marcatore = 'top_prospect_info = {"presente": bool(tp_row)'
    if marcatore not in contenuto:
        log("ERRORE - Marcatore top_prospect_info non trovato!")
        return False
    
    # Trovo la riga completa e aggiungo dopo
    righe = contenuto.split('\n')
    idx_marcatore = None
    for i, riga in enumerate(righe):
        if marcatore in riga:
            idx_marcatore = i
            break
    
    if idx_marcatore is None:
        log("ERRORE - Riga marcatore non trovata!")
        return False
    
    # Inserisco le query dopo la riga del marcatore
    query_satellite = [
        '',
        '    # Query dati satellite CRM',
        '    cursor.execute("SELECT tipo_consenso, valore, data_consenso FROM clienti_consensi WHERE cliente_id = ? AND origine = \'CRM\' ORDER BY tipo_consenso", (cliente_id,))',
        '    consensi_crm = [dict(row) for row in cursor.fetchall()]',
        '    cursor.execute("SELECT tipo_alert, valore, data_rilevazione FROM clienti_creditsafe_alert WHERE cliente_id = ? AND fonte = \'CRM\' ORDER BY tipo_alert", (cliente_id,))',
        '    alert_crm = [dict(row) for row in cursor.fetchall()]',
    ]
    
    for j, ql in enumerate(query_satellite):
        righe.insert(idx_marcatore + 1 + j, ql)
    
    contenuto = '\n'.join(righe)
    
    # === PATCH 2: Aggiungere parametri al render_template ===
    vecchio = 'top_prospect_info=top_prospect_info)'
    nuovo = ('top_prospect_info=top_prospect_info,\n'
             '                         consensi_crm=consensi_crm,\n'
             '                         alert_crm=alert_crm)')
    
    if vecchio not in contenuto:
        log("ERRORE - Chiusura render_template non trovata!")
        return False
    
    contenuto = contenuto.replace(vecchio, nuovo)
    
    if not dry_run:
        WEB_SERVER.write_text(contenuto, encoding='utf-8')
    
    log("OK - web_server.py patchato (query + parametri)")
    return True


def patch_dettaglio():
    """Aggiunge include riquadro CRM in dettaglio.html."""
    contenuto = DETTAGLIO.read_text(encoding='utf-8')
    
    if 'componenti/crm/_riquadro.html' in contenuto:
        log("SKIP - dettaglio.html gia' patchato")
        return False
    
    # Cerco il punto di inserimento: prima di "<!-- Rating (compatto) -->"
    marcatore = '<!-- Rating (compatto) -->'
    if marcatore not in contenuto:
        log("ERRORE - Marcatore Rating non trovato!")
        return False
    
    include_line = '                {% include "componenti/crm/_riquadro.html" %}\n                '
    contenuto = contenuto.replace(marcatore, include_line + marcatore)
    
    if not dry_run:
        DETTAGLIO.write_text(contenuto, encoding='utf-8')
    
    log("OK - dettaglio.html patchato (include CRM)")
    return True


def main():
    print("="*60)
    print("PATCH - Riquadro Dati CRM Scheda Cliente")
    print("="*60)
    print(f"  Modalita': {'DRY-RUN' if dry_run else 'APPLICAZIONE'}")
    print()
    
    # Verifica prerequisiti
    print("[0/3] Verifiche...")
    
    if not WEB_SERVER.exists():
        log(f"ERRORE: {WEB_SERVER} non trovato"); sys.exit(1)
    if not DETTAGLIO.exists():
        log(f"ERRORE: {DETTAGLIO} non trovato"); sys.exit(1)
    if not TEMPLATE_CRM.exists():
        log(f"ERRORE: {TEMPLATE_CRM} non trovato")
        log("Copia prima il file _riquadro.html in templates/componenti/crm/")
        sys.exit(1)
    log("OK - Tutti i file presenti")
    
    # Backup
    if not dry_run:
        print()
        print("[1/3] Backup...")
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(WEB_SERVER, str(WEB_SERVER) + f'.bak_crm_{ts}')
        shutil.copy2(DETTAGLIO, str(DETTAGLIO) + f'.bak_crm_{ts}')
        log("OK - Backup creati")
    
    # Patch web_server.py
    print()
    print("[2/3] Patch web_server.py...")
    patch_web_server()
    
    # Patch dettaglio.html
    print()
    print("[3/3] Patch dettaglio.html...")
    patch_dettaglio()
    
    # Verifica sintassi Python
    print()
    print("Verifica sintassi...")
    try:
        import ast
        ast.parse(WEB_SERVER.read_text(encoding='utf-8'))
        log("OK - web_server.py sintassi valida")
    except SyntaxError as e:
        log(f"ERRORE SINTASSI: {e}")
        sys.exit(1)
    
    print()
    if dry_run:
        print("  Nessuna modifica applicata (dry-run)")
    else:
        print("  Patch completata!")
        print("  Riavvia: sudo systemctl restart gestione_flotta")


if __name__ == '__main__':
    main()
