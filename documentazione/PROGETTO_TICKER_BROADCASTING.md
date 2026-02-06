# PROGETTO TICKER BROADCASTING
## Sistema messaggi scorrevoli con scheduling intelligente

**Data**: 2026-02-06
**Versione**: 2.0.0
**Stato**: Fasi 1-3 completate
**Modulo**: Ticker Broadcasting (topbar)

---

## 1. PANORAMICA

Sistema di broadcasting intelligente che mostra messaggi nel ticker
della topbar. I messaggi hanno scheduling temporale, priorita',
animazioni configurabili e frequenza di apparizione controllata.

### Concetto chiave
La barra NON deve mostrare sempre informazioni: i messaggi appaiono
a intervalli casuali, con una quantita' massima configurabile per ora.
Tra un messaggio e l'altro la barra resta vuota (pulita).

---

## 2. TIPI DI MESSAGGI

### 2.1 Manuali (inseriti dagli utenti)
- Qualsiasi utente puo' proporre un messaggio
- Admin approva/rifiuta prima della pubblicazione
- Scheduling configurabile (data inizio/fine, giorni settimana, orari)

### 2.2 Automatici (generati dal sistema)
| Tipo | Fonte | Quando |
|------|-------|--------|
| Compleanni utenti | `utenti.data_nascita` | Giorno esatto |
| Auguri Natale | Config fissa | 18-25 Dicembre |
| Cambio gomme invernali | Config fissa | 15 Ott - 15 Nov |
| Cambio gomme estive | Config fissa | 15 Mar - 15 Apr |
| Buon anno | Config fissa | 1-3 Gennaio |
| Scadenze contratti | `veicoli.data_scadenza` | 30gg prima |

I messaggi automatici vengono generati da un **cron job** che controlla
ogni giorno e inserisce i messaggi nel DB se non gia' presenti.

---

## 3. DESTINATARI

| Destinazione | Esempio |
|--------------|---------|
| `TUTTI` | Auguri Natale, Buon Anno |
| `RUOLO:COMMERCIALE` | Cambio gomme, scadenze contratti |
| `RUOLO:ADMIN` | Messaggi di sistema |
| `UTENTE:<id>` | Auguri compleanno specifico |

---

## 4. ANIMAZIONI

| Codice | Effetto | CSS |
|--------|---------|-----|
| `scroll-ltr` | Scorrimento sinistra &rarr; destra | translateX(-100%) &rarr; translateX(100%) |
| `scroll-rtl` | Scorrimento destra &rarr; sinistra (classico) | translateX(100%) &rarr; translateX(-100%) |
| `slide-up` | Sale dal basso | translateY(100%) &rarr; translateY(0) |
| `slide-down` | Scende dall'alto | translateY(-100%) &rarr; translateY(0) |
| `fade` | Dissolvenza in/out | opacity 0 &rarr; 1 &rarr; 0 |

Ogni messaggio ha la propria animazione configurabile.
Durata animazione configurabile (secondi di permanenza).

---

## 5. DATABASE

### 5.1 Tabella `ticker_messaggi`

```sql
CREATE TABLE IF NOT EXISTS ticker_messaggi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Contenuto
    testo TEXT NOT NULL,
    icona TEXT DEFAULT '',              -- classe bi-* (opzionale)
    colore_testo TEXT DEFAULT '#000000',
    
    -- Animazione
    animazione TEXT DEFAULT 'scroll-rtl',   -- scroll-rtl, scroll-ltr, slide-up, slide-down, fade
    durata_secondi INTEGER DEFAULT 8,       -- tempo permanenza/scorrimento
    velocita TEXT DEFAULT 'normale',         -- lenta, normale, veloce
    
    -- Scheduling
    data_inizio TEXT NOT NULL,              -- YYYY-MM-DD
    data_fine TEXT,                         -- YYYY-MM-DD (NULL = solo data_inizio)
    ora_inizio TEXT DEFAULT '00:00',        -- HH:MM
    ora_fine TEXT DEFAULT '23:59',          -- HH:MM
    giorni_settimana TEXT DEFAULT '1,2,3,4,5,6,7',  -- 1=lun, 7=dom
    ricorrenza TEXT DEFAULT 'nessuna',      -- nessuna, annuale, mensile
    
    -- Priorita' e frequenza
    priorita INTEGER DEFAULT 5,            -- 1=bassa, 5=normale, 10=urgente
    peso INTEGER DEFAULT 1,                -- peso nel random (piu' alto = piu' frequente)
    
    -- Destinatari
    destinatari TEXT DEFAULT 'TUTTI',       -- TUTTI, RUOLO:xxx, UTENTE:123
    
    -- Approvazione
    stato TEXT DEFAULT 'bozza',            -- bozza, in_attesa, approvato, rifiutato, scaduto
    creato_da INTEGER NOT NULL,
    approvato_da INTEGER,
    data_approvazione TEXT,
    nota_rifiuto TEXT,
    
    -- Tipo
    tipo TEXT DEFAULT 'manuale',           -- manuale, automatico, sistema
    codice_auto TEXT,                      -- per dedup automatici (es. compleanno_2026_42)
    
    -- Audit
    data_creazione TEXT DEFAULT (datetime('now', 'localtime')),
    data_modifica TEXT,
    
    FOREIGN KEY (creato_da) REFERENCES utenti(id),
    FOREIGN KEY (approvato_da) REFERENCES utenti(id)
);

-- Indici
CREATE INDEX IF NOT EXISTS idx_ticker_stato ON ticker_messaggi(stato);
CREATE INDEX IF NOT EXISTS idx_ticker_date ON ticker_messaggi(data_inizio, data_fine);
CREATE INDEX IF NOT EXISTS idx_ticker_tipo ON ticker_messaggi(tipo);
CREATE INDEX IF NOT EXISTS idx_ticker_codice ON ticker_messaggi(codice_auto);
```

### 5.2 Tabella `ticker_config`

```sql
CREATE TABLE IF NOT EXISTS ticker_config (
    chiave TEXT PRIMARY KEY,
    valore TEXT NOT NULL,
    descrizione TEXT
);

-- Valori default
INSERT OR IGNORE INTO ticker_config VALUES ('messaggi_ora', '4', 'Messaggi massimi per ora');
INSERT OR IGNORE INTO ticker_config VALUES ('pausa_minima_sec', '120', 'Pausa minima tra messaggi (secondi)');
INSERT OR IGNORE INTO ticker_config VALUES ('pausa_massima_sec', '600', 'Pausa massima tra messaggi (secondi)');
INSERT OR IGNORE INTO ticker_config VALUES ('attivo', '1', 'Sistema ticker attivo');
INSERT OR IGNORE INTO ticker_config VALUES ('auto_compleanni', '1', 'Genera automaticamente auguri compleanno');
INSERT OR IGNORE INTO ticker_config VALUES ('auto_festivita', '1', 'Genera automaticamente messaggi festivita');
INSERT OR IGNORE INTO ticker_config VALUES ('auto_gomme', '1', 'Genera automaticamente promemoria cambio gomme');
```

### 5.3 Tabella `ticker_log`

```sql
CREATE TABLE IF NOT EXISTS ticker_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    messaggio_id INTEGER NOT NULL,
    utente_id INTEGER NOT NULL,
    data_visualizzazione TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (messaggio_id) REFERENCES ticker_messaggi(id)
);

CREATE INDEX IF NOT EXISTS idx_ticker_log_msg ON ticker_log(messaggio_id);
CREATE INDEX IF NOT EXISTS idx_ticker_log_data ON ticker_log(data_visualizzazione);
```

---

## 6. ARCHITETTURA FILE

```
app/
    config_ticker.py              # Configurazione (legge ticker_config)
    motore_ticker.py              # Logica: selezione, scheduling, random, auto-gen
    routes_ticker.py              # Blueprint: API + pagina gestione

templates/
    componenti/
        _topbar.html              # Widget ticker (gia' deployato, da aggiornare)
    ticker/
        gestione.html             # Pagina principale gestione
        _griglia.html             # Griglia messaggi con filtri
        _modal_nuovo.html         # Modal creazione/modifica messaggio
        _preview.html             # Preview animazione live
        _scripts.html             # JavaScript
        _styles.html              # CSS

scripts/
    ticker_auto_gen.py            # Cron job generazione messaggi automatici
```

---

## 7. API

### 7.1 API per il widget topbar (polling)

```
GET /ticker/api/prossimo
```
Restituisce il prossimo messaggio da mostrare (o vuoto).
Il frontend chiama questa API a intervalli random.

Risposta:
```json
{
    "success": true,
    "messaggio": {
        "id": 42,
        "testo": "Buon compleanno Marco!",
        "icona": "balloon-heart",
        "colore_testo": "#000000",
        "animazione": "slide-up",
        "durata_secondi": 8
    },
    "prossimo_check_sec": 180
}
```

Se non c'e' nessun messaggio da mostrare:
```json
{
    "success": true,
    "messaggio": null,
    "prossimo_check_sec": 120
}
```

Il campo `prossimo_check_sec` e' calcolato dal backend in base
alla configurazione messaggi/ora + un fattore random.

### 7.2 API gestione (pagina admin)

```
GET    /ticker/api/lista              # Lista messaggi con filtri
POST   /ticker/api/crea               # Crea nuovo messaggio
POST   /ticker/api/<id>/modifica      # Modifica messaggio
POST   /ticker/api/<id>/elimina       # Elimina messaggio
POST   /ticker/api/<id>/approva       # Approva messaggio (admin)
POST   /ticker/api/<id>/rifiuta       # Rifiuta messaggio (admin)
GET    /ticker/api/config             # Leggi configurazione
POST   /ticker/api/config             # Salva configurazione (admin)
GET    /ticker/api/preview/<id>       # Dati per preview
POST   /ticker/api/genera-automatici  # Forza generazione auto (admin)
GET    /ticker/api/statistiche        # Stats visualizzazioni
```

---

## 8. PAGINA GESTIONE TICKER

### 8.1 Accesso
- Link in sidebar: sezione "Amministrazione" (visibile a tutti)
- Tasto prominente in alto nella pagina Gestione Sistema
- URL: `/ticker/gestione`

### 8.2 Layout pagina

```
+------------------------------------------------------------------+
|  [+ Nuovo Messaggio]                    [Configurazione (admin)]  |
+------------------------------------------------------------------+
|                                                                    |
|  === PREVIEW LIVE ===============================================  |
|  |                                                              |  |
|  |  [area preview - simula il ticker con il messaggio]          |  |
|  |                                                              |  |
|  ================================================================  |
|                                                                    |
|  FILTRI: [Stato v] [Tipo v] [Destinatari v] [Cerca...]           |
|                                                                    |
|  === GRIGLIA MESSAGGI ==========================================  |
|  | Testo | Animazione | Dal-Al | Priorita' | Stato | Azioni |   |
|  |-------|------------|--------|-----------|-------|---------|    |
|  | Buon..| slide-up   | 18-25/12| 8       | OK    | [E][D]  |   |
|  | Cambio| scroll-rtl | 15/10..| 5        | Attesa| [E][D]  |   |
|  ================================================================  |
+------------------------------------------------------------------+
```

### 8.3 Modal Nuovo/Modifica Messaggio

```
+------------------------------------------+
|  Nuovo Messaggio Ticker                   |
+------------------------------------------+
|                                           |
|  Testo: [________________________________]|
|  Icona: [dropdown icone bi-*            ] |
|  Colore testo: [color picker            ] |
|                                           |
|  --- Animazione ---                       |
|  Tipo: [scroll-rtl v]                     |
|  Durata (sec): [8]                        |
|  Velocita': [normale v]                   |
|                                           |
|  --- Scheduling ---                       |
|  Da: [data] Al: [data]                    |
|  Orario: dalle [HH:MM] alle [HH:MM]      |
|  Giorni: [x]L [x]Ma [x]Me [x]G [x]V []S []D |
|  Ricorrenza: [nessuna v]                  |
|                                           |
|  --- Destinatari ---                      |
|  [TUTTI v] / [RUOLO:xxx] / [UTENTE:xxx]  |
|                                           |
|  --- Priorita' ---                        |
|  Importanza: [====5====] (1-10)           |
|  Peso random: [1]                         |
|                                           |
|  [Preview]            [Salva] [Annulla]   |
+------------------------------------------+
```

### 8.4 Preview Live
Area che simula esattamente il ticker della topbar:
- Stesse dimensioni (altezza 50px, sfondo trasparente)
- Stessa animazione selezionata
- Aggiornamento in tempo reale mentre si compila il form
- Pulsante "Play" per rivedere l'animazione

---

## 9. LOGICA SELEZIONE MESSAGGIO

### Algoritmo `get_prossimo_messaggio(user_id)`

```python
1. Filtra messaggi con stato = 'approvato'
2. Filtra per data odierna tra data_inizio e data_fine
3. Filtra per ora corrente tra ora_inizio e ora_fine
4. Filtra per giorno settimana corrente
5. Filtra per destinatari (TUTTI, ruolo utente, UTENTE:id)
6. Ordina per priorita' (decrescente)
7. Applica peso random (weighted random selection)
8. Verifica rate limit (messaggi/ora non superato)
9. Restituisci messaggio selezionato (o None)
```

### Rate limiting
- Il backend tiene traccia dei messaggi mostrati via `ticker_log`
- Se il limite messaggi/ora e' raggiunto, restituisce `null`
- Il frontend riceve `prossimo_check_sec` calcolato dal backend

### Comportamento frontend
```
1. Pagina caricata
2. Attendi pausa random iniziale (30-120 sec)
3. Chiedi al backend: GET /ticker/api/prossimo
4. Se messaggio:
   a. Mostra con animazione appropriata
   b. Attendi durata_secondi
   c. Nascondi con animazione uscita
5. Attendi prossimo_check_sec (dal backend)
6. Torna al punto 3
```

---

## 10. WORKFLOW APPROVAZIONE

```
Utente crea messaggio -> stato: 'bozza'
Utente invia per approvazione -> stato: 'in_attesa'
Admin approva -> stato: 'approvato' (visibile nel ticker)
Admin rifiuta -> stato: 'rifiutato' (con nota motivazione)

Admin crea messaggio -> stato: 'approvato' (diretto, no approvazione)

Messaggi automatici -> stato: 'approvato' (generati gia' approvati)

Data_fine superata -> stato: 'scaduto' (automatico da cron/query)
```

---

## 11. MESSAGGI AUTOMATICI (cron job)

### Script `ticker_auto_gen.py`
Da eseguire ogni giorno alle 00:05 via crontab.

```python
# Compleanni
- Legge utenti.data_nascita
- Per ogni compleanno del giorno, genera messaggio
- Codice dedup: compleanno_YYYY_<utente_id>
- Testo: "Auguri di buon compleanno a [Nome Cognome]! 🎂"
- Destinatari: TUTTI
- Animazione: slide-up
- Priorita': 8

# Festivita' (da config Excel o hardcoded)
- Natale: 18-25 Dicembre
- Capodanno: 1-3 Gennaio
- Pasqua: calcolata
- Cambio gomme invernali: 15 Ott - 15 Nov
- Cambio gomme estive: 15 Mar - 15 Apr
```

### Crontab
```
5 0 * * * cd /home/michele/gestione_flotta && python3 scripts/ticker_auto_gen.py >> logs/ticker_auto.log 2>&1
```

---

## 12. INTEGRAZIONE SIDEBAR

Nella sezione "Amministrazione" di `base.html` aggiungere:
```html
<a href="/ticker/gestione" class="nav-link" data-tooltip="Ticker">
    <i class="bi bi-megaphone"></i> <span>Ticker</span>
</a>
```

In alternativa (o in aggiunta), bottone prominente nella pagina admin:
```html
<a href="/ticker/gestione" class="btn btn-outline-primary">
    <i class="bi bi-megaphone"></i> Gestione Ticker
</a>
```

---

## 13. FASI DI IMPLEMENTAZIONE

### Fase 1 - Backend + DB
1. Script migrazione DB (3 tabelle + config default)
2. `config_ticker.py` - Lettura configurazione
3. `motore_ticker.py` - Logica selezione + scheduling
4. `routes_ticker.py` - Blueprint con API base

### Fase 2 - Frontend widget (aggiorna _topbar.html)
1. Polling con intervallo variabile dal backend
2. 5 animazioni (scroll-rtl, scroll-ltr, slide-up, slide-down, fade)
3. Animazione uscita + pausa tra messaggi
4. Rispetto destinatari

### Fase 3 - Pagina gestione
1. Template principale + satellite
2. Griglia messaggi con filtri
3. Modal creazione/modifica
4. Preview live con tutte le animazioni
5. Workflow approvazione (in_attesa/approvato/rifiutato)

### Fase 4 - Messaggi automatici
1. Script `ticker_auto_gen.py`
2. Compleanni da `utenti.data_nascita`
3. Festivita' configurabili
4. Crontab setup

### Fase 5 - Configurazione admin
1. Pannello config (messaggi/ora, pause, toggle auto)
2. Statistiche visualizzazioni
3. Link sidebar

---

## 14. NOTE TECNICHE

- Il ticker e' gia' deployato in `templates/componenti/_topbar.html`
  e incluso in `base.html`. La Fase 2 lo aggiornera' per supportare
  le 5 animazioni e il polling dal backend.

- I messaggi automatici usano `codice_auto` per deduplicazione:
  il cron non crea duplicati se eseguito piu' volte.

- La preview nella pagina gestione usa lo STESSO CSS/JS del ticker
  reale, importato come include, cosi' l'effetto e' identico.

- Admin bypassa l'approvazione: i suoi messaggi vanno direttamente
  in stato 'approvato'.

- L'encoding usa entity HTML come da regole progetto.

---

## STATO IMPLEMENTAZIONE

### Fase 1 - Backend + DB [COMPLETATA]
- Script migrazione: `scripts/migrazione_ticker.py`
- Configurazione: `app/config_ticker.py`
- Motore selezione: `app/motore_ticker.py`
- Routes API: `app/routes_ticker.py` (13 endpoint)
- Blueprint `ticker_bp` registrato in `web_server.py`

### Fase 2 - Widget Topbar [COMPLETATA]
- Widget: `templates/componenti/_topbar.html` v2.0
- Polling con intervallo variabile dal backend
- 5 animazioni: scroll-rtl, scroll-ltr, slide-up, slide-down, fade
- 3 velocita: lenta, normale, veloce
- Pausa random iniziale (10-60 sec)
- Registrazione visualizzazioni via POST /ticker/api/visto

### Fase 3 - Pagina Gestione [COMPLETATA]
- Architettura satellite (6 file):
  - `templates/ticker/gestione.html` (coordinatore)
  - `templates/ticker/_styles.html`
  - `templates/ticker/_preview.html`
  - `templates/ticker/_griglia.html`
  - `templates/ticker/_modal_nuovo.html`
  - `templates/ticker/_scripts.html`
- Griglia messaggi con filtri (stato, tipo, cerca, destinatari)
- Modal creazione/modifica con preview live
- Configurazione admin (messaggi/ora, pause, toggle auto)
- Accesso: pulsante in pagina /admin (non in sidebar)
- Ticker nascosto nella pagina /admin

### Fase 4 - Messaggi Automatici [COMPLETATA]

**File implementati:**
- `scripts/migrazione_ticker_fase4.py` - Crea tabella festivita, 10 feste italiane
- `app/ticker_auto_gen.py` - Generatore automatico con 4 moduli
- Cron: `5 0 * * * cd ~/gestione_flotta && python3 app/ticker_auto_gen.py`

**Generatori:**
- Compleanni: reminder -5/-1 giorni, auguri giorno stesso (skip weekend/festivita)
- Festivita: reminder -7/-5 giorni, 10 fisse + Pasqua/Pasquetta
- Cambio gomme: 15/10 invernali, 15/4 estive, reminder -30 giorni
- Deposito bilancio: 30/05, reminder -30 giorni

**Miglioramenti aggiuntivi:**
- Toggle automatici in riga sulla pagina (non nel modal)
- Config font: dimensione (4 livelli) e stile (6 opzioni)
- Griglia semplificata senza filtri, colonna Tipo aggiunta
- Fix autenticazione ruolo_base, fix nomi colonne DB
- Script cron `ticker_auto_gen.py`
- Compleanni da utenti.data_nascita
- Festivita configurabili
- Cambio gomme stagionale

### Fase 5 - Statistiche [ELIMINATA]
- Ritenuta non necessaria: messaggi broadcast a tutti

### Correzioni Applicate
- Fix `ruolo_base` (sessione usa ruolo_base, non ruolo)
- Link sidebar rimosso, accesso solo da /admin
