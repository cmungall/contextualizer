import asyncio
import os
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx
import dotenv
from pydantic import Field, BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables with verbose output
dotenv.load_dotenv(verbose=True)
api_key = os.getenv("CBORG_API_KEY")

# Debug info
logger.info(f"API key found: {'Yes' if api_key else 'No'}")
if api_key:
    logger.info(f"API key starts with: {api_key[:5]}...")

# Ensure API key is available
if not api_key:
    raise ValueError("CBORG_API_KEY environment variable is not set.")


@dataclass
class ApiDeps:
    """Dependencies container for the API agent."""
    client: httpx.AsyncClient


# Using a model we know works based on previous testing
ai_model = OpenAIModel(
    "anthropic/claude-sonnet",  # Changed from openai/gpt-4o to a model we know works
    provider=OpenAIProvider(
        base_url="https://api.cborg.lbl.gov",  # Removed /v1 suffix
        api_key=api_key,
    )
)

wikipedia_api_agent = Agent(
    ai_model,
    system_prompt=(
        "You are a helpful assistant that can give any answers to Animals that are on Wikipedia. Do not use your own knowledge."
    ),
    deps_type=ApiDeps,
    instrument=True
)


# Create a simpler synchronous version of get_animal_info that doesn't rely on the async context
def get_animal_info_sync(animal_name: str) -> str:
    """
    Synchronous version of get_animal_info that uses a synchronous HTTP client.

    Args:
        animal_name: The name of the animal to look up

    Returns:
        A string containing information about the animal from Wikipedia
    """
    try:
        logger.info(f"Searching for information about: {animal_name}")

        # Create a synchronous client
        with httpx.Client() as client:
            # Search for the animal
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": f"{animal_name} animal",
                "format": "json"
            }
            logger.info(f"Making Wikipedia search request with params: {search_params}")
            search_response = client.get("https://en.wikipedia.org/w/api.php", params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()

            if not search_data["query"]["search"]:
                logger.warning(f"No search results found for {animal_name}")
                return f"No information found for {animal_name}."

            page_title = search_data["query"]["search"][0]["title"]
            logger.info(f"Found Wikipedia page: {page_title}")

            # Get content
            content_params = {
                "action": "query",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "titles": page_title,
                "format": "json"
            }
            logger.info(f"Fetching content with params: {content_params}")
            content_response = client.get("https://en.wikipedia.org/w/api.php", params=content_params)
            content_response.raise_for_status()
            content_data = content_response.json()

            pages = content_data["query"]["pages"]
            page_id = next(iter(pages))
            extract = pages[page_id].get("extract", "")

            if not extract:
                logger.warning(f"No content extracted from page {page_title}")
                return f"Found page {page_title} but couldn't extract any information."

            logger.info(f"Successfully extracted content from Wikipedia page: {page_title}")
            # Return a concise version
            return f"Information about {page_title} from Wikipedia:\n\n{extract[:800]}..."

    except Exception as e:
        logger.error(f"Error retrieving information about {animal_name}: {e}")
        return f"Error retrieving information about {animal_name}: {str(e)}"


@wikipedia_api_agent.tool()
async def get_animal_info(ctx: RunContext[ApiDeps], animal_name: str) -> str:
    """
    Get information about an animal using the Wikipedia API.

    This function searches for the specified animal on Wikipedia and returns
    a summary of information about it. Use this function whenever you need
    to provide factual information about animals, including:
    - Animal descriptions
    - Habitats
    - Diets
    - Behavior
    - Conservation status

    Args:
        ctx: The run context
        animal_name: The name of the animal to look up (e.g., "tiger", "blue whale", "emperor penguin")

    Returns:
        A string containing information about the animal from Wikipedia
    """
    try:
        logger.info(f"Searching for information about: {animal_name}")

        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": f"{animal_name} animal",
            "format": "json"
        }
        logger.info(f"Making Wikipedia search request with params: {search_params}")

        # Use get method of AsyncClient
        search_response = await ctx.deps.client.get("https://en.wikipedia.org/w/api.php", params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()

        if not search_data["query"]["search"]:
            logger.warning(f"No search results found for {animal_name}")
            return f"No information found for {animal_name}."

        page_title = search_data["query"]["search"][0]["title"]
        logger.info(f"Found Wikipedia page: {page_title}")

        # summary content
        content_params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": page_title,
            "format": "json"
        }
        logger.info(f"Fetching content with params: {content_params}")

        # Use get method of AsyncClient
        content_response = await ctx.deps.client.get("https://en.wikipedia.org/w/api.php", params=content_params)
        content_response.raise_for_status()
        content_data = content_response.json()

        pages = content_data["query"]["pages"]
        page_id = next(iter(pages))
        extract = pages[page_id].get("extract", "")

        if not extract:
            logger.warning(f"No content extracted from page {page_title}")
            return f"Found page {page_title} but couldn't extract any information."

        logger.info(f"Successfully extracted content from Wikipedia page: {page_title}")
        # Return a concise version
        return f"Information about {page_title} from Wikipedia:\n\n{extract[:800]}..."

    except Exception as e:
        logger.error(f"Error retrieving information about {animal_name}: {e}")
        return f"Error retrieving information about {animal_name}: {str(e)}"


def run_query(query: str) -> None:
    """
    Run a query against the wikipedia_api_agent synchronously.

    This function creates a synchronous HTTP client, injects the necessary
    dependencies, and prints the agent's response.

    Args:
        query (str): The question to be processed by the agent.
    """
    logger.info(f"Running query: {query}")
    try:
        # First try with the agent to demonstrate what it does
        with httpx.Client() as client:
            deps = ApiDeps(client=httpx.AsyncClient())
            result = wikipedia_api_agent.run_sync(query, deps=deps)
            print("\nAGENT RESPONSE:")
            print(result.output)

        # If the agent returned a tool call, extract the animal name and call directly
        if "<|python_start|>" in result.output and "get_animal_info" in result.output:
            print("\nThe agent suggested calling the tool but didn't execute it.")
            print("Attempting to extract animal name from the tool call...")

            # Very simple parsing of the tool call
            start = result.output.find('animal_name="')
            if start > -1:
                start += len('animal_name="')
                end = result.output.find('"', start)
                if end > -1:
                    animal_name = result.output[start:end]
                    print(f"Extracted animal name: {animal_name}")

                    # Call the synchronous version directly
                    print("\nDIRECT FUNCTION EXECUTION:")
                    info = get_animal_info_sync(animal_name)
                    print(info)

    except Exception as e:
        logger.error(f"Error during query execution: {e}")
        print(f"An error occurred: {e}")


# Only execute when run directly
if __name__ == "__main__":
    # Example query
    animal_query = "Tell me about pandas. What do they eat and where do they live?"
    run_query(animal_query)
