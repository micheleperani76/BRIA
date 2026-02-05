#!/usr/bin/env python3
# ==============================================================================
# GESTIONE FLOTTA - Configurazione Top Prospect
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-01-29
# Descrizione: Parametri configurabili per la funzionalit&agrave; Top Prospect
#
# COME MODIFICARE I PARAMETRI:
#   1. Aprire questo file con un editor di testo
#   2. Modificare i valori nella sezione PARAMETRI_CANDIDATURA
#   3. Salvare e riavviare il server
#
# ==============================================================================

# ==============================================================================
# PARAMETRI CANDIDATURA TOP PROSPECT
# ==============================================================================
# Questi parametri determinano quali clienti vengono proposti come candidati
# Un cliente diventa candidato se soddisfa TUTTI i criteri seguenti

PARAMETRI_CANDIDATURA = {
    # -------------------------------------------------------------------------
    # CRITERI BILANCIO
    # -------------------------------------------------------------------------
    
    # Variazione Valore Produzione (anno corrente vs anno precedente)
    # Valore: percentuale minima accettata (es: -10 = max calo del 10%)
    # Se il calo &egrave; maggiore di questa soglia, il cliente NON &egrave; candidato
    'variazione_valore_produzione_min': -10,  # -10 = accetta calo fino al 10%
    
    # Variazione Patrimonio Netto (anno corrente vs anno precedente)
    # Valore: percentuale minima accettata
    # Se la variazione &egrave; negativa (calo), il cliente NON &egrave; candidato
    'variazione_patrimonio_netto_min': 0,  # 0 = deve essere positivo o stabile
    
    # -------------------------------------------------------------------------
    # CRITERI DIMENSIONALI
    # -------------------------------------------------------------------------
    
    # Numero minimo di dipendenti
    'dipendenti_min': 50,
    
    # Numero minimo di veicoli in flotta
    # NOTA: Il criterio e soddisfatto se ALMENO UNO tra:
    #   - Veicoli nel database (tabella veicoli)
    #   - Campo "Veicoli Rilevati" (inserito manualmente)
    # supera questa soglia
    'veicoli_min': 50,
    
    # -------------------------------------------------------------------------
    # CRITERI OPZIONALI (impostare None per disabilitare)
    # -------------------------------------------------------------------------
    
    # Valore produzione minimo assoluto (in euro)
    # None = nessun limite
    'valore_produzione_min': None,  # es: 5000000 per 5 milioni
    
    # Patrimonio netto minimo assoluto (in euro)
    # None = nessun limite
    'patrimonio_netto_min': None,  # es: 1000000 per 1 milione
    
    # Score Creditsafe massimo accettato (A, B, C, D, E)
    # None = accetta tutti gli score
    'score_max': None,  # es: 'C' per accettare solo A, B, C
}

# ==============================================================================
# CONFIGURAZIONE PRIORIT&Agrave;
# ==============================================================================
# Livelli di priorit&agrave; per i Top Prospect confermati

LIVELLI_PRIORITA = {
    1: {
        'nome': 'Massima',
        'colore': '#dc3545',  # Rosso
        'icona': 'bi-star-fill',
        'badge_class': 'bg-danger'
    },
    2: {
        'nome': 'Alta',
        'colore': '#fd7e14',  # Arancione
        'icona': 'bi-star-fill',
        'badge_class': 'bg-warning text-dark'
    },
    3: {
        'nome': 'Media',
        'colore': '#ffc107',  # Giallo
        'icona': 'bi-star-half',
        'badge_class': 'bg-warning text-dark'
    },
    4: {
        'nome': 'Normale',
        'colore': '#0d6efd',  # Blu
        'icona': 'bi-star',
        'badge_class': 'bg-primary'
    },
    5: {
        'nome': 'Bassa',
        'colore': '#6c757d',  # Grigio
        'icona': 'bi-star',
        'badge_class': 'bg-secondary'
    }
}

# Priorit&agrave; di default per nuovi Top Prospect confermati
PRIORITA_DEFAULT = 4  # Normale

# ==============================================================================
# CONFIGURAZIONE ICONE
# ==============================================================================

ICONE_TOP_PROSPECT = {
    # Icona per candidati (coppa grigia)
    'candidato': {
        'icona': 'bi-trophy',
        'colore': '#6c757d',  # Grigio
        'tooltip': 'Candidato Top Prospect'
    },
    # Icona per confermati (coppa dorata)
    'confermato': {
        'icona': 'bi-trophy-fill',
        'colore': '#ffc107',  # Oro
        'tooltip': 'Top Prospect'
    },
    # Nessuna icona per archiviati
    'archiviato': None
}

# ==============================================================================
# CONFIGURAZIONE GRIGLIA
# ==============================================================================

# Colonne visibili nella griglia Top Prospect
# Ordine: come appaiono da sinistra a destra
COLONNE_GRIGLIA = [
    {'campo': 'priorita', 'label': 'P', 'width': '40px', 'ordinabile': True},
    {'campo': 'nome_cliente', 'label': 'Azienda', 'width': 'auto', 'ordinabile': True},
    {'campo': 'commerciale', 'label': 'Commerciale', 'width': '120px', 'ordinabile': True},
    {'campo': 'flotta', 'label': 'Flotta', 'width': '70px', 'ordinabile': True},
    {'campo': 'dipendenti', 'label': 'Dip.', 'width': '70px', 'ordinabile': True},
    {'campo': 'provincia', 'label': 'Prov.', 'width': '60px', 'ordinabile': True},
    {'campo': 'ultimo_appuntamento', 'label': 'Ultimo App.', 'width': '100px', 'ordinabile': True},
    {'campo': 'prossimo_appuntamento', 'label': 'Prossimo App.', 'width': '100px', 'ordinabile': True},
    {'campo': 'car_policy', 'label': 'CP', 'width': '40px', 'ordinabile': False},
    {'campo': 'note_count', 'label': 'Note', 'width': '50px', 'ordinabile': False},
]

# Colonne per griglia candidati (senza priorit&agrave;)
COLONNE_GRIGLIA_CANDIDATI = [
    {'campo': 'nome_cliente', 'label': 'Azienda', 'width': 'auto', 'ordinabile': True},
    {'campo': 'commerciale', 'label': 'Commerciale', 'width': '120px', 'ordinabile': True},
    {'campo': 'flotta', 'label': 'Flotta', 'width': '70px', 'ordinabile': True},
    {'campo': 'dipendenti', 'label': 'Dip.', 'width': '70px', 'ordinabile': True},
    {'campo': 'provincia', 'label': 'Prov.', 'width': '60px', 'ordinabile': True},
    {'campo': 'var_valore_prod', 'label': 'Var. VP', 'width': '80px', 'ordinabile': True},
    {'campo': 'var_patrimonio', 'label': 'Var. PN', 'width': '80px', 'ordinabile': True},
]

# ==============================================================================
# CONFIGURAZIONE APPUNTAMENTI
# ==============================================================================

# Quanti prossimi appuntamenti mostrare nel banner in alto
APPUNTAMENTI_BANNER_LIMIT = 5

# Giorni in avanti per considerare "prossimi" appuntamenti
APPUNTAMENTI_GIORNI_AVANTI = 30

# ==============================================================================
# PERMESSI
# ==============================================================================

# Codice permesso per visibilit&agrave; Top Prospect (operatori esterni)
PERMESSO_VISUALIZZA_TOP_PROSPECT = 'visualizza_top_prospect'

# Descrizione permesso (per catalogo)
PERMESSO_DESCRIZIONE = 'Visualizza pagina Top Prospect (senza accesso ai link aziende)'

# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def get_parametri_candidatura():
    """Restituisce i parametri di candidatura correnti."""
    return PARAMETRI_CANDIDATURA.copy()


def get_livello_priorita(livello):
    """Restituisce configurazione di un livello priorit&agrave;."""
    return LIVELLI_PRIORITA.get(livello, LIVELLI_PRIORITA[PRIORITA_DEFAULT])


def get_icona_stato(stato):
    """Restituisce configurazione icona per stato Top Prospect."""
    return ICONE_TOP_PROSPECT.get(stato)


def descrivi_parametri():
    """
    Restituisce una descrizione leggibile dei parametri correnti.
    Utile per debug o visualizzazione admin.
    """
    p = PARAMETRI_CANDIDATURA
    righe = [
        "=== PARAMETRI CANDIDATURA TOP PROSPECT ===",
        "",
        "CRITERI BILANCIO:",
        f"  - Variazione Valore Produzione: minimo {p['variazione_valore_produzione_min']}%",
        f"  - Variazione Patrimonio Netto: minimo {p['variazione_patrimonio_netto_min']}%",
        "",
        "CRITERI DIMENSIONALI:",
        f"  - Dipendenti: minimo {p['dipendenti_min']}",
        f"  - Veicoli: minimo {p['veicoli_min']}",
        "",
        "CRITERI OPZIONALI:",
    ]
    
    if p['valore_produzione_min']:
        righe.append(f"  - Valore Produzione minimo: {p['valore_produzione_min']:,.0f} EUR")
    else:
        righe.append("  - Valore Produzione minimo: nessun limite")
    
    if p['patrimonio_netto_min']:
        righe.append(f"  - Patrimonio Netto minimo: {p['patrimonio_netto_min']:,.0f} EUR")
    else:
        righe.append("  - Patrimonio Netto minimo: nessun limite")
    
    if p['score_max']:
        righe.append(f"  - Score massimo: {p['score_max']}")
    else:
        righe.append("  - Score massimo: nessun limite")
    
    return "\n".join(righe)
