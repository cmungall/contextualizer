
# 📍 Inference of NMDC Biosample Fields from Latitude and Longitude

This document outlines NMDC `Biosample` slots that can be inferred or approximated using reverse geocoding and map APIs such as Google Maps, OpenStreetMap, and related services.

---

## ✅ High Confidence Inference

These fields are **well supported** by general-purpose reverse geocoding.

| Slot | Description | Notes |
|------|-------------|-------|
| `geo_loc_name` | Geographic location name | ✅ Already implemented. |
| `elev` | Elevation in meters | ✅ Already implemented using elevation API or static DEM. |

---

## ⚖️ Shared Evaluations and Optimism

These slots are promising based on environmental context, even without climate or terrain APIs.

| Slot | Description | Notes |
|------|-------------|-------|
| `env_broad_scale` | Broad environmental context | Could be derived from biome or ecozone maps. |
| `env_local_scale` | Local habitat or land use | May be inferred from land cover or reverse geocoding detail (e.g., park, farm, industrial site). |
| `env_medium` | Environmental medium (soil, water, etc.) | Sometimes deducible from location context — e.g., near a lake, urban soil — but more uncertain. |

---

## 🧭 Moderate Confidence Inference

These slots may be estimated using **place names, land features, or proximity**.

| Slot | Description | Strategy |
|------|-------------|----------|
| `building_setting` | Urban/rural/industrial/etc. | Reverse geocoder “types” or address context can suggest setting. |
| `cur_land_use` | Current land use | Reverse geocode address or nearby feature (e.g., "farm", "park", "industrial site"). |
| `reservoir` | Nearby named reservoir | Use proximity to known waterbodies via map labels. |
| `habitat` | General environmental descriptor | Heuristically deduced from context (e.g., forest, grassland, desert). |
| `ecosystem`, `ecosystem_type`, `ecosystem_category`, `ecosystem_subtype`, `specific_ecosystem` | GOLD-controlled vocab | Requires a curated lookup table mapping geographic features or regions to expected GOLD terms. |
| `basin` | Watershed or catchment area | Use static shapefiles (e.g., USGS HUC polygons) to assign by spatial join. |

---

## 🚫 Low Confidence Inference

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

---

## 🔧 Suggested APIs and Place Type Strategies

### 🗺️ Google Maps Platform

- [**Reverse Geocoding API**](https://developers.google.com/maps/documentation/geocoding)
  - Returns place `types`, `formatted_address`, and optional bounding regions.
  - Examples of useful place types:  
    - `natural_feature` → lakes, mountains  
    - `park`, `campground` → `habitat`, `ecosystem_type`  
    - `industrial`, `premise`, `establishment` → `building_setting`  
    - `point_of_interest`, `university`, `airport` → useful for `cur_land_use`

- [**Elevation API**](https://developers.google.com/maps/documentation/elevation)  
  - Used for `elev` (already implemented)

### 🌍 OpenStreetMap / Nominatim

- [Nominatim](https://nominatim.org/) can return structured address info (`farm`, `forest`, `industrial`, etc.)
- Place tags and `category` can assist with:
  - `building_setting`
  - `cur_land_use`
  - `ecosystem_*` (when paired with custom mapping)

### 📦 Auxiliary Datasets

- USGS HUC shapefiles (for `basin`)
- ESA WorldCover, NLCD (land cover, if willing to precompute)
- Static GOLD mappings of place-to-ecosystem for heuristics

---

Let me know if you'd like this integrated into a script, or if you'd like a mapping table from Google types or OSM features to GOLD ecosystem terms.
