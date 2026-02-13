# Sessione 2026-02-13 - Creditsafe API Monitoring (Completamento)

## RIEPILOGO

Completati tutti i 6 task dell'integrazione Creditsafe API Monitoring.
372 clienti sincronizzati con il portfolio, 6 regole alert attivate,
polling automatico settimanale configurato.

---

## TASK COMPLETATI

### TASK 3 - Migrazione DB: campo amministratore_variato
- **File**: `scripts/migrazione_amministratore_variato.py` (NUOVO)
- Aggiunta colonna `amministratore_variato INTEGER DEFAULT 0` alla tabella `clienti`
- Usato dalla regola 107 (cambio amministratori) per segnalare variazione
- Reset automatico su import PDF Creditsafe

### TASK 1 - Script sync clienti con portfolio Creditsafe
- **File**: `scripts/creditsafe_sync_clienti.py` (NUOVO)
- Sincronizzati 296 clienti su 372 (75 persone fisiche/ditte individuali non trovate su Creditsafe)
- Rimossa azienda test A.T.I.B. SRL dal portfolio
- Slot monitoring usati: 297/2000
- Salvataggio progresso con ripresa da interruzione
- 6 regole alert attivate sul portfolio 1762584:
  - [101] International Score (variazione 1+ bande)
  - [102] Credit Limit (variazione 1%+)
  - [1404] Protesti
  - [1406] Company Status
  - [105] Address
  - [107] Directors

**Scoperta codici regole reali** (diversi da documentazione Creditsafe):
| Funzione | Doc vecchio | Codice reale |
|----------|-------------|--------------|
| Score | 1802 | 101 |
| Limit | 1801 | 102 |
| Protesti | 3054 | 1404 |
| Stato | 3055 | 1406 |
| Indirizzo | 3056 | 105 |
| Amministratori | 3057 | 107 |

### TASK 2 - Cron job polling alert settimanale
- **File**: `scripts/creditsafe_polling_alert.py` (NUOVO)
- Scheduling: ogni giovedi' ore 20:00
- Per ogni alert ricevuto:
  - Salva in `clienti_creditsafe_alert`
  - Aggiorna campo corrispondente in `clienti`
  - Registra in `storico_modifiche` (origine: "Creditsafe API Alert")
  - Marca evento come processato su API
- Logica aggiornamento per regola:
  - 102: aggiorna `clienti.credito` con `new_value`
  - 101: aggiorna `clienti.score` con `new_value`
  - 1404: aggiorna `clienti.protesti` con `new_value`
  - 1406: aggiorna `clienti.stato` con `new_value`
  - 105: aggiorna indirizzo + imposta `indirizzo_protetto = 1` (Creditsafe = fonte verita')
  - 107: imposta `amministratore_variato = 1` (flag, no dati)

### TASK 6 - Reset flag amministratore su import PDF
- **File**: `app/import_creditsafe.py` (MODIFICATO - righe 788-789 e 793-794)
- Dopo ogni `aggiorna_cliente_da_creditsafe()` esegue:
  `UPDATE clienti SET amministratore_variato = 0 WHERE id = ?`
- Si applica solo quando il PDF e' piu' recente o data mancante (non su PDF vecchi)

### TASK 4 - Card admin contatori monitoring
- **File**: `app/routes_admin_creditsafe.py` (MODIFICATO - aggiunta route `/admin/creditsafe/contatori`)
- **File**: `templates/admin/creditsafe/_card.html` (MODIFICATO - sezione contatori)
- **File**: `templates/admin/creditsafe/_scripts.html` (MODIFICATO - funzione `csCaricaContatori`)
- Mostra: aziende monitorate, alert usati, ultimo/prossimo polling, scadenza abbonamento

### TASK 5 - Dettaglio cliente: data API + flag amministratore
- **File**: `templates/dettaglio/rating/_content.html` (MODIFICATO)
  - Aggiunta riga "API Monitoring aggiornato alla data" (visibile solo se connect_id presente)
  - Rimossa riga "Flotta" (non pertinente al rating)
  - Aggiornata condizione "nessuna info disponibile"
- **File**: `templates/dettaglio/capogruppo/_content.html` (MODIFICATO)
  - Aggiunta icona ! rossa nell'header se `amministratore_variato = 1`
  - Tooltip: "Amministratore variato - verificare su Creditsafe"
- **File**: `templates/dettaglio/flotta/_content.html` (MODIFICATO)
  - Aggiunta riga "Ultimo import flotta" in fondo alla card

---

## FIX APPLICATI

### Fix isActive regole API
- Le regole API vogliono `isActive` come intero (1), non boolean Python (True)
- Corretto in `scripts/creditsafe_sync_clienti.py`

### Fix errore 409 (gia' nel portfolio)
- `scripts/creditsafe_sync_clienti.py`: gestione 409 come "gia' presente" (non errore)
- `app/creditsafe_api.py`: aggiunto 409 agli errori non recuperabili (no retry)

---

## CRONTAB AGGIORNATO

```
# Creditsafe polling alert - ogni giovedi ore 20:00
0 20 * * 4 cd /home/michele/gestione_flotta && python3 scripts/creditsafe_polling_alert.py >> logs/creditsafe_polling.log 2>&1
```

NOTA: nel crontab ci sono voci duplicate (scraping Ayvens/Arval/jato e Flotta). Da pulire.

---

## STATO ATTUALE SISTEMA

| Elemento | Valore |
|----------|--------|
| Clienti monitorati | 297/2000 slot |
| Alert usati | 0/49999 |
| Regole attive | 6 (101, 102, 105, 107, 1404, 1406) |
| Scadenza abbonamento | 09/06/2026 |
| Polling | Giovedi' 20:00 |
| Persone fisiche escluse | 75 (non presenti su Creditsafe) |

---

## FILE NUOVI

| File | Descrizione |
|------|-------------|
| `scripts/migrazione_amministratore_variato.py` | Migrazione DB campo flag |
| `scripts/creditsafe_sync_clienti.py` | Sync clienti -> portfolio |
| `scripts/creditsafe_polling_alert.py` | Cron job polling alert |

## FILE MODIFICATI

| File | Modifica |
|------|----------|
| `app/creditsafe_api.py` | Aggiunto 409 a errori non recuperabili |
| `app/import_creditsafe.py` | Reset flag amministratore_variato su import PDF |
| `app/routes_admin_creditsafe.py` | Route contatori monitoring |
| `templates/admin/creditsafe/_card.html` | Sezione contatori |
| `templates/admin/creditsafe/_scripts.html` | Funzione csCaricaContatori |
| `templates/dettaglio/rating/_content.html` | Riga API + pulizia Flotta |
| `templates/dettaglio/capogruppo/_content.html` | Flag ! amministratore |
| `templates/dettaglio/flotta/_content.html` | Riga ultimo import flotta |
| `db/gestionale.db` | Colonna amministratore_variato + 297 connect_id |
