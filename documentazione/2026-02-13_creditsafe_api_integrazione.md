# Integrazione Creditsafe API Monitoring
## Piano di lavoro e TODO

**Data inizio**: 2026-02-13
**Stato**: IN CORSO

---

## TODO PRE-IMPLEMENTAZIONE

### TODO #1 - Fix acquisizione PDF Creditsafe (PRIMA di tutto)
> Sistemare `app/import_creditsafe.py` per gestire la data del documento:
> - Verificare data report PDF in importazione vs data report gia' in archivio
> - Se il PDF importato e' PIU' VECCHIO di quello gia' presente: NON sovrascrivere
> - Se il PDF importato e' PIU' RECENTE: aggiornare normalmente
> - Se il dato e' stato aggiornato via API (piu' recente): NON sovrascrivere con PDF vecchio
> - Campo di riferimento: `data_report_creditsafe` nella tabella clienti
> **Stato**: DA FARE (blocco separato, prima dell'integrazione API)

---

## PIANO IMPLEMENTAZIONE API

### Step 1 - Migrazione DB
- Aggiungere `connect_id TEXT` a tabella `clienti`
- Aggiungere `creditsafe_api_sync_at TEXT` a tabella `clienti`
- Aggiungere colonne API a tabella `clienti_creditsafe_alert`:
  - `connect_id TEXT`
  - `event_id TEXT UNIQUE`
  - `event_date TEXT`
  - `rule_code INTEGER`
  - `rule_description TEXT`
  - `old_value TEXT`
  - `new_value TEXT`
  - `is_processed INTEGER DEFAULT 0`
  - `processed_at TEXT`
  - `processed_by_id INTEGER`
- Nuovi indici per performance
- **File**: `scripts/migrazione_creditsafe_api.py`

### Step 2 - Modulo API base
- Classe `CreditsafeAPI` con gestione token JWT (cache 1h)
- Metodi: authenticate, search_company, portfolio CRUD, events
- Rate limiting integrato (sleep tra richieste)
- Retry con backoff su errori temporanei
- Lettura credenziali da file cifrato
- **File**: `app/creditsafe_api.py`

### Step 3 - Script esplorativo
- Autenticazione test
- Lista regole disponibili IT + XX
- Verifica/creazione portfolio
- Scarico eventi di esempio per mappare struttura reale
- **File**: `scripts/creditsafe_esplora.py`

### Step 4 - Gestione credenziali
- Pagina in Gestione Sistema per inserire/aggiornare credenziali API
- Salvataggio cifrato in `account_esterni/`
- Test connessione automatico dopo salvataggio
- Controllo periodico validita' credenziali
- **File**: `app/routes_admin_creditsafe.py` + template satellite

### Step 5 - Sincronizzazione automatica
- Cron job polling alert (frequenza da definire)
- Logica aggiornamento: solo se dato API piu' recente o campo vuoto
- Mapping regola -> campo DB (es: 1801 -> credito, 1802 -> score)
- Salvataggio evento in `clienti_creditsafe_alert`
- Aggiornamento campo live in `clienti`
- Integrazione con sistema notifiche esistente
- **File**: `scripts/creditsafe_sync.py`

### Step 6 - Importazione clienti nel portfolio
- Script per aggiungere clienti esistenti al portfolio monitoring
- Match per P.IVA -> connectId
- Salvataggio connectId nel record cliente
- Gestione errori (P.IVA non trovata, duplicati)
- **File**: parte di `scripts/creditsafe_sync.py`

### Step 7 - Frontend
- Sezione alert nel dettaglio cliente (file satellite)
- Badge/icona per clienti con alert non processati
- Possibilita' di marcare alert come gestiti
- Dashboard alert globale (opzionale)
- **File**: `templates/dettaglio/creditsafe_alert/` (satellite)

---

## LIMITI ABBONAMENTO

| Risorsa | Disponibili | Note |
|---------|-------------|------|
| Aziende IT monitorate | 2.000 | Sufficienti per clienti attivi |
| Alert | 49.999 | Ampio margine |
| Export | 2.000 | Per esportazione lista |
| Aziende internazionali | 550 | Per clienti esteri |
| Report PDF completi | NO | Non disponibili |

---

## MAPPING REGOLE -> CAMPI DB

| ruleCode | Descrizione | Campo clienti | Note |
|----------|-------------|---------------|------|
| 1801 | Cambio Credit Limit | `credito` | Soglia % da configurare |
| 1802 | Cambio Credit Score | `score`, `punteggio_rischio` | Soglia punti da configurare |
| 3054 | Evento negativo | `protesti`, `importo_protesti` | Da verificare struttura dati |
| 3055 | Cambio stato azienda | `stato` | Attiva/Inattiva/Cessata |
| 3056 | Cambio indirizzo | `indirizzo`, `via`, `cap`, `citta` | Rispettare flag `indirizzo_protetto` |
| 3057 | Cambio amministratori | (log solo) | Solo storico, no campo diretto |

> NOTA: mapping definitivo dopo test reale con script esplorativo (Step 3)

---

## NOTE TECNICHE

- Token JWT dura 1 ora, implementare refresh automatico
- Rate limiting: `time.sleep(1)` tra richieste
- Credenziali in `account_esterni/Credenziali_api_creditsafe.txt`
- Endpoint produzione: `https://connect.creditsafe.com/v1`
- NO webhook disponibili, solo polling
