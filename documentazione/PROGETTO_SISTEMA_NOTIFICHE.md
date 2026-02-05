# PROGETTO - SISTEMA NOTIFICHE E AVVISI CENTRALIZZATO
## Hub di Distribuzione Avvisi, Allarmi e Segnalazioni

**Data**: 04 Febbraio 2026
**Versione**: 1.0 (Documento di progetto)
**Stato**: DA APPROVARE
**Priorita'**: ALTA

---

## 1. OBIETTIVO

Creare un **hub centralizzato** che raccoglie avvisi da tutte le parti del
gestionale e li distribuisce agli utenti giusti. Un unico punto dove confluiscono
segnalazioni di ogni tipo — dal task completato alla scadenza contratto, dal
cambio gomme al compleanno cliente — e ogni utente vede solo cio' che lo riguarda.

**Principio fondamentale:**
> Nessun modulo del gestionale invia notifiche direttamente.
> Tutti passano dall'hub. L'hub decide a chi, come e quando.

---

## 2. ARCHITETTURA

```
+=====================================================================+
|                      HUB NOTIFICHE CENTRALIZZATO                    |
|                        (motore_notifiche.py)                        |
+=====================================================================+
     ^        ^        ^        ^        ^        ^
     |        |        |        |        |        |
  +------+ +------+ +------+ +------+ +------+ +------+
  | Task | |Trasc.| |Scad. | |Calen.| |Sist. | |EMAIL |
  |      | |      | |      | |      | |      | | IMAP |
  +------+ +------+ +------+ +------+ +------+ +------+
     ^        ^        ^        ^        ^        ^
     |        |        |        |        |        |
  [routes  [worker  [cron    [google  [auth   [cron/
   task]    trasc]   nott.]  cal.]    ecc.]   polling]


                            |
                            v
+=====================================================================+
|                     DISTRIBUZIONE                                   |
+=====================================================================+
     |           |           |           |           |
     v           v           v           v           v
+---------+ +---------+ +---------+ +---------+ +---------+
|Campanella| | Badge  | | Banner  | |  Email  | |TELEGRAM |
| Navbar   | | Pagine | | Scroll  | |  SMTP   | |   BOT   |
+---------+ +---------+ +---------+ +---------+ +---------+
```

### 2.1 Separazione netta tra 3 strati

| Strato | Compito | File |
|--------|---------|------|
| **Connettori** | Generano eventi, chiamano l'hub | `connettori_notifiche/` |
| **Hub** | Riceve, filtra, smista, salva | `motore_notifiche.py` |
| **Uscite** | Mostrano all'utente | Template + API |

Ogni strato e' **indipendente**. Aggiungere un connettore non tocca l'hub.
Aggiungere un canale di uscita non tocca i connettori.

---

## 3. TIPOLOGIE DI NOTIFICA

### 3.1 Per urgenza

| Livello | Nome | Icona | Colore | Comportamento |
|---------|------|-------|--------|---------------|
| 1 | **INFO** | bi-info-circle | blu #0d6efd | Informativa, non urgente |
| 2 | **AVVISO** | bi-exclamation-triangle | giallo #ffc107 | Richiede attenzione |
| 3 | **ALLARME** | bi-exclamation-circle-fill | rosso #dc3545 | Richiede azione immediata |
| 0 | **SISTEMA** | bi-gear | grigio #6c757d | Evento tecnico (log, manutenzione) |

### 3.2 Per categoria (fonte)

Configurate in `impostazioni/categorie_notifiche.xlsx` — ampliabili da Excel.

| Codice | Etichetta | Icona | Descrizione |
|--------|-----------|-------|-------------|
| TASK | Task Interni | bi-clipboard-check | Task creati, presi, completati |
| TRASCRIZIONE | Trascrizione Audio | bi-mic | Trascrizione completata/errore |
| SCADENZA_CONTRATTO | Scadenze Contratti | bi-calendar-x | Contratto in scadenza |
| SCADENZA_DOCUMENTO | Scadenze Documenti | bi-file-earmark-x | Documento strutturato in scadenza |
| CAMBIO_GOMME | Cambio Gomme | bi-snow | Periodo cambio gomme stagionale |
| COMPLEANNO | Compleanni | bi-gift | Compleanno referente cliente |
| APPUNTAMENTO | Appuntamenti | bi-calendar-event | Promemoria appuntamento imminente |
| ASSEGNAZIONE | Assegnazioni | bi-person-plus | Cambio assegnazione cliente/commerciale |
| TRATTATIVA | Trattative | bi-handshake | Cambio stato trattativa |
| TOP_PROSPECT | Top Prospect | bi-star | Attivita' su prospect |
| EMAIL | Email Ricevute | bi-envelope | Email importanti ricevute su @brcarservice.it |
| SISTEMA | Sistema | bi-gear | Login falliti, errori, manutenzione |

### 3.3 Per persistenza

| Tipo | Durata | Esempio |
|------|--------|---------|
| **Persistente** | Fino a lettura/azione | "Task TASK-001 completato" |
| **Temporanea** | Scompare dopo N giorni | "Buon compleanno sig. Rossi" |
| **Ricorrente** | Si ripete ciclicamente | "Periodo cambio gomme invernali" |

---

## 4. DATABASE

### 4.1 Tabella `notifiche` (principale)

```sql
CREATE TABLE IF NOT EXISTS notifiche (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Contenuto
    categoria TEXT NOT NULL,              -- codice da categorie_notifiche.xlsx
    livello INTEGER DEFAULT 1,            -- 0=sistema, 1=info, 2=avviso, 3=allarme
    titolo TEXT NOT NULL,                 -- testo breve (max 100 char)
    messaggio TEXT,                       -- dettaglio (opzionale)
    
    -- Riferimenti (tutti opzionali, dipende dalla fonte)
    cliente_id INTEGER,                   -- cliente collegato
    task_id INTEGER,                      -- task collegato
    trattativa_id INTEGER,                -- trattativa collegata
    veicolo_id INTEGER,                   -- veicolo collegato
    entita_tipo TEXT,                     -- tipo entita' generica
    entita_id INTEGER,                    -- id entita' generica
    
    -- Link diretto (URL relativo per click)
    url_azione TEXT,                      -- es. /cliente/123, /task/45
    etichetta_azione TEXT,                -- es. "Vai al cliente", "Apri task"
    
    -- Origine
    connettore TEXT NOT NULL,             -- quale connettore l'ha generata
    codice_evento TEXT,                   -- codice univoco evento (per dedup)
    
    -- Temporalita'
    data_creazione TEXT NOT NULL,
    data_scadenza TEXT,                   -- dopo questa data, auto-elimina
    ricorrente INTEGER DEFAULT 0,         -- 0=no, 1=si
    
    -- Stato globale
    attiva INTEGER DEFAULT 1             -- 0=disattivata da admin
);

CREATE INDEX IF NOT EXISTS idx_notifiche_categoria ON notifiche(categoria);
CREATE INDEX IF NOT EXISTS idx_notifiche_livello ON notifiche(livello);
CREATE INDEX IF NOT EXISTS idx_notifiche_data ON notifiche(data_creazione);
CREATE INDEX IF NOT EXISTS idx_notifiche_connettore ON notifiche(connettore);
CREATE INDEX IF NOT EXISTS idx_notifiche_codice_evento ON notifiche(codice_evento);
CREATE INDEX IF NOT EXISTS idx_notifiche_attiva ON notifiche(attiva);
```

### 4.2 Tabella `notifiche_destinatari` (chi deve ricevere)

```sql
CREATE TABLE IF NOT EXISTS notifiche_destinatari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notifica_id INTEGER NOT NULL,
    utente_id INTEGER NOT NULL,
    
    -- Stato per questo utente
    letta INTEGER DEFAULT 0,              -- 0=non letta, 1=letta
    data_lettura TEXT,
    archiviata INTEGER DEFAULT 0,         -- 0=visibile, 1=archiviata
    data_archiviazione TEXT,
    
    FOREIGN KEY (notifica_id) REFERENCES notifiche(id) ON DELETE CASCADE,
    FOREIGN KEY (utente_id) REFERENCES utenti(id),
    UNIQUE(notifica_id, utente_id)
);

CREATE INDEX IF NOT EXISTS idx_notdest_utente ON notifiche_destinatari(utente_id);
CREATE INDEX IF NOT EXISTS idx_notdest_letta ON notifiche_destinatari(letta);
CREATE INDEX IF NOT EXISTS idx_notdest_notifica ON notifiche_destinatari(notifica_id);
```

### 4.3 Tabella `notifiche_preferenze` (opt-in/opt-out per utente)

```sql
CREATE TABLE IF NOT EXISTS notifiche_preferenze (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utente_id INTEGER NOT NULL,
    categoria TEXT NOT NULL,              -- categoria notifica
    abilitata INTEGER DEFAULT 1,         -- 0=non ricevere, 1=ricevi
    
    FOREIGN KEY (utente_id) REFERENCES utenti(id),
    UNIQUE(utente_id, categoria)
);
```

### 4.4 Tabella `notifiche_regole` (chi riceve cosa)

```sql
CREATE TABLE IF NOT EXISTS notifiche_regole (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT NOT NULL,              -- categoria notifica
    
    -- Destinatari (almeno uno deve essere valorizzato)
    ruolo TEXT,                           -- 'admin', 'commerciale', 'operatore'
    permesso TEXT,                        -- codice permesso (es. 'notifiche_scadenze')
    utente_id INTEGER,                    -- utente specifico
    
    -- Condizioni aggiuntive
    solo_propri_clienti INTEGER DEFAULT 0, -- 1=solo se il cliente e' del commerciale
    
    attiva INTEGER DEFAULT 1,
    
    FOREIGN KEY (utente_id) REFERENCES utenti(id)
);

CREATE INDEX IF NOT EXISTS idx_notreg_categoria ON notifiche_regole(categoria);
```

**Esempio regole preconfigurate:**

| Categoria | Ruolo | Permesso | Solo propri clienti | Significato |
|-----------|-------|----------|---------------------|-------------|
| TASK | - | task_prendi | no | Chi puo' prendere task riceve avviso nuovi task |
| TASK | - | - | si | Il creatore riceve aggiornamenti sul suo task |
| TRASCRIZIONE | - | - | si | L'utente che ha caricato riceve "completata" |
| SCADENZA_CONTRATTO | admin | - | no | Admin vede tutte le scadenze |
| SCADENZA_CONTRATTO | commerciale | - | si | Commerciale vede solo scadenze suoi clienti |
| CAMBIO_GOMME | commerciale | - | si | Solo per i propri clienti con veicoli |
| ASSEGNAZIONE | - | notifiche_assegnazioni | no | Figure preposte al controllo |
| SISTEMA | admin | - | no | Solo admin |

---

## 5. CONNETTORI

Ogni connettore e' un **file Python separato** nella cartella `app/connettori_notifiche/`.
Ha un'unica responsabilita': sapere QUANDO e COSA notificare.

### 5.1 Struttura connettore

```python
# app/connettori_notifiche/task.py

from app.motore_notifiche import pubblica_notifica

def notifica_task_creato(conn, task):
    """Chiamata da routes_task.py quando viene creato un task."""
    pubblica_notifica(
        conn=conn,
        categoria='TASK',
        livello=2,  # AVVISO
        titolo=f"Nuovo task: {task['oggetto']}",
        messaggio=f"Tipo: {task['tipologia']} - Cliente: {task['cliente_nome']}",
        cliente_id=task.get('cliente_id'),
        task_id=task['id'],
        url_azione=f"/task#{task['id']}",
        etichetta_azione="Apri task",
        connettore='task',
        codice_evento=f"task_creato_{task['id']}"
    )

def notifica_task_completato(conn, task):
    """Chiamata quando un task viene completato."""
    pubblica_notifica(
        conn=conn,
        categoria='TASK',
        livello=1,  # INFO
        titolo=f"Task completato: {task['oggetto']}",
        messaggio=f"Completato da {task['assegnato_nome']} in {task['minuti_lavorazione']} min",
        cliente_id=task.get('cliente_id'),
        task_id=task['id'],
        url_azione=f"/task#{task['id']}",
        etichetta_azione="Vedi dettaglio",
        connettore='task',
        codice_evento=f"task_completato_{task['id']}",
        destinatari_specifici=[task['creato_da_id']]  # solo chi l'ha creato
    )
```

### 5.2 Connettori previsti

| File | Fonte | Eventi generati |
|------|-------|-----------------|
| `task.py` | Sistema Task | task_creato, task_preso, task_completato, task_annullato |
| `trascrizione.py` | Worker Trascrizione | trascrizione_completata, trascrizione_errore |
| `scadenze.py` | Cron job notturno | contratto_in_scadenza (30/15/7/1 giorni) |
| `documenti.py` | Cron job notturno | documento_in_scadenza (30/15/7/1 giorni) |
| `calendario.py` | Cron job / polling | appuntamento_imminente (1 giorno / 1 ora prima) |
| `stagionali.py` | Cron job | cambio_gomme_invernali, cambio_gomme_estive |
| `compleanni.py` | Cron job notturno | compleanno_referente_oggi |
| `assegnazioni.py` | Modulo commerciali | cliente_riassegnato, eredita_clienti |
| `trattative.py` | Modulo trattative | trattativa_avanzata, trattativa_chiusa |
| `sistema.py` | Auth / sistema | login_fallito_multiplo, backup_completato |
| `email_imap.py` | Polling IMAP @brcarservice.it | email_ricevuta (filtrata per regole) |

### 5.3 Aggiungere un nuovo connettore (guida)

```python
# 1. Creare file: app/connettori_notifiche/mio_connettore.py

from app.motore_notifiche import pubblica_notifica

def notifica_mio_evento(conn, dati):
    pubblica_notifica(
        conn=conn,
        categoria='MIA_CATEGORIA',     # aggiungere in categorie_notifiche.xlsx
        livello=1,
        titolo="Il mio evento",
        messaggio="Dettagli...",
        connettore='mio_connettore',
        codice_evento=f"mio_evento_{dati['id']}"
    )

# 2. Chiamare dal punto del codice dove avviene l'evento:
#    from app.connettori_notifiche.mio_connettore import notifica_mio_evento
#    notifica_mio_evento(conn, dati)

# 3. Aggiungere riga in categorie_notifiche.xlsx

# 4. Aggiungere regole in notifiche_regole (chi riceve)

# FATTO. Zero modifiche all'hub o ai template.
```

### 5.4 Connettore Email IMAP (@brcarservice.it)

Questo connettore legge le caselle email aziendali via IMAP e genera
notifiche per le email importanti ricevute.

#### Flusso

```
Casella IMAP @brcarservice.it
        |
        v
[Polling ogni N minuti]  <-- cron o servizio systemd
        |
        v
[Filtro regole]
  - Mittente in whitelist?
  - Oggetto contiene keyword?
  - Destinatario = quale utente?
        |
        v
[pubblica_notifica]
  categoria='EMAIL'
  titolo="Email da: {mittente}"
  messaggio="{oggetto}"
  destinatari=[utente proprietario casella]
```

#### Configurazione `impostazioni/email_imap.conf`

```conf
# ==============================================================================
# CONFIGURAZIONE CONNETTORE EMAIL IMAP
# ==============================================================================

# Attivo (true/false)
EMAIL_IMAP_ATTIVO=false

# Server IMAP
IMAP_SERVER=imap.brcarservice.it
IMAP_PORT=993
IMAP_SSL=true

# Polling (minuti)
POLLING_MINUTI=5

# Quante email controllare per ciclo (ultime N non lette)
MAX_EMAIL_PER_CICLO=20

# Cartella IMAP da monitorare
IMAP_FOLDER=INBOX

# Filtro mittenti importanti (comma-separated, vuoto = tutti)
# Se popolato, solo email da questi domini/indirizzi generano notifica
WHITELIST_MITTENTI=

# Filtro keyword oggetto (comma-separated, vuoto = tutte)
# Se popolato, solo email con queste parole nell'oggetto generano notifica
KEYWORD_OGGETTO=

# Livello notifica
LIVELLO_DEFAULT=1
# Keyword che alzano a livello AVVISO (2)
KEYWORD_URGENTE=urgente,sollecito,scadenza,importante

# Retention: ignora email piu' vecchie di N ore
MAX_ANZIANITA_ORE=24
```

#### Mappatura utente-casella `impostazioni/email_caselle.xlsx`

| Utente_Username | Indirizzo_Email | Password_Env | Attivo |
|-----------------|-----------------|--------------|--------|
| p.ciotti | p.ciotti@brcarservice.it | EMAIL_PWD_CIOTTI | si |
| m.perani | m.perani@brcarservice.it | EMAIL_PWD_PERANI | si |
| c.pelucchi | c.pelucchi@brcarservice.it | EMAIL_PWD_PELUCCHI | si |
| f.zubani | f.zubani@brcarservice.it | EMAIL_PWD_ZUBANI | si |

**Nota sicurezza**: le password NON sono nel file Excel. La colonna
`Password_Env` indica il nome della variabile d'ambiente da cui leggere
la password. Le variabili vanno impostate in un file `.env` protetto
(permessi 600, fuori dal repository):

```bash
# /home/michele/gestione_flotta/.env (chmod 600)
EMAIL_PWD_CIOTTI=xxxxxxxxxxxx
EMAIL_PWD_PERANI=xxxxxxxxxxxx
EMAIL_PWD_PELUCCHI=xxxxxxxxxxxx
EMAIL_PWD_ZUBANI=xxxxxxxxxxxx
TELEGRAM_BOT_TOKEN=xxxxxxxxxxxx
```

#### Esempio connettore

```python
# app/connettori_notifiche/email_imap.py

import imaplib
import email
from email.header import decode_header
from app.motore_notifiche import pubblica_notifica
from app.config_notifiche import get_config_email_imap, get_caselle_email

def check_email_utente(conn, casella):
    """
    Controlla la casella IMAP di un utente.
    Genera notifiche per email non lette che passano i filtri.
    """
    config = get_config_email_imap()
    
    imap = imaplib.IMAP4_SSL(config['server'], config['port'])
    imap.login(casella['email'], casella['password'])
    imap.select(config['folder'])
    
    # Cerca email non lette
    status, messaggi = imap.search(None, 'UNSEEN')
    
    for msg_id in messaggi[0].split()[-config['max_per_ciclo']:]:
        status, data = imap.fetch(msg_id, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        
        mittente = email.utils.parseaddr(msg['From'])[1]
        oggetto = _decode_oggetto(msg['Subject'])
        
        # Applica filtri
        if not _passa_filtri(mittente, oggetto, config):
            continue
        
        livello = _calcola_livello(oggetto, config)
        
        pubblica_notifica(
            conn=conn,
            categoria='EMAIL',
            livello=livello,
            titolo=f"Email da: {mittente}",
            messaggio=oggetto[:200],
            connettore='email_imap',
            codice_evento=f"email_{casella['username']}_{msg['Message-ID']}",
            destinatari_specifici=[casella['utente_id']]
        )
    
    imap.logout()

def check_tutte_le_caselle(conn):
    """Chiamata dal cron/polling. Controlla tutte le caselle attive."""
    for casella in get_caselle_email():
        try:
            check_email_utente(conn, casella)
        except Exception as e:
            print(f"[WARN] Errore check email {casella['email']}: {e}")
```

#### Worker email (polling)

```bash
# Opzione A: crontab (semplice)
# Ogni 5 minuti dalle 7 alle 19
*/5 7-19 * * 1-5 cd ~/gestione_flotta && python3 scripts/check_email.py

# Opzione B: systemd timer (piu' robusto, come il worker trascrizione)
# gestione-flotta-email.timer + gestione-flotta-email.service
```

---

## 6. HUB CENTRALE (motore_notifiche.py)

### 6.1 Funzione principale

```python
def pubblica_notifica(conn, categoria, livello, titolo, connettore, codice_evento,
                      messaggio=None, cliente_id=None, task_id=None,
                      trattativa_id=None, veicolo_id=None,
                      entita_tipo=None, entita_id=None,
                      url_azione=None, etichetta_azione=None,
                      data_scadenza=None, ricorrente=False,
                      destinatari_specifici=None):
    """
    Punto di ingresso UNICO per tutte le notifiche.
    
    1. Controlla deduplicazione (codice_evento)
    2. Salva in tabella notifiche
    3. Determina destinatari (da regole + specifici)
    4. Filtra per preferenze utente (opt-out)
    5. Crea record in notifiche_destinatari
    """
```

### 6.2 Logica destinatari

```
Per ogni notifica:
  1. Cerca regole in notifiche_regole per la categoria
  2. Per ogni regola:
     - Se ruolo: tutti gli utenti con quel ruolo
     - Se permesso: tutti gli utenti con quel permesso
     - Se utente_id: quell'utente specifico
     - Se solo_propri_clienti: filtra per assegnazione
  3. Aggiungi destinatari_specifici (se passati)
  4. Rimuovi duplicati
  5. Filtra per notifiche_preferenze (opt-out)
  6. Crea record notifiche_destinatari
```

### 6.3 Deduplicazione

Il campo `codice_evento` impedisce notifiche duplicate:

```python
# Se esiste gia' una notifica con lo stesso codice_evento
# negli ultimi 60 minuti, NON crearla di nuovo
cursor.execute('''
    SELECT id FROM notifiche 
    WHERE codice_evento = ? 
    AND data_creazione > datetime('now', '-60 minutes')
''', (codice_evento,))
if cursor.fetchone():
    return None  # gia' notificato
```

---

## 7. CANALI DI USCITA

### 7.1 Campanella Navbar (principale)

```html
<!-- In base.html, nella navbar -->
<a href="/notifiche" class="nav-link position-relative">
    <i class="bi bi-bell"></i>
    <span class="badge bg-danger rounded-pill position-absolute" 
          id="notifiche-counter" style="display:none;">0</span>
</a>
```

**Dropdown al click** (senza cambiare pagina):

```
+------------------------------------------+
| NOTIFICHE                   [Segna tutte] |
+------------------------------------------+
| [!] Nuovo task: Quotazione ATIB    2 min |
| [i] Trascrizione completata      15 min  |
| [!] Contratto in scadenza (7gg)   1 ora  |
+------------------------------------------+
| Vedi tutte le notifiche >>                |
+------------------------------------------+
```

- Polling AJAX ogni 30 secondi (`/api/notifiche/counter`)
- Dropdown carica le ultime 10 non lette (`/api/notifiche/recenti`)
- Click su notifica: segna come letta + naviga a `url_azione`

### 7.2 Banner Scorrevole (opzionale, fase 2)

Striscia RSS-style sotto la navbar per avvisi informativi:

```
[i] Cambio gomme invernali dal 15/11 | Buon compleanno sig. Rossi (ATIB) | ...
```

- Solo notifiche di livello INFO
- Categorie selezionabili (cambio gomme, compleanni, ecc.)
- Configurabile da admin: attivo/disattivo, velocita', categorie

### 7.3 Badge nelle pagine

Nelle pagine specifiche, mostrare counter delle notifiche pertinenti:

```html
<!-- In pagina task -->
<h3>Task <span class="badge bg-danger">3 nuovi</span></h3>

<!-- In pagina cliente -->
<h5>Scadenze <span class="badge bg-warning">2 in scadenza</span></h5>
```

### 7.4 Email SMTP (uscita)

Canale per inviare notifiche importanti via email.
Solo notifiche con livello >= ALLARME (configurabile).

```python
# app/canali_notifiche/email_smtp.py

import smtplib
from email.mime.text import MIMEText

def invia_notifica_email(notifica, destinatario_email, config):
    """
    Invia una notifica via email SMTP.
    Chiamata dall'hub dopo pubblica_notifica se il canale e' attivo
    e la notifica supera la soglia di livello.
    """
    msg = MIMEText(f"{notifica['titolo']}\n\n{notifica['messaggio']}")
    msg['Subject'] = f"[GestioneFlotta] {notifica['titolo']}"
    msg['From'] = config['smtp_from']
    msg['To'] = destinatario_email
    
    with smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port']) as server:
        server.login(config['smtp_user'], config['smtp_password'])
        server.send_message(msg)
```

Configurazione in `impostazioni/notifiche.conf`:

```conf
# Email SMTP (uscita)
EMAIL_SMTP_ATTIVO=false
SMTP_SERVER=smtp.brcarservice.it
SMTP_PORT=465
SMTP_FROM=gestionale@brcarservice.it
SMTP_USER=gestionale@brcarservice.it
SMTP_PASSWORD_ENV=SMTP_PASSWORD
# Livello minimo per inviare email (2=AVVISO, 3=ALLARME)
EMAIL_LIVELLO_MINIMO=3
# Categorie che inviano email (vuoto = tutte sopra soglia)
EMAIL_CATEGORIE=SCADENZA_CONTRATTO,SISTEMA,ASSEGNAZIONE
```

### 7.5 Telegram Bot (uscita)

Bot Telegram che invia notifiche direttamente sul telefono degli utenti.
Perfetto per avvisi urgenti e per chi non e' davanti al gestionale.

#### Flusso

```
Hub notifica                    Utente Telegram
     |                               |
     v                               |
[Canale Telegram]                    |
  - Livello >= soglia?               |
  - Utente ha chat_id?               |
  - Categoria abilitata?             |
     |                               |
     v                               v
  Bot API  ---- messaggio ------> Chat privata
  @BRCarServiceBot                   |
                                     v
                              Notifica push
                              sul telefono!
```

#### Setup Bot

1. Creare bot con @BotFather su Telegram → ottieni `TELEGRAM_BOT_TOKEN`
2. Ogni utente avvia chat con @BRCarServiceBot
3. Il bot salva il `chat_id` dell'utente
4. Da quel momento, il gestionale puo' inviare messaggi

#### Registrazione utente (comando /start)

```
Utente apre @BRCarServiceBot su Telegram:

Utente:  /start
Bot:     Benvenuto nel bot BR Car Service!
         Per collegare il tuo account, inserisci
         il tuo codice di registrazione.
         Lo trovi in: Gestionale > Profilo > Telegram

Utente:  ABC123
Bot:     Account collegato! Sei: Paolo Ciotti
         Riceverai notifiche dal gestionale.
         
         /preferenze - Scegli cosa ricevere
         /silenzio   - Pausa notifiche
         /riattiva   - Riprendi notifiche
         /stato      - Vedi stato collegamento
         /scollega   - Rimuovi collegamento
```

Il codice di registrazione e' generato nella pagina profilo utente
del gestionale ed e' monouso, valido 24 ore.

#### Configurazione `impostazioni/telegram.conf`

```conf
# ==============================================================================
# CONFIGURAZIONE CANALE TELEGRAM
# ==============================================================================

# Attivo (true/false)
TELEGRAM_ATTIVO=false

# Token bot (letto da variabile d'ambiente per sicurezza)
TELEGRAM_TOKEN_ENV=TELEGRAM_BOT_TOKEN

# Nome bot
TELEGRAM_BOT_NAME=BRCarServiceBot

# Livello minimo per inviare su Telegram (1=INFO, 2=AVVISO, 3=ALLARME)
TELEGRAM_LIVELLO_MINIMO=2

# Categorie abilitate (vuoto = tutte sopra soglia)
TELEGRAM_CATEGORIE=TASK,SCADENZA_CONTRATTO,EMAIL,SISTEMA

# Orari invio (non disturbare fuori orario)
TELEGRAM_ORA_INIZIO=07:30
TELEGRAM_ORA_FINE=20:00

# Fuori orario: accoda e invia alla riapertura? (true/false)
TELEGRAM_ACCODA_FUORI_ORARIO=true

# Rate limit: max messaggi per utente per ora
TELEGRAM_MAX_PER_ORA=20

# Formato messaggio
TELEGRAM_FORMATO=html
```

#### Database: colonne aggiuntive in `utenti`

```sql
-- Aggiungere alla tabella utenti
ALTER TABLE utenti ADD COLUMN telegram_chat_id TEXT;
ALTER TABLE utenti ADD COLUMN telegram_attivo INTEGER DEFAULT 0;
ALTER TABLE utenti ADD COLUMN telegram_codice_reg TEXT;
ALTER TABLE utenti ADD COLUMN telegram_codice_scadenza TEXT;
ALTER TABLE utenti ADD COLUMN telegram_silenzio INTEGER DEFAULT 0;
```

#### Esempio canale

```python
# app/canali_notifiche/telegram_bot.py

import requests
from app.config_notifiche import get_config_telegram

API_URL = "https://api.telegram.org/bot{token}/sendMessage"

def invia_notifica_telegram(notifica, utente, config):
    """
    Invia notifica via Telegram.
    Chiamata dall'hub se il canale e' attivo e l'utente e' collegato.
    """
    if not utente.get('telegram_chat_id') or not utente.get('telegram_attivo'):
        return False
    
    if utente.get('telegram_silenzio'):
        return False  # utente in modalita' silenzio
    
    # Formatta messaggio
    icone_livello = {0: 'ℹ️', 1: 'ℹ️', 2: '⚠️', 3: '🚨'}
    icona = icone_livello.get(notifica['livello'], 'ℹ️')
    
    testo = (
        f"{icona} <b>{notifica['titolo']}</b>\n"
        f"{notifica.get('messaggio', '')}\n"
    )
    
    if notifica.get('url_azione'):
        url_completo = f"https://gestionale.brcarservice.it{notifica['url_azione']}"
        testo += f"\n<a href='{url_completo}'>{notifica.get('etichetta_azione', 'Apri')}</a>"
    
    response = requests.post(
        API_URL.format(token=config['token']),
        json={
            'chat_id': utente['telegram_chat_id'],
            'text': testo,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
    )
    
    return response.status_code == 200

def gestisci_comando(update):
    """
    Webhook o polling per gestire comandi dal bot.
    /start, /preferenze, /silenzio, /riattiva, /stato, /scollega
    """
    ...
```

#### Worker Telegram (polling comandi)

```bash
# Servizio systemd per ricevere comandi dal bot
# gestione-flotta-telegram.service
# Oppure webhook se il server e' raggiungibile dall'esterno

# Polling semplice:
# scripts/telegram_polling.py (gira come servizio)
```

#### Esempio messaggi ricevuti su Telegram

```
🚨 Contratto ATIB SRL in scadenza (7 giorni)
Contratto Arval n. 2024-1234 scade il 11/02/2026
Apri cliente

⚠️ Nuovo task: Quotazione ROSSI SRL
Tipo: Richiesta Quotazione - 5 veicoli Leasys
Apri task

ℹ️ Email da: info@arval.it
Oggetto: Conferma ordine veicoli lotto 2026-02
```

---

## 8. FILE DI CONFIGURAZIONE

### 8.1 `impostazioni/categorie_notifiche.xlsx`

| Codice | Etichetta | Icona | Colore | Default_Attiva | Ordine |
|--------|-----------|-------|--------|----------------|--------|
| TASK | Task Interni | bi-clipboard-check | #0d6efd | si | 1 |
| TRASCRIZIONE | Trascrizioni | bi-mic | #6610f2 | si | 2 |
| SCADENZA_CONTRATTO | Scadenze Contratti | bi-calendar-x | #dc3545 | si | 3 |
| SCADENZA_DOCUMENTO | Scadenze Documenti | bi-file-earmark-x | #fd7e14 | si | 4 |
| CAMBIO_GOMME | Cambio Gomme | bi-snow | #0dcaf0 | si | 5 |
| COMPLEANNO | Compleanni | bi-gift | #d63384 | si | 6 |
| APPUNTAMENTO | Appuntamenti | bi-calendar-event | #198754 | si | 7 |
| ASSEGNAZIONE | Assegnazioni | bi-person-plus | #fd7e14 | si | 8 |
| TRATTATIVA | Trattative | bi-handshake | #0d6efd | si | 9 |
| TOP_PROSPECT | Top Prospect | bi-star | #ffc107 | si | 10 |
| EMAIL | Email Ricevute | bi-envelope | #20c997 | si | 11 |
| SISTEMA | Sistema | bi-gear | #6c757d | no | 99 |

### 8.2 `impostazioni/notifiche.conf`

```conf
# ==============================================================================
# CONFIGURAZIONE SISTEMA NOTIFICHE
# ==============================================================================

# Retention notifiche lette (giorni)
RETENTION_LETTE=90

# Retention notifiche non lette (giorni) - 0 = mai
RETENTION_NON_LETTE=365

# Intervallo polling campanella (secondi)
POLLING_INTERVALLO=30

# Max notifiche nel dropdown
DROPDOWN_MAX=10

# Deduplicazione: finestra temporale (minuti)
DEDUP_FINESTRA_MINUTI=60

# Banner scorrevole
BANNER_ATTIVO=false
BANNER_VELOCITA=slow
BANNER_CATEGORIE=CAMBIO_GOMME,COMPLEANNO

# Scadenze: giorni di preavviso (comma-separated)
SCADENZE_PREAVVISO=30,15,7,1

# Cambio gomme: date (MM-DD)
CAMBIO_GOMME_INVERNALI_INIZIO=11-15
CAMBIO_GOMME_INVERNALI_FINE=04-15
CAMBIO_GOMME_ESTIVE_INIZIO=04-15
CAMBIO_GOMME_ESTIVE_FINE=11-15
```

### 8.3 `impostazioni/email_imap.conf`

Vedi sezione 5.4 per il contenuto completo.

### 8.4 `impostazioni/email_caselle.xlsx`

Vedi sezione 5.4 per la mappatura utente-casella.

### 8.5 `impostazioni/telegram.conf`

Vedi sezione 7.5 per il contenuto completo.

### 8.6 File `.env` (credenziali - fuori da repository)

```bash
# /home/michele/gestione_flotta/.env (chmod 600)
# Password caselle email IMAP
EMAIL_PWD_CIOTTI=xxxxxxxxxxxx
EMAIL_PWD_PERANI=xxxxxxxxxxxx
EMAIL_PWD_PELUCCHI=xxxxxxxxxxxx
EMAIL_PWD_ZUBANI=xxxxxxxxxxxx

# SMTP uscita
SMTP_PASSWORD=xxxxxxxxxxxx

# Telegram
TELEGRAM_BOT_TOKEN=xxxxxxxxxxxx
```

---

## 9. STRUTTURA FILE (Modularita' Estrema)

```
gestione_flotta/
  app/
    config_notifiche.py                    # Lettura Excel + conf
    motore_notifiche.py                    # Hub centrale (pubblica, smista, dedup)
    routes_notifiche.py                    # Blueprint API + pagina
    connettori_notifiche/                  # Cartella connettori (INGRESSO)
      __init__.py
      task.py                              # Eventi da sistema task
      trascrizione.py                      # Eventi da worker trascrizione
      scadenze.py                          # Scadenze contratti/documenti
      calendario.py                        # Appuntamenti imminenti
      stagionali.py                        # Cambio gomme
      compleanni.py                        # Compleanni referenti
      assegnazioni.py                      # Cambio assegnazioni
      trattative.py                        # Avanzamento trattative
      sistema.py                           # Eventi tecnici
      email_imap.py                        # Lettura email @brcarservice.it
    canali_notifiche/                      # Cartella canali (USCITA)
      __init__.py
      email_smtp.py                        # Invio email SMTP
      telegram_bot.py                      # Invio messaggi Telegram
  templates/
    notifiche/
      _campanella.html                     # Dropdown navbar
      _campanella_scripts.html             # JS polling + dropdown
      _campanella_styles.html              # CSS campanella
      _lista.html                          # Lista completa notifiche
      _lista_scripts.html                  # JS lista
      _filtri.html                         # Filtri per categoria/livello
      _preferenze.html                     # Preferenze utente (opt-in/out)
      _telegram.html                       # Collegamento Telegram nel profilo
      _banner.html                         # Banner scorrevole (fase 2)
      _banner_scripts.html                 # JS banner
    notifiche.html                         # Pagina completa notifiche
  impostazioni/
    categorie_notifiche.xlsx               # Categorie
    notifiche.conf                         # Configurazione generale
    email_imap.conf                        # Config connettore email IMAP
    email_caselle.xlsx                     # Mappatura utente-casella
    telegram.conf                          # Config canale Telegram
  scripts/
    cron_notifiche.py                      # Job notturno scadenze/compleanni
    check_email.py                         # Polling email IMAP (cron ogni 5 min)
    telegram_polling.py                    # Polling comandi bot Telegram
```

---

## 10. PERMESSI

Nuovi permessi da aggiungere al catalogo:

| Codice | Categoria | Descrizione |
|--------|-----------|-------------|
| notifiche_ricevi | notifiche | Riceve notifiche (base) |
| notifiche_scadenze | notifiche | Riceve avvisi scadenze |
| notifiche_assegnazioni | notifiche | Riceve avvisi cambio assegnazioni |
| notifiche_sistema | notifiche | Riceve avvisi di sistema |
| notifiche_gestisci | notifiche | Gestisce regole e configurazione |
| notifiche_email | notifiche | Riceve notifiche email IMAP |
| notifiche_telegram | notifiche | Puo' collegare account Telegram |

### Default per ruolo

| Ruolo | ricevi | scadenze | assegnazioni | sistema | gestisci | email | telegram |
|-------|--------|----------|--------------|---------|----------|-------|----------|
| Admin | si | si | si | si | si | si | si |
| Commerciale | si | si | no | no | no | si | si |
| Operatore | si | si | no | no | no | no | si |
| Viewer | si | no | no | no | no | no | no |

---

## 11. API / ROUTE

### Blueprint: `routes_notifiche.py`

| Metodo | Route | Descrizione |
|--------|-------|-------------|
| GET | `/notifiche` | Pagina lista completa |
| GET | `/api/notifiche/counter` | Counter non lette (per polling) |
| GET | `/api/notifiche/recenti` | Ultime N non lette (per dropdown) |
| GET | `/api/notifiche/lista` | Lista paginata con filtri |
| POST | `/api/notifiche/<id>/letta` | Segna come letta |
| POST | `/api/notifiche/segna-tutte` | Segna tutte come lette |
| POST | `/api/notifiche/<id>/archivia` | Archivia notifica |
| GET | `/api/notifiche/preferenze` | Preferenze utente |
| POST | `/api/notifiche/preferenze` | Salva preferenze utente |
| GET | `/api/notifiche/regole` | Regole distribuzione (solo admin) |
| POST | `/api/notifiche/regole` | Modifica regole (solo admin) |
| POST | `/api/notifiche/telegram/genera-codice` | Genera codice registrazione Telegram |
| GET | `/api/notifiche/telegram/stato` | Stato collegamento Telegram utente |
| POST | `/api/notifiche/telegram/scollega` | Scollega account Telegram |
| POST | `/api/notifiche/telegram/webhook` | Webhook comandi bot (se abilitato) |

---

## 12. CRON JOB NOTTURNO

Lo script `scripts/cron_notifiche.py` gira ogni notte e genera le notifiche
per eventi schedulati:

```python
# Eseguito da crontab alle 06:00 (prima dell'inizio lavoro)
# 0 6 * * * cd ~/gestione_flotta && python3 scripts/cron_notifiche.py

def main():
    conn = get_connection()
    
    # 1. Scadenze contratti (30, 15, 7, 1 giorno)
    check_scadenze_contratti(conn)
    
    # 2. Scadenze documenti strutturati
    check_scadenze_documenti(conn)
    
    # 3. Compleanni referenti oggi
    check_compleanni(conn)
    
    # 4. Promemoria appuntamenti domani
    check_appuntamenti(conn)
    
    # 5. Cambio gomme stagionale
    check_cambio_gomme(conn)
    
    # 6. Pulizia notifiche vecchie (retention)
    pulizia_retention(conn)
    
    conn.close()
```

---

## 13. INTEGRAZIONE CON SISTEMA TASK

Il sistema task (progetto separato) si collega al sistema notifiche
tramite il connettore `connettori_notifiche/task.py`:

```
Task creato          --> Notifica AVVISO a chi puo' prendere in carico
Task preso in carico --> Notifica INFO al creatore
Task completato      --> Notifica INFO al creatore
Task annullato       --> Notifica INFO al creatore (se diverso da chi annulla)
```

La campanella in navbar **unifica** il counter task + tutte le altre notifiche.
Non serve un counter separato per i task: tutto passa dall'hub.

---

## 14. PREFERENZE UTENTE

Ogni utente puo' scegliere quali categorie ricevere:

```
+------------------------------------------+
| LE MIE NOTIFICHE - Preferenze            |
+------------------------------------------+
| CATEGORIE                                |
| [x] Task Interni                         |
| [x] Trascrizioni                         |
| [x] Scadenze Contratti                   |
| [x] Scadenze Documenti                   |
| [ ] Cambio Gomme                         |  <-- opt-out
| [x] Compleanni                           |
| [x] Appuntamenti                         |
| [ ] Assegnazioni                         |  <-- non ha il permesso
| [x] Trattative                           |
| [x] Email Ricevute                       |
| [ ] Sistema                              |  <-- non ha il permesso
|                                          |
| CANALI DI USCITA                         |
| [x] Campanella nel gestionale            |
| [ ] Email (solo allarmi)                 |
| [x] Telegram  Collegato: @PaoloCiotti    |
|     [Scollega]                           |
|   oppure:                                |
| [ ] Telegram  Non collegato              |
|     [Genera codice registrazione]        |
+------------------------------------------+
| [Salva preferenze]                        |
+------------------------------------------+
```

Le categorie per cui l'utente non ha il permesso vengono mostrate
disabilitate (grigie, non cliccabili).

---

## 15. FASI DI IMPLEMENTAZIONE

### Fase 1 - Hub (Backend + DB)
1. File configurazione (`notifiche.conf`, `categorie_notifiche.xlsx`)
2. Modulo `config_notifiche.py`
3. Migrazione DB (4 tabelle + regole default)
4. Modulo `motore_notifiche.py` (pubblica + smista + dedup)
5. Permessi nel catalogo
6. Cartella `connettori_notifiche/` con `__init__.py`

### Fase 2 - Campanella + API
1. Blueprint `routes_notifiche.py`
2. API counter + recenti + lista
3. Template `_campanella.html` in base.html
4. Polling JS ogni 30 secondi
5. Dropdown con ultime 10 notifiche

### Fase 3 - Primi Connettori
1. Connettore task (se sistema task e' pronto)
2. Connettore trascrizione (integra nel worker)
3. Connettore scadenze (cron job)
4. Cron job notturno base

### Fase 4 - Pagina Notifiche + Preferenze
1. Pagina `/notifiche` con lista completa
2. Filtri per categoria e livello
3. Segna letta / archivia
4. Preferenze utente (opt-in/out)

### Fase 5 - Connettori Aggiuntivi + Banner
1. Connettore compleanni
2. Connettore cambio gomme
3. Connettore appuntamenti
4. Connettore assegnazioni
5. Banner scorrevole (opzionale)

### Fase 6 - Connettore Email IMAP (ingresso)
1. Config `email_imap.conf` + `email_caselle.xlsx`
2. Modulo `connettori_notifiche/email_imap.py`
3. Script `scripts/check_email.py` (polling cron)
4. Crontab: ogni 5 minuti in orario lavorativo
5. Filtri mittente + keyword oggetto
6. Test con una casella pilota

### Fase 7 - Canale Telegram Bot (uscita)
1. Creazione bot con @BotFather
2. Config `telegram.conf` + token in `.env`
3. Modulo `canali_notifiche/telegram_bot.py`
4. Colonne telegram in tabella utenti
5. Pagina collegamento nel profilo utente
6. Script `scripts/telegram_polling.py` per comandi
7. Integrazione nell'hub (invio automatico)
8. Test con utente pilota

### Fase 8 - Canale Email SMTP (uscita)
1. Config SMTP in `notifiche.conf` + password in `.env`
2. Modulo `canali_notifiche/email_smtp.py`
3. Integrazione nell'hub (invio per livello >= soglia)

### Fase 9 - Admin + Statistiche
1. Gestione regole distribuzione
2. Statistiche notifiche (quante, lette/non lette, tempi)
3. Log connettori (quante notifiche generate per fonte)
4. Monitoraggio canali uscita (email inviate, telegram inviati)

---

## 16. NOTE ARCHITETTURALI

### Coerenza con il progetto
- Pattern identico agli altri moduli (config da Excel + .conf)
- Blueprint separato come tutti gli altri
- Template modulari con file satellite
- Permessi nel catalogo esistente
- Integrazione in `base.html` (campanella) senza stravolgere il layout

### Scalabilita'
- **Nuovo connettore**: 1 file Python + 1 riga Excel. Zero modifiche all'hub.
- **Nuova categoria**: 1 riga Excel + opzionalmente regole in DB.
- **Nuovo canale di uscita**: 1 file in `canali_notifiche/`. Hub non cambia.
- **Nuova casella email**: 1 riga in `email_caselle.xlsx`. Connettore non cambia.
- **Nuovo bot**: stesso pattern di Telegram (Slack, WhatsApp, ecc.).

### Cosa NON fa questa v1.0
- SMS (possibile v2.0, stesso pattern Telegram)
- Push notification browser (possibile v2.0)
- Notifiche real-time WebSocket (polling e' sufficiente per ora)
- Escalation automatica (se non letta entro X ore, alza livello)
- SLA su notifiche (possibile v2.0)
- Risposta a email dal gestionale (solo lettura, non invio risposte)
- Risposte interattive da Telegram (solo comandi base, no workflow)

### Relazione con Sistema Task
Il sistema notifiche e' **indipendente** dal sistema task.
Il task ha il suo connettore ma l'hub funziona anche senza task.
Possono essere implementati in parallelo o in sequenza.

---

## 17. SCHEMA RIASSUNTIVO

```
CONNETTORI (generano)     HUB (smista)        USCITE (mostrano)
========================  ==================  ====================
task.py          ------+                      +--> Campanella navbar
trascrizione.py  ------+                      |
scadenze.py      ------+--> motore_notifiche  +--> Badge pagine
calendario.py    ------+    .py               |
stagionali.py    ------+    (pubblica,        +--> Banner scroll
compleanni.py    ------+     dedup,           |
assegnazioni.py  ------+     regole,          +--> Pagina /notifiche
trattative.py    ------+     destinatari)     |
sistema.py       ------+                      +--> Email SMTP
email_imap.py    ------+                      |
[futuro].py      ------+                      +--> Telegram Bot
                                              |
                                              +--> (Slack v2.0)
                                              +--> (SMS v2.0)
```
