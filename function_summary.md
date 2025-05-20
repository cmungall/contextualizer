# Contextualizer Functions Summary

## API Key Requirements

- **CBORG_API_KEY**: Required for all agent operations (all files)
- **GOOGLE_MAPS_API_KEY**: Required only for map-related functions

## External Service Usage Limits

### Nominatim Geocoder (used in weather.at.py)

- **Rate Limit**: Maximum 1 request per second
- **User Agent**: Required - set to 'EGSB Hackathon AI Agent toy' in weather.at.py
- **Production Use**: Not suitable for high-volume production without self-hosting
- **Implementation Notes**: No caching or rate limiting implemented in the code
- **Recommendation**: Implement request throttling for production use or consider self-hosting

## Function Categorization by Parameters

### Functions with NO latitude/longitude parameters

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

### Functions with ONLY latitude/longitude parameters

| Function                  | File         | Parameters | API Keys Required |
|---------------------------|--------------|------------|-------------------|
| `get_elev`                | geo_agent.py | lat, lon   | CBORG_API_KEY     |
| `get_current_temperature` | geo_agent.py | lat, lon   | CBORG_API_KEY     |

### Functions with latitude/longitude PLUS additional parameters

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

----

https://api.microbiomedata.org/nmdcschema/collection_stats

```json
  {
  "ns": "nmdc.biosample_set",
  "storageStats": {
    "size": 24174326,
    "count": 13006,
    "avgObjSize": 1858,
    "storageSize": 4120576,
    "totalIndexSize": 2904064,
    "totalSize": 7024640,
    "scaleFactor": 1
  }
}
```

For which GCP Projects owned by LBL is MAM@lbl.gov the owner?

```shell
gcloud projects list \
  --filter="lifecycleState:ACTIVE" \
  --format="value(projectId)" | while read -r PROJECT_ID; do
    POLICY=$(gcloud projects get-iam-policy "$PROJECT_ID" --flatten="bindings[].members" \
        --filter="bindings.role=roles/owner AND bindings.members:user:MAM@lbl.gov" \
        --format="value(bindings.members)" 2>/dev/null)
    if [[ -n "$POLICY" ]]; then
      echo "$PROJECT_ID"
    fi
done
```

* env-context-voting-sheets
* nmdc-geocoding

----

* List all accessible projects: `gcloud projects list`
    * ~ 7000 for MAM@lbl.gov
* Check active project: `gcloud config list project`
* Switch active project: `gcloud config set project PROJECT_ID`
* Set Application Default Credentials (ADC) quota project:
  `gcloud auth application-default set-quota-project PROJECT_ID`
    * _Requires roles/serviceusage.serviceUsageConsumer on the target project._
* Check if a project has billing enabled: `gcloud beta billing projects describe PROJECT_ID`
* List enabled APIs for a project: `gcloud services list --enabled --project=PROJECT_ID`

For both `env-context-voting-sheets` and `nmdc-geocoding`

> billingAccountName: ''
> billingEnabled: false

### env-context-voting-sheets

| NAME                                | TITLE                    |
|-------------------------------------|--------------------------|
| analyticshub.googleapis.com         | Analytics Hub API        |
| bigquery.googleapis.com             | BigQuery API             |
| bigqueryconnection.googleapis.com   | BigQuery Connection API  |
| bigquerydatapolicy.googleapis.com   | BigQuery Data Policy API |
| bigquerymigration.googleapis.com    | BigQuery Migration API   |
| bigqueryreservation.googleapis.com  | BigQuery Reservation API |
| bigquerystorage.googleapis.com      | BigQuery Storage API     |
| cloudapis.googleapis.com            | Google Cloud APIs        |
| cloudresourcemanager.googleapis.com | Cloud Resource Manager A |
| cloudtrace.googleapis.com           | Cloud Trace API          |
| dataform.googleapis.com             | Dataform API             |
| dataplex.googleapis.com             | Cloud Dataplex API       |
| datastore.googleapis.com            | Cloud Datastore API      |
| drive.googleapis.com                | Google Drive API         |
| logging.googleapis.com              | Cloud Logging API        |
| monitoring.googleapis.com           | Cloud Monitoring API     |
| servicemanagement.googleapis.com    | Service Management API   |
| serviceusage.googleapis.com         | Service Usage API        |
| sheets.googleapis.com               | Google Sheets API        |
| sql-component.googleapis.com        | Cloud SQL                |
| storage-api.googleapis.com          | Google Cloud Storage JSO |
| storage-component.googleapis.com    | Cloud Storage            |
| storage.googleapis.com              | Cloud Storage API        |
| websecurityscanner.googleapis.com   | Web Security Scanner API |

### nmdc-geocoding

| NAME                                | TITLE                         |
|-------------------------------------|-------------------------------|
| bigquery.googleapis.com             | BigQuery API                  |
| bigquerymigration.googleapis.com    | BigQuery Migration API        |
| bigquerystorage.googleapis.com      | BigQuery Storage API          |
| cloudapis.googleapis.com            | Google Cloud APIs             |
| cloudresourcemanager.googleapis.com | Cloud Resource Manager API    |
| cloudtrace.googleapis.com           | Cloud Trace API               |
| datacatalog.googleapis.com          | Google Cloud Data Catalog API |
| dataform.googleapis.com             | Dataform API                  |
| dataplex.googleapis.com             | Cloud Dataplex API            |
| datastore.googleapis.com            | Cloud Datastore API           |
| drive.googleapis.com                | Google Drive API              |
| logging.googleapis.com              | Cloud Logging API             |
| maps-backend.googleapis.com         | Maps JavaScript API           |
| monitoring.googleapis.com           | Cloud Monitoring API          |
| servicemanagement.googleapis.com    | Service Management API        |
| serviceusage.googleapis.com         | Service Usage API             |
| sheets.googleapis.com               | Google Sheets API             |
| sql-component.googleapis.com        | Cloud SQL                     |
| storage-api.googleapis.com          | Google Cloud Storage JSON API |
| storage-component.googleapis.com    | Cloud Storage                 |
| storage.googleapis.com              | Cloud Storage API             |
| visionai.googleapis.com             | Vision AI API                 |
| websecurityscanner.googleapis.com   | Web Security Scanner API      |

| API Name                          | env-context-voting-sheets | nmdc-geocoding |
|-----------------------------------|---------------------------|----------------|
| analyticshub.googleapis.com       | ✔️                        |                |
| bigqueryconnection.googleapis.com | ✔️                        |                |
| bigquerydatapolicy.googleapis.com | ✔️                        |                |
| datacatalog.googleapis.com        |                           | ✔️             |
| maps-backend.googleapis.com       |                           | ✔️             |
| visionai.googleapis.com           |                           | ✔️             |

1. Google Maps Static API

- Used in get_static_map() function in maptools.py
- Endpoint: https://maps.googleapis.com/maps/api/staticmap
- Purpose: Fetches satellite or road maps as static images
- Parameters: center coordinates, zoom level, image size, marker color, map type

2. Google Maps Javascript API (indirectly referenced)

- Used to generate URLs in get_map_url() function in maptools.py
- Returns a URL like https://www.google.com/maps/@{latitude},{longitude},{zoom}z/data=!3m1!1e3
- Purpose: Generates a link that users can click to view a location in Google Maps
- This doesn't directly call the API with the key, but constructs a URL to Google Maps

The GOOGLE_MAPS_API_KEY is used in the following functions:

1. Direct use (API calls):

- get_static_map() in maptools.py (line 30) - Makes a direct API call to Google Maps Static API

2. Checking for API key availability:

- get_location_info() in maptools.py (line 139) - Checks if the API key is present
- interpret_map_sync() in geo_agent.py (line 129) - Checks if API key exists before trying to get a map

3. Functions that indirectly require the API key (by calling other functions):

- fetch_map_image_and_interpret() - Calls interpret_map_sync()
- get_location_features() - Makes multiple calls to interpret_map_sync()
- execute_map_tool_directly() - Calls interpret_map_sync()
- get_location_description() - Calls get_location_features()
