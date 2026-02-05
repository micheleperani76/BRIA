# MANUALE TECNICO - GESTIONE FLOTTA
## BR CAR SERVICE

**Versione**: 1.2  
**Data**: 2026-02-04  
**Stack**: Python Flask + SQLite + Bootstrap

---

## INDICE

1. [Architettura Sistema](#1-architettura-sistema)
2. [Struttura Cartelle](#2-struttura-cartelle)
3. [Database](#3-database)
4. [Moduli Python](#4-moduli-python)
5. [Blueprint e Route](#5-blueprint-e-route)
6. [Template HTML](#6-template-html)
7. [Configurazione](#7-configurazione)
8. [Regole di Sviluppo](#8-regole-di-sviluppo)
9. [Deploy e Manutenzione](#9-deploy-e-manutenzione)

---

## 1. ARCHITETTURA SISTEMA

### 1.1 Stack Tecnologico
| Componente | Tecnologia |
|------------|------------|
| **Backend** | Python 3.x + Flask |
| **Database** | SQLite |
| **Frontend** | Bootstrap 5 + Jinja2 |
| **Icone** | Bootstrap Icons |
| **Server** | Porta 5001 |

### 1.2 Principi Architetturali

#### Modularit&agrave; Estrema (Regola Aurea #5)
- Ogni funzione = 1 file satellite separato
- Ogni componente ha la propria cartella dedicata
- Struttura: `_riquadro.html`, `_modal.html`, `_scripts.html`, `_styles.html`

#### Limite 1000 Righe (Regola Aurea #6)
- File Python &gt; 1000 righe: smembrare in Blueprint
- File HTML &gt; 500 righe: usare include Jinja2

#### Fonte Unica di Verit&agrave;
- Ogni informazione ha UNA SOLA funzione che la fornisce
- Tutti gli altri punti usano quella funzione

---

## 2. STRUTTURA CARTELLE

```
gestione_flotta/
â”œâ”€â”€ app/                          # Moduli Python
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ config.py                 # Configurazione centralizzata
â”‚   â”œâ”€â”€ config_percorsi.py        # Path cartelle
â”‚   â”œâ”€â”€ config_stati.py           # Stati cliente/veicolo
â”‚   â”œâ”€â”€ config_top_prospect.py    # Parametri Top Prospect
â”‚   â”œâ”€â”€ config_trattative.py      # Configurazione trattative
â”‚   â”œâ”€â”€ database.py               # Gestione DB principale
â”‚   â”œâ”€â”€ database_utenti.py        # Gestione utenti e permessi
â”‚   â”œâ”€â”€ auth.py                   # Decoratori autenticazione
â”‚   â”œâ”€â”€ utils.py                  # Funzioni utilit&agrave;
â”‚   â”œâ”€â”€ utils_identificativo.py   # Logica P.IVA/CF
â”‚   â”œâ”€â”€ gestione_commerciali.py   # Modulo commerciali centralizzato
â”‚   â”œâ”€â”€ connettori_stato_cliente.py # Indicatori cliente
â”‚   â”œâ”€â”€ import_creditsafe.py      # Import PDF Creditsafe
â”‚   â”œâ”€â”€ export_excel.py           # Generazione Excel
â”‚   â”œâ”€â”€ google_calendar.py        # Integrazione Google Calendar
â”‚   â”œâ”€â”€ motore_top_prospect.py    # Logica Top Prospect
â”‚   â”œâ”€â”€ motore_trattative.py      # Logica Trattative
â"‚   â"œâ"€â"€ config_notifiche.py       # Configurazione notifiche
â"‚   â"œâ"€â"€ motore_notifiche.py       # Hub centrale notifiche
â"‚   â"œâ"€â"€ connettori_notifiche/     # Package connettori notifiche
â”‚   â”œâ”€â”€ web_server.py             # Server Flask principale
â”‚   â””â”€â”€ routes_*.py               # Blueprint separati
â”œâ”€â”€ templates/                    # Template Jinja2
â”‚   â”œâ”€â”€ base.html                 # Layout base
â”‚   â”œâ”€â”€ auth/                     # Autenticazione
â”‚   â”œâ”€â”€ admin/                    # Amministrazione
â”‚   â”œâ”€â”€ componenti/               # Componenti riusabili
â”‚   â”œâ”€â”€ dashboard/                # Dashboard
â”‚   â”œâ”€â”€ dettaglio/                # Scheda cliente
â”‚   â”œâ”€â”€ documenti_cliente/        # Gestione documenti
â”‚   â”œâ”€â”€ index/                    # Lista clienti
â”‚   â”œâ”€â”€ top_prospect/             # Top Prospect
â”‚   â”œâ”€â”€ trattative/               # Trattative
â”‚   â””â”€â”€ trascrizione/              # Trascrizione audio
â"‚   â"œâ"€â"€ notifiche/                # Widget campanella notifiche
â”œâ”€â”€ db/
â”‚   â””â”€â”€ gestionale.db             # Database SQLite
â”œâ”€â”€ impostazioni/                 # File Excel configurazione
â”œâ”€â”€ clienti/                      # Cartelle clienti (per P.IVA/CF)
â”œâ”€â”€ allegati_note/                # Allegati note (legacy)
â”œâ”€â”€ pdf/                          # PDF da elaborare
â”œâ”€â”€ storico_pdf/                  # PDF elaborati (legacy)
â”œâ”€â”€ exports/                      # File export generati
â”œâ”€â”€ trascrizione/                 # Cartelle trascrizione audio
â”‚   â”œâ”€â”€ attesa/                   # Coda condivisa
â”‚   â”œâ”€â”€ lavorazione/              # 1 file alla volta
â”‚   â””â”€â”€ consumo/                  # Trascrizioni personali
â”œâ”€â”€ logs/                         # Log applicazione
â”œâ”€â”€ scripts/                      # Script bash
â”œâ”€â”€ backup/                       # Backup file
â”œâ”€â”€ documentazione/               # Documentazione .md
â””â”€â”€ Scaricati/                    # File deploy temporanei
```

---

## 3. DATABASE

### 3.1 Tabelle Principali

| Tabella | Descrizione |
|---------|-------------|
| `clienti` | Anagrafica clienti |
| `veicoli` | Parco veicoli |
| `utenti` | Utenti sistema |
| `supervisioni` | Gerarchia commerciali |
| `permessi_catalogo` | Catalogo permessi |
| `utenti_permessi` | Permessi per utente |

### 3.2 Tabelle Relazionali

| Tabella | Descrizione |
|---------|-------------|
| `referenti_clienti` | Referenti aziendali |
| `sedi_cliente` | Sedi operative |
| `clienti_noleggiatori` | Relazione cliente-noleggiatore |
| `collegamenti_clienti` | Relazioni tra clienti |
| `note_clienti` | Note cliente |
| `note_veicoli` | Note veicolo |
| `allegati_note_clienti` | Allegati note |

### 3.3 Tabelle Documenti

| Tabella | Descrizione |
|---------|-------------|
| `documenti_cliente` | Documenti strutturati |
| `car_policy_meta` | Metadati Car Policy |

### 3.4 Tabelle Trattative

| Tabella | Descrizione |
|---------|-------------|
| `trattative` | Trattative commerciali |
| `trattative_avanzamenti` | Storico avanzamenti |

### 3.5 Tabelle Top Prospect

| Tabella | Descrizione |
|---------|-------------|
| `top_prospect` | Candidati/confermati |
| `top_prospect_note` | Note Top Prospect |
| `top_prospect_appuntamenti` | Appuntamenti |
| `top_prospect_attivita` | Storico attivit&agrave; |
| `config_top_prospect` | Parametri analisi |

### 3.6 Tabelle Trascrizione Audio

| Tabella | Descrizione |
|---------|-------------|
| `coda_trascrizioni` | Coda lavori trascrizione audio |

Campi principali: id, utente_id, nome_file_originale, tipo (dashboard/cliente),
stato (attesa/lavorazione/completato/errore), modello, durata_audio,
percorso_audio, percorso_testo, cliente_id, priorita, data_creazione.

### 3.7 Tabelle Notifiche

| Tabella | Descrizione |
|---------|-------------|
| `notifiche` | Notifiche pubblicate (categoria, livello, titolo, messaggio, connettore, dedup) |
| `notifiche_destinatari` | Destinatari per notifica (letta, archiviata, data_lettura) |
| `notifiche_preferenze` | Preferenze canali per utente/categoria (campanella, email, telegram) |
| `notifiche_regole` | Regole routing automatico (categoria -> destinazione) |

Categorie: SISTEMA, TASK, TRATTATIVA, SCADENZA_CONTRATTO, TOP_PROSPECT, TRASCRIZIONE, CLIENTE, ASSEGNAZIONE, DOCUMENTO, IMPORT, BACKUP, COMMERCIALE, REPORT.
Livelli: 1=INFO, 2=AVVISO, 3=IMPORTANTE, 4=ALLARME.
Destinazioni regole: TUTTI, RUOLO:ADMIN, RUOLO:COMMERCIALE, PROPRIETARIO, SUPERVISORE.
18 indici di performance, 17 regole default.

### 3.8 Tabelle Audit

| Tabella | Descrizione |
|---------|-------------|
| `log_accessi` | Login/logout utenti |
| `log_attivita` | Audit trail operazioni |
| `storico_assegnazioni` | Storico assegnazioni commerciali |
| `storico_modifiche` | Modifiche dati |
| `storico_export` | Export effettuati |
| `storico_km` | Rilevazioni chilometriche |

---

## 4. MODULI PYTHON

### 4.1 web_server.py
Server Flask principale con route base:
- `/` - Home (redirect dashboard)
- `/dashboard` - Dashboard
- `/clienti` - Lista clienti
- `/cliente/<id>` - Dettaglio cliente
- `/veicolo/<id>` - Scheda veicolo
- `/flotta/*` - Sezione flotta
- `/statistiche` - Statistiche
- `/admin/*` - Amministrazione
- `/export/*` - Export

### 4.2 database.py
Gestione database principale:
- `get_db_connection()` - Connessione DB
- `init_db()` - Inizializzazione tabelle
- Tabelle: clienti, veicoli, storico_modifiche

### 4.3 database_utenti.py
Gestione utenti e permessi:
- `init_utenti_db()` - Inizializzazione tabelle utenti
- `verifica_credenziali()` - Autenticazione
- `get_subordinati()` - Gerarchia commerciali
- `ha_permesso()` - Verifica permessi
- `registra_accesso()` - Log accessi

### 4.4 auth.py
Decoratori autenticazione:
- `@login_required` - Richiede login
- `@permesso_required(nome)` - Richiede permesso specifico

### 4.5 gestione_commerciali.py
Modulo centralizzato commerciali:
- `format_nome_commerciale()` - Formato "M. Perani"
- `get_commerciale_display()` - Nome da ID
- Funzioni per visibilit&agrave; gerarchica

### 4.6 connettori_stato_cliente.py
Indicatori visivi cliente:
- `get_indicatori_cliente()` - Ritorna dict indicatori
- Car Policy, Documenti scaduti, Trattativa attiva

### 4.7 motore_top_prospect.py
Logica business Top Prospect:
- Analisi candidati basata su parametri
- Gestione stati (candidato, confermato, archiviato)
- Calcolo variazioni percentuali

### 4.8 motore_trattative.py
Logica business Trattative:
- CRUD trattative
- Gestione avanzamenti
- Statistiche

### 4.9 config_trascrizione.py
Configurazione sistema trascrizione audio:
- Legge `impostazioni/trascrizione.conf`
- Parametri: modello, thread, orari, retention, limiti
- `stima_tempo_trascrizione()` - Stima durata elaborazione
- `is_orario_elaborazione()` - Check orario elaborazione (7:00-4:00)
- Upload sempre consentito (nessun blocco orario accettazione)

### 4.10 routes_trascrizione.py
Blueprint trascrizione audio:
- Upload, coda, lista personale, spostamento su cliente
- Rinomina, elimina, scarica testo
- API lista/conta/testo/scarica/elimina per riquadro cliente

### 4.11 worker_trascrizione.py (scripts/)
Worker background trascrizione:
- Polling coda DB ogni 30 secondi
- Caricamento modello faster-whisper (riuso in RAM)
- Conversione audio con ffmpeg
- Trascrizione con VAD filter
- Pulizia retention automatica giornaliera
- Shutdown graceful (SIGTERM) con check stato 'eliminato'
- Recovery job bloccati all'avvio (rimette in coda con priorita' 2)
- Check pre-elaborazione: salta job eliminati nel frattempo
- Protezione orario: verifica tempo stimato vs ore rimaste prima dello stop
  - Scorre candidati, se un job non ci sta prova il prossimo piu' corto
  - Se nessuno ci sta, attende il giorno dopo
- Priorita': 2=recovery/massima, 1=normale, 0=bassa (file grande)

### 4.12 config_notifiche.py
Configurazione sistema notifiche:
- Legge `impostazioni/notifiche.conf` (polling, dedup, pulizia, canali futuri)
- Legge `impostazioni/categorie_notifiche.xlsx` (13 categorie + 4 livelli)
- `get_categorie()`, `get_livelli()` - Dati configurazione
- `get_colore_categoria()`, `get_icona_categoria()` - Per rendering UI
- Cache lru_cache per performance

### 4.13 motore_notifiche.py
Hub centrale sistema notifiche:
- `pubblica_notifica()` - Funzione principale con deduplicazione (codice_evento, finestra 24h)
- Risoluzione automatica destinatari tramite regole DB
- `get_contatore_non_lette()` - Per polling campanella
- `get_notifiche_utente()` - Lista arricchita (colori, icone, tempo relativo)
- `segna_letta()`, `segna_tutte_lette()`, `archivia_notifica()`
- `pulisci_notifiche_scadute()`, `pulisci_notifiche_vecchie()`
- `get_statistiche_notifiche()` - Statistiche per admin

### 4.14 connettori_notifiche/sistema.py
Primo connettore di riferimento:
- `notifica_avvio_sistema()` - Livello INFO, dest. ADMIN
- `notifica_errore_sistema()` - Livello ALLARME, no dedup
- `notifica_manutenzione()` - Livello AVVISO, dedup via data
- `notifica_test()` - Per testing, destinatario specifico

---

## 5. BLUEPRINT E ROUTE

### 5.1 routes_auth.py
```
/auth/login          GET/POST  Login
/auth/logout         GET       Logout
/auth/cambio-password GET/POST Cambio password
/auth/completa-profilo GET/POST Primo accesso
/auth/profilo        GET/POST  Profilo personale
```

### 5.2 routes_admin_utenti.py
```
/admin/utenti/              GET   Lista utenti
/admin/utenti/nuovo         POST  Crea utente
/admin/utenti/<id>          GET   Dettaglio utente
/admin/utenti/<id>/permessi POST  Modifica permessi
/admin/utenti/<id>/ruolo    POST  Modifica ruolo
/admin/utenti/storico-assegnazioni GET Storico
/admin/utenti/log           GET   Log accessi
```

### 5.3 routes_flotta_commerciali.py
```
/flotta/per-commerciale      GET   Report per commerciale
/flotta/gestione-commerciali GET   Gestione assegnazioni
/flotta/assegna-commerciali  POST  Assegna clienti
```

### 5.4 routes_note_clienti.py
```
/note/<cliente_id>/lista     GET   Lista note
/note/<cliente_id>/crea      POST  Crea nota
/note/<cliente_id>/<nota_id>/modifica POST Modifica
/note/<cliente_id>/<nota_id>/elimina  POST Elimina
/note/<cliente_id>/<nota_id>/fissa    POST Fissa/sfissa
/note/<cliente_id>/cestino   GET   Note eliminate
```

### 5.5 routes_documenti_cliente.py
```
/api/cliente/<id>/documenti/<tipo>         GET   Lista documenti
/api/cliente/<id>/documenti/<tipo>/upload  POST  Upload
/api/cliente/<id>/documenti/<tipo>/elimina POST  Elimina
/api/cliente/<id>/documenti/<tipo>/rinomina POST Rinomina
/api/cliente/<id>/documenti/car-policy/fissa POST Fissa file
/api/cliente/<id>/documenti/car-policy/converti-pdf POST Converti
```

### 5.6 routes_documenti_strutturati.py
```
/api/cliente/<id>/documenti-strutturati/info   GET   Info documenti
/api/cliente/<id>/documenti-strutturati/upload POST  Upload
/api/cliente/<id>/documenti-strutturati/elimina POST Elimina
/api/cliente/<id>/banca-iban                   POST  Salva IBAN
/api/cliente/<id>/note-documenti               POST  Note documenti
```

### 5.7 routes_sedi_cliente.py
```
/api/cliente/<id>/sedi       GET    Lista sedi
/api/cliente/<id>/sedi       POST   Crea sede
/api/cliente/<id>/sedi/<sid> PUT    Modifica sede
/api/cliente/<id>/sedi/<sid> DELETE Elimina sede
```

### 5.8 routes_collegamenti_clienti.py
```
/api/collegamenti/tipi-relazione  GET   Tipi relazione
/api/collegamenti/cerca-clienti   GET   Cerca clienti
/api/collegamenti/aggiungi        POST  Crea collegamento
/api/collegamenti/rimuovi         POST  Rimuovi collegamento
/api/collegamenti/modifica        POST  Modifica relazione
/admin/storico-collegamenti       GET   Storico
```

### 5.9 routes_noleggiatori_cliente.py
```
/api/cliente/<id>/crm              PUT    Aggiorna stato CRM
/api/cliente/<id>/noleggiatori     GET    Lista noleggiatori
/api/cliente/<id>/noleggiatori     POST   Aggiungi noleggiatore
/api/cliente/<id>/noleggiatori/<nid> PUT  Modifica
/api/cliente/<id>/noleggiatori/<nid> DELETE Elimina
/api/noleggiatori/lista            GET    Lista tutti noleggiatori
```

### 5.10 routes_trattative.py
```
/trattative/                    GET   Pagina trattative
/trattative/api/lista           GET   Lista trattative
/trattative/api/<id>            GET   Dettaglio
/trattative/api/crea            POST  Crea trattativa
/trattative/api/<id>/modifica   POST  Modifica
/trattative/api/<id>/avanzamento POST Aggiorna avanzamento
/trattative/api/<id>/elimina    POST  Elimina (soft delete)
/trattative/api/<id>/ripristina POST  Ripristina
/trattative/api/lista_cancellate GET  Lista cancellate
```

### 5.11 routes_top_prospect.py
```
/top-prospect/                  GET   Pagina principale
/top-prospect/api/candidati     GET   Lista candidati
/top-prospect/api/confermati    GET   Lista confermati
/top-prospect/api/archiviati    GET   Lista archiviati
/top-prospect/api/conferma/<id> POST  Conferma candidato
/top-prospect/api/archivia/<id> POST  Archivia
/top-prospect/api/ripristina/<id> POST Ripristina
/top-prospect/api/scarta/<id>   POST  Scarta
/top-prospect/api/<id>/note     GET   Note
/top-prospect/api/<id>/note/crea POST Crea nota
/top-prospect/api/<id>/appuntamenti GET Appuntamenti
/top-prospect/api/<id>/appuntamenti/crea POST Crea appuntamento
/top-prospect/api/parametri     GET/POST Parametri analisi
/top-prospect/api/analizza      POST  Avvia analisi
```

### 5.12 routes_trascrizione.py
```
/trascrizione/                         GET   Pagina principale
/trascrizione/upload                   POST  Upload audio
/trascrizione/coda                     GET   Stato coda
/trascrizione/mie                      GET   Le mie trascrizioni
/trascrizione/mie/<id>/testo           GET   Scarica testo
/trascrizione/sposta/<id>              POST  Sposta su cliente
/trascrizione/rinomina/<id>            POST  Rinomina
/trascrizione/elimina/<id>             POST  Elimina da consumo
/trascrizione/cliente/<id>/lista       GET   Lista trascrizioni cliente
/trascrizione/cliente/<id>/conta       GET   Conteggio (per badge)
/trascrizione/cliente/<id>/testo/<f>   GET   Leggi testo
/trascrizione/cliente/<id>/scarica/<f> GET   Download file
/trascrizione/cliente/<id>/elimina/<f> DELETE Elimina da cliente
```

### 5.13 routes_notifiche.py
```
/notifiche/api/contatore         GET   Contatore non lette (polling campanella)
/notifiche/api/recenti           GET   Lista notifiche recenti (dropdown)
/notifiche/api/<id>/letta        POST  Segna notifica come letta
/notifiche/api/tutte-lette       POST  Segna tutte come lette (opz. filtro categoria)
/notifiche/api/<id>/archivia     POST  Archivia notifica
/notifiche/api/test              POST  Genera notifica test (solo admin)
/notifiche/api/statistiche       GET   Statistiche notifiche (solo admin)
```

---

## 6. TEMPLATE HTML

### 6.1 Struttura Modulare

```
templates/componente/
    _riquadro.html      # Card/sezione HTML
    _modal.html         # Modal popup
    _scripts.html       # JavaScript dedicato
    _styles.html        # CSS dedicato
```

### 6.2 Include Jinja2
```html
{% include "componente/_riquadro.html" %}
{% include "componente/_modal.html" %}
{% include "componente/_scripts.html" %}
{% include "componente/_styles.html" %}
```

### 6.3 Convenzioni Naming
| Prefisso | Uso |
|----------|-----|
| `_riquadro` | Card/box UI |
| `_modal` | Finestre modali |
| `_scripts` | Codice JavaScript |
| `_styles` | Fogli di stile |
| `_griglia` | Tabelle/griglie |
| `_filtri` | Pannelli filtro |
| `_header` | Intestazioni |

---

## 7. CONFIGURAZIONE

### 7.1 File Excel (impostazioni/)

| File | Contenuto |
|------|-----------|
| `noleggiatori.xlsx` | Lista noleggiatori con colori |
| `noleggiatori_assistenza.xlsx` | Link assistenza e portali |
| `stati_cliente.xlsx` | Stati CRM cliente |
| `stati_noleggiatore.xlsx` | Stati relazione noleggiatore |
| `stati_crm.xlsx` | Mapping stati CRM |
| `stati_trattativa.xlsx` | Stati trattativa |
| `tipi_trattativa.xlsx` | Tipologie trattativa |
| `tipi_relazione.xlsx` | Tipi collegamento clienti |
| `scaglioni_flotta.xlsx` | Fasce dimensione flotta |
| `tipologie_veicolo.xlsx` | Tipi veicolo |
| `mappatura_ip.xlsx` | Mapping IP per zone |

### 7.2 File Configurazione Trascrizione (`impostazioni/trascrizione.conf`)

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `MODELLO` | large-v3-turbo | Modello faster-whisper |
| `NUM_THREADS` | 10 | Thread CPU per trascrizione |
| `COMPUTE_TYPE` | int8 | Tipo calcolo (int8/float16) |
| `ORA_INIZIO_ACCETTAZIONE` | 07:00 | Inizio accettazione upload |
| `ORA_FINE_ACCETTAZIONE` | 19:00 | Fine accettazione upload |
| `ORA_FINE_ELABORAZIONE` | 04:00 | Fine elaborazione notturna |
| `RETENTION_AUDIO_CLIENTE` | 180 | Giorni retention audio cliente |
| `RETENTION_TESTO_CONSUMO` | 21 | Giorni retention testo consumo |
| `MAX_FILE_SIZE_MB` | 500 | Dimensione massima upload |

### 7.3 File Configurazione Notifiche (`impostazioni/notifiche.conf`)

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `POLLING_SECONDI` | 30 | Intervallo polling campanella |
| `DEDUP_MINUTI` | 1440 | Finestra deduplicazione (24h) |
| `PULIZIA_GIORNI_LETTE` | 90 | Retention notifiche lette |
| `PULIZIA_GIORNI_NON_LETTE` | 180 | Retention notifiche non lette |
| `PULIZIA_GIORNI_ARCHIVIATE` | 30 | Retention notifiche archiviate |
| `LIMITE_DROPDOWN` | 20 | Max notifiche nel dropdown |

File `impostazioni/categorie_notifiche.xlsx`: 13 categorie (SISTEMA, TASK, TRATTATIVA, ecc.) con colore e icona Bootstrap Icons, 4 livelli (INFO, AVVISO, IMPORTANTE, ALLARME) con colore.

### 7.4 config.py
```python
DATABASE_PATH = 'db/gestionale.db'
UPLOAD_FOLDER = 'uploads'
SECRET_KEY = '...'
```

### 7.4 config_percorsi.py
Definisce tutti i path delle cartelle:
- `CARTELLA_CLIENTI`
- `CARTELLA_ALLEGATI`
- `CARTELLA_PDF`
- `CARTELLA_EXPORT`

---

## 8. REGOLE DI SVILUPPO

### 8.1 Encoding (Regola Aurea #1)
**OBBLIGATORIO**: Usare solo entit&agrave; HTML
```html
<!-- CORRETTO -->
&euro; &agrave; &egrave; &igrave; &ograve; &ugrave;

<!-- VIETATO -->
â‚¬ Ã  Ã¨ Ã¬ Ã² Ã¹
```

### 8.2 Icone
**OBBLIGATORIO**: Solo Bootstrap Icons
```html
<!-- CORRETTO -->
<i class="bi bi-person"></i>

<!-- VIETATO -->
ðŸ“Œ ðŸ” ðŸ“‹ (emoji Unicode)
```

### 8.3 Modifiche Chirurgiche (Regola Aurea #2)
- Preferire `sed`/`str_replace` a riscrittura file
- Verificare encoding dopo ogni modifica
- Confrontare con `diff` prima di applicare

### 8.4 ID Utenti (Regola Aurea #7)
```python
# Database: INTEGER
id = 1

# Display: sempre 6 cifre
f"{id:06d}"  # "000001"

# Jinja2
{{ "%06d"|format(utente.id) }}
```

### 8.5 Commerciali (Regola Aurea #8)
- Usare `commerciale_id` (INTEGER), non `commerciale` (TEXT)
- Route commerciali nel blueprint `routes_flotta_commerciali.py`
- Formato display: "M. Perani" (iniziale + cognome)

---

## 9. DEPLOY E MANUTENZIONE

### 9.1 Avvio Server
```bash
~/gestione_flotta/scripts/gestione_flotta.sh start
```

### 9.2 Riavvio Server
```bash
~/gestione_flotta/scripts/gestione_flotta.sh restart
```

### 9.3 Stop Server
```bash
~/gestione_flotta/scripts/gestione_flotta.sh stop
```

### 9.4 Backup
I backup vengono creati automaticamente nella cartella `backup/` con timestamp.

### 9.5 Deploy File
1. Scaricare file in `~/gestione_flotta/Scaricati/`
2. Backup file esistente: `cp file.py file.py.bak_$(date +%Y%m%d_%H%M%S)`
3. Spostare nuovo file: `mv ~/gestione_flotta/Scaricati/file.py destinazione/`
4. Riavviare server

### 9.6 Fix Encoding Post-Trasferimento
```bash
~/gestione_flotta/scripts/fix_encoding.sh file.py
```

### 9.7 Import Creditsafe
- Admin &rarr; Import PDF
- Oppure cron automatico configurabile

### 9.8 Pulizia Log
- Admin &rarr; Pulisci Log (retention 7 giorni)

### 9.9 Worker Trascrizione Audio
```bash
# Stato servizio
sudo systemctl status trascrizione-worker

# Riavvio worker (NON riavvia Flask)
sudo systemctl restart trascrizione-worker

# Log worker
tail -f ~/gestione_flotta/logs/trascrizione.log
```

Parametri systemd:
- CPUQuota=600% (6 core su 12)
- MemoryMax=8G
- Restart automatico dopo 30 secondi

---

## APPENDICE A: Permessi Catalogo

| Codice | Descrizione |
|--------|-------------|
| `admin` | Accesso completo amministrazione |
| `clienti_lettura` | Visualizzazione clienti |
| `clienti_modifica` | Modifica dati clienti |
| `clienti_assegnabili` | Pu&ograve; essere assegnato a clienti |
| `flotta_lettura` | Visualizzazione flotta |
| `flotta_assegnazioni` | Gestione assegnazioni |
| `veicoli_modifica` | Modifica dati veicoli |
| `documenti_upload` | Upload documenti |
| `documenti_elimina` | Eliminazione documenti |
| `note_scrittura` | Creazione/modifica note |
| `trattative_gestione` | Gestione trattative |
| `top_prospect_gestione` | Gestione Top Prospect |
| `export_excel` | Export dati |
| `utenti_gestione` | Gestione utenti (admin) |
| `statistiche` | Accesso statistiche |
| `import_creditsafe` | Import PDF Creditsafe |

---

## APPENDICE B: Struttura Cartelle Cliente

```
clienti/
â”œâ”€â”€ IT00552060980/              # Cartella per P.IVA
â”‚   â”œâ”€â”€ creditsafe/             # PDF Creditsafe
â”‚   â”œâ”€â”€ car_policy/             # Documenti Car Policy
â”‚   â”œâ”€â”€ contratti/              # Contratti firmati
â”‚   â”œâ”€â”€ quotazioni/             # Preventivi
â”‚   â”œâ”€â”€ documenti/              # Documenti strutturati
â”‚   â”œâ”€â”€ allegati_note/          # Allegati note
â”‚   â””â”€â”€ trascrizioni/           # Trascrizioni audio (.txt permanenti)
â””â”€â”€ RSSMRA80A01H501Z/           # Cartella per CF (persone fisiche)
    â””â”€â”€ ...
```

---

*Documento generato il 2026-02-04*
