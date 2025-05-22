"""
Enrich NMDC biosamples with OpenStreetMap geographical features.

This script processes NMDC biosamples that have latitude/longitude coordinates,
querying OpenStreetMap via Overpass API to obtain geographical and environmental
features near each sample location. These features can be used to validate or
enhance the environmental context of the biosamples.

Only processes samples where:
1. They have both asserted and inferred coordinates
2. The distance between asserted and inferred coordinates is within a specified threshold
"""

import json
import logging
import click
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tqdm import tqdm
from time import sleep
from agent_test.osm_features import query_osm_features, summarize_features

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sample_coordinates(biosample: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Extract both asserted and inferred coordinates from a biosample.
    
    Returns:
        Tuple of (asserted_lat, asserted_lon, inferred_lat, inferred_lon)
        Any coordinate pair may be (None, None) if not available
    """
    asserted_lat = asserted_lon = inferred_lat = inferred_lon = None
    
    # Get asserted coordinates
    lat_lon = biosample.get('lat_lon', {})
    if isinstance(lat_lon, dict):
        try:
            asserted_lat = float(lat_lon.get('latitude'))
            asserted_lon = float(lat_lon.get('longitude'))
        except (TypeError, ValueError):
            pass
            
    # Get inferred coordinates
    inferred = biosample.get('inferred_lat_lon', {})
    if isinstance(inferred, dict):
        try:
            inferred_lat = float(inferred.get('latitude'))
            inferred_lon = float(inferred.get('longitude'))
        except (TypeError, ValueError):
            pass
            
    return asserted_lat, asserted_lon, inferred_lat, inferred_lon

def check_coordinate_confidence(biosample: Dict[str, Any], max_distance_meters: float) -> bool:
    """
    Check if a biosample's coordinates meet our confidence threshold.
    
    Args:
        biosample: Dictionary containing biosample metadata
        max_distance_meters: Maximum allowed distance between asserted and inferred coordinates
        
    Returns:
        bool: True if coordinates are within confidence threshold
    """
    # Get both coordinate pairs
    asserted_lat, asserted_lon, inferred_lat, inferred_lon = get_sample_coordinates(biosample)
    
    # Skip if either pair is missing
    if None in (asserted_lat, asserted_lon, inferred_lat, inferred_lon):
        logger.info(f"Skipping biosample {biosample.get('id')} - missing coordinates")
        return False
        
    # Get distance if already calculated
    inferred = biosample.get('inferred_lat_lon', {})
    if isinstance(inferred, dict) and 'distance_from_asserted_meters' in inferred:
        distance = float(inferred['distance_from_asserted_meters'])
    else:
        logger.info(f"Skipping biosample {biosample.get('id')} - no distance calculation")
        return False
        
    # Check against threshold
    if distance > max_distance_meters:
        logger.info(
            f"Skipping biosample {biosample.get('id')} - "
            f"distance {distance:.1f}m exceeds threshold {max_distance_meters}m"
        )
        return False
        
    return True

def process_biosample(biosample: Dict[str, Any], radius: int = 1000) -> Dict[str, Any]:
    """
    Process a single biosample to add OSM features.
    
    Args:
        biosample: Dictionary containing biosample metadata with lat/lon
        radius: Search radius in meters for geographical features
        
    Returns:
        Biosample dictionary enriched with OSM features
    """
    # Extract coordinates from asserted lat/lon
    lat_lon = biosample.get('lat_lon', {})
    try:
        lat = float(lat_lon['latitude'])
        lon = float(lat_lon['longitude'])
    except (KeyError, TypeError, ValueError):
        logger.warning(f"Missing or invalid coordinates for biosample {biosample.get('id')}")
        return biosample
    
    # Query OSM features
    try:
        # Query OSM features
        features = query_osm_features(lat, lon, radius=radius)
        feature_summary = summarize_features(features, lat, lon)
        
        # Add raw features to biosample metadata
        enriched = biosample.copy()
        enriched['osm_features'] = feature_summary
        return enriched
        
    except Exception as e:
        logger.error(f"Error processing biosample {biosample.get('id')}: {e}")
        return biosample

@click.command()
@click.option('--input', '-i', 'input_path', type=click.Path(exists=True), required=True,
              help='Input JSON file containing NMDC biosamples with lat/lon')
@click.option('--output', '-o', 'output_path', type=click.Path(), required=True,
              help='Output path for enriched biosamples JSON')
@click.option('--radius', '-r', type=int, default=1000,
              help='Search radius in meters for geographical features (default: 1000)')
@click.option('--max-distance', '-d', type=float, default=10000,
              help='Maximum allowed distance in meters between asserted and inferred coordinates (default: 10000)')
@click.option('--max-samples', type=int, default=None,
              help='Maximum number of samples to process (default: all)')
def main(input_path: str, output_path: str, radius: int, max_distance: float, max_samples: int):
    """
    Process NMDC biosamples to add geographical features from OpenStreetMap.
    Only processes samples where asserted and inferred coordinates are within
    the specified distance threshold.
    """
    # Load input data
    logger.info(f"Loading biosamples from {input_path}")
    with open(input_path) as f:
        biosamples = json.load(f)
    
    if isinstance(biosamples, dict) and 'biosamples' in biosamples:
        biosamples = biosamples['biosamples']
    
    # Filter samples by coordinate confidence
    confident_samples = [
        sample for sample in biosamples 
        if check_coordinate_confidence(sample, max_distance)
    ]
    
    logger.info(
        f"Found {len(confident_samples)} samples with confident coordinates "
        f"(within {max_distance}m) out of {len(biosamples)} total samples"
    )
    
    if max_samples:
        confident_samples = confident_samples[:max_samples]
    
    logger.info(f"Processing {len(confident_samples)} biosamples")
    
    # Process each biosample
    enriched_samples = []
    skipped_samples = []
    
    for sample in tqdm(confident_samples):
        enriched = process_biosample(sample, radius=radius)
        if 'osm_features' in enriched:
            enriched_samples.append(enriched)
        else:
            skipped_samples.append(sample.get('id'))
        sleep(1)  # Rate limiting for Overpass API
    
    # Save results
    output_data = {
        'biosamples': enriched_samples,
        'metadata': {
            'total_input_samples': len(biosamples),
            'confident_coordinate_samples': len(confident_samples),
            'successfully_enriched_samples': len(enriched_samples),
            'skipped_samples': skipped_samples,
            'coordinate_confidence_threshold_meters': max_distance,
            'feature_radius_meters': radius
        }
    }
    
    logger.info(f"Writing results to {output_path}")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

if __name__ == '__main__':
    main()