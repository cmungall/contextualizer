#!/bin/bash

# Define the coordinates
LAT=35.97583846
LON=-84.2743123
RADIUS=2000

# Create the Overpass query
QUERY='[out:json][timeout:180];
(
  // Get all features with common environmental tags
  nwr["natural"](around:'$RADIUS','$LAT','$LON');
  nwr["waterway"](around:'$RADIUS','$LAT','$LON');
  nwr["water"](around:'$RADIUS','$LAT','$LON');
  nwr["landuse"](around:'$RADIUS','$LAT','$LON');
  nwr["geological"](around:'$RADIUS','$LAT','$LON');
  nwr["ecosystem"](around:'$RADIUS','$LAT','$LON');
  nwr["wetland"](around:'$RADIUS','$LAT','$LON');
  nwr["soil"](around:'$RADIUS','$LAT','$LON');
);
out body;'

# URL encode the query
ENCODED_QUERY=$(echo "$QUERY" | jq -sRr @uri)

# Make the request
curl -s "https://overpass-api.de/api/interpreter" \
  -d "data=$ENCODED_QUERY" \
  | jq '.elements[] | select(.tags != null) | .tags' \
  | jq -s 'group_by(keys) | map({tags: .[0] | keys, count: length})'