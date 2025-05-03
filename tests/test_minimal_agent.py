import pytest
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv(verbose=True)

# Check if API key is available
api_key = os.getenv("CBORG_API_KEY")
print(f"API key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API key starts with: {api_key[:5]}...")

# Import after environment setup
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Create a model with a known working model
ai_model = OpenAIModel(
    "anthropic/claude-sonnet",  # Using model we know works
    provider=OpenAIProvider(
        base_url="https://api.cborg.lbl.gov",
        api_key=api_key),
)

# Create a simple agent - rename to avoid conflict with test function
simple_agent = Agent(
    ai_model,
    system_prompt="You are a helpful assistant. Answer questions concisely."
)

@pytest.mark.parametrize(
    "query,ideal",
    [
        ("What is 2+2?", "4"),
        ("What is the capital of France?", "Paris"),
    ],
)
def test_agent(query, ideal):
    """Test that the agent can answer basic questions."""
    print(f"Running query: {query}")
    r = simple_agent.run_sync(query)  # Use the renamed agent variable
    data = r.data
    print(f"Response: {data}")
    assert data is not None
    if ideal is not None:
        assert ideal.lower() in data.lower()
    print("TEST RESULT:", data)

if __name__ == "__main__":
    # Run the test directly if needed
    response = simple_agent.run_sync("What is 2+2?")
    print(f"Direct test result: {response.data}")
