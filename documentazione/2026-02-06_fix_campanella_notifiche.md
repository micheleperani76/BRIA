# Fix Campanella Notifiche - Non Visibile

**Data**: 06 Febbraio 2026
**Problema**: Campanella notifiche non visibile nonostante notifiche presenti nel DB

---

## DIAGNOSI

### Sintomo
Widget campanella invisibile (`display: none`) su tutte le pagine.

### Indagine
1. Backend OK: API `/notifiche/api/contatore` risponde correttamente (401 senza login)
2. DB OK: 20 notifiche attive, 16 non lette globali
3. Template OK: `_campanella.html` incluso in `base.html` riga 566
4. Log OK: nessun errore
5. Widget presente nel DOM ma `display: none`
6. **API restituisce `{"contatore": 0}`** per utente m.perani (id=2)

### Causa
Le 3 notifiche non lette dell'utente m.perani avevano `archiviata = 1`:

| notifica_id | titolo | letta | archiviata |
|-------------|--------|-------|------------|
| 13 | Trattativa: In firma | 0 | **1** |
| 15 | Trattativa: Perso | 0 | **1** |
| 19 | Trattativa: Perso | 0 | **1** |

La query del contatore filtra `AND nd.archiviata = 0`, quindi escludeva tutte
le notifiche e restituiva 0. La campanella appare solo con contatore > 0.

### Causa probabile archiviazione
L'utente ha cliccato la X (archivia) nel dropdown campanella sulle notifiche
senza prima leggerle. Nessun altro modulo chiama `archivia_notifica()`.

---

## FIX APPLICATO

```sql
UPDATE notifiche_destinatari 
SET archiviata = 0 
WHERE utente_id = 2 AND letta = 0 AND archiviata = 1;
```

---

## VERIFICHE COLLATERALI

### Gerarchia supervisori - FUNZIONANTE
La catena gerarchica per le trattative funziona correttamente:
- utente 999999 (prova) -> supervisore 2 (m.perani) -> supervisore 1 (p.ciotti)
- Il connettore `trattative.py` usa `_risali_catena_supervisori()` 
- Le notifiche trattative arrivano correttamente a tutta la catena

### File coinvolti (non modificati)
- `templates/notifiche/_campanella.html` - Widget + JS polling
- `app/routes_notifiche.py` - API campanella
- `app/motore_notifiche.py` - Hub notifiche con `_risolvi_destinatari()`
- `app/connettori_notifiche/trattative.py` - Connettore trattative con catena gerarchica

---

## NOTE
Nessuna modifica al codice. Solo fix dati nel DB.
