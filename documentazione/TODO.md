# TODO - Gestione Flotta

Ultimo aggiornamento: 09 Febbraio 2026

---

## COMPLETATI RECENTEMENTE

### Import CRM Zoho (09 Febbraio 2026)
- [x] STEP 1: Migrazione DB (13+4 campi, 5 tabelle satellite, 11 indici)
- [x] STEP 2: Import Accounts (24 aggiornati, 2613 creati, 4 errori dati CRM)
- [x] STEP 3: Import Scadenze (879 veicoli INSTALLATO, 507 storicizzati, 0 errori)
- [~] STEP 4: Frontend (in corso)

### Ticker Broadcasting
- [x] Fase 1-4 completate
- [x] Config aspetto testo, toggle automatici, cron giornaliero

---

## IN CORSO

### Import CRM Zoho - STEP 4: Frontend
- [ ] Box upload admin multi-funzionale (Accounts, Scadenze)
- [x] Scheda cliente: riquadro dati CRM (stato, profilazione, flotta, consensi, alert)
- [x] Pagina Installato dedicata con stats, filtri, colorazione scadenze
- [ ] Filtri per tipo_veicolo (Installato/Extra) nelle viste flotta
- [x] Pagina storico dismessi (/installato/storico) con retention 5 anni

### Top Prospect
- [ ] Test completo sincronizzazione Google Calendar
- [ ] Test condivisione calendario con altri account

### Sistema Notifiche - Allineamenti
- [ ] Fine-tuning allineamenti grafici campanella

---

## PROSSIMI PASSI (Priorita' Alta)

### Import CRM Zoho - Sales Orders (SOSPESO)
- [ ] Analisi file Sales Orders (933 record)
- [ ] Script import_sales_orders_crm.py
- [ ] Collegamento trattative esistenti

### Sistema Notifiche - Fase 2: Sistema Task + Connettore Task
- [ ] Tabella `task` nel database (assegnatario, scadenza, stato, priorita')
- [ ] CRUD task (crea, modifica, completa, elimina)
- [ ] Connettore notifiche per task (notifica assegnazione, scadenza, completamento)
- [ ] Interfaccia gestione task
- [ ] Integrazione campanella con notifiche task

### Sistema Notifiche - Fase 3: Connettori Rimanenti
- [ ] Connettore SCADENZA_CONTRATTO (veicoli in scadenza)
- [ ] Connettore CLIENTE (nuovo cliente importato, modifica dati)
- [ ] Connettore ASSEGNAZIONE (cambio commerciale)
- [ ] Connettore DOCUMENTO (nuovo documento caricato)

### Sistema Notifiche - Fase 4: Canali Uscita Avanzati
- [ ] Canale email SMTP (invio notifiche via email)
- [ ] Canale Telegram (bot notifiche)
- [ ] Pannello preferenze utente (scegli canali per categoria)
- [ ] Digest giornaliero/settimanale via email

### Sistema Notifiche - Miglioramenti Campanella
- [ ] Pagina storico notifiche completa (/notifiche)
- [ ] Pannello admin statistiche notifiche
- [ ] Filtro notifiche per categoria nel dropdown

### Sistema Trascrizione Audio
- [ ] Test con piu' utenti contemporanei

### Top Prospect
- [ ] Notifiche email per appuntamenti imminenti
- [ ] Reminder automatici (es. 1 giorno prima)

### Trattative
- [ ] Collegamento trattativa -> Top Prospect
- [ ] Dashboard riepilogo trattative per commerciale
- [ ] Statistiche conversione (candidato -> trattativa -> cliente)

---

## BACKLOG (Priorita' Media/Bassa)

### Miglioramenti UI
- [ ] Dark mode
- [ ] Responsive migliorato per mobile
- [ ] Preferenze utente persistenti

### Reportistica
- [ ] Grafici andamento flotta nel tempo
- [ ] Report scadenze contratti
- [ ] Analisi produttivita' commerciali

### Encoding
- [ ] Eseguire fix_encoding.sh dopo ogni deploy via browser

### Test Pendenti
- [ ] Test completo note clienti vista ristretta (crea/modifica/fissa/elimina)
- [ ] Test completo note clienti vista fullscreen
- [ ] Test cestino note clienti (ripristina e elimina definitivo)
- [ ] Test allegati note (carica/scarica/elimina)
- [ ] Verificare soft delete note veicoli
