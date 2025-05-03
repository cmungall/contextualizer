import pytest
import os
import logging
from dotenv import load_dotenv
from agent_test.geo_agent import geo_agent, get_elev

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(verbose=True)

# Check for required API key
api_key = os.getenv("CBORG_API_KEY")
if not api_key:
    logger.warning("CBORG_API_KEY not found in environment, tests may fail")


@pytest.mark.parametrize(
    "query,expected_tool,expected_content",
    [
        (
                "What is the temperature at 35.97583846 and long=-84.2743123",
                "get_current_temperature",
                None
        ),
        (
                "What is the elevation at 35.97583846 and long=-84.2743123",
                "get_elev",
                "293"
        ),
        (
                "Describe the features you see at 35.97583846 and long=-84.2743123",
                "fetch_map_image_and_interpret",
                "lake"
        ),
    ],
)
def test_agent(query, expected_tool, expected_content):
    """
    Test the geo_agent with different queries.

    This test is designed to work with two behaviors:
    1. If the agent returns a tool call suggestion (most likely)
    2. If the agent actually executes the tool and returns content (less likely)

    Parameters:
        query: The query to test
        expected_tool: The tool we expect the agent to use
        expected_content: The content we expect in the result if the tool is executed
    """
    logger.info(f"Testing query: {query}")

    # Run the query through the agent
    r = geo_agent.run_sync(query)

    # Use .output instead of deprecated .data attribute
    result = r.output if hasattr(r, 'output') else r.data

    # Debug information
    logger.info(f"Response type: {type(result)}")
    logger.info(f"Response content: {result}")
    print(f"Response: {result}")

    # Make sure we got a result
    assert result is not None, "Agent returned None result"

    # Test for two possible behaviors:
    # 1. Tool call suggestion (most likely)
    if "[" in str(result) and "]" in str(result) and "(" in str(result) and ")" in str(result):
        logger.info("Agent returned tool call suggestion")
        # Check if the correct tool is being called
        assert expected_tool in str(result), f"Expected tool {expected_tool} not found in response"
        print(f"TEST PASSED: Found tool suggestion for {expected_tool}")

    # 2. Tool execution (less likely)
    elif expected_content is not None:
        logger.info("Agent appears to have executed the tool")
        # Check if the expected content is in the result
        if isinstance(expected_content, str):
            assert expected_content.lower() in str(
                result).lower(), f"Expected content '{expected_content}' not found in response"
        elif isinstance(expected_content, int):
            assert str(expected_content) in str(result), f"Expected content '{expected_content}' not found in response"
        elif isinstance(expected_content, float):
            # This is a bit trickier since float representation can vary
            found = False
            for word in str(result).split():
                try:
                    value = float(word.strip(',.;:!?'))
                    if abs(value - expected_content) < 0.1:
                        found = True
                        break
                except ValueError:
                    continue
            assert found, f"Expected numeric value around {expected_content} not found in response"
        print(f"TEST PASSED: Found expected content: {expected_content}")

    print("TEST RESULT:", result)


def test_direct_elevation():
    """Test the elevation function directly to ensure it works."""
    lat, lon = 35.97583846, -84.2743123
    elevation = get_elev(lat, lon)
    assert elevation is not None, "Elevation function returned None"
    assert isinstance(elevation, (int, float)), f"Elevation should be a number, got {type(elevation)}"
    # The expected elevation at these coordinates is around 293 meters
    assert abs(elevation - 293) < 10, f"Elevation at test coordinates expected around 293m, got {elevation}m"
    print(f"DIRECT ELEVATION TEST PASSED: {elevation}m")
