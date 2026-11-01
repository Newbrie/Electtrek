import geopandas as gpd
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

# 1. Open interactive file picker
root = Tk()
root.withdraw()
root.attributes("-topmost", True)

file_path = filedialog.askopenfilename(
    title="Select Countries File (GeoJSON / GPKG / SHP)",
    filetypes=[("Spatial Files", "*.geojson *.json *.gpkg *.shp"), ("All Files", "*.*")]
)

if file_path:
    print(f"📄 Loading spatial data from: {file_path}")
    gdf = gpd.read_file(file_path)

    # 2. Isolate FID 238 (United Kingdom)
    uk_row = gdf[gdf['FID'] == 238]

    if not uk_row.empty:
        name = uk_row.iloc[0].get('NAME', 'United Kingdom')
        print(f"✅ Found feature for '{name}' (FID 238). Rendering plot...")

        # 3. Plot the geometry
        fig, ax = plt.subplots(figsize=(8, 8))
        uk_row.plot(ax=ax, color='#3B82F6', edgecolor='#1E3A8A', alpha=0.7)

        ax.set_title(f"Geometry Plot: {name} (FID 238)", fontsize=14, fontweight='bold')
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        plt.grid(True, linestyle="--", alpha=0.5)

        plt.show()
    else:
        print("❌ FID 238 was not found in this dataset!")
else:
    print("❌ No file selected.")
