
from config import workdirectories, ELECTOR_FILE, TREKNODE_FILE, OPTIONS_FILE, ELECTOR_FILE, GENESYS_FILE, TREEPOLY_FILE, FULLPOLY_FILE
import os
import state
import json
import pandas as pd
import geopandas as gpd
import pickle
from flask import session
from flask import request, redirect, url_for, has_request_context
from layers import Featurelayers
from elections import get_election_data,get_tags_json
from folium import Map, Element
import folium
from elections import route
import uuid


levels = ['country','nation','county','constituency','ward/division','polling_district/walk','street/walkleg','elector']

from typing import Dict

Outcomes = pd.read_excel(GENESYS_FILE)
Outcols = Outcomes.columns.to_list()
allelectors = pd.DataFrame(Outcomes, columns=Outcols)
allelectors.drop(allelectors.index, inplace=True)


TREK_NODES_BY_ID: Dict[int, "TreeNode"] = {}
TREK_NODES_BY_VALUE: Dict[str, "TreeNode"] = {}

def create_root_node() -> "TreeNode":
    return TreeNode(
        value="UNITED_KINGDOM",
        fid="238",
        roid=(51.23228, -0.57630),
        origin="DEMO",
        node_type="country"
    )

def get_root() -> "TreeNode":
    """Always returns the single root node. Creates it if needed."""
    global TREK_NODES_BY_ID, TREK_NODES_BY_VALUE

    # If the root already exists, return it
    for node in TREK_NODES_BY_ID.values():
        if node.parent is None:
            return node

    # Otherwise, create the root and store it
    root = create_root_node()
    TREK_NODES_BY_ID[root.nid] = root
    TREK_NODES_BY_VALUE[root.value] = root
    return root

def first_node() -> "TreeNode":
    """Return the first inserted node, or the root if empty."""
    return next(iter(TREK_NODES_BY_ID.values()), get_root())



def parse_slot_key(slot_key):
    """
    Convert keys like '2025-04-15_9 AM' to a Python datetime object.
    """
    date_str, time_str = slot_key.split("_")
    time_str = time_str.replace(" ", "")  # "9 AM" → "9AM"

    try:
        if ":" in time_str:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M%p")
        else:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I%p")
        return dt
    except Exception as e:
        print(f"❌ Could not parse slot key {slot_key}: {e}")
        return None

def reset_nodes():
    """Clear all registered nodes (in-place)."""
    TREK_NODES_BY_ID.clear()
    TREK_NODES_BY_VALUE.clear()

def save_nodes(path):
    with open(path, "w") as f:
        json.dump(
            [n.to_dict() for n in TREK_NODES_BY_ID.values()],
            f
        )

def load_nodes(path):
    global TREK_NODES_BY_ID, TREK_NODES_BY_VALUE

    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print(f"[WARN] Node file missing or empty: {path}")
        return False

    reset_nodes()

    with open(path) as f:
        try:
            raw_nodes = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in {path}: {e}")
            return False

    # PASS 1: create nodes
    for data in raw_nodes:
        node = TreeNode.from_dict(data)
        TREK_NODES_BY_ID[node.nid] = node
        TREK_NODES_BY_VALUE[node.value] = node

    # PASS 2: wire relationships
    for data in raw_nodes:
        node = TREK_NODES_BY_ID[data["nid"]]

        pid = data.get("parent")
        if pid is not None:
            parent = TREK_NODES_BY_ID.get(pid)
            if not parent:
                raise ValueError(
                    f"Missing parent {pid} for node {node.nid} ({node.value})"
                )
            node.parent = parent

        for cid in data.get("children", []):
            child = TREK_NODES_BY_ID.get(cid)
            if not child:
                raise ValueError(
                    f"Missing child {cid} for node {node.nid} ({node.value})"
                )
            node.children.append(child)

    return True



def parent_level_for(child_type):
    """
    Returns the level index of the node you must be on
    to list children of `child_type`.
    """
    LEVEL_INDEX = {
        'country': 0,
        'nation': 1,
        'county': 2,
        'constituency': 3,
        'ward': 4,
        'division': 4,
        'polling_district': 5,
        'walk': 5,
        'street': 6,
        'walkleg': 6,
        'elector': 7
    }

    if child_type not in LEVEL_INDEX:
        raise ValueError(f"Unknown node type: {child_type}")

    child_level = LEVEL_INDEX[child_type]

    if child_level == 0:
        return None

    return child_level - 1


# want to look up the level of a type ,and the types in a level


def move_item(lst, from_index, to_index):
    """
    Move an item in the list from one index to another.

    Args:
        lst (list): The list to modify.
        from_index (int): The index of the item to move.
        to_index (int): The index to move the item to.

    Returns:
        list: The modified list with the item moved.
    """
    if not (0 <= from_index < len(lst)) or not (0 <= to_index <= len(lst)):
        raise IndexError("from_index or to_index is out of bounds")

    item = lst.pop(from_index)
    lst.insert(to_index, item)
    return lst


def get_creation_date(filepath):
    if filepath == "":
        return datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    try:
        # On Windows & Linux
        creation_time = os.path.getctime(filepath)

        # Convert timestamp to readable format
        return datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error getting creation date for {filepath}: {e}")
        return None  # Return None if the file is inaccessible

def normalname(name):
    if isinstance(name, str):
        name = name.replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(".","").replace(","," ").replace("  "," ").replace(" ","_").upper()
    elif isinstance(name, pd.Series):
        name = name.str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace("'","").str.replace(".","").str.replace(","," ").str.replace("  "," ").str.replace(" ","_").str.upper()
    else:
        print("______ERROR: Can only normalise name in a string or series")
    return name



def get_resources_json(election_data, resources):
    selectedResources = {
            k: v for k, v in resources.items()
            if k in election_data['resources']
        }
    print(f"___Resources: {selectedResources} ")

    return selectedResources




def get_places_json(markers):
    places_dict = {}
    print(f"___area markerframe {markers}")

    for entry in markers:
        print(entry['Lat'], entry['Long'], type(entry['Lat']))

        prefix = entry.get('AddressPrefix')
        if not prefix:
            continue  # skip blank prefixes

        address = f"{entry.get('Address1', '')} / {entry.get('Address2', '')}"
        postcode = entry.get('Postcode')
        lat = entry.get('Lat')
        lng = entry.get('Long')

        # Optionally warn but do NOT skip
        if lat is None or lng is None:
            print(f"⚠️ Null lat/lng for prefix {prefix}; included anyway")

        places_dict[prefix] = {
            "prefix": prefix,        # ← ✔ included here
            "address": address,
            "postcode": postcode,
            "lat": lat,
            "lng": lng
        }

    return places_dict


    # Serialize to JSON
    places_jsn = json.dumps(places_list)
    print(f"___on map create places_json {places_jsn}")
    return places_jsn


def gettypeoflevel(estyle,path,level):
# returns the correct type for nodes at a given level along a given path
# the level will give type options , which are resolved by looking at the path content
    global levels
    moretype = ""
    dest = path
    if path.find(" ") > -1:
        dest_path = path.split(" ")
        moretype = dest_path.pop() # take off any trailing parameters
        dest = dest_path[0]
    deststeps = list(state.stepify(dest)) # lowest left - UK right

    if level > 6:
        level = 6
    type = levels[level] # could have type options that need to be resolved

    if type == 'ward/division':
        if estyle == 'C' or estyle == 'U':
            type = 'division'
        else:
            type = 'ward'
    elif type == 'polling_district/walk':
        if path.find("/PDS/") >= 0 or path.endswith("-PDS.html"):
            type = 'polling_district'
        elif path.find("/WALKS/") >= 0 or path.endswith("-WALKS.html") or path.endswith("-MAP.html"):
            type = 'walk'
        elif level+1 >= len(deststeps) and moretype != "":
            print(f"____override! len child level {level} > {len(deststeps)}  so override with {moretype}")
            type = moretype # this is the type override syntax if level is new - ie desired level great than path level
        else:
            type = 'walk'
            print('XXStrange polling_district/walk Type discoveredXX')
    elif type == 'street/walkleg':
        if path.find("/PDS/") >= 0:
            type = 'street'
        elif path.find("/WALKS/") >= 0 or path.endswith("-MAP.html"):
            type = 'walkleg'
        elif level+1 >= len(deststeps) and moretype != "":
            print(f"____override! len child level {level} > {len(deststeps)}  so override with {moretype}")
            type = moretype # this is the type override syntax if level is new - ie desired level great than path level
        else:
            raise Exception('XXStrange street/walkleg Type discoveredXX')


    return type


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url,target))
    return test_url.scheme in ('http', 'https') and \
            ref_url.netloc == test_url.netloc

def get_layer_table(nodelist,title):
    from state import VNORM
    def safe_float(val, default=0.0):
        try:
            return float(val) if val is not None else default
        except:
            return default

    dfy = pd.DataFrame()
    if isinstance(nodelist, pd.DataFrame):
        dfy = nodelist
        dflev = 0
        title = f"Imported Records: {len(dfy)}"
    elif isinstance(nodelist, list) and nodelist != []:
        dfy = pd.DataFrame()
        dflev = nodelist[0].level
        i = 0
        for x in nodelist:
            dfy.loc[i,'LV'] = dflev
            dfy.loc[i,'No']= x.tagno
            VIoptions = x.VI
            for party in VIoptions:
                dfy.loc[i,party] = x.VI[party]
            if x.type == 'polling_district':
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/PDdownST/{x.dir}/{x.file}&#39;); return false;">{x.value}</a>'
            elif x.type == 'walk':
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/WKdownST/{x.dir}/{x.file}&#39;); return false;">{x.value}</a>'
            else:
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/transfer/{x.dir}/{x.file}&#39;); return false;">{x.value}</a>'
            # 1. Identify grandparent
            grandparent = x.parent.parent if x.parent else None

            # Get all sibling parents under the same grandparent
            if grandparent:
                sibling_parents = [child for child in grandparent.children if child.type == x.parent.type]
            else:
                sibling_parents = [x.parent]  # fallback

            # Generate dropdown HTML
            dropdown_html = f'<select class="parent-dropdown" data-old-value="{x.parent.value}" data-subject="{x.value}">'
            for option in sibling_parents:
                selected = 'selected' if option.value == x.parent.value else ''
                dropdown_html += f'<option value="{option.value}" {selected}>{option.value}</option>'
            dropdown_html += '</select>'

            dfy.loc[i, x.parent.type] = dropdown_html
            dfy.loc[i,'elect'] = safe_float(x.electorate)
            dfy.loc[i,'hous'] = safe_float(x.houses)
            dfy.loc[i,'turn'] = safe_float(x.turnout)
            dfy.loc[i,'gotv'] = safe_float(x.gotv)
            dfy.loc[i,'toget'] = 0
#            dfy.loc[i,'toget'] = int(((safe_float(x.electorate)*safe_float(x.turnout))/2+1)/safe_float(CurrentElection['GOTV'])) - int(x.VI.get(CurrentElection['yourparty'],0))
            i = i + 1

        # Step 1: Define numeric columns
        int_cols = ['elect', 'hous', 'toget']
        float_cols = ['turn', 'gotv']

        # Step 2: Compute totals row using only the original child rows
        totals_row = dfy.iloc[:len(nodelist)][int_cols + float_cols].sum(numeric_only=True)

        # Step 3: Format totals row
        formatted_row = {}
        for col in dfy.columns:
            if col == 'EL':  # Or another column you want to label TOTAL
                formatted_row[col] = 'TOTAL'
            elif col in int_cols:
                val = totals_row.get(col, 0)
                formatted_row[col] = str(int(val)) if pd.notna(val) else '0'
            elif col in float_cols:
                val = totals_row.get(col, 0.0)
                formatted_row[col] = f"{val:.2f}" if pd.notna(val) else '0.00'
            else:
                formatted_row[col] = ''

        # Step 4: Append totals row
        dfy = pd.concat([dfy, pd.DataFrame([formatted_row])], ignore_index=True)

        # Step 5: Convert numeric columns to formatted strings for display
        for col in int_cols:
            dfy[col] = dfy[col].apply(lambda x: str(int(x)) if pd.notna(x) and x != '' else '')
        for col in float_cols:
            dfy[col] = dfy[col].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) and x != '' else '')

        # Step 6: Fill remaining NaNs with empty strings
        dfy = dfy.fillna('')

    print("___existing get_layer_tableX", list(dfy.columns.values), dfy, title)
    return [list(dfy.columns.values), dfy, title]




def get_counters(session=None, session_data=None):
    from state import Treepolys, Fullpolys

    try:
        if not session or 'gtagno_counters' not in session:
            counters = {}
        elif not session_data or 'gtagno_counters' not in session_data:
            counters = {}
    except Exception as e:
        counters = {}
        print(f"___System error: No session or current_node: {e} ")
    """
    Returns the current node from TREK_NODES_BY_ID using either the Flask session or passed-in session_data.
    """


    if session and 'gtagno_counters' in session:
        counters = session['gtagno_counters']
        print("[Main Thread] gtagno_counters from session:", session.get('gtagno_counters',{}))
    elif session_data and 'gtagno_counters' in session_data and session_data.get('gtagno_counters',{}):
        counters = session_data['gtagno_counters']
        print("[Background Thread] gtagno_counters from session_data:", session_data.get('gtagno_counters',{}))
        counters = session_data.get('gtagno_counters',{})
    else:
        counters = {}
        node = None
        print("⚠️ gtagno_counters not found in session or session_data:so counters = ",{} )

    if counters == {}:
        for etype in Treepolys.keys():
            counters[etype] = 0
    return counters


def get_current_node(session=None, session_data=None):

    MapRoot = get_root()
    try:
        if not session or 'current_node_id' not in session:
            node = None
        elif not session_data or 'current_node_id' not in session_data:
            node = None
    except Exception as e:
        node = None
        print(f"___System error: No session or current_node: {e} ")
    """
    Returns the current node from TREK_NODES_BY_ID using either the Flask session or passed-in session_data.
    """

    if session and 'current_node_id' in session:
        current_node_id = session.get('current_node_id',None)
        print("[Main Thread] current_node_id from session:", session.get('current_node_id',"None"))
        node = TREK_NODES_BY_ID.get(current_node_id)
    elif session_data and 'current_node_id' in session_data and session_data.get('current_node_id',"None"):
        print("[Background Thread] current_node_id from session_data:", session_data.get('current_node_id',"None"))
        current_node_id = session_data.get('current_node_id',None)
        node = TREK_NODES_BY_ID.get(current_node_id)
    else:
        node = get_root()
        print("⚠️ current_node_id not found in session or session_data:so id = ",238 )

    if node == None:
        node = get_root()
        current_node_id = node.nid

        print (f" current_node_id: {current_node_id} not in TREK_NODES_BY_ID:",TREK_NODES_BY_ID)
        print("⚠️ current_node not found in stored TREK_NODES_BY_ID, so starting new MapRoot")

    return node

def atomic_pickle_dump(obj, path):
    import tempfile, os, pickle
    d = os.path.dirname(path)
    with tempfile.NamedTemporaryFile(dir=d, delete=False) as tf:
        pickle.dump(obj, tf)
        tmp = tf.name
    os.replace(tmp, path)

def safe_pickle_load(path, default):
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return default

        with open(path, "rb") as f:
            return pickle.load(f)

    except (EOFError, pickle.UnpicklingError, AttributeError, ValueError, TypeError) as e:
        print(f"❌ Pickle load failed for {path}: {e}")
        return default



def restore_from_persist(session=None,session_data=None):
    from state import Treepolys, Fullpolys
    global OPTIONS
    global CurrentElection
    global allelectors

    if  os.path.exists(OPTIONS_FILE) and os.path.getsize(OPTIONS_FILE) > 0:
        with open(OPTIONS_FILE, 'r',encoding="utf-8") as f:
            OPTIONS = json.load(f)


    if not ELECTOR_FILE or not os.path.exists(ELECTOR_FILE):
        print('_______no elector data so creating blank', ELECTOR_FILE)
        allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)
    else:
        print('_______allelectors file exists so reading in ', ELECTOR_FILE)
        allelectors = pd.read_csv(
            ELECTOR_FILE,
            sep='\t',                        # tab delimiter
            engine='python',                # Required for sep=None
            encoding='utf-8',
            keep_default_na=False,
            na_values=['']
        )

    resources = OPTIONS['resources']
    print('_______allelectors size: ', len(allelectors))
    print('_______resources: ', resources)

    if  os.path.exists(TREKNODE_FILE) and os.path.getsize(TREKNODE_FILE) > 0:
        load_nodes(TREKNODE_FILE)

    print('_______Trek Nodes: ', TREK_NODES_BY_VALUE, TREK_NODES_BY_ID)
    return

def persist(node):
    global allelectors
    from state import Treepolys, Fullpolys


    print('___persisting file ', TREEPOLY_FILE)
    atomic_pickle_dump(Treepolys,TREEPOLY_FILE)
    print('___persisting file ', FULLPOLY_FILE)
    atomic_pickle_dump(Fullpolys,FULLPOLY_FILE)

    print('___persisting file ', ELECTOR_FILE, len(allelectors))
    allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

    print('___persisting nodes ', node.value)

    return

def restore_fullpolys(node_type):

    from state import Treepolys, Fullpolys

    safe_pickle_load(TREEPOLY_FILE,Treepolys)

    safe_pickle_load(FULLPOLY_FILE,Fullpolys)

    Treepolys[node_type] = Fullpolys[node_type]

    print('___persisting file ', TREEPOLY_FILE)
    atomic_pickle_dump(Treepolys,TREEPOLY_FILE)


    return


def clean_path_part(part):
    """Clean file suffixes, or return None if ignorable/empty."""
    if part in IGNORABLE_SEGMENTS:
        return None
    for suffix in FILE_SUFFIXES:
        if part.endswith(suffix):
            return part.replace(suffix, "")
    return part

def split_clean_path(path_str):
    """Split path string and clean each segment."""
    parts = path_str.strip().split("/")
    cleaned = []
    for part in parts:
        cleaned_part = clean_path_part(part)
        if cleaned_part:
            cleaned.append(cleaned_part)
    return cleaned

def get_common_prefix_len(a, b):
    """Returns length of common prefix between lists a and b."""
    min_len = min(len(a), len(b))
    for i in range(min_len):
        if a[i] != b[i]:
            return i
    return min_len

def strip_filename_from_path(path):
    for suffix in [
        "-PRINT.html", "-MAP.html", "-CAL.html","-WALKS.html", "-ZONES.html",
        "-PDS.html", "-DIVS.html", "-WARDS.html", "-DEMO.html"
    ]:
        path = path.replace(suffix, "@@@")
    return path


# This prints a script tag you can paste into your HTML

def resolve_here_or_redirect(sourcepath, here):
    # Only read request args if a request context exists
    if has_request_context():
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        if lat is not None and lon is not None:
            here = (lat, lon)

        if sourcepath is None and here is None:
            return None, redirect(url_for("get_location"))

    return here, None


def get_last(current_election, CE):
    from state import Treepolys, Fullpolys, ensure_treepolys
    from flask import redirect

    cid = CE.get("cid")
    cidLat = CE.get("cidLat")
    cidLong = CE.get("cidLong")
    here = (cidLat, cidLong) if cidLat is not None and cidLong is not None else None
    sourcepath = CE.get("mapfiles", [None])[-1]
    estyle = CE.get("territories")

    # --- 1. CID lookup ---
    if cid and cid in TREK_NODES_BY_ID:
        last_node = TREK_NODES_BY_ID[cid]
        print("___after apply cid:", cid)
        return last_node

    print(f"___Get last Sourcepath {sourcepath} under {route()}")

    # --- 2. Resolve location or redirect ---
    here, response = resolve_here_or_redirect(sourcepath, here)
    if response:
        return response  # IMPORTANT

    # --- 3. Build tree from sourcepath / here ---
    Treepolys, Fullpolys, basepath = ensure_treepolys(
        sourcepath=sourcepath,
        estyle=estyle,
        here=here
    )

    print("___after apply basepath:", basepath)

    # --- 4. Try to resolve node from path ---
    MapRoot = get_root()

    last_node = get_root().ping_node(
        estyle,
        current_election,
        sourcepath
    )

    # --- 5. Final fallback to root ---
    if not last_node:
        print("⚠️ Falling back to root node")
        last_node = get_root()

    print(
        f"___ GET LAST - ELECTION: {current_election} "
        f"NODE {last_node.value} INVOKED AT: {here} "
        f"using source: {sourcepath}"
    )

    return last_node



def find_node_by_path(basepath: str, debug=False):
    MapRoot = get_root()
    if debug:
        print(f"[DEBUG] find_node_by_path: {basepath} on nodes of length {len(TREK_NODES_BY_ID)}")

    if not basepath:
        return None

    parts = [normalname(p) for p in basepath.strip("/").split("/") if p]
    if not parts:
        return None

    root = get_root()
    node = root

    if normalname(root.value) != parts[0]:
        if debug:
            print("[DEBUG] Root mismatch")
        return None

    for part in parts[1:]:
        if debug:
            print(f"[DEBUG] Descending to: {part}")

        matches = [c for c in node.children if normalname(c.value) == part]
        if not matches:
            if debug:
                print(f"[DEBUG] No child match for '{part}'")
            return None

        node = matches[0]

    if debug:
        print(f"[DEBUG] Found node: {node.value} ({node.nid})")

    return node


from geopy.distance import geodesic


def find_node_by_location(here):
    """
    Returns the TREK_NODES_BY_ID entry closest to the given lat/lon (here).
    """
    if not here:
        return None

    closest_node = None
    min_dist = float('inf')

    for node in TREK_NODES_BY_ID.values():
        if hasattr(node, 'latlongroid') and node.latlongroid:
            dist = geodesic(here, node.latlongroid).meters
            if dist < min_dist:
                min_dist = dist
                closest_node = node

    return closest_node




class TreeNode:
    def __init__(self, *, value, fid, roid, origin, node_type):
        self.nid = str(uuid.uuid1())
        self.value = normalname(str(value))
        self.fid = fid
        self.latlongroid = roid

        self.origin = origin
        self.election = origin

        self.type = node_type

        # Tree relations
        self.parent = None
        self.children = []

        # Electoral data
        self.electorate = None
        self.turnout = 0
        self.gotv = 0
        self.houses = 0
        self.target = 1
        self.party = "O"

        # UI
        self.tagno = 1
        self.gtagno = 1

        self.bbox = []
        self.VR = state.VIC.copy()
        self.VI = state.VIC.copy()

    def to_dict(self):
        return {
            "nid": self.nid,
            "value": self.value,
            "fid": self.fid,
            "latlongroid": self.latlongroid,
            "origin": self.origin,
            "node_type": self.type,

            "parent": self.parent.nid if self.parent else None,
            "children": [c.nid for c in self.children],

            "electorate": self.electorate,
            "turnout": self.turnout,
            "houses": self.houses,
            "target": self.target,
            "party": self.party,

            "tagno": self.tagno,
            "gtagno": self.gtagno,
            "bbox": self.bbox,
        }
    @classmethod
    def from_dict(cls, data):
        node = cls(
            value=data["value"],
            fid=data['fid'],
            roid=data["latlongroid"],
            origin=data["origin"],
            node_type=data["node_type"],
        )
        node.nid = data["nid"]  # IMPORTANT: preserve ID

        node.electorate = data["electorate"]
        node.turnout = data["turnout"]
        node.houses = data["houses"]
        node.target = data["target"]
        node.party = data["party"]
        node.tagno = data["tagno"]
        node.gtagno = data["gtagno"]
        node.bbox = data["bbox"]

        return node

    # ------------------------------
    # Computed properties
    # ------------------------------
    @property
    def level(self):
        """Compute tree level dynamically."""
        if self.parent is None:
            return 0
        return self.parent.level + 1

    @property
    def ui_col(self):
        try:
            return levelcolours["C" + str(self.level + 4)]
        except Exception:
            return "#999999"

    @property
    def col(self):
        """
        Final colour used for rendering.
        Party colour wins if available.
        """
        if hasattr(self, "party_col") and self.party_col:
            return self.party_col
        return self.ui_col

    @property
    def dir(self):
        """Compute directory path dynamically."""
        if self.parent is None:
            return self.value
        if self.type == "ward":
            return f"{self.parent.dir}/WARDS/{self.value}"
        elif self.type == "division":
            return f"{self.parent.dir}/DIVS/{self.value}"
        elif self.type == "polling_district":
            return f"{self.parent.dir}/PDS/{self.value}"
        elif self.type == "walk":
            return f"{self.parent.dir}/WALKS/{self.value}"
        else:
            return f"{self.parent.dir}/{self.value}"

    @property
    def file(self):
        """Compute map filename dynamically."""
        FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
        return f"{self.value}{FACEENDING[self.type]}"


    def layer_mapfile(self, estyle):
        if estyle in ("C", "U"):  # divisions
            return f"{self.dir}/DIVS/{self.value}-DIVS.html"
        elif estyle in ("B", "P", "W"):  # wards
            return f"{self.dir}/WARDS/{self.value}-WARDS.html"
        else:
            return self.mapfile()


    def set_parent(self, parent):
        if self.parent is parent:
            return

        # Remove from old parent
        if self.parent:
            self.parent.children.remove(self)

        self.parent = parent
        parent.children.append(self)
        save_nodes(TREKNODE_FILE)  # persists TREK_NODES_BY_ID and relationships



    def __repr__(self):
        return f"<TNode {self.value} L{self.level} {self.origin}>"


    def get_areas(self):
        """
        Returns a nested dictionary of areas grouped by their immediate children (regions).

        Example output:
        {
            "North Region": { "A1": "North Area 1", "A2": "North Area 2" },
            "South Region": { "B1": "South Area 1" }
        }
        """
        area_groups = {}

        if not self.children:
            return {}

        for child in self.children:  # top-level regions
            # Map grandchildren (areas) as fid -> name
            areas = {grand.nid: grand.value for grand in child.children} if child.children else {}
            area_groups[child.value] = areas

        return area_groups


    def process_lozenges(self,lozenges, CE):
        """
        Convert lozenges from calendar slots into readable forms.
        """

        resources = []
        tasks = []
        places = []
        areas = []


        CE_resources = OPTIONS['resources']
        CE_task_tags, CE_outcome_tags = get_tags_json(CE['tags'])
        CE_areas = self.get_areas()
        CE_places = CE.get("places", {})
        print(f"___Processing resources : {CE_resources} CE_task_tags : {CE_task_tags} CE_outcome_tags : {CE_outcome_tags} CE_areas : {CE_areas} CE_places : {CE_places}")
        for loz in lozenges:
            ltype = loz.get("type")
            code = loz.get("code")

            # AREA ---------------
            if ltype == "area" and code in CE_areas:
                areas.append(CE_areas[code])

            # RESOURCES ----------
            elif ltype == "resource" and code in CE_resources:
                resources.append(CE_resources[code])

            # TASKS --------------
            elif ltype == "task" and code in CE_task_tags:
                tasks.append(CE_task_tags[code])

            # PLACES -------------
            elif ltype == "place" and code in CE_places:
                places.append({
                    "code": code,
                    "prefix": CE_places[code].get("AddressPrefix"),
                    "lat": CE_places[code].get("Lat"),
                    "lng": CE_places[code].get("Long"),
                    "url": CE_places[code].get("url")
                })


        return resources, tasks, places, areas



    def build_eventlist_dataframe(self,c_election):
        """
        Produce an eventlist dataframe matching the intent of the JS summary.
        """
        CurrentElection = get_election_data(c_election)

        slots = CurrentElection["calendar_plan"]["slots"]
        rows = []
        print("__Building events from slots:",slots)
        for key, slot in slots.items():
            dt = parse_slot_key(key)
            if not dt:
                print(f"⚠️ Skipping slot with invalid datetime key: {key}")
                continue

            resources, tasks, places, areas = self.process_lozenges(
                slot.get("lozenges", []),
                CurrentElection
            )

            if not places:
                continue

            rows.append({
                "datetime": dt,
                "date": dt.date(),
                "time": dt.time(),
                "resources": resources,
                "tasks": tasks,
                "places": places,
                "areas": areas,
                "availability": slot.get("availability"),
                "raw_key": key,
                "lozenges": slot.get("lozenges", [])
            })


        df = pd.DataFrame(rows, columns=["datetime",
                    "date",
                    "time",
                    "resources",
                    "tasks",
                    "places",
                    "areas",
                    "availability",
                    "raw_key",
                    "lozenges"])
        df.sort_values("datetime", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def renumber(self, etype):
        # Filter only children of the matching type
        nodelist = [x for x in self.children if x.type == etype]

        # Proper enumerated loop
        for i, child_node in enumerate(nodelist, start=1):
            child_node.tagno = i

        return


    def upto(self,deststeps):
        node = self
        while node.value not in deststeps:
            if node.level == 0:
                break
            else:
                node = node.parent
        return node

    def mapfile(self):
        return self.dir+"/"+self.file



    def ping_node(self, estyle, c_election, dest_path):
        from state import Treepolys, Fullpolys,LEVEL_ZOOM_MAP

        global levels
        global allelectors
        global areaelectors
        global CurrentElection
        global SERVER_PASSWORD
        global OPTIONS



        def strip_leaf_from_path(path):
            leaf = path.split("/")[-1]
            for suffix in [
                "-PRINT.html", "-MAP.html", "-CAL.html","-WALKS.html", "-ZONES.html",
                "-PDS.html", "-DIVS.html", "-WARDS.html", "-DEMO.html"
            ]:
                if leaf.endswith(suffix):
                    leaf = leaf.replace(suffix, "")
            # In case the leaf has parts like "prefix--name", we take the last part
            leaf = leaf.split("--")[-1]
            return leaf

        def split_clean_path(path):
            # Get the leaf and remove suffixes
            leaf = strip_leaf_from_path(path)

            # Get the directory part (excluding the original filename)
            dir_path = "/".join(path.strip("/").split("/")[:-1])

            # Split and clean the directory path
            parts = [
                part for part in dir_path.strip("/").split("/")
                if part not in ["DIVS", "PDS", "WALKS", "WARDS", ""] and "@@@" not in part
            ]

            # Add leaf only if it's not already in parts and is valid
            if leaf and leaf not in ["DIVS", "PDS", "WALKS", "WARDS"] and leaf not in parts:
                parts.append(leaf)

            return parts


        """
        Find and return the node in the tree corresponding to dest_path,
        starting from any node in the tree (self).

        dest_path: string with path (and optional keyword after a space)
        c_election: passed into branch-creation functions
        """

        # Step 0: Handle optional keyword (e.g., "ward", "division" etc.)
        # Full destination path
        full_dest_path = dest_path.strip()

        # ✅ Split out the keyword, but keep the full original for gettypeoflevel()
        path_only, *keyword_parts = full_dest_path.rsplit(" ", 1)

        # If there's a keyword, extract it and restore full_path with keyword for later
        if keyword_parts and keyword_parts[0].lower() in LEVEL_ZOOM_MAP:
            keyword = keyword_parts[0].lower()
            raw_path_for_types = full_dest_path  # ✅ Keep keyword included for gettypeoflevel()
            path_str = path_only                 # ✅ Path for traversal only (no keyword)
        else:
            keyword = None
            raw_path_for_types = full_dest_path  # No keyword, use entire path
            path_str = full_dest_path


        # Clean paths
        self_path = split_clean_path(self.mapfile())
        dest_path_parts = split_clean_path(path_str)

        print(f"   🪜 under {route()} self_path: {self_path}")
        print(f"   🪜 under {route()} dest_path_parts: {dest_path_parts}")

        # Step 2: Find common ancestor
        common_len = get_common_prefix_len(self_path, dest_path_parts)
        print(f"   🔗 Common prefix length: {common_len}")

        # Step 3: Move up to the common ancestor

        node = self
        print(f"   📏 self_path length: {len(self_path)}")
        print(f"   📏 common_len: {common_len}")
        print(f"   📏 Steps to move up: {len(self_path) - common_len}")
        for i in range(len(self_path) - common_len):
            if not hasattr(node, "parent") or node.parent is None:
                print(f"   ⛔️ Reached root or missing parent at node: {node.value}")
                break
            node = node.parent
            print(f"   🔼 Moved up to: {node.value} (level {node.level})")

        # Step 4: Move down from common ancestor
        down_path = dest_path_parts[common_len:]
        print(f"   ⬇️ Moving down path: {down_path}")

        for part in down_path:
            next_level = node.level + 1
            ntype = gettypeoflevel(estyle, raw_path_for_types, next_level)

            print(f"   ➡️ under {route()} Looking for part: '{part}' at next level {next_level} (ntype={ntype})")

            # Expand children dynamically
            if next_level <= 4:
                print(f"      🛠 create_map_branch({ntype})")
                node.create_map_branch(estyle,c_election, ntype)
            elif next_level <= 6:
                print(f"      🛠 create_data_branch for election {c_election}({ntype})")
                node.create_data_branch(estyle,c_election, ntype)

            # Try to find a matching child
            matches = [child for child in node.children if child.value == part]
            if not matches:
                print(f"   ❌ under {route()} No match for '{part}' in node '{node.value}' children. Returning original node: {self.value}")
                print(f"   ❌ children of self:{[x.value for x in self.children]}")
                return self

            node = matches[0]
            print(f"   ✅ under {route()} Descended to: {node.value} (level {node.level})")

        # Step 5: Handle optional zoom keyword
        if keyword in LEVEL_ZOOM_MAP:
            node.zoom_level = LEVEL_ZOOM_MAP[keyword]
            print(f"   🔍 Set zoom level to {node.zoom_level} due to keyword '{keyword}'")

        print(f"✅ under {route()} Reached destination node: {node.value} (level {node.level})")
        # Step 6: Populate children of destination node
        final_level = node.level
        final_ntype = gettypeoflevel(estyle, raw_path_for_types, final_level + 1)

        print(f"   🌿 Expanding children of path {raw_path_for_types} final node '{node.value}' (level {final_level}) with type '{final_ntype}'")

        try:
            if final_level < 4:
                node.create_map_branch(estyle,c_election, final_ntype)
                print("   ✅ create_map_branch() called")
            elif final_level < 6:
                node.create_data_branch(estyle,c_election, final_ntype)
                print(f"   ✅ create_data_branch() called for {c_election}({final_ntype})")
            else:
                print("   ℹ️ No further branching at this level.")
        except Exception as e:
            print(f"   ⚠️ Failed to create child branches: {e}")


        print(f"   ✅ Descended to: {node.value} (level {node.level}) children: {len(node.children)}")
        if final_ntype == 'street' or final_ntype == 'walkleg':
            leaf = strip_leaf_from_path(raw_path_for_types)
            leafmatches = [child for child in node.children if child.value == leaf]
            if not leafmatches:
                print(f"   ❌ No match for leaf '{leaf}' under node '{node.value}'. Returning original node: {node.value}")
                return node
            node = leafmatches[0]

        return node


    def getselectedlayers(self,estyle,this_election,path):
        global Featurelayers
        global OPTIONS
#add children layer(level+1), eg wards,constituencies, counties
        print(f"_____layerstest0 type:{self.value},{self.type} path: {path}")

        selected = []
        childtype = gettypeoflevel(estyle,path,self.level+1)
        if childtype == 'elector':
            selected = []
        else:
            selectc = Featurelayers[childtype]
            selectc.show = True
            selected = [selectc]
            print(f"_____layerstest1 {self.value} layertype: {childtype} size: {len(selectc._children)} areas html:{OPTIONS['areas']}")
        if self.level > 0 :
#add siblings layer = self.level eg constituencies
    #        if len(selects._children) == 0:
            # parent children = siblings, eg constituencies, counties, nations
            print(f"_____layerstest20 {self.parent.value} lev:{self.level} type:{self.type} layers: {list(reversed(selected))}")
            Featurelayers[self.type].create_layer(this_election,self.parent,self.type)
            selected.append(Featurelayers[self.type])
            print(f"_____layerstest2 {self.parent.value} layertype: {self.type} areashtml2:{OPTIONS['areas']}")
        if self.level > 1:
#add parents layer, eg counties, nations, country
#            if len(selectp._children) == 0:
            print(f"_____layerstest30 {self.parent.parent.value} type:{self.parent.type} layers: {list(reversed(selected))}")
            Featurelayers[self.parent.type].create_layer(this_election,self.parent.parent,self.parent.type)
            selected.append(Featurelayers[self.parent.type])
            print(f"_____layerstest3 {self.parent.parent.value} layertype: {self.parent.type} areashtml3:{OPTIONS['areas']}")

        print(f"_____layerstest40 {self.findnodeat_Level(2).value} markers layers: {list(reversed(selected))}")
        markerlayer = Featurelayers['marker']
        print(f"_____layerstest401 {markerlayer} markers layers: {list(reversed(selected))}")
        selected.append(markerlayer)
        print(f"_____layerstest4 {self.findnodeat_Level(2).value} - len {len(markerlayer._children)} markers layers: {list(reversed(selected))}")
        return list(reversed(selected))


    def updateVI(self,viValue):
        origin = self
        if self.type == 'street' or self.type == 'walkleg':
            sumnode = origin
            for x in range(origin.level+1):
                sumnode.VI[viValue] = sumnode.VI[viValue] + 1
                print ("_____VInode:",sumnode.value,sumnode.level,sumnode.VI)
                sumnode = sumnode.parent
        self = origin
        print ("_____VIstatus:",self.value,self.type,self.VI)
        return

    def updateVR(self,vrValue):
        origin = self
        if self.type == 'street' or self.type == 'walkleg':
            sumnode = origin
            sumnode.VR[vrValue] = sumnode.VR[vrValue] + 1
#            print ("_____VRnode:",sumnode.value,sumnode.level,sumnode.VR)
        self = origin
#        print ("_____VRstatus:",self.value,self.type,self.VR)
        return

    def updateTurnout(self,electionstyle):
        from state import LastResults

        sname = self.value
        casnode = self

        # --- Base turnout assignment ---
        if electionstyle == "W":  # national
            if self.level == 3:
                entry = LastResults.get("constituency", {}).get(sname)
                self.turnout = entry.get("TURNOUT") if entry else None
            elif self.level > 3:
                self.turnout = self.parent.turnout

        else:  # local
            if self.level == 4:
                entry = LastResults.get("ward", {}).get(sname)
                self.turnout = entry.get("TURNOUT") if entry else None
            elif self.level > 4:
                self.turnout = self.parent.turnout

        # --- Cascade upward (compute parents from children) ---
        while casnode.parent:
            parent = casnode.parent
            children = parent.childrenoftype(
                gettypeoflevel(electionstyle, casnode.dir, casnode.level)
            )

            values = [c.turnout for c in children if c.turnout is not None]
            parent.turnout = sum(values) / len(values) if values else None

            casnode = parent

        return

    def updateGOTV(self, gotv_pct):
        """
        Compute absolute GOTV target:
            gotv = 0.5 * votes_cast + (gotv_pct / 100)
        """

        casnode = self

        # --- Base GOTV assignment ---
        if (
            self.turnout is not None
            and self.electorate is not None
            and gotv_pct is not None
        ):
            votes_cast = self.electorate * (self.turnout / 100.0)
            self.gotv = (0.5 * votes_cast) + (gotv_pct / 100.0)
        else:
            self.gotv = None

        # --- Cascade upward (sum children) ---
        while casnode.parent:
            parent = casnode.parent
            children = parent.children

            values = [c.gotv for c in children if c.gotv is not None]
            parent.gotv = sum(values) if values else None

            casnode = parent


    def updateParty(self):
        from state import VNORM, VCO, LastResults

        sname = self.value
        dname = sname.removesuffix("_ED")

        party = "OTHER"

        try:
            party = LastResults.get(self.type, {}).get(sname, {}).get("FIRST", "OTHER")
        except Exception:
            party = "OTHER"

        party = normalname(party)

        if party not in VNORM:
            party = "OTHER"

        party2 = VNORM[party]
        self.party = party2

        print(
            "______VNORM:",
            self.type,
            self.party,
            self.parent.value,
            self.parent.childrenoftype("walk"),
        )

        print(
            "_______Electorate:",
            self.value,
            self.electorate,
            self.houses,
        )
        return


    def updateElectorate(self, electstyle):
        from state import LastResults

        # --- Base electorate ---
        if self.level == 3:
            # Level 3: take from LastResults directly
            entry = LastResults.get(self.type, {}).get(self.value)
            self.electorate = entry.get("ELECTORATE", 0) if entry else 0
        elif self.level > 3:
            # Level > 3: sum children, treating missing as 0
            self.electorate = sum(c.electorate if c.electorate is not None else 0 for c in self.children)
        else:
            # Other levels: fallback
            self.electorate = sum(c.electorate if c.electorate is not None else 0 for c in self.children)

        # --- Aggregate upward through parents (skip level 3 parents) ---
        casnode = self
        while casnode.parent:
            parent = casnode.parent
            if parent.level != 3:
                parent.electorate = sum(
                    c.electorate if c.electorate is not None else 0
                    for c in parent.children
                )
            casnode = parent

        return

    def updateHouses(self,pop):

        sname = self.value
        pop = int(pop)

        origin = self
        sumnode = origin
        sumnode.houses = pop
# electorate is for a constituency is derived from wards is derived from streets (if you have electoral roll uploaded )
# turnover is fixed for constituency(National) or wards(non-National) - streets inherit from either wards or constituency depending on election type - in set up
        for l in range(origin.level):
            sumnode.parent.houses = 0
            i=1
            for x in sumnode.parent.childrenoftype(gettypeoflevel(estyle,sumnode.dir,sumnode.level)):
                sumnode.parent.houses = sumnode.parent.houses + x.houses
                print ("_____Houseslevel:",x.level,x.value,x.houses,sumnode.houses)
                i = i+1
            sumnode = sumnode.parent
            self = origin

        print ("_____OriginHouses:",self.findnodeat_Level(0).houses,self.value,self.type,self.houses)
        return

    def childrenoftype(self,electtype):
        typechildren = [x for x in self.children if x.type == electtype]
        print(f"__we have {len(typechildren)} children of type {electtype} for node:{self.value} at level {self.level} out of: {len(typechildren)} available here {[x.value for x in self.children]} ")
        return typechildren


    def locfilepath(self,file_text):
        global levelcolours

        target = workdirectories['workdir'] + self.dir + "/" + file_text

        dir = os.path.dirname(target)
        print(f"____target director {dir} and filename:{file_text}")
        os.chdir(workdirectories['workdir'])
        if not os.path.exists(dir):
          os.makedirs(dir)
          print("_______Folder %s created!" % dir)
          os.chdir(dir)
        else:
          print("________Folder %s already exists" % dir)
          os.chdir(dir)
        return target

    def create_name_nodes(self,electstyle,gotv_pct,elect,nodetype,namepoints,ending):
        zonecolour = {
            "ZONE_0": "black", "ZONE_1": "red", "ZONE_2": "lime",
            "ZONE_3": "blue", "ZONE_4": "yellow", "ZONE_5": "cyan",
            "ZONE_6": "magenta", "ZONE_7": "orange", "ZONE_8": "purple",
            "ZONE_9": "brown", "ZONE_10": "gray"
        }

        counters = get_counters(session)

        fam_nodes = []
        if namepoints.empty:
            raise ValueError("No data in namepoints DataFrame.")
        print(f"____Namepoints nodes: at {self.value} of type:{nodetype} there are {len(namepoints)} in fileending{ending}")
        geometry = gpd.points_from_xy(namepoints.Long.values,namepoints.Lat.values, crs="EPSG:4326")
        block = gpd.GeoDataFrame(
            namepoints, geometry=geometry
            )
        fam_nodes = self.childrenoftype(nodetype)
        [self.bbox, self.latlongroid] = self.get_bounding_box(self.type,block)

        if 'Zone' not in namepoints.columns:
            print("⚠️ 'Zone' column missing from namepoints. Defaulting all nodes to black.", namepoints.columns)
            namepoints['Zone'] = 'ZONE_0'  # or whatever default you want


        for index, limb  in namepoints.iterrows():

            if not TREK_NODES_BY_VALUE.get(limb['Name']) :
                datafid = abs(hash(limb['Name']))
                newnode = TreeNode(value=normalname(limb['Name']),fid=datafid, roid=(limb['Lat'],limb['Long']),origin=elect, node_type=nodetype )
                egg = self.add_Tchild(child_node=newnode,etype=nodetype, elect=elect,counters=counters)
                [egg.bbox, centroid] = egg.get_bounding_box(nodetype,block)
                egg.col = zonecolour.get(limb['Zone'],'black')
                print(f"🎨 Assigned color '{egg.col}' to walk_node '{egg.value}' for zone '{limb['Zone']}'")

                egg.updateTurnout(electstyle)
                egg.updateElectorate(electstyle)
                egg.updateGOTV(gotv_pct)
                print('______Data nodes',egg.value,egg.fid, egg.electorate,egg.houses,egg.target,egg.bbox)

                fam_nodes.append(egg)

    #    self.aggTarget()
        print('______Create Namepoints :',nodetype,namepoints)
        print('______Create Nodelist :',nodetype,[(x.value,x.type) for x in fam_nodes])

        return fam_nodes

    def findnodeat_Level(self,target_level):
        node = self
        if node.level >= target_level:
            while True:
                if node.level == target_level:
                    break
                node = node.parent

        return node


    def create_data_branch(self,electstyle,c_election, electtype):
        global allelectors
        global areaelectors
        global workdirectories
        from state import Treepolys, Fullpolys
        from elections import get_election_data


# if called from within ping, then this module should aim to return the next level of nodes of selected type underneath self.
# the new data namepoints must be derived from the electoral file - name is stored in session['importfile']
# if the electoral file hasn't been loaded yet then that needs to be done first.

        nodelist = []


        if not ELECTOR_FILE or not os.path.exists(ELECTOR_FILE):
            print('_______Redirect to upload_form', ELECTOR_FILE)
            flash("Please upload a file or provide the name of the electoral roll file.", "error")
            return nodelist

        Outcomes = pd.read_excel(GENESYS_FILE)
        Outcols = Outcomes.columns.to_list()

        allelectors = pd.DataFrame(allelectors, columns=Outcols)

# this section is common after data has been loaded: get filter area from node, PDs from data and the test if in area

        mask = (
            (allelectors['Election'] == c_election) &
            (allelectors['Area'] == self.value)
            )
        areaelectors = allelectors[mask]

        CE = get_election_data(c_election)
        gotv_pct = CE['GOTV']
        if len(areaelectors) > 0:
            try:
    #            allelectors.loc[areaelectors.index, "Area"] = areaelectors["Area"]
                allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

        # so all data is now loaded and we are able to filter by PDs(L5) , walks(L5), streets(L6), walklegs(L6)

        # already have data so node is ward/division level children should be PDs or Walks
                if electtype == 'polling_district':
                    PDPtsdf0 = pd.DataFrame(areaelectors, columns=['Election','PD', 'ENOP','Long', 'Lat', 'Zone'])
                    PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
        # we group electors by each polling_district, calculating mean lat , long for PD centroids and population of each PD for self.electorate
                    g = {'Election':'first','Lat':'mean','Long':'mean', 'ENOP':'count', 'Zone':'first'}
                    PDPtsdf = PDPtsdf1.groupby(['Name']).agg(g).reset_index()
                    nodelist = self.create_name_nodes(electstyle,gotv_pct,c_election,'polling_district',PDPtsdf,"-PDS.html") #creating PD_nodes with mean PD pos and elector counts
                elif electtype == 'walk':
                    print("📦 Starting WALK processing")
                    walkdf0 = pd.DataFrame(areaelectors, columns=['Election', 'WalkName', 'ENOP', 'Long', 'Lat', 'Zone'])
                    print(f"📊 walkdf0 created with {len(walkdf0)} rows")
                    unique_walks = areaelectors['WalkName'].unique()
                    print(f"Unique walk names ({len(unique_walks)}): {unique_walks}")

                    walkdf1 = walkdf0.rename(columns={'WalkName': 'Name'})
                    print("📛 Renamed 'WalkName' to 'Name' in walkdf1")

                    g = {'Election': 'first', 'Lat': 'mean', 'Long': 'mean', 'ENOP': 'count', 'Zone': 'first'}
                    nodeelectors = walkdf1.groupby(['Name']).agg(g).reset_index()
                    print(f"📈 Grouped nodeelectors shape: {nodeelectors.shape}")

                    nodelist = self.create_name_nodes(electstyle, gotv_pct,c_election, 'walk', nodeelectors, "-WALKS.html")
                    print(f"🧩 Created {len(nodelist)} walk nodes")

    #---------------------------------------------------
                elif electtype == 'street':
                    mask = areaelectors['PD'] == self.value
                    PDelectors = areaelectors[mask]
        #            StreetPts = [(x[0],x[1],x[2],x[3]) for x in PDelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                    streetdf0 = pd.DataFrame(PDelectors, columns=['Election','StreetName','ENOP', 'Long', 'Lat', 'Zone'])
                    streetdf1 = streetdf0.rename(columns= {'StreetName': 'Name'})
                    g = {'Election':'first','Lat':'mean','Long':'mean', 'ENOP':'count','Zone': 'first'}
                    streetdf = streetdf1.groupby(['Name']).agg(g).reset_index()
                    print("____Street df: ",streetdf)
                    nodelist = self.create_name_nodes(electstyle,gotv_pct,c_election,'street',streetdf,"-PRINT.html") #creating street_nodes with mean street pos and elector counts
                elif electtype == 'walkleg':
                    mask = areaelectors['WalkName'] == self.value
                    walkelectors = areaelectors[mask]
    #                WalklegPts = [(x[0],x[1],x[2],x[3]) for x in walkelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                    walklegdf0 = pd.DataFrame(walkelectors, columns=['Election','StreetName','ENOP', 'Long', 'Lat', 'Zone'])
                    walklegdf1 = walklegdf0.rename(columns= {'StreetName': 'Name'})
                    g = {'Election':'first','Lat':'mean','Long':'mean','ENOP':'count','Zone': 'first'}
                    walklegdf = walklegdf1.groupby(['Name']).agg(g).reset_index()
                    print("____Walkleg df: ",walklegdf)
                    print("____Walkleg elector df: ",walklegdf1)
                    nodelist = self.create_name_nodes(electstyle,gotv_pct,c_election,'walkleg',walklegdf,"-PRINT.html") #creating walkleg_nodes with mean street pos and elector counts
            except Exception as e:
                print("❌ Error during data branch generation:", e)
                return []
        else:
            print(f"_____ Electoral file contains no  data for election {c_election} and {self.value} for {electtype} types - Please load correct file",len(allelectors), len(areaelectors))

            nodelist = []
        print(f"____Created Data Branch for Election: {c_election} in area: {self.value} creating: {len(nodelist)} of child type {electtype} from: {len(allelectors)} - {len(areaelectors)} electors")

        save_nodes(TREKNODE_FILE)
        return nodelist

    def create_map_branch(self,electstyle,c_election,electtype):
        from state import Treepolys, Fullpolys, Overlaps
        import random
        from elections import get_election_data


        def newFid(existing_fids):
            """
            Generate a new unique integer FID not in existing_fids.
            Uses random integers in a large range.
            """
            existing_set = set(existing_fids)  # for fast lookup
            while True:
                fid = random.randint(1, 2**31 - 1)  # large positive integer
                if fid not in existing_set:
                    return fid


# need to know the CE['territories'] value to determine division or ward
        # NOW THIS IS SAFE
        parent_poly = Treepolys[self.type]

        print(
            f"🧭 create_map_branch({self.type}) polys loaded:",
            parent_poly is not None and not parent_poly.empty
        )

        # existing logic continues...

        counters = get_counters(session)
        CE = get_election_data(c_election)
        gotv_pct = CE['GOTV']
        block = pd.DataFrame()


        # Filter the parent geometry based on the FID
        parent_geom = parent_poly[parent_poly['FID'] == int(self.fid)]


        # If no matching geometry is found, handle the case where parent_geom is empty
        if parent_geom.empty:
            print(f"Adding back in Full '{self.type}' boundaries for {self.value} FID {self.fid}")
            raise Exception ("EMPTY COUNTRY PARENT GEOMETRY")
            restore_fullpolys(self.type)
            parent_poly = Treepolys[self.type]
            print(
                f"full map branch type: {self.type} "
                f"size {len(parent_poly)} "
                f"parent poly cols: {list(parent_poly.columns)} "
                f"NID {self.nid}"
            )

            parent_geom = parent_poly[parent_poly['FID'] == int(self.fid)]
            # Ensure that parent_geom has the desired geometry after the update
            if parent_geom.empty:
                print(f"Still no matching geometry found after adding new polygon for FID {self.fid}")
            else:
                parent_geom = parent_geom.geometry.values[0]
        else:
            print(f"___create_map_branch geometry for {self.value} FID {self.fid} is ",parent_geom)
            print(
                f"map branch type: {self.type} "
                f"size {len(parent_poly)} "
                f"parent poly cols: {list(parent_poly.columns)} "
                f"NID {self.nid}"
            )
            # If geometry was found, proceed with the matching geometry
            parent_geom = parent_geom.geometry.values[0]
        [self.bbox, self.latlongroid] = self.get_bounding_box(self.type,block)

        ChildPolylayer = Treepolys[electtype]

        print(f"____There are {len(ChildPolylayer)} Children candidates for {self.value} bbox:[{self.bbox}] of type {electtype}" )
        index = 0
        i = 0
        j = 0
        fam_nodes = self.childrenoftype(electtype)

        for index,limb in ChildPolylayer.iterrows():
            print(f"____Considering inclusion of child {limb.NAME} in Parent geometry of branch")
            fam_values = [x.value for x in fam_nodes]

            newname = normalname(limb.NAME)
            centroid_point = limb.geometry.centroid
            here = (centroid_point.y, centroid_point.x)
            overlaparea = parent_geom.intersection(limb.geometry).area
            Overlaps[electtype] = round(Overlaps[electtype], 8)  # 6 decimal places
            print (f"________trying map type {electtype} name {newname} names {fam_values} level+1 {self.level+1} area {overlaparea} margin {Overlaps[electtype]}" )
#            if parent_geom.intersects(limb.geometry) and parent_geom.intersection(limb.geometry).area > 0.0001:
            if overlaparea > Overlaps[electtype] and not TREK_NODES_BY_VALUE.get(newname) :
# if name is already in treknodes ignore
                egg = TreeNode(value=newname, fid=limb.FID, roid=here,origin="ONS_MAPS",node_type=electtype)
#                else:
#                    egg = TreeNode(newname, newFid(fam_fids), here,self.level+1,c_election)
                print (f"________found missing type {electtype} name {newname} names {fam_values} level+1 {self.level+1} area {overlaparea} margin {Overlaps[electtype]}" )
                egg = self.add_Tchild(child_node=egg,etype=electtype, elect=c_election,counters=counters)
                [egg.bbox, centroid] = egg.get_bounding_box(electtype,block)
                print (f"________bbox [{egg.bbox}] - child of type:{electtype} at lev {self.level+1} of {self.value}")
                fam_nodes.append(egg)
                egg.updateParty() # get the last recorded election result for this node
                egg.updateTurnout(electstyle) # get the last recorded election turnout for this node
                egg.updateElectorate(electstyle) # get the current electorate for this node
                egg.updateGOTV(gotv_pct)
                print (f"______Eggname: {egg.value} type {egg.type} level {egg.level} party {egg.party} " )
                j = j + 1
            i = i + 1


        if len(fam_nodes) == 0:
            print (f"________Xno children of type:{electtype} at lev {self.level+1} for {self.value}")

        print (f"___ at {self.value} lev {self.level} revised {electtype} type fam nodes:{fam_nodes}")

        print ("_________fam_nodes :",j," of ", i, [x.value for x in fam_nodes] )

        save_nodes(TREKNODE_FILE)
        return fam_nodes




    def create_area_map(self, flayers, CE, CEdata):
        global SERVER_PASSWORD
        global STATICSWITCH
        global OPTIONS

        from folium import IFrame
        from state import LEVEL_ZOOM_MAP




        print(f"___BEFORE cal creation: in route {route()} creating cal for: ", self.value)

        print(f"___BEFORE map creation: in route {route()} creating file: ", self.file)

        import hashlib
        import re
        from pathlib import Path




        # --- CSS to adjust popup styling
        move_close_button_css = """
            <style>
            .leaflet-popup-close-button {
                right: auto !important;
                left: 10px !important;
                top: 10px !important;
                font-size: 16px;
                color: #444;
                background: rgba(255, 255, 255, 0.8);
                border-radius: 4px;
                padding: 2px 5px;
            }
            </style>
            """

        # --- Search bar with map detection and one single searchMap() function
        search_bar_html = """
            <style>
            #customSearchBox {
                position: fixed;
                top: 60px;
                left: 100px;
                z-index: 1100;
                background: white;
                padding: 5px;
                border: 1px solid #ccc;
                font-size: 14px;
                display: flex;
                gap: 8px;
                align-items: center;
            }
            #customSearchBox input {
                padding: 4px 6px;
                font-size: 14px;
            }
            #customSearchBox button {
                padding: 4px 8px;
                font-size: 14px;
                cursor: pointer;
            }

            /* Change cursor to crosshair when in add-place mode */
            .leaflet-container.add-place-mode {
                cursor: crosshair;
            }


            </style>


            <div id="customSearchBox">
                <input type="text" id="searchInput" placeholder="Search..." />
                <button onclick="searchMap()">Search</button>
                <button id="backToCalendarBtn">📅 Calendar</button>
            </div>

            <script>


            document.addEventListener("DOMContentLoaded", function () {


                function waitForMap() {
                    for (const key in window) {
                        if (window.hasOwnProperty(key)) {
                            const val = window[key];
                            if (val && val instanceof L.Map) {
                                window.fmap = val;  // assign fmap here
                                return;
                            }
                        }
                    }
                    setTimeout(waitForMap, 100);
                }

                waitForMap();


            });

            document.getElementById("backToCalendarBtn").addEventListener("click", () => {
                console.log("📤 Sending back-to-calendar message to parent");

                window.parent.postMessage(
                    { type: "toggleView" },
                    "*"
                );
            });

            function extractVisibleText(element) {
                const walker = document.createTreeWalker(
                    element,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function (node) {
                            const parent = node.parentNode;
                            const style = window.getComputedStyle(parent);
                            if (style && style.visibility !== 'hidden' && style.display !== 'none') {
                                return NodeFilter.FILTER_ACCEPT;
                            }
                            return NodeFilter.FILTER_REJECT;
                        }
                    }
                );

                let visibleText = '';
                while (walker.nextNode()) {
                    visibleText += walker.currentNode.nodeValue + ' ';
                }
                return visibleText.trim();
            }

            async function searchMap() {
                const query = document.getElementById("searchInput").value.trim();
                if (!query) return;

                // --- 1️⃣ Check if query looks like a UK postcode ---
                const postcodePattern = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;
                if (postcodePattern.test(query)) {
                    const cleanPostcode = query.replace(/\s+/g, '');
                    const url = `http://api.getthedata.com/postcode/${cleanPostcode}`;
                    try {
                        const res = await fetch(url);
                        if (!res.ok) throw new Error("Network error");
                        const data = await res.json();

                        if (data.status === "match" && data.data) {
                            const { latitude, longitude } = data.data;
                            fmap.setView([latitude, longitude], 17);

                            L.marker([latitude, longitude])
                                .addTo(fmap)
                                .bindPopup(`<b>${query.toUpperCase()}</b><br>Lat: ${latitude.toFixed(5)}, Lon: ${longitude.toFixed(5)}`)
                                .openPopup();
                            return;
                        } else {
                            alert("Postcode not found.");
                            return;
                        }
                    } catch (err) {
                        console.error("Postcode lookup failed:", err);
                        // Only alert if the fmap didn’t already move
                        if (!fmap.getCenter()) alert("Error looking up postcode.");
                        return;
                    }

                }

                // --- 2️⃣ Otherwise, continue with your existing in-map search logic ---
                const normalizedQuery = query.toLowerCase();
                let found = false;

                fmap.eachLayer(function (layer) {
                    if (found) return;

                    // ✅ Search Popups with <b data-name="...">
                    if (layer.getPopup && layer.getPopup()) {
                        let bElements = [];
                        const content = layer.getPopup().getContent();

                        if (content instanceof HTMLElement) {
                            bElements = content.querySelectorAll('b[data-name]');
                        } else if (typeof content === 'string') {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(content, 'text/html');
                            bElements = doc.querySelectorAll('b[data-name]');
                        }

                        for (let b of bElements) {
                            const dataName = b.getAttribute('data-name');
                            const normalizedDataName = dataName.toLowerCase().replace(/_/g, ' ');
                            if (normalizedDataName.includes(normalizedQuery)) {
                                let latlng = null;
                                if (typeof layer.getLatLng === 'function') latlng = layer.getLatLng();
                                else if (typeof layer.getBounds === 'function') latlng = layer.getBounds().getCenter();

                                if (latlng) {
                                    fmap.setView(latlng, 17);
                                    if (typeof layer.openPopup === 'function') layer.openPopup();
                                    found = true;
                                    return;
                                }
                            }
                        }
                    }

                    // ✅ Search Tooltips
                    if (!found && layer.getTooltip && layer.getTooltip()) {
                        const tooltipContent = layer.getTooltip().getContent();
                        if (tooltipContent && tooltipContent.toLowerCase().includes(normalizedQuery)) {
                            let latlng = null;
                            if (typeof layer.getLatLng === 'function') latlng = layer.getLatLng();
                            else if (typeof layer.getBounds === 'function') latlng = layer.getBounds().getCenter();

                            if (latlng) {
                                fmap.setView(latlng, 17);
                                found = true;
                                return;
                            }
                        }
                    }

                    // ✅ Search DivIcons
                    if (!found && layer instanceof L.Marker) {
                        if (layer.options.icon instanceof L.DivIcon) {
                            const iconContent = layer.options.icon.options.html;
                            if (iconContent.toLowerCase().includes(normalizedQuery)) {
                                const latlng = layer.getLatLng();
                                if (latlng) {
                                    fmap.setView(latlng, 17);
                                    if (typeof layer.openPopup === 'function') layer.openPopup();
                                    if (layer._icon) layer._icon.style.border = "2px solid red";
                                    found = true;
                                    return;
                                }
                            }
                        }
                    }
                });

                if (!found) {
                    alert("No matching location found.");
                }
            }
            </script>

            """


        # --- Title for the map
        title = f"{self.value} MAP"
        title_html = f'''
            <h1 style="z-index:1100;color: black;position: fixed;left:100px;">{title}</h1>
            '''

        # --- Create the map
        FolMap = folium.Map(
            location=self.latlongroid,
            zoom_start=LEVEL_ZOOM_MAP[self.type],
            width='100%',
            height='800px'
        )

        # Inject custom CSS
        css = """
        <style>
        .leaflet-control-layers {
            margin-right: 300px !important; /* move left by increasing the right margin */
            /* or use left:50px; right:auto; for absolute positioning */
        }
        </style>
        """
        FolMap.get_root().html.add_child(Element(css))

        folium.TileLayer(
            tiles='https://tileserver.memomaps.de/tilegen/{z}/{x}/{y}.png',
            name='OPNVKarte (Public Transport)',
            attr='Map data © OpenStreetMap contributors, OPNVKarte by memomaps.de',
            overlay=False,
            control=True
        ).add_to(FolMap)

        # Add all layers
        for layer in flayers:
            layer.add_to(FolMap)
            print(f"layer name: {layer.name} size:{len(layer._children)}")
            if layer.areashtml != {}:
                OPTIONS['areas'] = layer.areashtml

        # --- Inject custom HTML and JS into map

#        FolMap.add_child(folium.LatLngPopup())


        FolMap.get_root().html.add_child(folium.Element(title_html))
        FolMap.get_root().html.add_child(folium.Element(move_close_button_css))

        # Add the LatLngPopup plugin
        FolMap.add_child(folium.LatLngPopup())


        fmap_tags_js = r"""
                <script>
                (function() {

                    console.log("🗺️ fmap_marker_js loaded (Layer Control Dictionary Search)");

                    window.fmap = null;
                    window.MarkerLayer = null;

                    let pollAttempts = 0;
                    const MAX_ATTEMPTS = 100; // 10 seconds timeout

                    // ---------------------------------------------------------
                    // 1️⃣ Stage 1: Detect the Folium map object
                    // ---------------------------------------------------------
                    function detectFoliumMap() {
                        if (typeof L === 'undefined' || typeof L.Map === 'undefined') {
                            setTimeout(detectFoliumMap, 100);
                            return;
                        }

                        for (const key in window) {
                            if (!window.hasOwnProperty(key)) continue;
                            const val = window[key];

                            if (key.startsWith("map_") && val instanceof L.Map) {
                                window.fmap = val;
                                startLayerPolling();
                                return;
                            }
                        }
                        setTimeout(detectFoliumMap, 100);
                    }

                    // ---------------------------------------------------------
                    // 2️⃣ Stage 2: Targeted Polling for the Layer Control Dictionary
                    // ---------------------------------------------------------
                    function findTargetLayer() {
                        pollAttempts++;

                        if (pollAttempts > MAX_ATTEMPTS) {
                            console.error("❌ Layer Control Dictionary not found after 100 attempts. Timeout exceeded.");
                            clearInterval(poll_interval_id);
                            return;
                        }

                        // --- Search for the Layer Control's internal dictionary ---
                        for (const key in window) {
                            if (!window.hasOwnProperty(key)) continue;
                            const val = window[key];

                            // Check if variable name starts with 'layer_control_' AND has an 'overlays' property
                            if (key.startsWith("layer_control_") && val && val.overlays) {

                                // Check if the target layer ("marker") is inside the overlays
                                if (val.overlays.marker) {
                                    window.MarkerLayer = val.overlays.marker;

                                    console.log(`🔥 'marker' Layer found via Layer Control Dictionary: ${key}`);
                                    console.log(`Marker Layer stored in window.MarkerLayer.`);

                                    clearInterval(poll_interval_id);
                                    return;
                                }
                            }
                        }
                    }

                    let poll_interval_id;
                    function startLayerPolling() {
                        poll_interval_id = setInterval(findTargetLayer, 100);
                    }

                    document.addEventListener("DOMContentLoaded", detectFoliumMap);

                })();
                </script>
                """

        FolMap.get_root().html.add_child(folium.Element(fmap_tags_js))


        # Inject canvas icon JS
        canvas_icon_js = """
        <script>
        window.makePrefixMarkerIcon = function(prefix, color="#007bff") {
            const size = 40;
            const radius = 18;

            const canvas = document.createElement("canvas");
            canvas.width = size;
            canvas.height = size;
            const ctx = canvas.getContext("2d");

            ctx.beginPath();
            ctx.arc(size/2, size/2, radius, 0, 2*Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.lineWidth = 3;
            ctx.strokeStyle = "#000";
            ctx.stroke();

            ctx.fillStyle = "#fff";
            ctx.font = "bold 16px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(prefix, size/2, size/2);

            console.log("📍 canvas icon:");

            return L.icon({
                iconUrl: canvas.toDataURL(),
                iconSize: [size, size],
                iconAnchor: [size/2, size],
                popupAnchor: [0, -size/2]
            });
        };
        </script>
        """
        FolMap.get_root().html.add_child(Element(canvas_icon_js))

        # Add LatLngPopup
        FolMap.add_child(folium.LatLngPopup())

        # Inject JS to replace default popup with canvas marker
        custom_click_js = r"""
            <script>
            (function () {

                console.log("📌 custom_click_js loaded");

                // State
                window.awaitingNewPlace = false;
                window.pinMarker = null;

                // --- The Layer Polling Mechanism (For the initial click) ---
                // If the layer isn't found on the first click, this function will wait for it.
                function tryAddMarkerToLayer(marker, lat, lng, prefix) {
                    if (window.MarkerLayer) {
                        window.MarkerLayer.addLayer(marker);
                        console.log("📌 Marker added to FeatureGroup 'marker'");
                        // Now safe to do the final geocoding/messaging

                        // Trigger the rest of the original logic here
                        window.reverseGeocode(lat, lng)
                            .then(({ address, house_number, road, suburb, city, postcode }) => {
                                console.log("Raw reverse geocode result:", house_number, road, suburb, city, postcode);
                                window.awaitingNewPlace = false;

                                window.parent.postMessage({
                                    type: "newPlaceCreated",
                                    prefix, lat, lng, house_number, road, suburb, city, postcode
                                }, "*");

                                marker.bindPopup(`<b>${prefix}</b><br>${address}`).openPopup();
                                window.fmap.getContainer().classList.remove("add-place-mode");
                                console.log("📍 newPlaceCreated message sent");
                            })
                            .catch(err => {
                                console.error("Reverse geocode error:", err);
                                // Important: If geocoding fails, you may want to remove the marker or handle the error gracefully
                                if (window.fmap.hasLayer(marker)) window.fmap.removeLayer(marker);
                                window.awaitingNewPlace = false;
                                window.fmap.getContainer().classList.remove("add-place-mode");
                            });

                    } else if (window.fmap) {
                        // Safety Fallback (Should only run if polling failed)
                        marker.addTo(window.fmap);
                        console.warn("📌 Marker added directly to fmap (Layer not yet found, using fallback).");

                        // To prevent code duplication and complexity, if the layer is not found,
                        // we add it to the map but skip the reverseGeocode logic here
                        // or simplify it to prevent errors.

                        // You need to decide if the rest of the logic should run without the target layer.
                        // For now, let's keep the original logic flow focused on success.

                    } else {
                        console.error("Critical Error: Map object (fmap) is null.");
                    }
                }


                // --------------------------------------------------------------------
                // Click handler — only fires when awaitingNewPlace === true
                // --------------------------------------------------------------------
                function handleMapClick(e) {
                    if (!window.awaitingNewPlace || !window.fmap) return;

                    const lat = e.latlng.lat;
                    const lng = e.latlng.lng;

                    const prefix = prompt("Enter a prefix for this new place:", "");
                    if (!prefix) return;

                    // Remove previous pinMarker
                    if (window.pinMarker) {
                        // Check if it's on the MarkerLayer or directly on the map
                        if (window.MarkerLayer && window.MarkerLayer.hasLayer(window.pinMarker)) {
                            window.MarkerLayer.removeLayer(window.pinMarker);
                        } else if (window.fmap.hasLayer(window.pinMarker)) {
                            window.fmap.removeLayer(window.pinMarker);
                        }
                    }

                    // Create canvas-based prefix icon (Assumes window.makePrefixMarkerIcon exists)
                    const icon = window.makePrefixMarkerIcon(prefix, "#d9534f");
                    window.pinMarker = L.marker([lat, lng], { icon });

                    // Use the consolidated function to handle adding the marker and reverse geocoding
                    // Note: The original geocoding/messaging logic is now moved INTO tryAddMarkerToLayer
                    tryAddMarkerToLayer(window.pinMarker, lat, lng, prefix);
                }

                // --------------------------------------------------------------------
                // Turn on add-place mode when parent sends enableAddPlace
                // --------------------------------------------------------------------
                window.addEventListener("message", (event) => {
                    if (event.data?.type === "enableAddPlace") {
                        console.log("🟡 enableAddPlace received");
                        window.awaitingNewPlace = true;

                        if (window.fmap) {
                            window.fmap.getContainer().classList.add("add-place-mode");
                        }

                        alert("Click on the map to select a new place.");
                    }
                });

                // --------------------------------------------------------------------
                // Attach click handler when fmap is ready
                // --------------------------------------------------------------------
                window.addEventListener("fmap-ready", (ev) => {
                    const fmap = ev.detail;
                    // Double-check window.fmap is set if the event didn't set it (good practice)
                    window.fmap = fmap;

                    console.log("🎯 custom_click_js attaching click handler to fmap");
                    fmap.on("click", handleMapClick);
                });

            })();
            </script>
            """

        FolMap.get_root().html.add_child(Element(custom_click_js))

        reverse_geocode_js = """
        <script>
        // Simple reverse geocoder using Nominatim
        window.reverseGeocode = async function(lat, lng) {
            const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`;

            const res = await fetch(url, {
                headers: {
                    "Accept": "application/json"
                }
            });

            if (!res.ok) throw new Error("Reverse geocoding failed");

            const data = await res.json();
            console.log("📍 Reverse geocode result:", data);

            return {
                address: data.display_name || "Unknown address",
                house_number: data.address?.house_number || "",
                road: data.address?.road || "",
                suburb: data.address?.suburb || "",
                city: data.address?.city || data.address?.town || data.address?.village || "",
                postcode: data.address?.postcode || ""
            };

        };
        </script>
        """

        FolMap.get_root().html.add_child(folium.Element(reverse_geocode_js))

    #    FolMap.get_root().html.add_child(folium.Element(add_place_js))



        FolMap.get_root().html.add_child(folium.Element(search_bar_html))



        # Ensure there's only one LayerControl
        if not any(isinstance(child, folium.map.LayerControl) for child in FolMap._children.values()):
            FolMap.add_child(folium.LayerControl())

        # Add custom CSS/JS
        FolMap.add_css_link("electtrekprint", "https://newbrie.github.io/Electtrek/static/print.css")
        FolMap.add_css_link("electtrekstyle", "https://newbrie.github.io/Electtrek/static/style.css")
        FolMap.add_js_link("electtrekmap", "https://newbrie.github.io/Electtrek/static/map.js")

        # Fit map to bounding box
        print(f"_____before saving map file: in {route()}", self.locfilepath(self.file), len(FolMap._children), self.value, self.level)
        if self.level == 4:
            print("_____bboxcheck", self.value, self.bbox)
        if self.bbox and isinstance(self.bbox, list) and len(self.bbox) == 2:
            try:
                sw, ne = self.bbox

                # Check each part is a pair
                if not (isinstance(sw, (list, tuple)) and len(sw) == 2 and
                        isinstance(ne, (list, tuple)) and len(ne) == 2):
                    raise ValueError("BBox corners are not 2-element lists")

                sw = [float(sw[0]), float(sw[1])]
                ne = [float(ne[0]), float(ne[1])]

                if sw == ne:
                    print("⚠️ BBox corners are identical; using centroid instead")
                    FolMap.location = self.latlongroid
                    FolMap.zoom_start = LEVEL_ZOOM_MAP.get(self.type, 13)
                else:
                    print("✅ BBox is valid, applying fit_bounds")
                    FolMap.fit_bounds([sw, ne], padding=(0, 0))

            except (TypeError, ValueError) as e:
                print(f"⚠️ Invalid bbox values: {self.bbox} | Error: {e}")
        else:
            print(f"⚠️ BBox is missing or badly formatted: {self.bbox}")

        # Save to file
        target = self.locfilepath(self.file)
        FolMap.save(target)

        print("Centroid raw:", self.latlongroid)
        print(f" ✅ _____saved map file in route: {route()}", target, len(flayers), self.value, self.dir, self.file)

        return FolMap


    def set_bounding_box(self,block):
      longmin = block.Long.min()
      latmin = block.Lat.min()
      longmax = block.Long.max()
      latmax = block.Lat.max()
      print("______Bounding Box:",longmin,latmin,longmax,latmax)
      return [Point(latmin,longmin),Point(latmax,longmax)]

    def get_bounding_box(self, ntype,block):
        from state import Treepolys, Fullpolys

        if self.level < 3:
            pfile = Treepolys[ntype]
            pb = pfile[pfile['FID'] == int(self.fid)]
            minx, miny, maxx, maxy = pb.geometry.total_bounds
            pad_lat = (maxy - miny) / 5
            pad_lon = (maxx - minx) / 5
            swne = [
                (miny + pad_lat, minx + pad_lon),  # SW (lat, lon)
                (maxy - pad_lat, maxx - pad_lon)   # NE (lat, lon)
            ]
            roid = pb.dissolve().centroid.iloc[0]

        elif self.level < 5:
            pfile = Treepolys[ntype]
            pb = pfile[pfile['FID'] == int(self.fid)]
            minx, miny, maxx, maxy = pb.geometry.total_bounds
            swne = [(miny, minx), (maxy, maxx)]
            roid = pb.dissolve().centroid.iloc[0]

        else:
            minx, miny, maxx, maxy = block.geometry.total_bounds
            swne = [(miny, minx), (maxy, maxx)]
            roid = block.dissolve().centroid.iloc[0]

        # Always return lat/lon tuple for centroid
        centroid = (roid.y, roid.x)

        return [swne, centroid]



    def get_level(self):
        level = 0
        p = self.parent
        while p :
            p = p.parent
            level += 1
        return level

    def get_url(self):
        level = 0
        p = self.parent
        d = []
        while p :
            if p.level > 0:
                d = d.insert(0, "/"+p.value)
                p = p.parent
                level += 1
        d = ''.join(d.insert(0,url_for('thru',path="UNITED_KINGDOM")))
        return d

    def add_Tchild(self, child_node, etype, elect, *, counters):
        """
        Attach child_node to self safely and consistently.
        """

        # 1. Detach from old parent
        if child_node.parent and child_node in child_node.parent.children:
            child_node.parent.children.remove(child_node)

        # 2. Attach to new parent
        child_node.parent = self
        if child_node not in self.children:
            self.children.append(child_node)

        # 3. Structural attributes
        child_node.type = etype
        child_node.election = elect

        # 4. Stable per-parent numbering
        same_type_siblings = [c for c in self.children if c.type == etype]
        child_node.tagno = len(same_type_siblings)

        # 5. Global display counter
        if etype not in counters:
            raise KeyError(f"layerCounter type '{etype}' does not exist!")

        counters[etype] += 1
        child_node.gtagno = counters[etype]

        # 6. Global registration
        TREK_NODES_BY_ID[child_node.nid] = child_node
        TREK_NODES_BY_VALUE[child_node.value] = child_node

        print(f"REGISTERED NODE:,parent {child_node.parent.nid}-{child_node.parent.value}, child {child_node.nid}-{child_node.value}")
        assert child_node.parent is self, "Child parent not set correctly"
        assert child_node in self.children, "Child missing from parent children"

        return child_node


    def create_streetsheet(self, c_election, electorwalks):
        current_election = c_election
        print(f"___streetsheet: {current_election} and street data len {len(electorwalks)}")
        Postcode = electorwalks.Postcode.values[0]
        streetfile_name = self.parent.value+"--"+self.value
        type_colour = "indigo"
        #      BMapImg = walk_name+"-MAP.png"

        # create point geometries from the Lat Long values of for all electors with different locations in each group(walk/cluster)
        geometry = gpd.points_from_xy(electorwalks.Long.values,electorwalks.Lat.values, crs="EPSG:4326")
        # create a geo dataframe for the Walk Map
        geo_df1 = gpd.GeoDataFrame(
        electorwalks, geometry=geometry
        )

        # Create a geometry list from the GeoDataFrame
        geo_df1_list = [[point.xy[1][0], point.xy[0][0]] for point in geo_df1.geometry]
        CL_unique_list = pd.Series(geo_df1_list).drop_duplicates().tolist()

        groupelectors = electorwalks.shape[0]
        if math.isnan(float('%.6f'%(electorwalks.Elevation.max()))):
          climb = 0
        else:
          climb = int(float('%.6f'%(electorwalks.Elevation.max())) - float('%.6f'%(electorwalks.Elevation.min())))

        x = electorwalks.AddressNumber.values
        y = electorwalks.StreetName
        z = electorwalks.AddressPrefix.values
        houses = len(list(set(zip(x,y,z))))
        self.updateHouses(houses)
        streets = len(electorwalks.StreetName.unique())
        areamsq = 34*21.2*20*21.2
        avstrlen = 200
        housedensity = round(houses / (areamsq / 10000), 3) if areamsq else 1
        avhousem = 100*round(math.sqrt(1/housedensity),2) if housedensity else 1
        streetdash = avstrlen*streets/houses if houses else 100
        speed = 5*1000
        climbspeed = 5*1000 - climb*50/7
        leafmins = 0.5
        canvassmins = 5
        canvasssample = .5
        leafhrs = round(houses*(leafmins+60*streetdash/climbspeed)/60,2)
        canvasshrs = round(houses*(canvasssample*canvassmins+60*streetdash/climbspeed)/60,2) if streetdash else 1
        prodstats = {}
        CurrentElection = get_election_data(current_election)
        prodstats['ward'] = self.parent.parent.value
        prodstats['polling_district'] = self.parent.value
        prodstats['groupelectors'] = groupelectors
        prodstats['climb'] = climb
        prodstats['walk'] = ""
        prodstats['houses'] = houses
        prodstats['streets'] = streets
        prodstats['housedensity'] = housedensity
        prodstats['leafhrs'] = round(leafhrs,2)
        prodstats['canvasshrs'] = round(canvasshrs,2)

        #                  electorwalks['ENOP'] =  electorwalks['PD']+"-"+electorwalks['ENO']+ electorwalks['Suffix']*0.1
        target = self.locfilepath(self.file)
        results_filename = streetfile_name+"-PRINT.html"
        datafile = "/STupdate/" + self.dir+"/"+streetfile_name+"-SDATA.csv"
        # mapfile is used for the up link to the PD streets list
        mapfile = "/upbut/" + self.parent.mapfile()
        electorwalks = electorwalks.fillna("")

        #              These are the street nodes which are the street data collection pages


        context = {
        "group": electorwalks,
        "prodstats": prodstats,
        "mapfile": mapfile,
        "datafile": datafile,
        "walkname": streetfile_name,
        }
        results_template = environment.get_template('canvasscard1.html')

        with open(results_filename, mode="w", encoding="utf-8") as results:
            results.write(results_template.render(context, url_for=url_for))

        print(f"Created streetsheet called {results_filename}")
        return results_filename

    def add_parent(self, parent_node):
        # creates parent-child relationship
        print("Adding parent " + parent_node.value )
        self.parent = parent_node.value
        parent_node.child = self
        parent_node.children.append(self)
        print("Children",parent_node.children)

    def path_intersect(self, path):
        # start at the leaf of path 1 and test membership of path 2
        first = state.stepify(self.dir+"/"+self.file)
        second = state.stepify(path)
        print("intersecting paths ",self.dir+"/"+self.file, path)
        d1 = {element: index for index, element in enumerate(first)}
        d2 = {element: index for index, element in enumerate(second)}
        d3 = {k: d1[k] for k in d1 if k in d2}
        d = dict(sorted(d3.items(), key=lambda item: item[1]))
        print("___sorted intersection:",list(d.keys()))
        return list(d.keys())

    def remove_child(self, child_node):
        # removes parent-child relationship
        print("Removing " + child_node.value + " from " + self.value)
        self.children = [child for child in self.children
                         if child is not child_node]


    # Run path directed establishment of node 'A'


    def create_enclosing_gdf(self, gdf, buffer_size=20):
        """
        Create a GeoDataFrame containing the enclosing shape around a set of geographic points.

        Parameters:
            gdf (GeoDataFrame): A GeoDataFrame with Point geometries (assumed to be EPSG:4326).
            buffer_size (float, optional): Buffer size in meters for single-point cases (default: 20m).

        Returns:
            GeoDataFrame: A GeoDataFrame with one row containing the enclosing shape in EPSG:3857.
        """
        if gdf.empty:
            return gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:3857")

        # Ensure CRS is set
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)

        # Convert to metric CRS for accurate geometry ops
        gdf_3857 = gdf.to_crs("EPSG:3857")

        multi_point = gdf_3857.iloc[0].geometry

        if multi_point.is_empty:
            return gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:3857")

        points = list(multi_point.geoms)

        if len(points) == 1:
            enclosed_shape = points[0]

        elif len(points) == 2:
            p1, p2 = points

            mid_x = (p1.x + p2.x) / 2
            mid_y = (p1.y + p2.y) / 2

            d = np.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

            if d == 0:
                enclosed_shape = p1
            else:
                h = d / np.sqrt(3)
                dx = (p2.y - p1.y) / d
                dy = -(p2.x - p1.x) / d
                p3 = Point(mid_x + h * dx, mid_y + h * dy)
                enclosed_shape = MultiPoint([p1, p2, p3]).convex_hull

        else:
            enclosed_shape = MultiPoint(points).convex_hull

        # Buffer for visual padding
        smoothing_radius = 3*buffer_size if len(points) == 1 else buffer_size * 2
        rounded_shape = enclosed_shape.buffer(smoothing_radius)

        # Build GeoDataFrame with same CRS (EPSG:3857)
        enclosing_gdf = gpd.GeoDataFrame(
            {
                "NAME": gdf.NAME,
                "FID": gdf.FID,
                "LAT": gdf.LAT.values[0],
                "LONG": gdf.LONG.values[0],
                "geometry": [rounded_shape]
            },
            crs="EPSG:3857"
        )

        return enclosing_gdf



    def makemapfiles(self):
    # moves through each node referenced from self downwards
        nodes_to_visit = [self]
        count = 0
        while len(nodes_to_visit) > 0:
          current_node = nodes_to_visit.pop()
          print("_________child node Level:  ",current_node.level," ",current_node.value)
          if current_node.parent is not None:
              print("_________Parent_node Level  ",current_node.level," ",current_node.parent.value)
          nodes_to_visit += current_node.children
          count = count+1
        print("_________leafnodes  ",count)
        return
