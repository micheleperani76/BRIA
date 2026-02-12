# FIX BUG SCHEDA DOCUMENTI CLIENTE
## Data: 2026-02-12

### Bug corretti

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `_scripts_comuni.html` | `refreshDocumenti()` non chiama `caricaContratti/Ordini/Quotazioni` | Aggiunti 3 rami elif |
| 2 | `_scripts_comuni.html` | `eseguiUpload()` cerca container ID sbagliati (`lista-contratti` vs `contratti-file-list`) | Mappatura container corretta |
| 3 | `routes_documenti_cliente.py` | Messaggio errore Car Policy non include XLS/XLSX | Aggiornato testo errore |
| 4 | `_scripts_collapse.html` | Dead code: file orfano non incluso da nessun template | Da rimuovere manualmente |

### File modificati
- `templates/documenti_cliente/shared/_scripts_comuni.html` (fix 1 + fix 2)
- `app/routes_documenti_cliente.py` (fix 3)

### File da rimuovere
- `templates/documenti_cliente/shared/_scripts_collapse.html` (dead code)

### Bug 5 - CRITICO: Conflitto nome eliminaDocumento()

| Aspetto | Dettaglio |
|---------|-----------|
| **Problema** | `window.eliminaDocumento` definita in `shared/_scripts_comuni.html` (2 parametri: tipo, nomeFile) sovrascriveva quella in `documenti_strutturati/_modal.html` (1 parametro: tipo). Il bottone elimina nei Documenti Strutturati chiamava la route sbagliata `/documenti/identita_lr/elimina` invece di `/documenti-strutturati/elimina` |
| **File corretto** | `templates/documenti_cliente/documenti_strutturati/_modal.html` (righe 316 e 646) |
| **Fix** | Rinominata in `eliminaDocStrutturato()` |
| **Nota** | Esiste anche `templates/documenti_modal.html` (file orfano/legacy, NON incluso da documenti_cliente.html). Fixato per sicurezza ma non era quello attivo |
