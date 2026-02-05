# TODO - Gestione Flotta

Ultimo aggiornamento: 05 Febbraio 2026

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

## COMPLETATI (Sessione 05/02/2026)

### Sistema Notifiche - Primi Connettori (Fase 3 parziale)
- [x] Connettore TRASCRIZIONE (completata + 5 scenari errore nel worker)
- [x] Connettore TOP_PROSPECT (nuovi candidati + conferma)
- [x] Connettore TRATTATIVE (nuova trattativa + avanzamento stato)
- [x] Patch motore_trattative.py (import + chiamate notifica)
- [x] Patch motore_top_prospect.py (import + chiamata notifica candidati)
- [x] Patch routes_top_prospect.py (import + chiamata notifica conferma)
- [x] Logica destinatari gerarchica: risalita catena supervisori per trattative
- [x] Script spazzino file orfani trascrizione
- [x] Rimozione messaggio "Benvenuto" dal login (sostituito da campanella)
- [x] Fix campanella corrotta da sed (ripristino + patch Python)
- [x] Aggiunta riga messaggio nel dropdown notifiche (notifica-messaggio)

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
- [x] Protezione orario: verifica tempo stimato vs ore rimaste
- [x] Scorrimento candidati: se job troppo lungo, prova il prossimo piu' corto
- [x] Attesa automatica giorno dopo se nessun job ci sta
- [x] Stima tempo cumulativa coda (somma job precedenti + corrente)

---

## COMPLETATI (Sessione 03/02/2026)

### Trascrizioni nella Scheda Cliente
- [x] 6o riquadro "Trascrizioni" nella riga documenti cliente
- [x] Modal lista trascrizioni con tabella (nome, data, dimensione)
- [x] Anteprima testo con copia clipboard
- [x] Download file .txt
- [x] Eliminazione trascrizioni
- [x] Badge conteggio automatico
- [x] 5 route API: lista, conta, testo, scarica, elimina

### Documentazione
- [x] CHANGELOG.md aggiornato (entry Febbraio 2026)
- [x] MANUALE_TECNICO.md aggiornato (trascrizione + notifiche)
- [x] MANUALE_UTENTE.md aggiornato (guida trascrizione)
- [x] README.md aggiornato

---

## COMPLETATI (Sessione 30/01/2026)

### Pulizia Documentazione
- [x] Riduzione da 70 a 11 file (-84%)
- [x] MANUALE_UTENTE.md completo
- [x] MANUALE_TECNICO.md completo (35 tabelle, 170+ API)
- [x] Regola Aurea #9 (convenzione backup/deploy)
- [x] raccolta_file_ia.sh v3.0 (backup ZIP automatico)

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
      {codice_utente}/       <- es. 000002/
        *.txt                <- retention 21gg
```
