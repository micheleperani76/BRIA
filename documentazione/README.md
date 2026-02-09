# GESTIONE FLOTTA

Sistema integrato per la gestione clienti, veicoli e dati Creditsafe.

**Repository GitHub**: https://github.com/micheleperani76/BRIA

## Sync con Claude AI

Il progetto e' collegato a un Claude Project tramite GitHub Integration.

**Flusso di lavoro:**
1. Modifiche al codice sul server BRserver
2. Sync su GitHub: `./raccolta_file_ia.sh --solo-git`
3. Su Claude: cliccare "Sync" nel Project Knowledge

**File esclusi da GitHub** (vedi `.gitignore`):
database, dati clienti, credenziali, log, allegati, audio, backup

## Struttura Cartelle

```
gestione_flotta/
├── app/                    # Moduli Python Flask
│   ├── __init__.py
│   ├── config.py           # Configurazione centralizzata
│   ├── database.py         # Gestione database SQLite
│   ├── database_utenti.py  # Gestione utenti e permessi
│   ├── auth.py             # Autenticazione e ruoli
│   ├── import_creditsafe.py # Import PDF Creditsafe
│   ├── utils.py            # Funzioni utilita'
│   ├── utils_identificativo.py # Normalizzazione P.IVA/CF
│   ├── web_server.py       # Server web Flask (routes principali)
│   ├── routes_sedi_cliente.py  # CRUD sedi cliente
│   ├── routes_referenti.py     # CRUD referenti
│   └── ...                 # Altri moduli routes
├── db/                     # Database SQLite
│   └── gestionale.db       # Database unico
├── documentazione/         # Documentazione progetto
├── import_dati/            # CSV per import CRM
├── impostazioni/           # File Excel configurazione
├── logs/                   # Log applicazione
├── pdf/                    # Input: PDF da elaborare
├── scripts/                # Script Python e Bash
│   ├── migrazione_crm_zoho.py      # Migrazione DB per CRM
│   ├── import_accounts_crm.py      # Import clienti da Zoho
│   ├── import_scadenze_crm.py      # Import veicoli da Zoho
│   └── ...
├── storico_pdf/            # Archivio PDF elaborati (A-Z)
├── templates/              # Template HTML Jinja2
├── main.py                 # Entry point principale
└── README.md
```

## Database

Il database `gestionale.db` contiene:

### Tabelle principali
| Tabella | Descrizione |
|---------|-------------|
| `clienti` | Anagrafica clienti (71 colonne), dati flotta + Creditsafe + CRM |
| `veicoli` | Veicoli flotta (45 colonne), tipo_veicolo: Installato/Extra |
| `storico_installato` | Veicoli dismessi INSTALLATO (retention 5 anni) |
| `storico_modifiche` | Log di tutte le modifiche ai dati |

### Tabelle satellite CRM
| Tabella | Descrizione |
|---------|-------------|
| `clienti_consensi` | Consensi GDPR (Newsletter, Comunicazioni, ecc.) |
| `clienti_dati_finanziari` | Dati economici per anno (fatturato, EBITDA, ecc.) |
| `clienti_creditsafe_alert` | Flag rischio (protesti, pregiudizievoli, ecc.) |
| `clienti_crm_metadata` | Dati tecnici Zoho (record_id, sync, ecc.) |

### Tabelle operative
| Tabella | Descrizione |
|---------|-------------|
| `sedi_cliente` | Sedi operative/filiali/fatturazione |
| `referenti_clienti` | Referenti aziendali |
| `note_clienti` | Note con allegati e soft delete |
| `note_veicoli` | Note su veicoli |
| `utenti` | Utenti sistema con ruoli e permessi |
| `coda_trascrizioni` | Coda trascrizione audio |

### Logica tipo veicolo
- **Installato**: gestito da BR Car Service (import da CRM Zoho Scadenze)
- **Extra**: gestito da broker esterno (import da file flotta noleggiatori)

## Import CRM Zoho

Importazione dati dal CRM Zoho in 3 fasi sequenziali.

### Fase 1: Migrazione DB
```bash
python3 scripts/migrazione_crm_zoho.py --dry-run
python3 scripts/migrazione_crm_zoho.py
```

### Fase 2: Import Accounts (clienti)
```bash
python3 scripts/import_accounts_crm.py import_dati/Accounts_*.csv --dry-run
python3 scripts/import_accounts_crm.py import_dati/Accounts_*.csv
```
Regole: match per P.IVA (zero-pad + IT), Creditsafe ha priorita' su nome/sede.

### Fase 3: Import Scadenze (veicoli)
```bash
python3 scripts/import_scadenze_crm.py import_dati/Scadenze_*.csv --dry-run
python3 scripts/import_scadenze_crm.py import_dati/Scadenze_*.csv
```
Categorizzazione: Circolante → veicoli, Archiviata → storico_installato.

### Priorita' dati
| Dato | Fonte prioritaria | Note |
|------|-------------------|------|
| nome_cliente, sede legale | Creditsafe | Mai sovrascritto da CRM |
| stato_crm, profilazione, flotta | CRM Zoho | Sempre aggiornati |
| commerciale_id | Assegnazione interna | Mai toccato da import |
| PEC, telefono | Creditsafe | CRM aggiorna solo se vuoti |
| driver, note | Inserimento manuale | Mai sovrascritti |

## Import PDF Creditsafe

1. Copia PDF nella cartella `pdf/`
2. Import manuale o crontab
3. Estrazione dati con regex, match per P.IVA
4. PDF archiviato in `storico_pdf/LETTERA/`

## Avvio e Configurazione

### Requisiti
```bash
sudo apt install python3 python3-pip
pip3 install flask openpyxl pillow --break-system-packages
```

### Avvio server
```bash
python3 main.py server          # Porta 5001
./scripts/gestione_flotta.sh start
```

### Crontab
```cron
@reboot /home/michele/gestione_flotta/scripts/avvia_server.sh
5 * * * * /home/michele/gestione_flotta/scripts/autoimport.sh
```

## Interfaccia Web

- **Home**: http://localhost:5001 - Lista clienti con filtri avanzati
- **Flotta**: http://localhost:5001/flotta - Dashboard veicoli
- **Installato**: http://localhost:5001/installato - Veicoli gestiti BR, stats, filtri, storico dismessi
- **Statistiche**: http://localhost:5001/statistiche
- **Amministrazione**: http://localhost:5001/admin - Import, utenti, ticker

---

## Novita' Febbraio 2026

### Import CRM Zoho
- Import completo anagrafica clienti (2637 clienti) e veicoli INSTALLATO (879 attivi + 507 storicizzati)
- Migrazione DB con 5 tabelle satellite, 13+4 nuovi campi, 11 indici
- Normalizzazione P.IVA cross-sistema (CRM senza zeri, DB con IT + 11 cifre)
- Categorizzazione automatica veicoli: ATTIVO/IN_GESTIONE/DISMESSO/ANOMALO
- Retention 5 anni per veicoli dismessi in storico_installato

### Trascrizione Audio
- Trascrizione automatica file audio con faster-whisper (large-v3-turbo)
- Upload drag & drop, coda con priorita', worker background systemd
- Spostamento trascrizioni su clienti con ricerca fuzzy
- Performance: ~0.42x realtime (54 min audio = 22 min elaborazione)

### Sistema Notifiche
- Hub centrale notifiche con deduplicazione e routing automatico
- 13 categorie + 4 livelli, widget campanella trascinabile
- Connettori modulari, predisposto per email SMTP e Telegram

### Export Avanzato
- Export Top Prospect confermati in Excel/CSV
- Export Trattative con filtri multipli
- Interfaccia 3 tab unificata (Clienti, Top Prospect, Trattative)
