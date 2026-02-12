# 2026-02-12 - Nomi Alternativi / Keyword Ricerca Cliente

## Descrizione
Aggiunta funzionalita' per associare nomi alternativi, sigle, abbreviazioni e keyword
speciali ai clienti, indicizzati nella ricerca smart (dashboard + lista clienti + API).

## Nuova Tabella DB

### `clienti_nomi_alternativi`
| Campo | Tipo | Note |
|-------|------|------|
| id | INTEGER PK | Autoincrement |
| cliente_id | INTEGER FK | Riferimento a clienti(id), CASCADE delete |
| nome_alternativo | TEXT NOT NULL | Nome/keyword (max 200 char) |
| data_creazione | TIMESTAMP | Default CURRENT_TIMESTAMP |
| creato_da | INTEGER FK | Riferimento a utenti(id) |

**Indici**: idx_nomi_alt_cliente (cliente_id), idx_nomi_alt_nome (nome_alternativo NOCASE)

## Interfaccia

### Pulsante "Alias" nel riquadro Dati Aziendali
- Posizione: card-header, a destra del titolo
- Badge viola con conteggio nomi alternativi
- Click apre modal di gestione

### Modal Nomi Alternativi
- Input con Enter per aggiungere
- Lista con pulsante elimina per ogni nome
- Controllo duplicati case-insensitive
- Log attivita' su ogni operazione

## API

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/cliente/<id>/nomi-alternativi` | GET | Lista nomi alternativi |
| `/api/cliente/<id>/nomi-alternativi` | POST | Aggiungi nome (body: nome_alternativo) |
| `/api/cliente/<id>/nomi-alternativi/<nome_id>` | DELETE | Rimuovi nome |

## Ricerca Smart - Indicizzazione

### `/api/cerca` (barra dashboard)
- Aggiunta subquery su `clienti_nomi_alternativi`
- Ricerca esatta + fuzzy (normalizzazione punti, spazi, trattini, &, apostrofi)

### Lista clienti (route principale `/`)
- Aggiunta EXISTS subquery su `clienti_nomi_alternativi` (31 parametri LIKE, era 30)

### `get_search_matches_per_cliente` (badge lista clienti)
- Nuovo tipo match: `alias`
- Badge viola nella tabella clienti quando il match avviene su un nome alternativo

## File Nuovi
| File | Descrizione |
|------|-------------|
| `templates/dettaglio/nomi_alternativi/_modal.html` | Modal gestione nomi |
| `templates/dettaglio/nomi_alternativi/_scripts.html` | JavaScript CRUD |
| `scripts/installa_nomi_alternativi.py` | Script installazione completa |
| `scripts/migrazione_nomi_alternativi.py` | Script migrazione DB standalone |

## File Modificati
| File | Tipo modifica |
|------|--------------|
| `templates/dettaglio/dati_aziendali/_content.html` | Card-header con pulsante Alias + badge |
| `templates/dettaglio.html` | Include modal + scripts nomi alternativi |
| `app/web_server.py` | API CRUD (3 route) + ricerca /api/cerca + ricerca lista clienti + badge match alias |
| `templates/index/_tabella.html` | Badge Alias viola nei risultati ricerca |
| `db/gestionale.db` | Nuova tabella + 2 indici |

## Note Installazione
Lo script `installa_nomi_alternativi.py` ha un bug nel check idempotenza dello step 5
(API routes): cercava la stringa "nomi_alternativi" nel file ma la trovava nella patch
ricerca anziche' nelle route API, risultando in falso SKIP. Le API sono state inserite
manualmente con sed. La patch ricerca lista clienti (31 params) e' stata aggiunta
separatamente con patch Python chirurgica.
