# LOGICA BROKER - NOLEGGIATORE - VEICOLI
## Documento Architetturale Fondamentale

**Data**: 2026-01-26
**Versione**: 1.0
**Stato**: DOCUMENTO UFFICIALE
**Priorit&agrave;**: CRITICA - Riferimento per tutte le logiche del programma

---

## 1. PREMESSA

Questo documento definisce la logica fondamentale che regola i rapporti tra:
- **Clienti** (aziende)
- **Broker** (intermediari come BR Car Service)
- **Noleggiatori** (Arval, Leasys, Ayvens, etc.)
- **Veicoli** (il parco auto)

Questa logica &egrave; alla base di tutte le funzionalit&agrave; del gestionale e deve essere rispettata in ogni sviluppo futuro.

---

## 2. REGOLA FONDAMENTALE

> ### UN NOLEGGIATORE = UN BROKER (per cliente)
>
> Per ogni cliente, ogni noleggiatore &egrave; gestito da UN SOLO broker.
> Non esistono broker multipli per lo stesso noleggiatore sullo stesso cliente.

### Esempio:
| Cliente | Noleggiatore | Broker |
|---------|--------------|--------|
| ATIB SRL | ARVAL | BR Car Service |
| ATIB SRL | AYVENS | Altro broker |
| ATIB SRL | LEASYS | Altro broker |

ATIB pu&ograve; avere contratti con 3 noleggiatori diversi, ma per ognuno c'&egrave; un solo broker che gestisce.

---

## 3. TIPOLOGIE DI VEICOLI

### 3.1 Veicoli INSTALLATO
- **Definizione**: Veicoli gestiti da BR Car Service
- **Origine dati**: Import dal CRM (campo "Flotta con CNS")
- **Caratteristiche**:
  - BR Car Service &egrave; il broker di riferimento
  - Generano statistiche operative
  - Sono oggetto di fatturazione
  - Sono sotto il controllo diretto di BR
- **Stato attuale DB**: Nessuno (arriveranno con import CRM)

### 3.2 Veicoli EXTRA
- **Definizione**: Veicoli NON gestiti da BR Car Service
- **Origine dati**: Caricamento manuale, fonti esterne
- **Caratteristiche**:
  - Gestiti da altro broker
  - Monitorati per intelligence commerciale
  - NON generano statistiche operative BR
  - NON sono oggetto di fatturazione BR
- **Stato attuale DB**: TUTTI i veicoli presenti

### 3.3 Tabella di sintesi

| Campo DB | Valore | Broker | Statistiche BR | Fatturazione BR |
|----------|--------|--------|----------------|-----------------|
| tipo_veicolo | INSTALLATO | BR Car Service | S&Igrave; | S&Igrave; |
| tipo_veicolo | EXTRA | Altro | NO | NO |

---

## 4. STATO CLIENTE

### 4.1 Definizione
Lo **Stato Cliente** indica la relazione commerciale tra il cliente e BR Car Service, indipendentemente dai singoli veicoli.

### 4.2 Valori (da CRM)
| Stato | Significato | Ha contratti attivi con BR? |
|-------|-------------|----------------------------|
| Prospetto | Potenziale cliente | NO |
| Cliente | Cliente attivo | S&Igrave; |
| Cliente non pi&ugrave; attivo | Ex cliente | NO (scaduti) |
| Prospetto Canale Tecnico | Potenziale via canale tecnico | NO |
| Cliente Canale Tecnico | Cliente via canale tecnico | S&Igrave; |
| Cliente senza relazione | Cliente senza attivit&agrave; | NO |
| Cliente Canale Tecnico non pi&ugrave; attivo | Ex cliente canale tecnico | NO (scaduti) |

### 4.3 Relazione Stato Cliente / Tipo Veicolo

> **IMPORTANTE**: Lo Stato Cliente e il Tipo Veicolo sono INDIPENDENTI

| Stato Cliente | Pu&ograve; avere INSTALLATO? | Pu&ograve; avere EXTRA? |
|---------------|------------------------------|-------------------------|
| Prospetto | NO | S&Igrave; |
| Cliente | S&Igrave; | S&Igrave; |
| Cliente non pi&ugrave; attivo | S&Igrave; (in scadenza) | S&Igrave; |

Un **Prospetto** pu&ograve; avere veicoli EXTRA (li monitoriamo in attesa di acquisirlo).
Un **Cliente** pu&ograve; avere sia INSTALLATO che EXTRA (broker diversi per noleggiatori diversi).

---

## 5. CASO STUDIO: ATIB SRL

### 5.1 Situazione attuale (dal CRM)
| Campo | Valore |
|-------|--------|
| Nome | ATIB SRL |
| P.IVA | 00552060980 |
| Stato Cliente | **Prospetto** |
| Totale Flotta | 5 |
| Flotta con CNS | 0 |

### 5.2 Interpretazione
- ATIB &egrave; un **Prospetto**: non ha ancora contratti attivi con BR Car Service
- Ha **5 veicoli** in totale (Totale Flotta)
- BR Car Service ne gestisce **0** (Flotta con CNS = 0)
- I veicoli ATIB nel nostro DB sono tutti **EXTRA**

### 5.3 Scenario futuro (quando diventa Cliente)

```
ATIB SRL (Stato: Cliente)
&boxv;
&boxvr;&boxh;&boxh; ARVAL &rarr; Broker: BR CAR SERVICE
&boxv;   &boxur;&boxh;&boxh; 3 veicoli &rarr; INSTALLATO
&boxv;       (gestiti, statistiche, fatturazione)
&boxv;
&boxur;&boxh;&boxh; AYVENS &rarr; Broker: Altro
    &boxur;&boxh;&boxh; 2 veicoli &rarr; EXTRA
        (monitorati, no statistiche BR)
```

In questo scenario:
- ATIB diventa "Cliente" perch&eacute; ha contratti con BR (via ARVAL)
- I 3 veicoli ARVAL sono INSTALLATO (li gestiamo noi)
- I 2 veicoli AYVENS restano EXTRA (altro broker)
- Le statistiche BR contano solo i 3 veicoli ARVAL

---

## 6. STATO CRM (Campo interno BR)

### 6.1 Definizione
Lo **Stato CRM** indica se il cliente &egrave; presente nel CRM di BR Car Service.
&Egrave; un campo INTERNO, diverso dallo "Stato Cliente".

### 6.2 Valori
| Codice | Significato |
|--------|-------------|
| PROSPECT NOSTRO | Nel CRM come potenziale |
| CLIENTE NOSTRO | Nel CRM come cliente attivo |
| CLIENTE NON NOSTRO | NON presente nel CRM |

### 6.3 Utilizzo
- Quando si importano clienti dal CRM: stato_crm = "PROSPECT NOSTRO" o "CLIENTE NOSTRO"
- Clienti caricati manualmente senza riscontro CRM: stato_crm = "CLIENTE NON NOSTRO"

---

## 7. RIQUADRO NOLEGGIATORI (Scheda Cliente)

### 7.1 Scopo
Mostrare per ogni noleggiatore usato dal cliente quale broker lo gestisce.

### 7.2 Stati relazione noleggiatore
| Stato | Colore | Significato |
|-------|--------|-------------|
| NOSTRI | Verde | BR Car Service &egrave; il broker |
| ALTRO BROKER | Rosso | Gestito da altro broker |
| PROSPECT | Blu | In trattativa |
| GI&Agrave; CLIENTI | Rosso | Ex clienti per quel noleggiatore |

### 7.3 Esempio visivo

```
&boxdr;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxdl;
&boxv; NOLEGGIATORI                      &boxv;
&boxvr;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxvl;
&boxv; ARVAL    [NOSTRI]        &squ; Verde &boxv;
&boxv; AYVENS   [ALTRO BROKER]  &squ; Rosso &boxv;
&boxv; LEASYS   [PROSPECT]      &squ; Blu   &boxv;
&boxur;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxh;&boxul;
```

---

## 8. RIQUADRO FLOTTA (Scheda Cliente)

### 8.1 Struttura proposta

| Campo | Descrizione | Fonte |
|-------|-------------|-------|
| Veicoli Installato | Counter veicoli gestiti BR | COUNT(tipo_veicolo='Installato') |
| Veicoli Extra | Counter veicoli altri broker | COUNT(tipo_veicolo='Extra') |
| Totale Flotta CRM | Dato ufficiale dal CRM | Campo `totale_flotta` |
| Flotta con CNS | Veicoli gestiti (da CRM) | Campo `flotta_con_cns` |
| Parco Potenziale | Stima inserita manualmente | Input utente |
| Veicoli Rilevati | Dichiarazione cliente + data | Input utente |

### 8.2 Controlli di coerenza
- `Veicoli Installato` dovrebbe corrispondere a `Flotta con CNS`
- Se diversi: possibili veicoli scaduti o non ancora importati

---

## 9. STATISTICHE E REPORT

### 9.1 Statistiche OPERATIVE (solo INSTALLATO)
- Canone medio flotta gestita
- Scadenze contratti
- KM percorsi
- Distribuzione per noleggiatore
- Fatturato BR

### 9.2 Statistiche COMMERCIALI (INSTALLATO + EXTRA)
- Parco totale clienti
- Quote di mercato per noleggiatore
- Potenziale aggredibile
- Intelligence competitiva

### 9.3 Filtri standard nei report
```python
# Solo veicoli gestiti (statistiche operative)
WHERE tipo_veicolo = 'Installato'

# Tutti i veicoli (analisi commerciale)
WHERE tipo_veicolo IN ('Installato', 'Extra')
```

---

## 10. PROCESSO DI ACQUISIZIONE

### 10.1 Da EXTRA a INSTALLATO
Quando BR Car Service acquisisce la gestione di veicoli precedentemente EXTRA:

1. Cliente firma contratto con BR per un noleggiatore
2. I veicoli di quel noleggiatore passano da EXTRA a INSTALLATO
3. Aggiornare `tipo_veicolo` = 'Installato'
4. Aggiornare relazione noleggiatore = 'NOSTRI'
5. I veicoli entrano nelle statistiche operative

### 10.2 Da INSTALLATO a storico
Quando un contratto scade:
1. Veicolo rimane INSTALLATO ma con data scadenza passata
2. Oppure: campo `stato_veicolo` = 'Scaduto'
3. Esce dalle statistiche attive

---

## 11. CAMPI DATABASE

### 11.1 Tabella `clienti` - Nuovi campi
| Campo | Tipo | Valori | Note |
|-------|------|--------|------|
| stato_cliente | TEXT | Valori CRM | Relazione commerciale |
| stato_crm | TEXT | PROSPECT NOSTRO, CLIENTE NOSTRO, CLIENTE NON NOSTRO | Presenza in CRM |
| totale_flotta | INTEGER | | Da import CRM |
| flotta_con_cns | INTEGER | | Da import CRM |

### 11.2 Tabella `veicoli` - Nuovi campi
| Campo | Tipo | Valori | Default |
|-------|------|--------|---------|
| tipo_veicolo | TEXT | Installato, Extra | Extra |

### 11.3 Tabella `clienti_noleggiatori` - Nuova tabella
| Campo | Tipo | Note |
|-------|------|------|
| cliente_id | INTEGER | FK a clienti |
| noleggiatore | TEXT | Nome noleggiatore |
| stato_relazione | TEXT | NOSTRI, ALTRO_BROKER, etc. |
| data_inizio | DATE | Inizio relazione |
| note | TEXT | |

---

## 12. CHECKLIST SVILUPPO

Ogni nuova funzionalit&agrave; deve verificare:

- [ ] Distingue correttamente INSTALLATO vs EXTRA?
- [ ] Le statistiche operative usano solo INSTALLATO?
- [ ] Lo Stato Cliente &egrave; gestito indipendentemente dal tipo veicolo?
- [ ] Il riquadro Noleggiatori mostra chi &egrave; il broker?
- [ ] I filtri rispettano la logica broker/noleggiatore?

---

## 13. GLOSSARIO

| Termine | Definizione |
|---------|-------------|
| **Broker** | Intermediario che gestisce i contratti di noleggio (es. BR Car Service) |
| **Noleggiatore** | Societ&agrave; di noleggio (es. Arval, Leasys, Ayvens) |
| **Installato** | Veicolo gestito da BR Car Service |
| **Extra** | Veicolo monitorato ma gestito da altro broker |
| **Flotta con CNS** | Numero veicoli gestiti da BR (dal CRM) |
| **Totale Flotta** | Numero totale veicoli del cliente |
| **Stato Cliente** | Relazione commerciale cliente-BR |
| **Stato CRM** | Presenza del cliente nel CRM BR |

---

## 14. FILE CRM ANALIZZATI

### 14.1 File sorgente
| File | Data | Record | Descrizione |
|------|------|--------|-------------|
| `Accounts_2026_01_26.csv` | 2026-01-26 | 2.618 | Export completo clienti CRM |
| `Accounts_2026_01_26.xml` | 2026-01-26 | 1 | Estrazione singola ATIB (test) |

### 14.2 Struttura file CRM (124 colonne)
Le colonne principali del file CRM sono:

| # | Colonna CRM | Mapping DB | Note |
|---|-------------|------------|------|
| 4 | Nome Azienda | nome_cliente | |
| 59 | Partita IVA/CF | p_iva | 11 cifre con zeri |
| 32 | Codice Fiscale | cod_fiscale | |
| 60 | **Stato Cliente** | **stato_cliente** | 7 valori possibili |
| 43 | **Totale Flotta** | totale_flotta | Veicoli totali cliente |
| 77 | **Flotta con CNS** | flotta_con_cns | Veicoli INSTALLATO |
| 5 | Telefono | telefono | |
| 34 | Email PEC | pec | |
| 33 | Codice Sdi | sdi | |
| 16-24 | Via/Citt&agrave;/Prov/CAP fatturazione | indirizzo (sede legale) | |
| 54-58 | Sede Operativa | sede_operativa_* | Campi separati |
| 65 | Commerciale | commerciale | |
| 70 | Codice Ateco | codice_ateco | |
| 82-83 | Noleggiatore principale CNS 1/2 | noleggiatore_principale | |
| 84 | Profilazione per totale flotta | profilazione_flotta | SINGLE/SMALL/MEDIUM/TOP/VIP |
| 87-88 | Holding | holding_id, holding_nome | |

### 14.3 Valori "Stato Cliente" estratti dal CRM
| Valore esatto CRM | Record | Percentuale |
|-------------------|--------|-------------|
| Prospetto | 2.060 | 78,7% |
| Cliente | 332 | 12,7% |
| Cliente non pi&ugrave; attivo | 172 | 6,6% |
| Prospetto Canale Tecnico | 24 | 0,9% |
| Cliente Canale Tecnico | 17 | 0,6% |
| Cliente senza relazione | 7 | 0,3% |
| Cliente Canale Tecnico non pi&ugrave; attivo | 4 | 0,2% |

### 14.4 Noleggiatori presenti nel CRM
| Noleggiatore | Come CNS 1 | Come CNS 2 |
|--------------|------------|------------|
| Arval | 154 | 11 |
| Leasys | 135 | 25 |
| Leaseplan | 117 | 30 |
| Ald | 15 | 5 |
| Ayvens | 9 | 5 |
| Drivalia | 1 | - |
| Alphabet | 1 | - |
| Sif&agrave; | - | 2 |
| Rent2Go | - | 1 |

### 14.5 Statistiche Flotta dal CRM
| Metrica | Valore |
|---------|--------|
| Totale veicoli (Totale Flotta) | 8.518 |
| Veicoli gestiti BR (Flotta con CNS) | 1.030 |
| Clienti con veicoli gestiti | 420 |
| Media veicoli/cliente | 3,3 |
| Max veicoli singolo cliente | 230 |

### 14.6 Profilazione clienti per dimensione flotta
| Profilazione | Range | Clienti |
|--------------|-------|---------|
| SINGLE | 1 | 1.798 |
| SMALL | 2-5 | 511 |
| MEDIUM | 6-20 | 160 |
| TOP | 21-50 | 34 |
| VIP | 50+ | 19 |
| Da definire | 0 | 93 |

---

## 15. DOCUMENTI CORRELATI

| Documento | Contenuto |
|-----------|-----------|
| `2026-01-26_analisi_completa_crm.md` | Analisi dettagliata file CRM |
| `2026-01-26_analisi_mappatura_crm.md` | Mappatura campi CRM &rarr; DB |
| `stati_cliente.xlsx` | Configurazione stati cliente |
| `stati_noleggiatore.xlsx` | Configurazione stati relazione noleggiatore |
| `stati_crm.xlsx` | Configurazione stati CRM interno |
| `noleggiatori_assistenza.xlsx` | Configurazione noleggiatori (colori, link) |

---

## 16. STORICO DOCUMENTO

| Data | Versione | Autore | Modifiche |
|------|----------|--------|-----------|
| 2026-01-26 | 1.0 | Claude + Michele | Creazione documento |
| 2026-01-26 | 1.1 | Claude + Michele | Aggiunta sezione file CRM analizzati |

---

**QUESTO DOCUMENTO &Egrave; RIFERIMENTO OBBLIGATORIO PER OGNI SVILUPPO FUTURO**
