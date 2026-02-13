# Sessione 2026-02-13 - Fix Import PDF Creditsafe (logica scarto)

## LAVORO COMPLETATO

### Modifica: `app/import_creditsafe.py` (v2.3.2 -> v2.4.0)

Modificata la funzione `processa_pdf()` con 3 patch chirurgiche per
implementare la nuova logica di scarto/eliminazione PDF.

### PATCH 1 - Ricerca fallback per Codice Fiscale
- Dopo la ricerca per P.IVA, se non trova corrispondenza, cerca per CF
- Query: `SELECT * FROM clienti WHERE cod_fiscale = ?`
- Log: "Trovato per CF: XXXXXX"

### PATCH 2 - PDF senza corrispondenza -> SCARTA
- **Prima**: se il PDF non corrispondeva a nessun cliente, creava un nuovo record
- **Dopo**: il PDF viene scartato (`return True`), il chiamante lo elimina da `pdf/`
- Non viene creato alcun cliente
- Log: "SCARTATO: nessuna corrispondenza P.IVA/CF in database"

### PATCH 3 - PDF piu' vecchio del DB -> SCARTA
- **Prima**: i dati non venivano aggiornati ma il PDF veniva comunque archiviato
- **Dopo**: il PDF viene scartato (`return True`), il chiamante lo elimina da `pdf/`
- Non viene archiviato nella cartella del cliente
- Log: "SCARTATO: report PDF (data) piu' vecchio del DB (data)"

## FLUSSO RISULTANTE

```
PDF in pdf/
  |
  v
Estrai testo + dati
  |
  v
Cerca cliente per P.IVA
  | (non trovato?)
  v
Cerca cliente per CF (NUOVO - Patch 1)
  |
  +-- NON trovato -> SCARTATO, PDF eliminato (Patch 2)
  |
  +-- Trovato, data DB vuota -> AGGIORNA + archivia (invariato)
  |
  +-- Trovato, PDF piu' recente -> AGGIORNA + archivia (invariato)
  |
  +-- Trovato, PDF piu' vecchio -> SCARTATO, PDF eliminato (Patch 3)
```

## RAGIONAMENTO API vs PDF

Non serve confrontare la data PDF con `creditsafe_api_sync_at` perche':
- Il PDF viene scaricato manualmente dal sito Creditsafe -> data sempre corrente
- L'API gira 1 volta/settimana (giovedi' 20:00) -> il PDF sara' sempre piu' recente
- Se il PDF sovrascrive un dato API, il polling successivo lo riallinea

## FILE MODIFICATI

| File | Modifica |
|------|----------|
| `app/import_creditsafe.py` | 3 patch a `processa_pdf()` |

## FILE NUOVI

| File | Descrizione |
|------|-------------|
| `scripts/patch_import_creditsafe_v3.py` | Script patch con dry-run e verifiche |

## BACKUP

- `backup/app__import_creditsafe.py.bak_20260213_145016`
