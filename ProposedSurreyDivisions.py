import requests
import json

# Base URL for the Existing_Division layer
BASE_URL = "https://services5.arcgis.com/F6GVRyx2cmmxgZzd/arcgis/rest/services/Surrey_Online/FeatureServer/6/query"

# Parameters for initial query
PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",  # WGS84
    "f": "geojson",
    "resultOffset": 0,
    "resultRecordCount": 1000  # Server limit per request
}

all_features = []

while True:
    print(f"Fetching records starting at offset {PARAMS['resultOffset']}...")
    response = requests.get(BASE_URL, params=PARAMS)
    data = response.json()

    features = data.get("features", [])
    all_features.extend(features)

    # If fewer features than requested, we are done
    if len(features) < PARAMS["resultRecordCount"]:
        break

    # Otherwise, increment offset to fetch next batch
    PARAMS["resultOffset"] += PARAMS["resultRecordCount"]

# Combine all features into a single FeatureCollection
geojson = {
    "type": "FeatureCollection",
    "features": all_features
}

# Save to file
with open("/Users/newbrie/Documents/ReformUK/GitHub/Reference/Boundaries/"+"Surrey_Proposed_Divisions.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print(f"Saved {len(all_features)} division features to Surrey_Existing_Divisions.geojson")
