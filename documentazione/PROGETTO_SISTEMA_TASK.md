# PROGETTO - SISTEMA TASK INTERNI
## Dashboard Interattiva di Comunicazione Lavori

**Data**: 04 Febbraio 2026
**Versione**: 1.0 (Documento di progetto)
**Stato**: DA APPROVARE
**Priorita'**: ALTA

---

## 1. OBIETTIVO

Creare un sistema di task/ticket interni che permetta ai colleghi di comunicare
richieste di lavoro in modo tracciato e misurabile. La dashboard diventa il
centro operativo dove commerciali e backoffice si scambiano richieste,
con tracking automatico dei tempi di presa in carico e svolgimento.

---

## 2. FLUSSO OPERATIVO

```
COMMERCIALE                         BACKOFFICE
    |                                   |
    |  1. Crea task (es. quotazione)    |
    |  --------- [NUOVO] ----------->   |
    |                                   |
    |  2. Task in coda (counter rosso)  |
    |                                   |
    |             <-- [PRESO IN CARICO] |  3. Primo libero prende in carico
    |                                   |     (timer lavorazione parte)
    |  4. Vede: chi, quando,            |
    |     stato "In lavorazione"        |
    |                                   |
    |             <-- [COMPLETATO] ---- |  5. Backoffice completa
    |                                   |     (timer si ferma)
    |  6. Vede risultato + file         |
    |     Puo' chiudere il task         |
    |                                   |
    |  7. Task va in archivio           |
    |     raggruppato per tipologia     |
```

### 2.1 Timer e Metriche

| Metrica | Cosa misura | Calcolata su |
|---------|-------------|--------------|
| **Tempo attesa** | Da creazione a presa in carico | Solo orario lavorativo |
| **Tempo lavorazione** | Da presa in carico a completamento | Solo orario lavorativo |
| **Tempo totale** | Da creazione a completamento | Solo orario lavorativo |

I tempi vengono calcolati **escludendo** ore fuori orario, weekend e festivita'
(configurabili in `impostazioni/orario_lavoro.conf`).

---

## 3. TIPOLOGIE TASK (v1.0)

Configurate in `impostazioni/tipologie_task.xlsx` — ampliabili senza toccare codice.

| Codice | Etichetta | Icona | Colore | Descrizione |
|--------|-----------|-------|--------|-------------|
| QUOTAZIONE | Richiesta Quotazione | bi-calculator | #0d6efd | Richiesta preventivo al backoffice |
| RICALCOLO | Ricalcolo | bi-arrow-repeat | #fd7e14 | Ricalcolo canone/condizioni |
| INFO_CONSEGNA | Info Consegna | bi-truck | #198754 | Informazioni su tempi/stato consegna |
| VARIA | Richiesta Varia | bi-chat-dots | #6c757d | Richiesta generica |

**Ampliamento futuro**: basta aggiungere righe al file Excel, il sistema le legge automaticamente.

---

## 4. STATI DEL TASK

Configurati in `impostazioni/stati_task.xlsx`.

| Codice | Etichetta | Colore | Fase |
|--------|-----------|--------|------|
| NUOVO | Nuovo | #dc3545 (rosso) | attivo |
| PRESO_IN_CARICO | Preso in carico | #fd7e14 (arancio) | attivo |
| IN_LAVORAZIONE | In lavorazione | #0d6efd (blu) | attivo |
| IN_ATTESA | In attesa | #6c757d (grigio) | attivo |
| COMPLETATO | Completato | #198754 (verde) | chiuso |
| ANNULLATO | Annullato | #6c757d (grigio) | chiuso |

### 4.1 Transizioni consentite

```
NUOVO ---> PRESO_IN_CARICO ---> IN_LAVORAZIONE ---> COMPLETATO
  |              |                     |
  |              +---> IN_ATTESA ------+
  |                    (es. manca info)
  +---> ANNULLATO (dal creatore o admin)
```

---

## 5. DATABASE

### 5.1 Tabella `task` (principale)

```sql
CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identificazione
    codice TEXT UNIQUE NOT NULL,          -- es. TASK-20260204-001
    tipologia TEXT NOT NULL,              -- codice da tipologie_task.xlsx
    
    -- Chi
    creato_da_id INTEGER NOT NULL,        -- FK utenti.id (commerciale)
    assegnato_a_id INTEGER,               -- FK utenti.id (chi prende in carico)
    cliente_id INTEGER,                   -- FK clienti.id (cliente di riferimento)
    
    -- Contenuto
    oggetto TEXT NOT NULL,                -- titolo breve
    descrizione TEXT,                     -- dettagli richiesta
    priorita INTEGER DEFAULT 1,          -- 0=bassa, 1=normale, 2=urgente
    
    -- Stato
    stato TEXT DEFAULT 'NUOVO',           -- codice da stati_task.xlsx
    
    -- Timestamp
    data_creazione TEXT NOT NULL,          -- ISO 8601
    data_presa_in_carico TEXT,            -- quando qualcuno lo prende
    data_completamento TEXT,              -- quando viene completato
    data_annullamento TEXT,               -- se annullato
    
    -- Tempi calcolati (in MINUTI, solo orario lavorativo)
    minuti_attesa INTEGER,                -- da creazione a presa in carico
    minuti_lavorazione INTEGER,           -- da presa in carico a completamento
    minuti_totale INTEGER,                -- da creazione a completamento
    
    -- Risultato
    nota_completamento TEXT,              -- nota di chi completa il task
    
    -- Audit
    data_modifica TEXT,
    modificato_da_id INTEGER,
    
    FOREIGN KEY (creato_da_id) REFERENCES utenti(id),
    FOREIGN KEY (assegnato_a_id) REFERENCES utenti(id),
    FOREIGN KEY (cliente_id) REFERENCES clienti(id)
);

-- Indici
CREATE INDEX IF NOT EXISTS idx_task_stato ON task(stato);
CREATE INDEX IF NOT EXISTS idx_task_tipologia ON task(tipologia);
CREATE INDEX IF NOT EXISTS idx_task_creato_da ON task(creato_da_id);
CREATE INDEX IF NOT EXISTS idx_task_assegnato_a ON task(assegnato_a_id);
CREATE INDEX IF NOT EXISTS idx_task_cliente ON task(cliente_id);
CREATE INDEX IF NOT EXISTS idx_task_data_creazione ON task(data_creazione);
```

### 5.2 Tabella `task_allegati` (file collegati)

```sql
CREATE TABLE IF NOT EXISTS task_allegati (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    
    -- Tipo allegato
    tipo TEXT NOT NULL,                   -- 'link' = file esistente, 'upload' = nuovo file
    
    -- Per tipo 'link': riferimento a file esistente
    percorso_originale TEXT,              -- path nel filesystem clienti
    
    -- Per tipo 'upload': file caricato col task
    nome_file TEXT,                       -- nome originale
    percorso_file TEXT,                   -- path nel filesystem task
    dimensione INTEGER,                   -- bytes
    
    -- Ricollocazione
    ricollocato INTEGER DEFAULT 0,        -- 0=no, 1=si
    percorso_destinazione TEXT,           -- dove e' stato spostato
    data_ricollocazione TEXT,
    ricollocato_da_id INTEGER,
    
    -- Meta
    caricato_da_id INTEGER NOT NULL,
    data_caricamento TEXT NOT NULL,
    nota TEXT,                            -- descrizione allegato
    fase TEXT DEFAULT 'richiesta',        -- richiesta / lavorazione / completamento
    
    FOREIGN KEY (task_id) REFERENCES task(id),
    FOREIGN KEY (caricato_da_id) REFERENCES utenti(id)
);

CREATE INDEX IF NOT EXISTS idx_task_allegati_task ON task_allegati(task_id);
```

### 5.3 Tabella `task_log` (storico cambi stato)

```sql
CREATE TABLE IF NOT EXISTS task_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    
    azione TEXT NOT NULL,                 -- 'creazione', 'presa_in_carico', 'stato', 'nota', 'allegato', 'completamento'
    stato_precedente TEXT,
    stato_nuovo TEXT,
    
    utente_id INTEGER NOT NULL,
    data_ora TEXT NOT NULL,
    dettaglio TEXT,                        -- nota opzionale
    
    FOREIGN KEY (task_id) REFERENCES task(id),
    FOREIGN KEY (utente_id) REFERENCES utenti(id)
);

CREATE INDEX IF NOT EXISTS idx_task_log_task ON task_log(task_id);
```

---

## 6. FILE DI CONFIGURAZIONE

### 6.1 `impostazioni/orario_lavoro.conf`

```conf
# ==============================================================================
# ORARIO LAVORATIVO - Per calcolo tempi task
# ==============================================================================

# Orario standard
ORA_INIZIO=08:30
ORA_FINE=18:00

# Pausa pranzo (esclusa dal conteggio)
PAUSA_INIZIO=12:30
PAUSA_FINE=14:00

# Giorni lavorativi (1=Lunedi ... 7=Domenica)
GIORNI_LAVORATIVI=1,2,3,4,5

# Festivita' fisse (formato MM-DD)
FESTIVITA_FISSE=01-01,01-06,04-25,05-01,06-02,08-15,11-01,12-08,12-25,12-26

# Festivita' variabili 2026 (aggiornare annualmente)
FESTIVITA_VARIABILI=2026-04-06,2026-04-07
```

### 6.2 `impostazioni/tipologie_task.xlsx`

| Codice | Etichetta | Icona | Colore | Descrizione | Attivo | Ordine |
|--------|-----------|-------|--------|-------------|--------|--------|
| QUOTAZIONE | Richiesta Quotazione | bi-calculator | #0d6efd | Richiesta preventivo | si | 1 |
| RICALCOLO | Ricalcolo | bi-arrow-repeat | #fd7e14 | Ricalcolo canone | si | 2 |
| INFO_CONSEGNA | Info Consegna | bi-truck | #198754 | Info tempi consegna | si | 3 |
| VARIA | Richiesta Varia | bi-chat-dots | #6c757d | Richiesta generica | si | 99 |

### 6.3 `impostazioni/stati_task.xlsx`

| Codice | Etichetta | Colore | Icona | Fase | Ordine |
|--------|-----------|--------|-------|------|--------|
| NUOVO | Nuovo | #dc3545 | bi-exclamation-circle | attivo | 1 |
| PRESO_IN_CARICO | Preso in carico | #fd7e14 | bi-person-check | attivo | 2 |
| IN_LAVORAZIONE | In lavorazione | #0d6efd | bi-gear | attivo | 3 |
| IN_ATTESA | In attesa | #6c757d | bi-pause-circle | attivo | 4 |
| COMPLETATO | Completato | #198754 | bi-check-circle | chiuso | 5 |
| ANNULLATO | Annullato | #6c757d | bi-x-circle | chiuso | 6 |

---

## 7. STRUTTURA FILE (Modularita' Estrema)

```
gestione_flotta/
  app/
    config_task.py                    # Lettura Excel + conf orario
    motore_task.py                    # Logica business (tempi, stati, codici)
    routes_task.py                    # Blueprint API + pagine
  templates/
    task/
      _header.html                   # Titolo + counter task attivi
      _griglia_attivi.html           # Task da fare / in lavorazione
      _griglia_completati.html       # Archivio task chiusi per tipologia
      _modal_nuovo.html              # Creazione nuovo task
      _modal_dettaglio.html          # Dettaglio task (stato, file, tempi)
      _modal_allegati.html           # Gestione allegati (link + upload + ricollocazione)
      _scripts.html                  # JS dedicato
      _scripts_modal_nuovo.html      # JS modal creazione
      _scripts_modal_dettaglio.html  # JS modal dettaglio
      _scripts_allegati.html         # JS gestione file
      _styles.html                   # CSS dedicato
    task.html                        # Pagina principale (include satellite)
  impostazioni/
    orario_lavoro.conf               # Orario lavorativo
    tipologie_task.xlsx              # Tipologie task
    stati_task.xlsx                  # Stati task
  task_allegati/                     # File caricati con i task
    {anno}/
      {mese}/
        {codice_task}/
          richiesta/                 # Allegati fase richiesta
          lavorazione/               # Allegati fase lavorazione
          completamento/             # Allegati fase completamento
```

---

## 8. SISTEMA ALLEGATI

### 8.1 Due modalita'

| Tipo | Descrizione | Uso tipico |
|------|-------------|------------|
| **Link** | Riferimento a file gia' presente nelle cartelle cliente | "Guarda il contratto in cartella" |
| **Upload** | Nuovo file caricato direttamente nel task | "Ecco il foglio con i dati" |

### 8.2 Browser file cliente

Nella modal allegati, un **file browser** mostra le cartelle del cliente collegato:

```
Cliente: ATIB SRL (IT01234567890)
  allegati_note/
  car_policy/
    car_policy_2025.pdf        [Collega]
  contratti/
    contratto_arval_2024.pdf   [Collega]
  quotazioni/
    ...
  trascrizioni/
    ...
```

Il pulsante **[Collega]** crea un record `task_allegati` con `tipo='link'` e
`percorso_originale` che punta al file nel filesystem cliente.

### 8.3 Ricollocazione file

A lavoro finito (o durante), i file caricati nel task possono essere
**ricollocati** nelle cartelle standard del cliente:

```
File: quotazione_arval_10veicoli.pdf
  Attualmente in: task_allegati/2026/02/TASK-20260204-001/completamento/
  Ricollocare in: [dropdown cartelle cliente]
    -> quotazioni/
    -> contratti/
    -> allegati_note/
  [Ricollocare]  [Copia (mantieni anche nel task)]
```

Operazioni:
- **Ricollocare**: sposta il file nella cartella cliente, segna `ricollocato=1`
- **Copia**: copia nella cartella cliente, file rimane anche nel task

---

## 9. DASHBOARD TASK

### 9.1 Vista Commerciale

```
+------------------------------------------+
| DASHBOARD TASK                           |
+------------------------------------------+
| I MIEI TASK APERTI          [+ Nuovo]    |
| +--------------------------------------+ |
| | [!] Quotazione ATIB - Arval 10 veic. | |
| |     Stato: In lavorazione (M. Perani)| |
| |     Creato: 04/02 09:30              | |
| |     Preso: 04/02 09:45 (15 min att.) | |
| +--------------------------------------+ |
| | [!] Info consegna ROSSI SRL          | |
| |     Stato: NUOVO (in attesa)         | |
| |     Creato: 04/02 10:15              | |
| +--------------------------------------+ |
|                                          |
| TASK COMPLETATI RECENTI                  |
| +--------------------------------------+ |
| | Quotazione BIANCHI - Leasys          | |
| |  Completato: 03/02 (2h 15min)       | |
| +--------------------------------------+ |
+------------------------------------------+
```

### 9.2 Vista Backoffice/Operatore

```
+------------------------------------------+
| DASHBOARD TASK                           |
+------------------------------------------+
| TASK DA PRENDERE IN CARICO    (3)  <--- counter rosso
| +--------------------------------------+ |
| | [!] Quotazione ATIB - P. Ciotti     | |
| |     Priorita': URGENTE              | |
| |     In attesa da: 15 min            | |
| |     [PRENDI IN CARICO]              | |
| +--------------------------------------+ |
|                                          |
| I MIEI TASK IN LAVORAZIONE    (1)       |
| +--------------------------------------+ |
| | Ricalcolo VERDI SRL - F. Zubani     | |
| |  In lavorazione da: 45 min          | |
| |  [Apri] [Completa]                  | |
| +--------------------------------------+ |
|                                          |
| COMPLETATI OGGI: 5                       |
+------------------------------------------+
```

### 9.3 Vista Admin

Vede tutto + statistiche tempi:
- Tempo medio attesa per tipologia
- Tempo medio lavorazione per operatore
- Task in ritardo (attesa > soglia configurabile)
- Classifica operatori per velocita'/volume

---

## 10. PERMESSI

Nuovi permessi da aggiungere al catalogo:

| Codice | Categoria | Descrizione |
|--------|-----------|-------------|
| task_crea | task | Puo' creare nuovi task |
| task_prendi | task | Puo' prendere in carico task |
| task_completa | task | Puo' completare task presi in carico |
| task_visualizza_tutti | task | Vede tutti i task (non solo propri) |
| task_statistiche | task | Vede tempi e statistiche |
| task_annulla | task | Puo' annullare task di altri |

### Default per ruolo

| Ruolo | crea | prendi | completa | visualizza_tutti | statistiche | annulla |
|-------|------|--------|----------|-----------------|-------------|---------|
| Admin | si | si | si | si | si | si |
| Commerciale | si | no | no | no | no | no |
| Operatore | si | si | si | no | no | no |
| Viewer | no | no | no | no | no | no |

**Nota**: Il commerciale vede solo i PROPRI task (creati da lui).
L'operatore vede i task da prendere in carico + i propri in lavorazione.
L'admin vede tutto.

---

## 11. API / ROUTE

### Blueprint: `routes_task.py`

| Metodo | Route | Descrizione |
|--------|-------|-------------|
| GET | `/task` | Pagina dashboard task |
| GET | `/api/task/attivi` | Task attivi (filtrati per ruolo) |
| GET | `/api/task/completati` | Task completati (paginati, per tipologia) |
| GET | `/api/task/<id>` | Dettaglio singolo task |
| POST | `/api/task/nuovo` | Crea nuovo task |
| POST | `/api/task/<id>/prendi` | Prendi in carico |
| POST | `/api/task/<id>/stato` | Cambia stato |
| POST | `/api/task/<id>/completa` | Completa task |
| POST | `/api/task/<id>/annulla` | Annulla task |
| GET | `/api/task/<id>/allegati` | Lista allegati |
| POST | `/api/task/<id>/allegati/upload` | Upload file |
| POST | `/api/task/<id>/allegati/link` | Collega file esistente |
| POST | `/api/task/allegati/<id>/ricollocare` | Ricollocare file in cartella cliente |
| GET | `/api/task/<id>/log` | Storico cambi stato |
| GET | `/api/task/statistiche` | Statistiche tempi (solo admin) |
| GET | `/api/task/counter` | Counter badge per navbar |
| GET | `/api/cliente/<id>/cartelle` | Browser cartelle cliente per link allegati |

---

## 12. CODICE TASK UNIVOCO

Formato: `TASK-YYYYMMDD-NNN`

```python
def genera_codice_task(conn):
    """Genera codice univoco per nuovo task."""
    oggi = datetime.now().strftime('%Y%m%d')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM task WHERE codice LIKE ?",
        (f'TASK-{oggi}-%',)
    )
    progressivo = cursor.fetchone()[0] + 1
    return f"TASK-{oggi}-{progressivo:03d}"
```

---

## 13. CALCOLO TEMPI LAVORATIVI

### Logica `motore_task.py`

```python
def calcola_minuti_lavorativi(data_inizio, data_fine, config_orario):
    """
    Calcola i minuti lavorativi tra due datetime.
    
    Esclude:
    - Ore fuori orario (prima di ORA_INIZIO, dopo ORA_FINE)
    - Pausa pranzo (PAUSA_INIZIO - PAUSA_FINE)
    - Weekend (giorni non in GIORNI_LAVORATIVI)
    - Festivita' (FESTIVITA_FISSE + FESTIVITA_VARIABILI)
    
    Returns:
        int: minuti lavorativi netti
    """
```

### Esempio

Task creato: Venerdi' 14:00
Task preso in carico: Lunedi' 09:30

Calcolo:
- Venerdi' 14:00 -> 18:00 = 4h (240 min, meno pausa se c'e')
- Sabato + Domenica = 0
- Lunedi' 08:30 -> 09:30 = 1h (60 min)
- **Totale attesa: ~270 minuti lavorativi** (non 63 ore solari!)

---

## 14. NAVBAR - COUNTER BADGE

Nella sidebar/navbar, aggiungere un badge con counter:

```html
<!-- Per operatori: task da prendere in carico -->
<a href="/task">
    <i class="bi bi-clipboard-check"></i> Task
    <span class="badge bg-danger" id="task-counter">3</span>
</a>
```

Il counter si aggiorna via polling AJAX ogni 30 secondi
(route `/api/task/counter`).

---

## 15. FASI DI IMPLEMENTAZIONE

### Fase 1 - Base (Backend + DB)
1. File configurazione (`orario_lavoro.conf`, `tipologie_task.xlsx`, `stati_task.xlsx`)
2. Modulo `config_task.py` (lettura config)
3. Modulo `motore_task.py` (logica business + calcolo tempi)
4. Migrazione DB (tabelle task, task_allegati, task_log)
5. Permessi nel catalogo
6. Test unitari calcolo tempi

### Fase 2 - API (Blueprint)
1. `routes_task.py` con tutte le route
2. CRUD task completo
3. Sistema presa in carico
4. Cambio stati con log
5. Counter per navbar

### Fase 3 - Frontend (Template)
1. Pagina `/task` con layout dashboard
2. Griglia task attivi (creati da me / da prendere)
3. Modal creazione nuovo task
4. Modal dettaglio task
5. Counter badge in navbar

### Fase 4 - Allegati
1. Upload file nel task
2. Browser cartelle cliente per link
3. Ricollocazione file
4. Integrazione nella modal dettaglio

### Fase 5 - Archivio e Statistiche
1. Sezione task completati raggruppati per tipologia
2. Statistiche tempi per admin
3. Filtri e ricerca nell'archivio

---

## 16. NOTE ARCHITETTURALI

### Coerenza con il progetto
- Pattern identico a trattative e top_prospect
- Config da Excel come `config_trattative.py`
- Orario da .conf come `config_trascrizione.py`
- Blueprint separato come tutti gli altri moduli
- Template modulari con file satellite
- Permessi nel catalogo esistente

### Scalabilita'
- Nuove tipologie: basta aggiungere riga in Excel
- Nuovi stati: basta aggiungere riga in Excel
- Nuove viste: basta aggiungere template satellite
- Nuove metriche: basta estendere `motore_task.py`
- Notifiche future: il `task_log` e' gia' pronto per alimentare il sistema notifiche (quando verra' implementato)

### Cosa NON fa questa v1.0
- Notifiche push/email (backlog separato)
- Chat/commenti nel task (possibile estensione futura)
- Assegnazione a persona specifica (per ora: primo libero prende)
- SLA configurabili per tipologia (possibile v2.0)
- Sotto-task / checklist (possibile v2.0)

---

## 17. SOSTITUZIONE NEL TODO

Nel file TODO.md, la voce:
```
- [ ] Dashboard unificata con KPI principali
```
Va sostituita con:
```
- [ ] Sistema Task Interni (dashboard comunicazione lavori)
```
