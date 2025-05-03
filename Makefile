.PHONY: hello elevation geo hello-world soil weather wiki test-agent test-minimal

RUN_UV_PYTHON=.venv/bin/python
RUN_UV_PYTEST=.venv/bin/pytest

all: hello elevation geo hello-world soil weather wiki test-agent test-minimal

# Run the agent-test entry point, corresponding to src/agent_test/__init__.py
hello:
	.venv/bin/agent-test

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



