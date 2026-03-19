import json
import os
import pandas as pd
import re
import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry import Point, Polygon
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
    import re
    import pandas as pd

    def clean(s):
        if not isinstance(s, str):
            return s

        s = s.replace(" & ", " AND ")

        # ✅ KEEP underscores
        s = re.sub(r"[^A-Za-z0-9 _]+", "", s)

        # normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()

        # convert spaces to underscores
        s = s.replace(" ", "_")

        # remove duplicate underscores
        s = re.sub(r"_+", "_", s)

        # remove leading/trailing underscores
        s = s.strip("_")

        return s.upper().removesuffix("_ED")

    if isinstance(name, str):
        return clean(name)

    elif isinstance(name, pd.Series):
        return name.apply(clean)

    else:
        print("______ERROR: Can only normalise name in a string or series")
        return name

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

    gdf_RAW = gpd.read_file(source)
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
        matched.to_file(destination, driver="GeoJSON")
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
    resolved_levels,
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
    gdf_RAW = gpd.read_file(source)
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
    child_type = resolved_levels[child_level]
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

    candidates_proj = candidates.to_crs(proj_crs)

    overlaps = candidates_proj.geometry.intersection(working_geom_proj).area
    mask = overlaps > threshold

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

def load_layer(
    *,
    layer,
    level,
    resolved_levels,
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
        resolved_levels=resolved_levels,
        destination=out,
        parent_row=parent_row,
        roid=roid,
        select_child_name=select_name,
        boundary_geom=boundary_geom
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



def get_parent_rows(plevels, child_level, parent_rows, roid, boundary_geom):
    from state import Treepolys
    from shapely.geometry import Point
    import logging

    parent_layer_type = plevels.get(child_level)
    parent_tree = Treepolys.get(parent_layer_type)

    if parent_tree is None or parent_tree.empty:
        logging.warning(f"[WARNING] No parent tree for {parent_layer_type}")
        return []

    logging.debug(f"[DEBUG] Parent tree has {len(parent_tree)} features")

    # --------------------------------------------------
    # 1️⃣ POLYGON MODE (Option B primary mode)
    # --------------------------------------------------
    if boundary_geom is not None:
        matches = parent_tree[parent_tree.geometry.intersects(boundary_geom)]
        if not matches.empty:
            logging.debug(f"[DEBUG] Polygon match → {len(matches)} parents")
            return list(matches.itertuples(index=False))

    # --------------------------------------------------
    # 2️⃣ POINT MODE (multi-match first)
    # --------------------------------------------------
    if roid is not None:
        pt = Point(roid[::-1])

        matches = parent_tree[parent_tree.contains(pt)]

        if not matches.empty:
            logging.debug(f"[DEBUG] Point match → {len(matches)} parents")
            return list(matches.itertuples(index=False))

        # --------------------------------------------------
        # 3️⃣ FALLBACK: closest parent (YOUR ORIGINAL LOGIC)
        # --------------------------------------------------
        logging.debug("[DEBUG] No containing parent, using nearest")

        distances = parent_tree.geometry.distance(pt)
        distances = distances.dropna()

        if not distances.empty:
            idx = distances.idxmin()
            nearest = parent_tree.loc[idx]
            logging.debug(f"[DEBUG] Closest parent: {nearest['NAME']}")
            return [nearest]

    # --------------------------------------------------
    # 4️⃣ LAST RESORT
    # --------------------------------------------------
    logging.warning("[WARNING] No parent match found, returning all")
    return list(parent_tree.itertuples(index=False))

def ensure_fulltree(*, resolved_levels, parent_levels):
    from state import Treepolys
    import geopandas as gpd

    geo_index = {}

    # Root
    ROOT = "UK"
    geo_index[ROOT] = {
        "level": "root",
        "name": ROOT,
        "parent": None,
        "children": []
    }

    active_paths = {0: [ROOT]}

    # -------------------------------------------------------
    # Walk through levels (same pattern as ensure_treepolys)
    # -------------------------------------------------------

    for level, layer_type in resolved_levels.items():

        layer_gdf = Treepolys.get(layer_type)
        parent_layer_type = parent_levels.get(level)

        if layer_gdf is None or layer_gdf.empty:
            continue

        next_paths = []

        for parent_path in active_paths.get(level, [ROOT]):

            parent_name = parent_path.split("/")[-1]
            parent_geom = None

            # --------------------------------------------------
            # Get parent geometry (if exists)
            # --------------------------------------------------
            if parent_layer_type:
                parent_tree = Treepolys.get(parent_layer_type)

                if parent_tree is not None:
                    match = parent_tree[
                        parent_tree["NAME"].astype(str).str.upper()
                        == parent_name.upper()
                    ]
                    if not match.empty:
                        parent_geom = match.iloc[0].geometry

            # --------------------------------------------------
            # Find children
            # --------------------------------------------------
            if parent_geom is not None:
                matches = layer_gdf[layer_gdf.geometry.intersects(parent_geom)]
            else:
                matches = layer_gdf

            for _, row in matches.iterrows():
                child_name = normalname(row["NAME"])
                child_path = f"{parent_path}/{child_name}"

                if child_path not in geo_index:
                    geo_index[child_path] = {
                        "level": layer_type,
                        "name": child_name,
                        "parent": parent_path,
                        "children": []
                    }

                # link parent → child
                if child_path not in geo_index[parent_path]["children"]:
                    geo_index[parent_path]["children"].append(child_path)

                next_paths.append(child_path)

        active_paths[level + 1] = next_paths

    return geo_index

def ensure_treepolys(
    *,
    territory: str | None,
    sourcepath: str | None,
    here: tuple[float, float] | None,
    boundary_geom=None,   # 👈 NEW
    resolved_levels: dict[int, str],
    parent_levels: dict[int, str]
    ):

    if boundary_geom is not None:
        boundary_geom = boundary_geom.buffer(0)

    if not resolved_levels:
        raise ValueError("resolved_levels is required")

    logging.debug(f"Starting treepolys with territory={territory} and sourcepath={sourcepath}")

    def path_compare(A: str | Path, B: str | Path) -> str:
        A_path = Path(A)
        B_path = Path(B)
        return str(A_path) if len(B_path.parts) > len(A_path.parts) else str(B_path)

    # -------------------------------------------------------
    # Prepare source path
    # -------------------------------------------------------

    sourcepath = path_compare(territory, sourcepath) if (territory or sourcepath) else None
    steps = stepify(sourcepath) if sourcepath else []

    layer_defs = {(l["level"], l["key"]): l for l in LAYERS}

    active_parent_rows: dict[int, list] = {}
    active_parent_rows[0] = [None]


    newpath = ""

    # -------------------------------------------------------
    # Walk through resolved levels
    # -------------------------------------------------------

    for level, layer_type in resolved_levels.items():

        if level >= len(steps) and not here and boundary_geom is None:
            logging.debug(f"[LEVEL {level}] Skipping {layer_type} layer — no step and no spatial fallback")
            continue

        layer = layer_defs.get((level, layer_type))


        if not layer:
            logging.warning(f"[LEVEL {level}] No layer processing for level {level} type {layer_type}")
            continue

        select_name = steps[level] if level < len(steps) else None
        roid = here

        parent_rows = active_parent_rows.get(level, [None])

        # -------------------------------------------------------
        # Load layer
        # -------------------------------------------------------
        # so potential county variant if parent_name == 'county_variant'
        all_results = []

        for parent_row in parent_rows:
            # Extract parent_name safely
            parent_name = normalname(parent_row["NAME"]) if parent_row is not None else None

            logging.debug(f"[LEVEL {level}] Loading {layer_type} with parent {parent_name}")



            src = layer['src']
            field = layer['field']

            if isinstance(src, list) and len(src) == 2:

                if parent_name and src[1].upper().find(parent_name.upper()) >= 0:
                    src = src[1]
                    field = field[1]
                    print(f"____Selecting secondary division source {src}")
                else:
                    src = src[0]
                    field = field[0]
                    print(f"____Selecting primary division source {src} & {field}")
            layer_local = dict(layer)
            layer_local['src'] = src
            layer_local['field'] = field

            name, tree_gdf, full_gdf = load_layer(
                layer=layer_local,
                level=level,
                resolved_levels=resolved_levels,
                parent_levels=parent_levels,
                parent_row=parent_row,
                select_name=select_name,
                roid=roid,
                boundary_geom=boundary_geom
            )

            if tree_gdf is not None and not tree_gdf.empty:
                all_results.append(tree_gdf)

        if all_results:
            tree_gdf = pd.concat(all_results, ignore_index=True)
        else:
            tree_gdf = gpd.GeoDataFrame()

        tree_gdf = tree_gdf.drop_duplicates(subset="FID")
        if tree_gdf is not None and tree_gdf.crs is None:
            tree_gdf.set_crs("EPSG:4326", inplace=True)

        # -------------------------------------------------------
        # Compute inclusion union
        # -------------------------------------------------------

        if boundary_geom is not None:
            inclusion_union = boundary_geom

        elif parent_rows:
            parent_geoms = [p.geometry for p in parent_rows if p is not None]
            inclusion_union = gpd.GeoSeries(parent_geoms).unary_union if parent_geoms else None

        else:
            inclusion_union = None

        existing_children = get_treepoly(layer_type)
        children_union = None

        if existing_children is not None and not existing_children.empty:
            if existing_children.crs is None:
                existing_children.set_crs("EPSG:4326", inplace=True)
            children_union = existing_children.geometry.unary_union


        if boundary_geom is None:
            if parent_rows:
                parent_geoms = [p.geometry for p in parent_rows if p is not None]
                parent_union = gpd.GeoSeries(parent_geoms).unary_union if parent_geoms else None
            else:
                parent_union = None

            if parent_union is not None and children_union is not None:
                inclusion_union = parent_union.union(children_union)
            elif parent_union is not None:
                inclusion_union = parent_union
            else:
                inclusion_union = children_union

        # -------------------------------------------------------
        # Filter candidates by intersection
        # -------------------------------------------------------
        if tree_gdf is None or tree_gdf.empty:
            continue  # skip empty layers
        if inclusion_union is not None and tree_gdf is not None and not tree_gdf.empty:
            tree_gdf = tree_gdf[tree_gdf.geometry.intersects(inclusion_union)]

        # -------------------------------------------------------
        # Upsert into Treepolys
        # -------------------------------------------------------

        existing = get_treepoly(layer_type)

        if existing is None:
            new_tree_gdf = tree_gdf
        else:
            new_tree_gdf = tree_gdf[~tree_gdf["FID"].isin(existing["FID"])]

        set_treepoly(layer_type, upsert_geodf(existing, new_tree_gdf))

        updated = get_treepoly(layer_type)

        logging.debug(
            f"[LEVEL {level}] After upsert {layer_type}: "
            f"{len(updated) if updated is not None else 0} rows"
            )


        # Prepare parent for next level
        # -------------------------------------------------------

        next_level = level + 1

        next_parents = []

        next_parents = get_parent_rows(
            parent_levels,
            next_level,
            parent_rows,
            roid,
            boundary_geom
        )

        # Deduplicate by NAME or FID
        seen = set()
        unique_parents = []

        for p in next_parents:
            key = getattr(p, "FID", getattr(p, "NAME", None))
            if key not in seen:
                seen.add(key)
                unique_parents.append(p)

        names = [getattr(p, "NAME", "Unknown") for p in unique_parents]
        # MISSING
        active_parent_rows[next_level] = unique_parents
        logging.debug(f"[LEVEL {next_level}] Active parents: {names}")

        # -------------------------------------------------------
        # Build path
        # -------------------------------------------------------

        if name:
            newpath = f"{newpath}/{name}" if newpath else name

            logging.debug(
                f"[LEVEL {level}] Layer {layer_type} loaded, newpath={newpath}"
            )

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
