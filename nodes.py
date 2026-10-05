from config import workdirectories, DATA_FILE, LOGO_FILE,TREKNODE_FILE, ELECTOR_FILE, GENESYS_FILE, TREEPOLY_FILE, GEO_INDEX_FILE
import os
import state
import json
import logging
import pandas as pd
import geopandas as gpd
import pickle
from flask import session
from flask import request, redirect, url_for, has_request_context, render_template, current_app
from layers import  ExtendedFeatureGroup
from layers import MAP_LAYERS
import elections
from folium import Map, Element
import folium
import uuid
from pathlib import Path
import sys
from datetime import datetime, time
import re



_MASTER_ROOT = None


def build_area_tree(node_path, geo_index, max_depth=3):
    """
    Pass ANY full node_path (even a deep constituency path).
    It automatically finds the County level and builds the tree from there down.
    """
    parts = node_path.split("/")

    # Automatically slice the path to the county level (index 2 / 3 parts: country/nation/county)
    if len(parts) >= 3:
        county_path = "/".join(parts[:3])
    else:
        county_path = node_path

    # Helper function to recursively build the tree downward from the county
    def _recursive_build(path, current_depth):
        node = geo_index.get(path)
        if not node:
            return {}

        name = node.get("name", path.split("/")[-1])

        # Stop if we've reached max depth relative to the county
        if current_depth >= max_depth:
            return {name: {}}

        children_dict = {}
        for child_path in node.get("children", []):
            child_tree = _recursive_build(child_path, current_depth + 1)
            if child_tree:
                children_dict.update(child_tree)

        return {name: children_dict}

    # Kick off the recursion starting at the county path (depth 1)
    return _recursive_build(county_path, current_depth=1)

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


def create_root_node() -> "TreeNode":
    return TreeNode(
        value="UNITED_KINGDOM",
        fid= 238,
        roid=(51.23228, -0.57630),
        origin="DEMO",
        node_type="country"
    )

def get_trek_root() -> "TreeNode":
    """Finds the genuine absolute root by its true structural name."""
    global _MASTER_ROOT

    # 1. Return cached pointer if we've already found it
    if _MASTER_ROOT is not None:
        return _MASTER_ROOT

    # 2. Look for the explicit UNITED_KINGDOM anchor in the registry
    for node in TREK_NODES_BY_ID.values():
        if node.value == "UNITED_KINGDOM" and node.parent is None:
            _MASTER_ROOT = node
            return _MASTER_ROOT

    # 3. Fallback/Creation if it doesn't exist yet
    root = create_root_node()
    TREK_NODES_BY_ID[root.nid] = root
    _MASTER_ROOT = root

    return root



def parse_slot_key(slot_key):
    """
    Safely converts slot keys like '2026-04-16_5 PM' or '2026-04-16_11:30 AM'
    to a Python datetime object by parsing strings explicitly. Completely
    immune to operating system C-library or locale bugs.
    """
    try:
        # 1. Split date and time blocks cleanly
        date_str, time_str = slot_key.split("_")

        # 2. Extract hours, optional minutes, and AM/PM via regex
        # Strips out all spaces and forces uppercase for reliable matching
        clean_time = time_str.replace(" ", "").upper()
        match = re.match(r"(\d+)(?::(\d+))?(AM|PM)", clean_time)

        if not match:
            raise ValueError(f"Time format unrecognized: {time_str}")

        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)

        # 3. Apply standard 12-to-24 hour conversion mathematically
        if period == "PM" and hour < 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0

        # 4. Extract date fields directly from the ISO string layout
        year, month, day = map(int, date_str.split("-"))

        # 5. Build the object natively
        return datetime(year, month, day, hour, minute)

    except Exception as e:
        print(f"❌ [PURE PARSER] Failed to parse slot key {slot_key}: {e}")
        return None

def reset_nodes():
    """Clear all registered nodes (in-place)."""
    TREK_NODES_BY_ID.clear()


def save_nodes(path):
    print(f"[DEBUG] registry id in save_nodes: {id(TREK_NODES_BY_ID)}")
    print(f"[DEBUG] registry size in save_nodes: {len(TREK_NODES_BY_ID)}")
    sum_of_all_nodes = len(TREK_NODES_BY_ID)

    seen_paths = set()

    for node in TREK_NODES_BY_ID.values():
        # Safety Check 1: Missing Parent
        if node.parent and node.parent.nid not in TREK_NODES_BY_ID:
            raise RuntimeError(
                f"Persist invariant violated: {node.value} ({node.nid}) has missing parent {node.parent.nid}"
            )

        # Safety Check 2: Duplicate Node Path collision check
        curr_path = node.node_path
        if curr_path in seen_paths:
            print(f"[WARN] Duplicate node path detected during save: '{curr_path}' (nid: {node.nid})")
        seen_paths.add(curr_path)

        # DEBUG: show candidates before saving
        print(f"💾 [DEBUG] Saving node '{node.value}' ({node.nid}) candidates: {node.candidates}")

    with open(path, "w") as f:
        json.dump([n.to_dict() for n in TREK_NODES_BY_ID.values()], f, indent=2)
        print(f"✅ [DEBUG] All {sum_of_all_nodes} nodes saved to {path}")

def load_nodes(path):
    """
    Load tree nodes from JSON file at `path`, wiring parents/children,
    and building O(1) TREK_NODES_BY_PATH index.
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

    # PASS 1: Create node objects
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

    # PASS 2: Wire relationships
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

    # PASS 3: Build O(1) Path Index now that parent chains are fully linked
    TREK_NODES_BY_PATH.clear()
    for node in TREK_NODES_BY_ID.values():
        TREK_NODES_BY_PATH[node.node_path] = node

    print(f"✅ [DEBUG] Finished wiring {len(TREK_NODES_BY_ID)} nodes across {len(TREK_NODES_BY_PATH)} unique paths")
    return True



def get_last_node(Celect,geoindex, create=True):
    """
    Returns the last node for the current election using 4 sources.
    1st source: election CID (verified to have loaded children).
    2nd source: browser GPS location (redirect if triggered).
    3rd source: stored election sourcepath derived from breadcrumb.
    4th source: stored territory path, resolved via ping_node.

    If `create=False`, do not call ping_node and return root if CID node is unavailable.
    """

    cid = Celect.get("cid")
    cidLat = Celect.get("cidLat")
    cidLong = Celect.get("cidLong")
    here = (cidLat, cidLong) if cidLat is not None and cidLong is not None else None

    # Helper function to verify node has children loaded
    def node_has_children(node):
        if node is None:
            return False
        # Check dictionary, list, or set of children depending on object design
        children = getattr(node, "children", None)
        return bool(children)

    # --- 1. CID lookup (Must have children) ---
    if cid and cid in TREK_NODES_BY_ID:
        last_node = TREK_NODES_BY_ID.get(cid, None)
        if node_has_children(last_node):
            print(f"___under route: {state.route()} return to existing cid: {cid} (children count: {len(last_node.children)})")
            return last_node
        else:
            print(f"⚠️ [CID STALE] Node for cid {cid} has 0 children. Bypassing CID to ping_node...")

    print(f"___under route: {state.route()} no valid CID with children, checking GPS/sourcepath:")

    # --- 2. Resolve location or redirect ---
    here, response = state.resolve_here_or_redirect(here)
    if response:
        return response  # redirect response

    # If create=False is passed, skip ping_node completely as requested in docstring
    if not create:
        print(f"___ create=False flag set. Returning MapRoot.")
        return MapRoot

    # --- 3. Resolve node from sourcepath / territory ---
    sourcepath = Celect.get("mapfiles", [None])[-1]
    steps = state.stepify(sourcepath)

    # Fall back to territory path if sourcepath is missing or too shallow
    if not sourcepath or sourcepath == "" or len(steps) < 6:
        sourcepath = Celect.get("territory", "")

    print(f"___ Last node under {state.route()} for {Celect.name} sourcepath: {sourcepath} create:{create}")

    last_node = MapRoot.ping_node(
        Celect.resolved_levels,
        geoindex,
        sourcepath,
        create=create,
        accumulate=False
    )

    # If ping_node resolved a node, but it still has 0 children, attempt territory ping
    territory_path = Celect.get("territory", "")
    if last_node and not node_has_children(last_node) and sourcepath != territory_path and territory_path:
        print(f"⚠️ [PING RETRY] Node '{last_node.value}' has 0 children. Re-pinging using territory path: {territory_path}")
        last_node = MapRoot.ping_node(
            Celect.resolved_levels,
            geoindex,
            territory_path,
            create=create,
            accumulate=False
        )

    # --- 4. Fallback to root if still missing or childless ---
    if not last_node or not node_has_children(last_node):
        print(f"⚠️ GAP: cid_in_index={cid in TREK_NODES_BY_ID} @FALLING BACK TO MAPROOT cid:{cid} - sp:{sourcepath}")
        print(f"⚠️ @NODE INDEX DUMP: {TREK_NODES_BY_ID}")
        last_node = MapRoot

    print(
        f"___ RETRIEVED LAST DESTINATION - election: {Celect.name} "
        f"NODE {getattr(last_node, 'value', 'ROOT')} at loc: {here} "
        f"using source: {sourcepath}"
    )

    return last_node



def parent_level_for(node_type):
    """
    Returns the level index of the node you must be on
    to list children of `node_type`.
    """
    from elections import LEVELS, LEVEL_INDEX


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
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/walkdownST/{x.mapfile()}&#39;); return false;">{x.value}</a>'
            elif x.type == 'walk':
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/WKdownST/{x.mapfile()}&#39;); return false;">{x.value}</a>'
            else:
                dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/transfer/{x.mapfile()}&#39;); return false;">{x.value}</a>'
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
    # 🔧 FIX: Add the missing imports right here inside the function scope
    import tempfile
    import os
    import json

    abs_path = os.path.abspath(path)
    d = os.path.dirname(abs_path)
    os.makedirs(d, exist_ok=True)

    tmp_name = None
    try:
        # Now 'tempfile' is securely defined in this scope!
        with tempfile.NamedTemporaryFile(mode='w', dir=d, delete=False, encoding='utf-8', suffix='.tmp') as tf:
            tmp_name = tf.name
            json.dump(obj, tf, ensure_ascii=False, indent=4)
            tf.flush()
            os.fsync(tf.fileno())

        os.replace(tmp_name, abs_path)

    except Exception as e:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        raise e

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



def restore_from_persist(Treepolys, geoindex):
    print(f'____Restore from persist under !{state.route()} called to restore nodes and polys! ')

    safe_pickle_load(TREEPOLY_FILE,Treepolys)


    load_nodes(TREKNODE_FILE)

    # Load from file
    safe_json_load(GEO_INDEX_FILE, geoindex)
    print("AFTER LOAD:")
    return

def persist(Treepolys, geoindex):
    atomic_pickle_dump(Treepolys,TREEPOLY_FILE)
    atomic_json_dump(geoindex,GEO_INDEX_FILE)
    return


def get_common_prefix_len(a, b):
    """Returns length of common prefix between lists a and b."""
    min_len = min(len(a), len(b))
    for i in range(min_len):
        if a[i] != b[i]:
            return i
    return min_len




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
        self.defcol = "#006064"
        self.candidates = {}

        # UI
        self.tagno = 1
        self.bbox = []
        self.VR = state.VIC.copy()
        self.VI = state.VIC.copy()


    def visit_node(self, c_elect):
        from state import stepify, pathify
        from elections import CurrentElection
        rlevels = c_elect.resolved_levels
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()

        c_elect['cid'] = self.nid
        c_elect['cidLat'] = self.latlongroid[0]
        c_elect['cidLong'] = self.latlongroid[1]

        newlist = c_elect.add_breadcrumb(self.mapfile())

        c_elect.save()
        print(f"=== VISIT self === {self.nid}")
        print(f"current children:{[c.value for c in self.children]}")
        print(
            f"___under {c_elect.name} leaving breadcrumb: "
            f"{c_elect['mapfiles'][-1]}"
        )

        return True

    def group_by_type(self, nodes):
        from collections import defaultdict
        groups = defaultdict(list)
        for node in nodes:
            groups[node.type].append(node)
        return dict(groups)


    def get_parent_layers(self):
        if self.parent:
            return {self.parent.type: [self.parent]}
        return {}

    def get_sibling_layers(self):
        if not self.parent:
            return {}

        sibling_groups = {}
        for child in self.parent.children:
            # Group every sibling cleanly by its own type
            if child.type not in sibling_groups:
                sibling_groups[child.type] = []
            sibling_groups[child.type].append(child)

        return sibling_groups

    def get_child_layers(self):
        return self.group_by_type(self.children)

    def get_grandchild_layers(self):
        from flask import session

        accumulated_ids = session.get("accumulated_nodes", [])

        if accumulated_ids:
            print(f"🔮 [GRANDCHILD EXTRACTION] Extracting grandchildren from {len(accumulated_ids)} session-staged child ")
            grandchildren = []

            for nid in accumulated_ids:
                child_node = TREK_NODES_BY_ID.get(nid)
                if child_node and hasattr(child_node, 'children'):
                    # The children of the passed wards/divisions are the walks/polling districts (grandchildren)
                    grandchildren.extend(child_node.children)

            print(f"✅ Extracted {len(grandchildren)} total grandchild nodes from the staged child selection.")
        else:
            # Standard structural tree fallback
            grandchildren = []
            for child in self.children:
                grandchildren.extend(child.children)

        return self.group_by_type(grandchildren)

    def surrounding_layers(self):
        yield from self.get_parent_layers().items()
        yield from self.get_sibling_layers().items()
        yield from self.get_child_layers().items()
        yield from self.get_grandchild_layers().items()


    @classmethod
    def from_dict(cls, data):
        node = cls(
            value=data["value"],
            fid=data["fid"],
            roid=data["latlongroid"],
            origin=data["origin"],
            node_type=data["node_type"],
            nid=data["nid"],
        )

        # Hydrate flat properties
        node.electorate = data.get("electorate")
        node.turnout = data.get("turnout", 0)
        node.houses = data.get("houses", 0)
        node.target = data.get("target", 0)
        node.party = data.get("party")
        node.candidates = data.get("candidates", {})
        node.defcol = data.get("defcol")
        node.tagno = data.get("tagno")
        node.bbox = data.get("bbox", [])

        # Cache pre-serialized node_path as a fallback
        node._cached_node_path = data.get("node_path")

        # Store raw parent/child UUID references for the re-linking pass
        node._parent_nid = data.get("parent")
        node._children_nids = data.get("children", [])

        return node

    def to_dict(self):
        return {
            "nid": self.nid,
            "node_path": self.node_path,  # <--- NEW FIELD
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
        "MAP_LAYERS": MAP_LAYERS
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

    @property
    def layer_path(self) -> str:
        """
        Computes the structural type blueprint trail dynamically from root to node.
        Example: "country/nation/county/constituency/ward"
        note that parents of treknodes can change if ping_node selected
        """
        if self.parent is None:
            return self.type
        return f"{self.parent.layer_path}/{self.type}"

    @property
    def node_path(self):
        """Recursively resolves path via parent object, or falls back to cached string."""
        if self.parent:
            return f"{self.parent.node_path}/{self.value}"
        if getattr(self, "_cached_node_path", None):
            return self._cached_node_path
        return self.value

    def path_at_level(self, target_level: int) -> str | None:
        """
        Truncates the node_path up to the specified level depth (0-indexed).

        Examples (given node_path = "UNITED_KINGDOM/ENGLAND/SURREY/DORKING_AND_HORLEY"):
            path_at_level(0) -> "UNITED_KINGDOM"
            path_at_level(1) -> "UNITED_KINGDOM/ENGLAND"
            path_at_level(2) -> "UNITED_KINGDOM/ENGLAND/SURREY"
            path_at_level(10) -> "UNITED_KINGDOM/ENGLAND/SURREY/DORKING_AND_HORLEY" (clamped)
        """
        if target_level < 0:
            return None

        # Split path into discrete level segments
        parts = self.node_path.split("/")

        # Slice up to target_level + 1 inclusive
        sliced_parts = parts[: target_level + 1]

        if not sliced_parts:
            return None

        return "/".join(sliced_parts)

    @property
    def actual_levels(self) -> dict[int, str]:
        """
        Generates the absolute depth-to-type map dynamically.
        Perfect for structural mapping and verifying path depth layouts.
        Example: {0: 'country', 1: 'nation', 2: 'county', 3: 'constituency', 4: 'ward'}
        """
        levels_map = {}
        cur = self
        while cur:
            levels_map[cur.level] = cur.type
            cur = cur.parent
        # Return sorted by depth level index ascending
        return dict(sorted(levels_map.items()))

    def child_type(self, elevels: dict) -> str | None:
        if not elevels:
            return None
        # 3. Safe access
        return elevels.get(self.level + 1)



    def endpoint_created(self, CElection,geo_index,rlevels, newpath, static=False):
        from flask import session
        import layers
        """
        Creates a map node (HTML) if it doesn't already exist,
        is stale, or if active node accumulation overrides the cache.
        """
        totalleaf =  0
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        next_level = self.level + 1

        print(f"___under {state.route()} testing endpoint:", newpath)
        print("endpoint children:", [c.value for c in self.children])

        max_level = max(elevels)

        if next_level > max_level:
            return False, 0

        atype = elevels[next_level]

        workdir = workdirectories.get('workdir')
        if not workdir:
            print("⚠️ [ERROR] 'workdir' not found in workdirectories!")
            return False, 0

        fullpath = Path(workdir) / newpath

        # Determine if the map is stale
        endpoint_created = False

        if not fullpath.exists():
            endpoint_created = True
        elif hasattr(self, 'last_modified') and self.last_modified:
            file_mtime = datetime.utcfromtimestamp(fullpath.stat().st_mtime)
            if self.last_modified > file_mtime:
                endpoint_created = True

        # 🧠 THE SESSION CHECK: If we have an active accumulation layout,
        # force the update flag to True to bypass old files on disk.
        accumulated = session.get('accumulated_nodes', [])
        if accumulated:
            print(f"🔄 [ACCUMULATION OVERRIDE] Found {len(accumulated)} target nodes in session. Forcing map refresh.")
            endpoint_created = True

        if next_level <= max_level and endpoint_created:
            map, totalleaf = self.create_node_map(CElection,geo_index,rlevels, static=static)
        else:
            # Fallback leaf-count calculation for clean exits
            totalleaf = len([c for c in self.children if c.level == max_level])

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
        CE_task_tags, CE_outcome_tags, CE_all_tags = CE.get_tags()
        CE_areas = self.get_areas()
        CE_places = CE.get("places", {})
        print(f"___Processing lozenges : {len(CE_resources)} CE_task_tags : {CE_task_tags} CE_outcome_tags : {CE_outcome_tags} CE_areas : {CE_areas} CE_places : {CE_places}")
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



    def build_eventlist_dataframe(self, rlevels, CElection):
        """
        Produce an eventlist dataframe matching the intent of the JS summary.
        """

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

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

    from pathlib import Path

    def mapfile(self) -> str:
        """Compute map filename dynamically."""
        node_type = self.type

        if node_type == "street":
            parent_val = getattr(self.parent, "value", self.parent) or ""
            name = f"{parent_val}--{self.value}"
            suffix = "-PRINT.html"
        else:
            name = self.value
            suffix = "-MAP.html"

        return str(Path(self.dir or "") / f"{name}{suffix}")


    def ping_node(self, rlevels, geoindex, dest_path, create=True, accumulate=False):
        from state import LEVEL_ZOOM_MAP, stepify
        from flask import session
        from elector import electors

        print("\n" + "="*50)
        print(f"🔍 [DEBUG PING_NODE START]")
        print(f"  ▪️ Current Node Path: '{self.node_path}' (Level {self.level})")
        print(f"  ▪️ Destination Path:  '{dest_path}'")
        print(f"  ▪️ Create Flag:        {create}")
        print("="*50)

        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"
        (c_election, elevels), = rlevels.items()

        # Base max level from election definition

        max_level = max(elevels)

        # ──────────────────────────────
        # Step 1: Clean & Normalize Paths
        # ──────────────────────────────
        full_dest_path = dest_path.strip()
        self_path = stepify(self.mapfile())
        dest_parts = stepify(full_dest_path)

        print(f"  [1] Parsed self_path:  {self_path}")
        print(f"  [1] Parsed dest_parts: {dest_parts}")

        # 🎯 TARGET LEVEL 4 RULE (Ward/Division):
        # If targeting level 4 (len == 5), extend max_level to 6 so it populates
        # both walks (level + 1) and streets (level + 2) grandchildren data.
        if len(dest_parts) == 5:
            max_level = max(max_level, 6)
            print(f"  🎯 [CUSTOM RULE] Target level 4 detected (path length 5). Extended max_level to 6 for walks & streets.")

        # ──────────────────────────────
        # Step 2: Compute Common Ancestor and Move Up
        # ──────────────────────────────
        common_len = get_common_prefix_len(self_path, dest_parts)
        print(f"  [2] Common prefix length: {common_len}")

        node = self
        up_steps = len(self_path) - common_len
        if up_steps > 0:
            print(f"  [2] Moving UP {up_steps} levels to common ancestor...")
            for i in range(up_steps):
                if not node.parent:
                    print(f"    ⚠️ Hit root early at step {i} while moving up.")
                    break
                node = node.parent
            print(f"    🎯 Common ancestor resolved to: '{node.node_path}' (Level {node.level})")

        # ──────────────────────────────
        # Step 3: Traverse Downwards with Strict Target Validation
        # ──────────────────────────────
        down_path = dest_parts[common_len:]
        print(f"  [3] Remaining downstream path to traverse: {down_path}")

        current_parts = dest_parts[:common_len]
        target_path = node.node_path  # Track target path sequence outside loop safely
        next_level = node.level

        for idx, part in enumerate(down_path):
            current_parts.append(part)
            target_path = "/".join(current_parts)
            next_level = node.level + 1

            print(f"\n     👉 [ITERATION {idx+1}] Processing part: '{part}'")
            print(f"        Constructed target_path: '{target_path}'")
            print(f"        Evaluating next_level:   {next_level}")

            if next_level > max_level:
                print(f"        ⚠️ [DEBUG] Next level {next_level} exceeds max_level {max_level}. Breaking.")
                break

            ntype = str(elevels[next_level]) if next_level in elevels else "walk"

            # --- 🛡️ PATH VALIDATION ENGINE ---
            is_valid_path = False
            if next_level < 7:
                is_valid_path = target_path in geoindex
                print(f"        🛡️ Checked geoindex for '{target_path}': Found = {is_valid_path}")
            else:
                df_check = electors.elector_for_path(rlevels, target_path)
                is_valid_path = df_check is not None and not df_check.empty
                print(f"        🛡️ Checked DB electors for '{target_path}': Found Rows = {is_valid_path}")

            if not is_valid_path:
                print(f"        🚫 [PING] Aborting down-step. Path '{target_path}' is invalid in registry sources.")
                print(f"🔍 [DEBUG PING_NODE ABORT-EXIT] Returning node: '{node.node_path}'\n" + "="*50)
                return node

            # Look for existing child match
            match = next((c for c in node.children if c.node_path == target_path), None)
            if match:
                print(f"        ✅ Found existing memory-cached child node for: '{target_path}'")

            # --- BRANCH CREATION ON MISS ---
            if create and not match:
                print(f"        ⚙️ [PING] Spawning missing branch for Level {next_level}: {target_path}")
                try:
                    if next_level <= 6:
                        node.create_map_branch(rlevels, geoindex)
                    else:
                        node.create_data_branch(rlevels, target_path)
                except Exception as e:
                    print(f"        ⚠️ [PING] Primary creation pass failed: {e}")

                match = next((c for c in node.children if c.node_path == target_path), None)

                # --- BIVALENT FALLBACK ---
                if not match and "/" in ntype:
                    print(f"        🔄 [PING] Bivalent type '{ntype}' missed primary. Triaging alternative strategy...")
                    try:
                        if next_level <= 6:
                            node.create_map_branch(rlevels, geoindex)
                        else:
                            node.create_data_branch(rlevels, target_path)
                    except Exception as e:
                        print(f"        ⚠️ [PING] Alternative bivalent strategy failed: {e}")

                    match = next((c for c in node.children if c.node_path == target_path), None)

            if not match:
                print(f"        ❌ [PING] Could not match or create node for path: {target_path}")
                print(f"🔍 [DEBUG PING_NODE FAIL-EXIT] Returning node: '{node.node_path}'\n" + "="*50)
                return node

            node = match

        # ──────────────────────────────
        # Step 4: Keyword Zoom Handling
        # ──────────────────────────────
        keyword = None
        if keyword and keyword in LEVEL_ZOOM_MAP:
            node.zoom_level = LEVEL_ZOOM_MAP[keyword]
            print(f"  [4] Applied zoom level rule: {node.zoom_level}")

        # ──────────────────────────────
        # Step 5: Exhaustive Bottom-Node Child Expansion
        # ──────────────────────────────
        print(f"\n  [5] Entering exhaustive bottom-node expansion phase for: '{node.node_path}'")
        if node.level <= max_level and create:
            children_type = str(elevels.get(node.level, ""))
            next_level = node.level + 1

            should_expand = False
            if next_level <= 6:
                should_expand = node.node_path in geoindex or any(k.startswith(node.node_path + "/") for k in geoindex)
            else:
                df_check = electors.elector_for_path(rlevels, node.mapfile())
                should_expand = df_check is not None and not df_check.empty

            if should_expand:
                try:
                    print(f"     ⚙️ Triggering bottom-node branch expansion pass for children...")
                    if next_level <= 6:
                        node.create_map_branch(rlevels, geoindex)
                    else:
                        node.create_data_branch(rlevels, node.node_path)
                except Exception as e:
                    print(f"     ⚠️ [PING] Final node primary expansion failed: {e}")

                # 🎯 TARGET LEVEL 4 RECURSIVE DEEP DIVE:
                # If we just expanded a Level 4 node into walks (Level 5),
                # let's immediately force those walks to expand into streets (Level 6)!
                if node.level == 4:
                    print(f"     🎯 [CUSTOM RULE] Level 4 expansion detected. Recursively triggering walk-to-street expansion...")
                    for walk_child in node.children:
                        walk_next_level = walk_child.level + 1
                        walk_should_expand = walk_child.node_path in geoindex or any(k.startswith(walk_child.node_path + "/") for k in geoindex)
                        if walk_should_expand:
                            try:
                                walk_child.create_map_branch(rlevels, geoindex)
                            except Exception as e:
                                print(f"     ⚠️ [PING] Walk child expansion failed for {walk_child.node_path}: {e}")



        print(f"🔍 [DEBUG PING_NODE SUCCESS-EXIT] Target achieved! Returning node: '{node.node_path}' (Level {node.level})")
        print("="*50 + "\n")
        return node

    def get_feature_layers(self,CE=None, rlevels=None, static=False):
        """
        Retrieves map layers for the node's parent, siblings, children, and grandchildren,
        applying a self-consistent visual hierarchy across both administrative boundaries
        and operational campaign telemetry overlays.
        """
        from flask import session
        from layers import make_feature_layers, ExtendedFeatureGroup
        from elections import CurrentElection
        from baked_data import baked_manager, BakedDataManager
        import state
        import copy
        from collections import defaultdict

        # 🔧 Fix 1: Track tags to safely handle duplicate closure assignments
        used_tags = set()

        def get_safe_tag_layer(tag_code, tag_desc):
            display_name = f"Task Overlay: [{tag_code}] {tag_desc}"
            if tag_code in used_tags:
                display_name = f"{display_name} (Upper)"
            used_tags.add(tag_code)

            tag_layer = ExtendedFeatureGroup(name=display_name, overlay=True, control=True, show=True)
            tag_layer.options = tag_layer.options or {}
            tag_layer.options.update({"tag": tag_code, "layer_type": "ghost"})
            return tag_layer

        def _attach_elector_overlays(selected_list, tier_key, node, rlevels):
            """Assembles complex voter demographic pin clusters (Postal and Pledges) relative to the active target tier."""
            from folium.plugins import MarkerCluster

            # 📬 1. Postal Voters Layer (Thematic Accent: Amethyst Purple)
            postal_layer = ExtendedFeatureGroup(
                name=f"Elector Overlay: [AV] Postal Voters ({tier_key.title()})",
                overlay=True, control=True, show=False
            )
            postal_layer.options = {
                "tag": "AV",
                "layer_type": "av_highlight",
                "style": {"color": "#7C3AED", "weight": 2, "fillColor": "#A78BFA", "fillOpacity": 0.15}
            }
            postal_cluster = MarkerCluster(name=f"Postal - {tier_key}", control=False).add_to(postal_layer)

            if hasattr(postal_layer, 'add_tag_layer'):
                postal_count = postal_layer.add_tag_layer(
                    rlevels=rlevels, node=node, tags=['AV'], operator='OR',
                    layer_name="Postal Voter", icon_color="purple", icon_name="envelope",
                    header_color="#7C3AED", target_cluster=postal_cluster
                )
                if postal_count > 0:
                    selected_list.append(postal_layer)

            # 🤝 2. Pledge Highlights Layer (Thematic Accent: Action Blue)
            pledge_layer = ExtendedFeatureGroup(
                name=f"Elector Overlay: [VI] Pledged Voters ({tier_key.title()})",
                overlay=True, control=True, show=False
            )
            pledge_layer.options = {
                "tag": "VI",
                "layer_type": "vi_highlight",
                "style": {"color": "#2563EB", "weight": 2, "fillColor": "#60A5FA", "fillOpacity": 0.15}
            }
            pledge_cluster = MarkerCluster(name=f"Pledges - {tier_key}", control=False).add_to(pledge_layer)

            if hasattr(pledge_layer, 'add_tag_layer'):
                pledge_count = pledge_layer.add_tag_layer(
                    rlevels=rlevels, node=node, tags=['PL'], operator='OR',
                    layer_name="Reform Pledge", icon_color="blue", icon_name="users",
                    header_color="#2563EB", target_cluster=pledge_cluster
                )
                if pledge_count > 0:
                    selected_list.append(pledge_layer)

        def _attach_task_campaign_overlays(selected_list, tier_key, node, active_tags, baked_dict):
            """Generates ghost progression overlays and tracking layers for active campaign operations."""
            import state  # Ensures state execution variables are explicitly bound

            # 👻 3. Ghost Task Heatmaps (Thematic Accent: Flame Orange Campaign Highlight)
            for tag_code, tag_desc in active_tags.items():
                tag_layer = get_safe_tag_layer(tag_code, f"{tag_desc} ({tier_key.title()})")

                tag_layer.options.update({
                    "style": {"color": "#EA580C", "weight": 1.5, "fillColor": "#F97316", "fillOpacity": 0.20}
                })

                if hasattr(tag_layer, 'add_ghosts'):
                    tag_layer.add_ghosts(
                        tag_code=tag_code,
                        baked_events=baked_dict,
                        parent_node=node,
                        branchcolours=state.branchcolours
                    )
                    selected_list.append(tag_layer)

        # Guard & Unpack election data contexts
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"
        (c_election, elevels), = rlevels.items()

        print(f"\n================ [DEBUG START: get_feature_layers] ================")

        task_tags, outcome_tags, all_tags = CE.get_tags()

        factory = make_feature_layers()
        selected = []
        counters = defaultdict(int)

        # Baseline Data: Establish Base Node Lists Upfront
        if session.get("accumulate", False):
            childnode_ids = session.get("accumulated_nodes", [])
            childnodelist = [TREK_NODES_BY_ID.get(nid) for nid in childnode_ids if nid in TREK_NODES_BY_ID]
        else:
            childnodelist = [self]

        test_node = childnodelist[0] if childnodelist else self
       # Setup infrastructure for task overlays
        baked_dict = baked_manager.load()
        active_tags = dict(task_tags)
        active_tags["VI"] = "Voter Intention"

        totalleaf = 0

        # Pre-group dynamic geographic nodes by type for fast lookup
        nodes_by_type = {}
        for layer_type, nodes in self.surrounding_layers():
            nodes_by_type[layer_type] = nodes
            print(f"Surrounding layer: {layer_type} count: {len(nodes_by_type[layer_type])}")

# Control panel whitelist toggles — ADDED 'country' AND 'nation'
        TEST_LAYERS = {"country", "nation", "county", "constituency", "ward", "walk", "division", "marker","street"}


        # 🎯 DIRECT STREAM ROUTING LOOP
        for factory_key, layer in factory.items():

            if factory_key not in TEST_LAYERS:
                continue

            nodes_to_render = nodes_by_type.get(factory_key, [])
            if factory_key != "marker" and not nodes_to_render:
                continue

            # ------------------------------------------------------------------
            # 🔧 CONTEXT PACKAGING: Safely pull style configurations from layer.options
            # ------------------------------------------------------------------
            style_cfg = getattr(layer, "options", {}) or {}

            if factory_key != "marker":
                # Build a uniform style dict directly from the layer properties safely
                geojson_style = {
                    "color": style_cfg.get("color", "#94A3B8"),
                    "weight": style_cfg.get("weight", 1.0),
                    "fillColor": style_cfg.get("fillColor", "none"),
                    "fillOpacity": 0.0 if style_cfg.get("fillColor", "none") == "none" else style_cfg.get("fillOpacity", 0.0)
                }
                if "dashArray" in style_cfg:
                    geojson_style["dashArray"] = style_cfg["dashArray"]


            # Route directly to precise rendering logic blocks
            # Route directly to precise rendering logic blocks
            match factory_key:

                # 📍 Pins & Global Anchors
                case "marker":
                    layer.add_genmarkers(CE,rlevels, test_node, static)

                # 🗺️ Polygon Map Layers
                # 🗺️ Polygon Map Layers
                case "country" | "nation" | "county" | "constituency" | "division" | "ward":
                    print(f"Nodemap layer: {factory_key} count: {len(nodes_to_render)}")

                    # Top-level nodes (like 'country') have parent = None; fall back to the target node itself
                    first_node = nodes_to_render[0]
                    parent_anchor = first_node.parent if first_node.parent is not None else first_node

                    layer.add_nodemaps(
                        CE,
                        rlevels=rlevels,
                        herenode=parent_anchor,
                        nodes_list=nodes_to_render,
                        static=static,
                        counters=counters
                    )

#                # 📐 Spatial Proximity Layers (Voronoi Grids)
                case "walk":
                    print(f"Nodemap Walk layer: {factory_key} count: {len(nodes_to_render)}")

                    # 🎯 FIX: Anchor the clipping envelope to the true parent container
                    # of the specific sub-units being drawn, fall back to self if list is empty.
                    layer.add_nodemaps(
                        CE,
                        rlevels=rlevels,
                        herenode=nodes_to_render[0].parent,
                        nodes_list=nodes_to_render,
                        static=static,
                        counters=counters
                    )
#                    layer.add_voronoi(
#                        rlevels=rlevels,
#                        nodes_list=nodes_to_render,
#                        static=static
#                    )
#                    _attach_task_campaign_overlays(
#                        selected, factory_key, nodes_to_render[0].parent, active_tags, baked_dict
#                    )
                # 🥾 Tactical Ground Line Elements & Analytics Fallbacks
                case "street" :
                    layer.add_linestrings(
                        CE,
                        rlevels,
                        nodes_to_render[0].parent.parent,
                        nodes_to_render,
                        static,
                        counters=counters)


                             # ⚠️ Catch-All Fallback Engine
                case _:
                    print(f"ℹ️ Factory key '{factory_key}' running default node markers routing.")
                    layer.add_nodemarks(
                        CE,
                        rlevels,
                        nodes_to_render[0].parent,
                        static,
                        factory_key)

                    selected.append(layer)

            # 📬 Operational Overlay Attachment Trigger

            # ------------------------------------------------------------------
            # 🔧 POST-EXECUTION CLEANUP: Maintain Flat Property Architecture
            # ------------------------------------------------------------------
            layer.overlay = True
            layer.control = True

            # Use safe explicit fallbacks for map initialization layers control panel states
            if factory_key in ["country", "nation","county","ward", "division", "constituency", "walk", "street"]:
                layer.show = True
            else:
                layer.show = False

            # Append the baseline administrative layer
            selected.append(layer)

        # Flat layer array emission ensures Folium handles deep nesting and controls perfectly
        return selected, totalleaf


    def sumupVI(self,viValue):
        origin = self
        if self.type == 'street' :
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
        if self.type == 'street' :
            sumnode = origin
            sumnode.VR[vrValue] = sumnode.VR[vrValue] + 1
#            print ("_____VRnode:",sumnode.value,sumnode.level,sumnode.VR)
        self = origin
#        print ("_____VRstatus:",self.value,self.type,self.VR)
        return

    def updateTurnout(self):
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

            children = parent.childrenoftype(casnode.type)
            values = [c.turnout for c in children if c.turnout is not None]
            parent.turnout = sum(values) / len(values) if values else None

            casnode = parent

        return

    def updateGOTV(self, gotv_pct):
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
            children = parent.childrenoftype(casnode.type)

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


    def updateCandidates(self):
        """Fill self.candidates from the global Candidates dict."""
        from state import Candidates

        if self.type == "division":
            # Safely get candidate dict or default to empty dict
            self.candidates = Candidates.get("division", {}).get(self.value, {})
            print(f"[DEBUG] Candidate update for {self.value}: {self.candidates}")



    def updateElectorate(self):
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
                    for c in parent.childrenoftype(casnode.type)
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
            for x in sumnode.parent.childrenoftype(sumnode.type):
                sumnode.parent.houses = sumnode.parent.houses + x.houses
                print ("_____Houseslevel:",x.level,x.value,x.houses,sumnode.houses)
                i = i+1
            sumnode = sumnode.parent
            self = origin

        print ("_____OriginHouses:",self.findnodeparenting_type("country").houses,self.value,self.type,self.houses)
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


    def create_name_nodes(self,resolved_levels,gotv_pct,nodetype,namepoints):

        # Guard: Ensure we have exactly one election to unpack
        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # The clean unpack you like
        (c_election, elevels), = resolved_levels.items()


        fam_nodes = []
        if namepoints.empty:
            raise ValueError("No data in namepoints DataFrame.")
        print(f"____Namepoints nodes: at {self.value} of type:{nodetype} there are {len(namepoints)} ")
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
                egg.parent = self
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

            egg.updateTurnout()
            egg.updateElectorate()
            egg.updateGOTV(gotv_pct, )

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

    def findnodeparenting_type(self, target_type):
        node = self
        print(f"find node at self: {self.value} of type {self.type} looking for parent of {target_type}")

        while node is not None:
            # Check if this current node has any children of the target type
            if hasattr(node, 'childrenoftype') and node.childrenoftype(target_type):
                return node

            # Climb up to the next ancestral level
            node = node.parent

        # If we reached the root (None) and found nothing, return None safely
        return None

    def create_data_branch(self, resolved_levels, localized_path):
        from elector import electors
        from layers import Treepolys
        import elections

        # Guard: Ensure we have exactly one election to unpack
        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # Clean unpack
        (c_election, elevels), = resolved_levels.items()

        CE = elections.CurrentElection.load(c_election)
        raw_electtype = elevels[self.level + 1]
        print(f"✅ Creating Data branch {raw_electtype}  for election {c_election}")

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


            for electtype in target_layers:

                # Fetch the isolated electoral records matching this exact layer pass
                areaelectors = electors.elector_for_path(resolved_levels, localized_path)

                if areaelectors.empty:
                    print(f"⚠️ No data from election {c_election} at node {self.value} for subtype '{electtype}'")
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
                    nodeelectors
                )

                print(f"📦 Created {len(branch_nodes)} nodes for type '{electtype}'")
                # ✅ CORRECTED
                all_created_data_nodes.extend(branch_nodes)

        except Exception as e:
            print("❌ Error during data branch generation:", e)
            import traceback
            traceback.print_exc()
            return []

        print(
            f"✅ Completed Multi-Data Branch for Election: {c_election} "
            f"in area: {self.value} | Total nodes created: {len(all_created_data_nodes)}"
        )

        # Ensure global persistence method is clean
        if 'save_nodes' in globals() or 'save_nodes' in dir(state):
            try:
                save_nodes(TREKNODE_FILE)
            except NameError:
                pass

        return all_created_data_nodes

    def create_map_branch(self, resolved_levels, geoindex):
        # Imports (keep them here if they are circular)
        from layers import Treepolys
        from state import branchcolours
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

        geo_node = geoindex.get(my_path_key)
        if not geo_node:
            print(f"⚠️ Warning: Path {my_path_key} not found in geoindex. Falling back to empty children.")
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

            # 🎯 DIRECT FID EXTRACTION: Fetch the unique FIDs explicitly stored in geoindex
            valid_child_fids = set()
            for path in allowed_child_paths:
                node = geoindex.get(path)
                if node and node.get("fid") is not None:
                    valid_child_fids.add(node["fid"])

            print(f"🎯 Target FIDs expected from geoindex: {valid_child_fids}")

            # Direct, vectorized filtering on the integer column — no string manipulation required
            selected_children = ChildPolylayer[ChildPolylayer['FID'].isin(valid_child_fids)]

            print(f"📦 Found {len(selected_children)} / {len(valid_child_fids)} precise shapefile matches via FID alignment.")

            fam_nodes = self.childrenoftype(electtype)
            fam_values = {x.node_path for x in fam_nodes}

            k = 0
            j = 0

            for _, limb in selected_children.iterrows():
                # 1. Use the pre-baked path directly from the GeoDataFrame properties
                child_path_key = limb.get('_parent_path')
                if child_path_key:
                    child_path_key = f"{child_path_key}/{limb['NAME']}"
                else:
                    # Fallback safety if property is missing
                    newname = state.normalname(limb['NAME'])
                    child_path_key = f"{my_path_key}/{newname}"

                newname = state.normalname(limb['NAME'])

                # Ensure uniqueness within this specific sub-layer type block
                if child_path_key in fam_values:
                    j += 1
                    continue

                baked_roid = geoindex.get(child_path_key, {}).get("roid")

                if baked_roid:
                    here = tuple(baked_roid)
                else:
                    centroid_point = limb.geometry.representative_point()
                    here = (centroid_point.y, centroid_point.x)

                try:
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

                    # ⚠️ FIX HERE: Pass the specific feature geometry/row instead of an empty DataFrame
                    # Assuming your bounding box function accepts a GeoSeries, geometry, or feature row:
                    egg.bbox, egg.latlongroid = egg.get_bounding_box(electtype, limb.geometry)

                    # Set branch color based on absolute index
                    color_idx = (len(all_created_children) + k) % len(branchcolours)
                    egg.defcol = branchcolours[color_idx]
                    egg.updateParty()
                    egg.updateCandidates()
                    egg.updateTurnout()
                    egg.updateElectorate()
                    egg.updateGOTV(gotv_pct)

                    fam_nodes.append(egg)
                    all_created_children.append(egg)
                    fam_values.add(child_path_key)
                    k += 1

                except Exception as e:
                    print(f"❌ ERROR during node update for {newname} ({electtype}): {str(e)}")
                    self.remove_child(egg)
                    raise

            print(f"✅ Layer '{electtype}': Added {k}, skipped duplicate {j}. Total branch size: {len(fam_nodes)}")



    def create_node_map(self,CElection, geo_index, resolved_levels, static=False):
        global SERVER_PASSWORD

        from folium import IFrame, Element  # 💡 Explicitly ensured Element is present
        from state import LEVEL_ZOOM_MAP
        from layers import Treepolys, MAP_LAYERS
        from layers import make_counters, ExtendedFeatureGroup

        import hashlib
        import re
        from pathlib import Path

        import json



        # Guard: Ensure we have exactly one election to unpack
        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # The clean unpack
        (c_election, elevels), = resolved_levels.items()
        print(f"DEBUG: Unpacked election: {c_election}")
        task_tags, outcome_tags, all_tags = CElection.get_tags()
        task_tags, outcome_tags, all_tags = CElection.get_tags()
        task_tree = CElection.get("taskTypes", {})

        # 1. Wrap the dictionary in Python first
        wrapped_task_tree = {"TASKS": task_tree or {}}

        # 2. Dump the wrapped dictionary to JSON
        task_tree_json = json.dumps(wrapped_task_tree)

        task_accordion_js = f"""
            <script>
            window.taskTree = {task_tree_json};

            window.addEventListener('load', function () {{
                try {{
                    window.parent.postMessage(
                        {{
                            type: 'taskTree',
                            tree: window.taskTree
                        }},
                        '*'
                    );
                }} catch (e) {{
                    console.warn('taskTree postMessage failed', e);
                }}
            }});
            </script>
            """

        area_root_path = self.node_path

        area_tree = build_area_tree(area_root_path, geo_index, max_depth=3)
        area_tree_json = json.dumps(area_tree or {})

        area_accordion_js = f"""
            <script>
            window.areaTree = {area_tree_json};

            window.addEventListener('load', function () {{
                try {{
                    window.parent.postMessage(
                        {{
                            type: 'areaTree',
                            tree: window.areaTree
                        }},
                        '*'
                    );
                }} catch (e) {{
                    console.warn('areaTree postMessage failed', e);
                }}
            }});
            </script>
            """



        accumulate = session.get("accumulate", False)

        # 1. DETERMINE CONTEXT (Who is the "Owner" of this map?)
        # If accumulating, we act as if we are the parent

        # 2. SET UP FILE PATHS
        # Use render_node for the filename so child updates overwrite the parent map
        mapfile_name = self.mapfile().split("/")[-1]
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
        print(f"___AFTER map creation: on elections.route {state.route()} acc: {accumulate} creating file: ", self.mapfile())

        counters = make_counters()

            # 2️⃣ Create fresh FeatureGroups for THIS map

        # 3️⃣ Select which layers to render for this map
        flayers, totalleaf = self.get_feature_layers(
            CE=CElection,rlevels=resolved_levels,
            static=static
        )
        print(f"___AFTER layer creation: on elections.route {state.route()} layercount: {len(flayers)} creating file: ", self.mapfile())

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

        tile_override_css = """
            <style>
                .leaflet-tile-container img {
                    filter: grayscale(100%) invert(5%) contrast(120%);
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

# 📈 FIX: Use your local server's static web route for the image asset
        logo_web_path = "/static/images/logo.png"  # Replace with your actual web asset path

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
                    margin-bottom: 10px !important;
                    margin-left: 10px !important;
                }}

                .leaflet-logo-icon {{
                    width: 100%;
                    height: 100%;
                    background-color: #17B9D1;
                    -webkit-mask-image: url("{logo_web_path}");
                    mask-image: url("{logo_web_path}");
                    -webkit-mask-size: contain;
                    mask-size: contain;
                    -webkit-mask-repeat: no-repeat;
                    mask-repeat: no-repeat;
                    -webkit-mask-position: center;
                    mask-position: center;
                }}
            </style>
        """

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

                -webkit-mask: url('{logo_web_path}') no-repeat center;
                mask: url('{logo_web_path}') no-repeat center;
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
                    <button id="backToCalendarBtn">📅 Calendar</button>
                </div>
            </div>
            """
        # --- Calendar UI injection
        calendar_html = f"""

            <div id="calendar">

                <div id="calendar-header" class="container-fluid text-center">

                    <h2 id="calendar-title" class="mb-2">
                        {c_election} Campaigns Calendar
                    </h2>

                    <div id="calendar-controls"
                         class="d-flex justify-content-center gap-2 flex-wrap mb-2">

                        <button id="switch-tomap-btn"
                                class="btn btn-tomap">
                            🧭 Map
                        </button>

                        <button id="save-calendar-btn"
                                class="btn btn-primary">
                            💾 Save Calendar
                        </button>

                        <button id="generate-summary-btn"
                                class="btn btn-secondary">
                            📋 Generate Table
                        </button>

                        <button id="export-html-btn"
                                class="btn btn-info">
                            🔐 Export HTML
                        </button>

                    </div>
                </div>

                <div id="calendar-scroll" class="container-fluid">

                    <div id="calendar-grid"
                         class="calendar-grid mt-4">
                    </div>

                    <div id="summary-report"
                         class="mt-4">
                    </div>

                </div>
            </div>


            <div id="map-overlay" class="map-overlay">

                <div id="map-overlay-container"
                     class="map-overlay-container">

                    <iframe id="overlay-iframe"
                            class="overlay-iframe"
                            src="">
                    </iframe>

                    <button id="close-overlay"
                            class="overlay-close-btn">
                        Close Map
                    </button>

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




        # 1. Inject Bootstrap CSS and JS directly into the Folium Header/Body


        # Assuming 'my_map' is your Folium Map object
        header_html = """
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        """

        # 2. Inject the Modal Skeleton HTML into the Map Body
        modal_html = """
        <div class="modal fade" id="streetListModal" tabindex="-1" aria-hidden="true" style="z-index: 99999;">
          <div class="modal-dialog modal-lg">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">Street Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body" id="modal-table-body">
                </div>
              <div class="modal-footer">
                <button type="button" class="btn class-secondary" data-bs-dismiss="modal">Close</button>
              </div>
            </div>
          </div>
        </div>
        """
        # --- Inject map finding , click handling and layer control adding functionality

        fmap_tags_js = r"""
            <script>

            (function() {
                console.log("🗺️ fmap_marker_js loaded (Direct Map Discovery & Modal Binding)");

                window.fmap = null;
                window.MarkerLayer = null;

                let pollAttempts = 0;
                const MAX_ATTEMPTS = 100;
                 // ---------------------------------------------------------
                 // 2️⃣ Stage 2: Targeted Polling for Layer Control Dictionary
                 // ---------------------------------------------------------
                 function findTargetLayer() {
                     pollAttempts++;
                     if (pollAttempts > MAX_ATTEMPTS) {
                         console.error("❌ Layer Control Dictionary timeout.");
                         clearInterval(poll_interval_id);
                         return;
                     }

                     for (const key in window) {
                         if (!window.hasOwnProperty(key)) continue;
                         const val = window[key];

                         if (key.startsWith("layer_control_") && val && val.overlays) {
                             if (val.overlays.marker) {
                                 window.MarkerLayer = val.overlays.marker;
                                 console.log(`🔥 'marker' Layer mapped: ${key}`);
                                 clearInterval(poll_interval_id);
                                 return;
                             }
                         }
                     }
                 }
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
                            console.log(`✅ Folium Map discovered: ${key}`);

                            if (typeof window.handleMapClick === 'function') {
                                window.fmap.on('click', window.handleMapClick);
                            }

                            console.log("⚡ Binding Full-Screen Modal Handlers directly to layers...");
                            let boundCount = 0;
                            let popupGuardCount = 0;

                            window.fmap.eachLayer(function(layer) {
                                if (layer.feature && layer.feature.properties && layer.feature.properties.street_html) {

                                    if (layer.unbindPopup) layer.unbindPopup();

                                    // 👇 RIGHT HERE! THIS IS WHERE THE LAYER.ON CODE GOES 👇
                                    layer.on('click', function(e) {
                                        if (e.originalEvent) e.originalEvent.stopPropagation();
                                        L.DomEvent.stopPropagation(e);


                                        if (e.target) {
                                            console.log("Target Found:", e.target);
                                            console.log("Target Feature:", e.target.feature);
                                            if (e.target.feature) {
                                                console.log("Target Feature Properties:", e.target.feature.properties);
                                            }
                                        }

                                        console.log("Layer Found:", layer);
                                        console.log("Layer Feature:", layer.feature);
                                        if (layer.feature) {
                                            console.log("Layer Feature Properties:", layer.feature.properties);
                                        }

                                        if (e.target && e.target.options) {
                                            console.log("Target Options:", e.target.options);
                                        }

                                        const clickedLayer = e.target;
                                        const feature = clickedLayer.feature || (clickedLayer.options && clickedLayer.options.feature);
                                        const props = feature ? feature.properties : null;

                                        if (!props || !props.street_html) {
                                            console.warn("⚠️ No street properties found on this layer.");
                                            return;
                                        }

                                        // 🎯 Find the active modal container
                                        const modalElement = document.getElementById('streetListModal');
                                        if (!modalElement) {
                                            console.error("❌ Critical: Could not find modal element with ID 'streetListModal'.");
                                            return;
                                        }

                                        // Find the body container strictly inside our target modal
                                        const modalBody = modalElement.querySelector('.modal-body') || document.getElementById('modal-table-body');
                                        if (!modalBody) {
                                            console.error("❌ Critical: Could not find any modal body container.");
                                            return;
                                        }

                                        // 🚀 Directly inject the clean HTML string
                                        modalBody.innerHTML = props.street_html;
                                        console.log("✨ Successfully wrote content to active DOM element:", modalBody);

                                        if (typeof bootstrap !== 'undefined') {

                                            if (!modalElement.__eventsBound) {

                                                modalElement.__eventsBound = true;

                                                modalElement.addEventListener("show.bs.modal", () => {
                                                    console.log("🟢 show.bs.modal");
                                                });

                                                modalElement.addEventListener("shown.bs.modal", () => {
                                                    console.log("🟢 shown.bs.modal");
                                                });

                                                modalElement.addEventListener("hide.bs.modal", () => {
                                                    console.log("🔴 hide.bs.modal");
                                                });

                                                modalElement.addEventListener("hidden.bs.modal", () => {
                                                    console.log("🔴 hidden.bs.modal");
                                                    window.syncBackend?.();
                                                });
                                            }

                                            window.streetBsModal = window.streetBsModal ||
                                                bootstrap.Modal.getOrCreateInstance(modalElement);

                                            window.streetBsModal.show();

                                            console.log("🚀 Modal display triggered via Bootstrap.");

                                        } else {
                                            console.error("❌ Bootstrap JS is not loaded.");
                                        }
                                    });
                                    // 👆 END OF THE LAYER.ON CODE 👆

                                    boundCount++;
                                }

                                // ------------------------------------------------------------
                                // 🛑 POPUP-BUBBLE GUARD
                                // Any layer with its own bound Folium popup (nation, country,
                                // county, constituency polygons via popup=click_popup) must not
                                // ALSO trigger the map-level "add a place here" handler bound
                                // above via window.fmap.on('click', window.handleMapClick).
                                // Leaflet path layers bubble click events up to the map by
                                // default (bubblingMouseEvents: true), so without this guard
                                // every click on a popup-bearing polygon fires handleMapClick
                                // too -- which is why popups were never visibly opening.
                                // ------------------------------------------------------------
                                if (layer.getPopup && layer.getPopup()) {
                                    layer.on('click', function(e) {
                                     if (e.originalEvent) e.originalEvent.stopPropagation();   // ADD THIS LINE
                                        L.DomEvent.stopPropagation(e);
                                    });
                                    popupGuardCount++;
                                }
                            });
                            console.log(`✅ Configured ${boundCount} map layers for modal presentations.`);
                            console.log(`🛑 Configured ${popupGuardCount} map layers with popup-bubble guards.`);

                            startLayerPolling();
                            return;
                        }
                    }
                    setTimeout(detectFoliumMap, 100);
                }


                let poll_interval_id;
                function startLayerPolling() {
                    poll_interval_id = setInterval(findTargetLayer, 100);
                }

                document.addEventListener("DOMContentLoaded", detectFoliumMap);
            })();
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
        FolMap.get_root().html.add_child(folium.Element(area_accordion_js))
        FolMap.get_root().html.add_child(folium.Element(task_accordion_js))
        FolMap.get_root().header.add_child(folium.Element(header_html))
        FolMap.get_root().html.add_child(folium.Element(modal_html))

        FolMap.get_root().html.add_child(folium.Element(fmap_tags_js))
        FolMap.get_root().html.add_child(folium.Element(search_bar_html))
        FolMap.get_root().html.add_child(folium.Element(calendar_html))
        FolMap.get_root().html.add_child(folium.Element(reverse_geocode_js))
        FolMap.get_root().html.add_child(Element(custom_click_js))
        FolMap.get_root().html.add_child(folium.Element(title_html))
        FolMap.get_root().html.add_child(folium.Element(move_close_button_css))
        FolMap.get_root().html.add_child(folium.Element(street_row_css))
        FolMap.get_root().html.add_child(folium.Element(transparency))
        FolMap.get_root().html.add_child(folium.Element(limit_popup_height_css))

        FolMap.get_root().header.add_child(folium.Element(tile_override_css))

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
        import time
        # Option A: Use a timestamp so it changes every time you run it
        cache_buster = int(time.time())

        FolMap.add_css_link("electtrekprint", f"https://newbrie.github.io/Electtrek/static/print.css?v={cache_buster}")
        FolMap.add_css_link("electtrekstyle", f"https://newbrie.github.io/Electtrek/static/style.css?v={cache_buster}")
        FolMap.add_js_link("electtrekresources", f"https://newbrie.github.io/Electtrek/static/resources.js?v={cache_buster}")
        FolMap.add_js_link("electtrekmap", f"https://newbrie.github.io/Electtrek/static/map.js?v={cache_buster}")

        # OR Option B: Manually increment a version number whenever you push an update
        # FolMap.add_js_link("electtrekmap", "https://newbrie.github.io/Electtrek/static/map.js?v=1.0.2")

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
        print(f"✅ Map Saved to: {target} (Accumulate: {accumulate}) elections.route: {state.route()}")
        return FolMap, totalleaf



    def set_bounding_box(self,block):
      longmin = block.Long.min()
      latmin = block.Lat.min()
      longmax = block.Long.max()
      latmax = block.Lat.max()
      print("______Bounding Box:",longmin,latmin,longmax,latmax)
      return [Point(latmin,longmin),Point(latmax,longmax)]

    def get_bounding_box(self, ntype,block):
        from layers import Treepolys

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
        elif self.level < 7:
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
            # Wrap the raw shapely geometry into a GeoSeries for GIS operations
            gs = gpd.GeoSeries([block], crs="EPSG:4326")

            minx, miny, maxx, maxy = gs.total_bounds
            swne = [(miny, minx), (maxy, maxx)]

            # Reproject the temporary GeoSeries to Web Mercator (meters)
            gs_proj = gs.to_crs(epsg=3857)

            # Get the centroid of the geometry
            roid = gs_proj.centroid.iloc[0]

            # Convert centroid back to lat/lon (EPSG:4326)
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
        # 🚨 TRACK INITIAL STATE BEFORE OVERWRITE
        orig_type = getattr(child_node, 'type', 'NOT_SET')
        child_node.type = etype

        registry = TREK_NODES_BY_ID

        print(f"[DEBUG] registry id in add_Tchild: {id(TREK_NODES_BY_ID)}")
        print(f"[DEBUG] registry size in add_Tchild: {len(TREK_NODES_BY_ID)}")
        print(f"\n🟢 [DEBUG] add_Tchild called for node '{child_node.value}' ({child_node.nid})")
        print(f"   - Type passed in: '{etype}' (Original node type was: '{orig_type}')")
        print(f"   - Proposed Parent: {self.value if self else 'None'} (Type: {getattr(self, 'type', 'None')})")
        print(f"   - Current Node Parent: {child_node.parent.value if child_node.parent else 'None'}")
        print(f"   - Registry size before: {len(registry)}")

        # ---------------------------------------------------------
        # 1️⃣ Prevent multiple root country nodes
        # ---------------------------------------------------------
        if child_node.parent is None and etype == "country":
            for existing in registry.values():
                if existing.type == "country" and existing.parent is None:
                    raise ValueError(
                        f"Cannot add another root node of type 'country': {child_node.value}"
                    )

        # ---------------------------------------------------------
        # 2️⃣ Prevent duplicates of same type + value (Robust Path Tracking)
        # ---------------------------------------------------------
        found_in_registry = False

        parent_path = self.node_path if (self and hasattr(self, 'node_path')) else ""
        target_path = f"{parent_path} -> {child_node.value}" if parent_path else child_node.value
        print(f"   - 🧭 Calculated target path for matching: '{target_path}'")

        for nid, existing in registry.items():
            # 🕵️‍♂️ TRACK NAME COLLISIONS WITH DIFFERENT TYPES
            if existing.value == child_node.value and existing.type != etype:
                print(f"   - ⚠️ [COLLISION] Found node with same name '{existing.value}' but mismatched type! "
                      f"Registry node type: '{existing.type}' vs. Incoming target type: '{etype}'.")

            if existing.type != etype:
                continue

            if existing.parent is None and etype == "country":
                continue  # skip root country

            is_ons_map = getattr(child_node, "origin", None) == "ONS_MAPS"
            match_found = False

            if is_ons_map and hasattr(existing, 'fid') and hasattr(child_node, 'fid'):
                if existing.fid == child_node.fid:
                    match_found = True
            else:
                if existing.node_path == target_path:
                    match_found = True

            if match_found:
                print(f"🔍 [DEBUG] Node matched in registry by path: {existing.node_path} ({existing.nid})")
                child_node = existing
                found_in_registry = True
                break

        print(f"   - Found in registry: {found_in_registry}")

        # ---------------------------------------------------------
        # 3️⃣ Attach to parent (With Parent Hijack Alarms)
        # ---------------------------------------------------------
        if child_node not in self.children:
            if child_node.parent and child_node.parent is not self:
                # 🚨 HIJACK ALERT
                print(f"💥 [ALARM] NODE POACHING DETECTED!")
                print(f"   - Node '{child_node.value}' ({child_node.nid}) is being ripped away from old parent!")
                print(f"   - Old Parent: '{child_node.parent.value}' (Path: {child_node.parent.node_path})")
                print(f"   - New Parent: '{self.value}' (Path: {self.node_path})")

                # Detach from old parent
                child_node.parent.children.remove(child_node)

            child_node.parent = self
            self.children.append(child_node)
            print(f"✅ Linked {child_node.value} to {self.value} (children now: {len(self.children)})")
        else:
            # Already attached
            print(f"ℹ️ Node '{child_node.value}' already present in parent '{self.value}' children array.")
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
        import math
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
        first = state.stepify(self.dir+"/"+self.mapfile(elevels))
        second = state.stepify(path)
        print("intersecting paths ",self.dir+"/"+self.mapfile(elevels), path)
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


from typing import Dict

Outcomes = pd.read_excel(GENESYS_FILE)
Outcols = Outcomes.columns.to_list()
allelectors = pd.DataFrame(Outcomes, columns=Outcols)
allelectors.drop(allelectors.index, inplace=True)

TREK_NODES_BY_ID: Dict[str, "TreeNode"] = {}
TREK_NODES_BY_PATH: Dict[str, "TreeNode"] = {}  # Direct path hash table

MapRoot = get_trek_root()

# Sync both registries
TREK_NODES_BY_ID[MapRoot.nid] = MapRoot
TREK_NODES_BY_PATH[MapRoot.node_path] = MapRoot  # <--- Sync root path here

save_nodes(TREKNODE_FILE)
