.PHONY: all clean test

RUN_UV_PYTHON=uv run
RUN_UV_PYTEST=uv run pytest

# Default target
all: local/oak_ridge_features.json local/nmdc-ai-map-enriched.json local/nmdc-osm-enriched.json local/nmdc-envo-normalized.json

# Directory setup
local/:
	mkdir -p $@

# OSM feature extraction for test location (Oak Ridge)
local/oak_ridge_features.json: src/agent_test/osm_features.py | local/
	$(RUN_UV_PYTHON) $< --lat 35.97583846 --lon -84.2743123 --radius 1000 --output $@

# NMDC biosample data fetch
local/nmdc-biosamples.json: | local/
	wget -O $@ 'https://api.microbiomedata.org/nmdcschema/biosample_set?max_page_size=99999'

# Process biosamples to add lat/lon and elevation
local/nmdc-latlon-inferred.json local/nmdc-latlon-summary.json: src/make_nmdc_biosamples_location_inferences.py local/nmdc-biosamples.json
	$(RUN_UV_PYTHON) $< \
		--input $(word 2,$^) \
		--add-inferred-latlon \
		--add-inferred-elevation \
		--random-n 130 \
		--output local/nmdc-latlon-inferred.json \
		--summary-output local/nmdc-latlon-summary.json
		
# Process biosamples with map image interpretation
local/nmdc-ai-map-enriched.json: src/biosample_map_interpreter.py local/nmdc-latlon-inferred.json
	$(RUN_UV_PYTHON) $< \
		--input $(word 2,$^) \
		--output $@ \
		--max-samples 13 \
		--map-types satellite,roadmap,terrain \
		--zoom-levels 13,15,17

# Extract OSM features for each biosample location (only for locations with confident coordinates)
local/nmdc-osm-enriched.json: src/biosample_osm_enricher.py local/nmdc-latlon-inferred.json
	$(RUN_UV_PYTHON) $< \
		--input $(word 2,$^) \
		--output $@ \
		--radius 1000 \
		--max-distance 10000 \
		--max-samples 13

# Apply EnvO normalization to OSM features
local/nmdc-envo-normalized.json: src/biosample_envo_normalizer.py local/nmdc-osm-enriched.json
	$(RUN_UV_PYTHON) -m src.biosample_envo_normalizer \
		--input $(word 2,$^) \
		--output $@ \
		--max-samples 13 \
		--max-features 20 \
		--confidence 0.7

# Compare asserted vs inferred environmental values
local/nmdc-comparison-summary.json local/nmdc-llm-comparison.json: src/biosample_llm_comparator.py local/nmdc-ai-map-enriched.json local/nmdc-envo-normalized.json
	$(RUN_UV_PYTHON) $< \
		--input $(word 2,$^) \
		--osm-features $(word 3,$^) \
		--output local/nmdc-llm-comparison.json \
		--summary-output local/nmdc-comparison-summary.json \
		--max-samples 13

# Testing targets
.PHONY: test-agent test-minimal test-soil
test: test-agent test-minimal test-soil

test-agent:
	$(RUN_UV_PYTEST) tests/test_agent.py -v

test-minimal:
	$(RUN_UV_PYTEST) tests/test_minimal_agent.py -v

test-soil:
	$(RUN_UV_PYTEST) tests/test_soil_agent.py -v

# Cleanup
clean:
	rm -rf local/

# Documentation of available map types
# - hybrid: Combines satellite imagery with road labels
# - terrain: Already added - shows topographical features
# - Historical imagery: Available through Earth Engine APIs (separate service)