#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MIGRAZIONE - Campi Immatricolazione e Revisione Veicoli
==============================================================================
Versione: 1.0.0
Data: 2026-02-06
Descrizione: Aggiunge i campi necessari per gestire data immatricolazione
             e revisione periodica dei veicoli.

Colonne aggiunte a 'veicoli':
    - data_immatricolazione TEXT  (data prima immatricolazione)
    - revisione_gestita TEXT     (data scadenza gestita, per dedup automatico)
    - data_revisione TEXT        (data effettiva revisione, opzionale)
    - note_revisione TEXT        (note libere, opzionale)

Uso:
    python3 scripts/migrazione_revisione.py
==============================================================================
"""

import sqlite3
import os
import sys

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

DB_PATH = os.path.expanduser('~/gestione_flotta/db/gestionale.db')

COLONNE_NUOVE = [
    # (nome, tipo, default)
    ('data_immatricolazione', 'TEXT', None),
    ('revisione_gestita',     'TEXT', None),
    ('data_revisione',        'TEXT', None),
    ('note_revisione',        'TEXT', None),
]


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 60)
    print("MIGRAZIONE - Immatricolazione e Revisione Veicoli")
    print("=" * 60)
    print()

    if not os.path.exists(DB_PATH):
        print(f"ERRORE: Database non trovato: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Leggi colonne esistenti
    cursor.execute("PRAGMA table_info(veicoli)")
    colonne_esistenti = {row[1] for row in cursor.fetchall()}

    print("[1/2] Aggiunta colonne alla tabella veicoli...")
    aggiunte = 0
    for nome, tipo, default in COLONNE_NUOVE:
        if nome in colonne_esistenti:
            print(f"  SKIP  {nome} - gia' presente")
        else:
            sql = f"ALTER TABLE veicoli ADD COLUMN {nome} {tipo}"
            if default is not None:
                sql += f" DEFAULT {default}"
            cursor.execute(sql)
            print(f"  ADD   {nome} {tipo}")
            aggiunte += 1

    conn.commit()

    # Verifica
    print()
    print("[2/2] Verifica struttura...")
    cursor.execute("PRAGMA table_info(veicoli)")
    colonne_dopo = {row[1] for row in cursor.fetchall()}
    
    ok = True
    for nome, _, _ in COLONNE_NUOVE:
        if nome in colonne_dopo:
            print(f"  OK    {nome}")
        else:
            print(f"  ERRORE  {nome} - NON trovata!")
            ok = False

    conn.close()

    print()
    print("=" * 60)
    if ok:
        print(f"  MIGRAZIONE COMPLETATA - {aggiunte} colonne aggiunte")
    else:
        print("  MIGRAZIONE CON ERRORI")
    print("=" * 60)
    print()
    print("Logica revisione:")
    print("  - Prima revisione: 5 anni dalla data immatricolazione")
    print("  - Successive: ogni 2 anni")
    print("  - Notifica a 60gg e 30gg (solo giorni lavorativi)")
    print("  - revisione_gestita = data scadenza -> stop notifiche")
    print("  - Ciclo automatico: nuova scadenza -> reset notifiche")


if __name__ == '__main__':
    main()
