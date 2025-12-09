import geopandas as gpd
import os

# Prompt the user for the input filename
workdirectories = {}
input_filename = input("Please enter the path to your GeoJSON file: ")
workdirectories['bounddir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Reference/Boundaries"

# Load the GeoJSON file into a GeoDataFrame
gdf = gpd.read_file(workdirectories['bounddir']+"/"+input_filename)

# Inspect the current CRS
print("Original CRS:", gdf.crs)

# Manually set CRS if it is not EPSG:27700, as we're assuming the data is in British National Grid (meters)
if gdf.crs is None or gdf.crs.to_string() != "EPSG:27700":
    print("Setting CRS to EPSG:27700 manually (assuming the file is in meters, BNG).")
    gdf = gdf.set_crs("EPSG:27700", allow_override=True)

# Convert to EPSG:4326 (degrees, WGS84)
gdf_degrees = gdf.to_crs("EPSG:4326")

# Inspect the first few rows to confirm the transformation
print(gdf_degrees.head())

# Create a new filename by modifying the original filename
base, ext = os.path.splitext(input_filename)
output_filename = f"{base}_degrees{ext}"

# Save the GeoDataFrame in the new file
gdf_degrees.to_file(workdirectories['bounddir']+"/"+output_filename, driver="GeoJSON")

print(f"File saved as {output_filename}")
