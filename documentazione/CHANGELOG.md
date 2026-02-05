# CHANGELOG - Aggiornamenti Recenti

## 2026-02-05 - Integrazione GitHub

### Repository GitHub
- Creato repository: https://github.com/micheleperani76/BRIA
- Configurato `.gitignore` per escludere: db, clienti, credenziali, log, allegati, audio, backup
- Primo push: 243 file di codice, template, documentazione e configurazione
- Cartella `account_esterni/` creata e esclusa da git

### raccolta_file_ia.sh v4.0
- Nuova funzione `sync_github()`: git add + commit interattivo + push
- Nuove opzioni: `--no-git`, `--solo-git`, `--solo-backup`
- Backup ZIP aggiornato: esclude anche `.git/`, `clienti/`, `db/`, `account_esterni/`
- Raccolta file IA: aggiunta cartella `app/connettori_notifiche/`
- Tree: esclusa cartella `.git` dall'output

### Documentazione aggiornata
- `INIZIO_SESSIONE.md` - Aggiunta sezione fonte file GitHub e sync fine sessione
- `REGOLE_CLAUDE.md` v6.0 - Checklist aggiornata con sync GitHub, struttura progetto completa
- `README.md` - Aggiunta sezione repository e flusso sync Claude
- `CHANGELOG.md` - Questa voce

---

## 2026-02-04 - Sistema Notifiche Fase 1

### Sistema Notifiche - Fondamenta Complete
**Configurazione**
- File `impostazioni/notifiche.conf` - Parametri hub (polling 30s, dedup 24h, pulizia 90/180/30 giorni)
- File `impostazioni/categorie_notifiche.xlsx` - 13 categorie + 4 livelli con colori/icone
- `app/config_notifiche.py` - Reader configurazione con lru_cache

**Database (migrazione_notifiche.py)**
- Tabella `notifiche` (13 colonne): categoria, livello, titolo, messaggio, url_azione, connettore, codice_evento, dedup, scadenza, ricorrente
- Tabella `notifiche_destinatari` (7 colonne): notifica_id, utente_id, letta, data_lettura, archiviata
- Tabella `notifiche_preferenze` (8 colonne): canali per utente/categoria (campanella, email, telegram)
- Tabella `notifiche_regole` (8 colonne): routing automatico per categoria/connettore
- 18 indici di performance, 17 regole default (TASK, SISTEMA, SCADENZA, ecc.)
- Destinazioni supportate: TUTTI, RUOLO:ADMIN, RUOLO:COMMERCIALE, PROPRIETARIO, SUPERVISORE

**Motore Hub (motore_notifiche.py)**
- `pubblica_notifica()` - Funzione centrale con deduplicazione via codice_evento (finestra 24h)
- Risoluzione automatica destinatari tramite regole DB
- `get_contatore_non_lette()` - Per polling campanella
- `get_notifiche_utente()` - Lista arricchita con colori/icone/tempo_fa
- `segna_letta()`, `segna_tutte_lette()`, `archivia_notifica()`
- `pulisci_notifiche_scadute()`, `pulisci_notifiche_vecchie()`
- `get_statistiche_notifiche()` - Stats per pannello admin

**Connettore Sistema (connettori_notifiche/sistema.py)**
- `notifica_avvio_sistema()`, `notifica_errore_sistema()`, `notifica_manutenzione()`, `notifica_test()`
- Pattern di riferimento per futuri connettori

**API Campanella (routes_notifiche.py)**
- `GET /notifiche/api/contatore` - Polling ogni 30s
- `GET /notifiche/api/recenti` - Lista per dropdown
- `POST /notifiche/api/<id>/letta` - Segna letta
- `POST /notifiche/api/tutte-lette` - Segna tutte
- `POST /notifiche/api/<id>/archivia` - Archivia
- `POST /notifiche/api/test` - Test (solo admin)
- `GET /notifiche/api/statistiche` - Stats admin

**Widget Campanella (templates/notifiche/_campanella.html)**
- Visibile SOLO quando ci sono notifiche non lette (scompare a contatore 0)
- Trascinabile nei 4 angoli dello schermo (drag mouse + touch)
- Posizione salvata in localStorage
- Posizioni sinistre rispettano larghezza sidebar (dinamico)
- Dropdown con lista notifiche, icone colorate, tempo relativo
- Animazione bell-ring su nuove notifiche
- Azioni: segna letta (naviga a url_azione), archivia con fade-out

### File Nuovi
- `impostazioni/notifiche.conf` - Configurazione hub notifiche
- `impostazioni/categorie_notifiche.xlsx` - Categorie e livelli
- `app/config_notifiche.py` - Reader configurazione
- `app/motore_notifiche.py` - Hub centrale notifiche
- `app/routes_notifiche.py` - Blueprint API campanella
- `app/connettori_notifiche/__init__.py` - Package connettori
- `app/connettori_notifiche/sistema.py` - Connettore sistema
- `scripts/migrazione_notifiche.py` - Migrazione database
- `templates/notifiche/_campanella.html` - Widget campanella

### File Modificati
- `app/web_server.py` - Import + registrazione blueprint notifiche_bp, context processor polling
- `templates/base.html` - Include campanella

---

## 2026-02-04 - Trascrizioni Cliente + Protezioni Worker

### Fix
- Corretto login HTTP 500 (auth.py: accesso `.get()` su `sqlite3.Row`)

### Riquadro Trascrizioni Cliente (documenti_cliente)
- Upload drag & drop multiplo con progress bar sequenziale
- Rinomina file (rinomina anche audio associato)
- Modifica/correzione testo trascritto con salvataggio
- Ricerca full-text nelle trascrizioni del cliente
- Eliminazione file trascrizione
- Ritorno automatico alla lista dopo chiusura anteprima

### Protezioni Worker Trascrizione
- **Recovery job bloccati**: all'avvio trova job in 'lavorazione' e li rimette in coda
- **Graceful shutdown**: SIGTERM interrompe trascrizione, rimette job in attesa
- **Check pre-elaborazione**: verifica che il job non sia stato eliminato
- **Check shutdown**: non sovrascrive stato 'eliminato' durante shutdown
- **Protezione orario**: calcola se il job puo' completarsi prima dello stop (4:00)
  - Scorre candidati in ordine, se un job non ci sta prova il prossimo piu' corto
  - Se nessuno ci sta, attende il giorno dopo
- Priorita' recovery corretta (2 = massima, 1 = normale, 0 = bassa)

### Miglioramenti Coda
- Upload sempre consentito (rimosso blocco orario accettazione)
- Stima tempo coda cumulativa (somma job davanti + in lavorazione)
- Formato tempo leggibile (~X minuti / ~Xh Xmin / ~Xg Xh)
- Bottone elimina job in coda (proprio o admin tutti)

### Nuove Route
- `/trascrizione/cliente/<id>/rinomina-file` POST - Rinomina file trascrizione
- `/trascrizione/cliente/<id>/modifica/<path>` POST - Salva testo modificato
- `/trascrizione/cliente/<id>/cerca?q=` GET - Ricerca full-text
- `/trascrizione/elimina-coda/<id>` POST - Elimina job in attesa dalla coda

### File Modificati/Creati
- `app/auth.py` - Fix accesso sqlite3.Row
- `app/routes_trascrizione.py` - 4 nuove route (rinomina, modifica, cerca, elimina-coda)
- `scripts/worker_trascrizione.py` - Recovery, protezione orario, check eliminato
- `templates/documenti_cliente/trascrizioni/_styles.html` (NUOVO)
- `templates/documenti_cliente/trascrizioni/_modal.html` - Upload, ricerca, anteprima
- `templates/documenti_cliente/trascrizioni/_scripts.html` - JS completo
- `templates/documenti_cliente.html` - Include styles
- `templates/trascrizione/_scripts.html` - Bottone elimina coda, ruoloUtente

---

## 2026-02-03 - Export Trattative + Sistema Trascrizione Audio

### Export e Stampa
- Export Top Prospect confermati in Excel/CSV
- Export Trattative con filtri (stato, tipo, noleggiatore, commerciale, date)
- Interfaccia 3 tab (Clienti, Top Prospect, Trattative)
- Anteprima dati prima dell'export
- Filtro date nel tab trattative

### Sistema Trascrizione Audio (completo)
**Backend**
- Worker background con faster-whisper (modello large-v3-turbo)
- Servizio systemd con CPUQuota 600% (6 core)
- Coda condivisa con priorita', retention automatica
- Conversione audio automatica (AAC, MP3, WAV, OGG)
- Orari operativi: accettazione 07-19, elaborazione 07-04
- Performance: ~0.42x realtime (54 min audio = 22 min elaborazione)

**API Flask (Blueprint routes_trascrizione.py)**
- Upload audio con validazione formato/dimensione
- Stato coda, lista trascrizioni, spostamento su cliente
- Rinomina, elimina, scarica testo

**Frontend**
- Pagina /trascrizione con layout 2 colonne
- Upload drag & drop con progress bar
- Auto-refresh lista, badge stato, modal coda
- Widget FAB flottante (visibile solo se job in corso)
- Link nel menu sidebar

**Riquadro nella Scheda Cliente**
- 6 riquadro "Trascrizioni" in documenti cliente
- Modal lista con anteprima testo, download, elimina
- Badge conteggio automatico

### File Nuovi
- `impostazioni/trascrizione.conf` - Configurazione worker
- `app/config_trascrizione.py` - Reader configurazione
- `app/routes_trascrizione.py` - Blueprint API trascrizione
- `scripts/worker_trascrizione.py` - Worker background
- `templates/trascrizione/*.html` - 8 template frontend
- `templates/documenti_cliente/trascrizioni/*.html` - 3 template riquadro

### File Modificati
- `app/export_excel.py` - Aggiunto export trattative/top prospect
- `templates/export_excel.html` - Tab trattative e top prospect
- `templates/base.html` - Link sidebar trascrizione, FAB widget
- `templates/documenti_cliente.html` - 6 riquadro trascrizioni

---

## 2026-01-30 - Ricerca Smart Dashboard + Fuzzy Search

### Nuove Funzionalita'

**Dashboard Search**
- Aggiunta barra di ricerca smart nella pagina Dashboard
- Posizione centrata nell'header
- Supporto comandi @com e @ope
- Risultati con: nome, telefono, email, referente principale

**Ricerca Fuzzy**
- La ricerca ora normalizza i caratteri speciali
- Rimuove automaticamente: punti, spazi, trattini, &, apostrofi
- Esempio: cercare "atib" trova "A.T.I.B. SRL"

**Fix Comandi @com/@ope**
- Corretto bug logico nel trigger dei comandi
- @com mostra commerciali, @ope mostra operatori
- Admin e utenti disattivati esclusi

### File Modificati
- `app/web_server.py` - API cerca con JOIN referenti + fuzzy
- `templates/index/_scripts.html` - Fix comandi @com/@ope
- `templates/dashboard.html` - Layout con ricerca
- `templates/dashboard/_ricerca_smart.html` - Componente ricerca
- `templates/dashboard/_ricerca_smart_styles.html` - CSS
- `templates/dashboard/_ricerca_smart_scripts.html` - JavaScript

---

## 2026-01-29 - Top Prospect + Soft Delete Trattative

### Nuove Funzionalita'
- Sistema Top Prospect completo con Google Calendar
- Soft delete per trattative (cancellazione logica)
- Note con allegati per Top Prospect

---

## 2026-01-28 - Griglie Trattative

### Nuove Funzionalita'
- Griglie separate per trattative attive/chiuse/cancellate
- Filtri avanzati per stato e commerciale
- Modal avanzamento con percentuale

---

## 2026-01-27 - Filtri Index + Documenti

### Nuove Funzionalita'
- Filtro forma giuridica nella lista clienti
- Toggle colonne con persistenza localStorage
- Sistema documenti strutturati completo

---

## 2026-01-26 - Stati Tipo Veicolo + Flotta

### Nuove Funzionalita'
- Riquadro flotta in trattativa
- Gestione stati tipo veicolo
- Analisi mappatura CRM

---

## Legenda Versioni

| Prefisso | Significato |
|----------|-------------|
| fix_ | Correzione bug |
| patch_ | Piccola modifica |
| sessione_ | Documentazione sessione completa |
| fase_ | Step di sviluppo pianificato |
