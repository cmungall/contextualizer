# NMDC Biosample Location Context Project

## Current Focus
Working on enriching NMDC biosample metadata with geographical context by:
1. Validating asserted lat/lon coordinates against inferred coordinates
2. Extracting OpenStreetMap features for validated locations
3. Planning to map these features to EnvO terms

## Pipeline Components

### 1. Data Acquisition
- Target: `make local/nmdc-biosamples.json`
- Downloads raw biosample data from NMDC API
- No processing at this stage

### 2. Location Validation 
- Target: `make local/nmdc-latlon-inferred.json`
- Processes biosamples to:
  - Add inferred lat/lon from location names
  - Calculate distance between asserted and inferred coordinates
  - Add elevation data
  - Generate validation summary

### 3. OSM Feature Extraction (Current Focus)
- Target: `make local/nmdc-osm-enriched.json`
- Only processes biosamples where:
  - Both asserted and inferred coordinates exist
  - Distance between coordinates is within 10km threshold
- Uses Overpass API to get nearby geographical features
- Includes retry logic and rate limiting

### 4. EnvO Integration (Next Step)
- Just updated EnvO agent to use OAK properly
- Plan to map OSM features to EnvO terms
- Will use OAK for:
  - Term validation
  - Label lookup
  - Text annotation

## Current Status
1. Basic pipeline structure is working
2. Location validation is implemented
3. OSM feature extraction is working but needs testing
4. EnvO integration started but needs refinement

## Next Steps
1. Test OSM feature extraction with real NMDC data
2. Refine feature relevance criteria
3. Complete EnvO term mapping
4. Add comparison of asserted vs inferred environmental context

## Notes
- Using OAK (Ontology Access Kit) for EnvO operations
- SQLite backend provides caching of ontology data
- Rate limiting needed for both Overpass API and LLM calls