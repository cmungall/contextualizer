import json
import time
import logging
import click
from math import radians, cos, sin, asin, sqrt
from geopy.geocoders import Nominatim
from nmdc_geoloc_tools import elevation as nmdc_elevation

import urllib.parse
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize geocoder and caches
geo = Nominatim(user_agent="NMDC Contextualizer Example")
latlon_cache = {}
elevation_cache = {}


def geojson_io_url(lat1, lon1, lat2, lon2):
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon1, lat1]},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon2, lat2]},
            },
        ],
    }
    url = "https://geojson.io/#data=data:application/json," + urllib.parse.quote(
        json.dumps(geojson)
    )
    return url


def get_coordinates_from_location(location_string):
    if not location_string:
        return None, None
    if location_string in latlon_cache:
        return latlon_cache[location_string]
    logger.info(f"Geocoding location: '{location_string}'")
    try:
        loc = geo.geocode(location_string)
        if loc is None:
            logger.warning(f"Could not geocode location: '{location_string}'")
            latlon_cache[location_string] = (None, None)
            return None, None
        logger.info(
            f"Found coordinates for '{location_string}': {loc.latitude}, {loc.longitude}"
        )
        latlon_cache[location_string] = (loc.latitude, loc.longitude)
        time.sleep(0.5)
        return loc.latitude, loc.longitude
    except Exception as e:
        logger.error(f"Error geocoding location '{location_string}': {e}")
        latlon_cache[location_string] = (None, None)
        return None, None


def enrich_biosample_with_inferred_latlon(sample):
    geo_loc_name = None
    if "geo_loc_name" in sample:
        if isinstance(sample["geo_loc_name"], dict):
            geo_loc_name = sample["geo_loc_name"].get("has_raw_value")
        elif isinstance(sample["geo_loc_name"], str):
            geo_loc_name = sample["geo_loc_name"]
    lat = lon = None
    if geo_loc_name:
        lat, lon = get_coordinates_from_location(geo_loc_name)
    if lat is not None and lon is not None:
        inferred = {
            "latitude": lat,
            "longitude": lon,
            "method": "geopy.Nominatim",
            "google_maps_url": f"https://www.google.com/maps?q={lat},{lon}",
        }
        asserted = sample.get("lat_lon")
        if (
            asserted
            and isinstance(asserted, dict)
            and "latitude" in asserted
            and "longitude" in asserted
        ):
            dist = haversine_distance(
                asserted["latitude"], asserted["longitude"], lat, lon
            )
            inferred["distance_from_asserted_meters"] = dist
            # Google Maps URL to show both pins
            asserted_lat = asserted["latitude"]
            asserted_lon = asserted["longitude"]
            inferred["google_maps_comparison_url"] = (
                f"https://www.google.com/maps/dir/{asserted_lat},{asserted_lon}/{lat},{lon}"
            )
            # geojson.io URL to show both pins
            inferred["geojson_io_url"] = geojson_io_url(
                asserted_lat, asserted_lon, lat, lon
            )
        sample["inferred_lat_lon"] = inferred
    return sample


def get_elevation_from_latlon(lat, lon):
    key = (lat, lon)
    if key in elevation_cache:
        return elevation_cache[key]
    try:
        elev = nmdc_elevation((lat, lon))
        elevation_cache[key] = elev
        time.sleep(0.1)
        return elev
    except Exception as e:
        logger.error(f"Error getting elevation for {lat}, {lon}: {e}")
        elevation_cache[key] = None
        return None


def enrich_biosample_with_inferred_elevation(sample):
    lat_lon = sample.get("lat_lon")
    lat = lon = None
    if lat_lon and isinstance(lat_lon, dict):
        lat = lat_lon.get("latitude")
        lon = lat_lon.get("longitude")
    if lat is not None and lon is not None:
        elev = get_elevation_from_latlon(lat, lon)
        if elev is not None:
            inferred = {
                "value": elev,
                "units": "meters",
                "method": "nmdc_geoloc_tools.elevation",
            }
            reported = sample.get("elev")
            if reported is not None:
                denom = max(abs(elev), abs(reported))
                percent_diff = abs(elev - reported) / denom * 100 if denom != 0 else 0
                inferred["percent_difference_from_asserted"] = percent_diff
            sample["inferred_elevation"] = inferred
    return sample


def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # meters
    return c * r


def compute_latlon_distances(samples):
    distances = []
    sample_ids = []
    for sample in samples:
        asserted = sample.get("lat_lon")
        inferred = sample.get("inferred_lat_lon")
        if (
            asserted
            and inferred
            and isinstance(asserted, dict)
            and isinstance(inferred, dict)
            and "latitude" in asserted
            and "longitude" in asserted
            and "latitude" in inferred
            and "longitude" in inferred
        ):
            d = haversine_distance(
                asserted["latitude"],
                asserted["longitude"],
                inferred["latitude"],
                inferred["longitude"],
            )
            distances.append(d)
            sample_ids.append(sample.get("id"))
    return distances, sample_ids


def compute_elevation_percent_diffs(samples):
    percent_diffs = []
    sample_ids = []
    for sample in samples:
        inferred = sample.get("inferred_elevation", {}).get("value")
        reported = sample.get("elev")
        if inferred is not None and reported is not None:
            denom = max(abs(inferred), abs(reported))
            percent_diff = abs(inferred - reported) / denom * 100 if denom != 0 else 0
            percent_diffs.append(percent_diff)
            sample_ids.append(sample.get("id"))
    return percent_diffs, sample_ids


def make_bins_and_labels(values, n_bins, unit):
    if not values:
        return [], []
    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        bin_edges = [min_val, max_val]
    else:
        bin_edges = [
            min_val + i * (max_val - min_val) / n_bins for i in range(n_bins + 1)
        ]
    bin_labels = [
        f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}{unit}"
        for i in range(len(bin_edges) - 1)
    ]
    return bin_edges, bin_labels


def count_bins(values, bin_edges, bin_labels):
    bin_counts = {label: 0 for label in bin_labels}
    for v in values:
        for i, label in enumerate(bin_labels):
            left = bin_edges[i]
            right = bin_edges[i + 1]
            if (i < len(bin_labels) - 1 and left <= v < right) or (
                i == len(bin_labels) - 1 and left <= v <= right
            ):
                bin_counts[label] += 1
                break
    return bin_counts


def generate_latlon_inference_summary(samples, n_bins=5):
    distances, sample_ids = compute_latlon_distances(samples)
    bin_edges, bin_labels = make_bins_and_labels(distances, n_bins, unit="m")
    bin_counts = count_bins(distances, bin_edges, bin_labels) if distances else {}
    summary = {
        "total_samples": len(samples),
        "samples_with_asserted_and_inferred_lat_lon": len(distances),
        "max_latlon_distance": {
            "value": max(distances) if distances else None,
            "sample_id": (
                sample_ids[distances.index(max(distances))] if distances else None
            ),
        },
        "latlon_distance_bins": bin_counts,
    }
    return summary


def generate_elevation_inference_summary(samples, n_bins=5):
    percent_diffs, sample_ids = compute_elevation_percent_diffs(samples)
    bin_edges, bin_labels = make_bins_and_labels(percent_diffs, n_bins, unit="%")
    bin_counts = (
        count_bins(percent_diffs, bin_edges, bin_labels) if percent_diffs else {}
    )
    summary = {
        "total_samples": len(samples),
        "samples_with_inferred_and_reported": len(percent_diffs),
        "max_inferred_percent_difference": {
            "value": max(percent_diffs) if percent_diffs else None,
            "sample_id": (
                sample_ids[percent_diffs.index(max(percent_diffs))]
                if percent_diffs
                else None
            ),
        },
        "inferred_percent_difference_bins": bin_counts,
    }
    return summary


@click.command()
@click.option("--biosample-id", help="Biosample ID to select")
@click.option("--random-n", type=int, help="Randomly select N biosamples")
@click.option(
    "--input",
    default="local/nmdc-biosamples.json",
    show_default=True,
    help="Path to biosamples JSON file",
)
@click.option(
    "--add-inferred-latlon",
    is_flag=True,
    help="Add inferred lat/lon data to biosamples",
)
@click.option(
    "--add-inferred-elevation",
    is_flag=True,
    help="Add inferred elevation data to biosamples",
)
@click.option(
    "--output", help="Path to save the enriched output JSON (defaults to stdout)"
)
@click.option(
    "--summary-output",
    help="Path to save the summary JSON (if specified, summary is generated)",
)
@click.option(
    "--distance-bins",
    type=int,
    default=5,
    show_default=True,
    help="Number of bins for lat/lon distance reporting",
)
@click.option(
    "--percent-bins",
    type=int,
    default=5,
    show_default=True,
    help="Number of bins for inferred percent difference reporting",
)
def main(
    biosample_id,
    random_n,
    input,
    add_inferred_latlon,
    add_inferred_elevation,
    output,
    summary_output,
    distance_bins,
    percent_bins,
):
    """Infer lat/lon from geo_loc_name and/or elevation from asserted lat/lon. Output enriched samples and summary."""
    with open(input) as f:
        data = json.load(f)

    samples = (
        data.get("resources", [])
        if isinstance(data, dict) and "resources" in data
        else data if isinstance(data, list) else []
    )

    # Filter by ID or random N if requested
    if biosample_id:
        samples = [s for s in samples if s.get("id") == biosample_id]
    elif random_n:
        import random

        if random_n > len(samples):
            raise click.ClickException(
                f"Requested {random_n} samples, but only {len(samples)} available."
            )
        samples = random.sample(samples, random_n)

    processed_samples = []
    for sample in samples:
        if add_inferred_latlon:
            sample = enrich_biosample_with_inferred_latlon(sample)
        if add_inferred_elevation:
            sample = enrich_biosample_with_inferred_elevation(sample)
        processed_samples.append(sample)

    # Write enriched samples
    if output:
        with open(output, "w") as f:
            json.dump(processed_samples, f, indent=2)
    else:
        click.echo(json.dumps(processed_samples, indent=2))

    # Write summary (only for the tasks performed)
    if summary_output:
        summary_data = {}
        if add_inferred_latlon:
            summary_data["latlon_inference_summary"] = (
                generate_latlon_inference_summary(
                    processed_samples, n_bins=distance_bins
                )
            )
        if add_inferred_elevation:
            summary_data["elevation_inference_summary"] = (
                generate_elevation_inference_summary(
                    processed_samples, n_bins=percent_bins
                )
            )
        with open(summary_output, "w") as f:
            json.dump(summary_data, f, indent=2)


if __name__ == "__main__":
    main()
