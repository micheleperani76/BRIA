# MIGRAZIONE ANAGRAFICA NOLEGGIATORI
## Documento di Riferimento

**Data**: 2026-02-12
**Versione**: 1.0
**Stato**: FASE 2 COMPLETATA - FASE 3 PENDENTE

---

## 1. OBIETTIVO

Centralizzare i noleggiatori in una tabella anagrafica unica (`noleggiatori`) con codice univoco,
eliminando la dipendenza da stringhe libere e dal file `noleggiatori.xlsx`.

---

## 2. SCHEMA TABELLA NOLEGGIATORI

```sql
CREATE TABLE noleggiatori (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codice TEXT NOT NULL UNIQUE,        -- Es: ARVAL, LEASEPLAN, ARVAL_TECH
    nome_display TEXT NOT NULL,          -- Es: Arval, LeasePlan, Arval Tech
    colore TEXT DEFAULT '#6c757d',       -- Colore hex per UI
    link_assistenza TEXT,                -- Link portale assistenza
    ordine INTEGER DEFAULT 0,            -- Ordine visualizzazione
    note TEXT,                           -- Note libere
    attivo INTEGER DEFAULT 1,            -- 0=disattivato
    origine TEXT DEFAULT 'PREDEFINITO',  -- PREDEFINITO/IMPORT/MANUALE
    data_inserimento TEXT DEFAULT (datetime('now', 'localtime'))
);
```

## 3. NOLEGGIATORI CENSITI

| ID | Codice | Nome Display | Origine |
|----|--------|-------------|---------|
| 1 | ALD | ALD Automotive | PREDEFINITO |
| 2 | ALPHABET | Alphabet | PREDEFINITO |
| 3 | ARVAL | Arval | PREDEFINITO |
| 4 | AYVENS | Ayvens | PREDEFINITO |
| 5 | DRIVALIA | Drivalia | PREDEFINITO |
| 6 | LEASEPLAN | LeasePlan | PREDEFINITO |
| 7 | LEASYS | Leasys | PREDEFINITO |
| 8 | RENT2GO | Rent2Go | PREDEFINITO |
| 9 | SIFA | Sifa | PREDEFINITO |
| 10 | ARVAL_TECH | Arval Tech | IMPORT |
| 11 | VOLKSWAGEN_LEASING | Volkswagen Leasing | IMPORT |

## 4. FK AGGIUNTE

- `veicoli.noleggiatore_id` → `noleggiatori.id` (1277 veicoli collegati, 0 orfani)
- `clienti_noleggiatori.noleggiatore_id` → `noleggiatori.id`
- Campo stringa `noleggiatore` TEXT mantenuto per retrocompatibilita'

## 5. MAPPA NORMALIZZAZIONE

Funzione `normalizza_nome()` in `routes_noleggiatori_cliente.py`:
- Case-insensitive: "Arval", "ARVAL", "arval" → codice ARVAL
- Accenti: "Sifa`" → SIFA
- Spazi: "Arval Tech" → ARVAL_TECH
- Fallback: nome sconosciuto → UPPER + replace spazi con _

## 6. TABELLA CLIENTI_NOLEGGIATORI (aggiornata)

```sql
-- Campi aggiunti rispetto alla versione originale:
ALTER TABLE clienti_noleggiatori ADD COLUMN noleggiatore_id INTEGER REFERENCES noleggiatori(id);
ALTER TABLE clienti_noleggiatori ADD COLUMN ordine INTEGER DEFAULT 0;
```

## 7. FILE AGGIORNATI (Fase 2)

| File | Stato | Note |
|------|-------|------|
| `app/database.py` | ✅ AGGIORNATO | CREATE TABLE noleggiatori + indici |
| `app/routes_noleggiatori_cliente.py` | ✅ RISCRITTO v2.0 | Tutte query con FK + JOIN |
| `app/web_server.py` | ✅ PATCHATO | JOIN noleggiatori in query veicoli |
| `app/routes_installato.py` | ✅ PATCHATO | JOIN noleggiatori nei filtri |
| `templates/componenti/noleggiatori/_riquadro.html` | ✅ PATCHATO | Select con id, frecce riordino |

## 8. FILE DA AGGIORNARE (Fase 3 - pendente)

| File | Priorita' | Cosa fare |
|------|-----------|-----------|
| `app/routes_revisioni.py` | BASSA | v.noleggiatore in SELECT → JOIN |
| `app/routes_trattative.py` | MEDIA | campo noleggiatore in trattative |
| `app/motore_trattative.py` | BASSA | logica trattative |
| `app/routes_flotta_commerciali.py` | MEDIA | filtri per noleggiatore |
| `app/export_excel.py` | BASSA | colonna export |
| `app/routes_export.py` | BASSA | export con noleggiatore |
| `app/routes_documenti_strutturati.py` | BASSA | riferimenti noleggiatore |
| `impostazioni/noleggiatori.xlsx` | -- | DA ELIMINARE (sostituito da tabella DB) |

**Nota**: tutti i file pendenti continuano a funzionare perche' il campo stringa
`noleggiatore` TEXT e' ancora presente sia in `veicoli` che in `clienti_noleggiatori`.

## 9. API NOLEGGIATORI (v2.0)

```
GET    /api/cliente/<id>/noleggiatori           Lista (manuali + da veicoli)
POST   /api/cliente/<id>/noleggiatori           Aggiungi (accetta noleggiatore_id o nome)
PUT    /api/cliente/<id>/noleggiatori/<nid>      Modifica stato/note
DELETE /api/cliente/<id>/noleggiatori/<nid>      Elimina
POST   /api/cliente/<id>/noleggiatori/riordina  Sposta su/giu (materializza auto)
PUT    /api/cliente/<id>/crm                     Aggiorna stato CRM
GET    /api/noleggiatori/lista                   Lista anagrafica completa
```

## 10. FUNZIONALITA' RIORDINAMENTO

- Bottone riordino nell'header card (icona frecce)
- Attiva/disattiva modalita' riordino
- Frecce su/giu inline accanto ai pulsanti azione
- Al primo riordino: materializza automaticamente noleggiatori da veicoli
- Ordine salvato per-cliente nel campo `ordine` di `clienti_noleggiatori`
- Max 4 righe visibili, scroll per il resto (max-height: 130px)

## 11. COMPORTAMENTO IMPORT/NUOVI NOLEGGIATORI

- **Nuovo da CRM/import**: funzione `trova_o_crea_noleggiatore()` cerca per codice,
  se non trova crea automaticamente con origine=IMPORT
- **Nuovo manuale**: dropdown legge da tabella `noleggiatori` (non piu' xlsx)
- **Conflitto manuale/import**: stessa FK, nessun conflitto
- **Rinomina**: aggiornare solo `nome_display` in tabella `noleggiatori`
