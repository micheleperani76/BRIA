# TODO - Gestione Flotta

Ultimo aggiornamento: 04 Febbraio 2026

---

## IN CORSO

### Top Prospect
- [ ] Test completo sincronizzazione Google Calendar
- [ ] Test condivisione calendario con altri account

### Sistema Notifiche - Allineamenti
- [ ] Fine-tuning allineamenti grafici campanella

---

## PROSSIMI PASSI (Priorita' Alta)

### Sistema Notifiche - Fase 2: Sistema Task + Connettore Task
- [ ] Tabella `task` nel database (assegnatario, scadenza, stato, priorita')
- [ ] CRUD task (crea, modifica, completa, elimina)
- [ ] Connettore notifiche per task (notifica assegnazione, scadenza, completamento)
- [ ] Interfaccia gestione task
- [ ] Integrazione campanella con notifiche task

### Sistema Notifiche - Fase 3: Connettori Progressivi Moduli Esistenti
- [ ] Connettore TRATTATIVE (nuova trattativa, avanzamento, chiusura)
- [ ] Connettore TOP_PROSPECT (nuovo candidato, conferma, promemoria appuntamento)
- [ ] Connettore TRASCRIZIONE (trascrizione completata, errore)
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

### Banner Dashboard (Progettato, non implementato)
- [ ] Striscia scorrevole RSS-style sotto navbar
- [ ] Messaggi: cambio gomme, compleanni clienti, scadenze contratti
- [ ] Configurabile da admin

### Miglioramenti UI
- [ ] Dark mode
- [ ] Responsive migliorato per mobile
- [ ] Preferenze utente persistenti

### Integrazioni
- [ ] Import massivo clienti da Excel
- [ ] Integrazione CRM esterno (quando disponibile)
- [ ] API REST per integrazioni terze parti

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

---

## COMPLETATI (Sessione 04/02/2026 - Pomeriggio)

### Sistema Notifiche - Fase 1 (Fondamenta Complete)
- [x] File configurazione: notifiche.conf + categorie_notifiche.xlsx
- [x] config_notifiche.py (reader configurazione con lru_cache)
- [x] Migrazione DB: 4 tabelle (notifiche, destinatari, preferenze, regole)
- [x] 18 indici di performance + 17 regole default
- [x] motore_notifiche.py (hub: pubblica, deduplicazione, risoluzione destinatari)
- [x] connettori_notifiche/sistema.py (primo connettore di riferimento)
- [x] routes_notifiche.py (7 API: contatore, recenti, letta, tutte-lette, archivia, test, statistiche)
- [x] Template campanella: visibile solo con notifiche, trascinabile nei 4 angoli
- [x] Integrazione in base.html + web_server.py (blueprint + context processor)
- [x] Posizioni sinistre campanella rispettano larghezza sidebar (dinamico)
- [x] Predisposto per canali futuri (email SMTP, Telegram)

---

## COMPLETATI (Sessione 04/02/2026 - Mattina)

### Fix
- [x] Corretto login HTTP 500 (auth.py: accesso .get() su sqlite3.Row)

### Riquadro Trascrizioni Cliente (miglioramenti)
- [x] Upload drag & drop multiplo direttamente dalla scheda cliente
- [x] Progress bar sequenziale per upload multipli
- [x] Rinomina file (rinomina anche audio associato)
- [x] Modifica/correzione testo trascritto con salvataggio
- [x] Ricerca full-text nelle trascrizioni del cliente
- [x] Ritorno automatico alla lista dopo chiusura anteprima/rinomina
- [x] 3 nuove route API: rinomina-file, modifica, cerca

### Protezioni Worker Trascrizione
- [x] Recovery job bloccati all'avvio (rimette in coda con priorita' 2)
- [x] Graceful shutdown con check stato 'eliminato'
- [x] Check pre-elaborazione: salta job eliminati nel frattempo
- [x] Protezione orario: calcola se job puo' completarsi prima dello stop (4:00)
- [x] Scorre candidati in ordine, prova job piu' corti se il primo non ci sta
- [x] Se nessun job entra in orario, attende il giorno dopo
- [x] Priorita' corretta: 2=recovery/massima, 1=normale, 0=bassa

### Miglioramenti Coda
- [x] Upload sempre consentito (rimosso blocco orario accettazione)
- [x] Stima tempo coda cumulativa (somma job davanti + in lavorazione)
- [x] Formato tempo leggibile (~X minuti / ~Xh Xmin / ~Xg Xh)
- [x] Bottone elimina job in coda (proprio o admin tutti)
- [x] Route elimina-coda con controllo permessi

---

## COMPLETATI (Sessioni 30/01 - 03/02/2026)

### Export e Stampa
- [x] Export Top Prospect confermati in Excel/CSV
- [x] Export Trattative con filtri (stato, tipo, noleggiatore, commerciale, date)
- [x] Interfaccia 3 tab (Clienti, Top Prospect, Trattative)
- [x] Anteprima dati prima dell'export
- [x] Fix nomi tabelle/colonne DB per export trattative
- [x] Filtro date nel tab trattative
- [x] Badge NS circolare nel riquadro documenti

### Sistema Trascrizione Audio - Fase 1 (Backend)
- [x] File configurazione: impostazioni/trascrizione.conf
- [x] Config reader: app/config_trascrizione.py
- [x] Tabella DB: coda_trascrizioni con indici
- [x] Worker background: scripts/worker_trascrizione.py
- [x] Servizio systemd: trascrizione-worker.service (enabled)
- [x] Conversione audio automatica con ffmpeg (AAC, MP3, WAV, OGG, ecc.)
- [x] Trascrizione con faster-whisper (modelli large-v3 / large-v3-turbo)
- [x] VAD filter per rimozione silenzio
- [x] Coda condivisa con priorita' (file >150MB = bassa)
- [x] Orari operativi: accettazione 07:00-19:00, elaborazione 07:00-04:00
- [x] Retention automatica: audio cliente 180gg, testo consumo 21gg
- [x] Pulizia retention giornaliera automatica
- [x] Shutdown graceful (SIGTERM rimette job in coda)

### Sistema Trascrizione Audio - Fase 2 (API Flask)
- [x] Blueprint routes_trascrizione.py con tutte le route
- [x] Upload audio con validazione formato/dimensione (max 500MB)
- [x] Calcolo durata con ffprobe
- [x] Scelta modello automatica (turbo se coda lunga)
- [x] API stato coda (privacy: solo nome utente, no dettagli file)
- [x] API "Le mie trascrizioni" (private per utente)
- [x] Spostamento trascrizione da consumo a cliente (ricerca fuzzy)
- [x] Rinomina trascrizioni
- [x] Eliminazione trascrizioni consumo
- [x] Scarica testo trascrizione

### Sistema Trascrizione Audio - Fase 3 (Frontend)
- [x] Pagina /trascrizione con layout 2 colonne
- [x] Upload drag & drop con progress bar XHR
- [x] Lista "Le Mie Trascrizioni" con auto-refresh
- [x] Badge stato (completato/lavorazione/attesa/errore)
- [x] Modal coda (job in lavorazione + attesa, privacy)
- [x] Modal spostamento su cliente con ricerca fuzzy
- [x] Modal anteprima testo con copia/download
- [x] Widget FAB flottante (visibile solo se job in corso, pulsazione)
- [x] Link nel menu sidebar
- [x] Avviso retention (audio non conservato, testo 21gg)

### Sistema Trascrizione Audio - Performance
- [x] Fix CPUQuota systemd: 80% -> 600% (6 core su 12)
- [x] Rimosso LD_PRELOAD dal servizio (rallentava caricamento modello)
- [x] Modello default: large-v3-turbo (6x piu' veloce, -1% accuratezza)
- [x] NUM_THREADS=10 per parallelismo CPU
- [x] Taratura stime tempo: fattore turbo 0.5x, large-v3 1.5x
- [x] Risultato: 54 min audio -> 22 min elaborazione (~0.42x realtime)
- [x] Fix bug "COMPLETATO in -1 minuti" nel log

### Trascrizioni nella Scheda Cliente
- [x] 6o riquadro "Trascrizioni" nella riga documenti cliente
- [x] Modal lista trascrizioni con tabella (nome, data, dimensione)
- [x] Anteprima testo con copia clipboard
- [x] Download file .txt
- [x] Eliminazione trascrizioni
- [x] Badge conteggio automatico
- [x] 5 route API: lista, conta, testo, scarica, elimina

---

## COMPLETATI (Sessione 29/01/2026)

### Top Prospect
- [x] Integrazione Google Calendar completa
- [x] Sincronizzazione bidirezionale (Google = fonte primaria)
- [x] Condivisione calendario (solo admin)
- [x] Upload allegati nelle note
- [x] Modal note ridimensionabile (resize bordi)
- [x] Modifica/eliminazione note esistenti
- [x] Colonna origine (mano/cpu) nella griglia confermati
- [x] Badge "Google" per appuntamenti sincronizzati
- [x] UX: riga espansa rimane aperta dopo salvataggio

### Trattative
- [x] Griglia trattative con stati colorati
- [x] Soft delete (cestino) con ripristino
- [x] Filtri per stato, tipo, commerciale
- [x] Modal nuova/modifica trattativa

### Sistema Utenti
- [x] Autenticazione con ruoli (admin/commerciale/viewer)
- [x] Visibilita' gerarchica (supervisore vede subordinati)
- [x] Storico assegnazioni commerciali
- [x] Log accessi

### Documenti Cliente
- [x] Struttura modulare (Car Policy, Contratti, Quotazioni, Ordini)
- [x] Documenti strutturati con scadenze
- [x] Upload e visualizzazione PDF

---

## BUG NOTI

Nessun bug critico aperto.

---

## NOTE TECNICHE

### Struttura Cartelle
```
gestione_flotta/
  clienti/
    PIVA/{partita_iva}/
      allegati_note/
      creditsafe/
      trascrizioni/          <- file .txt permanenti
      car_policy/
      contratti/
      quotazioni/
      ordini/
    CF/{codice_fiscale}/
      (stessa struttura)
  trascrizione/
    attesa/                  <- coda condivisa
    lavorazione/             <- 1 file alla volta
    consumo/
      {codice_utente}/       <- es. 000001 (Paolo)
        {gg-mm-aaaa}/        <- organizzato per data
          file.txt           <- retention 21 giorni
  impostazioni/
    trascrizione.conf        <- config trascrizione
    notifiche.conf           <- config hub notifiche
    categorie_notifiche.xlsx <- 13 categorie + 4 livelli
```

### Google Calendar
- Service Account: gestione-flotta-calendar@br-car-service-flotta.iam.gserviceaccount.com
- Calendario: "Top Prospect BR Car Service"
- Colori commerciali nel DB (tabella utenti.colore_calendario)

### Worker Trascrizione
- Servizio: trascrizione-worker.service
- Modello default: large-v3-turbo (CPU, int8, 10 thread)
- CPUQuota: 600% (6 core su 12)
- Performance: ~0.42x realtime (54 min audio -> 22 min)
- Log: logs/trascrizione.log
- Recovery automatico job bloccati all'avvio
- Protezione orario: posticipa job troppo lunghi, prova piu' corti
- Check job eliminati: non elabora e non ripristina job cancellati
- Upload sempre consentito (elaborazione gestita automaticamente)
- Priorita': 2=recovery, 1=normale, 0=bassa (file grande)

### Sistema Notifiche
- Hub: motore_notifiche.py con pubblica_notifica()
- Deduplicazione via codice_evento (finestra 24h)
- Routing destinatari via regole DB (TUTTI, RUOLO:xxx, PROPRIETARIO, SUPERVISORE)
- Campanella: polling 30s, visibile solo con notifiche, drag nei 4 angoli
- Connettori: ogni modulo ha il suo in app/connettori_notifiche/
- Admin: id=0 (destinatario di default per notifiche SISTEMA)
- Canali futuri predisposti: email SMTP, Telegram

### Database
- SQLite: db/gestionale.db
- Tabella: coda_trascrizioni (trascrizioni audio)
- Tabelle notifiche: notifiche, notifiche_destinatari, notifiche_preferenze, notifiche_regole
- Tabella: top_prospect_note.allegati (JSON)
