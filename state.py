import json
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry import Point, Polygon, MultiPoint
from shapely import crosses, contains, union, envelope, intersection
from shapely.ops import nearest_points
from elections import route

from config import TABLE_FILE, RESOURCE_FILE, LAST_RESULTS_FILE, workdirectories, DEVURLS


from types import MappingProxyType

def normalname(name):
    if isinstance(name, str):
        name = name.replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(".","").replace(","," ").replace("  "," ").replace(" ","_").upper()
    elif isinstance(name, pd.Series):
        name = name.str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace("'","").str.replace(".","").str.replace(","," ").str.replace("  "," ").str.replace(" ","_").str.upper()
    else:
        print("______ERROR: Can only normalise name in a string or series")
    return name


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

    nodestep = None

    # Load source GeoJSON
    gdf = gpd.read_file(source)
    matched = gdf.head(0)

    # ----- CRS FIX ------------------------------------------------------
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Standardize field names
    gdf = gdf.rename(columns={sourcekey: 'NAME'})
    if 'OBJECTID' in gdf.columns:
        gdf = gdf.rename(columns={'OBJECTID': 'FID'})


    # ----- LOOKUP BY NAME ----------------------------------------------
    if name is not None:
        target = normalname(name.split("/")[-1])
        matched = gdf[
            gdf["NAME"]
            .astype(str)
            .apply(normalname)
            == target
        ]

    elif roid is not None:
        # ----- LOOKUP BY LAT/LON ---------------------------------------
        latitude = roid[0]
        longitude = roid[1]
        if longitude is None or latitude is None:
            print(f"[filterArea] No coordinates — skipping spatial filter")
        else:
            point = Point(longitude, latitude)  # (lon, lat)
            matched = gdf[gdf.contains(point)]

    # ----- SAVE IF MATCHED ---------------------------------------------
    if not matched.empty:
        nodestep = normalname(matched['NAME'].values[0])
        output_path = destination

        matched.to_file(output_path, driver="GeoJSON")
        print(f"Found {len(matched)} matching feature(s). Saved to {output_path}")
    else:
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
    parent_level,
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
    Parent type is derived from resolved_levels[parent_level].
    """

    parent_type = resolved_levels.get(parent_level)
    if parent_type is None:
        raise ValueError(f"No parent type found for parent_level={parent_level}")

    print(f"\n[DEBUG] intersectingArea | source={source}")
    print(f"[DEBUG] parent_type={parent_type}, roid={roid}, select_child_name={select_child_name}")

    # ------------------------------------------------------------------
    # 1. Load child layer
    # ------------------------------------------------------------------
    gdf = gpd.read_file(source)

    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    gdf = gdf.rename(columns={sourcekey: "NAME"})
    if "OBJECTID" in gdf.columns:
        gdf = gdf.rename(columns={"OBJECTID": "FID"})

    all_child_polygons = gdf
    print(f"[DEBUG] Loaded {len(gdf)} child features")

    # ------------------------------------------------------------------
    # 2. Validate parent row
    # ------------------------------------------------------------------
    if parent_row is None or parent_row.geometry.is_empty:
        raise ValueError(f"Invalid parent_row for {parent_type} - {source} - {parent_level}")

    parent_geom = parent_row.geometry
    parent_name = normalname(parent_row["NAME"])

    parent_gdf = Fullpolys[parent_type].to_crs("EPSG:4326")
    parent_names = parent_gdf["NAME"].apply(normalname)

    if parent_name not in parent_names.values:
        raise ValueError(
            f"Parent '{parent_name}' not found in parent layer '{parent_type}'"
        )

    # ------------------------------------------------------------------
    # 3. Compute intersections (projected CRS)
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
    # 4. Resolve selected child (navigation only)
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
    # 5. Save
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
    parent_level,
    parent_row,
    select_name=None,
    roid=None,
):
    """
    Load a layer using either filter or intersection method.
    parent_level is used to derive parent_type from resolved_levels.
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
        parent_level=parent_level,
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



from collections import defaultdict
from typing import DefaultDict
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

def ensure_treepolys(
    *,
    territory: str | None,
    sourcepath: str | None,
    here: tuple[float, float] | None,
    resolved_levels: dict[int, str],
):
    if not resolved_levels:
        raise ValueError("resolved_levels is required")

    steps = stepify(sourcepath) if sourcepath else []
    territory_level = len(stepify(territory)) - 1 if territory else -1

    layer_defs = { (l["level"], l["key"]): l for l in LAYERS }
    active_parents: dict[int, pd.Series] = {}
    newpath = ""

    # ✅ Track inserted FIDs to prevent duplicates
    inserted_fids: DefaultDict[str, set] = defaultdict(set)

    for level, layer_type in resolved_levels.items():
        if level >= len(steps) and not here:
            print(f"[DEBUG] Skipping level {level} layer {layer_type} — no step and no spatial fallback")
            continue

        if has_treepoly(layer_type):
            print(f"[DEBUG] Skipping level {level} layer {layer_type} — already loaded")
            continue

        layer = layer_defs.get((level, layer_type))
        if not layer:
            print(f"[WARN] No layer definition for level {level} layer {layer_type}")
            continue

        # Parent row logic
        parent_level = max(0, min(level - 1, territory_level))
        parent_layer_type = resolved_levels.get(parent_level)
        parent_row = active_parents.get(parent_level)

        # fallback: if no active parent yet, try spatial or whole layer
        if parent_row is None and parent_layer_type:
            parent_gdf = get_treepoly(parent_layer_type)
            if isinstance(parent_gdf, gpd.GeoDataFrame) and len(parent_gdf) == 1:
                parent_row = parent_gdf.iloc[0]

        # Determine selection or spatial fallback
        select_name = steps[level] if level < len(steps) else None
        roid = here if level >= len(steps) else None

        # Load layer with updated signature
        name, tree_gdf, full_gdf = load_layer(
            layer=layer,
            level=level,
            resolved_levels=resolved_levels,
            parent_level=parent_level,
            parent_row=parent_row,
            select_name=select_name,
            roid=roid,
        )


        # 🔐 Update Treepolys and Fullpolys
        existing = get_treepoly(layer_type)

        if existing is None or existing.empty:
            print(f"[DEBUG] Before upsert {layer_type}: 0 rows (initial or reset)")
            new_tree_gdf = tree_gdf
        else:
            print(f"[DEBUG] Before upsert {layer_type}: {len(existing)} rows")
            new_tree_gdf = tree_gdf[~tree_gdf["FID"].isin(existing["FID"])]

        set_treepoly(layer_type, upsert_geodf(existing, new_tree_gdf))

        updated = get_treepoly(layer_type)
        print(f"[DEBUG] After upsert {layer_type}: {len(updated) if updated is not None else 0} rows")

        Fullpolys[layer_type] = upsert_geodf(Fullpolys.get(layer_type), full_gdf)

        for idx, row in tree_gdf.iterrows():
            print(f"___POLYCHECK: {layer_type.capitalize()} level {level}: {row['NAME']}, Parent: {parent_row['NAME'] if parent_row is not None else 'None'}")

        # Determine active parent row safely
        new_parent_row = None
        if not tree_gdf.empty:
            if name:
                matches = tree_gdf[tree_gdf["NAME"].apply(normalname) == normalname(name)]
                if not matches.empty:
                    new_parent_row = matches.iloc[0]
            if new_parent_row is None and len(tree_gdf) == 1:
                new_parent_row = tree_gdf.iloc[0]
            if new_parent_row is None and roid is not None:
                distances = tree_gdf.geometry.apply(lambda g: g.distance(Point(roid[::-1])))
                new_parent_row = tree_gdf.iloc[distances.idxmin()]

        if new_parent_row is not None:
            active_parents[level] = new_parent_row
            print(f"[DEBUG] Active parent for level {level} set to {new_parent_row['NAME']}")
        else:
            print(f"[DEBUG] No active parent could be set at level {level}")

        if name:
            newpath = f"{newpath}/{name}" if newpath else name
            print(f"[DEBUG] Layer {layer_type} loaded, newpath={newpath}, features={len(tree_gdf)}")

    return newpath




def layer_loaded(layer_key):
    return (
        layer_key in Treepolys
        and Treepolys[layer_key] is not None
        and not Treepolys[layer_key].empty
    )


def empty_gdf():
    return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


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
            f"{workdirectories['resultdir']}/LEH-Candidates-2023.xlsx"
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
    "report_data": "Report Data",
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
        "src": "Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson",
        "field": "CTYUA23NM",
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
progress = {
    "election": "",
    "status": "idle",       # Can be 'idle', 'running', 'complete', 'error'
    "percent": 0,           # Integer from 0 to 100
    "targetfile": "test.csv",
    "message": "Waiting...", # Optional string
    "dqstats_html": ""
    }

DQ_DATA = {
"df": pd.DataFrame(),  # initially empty
}

layeritems = []
#allelectors = pd.read_csv(config.workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
# need a keyed dict indicating last recorded winning first party name for a given normalised node name



load_last_results()
