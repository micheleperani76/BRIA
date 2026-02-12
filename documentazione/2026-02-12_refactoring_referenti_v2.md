# Refactoring Riquadro Referenti v2.0

**Data**: 2026-02-12
**Sessione**: Correzione grafica scheda clienti - Referenti

---

## Modifiche Effettuate

### 1. Grafica Card Referenti
- **Altezza minima 4 righe**: se ci sono meno di 4 referenti, righe vuote completano la tabella
- **Espansione automatica**: dal 5&deg; referente la card cresce in verticale
- **Badge contatore**: numero referenti nel titolo card
- **Email troncate**: con tooltip per visualizzare il testo completo

### 2. Note in Icona Popover
- Colonna "Note" rimossa dalla tabella
- Icona `bi-sticky-fill` gialla appare solo se il referente ha note
- Click sull'icona apre un popover Bootstrap con il testo completo
- Popover si chiude cliccando fuori

### 3. Separazione Codice (Modularit&agrave; Estrema)
Tutto il codice referenti ora vive in file satellite dedicati:

| File | Contenuto |
|------|-----------|
| `_content.html` | Card/tabella referenti (v2.0) |
| `_styles.html` | CSS dedicato (righe vuote, popover, hover) |
| `_modal.html` | 3 modal: Nuovo, Modifica, Elimina |
| `_scripts.html` | JS: modificaReferente(), eliminaReferente(), init popover |

### 4. Pulizia dettaglio.html
Rimosso da dettaglio.html:
- Modal `#modalNuovoReferente` (ora in `_modal.html`)
- Modal `#modalModificaReferente` (ora in `_modal.html`)
- Modal `#modalEliminaReferente` (ora in `_modal.html`)
- Funzioni JS `modificaReferente()` e `eliminaReferente()` (ora in `_scripts.html`)

---

## File Coinvolti

| File | Azione |
|------|--------|
| `templates/dettaglio/referenti/_content.html` | SOSTITUITO (v2.0) |
| `templates/dettaglio/referenti/_styles.html` | NUOVO |
| `templates/dettaglio/referenti/_modal.html` | NUOVO |
| `templates/dettaglio/referenti/_scripts.html` | NUOVO |
| `templates/dettaglio.html` | MODIFICATO (rimossi modal + JS referenti) |

---

## Deploy

```bash
# Backup
cp ~/gestione_flotta/templates/dettaglio/referenti/_content.html ~/gestione_flotta/backup/templates__dettaglio__referenti___content.html.bak_$(date +%Y%m%d_%H%M%S)
cp ~/gestione_flotta/templates/dettaglio.html ~/gestione_flotta/backup/templates__dettaglio.html.bak_$(date +%Y%m%d_%H%M%S)

# Deploy 4 file satellite
mv ~/gestione_flotta/Scaricati/_content.html ~/gestione_flotta/templates/dettaglio/referenti/
mv ~/gestione_flotta/Scaricati/_styles.html ~/gestione_flotta/templates/dettaglio/referenti/
mv ~/gestione_flotta/Scaricati/_modal.html ~/gestione_flotta/templates/dettaglio/referenti/
mv ~/gestione_flotta/Scaricati/_scripts.html ~/gestione_flotta/templates/dettaglio/referenti/

# Riavvio
~/gestione_flotta/scripts/gestione_flotta.sh restart
```

---

## Pulizia dettaglio.html (FASE 2 - dopo verifica)

Dopo aver verificato che i satellite funzionano, rimuovere da dettaglio.html:
1. Blocco Modal Nuovo Referente (da `<!-- Modal Nuovo Referente -->` a chiusura `</div>`)
2. Blocco Modal Modifica Referente
3. Blocco Modal Elimina Referente
4. Funzioni JS `modificaReferente()` e `eliminaReferente()`

Usare sed chirurgici forniti nella sessione.
