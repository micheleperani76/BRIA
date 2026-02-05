# REGOLA ARCHITETTURALE - Fonte Unica di Verita'

**Data**: 2026-01-30
**Versione**: 1.0.0
**Applicazione**: Tutti i moduli del progetto

---

## PRINCIPIO FONDAMENTALE

> **Ogni tipo di informazione deve avere UNA SOLA fonte nel codice.**
> 
> Se la stessa informazione serve in piu' punti, deve esistere UNA funzione 
> centralizzata che la fornisce. Tutti gli altri punti del codice DEVONO 
> usare quella funzione.
>
> **Un'unica modifica per variare tutti i punti collegati.**

---

## PERCHE' QUESTA REGOLA

### Problema Tipico
```
Pagina A: prende il colore commerciale dalla tabella utenti
Pagina B: prende il colore commerciale dall'evento calendar
Pagina C: prende il colore commerciale da una query custom

Risultato: 3 comportamenti diversi, bug difficili da tracciare
```

### Soluzione Corretta
```
Modulo centralizzato: get_info_commerciale_cliente(conn, cliente_id)
Pagina A, B, C: usano tutte la stessa funzione

Risultato: comportamento uniforme, una sola modifica per correggere ovunque
```

---

## APPLICAZIONE PRATICA

### Info Commerciale (incluso colore)

**FONTE UNICA**: `app/gestione_commerciali.py`

```python
# Per un singolo cliente
from app.gestione_commerciali import get_info_commerciale_cliente
info = get_info_commerciale_cliente(conn, cliente_id)
# Restituisce: id, nome, cognome, display, colore_id, colore_hex, fonte

# Per piu' clienti (ottimizzato, evita N+1 queries)
from app.gestione_commerciali import get_info_commerciale_bulk
info_map = get_info_commerciale_bulk(conn, [cliente_id_1, cliente_id_2, ...])
# Restituisce: {cliente_id: info_commerciale, ...}

# Per un commerciale dato il suo ID utente
from app.gestione_commerciali import get_info_commerciale
info = get_info_commerciale(conn, commerciale_id)
```

**Gestisce automaticamente:**
- Campo nuovo `commerciale_id` (integer, FK a utenti)
- Campo legacy `commerciale` (stringa con cognome)
- Fallback trasparente tra i due

**MAI FARE** query dirette come:
```python
# SBAGLIATO - query sparsa nel codice
cursor.execute('SELECT colore_calendario FROM utenti WHERE id = ?', ...)

# SBAGLIATO - duplica la logica
cursor.execute('''
    SELECT u.cognome, u.colore_calendario 
    FROM clienti c JOIN utenti u ON c.commerciale_id = u.id
    WHERE c.id = ?
''', ...)
```

---

### Colori Calendario

**FONTE UNICA**: `app/google_calendar.py`

```python
from app.google_calendar import get_hex_colore, COLORI_CALENDARIO

# Converti ID colore in HEX
hex_color = get_hex_colore(colore_id)  # '#039be5'

# Mappa completa colori disponibili
COLORI_CALENDARIO[7]  # {'nome': 'Pavone', 'hex': '#039be5', 'disponibile': True}
```

---

### Stati Cliente/CRM/Noleggiatore

**FONTE UNICA**: `app/config_stati.py`

```python
from app.config_stati import (
    get_stato_cliente_colore,
    get_stato_crm_colore,
    get_stato_noleggiatore_colore,
    get_colore_flotta
)
```

---

## MODULI CENTRALIZZATI

| Tipo Informazione | Modulo | Funzioni Principali |
|-------------------|--------|---------------------|
| Commerciali | `gestione_commerciali.py` | `get_info_commerciale()`, `get_info_commerciale_cliente()`, `get_info_commerciale_bulk()` |
| Utenti | `database_utenti.py` | `get_utente_by_id()`, `get_subordinati()` |
| Stati/Colori | `config_stati.py` | `get_stato_*_colore()`, `carica_stati_*()` |
| Calendario | `google_calendar.py` | `get_hex_colore()`, `COLORI_CALENDARIO` |
| Top Prospect | `motore_top_prospect.py` | `get_candidati()`, `get_top_prospect_confermati()` |
| Trattative | `motore_trattative.py` | `get_trattative()`, `get_trattativa()` |
| Car Policy | `connettori_stato_cliente.py` | `get_car_policy_singolo()` |

---

## CHECKLIST NUOVA FUNZIONALITA'

Quando sviluppi una nuova funzionalita', chiediti:

1. **Questa informazione esiste gia' da qualche parte?**
   - Se si': usa la funzione esistente
   - Se no: crea una funzione centralizzata nel modulo appropriato

2. **Sto duplicando una query?**
   - Se si': estrai in una funzione nel modulo appropriato

3. **Dove metto la funzione?**
   - Info commerciali -> `gestione_commerciali.py`
   - Info utenti -> `database_utenti.py`
   - Stati/colori -> `config_stati.py`
   - Calendario -> `google_calendar.py`

4. **La funzione gestisce tutti i casi?**
   - Campi legacy (stringhe)
   - Campi nuovi (ID/FK)
   - Valori NULL/mancanti

---

## ESEMPIO CORRETTO

### Prima (SBAGLIATO)
```python
# In routes_top_prospect.py - query duplicata, logica dispersa
cursor.execute('''
    SELECT u.cognome, u.colore_calendario 
    FROM utenti u
    JOIN clienti c ON c.commerciale_id = u.id
    WHERE c.id = ?
''', (cliente_id,))
# Non gestisce campo legacy 'commerciale'
```

### Dopo (CORRETTO)
```python
# In routes_top_prospect.py - usa funzione centralizzata
from app.gestione_commerciali import get_info_commerciale_cliente

info = get_info_commerciale_cliente(conn, cliente_id)
if info:
    nome = info['display']           # 'M. Perani' o 'Prova' (legacy)
    colore = info['colore_hex']      # '#039be5' o None
    fonte = info['fonte']            # 'commerciale_id' o 'commerciale_legacy'
```

---

## NOTE FINALI

- Questa regola **SI APPLICA SEMPRE**, anche per query "semplici"
- Se trovi codice che viola questa regola, **SEGNALALO** e proponine la correzione
- Quando aggiungi una nuova fonte centralizzata, **DOCUMENTA** in questo file
- Le funzioni centralizzate devono gestire **TUTTI** i casi edge (legacy, NULL, etc.)

**Ricorda**: Un'unica modifica per variare tutti i punti collegati!
