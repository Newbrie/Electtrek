from config import workdirectories, TREKNODE_FILE, ELECTOR_FILE, GENESYS_FILE, TREEPOLY_FILE, FULLPOLY_FILE
import os
import state
import layers
import json
import pandas as pd
import geopandas as gpd
import pickle
from flask import session
from flask import request, redirect, url_for, has_request_context
from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
from elections import route, CurrentElection, capped_append, stepify
from folium import Map, Element
import folium
import uuid
from pathlib import Path
from datetime import datetime
from state import branchcolours



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
    global TREK_NODES_BY_ID

    # If the root already exists, return it
    for node in TREK_NODES_BY_ID.values():
        if node.parent is None:
            return node
    # Otherwise, create the root and store it
    root = create_root_node()
    TREK_NODES_BY_ID[root.nid] = root

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


def save_nodes(path):
    for node in TREK_NODES_BY_ID.values():
        if node.parent and node.parent.nid not in TREK_NODES_BY_ID:
            raise RuntimeError(
                f"Persist invariant violated: {node.value} ({node.nid}) has missing parent {node.parent.nid}"
            )

        # DEBUG: show candidates before saving
        print(f"💾 [DEBUG] Saving node '{node.value}' ({node.nid}) candidates: {node.candidates}")

    with open(path, "w") as f:
        json.dump([n.to_dict() for n in TREK_NODES_BY_ID.values()], f, indent=2)
        print(f"✅ [DEBUG] All nodes saved to {path}")

def load_nodes(path):
    global TREK_NODES_BY_ID

    if not path.exists() or path.stat().st_size == 0:
        print(f"[WARN] Node file missing or empty: {path}")
        return False

    reset_nodes()

    with open(path) as f:
        raw_nodes = json.load(f)

    # PASS 1: create nodes
    for data in raw_nodes:
        node = TreeNode.from_dict(data)
        node.parent = None
        node.children = []
        TREK_NODES_BY_ID[node.nid] = node

        # DEBUG: show candidates on load
        print(f"📥 [DEBUG] Loaded node '{node.value}' ({node.nid}) candidates: {node.candidates}")

    # PASS 2: wire relationships
    for data in raw_nodes:
        node = TREK_NODES_BY_ID[data["nid"]]

        pid = data.get("parent")
        if pid:
            parent = TREK_NODES_BY_ID.get(pid)
            if not parent:
                raise ValueError(f"Missing parent {pid} for node {node.value}")
            node.parent = parent
            if node not in parent.children:
                parent.children.append(node)

        for cid in data.get("children", []):
            child = TREK_NODES_BY_ID.get(cid)
            if not child:
                raise ValueError(f"Missing child {cid} for node {node.value}")
            if child not in node.children:
                node.children.append(child)
            child.parent = node

    print(f"✅ [DEBUG] Finished wiring {len(TREK_NODES_BY_ID)} nodes")
    return True




def parent_level_for(node_type):
    """
    Returns the level index of the node you must be on
    to list children of `node_type`.
    """


    if node_type not in LEVEL_INDEX:
        raise ValueError(f"Unknown node type: {node_type}")

    child_level = LEVEL_INDEX[node_type]

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



def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url,target))
    return test_url.scheme in ('http', 'https') and \
            ref_url.netloc == test_url.netloc

def get_layer_table(nodelist,title,rlevels):
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
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/PDdownST/{x.dir}/{x.file(rlevels)}&#39;); return false;">{x.value}</a>'
            elif x.type == 'walk':
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/WKdownST/{x.dir}/{x.file(rlevels)}&#39;); return false;">{x.value}</a>'
            else:
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/transfer/{x.dir}/{x.file(rlevels)}&#39;); return false;">{x.value}</a>'
            # 1. Identify grandparent
            grandparent = x.parent.parent if x.parent else None

            # Get all sibling parents under the same grandparent
            if grandparent:
                sibling_parents = [child for child in grandparent.children if child.type == x.parent.type]
            else:
                sibling_parents = [x.parent]  # fallback

            # Generate dropdown HTML
            dropdown_html = (
                f'<select class="parent-dropdown" '
                f'data-nid="{x.nid}" '
                f'data-old-parent-nid="{x.parent.nid}">'
            )

            # Add DELETE option
            dropdown_html += '<option value="__DELETE__">Delete</option>'

            for option in sibling_parents:
                selected = 'selected' if option.nid == x.parent.nid else ''
                dropdown_html += (
                    f'<option value="{option.nid}" {selected}>'
                    f'{option.value}</option>'
                )

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




def get_current_node(session=None, session_data=None):

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
        node = MapRoot
        print("⚠️ current_node_id not found in session or session_data:so id = ",238 )

    if node == None:
        node = MapRoot
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



def restore_from_persist(treepolys, fullpolys):
    print(f'____Restore from persist under !{route()} called to restore allelectors, nodes and polys! ')
    if ELECTOR_FILE.exists():
        print('_______allelectors file exists so reading in ', ELECTOR_FILE)
        electors = pd.read_csv(
            ELECTOR_FILE,
            sep='\t',                        # tab delimiter
            engine='python',                # Required for sep=None
            encoding='utf-8',
            keep_default_na=False,
            na_values=['']
        )
    safe_pickle_load(TREEPOLY_FILE,treepolys)

    safe_pickle_load(FULLPOLY_FILE,fullpolys)

    load_nodes(TREKNODE_FILE)
    print("AFTER LOAD:")
    for nid, node in TREK_NODES_BY_ID.items():
        print(nid, node.candidates)
        break
    print('_______Trek Nodes: ',  TREK_NODES_BY_ID)
    return electors

def persist(treepolys, fullpolys, electors):
    print(f'___persisting pickle under !{route()}', TREEPOLY_FILE)
    atomic_pickle_dump(treepolys,TREEPOLY_FILE)
    print('___persisting pickle ', FULLPOLY_FILE)
    atomic_pickle_dump(fullpolys,FULLPOLY_FILE)

    print('___persisting elector csv ', ELECTOR_FILE, len(allelectors))
    electors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

    return

def restore_fullpolys(node_type):

    from state import Treepolys, Fullpolys

    safe_pickle_load(TREEPOLY_FILE,Treepolys)

    safe_pickle_load(FULLPOLY_FILE,Fullpolys)

    Treepolys[node_type] = Fullpolys[node_type]

    print('___persisting pickle ', TREEPOLY_FILE)
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


def get_last_node(current_election, CE, *, create=True):
    """
    Returns the last node for the current election.
    If `create=False`, do not call ping_node and return root if CID node is unavailable.
    """

    from flask import redirect

    cid = CE.get("cid")
    cidLat = CE.get("cidLat")
    cidLong = CE.get("cidLong")
    here = (cidLat, cidLong) if cidLat is not None and cidLong is not None else None
    sourcepath = CE.get("mapfiles", [None])[-1]

    # --- 1. CID lookup ---
    if cid and cid in TREK_NODES_BY_ID:
        last_node = TREK_NODES_BY_ID[cid]
        print(f"___under route: {route()} return to existing cid: {cid}")
        return last_node

    print(f"___No cid : {cid} Get last Sourcepath {sourcepath} under {route()}")

    # --- 2. Resolve location or redirect ---
    here, response = resolve_here_or_redirect(sourcepath, here)
    if response:
        return response  # redirect response

    print(f"___ {create}__ Last node under {route()} for {current_election} sourcepath: {sourcepath} create:{create}")

    # --- 3. Resolve node from path ---
    last_node = MapRoot.ping_node(
                CE.resolved_levels,
                current_election,
                sourcepath,
                create=create
            )

    # --- 4. Fallback to root ---
    if not last_node:
        print(f"⚠️ GAP: {cid in TREK_NODES_BY_ID} @FALLING BACK TO NEAREST NODE cid:{cid}- sp:{sourcepath}")
        print(f"⚠️ @NODE INDEX DUMP:{TREK_NODES_BY_ID} ")
        last_node = MapRoot

    print(
        f"___ RETRIEVED LAST DESTINATION - election: {current_election} "
        f"NODE {last_node.value} at loc: {here} "
        f"using source: {sourcepath}"
    )

    return last_node




def find_node_by_path(basepath: str, debug=False):
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
    from datetime import datetime
    def __init__(self, *, value, fid, roid, origin, node_type):
        self.nid = str(uuid.uuid1())
        self.value = normalname(str(value))
        self.fid = fid
        self.latlongroid = roid
        self._child_index = {}
        self.last_modified = datetime.now()


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
        self.defcol = "gray"
        self.candidates = {}

        # UI
        self.tagno = 1
        self.gtagno = 1

        self.bbox = []
        self.VR = state.VIC.copy()
        self.VI = state.VIC.copy()



    def path_options(self, rlevels, *, include_self=True):
        """
        Returns a list of dropdown items where:
        - key = full mapfile path for each step
        - value = human-readable step
        Example:
        UNITED_KINGDOM/UNITED_KINGDOM-MAP.html
        UNITED_KINGDOM/ENGLAND/ENGLAND-MAP.html
        ...
        """
        options = []
        cur = self if include_self else self.parent
        path_parts = []

        # collect all ancestors (from root → current)
        ancestors = []
        while cur:
            ancestors.insert(0, cur)  # prepend to get root → current
            cur = cur.parent

        # build key for each step
        for node in ancestors:
            path_parts.append(node.value)  # accumulate path
            key = "/".join(path_parts) + f"/{node.value}-MAP.html"
            options.append({
                "key": key,         # full mapfile path
                "value": node.value # step name
            })

        return options



    def available_tables(self,rlevels):
        return {
        "TABLE_TYPES": state.TABLE_TYPES
        }

    def available_layers(self,rlevels):
        return {
        "LAYERS": state.LAYERS
        }

    def get_options(self, *, program=None, electionctx=None):
            rlevels = electionctx.ce.resolved_levels
            next_level = self.level + 1


            return {
                # identity
                "node_id": self.nid,
                "node_name": self.value,
                "level": self.level,
                "ACC": {True,False}, # accumulate boundaries during navigation

                # navigation capabilities
                "has_parent": self.parent is not None,
                "child_types": (
                    [rlevels[next_level]] if next_level in rlevels else []
                ),

                # available UI elements
                "tables_available": self.available_tables(rlevels),
                "layers_available": self.available_layers(rlevels),
                "areas": self.get_areas(),

                # relationships
                "children": [c.value for c in self.children],
                "territory": self.path_options(rlevels, include_self=True)
            }


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
            "candidates": self.candidates,
            "defcol": self.defcol,

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
        node.candidates = data.get("candidates", {})
        node.defcol = data["defcol"]
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


    def child_type(self, rlevels: dict[int, str]) -> str | None:
        """
        Return the child node type for this node.
        Safely returns None if this is a leaf node.
        """
        if not rlevels:
            return None

        next_level = self.level + 1

        # If the next level does not exist in rlevels, this is a leaf
        if next_level not in rlevels:
            return None

        return rlevels[next_level]


    def file(self, rlevels: dict[int, str]) -> str:
        """Compute map filename dynamically."""
        FACEENDING = {
            'street': "-PRINT.html",
            'walkleg': "-PRINT.html",
            'polling_district': "-PDS.html",
            'walk': "-WALKS.html",
            'ward': "-WARDS.html",
            'division': "-DIVS.html",
            'constituency': "-MAP.html",
            'county': "-MAP.html",
            'nation': "-MAP.html",
            'country': "-MAP.html",
        }

        child = self.child_type(rlevels)
        suffix = FACEENDING.get(child, "")

        return f"{self.value}{suffix}"



    def endpoint_created(self, c_elect, CurrEL, newpath):
        """
        Creates a map node (HTML) if it doesn't already exist or
        the one that does exist is older than the node's last modification.
        """

        from pathlib import Path
        from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
        from elections import route
        import os
        from datetime import datetime

        rlevels = CurrEL.resolved_levels
        next_level = self.level + 1

        print(f"___under {route()} for {c_elect} testing endpoint:", self.mapfile(rlevels))
        print("endpoint children:", [c.value for c in self.children])

        if next_level > max(rlevels, default=0):
            return False  # No further levels to process

        atype = rlevels[next_level]

        workdir = workdirectories.get('workdir')
        if not workdir:
            print("⚠️ [ERROR] 'workdir' not found in workdirectories!")
            return False

        fullpath = Path(workdir) / newpath

        # Determine if the map is stale
        map_stale = True
        if fullpath.exists() and hasattr(self, 'last_modified') and self.last_modified:
            # Compare file modification time with node last_modified time
            file_mtime = datetime.utcfromtimestamp(fullpath.stat().st_mtime)
            map_stale = self.last_modified > file_mtime
            if not map_stale:
                print(f"⚙️ Map file {fullpath} is up-to-date (last_modified {self.last_modified})")

        # Create map if it doesn't exist or is stale
        if map_stale:
            print(f"⚙️ Creating/updating map file: {fullpath}")
            atype = self.child_type(rlevels)
            print(f" target type: {atype} current {self.value} type: {self.type}")
            self.create_area_map(c_elect, CurrEL)
            print(f"_________layeritems for {self.value} of type {atype} are {self.childrenoftype(atype)} for level {self.level}")

        # Record map in CurrEL mapfiles
        print("Endpoint Created/Updated:", CurrEL['mapfiles'][-1])

        return map_stale  # True if a new map was created or updated



    def set_parent(self, new_parent):
        # Ensure new parent is in the global index
        if new_parent.nid not in TREK_NODES_BY_ID:
            TREK_NODES_BY_ID[new_parent.nid] = new_parent

        # Ensure self is in the global index
        if self.nid not in TREK_NODES_BY_ID:
            TREK_NODES_BY_ID[self.nid] = self

        # Remove from old parent
        if self.parent:
            if self in self.parent.children:
                self.parent.children.remove(self)
            self.parent.last_modified = datetime.utcnow()

        # Add to new parent
        if self not in new_parent.children:
            new_parent.children.append(self)
        self.parent = new_parent
        new_parent.last_modified = datetime.utcnow()
        save_nodes(TREKNODE_FILE)



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
        Convert lozenges(a code , type & description) found in calendar slots into detailed lists of resources, areas, tags and places.
        """

        resources = []
        tasks = []
        places = []
        areas = []


        CE_resources = CE.get('resources',{})
        CE_task_tags, CE_outcome_tags, CE_all_tags = get_tags_json(CE['tags'])
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



    def build_eventlist_dataframe(self,CElection):
        """
        Produce an eventlist dataframe matching the intent of the JS summary.
        """

        slots = CElection["calendar_plan"]["slots"]
        rows = []
        print("__Building events from slots:",slots)
        for key, slot in slots.items():
            dt = parse_slot_key(key)
            if not dt:
                print(f"⚠️ Skipping slot with invalid datetime key: {key}")
                continue

            resources, tasks, places, areas = self.process_lozenges(
                slot.get("lozenges", []),
                CElection
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

    def mapfile(self,rlevels):
        return self.dir+"/"+self.file(rlevels)



    def ping_node(self, rlevels, c_election, dest_path, create=True):
        from state import LEVEL_ZOOM_MAP
        from flask import session
        from elections import route

        def strip_leaf_from_path(path):
            leaf = path.split("/")[-1]
            for suffix in [
                "-PRINT.html", "-MAP.html", "-CAL.html", "-WALKS.html",
                "-ZONES.html", "-PDS.html", "-DIVS.html",
                "-WARDS.html", "-DEMO.html"
            ]:
                if leaf.endswith(suffix):
                    leaf = leaf.replace(suffix, "")
            return leaf.split("--")[-1]

        def split_clean_path(path):
            leaf = strip_leaf_from_path(path)
            dir_path = "/".join(path.strip("/").split("/")[:-1])
            parts = [
                p for p in dir_path.split("/")
                if p and p not in ["DIVS", "PDS", "WALKS", "WARDS"] and "@@@" not in p
            ]
            if leaf and leaf not in parts:
                parts.append(leaf)
            return parts

        # ──────────────────────────────
        # Step 0: keyword handling
        full_dest_path = dest_path.strip()
        path_only, *kw = full_dest_path.rsplit(" ", 1)

        if kw and kw[0].lower() in LEVEL_ZOOM_MAP:
            keyword = kw[0].lower()
            path_str = path_only
        else:
            keyword = None
            path_str = full_dest_path

        # ──────────────────────────────
        # Step 1: clean paths
        self_path = split_clean_path(self.mapfile(rlevels))
        dest_parts = split_clean_path(path_str)

        print(f"🪜 [DEBUG] self_path: {self_path}")
        print(f"🪜 [DEBUG] dest_parts: {dest_parts}")

        # ──────────────────────────────
        # Step 2: common ancestor
        common_len = get_common_prefix_len(self_path, dest_parts)
        print(f"🔗 [DEBUG] Common prefix length: {common_len}")

        node = self

        # ──────────────────────────────
        # Step 3: move UP
        for _ in range(len(self_path) - common_len):
            if not node.parent:
                print(f"⚠️ [DEBUG] Reached root while moving up from {node.value}")
                break
            node = node.parent
            print(f"🔼 [DEBUG] Moved up to: {node.value} (L{node.level}), children: {[c.value for c in node.children]}")

        # ──────────────────────────────
        # Step 4: move DOWN
        down_path = dest_parts[common_len:]
        print(f"⬇️ [DEBUG] Moving down path: {down_path}")

        moved = False

        for part in down_path:
            next_level = node.level + 1
            if next_level > max(rlevels):
                raise Exception("Resolved level overflow")

            ntype = rlevels[next_level]

            print(f"➡️ [DEBUG] At node: {node.value} (L{node.level}), looking for part '{part}' at level {next_level} (type={ntype})")
            print(f"   Children before match: {[c.value for c in node.children]}")

            matches = [c for c in node.children if c.value == part]

            if create and not matches:
                print(f"   ⚙️ [DEBUG] Creating branch '{ntype}' under {node.value} to try and generate '{part}'")
                try:
                    if next_level <= 4:
                        node.create_map_branch(rlevels, c_election)
                    else:
                        node.create_data_branch(rlevels, c_election)
                except Exception as e:
                    print(f"   ⚠️ [DEBUG] Branch creation failed: {e}")

                matches = [c for c in node.children if c.value == part]

            print(f"   Children after branch creation: {create} {[c.value for c in node.children]}")

            if create and not matches :
                # Instead of returning self, raise a clear error
                raise ValueError(
                    f"Path error: Mode {create} could not find or create node '{part}' under '{node.value}' "
                    f"(level {node.level + 1})"
                )

            node = matches[0]
            moved = True
            print(f"✅ [DEBUG] Descended to: {node.value} (L{node.level}), children: {[c.value for c in node.children]}")

        # ──────────────────────────────
        # Step 5: keyword zoom
        if keyword:
            node.zoom_level = LEVEL_ZOOM_MAP[keyword]
            print(f"🔍 [DEBUG] Applied keyword zoom '{keyword}' → zoom_level {node.zoom_level}")

        print(f"✅ [DEBUG] Reached node: {node.value} (L{node.level}) with children: {[c.value for c in node.children]}")

        # ──────────────────────────────

        # ──────────────────────────────
        # Step 6: always expand children at final node
        next_level = node.level
        if next_level <= max(rlevels) and create:
            children_type = rlevels[next_level]
            print(f"🌿 [DEBUG] Expanding children of {node.value} as {children_type}")
            try:
                if node.level < 4:
                    node.create_map_branch(rlevels, c_election)
                else:
                    node.create_data_branch(rlevels, c_election)
            except Exception as e:
                print(f"⚠️ [DEBUG] Branch expansion failed: {e}")

        accumulate = session.get("accumulate", False)

        if accumulate:

            lst = session.get("accumulated_nodes", [])

            if node.nid not in lst:
                lst.append(node.nid)

            session["accumulated_nodes"] = lst


        else:
            # Idempotent mode → reset list
            session["accumulated_nodes"] = [node.nid]

        return node


    def getselectedlayers(self, rlevels, this_election, path):
        from layers import make_feature_layers, FEATURE_LAYER_SPECS, ExtendedFeatureGroup        # need to create child, sibling and parent layers for given self.level
        from flask import session
        # rlevels[self.level-1] = child type
        # rlevels[self.level] = sibling type
        # rlevels[self.parent.level] = parent type
        selected = []
        layers = make_feature_layers()

        childtype = self.child_type(rlevels)

        accumulate = session.get("accumulate", False)
        print(f"___ACCUMULATE IN SESSION: {accumulate}")
        if self.level < 7:
            # Determine nodes to render
            if accumulate:
                node_ids = session.get("accumulated_nodes", [])
                print("Accumulate SESSION IDS:", node_ids)
                print("Accumulate TREK KEYS:", list(TREK_NODES_BY_ID.keys()))

                nodelist = [TREK_NODES_BY_ID.get(nid) for nid in node_ids if nid in TREK_NODES_BY_ID]
                for n in nodelist:
                    print("ACC NODE:", n.value, "DEF:", n.defcol, "ID:", id(n))

            else:
                nodelist = [self]  # single node

            # Get the child layer
            child_layer = layers[childtype]
            print(f"__LAYER NODE LIST: {[n.nid for n in nodelist]} ")
            # Pass the list of nodes to create_layer

            child_layer.create_layer(this_election, nodelist, childtype)


            child_layer.show = True
            selected.append(child_layer)

        if self.level > 0:
            sibling_layer = layers[self.type]
            sibling_layer.create_layer(this_election, [self.parent], self.type)
            selected.append(sibling_layer)

        if self.level > 1:
            parent_layer = layers[self.parent.type]
            parent_layer.create_layer(this_election, [self.parent.parent], self.parent.type)
            selected.append(parent_layer)

        marker_layer = layers["marker"]
        selected.append(marker_layer)

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

    def updateTurnout(self,rlevels):
        from state import LastResults

        sname = self.value
        casnode = self

        # --- Base turnout assignment ---
        if self.level == 3:
            entry = LastResults.get("constituency", {}).get(sname)
            self.turnout = entry.get("TURNOUT") if entry else None
        elif self.level > 3:
            self.turnout = self.parent.turnout

        if self.level == 4:
            entry = LastResults.get("ward", {}).get(sname)
            self.turnout = entry.get("TURNOUT") if entry else None
        elif self.level > 4:
            self.turnout = self.parent.turnout

        # --- Cascade upward (compute parents from children) ---
        while casnode.parent:
            parent = casnode.parent
#            children = parent.childrenoftype(
#                gettypeoflevel(electionstyle, casnode.dir, casnode.level)
#            )
            children = parent.childrenoftype(rlevels[parent.level])
            values = [c.turnout for c in children if c.turnout is not None]
            parent.turnout = sum(values) / len(values) if values else None

            casnode = parent

        return

    def updateGOTV(self, gotv_pct, rlevels):
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
            children = parent.childrenoftype(rlevels[parent.level])

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


    def updateCandidates(self,rlevels):
        """Fill self.candidates from the global Candidates dict."""
        from state import Candidates

        if self.type == "division":
            # Safely get candidate dict or default to empty dict
            self.candidates = Candidates.get("division", {}).get(self.value, {})
            print(f"[DEBUG] Candidate update for {self.value}: {self.candidates}")
        save_nodes(TREKNODE_FILE)


    def updateElectorate(self, rlevels):
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
                    for c in parent.childrenoftype(rlevels[parent.level])
                )
            casnode = parent

        return

    def updateHouses(self,rlevels,pop):

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
            for x in sumnode.parent.childrenoftype(rlevels[sumnode.level]):
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


    def locfilepath(self, file_text: str) -> str:
        """
        Ensure the directory for the map file exists and
        return the full target file path.
        """

        # Build full path
        target = Path(workdirectories["workdir"]) / self.dir / file_text

        # Ensure directory exists
        target.parent.mkdir(parents=True, exist_ok=True)

        print(f"____mapfile path ensured: {target.parent}")
        return str(target)


    def create_name_nodes(self,resolved_levels,gotv_pct,elect,nodetype,namepoints,ending):
        zonecolour = {
            "ZONE_0": "black", "ZONE_1": "red", "ZONE_2": "lime",
            "ZONE_3": "blue", "ZONE_4": "yellow", "ZONE_5": "cyan",
            "ZONE_6": "magenta", "ZONE_7": "orange", "ZONE_8": "purple",
            "ZONE_9": "brown", "ZONE_10": "gray"
        }


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

        newname = normalname(limb['Name'])

        for index, limb  in namepoints.iterrows():

            if newname not in fam_nodes :
                datafid = abs(hash(newname))
                newnode = TreeNode(value=newname,fid=datafid, roid=(limb['Lat'],limb['Long']),origin=elect, node_type=nodetype )
                egg = self.add_Tchild(child_node=newnode,etype=nodetype, elect=elect)
                [egg.bbox, egg.latlongroid] = egg.get_bounding_box(nodetype,block)
                egg.defcol = zonecolour.get(limb['Zone'],'black')
                print(f"🎨 Assigned color '{egg.defcol}' to walk_node '{egg.value}' for zone '{limb['Zone']}'")

                egg.updateTurnout(resolved_levels)
                egg.updateElectorate(resolved_levels)
                egg.updateGOTV(gotv_pct, resolved_levels)
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


    def create_data_branch(self,resolved_levels,c_election):
        global allelectors
        global areaelectors
        global workdirectories
        from state import Treepolys, Fullpolys


# if called from within ping, then this module should aim to return the next level of nodes of selected type underneath self.
# the new data namepoints must be derived from the electoral file - name is stored in session['importfile']
# if the electoral file hasn't been loaded yet then that needs to be done first.


        nodelist = []

        electtype = resolved_levels[self.level+1]

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

        CE = CurrentElection.load(c_election)
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
                    nodelist = self.create_name_nodes(resolved_levels,gotv_pct,c_election,'polling_district',PDPtsdf,"-PDS.html") #creating PD_nodes with mean PD pos and elector counts
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

                    nodelist = self.create_name_nodes(resolved_levels, gotv_pct,c_election, 'walk', nodeelectors, "-WALKS.html")
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
                    nodelist = self.create_name_nodes(resolved_levels,gotv_pct,c_election,'street',streetdf,"-PRINT.html") #creating street_nodes with mean street pos and elector counts
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
                    nodelist = self.create_name_nodes(resolved_levels,gotv_pct,c_election,'walkleg',walklegdf,"-PRINT.html") #creating walkleg_nodes with mean street pos and elector counts
            except Exception as e:
                print("❌ Error during data branch generation:", e)
                return []
        else:
            print(f"_____ Electoral file contains no  data for election {c_election} and {self.value} for {electtype} types - Please load correct file",len(allelectors), len(areaelectors))

            nodelist = []
        print(f"____Created Data Branch for Election: {c_election} in area: {self.value} creating: {len(nodelist)} of child type {electtype} from: {len(allelectors)} - {len(areaelectors)} electors")

        save_nodes(TREKNODE_FILE)
        return nodelist

    def create_map_branch(self,resolved_levels,c_election):
        from state import Treepolys, Fullpolys, Overlaps
        import random

        electtype = resolved_levels[self.level+1]

        if self.type not in Treepolys:
            raise ValueError(f"Layer '{self.type}' not found in Treepolys")

# need to know the CE['territories'] value to determine division or ward
        # NOW THIS IS SAFE
        parent_poly = Treepolys[self.type]

        if parent_poly is None or parent_poly.empty:
            raise ValueError(f"No polygons loaded for layer '{self.type}'")

        print(
            f"🧭 create_map_branch({self.type}) polys loaded:",
            parent_poly is not None and not parent_poly.empty
        )

        # existing logic continues...


        CE = CurrentElection.load(c_election)
        gotv_pct = CE['GOTV']
        block = pd.DataFrame()


        # Filter the parent geometry based on the FID
        parent_geom = parent_poly[parent_poly['FID'] == int(self.fid)]


        # If no matching geometry is found, handle the case where parent_geom is empty
        if parent_geom.empty:
            print(f"Adding back in Full '{self.type}' boundaries for {self.value} FID {self.fid}")
            raise Exception ("EMPTY COUNTRY PARENT GEOMETRY")
        else:
            print(f"___create_map_branch geometry for {self.value} FID {self.fid} is: ")
            print(
                f"parent type: {self.type} "
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
        fam_nodes = self.childrenoftype(electtype)

        # Check if there’s anything to process
        if ChildPolylayer.empty:
            print(f"⚠️ No geometries found for children of type '{electtype}' under {self.value}. Skipping creation.")
            return fam_nodes

        i = 0
        j = 0
        k = 0
        for index, limb in ChildPolylayer.iterrows():
            newname = normalname(limb.NAME)
            print(f"____Considering inclusion of child {newname} in {self.value} of branch")
            fam_values = [x.value for x in fam_nodes]


            centroid_point = limb.geometry.centroid
            here = (centroid_point.y, centroid_point.x)
            overlaparea = parent_geom.intersection(limb.geometry).area
            overlap_margin = round(Overlaps[electtype], 8)  # 8 decimal places for safety

            print(
                f"________Trying map type {electtype} name {newname}, "
                f"existing names: {fam_values}, level+1: {self.level+1}, "
                f"area: {overlaparea}, margin: {overlap_margin}, "
                f"test: {overlaparea > overlap_margin}"
            )

            # Only create new node if doesn't already exist and passes the area overlap check
            if overlaparea > overlap_margin:
                existing_node = next((x for x in fam_nodes if x.value == newname), None)
                print(f"existing: {existing_node}")
                if not existing_node:
                    # new boundary inside parent
                    egg = TreeNode(
                        value=newname,
                        fid=limb.FID,
                        roid=here,
                        origin="ONS_MAPS",
                        node_type=electtype
                    )
                    print(f"________Found missing type {electtype} name {newname} at level {self.level+1}, area {overlaparea}")

                    # Add as child and calculate bbox
                    egg = self.add_Tchild(child_node=egg, etype=electtype, elect=c_election)
                    egg.bbox, egg.latlongroid = egg.get_bounding_box(electtype, block)
                    print(f"________bbox [{egg.bbox}] - child of type {electtype} at lev {self.level+1} of {self.value}")
                    egg.defcol = branchcolours[k]
                    # Update the node with latest stats
                    fam_nodes.append(egg)
                    try:
                        egg.updateParty()
                        egg.updateCandidates(resolved_levels)
                        egg.updateTurnout(resolved_levels)
                        egg.updateElectorate(resolved_levels)
                        egg.updateGOTV(gotv_pct, resolved_levels)
                        print(f"______Addedname: {egg.value}, type {egg.type}, level {egg.level}, party {egg.party}")
                    except Exception:
                        self.remove_child(egg)
                        raise Exception ("Tree branching error")
                    k += 1
                else:
                    j += 1
                    # boundary name already a child node
                    continue
            else:
                # boundary not inside parent ignore
                continue
            i += 1

        if len(fam_nodes) == 0:
            print(f"⚠️ No children of type '{electtype}' created for {self.value} at level {self.level+1}")

        print(f"___At {self.value}, level {self.level}, revised {electtype} type fam nodes: {fam_nodes}")
        print(f"______create_map_branch added_nodes: {k} existing {j} new of {i} total, values: {[x.value for x in fam_nodes]}")

        save_nodes(TREKNODE_FILE)
        return fam_nodes





    def create_area_map(self, CE, CEdata):
        global SERVER_PASSWORD
        global STATICSWITCH

        from folium import IFrame
        from state import LEVEL_ZOOM_MAP
        from layers import make_counters,FEATURE_LAYER_SPECS, ExtendedFeatureGroup

        import hashlib
        import re
        from pathlib import Path
        rlevels = CEdata.resolved_levels
        print(f"___BEFORE cal creation: in route {route()} creating cal for: ", self.value)

        print(f"___BEFORE map creation: in route {route()} creating file: ", self.file(rlevels))

        mapfile = self.mapfile(rlevels)
        counters = make_counters()

            # 2️⃣ Create fresh FeatureGroups for THIS map

        # 3️⃣ Select which layers to render for this map
        flayers = self.getselectedlayers(
            rlevels=CEdata.resolved_levels,
            this_election=CE,
            path=mapfile
        )


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

            let toggleSent = false;
            document.getElementById("backToCalendarBtn").addEventListener("click", () => {
                if (!toggleSent) {
                    window.parent.postMessage({ type: "toggleView" }, "*");
                    toggleSent = true;
                    setTimeout(() => { toggleSent = false }, 500); // reset after half a second
                }
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
                    // ✅ Search only markers inside the marker FeatureGroup
                    if (
                        !found &&
                        window.MarkerLayer &&
                        layer instanceof L.Marker &&
                        window.MarkerLayer.hasLayer(layer)
                    ) {
                        if (layer.options.icon instanceof L.DivIcon) {
                            const html = layer.options.icon.options.html || "";
                            if (html.toLowerCase().includes(normalizedQuery)) {
                                const latlng = layer.getLatLng();
                                fmap.setView(latlng, 17);
                                layer.openPopup?.();
                                layer._icon?.style && (layer._icon.style.border = "2px solid red");
                                found = true;
                                return;
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
#        FolMap.get_root().html.add_child(Element(css))
# no need for this if map left of nav buttons
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
            print(f"create map layer name: {layer.name} size:{len(layer._children)}")



        # --- Inject custom HTML and JS into map




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




        for k, v in FolMap._children.items():
            print(type(v), getattr(v, "name", None))

        # Ensure there's only one LayerControl
        if not any(isinstance(child, folium.map.LayerControl) for child in FolMap._children.values()):
            FolMap.add_child(folium.LayerControl())
        FolMap.get_root().html.add_child(folium.Element(fmap_tags_js))
        FolMap.get_root().html.add_child(folium.Element(search_bar_html))
        FolMap.get_root().html.add_child(folium.Element(reverse_geocode_js))
        FolMap.get_root().html.add_child(Element(custom_click_js))
        FolMap.get_root().html.add_child(Element(canvas_icon_js))
        FolMap.get_root().html.add_child(folium.Element(title_html))
        FolMap.get_root().html.add_child(folium.Element(move_close_button_css))

        # Add the LatLngPopup plugin
        FolMap.add_child(folium.LatLngPopup())

        # Add custom CSS/JS
        FolMap.add_css_link("electtrekprint", "https://newbrie.github.io/Electtrek/static/print.css")
        FolMap.add_css_link("electtrekstyle", "https://newbrie.github.io/Electtrek/static/style.css")
        FolMap.add_js_link("electtrekmap", "https://newbrie.github.io/Electtrek/static/map.js")


        # Fit map to bounding box
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

        # overwrite file
        target = self.locfilepath(self.file(rlevels))
        FolMap.save(target)

        print("Centroid raw:", self.latlongroid)
        print(f" ✅ _____saved map file in route: {route()}", target, len(flayers), self.value, self.dir, self.file(rlevels))

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

    def remove_child(self, child):
        """
        Remove a child node from this node safely.
        """
        if not child:
            return False

        try:
            if child in self.children:
                self.children.remove(child)

            # break back-reference if it exists
            if hasattr(child, "parent") and child.parent is self:
                child.parent = None

            return True

        except ValueError:
            return False


    def add_Tchild(self, child_node, etype, elect):
        # 1. Assign type FIRST
        child_node.type = etype

        # 1.1 🔒 DUPLICATE GUARD: same parent, same type, same fid
        for existing in self.children:
            if existing.type == etype and existing.fid == child_node.fid:
                print(
                    f"[DEBUG] Reusing existing child "
                    f"{existing.value} (fid={existing.fid}) "
                    f"under parent {self.value}"
                )
                return existing

        # 2. Detach from old parent if needed
        if child_node.parent and child_node in child_node.parent.children:
            print(f"[DEBUG] Detaching child {child_node.value} from its previous parent.")
            child_node.parent.children.remove(child_node)
            # Update old parent's last_modified
            from datetime import datetime
            child_node.parent.last_modified = datetime.utcnow()

        # 3. Attach to new parent
        child_node.parent = self
        if child_node not in self.children:
            self.children.append(child_node)
            # Update new parent's last_modified
            from datetime import datetime
            self.last_modified = datetime.utcnow()

        # 4. Per-parent numbering (keeping siblings ordered)
        same_type_siblings = [c for c in self.children if c is not child_node and c.type == etype]
        child_node.tagno = len(same_type_siblings)

        # 6. Register by ID only (safe)
        if self.nid not in TREK_NODES_BY_ID:
            TREK_NODES_BY_ID[self.nid] = self
        if child_node.nid not in TREK_NODES_BY_ID:
            TREK_NODES_BY_ID[child_node.nid] = child_node

        print(
            f"REGISTERED NODE: parent {self.nid}-{self.value}, "
            f"child {child_node.nid}-{child_node.value}"
        )

        save_nodes(TREKNODE_FILE)
        return child_node




    def create_streetsheet(self, c_election, rlevels,electorwalks):
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
        self.updateHouses(rlevels,houses)
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
        CElection = CurrentElection.load(current_election)
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
        target = self.locfilepath(self.file(rlevels))
        results_filename = streetfile_name+"-PRINT.html"
        datafile = "/STupdate/" + self.dir+"/"+streetfile_name+"-SDATA.csv"
        # mapfile is used for the up link to the PD streets list
        mapfile = "/upbut/" + self.parent.mapfile(rlevels)
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

    def path_intersect(self, path, rlevels):
        # start at the leaf of path 1 and test membership of path 2
        first = state.stepify(self.dir+"/"+self.file(rlevels))
        second = state.stepify(path)
        print("intersecting paths ",self.dir+"/"+self.file(rlevels), path)
        d1 = {element: index for index, element in enumerate(first)}
        d2 = {element: index for index, element in enumerate(second)}
        d3 = {k: d1[k] for k in d1 if k in d2}
        d = dict(sorted(d3.items(), key=lambda item: item[1]))
        print("___sorted intersection:",list(d.keys()))
        return list(d.keys())


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

levels = ['country','nation','county','constituency','ward/division','polling_district/walk','street/walkleg','elector']

from typing import Dict

Outcomes = pd.read_excel(GENESYS_FILE)
Outcols = Outcomes.columns.to_list()
allelectors = pd.DataFrame(Outcomes, columns=Outcols)
allelectors.drop(allelectors.index, inplace=True)


TREK_NODES_BY_ID: Dict[int, "TreeNode"] = {}


MapRoot = get_root()
TREK_NODES_BY_ID[MapRoot.nid] = MapRoot
save_nodes(TREKNODE_FILE)
