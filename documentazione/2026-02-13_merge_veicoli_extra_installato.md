# Merge Veicoli Extra -> Installato

**Data**: 2026-02-13
**Sessione**: Meccanismo merge duplicati veicoli

---

## PROBLEMA

Quando un veicolo Extra non ha targa, l'import CRM non riesce a riconciliarlo
con l'Installato e crea un doppione. Il sistema non aveva un meccanismo per
gestire i duplicati al momento dell'inserimento targa.

## SOLUZIONE

Meccanismo automatico di merge quando si salva una targa su un veicolo
e quella targa esiste gia' nel database.

### Scenari gestiti

| # | Situazione | Azione |
|---|-----------|--------|
| 1 | Targa esiste come Installato (stesso/altro cliente) | Extra assorbito dall'Installato (CRM fa fede) |
| 2 | Targa esiste come Extra (stesso cliente) | Unifica i due Extra |
| 3 | Targa non esiste | Salva normalmente (come prima) |

### Logica merge

1. **Copia campi "nostri"** dall'assorbito al sopravvissuto (solo se NULL):
   - driver, km_attuali, data_rilevazione_km, km_franchigia
   - data_immatricolazione, revisione_gestita, data_revisione, note_revisione
   - costo_km_extra_1, costo_km_extra_2

2. **Sposta tabelle satellite**:
   - `note_veicoli` -> UPDATE veicolo_id
   - `storico_km` -> UPDATE veicolo_id

3. **Soft-delete assorbito**:
   - `merged_in_veicolo_id` = ID sopravvissuto
   - `data_merge` = timestamp

4. **Log** in `storico_modifiche`

### Regola: CRM fa sempre fede
Il veicolo Installato (da CRM) non viene mai modificato nei campi CRM.
Solo i campi "nostri" vengono integrati se mancanti.

---

## MIGRAZIONE DATABASE

Script: `scripts/migrazione_merge_veicoli.py`

2 colonne aggiunte a `veicoli`:
- `merged_in_veicolo_id` INTEGER (FK al veicolo sopravvissuto)
- `data_merge` TEXT (timestamp)

1 indice: `idx_veicoli_merged`

---

## FILE COINVOLTI

| File | Azione |
|------|--------|
| `scripts/migrazione_merge_veicoli.py` | NUOVO - Migrazione DB |
| `app/web_server.py` | MODIFICATO - Route salva_targa + nuova route merge |
| `templates/veicolo.html` | MODIFICATO - JS salvaTarga + modal merge |

---

## DEPLOY

### Step 1: Migrazione DB
```bash
cd ~/gestione_flotta
python3 scripts/migrazione_merge_veicoli.py --dry-run
python3 scripts/migrazione_merge_veicoli.py
```

### Step 2: Backup e deploy file
```bash
# Migrazione
cp ~/gestione_flotta/Scaricati/migrazione_merge_veicoli.py ~/gestione_flotta/scripts/

# web_server.py - applicare le 2 patch con sed/str_replace (vedi PATCH_web_server_merge.py)
cp ~/gestione_flotta/app/web_server.py ~/gestione_flotta/backup/app__web_server.py.bak_$(date +%Y%m%d_%H%M%S)

# veicolo.html - applicare le 2 patch (vedi PATCH_veicolo_html_merge.txt)
cp ~/gestione_flotta/templates/veicolo.html ~/gestione_flotta/backup/templates__veicolo.html.bak_$(date +%Y%m%d_%H%M%S)
```

### Step 3: Riavvio
```bash
~/gestione_flotta/scripts/gestione_flotta.sh restart
```

---

## NOTE IMPORTANTI

- I veicoli con `merged_in_veicolo_id IS NOT NULL` sono esclusi da tutte le query
- Al prossimo import CRM i campi CRM vengono riscritti normalmente sull'Installato
- Il meccanismo funziona anche per merge tra due Extra
- L'operazione e' irreversibile (soft-delete, ma non previsto undo)
- Tutti i merge sono tracciati in `storico_modifiche`

## QUERY UTILI POST-DEPLOY

```sql
-- Veicoli mergiati
SELECT id, targa, tipo_veicolo, merged_in_veicolo_id, data_merge 
FROM veicoli WHERE merged_in_veicolo_id IS NOT NULL;

-- Verifica nessun veicolo attivo senza filtro merge
SELECT COUNT(*) FROM veicoli WHERE merged_in_veicolo_id IS NULL;
```
