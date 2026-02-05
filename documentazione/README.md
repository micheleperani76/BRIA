# GESTIONE FLOTTA

Sistema integrato per la gestione clienti, veicoli e dati Creditsafe.

## 📁 Struttura Cartelle

```
gestione_flotta/
├── app/                    # Moduli Python
│   ├── __init__.py
│   ├── config.py           # Configurazione centralizzata
│   ├── database.py         # Gestione database SQLite
│   ├── import_creditsafe.py # Import PDF Creditsafe
│   ├── utils.py            # Funzioni utilità
│   └── web_server.py       # Server web Flask
├── db/                     # Database
│   └── gestionale.db       # Database unico
├── logs/                   # Log e file temporanei (retention 7 giorni)
├── pdf/                    # Input: PDF da elaborare
├── scripts/                # Script bash
│   ├── gestione_flotta.sh  # Script principale (menu)
│   ├── autoimport.sh       # Per crontab (import automatico)
│   └── avvia_server.sh     # Per crontab (@reboot)
├── storico_pdf/            # Archivio PDF elaborati (organizzato A-Z)
│   ├── 0-9/
│   ├── A/
│   ├── B/
│   └── ...
├── templates/              # Template HTML
├── main.py                 # Entry point principale
└── README.md               # Questa documentazione
```

## 🚀 Installazione

### 1. Requisiti
```bash
sudo apt install python3 python3-pip
pip3 install flask openpyxl pillow --break-system-packages
```

### 2. Prima esecuzione
```bash
cd ~/gestione_flotta
chmod +x scripts/*.sh
python3 main.py init   # Inizializza database
```

### 3. Avvio server
```bash
# Metodo 1: Python diretto
python3 main.py server

# Metodo 2: Script bash
./scripts/gestione_flotta.sh start

# Metodo 3: Menu interattivo
./scripts/gestione_flotta.sh menu
```

### 4. Configurazione Crontab
```bash
crontab -e
```

Aggiungi:
```cron
# Gestione Flotta - Avvio server all'avvio sistema
@reboot /home/michele/gestione_flotta/scripts/avvia_server.sh

# Gestione Flotta - Import PDF ogni ora (minuto 5)
5 * * * * /home/michele/gestione_flotta/scripts/autoimport.sh
```

## 📊 Database Unificato

Il database `gestionale.db` contiene:

### Tabella `clienti`
Dati unificati da flotta + Creditsafe:
- **Identificativi**: nome_cliente, p_iva, cod_fiscale, numero_registrazione
- **Operativi flotta**: commerciale (NON sovrascritto da Creditsafe)
- **Dati Creditsafe**: ragione_sociale, indirizzo, telefono, pec, forma_giuridica, ecc.
- **Rating**: score (A-E), punteggio_rischio, credito
- **Bilancio**: valore_produzione, patrimonio_netto, utile, debiti (anno corrente e precedente)

### Tabella `veicoli`
Dati flotta veicoli:
- noleggiatore, targa, marca, modello, tipo, alimentazione
- durata, inizio, scadenza, km, franchigia, canone
- driver, contratto, commerciale

### Tabella `storico_modifiche`
Log di tutte le modifiche ai dati.

## 🔄 Flusso Import PDF

1. **Copia PDF** nella cartella `pdf/`
2. **Import** (manuale o crontab):
   - Estrae testo dal PDF (formato ZIP con immagini)
   - Estrae dati aziendali con pattern regex
   - Cerca cliente per P.IVA:
     - **Se esiste**: aggiorna dati Creditsafe (NON sovrascrive commerciale)
     - **Se non esiste**: crea nuovo cliente
   - Copia PDF in `storico_pdf/LETTERA/` (organizzato A-Z)
   - Rimuove PDF da cartella input

## 💻 Comandi Python

```bash
# Avvia server web
python3 main.py server
python3 main.py server -p 8080  # Porta diversa

# Import PDF
python3 main.py import

# Inizializza database
python3 main.py init

# Pulisci log vecchi
python3 main.py pulisci

# Info sistema
python3 main.py info
```

## 🖥️ Comandi Bash

```bash
./scripts/gestione_flotta.sh start    # Avvia server
./scripts/gestione_flotta.sh stop     # Ferma server
./scripts/gestione_flotta.sh restart  # Riavvia
./scripts/gestione_flotta.sh status   # Stato sistema
./scripts/gestione_flotta.sh import   # Import PDF
./scripts/gestione_flotta.sh clean    # Pulisci log
./scripts/gestione_flotta.sh logs     # Visualizza log
./scripts/gestione_flotta.sh menu     # Menu interattivo
```

## 🌐 Interfaccia Web

- **Home**: http://localhost:5001
  - Lista clienti con filtri avanzati
  - Score, provincia, regione, forma giuridica, credito
  - Click su card score per filtrare
  
- **Flotta**: http://localhost:5001/flotta
  - Dashboard veicoli
  - Report per noleggiatore/commerciale
  - Gestione assegnazioni massive
  
- **Statistiche**: http://localhost:5001/statistiche
  - Statistiche generali
  
- **Amministrazione**: http://localhost:5001/admin
  - Import PDF manuale (via web)
  - Pulizia log
  - Info sistema

## 📋 Note Importanti

### Logica Aggiornamento
- I dati **Creditsafe** sovrascrivono i dati anagrafici
- Il campo **commerciale** viene dalla flotta e NON viene sovrascritto
- Lo storico modifiche traccia ogni cambiamento

### PDF Storico
- I PDF originali vengono COPIATI in `storico_pdf/LETTERA/`
- Organizzazione alfabetica per evitare sovraffollamento
- Mai cancellati automaticamente

### Log e Retention
- Log in `logs/` con nome `tipo_YYYY-MM-DD.log`
- Retention automatica: 7 giorni
- Pulizia manuale o via crontab

## 🔧 Configurazione

Modifica `app/config.py` per:
- Percorsi cartelle
- Porta server web
- Giorni retention log
- Pattern estrazione dati

## 📝 Versione

- **1.0.0** (2025-01-12)
  - Prima versione con database unificato
  - Struttura modulare
  - Storico PDF organizzato A-Z

---

## Novit&agrave; Febbraio 2026

### Trascrizione Audio
- Trascrizione automatica file audio con faster-whisper (large-v3-turbo)
- Upload drag & drop sempre consentito, coda con priorita', worker background systemd
- Spostamento trascrizioni su clienti con ricerca fuzzy
- Riquadro trascrizioni cliente: upload diretto, rinomina, modifica testo, ricerca full-text
- Protezione orario: posticipa job troppo lunghi, prova job piu' corti
- Recovery automatico job bloccati, check job eliminati, graceful shutdown
- Stima tempo coda cumulativa (minuti/ore/giorni)
- Eliminazione job in coda (proprio o admin)
- Performance: ~0.42x realtime (54 min audio = 22 min elaborazione)

### Sistema Notifiche
- Hub centrale notifiche con deduplicazione e routing automatico destinatari
- 13 categorie (SISTEMA, TASK, TRATTATIVA, TOP_PROSPECT, ecc.) + 4 livelli (INFO/AVVISO/IMPORTANTE/ALLARME)
- Widget campanella: visibile solo con notifiche non lette, trascinabile nei 4 angoli
- Posizione campanella rispetta sidebar, salvata in localStorage
- Connettori modulari: ogni modulo genera notifiche tramite pubblica_notifica()
- Regole DB per routing destinatari (TUTTI, RUOLO:ADMIN, PROPRIETARIO, ecc.)
- API polling contatore ogni 30s, dropdown recenti, segna letta/archivia
- Predisposto per canali futuri: email SMTP, Telegram

### Export Avanzato
- Export Top Prospect confermati in Excel/CSV
- Export Trattative con filtri multipli (stato, tipo, noleggiatore, commerciale, date)
- Interfaccia 3 tab unificata (Clienti, Top Prospect, Trattative)
