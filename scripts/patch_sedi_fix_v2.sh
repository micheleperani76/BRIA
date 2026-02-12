#!/bin/bash
# ==============================================================================
# PATCH v2: Fix Modal Sedi - Autocomplete + Referente Rapido
# Data: 2026-02-12
# Approccio: sed piccoli + file satellite separato
# ==============================================================================

set -e
SEDI_FILE=~/gestione_flotta/templates/dettaglio/sedi/_riquadro.html
ROUTE_FILE=~/gestione_flotta/app/routes_sedi_cliente.py
TS=$(date +%Y%m%d_%H%M%S)

echo "=== PATCH v2 Modal Sedi ==="
echo ""

# ==============================================================================
# 0. BACKUP
# ==============================================================================
echo "[0/4] Backup..."
cp "$SEDI_FILE" ~/gestione_flotta/backup/templates__dettaglio__sedi___riquadro.html.bak_${TS}
cp "$ROUTE_FILE" ~/gestione_flotta/backup/app__routes_sedi_cliente.py.bak_${TS}
echo "  OK"

# ==============================================================================
# 1. FIX AUTOCOMPLETE - Campi indirizzo nel modal sede
# ==============================================================================
echo ""
echo "[1/4] Fix autocomplete sui campi indirizzo..."

sed -i 's/id="sede-indirizzo" placeholder/id="sede-indirizzo" autocomplete="off" placeholder/' "$SEDI_FILE"
sed -i 's/id="sede-cap" maxlength/id="sede-cap" autocomplete="off" maxlength/' "$SEDI_FILE"
sed -i 's/id="sede-citta" style/id="sede-citta" autocomplete="off" style/' "$SEDI_FILE"
sed -i 's/id="sede-provincia" maxlength/id="sede-provincia" autocomplete="off" maxlength/' "$SEDI_FILE"
sed -i 's/id="sede-telefono">/id="sede-telefono" autocomplete="off">/' "$SEDI_FILE"
sed -i 's/id="sede-email">/id="sede-email" autocomplete="off">/' "$SEDI_FILE"
sed -i 's/id="sede-denominazione" placeholder/id="sede-denominazione" autocomplete="off" placeholder/' "$SEDI_FILE"

CNT=$(grep -c 'autocomplete="off"' "$SEDI_FILE")
echo "  OK - $CNT campi con autocomplete='off'"

# ==============================================================================
# 2. PULSANTE "+" accanto al dropdown referente
#    Wrappa il select in un input-group e aggiunge il bottone
# ==============================================================================
echo ""
echo "[2/4] Pulsante '+' per referente rapido..."

# Aggiungi div input-group prima del select
sed -i 's|<select class="form-select" id="sede-referente">|<div class="input-group">\n                            <select class="form-select" id="sede-referente">|' "$SEDI_FILE"

# Aggiungi bottone + chiusura div dopo </select> del referente
# Il </select> del referente e' quello subito dopo sede-referente
sed -i '/<select class="form-select" id="sede-referente">/,/<\/select>/{
    /<\/select>/a\
                            <button type="button" class="btn btn-outline-success" onclick="apriReferenteRapido()" title="Crea nuovo referente"><i class="bi bi-person-plus"></i></button>\
                        </div>
}' "$SEDI_FILE"

echo "  OK"

# ==============================================================================
# 3. INCLUDE del file satellite referente rapido
#    Lo inserisco subito prima del primo <style> nel file
# ==============================================================================
echo ""
echo "[3/4] Aggiunta include satellite referente rapido..."

# Inserisci include prima della prima riga <style>
sed -i '0,/^<style>/s|^<style>|{% include "dettaglio/sedi/_referente_rapido.html" %}\n\n<style>|' "$SEDI_FILE"

echo "  OK"

# ==============================================================================
# 4. API Python: referente-rapido (append a routes_sedi_cliente.py)
# ==============================================================================
echo ""
echo "[4/4] Aggiunta API referente-rapido..."

# Verifica che non sia gia presente
if grep -q "referente-rapido" "$ROUTE_FILE"; then
    echo "  SKIP - API gia presente"
else
    cat >> "$ROUTE_FILE" << 'PYEOF'


# ==============================================================================
# API: Creazione referente rapido (dal modal sede)
# ==============================================================================

@sedi_bp.route('/api/cliente/<int:cliente_id>/referente-rapido', methods=['POST'])
@login_required
def api_crea_referente_rapido(cliente_id):
    """Crea un referente con campi essenziali e ritorna l'ID."""
    data = request.get_json()
    
    cognome = (data.get('cognome') or '').strip()
    if not cognome:
        return jsonify({'success': False, 'error': 'Cognome obbligatorio'})
    
    nome = (data.get('nome') or '').strip()
    ruolo = (data.get('ruolo') or '').strip()
    cellulare = (data.get('cellulare') or '').strip()
    email_principale = (data.get('email_principale') or '').strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO referenti_clienti
            (cliente_id, nome, cognome, ruolo, cellulare, email_principale)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cliente_id, nome or None, cognome, ruolo or None,
              cellulare or None, email_principale or None))
        
        referente_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'id': referente_id,
            'nome': ((nome or '') + ' ' + cognome).strip()
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})
PYEOF
    echo "  OK"
fi

# ==============================================================================
# VERIFICHE
# ==============================================================================
echo ""
echo "=== VERIFICHE ==="
echo "autocomplete='off': $(grep -c 'autocomplete="off"' "$SEDI_FILE")"
echo "input-group referente: $(grep -c 'apriReferenteRapido' "$SEDI_FILE")"
echo "include satellite: $(grep -c '_referente_rapido.html' "$SEDI_FILE")"
echo "API Python: $(grep -c 'referente-rapido' "$ROUTE_FILE")"
echo ""
echo "=== PATCH v2 COMPLETATA ==="
echo "Riavviare: ~/gestione_flotta/scripts/gestione_flotta.sh restart"
