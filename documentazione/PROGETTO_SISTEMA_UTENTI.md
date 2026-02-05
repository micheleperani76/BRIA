# PROGETTO SISTEMA UTENTI v3.0 - GESTIONE FLOTTA
**Data**: 2025-01-20
**Versione**: 3.0
**Stato**: ✅ IMPLEMENTATO
**Progetto**: gestione_flotta (BR CAR SERVICE)

---

## 🎯 OBIETTIVO

Sistema **enterprise-grade** di autenticazione, autorizzazione e gestione utenti con:
- **Gerarchia supervisioni a cascata** (chi vede chi)
- **Permessi granulari per utente** (checkbox individuali)
- **Database normalizzato** (relazioni solide)
- **Profilo personale** (ogni utente gestisce i propri dati)
- **Validazione unicità** (email e cellulare unici)

---

## 👥 UTENTI

### Codici Utente
Formato numerico 6 cifre: `000000`, `000001`, `000002`, ...
Codice `999999` riservato per utenti di test.

### Utenti Attuali
| ID | Codice | Username | Nome | Cognome | Ruolo |
|----|--------|----------|------|---------|-------|
| 1 | 000000 | admin | Amministratore | Sistema | Admin |
| 2 | 000001 | p.ciotti | Paolo | Ciotti | Commerciale |
| 3 | 000002 | m.perani | Michele | Perani | Commerciale |
| 4 | 000003 | c.pelucchi | Cristian | Pelucchi | Commerciale |
| 5 | 000004 | f.zubani | Fausto | Zubani | Commerciale |
| 6 | 999999 | prova | Test | Utente | Commerciale |

### Gerarchia Supervisioni
```
ADMIN (sistema)
    │
    └── Gestisce tutti gli utenti e configurazioni
    
PAOLO CIOTTI (supervisore top)
    │
    ├── MICHELE PERANI
    ├── CRISTIAN PELUCCHI
    └── FAUSTO ZUBANI
```

---

## 📁 STRUTTURA FILE

```
gestione_flotta/
├── app/
│   ├── auth.py                 # Funzioni autenticazione e sessione
│   ├── routes_auth.py          # Route login/logout/profilo
│   ├── routes_admin_utenti.py  # Route gestione utenti
│   ├── database_utenti.py      # Funzioni database utenti
│   └── web_server.py           # Route principali (con filtro supervisioni)
├── templates/
│   ├── auth/
│   │   ├── _base_auth.html     # Base template autenticazione
│   │   ├── login.html          # Pagina login
│   │   ├── cambio_password.html # Cambio password (obbligato/volontario)
│   │   ├── completa_profilo.html # Primo accesso
│   │   └── profilo.html        # Profilo personale
│   ├── admin/
│   │   ├── utenti_lista.html   # Griglia utenti
│   │   ├── utente_dettaglio.html # Scheda utente con permessi
│   │   └── log_accessi.html    # Log accessi utente
│   └── base.html               # Layout con menu (link profilo)
├── impostazioni/
│   ├── email_config.conf       # Validazione dominio email
│   └── mappatura_ip.xlsx       # IP/reti conosciute
└── db/
    └── gestionale.db           # Database SQLite
```

---

## 🗄️ SCHEMA DATABASE

### Tabelle Principali
- `utenti` - Anagrafica utenti
- `supervisioni` - Relazioni supervisore/subordinato
- `permessi_catalogo` - Catalogo permessi disponibili
- `utenti_permessi` - Permessi assegnati a ciascun utente
- `log_accessi` - Log login/logout/cambio password
- `log_attivita` - Log operazioni (modifica utenti, permessi, ecc.)

### Colonne Tabella `utenti`
```sql
id, codice_utente, username, password_hash,
nome, cognome, email, cellulare, data_nascita,
ruolo_base, attivo, pwd_temporanea, profilo_completo,
bloccato, tentativi_falliti,
non_cancellabile, non_modificabile,
data_creazione, data_ultimo_accesso, creato_da
```

---

## 🔐 PERMESSI

### Categorie
| Categoria | Permessi |
|-----------|----------|
| **clienti** | visualizza, modifica, note_visualizza, note_modifica |
| **documenti** | visualizza, carica, elimina |
| **veicoli** | visualizza, modifica |
| **strumenti** | export_excel, import_creditsafe |
| **statistiche** | proprie, globali |
| **admin** | utenti, permessi, sistema |

### Permessi Default per Ruolo
- **Admin**: Tutti i permessi
- **Commerciale**: Tutti tranne admin_*
- **Operatore**: Visualizza + modifica base
- **Viewer**: Solo visualizzazione

---

## 🖥️ FUNZIONALITÀ UI

### Gestione Utenti (`/admin/utenti`)
- Griglia ordinabile per colonne
- Statistiche rapide (totali, attivi, password temp, bloccati)
- Creazione nuovo utente con password temporanea
- Sblocco utenti bloccati

### Scheda Utente (`/admin/utenti/<id>`)
- Modifica username (pulsante matita)
- Visualizzazione dati anagrafici
- Cambio ruolo con aggiornamento permessi automatico
- Reset password
- Attiva/Disattiva utente
- Sblocca utente
- Gestione supervisioni (aggiungi/rimuovi)
- Griglia permessi con checkbox

### Profilo Personale (`/auth/profilo`)
- Visualizza/modifica dati personali
- Data di nascita (opzionale)
- Cambio password volontario
- Visualizza permessi (sola lettura)

### Login (`/auth/login`)
- Flusso primo accesso:
  1. Login con password temporanea
  2. Cambio password obbligatorio
  3. Completamento profilo (nome, cognome, email, cellulare)
- Blocco dopo 5 tentativi falliti
- Log IP e user agent

---

## ✅ VALIDAZIONI

### Email
- Dominio obbligatorio se configurato in `email_config.conf`
- Unicità nel sistema

### Cellulare
- Unicità nel sistema

### Username
- Solo lettere minuscole, numeri, punti e underscore
- Unicità nel sistema

### Password
- Minimo 8 caratteri

---

## 📊 LOG

### Log Accessi
Registra: login_ok, login_fallito, logout, cambio_pwd, profilo_completato, modifica_profilo

### Log Attività
Registra: creazione utente, modifica ruolo, modifica username, reset password, attiva/disattiva, sblocco, modifica permessi, supervisioni

---

## 🔧 CONFIGURAZIONE

### File `impostazioni/email_config.conf`
```ini
[email]
dominio_obbligatorio = brcarservice.it
```

### File `impostazioni/mappatura_ip.xlsx`
Mappa IP → Nome rete (es: 192.168.1.x → "Rete Locale Ufficio")

---

## 📋 STATO IMPLEMENTAZIONE

| Fase | Descrizione | Stato |
|------|-------------|-------|
| 1 | Database e tabelle | ✅ |
| 2 | Autenticazione base | ✅ |
| 3 | Protezione route | ✅ |
| 4 | Pannello admin utenti | ✅ |
| 5 | Filtro supervisioni | ✅ |
| 6 | Permessi granulari | ✅ |
| 7 | UI e profilo personale | ✅ |

---

## 📝 PATCH APPLICATE

- `2025-01-20_fase1_sistema_utenti.md` - Database
- `2025-01-20_fase2_autenticazione.md` - Login/logout
- `2026-01-20_sessione_sistema_utenti.md` - Riepilogo generale
- `2025-01-20_fase7_ui_profilo_personale.md` - UI e profilo

---

*Documento aggiornato - Sessione 2025-01-20*
