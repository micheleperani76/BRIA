# Migrazione VIEW veicoli_attivi
## Sostituzione FROM veicoli -> FROM veicoli_attivi in tutto il progetto

**Data**: 2026-02-14
**Stato**: COMPLETATO
**Priorit&agrave;**: ALTA - Fix bug veicoli merged visibili

---

## PROBLEMA

Dopo l'implementazione del merge veicoli Extra -> Installato (2026-02-13),
i veicoli con `merged_in_veicolo_id IS NOT NULL` apparivano ancora in molte
pagine del gestionale (conteggi, liste, statistiche).

Fix parziale della sessione precedente: solo 3 query patchate manualmente
con `AND merged_in_veicolo_id IS NULL`.

## SOLUZIONE

Creata VIEW `veicoli_attivi` che filtra automaticamente i veicoli merged:

```sql
CREATE VIEW IF NOT EXISTS veicoli_attivi AS 
SELECT * FROM veicoli WHERE merged_in_veicolo_id IS NULL;
```

Sostituito `FROM veicoli` con `FROM veicoli_attivi` in tutte le SELECT.
INSERT/UPDATE/DELETE restano sulla tabella `veicoli` reale.

## FILE MODIFICATI

### Step 1: VIEW nel database
- Script: `scripts/migrazione_view_veicoli_attivi.py`
- Backup DB: `backup/db__gestionale.db.bak_20260213_175109`

### Step 2: Sostituzione query (11 file)

| File | Occorrenze | Note |
|------|-----------|------|
| `app/web_server.py` | 27 | Con 6 eccezioni (vedi sotto) |
| `app/routes_installato.py` | 8 | Tutte sostituite |
| `app/routes_flotta_commerciali.py` | 9 | Tutte sostituite |
| `app/routes_revisioni.py` | 5 | Tutte sostituite |
| `app/routes_noleggiatori_cliente.py` | 4 | Tutte sostituite |
| `app/database.py` | 4 | Tutte sostituite |
| `app/motore_top_prospect.py` | 4 | Tutte sostituite |
| `app/routes_top_prospect.py` | 3 | Tutte sostituite |
| `app/export_excel.py` | 2 | Tutte sostituite |
| `app/routes_admin_utenti.py` | 1 | Tutte sostituite |
| `app/connettori_notifiche/revisione.py` | 1 | Tutte sostituite |

### Eccezioni (restano su FROM veicoli)

| Riga | Query | Motivo |
|------|-------|--------|
| 2052 | `SELECT * FROM veicoli WHERE id = ?` | Scheda singolo veicolo (anche merged per audit) |
| 2155 | `SELECT id FROM veicoli WHERE id = ?` | Verifica esistenza per note |
| 2337 | `SELECT id FROM veicoli WHERE id = ?` | Verifica esistenza per km |
| 2480 | `SELECT * FROM veicoli WHERE id = ?` | Merge route (sopravvive_id) |
| 2482 | `SELECT * FROM veicoli WHERE id = ?` | Merge route (assorbito_id) |
| 2600 | `SELECT id FROM veicoli WHERE UPPER(targa)` | Ricerca targa (deve trovare anche merged) |

### File NON toccati (corretto)
- `scripts/import_scadenze_crm.py` - Opera su tabella reale
- `scripts/migrazione_*.py` - Scripts di migrazione
- INSERT/UPDATE/DELETE in tutti i file

## BACKUP

Tutti i backup in `~/gestione_flotta/backup/` con timestamp `20260214_114046`:
- `app__web_server.py.bak_20260214_114046`
- `app__routes_installato.py.bak_20260214_114046`
- `app__routes_noleggiatori_cliente.py.bak_20260214_114046`
- `app__routes_revisioni.py.bak_20260214_114046`
- `app__routes_top_prospect.py.bak_20260214_114046`
- `app__routes_admin_utenti.py.bak_20260214_114046`
- `app__routes_flotta_commerciali.py.bak_20260214_114046`
- `app__database.py.bak_20260214_114046`
- `app__export_excel.py.bak_20260214_114046`
- `app__motore_top_prospect.py.bak_20260214_114046`
- `app__connettori_notifiche__revisione.py.bak_20260214_114046`

## VERIFICA

```sql
-- Conta veicoli totali vs attivi
SELECT 'totali' as tipo, COUNT(*) FROM veicoli
UNION ALL
SELECT 'attivi', COUNT(*) FROM veicoli_attivi
UNION ALL
SELECT 'merged', COUNT(*) FROM veicoli WHERE merged_in_veicolo_id IS NOT NULL;
-- Risultato: totali=1277, attivi=1276, merged=1
```

## REGOLA PER SVILUPPO FUTURO

Per ogni nuova query su veicoli:
- **SELECT**: usare `FROM veicoli_attivi` (esclude merged automaticamente)
- **INSERT/UPDATE/DELETE**: usare `FROM veicoli` (tabella reale)
- **Scheda singola per ID**: usare `FROM veicoli` (deve vedere anche merged per audit)
- **Ricerca targa**: usare `FROM veicoli` (deve trovare anche merged per evitare duplicati)
