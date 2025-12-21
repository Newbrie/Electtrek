import requests
import json

BASE_URL = "https://services5.arcgis.com/F6GVRyx2cmmxgZzd/arcgis/rest/services/Surrey_Online/FeatureServer/6/query"

PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "geojson",
    "resultOffset": 0,
    "resultRecordCount": 1000
}

all_features = []
feature_names = []

while True:
    print(f"Fetching records starting at offset {PARAMS['resultOffset']}...")
    response = requests.get(BASE_URL, params=PARAMS)
    data = response.json()

    features = data.get("features", [])
    all_features.extend(features)

    for feat in features:
        name = feat.get("properties", {}).get("Name")
        if name:
            feature_names.append(str(name))

    if len(features) < PARAMS["resultRecordCount"]:
        break

    PARAMS["resultOffset"] += PARAMS["resultRecordCount"]

geojson = {
    "type": "FeatureCollection",
    "features": all_features
}

base_path = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/Boundaries/"

with open(base_path + "Surrey_Proposed_Divisions.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

with open(base_path + "Surrey_Proposed_Divisions.txt", "w", encoding="utf-8") as f:
    for name in sorted(set(feature_names)):
        f.write(name + "\n")

print(data["features"][0]["properties"].keys())
print(f"Saved {len(all_features)} features")
print(f"Saved {len(set(feature_names))} feature names")
