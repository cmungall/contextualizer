.PHONY: hello elevation hello-world soil test-minimal

# Run the agent-test entry point, corresponding to src/agent_test/__init__.py
hello:
	.venv/bin/agent-test

# Run elevation info script directly
elevation:
	export $$(cat .env | xargs) && .venv/bin/python src/agent_test/evelation_info.py

# src/agent_test/geo_agent.py
# Run the geo_agent.py script
geo:
	export $$(cat .env | xargs) && .venv/bin/python src/agent_test/geo_agent.py

# Run the hello_world.py script
hello-world:
	export $$(cat .env | xargs) && .venv/bin/python src/agent_test/hello_world.py

# src/agent_test/maptools.py -- no main to test

# Run the soil_agent.py script
soil:
	export $$(cat .env | xargs) && .venv/bin/python src/agent_test/soil_agent.py

# Run the weather.at.py script
weather:
	export $$(cat .env | xargs) && .venv/bin/python src/agent_test/weather.at.py

# Run the wikipedia_animal_qa.py script
wiki:
	export $$(cat .env | xargs) && .venv/bin/python src/agent_test/wikipedia_animal_qa.py

# Run original agent tests
test-agent:
	.venv/bin/pytest tests/test_agent.py -v

test-minimal:
	.venv/bin/pytest tests/test_minimal_agent.py -v


