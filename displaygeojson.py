import geopandas as gpd
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi, voronoi_plot_2d

# 1. Load GeoJSON
gdf = gpd.read_file("fixed_walk_geom.geojson")

# 2. Re-project to projected CRS (British National Grid: EPSG:27700) to fix UserWarning
gdf_projected = gdf.to_crs(epsg=27700)

# 3. Calculate Centroids in projected meters
gdf_projected["centroid"] = gdf_projected.geometry.centroid
points = list(zip(gdf_projected.centroid.x, gdf_projected.centroid.y))

# 4. Handle Voronoi minimum points requirement
fig, ax = plt.subplots(figsize=(10, 8))

if len(points) >= 4:
    vor = Voronoi(points)
    voronoi_plot_2d(vor, ax=ax, show_vertices=False, line_colors="red", line_style="--", point_size=10)
else:
    print(f"Skipping Voronoi: At least 4 points are required, but only {len(points)} were found.")

# Plot original shapes in projected meters
gdf_projected.plot(ax=ax, color="lightblue", edgecolor="blue", alpha=0.5)

plt.title("GeoJSON Features & Centroids")
plt.xlabel("Easting (m)")
plt.ylabel("Northing (m)")
plt.show()
