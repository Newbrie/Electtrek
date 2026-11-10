from shapely import wkt
import matplotlib.pyplot as plt
import geopandas as gpd

# Your WKT polygon string
wkt_str = "POLYGON ((-0.4208939642857142 51.195298142857155, -0.6549058333333335 51.196567944444446, -0.7371042592592593 51.20993322222222, -0.760185960784314 51.332336333333345, -0.6681336842105263 51.37538734210528, -0.6267768750000001 51.369483875000014, -0.4732881333333333 51.32411186666668, -0.4052125833333333 51.272890849999996, -0.3981791020408162 51.260990081632634, -0.4208939642857142 51.195298142857155))"

poly = wkt.loads(wkt_str)
gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")

fig, ax = plt.subplots(figsize=(8, 8))
gdf.plot(ax=ax, facecolor='lightblue', edgecolor='blue', alpha=0.5)
plt.title("Pre-Flight Elector Convex Hull")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.grid(True)
plt.show()
