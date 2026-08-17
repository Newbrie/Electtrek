import geopandas as gpd

# Inspect only the first row to read column names and data types
gdf = gpd.read_file("UK-ROADS.gpkg", rows=1)

print("🔍 Columns found in UK-ROADS.gpkg:")
for col in gdf.columns:
    print(f"  - {col}")

print("\n📋 Sample Feature:")
print(gdf.head(1).T)
