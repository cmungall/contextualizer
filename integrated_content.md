# Contextualizer Project: Comprehensive Guide

## Table of Contents
1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [API Key Configuration](#api-key-configuration)
5. [Running Agents](#running-agents)
6. [Understanding and Using Agents](#understanding-and-using-agents)
7. [Troubleshooting](#troubleshooting)
8. [Running Tests](#running-tests)
9. [Code Style Guidelines](#code-style-guidelines)
10. [Project Status](#project-status)
11. [Vision Model Guidance](#vision-model-guidance)
12. [Function Summary](#function-summary)
13. [Geocoding Service Comparison](#geocoding-service-comparison)
14. [Google Maps API Monitoring](#google-maps-api-monitoring)
15. [Google Static Maps Zoom Levels](#google-static-maps-zoom-levels)
16. [Inferable Slots from Lat/Lon](#inferable-slots-from-latlon)
17. [Map Interpretation Analysis](#map-interpretation-analysis)
18. [Using OAK for Text Normalization](#using-oak-for-text-normalization)
19. [Development Log](#development-log)

## Project Overview

The Contextualizer project is an AI agent framework built on `pydantic-ai` that uses the Berkeley Lab's CBORG API to
access various language models. This guide combines official documentation, notes, and practical experience to help you
get started with the project.

## Prerequisites

- Python 3.10+ installed (3.10+ is specified in pyproject.toml)
- `uv` installed (a faster alternative to pip)
- CBORG API key (required for all agents)
- Google Maps API key (only required for map functionality in geo_agent.py)
- python-dotenv package (installed automatically as a dependency)

## Understanding The CBORG API

### What is CBORG?

CBORG is Berkeley Lab's AI Portal that provides secure access to various AI models. The CBORG API server is an
OpenAI-compatible proxy server built on LiteLLM, which means it can be used as a drop-in replacement for OpenAI's API.

### Available Models

The CBORG API provides access to various models. Based on testing, your account may have access to:

- **LBL-hosted models**:
    - lbl/cborg-chat:latest
    - lbl/cborg-vision:latest
    - lbl/nomic-embed-text

- **Commercial models**:
    - openai/gpt-4.1-nano
    - aws/claude-haiku
    - (potentially others)

Note that not all models listed in documentation may be available to your specific API key. You can use the test
connection script below to see which models are accessible to you.

## Environment Setup

### Install UV

```bash
# Install UV on Unix/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH if needed
```

### Create Virtual Environment

```bash
# Navigate to your repository
cd contextualizer

# Create a virtual environment with UV
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install development dependencies
uv pip install -e .
```

### Python Version Issues

The project requires Python 3.10+. If you're using pyenv and encounter version issues:

```bash
# Install Python 3.10 with pyenv
pyenv install 3.10

# Or remove .python-version file to use UV's Python directly
rm .python-version
```

## API Key Configuration

### Set Up Your CBORG API Key

You have several options:

1. **Create a .env file** (recommended):
   ```bash
   echo "CBORG_API_KEY=your_cborg_api_key_here
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here" > .env
   ```
   
   The project uses python-dotenv to load environment variables from this file.

2. **Export in your shell**:
   ```bash
   export CBORG_API_KEY="your_cborg_api_key_here"
   export GOOGLE_MAPS_API_KEY="your_google_maps_api_key_here"  # Only if using map functions
   ```

3. **Use the .venv/bin/python approach**:
   ```bash
   CBORG_API_KEY="your_cborg_api_key_here" .venv/bin/python your_script.py
   ```

### How to Get the CBORG API Key

- If affiliated with Berkeley Lab: CBORG is free for employees with @lbl.gov, @es.net, or @nersc.gov email.

## Running Agents

You can run any of the agents using the Makefile:

```bash
# Run the hello world example
make hello-world

# Run the geo agent
make geo

# Run the soil agent
make soil

# Run the weather agent
make weather

# Run the Wikipedia animal QA agent
make wiki
```

## Understanding and Using Agents

### Common Agent Structure

Most agents in this repository follow this pattern:

1. Load environment variables and API key (using python-dotenv)
2. Configure an AI model with the CBORG provider
3. Create an Agent with a system prompt
4. Register tools using decorators
5. Execute queries with the agent

### Agent Tools

Tools can be defined and registered using the `@agent.tool_plain` decorator, as shown in geo_agent.py:

```python
@geo_agent.tool_plain
def get_elev(
        lat: float, lon: float,
) -> float:
    """
    Get the elevation of a location.

    :param lat: latitude
    :param lon: longitude
    :return: elevation in m
    """
    print(f"Looking up elevation for lat={lat}, lon={lon}")
    return elevation((lat, lon))
```

### Available Agents

- **hello_world.py**: Simple "Hello World" example agent
- **geo_agent.py**: Geographic data agent (needs GOOGLE_MAPS_API_KEY for map functionality)
- **soil_agent.py**: Soil science agent
- **weather.at.py**: Weather information agent
- **wikipedia_animal_qa.py**: Wikipedia animal information agent
- **evelation_info.py**: Tool for elevation information (used by geo_agent)
- **envo_agent.py**: Agent for mapping OSM features to EnvO terms

## Troubleshooting

### Module Not Found Errors

If you see errors like: `ModuleNotFoundError: No module named 'agent_test'`:

1. Use the virtual environment Python directly (as configured in the Makefile):
   ```bash
   .venv/bin/python -m pytest tests/
   # or use the Makefile targets
   make test-agent
   make test-minimal
   ```

2. Or make sure you've activated the virtual environment:
   ```bash
   source .venv/bin/activate
   pytest tests/
   ```

### API Key Authentication Errors

If your CBORG API key isn't being loaded:

1. Check that your `.env` file exists and contains the correct key
2. Verify that python-dotenv is installed (it should be installed automatically with dependencies)
3. Ensure the .env file is in the root directory of the project

### Model Availability Errors

If you see errors related to model availability:

1. Update your agent code to use an available model (like "lbl/cborg-chat:latest")
2. Check the error message for specific details about the failure

## Running Tests

The repository includes tests in the `tests/` directory with corresponding targets in the `Makefile`:

```bash
# Run all tests
make test-agent test-minimal

# Run specific tests
make test-agent
make test-minimal
```

The Makefile uses `.venv/bin/pytest` to ensure the correct Python environment is used.

For more reliable testing, you can also run tests directly:

```bash
.venv/bin/pytest tests/test_agent.py -v
.venv/bin/pytest tests/test_minimal_agent.py -v
```

## Code Style Guidelines

The project follows these coding standards:

- **Imports**: Standard grouping (stdlib, third-party, local)
- **Type Annotations**: All functions should use Python type hints
- **Docstrings**: Multi-line docstring with params/returns (triple quotes)
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Error Handling**: Use try/except with logging, avoid silent failures
- **Tools**: Use @agent.tool_plain decorator for agent functions
- **Async**: Both sync and async functions are used; choose appropriately

## Project Status

### Current Focus
Working on enriching NMDC biosample metadata with geographical context by:
1. Validating asserted lat/lon coordinates against inferred coordinates
2. Extracting OpenStreetMap features for validated locations
3. Planning to map these features to EnvO terms

### Pipeline Components

#### 1. Data Acquisition
- Target: `make local/nmdc-biosamples.json`
- Downloads raw biosample data from NMDC API
- No processing at this stage

#### 2. Location Validation 
- Target: `make local/nmdc-latlon-inferred.json`
- Processes biosamples to:
  - Add inferred lat/lon from location names
  - Calculate distance between asserted and inferred coordinates
  - Add elevation data
  - Generate validation summary

#### 3. OSM Feature Extraction (Current Focus)
- Target: `make local/nmdc-osm-enriched.json`
- Only processes biosamples where:
  - Both asserted and inferred coordinates exist
  - Distance between coordinates is within 10km threshold
- Uses Overpass API to get nearby geographical features
- Includes retry logic and rate limiting

#### 4. EnvO Integration (Next Step)
- Just updated EnvO agent to use OAK properly
- Plan to map OSM features to EnvO terms
- Will use OAK for:
  - Term validation
  - Label lookup
  - Text annotation

### Next Steps
1. Test OSM feature extraction with real NMDC data
2. Refine feature relevance criteria
3. Complete EnvO term mapping
4. Add comparison of asserted vs inferred environmental context

## Vision Model Guidance

### Selected Model: Qwen 2.5 VL Instruct 72B (CBorg Vision)

**Vision Support:** Yes  
**Context Window:** 8,000 tokens  
**Minimum Image Size:** 256×256 pixels  
**Cost:** Free (locally hosted)

### Image Token Consumption Estimates

| Image Size       | Estimated Token Cost |
|------------------|----------------------|
| 256×256          | ~500–1,000 tokens    |
| 512×512          | ~2,000–3,000 tokens  |
| 1024×1024        | ~4,000–6,000 tokens  |

Token usage depends on:
- Image resolution
- Format (PNG/JPEG)
- Visual complexity (dense text increases cost)

### Prompt Size: "Half a Printed Page"

- Estimated text length: ~150–175 words
- Estimated token usage: **~300 tokens**
- Leaves **~7,700 tokens** for image + output

### Combined Use Feasibility

| Image Size       | Token Estimate | Safe With 300-Token Prompt? |
|------------------|----------------|------------------------------|
| 600×400          | ~1,000         | ✅ Yes                       |
| 800×600          | ~2,000         | ✅ Yes                       |
| 1024×768         | ~3,500         | ✅ Yes                       |
| 1600×1200        | ~6,000+        | ⚠️ Near limit                |
| 2048×2048        | ~8,000+        | ❌ Exceeds limit             |

### Recommendation

- For a 300-token instruction prompt:
  - Use **images up to ~1024×768** comfortably
  - Stay below **1600×1200** unless prompt/output is minimal
- 600×400 images are ideal for most tasks

## Function Summary

### API Key Requirements

- **CBORG_API_KEY**: Required for all agent operations (all files)
- **GOOGLE_MAPS_API_KEY**: Required only for map-related functions

### External Service Usage Limits

#### Nominatim Geocoder (used in weather.at.py)

- **Rate Limit**: Maximum 1 request per second
- **User Agent**: Required - set to 'EGSB Hackathon AI Agent toy' in weather.at.py
- **Production Use**: Not suitable for high-volume production without self-hosting
- **Implementation Notes**: No caching or rate limiting implemented in the code
- **Recommendation**: Implement request throttling for production use or consider self-hosting

### Function Categorization by Parameters

#### Functions with NO latitude/longitude parameters

| Function               | File                   | Parameters                            | API Keys Required |
|------------------------|------------------------|---------------------------------------|-------------------|
| `get_loc`              | weather.at.py          | location_string                       | CBORG_API_KEY     |
| `get_weather`          | weather.at.py          | location_string, start_date, end_date | CBORG_API_KEY     |
| `get_animal_info`      | wikipedia_animal_qa.py | ctx, animal_name                      | CBORG_API_KEY     |
| `get_animal_info_sync` | wikipedia_animal_qa.py | animal_name                           | CBORG_API_KEY     |
| `run_query`            | wikipedia_animal_qa.py | query                                 | CBORG_API_KEY     |
| `get_soil_ph_image`    | soil_agent.py          | west, south, east, north              | CBORG_API_KEY     |

#### Valid location_string examples for weather.at.py

- "Kalamazoo, Michigan"
- "Berkeley, California"
- "Paris, France"
- "1 Cyclotron Road, Berkeley, CA 94720"
- "Golden Gate Bridge, San Francisco"
- "Canada"
- "Tuscany, Italy"
- "94720, USA"

#### Functions with ONLY latitude/longitude parameters

| Function                  | File         | Parameters | API Keys Required |
|---------------------------|--------------|------------|-------------------|
| `get_elev`                | geo_agent.py | lat, lon   | CBORG_API_KEY     |
| `get_current_temperature` | geo_agent.py | lat, lon   | CBORG_API_KEY     |

#### Functions with latitude/longitude PLUS additional parameters

| Function                        | File         | Parameters                                             | API Keys Required                  |
|---------------------------------|--------------|--------------------------------------------------------|------------------------------------|
| `get_map_url`                   | maptools.py  | latitude, longitude, zoom, marker_color, maptype       | None                               |
| `get_static_map`                | maptools.py  | latitude, longitude, zoom, size, marker_color, maptype | GOOGLE_MAPS_API_KEY                |
| `fetch_map_image_and_interpret` | geo_agent.py | lat, lon, zoom, maptype                                | CBORG_API_KEY, GOOGLE_MAPS_API_KEY |
| `interpret_map_sync`            | geo_agent.py | lat, lon, zoom, maptype                                | GOOGLE_MAPS_API_KEY                |
| `get_location_features`         | geo_agent.py | lat, lon                                               | GOOGLE_MAPS_API_KEY                |
| `get_location_description`      | geo_agent.py | lat, lon                                               | CBORG_API_KEY, GOOGLE_MAPS_API_KEY |
| `execute_map_tool_directly`     | geo_agent.py | agent_response, lat, lon, zoom, maptype                | GOOGLE_MAPS_API_KEY                |
| `get_location_info`             | maptools.py  | latitude, longitude                                    | None                               |

## NMDC Biosample Fields as Function Inputs

The following fields from NMDC Biosample schema could be used as inputs to functions in this project:

### Latitude/Longitude Functions

**NMDC Field**: `lat_lon` (MIXS:0000009)

- **Description**: Geographic location as latitude and longitude in decimal degrees (WGS84)
- **Example**: `50.586825 6.408977`
- **Compatible Functions**:
    - `get_elev` (geo_agent.py)
    - `get_current_temperature` (geo_agent.py)
    - `get_location_description` (geo_agent.py)
    - `get_static_map` (maptools.py)
    - `get_map_url` (maptools.py)
    - Any other function requiring lat/lon coordinates

### Location Name Functions

**NMDC Field**: `geo_loc_name` (MIXS:0000010)

- **Description**: Geographic location as country/region
- **Example**: `USA: Maryland, Bethesda`
- **Compatible Functions**:
    - `get_loc` (weather.at.py) - to convert to coordinates
    - `get_weather` (weather.at.py) - for weather at location

### Other Potentially Useful NMDC Fields

- **`location`**: Generic location field
- **`sample_collection_site`**: Collection site description
- **`elev` (MIXS:0000093)**: Elevation in meters

### For Soil-Related Functions

The `geo_loc_name` field combined with soil properties (numerous in the schema) could be used with:

- `get_soil_ph_image` (soil_agent.py) - after conversion to bounding box coordinates

## Geocoding Service Comparison

### 🔍 Nominatim (OpenStreetMap)

#### ✅ Usage (Public instance)
- **Rate limit**:  
  - **1 request per second** per IP (strictly enforced)  
  - **No batch or bulk geocoding allowed**
- **User-Agent required**: Must include a valid `User-Agent` and ideally contact info (email)
- **Caching**: Required if you intend to repeatedly geocode the same queries

#### ❌ Restrictions
- **No heavy use**: Not for production/commercial use without hosting your own instance
- **No high-volume** automated use (e.g., large datasets)

#### ✅ Hosting Your Own Instance
- No usage limits (other than what your hardware/network can support)
- Requires ~40–60 GB for the planet data + RAM/CPU depending on region

### 🌍 Alternatives

#### ✅ Google Maps Geocoding API
- **Free**: 100 requests/day (after enabling billing)
- **Paid**: $5 per 1000 requests (first $200/month free = 40,000 requests/month)
- **Advantages**:
  - Highly accurate, global coverage
  - Reverse geocoding, autocomplete, place details
- **Limits**: 50 QPS by default (can request higher)

#### ✅ Mapbox Geocoding API
- **Free**: 100,000 requests/month
- **Paid**: Starts at $0.75 per 1000 requests
- **Great for**: Visual map integration, flexible plans

#### ✅ HERE Geocoding & Search API
- **Free**: 250,000 transactions/month with Freemium plan
- **Commercial**: Volume pricing available
- **Good for**: Batch geocoding, enterprise-grade use

#### ✅ Esri (ArcGIS) Geocoding
- Free limited use via developer accounts
- Commercial plans for enterprise
- Strong on address precision and parcel-level data (especially in US)

#### ✅ Positionstack
- Free tier: 25,000 requests/month
- Paid plans: Start at $9/month
- Offers both forward and reverse geocoding using OpenStreetMap and other sources

#### ✅ OpenCage
- Free: 2,500 requests/day
- Paid: From $50/month for 100,000 requests
- Built on OSM and other open data, includes confidence scores

### 🧭 Summary Comparison Table

| Provider        | Free Tier                        | Rate Limits             | Batch Support | Notes                              |
|----------------|----------------------------------|--------------------------|---------------|-------------------------------------|
| **Nominatim**   | Yes (1 rps, public instance)     | 1 rps/IP                 | ❌             | Must self-host for heavy use        |
| **Google Maps** | $200/month free (≈40,000 reqs)   | 50 QPS                   | ✅             | Very accurate, costly beyond free   |
| **Mapbox**      | 100,000 reqs/month               | Usage-based              | ✅             | Stylish maps, developer-friendly    |
| **HERE**        | 250,000/month (Freemium)         | Usage-based              | ✅             | Commercial-grade                    |
| **Esri**        | Limited via dev account          | Enterprise-focused       | ✅             | Excellent for US data               |
| **OpenCage**    | 2,500/day                        | Tier-based               | ✅             | Clean OSM-based API                 |
| **Positionstack** | 25,000/month                   | Tier-based               | ✅             | Lightweight, simple                 |

## Google Maps API Monitoring

You **can get fairly close to real-time monitoring** of your Google Maps Platform (and other Google Cloud) API usage and
costs, though there are some caveats. Here's a detailed breakdown of your options:

### 1. Google Cloud Console (Web Interface)

#### A. API Usage Monitoring

- **Go to:** [Google Cloud Console API Dashboard](https://console.cloud.google.com/apis/dashboard)
- **Features:**
    - See requests per API (e.g., Maps, Geocoding, Places, etc.).
    - Granular breakdown by method, per minute/hour/day.
    - Filter by project, time range, etc.
- **Latency:**
    - **Near real-time:** Data is usually updated within minutes, but sometimes up to a 5-15 minute delay.

#### B. Cost Monitoring

- **Go to:** [Google Cloud Billing Reports](https://console.cloud.google.com/billing)
- **Features:**
    - See cost per API, per project, per day.
    - Visual graphs, filters, and CSV export.
    - Set budgets and alerts.
- **Latency:**
    - **Not strictly real-time:** Typically updated every few hours, sometimes up to 24 hours for cost data.

### 2. Budgets and Alerts

- **Set up budgets:**
    - [Create a budget and alert](https://cloud.google.com/billing/docs/how-to/budgets)
    - Get email or Pub/Sub notifications when spending hits thresholds (e.g., 50%, 90%, 100% of budget).
- **Web Interface:**
    - Manage and view budgets/alerts in the Billing section.

### 3. Custom Dashboards (for More Real-Time Monitoring)

#### A. Cloud Monitoring (formerly Stackdriver)

- **Go to:** [Google Cloud Monitoring](https://console.cloud.google.com/monitoring)
- **Features:**
    - Create custom dashboards showing API usage metrics.
    - Use pre-built metrics or custom logs-based metrics.
    - Can get as granular as per-minute usage.
- **Latency:**
    - Data is generally available within minutes.

#### B. BigQuery Export (for Advanced Users)

- Export billing data to BigQuery for custom analysis and dashboards.
- Connect BigQuery to [Looker Studio](https://lookerstudio.google.com/) (formerly Data Studio) for web-based visual dashboards.
- **Latency:**
    - Exported data is typically updated multiple times a day, not strictly real-time.

### 4. API-Based Monitoring (for Automation)

- **Cloud Billing API:**
    - [Cloud Billing API](https://cloud.google.com/billing/docs/apis)
    - Programmatically get cost and usage data.
    - Integrate with your own web dashboard or monitoring tools.
    - **Note:** Cost data is not real-time, but usage metrics can be close.

- **Cloud Monitoring API:**
    - [Monitoring API](https://cloud.google.com/monitoring/api/ref_v3/rest)
    - Query metrics for API usage in near-real-time.

### Summary Table

| Method                      | Usage Data | Cost Data        | Web Interface?             | Real-Time?                             |
|-----------------------------|------------|------------------|----------------------------|----------------------------------------|
| Cloud Console API Dashboard | Yes        | No               | Yes                        | Near real-time (minutes)               |
| Cloud Console Billing       | No         | Yes              | Yes                        | Delayed (hours)                        |
| Cloud Monitoring            | Yes        | No               | Yes                        | Near real-time (minutes)               |
| Budgets/Alerts              | No         | Yes (thresholds) | Yes                        | Delayed (hours)                        |
| BigQuery Export + Looker    | Yes/Yes    | Yes/Yes          | Yes                        | Delayed (hours)                        |
| APIs (Billing/Monitoring)   | Yes        | Limited          | No (but you can build one) | Near real-time (usage), delayed (cost) |

### Recommended Approach

For most users **wanting a web interface and near real-time usage monitoring**:

1. **Use the [API Dashboard](https://console.cloud.google.com/apis/dashboard)** for per-API usage.
2. **Set up [Cloud Monitoring](https://console.cloud.google.com/monitoring) dashboards** for more granular, custom visualizations.
3. **Set up Budgets & Alerts** for cost overruns.
4. **Check Billing Reports** for cost, realizing it will lag by a few hours.
5. **(Optional)** Export billing data to BigQuery and visualize with Looker Studio for custom reports.

### Example: Monitoring Google Maps API Usage

1. **Go to Cloud Console > APIs & Services > Dashboard**
2. Select your project.
3. Filter for "Maps JavaScript API," "Geocoding API," etc.
4. View request counts, errors, latency, etc.

For more advanced, near-real-time dashboards (e.g., per-minute usage), use **Cloud Monitoring**:

- Go to Monitoring > Metrics Explorer.
- Search for "API request count" or relevant metric.
- Build a dashboard.

### Limitations

- **Usage metrics:** Near real-time (minutes).
- **Cost metrics:** Delayed (hours, sometimes up to a day).
- **No 100% real-time cost data** due to Google's billing pipeline.

## Google Static Maps Zoom Levels

### 1. Range of Zoom Levels for Google Static Maps

- **Zoom levels range from 0 (the whole world) to 21+ (building level)**, though the maximum available zoom depends on location and map type.
- **Typical range:**
  - **0:** Entire world in one tile
  - **21:** Individual buildings (in some places, especially urban areas)

### 2. Are All Zoom Levels Offered for All Map Types?

- **Map types:** `roadmap`, `satellite`, `terrain`, `hybrid`
- **Availability:**
  - **Roadmap:** Up to zoom 21 almost everywhere
  - **Satellite/Hybrid:** Up to zoom 21 in major cities; lower in rural/remote areas (sometimes maxes out at 18–19)
  - **Terrain:** Usually up to zoom 15; sometimes higher, but often limited
- **Not all zoom levels are available everywhere or for every map type.** If you request a zoom level that isn't available for a given location/map type, you may get a lower-resolution image or a blank tile.

### 3. What Do Zoom Levels Correspond To?

- **Zoom level** is a measure of scale, where each increment doubles the resolution (halves the visible area).
- **At zoom level N, the world is divided into 2^N × 2^N tiles.**
- **Scale at Equator:**
  - At **zoom 0:** the entire world fits in one 256x256 pixel tile
  - At **zoom 1:** the world is divided into 2x2 tiles
  - At **zoom 2:** 4x4 tiles, etc.
- **Ground Resolution (meters/pixel at Equator):**
  - Formula:  
    ```
    initial_resolution = 156543.03392 meters/pixel at zoom 0
    resolution = initial_resolution / 2^zoom
    ```
  - **Examples:**

    | Zoom | Meters/Pixel (Equator) | Map Width (km) |
    |------|------------------------|---------------|
    | 0    | ~156,543               | ~40,075       |
    | 5    | ~4,892                 | ~1,252        |
    | 10   | ~152                   | ~39           |
    | 15   | ~4.78                  | ~1.2          |
    | 20   | ~0.15                  | ~0.005        |

- **Scale and ground resolution** decrease with latitude (pixels represent less ground as you move toward the poles).

### Summary Table: Zoom Level vs. Ground Resolution (at Equator)

| Zoom | Meters/Pixel | Map Width (km) | Typical Map Type Max      |
|------|--------------|----------------|--------------------------|
| 0    | 156,543      | 40,075         | All                      |
| 5    | 4,892        | 1,252          | All                      |
| 10   | 152          | 39             | All                      |
| 15   | 4.78         | 1.2            | All, Terrain may limit   |
| 18   | 0.597        | 0.15           | Road/Sat, Terrain may limit |
| 21   | 0.0746       | 0.019          | Road/Sat (urban only)    |

### Key Points

- **Zoom levels:** 0–21 (practically, 0–21, but not all available everywhere)
- **Map types:** Roadmap and Satellite go highest; Terrain is often limited
- **Zoom = scale:** Each level doubles the detail (halves area shown)
- **Meters/pixel:** At zoom 21, ~7.5 cm/pixel at the equator

## Inferable Slots from Lat/Lon

This document outlines NMDC `Biosample` slots that can be inferred or approximated using reverse geocoding and map APIs such as Google Maps, OpenStreetMap, and related services.

### ✅ High Confidence Inference

These fields are **well supported** by general-purpose reverse geocoding.

| Slot | Description | Notes |
|------|-------------|-------|
| `geo_loc_name` | Geographic location name | ✅ Already implemented. |
| `elev` | Elevation in meters | ✅ Already implemented using elevation API or static DEM. |

### ⚖️ Shared Evaluations and Optimism

These slots are promising based on environmental context, even without climate or terrain APIs.

| Slot | Description | Notes |
|------|-------------|-------|
| `env_broad_scale` | Broad environmental context | Could be derived from biome or ecozone maps. |
| `env_local_scale` | Local habitat or land use | May be inferred from land cover or reverse geocoding detail (e.g., park, farm, industrial site). |
| `env_medium` | Environmental medium (soil, water, etc.) | Sometimes deducible from location context — e.g., near a lake, urban soil — but more uncertain. |

### 🧭 Moderate Confidence Inference

These slots may be estimated using **place names, land features, or proximity**.

| Slot | Description | Strategy |
|------|-------------|----------|
| `building_setting` | Urban/rural/industrial/etc. | Reverse geocoder "types" or address context can suggest setting. |
| `cur_land_use` | Current land use | Reverse geocode address or nearby feature (e.g., "farm", "park", "industrial site"). |
| `reservoir` | Nearby named reservoir | Use proximity to known waterbodies via map labels. |
| `habitat` | General environmental descriptor | Heuristically deduced from context (e.g., forest, grassland, desert). |
| `ecosystem`, `ecosystem_type`, `ecosystem_category`, `ecosystem_subtype`, `specific_ecosystem` | GOLD-controlled vocab | Requires a curated lookup table mapping geographic features or regions to expected GOLD terms. |
| `basin` | Watershed or catchment area | Use static shapefiles (e.g., USGS HUC polygons) to assign by spatial join. |

### 🚫 Low Confidence Inference

These fields require **specialized geological or subsurface data** not available in map APIs.

| Slot | Description | Limitation |
|------|-------------|------------|
| `arch_struc` | Aerospace structure | No reliable signal from reverse geocoding. |
| `sr_dep_env` | Depositional environment | Requires geologic maps. |
| `sr_geol_age` | Geological age | Subsurface knowledge needed. |
| `sr_kerog_type` | Kerogen type | Not observable via coordinates. |
| `sr_lithology` | Lithology | Requires geological data (e.g., rock type maps). |
| `cur_vegetation` | Specific vegetation | Hard to infer without satellite imagery or NDVI. |
| `water_feat_type`, `water_feat_size` | Nearby waterbody type and size | May appear in geocoding context but not detailed enough. |

### 🔧 Suggested APIs and Place Type Strategies

#### 🗺️ Google Maps Platform

- [**Reverse Geocoding API**](https://developers.google.com/maps/documentation/geocoding)
  - Returns place `types`, `formatted_address`, and optional bounding regions.
  - Examples of useful place types:  
    - `natural_feature` → lakes, mountains  
    - `park`, `campground` → `habitat`, `ecosystem_type`  
    - `industrial`, `premise`, `establishment` → `building_setting`  
    - `point_of_interest`, `university`, `airport` → useful for `cur_land_use`

- [**Elevation API**](https://developers.google.com/maps/documentation/elevation)  
  - Used for `elev` (already implemented)

#### 🌍 OpenStreetMap / Nominatim

- [Nominatim](https://nominatim.org/) can return structured address info (`farm`, `forest`, `industrial`, etc.)
- Place tags and `category` can assist with:
  - `building_setting`
  - `cur_land_use`
  - `ecosystem_*` (when paired with custom mapping)

#### 📦 Auxiliary Datasets

- USGS HUC shapefiles (for `basin`)
- ESA WorldCover, NLCD (land cover, if willing to precompute)
- Static GOLD mappings of place-to-ecosystem for heuristics

## Map Interpretation Analysis

### Summary of Results

The map interpretation approach successfully enriched NMDC Biosamples with environmental context information inferred from coordinates using AI vision models on Google Maps imagery.

### Key Metrics
- **Samples processed**: 10
- **Map images analyzed**: 41 (multiple views of each location)
- **Environmental fields inferred**: 6
- **Completion rate**: 100% for 5 fields, 90% for habitat
- **High confidence results**: 100% for 4 key fields

### Analysis of AI-Inferred Environmental Context

#### Strengths

1. **High field coverage**: Successfully inferred values for all 6 targeted environmental fields:
   - env_broad_scale (100% coverage, 100% high confidence)
   - env_local_scale (100% coverage, 100% high confidence)
   - env_medium (100% coverage, 0% high confidence)
   - building_setting (100% coverage, 100% high confidence)
   - cur_land_use (100% coverage, 100% high confidence)
   - habitat (90% coverage, 0% high confidence)

2. **Detailed interpretations**: AI provided rich environmental descriptions reflecting the true geographical context of each location.

3. **Multi-perspective analysis**: Using both satellite and roadmap views at different zoom levels (13 and 17) provided complementary information.

4. **Complete audit trail**: All map images and API responses were saved, enabling review and validation of the AI's interpretations.

#### Limitations

1. **Verbose descriptors**: Some extracted terms are sentences rather than concise classifications, making database integration challenging.

2. **Inconsistent term format**: The structure of inferred terms varies between samples - some have concise terms while others have paragraph-style descriptions.

3. **Non-standardized vocabulary**: The AI doesn't consistently use controlled vocabulary from environmental ontologies like ENVO.

4. **Uncertain environmental medium detection**: While env_medium has 100% coverage, all received "medium" confidence, suggesting this feature is harder to determine from images alone.

### Enhancement Opportunities

#### Map and Data Sources

1. **Additional map types**:
   - Terrain maps would highlight elevation changes and landforms
   - Land cover/land use maps would provide specialized ecological information
   - Hybrid maps would combine satellite imagery with labels

2. **More zoom levels**:
   - Very broad view (zoom 10) for regional biome context
   - Ultra-detailed view (zoom 19-20) for micro-habitat details

3. **Specialized environmental data sources**:
   - Integration with environmental datasets (soil, climate, etc.)
   - Access to ecological classification maps
   - Watershed and hydrological data

#### Model and Processing Improvements

1. **Multiple AI models**:
   - Use specialized environmental models if available
   - Implement consensus approach across multiple vision models
   - Assign different models to different aspects of interpretation

2. **Output standardization**:
   - Modify prompts to request concise, standardized terms
   - Add post-processing to map to controlled vocabularies
   - Implement confidence thresholds for accepting terms

### Conclusion

The AI interpretation of map images proves to be a viable approach for inferring environmental context from coordinates. The high completion rate and confidence levels demonstrate that this method can provide meaningful environmental characterization for biosamples.

To advance this approach for production use, the key priorities should be:

1. Adding specialized environmental map types beyond standard Google Maps
2. Standardizing outputs to conform with established environmental ontologies
3. Implementing additional validation against known environmental ground truth

This technique shows strong potential to enhance biosample metadata with rich environmental context, supporting more comprehensive ecological and bioscientific analysis.

## Using OAK for Text Normalization

### 1. Basic OAK Setup and Initialization

```python
from oaklib import get_adapter

# Initialize an OAK adapter for a specific ontology
# Format: "sqlite:obo:<ontology_name>"
envo_adapter = get_adapter("sqlite:obo:envo")
po_adapter = get_adapter("sqlite:obo:po")
# etc.
```

### 2. Core OAK Operations

#### Getting Labels from CURIEs

```python
# Simple label lookup
label = adapter.label('ENVO:01000813')  # Returns the rdfs:label for the CURIE

# Check if term is obsolete
is_obsolete = adapter.is_obsolete('ENVO:01000813')
```

#### Text Annotation with OAK

```python
from oaklib.datamodels.text_annotator import TextAnnotationConfiguration

# Configure annotation settings
config = TextAnnotationConfiguration()
config.match_whole_words_only = True  # Prevent partial word matches

# Annotate text
annotations = adapter.annotate_text('your text here', configuration=config)

# Process annotations
for annotation in annotations:
    print(f"Match: {annotation.match_string}")
    print(f"CURIE: {annotation.object_id}")
    print(f"Label: {annotation.object_label}")
    print(f"Position: {annotation.subject_start}-{annotation.subject_end}")
```

### 3. Working with Lexical Indexes

#### Loading/Creating Lexical Indexes

```python
from oaklib.utilities.lexical.lexical_indexer import (
    load_lexical_index,
    create_lexical_index,
    save_lexical_index
)

# Try loading existing index
LEX_INDEX_FILE = "expanded_envo_po_lexical_index.yaml"

try:
    lexical_index = load_lexical_index(LEX_INDEX_FILE)
except FileNotFoundError:
    # Create new index if file doesn't exist
    adapter = get_adapter("sqlite:obo:envo")
    lexical_index = create_lexical_index(adapter)
    # Save for future use
    save_lexical_index(lexical_index, LEX_INDEX_FILE)
```

#### Creating Element-to-Label Maps

```python
def build_element_to_label_map(lexical_index):
    """Extract CURIE to label mapping from lexical index."""
    index_data = lexical_index._as_dict
    element_to_label = {}
    
    for term, grouping in index_data["groupings"].items():
        for rel in grouping["relationships"]:
            if rel["predicate"] == "rdfs:label":
                element = rel["element"]
                label = rel["element_term"]
                element_to_label[element] = label
                
    return element_to_label
```

### 4. Text Annotation Best Practices

#### Filtering and Processing Annotations

```python
def filter_annotations(annotations, min_length=3):
    """Filter annotations based on quality criteria."""
    filtered = []
    for ann in annotations:
        # Skip too-short annotations
        if hasattr(ann, "subject_start") and hasattr(ann, "subject_end"):
            ann_length = ann.subject_end - ann.subject_start + 1
            if ann_length < min_length:
                continue
                
        # Ensure whole word matches for single words
        match_string = getattr(ann, "match_string", None)
        if match_string and " " not in match_string:
            if not is_true_whole_word_match(label, match_string):
                continue
                
        filtered.append(ann)
    return filtered

def is_true_whole_word_match(text, match_string):
    """Verify if match_string occurs as a complete word."""
    words = re.findall(r"\b\w+\b", text.lower())
    return match_string.lower() in words
```

#### Computing Annotation Coverage

```python
def compute_annotation_coverage(annotations, text_length):
    """Calculate what percentage of text is covered by annotations."""
    intervals = []
    for ann in annotations:
        if hasattr(ann, "subject_start") and hasattr(ann, "subject_end"):
            intervals.append((ann.subject_start, ann.subject_end))
            
    if not intervals or text_length == 0:
        return 0
        
    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    merged = []
    current_start, current_end = intervals[0]
    
    for start, end in intervals[1:]:
        if start <= current_end + 1:  # Adjacent or overlapping
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
            
    merged.append((current_start, current_end))
    
    total_covered = sum(end - start + 1 for start, end in merged)
    return total_covered / text_length
```

### 5. Supported Ontologies

The code shows support for many ontologies via SQLite backends. Here's a partial list:

```python
SUPPORTED_ONTOLOGIES = {
    "agro": "sqlite:obo:agro",
    "bco": "sqlite:obo:bco", 
    "chebi": "sqlite:obo:chebi",
    "envo": "sqlite:obo:envo",
    "po": "sqlite:obo:po",
    "uberon": "sqlite:obo:uberon",
    # Many more available
}
```

### 6. Error Handling and Best Practices

```python
def safe_oak_operation(curie, adapter):
    """Safely perform OAK operations with error handling."""
    try:
        label = adapter.label(curie)
        if label:
            try:
                obsolete = adapter.is_obsolete(curie)
            except Exception:
                obsolete = False
            return {
                "curie": curie,
                "label": label,
                "obsolete": obsolete
            }
    except Exception as e:
        print(f"Error processing {curie}: {str(e)}")
    return None
```

### Notes for LLMs

1. Always normalize CURIEs to use uppercase prefixes (e.g., 'ENVO:' not 'envo:')
2. Cache lexical indexes when possible to improve performance
3. Use whole word matching to avoid false positives in text annotation
4. Consider text length and annotation coverage when evaluating results
5. Handle obsolete terms appropriately in your application context
6. Be aware that some operations may require web API access (e.g., BioPortal)

## Development Log

Recent development work has focused on creating an EnvO agent using PydanticAI to map OpenStreetMap features to EnvO terms. The agent is designed to help standardize environmental feature mappings for NMDC biosamples.

The EnvO agent:
1. Takes OSM features as input
2. Uses the CBORG API to access language models
3. Maps the features to standardized EnvO terms
4. Provides confidence scores and reasoning
5. Returns structured data through Pydantic models

The pipeline for processing NMDC biosamples includes:
1. Fetching raw biosample data from the NMDC API
2. Validating and enriching location data (adding inferred coordinates and elevation)
3. Extracting OSM features for validated locations
4. Mapping these features to EnvO terms using the EnvO agent
5. Comparing the mapped terms to the original biosample metadata

Next steps include:
1. Testing the OSM feature extraction with real NMDC data
2. Refining the EnvO mapping process
3. Adding more validation checks for coordinates
4. Filtering for only high-confidence locations