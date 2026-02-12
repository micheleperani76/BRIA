# 2026-02-12 - Ricerca Smart: Campi Mancanti

## Problema
La ricerca smart nella lista clienti (`/clienti`) non cercava in tutti i campi disponibili nel DB.

## Campi Aggiunti

### Tabella `clienti`
| Campo | Prima | Dopo |
|-------|:-----:|:----:|
| `email` | NO | SI |

### Tabella `referenti_clienti`
| Campo | Prima | Dopo |
|-------|:-----:|:----:|
| `note` | NO | SI |

### Tabella `veicoli`
| Campo | Prima | Dopo |
|-------|:-----:|:----:|
| `driver_telefono` | NO | SI |
| `driver_email` | NO | SI |

### Tabella `sedi_cliente` (nuova subquery)
| Campo | Prima | Dopo |
|-------|:-----:|:----:|
| `indirizzo` | NO | SI |
| `citta` | NO | SI |
| `denominazione` | NO | SI |
| `provincia` | NO | SI |
| `cap` | NO | SI |

## Riepilogo parametri query
- **Prima**: 21 parametri LIKE
- **Dopo**: 30 parametri LIKE (+9)

## Badge "Trovato in" aggiornati
- **Contatto**: label cambiata da "Tel/PEC" a "Contatto" (include anche email)
- **Sede**: nuovo badge viola per match in sedi_cliente
- **Driver**: ora mostra anche match su telefono/email driver

## File Modificati
| File | Tipo modifica |
|------|--------------|
| `app/web_server.py` | 6 patch chirurgiche (query + matches) |
| `templates/index/_ricerca_smart.html` | Aggiunto badge Sede, label Contatto |

## Note
- `capogruppo_piva` non esiste nel DB (solo `capogruppo_nome` e `capogruppo_cf`)
- Se necessario, richiede ALTER TABLE separata
