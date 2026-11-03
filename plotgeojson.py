import geopandas as gpd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

# 1. Open interactive file picker
root = Tk()
root.withdraw()
root.attributes("-topmost", True)

file_path = filedialog.askopenfilename(
    title="Select Spatial File (GeoJSON / GPKG / SHP)",
    filetypes=[("Spatial Files", "*.geojson *.json *.gpkg *.shp"), ("All Files", "*.*")]
)

if file_path:
    print(f"📄 Loading spatial data from: {file_path}")
    gdf = gpd.read_file(file_path)

    if not gdf.empty:
        print(f"✅ Loaded {len(gdf)} feature(s). Rendering plot...")

        # 2. Plot all geometries in the GeoDataFrame
        fig, ax = plt.subplots(figsize=(8, 8))
        gdf.plot(ax=ax, color='#3B82F6', edgecolor='#1E3A8A', alpha=0.7)

        ax.set_title(f"Geometry Plot: All Features ({len(gdf)} total)", fontsize=14, fontweight='bold')
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        plt.grid(True, linestyle="--", alpha=0.5)

        plt.show()
    else:
        print("❌ The selected dataset is empty!")
else:
    print("❌ No file selected.")
