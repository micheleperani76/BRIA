-- =============================================================================
-- STOCK ENGINE - Inizializzazione Database PostgreSQL
-- =============================================================================
-- Versione: 1.0.0
-- Data: 28 gennaio 2026
--
-- Questo script viene eseguito automaticamente all'avvio del container
-- PostgreSQL se il database è vuoto.
-- =============================================================================

-- Estensioni utili
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Per ricerche fuzzy

-- =============================================================================
-- TABELLA: veicoli
-- Contiene tutti i veicoli stock importati dai noleggiatori
-- =============================================================================
CREATE TABLE IF NOT EXISTS veicoli (
    id SERIAL PRIMARY KEY,
    
    -- Identificativi
    noleggiatore VARCHAR(20) NOT NULL,
    vin VARCHAR(50),
    data_import DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Dati originali noleggiatore
    marca_originale VARCHAR(100),
    modello_originale VARCHAR(200),
    description_originale TEXT,
    fuel_originale VARCHAR(50),
    
    -- Dati normalizzati
    marca VARCHAR(100),
    modello VARCHAR(200),
    description VARCHAR(500),
    
    -- Tecnici
    co2 DECIMAL(5,1),
    prezzo_listino DECIMAL(10,2),
    prezzo_accessori DECIMAL(10,2),
    prezzo_totale DECIMAL(10,2),
    
    -- Location
    location VARCHAR(200),
    location_address VARCHAR(300),
    
    -- Date
    data_arrivo DATE,
    data_immatricolazione DATE,
    
    -- Altri
    colore VARCHAR(100),
    colore_interno VARCHAR(100),
    targa VARCHAR(20),
    km INTEGER,
    
    -- JATO
    jato_code VARCHAR(50),
    product_id VARCHAR(50),
    omologazione VARCHAR(100),
    kw INTEGER,
    hp INTEGER,
    alimentazione VARCHAR(50),
    jato_product_description VARCHAR(300),
    vehicle_set_description VARCHAR(300),
    transmission VARCHAR(100),
    powertrain VARCHAR(50),
    
    -- Match
    match_status VARCHAR(20),
    match_score INTEGER,
    match_note TEXT,
    match_details JSONB,
    
    -- Business
    neopatentati VARCHAR(5) DEFAULT 'ND',
    stato VARCHAR(20) DEFAULT 'disponibile',
    is_promo BOOLEAN DEFAULT FALSE,
    note TEXT,
    dati_extra JSONB,
    
    -- Metadata
    elaborato_il TIMESTAMP DEFAULT NOW(),
    aggiornato_il TIMESTAMP DEFAULT NOW(),
    elaborazione_id INTEGER,
    
    -- Vincolo unicità
    UNIQUE(noleggiatore, vin, data_import)
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_veicoli_noleggiatore_data ON veicoli(noleggiatore, data_import);
CREATE INDEX IF NOT EXISTS idx_veicoli_marca ON veicoli(marca);
CREATE INDEX IF NOT EXISTS idx_veicoli_jato_code ON veicoli(jato_code);
CREATE INDEX IF NOT EXISTS idx_veicoli_match_status ON veicoli(match_status);
CREATE INDEX IF NOT EXISTS idx_veicoli_alimentazione ON veicoli(alimentazione);

-- Indice GIN per ricerca full-text
CREATE INDEX IF NOT EXISTS idx_veicoli_description_gin ON veicoli USING gin(description gin_trgm_ops);

-- =============================================================================
-- TABELLA: jato_models
-- Database veicoli JATO per matching
-- =============================================================================
CREATE TABLE IF NOT EXISTS jato_models (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) UNIQUE,
    jato_code VARCHAR(50),
    brand_description VARCHAR(100),
    jato_model VARCHAR(100),
    jato_product_description VARCHAR(300),
    vehicle_set_description VARCHAR(300),
    alimentazione VARCHAR(50),
    kw INTEGER,
    horsepower INTEGER,
    homologation VARCHAR(100),
    transmission_description VARCHAR(100),
    powertrain_type VARCHAR(50),
    co2_wltp DECIMAL(5,1),
    body_type VARCHAR(50),
    doors INTEGER,
    source_sheet VARCHAR(50),
    brand_normalized VARCHAR(100),
    description_normalized TEXT,
    importato_il TIMESTAMP
);

-- Indici
CREATE INDEX IF NOT EXISTS idx_jato_brand ON jato_models(brand_description);
CREATE INDEX IF NOT EXISTS idx_jato_brand_normalized ON jato_models(brand_normalized);
CREATE INDEX IF NOT EXISTS idx_jato_code ON jato_models(jato_code);
CREATE INDEX IF NOT EXISTS idx_jato_fuel_kw ON jato_models(alimentazione, kw);

-- =============================================================================
-- TABELLA: glossario
-- Regole normalizzazione termini
-- =============================================================================
CREATE TABLE IF NOT EXISTS glossario (
    id SERIAL PRIMARY KEY,
    noleggiatore VARCHAR(20),
    cerca VARCHAR(100) NOT NULL,
    sostituisci VARCHAR(100) NOT NULL,
    colonna VARCHAR(50),
    attivo BOOLEAN DEFAULT TRUE,
    note TEXT,
    creato_il TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- TABELLA: pattern_carburante
-- Pattern identificazione alimentazione
-- =============================================================================
CREATE TABLE IF NOT EXISTS pattern_carburante (
    id SERIAL PRIMARY KEY,
    pattern VARCHAR(50) NOT NULL UNIQUE,
    fuel_type VARCHAR(30) NOT NULL,
    priorita INTEGER DEFAULT 10,
    note TEXT,
    attivo BOOLEAN DEFAULT TRUE
);

-- =============================================================================
-- TABELLA: elaborazioni
-- Log elaborazioni eseguite
-- =============================================================================
CREATE TABLE IF NOT EXISTS elaborazioni (
    id SERIAL PRIMARY KEY,
    noleggiatore VARCHAR(20) NOT NULL,
    data_elaborazione TIMESTAMP DEFAULT NOW(),
    file_origine VARCHAR(255),
    file_origine_size INTEGER,
    veicoli_importati INTEGER DEFAULT 0,
    veicoli_matched INTEGER DEFAULT 0,
    veicoli_partial INTEGER DEFAULT 0,
    veicoli_no_match INTEGER DEFAULT 0,
    match_rate DECIMAL(5,2),
    durata_secondi INTEGER,
    stato VARCHAR(20) DEFAULT 'in_corso',
    errore TEXT,
    file_excel_output VARCHAR(255)
);

-- Indici
CREATE INDEX IF NOT EXISTS idx_elaborazioni_noleggiatore ON elaborazioni(noleggiatore);
CREATE INDEX IF NOT EXISTS idx_elaborazioni_data ON elaborazioni(data_elaborazione);

-- Foreign key (dopo creazione tabelle)
ALTER TABLE veicoli 
    ADD CONSTRAINT fk_veicoli_elaborazione 
    FOREIGN KEY (elaborazione_id) REFERENCES elaborazioni(id)
    ON DELETE SET NULL;

-- =============================================================================
-- PATTERN CARBURANTE DEFAULT
-- =============================================================================
INSERT INTO pattern_carburante (pattern, fuel_type, priorita, note) VALUES
    -- Elettrico (priorità alta)
    ('BEV', 'ELECTRIC', 100, 'Battery Electric Vehicle'),
    ('ELECTRIC', 'ELECTRIC', 100, NULL),
    ('ELETTRIC', 'ELECTRIC', 100, 'Italiano'),
    
    -- Plugin Hybrid (priorità alta per distinguere da HYBRID)
    ('PHEV', 'PLUGIN', 90, 'Plugin Hybrid'),
    ('PLUG-IN', 'PLUGIN', 90, NULL),
    ('PLUG IN', 'PLUGIN', 90, NULL),
    
    -- Hybrid (dopo PHEV)
    ('MHEV', 'HYBRID', 80, 'Mild Hybrid'),
    ('HYBRID', 'HYBRID', 70, NULL),
    ('IBRIDO', 'HYBRID', 70, 'Italiano'),
    ('HEV', 'HYBRID', 70, NULL),
    
    -- Diesel patterns
    ('DIESEL', 'DIESEL', 50, NULL),
    ('TDI', 'DIESEL', 50, 'Volkswagen Diesel'),
    ('CDI', 'DIESEL', 50, 'Mercedes Diesel'),
    ('CRDI', 'DIESEL', 50, 'Hyundai/Kia Diesel'),
    ('HDI', 'DIESEL', 50, 'Peugeot/Citroen Diesel'),
    ('BLUEHDI', 'DIESEL', 50, 'Peugeot/Citroen Diesel'),
    ('JTD', 'DIESEL', 50, 'Fiat Diesel'),
    ('MJET', 'DIESEL', 50, 'Fiat Multijet'),
    ('MULTIJET', 'DIESEL', 50, 'Fiat Diesel'),
    ('180D', 'DIESEL', 50, 'Mercedes pattern'),
    ('200D', 'DIESEL', 50, 'Mercedes pattern'),
    ('220D', 'DIESEL', 50, 'Mercedes pattern'),
    
    -- Petrol patterns
    ('PETROL', 'PETROL', 40, NULL),
    ('BENZINA', 'PETROL', 40, 'Italiano'),
    ('TSI', 'PETROL', 40, 'Volkswagen Petrol'),
    ('TFSI', 'PETROL', 40, 'Audi Petrol'),
    ('GDI', 'PETROL', 40, 'Direct Injection'),
    ('TURBO', 'PETROL', 30, 'Generic turbo'),
    
    -- GPL
    ('GPL', 'GPL', 60, NULL),
    ('LPG', 'GPL', 60, NULL),
    
    -- Metano
    ('METANO', 'METHANE', 60, 'Italiano'),
    ('CNG', 'METHANE', 60, 'Compressed Natural Gas')
ON CONFLICT (pattern) DO NOTHING;

-- =============================================================================
-- FUNZIONE: Aggiorna timestamp
-- =============================================================================
CREATE OR REPLACE FUNCTION update_aggiornato_il()
RETURNS TRIGGER AS $$
BEGIN
    NEW.aggiornato_il = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger per aggiornamento automatico timestamp
DROP TRIGGER IF EXISTS trg_veicoli_aggiornato ON veicoli;
CREATE TRIGGER trg_veicoli_aggiornato
    BEFORE UPDATE ON veicoli
    FOR EACH ROW
    EXECUTE FUNCTION update_aggiornato_il();

-- =============================================================================
-- COMMENTI
-- =============================================================================
COMMENT ON TABLE veicoli IS 'Stock veicoli importati dai noleggiatori';
COMMENT ON TABLE jato_models IS 'Database JATO per matching veicoli';
COMMENT ON TABLE glossario IS 'Regole normalizzazione termini';
COMMENT ON TABLE pattern_carburante IS 'Pattern identificazione alimentazione';
COMMENT ON TABLE elaborazioni IS 'Log elaborazioni eseguite';

-- Fine inizializzazione
SELECT 'Database Stock Engine inizializzato correttamente' AS status;
