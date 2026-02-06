# TODO - Gestione Flotta

Ultimo aggiornamento: 06 Febbraio 2026

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

