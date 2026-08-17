import hashlib
import geopandas as gpd

def uuid_to_int64(guid_str: str) -> int:
    """Generates a stable, deterministic 64-bit integer from a UUID string."""
    if not guid_str or str(guid_str).lower() == 'none':
        return 0
    return int(hashlib.sha256(str(guid_str).encode('utf-8')).hexdigest()[:15], 16)

# Load raw OS roads or GeoDataFrame
gdf = gpd.read_file("UK-ROADS.gpkg")

# Method 1: Deterministic hash from OS 'identifier' (retains true identity across re-builds)
if 'identifier' in gdf.columns:
    gdf['FID'] = gdf['identifier'].apply(uuid_to_int64)
else:
    # Method 2: Sequential integer index (1, 2, 3...)
    gdf['FID'] = gdf.index.astype(int) + 1

# Ensure FID is explicitly integer type
gdf['FID'] = gdf['FID'].astype('int64')

# Save back to GeoPackage
gdf.to_file("UK-ROADS.gpkg", driver="GPKG", layer="uk_roads")
