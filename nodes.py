from config import workdirectories, DATA_FILE, LOGO_FILE,TREKNODE_FILE, ELECTOR_FILE, GENESYS_FILE, TREEPOLY_FILE, FULLPOLY_FILE, GEO_INDEX_FILE
import os
import state
import layers
import json
import logging
import pandas as pd
import geopandas as gpd
import pickle
from flask import session
from flask import request, redirect, url_for, has_request_context, render_template, current_app
from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
import elections
from folium import Map, Element
import folium
import uuid
from pathlib import Path
from datetime import datetime

import sys, math, stat, json
import tempfile


FACEENDING = {
    'elector': "-PRINT.html",
    'street': "-MAP.html",
    'walkleg': "-MAP.html",
    'polling_district': "-MAP.html",
    'walk': "-MAP.html",
    'ward': "-MAP.html",
    'division': "-MAP.html",
    'constituency': "-MAP.html",
    'county': "-MAP.html",
    'nation': "-MAP.html",
    'country': "-MAP.html",
}

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

    print(f"[DEBUG] registry id in save_nodes: {id(TREK_NODES_BY_ID)}")
    print(f"[DEBUG] registry size in save_nodes: {len(TREK_NODES_BY_ID)}")
    sum_of_all_nodes = len(TREK_NODES_BY_ID)

    for node in TREK_NODES_BY_ID.values():
        if node.parent and node.parent.nid not in TREK_NODES_BY_ID:
            raise RuntimeError(
                f"Persist invariant violated: {node.value} ({node.nid}) has missing parent {node.parent.nid}"
            )

        # DEBUG: show candidates before saving
        print(f"💾 [DEBUG] Saving node '{node.value}' ({node.nid}) candidates: {node.candidates}")

    with open(path, "w") as f:
        json.dump([n.to_dict() for n in TREK_NODES_BY_ID.values()], f, indent=2)
        print(f"✅ [DEBUG] All {sum_of_all_nodes} nodes saved to {path}")

def load_nodes(path):
    """
    Load tree nodes from JSON file at `path`, wiring parents/children.
    Resilient: missing parents or children are logged but skipped.
    """


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

def get_layer_table(nodelist,title,elevels):
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
            # --- 🔥 ADD THIS LINE HERE ---
            dfy.loc[i,'nid'] = x.nid  # This preserves the ID for the checkbox
            # -----------------------------
            VIoptions = x.VI
            for party in VIoptions:
                dfy.loc[i,party] = x.VI[party]
            if x.type == 'polling_district':
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/PDdownST/{x.dir}/{x.file(elevels)}&#39;); return false;">{x.value}</a>'
            elif x.type == 'walk':
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/WKdownST/{x.dir}/{x.file(elevels)}&#39;); return false;">{x.value}</a>'
            else:
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/transfer/{x.dir}/{x.file(elevels)}&#39;); return false;">{x.value}</a>'
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
#            dfy.loc[i,'toget'] = int(((safe_float(x.electorate)*safe_float(x.turnout))/2+1)/safe_float(elections.CurrenetElection['GOTV'])) - int(x.VI.get(elections.CurrenetElection['yourparty'],0))
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


def atomic_json_dump(obj, path):
    """
    Safely writes a JSON file by writing to a temp file first,
    then replacing the original. Prevents 'forgetting' branches
    due to file corruption during a crash.
    """
    d = os.path.dirname(path) or "."
    tmp_path = None

    try:
        # 1. Use 'w' mode (text) and 'utf-8' encoding
        # delete=False is required so we can rename it after closing
        with tempfile.NamedTemporaryFile(mode='w', dir=d, delete=False, encoding='utf-8', suffix='.tmp') as tf:
            json.dump(obj, tf, indent=4) # indent=4 makes it human-readable for debugging
            tmp_path = tf.name

        # 2. Atomic replacement (OS level move)
        os.replace(tmp_path, path)

    except Exception as e:
        logging.error(f"❌ Atomic JSON dump failed for {path}: {e}")
        # Clean up the temp file if it was created but not moved
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise  # Re-raise to let the caller know the save failed

def safe_pickle_load(path, default):
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return default

        with open(path, "rb") as f:
            return pickle.load(f)

    except (EOFError, pickle.UnpicklingError, AttributeError, ValueError, TypeError) as e:
        print(f"❌ Pickle load failed for {path}: {e}")
        return default

def safe_json_load(path, default):
    """
    Safely loads a JSON file. Returns 'default' if the file is missing,
    empty, or corrupted.
    """
    try:
        # 1. Check if file exists and isn't empty
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            logging.info(f"📂 {path} not found or empty. Using default.")
            return default

        # 2. Open in text mode for JSON
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        # Use JSON-specific error handling instead of Pickle
        logging.error(f"❌ JSON load failed for {path}: {e}")

        # IMPORTANT: Return the default so the app doesn't crash,
        # but consider backing up the 'broken' file first if it has data.
        return default



def restore_from_persist(treepolys, fullpolys, geo_index):
    print(f'____Restore from persist under !{elections.route()} called to restore nodes and polys! ')

    safe_pickle_load(TREEPOLY_FILE,treepolys)

    safe_pickle_load(FULLPOLY_FILE,fullpolys)

    load_nodes(TREKNODE_FILE)

    # Load from file
    safe_json_load(GEO_INDEX_FILE, geo_index)
    print("AFTER LOAD:")
    return

def persist(treepolys, fullpolys, geo_index):
    print(f'___persisting pickle under !{elections.route()}', TREEPOLY_FILE)
    atomic_pickle_dump(treepolys,TREEPOLY_FILE)
    print('___persisting pickle ', FULLPOLY_FILE)
    atomic_pickle_dump(fullpolys,FULLPOLY_FILE)
    print('___persisting json ', geo_index)
    atomic_json_dump(geo_index,GEO_INDEX_FILE)
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

    parts = [state.normalname(p) for p in basepath.strip("/").split("/") if p]
    if not parts:
        return None

    root = get_root()
    node = root

    if state.normalname(root.value) != parts[0]:
        if debug:
            print("[DEBUG] Root mismatch")
        return None

    for part in parts[1:]:
        if debug:
            print(f"[DEBUG] Descending to: {part}")

        matches = [c for c in node.children if state.normalname(c.value) == part]
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

        self.value = state.normalname(str(value))
        self.fid = fid
        self.latlongroid = roid
        self._child_index = {}
        self.last_modified = datetime.now()

        self.origin = origin
        self.election = origin
        self.type = node_type
        self.childtype = None

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

    def file(self, elevels: dict[int, str]) -> str:
        """Compute map filename dynamically."""

        # This unpacks the single key-value pair from the dictionary

        type = self.type
        suffix = FACEENDING.get(type, "")
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

    @property
    def allowed_child_types(self) -> list[str]:
        childtype = self.childtype or ""

        return [
            t.strip()
            for t in childtype.split("/")
            if t.strip()
        ]


    def path_options(self, elevels, *, include_self=True):
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



    def available_tables(self,elevels):
        return {
        "TABLE_TYPES": state.TABLE_TYPES
        }

    def available_layers(self,elevels):
        return {
        "LAYERS": state.LAYERS
        }

    def get_options(self, *, program=None, electionctx=None):
            rlevels = electionctx.ce.resolved_levels
            assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

            # The clean unpack
            (c_election, elevels), = rlevels.items()
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
                    [elevels[next_level]] if next_level in elevels else []
                ),

                # available UI elements
                "tables_available": self.available_tables(elevels),
                "layers_available": self.available_layers(elevels),
                "areas": self.get_areas(),

                # relationships
                "children": [c.value for c in self.children],
                "territory": self.path_options(elevels, include_self=True)
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


    def child_type(self, elevels: dict) -> str | None:
        if not elevels:
            return None
        # 3. Safe access
        return elevels.get(self.level + 1)



    def endpoint_created(self, rlevels, newpath, static=False):
        from flask import session
        """
        Creates a map node (HTML) if it doesn't already exist or
        the one that does exist is older than the node's last modification.
        """
        totalleaf =  0
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        next_level = self.level + 1

        print(f"___under {elections.route()} testing endpoint:", newpath)
        print("endpoint children:", [c.value for c in self.children])

        # 1. Extract the inner dictionary of {int: str}


        # 2. Find the maximum level integer (e.g., 5)
        max_level = max(elevels)

        if next_level > max_level:
            return False  # No further levels to process

        atype = elevels[next_level]

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

        if next_level <= max_level and endpoint_created:
            map, totalleaf = self.create_node_map(rlevels, static=static)

        accumulate = session.get("accumulate", False)
# if the endpoint doesn t exist or we area accumulating
        render_node = self
        if accumulate:
            render_node = self.parent if self.parent else self
            endpoint_created = True
            print(f"=== ACCUMULATING === {self.nid}")
            print(f"DEBUG: Current Session List BEFORE: {session.get('accumulated_nodes')}")

            # 1. Update the list
            lst = session.get("accumulated_nodes", [])
            if self.nid not in lst:
                lst.append(self.nid)
            session["accumulated_nodes"] = lst
            session.modified = True

            # 2. TRIGGER THE PARENT UPDATE
            # This ensures that even though we are 'visiting' a child,
            # we force the parent map to re-render with the updated session list.
            if self.parent:
                print(f"--- Triggering Parent Map Update for: {self.parent.value}")
                # Call create_node_map on the parent
                map, totalleaf = self.parent.create_node_map(rlevels, static=static)
        return endpoint_created, totalleaf



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
        CE_task_tags, CE_outcome_tags, CE_all_tags = get_tags_json(CE['Tags'])
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



    def build_eventlist_dataframe(self, rlevels):
        """
        Produce an eventlist dataframe matching the intent of the JS summary.
        """
        from election import CurrentElection

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        CElection = CurrentElection.load(c_election)
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

    def mapfile(self):
        from flask import session
        from elections import CurrentElection
        rlevels = CurrentElection.load(session.get("current_election")).resolved_levels
        # This unpacks the single key-value pair from the dictionary
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"
        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked mapfile election: {c_election} - el:{elevels}")
        return f"{self.dir}/{self.file(elevels)}"



    def ping_node(self, rlevels, dest_path, create=True, accumulate=False):
        from state import LEVEL_ZOOM_MAP, Treepolys, Fullpolys
        from flask import session
        from elector import electors

        # Move helper utilities cleanly to the top of the scope
        def strip_leaf_from_path(p_str):
            leaf = p_str.split("/")[-1]
            for suffix in [
                "-PRINT.html", "-MAP.html", "-CAL.html", "-WALKS.html",
                "-ZONES.html", "-PDS.html", "-DIVS.html",
                "-WARDS.html", "-DEMO.html"
            ]:
                if leaf.endswith(suffix):
                    leaf = leaf.replace(suffix, "")
            return leaf.split("--")[-1]

        def split_clean_path(p_str):
            # Clean out empty spaces/trailing slashes first
            p_str = p_str.strip("/")
            if not p_str:
                return []

            leaf = strip_leaf_from_path(p_str)

            # If it's a deep path with multiple steps
            if "/" in p_str:
                dir_path = "/".join(p_str.split("/")[:-1])
                raw_parts = dir_path.split("/")
            else:
                raw_parts = []

            parts = [
                p for p in raw_parts
                if p and p not in ["DIVS", "PDS", "WALKS", "WARDS"] and "@@@" not in p
            ]

            if leaf and leaf not in parts:
                parts.append(leaf)

            # 🎯 CRITICAL FIX: Eliminate sequential back-to-back duplicate root mutations
            sanitized_parts = []
            for item in parts:
                if not sanitized_parts or item.upper() != sanitized_parts[-1].upper():
                    sanitized_parts.append(item)

            return sanitized_parts

        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        for lev, ltype in elevels.items():
            print(f"Processing Level {lev}: {ltype}")

            # Split bivalent layer strings into an iterable array
            sub_types = [t.strip() for t in ltype.split("/")] if "/" in str(ltype) else [ltype]

            # Check Treepolys across sub-types
            valid_tree_type = None
            for st in sub_types:
                tree_gdf = Treepolys.get(st)
                if tree_gdf is not None and not tree_gdf.empty:
                    valid_tree_type = st
                    tot_tree = len(tree_gdf)
                    unique_name_tree = tree_gdf['NAME'].nunique()
                    unique_fid_tree = tree_gdf['FID'].nunique()
                    print(f"____Ping/Treepolys {st} - tot:{tot_tree} unique_NAME:{unique_name_tree} unique_FID:{unique_fid_tree}")
                    break

            if not valid_tree_type:
                print(f"____Ping/Treepolys {ltype} -> EMPTY")
                continue

            # Check Fullpolys across sub-types
            valid_full_type = None
            for st in sub_types:
                full_gdf = Fullpolys.get(st)
                if full_gdf is not None and not full_gdf.empty:
                    valid_full_type = st
                    tot_full = len(full_gdf)
                    unique_name_full = full_gdf['NAME'].nunique()
                    unique_fid_full = full_gdf['FID'].nunique()
                    # 🎯 FIX: Changed variable from typo 'unique_full_fid' to 'unique_fid_full'
                    print(f"____Ping/Fullpolys {st} - tot:{tot_full} unique_NAME:{unique_name_full} unique_FID:{unique_fid_full}")
                    break

            if not valid_full_type:
                print(f"____Ping/Fullpolys {ltype} - EMPTY")
                continue

        # ──────────────────────────────
        # Step 0: keyword handling
        full_dest_path = dest_path.strip()

        # Guard clause against paths with no extra parameter tokens
        if " " in full_dest_path:
            path_only, *kw = full_dest_path.rsplit(" ", 1)
            if kw and kw[0].lower() in LEVEL_ZOOM_MAP:
                keyword = kw[0].lower()
                path_str = path_only
            else:
                keyword = None
                path_str = full_dest_path
        else:
            keyword = None
            path_str = full_dest_path

        # ──────────────────────────────
        # Step 1: clean paths
        self_path = split_clean_path(self.mapfile())
        dest_parts = split_clean_path(path_str)

        print(f"🪜 [DEBUG] dest_path: {dest_path}")
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
        levels_dict = elevels

        # Find the maximum level integer (e.g., 7)
        max_level = max(elevels)

        for part in down_path:
            next_level = node.level + 1

            # Prevent breaking if we overshoot known levels
            if next_level > max_level:
                print(f"⚠️ [DEBUG] Next level {next_level} exceeds max_level {max_level}.")
                break

            ntype = str(elevels[next_level]) # Force string type checking

            print(f"➡️ [DEBUG] At node: {node.value} (L{node.level}), looking for part '{part}' at level {next_level} (type={ntype})")
            print(f"   Children before match: {[c.value for c in node.children]}")

            match = next((c for c in node.children if c.value == part), None)

            if create and not match:
                print(f"   ⚙️ [DEBUG] Attempting branch creation for '{part}' under {node.value} (Level {next_level})")

                # 🌟 DYNAMIC BIVALENT RESOLUTION: Try the primary logical fork first
                try:
                    if next_level <= 4:
                        node.create_map_branch(rlevels)
                    else:
                        node.create_data_branch(rlevels)
                except Exception as e:
                    print(f"   ⚠️ [DEBUG] Primary branch creation failed: {e}")

                # Re-check for a match
                match = next((c for c in node.children if c.value == part), None)

                # 🌟 FIX: Dynamic Bivalent Fallback Check!
                # If there's still no match, and the type definition contains a "/", try the alternative method.
                if not match and "/" in ntype:
                    print(f"   🔄 [DEBUG] Bivalent Level Detected ('{ntype}'). Primary method missed target. Running alternative execution...")
                    try:
                        if next_level <= 4:
                            node.create_data_branch(rlevels)   # Try data instead
                        else:
                            node.create_map_branch(rlevels)    # Try map instead
                    except Exception as e:
                        print(f"   ⚠️ [DEBUG] Alternative bivalent branch creation failed: {e}")

                    # Final check for this pass
                    match = next((c for c in node.children if c.value == part), None)

            print(f"   Children after branch creation: {create} {[c.value for c in node.children]}")

            if not match:
                # No match found, so best to fall back gracefully to the current node
                if node.parent:
                    print(f"[DEBUG] Ascended fallback to: {node.parent.value} "
                          f"(L{node.parent.level}), "
                          f"children: {[c.value for c in node.parent.children]}")
                    return node.parent
                else:
                    print("[DEBUG] Node has no parent (root node). Staying at root.")
                    return node

            node = match
            moved = True
            print(f"✅ [DEBUG] Descended to: {node.value} (L{node.level}), children: {[c.value for c in node.children]}")

        # ──────────────────────────────
        # Step 5: keyword zoom
        if keyword:
            node.zoom_level = LEVEL_ZOOM_MAP[keyword]
            print(f"🔍 [DEBUG] Applied keyword zoom '{keyword}' → zoom_level {node.zoom_level}")

        print(f"✅ [DEBUG] Reached node: {node.value} (L{node.level}) with children: {[c.value for c in node.children]}")

        # ──────────────────────────────
        # Step 6: always expand children at final node
        next_level = node.level

        print(f"✅ [DEBUG] Expanding node: {node.value} (L{node.level}) Max {max_level} createmode :{create} rlevels: {rlevels}")

        if next_level <= max_level and create:
            children_type = str(elevels[next_level])
            print(f"🌿 [DEBUG] Expanding children of {node.level}-{node.value} as {children_type}")

            # Execute primary expansion pass
            try:
                if node.level < 4:
                    node.create_map_branch(rlevels)
                else:
                    node.create_data_branch(rlevels)
            except Exception as e:
                print(f"⚠️ [DEBUG] Primary branch expansion failed: {e}")

            # 🌟 FIX: Exhaustively fire secondary strategy if current level specifies bivalent parsing with a "/"
            if "/" in children_type:
                print(f"🔄 [DEBUG] Level is bivalent ('{children_type}'). Expanding secondary alternative branches for final node {node.value}")
                try:
                    if node.level < 4:
                        node.create_data_branch(rlevels)
                    else:
                        node.create_map_branch(rlevels)
                except Exception as e:
                    print(f"⚠️ [DEBUG] Secondary bivalent expansion failed: {e}")

        return node


    def get_feature_layers(self, rlevels, static=False):
        """
        Retrieves map layers for the node's parent, siblings(of the same type), children(of all types), and grandchildren(of all types),
        along with marker assets and dynamic ghost task progress overlays.
        """
        from flask import session
        from layers import make_feature_layers, ExtendedFeatureGroup
        from elections import CurrentElection
        from baked_data import BakedDataManager
        import state # Ensure global state is imported for branchcolours

        # Guard & Unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"
        (c_election, elevels), = rlevels.items()

        # Load election contexts and task tracking configurations
        current_election = CurrentElection.load(c_election)
        task_tags, _, _ = current_election.get_tags()

        factory = make_feature_layers()
        selected = []
        used_keys = set()
        used_tags = set()

        def get_safe_tag_layer(tag_code, tag_desc):
            display_name = f"Task Overlay: [{tag_code}] {tag_desc}"
            if tag_code in used_tags:
                display_name = f"{display_name} (Upper)"
            used_tags.add(tag_code)

            tag_layer = ExtendedFeatureGroup(
                name=display_name,
                overlay=True,
                control=True,
                show=True
            )
            tag_layer.options = tag_layer.options or {}
            tag_layer.options.update({
                "tag": tag_code,
                "layer_type": "ghost"
            })
            return tag_layer

        def get_safe_level_layers(level_idx):
            raw_key = elevels.get(level_idx)
            if not raw_key:
                return []  # Return empty list instead of None for easier iteration downstream

            # 1. Unpack bi-valent keys if a slash exists, otherwise make a single-element list
            keys_to_process = raw_key.split('/') if '/' in raw_key else [raw_key]
            resolved_layers = []

            for key in keys_to_process:
                # 2. Check if this specific sub-key is missing from the factory configuration
                if key not in factory:
                    print(f"⚠️ Warning: Component layer '{key}' from raw key '{raw_key}' not found in factory.")
                    continue

                # 3. Handle name collisions using your used_keys tracking logic
                if key in used_keys:
                    # Dynamically instantiate a fresh layer instance
                    new_layer_instance = make_feature_layers()[key]
                    new_layer_instance.name = f"{new_layer_instance.name} (Upper)"
                    resolved_layers.append(new_layer_instance)
                else:
                    used_keys.add(key)
                    resolved_layers.append(factory[key])

            return resolved_layers

        # -------------------------------------------------
        # 📂 BASELINE DATA: Establish Base Node Lists Upfront
        # -------------------------------------------------
        if session.get("accumulate", False):
            childnode_ids = session.get("accumulated_nodes", [])
            childnodelist = [TREK_NODES_BY_ID.get(nid) for nid in childnode_ids if nid in TREK_NODES_BY_ID]
        else:
            childnodelist = [self]

            # -------------------------------------------------
        # 🔍 QUICK DEBUG: Let's see what the nodes actually have
        # -------------------------------------------------
        if childnodelist:
            test_node = childnodelist[0]
            print(f"DEBUG NODE: type={getattr(test_node, 'type', 'MISSING')}, layer_type={getattr(test_node, 'layer_type', 'MISSING')}, key={getattr(test_node, 'key', 'MISSING')}")
        # -------------------------------------------------
        # 1️⃣ Grandchild Layer (Level + 2)
        # -------------------------------------------------
        totalleaf = 0
        grandchildnodelist = []

        if self.level < 5:  # Under level 5, level + 2 safely exists
            grandchild_layers = get_safe_level_layers(self.level + 2)

            for grandchild_layer in grandchild_layers:
                # 1. 🔎 Check if grandchildren exist for this specific layer type
                has_grandchildren = False
                if childnodelist:
                    has_grandchildren = any(
                        gc.type == grandchild_layer.type
                        for child in childnodelist
                        for gc in child.children
                    )

                if has_grandchildren:
                    print(f"Processing layer asset: {grandchild_layer.name}")

                    # 2. Extract only the grandchildren that belong to this specific layer type
                    layer_specific_grandchildren = [
                        gc for child in childnodelist
                        for gc in child.children
                        if gc.type == grandchild_layer.type
                    ]

                    if layer_specific_grandchildren:
                        # 3. Capture how many items were successfully written for THIS layer
                        leaf_count = grandchild_layer.create_layer(rlevels, layer_specific_grandchildren, static=False)
                        totalleaf += leaf_count

                        # 4. 🛡️ Only add to the map if elements were actually created!
                        if leaf_count > 0 or (hasattr(grandchild_layer, '_children') and grandchild_layer._children):
                            grandchild_layer.show = True
                            selected.append(grandchild_layer)

                            # Keep track of all processed grandchildren across both layers for reference downstream
                            grandchildnodelist.extend(layer_specific_grandchildren)
        # -------------------------------------------------
        # 2️⃣ Child Layer (Level + 1) -> 🏁 FIXED: Level Guard against RAM Spikes
        # -------------------------------------------------
        if self.level < 6:
            child_layers = get_safe_level_layers(self.level + 1)
            if child_layers and childnodelist:
                for child_layer in child_layers:

                    layer_specific_children = []

                    # 🚀 LEVEL GUARD: Only do deep extraction if we are at Constituency level (3) or deeper.
                    # Otherwise, skip the intensive filtering to protect server memory.
                    if self.level >= 3:
                        for node in childnodelist:
                            if node.type == child_layer.type:
                                layer_specific_children.append(node)
                            elif hasattr(node, 'children') and node.children:
                                for ch in node.children:
                                    if ch.type == child_layer.type:
                                        layer_specific_children.append(ch)

                    # If we are high up (Level 0, 1, 2), safely default to standard child lists
                    if not layer_specific_children:
                        layer_specific_children = childnodelist

                    leaf_count = child_layer.create_layer(rlevels, layer_specific_children, static=False)
                    totalleaf += leaf_count

                    if leaf_count > 0 or (hasattr(child_layer, '_children') and child_layer._children):
                        child_layer.show = True
                        selected.append(child_layer)

        # -------------------------------------------------
        # 3️⃣ Sibling Layer (Current Level) -> 🏁 FIXED: Type-Filter Parent Target
        # -------------------------------------------------
        if self.level > 0:
            sibling_layers = get_safe_level_layers(self.level)
            if sibling_layers and self.parent:
                for sibling_layer in sibling_layers:
                    # Ensure the sibling generation is scoped to the target layer's structural type
                    if self.type == sibling_layer.type:
                        sibling_layer.create_layer(rlevels, [self.parent], static=False)
                        selected.append(sibling_layer)

        # -------------------------------------------------
        # 4️⃣ Parent Layer (Level - 1) -> 🏁 FIXED: Type-Filter Grandparent Target
        # -------------------------------------------------
        if self.level > 1:
            parent_layers = get_safe_level_layers(self.level - 1)
            if parent_layers and self.parent and self.parent.parent:
                for parent_layer in parent_layers:
                    # Ensure parent layer only builds if types align
                    if self.parent.type == parent_layer.type:
                        parent_layer.create_layer(rlevels, [self.parent.parent], static=False)
                        selected.append(parent_layer)


        # -------------------------------------------------
        # 5️⃣ Marker Asset Layer
        # -------------------------------------------------
        if "marker" in factory:
            selected.append(factory["marker"])

        # -------------------------------------------------
        # 6️⃣ ELECTOR DEMOGRAPHICS / HIGHLIGHTS LAYERS
        # -------------------------------------------------
        from folium.plugins import MarkerCluster

        target_highlight_nodes = grandchildnodelist if grandchildnodelist else childnodelist

        if target_highlight_nodes:
            # --- A. Postal Voters Layer ---
            postal_layer = ExtendedFeatureGroup(
                name="Elector Overlay: [AV] Postal Voters",
                overlay=True,
                control=True,
                show=False
            )
            postal_layer.options = postal_layer.options or {}
            postal_layer.options.update({
                "tag": "AV",
                "layer_type": "av_highlight"
            })

            postal_cluster = MarkerCluster(name="Postal Voters", control=False).add_to(postal_layer)

            postal_markers_count = 0
            for target_node in target_highlight_nodes:
                postal_markers_count += postal_layer.add_tag_layer(
                    rlevels=rlevels,
                    node=target_node,
                    tags=['AV'],
                    operator='OR',
                    layer_name="Postal Voter",
                    icon_color="purple", icon_name="envelope", header_color="#7C3AED",
                    target_cluster=postal_cluster
                )

            if postal_markers_count > 0:
                selected.append(postal_layer)

            # --- B. Pledge Highlights Layer ---
            pledge_layer = ExtendedFeatureGroup(
                name="Elector Overlay: [VI] Pledged Voters",
                overlay=True,
                control=True,
                show=False
            )
            pledge_layer.options = pledge_layer.options or {}
            pledge_layer.options.update({
                "tag": "VI",
                "layer_type": "vi_highlight"
            })

            pledge_cluster = MarkerCluster(name="Reform Pledges", control=False).add_to(pledge_layer)

            pledge_markers_count = 0
            for target_node in target_highlight_nodes:
                pledge_markers_count += pledge_layer.add_tag_layer(
                    rlevels=rlevels,
                    node=target_node,
                    tags=['PL'],
                    operator='OR',
                    layer_name="Reform Pledge",
                    icon_color="blue", icon_name="users", header_color="#2563EB",
                    target_cluster=pledge_cluster
                )

            if pledge_markers_count > 0:
                selected.append(pledge_layer)

        # -------------------------------------------------
        # 7️⃣ Ghost Task Progress Overlays
        # -------------------------------------------------
        baked_manager = BakedDataManager()
        baked_dict = baked_manager.load()
        active_tags = dict(task_tags)
        active_tags["VI"] = "Voter Intention"

        for tag_code, tag_desc in active_tags.items():
            tag_layer = get_safe_tag_layer(tag_code, tag_desc)
            tag_layer.add_ghosts(
                tag_code=tag_code,
                baked_dict=baked_dict,
                nodes=childnodelist,
                branchcolours=state.branchcolours
            )
            selected.append(tag_layer)

        return list(reversed(selected)), totalleaf

    def sumupVI(self,viValue):
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

    def updateTurnout(self,elevels):
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

            children = parent.childrenoftype(elevels[parent.level])
            values = [c.turnout for c in children if c.turnout is not None]
            parent.turnout = sum(values) / len(values) if values else None

            casnode = parent

        return

    def updateGOTV(self, gotv_pct, elevels):
        """
        Compute absolute GOTV target:
            gotv = 0.5 * votes_cast + (gotv_pct / 100)
        """
        # Guard: Ensure we have exactly one election to unpack

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
            children = parent.childrenoftype(elevels[parent.level])

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

        party = state.normalname(party)

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


    def updateCandidates(self,elevels):
        """Fill self.candidates from the global Candidates dict."""
        from state import Candidates

        if self.type == "division":
            # Safely get candidate dict or default to empty dict
            self.candidates = Candidates.get("division", {}).get(self.value, {})
            print(f"[DEBUG] Candidate update for {self.value}: {self.candidates}")



    def updateElectorate(self, elevels):
        from state import LastResults
        # Guard: Ensure we have exactly one election to unpack

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
                    for c in parent.childrenoftype(elevels[parent.level])
                )
            casnode = parent

        return

    def updateHouses(self,elevels,pop):
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
            for x in sumnode.parent.childrenoftype(elevels[sumnode.level]):
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


    def create_name_nodes(self,resolved_levels,gotv_pct,nodetype,namepoints,ending):

        # Guard: Ensure we have exactly one election to unpack
        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # The clean unpack you like
        (c_election, elevels), = resolved_levels.items()


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

            newname = state.normalname(limb['Name'])

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
                    origin=c_election,
                    node_type=nodetype
                )
                egg = self.add_Tchild(child_node=newnode, etype=nodetype, elect=c_election)

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

            egg.updateTurnout(elevels)
            egg.updateElectorate(elevels)
            egg.updateGOTV(gotv_pct, elevels)

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


    def create_data_branch(self, resolved_levels):
        from elector import electors
        from state import Treepolys, Fullpolys
        import elections

        # Guard: Ensure we have exactly one election to unpack
        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # Clean unpack
        (c_election, elevels), = resolved_levels.items()

        CE = elections.CurrentElection.load(c_election)
        raw_electtype = elevels[self.level + 1]
        print(f"✅ Creating {raw_electtype} Data branch for election {c_election}")

        # ----------------------------------------
        # Load electors from ElectorManager
        # ----------------------------------------
        areaelectors = electors.elector_for_path(resolved_levels, self.mapfile())

        if areaelectors.empty:
            print(f"⚠️ No data from election {c_election} at node {self.value}")
            return []

        gotv_pct = CE['GOTV']

        # 🎯 RESOLVE ALL POSSIBLE DATA TARGET LAYERS (e.g., ["walk", "polling_district"])
        target_layers = []
        if "/" in str(raw_electtype):
            target_layers = [t.strip() for t in raw_electtype.split("/")]
            print(f"🔄 Multi-branch data targets detected: {target_layers}")
        else:
            target_layers = [raw_electtype]

        all_created_data_nodes = []

        # -------------------------------
        # Process each individual data sub-branch
        # -------------------------------
        try:
            from elector import shapecolumn

            suffix_mapping = {
                "polling_district": "-PDS.html",
                "walk": "-WALKS.html",
                "street": "-PRINT.html",
                "walkleg": "-PRINT.html"
            }

            for electtype in target_layers:
                if electtype not in shapecolumn:
                    print(f"⚠️ Unknown elect type variant: {electtype}. Skipping sub-branch.")
                    continue

                colname = shapecolumn[electtype]

                # Ensure the mapped target column actually exists in the elector dataset
                if colname not in areaelectors.columns:
                    print(f"⚠️ Column '{colname}' for type '{electtype}' not found in elector records. Skipping branch.")
                    continue

                print(f"🧭 Processing data branch for sub-type: '{electtype}' using column '{colname}'")

                # Isolate target columns safely
                select_cols = [colname, 'ENOP', 'Long', 'Lat', 'Zone']
                existing_cols = [c for c in select_cols if c in areaelectors.columns]

                df = areaelectors[existing_cols].rename(columns={colname: 'Name'})

                # Skip aggregation if there is no name data to group by
                if df['Name'].dropna().empty:
                    print(f"⚠️ Data column '{colname}' contains only null values for this node territory. Skipping.")
                    continue

                # Aggregation
                agg_dict = {'Lat': 'mean', 'Long': 'mean', 'ENOP': 'count'}
                if 'Zone' in df.columns:
                    agg_dict['Zone'] = 'first'

                nodeelectors = df.groupby(['Name']).agg(agg_dict).reset_index()

                # Node creation for this specific target branch
                branch_nodes = self.create_name_nodes(
                    resolved_levels,
                    gotv_pct,
                    electtype,  # Stamped clean type context passed through
                    nodeelectors,
                    suffix_mapping.get(electtype, "-PRINT.html")
                )

                print(f"📦 Created {len(branch_nodes)} nodes for type '{electtype}'")
                all_created_data_nodes.extend(branch_nodes)

        except Exception as e:
            print("❌ Error during data branch generation:", e)
            import traceback
            traceback.print_exc()
            return []

        print(
            f"✅ Completed Multi-Data Branch for Election: {c_election} "
            f"in area: {self.value} | Total nodes created: {len(all_created_data_nodes)} "
            f"from {len(areaelectors)} base records."
        )

        # Ensure global persistence method is clean
        if 'save_nodes' in globals() or 'save_nodes' in dir(state):
            try:
                save_nodes(TREKNODE_FILE)
            except NameError:
                pass

        return all_created_data_nodes


    def create_map_branch(self, resolved_levels):
        # Imports (keep them here if they are circular)
        from state import Treepolys, Geo_index, branchcolours
        import pandas as pd
        import state
        import elections

        print(f"DEBUG: Entering create_map_branch for {self.value} (Level {self.level})")

        # Guard: Ensure we have exactly one election to unpack
        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # Clean unpack
        (c_election, elevels), = resolved_levels.items()
        raw_electtype = elevels.get(self.level + 1)
        parenttype = self.type

        if not raw_electtype:
            print(f"DEBUG: No child level found for level {self.level + 1}. Exiting.")
            return None

        # RESOLVE ALL POSSIBLE CHILD LAYERS (Handle single strings or "ward/division")
        target_layers = []
        if "/" in str(raw_electtype):
            target_layers = [t.strip() for t in raw_electtype.split("/")]
            print(f"🔄 Multi-branch child target detected: {target_layers}")
        else:
            target_layers = [raw_electtype]

        # Build the self-path key to find our entry in the geoindex
        # e.g., "UNITED_KINGDOM/ENGLAND/SURREY/DORKING_AND_HORLEY"
        my_path_key = self.get_absolute_path_string()

        geo_node = Geo_index.get(my_path_key)
        if not geo_node:
            print(f"⚠️ Warning: Path {my_path_key} not found in Geo_index. Falling back to empty children.")
            return []

        # Get the precise pre-calculated list of child paths from our index
        allowed_child_paths = geo_node.get("children", [])

        CE = elections.CurrentElection.load(c_election)
        gotv_pct = CE.get('GOTV', 0)
        all_created_children = []
# 🔄 LOOP OVER EVERY TARGET LAYER (e.g., 'constituency')
        for electtype in target_layers:
            ChildPolylayer = Treepolys.get(electtype)

            if ChildPolylayer is None or ChildPolylayer.empty:
                print(f"⚠️ Spatial table '{electtype}' is empty. Skipping.")
                continue

            # Extract just the normalized final token from the Geo_index children paths
            # This yields exact keys like: 'DORKING_AND_HORLEY', 'GUILDFORD', etc.
            valid_child_keys = {
                path.split('/')[-1].strip().upper()
                for path in allowed_child_paths
            }

            print(f"🎯 Target keys expected from Geo_index: {valid_child_keys}")

            # Vectorized normalization on the spatial dataframe to ensure apples-to-apples matching
            # We apply state.normalname to each row name dynamically
            ChildPolylayer_normalized = ChildPolylayer.copy()
            ChildPolylayer_normalized['NORMALIZED_NAME'] = ChildPolylayer_normalized['NAME'].apply(
                lambda x: str(state.normalname(x)).strip().upper()
            )

            # Filter the dataframe using the normalized strings
            selected_children = ChildPolylayer_normalized[
                ChildPolylayer_normalized['NORMALIZED_NAME'].isin(valid_child_keys)
            ]

            print(f"📦 Found {len(selected_children)} / {len(valid_child_keys)} shapefile matches for Surrey.")

            fam_nodes = self.childrenoftype(electtype)
            fam_values = {x.value for x in fam_nodes}

            k = 0
            j = 0

            for _, limb in selected_children.iterrows():
                newname = state.normalname(limb.NAME)

                # Ensure uniqueness within this specific sub-layer type block
                if newname in fam_values:
                    j += 1
                    continue

                # Check if centroid/representative point coordinates are already baked into geoindex
                # to skip spatial engine evaluation completely. Fallback to geometry calculation if absent.
                # Avoid leading double slashes at the root level ("UNITED_KINGDOM/ENGLAND")
                if my_path_key == "UNITED_KINGDOM":
                    child_path_key = f"UNITED_KINGDOM/{newname}"
                else:
                    child_path_key = f"{my_path_key}/{newname}"

                baked_roid = Geo_index.get(child_path_key, {}).get("roid")

                if baked_roid:
                    here = tuple(baked_roid)
                else:
                    centroid_point = limb.geometry.representative_point()
                    here = (centroid_point.y, centroid_point.x)

                # Create the TreeNode stamped explicitly with this unique layer type
                egg = TreeNode(
                    value=newname,
                    fid=limb.FID,
                    roid=here,
                    origin="ONS_MAPS",
                    node_type=electtype
                )

                # Attach node structurally to parent
                egg = self.add_Tchild(child_node=egg, etype=electtype, elect=c_election)

                block = pd.DataFrame()
                egg.bbox, egg.latlongroid = egg.get_bounding_box(electtype, block)

                # Set branch color based on absolute index
                color_idx = (len(all_created_children) + k) % len(branchcolours)
                egg.defcol = branchcolours[color_idx]

                try:
                    egg.updateParty()
                    egg.updateCandidates(elevels)
                    egg.updateTurnout(elevels)
                    egg.updateElectorate(elevels)
                    egg.updateGOTV(gotv_pct, elevels)

                    fam_nodes.append(egg)
                    all_created_children.append(egg)
                    fam_values.add(newname)
                    k += 1

                except Exception as e:
                    print(f"❌ ERROR during node update for {newname} ({electtype}): {str(e)}")
                    self.remove_child(egg)
                    raise

            print(f"✅ Layer '{electtype}': Added {k}, skipped duplicate {j}. Total branch size: {len(fam_nodes)}")

        if not all_created_children:
            print(f"⚠️ Warning: No children created anywhere under {self.value} for config target: {raw_electtype}")

        return all_created_children

    def create_node_map(self, resolved_levels, static=False):
        global SERVER_PASSWORD

        from folium import IFrame, Element  # 💡 Explicitly ensured Element is present
        from state import LEVEL_ZOOM_MAP, Treepolys, Fullpolys
        from layers import make_counters, FEATURE_LAYER_SPECS, ExtendedFeatureGroup

        import hashlib
        import re
        from pathlib import Path

        import json

        def generate_map_accordions(specs: list[dict]) -> str:
            """Generates a modular HTML/JS injection string for Folium maps.

            Each spec dict requires:
                - 'prefix': The layer text string to match and strip (e.g., 'Data Overlay:')
                - 'title': The visible heading text for the accordion (e.g., '📊 Task
                Progress')
            """

            css_content = """
            <style>
                .custom-map-accordion {
                    background-color: #ffffff;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    margin-top: 8px;
                    font-family: "Helvetica Neue", Arial, Helvetica, sans-serif;
                }
                .custom-map-accordion summary {
                    padding: 6px 10px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 12px;
                    color: #333;
                    outline: none;
                    list-style: none;
                }
                .custom-map-accordion summary::-webkit-details-marker {
                    display: none;
                }
                .custom-map-accordion-content {
                    padding: 5px 0 10px 0;
                    max-height: 200px;
                    overflow-y: auto;
                    border-top: 1px solid #eee;
                }
                .custom-map-accordion-content label {
                    display: block;
                    margin: 0;
                    padding: 3px 10px;
                    font-size: 11px;
                    cursor: pointer;
                }
                .custom-map-accordion-content label:hover {
                    background-color: #f4f4f4;
                }
            </style>
            """

            # 1. Cleanly serialize our specs list to a valid JSON string
            js_specs_json = json.dumps(specs)

            # 2. Keep this as a PURE string (NO f-string prefix).
            # This prevents Python from getting confused by JavaScript template literals.
            js_script = """
            <script>
            document.addEventListener("DOMContentLoaded", function() {
                // We will replace this placeholder string using Python's .replace()
                const specs = __ACCORDION_SPECS_PLACEHOLDER__;

                var observer = new MutationObserver(function(mutations, me) {
                    var controlContainer = document.querySelector('.leaflet-control-layers-overlays');
                    if (controlContainer) {
                        specs.forEach(spec => setupAccordion(controlContainer, spec));
                        me.disconnect();
                        return;
                    }
                });

                observer.observe(document.body, { childList: true, subtree: true });

                function setupAccordion(container, spec) {
                    var details = document.createElement('details');
                    details.className = 'custom-map-accordion';
                    details.innerHTML = `<summary>${spec.title}</summary>`;

                    var contentDiv = document.createElement('div');
                    contentDiv.className = 'custom-map-accordion-content';
                    details.appendChild(contentDiv);

                    var labels = container.querySelectorAll('label');
                    var foundAny = false;

                    labels.forEach(function(originalLabel) {
                        if (originalLabel.innerText.includes(spec.prefix)) {
                            foundAny = true;
                            originalLabel.style.display = 'none';

                            var proxyLabel = document.createElement('label');
                            var cleanName = originalLabel.innerText.replace(spec.prefix, '').trim();

                            var realInput = originalLabel.querySelector('input');
                            var isChecked = realInput ? realInput.checked : false;

                            proxyLabel.innerHTML = `
                                <input type="checkbox" ${isChecked ? 'checked' : ''}>
                                <span>${cleanName}</span>
                            `;

                            var proxyInput = proxyLabel.querySelector('input');
                            proxyInput.addEventListener('change', function() {
                                if (realInput) {
                                    realInput.click();
                                }
                            });

                            contentDiv.appendChild(proxyLabel);
                        }
                    });

                    if (foundAny) {
                        container.appendChild(details);
                    }
                }
            });
            </script>
            """

            # 3. Inject the config safely using string replacement
            final_js = js_script.replace("__ACCORDION_SPECS_PLACEHOLDER__", js_specs_json)

            return css_content + final_js

        # Guard: Ensure we have exactly one election to unpack
        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # The clean unpack
        (c_election, elevels), = resolved_levels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        # ... imports ...

        accumulate = session.get("accumulate", False)

        # 1. DETERMINE CONTEXT (Who is the "Owner" of this map?)
        # If accumulating, we act as if we are the parent

        # 2. SET UP FILE PATHS
        # Use render_node for the filename so child updates overwrite the parent map
        mapfile_name = self.file(elevels)
        target = self.locfilepath(mapfile_name)

        # 3. SET UP VISUALS (Title and Bounding Box)
        title = self.value
        # Use the parent's centroid and bbox so the map doesn't "zoom in" to just one child
        map_center = self.latlongroid
        map_zoom = LEVEL_ZOOM_MAP.get(self.type, 13)
        map_bbox = self.bbox

        # --- Create the map using the render_node's location ---
        FolMap = folium.Map(
            location=map_center,
            zoom_start=map_zoom,
            width='100%',
            height='800px'
        )
        print(f"___AFTER map creation: on elections.route {elections.route()} acc: {accumulate} creating file: ", self.mapfile())

        counters = make_counters()

            # 2️⃣ Create fresh FeatureGroups for THIS map

        # 3️⃣ Select which layers to render for this map
        flayers, totalleaf = self.get_feature_layers(
            rlevels=resolved_levels,
            static=static
        )

        # Configure only ghosts for testing
        accordion_configurations = [
            {"prefix": "Task Overlay:", "title": "📊 Task Progress"},
            {"prefix": "Elector Overlay:", "title": "📊 Elector Filters"},
        ]

        # Generate the snippet and inject it right before returning your map
        accordion_html = generate_map_accordions(accordion_configurations)


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

        # --- Title for the map

        if accumulate and self.parent is not None:
            title = self.parent.value
        else:
            title = self.value

        title_html = f'''
        <h2 style="
            z-index: 1100;
            color: black;
            position: absolute;
            top: 10px;
            left: 50px;
            font-variant: small-caps;
            font-size: 12px;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        ">{title} MAP</h2>
        '''
        import base64
    # 1. Convert PNG to Base64 (Keep as is)
        with open(LOGO_FILE, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode('utf-8')

        # 2. Updated Styles (Remove 'position: fixed' and 'bottom/left')
        # We let Leaflet handle the positioning now.
        logo_styles = f"""
            <style>
                .leaflet-logo-container {{
                    height: 60px;
                    width: 160px;
                    background-color: transparent;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    pointer-events: none;
                    margin-bottom: 10px !important; /* Spacing from map edge */
                    margin-left: 10px !important;
                }}

                .leaflet-logo-icon {{
                    width: 100%;
                    height: 100%;
                    background-color: #17B9D1; /* Your brand color */
                    -webkit-mask-image: url("data:image/png;base64,{b64_str}");
                    mask-image: url("data:image/png;base64,{b64_str}");
                    -webkit-mask-size: contain;
                    mask-size: contain;
                    -webkit-mask-repeat: no-repeat;
                    mask-repeat: no-repeat;
                    -webkit-mask-position: center;
                    mask-position: center;
                }}
            </style>
        """

        # Add this to your Python map generation string

        logo_css_injection = f"""
        <style>
            .leaflet-bottom.leaflet-left::after {{
                content: "";
                display: block;
                width: 60px;
                height: 60px;
                margin-left: 10px;
                margin-bottom: 10px;
                background-color: #00aaff;

                /* 💡 Dynamic logo file path injected here */
                -webkit-mask: url('{LOGO_FILE}') no-repeat center;
                mask: url('{LOGO_FILE}') no-repeat center;
                -webkit-mask-size: contain;
                mask-size: contain;

                pointer-events: auto;
            }}
        </style>
        """

        # --- Search bar with map detection and one single searchMap() function
        search_bar_html = """
            <style>
                #customSearchBox {
                    position: absolute; top: 10px; left: 50px; z-index: 1000;
                    background: white; padding: 8px 10px; border: 1px solid #ccc;
                    display: flex; flex-direction: column; gap: 5px;
                    font-family: sans-serif;
                }
                #customSearchBox input, #customSearchBox button { padding: 4px; font-size: 14px; }
            </style>

            <div id="customSearchBox">
                <div style="display: flex; gap: 8px;">
                    <input type="text" id="searchInput" placeholder="Search..." />
                    <button onclick="searchMap()">Search</button>
                    <button id="backToCalendarBtn" onclick="handleCalendarClick()">📅 Calendar</button>
                </div>
            </div>
            """

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



        # --- Inject map finding , click handling and layer control adding functionality

        fmap_tags_js = r"""
            <script>
            (function() {

                console.log("🗺️ fmap_marker_js loaded (Layer Control Dictionary Search & Click Binding)");

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

                            // 🎯 RIGHT HERE: Bind your custom reverse-geocoding click workflow
                            // the exact millisecond the map is discovered in memory.
                            if (typeof window.handleMapClick === 'function') {
                                console.log("⚓ Binding handleMapClick directly via detection hook.");
                                window.fmap.on('click', window.handleMapClick);
                            } else {
                                console.warn("⚠️ handleMapClick function not found in scope during map binding.");
                            }

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

                    for (const key in window) {
                        if (!window.hasOwnProperty(key)) continue;
                        const val = window[key];

                        if (key.startsWith("layer_control_") && val && val.overlays) {
                            if (val.overlays.marker) {
                                window.MarkerLayer = val.overlays.marker;
                                console.log(`🔥 'marker' Layer found via Layer Control Dictionary: ${key}`);
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
            async function handleMapClick(e) {

                if (!window.fmap) return;

                const lat = e.latlng.lat;
                const lng = e.latlng.lng;

                console.log("📍 Map click for add-place:", lat, lng);

                let result = null;

                try {
                    result = await window.reverseGeocode(lat, lng);
                } catch (err) {
                    console.error("Reverse geocode failed:", err);
                }

                // 🔑 Send to your existing modal system
                window.parent.postMessage({
                    type: "mapLocationSelected",
                    lat,
                    lng,
                    house_number: result?.house_number || "",
                    road: result?.road || "",
                    suburb: result?.suburb || "",
                    city: result?.city || "",
                    postcode: result?.postcode || ""
                }, "*");
            }
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
        popupclosure_injection_js = """
            <script>
            // ------------------------------------------------------------------
            // IFRAME CLIENT SCRIPTS (Injected into Folium Map Document)
            // ------------------------------------------------------------------
            (function() {
                console.log("🚀 [IFRAME MAP] Popup closure injection script executing...");

                function signalParentToClose() {
                    console.log("📤 [IFRAME MAP] Dispatching close request upward to parent window...");
                    try {
                        window.parent.postMessage('TRIGGER_PARENT_SYNC_CLOSE', '*');
                    } catch (err) {
                        console.error("💥 [IFRAME MAP] Failed to transmit postMessage:", err);
                    }
                }

                // Wrap in an instant checker as well as DOMContentLoaded to ensure we catch the elements
                function initializeListeners() {
                    console.log("🔧 [IFRAME MAP] Setting up interaction intercepts...");

                    // 1. BACKDROP INTERCEPT
                    var modalOverlay = document.getElementById('modal-overlay');
                    if (modalOverlay) {
                        console.log("✅ [IFRAME MAP] Local 'modal-overlay' element discovered inside iframe.");
                        modalOverlay.addEventListener('click', function(event) {
                            if (event.target === modalOverlay) {
                                console.log("📣 [IFRAME BACKDROP] Overlay surface clicked.");
                                signalParentToClose();
                            }
                        });
                    } else {
                        console.warn("⚠️ [IFRAME MAP] 'modal-overlay' was not found inside this iframe document. (Ignore this if the overlay lives on your parent template page instead)");
                    }

                    // 2. GLOBAL WINDOW KEYDOWN INTERCEPT (CAPTURE PHASE)
                    // Using 'true' at the end forces this listener to trigger on the way down,
                    // preventing Leaflet from consuming the event via stopPropagation().
                    window.addEventListener('keydown', function(event) {
                        if (event.key === 'Escape' || event.keyCode === 27) {
                            console.log("⌨️ [IFRAME WINDOW KEYDOWN] Escape key detected in Capture Phase.");

                            var activeLeafletPopup = document.querySelector('.leaflet-popup');
                            var overlay = document.getElementById('modal-overlay');

                            // Let's print out what we see so you know exactly why it passes or fails
                            console.log("🔍 [IFRAME STATE] Popup present:", !!activeLeafletPopup, " | Local Overlay present:", !!overlay);

                            // We intercept unconditionally on Escape to be safe, or you can restore your specific conditions here
                            console.log("📣 [IFRAME KEYDOWN] Intercepting Escape, forcing parent notify.");
                            event.preventDefault();
                            event.stopPropagation();
                            signalParentToClose();
                        }
                    }, true); // <-- TRUE activates the high-priority Capture phase!
                }

                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', initializeListeners);
                } else {
                    initializeListeners();
                }
            })();
            </script>
            """
        # 💡 NEW INJECTION: Compile-time 0ms Direct Object Lookup Registry Index
        # This ties into your existing map detection lifecycle to prevent race conditions.
# 💡 CORRECTED INJECTION: Property-Aligned Vector Compiler Index
        fast_index_js = """
            <script>
            (function() {
                window.regionLayerCache = {};

                function buildCompiledLayerIndex() {
                    if (!window.fmap) {
                        // Re-poll if map isn't instantiated yet
                        setTimeout(buildCompiledLayerIndex, 50);
                        return;
                    }

                    let indexedCount = 0;
                    window.fmap.eachLayer(function(layer) {
                        if (!layer || layer.is_ghost) return;

                        // 🎯 Exactly mirroring your working property fallback chain
                        const p = layer.feature?.properties;
                        const rawId = p?.region_id || p?.name || p?.id;

                        if (rawId && layer.feature?.geometry) {
                            const cleanId = String(rawId).trim().toUpperCase();
                            window.regionLayerCache[cleanId] = layer;
                            indexedCount++;
                        }
                    });
                    console.log("⚡ Fast Index Module Ready. Geometries indexed:", indexedCount);
                }

                document.addEventListener("DOMContentLoaded", buildCompiledLayerIndex);
            })();
            </script>
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

        FolMap.get_root().html.add_child(folium.Element(logo_css_injection))

        # 💡 Injected new static dictionary building capability cleanly into page generation blocks
        FolMap.get_root().html.add_child(folium.Element(fast_index_js))
        # Add popupclosure call to your Folium map
        FolMap.get_root().html.add_child(folium.Element(popupclosure_injection_js))
        # Add layer control accordion to your Folium map


        FolMap.get_root().header.add_child(folium.Element(accordion_html))

        # Add the LatLngPopup plugin
#            FolMap.add_child(folium.LatLngPopup())

        # Add custom CSS/JS
        FolMap.add_css_link("electtrekprint", "https://newbrie.github.io/Electtrek/static/print.css")
        FolMap.add_css_link("electtrekstyle", "https://newbrie.github.io/Electtrek/static/style.css")
        FolMap.add_js_link("electtrekmap", "https://newbrie.github.io/Electtrek/static/map.js")


        # Fit map to bounding box
        # 4. APPLY BOUNDS (Consolidated)
        if map_bbox:
            try:
                # Destructure and validate coordinates in one go
                (lat1, lon1), (lat2, lon2) = map_bbox

                if [lat1, lon1] == [lat2, lon2]:
                    # It's a single point, not a box
                    FolMap.location = map_center
                    FolMap.zoom_start = map_zoom
                else:
                    # Valid box
                    FolMap.fit_bounds([[lat1, lon1], [lat2, lon2]], padding=(10, 10))

            except (TypeError, ValueError, IndexError):
                print(f"⚠️ BBox format invalid: {map_bbox}. Falling back to centroid.")
                FolMap.location = map_center
        else:
            print("ℹ️ No BBox provided; using default center/zoom.")
        # 5. SAVE TO THE PARENT'S PATH
        FolMap.save(target)
        save_nodes(TREKNODE_FILE)
        print(f"✅ Map Saved to: {target} (Accumulate: {accumulate}) elections.route: {elections.route()}")
        return FolMap, totalleaf



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

    def _build_absolute_path_list(self):
        """
        Core structural engine. Climbs the tree from the current node
        up to the root, returning an ordered list of path elements.
        Example: ['UNITED_KINGDOM', 'ENGLAND', 'SURREY', 'SURREY_HEATH']
        """
        parts = []
        p = self
        while p:
            if p.level > 0 and p.value:
                # Strip any slashes out of the node value just in case
                parts.insert(0, str(p.value).strip("/"))
            p = p.parent

        parts.insert(0, "UNITED_KINGDOM")
        return parts


    def get_absolute_path_string(self):
        """
        Returns a clean dictionary key string for geoindex and data lookups.
        Example: 'UNITED_KINGDOM/ENGLAND/SURREY/SURREY_HEATH'
        """
        return "/".join(self._build_absolute_path_list())

    def get_url(self):
        """
        Returns a valid, web-safe Flask URL string for frontend routing.
        Example: '/thru/UNITED_KINGDOM/ENGLAND/SURREY/SURREY_HEATH'
        """
        from flask import url_for
        full_path_string = "/".join(self._build_absolute_path_list())
        return url_for('thru', path=full_path_string)

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

        child_node.type = etype

        registry = TREK_NODES_BY_ID

        print(f"[DEBUG] registry id in add_Tchild: {id(TREK_NODES_BY_ID)}")
        print(f"[DEBUG] registry size in add_Tchild: {len(TREK_NODES_BY_ID)}")
        print(f"\n🟢 [DEBUG] add_Tchild called for node '{child_node.value}' ({child_node.nid}), type: {child_node.type}")
        print(f"   - Parent: {self.value if self else 'None'}")
        print(f"   - Registry size before: {len(registry)}")

        # ---------------------------------------------------------
        # 1️⃣ Prevent multiple root country nodes
        # ---------------------------------------------------------
        if child_node.parent is None and etype == "country":
            # Check if any existing node of type country is already a root
            for existing in registry.values():
                if existing.type == "country" and existing.parent is None:
                    raise ValueError(
                        f"Cannot add another root node of type 'country': {child_node.value}"
                    )


        # ---------------------------------------------------------
        # 2️⃣ Prevent duplicates of same type + value
        # ---------------------------------------------------------
        found_in_registry = False
        for nid, existing in registry.items():
            if existing.type != etype:
                continue

            if existing.parent is None and etype == "country":
                continue  # skip root country

            is_ons_map = getattr(child_node, "origin", None) == "ONS_MAPS"
            match_found = False
            if is_ons_map and existing.fid == child_node.fid:
                match_found = True
            elif existing.value == child_node.value:
                match_found = True

            if match_found:
                print(f"🔍 [DEBUG] Node matched in registry: {existing.value} ({existing.nid})")
                child_node = existing
                found_in_registry = True
                break

        print(f"   - Found in registry: {found_in_registry}")

        # ---------------------------------------------------------
        # 3️⃣ Attach to parent
        # ---------------------------------------------------------
        if child_node not in self.children:
            if child_node.parent and child_node.parent is not self:
                # Detach from old parent
                child_node.parent.children.remove(child_node)
            child_node.parent = self
            self.children.append(child_node)
            print(f"✅ Linked {child_node.value} to {self.value} (children now: {len(self.children)})")
        else:
            # Already attached
            child_node.parent = self

        # ---------------------------------------------------------
        # 4️⃣ Register node if new
        # ---------------------------------------------------------
        if child_node.nid not in registry:
            registry[child_node.nid] = child_node
            print(f"💾 Registered new node {child_node.value} ({child_node.nid})")
        else:
            print(f"ℹ️ Node {child_node.value} ({child_node.nid}) already in registry")
        save_nodes(TREKNODE_FILE)
        return child_node


    def create_streetsheet(self, c_election, rlevels, electorwalks):
        """
        Generates an HTML streetsheet for a given walk/polling district.
        Uses Flask's render_template safely inside an app context.
        """
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()

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
        mapfile = f"/upbut/{self.parent.mapfile()}"

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

    def path_intersect(self, path, elevels):
        # start at the leaf of path 1 and test membership of path 2
        first = state.state.stepify(self.dir+"/"+self.file(elevels))
        second = state.state.stepify(path)
        print("intersecting paths ",self.dir+"/"+self.file(elevels), path)
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
