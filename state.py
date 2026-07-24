import json
import os
import pandas as pd
import re
import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry import Point, Polygon
from shapely import crosses, contains,covers, union, envelope, intersection
from shapely.ops import nearest_points

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
            return part.replace(suffix, "")
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
        for layer in LAYERS[from_level:]:
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

def filterArea(source, sourcekey, destination, roid=None, name=None, boundary_geom=None):
    """
    Lookup polygon(s) by name, point, or boundary polygon.
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

    # 2️⃣ Lookup by roid/coordinates
    elif roid is not None:
        coords = parse_coords(roid)
        if coords:
            lat, lon = coords[0]
            point = Point(lon, lat)
            matched = gdf[gdf.covers(point)]
        else:
            print(f"[filterArea] ⚠️ Invalid coordinate structure for roid: {roid}")

    # 3️⃣ Lookup by boundary polygon
    elif boundary_geom is not None:
        matched = gdf[gdf.intersects(boundary_geom)]

    # Export & metadata resolution
    if not matched.empty:
        nodestep = normalname(matched['NAME'].iloc[0])
        matched.to_file(destination, driver="GeoJSON", engine="fiona", mode='w')
        print(f"[filterArea] Found {nodestep} ({len(matched)} feature(s)), saved to {destination}")
    else:
        print(f"[filterArea] No matching feature found for name {name} or roid {roid}")

    return [nodestep, matched, gdf]


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

    # 2. Geometry selection
    if boundary_geom is not None:
        working_geom = boundary_geom
    elif parent_row is not None and hasattr(parent_row, "geometry") and not parent_row.geometry.is_empty:
        working_geom = parent_row.geometry
    else:
        working_geom = None

    # 3. Overlap math
    if working_geom is not None:
        child_polygons_within_parent = filter_gdf_by_overlap(
            children_gdf=gdf,
            parent_geometry=working_geom,
            layer_type=intention_type,
            threshold_dict=OVERLAP_THRESHOLDS
        )
    else:
        child_polygons_within_parent = gdf.copy()

    # 4. Resolve selected child polygon
    selected_child_name = None
    coords = parse_coords(roid)

    if coords and not child_polygons_within_parent.empty:
        lat, lon = coords[0]
        pt = Point(lon, lat)
        hit = child_polygons_within_parent[child_polygons_within_parent.geometry.contains(pt)]
        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    if not selected_child_name and select_child_name and not child_polygons_within_parent.empty:
        hit = child_polygons_within_parent[
            child_polygons_within_parent["NAME"].apply(normalname) == normalname(select_child_name)
        ]
        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    if not selected_child_name and not child_polygons_within_parent.empty:
        selected_child_name = normalname(child_polygons_within_parent.iloc[0]["NAME"])

    print(f"🏁 [DEBUG intersectingArea END] Final Selected Child Name: {selected_child_name}\n")
    return selected_child_name, child_polygons_within_parent, gdf


def load_layer(
    *, layer, level, intention_type, parent_levels, parent_row,
    select_name=None, roid=None, boundary_geom=None
):
    src = f"{workdirectories['bounddir']}/{layer['src']}"
    out = f"{workdirectories['bounddir']}/{layer['out']}"

    if layer.get("method") == "filter":
        return filterArea(
            src, layer["field"], out,
            roid=roid, name=select_name, boundary_geom=boundary_geom
        )

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
    from state import Treepolys, Geo_index
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


def ensure_treepolys_with_index(
    *,
    territory: str | None,
    sourcepath: str | None,
    here=None,
    boundary_geom=None,
    resolved_levels: dict[str, dict[int, str]],
    parent_levels: dict[int, str],
):
    from nodes import FACEENDING, persist
    from state import (
        Geo_index,
        Treepolys,
        get_treepoly,
        normalname,
        set_treepoly,
        stepify,
        upsert_geodf,
    )

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
        logging.debug(
            "   ↳ Applied buffer(0) to boundary_geom to sanitize geometry"
        )

    if not resolved_levels or len(resolved_levels) != 1:
        logging.error(
            f"❌ Invalid resolved_levels configuration: {resolved_levels}"
        )
        raise ValueError("Invalid resolved_levels configuration.")

    (_, elevels), = resolved_levels.items()
    sourcepath = sourcepath or territory

    # ------------------------------------------------------------------
    # 🌟 GEOMETRY PRE-LOADER: Source Path + Point-Derived Territory Paths
    # ------------------------------------------------------------------
    candidate_paths = set()

    if sourcepath:
        candidate_paths.add(sourcepath)

    coords = parse_coords(here) if "parse_coords" in globals() else []
    if coords:
        lat, lon = coords[0]
        if "classify_record_coords" in globals():
            classification = classify_record_coords(
                lat, lon, sourcepath, parent_levels
            )
            derived_path = classification.get("_derived_path")
            if derived_path:
                logging.info(
                    f"📍 Derived territory path from point ({lat}, {lon}): {derived_path}"
                )
                candidate_paths.add(derived_path)

    LAYERS = globals().get("LAYERS", [])
    layer_defs = {(l["level"], l["key"]): l for l in LAYERS}

    for path in candidate_paths:
        path_steps = stepify(path)
        for depth, step_name in enumerate(path_steps):
            level_key = parent_levels.get(depth)
            if not level_key:
                logging.warning(
                    f"⚠️ [PRE-LOAD] No parent_level key mapped for depth {depth} (step: '{step_name}')"
                )
                continue

            existing_gdf = get_treepoly(level_key)
            norm_step = normalname(step_name)

            already_loaded = (
                existing_gdf is not None
                and not existing_gdf.empty
                and "NAME" in existing_gdf.columns
                and (existing_gdf["NAME"].apply(normalname) == norm_step).any()
            )

            if not already_loaded:
                for (lvl, key), l_def in layer_defs.items():
                    if key == level_key:
                        src, field = l_def["src"], l_def["field"]
                        chosen_src = src[0] if isinstance(src, list) else src
                        chosen_field = (
                            field[0] if isinstance(field, list) else field
                        )
                        out_file = f"{config.workdirectories['bounddir']}/{l_def['out']}"

                        _, step_gdf, _ = filterArea(
                            source=f"{config.workdirectories['bounddir']}/{chosen_src}",
                            sourcekey=chosen_field,
                            destination=out_file,
                            name=step_name,
                        )

                        if step_gdf is not None and not step_gdf.empty:
                            upserted = upsert_geodf(existing_gdf, step_gdf)
                            set_treepoly(level_key, upserted)
                            logging.info(
                                f"✅ Pre-loaded step geometry '{norm_step}' into Treepolys['{level_key}']"
                            )
                        else:
                            logging.warning(
                                f"⚠️ [PRE-LOAD] filterArea returned empty/None GDF for '{step_name}'"
                            )
                        break

    # ------------------------------------------------------------------
    # MAIN PROCESSING ENGINE LOOP
    # ------------------------------------------------------------------

    steps = stepify(sourcepath) if sourcepath else []
    target_depth = len(steps) - 1 if steps else 0
    logging.info(f"   ↳ Parsed Steps: {steps} | Target Depth: {target_depth}")

    active_parent_rows = {}
    fid_to_path = {}

    logging.info("🔎 Scanning cached geometries in state...")

    # Level execution loop
    for level, compound_layer_type in elevels.items():
        sub_layers = [
            l.strip() for l in compound_layer_type.split("/") if l.strip()
        ]
        logging.info(f"🔄 Processing Level {level} with layers: {sub_layers}")

        next_level = level + 1
        if next_level not in active_parent_rows:
            active_parent_rows[next_level] = []

        for layer_type in sub_layers:
            layer = layer_defs.get((level, layer_type))
            if not layer:
                logging.warning(
                    f"⚠️ Layer definition missing for level={level}, key={layer_type}"
                )
                continue

            select_name = None

            # ------------------------------------------------------------------
            # FIX: Properly set name filter up to target_depth, allow children at target_depth + 1
            # ------------------------------------------------------------------
            if level <= target_depth and level < len(steps):
                # We are at or above the target node: filter by step name
                select_name = steps[level]
                logging.debug(
                    f"   ↳ Level {level} <= Target Depth {target_depth}. Filtering name: '{select_name}'"
                )
            elif level == target_depth + 1:
                # We are fetching the children of the target node: NO name filter (fetch all children)
                select_name = None
                logging.debug(
                    f"   ↳ Level {level} is Target Depth + 1. Fetching all child boundaries for parent..."
                )
            elif level > target_depth + 1:
                # Exceeds the target node + 1 window: skip
                logging.debug(
                    f"   ↳ Level {level} exceeds target depth window (+1). Skipping layer '{layer_type}'."
                )
                continue

            parent_rows = active_parent_rows.get(level, [None])
            logging.debug(
                f"   ↳ Executing load_layer across {len(parent_rows)} parent row(s)"
            )
            all_results = []

            for p_idx, parent_row in enumerate(parent_rows):
                if level > 0 and parent_row is not None:
                    parent_path = fid_to_path.get(parent_row.get("FID"), ROOT)
                    expected_type = parent_levels.get(level)
                    actual_type = Geo_index.get(parent_path, {}).get("level")

                    if expected_type != actual_type:
                        logging.warning(
                            f"❌ [GEO_INDEX SKIP] Skipping parent [{p_idx}] (FID: {parent_row.get('FID')}): "
                            f"Type mismatch! Expected level type '{expected_type}', but Geo_index['{parent_path}'] has level '{actual_type}'."
                        )
                        continue

                src, field = layer["src"], layer["field"]
                chosen_src = src[0] if isinstance(src, list) else src
                chosen_field = field[0] if isinstance(field, list) else field

                if isinstance(src, list):
                    is_surrey_context = sourcepath and "surrey" in str(sourcepath).lower()
                    if is_surrey_context:
                        chosen_idx = next(
                            (i for i, f in enumerate(src) if f and "surrey" in str(f).lower()), 0
                        )
                    else:
                        chosen_idx = next(
                            (i for i, f in enumerate(src) if f and "surrey" not in str(f).lower()), 0
                        )
                    chosen_src = src[chosen_idx]
                    chosen_field = field[chosen_idx] if isinstance(field, list) else field

                layer_local = dict(layer)
                layer_local["src"], layer_local["field"] = chosen_src, chosen_field

                try:
                    logging.debug(
                        f"   ↳ Calling load_layer for '{layer_type}' (Src: {chosen_src})..."
                    )
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
                    logging.debug(
                        f"   ↳ load_layer returned child name: '{selected_child_name}', tree_gdf count: {len(tree_gdf) if tree_gdf is not None else 0}"
                    )
                except Exception as load_err:
                    logging.error(
                        f"❌ Exception in load_layer for {layer_type}: {load_err}",
                        exc_info=True,
                    )
                    tree_gdf = None

                if (
                    tree_gdf is not None
                    and hasattr(tree_gdf, "empty")
                    and not tree_gdf.empty
                ):
                    tree_gdf = tree_gdf.copy()

                    if "FID" not in tree_gdf.columns:
                        logging.warning(
                            f"⚠️ 'FID' column missing in output for layer '{layer_type}'. Standardizing ID column..."
                        )
                        if "OBJECTID" in tree_gdf.columns:
                            tree_gdf = tree_gdf.rename(columns={"OBJECTID": "FID"})
                        elif "id" in tree_gdf.columns:
                            tree_gdf = tree_gdf.rename(columns={"id": "FID"})
                        else:
                            logging.warning(
                                "⚠️ No standard ID column found; generating synthetic FID from Index."
                            )
                            tree_gdf["FID"] = tree_gdf.index.astype(int)

                    coords = (
                        parse_coords(here)
                        if "parse_coords" in globals()
                        else []
                    )
                    anchor_points = [Point(lon, lat) for lat, lon in coords]
                    if level < target_depth and anchor_points:
                        logging.debug(
                            f"   ↳ Applying spatial point mask using {len(anchor_points)} coordinate pair(s)..."
                        )

                        def matches_any_point(geom):
                            if geom is None or geom.is_empty:
                                return False
                            return any(
                                geom.contains(pt) for pt in anchor_points
                            )

                        spatial_mask = tree_gdf.geometry.apply(matches_any_point)
                        text_mask = tree_gdf["NAME"].apply(normalname) == normalname(steps[level])
                        tree_gdf = tree_gdf[spatial_mask | text_mask]
                        logging.debug(
                            f"   ↳ Records remaining after spatial/text mask: {len(tree_gdf)}"
                        )

                    if not tree_gdf.empty:
                        tree_gdf["_parent_path"] = (
                            ROOT
                            if level == 0
                            else (
                                fid_to_path.get(parent_row["FID"], ROOT)
                                if parent_row is not None
                                else ROOT
                            )
                        )
                        all_results.append(tree_gdf)

            if not all_results:
                logging.warning(
                    f"⚠️ No results compiled for level={level}, layer_type='{layer_type}'"
                )
                continue

            tree_gdf = pd.concat(all_results, ignore_index=True)
            logging.info(
                f"📊 Combined tree_gdf for layer '{layer_type}': {len(tree_gdf)} total row(s)"
            )

            raw_out = layer_local.get("out")
            if raw_out and not tree_gdf.empty:
                out_path = f"{config.workdirectories['bounddir']}/{raw_out}"
                tree_gdf.to_file(out_path)
                logging.debug(f"   ↳ Exported shape/geojson layer to: {out_path}")

            existing = get_treepoly(layer_type)

            if (
                existing is None
                or "FID" not in existing.columns
                or "FID" not in tree_gdf.columns
            ):
                new_tree_gdf = tree_gdf
            else:
                new_tree_gdf = tree_gdf[~tree_gdf["FID"].isin(existing["FID"])]

            upserted_gdf = upsert_geodf(existing, new_tree_gdf)
            set_treepoly(layer_type, upserted_gdf)

            # ------------------------------------------------------------------
            # 🔍 [FIXED] GEO_INDEX POPULATION LOOP
            # ------------------------------------------------------------------
            logging.info(
                f"🗂️ [GEO_INDEX POPULATION] Iterating through {len(tree_gdf)} row(s) to populate Geo_index..."
            )

            for idx, row in tree_gdf.iterrows():
                raw_name = row.get("NAME")
                if pd.isna(raw_name) or raw_name is None:
                    logging.error(
                        f"❌ [GEO_INDEX FAIL] Row index {idx} in layer '{layer_type}' has a missing/NaN 'NAME' value! Row content: {dict(row)}"
                    )
                    child_name = f"UNNAMED_{idx}"
                else:
                    child_name = normalname(str(raw_name))

                # FIX 1: Explicitly build distinct hierarchy paths per level
                parent_path = row.get("_parent_path", ROOT)
                if level == 0:
                    this_path = ROOT if child_name == ROOT else f"{ROOT}/{child_name}"
                else:
                    this_path = f"{parent_path}/{child_name}"

                if this_path not in Geo_index:
                    roid_coords = None
                    if hasattr(row, "geometry") and row.geometry is not None:
                        try:
                            centroid_point = row.geometry.representative_point()
                            roid_coords = [
                                float(centroid_point.y),
                                float(centroid_point.x),
                            ]
                        except Exception as spatial_err:
                            logging.warning(
                                f"   ↳ Spatial error resolving centroid on '{this_path}': {spatial_err}"
                            )

                    Geo_index[this_path] = {
                        "level": layer_type,
                        "name": child_name,
                        "parent": parent_path if level > 0 else None,
                        "children": [],
                        "roid": roid_coords,
                        "fid": (
                            int(row["FID"]) if pd.notna(row.get("FID")) else None
                        ),
                    }
                    logging.info(
                        f"   ➕ [GEO_INDEX POPULATED] Added path: '{this_path}' | Level: {layer_type} | FID: {row.get('FID')}"
                    )

                if (
                    parent_path in Geo_index
                    and this_path not in Geo_index[parent_path]["children"]
                ):
                    Geo_index[parent_path]["children"].append(this_path)
                    logging.debug(
                        f"   ↳ Linked child '{this_path}' to parent '{parent_path}'"
                    )

                fid_to_path[row["FID"]] = this_path

                row_copy = row.copy()
                row_copy["_parent_path"] = this_path

                # FIX 2: Prevent duplicate row accumulation in active_parent_rows
                existing_fids = {
                    r["FID"] for r in active_parent_rows[next_level]
                    if r is not None and "FID" in r
                }
                if row_copy["FID"] not in existing_fids:
                    active_parent_rows[next_level].append(row_copy)

    # ------------------------------------------------------------------
    # 📊 DIAGNOSTIC SUMMARY
    # ------------------------------------------------------------------
    logging.info("==================================================")
    logging.info("📈 [GEO_INDEX DIAGNOSTIC SUMMARY]")
    logging.info(f"   Total entries in Geo_index: {len(Geo_index)}")
    logging.info("   Keys present in Geo_index:")
    for key, val in Geo_index.items():
        logging.info(
            f"    - '{key}' => Level: {val.get('level')}, Children Count: {len(val.get('children', []))}"
        )
    logging.info("==================================================")

    # Final Path Traversal resolution logic
    final_path = ROOT
    for step in steps[1:]:
        target = normalname(step)
        children = Geo_index.get(final_path, {}).get("children", [])
        found = next(
            (
                cp
                for cp in children
                if Geo_index.get(cp, {}).get("name") == target
            ),
            None,
        )
        if found is None:
            logging.warning(
                f"⚠️ Could not resolve target path step '{target}' from '{final_path}' (Available children: {children})"
            )
            break
        final_path = found

    node = Geo_index.get(final_path, {"level": "country"})
    match_full_filepath = final_path + FACEENDING.get(
        node["level"], "-MAP.html"
    )

    logging.info(
        f"🏁 [DEBUG END] Target Path Resolved: '{final_path}' | Map File: '{match_full_filepath}'"
    )
    logging.info("==================================================")
# Add this explicit validation before persist()
    logging.info(f"SURREY children right before persist: {Geo_index.get('UNITED_KINGDOM/ENGLAND/SURREY', {}).get('children')}")


    persist(Treepolys, Geo_index)

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
Geo_index = {}

LAYERS = [
    {
        "key": "country",
        "level": 0,
        "src": "World_Countries_(Generalized)_9029012925078512962.geojson",
        "field": "COUNTRY",
        "out": "Country_Boundaries.geojson",
        "method": "filter",
    },
    {
        "key": "nation",
        "level": 1,
        "src": "Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson",
        "field": "CTRY21NM",
        "out": "Nation_Boundaries.geojson",
        "method": "filter"
    },
    {
        "key": "county",
        "level": 2,
        "src": "Counties_and_Unitary_Authorities_December_2024_Boundaries_UK_BGC_-917943173031721243_degrees.geojson",
        "field": "CTYUA24NM",
        "out": "County_Boundaries.geojson",
        "method": "filter"
    },
    {
        "key": "constituency",
        "level": 3,
        "src": "Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson",
        "field": "PCON24NM",
        "out": "Constituency_Boundaries.geojson",
        "method": "intersect"
    },
    {
        "key": "ward",
        "level": 4,
        "src": "Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson",
        "field": "WD24NM",
        "out": "Ward_Boundaries.geojson",
        "method": "intersect"
    },
    {
        "key": "division",
        "level": 4,
        "src": ["County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson","Revised_Surrey_Proposed_Divisions.geojson"],
        "field": ["CED23NM","Division_n"],
        "out": "Division_Boundaries.geojson",
        "method": "intersect"
    },

]

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
TypeMaker = { 'nation' : 'downbut','county' : 'downbut', 'constituency' : 'downbut' , 'ward' : 'downbut', 'division' : 'downbut', 'polling_district' : 'downbut', 'walk' : 'downbut', 'street' : 'PDdownST', 'walkleg' : 'WKdownST'}


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
