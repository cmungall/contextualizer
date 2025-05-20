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

ai_model = OpenAIModel(
    "anthropic/claude-sonnet",  # Using a model we know works
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
    result = agent.run_sync('Where does "hello world" come from?')
    # print(result.output)  # Using .output instead of .data

    # print(dir(result))

    print(result.data)

    # Expected output:
    # The first known use of "hello, world" was in a 1974 textbook about the C programming language.
