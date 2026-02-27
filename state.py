import json
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry import Point, Polygon, MultiPoint
from shapely import crosses, contains,covers, union, envelope, intersection
from shapely.ops import nearest_points
from elections import route, branchcolours

from collections import defaultdict
from typing import DefaultDict
from pathlib import Path
from config import TABLE_FILE, CANDIDATES_FILE,LAST_RESULTS_FILE, workdirectories, DEVURLS

import logging


from types import MappingProxyType

progress = {}

def normalname(name):
    if isinstance(name, str):
        name = name.replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(".","").replace(","," ").replace("  "," ").replace(" ","_").upper()
    elif isinstance(name, pd.Series):
        name = name.str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace("'","").str.replace(".","").str.replace(","," ").str.replace("  "," ").str.replace(" ","_").str.upper()
    else:
        print("______ERROR: Can only normalise name in a string or series")
    return name

def ensure_4326(gdf):
    """
    Ensure the GeoDataFrame has CRS EPSG:4326 for Folium.
    Returns a GeoDataFrame in 4326.
    """
    # 1️⃣ Check if CRS exists
    if gdf.crs is None:
        print("[CRS] Missing — assuming EPSG:4326 (lon/lat)")
        gdf = gdf.set_crs(epsg=4326)
    else:
        print(f"[CRS] Detected: {gdf.crs}")

    # 2️⃣ Convert to 4326 if needed
    if gdf.crs.to_epsg() != 4326:
        print(f"[CRS] Reprojecting from {gdf.crs} to EPSG:4326 for Folium")
        gdf = gdf.to_crs(epsg=4326)
    else:
        print("[CRS] Already EPSG:4326 — no conversion needed")

    # 3️⃣ Optional: inspect bounds
    print("[CRS] GeoDataFrame bounds:", gdf.total_bounds)

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

def filterArea(source, sourcekey, destination,roid=None,name=None):
    """
    If name is provided → lookup by polygon NAME.
    Otherwise → lookup by lat/lon from roid.
    """
    print(f"[filterArea] destination :{destination} roid {roid} step:{name}")

    nodestep = None

    # Load source GeoJSON
    gdf_RAW = gpd.read_file(source)
    # ----- CRS FIX ------------------------------------------------------

    # -------------------------------

    gdf = ensure_4326(gdf_RAW)
    matched = gdf.head(0)


    # Standardize field names
    gdf = gdf.rename(columns={sourcekey: 'NAME'})
    if 'OBJECTID' in gdf.columns:
        gdf = gdf.rename(columns={'OBJECTID': 'FID'})


    # ----- LOOKUP BY NAME IF PRESENT ----------------------------------------------
    if name is not None:
        target = normalname(name.split("/")[-1])
        matched = gdf[
            gdf["NAME"]
            .astype(str)
            .apply(normalname)
            == target
        ]

    # ----- SAVE IF MATCHED ---------------------------------------------
    if not matched.empty:
        nodestep = normalname(matched['NAME'].values[0])
        output_path = destination

        matched.to_file(output_path, driver="GeoJSON")
        print(f"[filterArea] Found {nodestep}{len(matched)} matching feature(s). Saved to {output_path}")
    elif roid is not None:
        print("[filterArea] Coords — do spatial filter")

        # ----- LOOKUP BY LAT/LON ---------------------------------------
        latitude = roid[0]
        longitude = roid[1]

        if longitude is None or latitude is None:
            print("[filterArea] No coordinates — skipping spatial filter")
            matched = gdf.iloc[0:0]   # empty result
        else:
            # 1️⃣ Ensure GDF has a CRS
            if gdf.crs is None:
                raise ValueError("GeoDataFrame has no CRS set")

            # 2️⃣ Create point in WGS84 (lat/lon)

            point_gs = gpd.GeoSeries(
                [Point(longitude, latitude)],  # (lon, lat)
                crs="EPSG:4326"
            )

            point = point_gs.iloc[0]

            # 4️⃣ Now CRS definitely matches
            matched = gdf[gdf.covers(point)]
            nodestep = normalname(matched['NAME'].iloc[0])


        print(f"[filterArea] Coords — point {point} match ({name}) with {len(matched)} rows")


    if matched is None or matched.empty:
        if name:
            print(f'No match found for name "{name}".')
        else:
            print("No matching polygon found for that lat/lon.",roid)

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
    resolved_levels,
    destination,
    *,
    parent_row,          # full GeoSeries row
    roid=None,
    select_child_name=None,
):
    """
    Compute intersection of child polygons with a parent polygon.
    Parent type is derived from parent_levels[child_level].
    If parent_row is None, include all child polygons (no filtering).
    """
    parent_name = normalname(parent_row["NAME"]) if parent_row is not None else "None"
    parent_type = parent_levels.get(child_level)
    if parent_type is None:
        raise ValueError(f"No parent type found for parent_level IN {parent_levels}")

    print(f"\n[DEBUG] intersectingArea | source={source}")
    print(f"[DEBUG] parent_name={parent_name} parent_type={parent_type}, roid={roid}, select_child_name={select_child_name}")

    # ------------------------------------------------------------------
    # 1. Load child layer
    # ------------------------------------------------------------------
    gdf_RAW = gpd.read_file(source)
    # ----- CRS FIX ------------------------------------------------------

    # -------------------------------

    gdf = ensure_4326(gdf_RAW)

    gdf = gdf.rename(columns={sourcekey: "NAME"})
    if "OBJECTID" in gdf.columns:
        gdf = gdf.rename(columns={"OBJECTID": "FID"})

    all_child_polygons = gdf
    print(f"[DEBUG] Loaded {len(gdf)} child features")

    # ------------------------------------------------------------------
    # 2. Skip parent validation and intersection if parent_row is None
    # ------------------------------------------------------------------
    if parent_row is None or parent_row.geometry.is_empty:
        print(f"[DEBUG] parent_row is None, including all child polygons without filtering")
        return None, all_child_polygons, all_child_polygons


    parent_geom = parent_row.geometry

    # ------------------------------------------------------------------
    # 4. Compute intersections (projected CRS) only if parent_row is not None
    # ------------------------------------------------------------------
    child_type = resolved_levels[child_level]
    threshold = Overlaps.get(child_type, 0)
    print(f"[DEBUG] Intersection threshold ({child_type}): {threshold}")

    candidates = gdf[gdf.geometry.intersects(parent_geom)]
    print(f"[DEBUG] Candidates intersecting bbox: {len(candidates)}")

    if candidates.empty:
        return None, gpd.GeoDataFrame(), all_child_polygons

    proj_crs = "EPSG:3857"
    parent_geom_proj = gpd.GeoSeries([parent_geom], crs="EPSG:4326").to_crs(proj_crs).iloc[0]
    candidates_proj = candidates.to_crs(proj_crs)

    overlaps = candidates_proj.geometry.intersection(parent_geom_proj).area
    mask = overlaps > threshold

    child_polygons_within_parent = candidates[mask].copy()
    print(f"[DEBUG] Children within parent above threshold: {len(child_polygons_within_parent)}")

    # ------------------------------------------------------------------
    # 5. Resolve selected child (navigation only)
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
    #insert incoming geometries into the existing layer
    if existing is None or existing.empty:
        return incoming

    if incoming is None or incoming.empty:
        return existing

    if existing.crs != incoming.crs:
        incoming = incoming.to_crs(existing.crs)

    existing = existing.set_index(key, drop=False)
    incoming = incoming.set_index(key, drop=False)

    # overwrite or insert
    for fid, row in incoming.iterrows():
        existing.loc[fid] = row

    return gpd.GeoDataFrame(existing.reset_index(drop=True), crs=existing.crs)


def load_layer(
    *,
    layer,
    level,
    resolved_levels,
    parent_levels,
    parent_row,
    select_name=None,
    roid=None,
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
            name=select_name,
            roid=roid,
        )

    # Intersection-based selection
    return intersectingArea(
        source=src,
        sourcekey=layer["field"],
        parent_levels=parent_levels,
        child_level= level,
        resolved_levels=resolved_levels,
        destination=out,
        parent_row=parent_row,
        roid=roid,
        select_child_name=select_name,
    )


def stepify(path):
    if not path:
        return []

    route = (
        path.replace('/WALKS/', '/')
            .replace('/PDS/', '/')
            .replace('/WARDS/', '/')
            .replace('/DIVS/', '/')
    )
    parts = route.split("/")
    last = parts.pop()

    if "-PRINT.html" in last:
        leaf = subending(last, "").split("--").pop()
        parts.append(leaf)

    print("____LEAFNODE:", path, parts)
    return parts


import logging

def get_parent_row(plevels, child_level, parent_name, roid):
    """
    Resolves the parent row based on the level in plevels.
    """
    from state import Treepolys, Fullpolys

    logging.debug(f"[DEBUG] Resolving parent for child level {child_level}, parent_name={parent_name}, roid={roid}")

    # Get the parent layer type based on child_level from plevels
    parent_layer_type = plevels.get(child_level)
    logging.debug(f"[DEBUG] Parent layer type for child level {child_level} is {parent_layer_type} in levels {plevels}")

    # Get the GeoDataFrame for the parent layer from Treepolys
    parent_tree = Treepolys.get(parent_layer_type)
    if parent_tree is None:
        logging.warning(f"[WARNING] No parent tree found for layer type {parent_layer_type}")
        return None
    logging.debug(f"[DEBUG] Parent tree for {parent_layer_type} has {len(parent_tree)} features")

    parent_row = None

    # If no parent_row found and there is only one row in parent_tree, use that as the parent
    if len(parent_tree) == 1:
        parent_row = parent_tree.iloc[0]
        logging.debug(f"[DEBUG] Only one parent feature available, using it as the parent: {parent_row['NAME']}")
        return parent_row
    # If still no parent_row and a roid (spatial point) is provided, find the closest parent by distance
    if parent_row is None and roid is not None:
        logging.debug(f"[DEBUG] No parent found by name or single row fallback. Using spatial search for roid={roid}")

        # Calculate distances from the point to each geometry in the GeoDataFrame
        distances = parent_tree.geometry.apply(lambda g: g.distance(Point(roid[::-1])))

        # Check if distances is empty or contains NaNs
        if distances.empty:
            logging.error(f"[ERROR] Distances Series is empty. No geometries to calculate distances.")
            parent_row = None  # Handle empty case as needed
        elif distances.isna().all():
            logging.error(f"[ERROR] All distances are NaN. This could be due to invalid geometries.")
            parent_row = None  # Handle NaN case as needed
        else:
            # Check if there are any valid distances and ensure we have a valid index
            valid_distances = distances.dropna()  # Remove NaNs from distances

            if valid_distances.empty:
                logging.error(f"[ERROR] No valid distances after dropping NaNs.")
                parent_row = None  # Handle the case where no valid distances are left
            else:
                # Get the index of the minimum distance (the closest geometry)
                min_distance_idx = valid_distances.idxmin()

                # Ensure that the index is valid and within bounds
                if min_distance_idx in parent_tree.index:
                    parent_row = parent_tree.loc[min_distance_idx]  # Use .loc for better error handling
                else:
                    logging.error(f"[ERROR] The index {min_distance_idx} is out of bounds or invalid.")
                    parent_row = None  # Handle as needed (e.g., default or fallback logic)
        logging.debug(f"[DEBUG] Parent found by spatial search: {parent_row['NAME']} at distance {distances[min_distance_idx]}")

    if parent_row is None:
        logging.warning(f"[WARNING] No parent row could be found for child level {child_level}. Returning None.")

    return parent_row




def ensure_treepolys(
    *,
    territory: str | None,
    sourcepath: str | None,
    here: tuple[float, float] | None,
    resolved_levels: dict[int, str],
    parent_levels: dict[int, str]
):
    if not resolved_levels:
        raise ValueError("resolved_levels is required")

    logging.debug(f"Starting treepolys with territory={territory} and sourcepath={sourcepath}")

    def path_compare(A: str | Path, B: str | Path) -> str:
        """Compare paths and return the appropriate one."""
        A_path = Path(A)
        B_path = Path(B)

        len_A = len(A_path.parts)
        len_B = len(B_path.parts)

        return str(A_path) if len_B <= len_A else str(B_path)

    # Select the best source path based on length
    sourcepath = path_compare(territory, sourcepath)
    steps = stepify(sourcepath) if sourcepath else []
    territory_level = len(stepify(territory)) - 1 if territory else -1

    layer_defs = { (l["level"], l["key"]): l for l in LAYERS }
    active_parent_rows: dict[int, pd.Series] = {}
    active_parent_rows[0] = None
    newpath = ""

    for level, layer_type in resolved_levels.items():
        # Skip if no steps and no spatial fallback available
        if level >= len(steps) and not here:
            logging.debug(f"[LEVEL {level}] Skipping {layer_type} layer — no step and no spatial fallback")
            continue

        # Skip if the layer has already been processed
        if has_treepoly(layer_type):
            logging.debug(f"[LEVEL {level}] Skipping {layer_type} layer — already loaded")
            continue

        # Retrieve the layer definition for the current level
        layer = layer_defs.get((level, layer_type))
        if not layer:
            logging.warning(f"[LEVEL {level}] No layer processing for level {level} type {layer_type}")
            continue

        # Prepare the selection or spatial fallback criteria
        select_name = steps[level] if level < len(steps) else None
        roid = here
        logging.debug(f"[LEVEL {level}] layer_type: {layer_type}: select_name:{select_name}")

        # Parent resolution logic

        parent_row = active_parent_rows.get(level,None)

        # Check if the parent_tree GeoDataFrame is valid and contains exactly one row
        parent_name = normalname(parent_row["NAME"]) if parent_row is not None else None
        # Loading the layer for this level

        num_parent_rows = parent_row.shape[0] if parent_row is not None else 0

        logging.debug(f"[LEVEL {level}] Loading layer {layer_type} parent rows {num_parent_rows} in {parent_name} of type {parent_levels[level]}")

        name, tree_gdf, full_gdf = load_layer(
            layer=layer,
            level=level,
            resolved_levels=resolved_levels,
            parent_levels=parent_levels,
            parent_row=parent_row, # None is allowed
            select_name=select_name,
            roid=roid,
        )

        # Upsert the tree_gdf into Treepolys [layer type] and update the dataset
        existing = get_treepoly(layer_type)
        if existing is None:
            # layer search for name or lat long is empty so return all filter or intersecting candidates
            new_tree_gdf = tree_gdf
        else:
            new_tree_gdf = tree_gdf[~tree_gdf["FID"].isin(existing["FID"])]
        set_treepoly(layer_type, upsert_geodf(existing, new_tree_gdf))
        # this is where the layer boundary features are inserted
        # Debug upsert and check the updated data
        updated = get_treepoly(layer_type)
        logging.debug(f"[LEVEL {level}] After upsert {layer_type}: {len(updated) if updated is not None else 0} rows")
        next_level = level + 1
        # Determine the next level's parent filter from the current layer's data
        active_parent_rows[next_level] = get_parent_row(parent_levels,next_level, parent_name,roid)
        # parent_row of parent_layer_type = parent_levels[level]
        # so where to store it ? active_
        logging.debug(f"[LEVEL {next_level}] Active parent set to {parent_name}=={active_parent_rows[next_level].get('NAME', 'Unknown')}")

        # Build the new path for the current layer
        if name:
            newpath = f"{newpath}/{name}" if newpath else name
            logging.debug(f"[LEVEL {level}] Layer {layer_type} loaded, newpath={newpath}")


    logging.debug(f"Final newpath: {newpath}")
    return newpath



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

            ward = row.get("Wardname")
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

def check_level4_gap(rlevels: list) -> bool:
    if len(rlevels) <= 4:
        return True

    level_type = rlevels[4]
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

STATICSWITCH = False
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
VID = {"R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"Independent","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}
VNORM = {"OTHER":"O","REFORM" : "R" , "REFORM_DERBY" : "R" ,"REFORM_UK" : "R" ,"REF" : "R", "RUK" : "R","R" :"R","CONSERVATIVE_AND_UNIONIST" : "C","CONSERVATIVE" : "C", "CON" : "C", "C":"C","LABOUR_PARTY" : "S","LABOUR" : "S", "LAB" :"S", "L" : "L", "LIBERAL_DEMOCRATS" :"LD" ,"LIBDEM" :"LD" , "LIB" :"LD","LD" :"LD", "GREEN_PARTY" : "G" ,"GREEN" : "G" ,"G":"G", "INDEPENDENT" : "I", "IND" : "I" ,"I" : "I" ,"PLAID_CYMRU" : "PC" ,"PC" : "PC" ,"SNP": "SNP" ,"MAYBE" : "Z" ,"WONT_VOTE" : "W" ,"WONT_SAY" : "X" , "SDLP" : "S", "SINN_FEIN" : "SF", "SPK": "N", "TUV" : "C", "UUP" : "C", "DUP" : "C","APNI" : "N", "INET": "I", "NIP": "I","PBPA": "I","WPB": "S","OTHER" : "O"}
VCO = {"O" : "brown","R" : "cyan","C" : "blue","S" : "red","LD" :"yellow","G" :"limegreen","I" :"indigo","PC" : "darkred","SD" : "orange","Z" : "lightgray","W" :  "white", "X" :  "darkgray"}
onoff = {"on" : 1, 'off': 0}
data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))
autofix = {0,1,2,3,4}

# state.py
Treepolys: dict[str, gpd.GeoDataFrame] = {}
Fullpolys: dict[str, gpd.GeoDataFrame] = {}

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
        "src": "Surrey_Proposed_Divisions.geojson",
        "field": "Division_n",
        "out": "Division_Boundaries.geojson",
        "method": "intersect"
    }

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
TypeMaker = { 'nation' : 'downbut','county' : 'downbut', 'constituency' : 'downbut' , 'ward' : 'downbut', 'division' : 'downbut', 'polling_district' : 'downPDbut', 'walk' : 'downWKbut', 'street' : 'PDdownST', 'walkleg' : 'WKdownST'}


ROOT_LEVEL = {
    "W": 3,
    "C": 2,
    "U": 2,
    "B": 4,
    "P": 4,
}


Overlaps = {
    "country": 0.9,            # almost complete overlap; usually one polygon
    "nation": 0.5,             # moderate, allows small overseas regions
    "county": 0.1,           # counties are large; even tiny overlap is ok
    "constituency": 0.001,   # very small fraction of parent polygon
    "ward": 0.0001,          # tiny polygons; keep threshold tiny
    "division": 0.0001,      # similar to wards
    "walk": 0.005,             # walking routes
    "polling_district": 0.005, # small but meaningful overlap
    "street": 0.005,           # street polygons
    "walkleg": 0.005           # same as walk
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
