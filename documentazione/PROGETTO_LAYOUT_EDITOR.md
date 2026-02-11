# PROGETTO: Layout Editor Pagina Dettaglio Cliente

**Data**: 2026-02-10
**Versione**: 1.0
**Stato**: PROGETTO - In attesa approvazione
**Pagina target**: `templates/dettaglio.html`
**Accessibile da**: Gestione Sistema > Layout Pagine

---

## 1. OBIETTIVO

Creare un sistema visuale per riposizionare, ridimensionare e nascondere/mostrare
i "quadri" (card) della pagina dettaglio cliente, con un editor drag &amp; drop
accessibile dal menu Gestione Sistema. Il layout e' GLOBALE (uguale per tutti).

---

## 2. MAPPA QUADRI ATTUALI

Dall'analisi di `dettaglio.html` ho identificato tutti i quadri presenti.
L'header cliente (nome, badge, pulsanti azione) resta SEMPRE FISSO in alto
e NON partecipa al layout editor.

### 2.1 Colonna Sinistra (col-lg-8)

| # | ID Quadro | Nome | Tipo | Include satellite |
|---|-----------|------|------|-------------------|
| 1 | `dati_aziendali` | Dati Aziendali | INLINE | NO - da estrarre |
| 2 | `descrizione` | Descrizione (ATECO, SAE, RAE) | INLINE | NO - da estrarre |
| 3 | `capogruppo` | Capogruppo | INLINE (col-md-6) | NO - da estrarre |
| 4 | `collegamenti` | Collegamenti | INCLUDE (col-md-6) | SI: `dettaglio/collegamenti/_riquadro.html` |
| 5 | `contatti` | Contatti Generali | INLINE | NO - da estrarre |
| 6 | `noleggiatori` | Noleggiatori | INCLUDE | SI: `componenti/noleggiatori/_riquadro.html` |
| 7 | `documenti` | Documenti Cliente | INCLUDE | SI: `documenti_cliente.html` (coordinatore) |
| 8 | `referenti` | Referenti | INLINE (full-width) | NO - da estrarre |
| 9 | `veicoli` | Veicoli per Noleggiatore | INLINE (full-width) | NO - da estrarre |
| 10 | `consensi_crm` | Consensi CRM | INLINE | NO - da estrarre |
| 11 | `storico` | Storico Modifiche | INLINE | NO - da estrarre |

### 2.2 Colonna Destra (col-lg-4)

| # | ID Quadro | Nome | Tipo | Include satellite |
|---|-----------|------|------|-------------------|
| 12 | `crm` | Dati CRM Zoho | INCLUDE | SI: `componenti/crm/_riquadro.html` |
| 13 | `rating` | Rating / Score | INLINE | NO - da estrarre |
| 14 | `fido` | Fido Consigliato | INLINE | NO - da estrarre |
| 15 | `finanziari` | Dati Finanziari (Bilancio) | INLINE | NO - da estrarre |
| 16 | `commerciale` | Commerciale Assegnato | INLINE | NO - da estrarre |
| 17 | `top_prospect` | Info Top Prospect | INLINE (condizionale) | NO - da estrarre |
| 18 | `veicoli_rilevati` | Veicoli Rilevati | INLINE | NO - da estrarre |
| 19 | `info` | Info (date report) | INLINE | NO - da estrarre |

### 2.3 Riepilogo

- **Totale quadri**: 19
- **Gia' satellite (include)**: 4 (collegamenti, noleggiatori, documenti, crm)
- **Da estrarre in satellite**: 15
- **Quadri condizionali**: top_prospect (visibile solo se presente), consensi_crm

---

## 3. ARCHITETTURA TECNICA

### 3.1 Libreria Frontend: gridstack.js

**Perche' gridstack.js:**
- Leggera (~35kb minificata), zero dipendenze
- Drag &amp; drop nativo + resize
- Griglia a 12 colonne (perfetta con Bootstrap)
- Salva/carica layout come JSON
- CDN disponibile: `https://cdnjs.cloudflare.com/ajax/libs/gridstack.js/10.3.1/`
- Licenza MIT

**Come funziona:**
```html
<div class="grid-stack">
    <div class="grid-stack-item" gs-x="0" gs-y="0" gs-w="8" gs-h="4" gs-id="dati_aziendali">
        <div class="grid-stack-item-content">
            {% include "dettaglio/dati_aziendali/_riquadro.html" %}
        </div>
    </div>
    ...
</div>
```

Il layout e' definito da coordinate JSON:
```json
[
    {"id": "dati_aziendali", "x": 0, "y": 0, "w": 8, "h": 4, "visible": true},
    {"id": "crm",            "x": 8, "y": 0, "w": 4, "h": 3, "visible": true},
    ...
]
```

### 3.2 Storage: File JSON (NO database)

**DECISIONE**: I layout sono salvati come file JSON in una cartella dedicata,
NON in tabella DB. Questo permette salvataggi multipli con nomi personalizzati,
facile backup e rollback.

**Cartella**: `impostazioni/layout/`

```
impostazioni/layout/
    _config.json              # {"layout_attivo": "default"} 
    default.json              # Layout di fabbrica (NON eliminabile, NON sovrascrivibile)
    layout_compatto.json      # Salvataggio utente
    layout_finanziario.json   # Altro salvataggio
    ...
```

**Struttura file JSON:**
```json
{
    "nome": "Layout Compatto",
    "descrizione": "Per schermi piccoli",
    "data_creazione": "2026-02-10T15:30:00",
    "creato_da": "M. Perani",
    "versione_schema": 1,
    "colonne": 12,
    "quadri": [
        {"id": "dati_aziendali", "x": 0, "y": 0, "w": 8, "h": 4, "visible": true, "min_w": 4, "min_h": 2},
        ...
    ]
}
```

**Regole protezione:**
- `default.json`: NON eliminabile, NON sovrascrivibile
- Layout attivo: NON eliminabile (prima attivare un altro)
- Nomi file: sanitizzati automaticamente (lowercase, no spazi, max 50 char)

### 3.3 Flusso di funzionamento

```
RENDERING PAGINA DETTAGLIO:
1. Route /cliente/<id> carica dati + layout JSON dal DB
2. Se layout NULL -> usa DEFAULT_LAYOUT (costante Python)
3. Template Jinja2 itera sul JSON e per ogni quadro:
   a. Se visible=false -> skip
   b. Altrimenti: genera <div> gridstack con coordinate
   c. Include il satellite corrispondente
4. JS inizializza gridstack in modalita' STATICA (no drag)

EDITOR LAYOUT (pagina admin separata):
1. Carica layout JSON corrente (o default)
2. Inizializza gridstack in modalita' EDIT (drag + resize attivi)
3. Per ogni quadro nascosto: mostra in sidebar come "disponibile"
4. Drag dalla sidebar -> aggiunge alla griglia
5. Toggle occhio -> nasconde/mostra
6. Pulsante Salva -> POST JSON al server
7. Pulsante Reset -> ripristina DEFAULT_LAYOUT
8. Pulsante Anteprima -> apre un cliente di esempio in nuova tab
```

### 3.4 Struttura File

```
templates/
    admin/
        layout_editor.html              # Pagina editor (nuova)
        layout_editor/
            _styles.html                # CSS editor
            _scripts.html               # JS editor (gridstack)
            _sidebar.html               # Sidebar quadri nascosti

    dettaglio/
        dati_aziendali/
            _riquadro.html              # NUOVO - estratto da dettaglio.html
        descrizione/
            _riquadro.html              # NUOVO - estratto
        capogruppo/
            _riquadro.html              # NUOVO - estratto
        collegamenti/
            _riquadro.html              # GIA' ESISTENTE
        contatti/
            _riquadro.html              # NUOVO - estratto
        referenti/
            _riquadro.html              # NUOVO - estratto
        veicoli/
            _riquadro.html              # NUOVO - estratto
        consensi_crm/
            _riquadro.html              # NUOVO - estratto
        storico/
            _riquadro.html              # NUOVO - estratto
        rating/
            _riquadro.html              # NUOVO - estratto
        fido/
            _riquadro.html              # NUOVO - estratto
        finanziari/
            _riquadro.html              # NUOVO - estratto
        commerciale/
            _riquadro.html              # NUOVO - estratto
        top_prospect/
            _riquadro.html              # NUOVO - estratto
        veicoli_rilevati/
            _riquadro.html              # NUOVO - estratto
        info/
            _riquadro.html              # NUOVO - estratto

    componenti/
        noleggiatori/
            _riquadro.html              # GIA' ESISTENTE
        crm/
            _riquadro.html              # GIA' ESISTENTE

app/
    routes_layout.py                    # Blueprint API layout (NUOVO)
    layout_config.py                    # Config + DEFAULT_LAYOUT (NUOVO)
```

---

## 4. LAYOUT DI DEFAULT

Il layout di default replica ESATTAMENTE la disposizione attuale.
Griglia a 12 colonne, altezza in unita' gridstack (1 unita' = ~80px circa).

```python
DEFAULT_LAYOUT = {
    "pagina": "dettaglio_cliente",
    "versione": 1,
    "colonne": 12,
    "quadri": [
        # === COLONNA SINISTRA (w=8) ===
        {"id": "dati_aziendali",   "x": 0, "y": 0,  "w": 8, "h": 4, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "descrizione",      "x": 0, "y": 4,  "w": 8, "h": 3, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "capogruppo",       "x": 0, "y": 7,  "w": 4, "h": 3, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "collegamenti",     "x": 4, "y": 7,  "w": 4, "h": 3, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "contatti",         "x": 0, "y": 10, "w": 8, "h": 3, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "noleggiatori",     "x": 0, "y": 13, "w": 8, "h": 3, "visible": True,  "min_w": 4, "min_h": 2},
        {"id": "documenti",        "x": 0, "y": 16, "w": 8, "h": 2, "visible": True,  "min_w": 6, "min_h": 2},
        {"id": "referenti",        "x": 0, "y": 18, "w": 12,"h": 4, "visible": True,  "min_w": 8, "min_h": 3},
        {"id": "veicoli",          "x": 0, "y": 22, "w": 12,"h": 5, "visible": True,  "min_w": 8, "min_h": 3},
        {"id": "consensi_crm",     "x": 0, "y": 27, "w": 12,"h": 3, "visible": True,  "min_w": 6, "min_h": 2},
        {"id": "storico",          "x": 0, "y": 30, "w": 12,"h": 4, "visible": True,  "min_w": 8, "min_h": 3},

        # === COLONNA DESTRA (w=4) ===
        {"id": "crm",              "x": 8, "y": 0,  "w": 4, "h": 3, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "rating",           "x": 8, "y": 3,  "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "fido",             "x": 8, "y": 5,  "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "finanziari",       "x": 8, "y": 7,  "w": 4, "h": 4, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "commerciale",      "x": 8, "y": 11, "w": 4, "h": 4, "visible": True,  "min_w": 3, "min_h": 2},
        {"id": "top_prospect",     "x": 8, "y": 15, "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "veicoli_rilevati", "x": 8, "y": 17, "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
        {"id": "info",             "x": 8, "y": 19, "w": 4, "h": 2, "visible": True,  "min_w": 3, "min_h": 1},
    ]
}
```

---

## 5. API ROUTES

**Nuovo blueprint: `routes_layout.py`** (IMPLEMENTATO)

```
GET  /admin/layout-editor              Pagina editor visuale (solo admin)
GET  /api/layout/lista                 Lista tutti i layout salvati
GET  /api/layout/attivo                Carica layout attivo
GET  /api/layout/<nome>                Carica layout specifico
POST /api/layout/salva                 Salva nuovo layout (nome + descrizione + quadri)
POST /api/layout/attiva/<nome>         Imposta layout attivo
POST /api/layout/duplica               Duplica layout (sorgente + nuovo_nome)
POST /api/layout/elimina/<nome>        Elimina layout (protezione default + attivo)
GET  /api/layout/catalogo              Catalogo quadri disponibili
```

---

## 6. PIANO DI IMPLEMENTAZIONE

### FASE 1 - Modularizzazione (prerequisito)

**Obiettivo**: Estrarre tutti i 15 quadri inline in file satellite separati.
**Rischio**: BASSO (zero cambi visivi, solo riorganizzazione include)
**Stima**: 1-2 sessioni

| Step | Azione | File coinvolti |
|------|--------|----------------|
| 1.1 | Estrarre "Dati Aziendali" | `dettaglio/dati_aziendali/_riquadro.html` |
| 1.2 | Estrarre "Descrizione" | `dettaglio/descrizione/_riquadro.html` |
| 1.3 | Estrarre "Capogruppo" | `dettaglio/capogruppo/_riquadro.html` |
| 1.4 | Estrarre "Contatti" | `dettaglio/contatti/_riquadro.html` |
| 1.5 | Estrarre "Referenti" (card + tabella) | `dettaglio/referenti/_riquadro.html` |
| 1.6 | Estrarre "Veicoli per Noleggiatore" | `dettaglio/veicoli/_riquadro.html` |
| 1.7 | Estrarre "Consensi CRM" | `dettaglio/consensi_crm/_riquadro.html` |
| 1.8 | Estrarre "Storico Modifiche" | `dettaglio/storico/_riquadro.html` |
| 1.9 | Estrarre "Rating" | `dettaglio/rating/_riquadro.html` |
| 1.10 | Estrarre "Fido Consigliato" | `dettaglio/fido/_riquadro.html` |
| 1.11 | Estrarre "Dati Finanziari" | `dettaglio/finanziari/_riquadro.html` |
| 1.12 | Estrarre "Commerciale Assegnato" | `dettaglio/commerciale/_riquadro.html` |
| 1.13 | Estrarre "Top Prospect Info" | `dettaglio/top_prospect/_riquadro.html` |
| 1.14 | Estrarre "Veicoli Rilevati" | `dettaglio/veicoli_rilevati/_riquadro.html` |
| 1.15 | Estrarre "Info" | `dettaglio/info/_riquadro.html` |
| 1.16 | Verificare che `dettaglio.html` sia solo include | Test completo |

**Metodo per ogni estrazione:**
1. Identificare il blocco HTML esatto (da `<div class="card` a `</div>` chiusura)
2. Creare cartella `templates/dettaglio/[nome]/`
3. Creare `_riquadro.html` con header versione
4. Sostituire in `dettaglio.html` con `{% include "dettaglio/[nome]/_riquadro.html" %}`
5. Verificare funzionamento (zero diff visivo)

### FASE 2 - Sistema Layout Backend

**Obiettivo**: Tabella DB + API + rendering dinamico.
**Rischio**: MEDIO (cambia il rendering della pagina)
**Stima**: 1 sessione

| Step | Azione |
|------|--------|
| 2.1 | Script migrazione DB (tabella `layout_pagine`) |
| 2.2 | File `app/layout_config.py` con DEFAULT_LAYOUT e catalogo quadri |
| 2.3 | Blueprint `app/routes_layout.py` con API GET/POST |
| 2.4 | Modificare `dettaglio.html` per leggere layout dal DB |
| 2.5 | Aggiungere gridstack.js in modalita' statica |
| 2.6 | Test: pagina identica al layout attuale |

### FASE 3 - Editor Visuale Admin

**Obiettivo**: Pagina admin con drag &amp; drop per configurare il layout.
**Rischio**: BASSO (pagina nuova, non tocca codice esistente)
**Stima**: 1 sessione

| Step | Azione |
|------|--------|
| 3.1 | Template `admin/layout_editor.html` con gridstack in modalita' edit |
| 3.2 | Sidebar con quadri nascosti (drag per aggiungere) |
| 3.3 | Toggle visibilita' (icona occhio su ogni quadro) |
| 3.4 | Pulsanti: Salva, Reset Default, Anteprima |
| 3.5 | Voce menu "Layout Pagine" in Gestione Sistema |
| 3.6 | Test completo: modifica, salva, verifica su dettaglio |

---

## 7. DETTAGLI EDITOR VISUALE

### 7.1 Interfaccia Editor

```
+-------------------------------------------------------+
|  Layout Pagine > Dettaglio Cliente       [Anteprima]  |
+-------------------------------------------------------+
|                                    |  QUADRI NASCOSTI  |
|   +------------------+  +------+  |                   |
|   | Dati Aziendali   |  | CRM  |  |  [ ] Consensi    |
|   |        8x4    [x]|  | 4x3  |  |  [ ] Top Prosp.  |
|   +------------------+  +------+  |                   |
|   +------------------+  +------+  |                   |
|   | Descrizione      |  |Rating|  |  Trascina qui     |
|   |        8x3    [x]|  | 4x2  |  |  per aggiungere   |
|   +------------------+  +------+  |                   |
|   +--------+ +-------+  +------+  |                   |
|   |Capogr. | |Colleg.|  | Fido |  |                   |
|   | 4x3    | | 4x3   |  | 4x2  |  |                   |
|   +--------+ +-------+  +------+  |                   |
|   ...                              |                   |
+------------------------------------+-------------------+
|  [Salva Layout]  [Reset Default]  [Annulla]           |
+-------------------------------------------------------+
```

### 7.2 Interazioni

- **Drag**: trascina un quadro per spostarlo nella griglia
- **Resize**: trascina l'angolo in basso a destra per ridimensionare
- **Nascondi**: click sull'icona [x] sul quadro -> va nella sidebar "Nascosti"
- **Mostra**: trascina dalla sidebar alla griglia, oppure click
- **Anteprima**: apre `/cliente/[id_esempio]` in nuova tab
- **Salva**: POST layout JSON, conferma con toast
- **Reset**: ripristina DEFAULT_LAYOUT, chiede conferma

### 7.3 Vincoli

- Larghezza minima per quadro (min_w) per evitare rendering rotto
- Altezza minima per quadro (min_h)
- Header cliente NON spostabile/nascondibile
- Pannello Note NON fa parte della griglia (resta split-screen separato)

---

## 8. CATALOGO QUADRI

Ogni quadro ha metadati per l'editor:

```python
CATALOGO_QUADRI = {
    "dati_aziendali":   {"nome": "Dati Aziendali",         "icona": "bi-building",          "template": "dettaglio/dati_aziendali/_riquadro.html"},
    "descrizione":      {"nome": "Descrizione / ATECO",    "icona": "bi-briefcase",         "template": "dettaglio/descrizione/_riquadro.html"},
    "capogruppo":       {"nome": "Capogruppo",             "icona": "bi-building",          "template": "dettaglio/capogruppo/_riquadro.html"},
    "collegamenti":     {"nome": "Collegamenti",           "icona": "bi-diagram-3",         "template": "dettaglio/collegamenti/_riquadro.html"},
    "contatti":         {"nome": "Contatti Generali",      "icona": "bi-telephone",         "template": "dettaglio/contatti/_riquadro.html"},
    "noleggiatori":     {"nome": "Noleggiatori",           "icona": "bi-buildings",         "template": "componenti/noleggiatori/_riquadro.html"},
    "documenti":        {"nome": "Documenti Cliente",      "icona": "bi-folder",            "template": "documenti_cliente.html"},
    "referenti":        {"nome": "Referenti",              "icona": "bi-people",            "template": "dettaglio/referenti/_riquadro.html"},
    "veicoli":          {"nome": "Veicoli Flotta",         "icona": "bi-car-front",         "template": "dettaglio/veicoli/_riquadro.html"},
    "consensi_crm":     {"nome": "Consensi / Alert CRM",   "icona": "bi-shield-check",      "template": "dettaglio/consensi_crm/_riquadro.html"},
    "storico":          {"nome": "Storico Modifiche",      "icona": "bi-clock-history",     "template": "dettaglio/storico/_riquadro.html"},
    "crm":              {"nome": "Dati CRM Zoho",          "icona": "bi-cloud-arrow-down",  "template": "componenti/crm/_riquadro.html"},
    "rating":           {"nome": "Rating / Score",         "icona": "bi-shield-check",      "template": "dettaglio/rating/_riquadro.html"},
    "fido":             {"nome": "Fido Consigliato",       "icona": "bi-credit-card",       "template": "dettaglio/fido/_riquadro.html"},
    "finanziari":       {"nome": "Dati Finanziari",        "icona": "bi-graph-up",          "template": "dettaglio/finanziari/_riquadro.html"},
    "commerciale":      {"nome": "Commerciale Assegnato",  "icona": "bi-person-badge",      "template": "dettaglio/commerciale/_riquadro.html"},
    "top_prospect":     {"nome": "Top Prospect",           "icona": "bi-trophy",            "template": "dettaglio/top_prospect/_riquadro.html"},
    "veicoli_rilevati": {"nome": "Veicoli Rilevati",       "icona": "bi-speedometer2",      "template": "dettaglio/veicoli_rilevati/_riquadro.html"},
    "info":             {"nome": "Info Date",              "icona": "bi-info-circle",       "template": "dettaglio/info/_riquadro.html"},
}
```

---

## 9. RISCHI E MITIGAZIONI

| Rischio | Probabilita' | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Regressione visiva dopo modularizzazione | Media | Alto | Test pixel-perfect dopo ogni estrazione |
| Gridstack incompatibile con card esistenti | Bassa | Medio | PoC con 2-3 quadri prima di procedere |
| Layout rotto su mobile | Media | Medio | Gridstack ha modalita' single-column responsive |
| Altezze dinamiche dei quadri | Alta | Medio | Usare `gs-auto-height` o calcolo dinamico |
| JS/CSS dei quadri si rompono dopo spostamento | Media | Alto | Assicurarsi che ogni satellite sia autocontenuto |

### 9.1 Rischio Principale: Altezze Dinamiche

I quadri hanno altezze variabili (es. Referenti con 1 vs 20 righe, Veicoli con 2 vs 50).
Gridstack di default usa altezze fisse. Soluzioni:

**Opzione A** (consigliata): `gridstack.js` con `cellHeight: 'auto'`
- I quadri si autoridimensionano in altezza
- L'editor imposta solo ordine e larghezza
- Il resize verticale nell'editor e' solo indicativo

**Opzione B**: Altezza fissa con scroll interno
- Ogni quadro ha max-height + overflow-y: auto
- Piu' controllabile ma meno usabile

---

## 10. CONSIDERAZIONI TECNICHE

### 10.1 Performance
- Il layout JSON e' piccolo (~2KB), si puo' cachare in memoria
- Nessun impatto su tempi di rendering
- Gridstack in modalita' statica non aggiunge overhead

### 10.2 Encoding
- Tutti i file satellite usano entita' HTML (`&euro;`, `&agrave;`, ecc.)
- Nessun carattere Unicode diretto nei template

### 10.3 Compatibilita'
- Gridstack 10.x supporta tutti i browser moderni
- Fallback: se JS disabilitato, i quadri si mostrano in ordine sequenziale

### 10.4 Modal e Script
- I modal (modalContatti, modalCapogruppo, ecc.) restano in `dettaglio.html`
  come include separati FUORI dalla griglia gridstack
- Gli script dei quadri (inline `<script>`) vanno nei rispettivi `_scripts.html`

---

## 11. DECISIONI CONFERMATE (2026-02-10)

1. **Sedi**: RESTANO dentro "Dati Aziendali" (sotto Sede Legale). No quadro separato.
2. **Note Cliente**: il pannello note RESTA split-screen separato, fuori dalla griglia.
3. **Documenti**: UNICO quadro con le 6 mini-card dentro (Car Policy, Contratti, Ordini, Quotazioni, Documenti, Trascrizioni).
4. **Altezze**: OPZIONE A - auto-height (`cellHeight: 'auto'`). I quadri si adattano al contenuto.

---

## 12. SISTEMA SALVATAGGIO E ROLLBACK

### 12.1 Concetto

Ogni volta che si salva un layout, la versione precedente NON viene sovrascritta
ma archiviata come "snapshot". L'utente puo' in qualsiasi momento:
- Vedere la lista delle configurazioni salvate
- Dare un nome descrittivo a una configurazione
- Ripristinare una configurazione precedente con un click
- Salvare la configurazione corrente come "modello" con nome personalizzato

### 12.2 Database

**Tabella aggiornata: `layout_pagine`** (configurazione attiva)

```sql
CREATE TABLE IF NOT EXISTS layout_pagine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pagina TEXT NOT NULL UNIQUE,
    layout_json TEXT NOT NULL,
    data_modifica TEXT NOT NULL,
    modificato_da_id INTEGER,
    FOREIGN KEY (modificato_da_id) REFERENCES utenti(id)
);
```

**Nuova tabella: `layout_pagine_versioni`** (storico + modelli)

```sql
CREATE TABLE IF NOT EXISTS layout_pagine_versioni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pagina TEXT NOT NULL,              -- 'dettaglio_cliente'
    nome TEXT,                         -- Nome descrittivo (NULL = auto)
    tipo TEXT NOT NULL DEFAULT 'auto', -- 'auto' = backup automatico, 'modello' = salvato dall'utente
    layout_json TEXT NOT NULL,
    data_creazione TEXT NOT NULL,
    creato_da_id INTEGER,
    nota TEXT,                         -- Nota opzionale
    FOREIGN KEY (creato_da_id) REFERENCES utenti(id)
);

CREATE INDEX IF NOT EXISTS idx_layout_versioni_pagina ON layout_pagine_versioni(pagina);
CREATE INDEX IF NOT EXISTS idx_layout_versioni_tipo ON layout_pagine_versioni(tipo);
```

### 12.3 Logica di funzionamento

```
SALVATAGGIO (quando clicchi "Salva" nell'editor):
1. Copia layout ATTUALE in layout_pagine_versioni (tipo='auto', nome=data/ora)
2. Sovrascrive layout_pagine con il nuovo layout
3. Pulizia automatica: mantiene max 20 versioni 'auto' (le piu' vecchie si cancellano)
4. I 'modello' non vengono MAI cancellati automaticamente

SALVA COME MODELLO (pulsante dedicato):
1. Chiede nome descrittivo (es. "Layout compatto", "Layout con finanziari grandi")
2. Salva in layout_pagine_versioni con tipo='modello'
3. Nota opzionale per ricordare perche' l'ha salvato

RIPRISTINA (dalla lista versioni):
1. Mostra lista: prima i modelli, poi gli auto (con data/ora)
2. Click su "Ripristina" -> copia quel JSON in layout_pagine (attivo)
3. Il layout corrente viene prima salvato come 'auto' (sicurezza)

RESET DEFAULT:
1. Salva layout corrente come 'auto'
2. Sovrascrive con DEFAULT_LAYOUT hardcoded
```

### 12.4 Interfaccia nell'Editor

```
+-------------------------------------------------------+
|  Layout Pagine > Dettaglio Cliente                    |
+-------------------------------------------------------+
|  [Salva]  [Salva come modello...]  [Reset Default]   |
+-------------------------------------------------------+
|                                                       |
|   ... griglia gridstack ...                          |
|                                                       |
+-------------------------------------------------------+
|  CONFIGURAZIONI SALVATE                               |
|  +--------------------------------------------------+|
|  | * Layout compatto (modello)     12/02 14:30  [R] ||
|  | * Layout finanziari grandi      11/02 09:15  [R] ||
|  |--------------------------------------------------||
|  | Backup auto  10/02 18:45                     [R] ||
|  | Backup auto  10/02 16:20                     [R] ||
|  | Backup auto  10/02 15:00                     [R] ||
|  +--------------------------------------------------+|
|  [R] = Ripristina    [x] = Elimina (solo modelli)    |
+-------------------------------------------------------+
```

### 12.5 API aggiuntive

```
GET  /api/layout/<pagina>/versioni          Lista versioni + modelli
POST /api/layout/<pagina>/modello           Salva come modello (nome, nota)
POST /api/layout/<pagina>/ripristina/<id>   Ripristina una versione
DELETE /api/layout/<pagina>/versioni/<id>   Elimina modello (solo tipo='modello')
```

### 12.6 Sicurezze

| Situazione | Comportamento |
|------------|---------------|
| Salvo layout | Backup automatico del precedente |
| Ripristino versione | Backup automatico del corrente prima di sovrascrivere |
| Reset default | Backup automatico del corrente |
| Troppe versioni auto | Pulizia automatica: max 20, le piu' vecchie si eliminano |
| Modelli salvati | MAI eliminati automaticamente, solo manualmente |
| Nessun layout in DB | Usa DEFAULT_LAYOUT hardcoded (sempre disponibile) |

**Risultato**: e' IMPOSSIBILE perdere una configurazione. Anche nel caso peggiore,
il DEFAULT_LAYOUT hardcoded e' sempre disponibile come ultima risorsa.

---

## 13. CHECKLIST APPROVAZIONE

Prima di iniziare l'implementazione:

- [x] Michele approva la mappa dei 19 quadri
- [x] Michele sceglie opzione altezze: **Opzione A (auto-height)**
- [x] Michele risponde alle domande aperte (sezione 11)
- [x] Michele conferma ordine fasi (1 -> 2 -> 3)
- [x] Michele conferma che `dettaglio.html` nel progetto e' aggiornato

---

## STORICO DOCUMENTO

| Data | Versione | Modifiche |
|------|----------|-----------|
| 2026-02-10 | 1.0 | Creazione documento progetto completo |
| 2026-02-10 | 1.1 | Decisioni confermate: auto-height, sedi in Dati Aziendali, documenti unico quadro |
| 2026-02-10 | 2.0 | Architettura cambiata: da DB a file JSON multipli. Implementati layout_config.py e routes_layout.py |
