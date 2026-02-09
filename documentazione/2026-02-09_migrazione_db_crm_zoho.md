# 2026-02-09 - Migrazione DB per Import CRM Zoho

## Cosa fa lo script

Script `scripts/migrazione_crm_zoho.py` - Prepara il database per l'import dei dati CRM Zoho.

### Operazioni eseguite

| Step | Operazione | Dettaglio |
|------|-----------|-----------|
| 1 | ALTER TABLE clienti | 13 nuovi campi CRM |
| 2 | ALTER TABLE veicoli | 4 nuovi campi CRM |
| 3 | CREATE TABLE satellite | clienti_consensi, clienti_dati_finanziari, clienti_creditsafe_alert, clienti_crm_metadata |
| 4 | CREATE TABLE storico | storico_installato (dismessi con retention 5 anni) |
| 5 | CREATE INDEX | 11 indici di performance |

### Nuovi campi clienti (13)

crm_id, stato_crm, origine_contatto, azienda_tipo_crm, profilazione_flotta,
commerciale_consecution, pec, telefono, totale_flotta_crm, flotta_cns_crm,
noleggiatore_principale_1, noleggiatore_principale_2, note_concorrenza

### Nuovi campi veicoli (4)

co2, stato_targa, crm_id, crm_azienda_id

### Nuove tabelle (5)

- **clienti_consensi**: GDPR con storico (Newsletter, Comunicazioni, ecc.)
- **clienti_dati_finanziari**: serie storica per anno (fatturato, EBITDA, ecc.)
- **clienti_creditsafe_alert**: flag rischio (Protesti, Pregiudizievoli, ecc.)
- **clienti_crm_metadata**: dati tecnici Zoho (record_id, creato_da, ecc.)
- **storico_installato**: veicoli dismessi con retention 5 anni

## Come usare

```bash
# 1. Dry-run (verifica senza modificare nulla)
cd ~/gestione_flotta
python3 scripts/migrazione_crm_zoho.py --dry-run

# 2. Esecuzione reale (crea backup automatico)
python3 scripts/migrazione_crm_zoho.py
```

## Sicurezza

- Lo script crea un backup automatico del DB prima di operare
- Ogni ALTER/CREATE verifica se la colonna/tabella esiste gia' (idempotente)
- Supporta riesecuzioni multiple senza errori
- In caso di errore: rollback automatico

## Riferimento

Piano completo: `PIANO_IMPORT_CRM_ZOHO.md` sezioni 7, 8, 11
