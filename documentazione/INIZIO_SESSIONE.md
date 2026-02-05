# INIZIO SESSIONE - GESTIONE FLOTTA

## 1. RESET MEMORIA
I file allegati al progetto sono la UNICA fonte di verita'. Ignora versioni precedenti, cache o supposizioni.

## 2. FONTE DEI FILE
I file del progetto sono sincronizzati da GitHub:
- **Repository**: https://github.com/micheleperani76/BRIA
- **Sync**: l'utente clicca "Sync" nel Project Knowledge per aggiornare
- Se i file sembrano datati, chiedere: "Hai sincronizzato il repo GitHub?"

## 3. LETTURA OBBLIGATORIA
Prima di qualsiasi azione:
- Leggere `REGOLE_CLAUDE.md` (regole operative)
- Leggere `tree.txt` (struttura cartelle)
- Confermare lettura con riepilogo regole principali

## 4. MODIFICHE CODICE
- **Sempre chirurgiche**: sed, str_replace, patch mirate
- **Mai riscritture intere** se basta modificare poche righe
- **Mai modificare** grafica o codice non richiesto
- **Verificare** che il codice buono non sia corrotto prima del rilascio

## 5. ENCODING (CRITICO)
Il trasferimento corrompe UTF-8. Usare SOLO:
- `&euro;` (no €)
- `&agrave; &egrave; &igrave; &ograve; &ugrave;` (no à è ì ò ù)
- `<i class="bi bi-*">` (no emoji)

## 6. ARCHITETTURA
- **Modularita' estrema**: ogni funzione = cartella dedicata
- **Principio DRY**: mai duplicare codice, riusare l'esistente
- **File satellite**: HTML + CSS + JS nella stessa cartella

## 7. DEPLOY FILE
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

## 8. DOCUMENTAZIONE
Ad ogni step completato: creare file `.md` in `documentazione/`

## 9. RIAVVIO SERVER
```bash
~/gestione_flotta/scripts/gestione_flotta.sh restart
```

## 10. FINE SESSIONE - SYNC GITHUB
A fine sessione l'utente sincronizza il codice con:
```bash
# Metodo rapido (solo git)
~/gestione_flotta/raccolta_file_ia.sh --solo-git

# Metodo completo (raccolta + git + backup)
~/gestione_flotta/raccolta_file_ia.sh
```

---

**STATO**: Progetto in beta test. Massima cautela. Zero regressioni.
