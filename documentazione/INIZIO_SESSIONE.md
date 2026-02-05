# INIZIO SESSIONE - GESTIONE FLOTTA

## 1. RESET MEMORIA
I file allegati al progetto sono la UNICA fonte di verità. Ignora versioni precedenti, cache o supposizioni.

## 2. LETTURA OBBLIGATORIA
Prima di qualsiasi azione:
- Leggere `REGOLE_CLAUDE.md` (regole operative)
- Leggere `tree.txt` (struttura cartelle)
- Confermare lettura con riepilogo regole principali

## 3. MODIFICHE CODICE
- **Sempre chirurgiche**: sed, str_replace, patch mirate
- **Mai riscritture intere** se basta modificare poche righe
- **Mai modificare** grafica o codice non richiesto
- **Verificare** che il codice buono non sia corrotto prima del rilascio

## 4. ENCODING (CRITICO)
Il trasferimento corrompe UTF-8. Usare SOLO:
- `&euro;` (no €)
- `&agrave; &egrave; &igrave; &ograve; &ugrave;` (no à è ì ò ù)
- `<i class="bi bi-*">` (no emoji)

## 5. ARCHITETTURA
- **Modularità estrema**: ogni funzione = cartella dedicata
- **Principio DRY**: mai duplicare codice, riusare l'esistente
- **File satellite**: HTML + CSS + JS nella stessa cartella

## 6. DEPLOY FILE
Cartelle:
- **Download**: `~/gestione_flotta/Scaricati/`
- **Backup**: `~/gestione_flotta/backup/`

Formato backup: `[percorso]__[file].bak_YYYYMMDD_HHMMSS`

Comandi da fornire sempre:
```bash
# Backup
cp ~/gestione_flotta/[percorso]/[file] ~/gestione_flotta/backup/[percorso]__[file].bak_$(date +%Y%m%d_%H%M%S)

# Deploy
mv ~/gestione_flotta/Scaricati/[file] ~/gestione_flotta/[percorso]/
```

## 7. DOCUMENTAZIONE
Ad ogni step completato: creare file `.md` in `documentazione/`

## 8. RIAVVIO SERVER
```bash
~/gestione_flotta/scripts/gestione_flotta.sh restart
```

---

**STATO**: Progetto in beta test. Massima cautela. Zero regressioni.
