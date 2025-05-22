"""
OpenStreetMap feature extraction using Overpass API.

This module provides tools to query and analyze geographical and environmental features
from OpenStreetMap using the Overpass API. It focuses on features relevant to
environmental characterization of biosample collection sites.
"""

import json
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
import click
import requests
from dataclasses import dataclass
from time import sleep
from pathlib import Path
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_feature_types(config_path: Optional[str] = None) -> Dict[str, Set[str]]:
    """
    Load feature types from config file and flatten into tag sets.
    
    Args:
        config_path: Path to config file, defaults to osm_feature_types.json in same directory
        
    Returns:
        Dictionary mapping category names to sets of feature values
    """
    if config_path is None:
        config_path = Path(__file__).parent / "osm_feature_types.json"
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Flatten the hierarchical config into sets of values
    feature_types = {}
    for category, data in config.items():
        feature_types[category] = set()
        for subcategory in data["values"].values():
            feature_types[category].update(subcategory)
    
    return feature_types

# Load feature types from config
OSM_FEATURE_TAGS = load_feature_types()

@dataclass
class OSMFeature:
    """
    Represents a single OpenStreetMap environmental or geographical feature.
    
    Attributes:
        feature_id: Unique identifier from OSM
        feature_type: Type of feature (e.g., 'natural:water', 'wetland:marsh')
        tags: Dictionary of OSM tags associated with this feature
        geometry_type: Type of geometry ('node', 'way', or 'relation')
        coordinates: (latitude, longitude) tuple of feature center
        area: Area in square meters (if available)
    """
    feature_id: str
    feature_type: str
    tags: Dict[str, str]
    geometry_type: str
    coordinates: Tuple[float, float]
    area: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert feature to dictionary representation."""
        return {
            "id": self.feature_id,
            "type": self.feature_type,
            "coordinates": self.coordinates,
            "area": self.area,
            "environmental_tags": {
                k: v for k, v in self.tags.items()
                if k in OSM_FEATURE_TAGS
            }
        }

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points in meters.
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
        
    Returns:
        Distance in meters
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Earth radius in meters
    return c * r

def build_overpass_query(lat: float, lon: float, radius: float = 1000) -> str:
    """
    Build an Overpass API query for environmental features around a point.
    
    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        radius: Search radius in meters
        
    Returns:
        Overpass QL query string
    """
    # Build union of all environmental tag queries
    tag_queries = []
    for key, values in OSM_FEATURE_TAGS.items():
        for value in values:
            tag_queries.append(f'nwr["{key}"="{value}"](around:{radius},{lat},{lon});')
    
    # Combine into full query with longer timeout
    query = f"""
    [out:json][timeout:180];
    (
        {' '.join(tag_queries)}
    );
    out body center qt;  // qt: quadtile-sorted output for better area handling
    """
    return query

def get_feature_type(tags: Dict[str, str]) -> Optional[str]:
    """
    Determine the primary feature type from OSM tags.
    
    Args:
        tags: Dictionary of OSM tags
        
    Returns:
        Feature type string (e.g., 'natural:water') or None if no matching type
    """
    # Check each category in order of environmental relevance
    for category in [
        "natural", "water", "wetland", "landcover", "vegetation",
        "ecosystem", "geological", "soil", "landuse", "protected_area",
        "waterway", "agriculture", "climate"
    ]:
        if category in tags and tags[category] in OSM_FEATURE_TAGS.get(category, set()):
            return f"{category}:{tags[category]}"
    return None

def extract_coordinates(element: Dict) -> Tuple[float, float]:
    """Extract coordinates from an OSM element."""
    if "center" in element:
        return (element["center"]["lat"], element["center"]["lon"])
    elif "lat" in element and "lon" in element:
        return (element["lat"], element["lon"])
    else:
        raise ValueError(f"No coordinates found in element: {element}")

def query_osm_features(lat: float, lon: float, radius: float = 1000, 
                      max_retries: int = 3, retry_delay: int = 5) -> List[OSMFeature]:
    """Query OpenStreetMap features around a point using Overpass API."""
    query = build_overpass_query(lat, lon, radius)
    url = "https://overpass-api.de/api/interpreter"
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Querying OSM features at {lat}, {lon} (attempt {attempt + 1}/{max_retries})")
            response = requests.post(url, data={"data": query})
            response.raise_for_status()
            
            data = response.json()
            
            if "elements" not in data:
                logger.warning("No elements found in OSM response")
                return []
            
            features = []
            for element in data["elements"]:
                try:
                    if "tags" not in element:
                        continue
                        
                    feature_type = get_feature_type(element["tags"])
                    if not feature_type:
                        continue
                        
                    coordinates = extract_coordinates(element)
                    
                    # Try to get area if available
                    area = None
                    if "area" in element:
                        area = float(element["area"])
                    
                    feature = OSMFeature(
                        feature_id=str(element["id"]),
                        feature_type=feature_type,
                        tags=element["tags"],
                        geometry_type=element["type"],
                        coordinates=coordinates,
                        area=area
                    )
                    features.append(feature)
                    
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error processing element {element.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Found {len(features)} relevant features")
            return features
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                sleep(retry_delay)
                continue
            else:
                logger.error(f"All attempts failed: {e}")
                raise

def summarize_features(features: List[OSMFeature], center_lat: float, center_lon: float) -> Dict[str, Any]:
    """
    Summarize features by category with additional metadata.
    
    Args:
        features: List of OSMFeature objects
        center_lat: Latitude of query center
        center_lon: Longitude of query center
        
    Returns:
        Dictionary with feature summary and metadata
    """
    # Initialize summary with metadata
    summary = {
        "metadata": {
            "total_features": len(features),
            "query_coordinates": [center_lat, center_lon],
            "timestamp": datetime.now().isoformat(),
            "feature_type_counts": {}
        },
        "features": {}
    }
    
    # Group features by type
    for feature in features:
        category = feature.feature_type.split(":")[0]
        feature_type = feature.feature_type.split(":")[1]
        
        # Update type counts
        if category not in summary["metadata"]["feature_type_counts"]:
            summary["metadata"]["feature_type_counts"][category] = {}
        if feature_type not in summary["metadata"]["feature_type_counts"][category]:
            summary["metadata"]["feature_type_counts"][category][feature_type] = 0
        summary["metadata"]["feature_type_counts"][category][feature_type] += 1
        
        # Add feature details
        if category not in summary["features"]:
            summary["features"][category] = []
            
        # Calculate distance from center
        distance = calculate_distance(
            center_lat, center_lon,
            feature.coordinates[0], feature.coordinates[1]
        )
        
        feature_dict = feature.to_dict()
        feature_dict["distance_from_center"] = distance
        
        summary["features"][category].append(feature_dict)
    
    # Sort features by distance within each category
    for category in summary["features"]:
        summary["features"][category].sort(key=lambda x: x["distance_from_center"])
    
    return summary

@click.command()
@click.option('--lat', '--latitude', type=float, required=True,
              help='Latitude of the center point')
@click.option('--lon', '--longitude', type=float, required=True,
              help='Longitude of the center point')
@click.option('--radius', '-r', type=int, default=1000,
              help='Search radius in meters (default: 1000)')
@click.option('--output', '-o', type=click.Path(dir_okay=False),
              help='Output file for JSON results (optional)')
@click.option('--pretty/--no-pretty', default=True,
              help='Pretty print JSON output (default: True)')
@click.option('--config', type=click.Path(exists=True),
              help='Path to feature types config file (optional)')
def main(lat: float, lon: float, radius: int, output: Optional[str], 
         pretty: bool, config: Optional[str]):
    """
    Query OpenStreetMap features around a geographical point.
    
    This tool queries OpenStreetMap via the Overpass API to find geographical and
    environmental features around a specified point. Features are categorized by
    type and include distance from the center point.
    """
    try:
        # Load custom config if provided
        global OSM_FEATURE_TAGS
        if config:
            OSM_FEATURE_TAGS = load_feature_types(config)
        
        # Query features
        features = query_osm_features(lat, lon, radius=radius)
        
        # Summarize results
        summary = summarize_features(features, lat, lon)
        
        # Prepare JSON output
        json_opts = {'indent': 2} if pretty else {}
        json_str = json.dumps(summary, **json_opts)
        
        # Output results
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(json_str)
            click.echo(f"Results written to {output}")
        else:
            click.echo(json_str)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.ClickException(str(e))

if __name__ == "__main__":
    main()