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

def stepify(path):
    if not path:
        return []

    routeone = (
        path.replace('/WALKS/', '/')
            .replace('/PDS/', '/')
            .replace('/WARDS/', '/')
            .replace('/DIVS/', '/')
    )
    parts = routeone.split("/")
    last = parts.pop()

    if "-PRINT.html" in last:
        leaf = subending(last, "").split("--").pop()
        parts.append(leaf)

    print("____LEAFNODE:", path, parts)
    return parts

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
            Fullpolys[k] = gpd.GeoDataFrame()
    else:
        for layer in LAYERS[from_level:]:
            Treepolys[layer["key"]] = gpd.GeoDataFrame()
            Fullpolys[layer["key"]] = gpd.GeoDataFrame()

def filterArea(source, sourcekey,
    destination,
    roid=None,
    name=None,
    boundary_geom=None):
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
    point = None

    # 1️⃣ Lookup by name
    if name is not None:
        target = normalname(name.split("/")[-1])
        matched = gdf[gdf["NAME"].astype(str).apply(normalname) == target]

    # 2️⃣ Lookup by roid
    elif roid is not None:
        latitude, longitude = roid
        if latitude is not None and longitude is not None:
            point = Point(longitude, latitude)
            matched = gdf[gdf.covers(point)]

    # 3️⃣ Lookup by boundary polygon
    elif boundary_geom is not None:
        matched = gdf[gdf.intersects(boundary_geom)]

    # Determine nodestep
    if not matched.empty:
        nodestep = normalname(matched['NAME'].iloc[0])
        matched.to_file(destination, driver="GeoJSON", engine="fiona", mode='w')
        print(f"[filterArea] Found {nodestep} ({len(matched)} feature(s)), saved to {destination}")
    else:
        print(f"[filterArea] No matching feature found for name {name} or roid {roid}")

    return [nodestep, matched, gdf]



def select_parent_geoms(*, Treepolys, parent_key, sourcepath=None, here=None):
    parents = Treepolys.get(parent_key, gpd.GeoDataFrame())
    print(f"select_parent: raw Treepolys[{parent_key}] = {parents!r}")

    if parents.empty:
        return gpd.GeoDataFrame()

    # 1️⃣ Point-in-polygon
    if here is not None:
        pt = Point(here[1], here[0])  # (lon, lat)
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
    # 3️⃣ fallback: return all parents
    return parents

def intersectingArea(
    source,
    sourcekey,
    parent_levels,
    child_level,
    elevels,
    destination,
    *,
    parent_row,
    select_child_name=None,
    roid=None,
    boundary_geom=None
):


    parent_name = normalname(parent_row["NAME"]) if parent_row is not None else "None"
    parent_type = parent_levels.get(child_level)

    if parent_type is None:
        raise ValueError(f"No parent type found for parent_level IN {parent_levels}")

    print(f"\n[DEBUG] intersectingArea | source={source}")
    print(f"[DEBUG] parent_name={parent_name} parent_type={parent_type}, roid={roid}, select_child_name={select_child_name}")

    # ------------------------------------------------------------------
    # 1. Load child layer
    # ------------------------------------------------------------------
    gdf_RAW = get_layer_gdf(source)
    gdf = ensure_4326(gdf_RAW)

    if sourcekey in gdf.columns:
        gdf = gdf.rename(columns={sourcekey: "NAME"})
    else:
        raise ValueError(f"No sourcekey {sourcekey} IN {gdf.columns}")

    if "OBJECTID" in gdf.columns:
        gdf = gdf.rename(columns={"OBJECTID": "FID"})

    all_child_polygons = gdf
    print(f"[DEBUG] Loaded {len(gdf)} child features and cols: {gdf.columns}")

    # ------------------------------------------------------------------
    # 2. Choose geometry (FIXED LOGIC)
    # ------------------------------------------------------------------
    if boundary_geom is not None:
        working_geom = boundary_geom
        print("[DEBUG] Using boundary_geom for intersection")

    elif parent_row is not None and not parent_row.geometry.is_empty:
        working_geom = parent_row.geometry
        print("[DEBUG] Using parent_row geometry")

    else:
        print(f"[DEBUG] under {route()} No geometry available → returning all children")
        return None, all_child_polygons, all_child_polygons

    # ------------------------------------------------------------------
    # 3. Intersection filter
    # ------------------------------------------------------------------
    child_type = elevels[child_level]
    threshold = Overlaps.get(child_type, 0)

    print(f"[DEBUG] Intersection threshold ({child_type}): {threshold}")

    candidates = gdf[gdf.geometry.intersects(working_geom)]

    print(f"[DEBUG] Candidates intersecting bbox: {len(candidates)}")

    if candidates.empty:
        return None, gpd.GeoDataFrame(), all_child_polygons

    # ------------------------------------------------------------------
    # 4. Project + overlap
    # ------------------------------------------------------------------
    proj_crs = "EPSG:3857"

    working_geom_proj = (
        gpd.GeoSeries([working_geom], crs="EPSG:4326")
        .to_crs(proj_crs)
        .iloc[0]
    )
# ... inside intersectingArea ...
    candidates_proj = candidates.to_crs(proj_crs)

    # Calculate overlap area
    overlap_areas = candidates_proj.geometry.intersection(working_geom_proj).area
    # Calculate child's total area
    child_areas = candidates_proj.geometry.area

    # Proportional check: Is 50% of the child inside the parent?
    overlap_ratio = overlap_areas / child_areas
    mask = overlap_ratio > threshold  # threshold should be 0.5 (50%)

    child_polygons_within_parent = candidates[mask].copy()

    print(f"[DEBUG] Children within parent above threshold: {len(child_polygons_within_parent)}")

    # ------------------------------------------------------------------
    # 5. Resolve selected child
    # ------------------------------------------------------------------
    selected_child_name = None

    if roid:
        lat, lon = roid
        pt = Point(lon, lat)

        hit = child_polygons_within_parent[
            child_polygons_within_parent.geometry.contains(pt)
        ]

        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    if not selected_child_name and select_child_name:
        hit = child_polygons_within_parent[
            child_polygons_within_parent["NAME"].apply(normalname)
            == normalname(select_child_name)
        ]

        if not hit.empty:
            selected_child_name = normalname(hit.iloc[0]["NAME"])

    if not selected_child_name and not child_polygons_within_parent.empty:
        selected_child_name = normalname(child_polygons_within_parent.iloc[0]["NAME"])

    # ------------------------------------------------------------------
    # 6. Save
    # ------------------------------------------------------------------
    if not child_polygons_within_parent.empty:
        child_polygons_within_parent.to_file(destination)

    return selected_child_name, child_polygons_within_parent, all_child_polygons

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
    elif existing.crs is not None and incoming.crs is not None and existing.crs != incoming.crs:
        incoming = incoming.to_crs(existing.crs)

    # Combine
    combined = pd.concat([existing, incoming], ignore_index=True)

    # Drop duplicates keeping newest (incoming overwrites existing)
    combined = combined.drop_duplicates(subset=key, keep="last")

    # Rebuild GeoDataFrame safely
    combined = gpd.GeoDataFrame(combined, geometry=existing.geometry.name, crs=existing.crs)

    return combined

LAYER_CACHE = {}

def get_layer_gdf(src):
    if src not in LAYER_CACHE:
        LAYER_CACHE[src] = gpd.read_file(src)
    return LAYER_CACHE[src]

def load_layer(
    *,
    layer,
    level,
    elevels,
    parent_levels,
    parent_row,
    select_name=None,
    roid=None,
    boundary_geom=None
):
    """
    Load a layer using either filter or intersection method.
    parent_levels is used to derive parent_type.
    """
    src = f"{workdirectories['bounddir']}/{layer['src']}"
    out = f"{workdirectories['bounddir']}/{layer['out']}"

    if layer["method"] == "filter":
        # Filter-based selection (no parent needed)
        return filterArea(
            src,
            layer["field"],
            out,
            roid=roid,
            name=select_name,
            boundary_geom=boundary_geom
        )

    # Intersection-based selection
    return intersectingArea(
        source=src,
        sourcekey=layer["field"],
        parent_levels=parent_levels,
        child_level= level,
        elevels=elevels,
        destination=out,
        parent_row=parent_row,
        roid=roid,
        select_child_name=select_name,
        boundary_geom=boundary_geom
    )


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


def GetHierarchyMap():
    """
    Generates a nested dictionary mapping Polling District codes to their
    parent Ward and Division boundaries using spatial containment.

    Returns:
        dict: { 'PD_CODE': {'Ward': 'Ward Name', 'Division': 'Division Name'}, ... }
    """
    from state import Treepolys, normalname

    # 1. Pull the raw spatial layers from your state storage
    pd_layer = Treepolys.get("polling_district")
    ward_layer = Treepolys.get("ward")
    div_layer = Treepolys.get("division")

    # Safety check: If layers aren't loaded yet, return an empty map
    if pd_layer is None or len(pd_layer) == 0:
        print("⚠️ Warning: 'polling_district' spatial layer is not loaded. Empty map returned.")
        return {}

    # 2. Normalize and copy the layers to avoid modifying originals
    gdf_pd = gpd.GeoDataFrame(pd_layer.copy(), geometry='geometry', crs=pd_layer.crs)

    # We use representative points (centroids guaranteed to be inside the polygon)
    # to find parent boundaries without border-overlap edge cases.
    gdf_pd['rep_point'] = gdf_pd['geometry'].buffer(0).representative_point()
    gdf_pd_points = gdf_pd.set_geometry('rep_point')

    # Standardize the primary lookup key column
    gdf_pd_points['PD_KEY'] = gdf_pd_points['NAME'].apply(lambda x: normalname(x) if x else None)
    gdf_pd_points = gdf_pd_points.dropna(subset=['PD_KEY'])

    # 3. Spatial Join with Wards
    if ward_layer is not None and len(ward_layer) > 0:
        gdf_ward = gpd.GeoDataFrame(ward_layer.copy(), geometry='geometry', crs=ward_layer.crs).to_crs(gdf_pd_points.crs)
        # Spatial join: find which Ward contains the PD point
        joined_ward = gpd.sjoin(gdf_pd_points, gdf_ward[['NAME', 'geometry']], how='left', predicate='within')
        # Rename match to prevent conflicts
        joined_ward = joined_ward.rename(columns={'NAME_right': 'Ward_Name'}).drop_duplicates(subset='PD_KEY')
        pd_to_ward = dict(zip(joined_ward['PD_KEY'], joined_ward['Ward_Name']))
    else:
        pd_to_ward = {}

    # 4. Spatial Join with Divisions
    if div_layer is not None and len(div_layer) > 0:
        gdf_div = gpd.GeoDataFrame(div_layer.copy(), geometry='geometry', crs=div_layer.crs).to_crs(gdf_pd_points.crs)
        joined_div = gpd.sjoin(gdf_pd_points, gdf_div[['NAME', 'geometry']], how='left', predicate='within')
        joined_div = joined_div.rename(columns={'NAME_right': 'Div_Name'}).drop_duplicates(subset='PD_KEY')
        pd_to_div = dict(zip(joined_div['PD_KEY'], joined_div['Div_Name']))
    else:
        pd_to_div = {}

    # 5. Compile the nested dictionary structure
    hierarchy_map = {}
    for pd_code in gdf_pd_points['PD_KEY'].unique():
        # Fallback cleanly to 'OUTSIDE' if a spatial layer or intersection was missing
        ward_name = pd_to_ward.get(pd_code)
        div_name = pd_to_div.get(pd_code)

        hierarchy_map[pd_code] = {
            "Ward": ward_name if pd_not_empty(ward_name) else "OUTSIDE",
            "Division": div_name if pd_not_empty(div_name) else "OUTSIDE"
        }

    print(f"✅ Pre-compiled Hierarchy Map with {len(hierarchy_map)} unique PD layout mappings.")
    return hierarchy_map

def pd_not_empty(val):
    """Helper check to filter out NaN, None, or blank spatial strings."""
    if val is None:
        return False
    if isinstance(val, float) and pd.isna(val):
        return False
    if str(val).strip() in ['', 'nan', 'None']:
        return False
    return True


def ensure_treepolys_with_index(
    *,
    territory: str | None,
    sourcepath: str | None,
    here: tuple[float, float] | None,
    boundary_geom=None,
    resolved_levels: dict[str, dict[int, str]],
    parent_levels: dict[int, str]
):
    import pandas as pd
    import logging
    from state import Treepolys, Geo_index
    from nodes import persist, FACEENDING

    ROOT = "UNITED_KINGDOM"

    if ROOT not in Geo_index:
        Geo_index[ROOT] = {
            "level": "country",
            "name": ROOT,
            "parent": None,
            "children": [],
            "roid": [54.5, -2.5]  # 🌟 Hardcoded center of the UK (Lat, Lon)
        }

    t("start")

    if boundary_geom is not None:
        boundary_geom = boundary_geom.buffer(0)

    if not resolved_levels:
        raise ValueError("resolved_levels is required")

    if len(resolved_levels) != 1:
        raise ValueError(
            f"Expected 1 election, got {len(resolved_levels)}"
        )

    (_, elevels), = resolved_levels.items()

    print("elevels =", elevels)

    logging.debug(
        f"Starting treepolys with territory={territory} "
        f"and sourcepath={sourcepath}"
    )

    sourcepath = sourcepath or territory
    steps = stepify(sourcepath) if sourcepath else []

    layer_defs = {(l["level"], l["key"]): l for l in LAYERS}

    active_parent_rows = {}
    fid_to_path = {}

    # -------------------------------------------------------------
    # PRE-LOAD AND AGGREGATE ALL CACHED GEOMETRIES
    # -------------------------------------------------------------
    for lvl, compound_layer_type in elevels.items():

        sub_layers = [
            l.strip()
            for l in compound_layer_type.split('/')
            if l.strip()
        ]

        for l_type in sub_layers:

            existing_polys = get_treepoly(l_type)

            if existing_polys is not None:

                if lvl not in active_parent_rows:
                    active_parent_rows[lvl] = []

                existing_fids = {
                    r["FID"]
                    for r in active_parent_rows[lvl]
                    if r is not None and "FID" in r
                }

                for _, row in existing_polys.iterrows():
                    if row.get("FID") not in existing_fids:
                        active_parent_rows[lvl].append(row)

    # Reconstruct the absolute paths of the assigned parent records that filter child polys
    for lvl, rows in active_parent_rows.items():

        for r in rows:

            if r is not None and "FID" in r and "_parent_path" in r:

                child_name = normalname(r["NAME"])

                if lvl == 0 or child_name == ROOT:
                    this_path = ROOT
                else:
                    parent_path = r["_parent_path"] #the rows stored parent path
                    this_path = f"{parent_path}/{child_name}"

                fid_to_path[r["FID"]] = this_path

                logging.debug(
                    f"[LEVEL {lvl} - FID:{r['FID']}] "
                    f"maps to path: {this_path}"
                )

    if not active_parent_rows.get(0):
        active_parent_rows[0] = [None]

    matched_path = ROOT
    match_full_filepath = None

    # -------------------------------------------------------------
    # MAIN LOOP
    # -------------------------------------------------------------
    for level, compound_layer_type in elevels.items():

        if int(level) > 4:
            logging.info(
                f"[LEVEL {level}] "
                "Exceeded maximum processing level (4). "
                "Terminating drill-down early."
            )
            break

        t(f"LEVEL {level} ({compound_layer_type}) start")

        sub_layers = [
            l.strip()
            for l in compound_layer_type.split('/')
            if l.strip()
        ]

        for layer_type in sub_layers:

            layer = layer_defs.get((level, layer_type))

            if not layer:
                logging.warning(
                    f"[LEVEL {level}] "
                    f"No layer definition found for "
                    f"{(level, layer_type)}"
                )
                continue

            select_name = (
                steps[level]
                if level < len(steps)
                else None
            )

            parent_rows = active_parent_rows.get(level, [None])
            all_results = []

            logging.info(
                f"[LEVEL {level} - {layer_type}] "
                f"Starting with {len(parent_rows)} parent rows"
            )

            for parent_row in parent_rows:

                if level > 0 and parent_row is not None:

                    parent_fid = parent_row.get("FID")
                    parent_path = fid_to_path.get(parent_fid, ROOT)
                    expected_parent_type = parent_levels.get(level)

                    print()
                    print("LEVEL",level)
                    print("parent_fid =",parent_fid)
                    print("parent_path =",parent_path)
                    print("expected_parent_type =",expected_parent_type)
                    print("actual type =",Geo_index.get(parent_path,{}).get("level"))

                    if (
                        expected_parent_type
                        and Geo_index.get(parent_path, {}).get("level")
                        != expected_parent_type
                    ):
                        continue

                src = layer["src"]
                field = layer["field"]

                chosen_src = src
                chosen_field = field

                if isinstance(src, list):

                    chosen_src = src[0]
                    chosen_field = (
                        field[0]
                        if isinstance(field, list)
                        else field
                    )

                    for index, filename in enumerate(src):

                        if (
                            filename
                            and "surrey" in str(filename).lower()
                        ):
                            chosen_src = src[index]
                            chosen_field = (
                                field[index]
                                if isinstance(field, list)
                                else field
                            )
                            break

                layer_local = dict(layer)
                layer_local["src"] = chosen_src
                layer_local["field"] = chosen_field

                logging.debug(
                    f"[LEVEL {level}-{layer_type}] "
                    f"load_layer src={chosen_src}"
                )

                print()
                print(f"LEVEL {level}")
                print("method =", layer_local["method"])
                print("src =", layer_local["src"])
                print("field =", layer_local["field"])
                print("select_name =", select_name)

                _, tree_gdf, _ = load_layer(
                    layer=layer_local,
                    level=level,
                    elevels=elevels,
                    parent_levels=parent_levels,
                    parent_row=parent_row,
                    select_name=select_name,
                    roid=here,
                    boundary_geom=boundary_geom
                )
                print()
                print(f"LOAD_LAYER level={level} type={layer_type}")
                print("select_name =", select_name)
                print("parent_row =", None if parent_row is None else parent_row["NAME"])

                if tree_gdf is None:
                    print("tree_gdf is None")
                else:
                    print("tree_gdf rows =", len(tree_gdf))
                    if not tree_gdf.empty:
                        print(tree_gdf[["FID","NAME"]])

                if tree_gdf is not None and not tree_gdf.empty:

                    tree_gdf = tree_gdf.copy()
                    if level == 0:
                        parent_path = None

                    elif parent_row is None:
                        parent_path = ROOT

                    else:
                        parent_fid = parent_row["FID"]
                        if parent_fid not in fid_to_path:
                            raise ValueError(
                                f"[LEVEL {level}] Missing parent path for FID {parent_fid}"
                            )
                        parent_path = fid_to_path[parent_fid]

                    tree_gdf["_parent_path"] = parent_path

                    all_results.append(tree_gdf)

            if not all_results:

                logging.warning(
                    f"[LEVEL {level}-{layer_type}] "
                    "No spatial records found"
                )

                continue

            tree_gdf = pd.concat(
                all_results,
                ignore_index=True
            )

            logging.info(
                f"[LEVEL {level}-{layer_type}] "
                f"Combined rows={len(tree_gdf)}"
            )

            existing = get_treepoly(layer_type)

            if existing is None:

                new_tree_gdf = tree_gdf

                logging.info(
                    f"[LEVEL {level}-{layer_type}] "
                    f"Inserting {len(new_tree_gdf)} rows"
                )

            else:

                new_tree_gdf = tree_gdf[
                    ~tree_gdf["FID"].isin(existing["FID"])
                ]

                logging.info(
                    f"[LEVEL {level}-{layer_type}] "
                    f"{len(new_tree_gdf)} new rows"
                )

            logging.info(
                f"💾 inserting {len(new_tree_gdf)} rows "
                f"for {layer_type}"
            )

            set_treepoly(
                layer_type,
                upsert_geodf(existing, new_tree_gdf)
            )

            # BUILD GEO INDEX & SEED NEXT LEVELS
            next_level = level + 1

            if next_level not in active_parent_rows:
                active_parent_rows[next_level] = []

            matched_this_level = None

            expected_name = (
                normalname(steps[level])
                if level < len(steps)
                else None
            )

            print(f"\nXLEVEL {level} ({layer_type})")
            print(tree_gdf[["FID", "NAME", "_parent_path"]])
            for _, row in tree_gdf.iterrows():

                child_name = normalname(row["NAME"])

                if level == 0:
                    parent_path = None
                    this_path = ROOT
                else:
                    parent_path = row.get("_parent_path", ROOT)
                    this_path = f"{parent_path}/{child_name}"
                # -----------------------------------------------------------------
                # 🌟 REPLACE WITH THIS AMENDED VERSION:
                # -----------------------------------------------------------------
                if this_path not in Geo_index:

                    # 1. Safely pull the spatial geometry from the GeoPandas row
                    roid_coords = None
                    if hasattr(row, "geometry") and row.geometry is not None:
                        try:
                            # Calculate the heavy representative point once during creation
                            centroid_point = row.geometry.representative_point()
                            # Explicitly force float conversion to prevent JSON serialization errors
                            roid_coords = [float(centroid_point.y), float(centroid_point.x)]
                        except Exception as spatial_err:
                            logging.warning(f"Could not calculate representative point for {this_path}: {spatial_err}")

                    # 2. Inject 'roid' directly into your index master schema
                    Geo_index[this_path] = {
                        "level": layer_type,
                        "name": child_name,
                        "parent": parent_path,
                        "children": [],
                        "roid": roid_coords  # 🌟 Added permanently to the baked file output!
                    }

                if parent_path in Geo_index:

                    if this_path not in Geo_index[parent_path]["children"]:
                        Geo_index[parent_path]["children"].append(this_path)

                fid_to_path[row["FID"]] = this_path

                should_match = (
                    level == 0
                    or level >= len(steps)
                    or child_name == expected_name
                )

                if should_match:

                    matched_path = this_path
                    matched_this_level = this_path

                print("layer_type =", layer_type)
                print("FACEENDING[layer_type] =", FACEENDING[layer_type])
                print("matched_path =", matched_path)


                # Append discovered nodes straight into the active parents cache
                row_copy = row.copy()
                row_copy["_parent_path"] = this_path
                active_parent_rows[next_level].append(row_copy)

            if level < len(steps) and matched_this_level is None:

                logging.warning(
                    f"[LEVEL {level}] "
                    f"No match found for step: {expected_name}"
                )

    logging.debug(
        f"Final matched_path: {matched_path}"
    )
    final_path = ROOT

    for step in steps[1:]:
        target = normalname(step)

        children = Geo_index[final_path]["children"]

        found = None

        for child_path in children:
            if Geo_index[child_path]["name"] == target:
                found = child_path
                break

        if found is None:
            break

        final_path = found

    node = Geo_index[final_path]

    match_full_filepath = (
        final_path +
        FACEENDING[node["level"]]
    )

    print("match_full_filepath =", match_full_filepath)

    logging.debug(
        f"Geo_index contains {len(Geo_index)} entries"
    )

    persist(Treepolys, Fullpolys, Geo_index)

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

#Fullpolys = {
#    k: empty_gdf() for k in Treepolys
#}


def get_treepoly(layer_type: str):
    return Treepolys.get(layer_type)

def set_treepoly(layer_type: str, gdf: gpd.GeoDataFrame):
    Treepolys[layer_type] = gdf

def has_treepoly(layer_type: str) -> bool:
    return layer_type in Treepolys and not Treepolys[layer_type].empty

def check_level4_gap(elevels: list) -> bool:
    if len(elevels) <= 4:
        return True

    level_type = elevels[4]
    gdf = Treepolys.get(level_type)

    if gdf is None:
        return True

    return gdf.empty



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
Fullpolys: dict[str, gpd.GeoDataFrame] = {}
Geo_index = {}
print(f"DEBUG: Config Memory Address of Geo_index here: {id(Geo_index)}")
# Then check the ID inside the persist function

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

levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }






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


Overlaps = {
    "country": 0.5,            # almost complete overlap; usually one polygon
    "nation": 0.5,             # moderate, allows small overseas regions
    "county": 0.5,           # counties are large; even tiny overlap is ok
    "constituency": 0.3,   # very small fraction of parent polygon
    "ward": 0.3,          # tiny polygons; keep threshold tiny
    "division": 0.3,      # similar to wards
    "walk": 0.1,             # walking routes
    "polling_district": 0.1, # small but meaningful overlap
    "street": 0.05,           # street polygons
    "walkleg": 0.05           # same as walk
}

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
