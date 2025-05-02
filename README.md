# Contextualizer Project: Comprehensive Guide

## Project Overview

The Contextualizer project is an AI agent framework built on `pydantic-ai` that uses the Berkeley Lab's CBORG API to access various language models. This guide combines official documentation, notes, and practical experience to help you get started with the project.

## Repository Structure

```
contextualizer/
├── CBORG-CODE.md        # Project documentation
├── debug_env.py         # Utility to debug environment variables
├── pyproject.toml       # Project dependencies
├── src/
│   └── agent_test/      # Agent implementations
│       ├── geo_agent.py            # Geographic information agent
│       ├── soil_agent.py           # Soil science agent
│       ├── wikipedia_animal_qa.py  # Animal information agent
│       ├── weather.at.py           # Weather information agent
│       ├── hello_world.py          # Simple example agent
│       ├── maptools.py             # Map utilities
│       └── dotenv_fix.py           # Environment variable loader
├── tests/               # Test files
└── .env                 # Environment variables (create this)
```

## Prerequisites

- Python 3.9+ installed (3.9 is specified in pyproject.toml)
- `uv` installed (a faster alternative to pip)
- CBORG API key (required for all agents)
- Google Maps API key (only required for map functionality in geo_agent.py)

## 1. Understanding The CBORG API

### What is CBORG?

CBORG is Berkeley Lab's AI Portal that provides secure access to various AI models. The CBORG API server is an OpenAI-compatible proxy server built on LiteLLM, which means it can be used as a drop-in replacement for OpenAI's API.

### Available Models

The CBORG API provides access to various models. Based on testing, your account may have access to:

- **LBL-hosted models**:
  - lbl/cborg-chat:latest
  - lbl/cborg-vision:latest
  - lbl/nomic-embed-text

- **Commercial models**:
  - openai/gpt-4.1-nano
  - aws/claude-haiku
  - (potentially others)

Note that not all models listed in documentation may be available to your specific API key. You can use the test connection script below to see which models are accessible to you.

## 2. Environment Setup

### Install UV

```bash
# Install UV on Unix/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH if needed
export PATH="$HOME/.cargo/bin:$PATH"
```

### Create Virtual Environment

```bash
# Navigate to your repository
cd contextualizer

# Create a virtual environment with UV
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install development dependencies
uv pip install -e .
```

### Python Version Issues

The project requires Python 3.9. If you're using pyenv and encounter version issues:

```bash
# Install Python 3.9 with pyenv
pyenv install 3.9

# Or remove .python-version file to use UV's Python directly
rm .python-version
```

## 3. API Key Configuration

### Set Up Your CBORG API Key

You have several options:

1. **Create a .env file** (recommended):
   ```bash
   echo "CBORG_API_KEY=your_cborg_api_key_here
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here" > .env
   ```

2. **Export in your shell**:
   ```bash
   export CBORG_API_KEY="your_cborg_api_key_here"
   export GOOGLE_MAPS_API_KEY="your_google_maps_api_key_here"  # Only if using map functions
   ```

3. **Use the .venv/bin/python approach**:
   ```bash
   CBORG_API_KEY="your_cborg_api_key_here" .venv/bin/python your_script.py
   ```

### How to Get the CBORG API Key

- If affiliated with Berkeley Lab: CBORG is free for employees with @lbl.gov, @es.net, or @nersc.gov email.
- If not affiliated: Contact Berkeley Lab to discuss access options.

## 4. Verifying Your Setup

Create a test_connection.py file to verify your API connection:

```python
import os
from dotenv import load_dotenv

# Load environment variables and debug
load_dotenv(verbose=True)
api_key = os.getenv("CBORG_API_KEY")
print(f"CBORG_API_KEY found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"First few characters: {api_key[:5]}...")

# Test basic API connection
import openai

client = openai.OpenAI(
    api_key=api_key,
    base_url="https://api.cborg.lbl.gov"
)

try:
    # List available models
    models = client.models.list()
    print("Connection successful!")
    print(f"Available models: {[m.id for m in models.data][:5]}...")
except Exception as e:
    print(f"Connection error: {e}")
```

Save this as `src/agent_test/test_connection.py` and run it:

```bash
source .venv/bin/activate
python src/agent_test/test_connection.py
```

Or directly using the virtual environment's Python:

```bash
.venv/bin/python src/agent_test/test_connection.py
```

## 5. Running Your First Agent

### Fix hello_world.py

The original hello_world.py file needs fixing to use an available model. Here's a proper version:

```python
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load CBORG API key from environment variable
api_key = os.getenv("CBORG_API_KEY")

# Check if API key is available
if not api_key:
    raise ValueError("CBORG_API_KEY environment variable is not set.")

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Use a model that we know is available from the test_connection.py output
ai_model = OpenAIModel(
    "lbl/cborg-chat:latest",  # Use a model you confirmed is available
    provider=OpenAIProvider(
        base_url="https://api.cborg.lbl.gov",
        api_key=api_key),
)

agent = Agent(
    ai_model,
    system_prompt='Be concise, reply with one sentence.',
)

if __name__ == "__main__":
    # Only run this code when file is executed directly
    print("Sending query to LLM...")
    result = agent.run_sync('Where does "hello world" come from?')
    print("Response received!")
    print(result.data)
```

Save this file and run it using:

```bash
.venv/bin/python src/agent_test/hello_world.py
```

### Create a Simple Animal Test Agent

Here's a simple agent for testing that works with the result attributes:

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("CBORG_API_KEY")

# Check if API key is available
if not api_key:
    raise ValueError("CBORG_API_KEY environment variable is not set.")
else:
    print(f"API key loaded: {api_key[:5]}...")

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Create a model with a model we know exists
ai_model = OpenAIModel(
    "lbl/cborg-chat:latest",  # Use a model we know works
    provider=OpenAIProvider(
        base_url="https://api.cborg.lbl.gov",
        api_key=api_key),
)

# Create a simple animal agent
animal_agent = Agent(
    ai_model,
    system_prompt="You are a helpful assistant that provides information about animals.",
)

if __name__ == "__main__":
    # Run a query about an animal
    animal = "tiger"
    print(f"Asking about {animal}...")
    
    try:
        result = animal_agent.run_sync(f"Tell me three interesting facts about the {animal}.")
        print("\nRESPONSE:")
        # Check for different result attributes and use what's available
        if hasattr(result, 'data'):
            print(result.data)
        elif hasattr(result, 'content'):
            print(result.content)
        elif hasattr(result, 'message'):
            print(result.message)
        else:
            # Just print the entire result object
            print(result)
            print("\nAvailable attributes:")
            for attr in dir(result):
                if not attr.startswith('_'):
                    print(f"- {attr}")
    except Exception as e:
        print(f"Error running agent: {e}")
```

Save this file as `src/agent_test/animal_test.py` and run it with:

```bash
.venv/bin/python src/agent_test/animal_test.py
```

## 6. Understanding and Using Agents

### Common Agent Structure

Most agents in this repository follow this pattern:

1. Load environment variables and API key
2. Configure an AI model with the CBORG provider
3. Create an Agent with a system prompt
4. Register tools using decorators
5. Execute queries with the agent

### Agent Tools

Tools can be defined and registered using the `@agent.tool_plain` decorator, as shown in geo_agent.py:

```python
@geo_agent.tool_plain
def get_elev(
    lat: float, lon: float,
) -> float:
    """
    Get the elevation of a location.

    :param lat: latitude
    :param lon: longitude
    :return: elevation in m
    """
    print(f"Looking up elevation for lat={lat}, lon={lon}")
    return elevation((lat, lon))
```

### Available Agents

- **geo_agent.py**: Geographic data agent (needs GOOGLE_MAPS_API_KEY for map functionality)
- **soil_agent.py**: Soil science agent
- **weather.at.py**: Weather information agent
- **wikipedia_animal_qa.py**: Wikipedia animal information agent

## 7. Troubleshooting

### Module Not Found Errors

If you see errors like: `ModuleNotFoundError: No module named 'agent_test'`:

1. Use the virtual environment Python directly:
   ```bash
   .venv/bin/python -m pytest tests/
   ```
   
2. Or make sure you've activated the virtual environment:
   ```bash
   source .venv/bin/activate
   pytest tests/
   ```

### API Key Authentication Errors

If your CBORG API key isn't being loaded:

1. Check that your `.env` file exists and contains the correct key
2. Check that dotenv is loading properly:
   ```python
   from dotenv import load_dotenv
   load_dotenv(verbose=True)  # Set verbose=True to see loading details
   ```
3. Try explicitly exporting the variable:
   ```bash
   export CBORG_API_KEY="your_cborg_api_key_here"
   ```

### Model Availability Errors

If you see errors related to model availability:

1. Run the `test_connection.py` script to see which models are available to your API key
2. Update your agent code to use an available model (like "lbl/cborg-chat:latest")
3. Check the error message for specific details about the failure

## 8. Running Tests

The repository includes tests in the `tests/` directory:

```bash
# Run all tests (not recommended initially)
.venv/bin/pytest tests/

# Run a specific test
.venv/bin/pytest tests/test_agent.py::test_agent -v

# Run with specific parameters
.venv/bin/pytest tests/test_agent.py::test_agent[query-ideal] -v
```

For more reliable testing, create a debug test file and run it directly:

```bash
.venv/bin/python test_agent_debug.py
```

## 9. Code Style Guidelines

The project follows these coding standards:

- **Imports**: Standard grouping (stdlib, third-party, local)
- **Type Annotations**: All functions should use Python type hints
- **Docstrings**: Multi-line docstring with params/returns (triple quotes)
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Error Handling**: Use try/except with logging, avoid silent failures
- **Tools**: Use @agent.tool_plain decorator for agent functions
- **Async**: Both sync and async functions are used; choose appropriately

## 10. If You Don't Have Berkeley Lab Access

If you're not affiliated with Berkeley Lab and can't get a CBORG API key, you can modify the repository to use other LLM providers:

1. Change the base_url to your preferred provider
2. Update the model names to ones available on that provider
3. Adjust the API authentication methods as needed

Example for using OpenAI directly:

```python
ai_model = OpenAIModel(
    "gpt-4-turbo",  # Use your available model
    provider=OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY")),  # No need for base_url with direct OpenAI
)
```

## References and Resources

- CBORG API Portal: https://cborg.lbl.gov/
- API Documentation: https://cborg.lbl.gov/api_docs/
- API Examples: https://cborg.lbl.gov/api_examples/
- Pydantic-AI: Framework for building AI agents used by this project
- 