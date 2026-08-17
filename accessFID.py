import geopandas as gpd

print("📂 Re-building UK-ROADS.gpkg from source...")
gdf = gpd.read_file("path_to_raw_os_roads_data")

# Drop any manual FID/fid columns so GDAL auto-generates the internal SQLite primary key
for col in ['FID', 'fid', 'OBJECTID']:
    if col in gdf.columns:
        gdf = gdf.drop(columns=[col])

# Save cleanly to GeoPackage
gdf.to_file("UK-ROADS.gpkg", driver="GPKG", layer="uk_roads")
print("✅ UK-ROADS.gpkg rebuilt successfully!")
