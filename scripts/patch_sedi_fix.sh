#!/bin/bash
# ==============================================================================
# PATCH: Fix Modal Sedi - Autocomplete + Referente Rapido
# Data: 2026-02-12
# Target: templates/dettaglio/sedi/_riquadro.html
#          app/routes_sedi_cliente.py
# ==============================================================================

set -e
SEDI_FILE=~/gestione_flotta/templates/dettaglio/sedi/_riquadro.html
ROUTE_FILE=~/gestione_flotta/app/routes_sedi_cliente.py
TS=$(date +%Y%m%d_%H%M%S)

echo "=== PATCH Modal Sedi ==="
echo ""

# ==============================================================================
# 0. BACKUP
# ==============================================================================
echo "[0/5] Backup..."
cp "$SEDI_FILE" ~/gestione_flotta/backup/templates__dettaglio__sedi___riquadro.html.bak_${TS}
cp "$ROUTE_FILE" ~/gestione_flotta/backup/app__routes_sedi_cliente.py.bak_${TS}
echo "  OK"

# ==============================================================================
# 1. FIX AUTOCOMPLETE - Campi indirizzo
# ==============================================================================
echo ""
echo "[1/5] Fix autocomplete sui campi indirizzo..."

sed -i 's/id="sede-indirizzo" placeholder/id="sede-indirizzo" autocomplete="off" placeholder/' "$SEDI_FILE"
sed -i 's/id="sede-cap" maxlength/id="sede-cap" autocomplete="off" maxlength/' "$SEDI_FILE"
sed -i 's/id="sede-citta" style/id="sede-citta" autocomplete="off" style/' "$SEDI_FILE"
sed -i 's/id="sede-provincia" maxlength/id="sede-provincia" autocomplete="off" maxlength/' "$SEDI_FILE"
sed -i 's/id="sede-telefono">/id="sede-telefono" autocomplete="off">/' "$SEDI_FILE"
sed -i 's/id="sede-email">/id="sede-email" autocomplete="off">/' "$SEDI_FILE"
sed -i 's/id="sede-denominazione" placeholder/id="sede-denominazione" autocomplete="off" placeholder/' "$SEDI_FILE"

echo "  OK - autocomplete='off' aggiunto a 7 campi"

# ==============================================================================
# 2. PULSANTE "+" accanto al dropdown referente
# ==============================================================================
echo ""
echo "[2/5] Aggiunta pulsante '+' per referente rapido..."

# Sostituisco il select semplice con input-group (select + bottone)
sed -i '/<select class="form-select" id="sede-referente">/,/<\/select>/{
    /select class="form-select"/c\
                        <div class="input-group">\
                            <select class="form-select" id="sede-referente">\
                                <option value="">-- Nessun referente --</option>\
                            </select>\
                            <button type="button" class="btn btn-outline-success" onclick="apriReferenteRapido()" title="Crea nuovo referente">\
                                <i class="bi bi-person-plus"></i>\
                            </button>\
                        </div>
    /option value="">-- Nessun/d
    /<\/select>/d
}' "$SEDI_FILE"

echo "  OK - Pulsante '+' aggiunto"

# ==============================================================================
# 3. MINI-MODAL creazione referente rapido (inserito prima di </script>)
# ==============================================================================
echo ""
echo "[3/5] Aggiunta mini-modal referente rapido..."

# Trovo l'ultimo </script> e inserisco il modal PRIMA della chiusura style/script
# Inserisco il modal HTML subito dopo il modal Dettaglio Referente
sed -i '/<!-- Modal Dettaglio Referente -->/i\
<!-- Modal Referente Rapido (da modal sede) -->\
<div class="modal fade" id="modalReferenteRapido" tabindex="-1" data-bs-backdrop="static">\
    <div class="modal-dialog modal-dialog-centered">\
        <div class="modal-content">\
            <div class="modal-header py-2 bg-success text-white">\
                <h6 class="modal-title"><i class="bi bi-person-plus me-1"></i>Nuovo Referente (rapido)</h6>\
                <button type="button" class="btn-close btn-close-white" onclick="chiudiReferenteRapido()"></button>\
            </div>\
            <div class="modal-body">\
                <div class="row g-2">\
                    <div class="col-md-6">\
                        <label class="form-label small">Nome</label>\
                        <input type="text" class="form-control form-control-sm" id="rapido-ref-nome" autocomplete="off">\
                    </div>\
                    <div class="col-md-6">\
                        <label class="form-label small">Cognome <span class="text-danger">*</span></label>\
                        <input type="text" class="form-control form-control-sm" id="rapido-ref-cognome" autocomplete="off" required>\
                    </div>\
                    <div class="col-md-6">\
                        <label class="form-label small">Ruolo</label>\
                        <select class="form-select form-select-sm" id="rapido-ref-ruolo">\
                            <option value="">-- Seleziona --</option>\
                            <option value="Titolare">Titolare</option>\
                            <option value="Amministratore">Amministratore</option>\
                            <option value="Commerciale">Commerciale</option>\
                            <option value="Fleet Manager">Fleet Manager</option>\
                            <option value="HR">HR</option>\
                            <option value="Segreteria">Segreteria</option>\
                            <option value="Contabilita">Contabilita</option>\
                            <option value="Altro">Altro</option>\
                        </select>\
                    </div>\
                    <div class="col-md-6">\
                        <label class="form-label small">Cellulare</label>\
                        <input type="tel" class="form-control form-control-sm" id="rapido-ref-cellulare" autocomplete="off">\
                    </div>\
                    <div class="col-md-12">\
                        <label class="form-label small">Email</label>\
                        <input type="email" class="form-control form-control-sm" id="rapido-ref-email" autocomplete="off">\
                    </div>\
                </div>\
            </div>\
            <div class="modal-footer py-2">\
                <button type="button" class="btn btn-secondary btn-sm" onclick="chiudiReferenteRapido()">Annulla</button>\
                <button type="button" class="btn btn-success btn-sm" onclick="salvaReferenteRapido()">\
                    <i class="bi bi-check"></i> Crea e Collega\
                </button>\
            </div>\
        </div>\
    </div>\
</div>\
' "$SEDI_FILE"

echo "  OK - Mini-modal inserito"

# ==============================================================================
# 4. FUNZIONI JS per referente rapido (inserite prima di </script>)
# ==============================================================================
echo ""
echo "[4/5] Aggiunta funzioni JS referente rapido..."

# Trovo l'ultimo </script> nel file e inserisco prima di esso
# Uso un marker unico: la funzione confermaCancellaSede è l'ultima funzione
cat >> /tmp/patch_ref_rapido_js.txt << 'JSEOF'

// =====================================================================
// CREAZIONE REFERENTE RAPIDO (dal modal sede)
// =====================================================================
let sedeModalStateSaved = null;

function apriReferenteRapido() {
    // Salva stato corrente del modal sede
    sedeModalStateSaved = {
        editId: document.getElementById('sede-edit-id').value,
        tipo: document.getElementById('sede-tipo').value,
        denominazione: document.getElementById('sede-denominazione').value,
        indirizzo: document.getElementById('sede-indirizzo').value,
        cap: document.getElementById('sede-cap').value,
        citta: document.getElementById('sede-citta').value,
        provincia: document.getElementById('sede-provincia').value,
        telefono: document.getElementById('sede-telefono').value,
        email: document.getElementById('sede-email').value,
        referente: document.getElementById('sede-referente').value,
        note: document.getElementById('sede-note').value
    };
    
    // Nascondi modal sede
    bootstrap.Modal.getInstance(document.getElementById('modalSede')).hide();
    
    // Pulisci e apri mini-modal referente
    document.getElementById('rapido-ref-nome').value = '';
    document.getElementById('rapido-ref-cognome').value = '';
    document.getElementById('rapido-ref-ruolo').value = '';
    document.getElementById('rapido-ref-cellulare').value = '';
    document.getElementById('rapido-ref-email').value = '';
    
    setTimeout(function() {
        new bootstrap.Modal(document.getElementById('modalReferenteRapido')).show();
    }, 300);
}

function chiudiReferenteRapido() {
    bootstrap.Modal.getInstance(document.getElementById('modalReferenteRapido')).hide();
    // Riapri modal sede con stato salvato
    if (sedeModalStateSaved) {
        setTimeout(function() { ripristinaSede(); }, 300);
    }
}

function ripristinaSede() {
    const s = sedeModalStateSaved;
    if (!s) return;
    
    document.getElementById('sede-edit-id').value = s.editId;
    document.getElementById('modalSedeTitle').textContent = s.editId ? 'Modifica Sede' : 'Aggiungi Sede';
    document.getElementById('sede-tipo').value = s.tipo;
    document.getElementById('sede-denominazione').value = s.denominazione;
    document.getElementById('sede-indirizzo').value = s.indirizzo;
    document.getElementById('sede-cap').value = s.cap;
    document.getElementById('sede-citta').value = s.citta;
    document.getElementById('sede-provincia').value = s.provincia;
    document.getElementById('sede-telefono').value = s.telefono;
    document.getElementById('sede-email').value = s.email;
    document.getElementById('sede-note').value = s.note;
    
    new bootstrap.Modal(document.getElementById('modalSede')).show();
    
    // Seleziona referente dopo che il modal si apre
    setTimeout(function() {
        document.getElementById('sede-referente').value = s.referente;
    }, 100);
}

function salvaReferenteRapido() {
    const cognome = document.getElementById('rapido-ref-cognome').value.trim();
    if (!cognome) {
        alert('Il cognome e\' obbligatorio');
        document.getElementById('rapido-ref-cognome').focus();
        return;
    }
    
    const payload = {
        nome: document.getElementById('rapido-ref-nome').value.trim(),
        cognome: cognome,
        ruolo: document.getElementById('rapido-ref-ruolo').value,
        cellulare: document.getElementById('rapido-ref-cellulare').value.trim(),
        email_principale: document.getElementById('rapido-ref-email').value.trim()
    };
    
    fetch(`/api/cliente/${clienteIdSedi}/referente-rapido`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Chiudi mini-modal
            bootstrap.Modal.getInstance(document.getElementById('modalReferenteRapido')).hide();
            
            // Aggiorna lista referenti dal server
            fetch(`/api/cliente/${clienteIdSedi}/sedi`)
                .then(r => r.json())
                .then(sediData => {
                    if (sediData.success) {
                        referentiDisponibili = sediData.referenti || [];
                        popolaSelectReferenti();
                    }
                    
                    // Imposta il nuovo referente come selezionato
                    if (sedeModalStateSaved) {
                        sedeModalStateSaved.referente = data.id;
                    }
                    
                    // Riapri modal sede
                    setTimeout(function() { ripristinaSede(); }, 300);
                });
        } else {
            alert(data.error || 'Errore creazione referente');
        }
    })
    .catch(err => {
        console.error(err);
        alert('Errore di rete');
    });
}
JSEOF

# Inserisci prima dell'ultimo </script>
sed -i '/^<\/script>$/{
    r /tmp/patch_ref_rapido_js.txt
}' "$SEDI_FILE"

rm -f /tmp/patch_ref_rapido_js.txt
echo "  OK - 5 funzioni JS aggiunte"

# ==============================================================================
# 5. API Python: referente-rapido in routes_sedi_cliente.py
# ==============================================================================
echo ""
echo "[5/5] Aggiunta API referente-rapido..."

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

echo "  OK - API /api/cliente/<id>/referente-rapido aggiunta"

# ==============================================================================
# VERIFICHE FINALI
# ==============================================================================
echo ""
echo "=== VERIFICHE ==="
echo ""
echo "--- autocomplete='off' ---"
grep -c "autocomplete=" "$SEDI_FILE"
echo ""
echo "--- Pulsante referente rapido ---"
grep -c "apriReferenteRapido" "$SEDI_FILE"
echo ""
echo "--- Modal referente rapido ---"
grep -c "modalReferenteRapido" "$SEDI_FILE"
echo ""
echo "--- API Python ---"
grep -c "referente-rapido" "$ROUTE_FILE"
echo ""
echo "=== PATCH COMPLETATA ==="
echo "Riavviare: ~/gestione_flotta/scripts/gestione_flotta.sh restart"
