# Sessione 2026-02-13 - Integrazione Creditsafe API (Inizio)

## LAVORI COMPLETATI

### Step 1 - Migrazione DB
- **File**: `scripts/migrazione_creditsafe_api.py`
- Aggiunta 3 colonne a tabella `clienti`: `connect_id`, `creditsafe_api_sync_at`, `creditsafe_portfolio_ref`
- Aggiunta 10 colonne a tabella `clienti_creditsafe_alert` per eventi API: `connect_id`, `event_id`, `event_date`, `rule_code`, `rule_description`, `old_value`, `new_value`, `is_processed`, `processed_at`, `processed_by_id`
- Creati 6 indici per performance
- Backup automatico DB prima della migrazione

### Step 2 - Modulo API base
- **File**: `app/creditsafe_api.py`
- Classe `CreditsafeAPI` con tutti i metodi: authenticate, search, portfolio CRUD, event rules, notification events
- Cache token JWT (55 minuti)
- Rate limiting integrato (1s tra richieste)
- Retry con backoff (3 tentativi) su errori temporanei
- Auto-refresh token su 401
- Lettura credenziali da file `account_esterni/Credenziali_api_creditsafe.txt`

### Step 3 - Script esplorativo
- **File**: `scripts/creditsafe_esplora.py`
- Test autenticazione: OK
- Verifica accesso account: confermati 2.000 monitoring domestici, scadenza 09/06/2026
- Regole e portfolio: endpoint monitoring in 504/500 (problema server Creditsafe temporaneo)
- Test ricerca azienda per P.IVA: OK (testato con A.T.I.B. S.R.L.)

### Step 4 - Gestione credenziali in Amministrazione
- **File**: `app/routes_admin_creditsafe.py` (blueprint)
- **File**: `templates/admin/creditsafe/_card.html` (HTML satellite)
- **File**: `templates/admin/creditsafe/_scripts.html` (JS satellite)
- Route: `/admin/creditsafe/stato` (GET), `/admin/creditsafe/test` (POST), `/admin/creditsafe/salva` (POST)
- Card nella pagina admin con stato, test connessione, modifica credenziali
- Backup automatico file credenziali prima della sovrascrittura
- Log attivita' su modifica credenziali

### Documentazione
- **File**: `documentazione/2026-02-13_creditsafe_api_integrazione.md` (piano lavoro completo + TODO)

## SCOPERTE DALLA RISPOSTA API REALE

- `connectId` formato reale: `IT-0-BS183271` (non `IT001-X-...` come documentato)
- `vatNo` e' un **array** (azienda puo' avere piu' P.IVA)
- `regNo` corrisponde al nostro `numero_registrazione` gia' nel DB

## PROSSIMI STEP

1. **Riprovare endpoint monitoring** (eventRules + portfolios) - problema temporaneo server Creditsafe
2. **Script sync clienti** - mapping connectId per clienti esistenti
3. **Cron job** - polling alert periodico
4. **Frontend alert** - sezione nel dettaglio cliente

## TODO PRE-IMPLEMENTAZIONE (da fare separatamente)
- Fix `app/import_creditsafe.py`: logica confronto date report per non sovrascrivere dati piu' recenti

## FILE MODIFICATI

| File | Tipo modifica |
|------|--------------|
| `scripts/migrazione_creditsafe_api.py` | NUOVO |
| `app/creditsafe_api.py` | NUOVO |
| `scripts/creditsafe_esplora.py` | NUOVO |
| `app/routes_admin_creditsafe.py` | NUOVO |
| `templates/admin/creditsafe/_card.html` | NUOVO |
| `templates/admin/creditsafe/_scripts.html` | NUOVO |
| `documentazione/2026-02-13_creditsafe_api_integrazione.md` | NUOVO |
| `app/web_server.py` | MODIFICATO (import + register blueprint) |
| `templates/admin.html` | MODIFICATO (include card + scripts) |
| `db/gestionale.db` | MODIFICATO (migrazione: 13 colonne + 6 indici) |
