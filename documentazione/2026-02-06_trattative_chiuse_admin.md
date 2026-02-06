# TRATTATIVE CHIUSE - PERMESSI ADMIN
## Modifiche del 06/02/2026

**Versione**: 1.1
**Richiesta**: Solo admin puo' cancellare o riaprire trattative dal riquadro Trattative Chiuse

---

## MODIFICHE IMPLEMENTATE

### 1. Backend - motore_trattative.py

#### Modifica funzione `trattativa_cancellabile()`
- **Prima**: Trattative chiuse non cancellabili da nessuno (`return False`)
- **Dopo**: Admin puo' cancellare anche le trattative chiuse (`return is_admin`)

#### Nuova funzione `riapri_trattativa()`
Riapre una trattativa chiusa riportandola allo stato "Preso in carico":
- Verifica che la trattativa sia chiusa (non cancellata)
- Resetta stato a "Preso in carico"
- Rimuove data_chiusura
- Registra avanzamento con nota "Trattativa riaperta da admin"

---

### 2. Backend - routes_trattative.py

#### Nuovo import
- `riapri_trattativa` aggiunto agli import da motore_trattative

#### Nuovo endpoint
```
POST /trattative/api/<id>/riapri
```
- **Accesso**: Solo admin
- **Funzione**: Riapre trattativa chiusa
- **Risposta**: `{"success": true, "message": "Trattativa riaperta con successo"}`

---

### 3. Frontend - _scripts_chiuse.html

#### Flag admin
```javascript
var isAdminChiuse = {{ 'true' if session.get('ruolo_base') == 'admin' else 'false' }};
```

#### Bottoni nella colonna Azioni (visibilita' condizionale)
| Bottone | Icona | Visibilita' | Funzione |
|---------|-------|-------------|----------|
| Storico | bi-eye | Tutti | toggleEspandi() |
| Riapri | bi-arrow-counterclockwise (verde) | Solo admin | riapriTrattativa() |
| Cancella | bi-trash (rosso) | Solo admin | cancellaTrattativaChiusa() |

---

### 4. Fix Grafici - Allineamento Griglie

#### _styles.html
- Aggiunto selettori per `#tabellaTrattativeChiuse`
- Aggiunto `table-layout: fixed` + `width: 100%`
- Aggiunto CSS ellipsis per celle con testo lungo

#### _griglia.html e _griglia_chiuse.html
- Header con larghezze fisse per tutte le colonne:
  - Cliente: 18%
  - Noleggiatore: 8%
  - Veicolo: 10%
  - Tipologia: 7%
  - Tipo: 10%
  - Pz: 35px
  - Stato: 9%
  - Avanz.: 70px
  - Date: 85px ciascuna
  - Commerciale: 10%
  - Azioni: 100px

---

## FILE MODIFICATI

| File | Tipo Modifica |
|------|---------------|
| `app/motore_trattative.py` | Modifica funzione + nuova funzione |
| `app/routes_trattative.py` | Nuovo import + nuovo endpoint |
| `templates/trattative/_scripts_chiuse.html` | Flag + bottoni + funzioni JS |
| `templates/trattative/_styles.html` | CSS unificato + layout fisso |
| `templates/trattative/_griglia.html` | Header con larghezze fisse |
| `templates/trattative/_griglia_chiuse.html` | Header con larghezze fisse |

---

## BUG CORRETTI

1. **Campo `percentuale` inesistente**: Rimosso da UPDATE in `riapri_trattativa()`
2. **Colonne avanzamenti errate**: Corretto INSERT con colonne corrette (`stato`, `note_avanzamento`, `data_avanzamento`, `registrato_da`)
3. **CSS fuori tag style**: Ripristinato e corretto
4. **Griglie disallineate**: Unificati stili e larghezze colonne

---

## BACKUP CREATI

- `backup/app__motore_trattative.py.bak_20260206_*`
- `backup/app__routes_trattative.py.bak_20260206_*`
- `backup/templates__trattative___scripts_chiuse.html.bak_20260206_*`
- `backup/templates__trattative___styles.html.bak_20260206_*`
