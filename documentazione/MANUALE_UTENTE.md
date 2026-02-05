# MANUALE UTENTE - GESTIONE FLOTTA
## BR CAR SERVICE

**Versione**: 1.0  
**Data**: 2026-01-30  
**Applicazione**: http://[server]:5001

---

## INDICE

1. [Accesso al Sistema](#1-accesso-al-sistema)
2. [Dashboard](#2-dashboard)
3. [Gestione Clienti](#3-gestione-clienti)
4. [Scheda Cliente](#4-scheda-cliente)
5. [Gestione Veicoli](#5-gestione-veicoli)
6. [Documenti Cliente](#6-documenti-cliente)
7. [Note e Comunicazioni](#7-note-e-comunicazioni)
8. [Trattative](#8-trattative)
9. [Top Prospect](#9-top-prospect)
10. [Sezione Flotta](#10-sezione-flotta)
11. [Export e Report](#11-export-e-report)
12. [Amministrazione](#12-amministrazione)

---

## 1. ACCESSO AL SISTEMA

### 1.1 Login
- Accedere all'URL del sistema
- Inserire **Username** e **Password**
- Al primo accesso viene richiesto il cambio password obbligatorio

### 1.2 Profilo Personale
- Menu utente in alto a destra &rarr; **Profilo**
- Modificare: nome, cognome, email, cellulare
- Cambiare password volontariamente

### 1.3 Ruoli Utente
| Ruolo | Descrizione |
|-------|-------------|
| **Admin** | Accesso completo a tutte le funzioni |
| **Commerciale** | Gestione clienti assegnati e subordinati |
| **Operatore** | Funzioni backend limitate |

---

## 2. DASHBOARD

La dashboard &egrave; la pagina iniziale dopo il login.

### 2.1 Ricerca Smart
- Barra di ricerca centrale per trovare clienti rapidamente
- Ricerca per: ragione sociale, P.IVA, telefono, email
- La ricerca &egrave; **fuzzy**: ignora punti, spazi e caratteri speciali
- Esempio: cercare "atib" trova "A.T.I.B. SRL"

### 2.2 Comandi Speciali
| Comando | Funzione |
|---------|----------|
| `@com` | Mostra lista commerciali |
| `@ope` | Mostra lista operatori |

---

## 3. GESTIONE CLIENTI

### 3.1 Lista Clienti
- Menu laterale &rarr; **Clienti**
- Tabella con tutti i clienti (filtrabili per visibilit&agrave;)

### 3.2 Filtri Disponibili
| Filtro | Descrizione |
|--------|-------------|
| **Ricerca Smart** | Cerca in ragione sociale, P.IVA, telefono |
| **Stato Cliente** | Filtra per stato CRM |
| **Forma Giuridica** | SRL, SPA, Ditta Individuale, ecc. |
| **Commerciale** | Filtra per commerciale assegnato |
| **Scaglione Flotta** | Filtra per dimensione parco veicoli |

### 3.3 Colonne Tabella
Le colonne possono essere nascoste/mostrate cliccando sull'icona ingranaggio.

### 3.4 Indicatori Visivi
| Icona | Significato |
|-------|-------------|
| **CP** (verde) | Car Policy presente |
| **!** (rosso) | Documenti scaduti |
| **T** (blu) | Trattativa in corso |

---

## 4. SCHEDA CLIENTE

### 4.1 Accesso
- Click sulla riga cliente nella lista
- URL stabile: `/c/IT[PIVA]` (es. `/c/IT00552060980`)

### 4.2 Sezioni Disponibili

#### Dati Aziendali
- Ragione sociale, P.IVA, Codice Fiscale
- Forma giuridica, Numero REA
- SDI, BIC (modificabili manualmente)

#### Capogruppo
- Collegamento a eventuale societ&agrave; madre
- Protezione da sovrascrittura import

#### Contatti Generali
- Telefono, email, PEC, sito web
- Modificabili tramite icona matita

#### Referenti
- Lista referenti aziendali con ruolo
- Aggiungere/modificare/eliminare referenti
- Impostare referente principale

#### Indirizzo e Sede
- Sede legale con mappa
- Gestione sedi operative multiple

#### Noleggiatori
- Lista noleggiatori associati al cliente
- Stato relazione (Attivo, Prospect, ecc.)
- Colori identificativi per brand

#### Collegamenti
- Relazioni con altre aziende (consociate, filiali, partner)
- Relazioni bidirezionali configurabili

#### Flotta Veicoli
- Riepilogo veicoli per tipologia
- Statistiche: totale, in scadenza, scaduti
- Link a dettaglio veicoli

---

## 5. GESTIONE VEICOLI

### 5.1 Accesso Scheda Veicolo
- Dalla scheda cliente &rarr; sezione Flotta
- Click su riga veicolo

### 5.2 Dati Veicolo
- Targa, marca, modello
- Noleggiatore, durata contratto
- Date: immatricolazione, inizio/fine noleggio
- Costi: canone, servizi, totale

### 5.3 Funzioni Disponibili
| Funzione | Descrizione |
|----------|-------------|
| **Modifica Targa** | Correzione targa errata |
| **Driver** | Assegnazione conducente |
| **Km Rilevati** | Registrazione chilometraggio |
| **Franchigia Km** | Impostazione limite km |
| **Costi Extra** | Costi carburante, pedaggi, ecc. |
| **Note Veicolo** | Annotazioni sul veicolo |

### 5.4 Link Esterni
- **Portale Noleggiatore**: accesso diretto al portale
- **Assistenza**: contatti centro assistenza
- **Guida Restituzione**: istruzioni per riconsegna

---

## 6. DOCUMENTI CLIENTE

### 6.1 Accesso
- Scheda cliente &rarr; Tab **Documenti**

### 6.2 Categorie Documenti

#### Car Policy
- Documenti policy aziendale
- Drag &amp; Drop per upload
- Conversione automatica in PDF
- File "fissabili" in alto

#### Contratti
- Contratti di noleggio firmati
- Organizzati per data

#### Quotazioni
- Preventivi e offerte
- Storico quotazioni

#### Documenti Strutturati
- Checklist basata su forma giuridica
- Documenti con scadenza (es. Visura Camerale)
- Indicatore completamento

### 6.3 Gestione File
| Azione | Descrizione |
|--------|-------------|
| **Upload** | Trascina file o click su area |
| **Rinomina** | Click destro &rarr; Rinomina |
| **Elimina** | Click destro &rarr; Elimina |
| **Converti PDF** | Per file .doc/.docx/.odt |
| **Scarica** | Click sul nome file |

---

## 7. NOTE E COMUNICAZIONI

### 7.1 Note Cliente
- Scheda cliente &rarr; sezione **Note**
- Note ordinate per data (pi&ugrave; recenti in alto)

### 7.2 Creare una Nota
1. Click **Nuova Nota**
2. Inserire testo
3. Opzionale: allegare file
4. Salvare

### 7.3 Funzioni Note
| Funzione | Descrizione |
|----------|-------------|
| **Fissa** | Blocca nota in alto |
| **Modifica** | Modifica testo |
| **Elimina** | Sposta nel cestino |
| **Allegati** | Aggiungi/rimuovi file |
| **Cerca** | Ricerca nel testo delle note |

### 7.4 Vista Fullscreen
- Click icona espandi per vista a schermo intero
- Ideale per molte note

### 7.5 Cestino
- Note eliminate vanno nel cestino
- Ripristinabili o eliminabili definitivamente

---

## 8. TRATTATIVE

### 8.1 Accesso
- Menu laterale &rarr; **Trattative**
- Oppure: scheda cliente &rarr; pulsante **Trattativa**

### 8.2 Creare una Trattativa
1. Click **Nuova Trattativa**
2. Selezionare cliente (ricerca smart)
3. Scegliere tipo (Nuovo Cliente, Estensione, Rinnovo, ecc.)
4. Impostare numero veicoli e valore
5. Salvare

### 8.3 Stati Trattativa
| Stato | Descrizione |
|-------|-------------|
| **In Corso** | Trattativa attiva |
| **Chiusa Vinta** | Contratto acquisito |
| **Chiusa Persa** | Trattativa non conclusa |
| **Cancellata** | Rimossa (soft delete) |

### 8.4 Avanzamento
- Percentuale 0-100%
- Aggiornare con note di avanzamento
- Storico avanzamenti visibile

### 8.5 Griglie
- **In Corso**: trattative attive
- **Chiuse**: storico trattative concluse
- **Cancellate**: trattative rimosse (ripristinabili)

---

## 9. TOP PROSPECT

### 9.1 Cos'&egrave;
Sistema automatico per identificare i migliori potenziali clienti basandosi su parametri configurabili.

### 9.2 Accesso
- Menu laterale &rarr; **Top Prospect**

### 9.3 Griglie

#### Candidati
- Clienti identificati automaticamente dal sistema
- Azioni: Conferma, Scarta, Archivia

#### Confermati
- Clienti promossi a Top Prospect attivi
- Gestione appuntamenti
- Note dedicate

#### Archiviati
- Ex Top Prospect non pi&ugrave; attivi
- Ripristinabili

### 9.4 Parametri Analisi
- Configurabili da admin
- Basati su: flotta, trend, settore, zona

### 9.5 Appuntamenti
- Creazione appuntamenti per ogni Top Prospect
- Sincronizzazione con Google Calendar
- Notifiche e promemoria

### 9.6 Note Top Prospect
- Sistema note dedicato
- Allegati supportati
- Storico attivit&agrave;

---

## 10. SEZIONE FLOTTA

### 10.1 Report Disponibili

#### Per Noleggiatore
- Menu &rarr; Flotta &rarr; **Per Noleggiatore**
- Riepilogo veicoli raggruppati per noleggiatore
- Scadenze imminenti evidenziate

#### Per Commerciale
- Menu &rarr; Flotta &rarr; **Per Commerciale**
- Veicoli raggruppati per commerciale assegnato
- Visibilit&agrave; gerarchica (solo subordinati)

#### Per Cliente
- Dalla scheda cliente &rarr; Flotta
- Dettaglio completo veicoli cliente

### 10.2 Ricerca Veicoli
- Cerca per targa, cliente, noleggiatore
- Filtri avanzati disponibili

### 10.3 Gestione Assegnazioni (Admin)
- Menu &rarr; Flotta &rarr; **Gestione Commerciali**
- Assegnazione massiva clienti a commerciali
- Storico assegnazioni

---

## 11. EXPORT E REPORT

### 11.1 Export Excel
- Menu &rarr; **Export Excel**
- Selezione colonne da esportare
- Nome file personalizzabile

### 11.2 Colonne Disponibili
- Dati anagrafici cliente
- Contatti
- Statistiche flotta
- Commerciale assegnato

### 11.3 Export Evernote
- Dalla scheda cliente &rarr; **Export Evernote**
- Genera file importabile in Evernote

---

## 12. AMMINISTRAZIONE

### 12.1 Accesso
- Menu &rarr; **Admin** (solo utenti autorizzati)

### 12.2 Gestione Utenti
| Funzione | Descrizione |
|----------|-------------|
| **Nuovo Utente** | Creazione account |
| **Reset Password** | Genera password temporanea |
| **Permessi** | Assegnazione permessi individuali |
| **Supervisioni** | Gerarchia commerciali |
| **Attiva/Disattiva** | Blocco account |

### 12.3 Import Creditsafe
- Upload PDF report Creditsafe
- Import automatico dati aziendali
- Aggiornamento database clienti

### 12.4 Log e Storico
- **Log Accessi**: storico login utenti
- **Storico Assegnazioni**: chi ha assegnato cosa
- **Storico Collegamenti**: modifiche relazioni clienti

### 12.5 Configurazione
- Gestione crontab per import automatici
- Pulizia log vecchi

---

## SCORCIATOIE DA TASTIERA

| Tasto | Funzione |
|-------|----------|
| `/` | Focus su ricerca |
| `Esc` | Chiudi modal |

---

## SUPPORTO

Per problemi tecnici contattare l'amministratore di sistema.

---

*Documento generato il 2026-01-30*

---

## TRASCRIZIONE AUDIO

### Accesso
Dal menu laterale, cliccare su **Trascrizione**.

### Upload Audio
1. Trascinare un file audio nell'area di upload (drag &amp; drop)
2. Oppure cliccare per selezionare il file
3. Formati supportati: AAC, MP3, WAV, OGG, M4A, FLAC, WMA, WEBM
4. Dimensione massima: 500 MB
5. Upload consentito in qualsiasi orario (elaborazione automatica in base alla coda)

### Le Mie Trascrizioni
La colonna sinistra mostra le trascrizioni personali con stato:
- **Verde (Completato)**: testo pronto, cliccabile per anteprima
- **Blu (In lavorazione)**: elaborazione in corso
- **Giallo (In attesa)**: in coda
- **Rosso (Errore)**: elaborazione fallita

### Spostamento su Cliente
1. Cliccare l'icona freccia sulla trascrizione completata
2. Cercare il cliente per nome (ricerca fuzzy)
3. Confermare lo spostamento
4. Il file diventa permanente nella cartella del cliente

### Trascrizioni nella Scheda Cliente
Nella pagina documenti di ogni cliente, il riquadro **Trascrizioni** mostra:
- Lista file con data e dimensione
- **Occhio**: anteprima testo con copia clipboard
- **Download**: scarica file .txt
- **Matita**: rinomina file (rinomina anche audio associato)
- **Modifica testo**: correzione testo trascritto con salvataggio
- **Cestino**: elimina trascrizione
- **Ricerca**: barra di ricerca full-text nelle trascrizioni
- **Upload diretto**: drag & drop per caricare audio direttamente sul cliente

Il riquadro supporta upload multiplo con progress bar sequenziale.
Dopo la chiusura dell'anteprima, la lista si riapre automaticamente.

### Coda Elaborazione
Il pulsante "Stato Coda" mostra:
- Job attualmente in elaborazione (solo nome utente, no dettagli file)
- Job in attesa con tempo stimato cumulativo (somma di tutti i job davanti)
- Formato tempo leggibile: minuti, ore o giorni
- Bottone **X** per eliminare un proprio job in attesa (admin puo' eliminare qualsiasi job)

### Protezione Orario Automatica
Il sistema gestisce automaticamente la coda:
- Se un job e' troppo lungo per completarsi prima delle 4:00, viene posticipato
- Il worker prova job piu' corti che possono entrare nell'orario rimasto
- Se nessun job ci sta, attende il giorno dopo alle 7:00
- Il widget flottante (FAB) appare quando hai job in corso

### Retention
- **Testo consumo**: eliminato dopo 21 giorni (spostare su cliente!)
- **Testo cliente**: permanente
- **Audio**: eliminato dopo l'elaborazione (non conservato)

---

## EXPORT AVANZATO

### Accesso
Dal menu laterale, cliccare su **Export / Stampa**.

### Tab Disponibili
- **Clienti**: export lista clienti con filtri
- **Top Prospect**: export confermati con dati flotta
- **Trattative**: export con filtri per stato, tipo, noleggiatore, commerciale, date

### Formati
- Excel (.xlsx) con formattazione
- CSV per importazione in altri sistemi
