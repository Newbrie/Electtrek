import geopandas as gpd
import folium

# Ask user for file path
filename = input("Enter path to your GeoJSON file: ")

# Load file
gdf = gpd.read_file("/Users/newbrie/Documents/ReformUK/GitHub/Reference/Boundaries/"+filename)
print("\nLoaded GeoJSON with", len(gdf), "features")
print("CRS:", gdf.crs)

# Convert to WGS84 (Folium requires EPSG:4326)
if gdf.crs is None or gdf.crs.to_epsg() != 4326:
    print("Reprojecting to EPSG:4326 for Folium…")
    gdf = gdf.to_crs(epsg=4326)

# Get centroid for map start
centroid = gdf.geometry.unary_union.centroid
start_coords = (centroid.y, centroid.x)

# Create the Folium map
m = folium.Map(location=start_coords, zoom_start=10)

# Add GeoJSON layer
folium.GeoJson(
    gdf,
    name="GeoJSON Data"
).add_to(m)

# Layer control
folium.LayerControl().add_to(m)

# Save file
output = "map.html"
m.save(output)

print(f"\nMap saved as {output}")
print("Open map.html in your browser to view the interactive map.")
