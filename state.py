import json
import os
import pandas as pd
import re
import geopandas as gpd
from shapely import crosses, contains,covers, union, envelope, intersection
from shapely.ops import nearest_points
# ✅ CORRECT

from shapely.geometry import Polygon
from shapely.geometry import Point, MultiPoint
from shapely.geometry.base import BaseGeometry

from collections import defaultdict
from typing import DefaultDict
from pathlib import Path
import config
from config import TABLE_FILE, CANDIDATES_FILE,LAST_RESULTS_FILE, workdirectories, DEVURLS
from flask import has_request_context, request, redirect
import logging



from types import MappingProxyType

progress = {}


branchcolours = [
    "#006064",  # 0 Darkest Cyan (Cyan 900)
    "#00838F",  # 1 Deep Sea
    "#0097A7",  # 2 Original Cyan
    "#00ACC1",  # 3 Robin's Egg
    "#00BCD4",  # 4 Vivid Cyan
    "#26C6DA",  # 5 Bright Turquoise
    "#4DD0E1",  # 6 Sky Aqua
    "#80DEEA",  # 7 Soft Cyan
    "#B2EBF2",  # 8 Pale Mist
    "#E0F7FA",  # 9 Ice White-Cyan
    "#00E5FF",  # 10 Electric Cyan (High Saturation)
    "#18FFFF",  # 11 Neon Aqua
]


Geo_index = {}


def route():
    if has_request_context():
        return request.endpoint
    return None  # or a default string like "no_request_context"

def resolve_here_or_redirect(here):
    if has_request_context():
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        if lat is not None and lon is not None:
            here = (lat, lon)

        if here is None:
            return None, redirect(url_for("get_location"))

    return here, None

def clean_path_part(part):
    """Clean file suffixes, or return None if ignorable/empty."""
    if part in IGNORABLE_SEGMENTS:
        return None
    for suffix in FILE_SUFFIXES:
        if part.endswith(suffix):
            return None
    return part

def stepify(path_str):
    """Split path string, clean each segment, and remove sequential duplicates."""
    parts = path_str.strip().split("/")
    cleaned = []

    for part in parts:
        cleaned_part = clean_path_part(part)
        if cleaned_part:
            # Only append if it's the first element OR not a duplicate of the previous element
            if not cleaned or cleaned[-1] != cleaned_part:
                cleaned.append(cleaned_part)

    return cleaned

def pathify(parts):
    """
    Takes a clean list of geographic parts and builds a node path.
    Automatically infers whether it's a MAP or a PRINT view based on array depth.
    """
    if not parts:
        return ""

    base_path = "/".join(parts)

    # Inference rules based on hierarchy depth:
    # Length 1-5: Country, Region, County, Constituency, Ward -> Always MAP overviews
    # Length 6+: Polling Districts (PDS) or Walks -> Swaps to PRINT sheets
    return f"{base_path}"


def selprefix(election):
    from elections import list_elections

    election = election.upper()
    elections_list = list_elections()  # already sorted

    if election not in elections_list:
        raise ValueError(f"Election '{election}' not found")

    idx = elections_list.index(election)

    if idx >= 26:
        raise ValueError("Too many elections for single-letter prefix")

    return chr(65 + idx)

def make_upd(election, pd):
    eprefix = selprefix(election).strip().upper()
    pd = str(pd).strip().upper()

    if not eprefix:
        raise ValueError(f"Invalid election prefix for election={election}")

    if not pd:
        raise ValueError("Blank PD")

    return f"{eprefix}-{pd}"

def normalname(name):
    def clean(s):
        if pd.isna(s):
            return ""

        s = str(s)
        s = s.replace(" & ", " AND ")

        # ✅ Added \( and \) to the "allow" list
        s = re.sub(r"[^A-Za-z0-9 _\(\)]+", "", s)

        # Normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()

        # Convert spaces to underscores
        s = s.replace(" ", "_")

        # Remove duplicate underscores
        s = re.sub(r"_+", "_", s)

        # Remove leading/trailing underscores
        s = s.strip("_")

        return s.upper().removesuffix("_ED")

    if isinstance(name, (str, bool, int, float)) or name is None:
        return clean(name)
    elif isinstance(name, pd.Series):
        return name.fillna("").astype(str).apply(clean)
    else:
        print(f"______ERROR: Unsupported type {type(name)}")
        return name


def get_path_step(path, n):
    """
    Return the nth component of a node path (0-based index).

    Example:
        get_path_step("A/B/C", 1) -> "B"
    """
    if not path:
        return None

    parts = [p for p in path.strip("/").split("/") if p]

    if 0 <= n < len(parts):
        return parts[n]

    return None


def ensure_4326(gdf):
    """
    If data is naive, set the CRS to 4326.
    If it is ALREADY 4326, do nothing (don't force a transformation).
    """
    if gdf.crs is None:
        # This is where you tell the system: "I know these are 4326"
        logging.info("[CRS] Data is naive; setting to EPSG:4326")
        gdf = gdf.set_crs("EPSG:4326")

    # If the CRS is already 4326, skip the math entirely to avoid the crash
    elif not gdf.crs.equals("EPSG:4326"):
        logging.info(f"[CRS] Data is in {gdf.crs}; transforming to 4326")
        gdf = gdf.to_crs("EPSG:4326")

    return gdf




def clear_treepolys(from_level=None):

    if from_level is None:
        for k in Treepolys:
            Treepolys[k] = gpd.GeoDataFrame()
    else:
        for layer in MAP_LAYERS[from_level:]:
            Treepolys[layer["key"]] = gpd.GeoDataFrame()

def parse_coords(coord_input) -> list[tuple[float, float]]:
    """
    Normalizes various coordinate representations into a list of (lat, lon) tuples.
    Handles: (lat, lon), [lat, lon], [[lat, lon]], or None.
    """
    if not coord_input:
        return []

    # Single pair: (lat, lon) or [lat, lon]
    if isinstance(coord_input, (list, tuple)):
        if len(coord_input) == 2 and isinstance(coord_input[0], (int, float)):
            lat, lon = coord_input
            if lat is not None and lon is not None:
                return [(float(lat), float(lon))]
        # Nested list: [[lat, lon], ...]
        elif len(coord_input) > 0 and isinstance(coord_input[0], (list, tuple)):
            valid_pairs = []
            for item in coord_input:
                if len(item) == 2 and item[0] is not None and item[1] is not None:
                    valid_pairs.append((float(item[0]), float(item[1])))
            return valid_pairs

    return []


def clean_text(value: str | None) -> str:
    """Remove hidden unicode chars and trim whitespace."""
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r'[\u202a-\u202e]', '', value)
    return value.strip()


def clean_mobile(value: str | None) -> str:
    """Normalize mobile numbers."""
    value = clean_text(value)
    return value.replace("M:", "").replace(" ", "").strip()


def generate_code(firstname: str, surname: str, existing_codes: set) -> str:
    """Generate a short unique identifier code."""
    base = (firstname[:1] + surname[:1]).upper()
    if base not in existing_codes:
        return base
    i = 1
    while f"{base}{i}" in existing_codes:
        i += 1
    return f"{base}{i}"


# ------------------------------------------------------------------------------
# 🗺️ SPATIAL PIPELINE FUNCTIONS
# ------------------------------------------------------------------------------


def get_centroid_or_point(roid):
    """
    Extracts a single representative Shapely Point from 'roid'.
    Handles Shapely geometries, (lat, lon) tuples/lists, or string paths/coords.
    Guarantees output in Shapely Point(lon, lat) format.
    """
    if roid is None:
        return None

    # 1. Any Shapely Geometry (Point, Polygon, MultiPolygon, etc.)
    if hasattr(roid, "geom_type") or hasattr(roid, "centroid"):
        if getattr(roid, "is_empty", False):
            return None
        return roid.centroid

    # 2. Raw (lat, lon) tuple or list of numbers, e.g. (51.248, -0.420)
    if isinstance(roid, (tuple, list)) and len(roid) >= 2 and isinstance(roid[0], (int, float)):
        lat, lon = float(roid[0]), float(roid[1])
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return Point(lon, lat)  # Point(x, y) = Point(lon, lat)
        return Point(lat, lon)

    # 3. Parse coordinate strings or paths
    coords = parse_coords(roid) if "parse_coords" in globals() else []
    if not coords:
        return None

    points = []
    for c in coords:
        if len(c) >= 2:
            c0, c1 = float(c[0]), float(c[1])
            if -90 <= c0 <= 90 and -180 <= c1 <= 180:
                points.append(Point(c1, c0))  # lon, lat
            else:
                points.append(Point(c0, c1))  # x, y

    if not points:
        return None

    if len(points) == 1:
        return points[0]

    return MultiPoint(points).centroid

def filterArea(source, sourcekey, destination, roid=None, name=None, boundary_geom=None):
    """
    Lookup polygon(s) by name, centroid of roid/convex hull, or boundary polygon.
    Returns: [selected_name, matched_gdf, full_gdf]
    """
    print(f"[filterArea] destination: {destination}, roid: {roid}, step: {name}")

    gdf_RAW = get_layer_gdf(source)
    gdf = ensure_4326(gdf_RAW)

    gdf = gdf.rename(columns={sourcekey: 'NAME'})
    if 'OBJECTID' in gdf.columns:
        gdf = gdf.rename(columns={'OBJECTID': 'FID'})

    matched = gdf.head(0)
    nodestep = None

    # 1️⃣ Lookup by name
    if name is not None:
        target = normalname(name.split("/")[-1])
        matched = gdf[gdf["NAME"].astype(str).apply(normalname) == target]

    # 2️⃣ Lookup by boundary polygon
    elif boundary_geom is not None:
        if isinstance(boundary_geom, BaseGeometry):
            matched = gdf[gdf.intersects(boundary_geom)]
        else:
            filter_geom = resolve_here_geometry(boundary_geom) if "resolve_here_geometry" in globals() else None
            matched = gdf[gdf.intersects(filter_geom)] if filter_geom else gdf.head(0)

    # 3️⃣ Lookup by ROID (Resolves lat/lon tuple, list, or geometry to a Shapely Point)
    elif roid is not None:
        centroid_pt = get_centroid_or_point(roid)

        if centroid_pt is not None and not centroid_pt.is_empty:
            # Primary lookup
            matched = gdf[gdf.covers(centroid_pt)]

            # Edge fallback: if point sits exactly on a boundary line
            if matched.empty:
                matched = gdf[gdf.intersects(centroid_pt)]

            print(f"[filterArea] 📍 Using ROID Centroid ({centroid_pt.y:.5f}, {centroid_pt.x:.5f}) -> Matched {len(matched)} feature(s)")
        else:
            print(f"[filterArea] ⚠️ Invalid coordinate structure for roid: {roid}")

    # Export & metadata resolution
    if not matched.empty:
        nodestep = normalname(matched['NAME'].iloc[0])
        matched.to_file(destination, driver="GeoJSON")
        print(f"[filterArea] Found {nodestep} ({len(matched)} feature(s)), saved to {destination}")
    else:
        print(f"[filterArea] No matching feature found for name {name} or roid {roid}")

    return [nodestep, matched, gdf]


import numpy as np
from scipy.spatial import cKDTree
import geopandas as gpd

def indexSpatialArea(source, field, destination, boundary_geom=None, roid=None):
    """
    Slices UPRN points, builds an in-memory cKDTree index, and returns
    a structured layer dict for Treepolys['street'].
    """
    bounds = None
    if boundary_geom is not None:
        geom_gdf = boundary_geom if isinstance(boundary_geom, (gpd.GeoSeries, gpd.GeoDataFrame)) else gpd.GeoDataFrame(geometry=[boundary_geom], crs="EPSG:4326")
        bounds = geom_gdf.to_crs(epsg=27700).total_bounds

    # 1. Read slice from GPKG
    uprn_gdf = gpd.read_file(source, bbox=bounds)

    if uprn_gdf.crs and uprn_gdf.crs.to_epsg() != 4326:
        uprn_gdf = uprn_gdf.to_crs(epsg=4326)

    # 2. Export GeoJSON to disk for pipeline compatibility
    uprn_gdf.to_file(destination, driver="GeoJSON")

    # 3. Extract coordinate matrix (Lat, Lon) for KDTree
    coords = np.column_stack((uprn_gdf.geometry.y, uprn_gdf.geometry.x))

    # 4. Return structured dictionary containing BOTH vector layer and spatial index
    return {
        "gdf": uprn_gdf,
        "index": cKDTree(coords) if len(coords) > 0 else None,
        "coords": coords,
        "ids": uprn_gdf[field].values if field in uprn_gdf else np.array([])
    }


from pyogrio import read_dataframe

from pyogrio import read_dataframe, read_info
from shapely.geometry.base import BaseGeometry

def linestringArea(source, field, destination, boundary_geom=None, roid=None, select_name=None):
    """
    Slices pre-downloaded local street LineStrings by spatial bounding box / intersection
    and optional street name matching.
    Returns: [selected_name, matched_gdf, full_gdf]
    """
    print("\n" + "="*80)
    print(f"▶️ ENTERING linestringArea for source: {source}")
    print("="*80)

    # 1. Inspect Boundary Geometry
    working_geom = None
    if boundary_geom is not None:
        working_geom = boundary_geom if isinstance(boundary_geom, BaseGeometry) else get_centroid_or_point(boundary_geom)

    if working_geom is not None:
        print(f"DEBUG [linestringArea]: working_geom type={type(working_geom)}, is_empty={working_geom.is_empty}, bounds={working_geom.bounds}")
    else:
        print("DEBUG [linestringArea]: working_geom is None")

    # 2. Inspect File Metadata (Lightweight check for driver and FID support)
    info = read_info(source)
    print("=== FILE INFO ===")
    print(f"Driver: {info['driver']}")
    print(f"Feature Count: {info['features']}")
    print(f"FID Column Name in Source: {info.get('fid_column')}")

    # 3. Read GeoPackage using spatial bbox if available, defaulting to full read
    bbox = working_geom.bounds if (working_geom is not None and not working_geom.is_empty) else None

    if bbox:
        print(f"DEBUG [linestringArea]: Attempting pyogrio read with bbox={bbox}")
        try:
            gdf_raw = read_dataframe(source, bbox=bbox, fid_as_index=True)
            print(f"DEBUG [linestringArea]: pyogrio bbox read returned {len(gdf_raw)} rows")
        except Exception as e:
            print(f"DEBUG [linestringArea]: pyogrio bbox read failed with error ({e}), falling back to full read...")
            gdf_raw = read_dataframe(source, fid_as_index=True)
    else:
        print(f"DEBUG [linestringArea]: Reading raw source without bbox filter...")
        gdf_raw = read_dataframe(source, fid_as_index=True)

    print(f"DEBUG [linestringArea]: Raw file read count={len(gdf_raw)}, CRS={gdf_raw.crs}")

    # Standardize CRS to WGS84
    gdf = ensure_4326(gdf_raw)

    # Preserve / Promote OGR FID from DataFrame index
    if 'FID' not in gdf.columns:
        gdf['FID'] = gdf.index.astype(str)
    else:
        gdf['FID'] = gdf['FID'].astype(str)

    # Standardize column naming
    if field in gdf.columns:
        gdf = gdf.rename(columns={field: 'NAME'})
    elif 'NAME' not in gdf.columns:
        gdf['NAME'] = "Unnamed Street"

    # Filter LineStrings
    geom_types = gdf.geometry.type.unique() if not gdf.empty else []
    print(f"DEBUG [linestringArea]: Unique geometry types found: {geom_types}")

    gdf = gdf[gdf.geometry.type.isin(['LineString', 'MultiLineString'])].copy()
    print(f"DEBUG [linestringArea]: Count after LineString filter={len(gdf)}")

    # 4. Spatial Intersection Step
    if working_geom is not None and not working_geom.is_empty and not gdf.empty:
        print(f"DEBUG [linestringArea]: Running spatial index intersection...")
        # sindex returns integer row positions for iloc
        possible_pos = list(gdf.sindex.intersection(working_geom.bounds))
        matched = gdf.iloc[possible_pos].copy()

        exact_intersects = matched.geometry.intersects(working_geom)
        matched = matched[exact_intersects].copy()
        print(f"DEBUG [linestringArea]: Count after matched.intersects()={len(matched)}")
    else:
        print("DEBUG [linestringArea]: Skipping spatial clip (working_geom is None or gdf is empty)")
        matched = gdf.copy()

    # 5. Target street name filtering
    nodestep = None
    if select_name is not None and not matched.empty:
        target_norm = normalname(select_name)
        print(f"DEBUG [linestringArea]: Filtering by select_name='{select_name}' (norm='{target_norm}')")
        name_matched = matched[matched['NAME'].astype(str).apply(normalname) == target_norm]
        if not name_matched.empty:
            matched = name_matched
            nodestep = target_norm

    if nodestep is None and not matched.empty:
        nodestep = normalname(str(matched['NAME'].iloc[0]))

    print(f"DEBUG [linestringArea]: Final matched count to be saved={len(matched)}")

    # 6. Save sliced subset
    matched.to_file(destination, driver="GeoJSON")
    print(f"🏁 LEAVING linestringArea. Saved {len(matched)} linestrings to {destination}")
    print("="*80 + "\n")

    return [nodestep, matched, gdf]

import logging

import osmnx as ox

# Ensure OSMnx caching is enabled for performance
ox.settings.use_cache = True
ox.settings.log_console = False

import logging
import pandas as pd
import geopandas as gpd
from shapely.geometry.base import BaseGeometry
import osmnx as ox

# Ensure OSMnx caching is enabled for performance
ox.settings.use_cache = True
ox.settings.log_console = False


def intersectingArea(
    source, sourcekey, parent_levels, child_level, intention_type, destination,
    parent_row, *, select_child_name=None, roid=None, boundary_geom=None
    ):
    parent_name = normalname(parent_row["NAME"]) if parent_row is not None else "None"
    parent_type = parent_levels.get(child_level)

    print(f"\n🔍 [DEBUG intersectingArea START] Processing Level {child_level} -> {intention_type.upper()}")
    print(f"   ↳ Parent Name: {parent_name} | Parent Type: {parent_type}")

    if parent_type is None:
        raise ValueError(f"No parent type found for parent_level IN {parent_levels}")

    # 1. Load & sanitize layer
    gdf_RAW = get_layer_gdf(source)
    gdf = ensure_4326(gdf_RAW)

    if sourcekey in gdf.columns:
        gdf = gdf.rename(columns={sourcekey: "NAME"})
    else:
        raise ValueError(f"No sourcekey {sourcekey} IN {gdf.columns}")

    if "OBJECTID" in gdf.columns:
        gdf = gdf.rename(columns={"OBJECTID": "FID"})

    # 2. Geometry selection — Priority: explicitly passed boundary_geom convex hull -> parent geometry
    working_geom = None
    if boundary_geom is not None:
        working_geom = boundary_geom.buffer(0) if isinstance(boundary_geom, BaseGeometry) else boundary_geom
        logging.debug("   ↳ Using explicit boundary_geom convex hull for child filtering")
    elif parent_row is not None and hasattr(parent_row, "geometry") and not parent_row.geometry.is_empty:
        working_geom = parent_row.geometry

    # 3. Overlap math against boundary_geom / working_geom
    if working_geom is not None:
        child_polygons_within_parent = filter_gdf_by_overlap(
            children_gdf=gdf,
            parent_geometry=working_geom,
            layer_type=intention_type,
            threshold_dict=OVERLAP_THRESHOLDS
        )
    else:
        child_polygons_within_parent = gdf.copy()

    # 4. Resolve selected child polygon name
    selected_child_name = None

    # Option A: Use Centroid of ROID / Convex Hull
    centroid_pt = get_centroid_or_point(roid)
    if centroid_pt is not None and not child_polygons_within_parent.empty:
        hit = child_polygons_within_parent[child_polygons_within_parent.geometry.contains(centroid_pt)]
        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    # Option B: Fallback to explicit name lookup
    if not selected_child_name and select_child_name and not child_polygons_within_parent.empty:
        hit = child_polygons_within_parent[
            child_polygons_within_parent["NAME"].apply(normalname) == normalname(select_child_name)
        ]
        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    # Option C: Fallback to first overlapping child
    if not selected_child_name and not child_polygons_within_parent.empty:
        selected_child_name = normalname(child_polygons_within_parent.iloc[0]["NAME"])

    print(f"🏁 [DEBUG intersectingArea END] Final Selected Child Name: {selected_child_name}\n")
    return selected_child_name, child_polygons_within_parent, gdf

def select_parent_geoms(*, Treepolys, parent_key, sourcepath=None, here=None):
    parents = Treepolys.get(parent_key, gpd.GeoDataFrame())
    print(f"select_parent: raw Treepolys[{parent_key}] = {len(parents)} records")

    if parents.empty:
        return gpd.GeoDataFrame()

    # 1️⃣ Point-in-polygon
    coords = parse_coords(here)
    if coords:
        lat, lon = coords[0]
        pt = Point(lon, lat)
        matches = parents[parents.contains(pt)]
        if not matches.empty:
            return matches

    # 2️⃣ Sourcepath/name match
    if sourcepath:
        steps = stepify(sourcepath)
        target_name = steps[-1].replace("_", " ")
        matches = parents[
            parents["NAME"].apply(normalname) == normalname(target_name)
        ]
        if not matches.empty:
            return matches

    # 3️⃣ Fallback: return all parent features
    return parents


def load_layer(
    *, layer, level, intention_type, parent_levels, parent_row,
    select_name=None, roid=None, boundary_geom=None, **kwargs
):
    """
    Dynamically routes layer loading to the appropriate spatial operation method:
    1. Direct Attribute/Name Filtering (Level 0 - 2) -> filterArea
    2. Point-Based Spatial Index Slicing (Level 4 UPRNs) -> indexSpatialArea
    3. LineString Geometry Slicing (Level 6 Streets) -> linestringArea
    4. Polygon Overlap/Intersection (Level 3 - 4 Boundaries) -> intersectingArea
    """
    src = f"{workdirectories['bounddir']}/{layer['src']}"
    out = f"{workdirectories['bounddir']}/{layer['out']}"
    method = layer.get("method")

    # Comprehensive Entry Debug Statement
    print("\n" + "=" * 80)
    print(f"▶️ [load_layer] CALL DISPATCH:")
    print(f"   • Layer Name/Key : {layer.get('name', layer.get('field', 'UNKNOWN'))}")
    print(f"   • Method Specified: '{method}'")
    print(f"   • Level          : {level}")
    print(f"   • Intention Type : {intention_type}")
    print(f"   • Select Name    : '{select_name}'")
    print(f"   • ROID           : {roid}")
    print(f"   • Source Path    : {src}")
    print(f"   • Destination    : {out}")
    if boundary_geom is not None:
        geom_type = getattr(boundary_geom, "geom_type", type(boundary_geom).__name__)
        is_empty = getattr(boundary_geom, "is_empty", "N/A")
        bounds = getattr(boundary_geom, "bounds", "N/A")
        print(f"   • Boundary Geom  : Type={geom_type}, is_empty={is_empty}, bounds={bounds}")
    else:
        print(f"   • Boundary Geom  : None")
    print("=" * 80)

    # 1. Direct Attribute/Name Filtering (Level 0 - 2)
    if method == "filter":
        print(f"🔀 [load_layer] Routing to -> filterArea()")
        return filterArea(
            src, layer["field"], out,
            roid=roid, name=select_name, boundary_geom=boundary_geom
        )

    # 2. Point-Based Spatial Index Slicing (Level 4 UPRNs)
    if method == "index":
        print(f"🔀 [load_layer] Routing to -> indexSpatialArea()")
        return indexSpatialArea(
            source=src,
            field=layer["field"],
            destination=out,
            boundary_geom=boundary_geom,
            roid=roid
        )

    # 3. Local LineString Spatial Slicing (Level 6 Streets)
    if method == "linestringArea":
        print(f"🔀 [load_layer] Routing to -> linestringArea()")
        return linestringArea(
            source=src,
            field=layer["field"],
            destination=out,
            boundary_geom=boundary_geom,
            roid=roid,
            select_name=select_name
        )

    # 4. Polygon Intersection Operations (Level 3 - 4 Boundaries / Fallback)
    print(f"🔀 [load_layer] Routing to -> intersectingArea() (method='{method}')")
    return intersectingArea(
        source=src,
        sourcekey=layer["field"],
        parent_levels=parent_levels,
        child_level=level,
        intention_type=intention_type,
        destination=out,
        parent_row=parent_row,
        roid=roid,
        select_child_name=select_name,
        boundary_geom=boundary_geom
    )

def subending(filename, ending):
  stem = filename.replace(".XLSX", "@@@").replace(".CSV", "@@@").replace(".xlsx", "@@@").replace(".csv", "@@@").replace("-PRINT.html", "@@@").replace("-CAL.html", "@@@").replace("-MAP.html", "@@@").replace("-WALKS.html", "@@@").replace("-ZONES.html", "@@@").replace("-PDS.html", "@@@").replace("-DIVS.html", "@@@").replace("-WARDS.html", "@@@")
  print(f"____Subending test: from {filename} to {stem.replace('@@@', ending)}")
  return stem.replace("@@@", ending)


def upsert_geodf(existing, incoming, key="FID"):
    if existing is None or existing.empty:
        return incoming
    if incoming is None or incoming.empty:
        return existing

    # Ensure CRS compatibility
    if existing.crs is None and incoming.crs is not None:
        existing = existing.set_crs(incoming.crs)
    elif (
        existing.crs is not None
        and incoming.crs is not None
        and existing.crs != incoming.crs
    ):
        incoming = incoming.to_crs(existing.crs)

    # Combine DataFrames
    combined = pd.concat([existing, incoming], ignore_index=True)

    # Drop duplicates keeping newest
    combined = combined.drop_duplicates(subset=key, keep="last")

    # ✅ SAFELY Rebuild GeoDataFrame ensuring 'geometry' column is used
    geom_col = (
        existing.geometry.name
        if isinstance(existing, gpd.GeoDataFrame)
        else "geometry"
    )
    if geom_col not in combined.columns:
        geom_col = "geometry"

    return gpd.GeoDataFrame(combined, geometry=geom_col, crs=existing.crs)

LAYER_CACHE = {}

def get_layer_gdf(src):
    if src not in LAYER_CACHE:
        LAYER_CACHE[src] = gpd.read_file(src)
    return LAYER_CACHE[src]


def get_parent_rows(plevels, child_level, parent_rows, roid, boundary_geom):
    from shapely.geometry import Point
    import logging
    import geopandas as gpd

    parent_layer_type = plevels.get(child_level)
    parent_tree = Treepolys.get(parent_layer_type)

    if parent_tree is None or parent_tree.empty:
        logging.warning(f"[WARNING] No parent tree for {parent_layer_type}")
        return []

    logging.debug(f"[DEBUG] Parent tree has {len(parent_tree)} features")

    # 1️⃣ POLYGON MODE
    if boundary_geom is not None:
        matches = parent_tree[parent_tree.geometry.intersects(boundary_geom)]
        if not matches.empty:
            logging.debug(f"[DEBUG] Polygon match → {len(matches)} parents")
            return [row for _, row in matches.iterrows()]

    # 2️⃣ POINT MODE
    if roid is not None:
        pt = Point(roid[::-1])
        matches = parent_tree[parent_tree.contains(pt)]
        if not matches.empty:
            logging.debug(f"[DEBUG] Point match → {len(matches)} parents")
            return [row for _, row in matches.iterrows()]

        # 3️⃣ FALLBACK: nearest parent
        logging.debug("[DEBUG] No containing parent, using nearest")
        distances = parent_tree.geometry.distance(pt).dropna()
        if not distances.empty:
            idx = distances.idxmin()
            nearest = parent_tree.loc[idx]
            logging.debug(f"[DEBUG] Closest parent: {nearest['NAME']}")
            return [nearest]

    # 4️⃣ LAST RESORT: return all
    logging.warning("[WARNING] No parent match found, returning all")
    return [row for _, row in parent_tree.iterrows()]

import time

def t(msg, start=[time.perf_counter()]):
    now = time.perf_counter()
    print(f"[TIMER] {msg}: {now - start[0]:.3f}s")
    start[0] = now



def pd_not_empty(val):
    """Helper check to filter out NaN, None, or blank spatial strings."""
    if val is None:
        return False
    if isinstance(val, float) and pd.isna(val):
        return False
    if str(val).strip() in ['', 'nan', 'None']:
        return False
    return True


def filter_gdf_by_overlap(children_gdf, parent_geometry, layer_type: str, threshold_dict, default_threshold=0.40):
    """
    Pure spatial math function: Takes a child GeoDataFrame and a parent geometry,
    projects them to EPSG:3857, calculates proportional intersection area,
    and returns a filtered copy of the children exceeding the configured threshold.
    """
    import geopandas as gpd

    if children_gdf is None or children_gdf.empty or parent_geometry is None:
        return gpd.GeoDataFrame(columns=children_gdf.columns) if children_gdf is not None else None

    # 1. Resolve dynamic threshold configuration
    primary_type = layer_type.split('/')[0].strip()
    threshold = threshold_dict.get(primary_type, threshold_dict.get(layer_type, default_threshold))
    print(f"[SPATIAL MATH] Filtering {layer_type} with threshold: {threshold}")

    # 2. Fast Bounding-Box pre-filter to drop completely unrelated features immediately
    if children_gdf.crs is None:
        children_gdf = children_gdf.set_crs("EPSG:4326")
    candidates = children_gdf[children_gdf.geometry.intersects(parent_geometry)].copy()

    if candidates.empty:
        return candidates

    # 3. Project to Equal-Area/Metric CRS for precise ratio calculations
    proj_crs = "EPSG:3857"
    parent_geom_proj = gpd.GeoSeries([parent_geometry], crs="EPSG:4326").to_crs(proj_crs).iloc[0]
    candidates_proj = candidates.to_crs(proj_crs)

    # 4. Clean up invalid/empty geometries
    valid_mask = candidates_proj.geometry.notnull() & ~candidates_proj.geometry.is_empty
    valid_candidates_proj = candidates_proj[valid_mask].copy()

    if valid_candidates_proj.empty:
        return candidates.iloc[0:0] # Return empty GDF preserving original structure

    # 5. Vectorized Math Operations
    overlap_areas = valid_candidates_proj.geometry.intersection(parent_geom_proj).area
    child_areas = valid_candidates_proj.geometry.area.replace(0, 1e-9) # Prevent division-by-zero

    valid_candidates_proj['_overlap_ratio'] = overlap_areas / child_areas

    # 6. Print diagnostics
    for idx, row in valid_candidates_proj.iterrows():
        name = row.get("name") or row.get("NAME") or f"Index-{idx}"
        ov = row['_overlap_ratio']
        print(f"📐 [{layer_type.upper()}] -> {name}: overlap={ov:.3f} {'✅' if ov >= threshold else '❌'}")

    # 7. Map back to original unprojected indices and return
    matched_indices = valid_candidates_proj[valid_candidates_proj['_overlap_ratio'] >= threshold].index
    return candidates.loc[matched_indices].copy()

import logging
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

import logging
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


import logging
import pandas as pd
from shapely.geometry import Point

def ensure_treepolys_with_index(
    *,
    territory: str | None,
    sourcepath: str | None,
    here=None,
    boundary_geom=None,
    resolved_levels: dict[str, dict[int, str]],
    parent_levels: dict[int, str],
):
    logging.info("==================================================")
    logging.info("🚀 [DEBUG START] ensure_treepolys_with_index")
    logging.info(f"   ↳ Initial Geo_index size: {len(Geo_index)}")
    logging.info(f"   ↳ territory: {territory}")
    logging.info(f"   ↳ sourcepath: {sourcepath}")
    logging.info(f"   ↳ here (raw): {here}")
    logging.info(f"   ↳ boundary_geom provided: {boundary_geom is not None}")
    logging.info(f"   ↳ resolved_levels: {resolved_levels}")
    logging.info(f"   ↳ parent_levels: {parent_levels}")

    ROOT = "UNITED_KINGDOM"

    if ROOT not in Geo_index:
        logging.debug(f"[INIT] Injecting default ROOT '{ROOT}' into Geo_index")
        Geo_index[ROOT] = {
            "level": "country",
            "name": ROOT,
            "parent": None,
            "children": [],
            "roid": [54.5, -2.5],
            "fid": 238,
        }
    else:
        logging.debug(f"[INIT] ROOT '{ROOT}' already exists in Geo_index")

    if boundary_geom is not None:
        boundary_geom = boundary_geom.buffer(0)
        logging.debug("   ↳ Applied buffer(0) to boundary_geom to sanitize geometry")

    if not resolved_levels or len(resolved_levels) != 1:
        logging.error(f"❌ Invalid resolved_levels configuration: {resolved_levels}")
        raise ValueError("Invalid resolved_levels configuration.")

    (_, elevels), = resolved_levels.items()
    sourcepath = sourcepath or territory

    # ------------------------------------------------------------------
    # 🌟 GEOMETRY & POINT PATH RESOLUTION
    # ------------------------------------------------------------------
    candidate_paths = set()
    if sourcepath:
        candidate_paths.add(sourcepath)

    coords = parse_coords(here) if ("parse_coords" in globals() and here) else []
    anchor_points = [Point(lon, lat) for lat, lon in coords] if coords else []

    if coords and "classify_record_coords" in globals():
        lat, lon = coords[0]
        classification = classify_record_coords(lat, lon, sourcepath, parent_levels)
        derived_path = classification.get("_derived_path")
        if derived_path:
            logging.info(f"📍 Derived territory path from point ({lat}, {lon}): {derived_path}")
            candidate_paths.add(derived_path)

    # Pick best path from candidates if sourcepath was missing/partial
    effective_sourcepath = sourcepath
    if not effective_sourcepath and candidate_paths:
        effective_sourcepath = next(iter(candidate_paths))

    MAP_LAYERS = globals().get("MAP_LAYERS", {})
    if isinstance(MAP_LAYERS, list):
        MAP_LAYERS = {l.get("key", idx): l for idx, l in enumerate(MAP_LAYERS)}

    layer_defs = {l.get("key", k): l for k, l in MAP_LAYERS.items()}

    for k, l in MAP_LAYERS.items():
        layer_key = l.get("key", k)
        if layer_key not in Treepolys:
            Treepolys[layer_key] = gpd.GeoDataFrame()

    # ------------------------------------------------------------------
    # MAIN PROCESSING ENGINE LOOP
    # ------------------------------------------------------------------
    dynamic_steps = [ROOT]
    raw_steps = stepify(effective_sourcepath) if effective_sourcepath else []

    if raw_steps and normalname(raw_steps[0]) != normalname(ROOT):
        steps = [ROOT] + raw_steps
    else:
        steps = raw_steps if raw_steps else [ROOT]

    # Target depth corresponds to the target node level T
    target_depth = len(steps) - 1 if len(steps) > 1 else max(elevels.keys())
    # Required traversal max level is Target Depth + 1 (Children level)
    max_required_level = target_depth + 1

    logging.info(f"   ↳ Parsed Steps: {steps} | Target Depth (T): {target_depth} | Max Target Fetch Level (T+1): {max_required_level}")

    active_parent_rows = {0: [None]}
    fid_to_path = {}
    deepest_path_registered = ROOT

    for level, compound_layer_type in sorted(elevels.items()):
        # Stop execution beyond children level (level > T + 1)
        if level > max_required_level:
            logging.info(f"🛑 Reached depth boundary (Level {level} > {max_required_level}). Halting tree expansion.")
            break

        sub_layers = [l.strip() for l in compound_layer_type.split("/") if l.strip()]
        logging.info(f"🔄 Processing Level {level} with layers: {sub_layers}")

        next_level = level + 1
        if next_level not in active_parent_rows:
            active_parent_rows[next_level] = []

        for layer_type in sub_layers:
            layer = layer_defs.get(layer_type)
            if not layer:
                logging.warning(f"⚠️ Layer definition missing for key={layer_type}")
                continue

            # Determine name filter for current level
            select_name = None
            if level <= target_depth and level < len(steps):
                select_name = steps[level]
                logging.debug(f"   ↳ Level {level} <= Target Depth {target_depth}. Filtering by name: '{select_name}'")
            else:
                # Level == target_depth + 1 (Children): Fetch ALL child geometries inside parent
                logging.debug(f"   ↳ Level {level} is Children Level (T+1). Fetching all children under parent envelope.")

            parent_rows = active_parent_rows.get(level, [None])
            if not parent_rows:
                parent_rows = [None]

            logging.info(f"   ↳ Executing load_layer for level={level}, layer='{layer_type}' across {len(parent_rows)} parent row(s)")
            all_results = []

            for p_idx, parent_row in enumerate(parent_rows):
                if level > 0 and parent_row is not None:
                    p_fid = parent_row.get("FID")
                    parent_path = fid_to_path.get(p_fid, ROOT)
                    expected_type = parent_levels.get(level)
                    actual_type = Geo_index.get(parent_path, {}).get("level")

                    if expected_type and actual_type and expected_type != actual_type:
                        logging.warning(
                            f"❌ [GEO_INDEX SKIP] Skipping parent [{p_idx}] (FID: {p_fid}): "
                            f"Type mismatch! Expected level type '{expected_type}', but Geo_index['{parent_path}'] has level '{actual_type}'."
                        )
                        continue

                src = layer.get("src")
                field = layer.get("field")

                # Handle Virtual / Derived layers with no spatial source
                if not src or not field:
                    logging.info(f"ℹ️ Layer '{layer_type}' has no 'src'/'field' defined (virtual layer). Forwarding parents to Level {next_level}.")
                    if parent_row is not None:
                        active_parent_rows[next_level].append(parent_row)
                    continue

                chosen_src = src[0] if isinstance(src, list) else src
                chosen_field = field[0] if isinstance(field, list) else field

                if isinstance(src, list):
                    is_surrey = effective_sourcepath and "surrey" in str(effective_sourcepath).lower()
                    chosen_idx = next(
                        (i for i, f in enumerate(src) if f and ("surrey" in str(f).lower() if is_surrey else "surrey" not in str(f).lower())),
                        0
                    )
                    chosen_src = src[chosen_idx]
                    chosen_field = field[chosen_idx] if isinstance(field, list) else field

                layer_local = dict(layer)
                layer_local["src"], layer_local["field"] = chosen_src, chosen_field

                try:
                    selected_child_name, tree_gdf, raw_gdf = load_layer(
                        layer=layer_local,
                        level=level,
                        intention_type=layer_type,
                        parent_levels=parent_levels,
                        parent_row=parent_row,
                        select_name=select_name,
                        roid=here,
                        boundary_geom=boundary_geom,
                    )

                    if selected_child_name:
                        norm_child = normalname(selected_child_name)
                        if norm_child not in [normalname(s) for s in dynamic_steps]:
                            dynamic_steps.append(selected_child_name)

                except Exception as e:
                    logging.error(f"❌ load_layer failed at Level {level}, layer '{layer_type}': {e}", exc_info=True)
                    continue

                if tree_gdf is not None and hasattr(tree_gdf, "empty") and not tree_gdf.empty:
                    tree_gdf = tree_gdf.copy()

                    if "FID" not in tree_gdf.columns:
                        if "OBJECTID" in tree_gdf.columns:
                            tree_gdf = tree_gdf.rename(columns={"OBJECTID": "FID"})
                        elif "id" in tree_gdf.columns:
                            tree_gdf = tree_gdf.rename(columns={"id": "FID"})
                        else:
                            tree_gdf["FID"] = tree_gdf.index.astype(int)

                    # Spatial Point fallback filtering when step path is unknown/partial
                    if level <= target_depth and anchor_points and select_name is None:
                        def matches_any_point(geom):
                            if geom is None or geom.is_empty:
                                return False
                            return any(geom.contains(pt) for pt in anchor_points)

                        spatial_mask = tree_gdf.geometry.apply(matches_any_point)
                        if spatial_mask.any():
                            tree_gdf = tree_gdf[spatial_mask]

                    resolved_p_path = (
                        ROOT if level == 0
                        else (fid_to_path.get(parent_row["FID"], ROOT) if parent_row is not None else ROOT)
                    )
                    tree_gdf["_parent_path"] = resolved_p_path
                    all_results.append(tree_gdf)

            if not all_results:
                logging.warning(f"⚠️ [NO RESULTS] all_results empty for level={level}, layer_type='{layer_type}'!")
                continue

            tree_gdf = pd.concat(all_results, ignore_index=True)

            existing = get_treepoly(layer_type)
            if existing is None or "FID" not in existing.columns or "FID" not in tree_gdf.columns:
                new_tree_gdf = tree_gdf
            else:
                new_tree_gdf = tree_gdf[~tree_gdf["FID"].isin(existing["FID"])]

            upserted_gdf = upsert_geodf(existing, new_tree_gdf)
            set_treepoly(layer_type, upserted_gdf)

            # Populate Geo_index & map FIDs
            for idx, row in tree_gdf.iterrows():
                raw_name = row.get("NAME")
                child_name = f"UNNAMED_{idx}" if (pd.isna(raw_name) or raw_name is None) else normalname(str(raw_name))

                parent_path = row.get("_parent_path", ROOT)
                this_path = ROOT if (level == 0 and child_name == ROOT) else f"{parent_path}/{child_name}"

                roid_coords = None
                if hasattr(row, "geometry") and row.geometry is not None:
                    try:
                        centroid_point = row.geometry.representative_point()
                        roid_coords = [float(centroid_point.y), float(centroid_point.x)]
                    except Exception:
                        pass

                row_fid = int(row["FID"]) if pd.notna(row.get("FID")) else None

                if this_path not in Geo_index:
                    Geo_index[this_path] = {
                        "level": layer_type,
                        "name": child_name,
                        "parent": parent_path if level > 0 else None,
                        "children": [],
                        "roid": roid_coords,
                        "fid": row_fid,
                    }
                else:
                    entry = Geo_index[this_path]
                    if entry.get("fid") is None and row_fid is not None:
                        entry["fid"] = row_fid
                    if entry.get("roid") is None and roid_coords is not None:
                        entry["roid"] = roid_coords

                # FIX: Prevent appending the root node to its own children list
                if parent_path in Geo_index and this_path != parent_path:
                    if this_path not in Geo_index[parent_path]["children"]:
                        Geo_index[parent_path]["children"].append(this_path)

                fid_to_path[row["FID"]] = this_path

                row_copy = row.copy()
                row_copy["_parent_path"] = this_path

                existing_fids = {
                    r["FID"] for r in active_parent_rows[next_level]
                    if r is not None and "FID" in r
                }
                if row_copy["FID"] not in existing_fids:
                    active_parent_rows[next_level].append(row_copy)

                deepest_path_registered = this_path

    # Path Traversal & Fallback Resolution
    active_steps = steps if len(steps) > 1 else dynamic_steps
    current_path = ""
    deepest_valid_path = ROOT

    for step in active_steps:
        normalized_step = normalname(step)
        current_path = f"{current_path}/{normalized_step}" if current_path else normalized_step
        if current_path in Geo_index:
            deepest_valid_path = current_path
        else:
            break

    final_path = deepest_valid_path if deepest_valid_path in Geo_index else deepest_path_registered

    # Extract the leaf component (e.g., 'THE_BENTLEYS_AND_FRATING')
    leaf_name = final_path.split("/")[-1]

    # Construct the full nested map file path
    match_full_filepath = f"{final_path}/{leaf_name}-MAP.html"

    logging.info(f"🎯 Final Resolved Target Path: '{final_path}' | Map File Path: '{match_full_filepath}'")
    return match_full_filepath, Geo_index

def layer_loaded(layer_key):
    return (
        layer_key in Treepolys
        and Treepolys[layer_key] is not None
        and not Treepolys[layer_key].empty
    )


def empty_gdf():
    return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def load_candidates():
    global Candidates
    # --- Candidates ---
    print(f"___Creating CANDIDATES data and file")
    if not os.path.exists(CANDIDATES_FILE) or os.path.getsize(CANDIDATES_FILE) == 0:

        Candidates_data = pd.read_excel(
            f"{workdirectories['candidatedir']}/Candidate_Placement_for_Surrey-2.xlsx"
        )

        for _, row in Candidates_data.iterrows():

            ward = row.get("Division")
            c1 = row.get("Candidate 1")
            c2 = row.get("Candidate 2")

            # Skip row if ward OR either candidate is missing
            if pd.isna(ward) or pd.isna(c1) or pd.isna(c2):
                continue

            # Now safe to normalise
            nodename = normalname(str(ward))
            C1 = normalname(str(c1))
            C2 = normalname(str(c2))

            Candidates["division"][nodename] = {
                "Candidate_1": C1,
                "Candidate_2": C2
            }


        with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
            json.dump(Candidates, f, indent=2, ensure_ascii=False)


    else:
        # Load from file without overwriting keys
        with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            Candidates["ward"].update(data.get("ward", {}))
            Candidates["division"].update(data.get("division", {}))
            Candidates["constituency"].update(data.get("constituency", {}))


def load_last_results():
    global LastResults

    if not os.path.exists(LAST_RESULTS_FILE) or os.path.getsize(LAST_RESULTS_FILE) == 0:
        # --- Constituencies ---
        Con_Results_data = pd.read_excel(
            f"{workdirectories['resultdir']}/HoC-GE2024-results-by-constituency.xlsx"
        )

        for _, row in Con_Results_data.iterrows():
            nodename = normalname(row["Constituency name"])
            party = normalname(row["First party"])
            electorate = int(row["Electorate"]) if pd.notna(row["Electorate"]) else None
            turnout = round(float(row["Turnout"]), 6) if "Turnout" in row and pd.notna(row["Turnout"]) else None

            LastResults["constituency"][nodename] = {
                "FIRST": party,
                "TURNOUT": turnout,
                "ELECTORATE": electorate
            }

        # --- Wards ---
        Ward_Results_data = pd.read_excel(
            f"{workdirectories['candidatedir']}/LEH-Candidates-2023.xlsx"
        )
        Ward_Results_data = Ward_Results_data.loc[Ward_Results_data["WINNER"] == 1]

        for _, row in Ward_Results_data.iterrows():
            nodename = normalname(row["NAME"])
            party = normalname(row["PARTYNAME"])
            electorate = int(row["ELECT"]) if pd.notna(row["ELECT"]) else None
            turnout = round(float(row["TURNOUT"]), 6) if "TURNOUT" in row and pd.notna(row["TURNOUT"]) else None

            LastResults["ward"][nodename] = {
                "FIRST": party,
                "TURNOUT": turnout,
                "ELECTORATE": electorate
            }

        # --- Divisions ---
        Level4_Results_data = pd.read_excel(
            f"{workdirectories['resultdir']}/opencouncildata_councillors.xlsx"
        )

        for _, row in Level4_Results_data.iterrows():
            nodename = normalname(row["Ward Name"])
            party = normalname(row["Party Name"])

            LastResults["division"][nodename] = {
                "FIRST": party
            }

        # --- Persist ---
        with open(LAST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(LastResults, f, indent=2, ensure_ascii=False)

    else:
        # Load from file without overwriting keys
        with open(LAST_RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            LastResults["ward"].update(data.get("ward", {}))
            LastResults["division"].update(data.get("division", {}))
            LastResults["constituency"].update(data.get("constituency", {}))


#Treepolys = {
#    'country': empty_gdf(),
#    'nation': empty_gdf(),
#    'county': empty_gdf(),
#    'constituency': empty_gdf(),
#    'ward': empty_gdf(),
#    'division': empty_gdf()
#}


def get_treepoly(layer_type: str):
    return Treepolys.get(layer_type)

def set_treepoly(layer_type: str, gdf: gpd.GeoDataFrame):
    Treepolys[layer_type] = gdf

def has_treepoly(layer_type: str) -> bool:
    return layer_type in Treepolys and not Treepolys[layer_type].empty


# original dict
_LEVEL_ZOOM_MAP = {
    'country': 12,
    'nation': 13,
    'county': 14,
    'constituency': 15,
    'ward': 16,
    'division': 16,
    'polling_district': 17,
    'walk': 17,
    'walkleg': 18,
    'street': 18
}

# share task and outcome tags for each election

OPTIONS = {
    "ACC": False,
    "DEVURLS": {},
    "territories": {},
    "yourparty": {},
    "previousParty": {},
    "resources" : {},
    "areas" : {},
    "candidate" : {},
    "chair" : {},
    "tags": {},
    "task_tags": {},
    "autofix" : {},
    "VNORM" : {},
    "VCO" : {},
    "streams" : {},
    "stream_table": {}
    # Add more mappings here if needed
}


TABLE_TYPES  = {
    "resources": "Resources",
    "events": "Event Markers",
    "DQstats": "Import Data Quality",
    "stream_table": "Import Data Streams",
    "nodelist_xref" : "Nodelist xref",
    "country_layer" : "Countries",
    "nation_layer" : "Nations",
    "county_layer" : "Counties",
    "constituency_layer" : "Constituencies",
    "ward_layer" : "Wards",
    "division_layer" : "Divisions",
    "polling_district_layer" : "Polling Districts",
    "walk_layer" : "Walks",
    "street_layer" : "Streets",
    "walkleg_layer" : "Walklegs"
}
# make it read-only
LEVEL_ZOOM_MAP = MappingProxyType(_LEVEL_ZOOM_MAP)

ElectionTypes = {"W":"Westminster","C":"County","B":"Borough","P":"Parish","U":"Unitary"}
VID = {"U" : "Uncanvassed","R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"Independent","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}
VNORM = {"OTHER":"O","REFORM" : "R" , "REFORM_DERBY" : "R" ,"REFORM_UK" : "R" ,"REF" : "R", "RUK" : "R","R" :"R","CONSERVATIVE_AND_UNIONIST" : "C","CONSERVATIVE" : "C", "CON" : "C", "C":"C","LABOUR_PARTY" : "S","LABOUR" : "S", "LAB" :"S", "L" : "S", "LIBERAL_DEMOCRATS" :"LD" ,"LIBDEM" :"LD" , "LIB" :"LD","LD" :"LD", "GREEN_PARTY" : "G" ,"GREEN" : "G" ,"G":"G", "INDEPENDENT" : "I", "IND" : "I" ,"I" : "I" ,"PLAID_CYMRU" : "PC" ,"PC" : "PC" ,"SNP": "SNP" ,"MAYBE" : "Z" ,"WONT_VOTE" : "W" ,"WONT_SAY" : "X" , "SDLP" : "S", "SINN_FEIN" : "SF", "SPK": "N", "TUV" : "C", "UUP" : "C", "DUP" : "C","APNI" : "N", "INET": "I", "NIP": "I","PBPA": "I","WPB": "S","OTHER" : "O"}
VCO = {
    "S": "#DC241F",   # Labour (Official Red)
    "C": "#0087DC",   # Conservative (Official Blue)
    "LD": "#FAA61A",  # Liberal Democrats (Official Gold/Yellow)
    "G": "#6AB023",   # Green Party (Official Green)
    "R": "#00BFFF",   # Reform UK (Official Turquoise/Cyan)
    "I": "#4B0082",   # Independent (Indigo)
    "PC": "#990033",  # Plaid Cymru (Official Party Crimson)
    "SD": "#E65C00",  # SDP (Orange)
    "O": "#8B4513",   # Other (Brown)
    "Z": "#7F8C8D",   # Maybe (Neutral Muted Grey)
    "W": "#DCDCDC",   # Won't Vote (Light Grey fallback - pure #FFFFFF is invisible on white lists!)
    "X": "#34495E"    # Won't Say (Dark Charcoal Grey)
}
onoff = {"on" : 1, 'off': 0}
data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))
autofix = {0,1,2,3,4}

# state.py
Treepolys: dict[str, gpd.GeoDataFrame] = {}


# state.py or config.py

MAP_LAYERS = {
    "marker": {
        "key": "marker", "mytag": "marker", "overlay": True, "control": True, "show": False, "type": "marker"
    },
    "country": {
        "key": "country", "mytag": "country", "level": 0, "type": "node",
        "overlay": True, "control": True, "show": False,
        "src": "World_Countries_(Generalized)_9029012925078512962.geojson",
        "field": "COUNTRY", "out": "Country_Boundaries.geojson", "method": "filter",
        "options": {"color": "#0F172A", "fontColor": "#0F172A", "weight": 3.0, "fillColor": "none", "fillOpacity": 0.0}
    },
    "nation": {
        "key": "nation", "mytag": "nation", "level": 1, "type": "node",
        "overlay": True, "control": True, "show": False,
        "src": "Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson",
        "field": "CTRY21NM", "out": "Nation_Boundaries.geojson", "method": "filter",
        "options": {"color": "#1E293B", "fontColor": "#1E293B", "weight": 3.0, "fillColor": "none", "fillOpacity": 0.0}
    },
    "county": {
        "key": "county", "mytag": "county", "level": 2, "type": "node",
        "overlay": True, "control": True, "show": False,
        "src": "Counties_and_Unitary_Authorities_December_2024_Boundaries_UK_BGC_-917943173031721243_degrees.geojson",
        "field": "CTYUA24NM", "out": "County_Boundaries.geojson", "method": "filter",
        "options": {"color": "#475569", "fontColor": "#475569", "weight": 2.5, "fillColor": "#F1F5F9", "fillOpacity": 0.35}
    },
    "constituency": {
        "key": "constituency", "mytag": "constituency", "level": 3, "type": "node",
        "overlay": True, "control": True, "show": False,
        "src": "Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson",
        "field": "PCON24NM", "out": "Constituency_Boundaries.geojson", "method": "intersect",
        "options": {"color": "#0369A1", "fontColor": "#0369A1", "weight": 2.0, "fillColor": "#E0F2FE", "fillOpacity": 0.25}
    },
    "ward": {
        "key": "ward", "mytag": "ward", "level": 4, "type": "node",
        "overlay": True, "control": True, "show": False,
        "src": "Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson",
        "field": "WD24NM", "out": "Ward_Boundaries.geojson", "method": "intersect",
        "options": {"color": "#2E6FBB", "fontColor": "#2E6FBB", "weight": 2.5, "fillColor": "#A9C8F5", "fillOpacity": 0.18}
    },
    "division": {
        "key": "division", "mytag": "division", "level": 4, "type": "node",
        "overlay": True, "control": True, "show": False,
        "src": ["County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson", "Revised_Surrey_Proposed_Divisions.geojson"],
        "field": ["CED23NM", "Division_n"], "out": "Division_Boundaries.geojson", "method": "intersect",
        "options": {"color": "#D95F02", "fontColor": "#D95F02", "weight": 2.5, "fillColor": "#F6C28B", "fillOpacity": 0.12, "dashArray": "8,5"}
    },
    "walk": {
        "key": "walk", "mytag": "walk", "level": 5, "type": "node",
        "overlay": True, "control": True, "show": False,
        "options": {"color": "#0F766E", "fontColor": "#0F766E", "weight": 1.0, "fillColor": "#FBCFE8", "fillOpacity": 0.5, "dashArray": "2,4"}
    },
    "street": {
        "key": "street", "mytag": "street", "level": 6, "type": "node",
        "overlay": True, "control": True, "show": False,
        "src": "UK-ROADS.gpkg",        # Pre-downloaded regional OS linestring network
        "field": "name1",                       # Attribute field containing street names
        "out": "Street_Geometries.gpkg",    # Standard output GeoJSON path
        "method": "linestringArea",                # Triggers linestring spatial slicing
        "options": {"color": "#0F766E", "fontColor": "#0F766E", "weight": 2.5, "fillColor": "none", "fillOpacity": 0.0}
    },
    "walkleg": {
        "key": "walkleg", "mytag": "walkleg", "level": 6, "type": "node",
        "overlay": True, "control": True, "show": False,
        "options": {"color": "#115E59", "fontColor": "#115E59", "weight": 1.0, "fillColor": "#FBCFE8", "fillOpacity": 0.5}
    },
    "elector": {"key": "elector", "mytag": "elector", "overlay": True, "control": True, "show": False, "type": "marker"},
    "result": {"key": "result", "mytag": "result", "overlay": True, "control": True, "show": False, "type": "marker"},
    "target": {"key": "target", "mytag": "target", "overlay": True, "control": True, "show": False, "type": "marker"},
    "data": {"key": "data", "mytag": "data", "overlay": True, "control": True, "show": False, "type": "marker"},
}


levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'#006064',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }






kanban_options = [
    {"code": "R", "label": "Resourcing"},
    {"code": "P", "label": "Post-Bundling"},
    {"code": "L", "label": "Informing"},
    {"code": "C", "label": "Canvassing"},
    {"code": "K", "label": "Klosing"},
    {"code": "T", "label": "Telling"}
]


# this is for creating a new mapfile when one does not exist.
TypeMaker = { 'nation' : 'downbut','county' : 'downbut', 'constituency' : 'downbut' , 'ward' : 'downbut', 'division' : 'downbut', 'polling_district' : 'downbut', 'walk' : 'downbut', 'street' : 'walkdownST', 'walkleg' : 'WKdownST'}


ROOT_LEVEL = {
    "W": 3,
    "C": 2,
    "U": 2,
    "B": 4,
    "P": 4,
}


# Threshold configuration: (Intersection Area / Child Area) >= Threshold
OVERLAP_THRESHOLDS = {
    "country": 0.90,           # High precision: should be almost completely inside
    "region": 0.75,            # Minor boundary clipping allowed
    "county": 0.60,            # Forgiving of coastline/river edge mismatches
    "constituency": 0.50,      # Balanced threshold for parliamentary lines
    "ward": 0.25,              # Forgiving enough for Windlesham / Heathlands boundary bleed
    "division": 0.25,          # Similar to wards
    "polling_district": 0.20,  # Lower threshold: small shapes clipping complex edges
    "street": 0.15,            # Streets can run right along borders; low threshold prevents exclusion
    "walk": 0.10,              # Route paths frequently cross borders
    "walkleg": 0.05            # Highly granular slivers
}
DEFAULT_THRESHOLD = 0.50       # Fallback safety blanket

Candidates = {
    "ward": {},
    "division": {},
    "constituency": {},
}


LastResults = {
    "ward": {},
    "division": {},
    "constituency": {},
}

areaoptions = ["UNITED_KINGDOM/ENGLAND/SURREY/SURREY_HEATH/SURREY_HEATH-MAP.html"]

IGNORABLE_SEGMENTS = {"PDS", "WALKS", "DIVS", "WARDS"}

FILE_SUFFIXES = [
    "-PRINT.html", "-MAP.html","-CAL.html", "-WALKS.html",
    "-ZONES.html", "-PDS.html", "-DIVS.html", "-WARDS.html"
]



import logging
logging.getLogger("pyproj").setLevel(logging.WARNING)

# Setup logger
logging.basicConfig(
    level=logging.DEBUG,  # or INFO
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)



#or i, (key, fg) in enumerate(Featurelayers.items(), start=1):
#    fg.id = i
#    fg.type = [
#        'country','nation', 'county', 'constituency', 'ward', 'division', 'polling_district',
#        'walk', 'walkleg', 'street', 'result', 'target', 'data', 'special'
#    ][i - 1]

# Overall progress fractions for each stage
STAGE_FRACTIONS = {
    "sourcing": 0.1,        # 0% → 10%
    "normz": 0.1,           # 10% → 20%
    "address_norm": 0.4,    # 20% → 60%
    "assign_areas": 0.25,   # 60% → 85%
    "assign_walks": 0.15    # 85% → 100%
}


progress = {
    "stages": STAGE_FRACTIONS,
    "election": "",
    "status": "idle",       # Can be 'idle', 'running', 'complete', 'error'
    "percent": 0,           # Integer from 0 to 100
    "targetfile": "test.csv",
    "message": "Waiting...", # Optional string
    "dqstats_html": ""
    }


def update_progress(progress, stage_name, stage_local_fraction, message=""):
    stages = progress["stages"]

    accumulated = 0
    for name, fraction in stages.items():
        if name == stage_name:
            break
        accumulated += fraction

    stage_fraction = stages.get(stage_name, 0)

    progress["current_stage"] = stage_name
    progress["stage_progress"] = round(stage_local_fraction * 100, 2)
    progress["percent"] = round(
        100 * (accumulated + stage_local_fraction * stage_fraction),
        2
    )
    progress["status"] = "running"
    progress["message"] = message



DQstats = {
"df": pd.DataFrame(),  # initially empty
}

layeritems = []
#allelectors = pd.read_csv(config.workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
# need a keyed dict indicating last recorded winning first party name for a given normalised node name



load_last_results()
load_candidates()
