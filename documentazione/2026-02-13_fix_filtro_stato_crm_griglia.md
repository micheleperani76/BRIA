# Fix Filtro Stato Cliente → Stato CRM nella Griglia Clienti

**Data**: 2026-02-13
**File modificato**: `app/web_server.py`
**Tipo**: Fix - Correzione filtro dropdown

---

## Problema

Il dropdown "Stato Cliente" nella griglia clienti (`/clienti`) filtrava sul campo `stato_cliente` della tabella `clienti`, che era praticamente vuoto (2869 su 2870 record NULL). Il campo corretto da usare è `stato_crm`, popolato dall'import CRM Zoho con 7 valori reali.

### Valori stato_crm nel DB
| Valore | Conteggio |
|--------|-----------|
| Prospetto | 2073 |
| Cliente | 331 |
| (vuoto) | 244 |
| Cliente non più attivo | 170 |
| Prospetto Canale Tecnico | 24 |
| Cliente Canale Tecnico | 17 |
| Cliente senza relazione | 7 |
| Cliente Canale Tecnico non più attivo | 4 |

---

## Modifiche applicate (5 sed chirurgici)

### Punto 1: Query dropdown (popola le opzioni)
```sql
-- PRIMA:
SELECT DISTINCT stato_cliente FROM clienti
WHERE stato_cliente IS NOT NULL AND stato_cliente != ''
ORDER BY stato_cliente

-- DOPO:
SELECT DISTINCT stato_crm FROM clienti
WHERE stato_crm IS NOT NULL AND stato_crm != ''
ORDER BY stato_crm
```

### Punto 2: Clausola WHERE filtro
```sql
-- PRIMA (caso NULL):
AND (c.stato_cliente IS NULL OR c.stato_cliente = '')
-- DOPO:
AND (c.stato_crm IS NULL OR c.stato_crm = '')

-- PRIMA (caso valore):
AND c.stato_cliente = ?
-- DOPO:
AND c.stato_crm = ?
```

---

## File NON modificati
- `templates/index/_filtri.html` - Usa variabili Python, non nomi colonna DB
- Parametro URL `stato_cliente` - Invariato (è il nome del parametro GET)
- Variabile Python `stati_cliente_usati` - Invariato (nome variabile)

---

## Note
- Righe 628-629 di web_server.py contengono ancora ordinamento su `c.stato_cliente` (da correggere in sessione futura se necessario)
- Il campo `stato_cliente` nel DB resta presente ma non viene più usato per il filtro griglia
