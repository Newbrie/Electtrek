import os
import sys
import zipfile
import requests
from pathlib import Path
import geopandas as gpd

# Configuration
ZIP_URL = "https://api.os.uk/downloads/v1/products/OpenRoads/downloads?area=GB&format=ESRI%C2%AE+Shapefile&redirect"
DOWNLOAD_ZIP = Path("oproad_gb.zip")
EXTRACT_DIR = Path("OS_Open_Roads")
OUTPUT_GPKG = Path("UK-ROADS.gpkg")
TARGET_CRS = "EPSG:4326"  # Reproject to WGS 84 for Folium / web mapping

def download_and_build_gpkg(force_rebuild=False):
    # Step 0: Check if valid OUTPUT_GPKG already exists
    if OUTPUT_GPKG.exists() and not force_rebuild:
        try:
            # Check if file is readable and non-empty
            if OUTPUT_GPKG.stat().st_size > 1000:
                print(f"✅ Found existing '{OUTPUT_GPKG}' ({OUTPUT_GPKG.stat().st_size / (1024**2):.1f} MB). Skipping build.")
                return
        except Exception:
            print(f"⚠️ Existing '{OUTPUT_GPKG}' appears corrupted. Rebuilding...")

    # Step 1: Check existing files or download Zip Archive
    # Search for shapefiles or zip in EXTRACT_DIR or working dir
    existing_shps = list(EXTRACT_DIR.rglob("*RoadLink.shp")) if EXTRACT_DIR.exists() else []

    if existing_shps:
        print(f"📂 Found {len(existing_shps)} existing extracted shapefiles in '{EXTRACT_DIR}'. Skipping download/extraction.")
    else:
        # Check for zip archive
        if not DOWNLOAD_ZIP.exists():
            print(f"⬇️ Downloading OS Open Roads archive (~350 MB)...")
            with requests.get(ZIP_URL, stream=True) as response:
                response.raise_for_status()
                with open(DOWNLOAD_ZIP, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(" Download complete.")
        else:
            print(f"📦 Found existing archive: '{DOWNLOAD_ZIP}'")

        # Step 2: Extract Zip File if no shapefiles found
        print(f" Extracting files to '{EXTRACT_DIR}'...")
        with zipfile.ZipFile(DOWNLOAD_ZIP, "r") as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
        print(" Extraction complete.")
        existing_shps = sorted([p for p in EXTRACT_DIR.rglob("*RoadLink.shp")])

    if not existing_shps:
        print(f"❌ Error: No '*RoadLink.shp' files found in '{EXTRACT_DIR}'.")
        return

    print(f" Found {len(existing_shps)} grid tile shapefiles. Compiling to '{OUTPUT_GPKG}'...")

    # Remove old/corrupted GPKG before building
    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()

    total_roads = 0
    engine = "pyogrio" if "pyogrio" in sys.modules else "fiona"

    for idx, shp_path in enumerate(existing_shps):
        gdf = gpd.read_file(shp_path)
        if gdf.empty:
            continue

        # Keep key road attributes to optimize performance and filesize
        cols = [c for c in ["fictitious", "identifier", "class", "roadNumber", "name1", "formOfWay", "length", "geometry"] if c in gdf.columns]
        gdf = gdf[cols]

        # CRITICAL FIX: Drop legacy FID/fid columns so GDAL auto-generates
        # a unique, clean integer primary key (fid) in SQLite without collisions.
        for col in ['FID', 'fid', 'OBJECTID']:
            if col in gdf.columns:
                gdf = gdf.drop(columns=[col])

        if TARGET_CRS and gdf.crs != TARGET_CRS:
            gdf = gdf.to_crs(TARGET_CRS)

        mode = "w" if idx == 0 else "a"
        gdf.to_file(OUTPUT_GPKG, layer="uk_roads", driver="GPKG", mode=mode, engine=engine)
        total_roads += len(gdf)

        if (idx + 1) % 10 == 0 or (idx + 1) == len(existing_shps):
            print(f"  Processed {idx + 1}/{len(existing_shps)} tiles ({total_roads:,} road features written)")

    print(f"\n Finished building '{OUTPUT_GPKG}' with {total_roads:,} features.")

if __name__ == "__main__":
    download_and_build_gpkg()
