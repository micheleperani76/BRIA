# Fix addEventListener null + Collegamenti
# Data: 2026-02-11
# Stato: TUTTO RISOLTO

## Fix 1: addEventListener null (dettaglio.html riga 1178)
- Aggiunto null-check su `selectAutoreNuovo`
- L'errore JS bloccava tutti gli script successivi, inclusa la ricerca collegamenti

## Fix 2: Nodo centro grafo sbagliato
- Risolto

## Fix 3: Livello 2 grafo
- Risolto

## File modificato
- `templates/dettaglio.html` (riga 1178)

## Sessioni precedenti (fix gia' applicati)
- COALESCE ricerca/card/grafo in routes_collegamenti_clienti.py
- _scripts.html riscritto con DOMContentLoaded + null-check
- _modal_espanso.html tab-grafo protetto
- Rimossi include duplicati da dettaglio.html
- Rating Creditsafe riquadro sistemato
