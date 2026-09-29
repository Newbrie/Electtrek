import config
from config import workdirectories, DEVURLS, WALK_GEOM_FILE
from folium import FeatureGroup
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
from folium import GeoJson, Tooltip, Popup
from shapely.geometry import Point, Polygon, MultiPoint
from shapely import crosses, contains,covers, union, envelope, intersection
from shapely.ops import nearest_points, split, unary_union
from shapely import count_coordinates
from shapely.geometry import box, LineString
from shapely.geometry.base import BaseGeometry
# Fix invalid geometries dynamically using Shapely/GeoPandas
from shapely.validation import make_valid

import hashlib

from geovoronoi import voronoi_regions_from_coords
import numpy as np
import folium
from datetime import datetime, timedelta, date
import elections
import json
import os
import html
import pandas as pd
import re
import math
import colorsys
import state
from state import stepify, pathify, derive_territory, normalname
from matplotlib.colors import to_hex, to_rgb
import geopandas as gpd
# ✅ CORRECT

from collections import defaultdict
from typing import DefaultDict
from pathlib import Path

from pyogrio import read_dataframe, read_info
from scipy.spatial import cKDTree

import osmnx as ox

# Ensure OSMnx caching is enabled for performance
ox.settings.use_cache = True
ox.settings.log_console = False



import logging

logger = logging.getLogger(__name__)


# state.py
Treepolys: dict[str, gpd.GeoDataFrame] = {}

Geo_index = {}


ROOT = "UNITED_KINGDOM"

REVISED = "Surrey" # use the Revised Surrey Division_Boundaries


# state.py or config.py

MAP_LAYERS = {
    "marker": {
        "key": "marker", "mytag": "marker", "overlay": True, "control": True, "show": False, "type": "marker"
    },
    "country": {
        "key": "country", "mytag": "country", "level": 0, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": None,
        "aggregation_mode": "selected_name",
        "id_field": "FID",
        "src": "World_Countries_(Generalized)_9029012925078512962.geojson",
        "field": "COUNTRY", "out": "Country_Boundaries.gpkg", "method": "filter",
        "options": {"color": "#0F172A", "fontColor": "#0F172A", "weight": 3.0, "fillColor": "#CBD5E1", "fillOpacity": 0.08}
    },
    "nation": {
        "key": "nation", "mytag": "nation", "level": 1, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": None,
        "aggregation_mode": "selected_name",
        "id_field": "FID",
        "src": "Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson",
        "field": "CTRY21NM", "out": "Nation_Boundaries.gpkg", "method": "filter",
        "options": {"color": "#1E293B", "fontColor": "#1E293B", "weight": 3.0, "fillColor": "#94A3B8", "fillOpacity": 0.12}
    },
    "county": {
        "key": "county", "mytag": "county", "level": 2, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": "nation",
        "aggregation_mode": "selected_name",
        "id_field": "FID",
        "src": "Counties_and_Unitary_Authorities_December_2024_Boundaries_UK_BGC_-917943173031721243_degrees.geojson",
        "field": "CTYUA24NM", "out": "County_Boundaries.gpkg", "method": "filter",
        "options": {"color": "#475569", "fontColor": "#475569", "weight": 2.5, "fillColor": "#F1F5F9", "fillOpacity": 0.35}
    },
    "constituency": {
        "key": "constituency", "mytag": "constituency", "level": 3, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": "county",
        "aggregation_mode": "selected_name",
        "id_field": "FID",
        "src": "Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson",
        "field": "PCON24NM", "out": "Constituency_Boundaries.gpkg", "method": "intersect",
        "options": {"color": "#0369A1", "fontColor": "#0369A1", "weight": 2.0, "fillColor": "#E0F2FE", "fillOpacity": 0.25}
    },
    "ward": {
        "key": "ward", "mytag": "ward", "level": 4, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": "constituency",
        "aggregation_mode": "selected_name",
        "id_field": "FID",
        "src": "Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson",
        "field": "WD24NM", "out": "Ward_Boundaries.gpkg", "method": "intersect",
        "options": {"color": "#2E6FBB", "fontColor": "#2E6FBB", "weight": 2.5, "fillColor": "#A9C8F5", "fillOpacity": 0.18}
    },
    "division": {
        "key": "division", "mytag": "division", "level": 4, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": "constituency",
        "aggregation_mode": "selected_name",
        "src": ["County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson", "Revised_Surrey_Proposed_Divisions.geojson"],
        "field": ["CED23NM", "Division_n"], "out": "Division_Boundaries.gpkg", "method": "intersect",
        "options": {"color": "#D95F02", "fontColor": "#D95F02", "weight": 2.5, "fillColor": "#F6C28B", "fillOpacity": 0.12, "dashArray": "8,5"}
    },
    "walk": {
        "key": "walk", "mytag": "walk", "level": 5, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": "ward",
        "aggregation_mode": "selected_name",
        "src": "walk_geoms.geojson",
        "field": "WalkName",
        "id_field": "FID",
        "out": "Walk_Boundaries.gpkg",
        "fan_out_to_all_parents": True,
        "method": "intersect",
        "simplify_tolerance": None,
        "options": {"color": "#0F766E", "fontColor": "#0F766E", "weight": 1.0, "fillColor": "#FBCFE8", "fillOpacity": 0.5, "dashArray": "2,4"}
    },
    "street": {
        "key": "street", "mytag": "street", "level": 6, "type": "node",
        "overlay": True, "control": True, "show": False,
        "parent_layer": "walk",
        "aggregation_mode": "selected_name",
        "src": "UK-ROADS.gpkg",
        "field": "name1",
        "out": "Street_Geometries.gpkg",
        "fan_out_to_all_parents": True,
        "method": "linestringArea",
        "simplify_tolerance": None,
        "options": {"color": "#0F766E", "fontColor": "#0F766E", "weight": 2.5, "fillColor": "none", "fillOpacity": 0.0}
    },
    "elector": {"key": "elector", "mytag": "elector", "overlay": True, "control": True, "show": False, "type": "marker"},
    "result": {"key": "result", "mytag": "result", "overlay": True, "control": True, "show": False, "type": "marker"},
    "target": {"key": "target", "mytag": "target", "overlay": True, "control": True, "show": False, "type": "marker"},
    "data": {"key": "data", "mytag": "data", "overlay": True, "control": True, "show": False, "type": "marker"},
}

OVERLAP_THRESHOLDS = {
    "country": 0.90,           # High precision: should be almost completely inside
    "region": 0.75,            # Minor boundary clipping allowed
    "county": 0.60,            # Forgiving of coastline/river edge mismatches
    "constituency": 0.50,      # Balanced threshold for parliamentary lines
    "ward": 0.25,              # Forgiving enough for Windlesham / Heathlands boundary bleed
    "division": 0.25,          # Similar to wards
    "polling_district": 0.20,  # Lower threshold: small shapes clipping complex edges
    "street": 0.15,            # Streets can run right along borders; low threshold prevents exclusion
    "walk": 0.15
}
DEFAULT_THRESHOLD = 0.50       # Fallback safety blanket



# Cache key includes the REVISED flag state so toggling REVISED reloads correctly


LAYER_CACHE = {}

def compute_font_size(days_to, min_size=10, max_size=28, default_size=14):
    """
    Computes a dynamic font size based on how many days remain until an event.
    Closer events get larger text; distant events get smaller text.
    """
    try:
        days = int(days_to)
    except (TypeError, ValueError):
        return default_size

    # Handle past events (negative days): keep them small/subdued
    if days < 0:
        return min_size

    # Inverse scaling: 0 days away = max_size, scaling down as days increase
    # Using a logarithmic or inverse decay curve works well so that changes
    # are dramatic close to zero and flatten out for distant future dates.
    # Formula: max_size - (days / scaling_factor), bounded between min_size and max_size

    scaling_factor = 10.0  # Adjust this to change how quickly text shrinks with time
    computed = max_size - (days / scaling_factor)

    return max(min_size, min(max_size, int(round(computed))))

def clear_treepolys(from_level=None):
    if from_level is None:
        for k in Treepolys:
            Treepolys[k] = gpd.GeoDataFrame()
    else:
        for layer in MAP_LAYERS[from_level:]:
            Treepolys[layer["key"]] = gpd.GeoDataFrame()

def empty_gdf():
    return gpd.GeoDataFrame(
        columns=["FID", "NAME", "geometry"],
        geometry="geometry",
        crs="EPSG:4326"
    )

def _empty_gdf():
    return empty_gdf()

def get_treepoly(layer_type: str):
    return Treepolys.get(layer_type)

def set_treepoly(layer_type: str, gdf: gpd.GeoDataFrame):
    Treepolys[layer_type] = gdf

def has_treepoly(layer_type: str) -> bool:
    return layer_type in Treepolys and not Treepolys[layer_type].empty


def _get_known_name_candidates():
    return ["NAME", "name", "Name", "NAME_0", "NAME_1", "NAME_2", "NAME_3", "CTY24NM", "WD24NM", "PCON24NM"]


def normalize_column_case(gdf: gpd.GeoDataFrame, canonical_names: list[str]) -> gpd.GeoDataFrame:
    """
    For each name in canonical_names, find any column that matches it
    case-insensitively and rename it to the canonical (exact-case) form.

    GPKG/SQLite treats column names case-insensitively, so "Name" and
    "NAME" collide at write time even though pandas happily holds both
    side by side. Renaming in place (rather than add-a-column-then-drop)
    avoids ever creating that collision to begin with.

    If more than one column matches a given canonical name case-insensitively
    (e.g. both "Name" and "NAME" already exist as distinct columns with
    potentially different data), the first match in column order wins and
    is renamed; the rest are dropped, and a warning is logged since this is
    a genuine data decision, not just a formatting nit.
    """
    gdf = gdf.copy()
    rename_map = {}
    drop_cols = []

    for canonical in canonical_names:
        matches = [c for c in gdf.columns if c.upper() == canonical.upper()]
        if not matches:
            continue
        if canonical in matches:
            # Exact-case canonical column already exists; drop any other
            # case-variant duplicates, keeping the canonical one as-is.
            extras = [c for c in matches if c != canonical]
            if extras:
                logging.warning(
                    f"[SCHEMA] Column '{canonical}' already exists alongside "
                    f"case-variant duplicate(s) {extras}; dropping duplicate(s)."
                )
                drop_cols.extend(extras)
            continue

        # No exact-case canonical column yet; promote the first case-variant match.
        keep, *extras = matches
        rename_map[keep] = canonical
        if extras:
            logging.warning(
                f"[SCHEMA] Multiple case-variant columns matched '{canonical}': "
                f"{matches}; renaming '{keep}' -> '{canonical}' and dropping {extras}."
            )
            drop_cols.extend(extras)

    if drop_cols:
        gdf = gdf.drop(columns=drop_cols)
    if rename_map:
        gdf = gdf.rename(columns=rename_map)

    return gdf

def get_layer_gdf(key: str, node_path=None):
    """Loads and standardizes a GeoDataFrame for a given layer key from global MAP_LAYERS.

    Uses resolved absolute file paths for cache keying to prevent cache misses caused
    by node_path structural variances.
    """
    global LAYER_CACHE
    from state import stepify

    if key not in MAP_LAYERS:
        logger.error(f"❌ Key '{key}' not found in global MAP_LAYERS.")
        return _empty_gdf()

    layer_cfg = MAP_LAYERS[key]
    src_val = layer_cfg.get("src")
    out_val = layer_cfg.get("out")

    if not src_val:
        logger.warning(f"⚠️ Layer '{key}' has no 'src' specified in MAP_LAYERS.")
        return _empty_gdf()

    # 1. Determine REVISED setting logic
    revised_setting = str(globals().get("REVISED", "")).strip().upper()
    current_county = ""
    if node_path:
        steps = stepify(node_path)
        current_county = str(steps[2]).strip().upper() if len(steps) > 2 else ""

    is_revised = bool(
        revised_setting and current_county and (revised_setting == current_county)
    )

    # 2. Resolve source file path before cache key creation
    src_idx = 1 if (is_revised and isinstance(src_val, list) and len(src_val) > 1) else 0
    raw_src = src_val[src_idx] if isinstance(src_val, list) else src_val
    raw_out = out_val

    if not raw_src:
        logger.warning(f"⚠️ Layer '{key}' has an empty path value in MAP_LAYERS.")
        return _empty_gdf()

    # --- LEVEL-AWARE REGIONAL SCOPING FOR CACHE ---
    scoped_out_name = raw_out
    if key in ["ward", "division", "walk"] and current_county:
        base_out_name, out_ext = os.path.splitext(raw_out)
        scoped_out_name = f"{base_out_name}_{current_county}{out_ext}"

    bounddir = workdirectories.get("bounddir", "")
    if not os.path.isabs(raw_src) and bounddir:
        src = os.path.abspath(os.path.join(bounddir, raw_src))
        out = os.path.abspath(os.path.join(bounddir, scoped_out_name))
    else:
        src = os.path.abspath(raw_src)
        out = os.path.abspath(scoped_out_name)

    # --- ROBUST CACHE CHECK ---
    if os.path.exists(out) and os.path.getsize(out) > 100:
        logger.info(f"⚡ Using cached/filtered efficiency file for key '{key}': {out}")
        src = out
    else:
        logger.info(f"🐢 Efficiency file missing or empty; falling back to raw source for key '{key}': {src}")

    # 3. Use absolute file path and mtime as the deterministic cache key
    if not os.path.exists(src):
        logger.warning(f"⚠️ Layer file missing or does not exist for key '{key}': {src}")
        return _empty_gdf()

    file_mtime = os.path.getmtime(src)
    cache_key = (key, src, file_mtime)

    # 4. Check Cache
    if cache_key in LAYER_CACHE:
        logger.debug(f"⚡ Cache HIT for layer '{key}' [{cache_key}]")
        return LAYER_CACHE[cache_key]

    logger.info(f"🐢 Cache MISS for layer '{key}'. Loading from disk: {src}")

    # 5. Disk Read & Standardization
    try:
        try:
            gdf = gpd.read_file(src, engine="pyogrio")
        except Exception:
            gdf = gpd.read_file(src)

        if gdf.empty:
            return _empty_gdf()

        # Standardize CRS
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        # ------------------------------------------------------------
        # Standardize casing for our reserved columns FIRST. GPKG/SQLite
        # is case-insensitive on column names, so any source column that
        # is a case-variant of one of these (e.g. "Name", "Fid", "Id")
        # must be reconciled before we add our own canonically-cased
        # versions, or we end up creating a collision at write time.
        # ------------------------------------------------------------
        gdf = normalize_column_case(gdf, ["FID", "NAME", "TYPEKEY"])

        # Standardize FID (covers "id" / "OBJECTID" -- "fid" case-variants
        # are already handled by normalize_column_case above)
        if "FID" not in gdf.columns:
            for candidate in ["id", "OBJECTID"]:
                ci_matches = [c for c in gdf.columns if c.upper() == candidate.upper()]
                if ci_matches:
                    gdf = gdf.rename(columns={ci_matches[0]: "FID"})
                    break
            else:
                gdf["FID"] = range(1, len(gdf) + 1)

        gdf["FID"] = pd.to_numeric(gdf["FID"], errors="coerce")
        if gdf["FID"].isnull().any():
            gdf["FID"] = gdf["FID"].fillna(pd.Series(range(1, len(gdf) + 1), index=gdf.index))
        gdf["FID"] = gdf["FID"].astype(int)

        # ------------------------------------------------------------
        # Resolve which column should populate NAME. Matching is done
        # case-insensitively against gdf's (now-normalized) columns, since
        # a configured_field like "Name" may have already been renamed to
        # the canonical "NAME" by normalize_column_case above.
        # ------------------------------------------------------------
        configured_field = layer_cfg.get("field")
        if isinstance(configured_field, list):
            configured_field = configured_field[min(src_idx, len(configured_field) - 1)]

        matched_col = None
        if isinstance(configured_field, str):
            ci_matches = [c for c in gdf.columns if c.upper() == configured_field.upper()]
            if ci_matches:
                matched_col = ci_matches[0]

        if not matched_col:
            known_candidates = _get_known_name_candidates()
            matched_col = next((c for c in known_candidates if c in gdf.columns), None)

        if not matched_col:
            pattern = re.compile(r".*(nm|name)$", re.IGNORECASE)
            matched_col = next((c for c in gdf.columns if pattern.match(c) and c.upper() != "NAME"), None)

        if matched_col:
            if matched_col.upper() != "NAME":
                # matched_col is a distinct source field (e.g. "Division_n"),
                # not a case-variant of NAME -- copy its values in.
                gdf["NAME"] = gdf[matched_col]
            # else: matched_col already IS the canonical NAME column
            # (renamed by normalize_column_case above); nothing to do.
        elif "NAME" not in gdf.columns:
            gdf["NAME"] = gdf["FID"].astype(str)

        gdf["TYPEKEY"] = key

        # Pre-build spatial index for spatial filtering performance
        _ = gdf.sindex

        # --- SAFE SAVE TO EFFICIENCY CACHE FILE ---
        if out != raw_out and not os.path.exists(out):
            try:
                os.makedirs(os.path.dirname(out), exist_ok=True)
                if os.path.exists(out):
                    os.remove(out)
                gdf.to_file(out, driver="GPKG" if out.endswith(".gpkg") else "GeoJSON")
                logger.info(f"💾 Created county efficiency cache file: {out}")
            except Exception as write_err:
                logger.warning(f"⚠️ Failed to write efficiency cache file {out}: {write_err}")
                if os.path.exists(out):
                    try:
                        os.remove(out)
                    except:
                        pass

        # Store in cache
        LAYER_CACHE[cache_key] = gdf
        return LAYER_CACHE[cache_key]

    except Exception as e:
        logger.error(f"❌ Error loading GeoDataFrame for layer '{key}' from {src}: {e}")
        return _empty_gdf()


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



# Add the '*' right after typekey

def ensure_4326(gdf):
    """
    If data is naive, set the CRS to 4326.
    If it is already 4326 (or equivalent geographic WGS84), do nothing.
    Otherwise, transform it safely.
    """
    if gdf.crs is None:
        logging.info("[CRS] Data is naive; setting to EPSG:4326")
        return gdf.set_crs("EPSG:4326")

    # Use robust CRS comparison to prevent redundant transformation loops
    target_crs = "EPSG:4326"
    if gdf.crs.to_epsg() == 4326 or gdf.crs == target_crs:
        return gdf

    logging.info(f"[CRS] Data is in {gdf.crs}; transforming to EPSG:4326")
    return gdf.to_crs(target_crs)



def extract_geometry(parent_row):
    """Safely extract Shapely geometry from dict or object types."""
    if parent_row is None:
        return None
    if isinstance(parent_row, dict):
        geom = parent_row.get("geometry")
    else:
        geom = getattr(parent_row, "geometry", None)

    if geom is not None and hasattr(geom, "is_empty") and not geom.is_empty:
        return geom.buffer(0) if isinstance(geom, BaseGeometry) else geom
    return None


def filterArea(
    gdf: gpd.GeoDataFrame,
    *,
    typekey: str = "",
    roid=None,
    name=None,
    parent_row=None,
):
    """
    Lookup polygon(s) in a pre-loaded GeoDataFrame by name, centroid of roid, or parent_row geometry.
    Returns: [nodestep, matched_gdf, full_gdf]
    """
    from state import normalname

    if gdf is None or gdf.empty:
        return None, _empty_gdf(), _empty_gdf()

    gdf = ensure_4326(gdf)

    layer_cfg = MAP_LAYERS.get(typekey, {})
    destination = layer_cfg.get("out", f"{typekey}_Boundaries.geojson")

    matched = gdf.iloc[0:0]

    # 1️⃣ Lookup by name
    if name is not None:
        target = normalname(name.rsplit("/", 1)[-1])
        matched = gdf[gdf["NAME"].astype(str).map(normalname) == target]

    # 2️⃣ Lookup by parent_row geometry
    elif parent_row is not None:
        geom = extract_geometry(parent_row)
        if geom:
            matched = gdf[gdf.intersects(geom)]
        else:
            # Fallback: if parent has no geometry (e.g. root node), accept all candidates
            matched = gdf

    # 3️⃣ Lookup by ROID
    elif roid is not None:
        pt = get_centroid_or_point(roid)
        if pt and not pt.is_empty:
            matched = gdf[gdf.intersects(pt)]
            print(
                f"[filterArea] 📍 Using ROID Centroid ({pt.y:.5f}, {pt.x:.5f}) -> Matched {len(matched)} feature(s)"
            )
        else:
            print(f"[filterArea] ⚠️ Invalid coordinate structure for roid: {roid}")
            matched = gdf
    else:
        # Default fallback if no filters are provided at all
        matched = gdf

    nodestep = normalname(matched["NAME"].iloc[0]) if not matched.empty else None

    if nodestep:
        print(f"[filterArea] Found {nodestep} ({len(matched)} feature(s)), saved to {destination}")
    else:
        print(f"[filterArea] No matching feature found for name {name} or roid {roid}")

    return [nodestep, matched, gdf]

def indexSpatialArea(
    gdf: gpd.GeoDataFrame,
    *,
    typekey: str = "",
    roid=None,
    name=None,
    parent_row=None,
):
    """
    Slices point/vector features from a pre-loaded GeoDataFrame, builds an in-memory cKDTree
    spatial index, and saves the output layer GeoJSON.
    """
    if gdf is None or gdf.empty:
        return {
            "gdf": _empty_gdf(),
            "index": None,
            "coords": np.empty((0, 2)),
            "ids": np.array([]),
        }

    gdf = ensure_4326(gdf)

    layer_cfg = MAP_LAYERS.get(typekey, {})
    destination = layer_cfg.get("out", f"{typekey}_Boundaries.geojson")

    working_geom = extract_geometry(parent_row)
    if working_geom is None and roid is not None:
        working_geom = get_centroid_or_point(roid)

    if working_geom is not None and not gdf.empty:
        sliced_gdf = gdf[gdf.geometry.intersects(working_geom)].copy()
    else:
        sliced_gdf = gdf.copy()

    sliced_gdf.to_file(destination, driver="GeoJSON")

    if not sliced_gdf.empty:
        coords = np.column_stack((sliced_gdf.geometry.y, sliced_gdf.geometry.x))
    else:
        coords = np.empty((0, 2))

    id_field = layer_cfg.get("id_field", layer_cfg.get("field"))
    if isinstance(id_field, list):
        id_field = id_field[0]

    if id_field and id_field in sliced_gdf.columns:
        ids = sliced_gdf[id_field].values
    elif "NAME" in sliced_gdf.columns:
        ids = sliced_gdf["NAME"].values
    elif "FID" in sliced_gdf.columns:
        ids = sliced_gdf["FID"].values
    else:
        ids = np.array([])

    return {
        "gdf": sliced_gdf,
        "index": cKDTree(coords) if len(coords) > 0 else None,
        "coords": coords,
        "ids": ids,
    }


def linestringArea(
    gdf: gpd.GeoDataFrame,
    *,
    typekey: str = "",
    roid=None,
    name=None,
    parent_row=None,
):
    """
    Slices pre-loaded LineStrings (e.g., streets) from a GeoDataFrame by spatial boundary
    and optional street name matching using sindex optimization, with comprehensive debugging.
    """
    from state import normalname

    # 1. Inspect input GDF
    p_name = parent_row.get("NAME") if isinstance(parent_row, dict) else getattr(parent_row, "NAME", "Unknown") if parent_row is not None else "None"
    logging.info(f"🔍 [linestringArea ENTRY] typekey: {typekey} | parent: {p_name} | input gdf len: {len(gdf) if gdf is not None else 'None'}")

    if gdf is None or gdf.empty:
        logging.warning(f"⚠️ [linestringArea] Input gdf for typekey '{typekey}' is None or empty.")
        return None, _empty_gdf(), _empty_gdf()

    gdf = ensure_4326(gdf)


    layer_cfg = MAP_LAYERS.get(typekey, {})
    destination = layer_cfg.get("out", f"{typekey}_Geometries.geojson")

    # 2. Inspect working geometry and bounds
    working_geom = extract_geometry(parent_row)
    if working_geom is None and roid is not None:
        working_geom = get_centroid_or_point(roid)

    if working_geom is not None:
        logging.info(f"📍 [linestringArea] working_geom type: {type(working_geom)} | Bounds: {working_geom.bounds}")
    else:
        logging.warning(f"⚠️ [linestringArea] working_geom is None for parent: {p_name} (roid: {roid})")

    line_gdf = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])].copy()
    logging.info(f"🛤️ [linestringArea] Filtered line_gdf count (LineString/MultiLineString): {len(line_gdf)}")

    # Use sindex optimization
    matched = _empty_gdf()
    if working_geom is not None and not line_gdf.empty:
        bbox = working_geom.bounds
        try:
            # --- DEBUG: CRS and Bounding Box Check ---
            line_crs = line_gdf.crs if hasattr(line_gdf, "crs") else "Unknown"
            logger.info(f"📐 [CRS DEBUG] line_gdf CRS: {line_crs} | Total features: {len(line_gdf)}")
            logger.info(f"📐 [CRS DEBUG] working_geom bounds: {bbox}")
            if not line_gdf.empty:
                sample_geom = line_gdf.geometry.iloc[0]
                logger.info(f"📐 [CRS DEBUG] Sample line geometry bounds: {sample_geom.bounds}")
            # -----------------------------------------

            candidate_indices = list(line_gdf.sindex.intersection(bbox))
            logging.info(f"📦 [linestringArea] sindex intersection count for bbox {bbox}: {len(candidate_indices)}")

            valid_indices = [idx for idx in candidate_indices if idx < len(line_gdf)]

            if valid_indices:
                candidate_gdf = line_gdf.iloc[valid_indices]
                intersects_mask = candidate_gdf.geometry.intersects(working_geom)
                matched = candidate_gdf[intersects_mask].copy()
                logging.info(f"🎯 [linestringArea] Final matched count after precise geometry intersection: {len(matched)}")
            else:
                logging.warning(f"⚠️ [linestringArea] No valid indices found in sindex intersection for bbox: {bbox}")

        except Exception as e:
            logging.warning(f"⚠️ sindex intersection failed for linestringArea, falling back to full scan: {e}")
            matched = line_gdf[line_gdf.geometry.intersects(working_geom)].copy()
            logging.info(f"🔄 [linestringArea] Fallback scan matched count: {len(matched)}")
    else:
        logging.warning(f"⚠️ [linestringArea] Skipping spatial filter because working_geom is None or line_gdf is empty.")
        matched = line_gdf.copy()

    nodestep = None
    if name is not None and not matched.empty:
        target_norm = normalname(name)
        name_matched = matched[matched["NAME"].astype(str).map(normalname) == target_norm]
        if not name_matched.empty:
            matched = name_matched
            nodestep = target_norm
            logging.info(f"🏷️ [linestringArea] Matched specific name '{name}' (normalized: {target_norm}), count: {len(matched)}")
        else:
            logging.warning(f"⚠️ [linestringArea] Name '{name}' requested, but no matching rows found in matched subset.")

    if nodestep is None and not matched.empty:
        try:
            nodestep = normalname(str(matched["NAME"].iloc[0]))
        except Exception as ex:
            logging.warning(f"⚠️ [linestringArea] Could not extract nodestep name from matched data: {ex}")

    try:
        matched.to_file(destination, driver="GeoJSON")
        logging.info(f"💾 [linestringArea] Saved {len(matched)} geometries to {destination}")
    except Exception as ex:
        logging.error(f"❌ [linestringArea] Failed to save GeoJSON to {destination}: {ex}")

    return [nodestep, matched, gdf]

def intersectingArea(
    gdf: gpd.GeoDataFrame,
    *,
    typekey: str = "",
    roid=None,
    name=None,
    parent_row=None,
):
    """
    Finds intersecting child geometries against a parent row feature.
    """
    from state import normalname

    if gdf is None or gdf.empty:
        return None, _empty_gdf(), _empty_gdf()

    gdf = ensure_4326(gdf)

    layer_cfg = MAP_LAYERS.get(typekey, {})
    child_level = layer_cfg.get("level", "N/A")

    parent_name = "None"
    if parent_row is not None:
        if isinstance(parent_row, dict):
            p_name_val = parent_row.get("NAME", "None")
        else:
            p_name_val = getattr(parent_row, "NAME", "None")
        parent_name = normalname(p_name_val)

    working_geom = extract_geometry(parent_row)

    p_name = parent_row.get("NAME") if isinstance(parent_row, dict) else getattr(parent_row, "NAME", "Unknown")
    logging.info(f"Checking intersection for parent: {p_name} | Geom type: {type(working_geom)} | Bounds: {working_geom.bounds if working_geom else 'NONE'}")
    if working_geom is not None:
        bbox = working_geom.bounds
        candidate_indices = list(gdf.sindex.intersection(bbox))

        if candidate_indices:
            # Filter out any indices that might fall outside the current bounds of gdf
            valid_indices = [idx for idx in candidate_indices if idx < len(gdf)]
            if valid_indices:
                candidate_gdf = gdf.iloc[valid_indices]
                child_polygons_within_parent = filter_gdf_by_overlap(
                    children_gdf=candidate_gdf,
                    parent_geometry=working_geom,
                    layer_type=typekey,
                    threshold_dict=globals().get("OVERLAP_THRESHOLDS", {}),
                )
            else:
                child_polygons_within_parent = _empty_gdf()
        else:
            child_polygons_within_parent = _empty_gdf()
    else:
        logging.warning("⚠️ No valid parent geometry in parent_row! Returning empty spatial subset.")
        child_polygons_within_parent = _empty_gdf()

    selected_child_name = None

    # 1. Try matching via coordinate/centroid (roid)
    centroid_pt = get_centroid_or_point(roid)
    if centroid_pt is not None and not child_polygons_within_parent.empty:
        hit = child_polygons_within_parent[
            child_polygons_within_parent.geometry.contains(centroid_pt)
        ]
        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    # 2. Try matching via explicit name input
    if not selected_child_name and name and not child_polygons_within_parent.empty:
        target = normalname(name)
        hit = child_polygons_within_parent[
            child_polygons_within_parent["NAME"].astype(str).map(normalname) == target
        ]
        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    # NOTE: The old fallback block that forced `selected_child_name = iloc[0]`
    # when name was None has been removed. Now, if name is None and no roid matches,
    # selected_child_name stays None, leaving all child polygons intact for export.

    return selected_child_name, child_polygons_within_parent, gdf


import logging

import geopandas as gpd


# UK bounding box in WGS84 degrees, with generous padding. Genuine lon/lat
# values for anything in this pipeline fall well inside this range;
# coordinates still in EPSG:27700 (or any other projected/metric CRS) show
# up as values in the hundreds of thousands and fail this check instantly.
# This doesn't prove a geometry is correctly EPSG:4326 -- it's a cheap,
# reliable trip-wire for the specific failure mode of a geometry silently
# still being in a projected CRS when 4326 is assumed.
_UK_WGS84_BOUNDS = (-11.0, 49.5, 2.5, 61.5)


def _looks_like_wgs84(geom, bounds=_UK_WGS84_BOUNDS):
    """Sanity-check a geometry's own coordinate values, not its CRS label."""
    if geom is None or geom.is_empty:
        return False
    minx, miny, maxx, maxy = geom.bounds
    ux_min, uy_min, ux_max, uy_max = bounds
    return (
        ux_min <= minx <= ux_max and ux_min <= maxx <= ux_max and
        uy_min <= miny <= uy_max and uy_min <= maxy <= uy_max
    )


def _resolve_ancestor_geometry(*, node_path, parent_row, ancestor_levels_up=2):
    """
    Resolve a stable boundary to pre-clip against.

    Prefers a genuine ancestor a fixed number of hierarchy levels above the
    immediate parent (looked up via Geo_index -> Treepolys by FID). A
    broader ancestor is deliberately used instead of the immediate parent:
    clipping tightly against the immediate parent risks losing valid
    features that sit right on that parent's edge, if the parent's own
    boundary has any small misalignment relative to the true source data.
    Falls back to the immediate parent's own geometry if no such ancestor
    can be resolved (e.g. we're only a level or two deep in the hierarchy).

    Returns (geometry, crs_or_None). crs_or_None is None when the source
    of the geometry doesn't carry known CRS metadata (e.g. a dict-based
    parent_row) — callers should treat that as "assume same CRS as gdf",
    not as "no reprojection needed". Every geometry returned here has
    already passed the WGS84 plausibility check; a geometry that fails it
    is treated as unusable rather than silently trusted.
    """
    if node_path and "Geo_index" in globals() and "Treepolys" in globals():
        path_parts = [p for p in node_path.split("/") if p]
        if len(path_parts) > ancestor_levels_up:
            ancestor_path = "/".join(path_parts[:ancestor_levels_up])
            ancestor_node = Geo_index.get(ancestor_path)
            if ancestor_node and ancestor_node.get("fid") is not None:
                level = ancestor_node.get("level")
                layer_gdf = Treepolys.get(level) if level else None
                if layer_gdf is not None and not layer_gdf.empty and "FID" in layer_gdf.columns:
                    match = layer_gdf[layer_gdf["FID"] == int(ancestor_node["fid"])]
                    if not match.empty:
                        geom = match.geometry.iloc[0]
                        if geom is not None and not geom.is_empty:
                            if not _looks_like_wgs84(geom):
                                logging.error(
                                    f"[ANCESTOR CLIP] Ancestor '{ancestor_path}' geometry bounds "
                                    f"{geom.bounds} don't look like WGS84; refusing to use it."
                                )
                            else:
                                return geom, layer_gdf.crs

    # Fallback: the immediate parent's own geometry.
    if parent_row is not None:
        p_geom = extract_geometry(parent_row)
        if p_geom is not None and not p_geom.is_empty:
            if not _looks_like_wgs84(p_geom):
                logging.error(
                    f"[ANCESTOR CLIP] Parent row geometry bounds {p_geom.bounds} don't look "
                    f"like WGS84 (likely still in a projected CRS); refusing to use it."
                )
                return None, None
            return p_geom, None

    return None, None


def load_layer(
    *,
    layer,
    parent_levels,
    parent_row,
    select_name=None,
    roid=None,
    node_path=None,
    **kwargs
):
    """
    Standardized layer-loader entrypoint using the provided parent_row directly.
    """
    typekey = layer.get("key")
    method = layer.get("method")

    gdf = get_layer_gdf(typekey, node_path=node_path)
    if gdf is None or gdf.empty:
        return _empty_gdf()

    # ------------------------------------------------------------------
    # STAGE 1 & STAGE 2 GEOMETRY RESOLUTION (Directly from parent_row)
    # ------------------------------------------------------------------
    exact_clip_geom = None
    clip_crs = getattr(gdf, "crs", None)

    try:
        # Extract geometry directly from parent_row if available
        if parent_row is not None:
            if hasattr(parent_row, "geometry"):
                exact_clip_geom = parent_row.geometry
            elif isinstance(parent_row, dict) and "geometry" in parent_row:
                exact_clip_geom = parent_row["geometry"]
    except Exception as e:
        logging.debug(f"[ANCESTOR CLIP] Could not extract geometry directly from parent_row: {e}")

    # Fallback to _resolve_ancestor_geometry if parent_row didn't yield a geometry
    if exact_clip_geom is None:
        exact_clip_geom, clip_crs = _resolve_ancestor_geometry(
            node_path=node_path, parent_row=parent_row, ancestor_levels_up=1,
        )

    # Build Stage 1 broad filter geometry: double the bounding box of the parent
    stage1_clip_geom = exact_clip_geom
    if exact_clip_geom is not None:
        try:
            minx, miny, maxx, maxy = exact_clip_geom.bounds
            width = maxx - minx
            height = maxy - miny

            # Expand parent bounds outward by 50% on all sides (doubling total footprint)
            stage1_clip_geom = box(
                minx - (width * 0.5),
                miny - (height * 0.5),
                maxx + (width * 0.5),
                maxy + (height * 0.5)
            )
        except Exception as e:
            logging.debug(f"[ANCESTOR CLIP] Failed to double parent bbox, falling back to exact bounds: {e}")

    if exact_clip_geom is not None and not gdf.empty:
        try:
            if gdf.crs is not None and clip_crs is not None and str(gdf.crs) != str(clip_crs):
                if stage1_clip_geom is not None:
                    stage1_clip_geom = gpd.GeoSeries([stage1_clip_geom], crs=clip_crs).to_crs(gdf.crs).iloc[0]
                exact_clip_geom = gpd.GeoSeries([exact_clip_geom], crs=clip_crs).to_crs(gdf.crs).iloc[0]

            before = len(gdf)

            # STAGE 1: Broad bounding-box-only pre-filter using the doubled parent box
            active_stage1_geom = stage1_clip_geom if stage1_clip_geom is not None else exact_clip_geom
            candidate_idx = list(gdf.sindex.query(active_stage1_geom))  # bbox-only pre-filter

            MAX_EXACT_VERIFY = 2000
            if candidate_idx and len(candidate_idx) <= MAX_EXACT_VERIFY:
                candidates = gdf.iloc[candidate_idx]
                # STAGE 2: Exact intersection test against the strict parent geometry
                exact_mask = candidates.geometry.intersects(exact_clip_geom)
                gdf = candidates[exact_mask]
            elif candidate_idx:
                logging.debug(
                    f"[ANCESTOR CLIP] '{typekey}': {len(candidate_idx)} candidates exceeds "
                    f"exact-verify cap ({MAX_EXACT_VERIFY}); using bbox-query result as-is."
                )
                gdf = gdf.iloc[candidate_idx]
            else:
                gdf = gdf.iloc[0:0]

            logging.debug(
                f"[ANCESTOR CLIP] '{typekey}': {before} -> {len(gdf)} candidates "
                f"(Stage 1: doubled parent bbox, Stage 2: strict parent from parent_row)."
            )
        except Exception as e:
            logging.error(f"[ANCESTOR CLIP] Pre-filter failed for '{typekey}': {e}", exc_info=True)
            return _empty_gdf()

    # ------------------------------------------------------------------
    # STAGE 2: Route to specific spatial method
    # ------------------------------------------------------------------
    if method == "index":
        return indexSpatialArea(gdf, typekey=typekey, parent_row=parent_row, roid=roid)

    if method == "linestringArea":
        return linestringArea(gdf, typekey=typekey, parent_row=parent_row, roid=roid, name=select_name)

    if method == "filter":
        return filterArea(gdf, typekey=typekey, roid=roid, name=select_name, parent_row=parent_row)

    return intersectingArea(gdf, typekey=typekey, parent_row=parent_row, name=select_name, roid=roid)

def _get_known_name_candidates():
    """Extract all potential 'NAME' field strings from global MAP_LAYERS."""
    candidates = []
    for layer in MAP_LAYERS.values():
        field_val = layer.get("field")
        if field_val:
            if isinstance(field_val, list):
                candidates.extend(field_val)
            else:
                candidates.append(field_val)

    # Standard general fallbacks
    candidates.extend(["NAME", "Name", "name", "County_Nam", "Ward_name", "Division_n"])

    # Unique list while preserving order
    return list(dict.fromkeys(candidates))

def filter_gdf_by_overlap(children_gdf, parent_geometry, layer_type: str, threshold_dict, default_threshold=0.40):
    """
    Pure spatial math function: Takes a child GeoDataFrame and a parent geometry,
    projects them to EPSG:3857, calculates proportional intersection area,
    and returns a filtered copy of the children exceeding the configured threshold.
    """


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
    # In state.py around line 875:


# Replace:
# parent_geom_proj = parent_geom_proj.make_valid()

# With:
    parent_geom_proj = make_valid(parent_geom_proj)

    valid_candidates_proj = valid_candidates_proj.copy()
    valid_candidates_proj['geometry'] = valid_candidates_proj.geometry.make_valid()

    # Now run intersection safely
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


# ==============================================================================
# 🛠️ HELPER FUNCTIONS & STATE ACCESSORS
# ==============================================================================

def upsert_geodf(
    existing: gpd.GeoDataFrame | None,
    incoming: gpd.GeoDataFrame | None,
    key: str = "FID"
) -> gpd.GeoDataFrame:
    """
    Upsert incoming spatial features into an existing GeoDataFrame using Version 2 logic:
    CRS alignment, duplicate resolution keeping newest records, and active geometry preservation.
    """
    if existing is None or existing.empty:
        return incoming.copy() if incoming is not None else gpd.GeoDataFrame()
    if incoming is None or incoming.empty:
        return existing.copy()

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

    # Drop duplicates keeping newest if key column exists
    if key in combined.columns:
        combined = combined.drop_duplicates(subset=key, keep="last")

    # Safely rebuild GeoDataFrame ensuring active geometry column is maintained
    geom_col = (
        existing.geometry.name
        if isinstance(existing, gpd.GeoDataFrame) and hasattr(existing, "geometry")
        else "geometry"
    )
    if geom_col not in combined.columns:
        geom_col = "geometry"

    return gpd.GeoDataFrame(combined, geometry=geom_col, crs=existing.crs)


def _generate_walk_geometries(areaelectors):
    """
    Build and persist walk-level (Level 5) geometries via Voronoi tessellation,
    grouped hierarchically by Nation, County, Constituency, Ward, and WalkName.
    """
    logger = logging.getLogger(__name__)

    if areaelectors is None or areaelectors.empty:
        logger.warning("Cannot build walk geoms: areaelectors is missing or empty.")
        return

    null_coords = areaelectors["Long"].isna() | areaelectors["Lat"].isna()
    if null_coords.any():
        logger.warning(f"{null_coords.sum()} electors have missing/NaN coordinates.")

    # -------------------------------------------------------------------------
    # 1. GROUPING & CENTROID CALCULATION
    # -------------------------------------------------------------------------
    group_cols = []
    for col in ["Nation", "County", "Constituency", "Ward", "WalkName"]:
        if col in areaelectors.columns:
            group_cols.append(col)
        else:
            logger.warning(f"⚠️ Grouping column '{col}' missing from areaelectors. Proceeding without it.")

    if not group_cols:
        logger.error("❌ No valid grouping columns found in areaelectors DataFrame.")
        return

    logger.info(f"📊 Grouping elector data by: {group_cols}")

    centroids_df = areaelectors.groupby(group_cols, as_index=False, dropna=False).agg(
        centroid_x=("Long", "mean"),
        centroid_y=("Lat", "mean"),
        Division=("Division", "first") if "Division" in areaelectors.columns else ("WalkName", "first"),
        PD=("PD", "first") if "PD" in areaelectors.columns else ("WalkName", "first"),
        elector_count=("WalkName", "count"),
    ).dropna(subset=["centroid_x", "centroid_y"])

    if centroids_df.empty:
        logger.warning("Centroids DataFrame is empty after grouping; skipping Voronoi build.")
        return

    # -------------------------------------------------------------------------
    # 2. RUN IMPROVED VORONOI BUILD LOGIC
    # -------------------------------------------------------------------------
    walk_gdf = build_walk_geoms_geovoronoi(
        centroids_df=centroids_df,
        crs_input="EPSG:4326",
        crs_proj="EPSG:27700",
        crs_out="EPSG:4326",
    )

    if walk_gdf.empty:
        logger.warning("Voronoi build returned an empty GeoDataFrame.")
        return

    # -------------------------------------------------------------------------
    # 3. PERSISTENCE
    # -------------------------------------------------------------------------
    if "WALK_GEOM_FILE" in globals():
        os.makedirs(os.path.dirname(os.path.abspath(WALK_GEOM_FILE)), exist_ok=True)
        walk_gdf.to_file(WALK_GEOM_FILE, driver="GeoJSON")
        logger.info(f"Wrote {len(walk_gdf)} walk geoms to '{WALK_GEOM_FILE}'.")
    else:
        logger.warning("WALK_GEOM_FILE path variable not found in globals; GeoDataFrame returned but not written.")

    return walk_gdf


def build_walk_geoms_geovoronoi(
    centroids_df,
    crs_input="EPSG:4326",
    crs_proj="EPSG:27700",
    crs_out="EPSG:4326",
):
    """
    Builds Voronoi walk geometries partitioned strictly within parent ward boundaries
    using convex-hull calculation wrappers followed by exact boundary intersection clipping.
    """
    logger = logging.getLogger(__name__)
    from state import normalname
    from layers import Treepolys

    logger.info("🚀 [DEBUG] Starting optimized hierarchical build_walk_geoms_geovoronoi")

    empty_gdf = gpd.GeoDataFrame(
        columns=["FID", "NAME", "TYPEKEY", "geometry"],
        geometry="geometry",
        crs=crs_out,
    )

    if centroids_df is None or centroids_df.empty:
        return empty_gdf

    df = centroids_df.dropna(subset=["centroid_x", "centroid_y", "WalkName"]).copy().reset_index(drop=True)
    if df.empty:
        return empty_gdf

    # Coordinate transformation prep (EPSG:4326 -> EPSG:27700)
    sample_x = df["centroid_x"].iloc[0]
    sample_y = df["centroid_y"].iloc[0]

    if abs(sample_x) > 180 or abs(sample_y) > 180:
        pts_gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df["centroid_x"], df["centroid_y"]), crs=crs_proj,
        )
    else:
        if sample_x > 30 and sample_y < 10:
            x_vals, y_vals = df["centroid_y"], df["centroid_x"]
        else:
            x_vals, y_vals = df["centroid_x"], df["centroid_y"]

        pts_gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(x_vals, y_vals), crs=crs_input
        ).to_crs(crs_proj)

    min_x, min_y, max_x, max_y = pts_gdf.total_bounds
    pad = 1000.0
    fallback_hull = box(min_x - pad, min_y - pad, max_x + pad, max_y + pad)

    ward_groups = pts_gdf.groupby("Ward" if "Ward" in pts_gdf.columns else pts_gdf.columns[0])
    all_processed_features = []

    for ward_name, group_df in ward_groups:
        logger.info(f"\n--- Processing Voronoi Group for Ward: {ward_name} | Sub-nodes: {len(group_df)} ---")

        # Look up exact parent territory boundary
        parent_boundary = fallback_hull
        source_used = "fallback_hull"

        if "Treepolys" in globals() and isinstance(Treepolys, dict) and "ward" in Treepolys:
            pfile = Treepolys["ward"]
            if not pfile.empty and "NAME" in pfile.columns:
                w_norm = normalname(str(ward_name))
                logger.debug(f"Normalized ward name search: '{w_norm}' (Original: '{ward_name}')")

                matched_ward = pfile[pfile["NAME"].apply(normalname) == w_norm]
                if not matched_ward.empty:
                    parent_boundary = matched_ward.to_crs(crs_proj).union_all()
                    matched_names = matched_ward["NAME"].tolist()
                    source_used = f"Treepolys['ward'] (Matched names: {matched_names})"
                else:
                    logger.debug(f"No match in Treepolys['ward'] for normalized name '{w_norm}'.")
            else:
                logger.debug("Treepolys['ward'] dataframe is empty or missing the 'NAME' column.")
        else:
            logger.debug("Treepolys dictionary or 'ward' key is not present in globals.")

        logger.info(f"-> Parent boundary source used: {source_used}")

        if not parent_boundary.is_valid:
            logger.warning(f"-> Warning: Parent boundary for '{ward_name}' is invalid. Applying .buffer(0) correction.")
            parent_boundary = parent_boundary.buffer(0)

        # Create a clean calculation bounding hull for geovoronoi outer margins
        calc_hull = parent_boundary.convex_hull

        # Extract coordinates safely and map to original rows
        coords_list = []
        point_to_row_indices = {}

        for idx, row in group_df.iterrows():
            pt_geom = row.geometry
            # Ensure point falls safely inside the parent boundary
            if not parent_boundary.contains(pt_geom):
                pt_geom = nearest_points(parent_boundary, pt_geom)[0]

            pt_coord = (round(pt_geom.x, 6), round(pt_geom.y, 6))
            coords_list.append(pt_coord)
            if pt_coord not in point_to_row_indices:
                point_to_row_indices[pt_coord] = []
            point_to_row_indices[pt_coord].append(idx)

        coords = np.array(coords_list)
        if len(coords) == 0:
            continue

        # -----------------------------------------------------------------
        # VORONOI COMPUTATION FOR GROUP (Using Convex Hull wrapper)
        # -----------------------------------------------------------------
        region_polys = {}
        region_pts = {}

        if len(coords) >= 3:
            try:
                region_polys, region_pts = voronoi_regions_from_coords(coords, calc_hull)
            except Exception as err:
                logger.error(f"❌ geovoronoi calculation failed for ward {ward_name}: {err}. Falling back to fallback hull.")
                try:
                    region_polys, region_pts = voronoi_regions_from_coords(coords, fallback_hull)
                except Exception as inner_err:
                    logger.error(f"❌ Fallback hull calculation also failed for {ward_name}: {inner_err}")
                    continue
        elif len(coords) == 1:
            region_polys = {0: calc_hull}
            region_pts = {0: [0]}
        elif len(coords) == 2:
            pt1, pt2 = coords[0], coords[1]
            mid_x, mid_y = (pt1[0] + pt2[0]) / 2.0, (pt1[1] + pt2[1]) / 2.0
            dx, dy = pt2[0] - pt1[0], pt2[1] - pt1[1]
            scale = 20.0
            dividing_line = LineString([
                (mid_x - (-dy) * scale, mid_y - dx * scale),
                (mid_x + (-dy) * scale, mid_y + dx * scale)
            ])
            split_res = split(calc_hull, dividing_line)
            geoms = list(split_res.geoms) if hasattr(split_res, "geoms") else [split_res]
            for r_idx, geom in enumerate(geoms):
                dist0 = geom.centroid.distance(Point(pt1))
                dist1 = geom.centroid.distance(Point(pt2))
                region_polys[r_idx] = geom
                region_pts[r_idx] = [0 if dist0 < dist1 else 1]
        elif len(coords) == 3:
            bx_min, by_min, bx_max, by_max = calc_hull.bounds
            dummy_point = np.array([[bx_max + 10.0, by_max + 10.0]])
            extended_coords = np.vstack([coords, dummy_point])
            ext_polys, ext_pts = voronoi_regions_from_coords(extended_coords, calc_hull)
            r_idx = 0
            for k, poly in ext_polys.items():
                assigned_indices = ext_pts[k]
                if 3 not in assigned_indices and not poly.is_empty:
                    region_polys[r_idx] = poly
                    region_pts[r_idx] = assigned_indices
                    r_idx += 1

        # -----------------------------------------------------------------
        # CLEANUP AND EXACT INTERSECTION CLIPPING AGAINST WARD BOUNDARY
        # -----------------------------------------------------------------
        for region_id, poly in region_polys.items():
            # Strict secondary intersection clip against the actual parent boundary shape
            raw_intersection = poly.intersection(parent_boundary)
            if raw_intersection.is_empty:
                continue

            if raw_intersection.geom_type in ["Polygon", "MultiPolygon"]:
                actual_shape = raw_intersection
            elif raw_intersection.geom_type == "GeometryCollection":
                polys = [g for g in raw_intersection.geoms if g.geom_type in ["Polygon", "MultiPolygon"]]
                actual_shape = unary_union(polys) if polys else None
            else:
                continue

            if actual_shape is None or actual_shape.is_empty or not actual_shape.is_valid:
                continue

            pt_idx = region_pts[region_id]
            if isinstance(pt_idx, (list, np.ndarray)):
                pt_idx = pt_idx[0]

            coord = coords[pt_idx]
            orig_indices = point_to_row_indices.get(tuple(coord), [])

            for orig_idx in orig_indices:
                row_data = group_df.loc[orig_idx].copy()
                row_data["geometry"] = actual_shape
                all_processed_features.append(row_data)

    if not all_processed_features:
        return empty_gdf

    walk_gdf = gpd.GeoDataFrame(all_processed_features, crs=crs_proj)
    walk_gdf["geometry"] = walk_gdf["geometry"].make_valid()

    walk_gdf["FID"] = [
        int(hashlib.sha1(f"{row.get('Ward', '')}|{row['WalkName']}".encode()).hexdigest(), 16) % (2**31 - 1)
        for _, row in walk_gdf.iterrows()
    ]
    walk_gdf["NAME"] = walk_gdf["WalkName"]
    walk_gdf["TYPEKEY"] = "walk"

    return walk_gdf[["FID", "NAME", "TYPEKEY", "geometry"]].to_crs(crs_out)

# ==============================================================================
# CORE ENGINE PIPELINE
# ==============================================================================

# ------------------------------------------------------------------
# Small helpers extracted from duplicated inline logic
# ------------------------------------------------------------------

def _union_rows(rows, label):
    """Combine the geometries of several rows into one aggregated row.
    Used both for explicit 'union' aggregation mode and as a fallback
    when several individual parents map to the same layer_type.
    """
    geoms = [r["geometry"] for r in rows if r.get("geometry") is not None]
    if not geoms:
        return None

    series = gpd.GeoSeries(geoms)
    combined_geom = series.union_all() if hasattr(series, "union_all") else series.unary_union

    return {
        "FID": [r.get("FID") for r in rows],
        "NAME": f"Aggregated_{label}_{len(rows)}_parents",
        "geometry": combined_geom,
        "_parent_path": rows[0].get("_parent_path", ROOT),
    }


def _resolve_fid_column(gdf):
    """Ensure a GeoDataFrame has a usable FID column, renaming/generating as needed."""
    if "FID" in gdf.columns:
        return gdf
    if "OBJECTID" in gdf.columns:
        return gdf.rename(columns={"OBJECTID": "FID"})
    if "id" in gdf.columns:
        return gdf.rename(columns={"id": "FID"})
    gdf["FID"] = gdf.index.astype(int)
    return gdf


def _spatial_filter(tree_gdf, anchor_points):
    if tree_gdf.empty or not anchor_points:
        return tree_gdf

    # Use GeoPandas spatial index for fast bounding-box lookups
    sindex = tree_gdf.sindex
    matched_indices = set()

    for point in anchor_points:
        # Fast candidate retrieval using R-tree bounding box
        possible_matches_index = list(sindex.query(point, predicate="intersects"))
        matched_indices.update(possible_matches_index)

    return tree_gdf.iloc[list(matched_indices)].copy()


def _derive_child_name(raw_name, idx):
    """Turn a raw NAME value into a clean, index-safe identifier."""
    is_valid = pd.notna(raw_name) and raw_name is not None and str(raw_name).strip() != ""
    if not is_valid:
        return f"UNNAMED_{idx}"

    raw_str = str(raw_name).strip()
    cleaned = normalname(raw_str)
    if cleaned and str(cleaned).strip():
        return str(cleaned).strip()
    return raw_str.upper().replace(" ", "_")



# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------
def ensure_treepolys_with_index(
    *,
    sourcepath: str | None,
    here=None,
    resolved_levels: dict[str, dict[int, str]],
    parent_levels: dict[int, str],
    areaelectors=None,
):
    territory = derive_territory(sourcepath)
    logging.info(f"[START] ensure_treepolys_with_index | territory={territory} | sourcepath={sourcepath}")
    logging.debug(f"here={here} | resolved_levels={resolved_levels} | parent_levels={parent_levels} | "
                  f"initial Geo_index size={len(Geo_index)}")

    if ROOT not in Geo_index:
        Geo_index[ROOT] = {
            "level": "country", "name": ROOT, "parent": None,
            "children": [], "roid": [54.5, -2.5], "fid": 238,
        }
        logging.debug(f"[INDEX] Initialized ROOT node '{ROOT}' in Geo_index.")

    if not resolved_levels or len(resolved_levels) != 1:
        logging.error(f"Invalid resolved_levels configuration: {resolved_levels}")
        raise ValueError("Invalid resolved_levels configuration.")

    (_, elevels), = resolved_levels.items()
    sourcepath = sourcepath or territory

    # ------------------------------------------------------------------
    # Geometry & point path resolution
    # ------------------------------------------------------------------
    coords = parse_coords(here) if ("parse_coords" in globals() and here) else []
    anchor_points = [Point(lon, lat) for lat, lon in coords] if coords else []
    logging.debug(f"[COORDS] Parsed coords count: {len(coords)} | Anchor points count: {len(anchor_points)}")

    effective_sourcepath = sourcepath
    if not effective_sourcepath and coords and "classify_record_coords" in globals():
        lat, lon = coords[0]
        derived_path = classify_record_coords(lat, lon, sourcepath, parent_levels).get("_derived_path")
        if derived_path:
            logging.info(f"Derived territory path from point ({lat}, {lon}): {derived_path}")
            effective_sourcepath = derived_path

    MAP_LAYERS = globals().get("MAP_LAYERS", {})
    if isinstance(MAP_LAYERS, list):
        MAP_LAYERS = {l.get("key", idx): l for idx, l in enumerate(MAP_LAYERS)}
    layer_defs = {l.get("key", k): l for k, l in MAP_LAYERS.items()}

    for k, l in MAP_LAYERS.items():
        layer_key = l.get("key", k)
        Treepolys.setdefault(layer_key, gpd.GeoDataFrame())

    # ------------------------------------------------------------------
    # Dynamic level deduction (target level + 1, driven by sourcepath)
    # ------------------------------------------------------------------
    dynamic_steps = [ROOT]
    raw_steps = stepify(effective_sourcepath) if effective_sourcepath else []
    steps = raw_steps if raw_steps else [ROOT]

    # --- FIX: Ensure target_levels AND target_depth are always initialized ---
    max_available_level = max(elevels.keys()) if elevels else 0
    target_depth = 0  # Default fallback depth

    if effective_sourcepath and effective_sourcepath != ROOT:
        raw_steps = stepify(effective_sourcepath)
        steps = raw_steps if raw_steps else [ROOT]
        target_depth = max(0, len(steps) - 1)
        if target_depth > 3:
            max_processing_level = min(target_depth + 2, max_available_level)
        else:
            max_processing_level = min(target_depth + 1, max_available_level)
        target_levels = list(range(0, max_processing_level + 1))
        logging.info(f"Processing filtered levels based on sourcepath: {target_levels}")
    else:
        # Fallback: Process all available levels when viewing root
        target_levels = list(range(0, max_available_level + 1))
        logging.info(f"No specific sourcepath depth; processing all available levels: {target_levels}")

    # Active parent features tracked by explicit layer name
    active_layer_rows = {ROOT: [{"NAME": ROOT, "_parent_path": None}]}
    fid_to_path = {}
    deepest_path_registered = ROOT

    # Tracks, per layer_type, the single row that matched this level's
    # select_name (i.e. the branch actually being navigated into). Used to
    # stop descent from fanning out across every sibling registered at a
    # given level -- registering all siblings is correct (so the UI can
    # show them), but only ONE of them is the path actually being walked,
    # and every other sibling triggering its own load_layer call for the
    # next level down is pure wasted fan-out (e.g. re-loading constituency
    # data once per English county instead of once for the selected one).
    selected_row_by_layer = {}

    # ------------------------------------------------------------------
    # Main processing loop
    # ------------------------------------------------------------------
    for level in target_levels:
        compound_layer_type = elevels.get(level)
        if not compound_layer_type:
            logging.warning(f"No layer mapping for Level {level}; skipping.")
            continue

        sub_layers = [l.strip() for l in compound_layer_type.split("/") if l.strip()]
        logging.info(f"--- Processing Level {level} with sub_layers: {sub_layers} ---")

        for layer_type in sub_layers:
            active_layer_rows.setdefault(layer_type, [])

            if layer_type.lower() == "walk" and not os.path.exists(WALK_GEOM_FILE):
                logging.info(f"Level {level} ('walk') geometry file missing; generating via _generate_walk_geometries.")
                _generate_walk_geometries(areaelectors)

            layer = layer_defs.get(layer_type)
            if not layer:
                logging.warning(f"Layer definition missing for key={layer_type}")
                continue

            select_name = None
            if effective_sourcepath and level < len(steps) and (level <= 3 or level < target_depth):
                select_name = steps[level]
                logging.debug(f"[SELECT] Target selection name for level {level} ('{layer_type}'): {select_name}")


            # --------------------------------------------------------
            # Parent resolution
            # --------------------------------------------------------
            parent_layer_key = layer.get("parent_layer")
            fan_out_to_all_parents = layer.get("fan_out_to_all_parents", False)
            logging.debug(
                f"[PARENT] Layer '{layer_type}' has parent_layer_key='{parent_layer_key}' | "
                f"fan_out_to_all_parents={fan_out_to_all_parents}"
            )

            if parent_layer_key is None:
                # No parent layer configured at all (e.g. 'country', the root
                # layer) -- a None parent_row is legitimate here.
                parent_rows = [None]
            elif not fan_out_to_all_parents and parent_layer_key in selected_row_by_layer:
                # Single-branch navigation layer (nation/county/constituency/ward):
                # a specific sibling was selected at the parent level, so only
                # descend through that one -- not every registered sibling.
                parent_rows = [selected_row_by_layer[parent_layer_key]]
                logging.debug(f"[PARENT] Narrowed to selected row for '{parent_layer_key}' (avoiding sibling fan-out).")
            else:
                # Either fan_out_to_all_parents is True (walk/street: genuinely
                # want every sibling processed), or there's no selected-row
                # narrowing available for this parent yet -- fall back to the
                # full registered set.
                parent_rows = active_layer_rows.get(parent_layer_key)
                if not parent_rows:
                    logging.error(
                        f"[PARENT] Layer '{layer_type}' requires parent layer "
                        f"'{parent_layer_key}', but it has no active rows. "
                        f"Refusing to fall back to an unclipped parent_row=None "
                        f"load -- skipping '{layer_type}' for this branch."
                    )
                    continue
                logging.debug(f"[PARENT] Retrieved {len(parent_rows)} active row(s) from parent layer '{parent_layer_key}'")

            src = layer.get("src")
            field = layer.get("field")

            if not src or not field:
                logging.debug(f"Virtual layer '{layer_type}' (missing src or field); forwarding parents unchanged.")
                active_layer_rows[layer_type].extend(p for p in parent_rows if p is not None)
                continue

            # --------------------------------------------------------
            # Determine parent processing contexts
            # --------------------------------------------------------
            parent_contexts = parent_rows if parent_rows else [None]
            all_results = []
            for parent_ctx in parent_contexts:
                resolved_p_path = ROOT
                if parent_ctx is not None:
                    resolved_p_path = (
                        parent_ctx.get("_parent_path", ROOT) if isinstance(parent_ctx, dict)
                        else getattr(parent_ctx, "_parent_path", ROOT)
                    )

                # 🔍 REVEALING DEBUG: Inspect the parent context coming into the loop
                p_type = type(parent_ctx).__name__
                p_name = (
                    parent_ctx.get("NAME") if isinstance(parent_ctx, dict)
                    else getattr(parent_ctx, "NAME", "N/A")
                )
                p_geom = (
                    parent_ctx.get("geometry") if isinstance(parent_ctx, dict)
                    else getattr(parent_ctx, "geometry", None)
                )
                p_bounds = p_geom.bounds if p_geom is not None and hasattr(p_geom, "bounds") else "NO_GEOM"

                logging.debug(
                    f"[CONTEXT DEBUG] Loop item -> Type: {p_type} | Name: '{p_name}' | "
                    f"Resolved Path: '{resolved_p_path}' | Geometry Bounds: {p_bounds}"
                )

                # --------------------------------------------------------
                # 🚀 HARDENED EARLY CACHE CHECK (BYPASS RAW LOAD IF ALREADY INDEXED)
                # --------------------------------------------------------
                cache_hit = False
                if resolved_p_path in Geo_index and Geo_index[resolved_p_path].get("children"):
                    children_paths = Geo_index[resolved_p_path]["children"]
                    if children_paths and (not select_name or any(select_name.upper() in cp.upper() for cp in children_paths)):
                        existing_treepoly = get_treepoly(layer_type)
                        if existing_treepoly is not None and not existing_treepoly.empty:
                            if "_parent_path" in existing_treepoly.columns:
                                matched_cached_rows = existing_treepoly[
                                    existing_treepoly["_parent_path"] == resolved_p_path
                                ]
                            else:
                                logging.debug(f"[CACHE WARNING] '_parent_path' missing in cache for '{layer_type}'; using fallback matching.")
                                matched_cached_rows = existing_treepoly
                            if not matched_cached_rows.empty:
                                existing_fids = {r["FID"] for r in active_layer_rows[layer_type] if r is not None and "FID" in r}
                                added_count = 0
                                for _, cached_row in matched_cached_rows.iterrows():
                                    row_copy = cached_row.copy()

                                    # _parent_path on an active row must mean "this row's own full
                                    # path" (that's the contract the main registration loop sets up
                                    # and every downstream level relies on) -- NOT the path we used
                                    # to look this row up. Resolve it properly against the known
                                    # children of resolved_p_path rather than reusing resolved_p_path
                                    # itself, or every level below this one silently drops a segment.
                                    row_norm_name = normalname(str(cached_row.get("NAME", "")))
                                    own_full_path = next(
                                        (cp for cp in children_paths if normalname(cp.split("/")[-1]) == row_norm_name),
                                        None,
                                    )
                                    row_copy["_parent_path"] = own_full_path or resolved_p_path

                                    row_fid = row_copy.get("FID")
                                    if row_fid not in existing_fids and pd.notna(row_fid):
                                        active_layer_rows[layer_type].append(row_copy)
                                        existing_fids.add(row_fid)
                                        added_count += 1

                                if added_count > 0:
                                    logging.info(f"⚡ [FAST PATH HIT] Loaded {added_count} cached rows for layer '{layer_type}' under '{resolved_p_path}'. Skipping raw load.")
                                    cache_hit = True

                if cache_hit:
                    continue  # Skip standard load_layer entirely for this context!

                logging.debug(f"[RAW LOAD TRIGGER] Cache missed or unavailable for '{resolved_p_path}'. Calling load_layer for '{p_name}'...")

                try:
                    selected_child_name, tree_gdf, raw_gdf = load_layer(
                        layer=layer, level=level, intention_type=layer_type,
                        parent_levels=parent_levels, parent_row=parent_ctx,
                        select_name=select_name, roid=here, node_path=effective_sourcepath,
                    )
                    logging.debug(f"Level {level} '{layer_type}' load result: "
                                  f"selected_child='{selected_child_name}' | "
                                  f"raw_gdf count={len(raw_gdf) if raw_gdf is not None else 0} | "
                                  f"tree_gdf count={len(tree_gdf) if tree_gdf is not None else 0}")

                    if selected_child_name:
                        norm_child = normalname(selected_child_name)
                        if norm_child not in [normalname(s) for s in dynamic_steps]:
                            dynamic_steps.append(selected_child_name)
                            logging.debug(f"[DYNAMIC STEPS] Added '{selected_child_name}' to dynamic_steps.")

                except Exception as e:
                    logging.error(f"[ERROR] load_layer failed for parent '{p_name}' at path '{resolved_p_path}' "
                                  f"(Level {level}, layer '{layer_type}'): {e}", exc_info=True)
                    continue

                if tree_gdf is None or tree_gdf.empty:
                    logging.debug(f"[SKIP] tree_gdf is empty or None for layer '{layer_type}' under parent path '{resolved_p_path}'")
                    continue

                # Simplify high-resolution polygons to speed up spatial math dramatically
                tol = layer.get("simplify_tolerance", 0.0001)   # default keeps current behaviour
                if tol and "geometry" in tree_gdf.columns:
                    tree_gdf["geometry"] = tree_gdf["geometry"].simplify(tolerance=tol, preserve_topology=True)
                tree_gdf = _resolve_fid_column(tree_gdf.copy())

                if level <= target_depth and anchor_points and select_name is None:
                    pre_count = len(tree_gdf)
                    tree_gdf = _spatial_filter(tree_gdf, anchor_points)
                    logging.debug(f"[SPATIAL FILTER] Filtered tree_gdf for '{layer_type}': {pre_count} -> {len(tree_gdf)} rows remaining.")

                tree_gdf["_parent_path"] = ROOT if level == 0 else resolved_p_path
                all_results.append(tree_gdf)

            if not all_results:
                logging.warning(f"No results collected across all contexts for level={level}, layer_type='{layer_type}'.")
                continue

            tree_gdf = pd.concat(all_results, ignore_index=True)
            logger.debug(f"[CONCAT] Combined total {len(tree_gdf)} rows for layer '{layer_type}'")

            if "FID" in tree_gdf.columns and tree_gdf["FID"].duplicated().any():
                dupe_fids = tree_gdf.loc[tree_gdf["FID"].duplicated(keep=False), "FID"].unique().tolist()
                before = len(tree_gdf)

                # If filter_gdf_by_overlap attaches an overlap score column, prefer the
                # parent with the strongest overlap as canonical owner. Otherwise fall
                # back to "first wins" -- but this is a genuine ownership decision, not
                # just crash-avoidance, so log it loudly rather than silently.
                sort_col = "overlap_ratio" if "overlap_ratio" in tree_gdf.columns else None
                if sort_col:
                    tree_gdf = tree_gdf.sort_values(sort_col, ascending=False)

                tree_gdf = tree_gdf.drop_duplicates(subset="FID", keep="first").reset_index(drop=True)
                logger.warning(
                    f"[DEDUP] Layer '{layer_type}': dropped {before - len(tree_gdf)} duplicate-FID rows "
                    f"(boundary features matched to multiple parents: FIDs {dupe_fids}). "
                    f"Kept the {'highest-overlap' if sort_col else 'first-seen'} parent as canonical owner."
                )

            # --- OPTIMIZATION CHECK ---
            all_children_cached = True
            for idx, row in tree_gdf.iterrows():
                child_name = _derive_child_name(row.get("NAME"), idx)
                parent_path = resolved_p_path
                test_path = f"{parent_path}/{child_name}"

                if test_path not in Geo_index or not Geo_index[test_path].get("children"):
                    all_children_cached = False
                    break

            if all_children_cached and not get_treepoly(layer_type).empty:
                logger.debug(f"[CACHE HIT] Node '{test_path}' and its children are already fully cached in Geo_index. Skipping upsert and export.")
                continue

            existing = get_treepoly(layer_type)
            upserted_gdf = upsert_geodf(existing, tree_gdf, key="FID")
            set_treepoly(layer_type, upserted_gdf)

            # Export layer to file only if changes/new data occurred
            if upserted_gdf is not None and not upserted_gdf.empty:
                destination = MAP_LAYERS.get(layer_type, {}).get("out")
                if not destination:
                    out_dir = config.workdirectories["bounddir"]
                    os.makedirs(out_dir, exist_ok=True)
                    destination = os.path.join(out_dir, f"{layer_type}_Boundaries.gpkg")
                else:
                    base, _ = os.path.splitext(destination)
                    destination = base + ".gpkg"

                os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)

            # Remove old file if it exists to prevent locks
            if os.path.exists(destination):
                try:
                    os.remove(destination)
                except Exception:
                    pass

            upserted_gdf = upserted_gdf.reset_index(drop=True)

            # Final guard: GPKG/SQLite is case-insensitive on column names,
            # so a case-variant collision (e.g. "Name" alongside "NAME")
            # that slipped in from a merge or a differently-cased source
            # layer would otherwise only surface as a cryptic sqlite3_exec
            # failure deep inside pyogrio at write time.
            upserted_gdf = normalize_column_case(upserted_gdf, ["FID", "NAME", "TYPEKEY"])

            upserted_gdf.to_file(destination, driver="GPKG")
            logger.info(f"Level {level} [{layer_type}] exported ({len(upserted_gdf)} features) -> {destination}")
            # --------------------------------------------------------
            # Index registration & parent propagation
            # --------------------------------------------------------
            existing_fids = {r["FID"] for r in active_layer_rows[layer_type] if r is not None and "FID" in r}

            for idx, row in tree_gdf.iterrows():
                child_name = _derive_child_name(row.get("NAME"), idx)
                parent_path = row.get("_parent_path", ROOT)
                this_path = ROOT if (level == 0 and child_name == ROOT) else f"{parent_path}/{child_name}"

                roid_coords = None
                if getattr(row, "geometry", None) is not None:
                    try:
                        centroid = row.geometry.representative_point()
                        roid_coords = [float(centroid.y), float(centroid.x)]
                    except Exception as ex:
                        logging.debug(f"[ROID ERROR] Failed to calculate representative point for '{child_name}': {ex}")

                row_fid = int(row["FID"]) if pd.notna(row.get("FID")) else None

                if this_path not in Geo_index:
                    Geo_index[this_path] = {
                        "level": layer_type, "name": child_name,
                        "parent": parent_path if level > 0 else None,
                        "children": [], "roid": roid_coords, "fid": row_fid,
                    }
                    logging.debug(f"[GEO_INDEX NEW] Registered path: '{this_path}' (FID: {row_fid})")
                else:
                    entry = Geo_index[this_path]
                    if entry.get("fid") is None and row_fid is not None:
                        entry["fid"] = row_fid
                    if entry.get("roid") is None and roid_coords is not None:
                        entry["roid"] = roid_coords
                    logging.debug(f"[GEO_INDEX UPDATE] Updated existing path: '{this_path}'")

                if parent_path in Geo_index and this_path != parent_path:
                    siblings = Geo_index[parent_path]["children"]
                    if this_path not in siblings:
                        siblings.append(this_path)
                        logging.debug(f"[GEO_INDEX CHILD] Added '{this_path}' to children of parent '{parent_path}'")

                if row_fid is not None:
                    fid_to_path[(level, row_fid)] = this_path

                row_copy = row.copy()
                row_copy["_parent_path"] = this_path
                if row_copy["FID"] not in existing_fids:
                    active_layer_rows[layer_type].append(row_copy)
                    existing_fids.add(row_copy["FID"])

                deepest_path_registered = this_path

            # After registering all sibling rows for this layer_type, note
            # which one (if any) matches this level's select_name -- that's
            # the only one subsequent levels should descend through.
            if select_name:
                norm_target = normalname(select_name)
                for r in active_layer_rows[layer_type]:
                    r_name = r.get("NAME") if isinstance(r, dict) else getattr(r, "NAME", None)
                    if r_name is not None and normalname(str(r_name)) == norm_target:
                        selected_row_by_layer[layer_type] = r
                        break

    # ------------------------------------------------------------------
    # Path traversal & fallback resolution
    # ------------------------------------------------------------------
    active_steps = steps if len(steps) > 1 else dynamic_steps
    current_path = ""
    deepest_valid_path = ROOT

    for step in active_steps:
        normalized_step = normalname(step)
        current_path = f"{current_path}/{normalized_step}" if current_path else normalized_step
        if current_path in Geo_index:
            deepest_valid_path = current_path
        else:
            logging.debug(f"[TRAVERSAL BREAK] Step '{step}' (normalized: '{normalized_step}') yielded path '{current_path}', which is missing from Geo_index.")
            break

    final_path = deepest_valid_path if deepest_valid_path in Geo_index else deepest_path_registered
    leaf_name = final_path.split("/")[-1]
    match_full_filepath = f"{final_path}/{leaf_name}-MAP.html"

    logging.info(f"[DONE] Final Resolved Target Path: '{final_path}' | Map File Path: '{match_full_filepath}'")
    return match_full_filepath, Geo_index



def normalize_osm_name(val):
    """
    Safely normalizes a string or list of strings from OSM's 'name' column.
    Converts underscores to spaces and uses normalname for consistent formatting.
    """
    from state import normalname
    if pd.isna(val) or val is None:
        return ""

    # Handle cases where OSM returns a list of street names for a single segment
    if isinstance(val, list):
        return [normalname(str(item).replace('_', ' ')) for item in val]

    return normalname(str(val).replace('_', ' '))


def matches_target_street(osm_name, target_norm):
    """
    Checks if target normalized name matches a single string or any item in an OSM name list.
    """
    norm_val = normalize_osm_name(osm_name)
    if isinstance(norm_val, list):
        return target_norm in norm_val
    return norm_val == target_norm


def Hconcat(house_list):
    # Make sure house_list is iterable and not accidentally a DataFrame or something else
    try:
        return ', '.join(sorted(set(map(str, house_list))))
    except Exception as e:
        print("❌ Error in Hconcat:", e)
        print("Type of house_list:", type(house_list))
        raise


def spread_coordinates_vertical(base_lat, base_lon, index, total, spread_lat=0.00005, spread_lon=0.00001):
    """
    Returns slightly offset coordinates to prevent marker overlap.
    Vertical-biased: spreads more in latitude than longitude.

    base_lat, base_lon : original coordinates
    index              : index of this marker in the group (0-based)
    total              : total markers sharing this area
    spread_lat         : max offset in latitude (vertical)
    spread_lon         : max offset in longitude (horizontal)

    Returns: (lat, lon)
    """

    # No need to offset if only one marker
    if total <= 1:
        return base_lat, base_lon

    # Evenly distribute along vertical "arc"
    angle = (math.pi / total) * index  # semi-circle vertically

    offset_lat = base_lat + spread_lat * math.cos(angle)
    offset_lon = base_lon + spread_lon * math.sin(angle)

    return offset_lat, offset_lon

def readable_text_color(hex_color, threshold=0.55):
    """Return a dark readable colour that contrasts with hex_color"""
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
    luminance = 0.2126*r + 0.7152*g + 0.0722*b

    # Always return a DARK tone for consistency
    return "#111111" if luminance > threshold else "#000000"



def get_text_color(fill_hex):
    # Convert hex to RGB
    fill_hex = fill_hex.lstrip('#')
    r, g, b = [int(fill_hex[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

    # Calculate luminance
    def adjust(c): return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    lum = 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

    # Contrast against white and black
    white_contrast = (1.05) / (lum + 0.05)
    black_contrast = (lum + 0.05) / 0.05

    return '#ffffff' if white_contrast >= black_contrast else '#000000'

def invert_black_white(hex_color):
    hex_color = hex_color.strip().lower()
    if hex_color in ("#000000", "000000"):
        return "#ffffff"
    elif hex_color in ("#ffffff", "ffffff"):
        return "#000000"
    else:
        return None  # or raise ValueError("Not black or white")

def adjust_boundary_color(fill_hex, factor=0.7):
    fill_hex = fill_hex.lstrip('#')
    r, g, b = [int(fill_hex[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

    # Convert to HLS (Hue, Lightness, Saturation)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Darken or lighten
    new_l = max(0, min(1, l * factor))
    new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)

    # Back to hex
    return '#{:02x}{:02x}{:02x}'.format(int(new_r*255), int(new_g*255), int(new_b*255))

def create_boundary_geom(elector_df, buffer_meters=50):
    """
    Create a boundary geometry from a set of elector points.

    Parameters:
        elector_df (pd.DataFrame): Must have 'Lat' and 'Long' columns.
        buffer_meters (float): Optional buffer in meters around the convex hull.

    Returns:
        shapely Polygon: EPSG:4326 polygon covering all points.
    """
    if elector_df.empty:
        return None

    # Ensure Lat/Long columns exist
    if 'Lat' not in elector_df.columns or 'Long' not in elector_df.columns:
        raise ValueError("elector_df must have 'Lat' and 'Long' columns")

    # Create points
    points = [Point(lon, lat) for lon, lat in zip(elector_df['Long'], elector_df['Lat'])]
    multipoint = MultiPoint(points)

    # GeoSeries in WGS84
    gdf = gpd.GeoSeries([multipoint], crs="EPSG:4326")

    # Project to metric CRS for accurate buffer
    gdf_proj = gdf.to_crs("EPSG:3857")

    # Convex hull + buffer
    hull = gdf_proj.iloc[0].convex_hull
    hull_buffered = hull.buffer(buffer_meters)

    # Convert back to WGS84
    hull_wgs84 = gpd.GeoSeries([hull_buffered], crs="EPSG:3857").to_crs("EPSG:4326").iloc[0]

    return hull_wgs84


def build_street_list_html(reg_id, streets_df, street_stats, task_tags, uiScope="walk"):
    import json
    from state import VID
    from baked_data import baked_manager

    sorted_task_codes = sorted(task_tags.keys())
    tag_headers_html = "".join([f'<th class="text-center text-info small" style="min-width: 45px; position: sticky; top: 0; z-index: 2; background: #212529;">{code}</th>' for code in sorted_task_codes])
    ui_scope_json = json.dumps(uiScope)
    vid_json_payload = json.dumps(VID)

    # Convert event logs to a list safely
    events = baked_manager if isinstance(baked_manager, list) else []

    # Filter events to only this region
    region_events = [e for e in events if str(e.get('region')) == str(reg_id)]

    # Process events to find current state for UI rendering
    # { street_name: { unit_name: { "votes": X, "tags": { tag_code: val }, "active_votes": { vi_code: votes } } } }
    live_state = {}
    for ev in region_events:
        st_name = ev.get('street')
        unit_name = ev.get('unit')
        if not st_name or not unit_name:
            continue

        if st_name not in live_state:
            live_state[st_name] = {}
        if unit_name not in live_state[st_name]:
            live_state[st_name][unit_name] = {"tags": {}, "votes": 0, "active_votes": {}}

        ev_type = ev.get('type')
        if ev_type == 'tag':
            t_code = ev.get('tag_code')
            t_val = ev.get('value')
            live_state[st_name][unit_name]["tags"][t_code] = t_val
        elif ev_type == 'vote':
            v_val = int(ev.get('value', 0))
            vi_code = ev.get('vi_code', 'VI')
            live_state[st_name][unit_name]["votes"] = v_val
            live_state[st_name][unit_name]["active_votes"][vi_code] = v_val

    persistence_js = f'''
        <style>
            .tag-toggle {{
                cursor: pointer;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 0.85rem;
                display: inline-block;
                min-width: 28px;
                text-align: center;
                border: 1px solid #444;
                transition: background 0.2s, transform 0.1s;
            }}
            .tag-toggle:active {{
                transform: scale(0.92);
            }}
            .tag-active {{ background: #198754; color: white; border-color: #157347; }}
            .tag-inactive {{ background: #343a40; color: #6c757d; border-color: #495057; }}

            @media (max-width: 575.98px) {{
                .offcanvas.offcanvas-bottom {{
                    height: 100dvh !important;
                    max-height: 100dvh !important;
                    width: 100vw !important;
                    border-top-left-radius: 0 !important;
                    border-top-right-radius: 0 !important;
                }}
                .table-responsive {{
                    max-height: calc(100dvh - 58px);
                    overflow-y: auto;
                }}
            }}

            .table-responsive thead th {{
                position: sticky;
                top: 0;
                z-index: 5;
                background-color: #212529 !important;
                box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.15);
            }}
        </style>

        <script>
        (function() {{
            var scope = {ui_scope_json};
            window.VID_DATA = {vid_json_payload};

            setTimeout(function() {{
                var parentWindow = window.parent || window;

                document.querySelectorAll('.unit-selector').forEach(function(sel) {{
                    try {{
                        if (typeof parentWindow.initializeStreetRowState === 'function') {{
                            parentWindow.initializeStreetRowState(sel, scope);
                        }}
                    }} catch (rowErr) {{
                        console.error("❌ Error running initializeStreetRowState on row:", rowErr);
                    }}
                }});

                if (typeof parentWindow.replayLocalBakedDataForPopup === 'function') {{
                    try {{ parentWindow.replayLocalBakedDataForPopup(document); }}
                    catch (err) {{ console.error("❌ Local replay error:", err); }}
                }}
            }}, 220);
        }})();
        </script>
    '''

    html = persistence_js + f'''
    <div class="offcanvas-header bg-dark text-white border-bottom border-secondary py-3 px-3">
            <h6 class="offcanvas-title fw-bold text-info m-0 d-flex align-items-center fs-5">
                <i class="bi bi-geo-alt-fill me-2"></i> Region: {reg_id} ({uiScope.upper()})
            </h6>
            # No inline onclick handlers, no escaping headaches!
            <button type="button" class="btn-close btn-close-white"
                    data-bs-dismiss="offcanvas"
                    aria-label="Close"
                    style="transform: scale(1.2);"></button>
        </div>
        <div class="offcanvas-body bg-dark text-white p-0">
            <div class="table-responsive">
                <table class="table table-dark table-striped table-hover align-middle m-0" style="font-size: 0.85rem; min-width: 650px;">
                    <thead>
                        <tr class="table-active text-secondary">
                            <th class="ps-3 py-2" style="position: sticky; top: 0; z-index: 2; background: #212529;">Street Name</th>
                            <th class="py-2" style="width: 110px; position: sticky; top: 0; z-index: 2; background: #212529;">Unit</th>
                            {tag_headers_html}
                            <th class="py-2" style="width: 100px; position: sticky; top: 0; z-index: 2; background: #212529;">VI</th>
                            <th class="py-2 text-center" style="width: 100px; position: sticky; top: 0; z-index: 2; background: #212529;">Votes</th>
                            <th class="text-center py-2" style="position: sticky; top: 0; z-index: 2; background: #212529;">Total</th>
                            <th class="text-center py-2" style="position: sticky; top: 0; z-index: 2; background: #212529;">Range</th>
                            <th class="text-center pe-3 py-2" style="position: sticky; top: 0; z-index: 2; background: #212529;">Gaps</th>
                        </tr>
                    </thead>
                    <tbody>
    '''

    for i, (street_name, data) in enumerate(street_stats.items()):
        try:
            pd_code = streets_df[streets_df['StreetName'] == street_name]['PD'].iloc[0]
        except (KeyError, IndexError):
            pd_code = "UNKNOWN"

        unit_list = data.get("unit_list", [])
        unit_counts = data.get("unit_counts", {})
        hos = data.get("houses", 0)
        num_display = f"{data['min_num']} - {data['max_num']}" if data.get("min_num") is not None else "- / -"
        house_gaps_display = data.get("house_gaps", 0)

        # Retrieve current unit and state
        first_unit = unit_list[0] if unit_list else None
        first_unit_state = live_state.get(street_name, {}).get(first_unit, {}) if first_unit else {}

        # 1. Build Tag cells based on live state
        tag_cells = ""
        tags = first_unit_state.get("tags", {})
        for code in sorted_task_codes:
            is_active = str(tags.get(code, 'n')).lower() == 'y'
            status_class = "tag-active" if is_active else "tag-inactive"
            display_char = "y" if is_active else "n"

            tag_cells += f'''
                <td class="text-center px-1">
                    <span class="tag-toggle {status_class}" data-code="{code}" data-value="{display_char}" role="button" tabindex="0"
                          onclick="var p = window.parent || window; if(typeof p.handleTagClick === 'function') {{ p.handleTagClick(this, '{uiScope}'); }} if(typeof p.plotTaskProgress === 'function') {{ p.plotTaskProgress('{reg_id}', '{code}', '{uiScope}'); }} else if(typeof window.plotTaskProgress === 'function') {{ window.plotTaskProgress('{reg_id}', '{code}', '{uiScope}'); }}">
                        {display_char}
                    </span>
                </td>'''

        unit_options = "".join([f'<option value="{u}" data-max="{unit_counts.get(u, 1)}">{u}</option>' for u in unit_list])
        unit_dropdown = f'<select class="unit-selector form-select form-select-sm bg-secondary text-white border-0" onchange="var p = window.parent || window; p.handleUnitChangeVIUpdate(this); p.updateMaxVote(this); p.loadHouseData(this); p.updateTagToggles(this); p.refreshRowVoteBadge(this.closest(\'.canvass-row\'));" style="max-width: 95px;">{unit_options}</select>'

        max_votes = unit_counts.get(first_unit, 1) if first_unit else 1

        # 2. Determine default VI Code & active vote allocations
        unit_active_votes = {}
        for u in unit_list:
            unit_active_votes[u] = live_state.get(street_name, {}).get(u, {}).get("active_votes", {})

        default_vi_code = ""
        first_unit_votes = unit_active_votes.get(first_unit, {}) if first_unit else {}
        if first_unit_votes:
            valid_votes = {k: int(v) for k, v in first_unit_votes.items() if v is not None}
            if valid_votes:
                default_vi_code = str(max(valid_votes, key=valid_votes.get)).upper()

        if not default_vi_code and VID:
            default_vi_code = str(next(iter(VID.keys()))).upper()

        vi_options_html = ""
        if VID:
            for key, val in VID.items():
                selected_attr = ' selected="selected"' if str(key).upper() == str(default_vi_code).upper() else ""
                vi_options_html += f'<option value="{key}"{selected_attr}>{val}</option>'

        vi_select = f'<select class="vi-selector form-select form-select-sm bg-secondary text-white border-0" data-default="{default_vi_code}" onchange="var p = window.parent || window; p.updateVI(this); p.refreshRowVoteBadge(this.closest(\'.canvass-row\'));">{vi_options_html}</select>'

        db_vote_value = first_unit_votes.get(default_vi_code) if first_unit_votes else None
        initial_votes, initial_count_attr, visual_button_text = (int(db_vote_value), str(db_vote_value), f"{db_vote_value}/{max_votes}") if db_vote_value is not None and str(db_vote_value).strip() != "" else (0, "", f"0/{max_votes}")

        vote_button = f'<button class="vote-btn btn btn-sm btn-info text-dark fw-bold w-100" onclick="var p = window.parent || window; p.incrementVoteCount(this)" data-count="{initial_votes}" data-initial-count="{initial_count_attr}" data-max="{max_votes}">{visual_button_text}</button>'
        json_active_votes_db = json.dumps(unit_active_votes).replace('"', '&quot;')

        html += f'''
        <tr class="canvass-row border-secondary" data-scope="{uiScope}" data-region="{reg_id}" data-street="{street_name}" data-district="{pd_code}" data-initial-count="{initial_count_attr}" data-active-votes-db="{json_active_votes_db}">
            <td class="ps-3">
                <div class="fw-bold">{street_name}</div>
            </td>
            <td>{unit_dropdown}</td>
            {tag_cells}
            <td>{vi_select}</td>
            <td>{vote_button}</td>
            <td class="text-center font-monospace">{hos}</td>
            <td class="text-center font-monospace text-nowrap">{num_display}</td>
            <td class="text-center font-monospace pe-3">{house_gaps_display}</td>
        </tr>
        '''

    html += "</tbody></table></div></div>"
    return html

def preprocess_streets(df, task_tags=None):
    import pandas as pd
    from collections import Counter
    """
    Safely preprocesses street data, handling empty DataFrames gracefully.
    """
    if df is None or df.empty or len(df.columns) == 0:
        # Return empty stats and 0 house count if there's no data
        return {}, 0

    df = df.copy()
    task_tags = task_tags or {}
    sorted_task_codes = sorted(task_tags.keys())

    # 1. CLEANING
    for col in ["AddressPrefix", "AddressNumber", "StreetName"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(["nan", "None", ""], pd.NA)

    # 2. UNIQUE IDENTIFIER
    def combine_unit(row):
        p = str(row["AddressPrefix"]).strip() if pd.notna(row["AddressPrefix"]) else ""
        n = str(row["AddressNumber"]).strip() if pd.notna(row["AddressNumber"]) else ""
        if p and n:
            return f"{p} {n}"
        return p or n or "Unknown"

    df["unit"] = df.apply(combine_unit, axis=1)

    # 3. EXPLODE (comma-separated units)
    exploded = df.assign(unit=df["unit"].str.split(",")).explode("unit")
    exploded["unit"] = exploded["unit"].str.strip()
    exploded = exploded[exploded["unit"].notna() & (exploded["unit"] != "Unknown")]

    # 4. NUMERIC EXTRACTION
    exploded["num"] = exploded["unit"].str.extract(r'(\d+)')[0].astype(float)

    street_data = {}

    # 5. PER-STREET PROCESSING
    for street, group in exploded.groupby("StreetName"):
        group = group.copy()

        # --- Units + counts (single pass) ---
        unit_counts = Counter(group["unit"])
        units = sorted(unit_counts.keys())
        actual_houses = len(units)

        # --- HOUSEHOLD ACTIVE VI VOTES COUNT ---
# --- 🌟 UPDATED: HOUSEHOLD ACTIVE VOTES BY SPECIFIC VI CODE ---
        unit_active_votes = {}
        for unit, unit_group in group.groupby("unit"):
            # Initialize a dictionary for this specific house number
            unit_active_votes[unit] = {}

            if 'VI' in unit_group.columns:
                # Clean up the VI series to remove empty strings or nan entries
                cleaned_vi = unit_group['VI'].astype(str).str.strip().str.upper()
                cleaned_vi = cleaned_vi.replace(['NAN', 'NONE', ''], pd.NA).dropna()

                # Count occurrences of every specific intention code found at this address
                vi_counts = cleaned_vi.value_counts().to_dict()

                # Save the counts (e.g., {"R": 2, "D": 1}) converted safely to plain integers
                unit_active_votes[unit] = {str(vi): int(count) for vi, count in vi_counts.items()}

            else:
                unit_active_votes[unit] = 0

        # --- FAST TAG PROCESSING ---
        if 'Tags' in group.columns:
            tag_series = (
                group['Tags']
                .dropna()
                .astype(str)
                .str.upper()
                .str.replace(',', ' ')
                .str.split()
                .explode()
                .str.strip()
            )
            tag_set = set(tag_series)
        else:
            tag_set = set()

        street_tags = {
            code: ("y" if str(code).strip().upper() in tag_set else "n")
            for code in sorted_task_codes if str(code).strip()
        }

        # --- NUMBER ANALYSIS (Safe parsing alternative) ---
        valid_nums = group["num"].dropna()
        if not valid_nums.empty:
            nums = valid_nums.astype(int).unique() # Clean conversion safety
            nums.sort()

            min_num, max_num = int(nums.min()), int(nums.max())

            # Detect even/odd pattern
            if len(nums) > 1 and all(n % 2 == nums[0] % 2 for n in nums):
                estimated_houses = ((max_num - min_num) // 2) + 1
                expected_numbers = set(range(min_num, max_num + 1, 2))
            else:
                estimated_houses = (max_num - min_num) + 1
                expected_numbers = set(range(min_num, max_num + 1))

            missing_numbers = sorted(expected_numbers - set(nums))
        else:
            min_num = max_num = None
            estimated_houses = actual_houses
            missing_numbers = []

        # --- BUILD OUTPUT ---
        street_data[street] = {
            "houses": actual_houses,
            "estimated_houses": estimated_houses,
            "house_gaps": max(0, estimated_houses - actual_houses),
            "missing_numbers": missing_numbers,
            "unit_list": units,
            "unit_counts": dict(unit_counts),
            "unit_active_votes": unit_active_votes,
            "min_num": min_num,
            "max_num": max_num,
            "tags": street_tags
        }

    total_houses_count = sum(data["houses"] for data in street_data.values())
    print("END OF PREPROCESSING OF STREET DATA")
    return street_data, total_houses_count

def build_nodemap_list_html(herenode):
    """
    Build HTML tooltip listing all children of a node.
    Returns a string of safe HTML.
    """

    if not herenode or not getattr(herenode, "children", None):
        return "<em>No children</em>"

    items_html = []

    for child in herenode.children:

        label = getattr(child, "name", None) or getattr(child, "value", "") or "Unnamed"
        label = html.escape(str(label))

        missing = getattr(child, "house_gaps", None)

        if missing and missing > 0:
            label += f" <span style='color:#ffcc66'>(gap: {missing})</span>"

        items_html.append(f"<li>{label}</li>")

    tooltip_html = "<ul style='margin:0; padding-left:1em;'>" + "".join(items_html) + "</ul>"

    return tooltip_html

def get_children_within(parent_geom, children_gdf, threshold=0.5):


    proj_crs = "EPSG:3857"

    # Project parent
    parent_geom_proj = (
        gpd.GeoSeries([parent_geom], crs="EPSG:4326")
        .to_crs(proj_crs)
        .iloc[0]
    )

    # Project children
    children_proj = children_gdf.to_crs(proj_crs)

    selected_idx = []

    for idx, row in children_proj.iterrows():
        name = row.get("name") or row.get("NAME")
        geom = row.geometry

        if geom is None or geom.is_empty:
            print(f"❌ {name}: no geometry")
            continue

        inter_area = geom.intersection(parent_geom_proj).area
        total_area = geom.area if geom.area > 0 else 1e-9

        overlap = inter_area / total_area

        print(f"{name}: overlap={overlap:.3f} {'✅' if overlap >= threshold else '❌'}")

        if overlap >= threshold:
            selected_idx.append(idx)

    return children_gdf.loc[selected_idx].copy()



import numpy as np
from scipy.spatial import KDTree
# Ensure project_to_bng and project_to_wgs84 are imported if located in another module

def snap_houses_to_uprns(children, kdtree=None, coords=None, uprn_ids=None, max_distance_meters=25.0):
    """
    Strategy B Implementation:
    1. Unpacks spatial index inputs (kdtree, coords, uprn_ids) or handles dictionary payloads.
    2. Extracts known anchor nodes from children (e.g., nodes with explicit house numbers & coords).
    3. Interpolates candidate metrics along the trajectory.
    4. Uses KDTree to snap estimated positions to nearest unallocated UPRN point.

    :param children: List of child nodes representing properties/houses.
    :param kdtree: Pre-built cKDTree instance (or dict payload from legacy calls).
    :param coords: NumPy array or list of [lat, lon] coordinates matching KDTree indices.
    :param uprn_ids: List of UPRN string identifiers corresponding to coords.
    :param max_distance_meters: Dynamic distance buffer for snapping threshold.
    :return: Dict of {child_node_id: [lat, lon]}
    """
    mapped_coords = {}

    # Handle legacy dictionary invocation: snap_houses_to_uprns(children, street_uprn_coords)
    if isinstance(kdtree, dict) and coords is None:
        street_uprn_coords = kdtree
        uprn_ids = list(street_uprn_coords.keys())
        coords = [street_uprn_coords[uid] for uid in uprn_ids]
        kdtree = None  # Will rebuild BNG KDTree below

    # Guard: Return original latlongroids if no spatial data is available
    if (kdtree is None and (coords is None or len(coords) == 0)) or not children:
        for c in children:
            if hasattr(c, "latlongroid") and c.latlongroid:
                mapped_coords[c.value] = [float(c.latlongroid[0]), float(c.latlongroid[1])]
        return mapped_coords

    # Extract coordinates array if passed as list
    if coords is not None and not isinstance(coords, np.ndarray):
        coords = np.array(coords)

    # Convert UPRN coordinates to British National Grid (BNG) meters for isotropic calculations
    uprn_bng = []
    for lat, lon in coords:
        x, y = project_to_bng(float(lon), float(lat))
        uprn_bng.append([x, y])

    uprn_bng = np.array(uprn_bng)
    tree = KDTree(uprn_bng)

    # Extract anchors (children with valid numerical tags & non-zero latlongroid)
    anchors = {}
    for c in children:
        try:
            num = int(c.tagno)
            lat, lon = float(c.latlongroid[0]), float(c.latlongroid[1])
            if lat != 0.0 and lon != 0.0:
                x, y = project_to_bng(lon, lat)
                anchors[num] = (x, y)
        except (ValueError, TypeError, AttributeError):
            continue

    used_uprn_indices = set()
    num_uprns = len(coords)

    # Case 1: We have at least 2 anchors -> Calculate dynamic vector step
    if len(anchors) >= 2:
        sorted_anchor_nums = sorted(anchors.keys())
        n1, n2 = sorted_anchor_nums[0], sorted_anchor_nums[-1]
        p1 = np.array(anchors[n1])
        p2 = np.array(anchors[n2])

        unit_step = (p2 - p1) / (n2 - n1) if n2 != n1 else np.array([5.0, 0.0])

        for c in children:
            try:
                num = int(c.tagno)
                estimated_bng = p1 + unit_step * (num - n1)
            except (ValueError, TypeError, AttributeError):
                # Fallback to centroid if tagno isn't an integer
                try:
                    x, y = project_to_bng(float(c.latlongroid[1]), float(c.latlongroid[0]))
                    estimated_bng = np.array([x, y])
                except (ValueError, TypeError, AttributeError, IndexError):
                    continue

            # Query nearest UPRNs from BNG KDTree
            k_query = min(num_uprns, 10)  # Search up to 10 nearest neighbors
            distances, indices = tree.query(estimated_bng, k=k_query)

            if isinstance(indices, (int, np.integer)):
                indices = [indices]
                distances = [distances]

            # Pick closest unallocated UPRN within maximum distance buffer
            snapped_idx = None
            for dist, idx in zip(distances, indices):
                if idx not in used_uprn_indices and dist <= max_distance_meters:
                    snapped_idx = idx
                    used_uprn_indices.add(idx)
                    break

            if snapped_idx is not None:
                snapped_bng = uprn_bng[snapped_idx]
                lon, lat = project_to_wgs84(snapped_bng[0], snapped_bng[1])
                mapped_coords[c.value] = [lat, lon]

                # Attach metadata to child node
                if uprn_ids is not None and snapped_idx < len(uprn_ids):
                    c.snapped_uprn = uprn_ids[snapped_idx]
                c.snapped_by = "Strategy_B_VectorInterpolation"
            else:
                mapped_coords[c.value] = [float(c.latlongroid[0]), float(c.latlongroid[1])]

    # Case 2: Fallback when < 2 anchors are available -> Simple Nearest Neighbor from centroid
    else:
        for c in children:
            try:
                cx, cy = project_to_bng(float(c.latlongroid[1]), float(c.latlongroid[0]))
            except (ValueError, TypeError, AttributeError, IndexError):
                continue

            k_query = min(num_uprns, 10)
            distances, indices = tree.query([cx, cy], k=k_query)

            if isinstance(indices, (int, np.integer)):
                indices = [indices]
                distances = [distances]

            snapped = False
            for dist, idx in zip(distances, indices):
                if idx not in used_uprn_indices and dist <= max_distance_meters:
                    used_uprn_indices.add(idx)
                    snapped_bng = uprn_bng[idx]
                    lon, lat = project_to_wgs84(snapped_bng[0], snapped_bng[1])
                    mapped_coords[c.value] = [lat, lon]

                    if uprn_ids is not None and idx < len(uprn_ids):
                        c.snapped_uprn = uprn_ids[idx]
                    c.snapped_by = "Strategy_B_NearestNeighbor"
                    snapped = True
                    break

            if not snapped:
                mapped_coords[c.value] = [float(c.latlongroid[0]), float(c.latlongroid[1])]

    return mapped_coords

class ExtendedFeatureGroup(FeatureGroup):
    def __init__(self, name=None, overlay=True, control=True, show=True):
        super().__init__(
            name=name,
            overlay=overlay,
            control=control,
            show=show
        )
        self.name = name         # <--- explicitly store it
        self.key = None
        self.mytag = None
        self.id = None
        self.areashtml = {}



    def add_ghosts(self, tag_code, baked_events, parent_node, branchcolours):
        """
        Populates this layer with ghost polygons based on flat baked event logs.
        """
        import folium
        polygons_added = 0

        is_vi_task = (str(tag_code).upper() == 'VI')

        # Convert incoming events to a list if it isn't already
        events = baked_events if isinstance(baked_events, list) else []

        for child in parent_node.children:
            region_id = str(child.value)

            # 1. Filter events down to this specific region
            region_events = [e for e in events if str(e.get('region')) == region_id]
            if not region_events:
                continue

            # 2. Build the current state of each street from the event logs
            # Structure: { street_name: { unit_name: { "votes": X, "tags": { tag: val } } } }
            street_states = {}
            for ev in region_events:
                st_name = ev.get('street')
                unit_name = ev.get('house')
                if not st_name:
                    continue

                if st_name not in street_states:
                    street_states[st_name] = {}

                # Apply state mutation based on event
                ev_type = ev.get('type')
                if unit_name:
                    if unit_name not in street_states[st_name]:
                        street_states[st_name][unit_name] = {"tags": {}, "votes": 0}

                    if ev_type == 'tag':
                        t_code = ev.get('tag_code')
                        t_val = ev.get('value')
                        street_states[st_name][unit_name]["tags"][t_code] = t_val
                    elif ev_type == 'vote':
                        street_states[st_name][unit_name]["votes"] = int(ev.get('value', 0))

            # 3. Calculate Task Weight
            completed_weight = 0
            total_possible = len(street_states) if street_states else 1  # Fallback ceiling

            for street_name, units in street_states.items():
                has_task_progress = False

                if is_vi_task:
                    # Active if any unit has votes > 0
                    has_task_progress = any(u.get('votes', 0) > 0 for u in units.values())
                else:
                    # Active if any unit has the target tag set to 'y'
                    has_task_progress = any(u.get('tags', {}).get(tag_code) == 'y' for u in units.values())

                if has_task_progress:
                    completed_weight += 1  # Treating each active street as weight 1

            opacity = (0.8 * (completed_weight / total_possible)) if total_possible > 0 else 0

            # 4. Build the Ghost Polygon
            if opacity > 0:
                try:
                    if is_vi_task:
                        fill_color = "#800080"  # Purple for VI
                    else:
                        color_idx = int(tag_code[1:]) if tag_code[1:].isdigit() else 0
                        fill_color = branchcolours[color_idx % 12]

                    ghost_gj = folium.GeoJson(
                        child.geometry,
                        name=f"ghost_{tag_code}_{region_id}",
                        style_function=lambda x, op=opacity, col=fill_color: {
                            'fillColor': col,
                            'color': 'transparent',
                            'fillOpacity': op,
                            'interactive': False
                        }
                    )
                    ghost_gj.ghost_id = f"ghost_{tag_code}_{region_id}"
                    ghost_gj.add_to(self)
                    polygons_added += 1

                except Exception as e:
                    print(f"⚠️ Ghost Error: Failed adding ghost for {tag_code} in {region_id} -> {e}")

        print(f"DEBUG GHOSTS: Added {polygons_added} polygons to tag layer [{tag_code}]")
        return polygons_added

    def reset(self):
        # This clears internal children before rendering
        self._children.clear()
        self.areashtml = {}
        print("____reset the layer",len(self._children), self)
        return self


    def add_voronoi(self, CElection,rlevels, nodes_list, static=False):
        from shapely.geometry import Point
        from shapely.ops import nearest_points
        import numpy as np
        from flask import url_for
        from geovoronoi import voronoi_regions_from_coords
        from layers import Treepolys

        import pandas as pd
        import folium
        from elector import electors
        from elections import CurrentElection
        from collections import defaultdict

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        if not nodes_list:
            print("⚠️ No sub-units provided in nodes_list for Voronoi calculation.")
            return

        # Clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        task_tags, outcome_tags, all_tags = CElection.get_tags()

# -------------------------------------------------
        # 📦 STEP 1: Group by a structurally unique tuple key
        # -------------------------------------------------
        grouped_by_parent = defaultdict(list)
        parent_registry = {}  # Holds one concrete parent object instance per key

        for child in nodes_list:
            if not child.parent:
                print(f"⚠️ Skipping node {child.value}; it lacks a parent relation.")
                continue

            # Create an immutable structural key
            parent_key = (child.parent.type, child.parent.value, child.parent.fid)

            grouped_by_parent[parent_key].append(child)
            if parent_key not in parent_registry:
                parent_registry[parent_key] = child.parent

        # Total diagnostic counters across all groups
        grand_total_polygons_added = 0

        # -------------------------------------------------
        # 🔁 STEP 2: Process each parent group independently
        # -------------------------------------------------
        for parent_key, sub_nodes in grouped_by_parent.items():
            parent_node = parent_registry[parent_key]
            p_type, p_value, p_fid = parent_key

            print(f"\n--- Processing Voronoi Group for Parent: {p_value} ({p_type}) | Sub-nodes: {len(sub_nodes)} ---")

            try:
                pfile = Treepolys[parent_node.type]
                Territory_boundary = pfile[pfile['FID'] == int(parent_node.fid)]
                parent_node.geometry = Territory_boundary.union_all()
            except Exception as e:
                print(f"⚠️ Failed to look up spatial poly framework layer for {parent_node.type}: {e}")
                continue

            parent_boundary = parent_node.geometry
            if parent_boundary is None:
                print(f"⚠️ Parent boundary missing for parent node: {parent_node.value}")
                continue

            # Ensure geometric validity
            if not parent_boundary.is_valid:
                parent_boundary = parent_boundary.buffer(0)

            # Create a clean calculation bounding hull
            calc_hull = parent_boundary.convex_hull

            # Build coordinates for this isolated parent group
            points = []
            point_to_child = {}
            child_elector_map = {}

            for child in sub_nodes:
                child_elector_map[child] = electors.elector_for_path(rlevels, child.mapfile())
                if child.latlongroid and len(child.latlongroid) == 2:
                    child.centre = Point(child.latlongroid[1], child.latlongroid[0])  # lon, lat
                else:
                    child.centre = None

                if not child.centre:
                    continue

                pt = (round(float(child.centre.x), 6), round(float(child.centre.y), 6))
                point_to_child[pt] = child
                points.append(pt)

            if not points:
                print(f"⚠️ No valid sub-unit centers found inside {parent_node.value}")
                continue

            coords = np.array(points)

            # Ensure all points fall safely inside parent envelope
            fixed_points = []
            point_to_child_fixed = {}

            for pt in coords:
                point = Point(pt)
                if not parent_boundary.contains(point):
                    nearest = nearest_points(parent_boundary, point)[0]
                    new_pt = (round(nearest.x, 6), round(nearest.y, 6))
                else:
                    new_pt = (round(pt[0], 6), round(pt[1], 6))

                fixed_points.append(new_pt)
                point_to_child_fixed[new_pt] = point_to_child.get((round(pt[0], 6), round(pt[1], 6)))

            coords = np.array(fixed_points)
            point_to_child = point_to_child_fixed

            if len(coords) < 1:
                continue

# -------------------------------------------------
            # Run Voronoi Calculation Paths for this group
            # -------------------------------------------------
            region_polys = {}
            region_pts = {}

            # ✅ geovoronoi handles 3+ points flawlessly on its own without dummy hacks
            if len(coords) >= 3:
                region_polys, region_pts = voronoi_regions_from_coords(coords, calc_hull)
                print(f"DEBUG VORONOI: Built {len(region_polys)} regional cells using Convex Hull.")
            else:
                print(f"ℹ️ Low density point array ({len(coords)}). Initializing custom layout splittings...")
                if len(coords) == 1:
                    region_polys = {0: calc_hull}
                    region_pts = {0: [0]}

                elif len(coords) == 2:
                    from shapely.ops import split
                    from shapely.geometry import LineString

                    pt1, pt2 = coords[0], coords[1]
                    mid_x, mid_y = (pt1[0] + pt2[0]) / 2, (pt1[1] + pt2[1]) / 2
                    dx, dy = pt2[0] - pt1[0], pt2[1] - pt1[1]

                    scale = 20.0
                    dividing_line = LineString([
                        (mid_x - (-dy) * scale, mid_y - dx * scale),
                        (mid_x + (-dy) * scale, mid_y + dx * scale)
                    ])

                    split_result = split(calc_hull, dividing_line)
                    geoms = list(split_result.geoms) if hasattr(split_result, 'geoms') else [split_result]

                    for r_idx, geom in enumerate(geoms):
                        dist0 = geom.centroid.distance(Point(pt1))
                        dist1 = geom.centroid.distance(Point(pt2))
                        assigned_pt_idx = 0 if dist0 < dist1 else 1

                        region_polys[r_idx] = geom
                        region_pts[r_idx] = [assigned_pt_idx]

                elif len(coords) == 3:
                    min_x, min_y, max_x, max_y = calc_hull.bounds
                    dummy_point = np.array([[max_x + 10.0, max_y + 10.0]])
                    extended_coords = np.vstack([coords, dummy_point])

                    ext_polys, ext_pts = voronoi_regions_from_coords(extended_coords, calc_hull)

                    r_idx = 0
                    for k, poly in ext_polys.items():
                        assigned_indices = ext_pts[k]
                        if 3 not in assigned_indices and not poly.is_empty:
                            region_polys[r_idx] = poly
                            region_pts[r_idx] = assigned_indices
                            r_idx += 1

            # Load electors for this group's parent node envelope
            nodeelectors = electors.elector_for_path(rlevels, parent_node.mapfile())

            total_electorate = 0
            total_houses = 0

            # Loop through cells, intersection-clipping against this group's specific parent boundary
            for region_id, poly in region_polys.items():
                raw_intersection = poly.intersection(parent_boundary)

                if raw_intersection.is_empty:
                    continue

                if raw_intersection.geom_type in ['Polygon', 'MultiPolygon']:
                    actual_shape_poly = raw_intersection
                elif raw_intersection.geom_type == 'GeometryCollection':
                    polys = [g for g in raw_intersection.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]
                    if not polys:
                        continue
                    from shapely.ops import unary_union
                    actual_shape_poly = unary_union(polys)
                else:
                    continue

                if actual_shape_poly.is_empty or not actual_shape_poly.is_valid:
                    continue

                idx = region_pts[region_id]
                if isinstance(idx, (list, np.ndarray)):
                    idx = idx[0]

                coord = coords[idx]
                coord_key = (round(float(coord[0]), 6), round(float(coord[1]), 6))
                child = point_to_child.get(coord_key)

                if child is None:
                    continue

                child.voronoi_region = actual_shape_poly
                region_electors = child_elector_map.get(child, pd.DataFrame())

                # Navigation UI Links
                has_parent = child.parent is not None
                parent_mapfile = child.parent.mapfile() if has_parent else parent_node.mapfile()
                parent_value = child.parent.value if has_parent else parent_node.value

                upmessage = f"moveUp('/upbut/{parent_mapfile}','{parent_value}')"
                up_link = f'<a href="#" onclick="{upmessage}">⬆ Up</a>'

                if not static:
                    showmessageST = f"showMore('/walkdownST/{child.mapfile()}','{child.value}')"
                    street_link = f'<a href="#" onclick="{showmessageST}">Street view</a>'
                    nav_html = f"""
                    <div style="margin-bottom:8px; padding-left:22px; line-height:1.6;">
                    {street_link}<br>
                    {up_link}
                    </div>
                    """
                else:
                    nav_html = f"""
                    <div style="margin-bottom:8px; padding-left:22px; line-height:1.6;">
                    {up_link}
                    </div>
                    """

                street_stats, house_count = preprocess_streets(region_electors, task_tags)
                missing_total = sum(d['house_gaps'] for d in street_stats.values())

                child.electorate = len(region_electors)
                child.houses = house_count
                total_electorate += len(region_electors)
                total_houses += house_count

                if not region_electors.empty and 'PD' in region_electors.columns:
                    pd_code = str(region_electors.iloc[0]['PD']).strip().upper()
                else:
                    pd_code = str(child.value).split('_')[0].strip().upper()

                if not hasattr(self, '_pd_color_cache'):
                    self._pd_color_cache = {}

                if pd_code not in self._pd_color_cache:
                    import hashlib
                    hash_bytes = hashlib.md5(pd_code.encode('utf-8')).digest()
                    r = (hash_bytes[0] % 180) + 50
                    g = (hash_bytes[1] % 180) + 50
                    b = (hash_bytes[2] % 180) + 50
                    self._pd_color_cache[pd_code] = f"#{r:02x}{g:02x}{b:02x}"

                region_color = self._pd_color_cache[pd_code]

                tooltip_html = f"""
                <b>{child.value}</b><br>
                Electors: {len(region_electors)}<br>
                Houses: {house_count}<br>
                Elector/house: {round(len(region_electors)/house_count,2) if house_count else 0}<br>
                House gaps: {missing_total}
                """

    # ... (rest of your loop remains unchanged) ...

                street_html = nav_html + "<hr>" + build_street_list_html(child.value, region_electors, street_stats, task_tags)

                style = {
                    "fillColor": region_color,
                    "color": "white",
                    "weight": 1,
                    "fillOpacity": 0.6,
                }

                try:
                    # Clean up the HTML string to make sure it doesn't break JSON parsing

                    feature_properties = {
                        'nid': child.nid,
                        'region_id': child.value,
                        'type': 'voronoi_poly',
                        'expected_houses': house_count,
                        'level': getattr(child, 'level', 'PD'),
                        'street_html': street_html  # 👈 Pass the clean, safe string
                    }

                    if getattr(self, 'is_ghost', False):
                        feature_properties['style_type'] = 'grey_ghost'

                    geojson_feature = {
                        "type": "Feature",
                        "geometry": actual_shape_poly.__geo_interface__,
                        "properties": feature_properties
                    }

                    gj = folium.GeoJson(
                        geojson_feature,
                        style_function=lambda x, s=style: s,
                        tooltip=folium.Tooltip(
                            tooltip_html,
                            sticky=False,
                            direction="bottom",
                            offset=(0, 15),
                            style="background-color: white; color: #333; font-family: sans-serif; border-radius: 4px; padding: 6px; border: 1px solid #ccc; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
                        )
                    )

                    # ❌ REMOVED: Do not add folium.Popup here anymore!
                    # popup = folium.Popup(street_html, max_width=900, show=False)
                    # gj.add_child(popup)

                    gj.add_to(self)
                    grand_total_polygons_added += 1

                except Exception as e:
                    print(f"DEBUG ERROR: Failed adding canvas feature for {child.value} -> {e}")
            # Assign totals back to each respective parent container node safely
            parent_node.electorate = total_electorate
            parent_node.houses = total_houses

        print(f"\n🚀 GLOBAL VORONOI SUMMARY: Total map elements rendered across all groups: {grand_total_polygons_added}")

    def add_linestrings(self, CE,rlevels, herenode, nodes_list, static, counters):
        from layers import Treepolys
        from state import Candidates, LastResults, normalname
        from flask import session, flash
        import folium
        global levelcolours
        global Con_Results_data
        global OPTIONS

        print("\n" + "=" * 80)
        print("▶️ ENTERING add_linestrings")
        print("=" * 80)

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # Clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        # 🎯 SELF-AWARE PROPERTIES
        layer_type = getattr(self, "mytag", "street")

        raw_opts = getattr(self, "options", {}) or {}
        layer_style = raw_opts.get("style", raw_opts) if "style" in raw_opts else raw_opts
        print(f"DEBUG: self class: {self.__class__.__name__}")
        print(f"DEBUG: self.mytag evaluated to: '{layer_type}'")
        print(f"DEBUG: herenode details -> value: '{herenode.value}', type: '{herenode.type}', level: {herenode.level}")

        # Read from explicit decouple nodes list
        childlist = nodes_list
        allchildlist = herenode.children if herenode else []

        # Safe execution of helper function if exists
        try:
            nodeshtml = build_nodemap_list_html(herenode) if herenode else ""
        except NameError:
            nodeshtml = ""

        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
            "code": herenode.value,
            "details": details,
            "tooltip_html": nodeshtml,
        }

        print(f"_________Linestring: at {herenode.value} we have {len(childlist)} features to map of type:{layer_type}")

        if len(childlist) == 0:
            print(f"❌ WARNING: childlist is EMPTY for type '{layer_type}'. Line processing skipped!")

        # Reset counters of child type so that child tag = this node's childno
        accumulate = session.get("accumulate", False)
        if not accumulate:
            counters[layer_type] = counters.get(layer_type, 0)
            print(f"DEBUG: Reset counters['{layer_type}'] to 0")

        loop_counter = 0
        for c in childlist:
            loop_counter += 1
            print(f"\n--- Processing Linestring Feature #{loop_counter}: '{getattr(c, 'node_path', c.value)}' (c.fid={c.fid}) ---")

            if layer_type not in Treepolys:
                print(f"❌ ERROR: '{layer_type}' key missing from state.Treepolys dictionary!")
                continue

            pfile = Treepolys[layer_type]
            # 🔍 DEBUG: Check size, index, and columns of the loaded GeoDataFrame
            print(f"DEBUG [{layer_type}]: DataFrame row count (len): {len(pfile)}")
            print(f"DEBUG [{layer_type}]: Columns available: {list(pfile.columns)}")
            print(f"DEBUG [{layer_type}]: Index type/values sample: {list(pfile.index[:5])}")

            if not pfile.empty and len(pfile) > 0:
                print(f"DEBUG [{layer_type}]: First row preview:\n{pfile.iloc[0]}")

            # ------------------------------------------------------------------
            # ✅ FID MATCHING USING c.fid
            # ------------------------------------------------------------------
            id_col = next((col for col in ["FID", "identifier", "OBJECTID"] if col in pfile.columns), None)
            target_fid = str(c.fid)

            print(f"DEBUG [{layer_type}]: Querying c.fid='{target_fid}' against id_col='{id_col}'")

            # 1. Direct match check
            if id_col is not None:
                mask = pfile[id_col].astype(str) == target_fid
            else:
                mask = pfile.index.astype(str) == target_fid

            limbX = pfile[mask].copy()

            # 2. Fallbacks: Off-by-one offsets (e.g. 0-based c.fid vs 1-based GPKG FID) or iloc
            if len(limbX) == 0 and target_fid.isdigit():
                target_int = int(target_fid)
                offset_fid = str(target_int + 1)
                print(f"DEBUG [{layer_type}]: Direct match 0 rows. Retrying with +1 offset FID='{offset_fid}'")

                if id_col is not None:
                    mask = pfile[id_col].astype(str) == offset_fid
                else:
                    mask = pfile.index.astype(str) == offset_fid

                limbX = pfile[mask].copy()

                # Positional fallback if FID lookup fails
                if len(limbX) == 0 and 0 <= target_int < len(pfile):
                    print(f"DEBUG [{layer_type}]: Offset match 0 rows. Falling back to positional iloc[[{target_int}]]")
                    limbX = pfile.iloc[[target_int]].copy()

            # ------------------------------------------------------------------
            # FEATURE RENDER & POPUP GENERATION
            # ------------------------------------------------------------------
            if len(limbX) > 0:
                # Deduplicate multiple spatial slices to 1 row
                if len(limbX) > 1:
                    print(f"DEBUG [{layer_type}]: Multiple matches ({len(limbX)}) found for c.fid '{target_fid}'. Slicing first row.")
                    limbX = limbX.iloc[[0]].copy()

                target_idx = limbX.index[0]
                font_style = "style='font-size: 12pt;'"
                c_path = f"{c.mapfile()}"
                here_path = f"{herenode.mapfile()}"
                c_val = c.value
                here_val = herenode.value

                # LEVEL ROUTING RULES (Street & Walkleg Buttons)
                up_js = f"moveUp('/upbut/{here_path}', '{here_val}')"
                up_tag = f"<button type='button' id='btn_up_l6' onclick=\"{up_js}\" {font_style}>UP</button>"

                if layer_type == "street":
                    walkleg_js = f"moveDown('/downbut/{c_path}', '{c_val}')"
                    elector_js = f"moveDown('/electorreport/{c_path}', '{c_val}')"
                    leg_btn = f"<button type='button' class='guil-button btn btn-norm' onclick=\"{walkleg_js}\">Walk legs</button>"
                    elec_btn = f"<button type='button' class='guil-button btn btn-norm' onclick=\"{elector_js}\">Electors</button>"
                    limbX.at[target_idx, "UPDOWN"] = f"<br>{c_val}<br>{up_tag}<br>{leg_btn} {elec_btn}" if not static else f"<br>{c_val}<br>"
                    mapfile = f"/transfer/{c.mapfile()}"
                else:
                    limbX.at[target_idx, "UPDOWN"] = f"<br>{c_val}<br>{up_tag}" if not static else f"<br>{c_val}<br>"
                    mapfile = f"/transfer/{c.mapfile()}"

                counters[c.type] = counters.get(c.type, 0) + 1
                num = str(counters[c.type])
                tag = str(c.value)

                # Position marker using centroid coordinate
                here = [float(f"{c.latlongroid[0]:.6f}"), float(f"{c.latlongroid[1]:.6f}")]

                tcol_node = layer_style.get("fontColor", "#2563EB")
                fcol_node = layer_style.get("fillColor", "#3B82F6")

                marker_link = mapfile if not static else ""
                htmlhalo = f"""
                <a href="{marker_link}" data-name="{tag}">
                  <div style="color: {tcol_node}; font-size: 8pt; font-weight: bold; text-align: center; padding: 2px; white-space: nowrap; text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff, 0px 0px 3px #fff;">
                    <span style="background: {fcol_node}; color: #ffffff; padding: 1px 4px; border-radius: 4px; border: 1.5px solid black;">{num}</span>
                    {tag}
                  </div>
                </a>
                """.strip()

                html_popup_content = str(limbX.at[target_idx, "UPDOWN"])
                click_popup = folium.Popup(html_popup_content, max_width=300)

                # Render LineString GeoJSON
                folium.GeoJson(
                    limbX,
                    style_function=lambda feature: {
                        "color": layer_style.get("color", "#2563EB"),
                        "weight": layer_style.get("weight", 4.0),
                        "opacity": layer_style.get("opacity", 0.85),
                        "fill": False,
                        "dashArray": layer_style.get("dashArray", "0"),
                    },
                    highlight_function=lambda feature: {
                        "weight": layer_style.get("weight", 4.0) + 3,
                        "color": layer_style.get("highlightColor", "#1D4ED8"),
                        "opacity": 1.0,
                    },
                    tooltip=folium.Tooltip(htmlhalo),
                    popup=click_popup,
                ).add_to(self)

                self.add_child(folium.Marker(location=here, icon=folium.DivIcon(html=htmlhalo)))
            else:
                print(f"❌ WARNING: limbX contains 0 matching linestring rows for c.fid '{c.fid}'")

        print(f"\n🏁 LEAVING add_linestrings. Processed {loop_counter} linestrings.")
        print("=" * 80 + "\n")
        return self._children


    def lookup_linestrings(self, CElection, rlevels, parent_node, nodes_list, static=False):
        import hashlib
        from collections import defaultdict
        from state import normalname

        import folium
        import osmnx as ox

        from shapely import count_coordinates
        from shapely.geometry import LineString, MultiLineString
        from layers import Treepolys
        from state import stepify, pathify
        from elector import electors
        from elections import CurrentElection

        # Guard: Ensure single election context
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        if not nodes_list:
            print("⚠️ No sub-units provided in nodes_list for LineString calculation.")
            return

        # Unpack current election context
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")
        task_tags, outcome_tags, all_tags = CElection.get_tags()

        # Helper: Enhanced street name matcher handling tokens & variations
        def matches_target_street(osm_name, target_norm, raw_target):
            if not osm_name:
                return False

            names_to_check = osm_name if isinstance(osm_name, list) else [osm_name]
            clean_target = raw_target.replace('_', ' ').strip().upper()
            target_tokens = set(clean_target.split())

            for name in names_to_check:
                clean_osm = str(name).replace('_', ' ').strip().upper()
                norm_osm = normalname(clean_osm)

                # 1. Exact normalized or raw string match
                if clean_osm == clean_target or norm_osm == target_norm:
                    return True

                # 2. Substring matching
                if clean_target in clean_osm or clean_osm in clean_target:
                    return True

                # 3. Token set matching (e.g. "RAILWAY COTTAGES" in "1-4 RAILWAY COTTAGES")
                osm_tokens = set(clean_osm.split())
                if len(target_tokens) > 1 and target_tokens.issubset(osm_tokens):
                    return True

            return False

        # -------------------------------------------------
        # 📦 STEP 1: Group street nodes by parent container
        # -------------------------------------------------
        grouped_by_parent = defaultdict(list)
        parent_registry = {}

        for child in nodes_list:
            if not child.parent:
                print(f"⚠️ Skipping node {child.value}; it lacks a parent relation.")
                continue

            parent_key = (child.parent.type, child.parent.value, child.parent.fid)
            grouped_by_parent[parent_key].append(child)
            if parent_key not in parent_registry:
                parent_registry[parent_key] = child.parent

        grand_total_linestrings_added = 0

        # -------------------------------------------------
        # 🔁 STEP 2: Process each street group
        # -------------------------------------------------
        for parent_key, sub_nodes in grouped_by_parent.items():
            grp_parent_node = parent_registry[parent_key]
            p_type, p_value, p_fid = parent_key

            print(f"\n--- Fetching OSM LineStrings for Group Parent: {p_value} ({p_type}) | Streets: {len(sub_nodes)} ---")

            total_electorate = 0
            total_houses = 0

            # Retrieve Ward Geometry accurately using parent references
            sample_child = sub_nodes[0]
            ward_node = sample_child.parent.parent if (sample_child.parent and sample_child.parent.parent) else grp_parent_node
            ward_fid = ward_node.fid if ward_node and hasattr(ward_node, 'fid') else None
            ward_polygon = Treepolys['ward'].get(ward_fid) if (Treepolys and 'ward' in Treepolys and ward_fid is not None) else None

            # Fetch all highway geometries in the Ward bounding polygon via OSMnx features API
            gdf_ward_highways = None
            if ward_polygon is not None and not ward_polygon.is_empty:
                try:
                    print(f"🌐 Querying OSM highway features via Ward Polygon (FID: {ward_fid})...")
                    gdf_ward_highways = ox.features_from_polygon(ward_polygon, tags={"highway": True})
                    if not gdf_ward_highways.empty:
                        gdf_ward_highways = gdf_ward_highways[
                            gdf_ward_highways.geometry.type.isin(['LineString', 'MultiLineString'])
                        ]
                        # 🔍 DEBUG PRINT 1: Check what OSM streets were returned in the Ward
                        if 'name' in gdf_ward_highways.columns:
                            osm_names = gdf_ward_highways['name'].dropna().unique().tolist()
                            print(f"  [DEBUG OSM Polygon] Found {len(gdf_ward_highways)} lines. Sample OSM names in Ward: {osm_names[:15]}")
                        else:
                            print("  [DEBUG OSM Polygon] Highways returned but NO 'name' column present in GeoDataFrame.")
                    else:
                        print("  [DEBUG OSM Polygon] Query succeeded but returned 0 highway features.")
                except Exception as e:
                    print(f"⚠️ OSM highway query failed for Ward FID {ward_fid}: {e}")
            else:
                print(f"  [DEBUG OSM Polygon] Ward polygon for FID {ward_fid} is None or Empty!")

            # -------------------------------------------------
            # 🚗 STEP 3: Match & Retrieve individual street geometries
            # -------------------------------------------------
            for child in sub_nodes:
                elector_path = pathify(stepify(child.mapfile()))

                raw_street_name = str(child.value).strip() if child.type == 'street' else str(child.parent.value).strip() if child.parent else str(child.value).strip()

                # Clean and normalize target street name
                clean_street_str = raw_street_name.replace('_', ' ')
                target_norm = normalname(clean_street_str)

                # Dynamic hierarchy parsing
                pd_node = child.parent if child.type == 'street' else (child.parent.parent if child.parent else None)
                ward_node = pd_node.parent if pd_node else None
                constituency_node = ward_node.parent if ward_node else None

                pd_raw = str(pd_node.value) if pd_node else ""
                polling_district = pd_raw.split('_')[0].strip() if '_' in pd_raw else pd_raw
                ward_name = str(ward_node.value) if ward_node else ""
                constituency_name = str(constituency_node.value) if constituency_node else ""

                # Load electors
                street_electors = electors.elector_for_path(rlevels, elector_path)
                street_stats, house_count = preprocess_streets(street_electors, task_tags)

                child.electorate = len(street_electors)
                child.houses = house_count
                total_electorate += len(street_electors)
                total_houses += house_count

                street_geom = None

                # Strategy A: Filter Ward highways GeoDataFrame by street name match
                if gdf_ward_highways is not None and not gdf_ward_highways.empty and 'name' in gdf_ward_highways.columns:
                    matched = gdf_ward_highways[
                        gdf_ward_highways['name'].apply(lambda val: matches_target_street(val, target_norm, raw_street_name))
                    ]
                    if not matched.empty:
                        street_geom = matched.geometry.union_all()

                # Strategy B: Centroid point radius search fallback if polygon lookup failed to find street
                if (street_geom is None or street_geom.is_empty) and hasattr(child, 'latlongroid') and child.latlongroid:
                    try:
                        lat, lon = child.latlongroid[0], child.latlongroid[1]
                        gdf_dist = ox.features_from_point((lat, lon), tags={"highway": True}, dist=500)
                        if not gdf_dist.empty and 'name' in gdf_dist.columns:
                            lines = gdf_dist[gdf_dist.geometry.type.isin(['LineString', 'MultiLineString'])]
                            matched = lines[lines['name'].apply(lambda val: matches_target_street(val, target_norm, raw_street_name))]
                            if not matched.empty:
                                street_geom = matched.geometry.union_all()
                    except Exception as e:
                        pass

                # Strategy C: Centroid Stub Fallback if all OSM queries return no geometry match
                if (street_geom is None or street_geom.is_empty) and hasattr(child, 'latlongroid') and child.latlongroid and len(child.latlongroid) == 2:
                    lat, lon = child.latlongroid[0], child.latlongroid[1]
                    street_geom = LineString([(lon - 0.0005, lat), (lon + 0.0005, lat)])
                    print(f"⚠️ Created stub fallback line for {raw_street_name}")

                if street_geom is None or street_geom.is_empty:
                    print(f"❌ Failed to retrieve OSM LineString for street: {raw_street_name}")
                    continue

                point_count = count_coordinates(street_geom)
                print(f"Street: {raw_street_name} | Geometry points found: {point_count}")

                # -------------------------------------------------
                # 🎨 STEP 4: Color Styling & Navigation Links
                # -------------------------------------------------
                pd_code = polling_district.upper()
                if not hasattr(self, '_pd_color_cache'):
                    self._pd_color_cache = {}

                if pd_code not in self._pd_color_cache:
                    hash_bytes = hashlib.md5(pd_code.encode('utf-8')).digest()
                    r = (hash_bytes[0] % 180) + 50
                    g = (hash_bytes[1] % 180) + 50
                    b = (hash_bytes[2] % 180) + 50
                    self._pd_color_cache[pd_code] = f"#{r:02x}{g:02x}{b:02x}"

                line_color = self._pd_color_cache[pd_code]

                has_parent = child.parent is not None
                parent_mapfile = child.parent.mapfile() if has_parent else grp_parent_node.mapfile()
                parent_val = child.parent.value if has_parent else grp_parent_node.value

                upmessage = f"moveUp('/upbut/{parent_mapfile}','{parent_val}')"
                up_link = f'<a href="#" onclick="{upmessage}">⬆ Up</a>'

                if not static:
                    showmessageST = f"showMore('/walkdownST/{child.mapfile()}','{child.value}')"
                    street_link = f'<a href="#" onclick="{showmessageST}">Street view</a>'
                    nav_html = f"""
                    <div style="margin-bottom:8px; padding-left:10px; line-height:1.6;">
                    {street_link}<br>
                    {up_link}
                    </div>
                    """
                else:
                    nav_html = f"""
                    <div style="margin-bottom:8px; padding-left:10px; line-height:1.6;">
                    {up_link}
                    </div>
                    """

                # -------------------------------------------------
                # 💬 STEP 5: Construct Popup & Tooltip HTML
                # -------------------------------------------------
                popup_html = f"""
                <div style="font-family: sans-serif; font-size: 13px; min-width: 180px;">
                    <h4 style="margin: 0 0 6px 0; color: #2c3e50;">{raw_street_name}</h4>
                    {nav_html}
                    <hr style="border: none; border-top: 1px solid #ccc; margin: 8px 0;">
                    <b>Houses:</b> {house_count}<br>
                    <b>Electors:</b> {len(street_electors)}<br>
                    <b>Polling District:</b> {polling_district}<br>
                    <b>Ward:</b> {ward_name}<br>
                    <b>Constituency:</b> {constituency_name}
                </div>
                """

                tooltip_html = f"""
                <b>Street:</b> {raw_street_name}<br>
                <b>Houses:</b> {house_count}<br>
                <b>Electors:</b> {len(street_electors)}<br>
                <b>PD:</b> {polling_district}
                """

                style = {
                    "color": line_color,
                    "weight": 4,
                    "opacity": 0.85,
                }

                # -------------------------------------------------
                # 🗺️ STEP 6: Add GeoJSON Feature to Folium
                # -------------------------------------------------
                try:
                    geojson_feature = {
                        "type": "Feature",
                        "geometry": street_geom.__geo_interface__,
                        "properties": {
                            'nid': child.nid,
                            'street_name': raw_street_name,
                            'houses': house_count,
                            'electors': len(street_electors),
                            'polling_district': polling_district,
                            'ward': ward_name,
                            'constituency': constituency_name
                        }
                    }

                    gj = folium.GeoJson(
                        geojson_feature,
                        style_function=lambda x, s=style: s,
                        tooltip=folium.Tooltip(
                            tooltip_html,
                            sticky=False,
                            direction="bottom",
                            offset=(0, 10),
                            style="background-color: white; color: #333; font-family: sans-serif; border-radius: 4px; padding: 6px; border: 1px solid #ccc;"
                        )
                    )

                    folium.Popup(popup_html, max_width=300).add_to(gj)
                    gj.add_to(self)
                    grand_total_linestrings_added += 1

                except Exception as e:
                    print(f"DEBUG ERROR: Failed adding OSM LineString feature for street {child.value} -> {e}")

            # Assign calculated totals back to group parent node
            grp_parent_node.electorate = total_electorate
            grp_parent_node.houses = total_houses

        print(f"\n🚀 OSM LINESTRING SUMMARY: Retrieved and added {grand_total_linestrings_added} dynamic street features directly to the map layer.")




    def add_tag_layer(self, rlevels, node, tags, operator, layer_name, icon_color, icon_name, header_color, target_cluster=None, static=False):
        """
        Advanced centralized backend filter engine on the ExtendedFeatureGroup class.
        Filters electors for the explicitly passed node and mounts them to the layer.
        """
        import pandas as pd
        import folium
        import logging
        from folium.plugins import MarkerCluster
        from elector import electors

        logger = logging.getLogger(__name__)

        # 🎯 FIX 1: Safely use the passed node to get the file path
        path = node.mapfile()
        node_electors = electors.elector_for_path(rlevels, path)

        if node_electors is None or node_electors.empty:
            return 0

        if 'Tags' not in node_electors.columns:
            logger.warning(f"Tags column missing for path: {path}")
            return 0

        # ... [Keep your exact same Pandas tag filtering logic here] ...
        if isinstance(tags, str):
            tags = [tags]
        tags = [t.strip() for t in tags if t.strip()]
        if not tags:
            return 0

        operator = operator.strip().upper()
        tags_series = node_electors['Tags'].astype(str)

        if len(tags) == 1 or operator == 'OR':
            combined_pattern = rf"\b({'|'.join(tags)})\b"
            mask = tags_series.str.contains(combined_pattern, na=False, regex=True)
        elif operator == 'AND':
            mask = pd.Series(True, index=node_electors.index)
            for tag in tags:
                mask &= tags_series.str.contains(rf"\b{tag}\b", na=False, regex=True)
        else:
            raise ValueError("Invalid operator selection. Use 'AND' or 'OR'.")

        filtered_electors = node_electors[mask]
        if filtered_electors.empty:
            return 0

        # 🎯 FIX 2: Cluster Management
        # If no cluster was passed down, look for an existing one or create it directly on self
        if target_cluster is None:
            # Try to fetch an existing cluster child from this ExtendedFeatureGroup to prevent duplicate groups
            existing_clusters = [child for child in self._children.values() if isinstance(child, MarkerCluster)]
            if existing_clusters:
                target_cluster = existing_clusters[0]
            else:
                # Initialize a clean cluster inside this ExtendedFeatureGroup container
                target_cluster = MarkerCluster(name=layer_name, control=False).add_to(self)

        markers_added = 0
        for _, elector in filtered_electors.iterrows():
            lat, lon = elector.get('Lat'), elector.get('Long')
            if pd.isna(lat) or pd.isna(lon):
                continue

            # --- Name & Address Construction ---
            fn = str(elector.get('Firstname', '')).replace('_', ' ').strip()
            init = str(elector.get('Initials', '')).replace('_', ' ').strip()
            sn = str(elector.get('Surname', '')).replace('_', ' ').strip()
            full_name = " ".join([p for p in [fn, init, sn] if p]).title()

            def get_val(k): return "" if pd.isna(elector.get(k, "")) else str(elector.get(k, "")).strip()
            pref, num, street, pc = get_val('AddressPrefix'), get_val('AddressNumber'), get_val('StreetName'), get_val('Postcode')
            main_line = " ".join([p for p in [f"{pref}," if pref else "", num, street] if p]).replace(" ,", ",")
            display_address = f"{main_line}, {pc}" if pc else main_line

            popup_html = f"""
                <div style="font-family: Arial, sans-serif; min-width: 200px; font-size: 13px; line-height: 1.4;">
                    <div style="background-color: {header_color}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; margin-bottom: 6px; text-align: center;">
                        {layer_name}
                    </div>
                    <div style="font-weight: bold; font-size: 14px; color: #111;">{full_name}</div>
                    <div style="color: #444; margin-bottom: 6px;">{display_address}</div>
                    <div style="border-top: 1px dotted #ccc; padding-top: 4px; font-size: 11px; color: #777;">
                        <strong>Elector No:</strong> {elector.get('ENOP', 'N/A')}
                    </div>
                </div>
            """

            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color=icon_color, icon=icon_name, prefix='fa'),
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=full_name
            ).add_to(target_cluster)
            markers_added += 1

        return markers_added

    def add_genmarkers(self,CElection,rlevels, node, static):
        eventlist = node.build_eventlist_dataframe(rlevels, CElection)
        print(f" ___GenMarkers: under {state.route()} eventlist: {eventlist}")
        for _, row in eventlist.iterrows():

            for place in row["places"]:
                lat = place["lat"]
                lng = place["lng"]
                tag = place["prefix"]
                url = place["url"]

                days_to = (row["date"] - datetime.today().date()).days
                fontsize = compute_font_size(days_to)

                tooltip = f"{tag} ({row['date']})"
                print(f"___layer marker: {tag} at {lat},{lng} on {row['date']}")

                self.add_child(folium.Marker(
                    location=[lat, lng],
                    tooltip=tooltip,
                    icon=folium.DivIcon(html=f"""
                        <a href='{url}' data-name='{tag}'>
                            <div style="color:yellow;font-weight:bold;text-align:center;padding:2px;">
                                <span style="font-size:{fontsize}px;background:red;padding:1px 2px;
                                             border-radius:5px;border:2px solid black;">
                                    {days_to}
                                </span> {tag}
                            </div>
                        </a>
                    """)
                ))

        return eventlist

    def add_nodemaps(self, CElection, rlevels, herenode, nodes_list, static, counters):
        from state import Candidates, LastResults
        from flask import session, flash
        from elections import CurrentElection
        import pandas as pd
        import folium
        from elector import electors

        global levelcolours
        global Con_Results_data
        global OPTIONS

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        (c_election, elevels), = rlevels.items()
        task_tags, outcome_tags, all_tags = CElection.get_tags()
        # 🎯 SELF-AWARE PROPERTIES (mytag represents the type of nodes being added)
        layer_type = getattr(self, "mytag", "ward")
        print("\n" + "=" * 80)
        print(f"▶️ ENTERING add_nodemaps (type: '{layer_type}')")
        print("=" * 80)

        raw_opts = getattr(self, "options", {}) or {}
        layer_style = raw_opts.get("style", raw_opts) if "style" in raw_opts else raw_opts

        childlist = nodes_list
        allchildlist = herenode.children if herenode else []

        print(
            f"_________Nodemap: at {herenode.value if herenode else 'NONE'} "
            f"we have {len(childlist)} features to map of type:{layer_type}"
        )

        if len(childlist) == 0:
            print(f"❌ WARNING: childlist is EMPTY for type '{layer_type}'. Skipping loops.")

        # ------------------------------------------------------------------
        # GENERATE HEADER TOOLTIP HTML FOR THE CURRENT NODE
        # ------------------------------------------------------------------
        reg_id = getattr(herenode, 'value', 'UNKNOWN')
        if layer_type == 'street': # ie the children are streets
            streets_df = electors.elector_for_path(rlevels, herenode.mapfile())
            if not streets_df.empty:
                street_stats, _ = preprocess_streets(streets_df, task_tags=task_tags)
                nodeshtml = build_street_list_html(reg_id, streets_df, street_stats, task_tags, uiScope="walk")
            else:
                nodeshtml = f"<div class='p-2 bg-dark text-white'>No street data for this walk {reg_id}</div>"
        else:
            nodeshtml = build_nodemap_list_html(herenode) if herenode else ""

        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
            "code": herenode.value,
            "details": details,
            "tooltip_html": nodeshtml
        }

        # Reset counters of child type so that child tag = this node's childno
        accumulate = session.get("accumulate", False)
        popup_body = ""
        if not accumulate:
            counters[layer_type] = counters.get(layer_type, 0)

        # ------------------------------------------------------------------
        # POLYGON LAYERS RENDERING LOOP
        # ------------------------------------------------------------------
        loop_counter = 0
        for c in childlist:
            loop_counter += 1

            if c.level < 7:
                # Resolve lookup key fallback for 'walk' -> 'ward' if 'walk' not pre-cached in Treepolys
                lookup_key = 'walk' if ('walk' in Treepolys and layer_type == 'walk') else ('ward' if layer_type == 'walk' else layer_type)

                if lookup_key not in Treepolys:
                    print(f"❌ ERROR: '{lookup_key}' key missing from state.Treepolys dictionary!")
                    continue

                pfile = Treepolys[lookup_key]
                mask = pfile['FID'] == int(c.fid)
                limbX = pfile[mask].copy()

                if len(limbX) > 0:
                    # Force-clean duplicate geographic slice occurrences to 1 clean unique spatial entity row
                    if len(limbX) > 1:
                        limbX = limbX.iloc[[0]].copy()

                    target_idx = limbX.index[0]
                    font_style = "style='font-size: 12pt;'"
                    c_path = f"{c.mapfile()}"
                    here_path = f"{herenode.mapfile()}"
                    c_val = c.value
                    here_val = herenode.value
                    mapfile = f"/transfer/{c.mapfile()}"

                    # Standard JavaScript Callbacks for Up and Down Navigation
                    up_js = f"moveUp('/upbut/{here_path}', '{here_val}')"
                    down_js = f"moveDown('/downbut/{c_path}', '{c_val}')"

                    # Standardized Up and Down Tag Buttons
                    up_tag = f"<button type='button' class='guil-button btn btn-norm' onclick=\"{up_js}\" {font_style}>UP</button>"
                    down_tag = f"<button type='button' class='guil-button btn btn-norm' onclick=\"{down_js}\" {font_style}>DOWN</button>"

                    # ------------------------------------------------------------------
                    # LEVEL ROUTING & POPUP CONTENT GENERATION
                    # ------------------------------------------------------------------
                    # Initialize default polygon tooltip content
                    polygon_tooltip_content = f"<b>{c_val}</b>"
                    print(f"\n--- Processing Feature #{loop_counter}: '{getattr(c, 'node_path', c.value)}' ---")


                    if layer_type in ['nation', 'constituency', 'ward', 'division']:
                        popup_body = f"<br><strong>{c_val}</strong><br>{up_tag}<br>{down_tag}"

                    elif layer_type == 'county':
                        ward_js = f"moveDown('/wardreport/{c_path}', '{c_val}')"
                        div_js = f"moveDown('/divreport/{c_path}', '{c_val}')"

                        ward_tag = f"<button type='button' id='btn_ward_l1' class='guil-button btn btn-norm' onclick=\"{ward_js}\" {font_style}>WARD Report</button>"
                        div_tag = f"<button type='button' id='btn_div_l1' class='guil-button btn btn-norm' onclick=\"{div_js}\" {font_style}>DIV Report</button>"

                        popup_body = f"<br><strong>{c_val}</strong><br>{up_tag}<br>{ward_tag}{div_tag}<br>{down_tag}"

                    elif layer_type == 'walk': # ie children are walks, grandchildren are streets
                        has_parent = c.parent is not None
                        parent_mapfile = c.parent.mapfile() if has_parent else herenode.mapfile()
                        parent_value = c.parent.value if has_parent else herenode.value

                        upmessage = f"moveUp('/upbut/{parent_mapfile}','{parent_value}')"
                        up_link = f'<a href="#" onclick="{upmessage}">⬆ Up</a>'

                        if not static:
                            showmessageST = f"showMore('/walkdownST/{c.mapfile()}','{c_val}')"
                            street_link = f'<a href="#" onclick="{showmessageST}">Street view</a>'
                            nav_html = f"""
                            <div style="margin-bottom:8px; padding-left:22px; line-height:1.6;">
                            {street_link}<br>
                            {up_link}
                            </div>
                            """
                        else:
                            nav_html = f"""
                            <div style="margin-bottom:8px; padding-left:22px; line-height:1.6;">
                            {up_link}
                            </div>
                            """

                        # ✅ RELIABLE ELECTOR FETCH (Matches add_voronoi approach)
                        try:
                            child_df = electors.elector_for_path(rlevels, c.mapfile())
                            print(f"DEBUG: elector_for_path size {len(child_df)}")
                        except Exception as e:
                            print(f"DEBUG: elector_for_path failed for {c_val}: {e}")
                            child_df = pd.DataFrame()

                        street_stats, house_count = preprocess_streets(child_df, task_tags=task_tags)
                        missing_total = sum(d.get('house_gaps', 0) for d in street_stats.values())
                        electorate_count = len(child_df)

                        # Build the rich metric tooltip HTML string for walk regions
                        polygon_tooltip_content = f"""
                        <b>{c_val}</b><br>
                        Electors: {electorate_count}<br>
                        Houses: {house_count}<br>
                        Elector/house: {round(electorate_count/house_count, 2) if house_count else 0}<br>
                        House gaps: {missing_total}
                        """

                        if not child_df.empty:
                            street_table_html = build_street_list_html(c_val, child_df, street_stats, task_tags, uiScope="walk")
                        else:
                            street_table_html = f"<div class='p-2 text-warning'>No street metrics for {c_val}</div>"

                        street_html = nav_html + "<hr>" + street_table_html
                        popup_body = street_html
                    else:
                        popup_body = f"<br><strong>{c_val}</strong><br>{up_tag}<br>{down_tag}"

                    # Assign UPDOWN safely to avoiding pandas indexing key issues


                    limbX['UPDOWN'] = popup_body

                    # ------------------------------------------------------------------
                    # MARKER / LABEL HOOKS
                    # ------------------------------------------------------------------
                    party_val = getattr(c, 'party', '')
                    party = f"({party_val})" if party_val else "X"
                    counters[c.type] = counters.get(c.type, 0) + 1
                    num = str(counters[c.type])
                    tag = str(c.value)
                    numtag = str(c.value) + party
                    here = [float(f"{c.latlongroid[0]:.6f}"), float(f"{c.latlongroid[1]:.6f}")]

                    tcol_node = layer_style.get("fontColor", "#EF4444")
                    fcol_node = layer_style.get("fillColor", "#EF4444")

                    if c.type == 'division' and isinstance(getattr(c, 'candidates', None), dict):
                        c1 = c.candidates.get('Candidate_1', '')
                        c2 = c.candidates.get('Candidate_2', '')
                        sub_label = f"[{c1},{c2}]"
                    elif layer_type == 'walk':
                        sub_label = f"Houses: {getattr(c, 'house_count', 'N/A')}"
                    else:
                        sub_label = ""

                    htmlhalo = f'''
                    <a href="{mapfile}" data-name="{tag}">
                      <div style="color: {tcol_node}; font-size: 8pt; font-weight: bold; text-align: center; padding: 2px; white-space: nowrap; text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff, 0px 0px 3px #fff;">
                        <span style="background: {fcol_node}; padding: 1px 2px; border-radius: 5px; border: 2px solid black;">{num}</span>
                        {numtag}<br>
                        <span style="font-size: 6pt; font-weight: normal;">{sub_label}</span>
                      </div>
                    </a>
                    '''

                    htmlhalostatic = f'''
                    <a href="" data-name="{tag}">
                      <div style="color: {tcol_node}; font-size: 8pt; font-weight: bold; text-align: center; padding: 2px; white-space: nowrap; text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff, 0px 0px 3px #fff;">
                        <span style="background: {fcol_node}; padding: 1px 2px; border-radius: 5px; border: 2px solid black;">{num}</span>
                        {numtag}<br>
                        <span style="font-size: 6pt; font-weight: normal;">{sub_label}</span>
                      </div>
                    </a>
                    '''

                    # --- DEBUG: Insert inside your feature processing loop ---
                    print(f"================ [POPUP DEBUG] ================")
                    print(f"🔍 Feature Name / Code: {c_val}")
                    print(f"🔍 Feature Path (c_path): {c_path}")
                    print(f"🔍 Layer Type (layer_type): {layer_type}")
                    print(f"🔍 Generated up_tag: {repr(up_tag)}")
                    print(f"🔍 Generated down_tag: {repr(down_tag)}")
                    print(f"🔍 Generated popup_body: {repr(popup_body)}")

                    click_popup = folium.Popup(popup_body, max_width=700 if layer_type == 'walk' else 300)

                    # 1. POLYGON GEOJSON WITH CORRECT TOOLTIP CONTENT
                    # ------------------------------------------------------------------
                    # FEATURE PROPERTIES & GEOJSON DICT CONSTRUCTION
                    # ------------------------------------------------------------------
                    try:
                        geom_obj = limbX.geometry.iloc[0]

                        # Base properties for all layers
                        feature_properties = {
                            'region_id': c_val,
                            'type': layer_type,
                        }

                        # Only add street_html if it's a walk layer
                        if layer_type == 'walk':
                            feature_properties['street_html'] = street_html

                        geojson_feature = {
                            "type": "Feature",
                            "geometry": geom_obj.__geo_interface__,
                            "properties": feature_properties
                        }

                        # Define base arguments for GeoJson (NO popup argument here)
                        geojson_kwargs = {
                        "style_function": lambda feature, style=layer_style: {
                            "fillColor": style.get("fillColor", "#EF4444"),
                            "color": style.get("color", "#991B1B"),
                            "weight": style.get("weight", 2.5),
                            "opacity": 1.0,
                            "fillOpacity": max(style.get("fillOpacity", 0.15), 0.01),
                            "stroke": True,
                            "fill": True,
                            "dashArray": style.get("dashArray", "0"),
                            },
                            "highlight_function": lambda feature: {
                                "weight": layer_style.get("weight", 2.5) + 2,
                                "fillOpacity": 0.35,
                                "opacity": 1.0,
                            },
                            "tooltip": folium.Tooltip(
                                polygon_tooltip_content,
                                sticky=False,
                                direction="bottom",
                                offset=(0, 15),
                                style="background-color: white; color: #333; font-family: sans-serif; border-radius: 4px; padding: 6px; border: 1px solid #ccc; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
                            )
                        }

                        gj = folium.GeoJson(geojson_feature, **geojson_kwargs)

                        # 🎯 CONDITIONAL POPUP ATTACHMENT:
                        # Only create and add native Folium popups for non-walk layers.
                        # Walk layers skip this entirely, leaving their clicks open for your Bootstrap modal JS.
                        if layer_type != 'walk':
                            click_popup = folium.Popup(popup_body, max_width=300)
                            gj.add_child(click_popup)

                        gj.add_to(self)

                    except Exception as e:
                        print(f"DEBUG ERROR: Failed adding canvas feature for {c_val} -> {e}")

                    # 2. SEPARATE PERMANENT CENTROID BADGE MARKER
                    if not static:
                        self.add_child(folium.Marker(location=here, icon=folium.DivIcon(html=htmlhalo)))
                    else:
                        self.add_child(folium.Marker(location=here, icon=folium.DivIcon(html=htmlhalostatic)))

                else:
                    print(f"❌ WARNING: limbX contains 0 matching polygon rows for FID {c.fid}")

        print(f"\n🏁 LEAVING add_nodemaps. Processed {loop_counter} children.")
        print("=" * 80 + "\n")
        return self._children

    def add_nodemarks(self, CElection,rlevels, herenode, static, intention_type):
        global levelcolours

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        # 🎯 SELF-AWARE PROPERTY STRIPPING (Mirrors add_nodemaps logic)
        raw_opts = getattr(self, "options", {}) or {}
        layer_style = raw_opts.get("style", raw_opts) if "style" in raw_opts else raw_opts

        childlist = herenode.childrenoftype(intention_type)
        nodeshtml = build_nodemap_list_html(herenode)

        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
            "code": herenode.value,
            "details": details,
            "tooltip_html": nodeshtml
        }
        num = len(herenode.childrenoftype(intention_type))
        print(f"___creating {num} add_nodemarks of type {intention_type} for {herenode.value} at level {herenode.level}")

        children = herenode.childrenoftype(intention_type)

        for i, c in enumerate(children):

            base_lat = float(f"{c.latlongroid[0]:.6f}")
            base_lon = float(f"{c.latlongroid[1]:.6f}")

            lat, lon = spread_coordinates_vertical(
                base_lat,
                base_lon,
                i,
                len(children),
                spread_lat=0.0006,   # more vertical spacing
                spread_lon=0.00001    # minimal horizontal spacing
            )
            here = [lat, lon]

            print('_______MAP Markers')

            numtag = str(c.tagno)+" "+str(c.value)
            num = str(c.tagno)
            tag = str(c.value)
            fill = herenode.col
            pathref = c.mapfile()
            mapfile = '/transfer/'+pathref

            print("______Display childrenx:", c.value, c.level, type, c.latlongroid)

            # 🎯 layer_style is now safely defined up top!
            bcol = layer_style.get("color", "#991B1B")       # boundary
            tcol = layer_style.get("fontColor", "#EF4444")   # font colour
            fcol = layer_style.get("fillColor", "#EF4444")   # area colour

            node_col = tcol
            tcol_node = tcol
            fcol_node = fcol
            poly_col_node = tcol

            htmlhalo = f'''
            <a href="{mapfile}" data-name="{tag}">
              <div style="
                color: {tcol_node};
                font-size: 8pt;
                font-weight: bold;
                text-align: center;
                padding: 2px;
                white-space: nowrap;

                /* 🗺️ Cartographic halo */
                text-shadow:
                  -1px -1px 0 #fff,
                   1px -1px 0 #fff,
                  -1px  1px 0 #fff,
                   1px  1px 0 #fff,
                   0px  0px 3px #fff;
              ">
                <span style="
                  background: {fcol_node};
                  padding: 1px 2px;
                  border-radius: 5px;
                  border: 2px solid black;
                ">{num}</span>
                {numtag}<br>
                <span style="
                    font-size: 6pt;
                    font-weight: normal;
                ">

                </span>

              </div>
            </a>
            '''
            htmlhalostatic = f'''
            <a href="" data-name="{tag}">
              <div style="
                color: {tcol_node};
                font-size: 8pt;
                font-weight: bold;
                text-align: center;
                padding: 2px;
                white-space: nowrap;

                /* 🗺️ Cartographic halo */
                text-shadow:
                  -1px -1px 0 #fff,
                   1px -1px 0 #fff,
                  -1px  1px 0 #fff,
                   1px  1px 0 #fff,
                   0px  0px 3px #fff;
              ">
                <span style="
                  background: {fcol_node};
                  padding: 1px 2px;
                  border-radius: 5px;
                  border: 2px solid black;
                ">{num}</span>
                {numtag}<br>
                <span style="
                    font-size: 6pt;
                    font-weight: normal;
                ">

                </span>

              </div>
            </a>
            '''

            if not static:
                self.add_child(folium.Marker(
                     location=here,
                     icon=folium.DivIcon(
                            html=htmlhalo,
                           )
                           )
                           )
            else:
                self.add_child(folium.Marker(
                     location=here,
                     icon=folium.DivIcon(
                            html=htmlhalostatic,
                           )
                           )
                           )

        print("________Layer map points", herenode.value, herenode.level, len(self._children))

        return self._children


    def add_houses(self, rlevels, herenode, static, intention_type):
        global levelcolours
        from layers import Treepolys

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        # 🎯 SELF-AWARE PROPERTY STRIPPING
        raw_opts = getattr(self, "options", {}) or {}
        layer_style = raw_opts.get("style", raw_opts) if "style" in raw_opts else raw_opts

        childlist = herenode.childrenoftype(intention_type)
        nodeshtml = build_nodemap_list_html(herenode)

        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
            "code": herenode.value,
            "details": details,
            "tooltip_html": nodeshtml
        }
        num = len(childlist)
        print(f"___creating {num} add_houses of type {intention_type} for {herenode.value} at level {herenode.level}")

        children = herenode.childrenoftype(intention_type)

        # ------------------------------------------------------------------
        # 🎯 STRATEGY B: Fetch dual Treepolys['street'] & Snap via KDTree
        # ------------------------------------------------------------------
        # 1. Fetch street layer directly from imported state
        street_data = Treepolys.get("street")

        # 2. Unpack pre-compiled spatial components from dual dictionary structure
        if isinstance(street_data, dict):
            kdtree = street_data.get("index")
            coords = street_data.get("coords")
            uprn_ids = street_data.get("ids")
        else:
            # Fallback if Treepolys['street'] was loaded solely as a raw GeoDataFrame
            kdtree, coords, uprn_ids = None, None, None

        # 3. Read dynamic snapping threshold from layer_style or default to 25m
        buffer_meters = layer_style.get("bufferMeters", 25.0)

        # 4. Execute KDTree spatial query against house children
        snapped_positions = snap_houses_to_uprns(
            children=children,
            kdtree=kdtree,
            coords=coords,
            uprn_ids=uprn_ids,
            max_distance_meters=buffer_meters
        )

        for i, c in enumerate(children):
            # Retrieve snapped coordinate or fallback to child centroid
            here = snapped_positions.get(c.value, [float(c.latlongroid[0]), float(c.latlongroid[1])])

            print('_______MAP Markers')

            numtag = str(c.tagno) + " " + str(c.value)
            num_str = str(c.tagno)
            tag = str(c.value)
            pathref = c.mapfile()
            mapfile = '/transfer/' + pathref

            print("______Display childrenx:", c.value, c.level, intention_type, c.latlongroid, "-> Snapped:", here)

            # 🎯 layer_style styling
            bcol = layer_style.get("color", "#991B1B")       # boundary
            tcol = layer_style.get("fontColor", "#EF4444")   # font colour
            fcol = layer_style.get("fillColor", "#EF4444")   # area colour

            tcol_node = tcol
            fcol_node = fcol

            html_content = f'''
            <a href="{mapfile if not static else ''}" data-name="{tag}">
              <div style="
                color: {tcol_node};
                font-size: 8pt;
                font-weight: bold;
                text-align: center;
                padding: 2px;
                white-space: nowrap;

                /* 🗺️ Cartographic halo */
                text-shadow:
                  -1px -1px 0 #fff,
                   1px -1px 0 #fff,
                  -1px  1px 0 #fff,
                   1px  1px 0 #fff,
                   0px  0px 3px #fff;
              ">
                <span style="
                  background: {fcol_node};
                  padding: 1px 2px;
                  border-radius: 5px;
                  border: 2px solid black;
                ">{num_str}</span>
                {numtag}<br>
                <span style="
                    font-size: 6pt;
                    font-weight: normal;
                ">
                </span>
              </div>
            </a>
            '''

            self.add_child(
                folium.Marker(
                    location=here,
                    icon=folium.DivIcon(html=html_content)
                )
            )

        print("________Layer map points", herenode.value, herenode.level, len(self._children))

        return self._children



# -----------------------------
# Factory: make fresh layers per map
# -----------------------------
def make_feature_layers():
    """
    Returns a fresh dict of ExtendedFeatureGroup instances for a single map.
    Derived dynamically from the unified MAP_LAYERS config dictionary.
    Each layer has Python-only metadata: .key, .mytag, .layer_type, .level, and .options.
    """
    global OPTIONS
    global_options = globals().get("OPTIONS", {})

    layers = {}
    for key, spec in MAP_LAYERS.items():
        # 1. Initialize ExtendedFeatureGroup with standard Folium kwargs
        layer = ExtendedFeatureGroup(
            name=spec.get("name", key),
            overlay=spec.get("overlay", True),
            control=spec.get("control", True),
            show=spec.get("show", False),
        )

        # 2. Assign metadata attributes on the Python instance
        layer.key = key
        layer.mytag = spec.get("mytag", key)
        layer.type = spec.get("type", "node")
        layer.layer_type = spec.get("type", "node")
        layer.level = spec.get("level", None)  # 👈 Exposes hierarchy level (0-7)

        # 3. Resolve options: Local spec options > Global fallback > Empty dict
        layer.options = spec.get("options", global_options if global_options else {})

        layers[key] = layer

    return layers




def make_counters():
    """
    Returns a dictionary initialized with zero counts for every layer key
    defined in MAP_LAYERS.
    """
    return {key: 0 for key in MAP_LAYERS}
