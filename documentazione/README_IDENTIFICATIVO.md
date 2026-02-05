# Sistema Identificativo P.IVA/CF - Documentazione

## Panoramica

Il sistema usa **P.IVA** per le aziende e **Codice Fiscale** per le persone fisiche come identificativo univoco dei clienti. Questo garantisce:

- **URL stabili** condivisibili: `/c/IT00552060980`
- **API-ready** per integrazioni esterne
- **Nessuna commistione** tra aziende e persone
- **Resilienza** a ricostruzioni database

## Logica Identificativo

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENTE                               │
├─────────────────────────────────────────────────────────┤
│  Ha P.IVA?                                              │
│     SÌ → Identificativo = IT + 11 cifre                 │
│          Esempio: IT00552060980                         │
│                                                         │
│     NO → Ha CF?                                         │
│           SÌ (persona) → Identificativo = 16 caratteri  │
│                          Esempio: RSSMRA80A01F205X      │
│           SÌ (azienda) → Identificativo = 11 cifre      │
│                          Esempio: 00297880171           │
│                                                         │
│           NO → Fallback = id_<numero>                   │
│                Esempio: id_123                          │
└─────────────────────────────────────────────────────────┘
```

## Struttura Cartelle Allegati

### Prima (vecchia struttura)
```
allegati_note/
└── clienti/
    └── 123/                    # ID nota (fragile!)
        └── documento.pdf
```

### Dopo (nuova struttura)
```
allegati_note/
└── clienti/
    ├── IT00552060980/          # P.IVA azienda
    │   └── 20250113_143052_123/  # timestamp_notaID
    │       └── documento.pdf
    │
    └── RSSMRA80A01F205X/       # CF persona fisica
        └── 20250113_150030_456/
            └── foto.jpg
```

## URL Disponibili

### Pagine Cliente
| URL | Descrizione |
|-----|-------------|
| `/c/IT00552060980` | Cliente per P.IVA |
| `/c/RSSMRA80A01F205X` | Cliente per CF |
| `/cliente/123` | (retrocompatibilità) Cliente per ID |

### API JSON
| URL | Descrizione |
|-----|-------------|
| `/api/cliente/IT00552060980` | Dati completi cliente |
| `/api/cerca?q=rossi&limit=10` | Ricerca clienti |

### Esempio risposta API
```json
{
  "id": 123,
  "nome_cliente": "ROSSI SRL",
  "p_iva": "IT00552060980",
  "cod_fiscale": "00552060980",
  "score": "B",
  "credito": 50000,
  "_identificativo": "IT00552060980",
  "_url": "/c/IT00552060980",
  "_num_veicoli": 5,
  "_canone_totale": 2500,
  "_num_note": 3
}
```

## Uso nei Template

### Helper disponibili
```html
<!-- URL cliente -->
<a href="{{ url_cliente(cliente) }}">Vai al cliente</a>

<!-- Identificativo -->
<code>{{ get_identificativo(cliente) }}</code>

<!-- Esempio completo -->
{% for c in clienti %}
<tr>
    <td>
        <a href="{{ url_cliente(c) or url_for('dettaglio_cliente', cliente_id=c.id) }}">
            {{ c.nome_cliente }}
        </a>
    </td>
    <td>{{ get_identificativo(c) or '-' }}</td>
</tr>
{% endfor %}
```

## Funzioni Python

### Modulo `utils_identificativo.py`

```python
from app.utils_identificativo import (
    # Normalizzazione
    normalizza_piva,          # 'it00552060980' → 'IT00552060980'
    normalizza_cf,            # 'rssmra80a01f205x' → 'RSSMRA80A01F205X'
    
    # Identificativo
    get_identificativo_cliente,   # dict → 'IT00552060980' o 'RSSMRA...'
    get_identificativo_or_id,     # con fallback a 'id_123'
    
    # Ricerca
    cerca_cliente_per_identificativo,  # cursor, 'IT...' → dict cliente
    
    # Cartelle
    get_cartella_allegati_cliente,     # Path cliente
    get_cartella_nota_cliente,         # Path nota specifica
    trova_cartella_nota_esistente,     # Cerca cartella esistente
    
    # URL
    url_cliente,              # dict → '/c/IT00552060980'
)
```

### Esempi d'uso

```python
# In una route Flask
from app.utils_identificativo import cerca_cliente_per_identificativo

@app.route('/esempio/<identificativo>')
def esempio(identificativo):
    conn = get_connection()
    cursor = conn.cursor()
    
    cliente = cerca_cliente_per_identificativo(cursor, identificativo)
    
    if not cliente:
        return "Non trovato", 404
    
    # cliente è un dict con tutti i dati
    return f"Trovato: {cliente['nome_cliente']}"
```

## Migrazione

### Verifica struttura attuale
```bash
python3 migra_allegati.py --status
```

### Anteprima (dry-run)
```bash
python3 migra_allegati.py --dry-run
```

### Esegui migrazione
```bash
python3 migra_allegati.py
```

## Installazione

### Metodo automatico (consigliato)
```bash
# Copia i file in ~/Scaricati/, poi:
chmod +x installa_sistema_identificativo.sh
./installa_sistema_identificativo.sh
```

### Metodo manuale
```bash
cd ~/gestione_flotta

# 1. Ferma server
./scripts/gestione_flotta.sh stop

# 2. Copia modulo
cp ~/Scaricati/utils_identificativo.py app/

# 3. Applica patch
python3 ~/Scaricati/patch_sistema_identificativo.py

# 4. Migra allegati (opzionale)
python3 migra_allegati.py --dry-run
python3 migra_allegati.py

# 5. Riavvia
./scripts/gestione_flotta.sh start
```

## Retrocompatibilità

- I vecchi URL `/cliente/<id>` **continuano a funzionare**
- Gli allegati vecchi vengono cercati anche nella struttura precedente
- La migrazione è opzionale (ma consigliata)

## File Coinvolti

| File | Modifiche |
|------|-----------|
| `app/utils_identificativo.py` | **NUOVO** - Funzioni helper |
| `app/web_server.py` | Nuove route, import, context processor |
| `allegati_note/clienti/` | Nuova struttura cartelle |
| `db/gestionale.db` | Percorsi allegati aggiornati |

## Troubleshooting

### "Cliente non trovato"
- Verifica che P.IVA abbia il prefisso IT
- CF persona deve essere 16 caratteri esatti
- Prova con `/cliente/<id>` per escludere problemi identificativo

### Allegati non trovati dopo migrazione
- Verifica log in `logs/migrazione_allegati_*.log`
- Controlla percorsi in tabella `allegati_note`

### Errore import
```bash
# Verifica che il modulo esista
ls -la ~/gestione_flotta/app/utils_identificativo.py
```
