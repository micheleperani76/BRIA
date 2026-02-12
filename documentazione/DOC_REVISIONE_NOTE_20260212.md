# Revisione Sistema Note v3.0
**Data:** 2026-02-12
**Sessione:** Debug e riscrittura motore note cliente

---

## Problemi identificati e risolti

### CRITICI
| # | Problema | File | Fix |
|---|----------|------|-----|
| 1 | Route `note_fullscreen` senza `@login_required` - causava 302 sulle API JS con sessione scaduta, errore "Errore caricamento cestino" | `web_server.py` | Aggiunto decoratore |
| 2 | Cestino vuoto causava `alert()` bloccante e freeze interfaccia | `note_fullscreen.html` | Riscrittura completa con placeholder grafici |

### MEDI
| # | Problema | File | Fix |
|---|----------|------|-----|
| 3 | `cerca_note_cliente` senza `@login_required` | `web_server.py` | Aggiunto decoratore |
| 4 | `elimina_allegato_cliente` senza `@login_required` | `web_server.py` | Aggiunto decoratore |
| 5 | Ricerca note non trovava note con `eliminato IS NULL` (vecchie) | `web_server.py` | `AND (eliminato = 0 OR eliminato IS NULL)` |

### BASSI (backlog)
| # | Problema | Stato |
|---|----------|-------|
| 6 | `eliminato_da` salva stringa invece di ID intero | Da fare - richiede migrazione DB |
| 7 | `routes_note_fullscreen.py` codice morto con nomi tabella sbagliati | Da eliminare |

---

## Modifiche architetturali

### note_fullscreen.html v3.0 (riscrittura completa)
**Architettura ispirata a Evernote, adattata a gestione_flotta:**
- Ogni scheda cliente = 1 taccuino
- Sidebar sinistra: lista note / toggle cestino
- Editor destro: titolo + testo + allegati
- Top bar: ricerca full-text centrata + nome cliente + chiudi

**Funzionalit&agrave;:**
- CRUD note con autosave (2s inattivit&agrave; + Ctrl+S)
- Indicatore salvataggio tempo reale (Salvato/Non salvato/Salvataggio.../Errore)
- Cestino come toggle sidebar - icona rossa quando attivo
- Note cestinate in sola lettura con barra gialla + azioni ripristina/elimina
- Toast notifiche al posto di alert() bloccanti
- Placeholder grafici per tutti gli stati vuoti
- Pin/fissa note con riordino automatico
- Upload allegati con contatore in sidebar
- Ricerca full-text con debounce 300ms

**API utilizzate (Blueprint /api/note-clienti):**
- `/<cid>/lista` - Note attive
- `/<cid>/crea` - Crea nota
- `/<cid>/<nid>/modifica` - Modifica nota
- `/<cid>/<nid>/elimina` - Soft delete
- `/<cid>/<nid>/fissa` - Toggle pin
- `/<cid>/cestino` - Note eliminate
- `/<cid>/<nid>/ripristina` - Ripristina
- `/<cid>/<nid>/elimina-definitivo` - Elimina per sempre
- `/<cid>/<nid>/allegati` - Upload allegati
- `/allegato/<aid>/elimina` - Elimina allegato
- `/allegato/<aid>/scarica` - Download allegato
- `/cliente/<cid>/note/cerca?q=` - Ricerca full-text

### dettaglio.html - FAB fluttuante
- Rimosso tasto Note dalla barra header
- Aggiunto FAB (Floating Action Button) rotondo giallo in basso a destra
- FAB si nasconde quando pannello note &egrave; aperto
- FAB riappare quando pannello note si chiude
- Fullscreen si apre in nuovo tab (`target="_blank"`)
- Chiusura fullscreen = `window.close()` (torna al tab scheda cliente)
- Script inline anti-flash per riapertura pannello senza reload visibile

---

## File modificati
| File | Tipo modifica |
|------|---------------|
| `app/web_server.py` | Fix chirurgici (4 sed) |
| `templates/note_fullscreen.html` | Riscrittura completa v3.0 |
| `templates/dettaglio.html` | Fix chirurgici (FAB, target_blank, script inline) |

## Backup
- `backup/app__web_server.py.bak_20260212_*`
- `backup/templates__note_fullscreen.html.bak_20260212_*`
- `backup/templates__dettaglio.html.bak_20260212_*`

---

## DB - Nessuna modifica
- Tabella `note_clienti`: invariata
- Tabella `allegati_note`: invariata (nome corretto, FK `nota_cliente_id`)
- File morto `routes_note_fullscreen.py` usava nomi sbagliati (`allegati_note_clienti`, `nota_id`) - da eliminare

## Prossimi step
1. Eliminare `app/routes_note_fullscreen.py` (codice morto)
2. Migrare `eliminato_da` TEXT &rarr; `eliminato_da_id` INTEGER
3. Valutare WAL mode su SQLite per concorrenza
4. Tool fase 2: export nota TXT/PDF, ordinamento per data/titolo/autore
