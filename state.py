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

def clear_treepolys(from_level=None):
    from state import Treepolys, Fullpolys, LAYERS

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
    parent_type,
    destination,
    *,
    parent_geoms=None,
    roid=None,
    select_child_name=None,
):
    """
    Returns:
        (
            selected_child_name,
            child_polygons_within_parent,
            all_child_polygons
        )
    Debug version with detailed logging.
    """

    from state import Treepolys, Fullpolys
    print(f"\n[DEBUG] intersecting Area called for source: {source}")
    print(f"[DEBUG] parent_type: {parent_type}, roid: {roid}, select_child_name: {select_child_name}")

    # ------------------------------------------------------------------
    # 1. Load child layer
    # ------------------------------------------------------------------
    gdf = gpd.read_file(source)
    print(f"[DEBUG] Loaded child layer: {len(gdf)} features")

    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
        print("[DEBUG] CRS was None; set to EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
        print(f"[DEBUG] Reprojected child layer to EPSG:4326")

    gdf = gdf.rename(columns={sourcekey: "NAME"})
    if "OBJECTID" in gdf.columns:
        gdf = gdf.rename(columns={"OBJECTID": "FID"})

    all_child_polygons = gdf

    # ------------------------------------------------------------------
    # 2. Resolve parent geometries
    # ------------------------------------------------------------------
    if parent_geoms is None:
        parent_geoms = Treepolys.get(parent_type, [])
        print(f"[DEBUG] parent_geoms obtained from Treepolys: {type(parent_geoms)}")

    # Handle empty or invalid parent_geoms
    if parent_geoms is None:
        print(f"[WARNING] parent_geoms is None for {parent_type}")
        return None, gpd.GeoDataFrame(), all_child_polygons

    if isinstance(parent_geoms, gpd.GeoDataFrame):
        if parent_geoms.empty:
            print(f"[WARNING] parent_geoms GeoDataFrame is empty for {parent_type}")
            return None, gpd.GeoDataFrame(), all_child_polygons
        parent_geom_list = [row.geometry for _, row in parent_geoms.iterrows()]
    elif isinstance(parent_geoms, list):
        parent_geom_list = parent_geoms
    else:
        print(f"[ERROR] parent_geoms is not a GeoDataFrame or list: {type(parent_geoms)}")
        return None, gpd.GeoDataFrame(), all_child_polygons

    print(f"[DEBUG] Number of parent geometries: {len(parent_geom_list)}")

    # Union parents into a single geometry
    parent_geom = gpd.GeoSeries(parent_geom_list, crs=gdf.crs).union_all()
    if isinstance(parent_geom, gpd.GeoSeries):
        parent_geom = parent_geom.iloc[0]  # ensure single geometry
    print(f"[DEBUG] Unioned parent geometry created")

    # ------------------------------------------------------------------
    # 3. Optional child selection by point or name
    # ------------------------------------------------------------------
    matched_child = gpd.GeoDataFrame()
    if roid is not None:
        lat, lon = roid
        if lon is None or lat is None:
            print("[DEBUG] intersectingArea skipped: no roid")
        else:
            pt = Point(lon, lat)
            matched_child = gdf[gdf.contains(pt)]
            print(f"[DEBUG] Point selection: {len(matched_child)} match(es) found")
    elif select_child_name:
        matched_child = gdf[gdf["NAME"].apply(normalname) == normalname(select_child_name)]
        print(f"[DEBUG] Name selection: {len(matched_child)} match(es) found for '{select_child_name}'")

    # ------------------------------------------------------------------
    # 4. Intersection filtering
    # ------------------------------------------------------------------
    threshold = Overlaps.get(parent_type, 0)
    print(f"[DEBUG] Intersection threshold for {parent_type}: {threshold}")

    candidates = gdf[gdf.geometry.intersects(parent_geom)]
    print(f"[DEBUG] Candidates intersecting parent: {len(candidates)}")

    child_polygons_within_parent = candidates[
        candidates.intersection(parent_geom).area > threshold
    ]
    print(f"[DEBUG] Children within parent above threshold: {len(child_polygons_within_parent)}")

    # ------------------------------------------------------------------
    # 5. Choose selected child name
    # ------------------------------------------------------------------
    selected_child_name = None
    if not matched_child.empty:
        selected_child_name = normalname(matched_child.iloc[0]["NAME"])
        print(f"[DEBUG] Selected child via match: {selected_child_name}")
    elif not child_polygons_within_parent.empty:
        selected_child_name = normalname(child_polygons_within_parent.iloc[0]["NAME"])
        print(f"[DEBUG] Selected child via intersection: {selected_child_name}")
    elif not candidates.empty:
        selected_child_name = normalname(candidates.iloc[0]["NAME"])
        print(f"[DEBUG] Selected child via fallback: {selected_child_name}")
    else:
        print("[WARNING] No intersecting child polygons found.")
        return None, child_polygons_within_parent, all_child_polygons

    # ------------------------------------------------------------------
    # 6. Save results
    # ------------------------------------------------------------------
    if not child_polygons_within_parent.empty:
        child_polygons_within_parent.to_file(destination)
        print(f"[DEBUG] Saved {len(child_polygons_within_parent)} intersecting feature(s) to {destination}")
    else:
        print("[DEBUG] No polygons to save.")

    # ------------------------------------------------------------------
    # 7. Return
    # ------------------------------------------------------------------
    return selected_child_name, child_polygons_within_parent, all_child_polygons

def subending(filename, ending):
  stem = filename.replace(".XLSX", "@@@").replace(".CSV", "@@@").replace(".xlsx", "@@@").replace(".csv", "@@@").replace("-PRINT.html", "@@@").replace("-CAL.html", "@@@").replace("-MAP.html", "@@@").replace("-WALKS.html", "@@@").replace("-ZONES.html", "@@@").replace("-PDS.html", "@@@").replace("-DIVS.html", "@@@").replace("-WARDS.html", "@@@")
  print(f"____Subending test: from {filename} to {stem.replace('@@@', ending)}")
  return stem.replace("@@@", ending)


def combine_geodfs(existing, new):
    if existing is None or existing.empty:
        return new
    if new is None or new.empty:
        return existing
    if existing.crs != new.crs:
        new = new.to_crs(existing.crs)

    return gpd.GeoDataFrame(
        pd.concat([existing, new], ignore_index=True),
        crs=existing.crs
    )


def stepify(path):
    # turn path into steps removing directories and file ending ie 'WARDS, DIVS, PDS and WALKS'
    route = path.replace('/WALKS/','/').replace('/PDS/','/').replace('/WARDS/','/').replace('/DIVS/','/') # strip out all padding directories and file endings except -PRINT.html (leaves)
    parts = route.split("/")
    last = parts.pop() #eg KA>SMITH_STREET or BAGSHOT-MAP
    if last.find("-PRINT.html"):#only works for street-leaf nodes, not -WALKS etc nodes
        leaf = subending(last,"").split("--").pop()
        parts.append(leaf) #eg SMITH_STREET
    parts = list(dict.fromkeys(parts))
    print("____LEAFNODE:", path,parts)
    return parts

def ensure_treepolys(
    *,
    sourcepath: str | None = None,
    here: tuple[float, float] | None = None,
    estyle: str | None = None,
    ):
    """
    Load and maintain Treepolys and Fullpolys.

    Parameters
    ----------
    sourcepath : hierarchical path e.g. "UNITED_KINGDOM/ENGLAND/SURREY/GUILDFORD/ONSLOW"
    here       : (lat, lon) tuple for point-based selection
    estyle     : election territories flag ("W", "C", "B", "P", "U")
    """

    print(f"[DEBUG] ensure_treepolys | sourcepath={sourcepath} here={here} estyle={estyle}")

    steps = stepify(sourcepath) if sourcepath else []
    newpath = ""

    # ------------------------------------------------------------
    # Helper: decide whether this layer consumes a path name
    # ------------------------------------------------------------
    def path_name_for_layer(layer_key: str, level: int):
        if not sourcepath or level >= len(steps):
            return None

        # level-4 ambiguity: ward vs division
        if level == 4:
            if layer_key == "ward" and estyle in ("W", "B", "P"):
                return "/".join(steps[:5])
            if layer_key == "division" and estyle in ("C", "U"):
                return "/".join(steps[:5])
            return None

        return "/".join(steps[: level + 1])

    # ------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------
    for layer in LAYERS:
        key = layer["key"]
        level = layer["level"]

        print(f"\n[DEBUG] Processing layer: {key} (level {level})")

        # Skip if already loaded
        if layer_loaded(key):
            print(f"[DEBUG] {key} already loaded")
            pname = path_name_for_layer(key, level)
            if pname:
                name_part = pname.split("/")[-1]
                newpath = f"{newpath}/{name_part}" if newpath else name_part
            continue

        src = f"{workdirectories['bounddir']}/{layer['src']}"
        out = f"{workdirectories['bounddir']}/{layer['out']}"

        kwargs = {}

        # --- selection source ---
        pname = path_name_for_layer(key, level)
        if pname:
            kwargs["name"] = pname
        elif here:
            kwargs["roid"] = here
        elif sourcepath:
            # sourcepath exists but this layer does not consume its name
            pass
        else:
            Treepolys[key] = Fullpolys[key] = gpd.GeoDataFrame()
            continue

        # --------------------------------------------------------
        # FILTER layers
        # --------------------------------------------------------
        if layer["method"] == "filter":
            name, new_tree, new_full = filterArea(
                src,
                layer["field"],
                out,
                **kwargs
            )

            Treepolys[key] = new_tree
            Fullpolys[key] = new_full

            if name:
                newpath = f"{newpath}/{name}" if newpath else name

        # --------------------------------------------------------
        # INTERSECT layers
        # --------------------------------------------------------
        else:
            parent_key = layer["parent"]
            parent_gdf = Treepolys.get(parent_key, gpd.GeoDataFrame())
            parent_geoms = (
                list(parent_gdf.geometry)
                if hasattr(parent_gdf, "geometry")
                else []
            )

            name, new_tree, new_full = intersectingArea(
                src,
                layer["field"],
                parent_key,
                out,
                parent_geoms=parent_geoms,
                roid=here,
                select_child_name=steps[level]
                if pname and level < len(steps)
                else None,
            )

            Treepolys[key] = combine_geodfs(Treepolys.get(key), new_tree)
            Fullpolys[key] = new_full

            if pname and name:
                newpath = f"{newpath}/{name}" if newpath else name

        print(f"[DEBUG] {key} loaded | Tree size = {len(Treepolys[key])}")


    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------
    print("\n[DEBUG] Treepolys summary:")
    for k in ("country", "nation", "county", "constituency", "division", "ward"):
        print(f"  {k}: {len(Treepolys.get(k, gpd.GeoDataFrame()))}")

    return Treepolys, Fullpolys, newpath


def layer_loaded(layer_key):
    return (
        layer_key in Treepolys
        and Treepolys[layer_key] is not None
        and not Treepolys[layer_key].empty
    )


def empty_gdf():
    return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

Treepolys = {
    'country': empty_gdf(),
    'nation': empty_gdf(),
    'county': empty_gdf(),
    'constituency': empty_gdf(),
    'ward': empty_gdf(),
    'division': empty_gdf()
}

Fullpolys = {
    k: empty_gdf() for k in Treepolys
}


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
        "method": "filter",
        "parent": "country"
    },
    {
        "key": "county",
        "level": 2,
        "src": "Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson",
        "field": "CTYUA23NM",
        "out": "County_Boundaries.geojson",
        "method": "filter",
        "parent": "nation"
    },
    {
        "key": "constituency",
        "level": 3,
        "src": "Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson",
        "field": "PCON24NM",
        "out": "Constituency_Boundaries.geojson",
        "method": "intersect",
        "parent": "county"
    },
    {
        "key": "ward",
        "level": 4,
        "src": "Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson",
        "field": "WD24NM",
        "out": "Ward_Boundaries.geojson",
        "method": "intersect",
        "parent": "constituency"
    },
    {
        "key": "division",
        "level": 4,
        "src": "Surrey_Proposed_Divisions.geojson",
        "field": "Division_n",
        "out": "Division_Boundaries.geojson",
        "method": "intersect",
        "parent": "constituency"
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
"country" : 1,
"nation" : 0.1,
"county" : 0.001,
"constituency" : 0.00005,
"ward" : 0.00005,
"division" : 0.00005,
"walk" : 0.005,
"polling_district" : 0.005,
"street" : 0.005,
"walkleg" : 0.005
}



LastResults = {
    "ward": {},
    "division": {},
    "constituency": {},
}

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
