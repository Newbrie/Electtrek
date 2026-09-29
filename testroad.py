
import geopandas as gpd

gdf_sample = gpd.read_file("/Users/newbrie/Documents/ReformUK/Github/Reference/Boundaries/UK-ROADS.gpkg", rows=3)

# Exclude geometry column for cleaner text output if desired
attribute_df = gdf_sample.drop(columns=['geometry'])

for idx, row in attribute_df.iterrows():
    print(f"\n--- RECORD {idx + 1} ---")
    for col, val in row.items():
        print(f"  {col:<25} : {val}")
