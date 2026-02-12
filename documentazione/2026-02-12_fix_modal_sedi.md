# Fix Modal Sedi: Autocomplete + Referente Rapido

**Data**: 2026-02-12
**Sessione**: Correzione errori scheda clienti

---

## Bug Risolti

### 1. Errore SQL "Incorrect number of bindings" (FIX 1)
- **Causa**: `protetto = 1` hardcoded nell'UPDATE invece di `protetto = ?`
- **Fix**: sed su `routes_sedi_cliente.py` riga 190
- **Applicato**: SI

### 2. TIPI_SEDE triplicato (FIX 2)
- **Causa**: patch precedente ha aggiunto "Indirizzo Fatturazione" 3 volte
- **Fix**: sed su `routes_sedi_cliente.py`
- **Applicato**: SI

### 3. Browser chiede "Salvare indirizzo?" (FIX 3)
- **Causa**: Chrome rileva campi indirizzo e propone salvataggio
- **Fix**: `autocomplete="off"` su tutti i campi del modal sede
- **File**: `templates/dettaglio/sedi/_riquadro.html`

### 4. Creazione referente al volo dalla sede (FIX 4)
- **Richiesta**: poter creare un referente senza uscire dal modal sede
- **Soluzione**: pulsante "+" accanto al dropdown + mini-modal rapido
- **Flusso**: 
  1. Utente clicca "+" nel modal sede
  2. Stato modal sede salvato in memoria JS
  3. Si apre mini-modal con campi essenziali (nome, cognome, ruolo, cell, email)
  4. "Crea e Collega" salva via AJAX
  5. Modal sede si riapre con il nuovo referente auto-selezionato
- **File modificati**: `_riquadro.html` + `routes_sedi_cliente.py`
- **Nuova API**: `POST /api/cliente/<id>/referente-rapido`

---

## File Coinvolti

| File | Azione |
|------|--------|
| `app/routes_sedi_cliente.py` | FIX SQL + FIX duplicati + API referente-rapido |
| `templates/dettaglio/sedi/_riquadro.html` | autocomplete + pulsante + mini-modal + JS |

---

## Deploy

```bash
bash ~/gestione_flotta/Scaricati/patch_sedi_fix.sh
~/gestione_flotta/scripts/gestione_flotta.sh restart
```
