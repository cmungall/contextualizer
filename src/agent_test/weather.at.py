import os
from geopy.geocoders import Nominatim
from meteostat import Point, Daily
from pydantic_ai import Agent
from dateutil import parser
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing import Any, Tuple
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(verbose=True)

# Load CBORG API key from environment variable
api_key = os.getenv("CBORG_API_KEY")

# Debug info
logger.info(f"API key found: {'Yes' if api_key else 'No'}")
if api_key:
    logger.info(f"API key starts with: {api_key[:5]}...")

# Ensure the API key is set
if not api_key:
    raise ValueError("CBORG_API_KEY environment variable is not set.")

# Initialize geocoder
geo = Nominatim(user_agent="EGSB Hackathon AI Agent toy")

# Configure the AI model with CBORG API endpoint
# Keep using the original model as requested
ai_model = OpenAIModel(
    "anthropic/claude-sonnet",  # Using the original model
    provider=OpenAIProvider(
        base_url="https://api.cborg.lbl.gov",
        api_key=api_key,
    )
)

# Initialize the Agent with a system prompt
geo_agent = Agent(
    ai_model,
    system_prompt='You are an awesome geography teacher who specializes in weather patterns.',
)


# Register a tool to get lat/long for a location string
@geo_agent.tool_plain
def get_loc(location_string: str) -> Tuple[float, float]:
    """
    Get the lat / long for a place given an address string or other location
    string.

    :param location_string: the location to query like an address a city / state / country etc.
    :return: A tuple of the latitude and longitude of the location.
    """
    try:
        logger.info(f"Geocoding location: {location_string}")
        loc = geo.geocode(location_string)
        if loc is None:
            logger.warning(f"Could not geocode location: {location_string}")
            return (0.0, 0.0)  # Default return for failed geocoding

        logger.info(f"Found location: {loc}")
        return (loc.latitude, loc.longitude)
    except Exception as e:
        logger.error(f"Error geocoding location {location_string}: {e}")
        return (0.0, 0.0)  # Default return for failed geocoding


@geo_agent.tool_plain
def get_weather(location_string: str, start_date: str, end_date: str) -> dict[str, Any]:
    """
    Get information about the weather at a particular location over a particular time period.

    :param location_string: the location to query like an address a city / state / country etc.
    :param start_date: the start of the period of interest as a string.
    :param end_date: the end of the period of interest as a string.
    :return: A dictionary of weather information for the location.
    """
    try:
        # Get location coordinates
        logger.info(f"Getting weather for {location_string} from {start_date} to {end_date}")
        lat, lon = get_loc(location_string)
        if lat == 0.0 and lon == 0.0:
            return {"error": f"Could not geocode location: {location_string}"}

        # Create Point object
        pt = Point(lat, lon)

        # Parse dates
        st = parser.parse(start_date)
        end = parser.parse(end_date)
        logger.info(f"Using coordinates: {pt}, date range: {st} to {end}")

        # Fetch weather data
        ret = Daily(pt, st, end).fetch()
        logger.info(f"Weather data fetched: {len(ret)} records")

        # Convert to dictionary
        d = ret.to_dict()
        return d

    except Exception as e:
        logger.error(f"Error getting weather: {e}")
        return {"error": str(e)}


# Only run this code when the script is executed directly
if __name__ == "__main__":
    # Use the agent to query weather
    query = """
    Tell me about the weather in the city of kalamazoo over 7 days from February 14, 2024.
    Summarize the general trends and how happy you think people would be about the weather.
    """
    logger.info(f"Running query: {query}")

    try:
        # Run the query through the agent
        result = geo_agent.run_sync(query)

        # Print the result
        print("\nAGENT RESPONSE:")
        print(result.data)  # Using .output instead of deprecated .data

        # Try direct function call as well
        print("\nDIRECT FUNCTION EXECUTION:")
        direct_result = get_weather(
            "Kalamazoo, Michigan",
            "February 14, 2024",
            "February 21, 2024"
        )
        print(f"Found {len(direct_result.keys())} weather data points")

    except Exception as e:
        logger.error(f"Error running agent: {e}")
