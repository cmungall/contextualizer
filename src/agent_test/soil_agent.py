import os
import logging
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from soilgrids import SoilGrids

# Load environment variables
load_dotenv(verbose=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load CBORG API key from environment variable
api_key = os.getenv("CBORG_API_KEY")

# Debug info
logger.info(f"API key found: {'Yes' if api_key else 'No'}")
if api_key:
    logger.info(f"API key starts with: {api_key[:5]}...")

# Ensure the API key is set
if not api_key:
    raise ValueError("CBORG_API_KEY environment variable is not set.")

# Configure the AI model with CBORG API endpoint - using original model
ai_model = OpenAIModel(
    "anthropic/claude-sonnet",  # Using the original model
    provider=OpenAIProvider(
        base_url="https://api.cborg.lbl.gov",
        api_key=api_key,
    )
)

# Create Soil Science Agent
soil_agent = Agent(
    ai_model,
    system_prompt="You are a soil science expert helping users understand soil properties. Provide clear, concise answers.",
)

# Initialize SoilGrids client
soil_grids = SoilGrids()


# Register a tool to fetch soil pH data and metadata
@soil_agent.tool_plain
def get_soil_ph_image(
        west: float, south: float, east: float, north: float
) -> str:
    """
    Get and visualize mean soil pH between 0–5 cm for a region.

    :param west: Western boundary
    :param south: Southern boundary
    :param east: Eastern boundary
    :param north: Northern boundary
    :return: Metadata summary of soil pH
    """
    try:
        logger.info(f"Fetching soil pH data for region: west={west}, south={south}, east={east}, north={north}")

        # Fetch pH data as GeoTIFF
        tif_file = "soil_ph_map.tif"
        data = soil_grids.get_coverage_data(
            service_id="phh2o",
            coverage_id="phh2o_0-5cm_mean",
            west=west,
            south=south,
            east=east,
            north=north,
            crs="urn:ogc:def:crs:EPSG::152160",
            output=tif_file
        )

        # Prepare metadata summary
        metadata_summary = "\n".join(
            [f"{key}: {value}" for key, value in soil_grids.metadata.items()]
        )

        return f"Metadata summary:\n{metadata_summary}"

    except Exception as e:
        logger.error(f"Failed to fetch soil pH data: {e}")
        return f"An error occurred while fetching soil pH data: {str(e)}"


# Only run this code when the script is executed directly
if __name__ == "__main__":
    # Parse a query and then directly execute the tool function
    query = "Show me a soil pH map for the region west=-1784000, south=1356000, east=-1140000, north=1863000"
    logger.info(f"Processing query: {query}")

    try:
        # Run the query through the agent
        logger.info("Running query through agent...")
        result = soil_agent.run_sync(query)
        agent_response = result.data
        logger.info(f"Agent response: {agent_response}")

        # Print the response
        print("\nAGENT RESPONSE:")
        print(agent_response)

        print("\nDIRECT FUNCTION EXECUTION:")
        direct_result = get_soil_ph_image(west=-1784000, south=1356000, east=-1140000, north=1863000)
        print(direct_result)

    except Exception as e:
        logger.error(f"Error running script: {e}")
