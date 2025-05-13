import os
import json
import time
import logging
import click
import sys
import base64
import requests
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv
import uuid

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables including API keys
load_dotenv(verbose=True)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
CBORG_API_KEY = os.getenv("CBORG_API_KEY")

logger.info(f"Google Maps API key found: {'Yes' if GOOGLE_MAPS_API_KEY else 'No'}")
logger.info(f"CBORG API key found: {'Yes' if CBORG_API_KEY else 'No'}")

# Create directories for saving maps and responses
os.makedirs("local/maps", exist_ok=True)
os.makedirs("local/responses", exist_ok=True)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in meters."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # meters
    return c * r

def get_static_map(latitude: float, longitude: float, zoom: int = 13,
                  size: Tuple[int, int] = (600, 400),
                  marker_color: str = "red",
                  maptype: str = "satellite") -> Optional[bytes]:
    """
    Fetches a static map image from Google Maps API with improved error handling and logging.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        zoom: Zoom level (1-20)
        size: Image size as (width, height) tuple
        marker_color: Color of the marker
        maptype: Type of map (roadmap, satellite, hybrid, terrain)
        
    Returns:
        Raw image bytes or None if request failed
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY environment variable not set")
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")
    
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
        "key": GOOGLE_MAPS_API_KEY
    }
    logger.info(f"Fetching map for coordinates: {latitude}, {longitude}, zoom: {zoom}, maptype: {maptype}")

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

def save_map_image(image_bytes: bytes, latitude: float, longitude: float, 
                   zoom: int, maptype: str, sample_id: str) -> str:
    """
    Save map image to file and return the path.
    
    Args:
        image_bytes: Raw image bytes
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        zoom: Zoom level
        maptype: Map type (satellite, roadmap, etc.)
        sample_id: Biosample ID
        
    Returns:
        Path to saved image
    """
    # Create a safe filename
    safe_id = sample_id.replace(':', '_').replace('/', '_')
    filename = f"local/maps/{safe_id}_{maptype}_zoom{zoom}_{latitude}_{longitude}.png"
    
    with open(filename, "wb") as f:
        f.write(image_bytes)
    
    logger.info(f"Saved map image to {filename}")
    return filename

def interpret_map_with_cborg(image_path: str) -> Dict[str, Any]:
    """
    Use CBORG Vision API to interpret a map image.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with AI interpretation
    """
    if not CBORG_API_KEY:
        logger.error("CBORG_API_KEY environment variable not set")
        raise ValueError("CBORG_API_KEY environment variable not set")
    
    # Read image file
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        # Convert to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Define API endpoint
        api_url = "https://api.cborg.lbl.gov/v1/chat/completions"
        
        # Define prompt with more structured output requirements
        prompt = """
        This satellite or map image shows a geographical location. 
        Describe what you see in detail, focusing on:
        
        1. Natural features (water bodies, forests, vegetation, mountains, etc.)
        2. Human structures (buildings, roads, agricultural fields, urban areas, etc.)
        3. Landscape characteristics (terrain type, land use patterns)
        
        After your description, provide a CLASSIFICATION section with these categories, using ONLY short, standardized terms (1-5 words maximum per category):
        
        CLASSIFICATION:
        - Biome type: [forest biome|grassland biome|desert biome|freshwater biome|marine biome|urban biome|agricultural biome|wetland biome|tundra biome]
        - Local environment: [forest|agricultural field|urban area|grassland|lake|river|desert|wetland]
        - Building setting: [urban|suburban|rural|industrial|none]
        - Land use: [agriculture|residential|commercial|industrial|conservation|recreation|forestry|mixed]
        - Environmental medium: [soil|water|air|sediment|rock]
        - Habitat: [forest|grassland|aquatic|urban|agricultural]
        
        It is CRITICAL that your classification uses ONLY the specified standard terms (not sentences). If multiple terms apply, use a hyphenated combination (e.g., "forest-agricultural").
        """
        
        # Prepare request payload
        payload = {
            "model": "lbl/cborg-vision:latest",  # or appropriate CBORG vision model
            "messages": [
                {
                    "role": "system",
                    "content": "You analyze and describe geographical features from map and satellite images."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                    ]
                }
            ],
            "max_tokens": 1000
        }
        
        # Set headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CBORG_API_KEY}"
        }
        
        # Log the request
        logger.info(f"Sending interpretation request to CBORG for image: {image_path}")
        
        # Make the API call
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        
        # Save full response for reference
        response_path = image_path.replace("/maps/", "/responses/").replace(".png", "_response.json")
        with open(response_path, "w") as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Saved CBORG response to {response_path}")
        
        # Extract the text content from the response
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            return {
                "full_response": result,
                "description": content,
                "success": True
            }
        else:
            logger.error(f"Unexpected response format: {result}")
            return {
                "full_response": result,
                "success": False,
                "error": "Unexpected response format"
            }
    
    except Exception as e:
        logger.error(f"Error interpreting map with CBORG: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def extract_environmental_factors(description: str) -> Dict[str, Dict[str, str]]:
    """
    Extract environmental factors from the AI description.
    
    Args:
        description: Text description from AI
        
    Returns:
        Dictionary with environmental factors
    """
    # Lower case for easier matching
    text = description.lower()
    
    # Initialize results
    factors = {
        "env_broad_scale": {"term": None, "confidence": "low", "source": "CBORG interpretation"},
        "env_local_scale": {"term": None, "confidence": "low", "source": "CBORG interpretation"},
        "env_medium": {"term": None, "confidence": "low", "source": "CBORG interpretation"},
        "building_setting": {"term": None, "confidence": "low", "source": "CBORG interpretation"},
        "cur_land_use": {"term": None, "confidence": "low", "source": "CBORG interpretation"},
        "habitat": {"term": None, "confidence": "low", "source": "CBORG interpretation"}
    }
    
    # Look for explicit classifications in the text
    biome_indicators = {
        "forest biome": ["forest biome", "forest ecosystem", "woodland biome", "forested area"],
        "grassland biome": ["grassland biome", "grassland ecosystem", "prairie biome", "savanna"],
        "desert biome": ["desert biome", "desert ecosystem", "arid biome"],
        "freshwater biome": ["freshwater biome", "aquatic ecosystem", "freshwater ecosystem"],
        "marine biome": ["marine biome", "marine ecosystem", "coastal biome", "ocean biome"],
        "urban biome": ["urban biome", "urban ecosystem", "city biome"],
        "agricultural biome": ["agricultural biome", "agricultural ecosystem", "farmland biome"],
        "tundra biome": ["tundra biome", "tundra ecosystem", "arctic biome"],
        "wetland biome": ["wetland biome", "wetland ecosystem", "swamp biome", "marsh biome"]
    }
    
    local_env_indicators = {
        "forest": ["forest", "woodland", "woods", "forested"],
        "agricultural field": ["agricultural field", "farm field", "crop field", "farmland"],
        "urban area": ["urban area", "city", "town", "suburban", "metropolitan"],
        "grassland": ["grassland", "prairie", "meadow", "pasture"],
        "lake": ["lake", "pond", "reservoir"],
        "river": ["river", "stream", "creek"],
        "desert": ["desert", "arid land"],
        "wetland": ["wetland", "marsh", "swamp", "bog"]
    }
    
    land_use_indicators = {
        "agriculture": ["agriculture", "farming", "agricultural", "crop production"],
        "residential": ["residential", "housing", "residential area"],
        "commercial": ["commercial", "business", "commerce"],
        "industrial": ["industrial", "factory", "manufacturing"],
        "conservation": ["conservation", "protected area", "nature reserve", "park"],
        "recreation": ["recreation", "recreational", "park", "sports"],
        "forestry": ["forestry", "timber", "logging"]
    }
    
    building_setting_indicators = {
        "urban": ["urban", "city", "town", "metropolitan"],
        "suburban": ["suburban", "outskirts", "suburb"],
        "rural": ["rural", "countryside", "remote", "sparsely populated"],
        "industrial": ["industrial area", "industrial park", "industrial zone"]
    }
    
    env_medium_indicators = {
        "soil": ["soil", "ground", "dirt", "earth"],
        "water": ["water", "aquatic", "lake", "river", "stream"],
        "air": ["air", "atmosphere"],
        "sediment": ["sediment", "silt", "sand"]
    }
    
    habitat_indicators = {
        "forest": ["forest habitat", "woodland habitat", "forested"],
        "grassland": ["grassland habitat", "prairie habitat", "meadow"],
        "aquatic": ["aquatic habitat", "water habitat", "lake habitat", "river habitat"],
        "urban": ["urban habitat", "city habitat", "human-dominated"],
        "agricultural": ["agricultural habitat", "farmland habitat", "cropland"]
    }
    
    # Check for biome indicators
    for biome, indicators in biome_indicators.items():
        for indicator in indicators:
            if indicator in text:
                factors["env_broad_scale"]["term"] = biome
                factors["env_broad_scale"]["confidence"] = "medium"
                break
    
    # Check for local environment indicators
    for env, indicators in local_env_indicators.items():
        for indicator in indicators:
            if indicator in text:
                factors["env_local_scale"]["term"] = env
                factors["env_local_scale"]["confidence"] = "medium"
                break
    
    # Check for land use indicators
    for use, indicators in land_use_indicators.items():
        for indicator in indicators:
            if indicator in text:
                factors["cur_land_use"]["term"] = use
                factors["cur_land_use"]["confidence"] = "medium"
                break
    
    # Check for building setting indicators
    for setting, indicators in building_setting_indicators.items():
        for indicator in indicators:
            if indicator in text:
                factors["building_setting"]["term"] = setting
                factors["building_setting"]["confidence"] = "medium"
                break
    
    # Check for env medium indicators
    for medium, indicators in env_medium_indicators.items():
        for indicator in indicators:
            if indicator in text:
                factors["env_medium"]["term"] = medium
                factors["env_medium"]["confidence"] = "medium"
                break
    
    # Check for habitat indicators
    for habitat, indicators in habitat_indicators.items():
        for indicator in indicators:
            if indicator in text:
                factors["habitat"]["term"] = habitat
                factors["habitat"]["confidence"] = "medium"
                break
    
    # Try to extract from 'classification' sections - usually at the end
    if "probable biome" in text or "biome type" in text:
        lines = description.split('\n')
        for i, line in enumerate(lines):
            if "biome" in line.lower() and i+1 < len(lines):
                # Extract term after the label
                if ":" in line:
                    biome = line.split(":", 1)[1].strip()
                    factors["env_broad_scale"]["term"] = biome
                    factors["env_broad_scale"]["confidence"] = "high"
    
    # Similar extraction for other classification lines
    categories_to_check = {
        "local environment": "env_local_scale",
        "land use": "cur_land_use",
        "building setting": "building_setting"
    }
    
    for category, factor in categories_to_check.items():
        if category in text:
            lines = description.split('\n')
            for i, line in enumerate(lines):
                if category in line.lower() and i+1 < len(lines):
                    # Extract term after the label
                    if ":" in line:
                        value = line.split(":", 1)[1].strip()
                        if value.lower() not in ["n/a", "none", "not applicable"]:
                            factors[factor]["term"] = value
                            factors[factor]["confidence"] = "high"
    
    return factors

def enrich_biosample_with_map_interpretation(sample: Dict, map_types: List[str], zoom_levels: List[int]) -> Dict:
    """
    Enrich a biosample with map interpretations from multiple map types and zoom levels.
    
    Args:
        sample: NMDC Biosample JSON object
        map_types: List of map types to request (e.g., ["satellite", "roadmap"])
        zoom_levels: List of zoom levels to request
        
    Returns:
        Enriched biosample
    """
    # Check if the sample has valid coordinates
    lat_lon = sample.get("lat_lon")
    if not lat_lon or not isinstance(lat_lon, dict) or "latitude" not in lat_lon or "longitude" not in lat_lon:
        logger.warning(f"Sample {sample.get('id', 'unknown')} does not have valid lat_lon")
        return sample
    
    # Get coordinates
    lat = lat_lon["latitude"]
    lon = lat_lon["longitude"]
    sample_id = sample.get("id", f"unknown_{uuid.uuid4().hex[:8]}")
    
    # Create a place to store all interpretations
    all_interpretations = []
    
    # Process each combination of map type and zoom level
    for map_type in map_types:
        for zoom in zoom_levels:
            # Fetch map
            logger.info(f"Fetching {map_type} map at zoom {zoom} for sample {sample_id}")
            map_image = get_static_map(lat, lon, zoom=zoom, maptype=map_type)
            
            if not map_image:
                logger.warning(f"Failed to fetch {map_type} map at zoom {zoom} for sample {sample_id}")
                continue
            
            # Save map image
            image_path = save_map_image(map_image, lat, lon, zoom, map_type, sample_id)
            
            # Interpret with CBORG Vision API
            logger.info(f"Interpreting {map_type} map at zoom {zoom} for sample {sample_id}")
            interpretation = interpret_map_with_cborg(image_path)
            
            if not interpretation.get("success", False):
                logger.warning(f"Failed to interpret {map_type} map at zoom {zoom} for sample {sample_id}")
                continue
            
            # Extract environmental factors
            factors = extract_environmental_factors(interpretation["description"])
            
            # Add to interpretations
            all_interpretations.append({
                "map_type": map_type,
                "zoom_level": zoom,
                "image_path": image_path,
                "description": interpretation["description"],
                "environmental_factors": factors
            })
            
            # Add a short delay before the next request to avoid rate limits
            time.sleep(1.0)
    
    # If we have interpretations, add them to the sample
    if all_interpretations:
        # Merge environmental factors from all interpretations
        merged_factors = {
            "env_broad_scale": {"term": None, "confidence": "low", "source": None},
            "env_local_scale": {"term": None, "confidence": "low", "source": None},
            "env_medium": {"term": None, "confidence": "low", "source": None},
            "building_setting": {"term": None, "confidence": "low", "source": None},
            "cur_land_use": {"term": None, "confidence": "low", "source": None},
            "habitat": {"term": None, "confidence": "low", "source": None}
        }
        
        # Prefer high confidence factors from any interpretation
        for interp in all_interpretations:
            factors = interp["environmental_factors"]
            for factor, data in factors.items():
                if data["confidence"] == "high" and merged_factors[factor]["confidence"] != "high":
                    merged_factors[factor] = {
                        "term": data["term"],
                        "confidence": data["confidence"],
                        "source": f"{interp['map_type']} map at zoom {interp['zoom_level']}"
                    }
                elif data["confidence"] == "medium" and merged_factors[factor]["confidence"] == "low":
                    merged_factors[factor] = {
                        "term": data["term"],
                        "confidence": data["confidence"],
                        "source": f"{interp['map_type']} map at zoom {interp['zoom_level']}"
                    }
                elif data["confidence"] == "low" and merged_factors[factor]["confidence"] == "low" and merged_factors[factor]["term"] is None:
                    merged_factors[factor] = {
                        "term": data["term"],
                        "confidence": data["confidence"],
                        "source": f"{interp['map_type']} map at zoom {interp['zoom_level']}"
                    }
        
        # Add to sample
        sample["map_interpretations"] = {
            "interpretations": all_interpretations,
            "merged_environmental_factors": merged_factors
        }
    
    return sample

@click.command()
@click.option("--input", 
              default="local/nmdc-latlon-inferred.json", 
              help="Input JSON file containing biosamples with lat_lon")
@click.option("--output", 
              default="local/nmdc-ai-map-enriched.json", 
              help="Output file for enriched biosamples")
@click.option("--max-samples", 
              type=int, 
              default=None, 
              help="Maximum number of samples to process (for testing)")
@click.option("--map-types",
              default="satellite,roadmap",
              help="Comma-separated list of map types to use (satellite,roadmap,hybrid,terrain)")
@click.option("--zoom-levels",
              default="13,17",
              help="Comma-separated list of zoom levels to use (1-20)")
def main(input, output, max_samples, map_types, zoom_levels):
    """Enrich NMDC Biosamples with AI interpretation of map images."""
    logger.info(f"Starting Biosample map interpretation from {input}")
    
    # Check for required API keys
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY environment variable not set")
        sys.exit(1)
    
    if not CBORG_API_KEY:
        logger.error("CBORG_API_KEY environment variable not set")
        sys.exit(1)
    
    # Parse map types and zoom levels
    map_type_list = [mt.strip() for mt in map_types.split(",")]
    zoom_level_list = [int(zl.strip()) for zl in zoom_levels.split(",")]
    
    # Load input file
    try:
        with open(input, 'r') as f:
            samples = json.load(f)
        logger.info(f"Loaded {len(samples)} samples from {input}")
    except Exception as e:
        logger.error(f"Error loading input file: {e}")
        sys.exit(1)
    
    # Limit samples if needed
    if max_samples and max_samples < len(samples):
        logger.info(f"Limiting to {max_samples} samples for processing")
        samples = samples[:max_samples]
    
    # Process samples
    enriched_samples = []
    for i, sample in enumerate(samples):
        logger.info(f"Processing sample {i+1}/{len(samples)}: {sample.get('id', 'unknown')}")
        
        # Check if the sample has coordinates
        lat_lon = sample.get("lat_lon")
        
        if lat_lon and isinstance(lat_lon, dict) and "latitude" in lat_lon and "longitude" in lat_lon:
            logger.info(f"Sample {sample.get('id', 'unknown')} has coordinates - enriching with map interpretation")
            enriched_sample = enrich_biosample_with_map_interpretation(
                sample, map_type_list, zoom_level_list
            )
            enriched_samples.append(enriched_sample)
        else:
            logger.info(f"Sample {sample.get('id', 'unknown')} missing coordinates - skipping")
            enriched_samples.append(sample)
    
    # Write output
    with open(output, 'w') as f:
        json.dump(enriched_samples, f, indent=2)
    logger.info(f"Wrote {len(enriched_samples)} enriched samples to {output}")
    
    # Summary statistics
    enriched_count = sum(1 for s in enriched_samples if "map_interpretations" in s)
    logger.info(f"Successfully enriched {enriched_count}/{len(enriched_samples)} samples with map interpretations")
    
    # List fields that were successfully inferred
    if enriched_count > 0:
        nmdc_term_counts = {
            "env_broad_scale": 0,
            "env_local_scale": 0,
            "env_medium": 0,
            "building_setting": 0,
            "cur_land_use": 0,
            "habitat": 0
        }
        
        for sample in enriched_samples:
            if "map_interpretations" in sample and "merged_environmental_factors" in sample["map_interpretations"]:
                for term, data in sample["map_interpretations"]["merged_environmental_factors"].items():
                    if data["term"] is not None:
                        nmdc_term_counts[term] += 1
        
        logger.info("Successfully inferred NMDC terms:")
        for term, count in nmdc_term_counts.items():
            if count > 0:
                logger.info(f"  {term}: {count}/{enriched_count} samples ({count/enriched_count*100:.1f}%)")

if __name__ == "__main__":
    main()