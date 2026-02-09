# 2026-02-09 - Import Accounts CRM Zoho

## Cosa fa lo script

Script `scripts/import_accounts_crm.py` - Importa anagrafica clienti dal CSV Zoho CRM.

### Logica di import

1. Legge il CSV Accounts esportato da Zoho
2. Per ogni record, normalizza P.IVA (zero-pad a 11 cifre + prefisso IT)
3. Cerca cliente nel DB per P.IVA, fallback per Codice Fiscale
4. **Se trovato**: aggiorna SOLO campi CRM, NON tocca nome/sede legale/dati Creditsafe
5. **Se non trovato**: crea nuovo cliente con commerciale_id = Paolo Ciotti
6. Popola tabelle satellite: consensi, dati finanziari, alert, metadata CRM
7. Gestisce sedi: operativa + fatturazione (crea o aggiorna)

### Regole di priorita'

| Dato | Fonte prioritaria | Note |
|------|-------------------|------|
| nome_cliente | Creditsafe | Mai sovrascritto da CRM |
| sede legale | Creditsafe | Mai sovrascritto da CRM |
| pec, telefono | Creditsafe | CRM aggiorna solo se vuoti nel DB |
| stato_crm, profilazione, ecc. | CRM | Sempre aggiornati da CRM |
| commerciale_id | Nostro | Mai toccato dall'import |
| note | Nostro | Mai toccato dall'import |

### Normalizzazione P.IVA

Il CRM esporta P.IVA senza prefisso IT e senza zeri iniziali:
- CSV: `672420171` (9 cifre) → DB: `IT00672420171`
- CSV: `2006580985` (10 cifre) → DB: `IT02006580985`

## Come usare

```bash
cd ~/gestione_flotta

# 1. Copiare il CSV nella cartella import_dati
cp ~/Scaricati/Accounts_2026_02_09.csv import_dati/

# 2. Dry-run
python3 scripts/import_accounts_crm.py import_dati/Accounts_2026_02_09.csv --dry-run

# 3. Import reale (crea backup automatico)
python3 scripts/import_accounts_crm.py import_dati/Accounts_2026_02_09.csv
```

## Output

- Log dettagliato a schermo con elenco clienti aggiornati/creati/errori
- File log in `logs/import_accounts_*.log`
- Backup automatico del DB prima dell'import reale

## Riferimento

Piano completo: `PIANO_IMPORT_CRM_ZOHO.md` sezione 4
