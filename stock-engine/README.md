# 🚗 Stock Engine

**Sistema Elaborazione Stock Veicoli v1.0.0**

Applicazione Flask per l'elaborazione automatica dei file stock dei noleggiatori (AYVENS, ARVAL, LEASYS), con matching JATO e generazione Excel.

> **Questo sistema sostituisce la pipeline bash (ayvens.sh, arval.sh, etc.) con un'applicazione web moderna, API REST e database PostgreSQL.**

---

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Confronto Performance](#confronto-performance)
3. [Struttura Progetto](#struttura-progetto)
4. [Requisiti](#requisiti)
5. [Installazione Rapida (Docker)](#installazione-rapida-docker)
6. [Installazione Manuale](#installazione-manuale)
7. [Configurazione](#configurazione)
8. [Primo Avvio](#primo-avvio)
9. [Uso Quotidiano](#uso-quotidiano)
10. [API Reference](#api-reference)
11. [API per Programma Principale](#api-per-programma-principale)
12. [Architettura](#architettura)
13. [Troubleshooting](#troubleshooting)

---

## 🎯 Panoramica

Stock Engine è un sistema completo che:

- **Acquisisce automaticamente** i file stock dai noleggiatori (AYVENS, ARVAL, LEASYS)
- **Importa i dati** in un database PostgreSQL centralizzato
- **Esegue l'elaborazione** (pulizia, normalizzazione, match JATO, arricchimento)
- **Espone API REST** per il portale principale esistente
- **Genera Excel on-demand** per consultazione
- **Gestisce lo storico completo** via database (non più file)

---

## 📊 Confronto Performance

| Operazione | Sistema Attuale (bash) | Stock Engine |
|------------|------------------------|--------------|
| Elaborazione AYVENS | ~10 minuti | **30-60 secondi** |
| Letture/scritture Excel | ~15 per elaborazione | **1 (solo finale)** |
| Ricerca veicoli | Manuale su Excel | **API instant** |
| Storico | File sparsi | **Database queryable** |
| Manutenzione | Molti script bash | **1 applicazione** |
| API per portale | ❌ Non disponibile | ✅ REST API completa |
| Dashboard | ❌ Non disponibile | ✅ Web interface |
| Monitoraggio | Log sparsi | ✅ Centralizzato |

---

## 📦 Struttura Progetto

```
stock-engine/                    # 34 file totali
├── app/
│   ├── __init__.py              # Flask app factory con comandi CLI
│   ├── config.py                # Configurazioni (PostgreSQL, percorsi)
│   │
│   ├── models/                  # 5 modelli database
│   │   ├── __init__.py
│   │   ├── veicolo.py           # Stock veicoli (tabella principale)
│   │   ├── jato.py              # Database JATO per matching
│   │   ├── glossario.py         # Regole normalizzazione termini
│   │   ├── pattern.py           # Pattern identificazione carburante
│   │   └── elaborazione.py      # Log elaborazioni eseguite
│   │
│   ├── services/                # 9 servizi logica business
│   │   ├── __init__.py
│   │   ├── pipeline.py          # ⭐ CORE: Orchestratore (sostituisce ayvens.sh)
│   │   ├── matcher.py           # ⭐ CORE: Match JATO (da 02_match_jato.py)
│   │   ├── normalizer.py        # Applica glossario (da 00_applica_glossario.py)
│   │   ├── enricher.py          # Arricchimento dati (da 03_arricchimento.py)
│   │   ├── exporter.py          # Genera file Excel output
│   │   ├── jato_migrator.py     # Migra database_jato.db esistente
│   │   ├── config_migrator.py   # Migra glossario/pattern da Excel
│   │   └── importers/           # Import specifici per noleggiatore
│   │       ├── __init__.py
│   │       ├── base_importer.py     # Classe base comune
│   │       ├── ayvens_importer.py   # Import AYVENS (CSV/XLSX)
│   │       └── arval_importer.py    # Import ARVAL (XLSX)
│   │
│   ├── api/                     # 3 blueprint API REST
│   │   ├── __init__.py
│   │   ├── stock.py             # GET /api/stock/* - Veicoli
│   │   ├── elaborazioni.py      # POST /api/elabora/* - Elaborazioni
│   │   └── export.py            # GET /api/export/* - Download Excel
│   │
│   └── web/                     # Interfaccia web
│       ├── __init__.py
│       └── templates/
│           ├── base.html        # Template base
│           └── dashboard.html   # Dashboard principale
│
├── scheduler/
│   └── run_scheduler.py         # Elaborazione automatica ore 07:00
│
├── migrations/
│   └── init.sql                 # Schema PostgreSQL completo + dati default
│
├── output/
│   └── stock/                   # Directory file Excel generati
│
├── docker-compose.yml           # PostgreSQL + App + Scheduler
├── Dockerfile                   # Immagine Docker applicazione
├── requirements.txt             # Dipendenze Python
├── run.py                       # Entry point sviluppo
├── .env.example                 # Template variabili ambiente
└── README.md                    # Questa documentazione
```

---

## 🔧 Requisiti

- **Sistema**: Linux (Debian/Ubuntu)
- **Python**: 3.10+
- **Spazio disco**: 1GB+ (dipende dallo storico)
- **RAM**: 512MB minimo

Database: **SQLite** (incluso in Python, nessuna installazione)

---

## 🚀 Installazione

### 1. Estrai il progetto
```bash
cd /home/michele
unzip stock-engine-v1.0.0.zip
cd stock-engine
```

### 2. Configura i percorsi
```bash
# Copia il template
cp .env.example .env

# Modifica con i tuoi percorsi
nano .env
```

**Percorsi da configurare in `.env`:**
```bash
DIR_INPUT=/home/michele/stock/elaborazione      # Dove MEGA sincronizza
DIR_JATO=/home/michele/stock/mappati            # Dove sta database_jato.db
DIR_IMPOSTAZIONI=/home/michele/stock/impostazioni  # glossario, pattern
```

### 3. Prima installazione
```bash
# Rendi eseguibili gli script
chmod +x scripts/*.sh

# Inizializza (crea venv, installa dipendenze, migra dati)
./scripts/stock_engine.sh init
```

### 4. Avvia il server
```bash
./scripts/stock_engine.sh start
```

### 5. Verifica funzionamento
```bash
# Stato servizi
./scripts/stock_engine.sh status

# Health check
curl http://localhost:5000/api/health

# Apri dashboard
firefox http://localhost:5000
```

---

## ⚙️ Gestione Server

Lo script `scripts/stock_engine.sh` gestisce tutto:

```bash
# Avvia server e scheduler
./scripts/stock_engine.sh start

# Ferma tutto
./scripts/stock_engine.sh stop

# Riavvia
./scripts/stock_engine.sh restart

# Stato servizi
./scripts/stock_engine.sh status

# Log in tempo reale
./scripts/stock_engine.sh logs follow

# Elaborazione manuale
./scripts/stock_engine.sh elabora AYVENS
./scripts/stock_engine.sh elabora          # tutti i noleggiatori
```

---

## 🔄 Avvio Automatico (Crontab)

Per avviare Stock Engine automaticamente al boot:

```bash
crontab -e

# Aggiungi questa riga:
@reboot /home/michele/stock-engine/scripts/avvia_server.sh
```

---

## ⚙️ Configurazione

### File `.env`

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `DIR_INPUT` | Directory file input noleggiatori | `/home/michele/stock/elaborazione` |
| `DIR_OUTPUT` | Directory output Excel | `./output/stock` |
| `DIR_JATO` | Directory database JATO | `/home/michele/stock/mappati` |
| `DIR_IMPOSTAZIONI` | Directory glossario/pattern | `/home/michele/stock/impostazioni` |
| `SCHEDULER_ORA` | Ora elaborazione automatica | `07:00` |
| `STORICO_GIORNI` | Giorni storico da mantenere | `365` |
| `DATABASE_URL` | URL database (opzionale) | SQLite in `instance/` |

### Noleggiatori Attivi

In `app/config.py`:
```python
NOLEGGIATORI_ATTIVI = ['AYVENS', 'ARVAL', 'LEASYS']
```

---

## 🧪 Primo Avvio

### 1. Verifica database JATO
```bash
./scripts/stock_engine.sh elabora AYVENS

# Oppure da flask shell:
source venv/bin/activate
flask shell
>>> from app.models import JatoModel
>>> JatoModel.query.count()
# Dovrebbe mostrare ~50000+ record
```

### 2. Test elaborazione
```bash
# Elabora AYVENS
./scripts/stock_engine.sh elabora AYVENS

# Output atteso:
# ============================================================
# ELABORAZIONE AYVENS COMPLETATA
# ============================================================
# Veicoli importati: 5170
# Veicoli matched:   4920
# Match rate:        95.2%
# Durata:            45 secondi
# File Excel:        output/stock/ayvens_stock_28-01-2026.xlsx
```

### 3. Verifica API
```bash
# Health check
curl http://localhost:5000/api/health

# Lista veicoli
curl http://localhost:5000/api/stock/ayvens | head
```

---

## 📅 Uso Quotidiano

### Elaborazione Automatica
Lo scheduler esegue automaticamente l'elaborazione all'ora configurata (default 07:00).

```bash
# Verifica scheduler attivo
./scripts/stock_engine.sh status

# Vedi log scheduler
./scripts/stock_engine.sh logs scheduler
```

### Elaborazione Manuale
```bash
# Singolo noleggiatore
./scripts/stock_engine.sh elabora AYVENS

# Tutti i noleggiatori
./scripts/stock_engine.sh elabora

# Via API
curl -X POST http://localhost:5000/api/elabora/ayvens
```

### Download Excel
I file Excel vengono generati in `output/stock/`:

```bash
# Lista file generati
ls -la output/stock/

# Download via API
curl -o stock.xlsx http://localhost:5000/api/export/excel/ayvens
```

### Gestione Servizi
```bash
# Stato
./scripts/stock_engine.sh status

# Log in tempo reale
./scripts/stock_engine.sh logs follow

# Riavvia dopo modifiche
./scripts/stock_engine.sh restart
```

---

## 📡 API Reference

### Stock

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/stock` | GET | Lista veicoli (paginata) |
| `/api/stock/{noleggiatore}` | GET | Veicoli per noleggiatore |
| `/api/stock/search` | GET | Ricerca con filtri |
| `/api/stock/{id}` | GET | Dettaglio veicolo |
| `/api/stock/statistics` | GET | Statistiche |

### Elaborazioni

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/elaborazioni` | GET | Lista elaborazioni |
| `/api/elaborazioni/{id}` | GET | Dettaglio elaborazione |
| `/api/elabora/{noleggiatore}` | POST | Lancia elaborazione |
| `/api/elabora/tutti` | POST | Elabora tutti |

### Export

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/export/excel/{noleggiatore}` | GET | Download Excel |
| `/api/export/list` | GET | Lista file disponibili |

### Health

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/health` | GET | Health check |

---

## 🔌 API per Programma Principale

Il tuo programma principale può chiamare queste API per attingere ai dati elaborati:

### Ottenere veicoli giornalieri
```bash
# Veicoli AYVENS di oggi
curl "http://localhost:5000/api/stock/ayvens"

# Veicoli AYVENS di una data specifica
curl "http://localhost:5000/api/stock/ayvens?data=2026-01-28"

# Risposta JSON
{
  "noleggiatore": "AYVENS",
  "data": "2026-01-28",
  "count": 5170,
  "veicoli": [
    {
      "id": 1,
      "vin": "WVWZZZ...",
      "marca": "VOLKSWAGEN",
      "modello": "GOLF",
      "description": "GOLF 1.5 TSI ACT DSG Life",
      "alimentazione": "PETROL",
      "kw": 110,
      "hp": 150,
      "co2": 128,
      "prezzo_listino": 28500.00,
      "prezzo_totale": 31200.00,
      "location": "Milano",
      "jato_code": "IT123456",
      "match_status": "MATCHED",
      "neopatentati": "NO"
    },
    ...
  ]
}
```

### Ricerca con filtri
```bash
# Cerca FIAT diesel per neopatentati
curl "http://localhost:5000/api/stock/search?marca=FIAT&alimentazione=DIESEL&neopatentati=SI"

# Cerca per range prezzo
curl "http://localhost:5000/api/stock/search?prezzo_min=20000&prezzo_max=35000"

# Cerca modello specifico
curl "http://localhost:5000/api/stock/search?marca=BMW&modello=X1"
```

### Download Excel
```bash
# Download Excel AYVENS oggi
curl -o stock_ayvens.xlsx "http://localhost:5000/api/export/excel/ayvens"

# Download Excel data specifica
curl -o stock.xlsx "http://localhost:5000/api/export/excel/ayvens?data=2026-01-28"

# Rigenera Excel (ignora cache)
curl -o stock.xlsx "http://localhost:5000/api/export/excel/ayvens?regenerate=true"
```

### Statistiche
```bash
# Statistiche generali
curl "http://localhost:5000/api/stock/statistics"

# Statistiche per noleggiatore
curl "http://localhost:5000/api/stock/statistics?noleggiatore=AYVENS"

# Risposta
{
  "totale": 5170,
  "matched": 4920,
  "partial": 150,
  "no_match": 100,
  "match_rate": 95.2
}
```

### Lancia elaborazione manuale
```bash
# Elabora AYVENS
curl -X POST "http://localhost:5000/api/elabora/ayvens"

# Elabora tutti i noleggiatori
curl -X POST "http://localhost:5000/api/elabora/tutti"

# Risposta
{
  "noleggiatore": "AYVENS",
  "data": "2026-01-28",
  "veicoli_importati": 5170,
  "veicoli_matched": 4920,
  "match_rate": 95.2,
  "durata_secondi": 45,
  "file_excel": "/output/stock/ayvens_stock_28-01-2026.xlsx",
  "stato": "completata"
}
```

### Integrazione Python
```python
import requests

BASE_URL = "http://localhost:5000/api"

# Ottieni veicoli
response = requests.get(f"{BASE_URL}/stock/ayvens")
veicoli = response.json()['veicoli']

# Filtra in memoria o usa parametri
for v in veicoli:
    if v['match_status'] == 'MATCHED' and v['neopatentati'] == 'SI':
        print(f"{v['marca']} {v['description']} - €{v['prezzo_totale']}")

# Ricerca server-side (più efficiente)
params = {
    'marca': 'FIAT',
    'alimentazione': 'DIESEL',
    'neopatentati': 'SI',
    'limit': 100
}
response = requests.get(f"{BASE_URL}/stock/search", params=params)
risultati = response.json()['veicoli']
```

### Esempi

```bash
# Lista veicoli AYVENS oggi
curl "http://localhost:5000/api/stock/ayvens"

# Ricerca FIAT diesel
curl "http://localhost:5000/api/stock/search?marca=FIAT&alimentazione=DIESEL"

# Statistiche
curl "http://localhost:5000/api/stock/statistics?noleggiatore=AYVENS"

# Download Excel con data specifica
curl -o stock.xlsx "http://localhost:5000/api/export/excel/ayvens?data=2026-01-28"
```

---

## 🏗 Architettura

```
┌─────────────────────────────────────────────────────────────────┐
│                        STOCK ENGINE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  MEGA    │───▶│  INPUT   │───▶│ PIPELINE │───▶│   API    │  │
│  │  Sync    │    │  Files   │    │          │    │  REST    │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                        │              │          │
│                                        ▼              ▼          │
│                                  ┌──────────┐   ┌──────────┐    │
│                                  │ DATABASE │   │  EXCEL   │    │
│                                  │ PostgreSQL│   │  Output  │    │
│                                  └──────────┘   └──────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flusso Elaborazione (Pipeline)

```
PRIMA (bash - 10 minuti):
AY000 → AY008 → AY016 → AY024 → AY032 → AY040 → AY048 → AY056 → AY064 → AY072 → AY090
  ↓       ↓       ↓       ↓       ↓       ↓       ↓       ↓       ↓       ↓       ↓
cerca  converte pulisce corregge ordina  backup  MATCH  riepilogo selez. storico DB
file   CSV→XLSX grafica colonne  righe   file   JATO   Excel    Excel   archiv. archiv.

DOPO (Python - 30-60 secondi):
┌─────────┐   ┌───────────┐   ┌─────────┐   ┌─────────┐   ┌──────┐   ┌────────┐
│ IMPORT  │──▶│ NORMALIZE │──▶│  MATCH  │──▶│ ENRICH  │──▶│ SAVE │──▶│ EXPORT │
│         │   │ Glossario │   │  JATO   │   │  Dati   │   │  DB  │   │ Excel  │
└─────────┘   └───────────┘   └─────────┘   └─────────┘   └──────┘   └────────┘
    │              │               │             │            │           │
    ▼              ▼               ▼             ▼            ▼           ▼
  CSV/XLSX    Sostituzioni    Query DB      kW, HP,      INSERT/    File .xlsx
  da file     termini         + Scoring     Omologaz.    UPDATE     in output/
```

### Algoritmo Match JATO

Il matcher (`services/matcher.py`) implementa l'algoritmo originale di `02_match_jato.py`:

1. **HARD FILTER**: MARCA + pattern carburante + kW/HP (±3kW, ±5HP)
2. **SCORING**:
   - Vehicle Set match: 40 punti
   - Product Description: 30 punti
   - Fuel Type: 15 punti
   - Body Type: 10 punti
3. **BONUS/PENALITÀ**:
   - Parole ripetute (es. ALFA ROMEO JUNIOR): +10 punti
   - Parole extra nel candidato: -2 punti/parola
4. **SELEZIONE**: Best match, gestione duplicati (status PARTIAL)

Soglia minima: `MIN_MATCH_SCORE = 25`

---

## ⏰ Elaborazione Automatica

Lo **scheduler** (`scheduler/run_scheduler.py`) esegue automaticamente:

### Job Mattutino (07:00)
- Elabora tutti i noleggiatori attivi (AYVENS, ARVAL, LEASYS)
- Genera file Excel in `/output/stock/`
- Logga risultati

### Job Settimanale (Domenica 03:00)
- Pulizia dati più vecchi di 365 giorni
- Ottimizzazione database

### Configurazione
```bash
# Modifica ora elaborazione in docker-compose.yml o .env
SCHEDULER_ORA=07:00

# Giorni storico da mantenere
STORICO_GIORNI=365
```

### Verifica Scheduler
```bash
# Logs scheduler
docker-compose logs -f scheduler

# Ultima elaborazione
curl "http://localhost:5000/api/elaborazioni/ultima/ayvens"
```

---

## 🔧 Troubleshooting

### Server non parte
```bash
# Controlla log errori
./scripts/stock_engine.sh logs error

# Verifica porte libere
sudo lsof -i :5000

# Riavvia forzato
./scripts/stock_engine.sh stop
./scripts/stock_engine.sh start
```

### Elaborazione fallisce
```bash
# Controlla log
./scripts/stock_engine.sh logs app

# Verifica file input esiste
ls -la /home/michele/stock/elaborazione/

# Test manuale
source venv/bin/activate
flask elabora AYVENS
```

### Database JATO non importato
```bash
# Verifica file esiste
ls -la /home/michele/stock/mappati/database_jato.db

# Reimporta
source venv/bin/activate
flask import-jato
```

### Match rate basso
1. Verifica glossario importato:
   ```bash
   flask shell
   >>> from app.models import Glossario
   >>> Glossario.query.count()  # Dovrebbe essere > 0
   ```

2. Verifica pattern carburante:
   ```bash
   >>> from app.models import PatternCarburante
   >>> PatternCarburante.query.count()  # Dovrebbe essere > 20
   ```

3. Controlla log match per dettagli

### Reset completo
```bash
# ATTENZIONE: cancella tutti i dati!
./scripts/stock_engine.sh stop
rm -rf instance/stock_engine.db
rm -rf venv
./scripts/stock_engine.sh init
./scripts/stock_engine.sh start
```

---

## 📞 File e Directory

```
stock-engine/
├── .env                    # Configurazione (DA CREARE da .env.example)
├── instance/
│   └── stock_engine.db     # Database SQLite (creato automaticamente)
├── output/
│   └── stock/              # File Excel generati
├── logs/
│   ├── app.log             # Log applicazione
│   ├── scheduler.log       # Log scheduler
│   └── error.log           # Log errori
├── scripts/
│   ├── stock_engine.sh     # Script gestione principale
│   └── avvia_server.sh     # Script per crontab @reboot
└── venv/                   # Virtual environment Python
```

---

**Stock Engine v1.0.0** - Sistema Gestione Stock Veicoli  
Data: 28 gennaio 2026
