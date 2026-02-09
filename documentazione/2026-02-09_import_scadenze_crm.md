# 2026-02-09 - Import Scadenze CRM Zoho (Veicoli INSTALLATO)

## Cosa fa lo script

Script `scripts/import_scadenze_crm.py` - Importa veicoli INSTALLATO dal CSV Scadenze Zoho CRM.

### Categorizzazione automatica

| Stato Targa | Contratto | Categoria | Destinazione |
|-------------|-----------|-----------|-------------|
| Circolante | In corso | ATTIVO | tabella `veicoli` |
| Circolante | Scaduto | IN_GESTIONE | tabella `veicoli` |
| Archiviata | Scaduto | DISMESSO | tabella `storico_installato` |
| Archiviata | In corso | ANOMALO | tabella `storico_installato` |

### Logica di import

1. Per ogni record, normalizza targa e P.IVA
2. Categorizza in base a Stato Targa + Data fine
3. Cerca cliente nel DB per P.IVA (deve esistere dopo import Accounts)
4. **Se Circolante**: cerca veicolo per targa, crea o aggiorna con tipo_veicolo = 'Installato'
5. **Se Archiviata**: inserisce in storico_installato con retention 5 anni
6. Se veicolo era EXTRA e ora e' nel CRM come Circolante: voltura automatica a INSTALLATO

### Regole di priorita'

| Dato | Fonte prioritaria | Note |
|------|-------------------|------|
| noleggiatore, canone, durata, km, date | CRM | Aggiornati da import |
| driver, note, km_attuali | Nostro | Mai sovrascritti |
| tipo_veicolo | CRM/Import | Diventa 'Installato' |
| commerciale_id | Nostro | Mai toccato |

## Come usare

```bash
cd ~/gestione_flotta

# Prerequisito: import Accounts deve essere gia' stato eseguito

# 1. Copiare il CSV
cp ~/Scaricati/Scadenze_2026_02_09.csv import_dati/

# 2. Dry-run
python3 scripts/import_scadenze_crm.py import_dati/Scadenze_2026_02_09.csv --dry-run

# 3. Import reale (backup automatico)
python3 scripts/import_scadenze_crm.py import_dati/Scadenze_2026_02_09.csv
```

## Riferimento

Piano completo: `PIANO_IMPORT_CRM_ZOHO.md` sezione 5
