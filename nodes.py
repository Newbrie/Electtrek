from config import workdirectories, TREKNODE_FILE, ELECTOR_FILE, GENESYS_FILE, TREEPOLY_FILE, FULLPOLY_FILE
import os
import state
import layers
import json
import pandas as pd
import geopandas as gpd
import pickle
from flask import session
from flask import request, redirect, url_for, has_request_context, render_template, current_app
from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
from elections import route, CurrentElection, stepify
from folium import Map, Element
import folium
import uuid
from pathlib import Path
from datetime import datetime
from state import branchcolours
import sys, math, stat, json



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
    """
    Load tree nodes from JSON file at `path`, wiring parents/children.
    Resilient: missing parents or children are logged but skipped.
    """
    global TREK_NODES_BY_ID

    if not path.exists() or path.stat().st_size == 0:
        print(f"[WARN] Node file missing or empty: {path}")
        return False

    reset_nodes()

    with open(path) as f:
        try:
            raw_nodes = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            return False

    # PASS 1: create node objects
    for data in raw_nodes:
        try:
            node = TreeNode.from_dict(data)
        except Exception as e:
            print(f"[WARN] Skipping node due to error: {data}. Error: {e}")
            continue

        node.parent = None
        node.children = []
        TREK_NODES_BY_ID[node.nid] = node

        print(f"📥 [DEBUG] Loaded node '{node.value}' ({node.nid}) candidates: {node.candidates}")

    print(f"JSON count: {len(raw_nodes)}")
    print(f"Dict count: {len(TREK_NODES_BY_ID)}")

    # PASS 2: wire relationships
    for data in raw_nodes:
        node = TREK_NODES_BY_ID.get(data["nid"])
        if not node:
            continue  # skipped in pass 1

        # Wire parent safely
        pid = data.get("parent")
        if pid:
            parent = TREK_NODES_BY_ID.get(pid)
            if parent:
                node.parent = parent
                if node not in parent.children:
                    parent.children.append(node)
            else:
                print(f"[WARN] Missing parent {pid} for node '{node.value}'. Node treated as root.")

        # Wire children safely
        for cid in data.get("children", []):
            child = TREK_NODES_BY_ID.get(cid)
            if not child:
                print(f"[WARN] Missing child {cid} for node '{node.value}'. Skipping.")
                continue
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
    print(f'____Restore from persist under !{route()} called to restore nodes and polys! ')

    safe_pickle_load(TREEPOLY_FILE,treepolys)

    safe_pickle_load(FULLPOLY_FILE,fullpolys)

    load_nodes(TREKNODE_FILE)
    print("AFTER LOAD:")
    return

def persist(treepolys, fullpolys):
    print(f'___persisting pickle under !{route()}', TREEPOLY_FILE)
    atomic_pickle_dump(treepolys,TREEPOLY_FILE)
    print('___persisting pickle ', FULLPOLY_FILE)
    atomic_pickle_dump(fullpolys,FULLPOLY_FILE)
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

    def __init__(self, *, value, fid, roid, origin, node_type, nid=None):
        # If nid provided (loading from JSON) → use it
        # If not (new node) → generate one
        self.nid = nid if nid is not None else str(uuid.uuid4())

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
        self.bbox = []
        self.VR = state.VIC.copy()
        self.VI = state.VIC.copy()

    def file(self, rlevels: dict[int, str]) -> str:
        """Compute map filename dynamically."""
        FACEENDING = {
            'elector': "-PRINT.html",
            'street': "-MAP.html",
            'walkleg': "-MAP.html",
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
        if self.type == "street":
            filename = f"{self.parent.value}--{self.value}{suffix}"
        else:
            filename = f"{self.value}{suffix}"

        return filename

    @classmethod
    def from_dict(cls, data):
        node = cls(
            value=data["value"],
            fid=data["fid"],
            roid=data["latlongroid"],
            origin=data["origin"],
            node_type=data["node_type"],
            nid=data["nid"],   # 🔥 THIS is the important change
        )

        node.electorate = data["electorate"]
        node.turnout = data["turnout"]
        node.houses = data["houses"]
        node.target = data["target"]
        node.party = data["party"]
        node.candidates = data.get("candidates", {})
        node.defcol = data["defcol"]
        node.tagno = data["tagno"]
        node.bbox = data["bbox"]

        return node

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
            "bbox": self.bbox,
        }


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



    def endpoint_created(self, c_elect, CurrEL, newpath, static=False):
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

        print(f"___under {route()} for {c_elect} testing endpoint:", newpath)
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
        endpoint_created = False

        if not fullpath.exists():
            endpoint_created = True

        elif hasattr(self, 'last_modified') and self.last_modified:
            file_mtime = datetime.utcfromtimestamp(fullpath.stat().st_mtime)
            if self.last_modified > file_mtime:
                endpoint_created = True

        if self.level < 6 and endpoint_created:
            self.create_area_map(c_elect, CurrEL, static=static)

        return endpoint_created



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


    def get_areas(self, nodelist=None):
        """
        Returns a nested dictionary of areas grouped by their immediate children (regions).

        If nodelist is provided, it merges areas from all nodes in the list.

        Example output:
        {
            "North Region": { "A1": "North Area 1", "A2": "North Area 2" },
            "South Region": { "B1": "South Area 1" }
        }
        """
        area_groups = {}

        # Determine which nodes to process
        if nodelist is None:
            nodes_to_process = [self]
        else:
            nodes_to_process = nodelist

        for node in nodes_to_process:
            if not node.children:
                continue

            for child in node.children:  # top-level regions
                areas = {grand.nid: grand.value for grand in child.children} if child.children else {}

                if child.value in area_groups:
                    # Merge areas if the region already exists (accumulated nodes)
                    area_groups[child.value].update(areas)
                else:
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



    def ping_node(self, rlevels, c_election, dest_path, create=True, accumulate=False):
        from state import LEVEL_ZOOM_MAP, Treepolys, Fullpolys
        from nodes import TREK_NODES_BY_ID
        from flask import session
        from elections import route
        from elector import electors

        for lev, ltype in rlevels.items():
            tree_gdf = Treepolys.get(ltype)
            if tree_gdf is None or tree_gdf.empty:
                print(f"____Ping/Treepolys {ltype} - EMPTY")
                continue
            tot_tree = len(tree_gdf)
            unique_name_tree = tree_gdf['NAME'].nunique()
            unique_fid_tree = tree_gdf['FID'].nunique()
            print(f"____Ping/Treepolys {ltype} - tot:{tot_tree} unique_NAME:{unique_name_tree} unique_FID:{unique_fid_tree}")

                # Same for Fullpolys
            full_gdf = Fullpolys.get(ltype)
            if full_gdf is None or full_gdf.empty:
                print(f"____Ping/Fullpolys {ltype} - EMPTY")
                continue

            tot_full = len(full_gdf)
            unique_name_full = full_gdf['NAME'].nunique()
            unique_fid_full = full_gdf['FID'].nunique()
            print(f"____Ping/Fullpolys {ltype} - tot:{tot_full} unique_NAME:{unique_name_full} unique_FID:{unique_fid_full}")


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

            if not matches:
                # no mstch found so best to return current node
                if node.parent:
                    print(f"[DEBUG] Ascended to: {node.parent.value} "
                          f"(L{node.parent.level}), "
                          f"children: {[c.value for c in node.parent.children]}")
                else:
                    print("[DEBUG] Node has no parent (root node)")

                return node.parent  # or raise a controlled exception

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
        print(f"✅ [DEBUG] Expanding node: {node.value} (L{node.level}) Max {max(rlevels)} createmode :{create} rlevels: {rlevels}")

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

        if accumulate:
            # Get the list of accumulated nodes from the session, or initialize it as an empty list if not available
            lst = session.get("accumulated_nodes", [])

            # Only add the node to the list if it's not already there
            if node.nid not in lst:
                lst.append(node.nid)

            # Update the session with the new list of accumulated nodes
            session["accumulated_nodes"] = lst
            session.modified = True



        return node



    def getselectedlayers(self, rlevels, this_election, path, static=False):
        from layers import make_feature_layers
        from flask import session
        from state import Treepolys, Fullpolys

        selected = []
        layers = make_feature_layers()

        # Get the accumulate flag from the session
        accumulate = session.get("accumulate", False)
        print(f"___ACCUMULATE IN SESSION: {accumulate}")

        # -------------------------------------------------
        # Handle the Child Layer (Level + 1)
        # -------------------------------------------------
        if self.level < 7:
            if accumulate:
                # Get accumulated node IDs from the session
                node_ids = session.get("accumulated_nodes", [])
                valid_nodes = []
                stale_ids = []

                for nid in node_ids:
                    node = TREK_NODES_BY_ID.get(nid)
                    if node and node.parent:   # ensure parent exists
                        valid_nodes.append(node)
                    else:
                        stale_ids.append(nid)

                if stale_ids:
                    print("⚠️ Removing stale node IDs from session:", stale_ids)
                    session["accumulated_nodes"] = [
                        nid for nid in node_ids if nid not in stale_ids
                    ]

                nodelist = valid_nodes
                session.modified = True

                print("Accumulate SESSION IDS:", node_ids)

                # Fetch nodes from TREK_NODES_BY_ID based on node_ids                nodelist = [TREK_NODES_BY_ID.get(nid) for nid in node_ids if nid in TREK_NODES_BY_ID]
                if not nodelist:
                    print(f"Warning: No nodes found in TREK_NODES_BY_ID for IDs {node_ids}")
                else:
                    print("Accumulated Nodes:", [n.value for n in nodelist])

            else:
                # If accumulation is off, render only the current node
                nodelist = [self]

            # Render the child layer
            print(f"__LAYER NODE LIST (Child Layer): {[n.value for n in nodelist]} ")

            child_layer = layers[rlevels[self.level + 1]]
            child_layer.create_layer(this_election, nodelist, static=False)
            child_layer.show = True
            selected.append(child_layer)

        # -------------------------------------------------
        # Handle the Sibling Layer (Current Level)
        # -------------------------------------------------
        if self.level > 0:
            sibling_layer = layers[rlevels[self.level]]
            sibling_layer.create_layer(this_election, [self.parent], static=False)
            selected.append(sibling_layer)

        # -------------------------------------------------
        # Handle the Parent Layer (Level - 1)
        # -------------------------------------------------
        if self.level > 1:
            parent_layer = layers[rlevels[self.level - 1]]
            parent_layer.create_layer(this_election, [self.parent.parent], static=False)
            selected.append(parent_layer)

        # -------------------------------------------------
        # Always Add Marker Layer
        # -------------------------------------------------
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


        for index, limb in namepoints.iterrows():

            newname = normalname(limb['Name'])

            existing = next(
                (c for c in self.children
                 if c.type == nodetype and c.value == newname),
                None
            )

            if existing:
                egg = existing
            else:
                datafid = index
                newnode = TreeNode(
                    value=newname,
                    fid=datafid,
                    roid=(limb['Lat'], limb['Long']),
                    origin=elect,
                    node_type=nodetype
                )
                egg = self.add_Tchild(child_node=newnode, etype=nodetype, elect=elect)

            # 🔥 Always update geometry
            lon = limb['Long']
            lat = limb['Lat']
            delta = 0.0001

            egg.latlongroid = (lat, lon)
            egg.bbox = [
                lon - delta,
                lat - delta,
                lon + delta,
                lat + delta
            ]

            egg.defcol = zonecolour.get(limb['Zone'], 'black')

            egg.updateTurnout(resolved_levels)
            egg.updateElectorate(resolved_levels)
            egg.updateGOTV(gotv_pct, resolved_levels)

            print('______Data nodes', egg.value, egg.fid,
                  egg.electorate, egg.houses, egg.target, egg.bbox)

        # After loop
        fam_nodes = self.childrenoftype(nodetype)


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


    def create_data_branch(self, resolved_levels, c_election):
        from elector import electors
        from state import Treepolys, Fullpolys


        nodelist = []
        CE = CurrentElection.load(c_election)
        electtype = resolved_levels[self.level + 1]
        print(f"✅ Creating {electtype} Data branch for election {c_election}")

        # ----------------------------------------
        # Load electors from ElectorManager
        # ----------------------------------------
        areaelectors = electors.electors_for_node(self)


        if areaelectors.empty:
            print(f"⚠️ No data from election {c_election} at node {self.value}")
            return []


        gotv_pct = CE['GOTV']

        try:

                # Mapping of node type to column name in areaelectors
            shapecolumn = {
                "polling_district": "PD",
                "walk": "WalkName",
                "street": "StreetName",
                "walkleg": "StreetName"  # same as street, but filtered by WalkName
            }

            # Optional mapping for output suffix per type
            suffix_mapping = {
                "polling_district": "-PDS.html",
                "walk": "-WALKS.html",
                "street": "-PRINT.html",
                "walkleg": "-PRINT.html"
            }

            # -------------------------------
            # Refactored node elector processing
            # -------------------------------
            if electtype in shapecolumn:
                colname = shapecolumn[electtype]
                df = areaelectors.copy()

                # Special filtering for street and walkleg types
                if electtype == "street":
                    df = df[df['PD'] == self.value]
                elif electtype == "walkleg":
                    df = df[df['WalkName'] == self.value]

                # Select relevant columns
                select_cols = [colname, 'ENOP', 'Long', 'Lat', 'Zone']
                df = df[select_cols].rename(columns={colname: 'Name'})

                # Aggregation dictionary
                agg_dict = {'Lat': 'mean', 'Long': 'mean', 'ENOP': 'count', 'Zone': 'first'}
                nodeelectors = df.groupby(['Name']).agg(agg_dict).reset_index()

                # Call the node creation function
                nodelist = self.create_name_nodes(
                    resolved_levels,
                    gotv_pct,
                    c_election,
                    electtype,
                    nodeelectors,
                    suffix_mapping.get(electtype, "-PRINT.html")
                )
            else:
                print(f"⚠️ Unknown elect type: {electtype}")

        except Exception as e:
            print("❌ Error during data branch generation:", e)
            return []

        print(
            f"✅ Created Data Branch for Election: {c_election} "
            f"in area: {self.value} "
            f"creating: {len(nodelist)} of type {electtype} "
            f"from {len(areaelectors)} electors",
            f"under resolved {resolved_levels} electors"
        )

        save_nodes(TREKNODE_FILE)
        return nodelist


    def create_map_branch(self,resolved_levels,c_election):
        from state import Treepolys, Fullpolys, Overlaps
        import random

        electtype = resolved_levels[self.level+1]
        parenttype = resolved_levels[self.level]
        print(f"🧭 create_map_branch 1Y {electtype} filteredby ({parenttype}) : {Treepolys[parenttype]}:")
        if Treepolys.get(parenttype, []).empty:
            raise ValueError(f"Parent Layer '{self.type}' not found in Treepolys")

# need to know the CE['territories'] value to determine division or ward
        # NOW THIS IS SAFE


        parent_poly = Treepolys[parenttype]

        print(f"🧭 create_map_branch 2Y {electtype} filteredby ({parenttype}) :")

        if parent_poly is None or parent_poly.empty:
            raise ValueError(f"No polygons loaded for layer '{self.type}'")

        print(
            f"🧭 create_map_branch({parenttype}) polys loaded:",
            parent_poly is not None and not parent_poly.empty
        )

        # existing logic continues...


        CE = CurrentElection.load(c_election)
        gotv_pct = CE['GOTV']
        block = pd.DataFrame()


        # Filter the parent geometry based on the FID
        parent_geom = parent_poly[parent_poly['FID'] == int(self.fid)]

        print(f"🧭 create_map_branch 3Y parent_geom ({parent_geom}) :")

        # If no matching geometry is found, handle the case where parent_geom is empty
        if parent_geom.empty:
            print(f"Adding back in Full '{parenttype}' boundaries for {self.value} FID {self.fid}")
            raise Exception ("EMPTY COUNTRY PARENT GEOMETRY")
        else:
            print(f"___create_map_branch geometry for {self.value} FID {self.fid} is: ")
            print(
                f"parent type: {parenttype} "
                f"size {len(parent_poly)} "
                f"parent poly cols: {list(parent_poly.columns)} "
                f"NID {self.nid}"
            )
            # If geometry was found, proceed with the matching geometry
            parent_geom = parent_geom.geometry.values[0]
        [self.bbox, self.latlongroid] = self.get_bounding_box(parenttype,block)

        ChildPolylayer = Treepolys[electtype]

        print(f"____There are {len(ChildPolylayer)} Children candidates for {self.value} bbox:[{self.bbox}] of type {electtype}" )

        index = 0
        fam_nodes = self.childrenoftype(electtype)

        # Check if there’s anything to process
        if ChildPolylayer.empty:
            raise Exception ("No geometries found!")
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
            here = (centroid_point.y, centroid_point.x) # (lat , Long)
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





    def create_area_map(self, CE, CEdata, static=False):
        global SERVER_PASSWORD

        from folium import IFrame
        from state import LEVEL_ZOOM_MAP, Treepolys, Fullpolys
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
            path=mapfile,
            static=static
        )

        street_row_css = """
            <style>
            .street-row-odd {
                border-bottom: 1px solid #00509e;
                background-color: #d3d3d3;  /* light gray for odd rows */
                color: #003366;
                transition: background 0.3s, color 0.3s;
            }

            .street-row-even {
                border-bottom: 1px solid #00509e;
                background-color: #e6f2ff;  /* light blue for even rows */
                color: #003366;
                transition: background 0.3s, color 0.3s;
            }

            .street-row-odd:hover,
            .street-row-even:hover {
                background-color: #004080;  /* dark blue on hover */
                color: #ffffff;             /* white text on hover */
            }
            </style>
            """
        voronoi_labelandtag_css = """
            <style>
            .voronoi-label{
              font-size:10pt;
              font-weight:500;
              text-align:center;
              -webkit-text-stroke:2px white;
              paint-order:stroke fill;
            }
            .voronoi-tag{
              padding:2px 4px;
              border-radius:5px;
              border:2px solid black;
            }
            </style>
            """


        move_close_button_css = """
            <style>

            /* Make popup close button large and visible */
            .leaflet-popup-close-button {
                right: auto !important;
                left: 8px !important;
                top: 8px !important;

                width: 28px !important;
                height: 28px !important;

                line-height: 26px !important;
                text-align: center;

                font-size: 20px !important;
                font-weight: bold;

                color: white !important;
                background: #d9534f !important;

                border-radius: 50% !important;
                border: 2px solid white !important;

                box-shadow: 0 2px 6px rgba(0,0,0,0.4);

                cursor: pointer;
            }

            /* Hover effect */
            .leaflet-popup-close-button:hover {
                background: #c9302c !important;
                transform: scale(1.1);
            }

            </style>
            """


        limit_popup_height_css = """
            <style>
            .leaflet-popup-content {
                max-height: 300px;
                overflow-y: auto;
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

        transparency = """
        <style>
        .leaflet-div-icon {
            background: transparent !important;
            border: none !important;
        }
        </style>
        """


        for k, v in FolMap._children.items():
            print(type(v), getattr(v, "name", None))

        # Ensure there's only one LayerControl
        FolMap.add_child(folium.LayerControl(collapsed=True))

        FolMap.get_root().html.add_child(folium.Element(fmap_tags_js))
        FolMap.get_root().html.add_child(folium.Element(search_bar_html))
        FolMap.get_root().html.add_child(folium.Element(reverse_geocode_js))
        FolMap.get_root().html.add_child(Element(custom_click_js))
        FolMap.get_root().html.add_child(Element(canvas_icon_js))
        FolMap.get_root().html.add_child(folium.Element(title_html))
        FolMap.get_root().html.add_child(folium.Element(move_close_button_css))
        FolMap.get_root().html.add_child(folium.Element(voronoi_labelandtag_css))
        FolMap.get_root().html.add_child(folium.Element(street_row_css))
        FolMap.get_root().html.add_child(folium.Element(transparency))
        FolMap.get_root().html.add_child(folium.Element(limit_popup_height_css))

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
            # If currently in EPSG:4326 (WGS84)
            pb_proj = pb.to_crs(epsg=3857)   # Web Mercator (meters)

            roid = pb_proj.dissolve().centroid.iloc[0]

            # Optional: convert centroid back to lat/lon
            roid = gpd.GeoSeries([roid], crs=3857).to_crs(epsg=4326).iloc[0]
        elif self.level < 5:
            pfile = Treepolys[ntype]
            pb = pfile[pfile['FID'] == int(self.fid)]
            minx, miny, maxx, maxy = pb.geometry.total_bounds
            swne = [(miny, minx), (maxy, maxx)]
            # If currently in EPSG:4326 (WGS84)
            pb_proj = pb.to_crs(epsg=3857)   # Web Mercator (meters)

            roid = pb_proj.dissolve().centroid.iloc[0]

            # Optional: convert centroid back to lat/lon
            roid = gpd.GeoSeries([roid], crs=3857).to_crs(epsg=4326).iloc[0]
        else:
            minx, miny, maxx, maxy = block.geometry.total_bounds
            swne = [(miny, minx), (maxy, maxx)]
            pb_proj = block.to_crs(epsg=3857)   # Web Mercator (meters)

            roid = pb_proj.dissolve().centroid.iloc[0]

            # Optional: convert centroid back to lat/lon
            roid = gpd.GeoSeries([roid], crs=3857).to_crs(epsg=4326).iloc[0]

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
            if existing.type == etype:

                # Polygon nodes: use fid
                if hasattr(child_node, "origin") and child_node.origin == "ONS_MAPS":
                    if existing.fid == child_node.fid:
                        return existing

                # Data nodes: use name
                else:
                    if existing.value == child_node.value:
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



    def create_streetsheet(self, c_election, rlevels, electorwalks):
        """
        Generates an HTML streetsheet for a given walk/polling district.
        Uses Flask's render_template safely inside an app context.
        """

        current_election = c_election
        print(f"___streetsheet: {current_election} and street data len {len(electorwalks)}")

        # Basic file naming
        streetfile_name = f"{self.parent.value}--{self.value}"
        results_filename = f"{streetfile_name}-PRINT.html"

        # Create GeoDataFrame for map points
        geometry = gpd.points_from_xy(electorwalks.Long.values, electorwalks.Lat.values, crs="EPSG:4326")
        geo_df = gpd.GeoDataFrame(electorwalks, geometry=geometry)
        geo_df_list = [[pt.xy[1][0], pt.xy[0][0]] for pt in geo_df.geometry]
        unique_coords = pd.Series(geo_df_list).drop_duplicates().tolist()

        # Compute street/housing stats
        groupelectors = electorwalks.shape[0]
        climb = int(float(electorwalks.Elevation.max() or 0) - float(electorwalks.Elevation.min() or 0))
        houses = len(set(zip(electorwalks.AddressNumber, electorwalks.StreetName, electorwalks.AddressPrefix)))
        streets = len(electorwalks.StreetName.unique())
        areamsq = 34 * 21.2 * 20 * 21.2
        housedensity = round(houses / (areamsq / 10000), 3) if areamsq else 1
        avhousem = 100 * round(math.sqrt(1 / housedensity), 2) if housedensity else 1
        streetdash = 200 * streets / houses if houses else 100
        leafmins = 0.5
        canvassmins = 5
        canvasssample = 0.5
        speed = 5000
        climbspeed = speed - climb * 50 / 7
        leafhrs = round(houses * (leafmins + 60 * streetdash / climbspeed) / 60, 2)
        canvasshrs = round(houses * (canvasssample * canvassmins + 60 * streetdash / climbspeed) / 60, 2) if streetdash else 1

        # Production stats dictionary
        prodstats = {
            "ward": self.parent.parent.value,
            "polling_district": self.parent.value,
            "groupelectors": groupelectors,
            "climb": climb,
            "walk": "",
            "houses": houses,
            "streets": streets,
            "housedensity": housedensity,
            "leafhrs": leafhrs,
            "canvasshrs": canvasshrs,
        }

        # File paths
        results_path = self.locfilepath(results_filename)
        datafile = f"/STupdate/{self.dir}/{streetfile_name}-SDATA.csv"
        mapfile = f"/upbut/{self.parent.mapfile(rlevels)}"

        # Fill missing data to prevent template errors
        electorwalks = electorwalks.fillna("")

        from Electtrek import app
        # Template context
        context = {
            "group": electorwalks,
            "prodstats": prodstats,
            "mapfile": mapfile,
            "datafile": datafile,
            "walkname": streetfile_name,
        }

        # Render street capture template safely inside Flask app context
        with app.app_context():
            html_output = render_template("canvasscard1.html", **context)
        print("HTML LENGTH:", len(html_output))
        print("HTML START:", repr(html_output[:200]))

        # Write HTML to the file to be used as canvasssheet
        with open(results_path, "w", encoding="utf-8") as f:
            f.write(html_output)

        print(f"✅ Created streetsheet called {results_path}")
        return results_path


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
