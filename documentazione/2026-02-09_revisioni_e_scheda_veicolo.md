# Sessione 09 Febbraio 2026 - Revisioni Veicoli e Scheda Veicolo

**Data**: 09 Febbraio 2026
**Tipo**: Nuove funzionalita' + Miglioramenti

---

## PANORAMICA

Implementato sistema completo di monitoraggio revisioni veicoli con pagina
dedicata, notifiche raggruppate e controllo permessi. Migliorata la scheda
veicolo con badge riposizionato, URL per targa e titolo corretto.

---

## 1. SISTEMA REVISIONI VEICOLI

### Pagina dedicata `/revisioni`
- Voce separata nel sidebar (sezione Flotta)
- Counter cards: totale, da gestire, scaduti, gestiti
- Filtri rapidi per stato
- Tabella completa con colonne: Targa, Veicolo, Cliente, Commerciale,
  Driver, Scadenza, Giorni, Stato, Azioni
- Colonne future riservate (trasparenti)
- Ordinamento per urgenza (scadenza piu' vicina prima)
- Targa mancante evidenziata in viola con scritta "MANCANTE"

### Dati contatto nella griglia
- Telefono azienda sotto il nome cliente
- Referente principale (flag `principale=1`) con telefono
- Telefono driver sotto il nome driver
- Nome commerciale assegnato

### Visibilita' dati
- Admin: vede tutto
- Operatore con permesso: vede tutto (senza veicoli propri)
- Commerciale: vede solo gerarchia (propri + subordinati)

### Azioni inline
- **Revisione effettuata**: con data e note opzionali
- **Presa visione**: dismissione notifiche con motivo opzionale
- **Riapri**: reset per ri-gestire la scadenza

### Logica calcolo scadenze
- Prima revisione: 5 anni dalla data immatricolazione
- Successive: ogni 2 anni
- Esempio: immatricolata 15/03/2020 -> 15/03/2025, 15/03/2027, ...

### Notifiche raggruppate
- UNA sola notifica per commerciale (non una per veicolo)
- Titolo: "Revisioni: N veicoli da gestire"
- Link diretto a pagina `/revisioni`
- Dedup settimanale (una notifica a settimana)
- Solo giorni lavorativi (lun-ven)
- Livello basato sull'urgenza peggiore nel gruppo

### Permesso `revisioni_view`
- Aggiunto al catalogo permessi (categoria: flotta, ordine: 145)
- Protegge route index e gestione
- Protegge voce sidebar
- Assegnato a utenti id 1 (p.ciotti) e 2 (m.perani)

---

## 2. MIGRAZIONE DATABASE

Tabella `veicoli` - 4 nuove colonne:

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| data_immatricolazione | TEXT | Data prima immatricolazione (YYYY-MM-DD) |
| revisione_gestita | TEXT | Data scadenza gestita (match = stop notifiche) |
| data_revisione | TEXT | Data effettiva revisione (opzionale) |
| note_revisione | TEXT | Note libere (opzionale) |

Script: `scripts/migrazione_revisione.py`

---

## 3. SCHEDA VEICOLO - MIGLIORAMENTI

### Badge tipo veicolo spostato
- Da: colonna destra (con bottoni noleggiatore)
- A: inline accanto al nome veicolo nella riga titolo

### Titolo veicolo corretto
- Prima: `GM802NS - KIA 1.6 CRDI MHEV BUSINESS 2WD DCT`
- Dopo: `GM802NS - KIA Sportage` (nome modello estratto dal campo `tipo`)
- Specifiche (modello completo) in riga sotto in grigio piccolo

### URL doppia per targa
- `/veicolo/GM802NS` (accesso per targa)
- `/veicolo/115` (accesso per id, invariato)
- Veicoli senza targa continuano a funzionare per id

### Campo data immatricolazione
- Aggiunto in fondo alla card "Dati Contratto"
- Pulsante Inserisci/Modifica con modal dedicato

### Card revisione nella scheda veicolo
- Posizione: colonna destra, sotto Grafico Km
- File satellite: `templates/veicolo/_revisione.html`
- Mostra prossima scadenza, stato, azioni (fatta/visione/reset)
- Se manca data immatricolazione: invito a inserirla

---

## FILE NUOVI

| File | Descrizione |
|------|-------------|
| `scripts/migrazione_revisione.py` | Migrazione DB (4 colonne) |
| `app/connettori_notifiche/revisione.py` | Connettore notifiche + calcolo revisione |
| `app/routes_revisioni.py` | Blueprint pagina revisioni con permessi |
| `templates/revisioni/index.html` | Template pagina revisioni |
| `templates/veicolo/_revisione.html` | Card revisione satellite |

## FILE MODIFICATI

| File | Modifica |
|------|----------|
| `templates/veicolo.html` | Badge spostato, titolo corretto, campo immatricolazione, include satellite |
| `app/web_server.py` | Import/registra blueprint, estrazione nome_modello, route targa, route immatricolazione/revisione |
| `templates/base.html` | Voce sidebar "Revisioni" con permesso |

## DATABASE

| Tabella | Modifica |
|---------|----------|
| `veicoli` | +4 colonne (immatricolazione, revisione) |
| `permessi_catalogo` | +1 riga (revisioni_view) |
| `utenti_permessi` | +2 righe (permesso assegnato a utenti 1 e 2) |

---

## NOTE TECNICHE

- Connettore revisione usa categoria `SCADENZA_CONTRATTO` (regole routing esistenti)
- `calcola_prossima_revisione()` centralizzata in `revisione.py` (DRY)
- Ciclo automatico: nuova scadenza ogni 2 anni -> reset notifiche
- Link cliente usa `/cerca/{{ v.p_iva }}` (non `/clienti/id`)
- Il cron notturno dovra' chiamare `check_revisioni(conn)` per notifiche automatiche
