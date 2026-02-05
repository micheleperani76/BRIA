# REGOLE CLAUDE - Gestione Flotta
## Documento di riferimento per modifiche al codice

**Versione**: 6.0
**Ultimo aggiornamento**: 2026-02-05
**Progetto**: gestione_flotta (BR CAR SERVICE)

---

## SCOPO DI QUESTO FILE

Questo documento e' scritto DA CLAUDE PER CLAUDE. Contiene le regole, metodologie e attenzioni che DEVO seguire quando lavoro su questo progetto. E' il mio promemoria per evitare errori ricorrenti.

---

## CHECKLIST INIZIO SESSIONE

### Prima domanda da fare SEMPRE:
```
"Hai sincronizzato il repo GitHub nel progetto Claude?
Hai modificato qualcosa dall'ultima sessione?"
```

### FONTE DEI FILE
I file del progetto sono sincronizzati tramite GitHub:
- **Repository**: https://github.com/micheleperani76/BRIA
- I file in `/mnt/project/` provengono dal sync GitHub
- Se sembrano datati, chiedere all'utente di cliccare "Sync" nel Project Knowledge

### Se la sessione e' lunga o stiamo modificando file complessi:
```
"Prima di procedere, puoi caricarmi il file [nome] attuale 
cosi' verifico di lavorare sulla versione corrente?"
```

### NON FARE MAI:
- Assumere che i file nel progetto `/mnt/project/` siano aggiornati
- Modificare file senza prima confrontarli con la versione dell'utente
- Riscrivere interi file quando basta una modifica chirurgica

---

## REGOLA AUREA #1 - ENCODING UTF-8

### IL PROBLEMA
Quando riscrivo file, i caratteri speciali possono corrompersi:
- Euro diventa sequenze corrotte
- Lettere accentate diventano caratteri strani

### LA SOLUZIONE
1. **Preferire SEMPRE sed/str_replace chirurgici** invece di riscrivere file interi
2. Se devo riscrivere un file intero:
   - Verificare PRIMA l'encoding con: `file -i nomefile`
   - Dopo la scrittura, verificare i caratteri speciali
   - Confrontare con l'originale: `diff originale.py nuovo.py | head -50`

### PROBLEMA TRASFERIMENTO FILE VIA CHROMIUM

**IL PROBLEMA RICORRENTE:**
Quando l'utente scarica i file da Claude e li trasferisce sul server, il browser Chromium corrompe i caratteri UTF-8 durante il download/upload.

**SOLUZIONE OBBLIGATORIA:**
Dopo OGNI trasferimento di file, DEVO sempre:
1. Chiedere all'utente di verificare se funziona
2. Se ci sono problemi di encoding, fornire il comando per correggere

---

## REGOLA AUREA #2 - MODIFICHE CHIRURGICHE

### APPROCCIO CORRETTO
```
1. L'utente descrive il problema
2. Chiedo il file ATTUALE se non ce l'ho
3. Identifico la sezione ESATTA da modificare
4. Uso str_replace con old_str/new_str PRECISI
5. Mostro il diff delle modifiche
6. L'utente verifica e applica
```

### APPROCCIO SBAGLIATO
```
- Riscrivo l'intero file
- Modifico sezioni non richieste
- Assumo di avere la versione corretta
- Non verifico l'encoding dopo la modifica
```

### STRUMENTI DA USARE
- `str_replace` per modifiche precise (PREFERITO)
- `sed -i 's/vecchio/nuovo/g'` per sostituzioni semplici
- `diff -u originale modificato` per verificare le differenze

---

## REGOLA AUREA #3 - VERIFICA PRIMA DI MODIFICARE

### Prima di OGNI modifica a un file:
1. **Chiedere** se l'utente ha una versione piu' recente
2. **Confrontare** il file nel progetto con quello dell'utente
3. **Identificare** solo le righe da modificare
4. **Mostrare** il diff PRIMA di applicare

---

## REGOLA AUREA #4 - DOCUMENTAZIONE STEP BY STEP

### OBBLIGO ASSOLUTO
Ad ogni **step completato** di modifiche, DEVO rilasciare un file `.md` di documentazione.

### DOVE SALVARE
```
documentazione/
    2025-01-16_fix_flotta_commerciale.md
    2025-01-17_nuova_funzione_export.md
    ...
```

### FORMATO NOME FILE
```
YYYY-MM-DD_descrizione_breve.md
```

### QUANDO RILASCIARE
- Dopo ogni fix completato
- Dopo ogni nuova funzionalita'
- Dopo refactoring
- Prima di chiudere la sessione (riepilogo)

---

## REGOLA AUREA #5 - MODULARITA' ESTREMA AL 100%

### PRINCIPIO FONDAMENTALE
> **Ogni funzione = 1 file satellite separato**
> Non importa se ha 1 riga o 1000, il codice deve essere **ESTREMAMENTE MODULARE**

### STRUTTURA FILE SATELLITE
Ogni componente/funzione ha la propria **cartella dedicata** contenente:
```
templates/componente/
    _sezione.html      # HTML della sezione
    _modal.html        # Modal se presente
    _styles.html       # CSS dedicato
    _scripts.html      # JS dedicato
```

### VANTAGGI
| Aspetto | Beneficio |
|---------|-----------|
| **Manutenzione** | 1 cartella = 1 funzione, tutto in un posto |
| **Scalabilita'** | Aggiungo funzioni senza toccare codice esistente |
| **Debug** | Problema in Car Policy = apro solo quella cartella |
| **Portabilita'** | Copio cartella = copio modulo completo |

### QUANDO CREARE UN NUOVO FILE SATELLITE
**SEMPRE** quando:
- Aggiungo una nuova funzione/sezione
- Una sezione ha logica JS propria
- Una sezione ha CSS specifico
- Una sezione ha modal dedicati

**MAI** tenere piu' funzioni nello stesso file solo perche' "sono poche righe".

---

## REGOLA AUREA #6 - LIMITE 1000 RIGHE PER FILE

### PRINCIPIO
> **Se un file supera le 1000 righe, va smembrato in file piu' piccoli**

### QUANDO APPLICARE
- File Python (.py) > 1000 righe
- File HTML > 500 righe (esclusi include)
- File JS > 500 righe

### COME SMEMBRARE

#### Per file Python (es. web_server.py troppo grande)
Creare **Blueprint separati**:
```python
# app/routes_nuova_funzione.py
from flask import Blueprint
nuova_bp = Blueprint('nuova', __name__)

@nuova_bp.route('/nuova-route')
def nuova_route():
    ...
```

```python
# web_server.py - aggiungere solo:
from app.routes_nuova_funzione import nuova_bp
app.register_blueprint(nuova_bp)
```

#### Per file HTML (es. dettaglio.html troppo grande)
Usare **include Jinja2**:
```html
{% include "dettaglio/sezione/_content.html" %}
```

---

## REGOLA AUREA #7 - CONVENZIONI ID UTENTI

### PRINCIPIO
> **ID utente = codice numerico a 6 cifre**
> Un solo campo, nessuna duplicazione

### FORMATO
- Database: `id INTEGER` (0, 1, 2, 500000, 999999)
- Display: sempre 6 cifre (`000000`, `000001`, `500000`, `999999`)

### RANGE CONSIGLIATI
| Range | Tipo utente |
|-------|-------------|
| 0 | Admin sistema |
| 1-99 | Commerciali |
| 500000+ | Backend/Operatori |
| 999999 | Test |

### CODICE
```python
# Python
f"{id:06d}"  # "000001"

# Jinja2
{{ "%06d"|format(utente.id) }}  # "000001"
```

---

## REGOLA AUREA #8 - COMMERCIALI E BLUEPRINT

### PRINCIPIO
> **Tutte le route commerciali sono nel blueprint `routes_flotta_commerciali.py`**
> NON aggiungere route commerciali in `web_server.py`

### CAMPO DA USARE
- **USARE**: `commerciale_id` (INTEGER, FK a utenti.id)
- **NON USARE**: `commerciale` (TEXT, campo legacy)

### NOMI COMMERCIALI
- **Formato display**: "M. Perani" (iniziale puntata + cognome)
- **Funzione**: `get_commerciale_display(conn, commerciale_id)`

### VISIBILITA'
- **Riepilogo Globale**: visibile a TUTTI gli utenti
- **Dettaglio (card)**: filtrato per subordinati
- **Funzione**: `get_subordinati(conn, user_id)` restituisce [user_id, sub1, sub2, ...]

### GERARCHIA VISIVA
```
M. Perani                  <- livello 0
  +-- C. Pelucchi          <- livello 1 (subordinato)
       +-- F. Zubani       <- livello 2 (subordinato di subordinato)
```

---

## REGOLA AUREA #9 - CONVENZIONE BACKUP E DEPLOY

### PRINCIPIO
> **Ogni file modificato deve avere un backup PRIMA della sostituzione**
> I backup hanno naming univoco con percorso, nome, data e ora

### CARTELLE
| Cartella | Scopo |
|----------|-------|
| `~/gestione_flotta/Scaricati/` | File nuovi/aggiornati scaricati da Claude |
| `~/gestione_flotta/backup/` | Backup dei file prima della modifica |

### FORMATO NOME BACKUP
```
[percorso]__[nomefile].[estensione].bak_[YYYYMMDD]_[HHMMSS]
```

### ESEMPI
| File originale | Nome backup |
|----------------|-------------|
| `app/web_server.py` | `app__web_server.py.bak_20260130_154500` |
| `templates/base.html` | `templates__base.html.bak_20260130_154500` |
| `templates/admin/login.html` | `templates__admin__login.html.bak_20260130_154500` |

### COMANDI DA FORNIRE ALL'UTENTE

Quando fornisco un file nuovo/aggiornato, DEVO sempre dare questi comandi:

```bash
# 1. Backup del file esistente
cp ~/gestione_flotta/[percorso]/[file] ~/gestione_flotta/backup/[percorso]__[file].bak_$(date +%Y%m%d_%H%M%S)

# 2. Spostamento nuovo file
mv ~/gestione_flotta/Scaricati/[file] ~/gestione_flotta/[percorso]/
```

### ESEMPIO COMPLETO
Se modifico `app/web_server.py`:
```bash
# Backup
cp ~/gestione_flotta/app/web_server.py ~/gestione_flotta/backup/app__web_server.py.bak_$(date +%Y%m%d_%H%M%S)

# Deploy
mv ~/gestione_flotta/Scaricati/web_server.py ~/gestione_flotta/app/
```

### VANTAGGI
| Aspetto | Beneficio |
|---------|-----------|
| **Rintracciabilita'** | Il percorso nel nome identifica l'origine |
| **No omonimia** | Data/ora rende ogni backup unico |
| **Storico** | Tutti i backup in una cartella centralizzata |
| **Rollback facile** | Basta copiare il .bak al posto dell'originale |

---

## STRUTTURA PROGETTO (Aggiornata 2026-02-05)

### Repository GitHub
- **URL**: https://github.com/micheleperani76/BRIA
- **Branch**: master
- **Sync Claude**: Project Knowledge collegato al repo
- **Sync script**: `raccolta_file_ia.sh --solo-git` (commit + push)

### .gitignore (file esclusi da GitHub)
```
db/                     # Database SQLite
clienti/                # Dati clienti (privacy)
import_dati/            # CSV/XML import Creditsafe
account_esterni/        # Credenziali servizi esterni
allegati_note/          # Allegati note clienti
audio_trascrizioni/     # File audio
trascrizione/consumo/   # Testi trascrizioni
logs/                   # Log applicazione
backup/                 # Backup file
Scaricati/              # File temporanei
file_per_ia/            # Raccolta per IA
*.zip *.bak *.pyc       # File temporanei
impostazioni/google_calendar/*.json  # Credenziali Google
```

### Cartelle
```
gestione_flotta/
    .git/                         # Repository Git
    .gitignore                    # Esclusioni GitHub
    app/                          # Moduli Python
        config.py                 # Configurazione
        database.py               # Gestione DB
        database_utenti.py        # Gestione utenti + get_subordinati()
        gestione_commerciali.py   # Modulo commerciali centralizzato
        auth.py                   # Autenticazione
        routes_auth.py            # Blueprint auth
        routes_admin_utenti.py    # Blueprint admin
        routes_flotta_commerciali.py  # Blueprint commerciali v2.3.0
        motore_notifiche.py       # Hub centrale notifiche
        routes_notifiche.py       # Blueprint notifiche
        connettori_notifiche/     # Connettori notifiche modulari
        web_server.py             # Server Flask (senza route commerciali)
        ...
    templates/
        admin/                    # Template amministrazione
        dettaglio/                # Componenti modulari dettaglio
        documenti_cliente/        # Sezione documenti
        notifiche/                # Widget campanella
        top_prospect/             # Griglia top prospect
        trattative/               # Gestione trattative
        trascrizione/             # Trascrizione audio
        ...
    db/                           # Database SQLite (escluso da git)
        gestionale.db
    account_esterni/              # Credenziali (escluso da git)
    backup/                       # Backup file con naming strutturato
    Scaricati/                    # File temporanei da deployare
    scripts/                      # Script migrazione/manutenzione
    documentazione/               # File .md documentazione
    impostazioni/                 # Config Excel + .conf
    raccolta_file_ia.sh           # Script fine sessione (v4.0)
    ...
```

---

## COSE DA NON FARE MAI

1. **NON riscrivere file interi** se basta modificare 10 righe
2. **NON assumere** che `/mnt/project/` sia aggiornato
3. **NON modificare** sezioni non richieste
4. **NON dimenticare** di verificare l'encoding dopo le modifiche
5. **NON procedere** senza aver confrontato le versioni dei file
6. **NON mettere** piu' funzioni nello stesso file
7. **NON lasciare** file > 1000 righe senza smembrarli
8. **NON creare** colonne duplicate per lo stesso dato
9. **NON usare** campo `commerciale` (stringa), usare `commerciale_id`
10. **NON aggiungere** route commerciali in web_server.py
11. **NON fornire** file senza comandi di backup e deploy

---

## COSE DA FARE SEMPRE

1. **CHIEDERE** conferma versione file prima di modificare
2. **CONFRONTARE** file utente vs file progetto
3. **USARE** modifiche chirurgiche (str_replace/sed)
4. **VERIFICARE** encoding dopo ogni modifica
5. **MOSTRARE** diff delle modifiche
6. **DOCUMENTARE** cosa e' stato cambiato
7. **RILASCIARE** file .md in `documentazione/` dopo ogni step
8. **CREARE** file satellite per ogni nuova funzione
9. **SMEMBRARE** file > 1000 righe in moduli/blueprint
10. **USARE** `commerciale_id` per le assegnazioni
11. **FORNIRE** comandi backup + deploy per ogni file
12. **AGGIORNARE** questo file a fine sessione

---

## STORICO AGGIORNAMENTI

| Data | Versione | Modifiche |
|------|----------|-----------|
| 2025-01-16 | 1.0 | Creazione documento con regole base |
| 2025-01-16 | 1.1 | Aggiunta Regola Aurea #4 - Documentazione |
| 2025-01-16 | 1.2 | Aggiunta regola trasferimento Chromium |
| 2025-01-20 | 2.0 | Aggiunta Regola Aurea #5 - Modularita' Estrema |
| 2025-01-21 | 3.0 | Aggiunta Regola #6 (limite 1000 righe) e #7 (convenzioni ID) |
| 2025-01-21 | 4.0 | Aggiunta Regola #8 (commerciali e blueprint) |
| 2026-01-30 | 5.0 | Aggiunta Regola #9 (convenzione backup e deploy) |
| 2026-02-05 | 6.0 | Integrazione GitHub: repo BRIA, sync Claude, script v4.0 |

---

## NOTE FINALI

Questo documento deve essere:
- **Allegato SEMPRE** ai file del progetto
- **Aggiornato** a fine sessione con nuove regole/errori scoperti
- **Consultato** all'inizio di ogni sessione

**Ricorda**: E' meglio chiedere una conferma in piu' che rompere il codice funzionante!

**Ricorda**: Ogni funzione = 1 file satellite. Modularita' estrema al 100%!

**Ricorda**: File > 1000 righe = smembrare in moduli/blueprint!

**Ricorda**: Route commerciali = blueprint `routes_flotta_commerciali.py`!

**Ricorda**: Ogni file = backup PRIMA + deploy DOPO!
