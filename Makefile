.PHONY: hello elevation geo hello-world soil weather wiki test-agent test-minimal test-soil

RUN_UV_PYTHON=uv run
RUN_UV_PYTEST=uv run pytest

all: hello elevation geo hello-world soil weather wiki test-agent test-minimal test-soil

# Run the agent-test entry point, corresponding to src/agent_test/__init__.py
hello:
	$(RUN_UV_PYTHON) agent-test

# Run elevation info script directly
elevation:
	$(RUN_UV_PYTHON) src/agent_test/evelation_info.py

# src/agent_test/geo_agent.py
# Run the geo_agent.py script
geo:
	$(RUN_UV_PYTHON) src/agent_test/geo_agent.py

# Run the hello_world.py script
hello-world:
	$(RUN_UV_PYTHON) src/agent_test/hello_world.py

# src/agent_test/maptools.py -- no main to test

# Run the soil_agent.py script
soil:
	$(RUN_UV_PYTHON) src/agent_test/soil_agent.py

# Run the weather.at.py script
weather:
	$(RUN_UV_PYTHON) src/agent_test/weather.at.py

# Run the wikipedia_animal_qa.py script
wiki:
	$(RUN_UV_PYTHON) src/agent_test/wikipedia_animal_qa.py

# Run original agent tests
test-agent:
	$(RUN_UV_PYTEST) tests/test_agent.py -v

test-minimal:
	$(RUN_UV_PYTEST) tests/test_minimal_agent.py -v

# Run soil agent tests
test-soil:
	$(RUN_UV_PYTEST) tests/test_soil_agent.py -v

local/nmdc-biosamples.json:
	wget -O $@ 'https://api.microbiomedata.org/nmdcschema/biosample_set?max_page_size=99999'



local/nmdc-latlon-inferred.json local/nmdc-latlon-summary.json: local/nmdc-biosamples.json
	$(RUN_UV_PYTHON) src/make_nmdc_biosamples_location_inferences.py \
		--input $< \
		--add-inferred-latlon \
		--add-inferred-elevation \
		--random-n 130 \
		--output local/nmdc-latlon-inferred.json \
		--summary-output local/nmdc-latlon-summary.json
		
# Process biosamples with AI interpretation of map images (using both Google Maps & CBORG)
local/nmdc-ai-map-enriched.json: local/nmdc-latlon-inferred.json
	$(RUN_UV_PYTHON) src/biosample_map_interpreter.py \
		--input $< \
		--output $@ \
		--max-samples 13 \
		--map-types satellite,roadmap,terrain \
		--zoom-levels 13,15,17

# Compare asserted vs inferred environmental values using Claude Sonnet
local/nmdc-comparison-summary.json local/nmdc-llm-comparison.json: local/nmdc-ai-map-enriched.json
	$(RUN_UV_PYTHON) src/biosample_llm_comparator.py \
		--input $< \
		--output local/nmdc-llm-comparison.json \
		--summary-output local/nmdc-comparison-summary.json \
		--max-samples 13

# Other map types available:
# - hybrid: Combines satellite imagery with road labels
# - terrain: Already added - shows topographical features
# - Historical imagery: Available through Earth Engine APIs (separate service)
