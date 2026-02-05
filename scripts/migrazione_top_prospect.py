#!/usr/bin/env python3
# ==============================================================================
# MIGRAZIONE DATABASE - Tabelle Top Prospect
# ==============================================================================
# Versione: 1.0.0
# Data: 2026-01-29
# Descrizione: Crea le tabelle necessarie per la funzionalit&agrave; Top Prospect
#
# ESECUZIONE:
#   cd ~/gestione_flotta
#   python3 scripts/migrazione_top_prospect.py
#
# ==============================================================================

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Path del database
DB_PATH = Path(__file__).parent.parent / 'db' / 'gestionale.db'

def log(msg):
    """Stampa messaggio con timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def esegui_migrazione():
    """Esegue la migrazione del database."""
    
    if not DB_PATH.exists():
        log(f"ERRORE: Database non trovato: {DB_PATH}")
        sys.exit(1)
    
    log(f"Connessione a: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # ==================================================================
        # TABELLA TOP_PROSPECT
        # ==================================================================
        log("Creazione tabella top_prospect...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS top_prospect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Riferimento cliente
                cliente_id INTEGER NOT NULL UNIQUE,
                
                -- Stato: candidato, confermato, archiviato
                stato TEXT NOT NULL DEFAULT 'candidato',
                
                -- Priorita (1=massima, 5=bassa) - solo per confermati
                priorita INTEGER DEFAULT 4,
                
                -- Date transizioni
                data_candidatura TEXT NOT NULL,
                data_conferma TEXT,
                data_archiviazione TEXT,
                
                -- Chi ha effettuato le azioni
                confermato_da_id INTEGER,
                archiviato_da_id INTEGER,
                
                -- Note opzionali
                note_conferma TEXT,
                note_archiviazione TEXT,
                
                -- Dati snapshot al momento della candidatura (per storico)
                snapshot_dipendenti INTEGER,
                snapshot_veicoli INTEGER,
                snapshot_var_valore_prod REAL,
                snapshot_var_patrimonio REAL,
                
                -- Metadati
                data_creazione TEXT NOT NULL,
                data_ultimo_aggiornamento TEXT,
                
                FOREIGN KEY (cliente_id) REFERENCES clienti(id),
                FOREIGN KEY (confermato_da_id) REFERENCES utenti(id),
                FOREIGN KEY (archiviato_da_id) REFERENCES utenti(id)
            )
        ''')
        log("  OK - tabella top_prospect creata")
        
        # ==================================================================
        # TABELLA TOP_PROSPECT_ATTIVITA (Storico)
        # ==================================================================
        log("Creazione tabella top_prospect_attivita...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS top_prospect_attivita (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Riferimento Top Prospect
                top_prospect_id INTEGER NOT NULL,
                
                -- Tipo attivita
                -- Valori: candidatura, conferma, archiviazione, ripristino,
                --         modifica_priorita, appuntamento_creato, appuntamento_modificato,
                --         nota_creata, nota_modificata
                tipo_attivita TEXT NOT NULL,
                
                -- Descrizione leggibile
                descrizione TEXT,
                
                -- Dettagli aggiuntivi (JSON)
                dettaglio_json TEXT,
                
                -- Chi ha eseguito l'azione
                utente_id INTEGER,
                
                -- Quando
                data_ora TEXT NOT NULL,
                
                FOREIGN KEY (top_prospect_id) REFERENCES top_prospect(id) ON DELETE CASCADE,
                FOREIGN KEY (utente_id) REFERENCES utenti(id)
            )
        ''')
        log("  OK - tabella top_prospect_attivita creata")
        
        # ==================================================================
        # TABELLA TOP_PROSPECT_APPUNTAMENTI
        # ==================================================================
        log("Creazione tabella top_prospect_appuntamenti...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS top_prospect_appuntamenti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Riferimento Top Prospect
                top_prospect_id INTEGER NOT NULL,
                
                -- Data e ora appuntamento
                data_appuntamento TEXT NOT NULL,
                ora_appuntamento TEXT,
                
                -- Tipo: visita, telefonata, videochiamata, altro
                tipo_appuntamento TEXT DEFAULT 'visita',
                
                -- Note su quanto fatto/da fare
                note TEXT,
                
                -- Esito (compilato dopo l'appuntamento)
                esito TEXT,
                completato INTEGER DEFAULT 0,
                
                -- Sincronizzazione Google Calendar
                sincronizzato_google INTEGER DEFAULT 0,
                google_event_id TEXT,
                
                -- Chi ha creato/modificato
                creato_da_id INTEGER,
                modificato_da_id INTEGER,
                
                -- Timestamp
                data_creazione TEXT NOT NULL,
                data_modifica TEXT,
                
                FOREIGN KEY (top_prospect_id) REFERENCES top_prospect(id) ON DELETE CASCADE,
                FOREIGN KEY (creato_da_id) REFERENCES utenti(id),
                FOREIGN KEY (modificato_da_id) REFERENCES utenti(id)
            )
        ''')
        log("  OK - tabella top_prospect_appuntamenti creata")
        
        # ==================================================================
        # TABELLA TOP_PROSPECT_NOTE
        # ==================================================================
        log("Creazione tabella top_prospect_note...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS top_prospect_note (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Riferimento Top Prospect
                top_prospect_id INTEGER NOT NULL,
                
                -- Contenuto nota
                titolo TEXT NOT NULL,
                testo TEXT,
                
                -- Autore (nome visualizzato)
                autore TEXT,
                
                -- Fissata in alto
                fissata INTEGER DEFAULT 0,
                
                -- Chi ha creato/modificato
                creato_da_id INTEGER,
                modificato_da_id INTEGER,
                
                -- Timestamp
                data_creazione TEXT NOT NULL,
                data_modifica TEXT,
                
                -- Soft delete
                eliminato INTEGER DEFAULT 0,
                data_eliminazione TEXT,
                eliminato_da TEXT,
                
                FOREIGN KEY (top_prospect_id) REFERENCES top_prospect(id) ON DELETE CASCADE,
                FOREIGN KEY (creato_da_id) REFERENCES utenti(id),
                FOREIGN KEY (modificato_da_id) REFERENCES utenti(id)
            )
        ''')
        log("  OK - tabella top_prospect_note creata")
        
        # ==================================================================
        # TABELLA TOP_PROSPECT_PARAMETRI_STORICO
        # ==================================================================
        log("Creazione tabella top_prospect_parametri_storico...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS top_prospect_parametri_storico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Snapshot dei parametri usati
                parametri_json TEXT NOT NULL,
                
                -- Risultati analisi
                clienti_analizzati INTEGER,
                candidati_trovati INTEGER,
                
                -- Chi e quando
                eseguito_da_id INTEGER,
                data_esecuzione TEXT NOT NULL,
                
                FOREIGN KEY (eseguito_da_id) REFERENCES utenti(id)
            )
        ''')
        log("  OK - tabella top_prospect_parametri_storico creata")
        
        # ==================================================================
        # INDICI
        # ==================================================================
        log("Creazione indici...")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_top_prospect_stato ON top_prospect(stato)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_top_prospect_cliente ON top_prospect(cliente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_top_prospect_priorita ON top_prospect(priorita)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tp_attivita_tp ON top_prospect_attivita(top_prospect_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tp_attivita_data ON top_prospect_attivita(data_ora)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tp_app_tp ON top_prospect_appuntamenti(top_prospect_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tp_app_data ON top_prospect_appuntamenti(data_appuntamento)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tp_app_completato ON top_prospect_appuntamenti(completato)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tp_note_tp ON top_prospect_note(top_prospect_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tp_note_eliminato ON top_prospect_note(eliminato)')
        
        log("  OK - indici creati")
        
        # ==================================================================
        # PERMESSO NEL CATALOGO
        # ==================================================================
        log("Aggiunta permesso visualizza_top_prospect al catalogo...")
        
        # Verifica se esiste gia
        cursor.execute('''
            SELECT id FROM permessi_catalogo WHERE codice = 'visualizza_top_prospect'
        ''')
        
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO permessi_catalogo (codice, descrizione, categoria, ordine, attivo)
                VALUES ('visualizza_top_prospect', 
                        'Visualizza pagina Top Prospect (senza accesso ai link aziende)', 
                        'Visualizzazione', 
                        50, 
                        1)
            ''')
            log("  OK - permesso aggiunto")
        else:
            log("  SKIP - permesso gia esistente")
        
        # ==================================================================
        # COMMIT
        # ==================================================================
        conn.commit()
        log("")
        log("=" * 50)
        log("MIGRAZIONE COMPLETATA CON SUCCESSO!")
        log("=" * 50)
        log("")
        log("Tabelle create:")
        log("  - top_prospect")
        log("  - top_prospect_attivita")
        log("  - top_prospect_appuntamenti")
        log("  - top_prospect_note")
        log("  - top_prospect_parametri_storico")
        log("")
        log("Prossimo step: copiare config_top_prospect.py in app/")
        
    except Exception as e:
        conn.rollback()
        log(f"ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


def verifica_tabelle():
    """Verifica che le tabelle siano state create correttamente."""
    
    log("Verifica tabelle...")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    tabelle = [
        'top_prospect',
        'top_prospect_attivita',
        'top_prospect_appuntamenti',
        'top_prospect_note',
        'top_prospect_parametri_storico'
    ]
    
    for tabella in tabelle:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabella}'")
        if cursor.fetchone():
            # Conta colonne
            cursor.execute(f"PRAGMA table_info({tabella})")
            cols = len(cursor.fetchall())
            log(f"  OK - {tabella} ({cols} colonne)")
        else:
            log(f"  ERRORE - {tabella} NON TROVATA!")
    
    conn.close()


if __name__ == '__main__':
    print("")
    print("=" * 60)
    print("  MIGRAZIONE DATABASE - TOP PROSPECT")
    print("=" * 60)
    print("")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        verifica_tabelle()
    else:
        esegui_migrazione()
        print("")
        verifica_tabelle()
