import os
import requests
import logging
from typing import Tuple, Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(verbose=True)


def get_static_map(latitude: float, longitude: float, zoom: int = 13,
                   size: Tuple[int, int] = (600, 400),
                   marker_color: str = "red",
                   maptype: str = "satellite") -> Optional[bytes]:
    """
    Fetches a static map image from Google Maps API.

    :param latitude: Latitude coordinate
    :param longitude: Longitude coordinate
    :param zoom: Zoom level (1-20)
    :param size: Image size as (width, height) tuple
    :param marker_color: Color of the marker
    :param maptype: Type of map (roadmap, satellite, hybrid, terrain)
    :return: Raw image bytes or None if request failed
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    # Log API key status (securely)
    if not api_key:
        logger.warning("GOOGLE_MAPS_API_KEY environment variable not set")
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")
    else:
        logger.info(f"Google Maps API key found (starts with: {api_key[:5]}...)")

    base_url = "https://maps.googleapis.com/maps/api/staticmap"

    # Validate parameters
    if zoom < 1 or zoom > 20:
        logger.warning(f"Invalid zoom level: {zoom}, must be between 1-20. Using default of 13.")
        zoom = 13

    if size[0] > 640 or size[1] > 640:
        logger.warning(f"Size exceeds Google Maps API limits: {size}. Maximum is 640x640. Adjusting.")
        size = (min(size[0], 640), min(size[1], 640))

    valid_maptypes = ["roadmap", "satellite", "hybrid", "terrain"]
    if maptype not in valid_maptypes:
        logger.warning(f"Invalid maptype: {maptype}. Using default of 'satellite'.")
        maptype = "satellite"

    # Build request parameters
    params = {
        "center": f"{latitude},{longitude}",
        "zoom": zoom,
        "size": f"{size[0]}x{size[1]}",
        "markers": f"color:{marker_color}|{latitude},{longitude}",
        "maptype": maptype,
        "key": api_key
    }
    logger.info(f"Fetching map for coordinates: {latitude}, {longitude}, zoom: {zoom}, maptype: {maptype}")
    logger.debug(f"Full request parameters: {params}")

    try:
        logger.info("Sending request to Google Maps API")
        response = requests.get(base_url, params=params)
        response.raise_for_status()

        # Check content type to ensure we got an image
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type:
            logger.error(f"Received non-image response: {content_type}")
            return None

        logger.info(f"Successfully fetched map image: {len(response.content)} bytes")
        return response.content
    except requests.RequestException as e:
        logger.error(f"Error fetching map: {e}")
        return None


def get_map_url(latitude: float, longitude: float, zoom: int = 13,
                marker_color: str = "red",
                maptype: str = "satellite") -> Optional[str]:
    """
    Generates a Google Maps URL for the given coordinates.
    This can be used to open the location in Google Maps in a browser.

    :param latitude: Latitude coordinate
    :param longitude: Longitude coordinate
    :param zoom: Zoom level (1-20)
    :param marker_color: Color of the marker
    :param maptype: Type of map (roadmap, satellite, hybrid, terrain)
    :return: URL string or None if parameters are invalid
    """
    try:
        # Validate parameters
        if zoom < 1 or zoom > 20:
            logger.warning(f"Invalid zoom level: {zoom}, must be between 1-20. Using default of 13.")
            zoom = 13

        valid_maptypes = ["roadmap", "satellite", "hybrid", "terrain"]
        if maptype not in valid_maptypes:
            logger.warning(f"Invalid maptype: {maptype}. Using default of 'satellite'.")
            maptype = "satellite"

        # Build the URL
        url = f"https://www.google.com/maps/@{latitude},{longitude},{zoom}z/data=!3m1!1e3"

        if maptype == "roadmap":
            url = f"https://www.google.com/maps/@{latitude},{longitude},{zoom}z"

        logger.info(f"Generated Google Maps URL for coordinates: {latitude}, {longitude}")
        return url
    except Exception as e:
        logger.error(f"Error generating map URL: {e}")
        return None


def get_location_info(latitude: float, longitude: float) -> dict:
    """
    Returns a dictionary with basic information about a location.

    :param latitude: Latitude coordinate
    :param longitude: Longitude coordinate
    :return: Dictionary with location information
    """
    try:
        # Create a dictionary with location information
        info = {
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude
            },
            "maps_url": get_map_url(latitude, longitude),
            "static_map_available": os.getenv("GOOGLE_MAPS_API_KEY") is not None
        }

        return info
    except Exception as e:
        logger.error(f"Error getting location info: {e}")
        return {"error": str(e)}
