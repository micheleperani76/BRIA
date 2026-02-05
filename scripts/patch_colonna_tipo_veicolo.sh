#!/bin/bash
# ==============================================================================
# PATCH - Aggiunta colonna Tipo Veicolo (I/E) a tutti gli elenchi
# ==============================================================================
# Data: 2026-01-26
# Descrizione: Aggiunge colonna "T" con badge I (Installato) / E (Extra)
# ==============================================================================

echo "=== Inizio patch colonna Tipo Veicolo ==="

# Backup di tutti i file
for f in flotta.html flotta_cliente.html flotta_commerciale.html flotta_noleggiatore.html flotta_risultati.html; do
    if [ -f ~/gestione_flotta/templates/$f ]; then
        cp ~/gestione_flotta/templates/$f ~/gestione_flotta/templates/${f}.bak_$(date +%Y%m%d_%H%M%S)
        echo "Backup: $f"
    fi
done

echo ""
echo "=== Applico modifiche ==="

# -----------------------------------------------------------------------------
# FLOTTA.HTML - Due tabelle (scadenze_prossime e scadenze_passate)
# -----------------------------------------------------------------------------
echo "Modifico flotta.html..."

# Tabella 1: Header - Aggiungi <th>T</th> dopo <th>Targa</th>
sed -i 's|<th>Targa</th>|<th>Targa</th>\n                        <th class="text-center" title="Tipo: I=Installato, E=Extra">T</th>|g' ~/gestione_flotta/templates/flotta.html

# Tabella 1 e 2: Body - Aggiungi cella dopo targa
sed -i 's|<td><code>{{ v.targa }}</code></td>|<td><code>{{ v.targa }}</code></td>\n                        <td class="text-center"><span class="badge" style="background-color: {{ get_tipo_veicolo_colore(v.tipo_veicolo) }};" title="{{ v.tipo_veicolo or '\''Extra'\'' }}">{{ (v.tipo_veicolo or '\''Extra'\'')[0] }}</span></td>|g' ~/gestione_flotta/templates/flotta.html

# -----------------------------------------------------------------------------
# FLOTTA_CLIENTE.HTML
# -----------------------------------------------------------------------------
echo "Modifico flotta_cliente.html..."

# Header
sed -i 's|<th>Targa</th>|<th>Targa</th>\n                        <th class="text-center" title="Tipo: I=Installato, E=Extra">T</th>|g' ~/gestione_flotta/templates/flotta_cliente.html

# Body
sed -i 's|<td><code>{{ v.targa }}</code></td>|<td><code>{{ v.targa }}</code></td>\n                        <td class="text-center"><span class="badge" style="background-color: {{ get_tipo_veicolo_colore(v.tipo_veicolo) }};" title="{{ v.tipo_veicolo or '\''Extra'\'' }}">{{ (v.tipo_veicolo or '\''Extra'\'')[0] }}</span></td>|g' ~/gestione_flotta/templates/flotta_cliente.html

# -----------------------------------------------------------------------------
# FLOTTA_NOLEGGIATORE.HTML
# -----------------------------------------------------------------------------
echo "Modifico flotta_noleggiatore.html..."

# Header
sed -i 's|<th>Targa</th>|<th>Targa</th>\n                        <th class="text-center" title="Tipo: I=Installato, E=Extra">T</th>|g' ~/gestione_flotta/templates/flotta_noleggiatore.html

# Body
sed -i 's|<td><code>{{ v.targa }}</code></td>|<td><code>{{ v.targa }}</code></td>\n                        <td class="text-center"><span class="badge" style="background-color: {{ get_tipo_veicolo_colore(v.tipo_veicolo) }};" title="{{ v.tipo_veicolo or '\''Extra'\'' }}">{{ (v.tipo_veicolo or '\''Extra'\'')[0] }}</span></td>|g' ~/gestione_flotta/templates/flotta_noleggiatore.html

# -----------------------------------------------------------------------------
# FLOTTA_RISULTATI.HTML
# -----------------------------------------------------------------------------
echo "Modifico flotta_risultati.html..."

# Header
sed -i 's|<th>Targa</th>|<th>Targa</th>\n                        <th class="text-center" title="Tipo: I=Installato, E=Extra">T</th>|g' ~/gestione_flotta/templates/flotta_risultati.html

# Body
sed -i 's|<td><code>{{ v.targa }}</code></td>|<td><code>{{ v.targa }}</code></td>\n                        <td class="text-center"><span class="badge" style="background-color: {{ get_tipo_veicolo_colore(v.tipo_veicolo) }};" title="{{ v.tipo_veicolo or '\''Extra'\'' }}">{{ (v.tipo_veicolo or '\''Extra'\'')[0] }}</span></td>|g' ~/gestione_flotta/templates/flotta_risultati.html

# -----------------------------------------------------------------------------
# FLOTTA_COMMERCIALE.HTML
# -----------------------------------------------------------------------------
echo "Modifico flotta_commerciale.html..."

# Header
sed -i 's|<th>Targa</th>|<th>Targa</th>\n                        <th class="text-center" title="Tipo: I=Installato, E=Extra">T</th>|g' ~/gestione_flotta/templates/flotta_commerciale.html

# Body
sed -i 's|<td><code>{{ v.targa }}</code></td>|<td><code>{{ v.targa }}</code></td>\n                        <td class="text-center"><span class="badge" style="background-color: {{ get_tipo_veicolo_colore(v.tipo_veicolo) }};" title="{{ v.tipo_veicolo or '\''Extra'\'' }}">{{ (v.tipo_veicolo or '\''Extra'\'')[0] }}</span></td>|g' ~/gestione_flotta/templates/flotta_commerciale.html

echo ""
echo "=== Patch completata ==="
echo ""
echo "Verificare i file con:"
echo "  grep -n 'tipo_veicolo' ~/gestione_flotta/templates/flotta*.html"
