import sys
import os

# 1. FIX: sys.path must be configured FIRST before any local custom modules are imported
PROJECT_PATH = '/Users/newbrie/Documents/ReformUK/GitHub/Electtrek'
if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

print("TEST LOGGER - sys.path:", sys.path)

# 2. Configure Logging FIRST (before heavy module loading)
import logging
from pathlib import Path
import config
from config import (
    DEBUG_FILE, LOG_FILE, WALK_GEOM_FILE, POSTCODE_FILE, LAST_RESULTS_FILE,
    ELECTIONS_FILE, TREEPOLY_FILE, GENESYS_FILE, ELECTOR_FILE, TREKNODE_FILE,
    RESOURCE_FILE, DEVURLS, NATIONAL_DIVISION_FILE, DATA_FILE
)

# Silencing noisy third-party loggers
logging.getLogger("pyproj").setLevel(logging.WARNING)

# Ensure parent directories of log files exist
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
Path(DEBUG_FILE).parent.mkdir(parents=True, exist_ok=True)

# Configure Root Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

info_handler = logging.FileHandler(LOG_FILE)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(formatter)
logger.addHandler(info_handler)

debug_handler = logging.FileHandler(DEBUG_FILE)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)
logger.addHandler(debug_handler)

# 3. Safe Locale Configuration
import locale
try:
    locale.setlocale(locale.LC_TIME, 'en_GB.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'en_GB')
    except Exception:
        logger.warning("Could not set en_GB locale, falling back to default.")

# 4. Consolidated Third-Party Imports
from datetime import datetime, timedelta, date
from decimal import Decimal
import glob
import io
import json
from json import JSONEncoder, JSONDecodeError
import math
import os, sys, math, stat, json, jinja2, random
from os import listdir, system
from pathlib import Path
import re
import statistics
import time
import threading
import traceback
from collections import defaultdict
from urllib.parse import urlparse, urljoin

import numpy as np
from numpy import ceil
import pandas as pd
import geopandas as gpd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from pyproj import Proj
import requests
import unidecode

# Shapely & Geospatial
from shapely.geometry import Point, Polygon, MultiPolygon, shape, LineString, box
from shapely.ops import nearest_points, split, unary_union
from shapely.validation import make_valid
from geovoronoi import voronoi_regions_from_coords

# Flask & Extensions
from flask import (
    Flask, render_template, request, redirect, session, url_for,
    send_from_directory, jsonify, flash, render_template_string,
    abort, get_flashed_messages, make_response, Response
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, current_user, login_required
)
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from markupsafe import escape

# 5. Local Application Imports (Safe now that sys.path is updated)
from canvasscards import prodcards, find_boundary
from walks import prodwalks
from normalised import normz
import state
from state import (
    VNORM, TABLE_TYPES, LEVEL_ZOOM_MAP, LastResults, levelcolours, subending,
    update_progress, normalname, route, stepify, resolve_here_or_redirect
)
import layers
from layers import MAP_LAYERS
import nodes
from nodes import (
    get_last_node, get_layer_table, get_trek_root, restore_from_persist,
    persist, parent_level_for, save_nodes, move_item, MapRoot
)
from elections import get_available_elections, get_elections, CurrentElection, ElectionContext
from elector import electors
import baked_data

LEVEL_INDEX = {
    "country": 0,
    "nation": 1,
    "county": 2,
    "constituency": 3,
    "ward": 4,
    "division": 4,
    "walk": 5,
    "street": 6,
    "elector": 7,
}

LEVELS = {
    0: "country",
    1: "nation",
    2: "county",
    3: "constituency",
    4: "ward/division",
    5: "walk",
    6: "street",
    7: "elector",
}

class ProgramContext:
    def get_options(self):
        # on startup its possible to define a range of global options

        return {
            "LEVELS": LEVELS,
            "LEVEL_INDEX": LEVEL_INDEX,
            "MAP_LAYERS": MAP_LAYERS,
            "TABLE_TYPES": state.TABLE_TYPES,
            "DEVURLS": config.DEVURLS, #backend urls used on start up
            "VNORM": state.VNORM, #normalised party used everywhere
            "VCO": state.VCO, # party colours used everywhere
            "streams": get_available_elections(), # currently running elections
        }


def resolve_ui_context(program, election, node):
    """
    Merge program, election, and node options into a single dict,
    converting any sets to lists so the result is JSON-serializable.
    """
    def make_json_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_json_serializable(v) for v in obj]
        elif isinstance(obj, set):
            return [make_json_serializable(v) for v in obj]
        else:
            return obj

    merged = {
        **program.get_options(),# program options
        **election.get_options(), # election options
        **node.get_options(program=program, electionctx=election),
    }

    return make_json_serializable(merged)



def get_level_from_geo_index(node_path, geo_index):
    """
    Looks up a node_path in Geo_index and returns its 'level' string.

    Parameters:
        node_path (str): Path string (e.g., 'UNITED_KINGDOM/ENGLAND/ESSEX/CLACTON')
        geo_index (dict): Dict mapping node paths to metadata objects.

    Returns:
        str | None: The 'level' string if found (e.g. 'constituency'), else None.
    """
    if not node_path or not isinstance(geo_index, dict):
        logger.warning("⚠️ Invalid node_path or geo_index provided to lookup.")
        return None

    # 1. Direct O(1) key lookup
    if node_path in geo_index:
        return geo_index[node_path].get('level')

    # 2. Case-insensitive / normalized lookup fallback
    norm_target = str(node_path).strip("/").upper()
    for key, data in geo_index.items():
        if key.strip("/").upper() == norm_target:
            return data.get('level')

    logger.warning(f"⚠️ Could not find level for node_path '{node_path}' in Geo_index.")
    return None

def make_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(i) for i in obj]
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)

def _purge_registry_recursive(node):

    # 1. Recurse first to clean the deep leaves
    for child in list(node.children):
        _purge_registry_recursive(child)

    # 2. Wipe the registry entry
    nid = getattr(node, 'nid', None)
    if nid and nid in nodes.TREK_NODES_BY_ID:
        del nodes.TREK_NODES_BY_ID[nid]

    # 3. CRITICAL: Clear the node's own list of children
    # and parent reference to break circular links
    node.children = []
    if hasattr(node, 'parent'):
        node.parent = None

def prune_subtree(node, max_level=4):
    """
    Removes descendants where level > max_level and cleans up the global registry.
    """
    # Use list() to avoid mutation errors during iteration
    for child in list(node.children):

        if child.level > max_level:
            print(f"🧹 Pruning Subtree: {child.value} (Level {child.level})")

            # 1. Clear the global dictionary for this node AND all its children
            # Do this while we still have the 'child' reference
            _purge_registry_recursive(child)

            # 2. Unlink the child from the parent
            node.children.remove(child)

            # 3. Optimization: Don't recurse into a branch we just deleted
            continue

        # If we didn't prune it, recurse deeper
        prune_subtree(child, max_level=max_level)

def importVI(electorsVI):
    allelectorscopy = electorsVI
    path = config.workdirectories['workdir']+"INDATA"
    headtail = os.path.split(path)
    path2 = headtail[0]
    merge = headtail[1]+"Auto.xlsx"
    indatamerge = headtail[1]+"inDataAuto.csv"
    print ("path:", path, "path2:", path2, "merge:", merge)
    if os.path.exists(path2+indatamerge):
        os.remove(path2+indatamerge)
    if os.path.exists(path2+merge):
        os.remove(path2+merge)
    all_files = glob.glob(f'{path}/*DATA*.csv')
    print("all files",all_files)
    full_revamped = []
    allelectorsX = pd.DataFrame()
#upload street and walk VI and Notes saved updates
    for filename in all_files:
        inDatadf = pd.read_csv(filename,sep='\t', engine='python')
        print("____inDatadf:",inDatadf.head())

        full_revamped.append(inDatadf)
        pathval = inDatadf['Path'][0]
        Lat = inDatadf['Lat'][0]
        Long = inDatadf['Long'][0]
        roid = Point(Long,Lat)
        session['importfile'] = inDatadf['Electrollfile'][0]
        print("____pathval param:",pathval,Long,Lat,CElection['importfile'])
#or just process the elector level updates
        file_path = ELECTOR_FILE
        if file_path and os.path.exists(file_path):
            allelectorsX = pd.read_csv(file_path,sep='\t', engine='python',encoding='utf-8')
            for index,entry in inDatadf.iterrows():
                mask = allelectorsX["ENOP"] == entry['ENOP']
                if mask.any():
                    if not pd.isna(entry['VR']) and not str(entry['VR']).strip() == '':
                        allelectorsX.loc[mask, 'VR'] = entry['VR']
                        print(f"{entry['ENOP']} line VR update: {entry['VR']}")
                    if not pd.isna(entry['VI']) and not str(entry['VI']).strip() == '':
                        allelectorsX.loc[mask, 'VI'] = entry['VI']
                        print(f"{entry['ENOP']} line VI update: {entry['VI']}")
                    if not pd.isna(entry['Notes']) and not str(entry['Notes']).strip() == '':
                        allelectorsX.loc[mask, 'Notes'] = entry['Notes']
                        print(f"{entry['ENOP']} line Notes update: {entry['Notes']}")
                    if not pd.isna(entry['Tags']) and not str(entry['Tags']).strip() == '':
                        allelectorsX.loc[mask, 'Tags'] = entry['Tags']
                        print(f"{entry['ENOP']} line Tags update: {entry['Tags']}")
            print ("uploaded mergefile:",filename)
        else:
            print("______NO Voter Intention Data found to be imported ",full_revamped)
    return allelectorsX


def dfs(root, target, path=()):
    found_node = None
    path = path + (root,)
    if root.value == target:
        return root
    else:
        for child in root.children:
            found_node = dfs(child, target, path)
            if found_node is not None :
                return found_node
        return None

def bfs(self, target, path=()):
    node_list = self.traverse()
    for neighbour in node_list:
        if neighbour.value == target:
            return neighbour
    return None

def selected_childnode(cnode,val):
    print("______selected lower node at end of levels: ",cnode,val)
    for child in cnode.children:
        if child.value == val:
            return child
    return cnode

def get_versioned_filename(base_path, base_name, extension):
    """Generate a versioned filename to prevent overwriting existing files."""
    version = 1
    new_filename = f"{base_name}_v{version}{extension}"
    new_filepath = os.path.join(base_path, new_filename)

    # Increment version number if file already exists
    while os.path.exists(new_filepath):
        version += 1
        new_filename = f"{base_name}_v{version}{extension}"
        new_filepath = os.path.join(base_path, new_filename)

    return new_filepath



def get_L4area(nodelist, here):

    if not nodelist:
        raise ValueError("Empty nodelist passed to get_L4area")

    # Get the level and dir from the first node
    level = nodelist[0].level
    dir_path = nodelist[0].parent.dir  # assuming this structure
    ttype = nodelist[0].type

    # Load correct polygon file for that level
    pfile = Treepolys[ttype]

    if pfile.empty:
        print("____No Level 4 boundary found in file")
        raise Exception('No Level 4 boundaries found')

    # Loop through rows and check containment
    for _, row in pfile.iterrows():
        geom = row['geometry']
        if geom.contains(here):
            polyname = normalname(row['NAME'])  # directly access the string
            print("____Level 4 boundary found:", polyname)
            return polyname  # ✅ return string

    print("____No Level 4 boundary matched for this point")
    return None



def recursive_kmeans(X, prefix='K', depth=0, max_depth=10, max_walk_size=300):
    if depth >= max_depth or len(X) <= max_walk_size:
        return {i: prefix for i in X.index}

    k = min(int(np.ceil(len(X) / max_walk_size)), len(X))
    coords = X[['Lat', 'Long']].values

    kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(coords)

    label_map = {}
    for i in range(k):
        idx = X.index[labels == i]
        if len(idx) == 0:
            continue
        sub_df = X.loc[idx]
        sub_label_map = recursive_kmeans(
            sub_df,
            prefix=f"{prefix}-{i+1}",
            depth=depth+1,
            max_depth=max_depth,
            max_walk_size=max_walk_size
        )
        label_map.update(sub_label_map)
    return label_map

def GetHierarchyMapFromPoints(df):
    """
    Builds a hierarchy map by calculating a single representative coordinate per PD
    and intersecting it directly with Ward and Division spatial layers.
    """
    import geopandas as gpd
    import pandas as pd
    from layers import normalname  # 💡 Imported normalname here

    ward_layer = Treepolys.get("ward")
    div_layer = Treepolys.get("division")

    is_ward_empty = ward_layer is None or len(ward_layer) == 0
    is_div_empty = div_layer is None or len(div_layer) == 0

    if is_ward_empty and is_div_empty:
        print("⚠️ [Hierarchy] Both Ward and Division layers are missing or empty. Cannot resolve hierarchy.")
        return {}

    valid_coords = df[df['Lat'].notna() & df['Long'].notna() & (df['Lat'] != 0) & (df['Long'] != 0)]
    print("🧩 Computing representative points per Polling District...")

    # Calculate the average centroid coordinates per PD group
    pd_pts = valid_coords.groupby('PD')[['Long', 'Lat']].mean().reset_index()

    if pd_pts.empty:
        print("❌ [Hierarchy] No valid coordinates available to calculate representatives.")
        return {}

    gdf_pts = gpd.GeoDataFrame(
        pd_pts,
        geometry=gpd.points_from_xy(pd_pts['Long'], pd_pts['Lat']),
        crs="EPSG:4326"
    )

    # Spatial Join: Match the representative points to their containing Ward
    pd_to_ward = {}
    if not is_ward_empty:
        gdf_ward = ward_layer.copy().to_crs("EPSG:4326")[['NAME', 'geometry']].rename(columns={'NAME': 'Ward_Name'})
        joined_ward = gpd.sjoin(gdf_pts, gdf_ward, how='left', predicate='intersects')
        joined_ward = joined_ward.drop_duplicates(subset='PD')
        pd_to_ward = dict(zip(joined_ward['PD'], joined_ward['Ward_Name']))

    # Spatial Join: Match the representative points to their containing Division
    pd_to_div = {}
    if not is_div_empty:
        gdf_div = div_layer.copy().to_crs("EPSG:4326")[['NAME', 'geometry']].rename(columns={'NAME': 'Div_Name'})
        joined_div = gpd.sjoin(gdf_pts, gdf_div, how='left', predicate='intersects')
        joined_div = joined_div.drop_duplicates(subset='PD')
        pd_to_div = dict(zip(joined_div['PD'], joined_div['Div_Name']))

    hierarchy_map = {}
    for pd_code in pd_pts['PD'].unique():
        w_name = pd_to_ward.get(pd_code)
        d_name = pd_to_div.get(pd_code)

        # 🎯 Apply normalname() clean up to matched strings or fallback to 'OUTSIDE'
        norm_ward = normalname(str(w_name).strip()) if pd.notna(w_name) and str(w_name).strip() != "" else "OUTSIDE"
        norm_div = normalname(str(d_name).strip()) if pd.notna(d_name) and str(d_name).strip() != "" else "OUTSIDE"

        hierarchy_map[pd_code] = {
            "Ward": norm_ward,
            "Division": norm_div
        }

    print(f"✅ [Hierarchy] Map compiled with {len(hierarchy_map)} entries using representative points.")
    return hierarchy_map


def assign_areas_by_polling_district(electors_df, rlevels, progress=None):
    from state import update_progress
    import pandas as pd
    import numpy as np

    print("\n🚀 --- STARTING DEBUG: assign_areas_by_polling_district ---")

    if progress:
        update_progress(progress, "assign_areas", 0.0, "Inheriting hierarchy from existing PD values...")

    print(f"📊 Incoming DataFrame Shape: {electors_df.shape}")

    for col in ['PD', 'Ward', 'Division']:
        if col not in electors_df.columns:
            electors_df[col] = None

    existing_wards = electors_df['Ward'].copy()
    existing_divisions = electors_df['Division'].copy()

    # 🔄 INHERIT WARD & DIVISION STRINGS
    print("\n🔄 Entering Point Hierarchy Inheritance Pipeline...")
    try:
        # 🎯 HERE IS THE INVOCATION: Pass electors_df down to build the dynamic map!
        hierarchy_lookup = GetHierarchyMapFromPoints(electors_df)
        print(f"   ℹ️ Dynamic Lookup active. Found {len(hierarchy_lookup)} structural keys.")

        # Diagnostic check on key format matching
        sample_lookup_keys = list(hierarchy_lookup.keys())[:3]
        sample_assigned_pds = [x for x in electors_df['PD'].dropna().unique() if x != 'OUTSIDE'][:3]
        print(f"   🔍 Lookup Map Schema Check:")
        print(f"      > Sample dictionary lookup keys: {sample_lookup_keys}")
        print(f"      > Sample assigned dataframe PDs: {sample_assigned_pds}")

        seen_misses = set()

        def debug_rollup(pd_val, col_name, fallback_val):
            fallback_str = str(fallback_val)
            if "-MAP" in fallback_str.upper() or fallback_str == 'None' or fallback_str.upper() == 'NAN':
                fallback_str = "OUTSIDE"

            if pd_val and pd_val not in ['OUTSIDE', 'NONE']:
                node = hierarchy_lookup.get(pd_val)
                if node is None:
                    if pd_val not in seen_misses:
                        print(f"   ⚠️ LOOKUP MISS: PD code '{pd_val}' unmapped. Using fallback: '{fallback_str}'")
                        seen_misses.add(pd_val)
                    return fallback_str

                target_val = node.get(col_name)
                if not target_val or target_val == "OUTSIDE":
                    return fallback_str

                return target_val
            return fallback_str

        print("⚙️ Processing vector evaluations across ALL rows...")
        new_wards = [
            debug_rollup(pd_v, 'Ward', fb_w)
            for pd_v, fb_w in zip(electors_df['PD'], existing_wards)
        ]
        new_divs = [
            debug_rollup(pd_v, 'Division', fb_d)
            for pd_v, fb_d in zip(electors_df['PD'], existing_divisions)
        ]

        electors_df['Ward'] = new_wards
        electors_df['Division'] = new_divs

    except Exception as e:
        print(f"❌ EXCEPTION inside hierarchy engine: {str(e)}")
        import traceback
        traceback.print_exc()

    # Final cleanup sweep to safely catch unassigned rows
    for col in ['PD', 'Ward', 'Division']:
        electors_df[col] = electors_df[col].fillna('OUTSIDE')

    print("\n🏁 --- END OF DEBUG SUMMARY ---")
    for col in ['PD', 'Ward', 'Division']:
        unique_summary = electors_df[col].value_counts().head(3).to_dict()
        print(f"📌 Column '{col}' final distribution highlights: {unique_summary}")
    print("--------------------------------------------------\n")

    return electors_df

def assign_walks_and_zones(
    electors_df,
    teamsize,
    territory_path,
    rlevels,
    aprefix,
    max_walk_size=300,
    max_depth=10,
    cluster_by_col='PD',
    progress=None
):
    from state import update_progress

    for col in ['WalkName', 'WalkName_hier', 'Zone']:
        if col not in electors_df.columns:
            electors_df[col] = np.nan

    mask_assign = (electors_df[cluster_by_col].notna()) & (electors_df[cluster_by_col] != 'OUTSIDE') & (
        electors_df['WalkName'].isna() | (electors_df['WalkName'] == '')
    )
    to_assign = electors_df.loc[mask_assign]

    if to_assign.empty:
        return electors_df

    unique_areas = to_assign[cluster_by_col].unique()

    for area_name in unique_areas:
        area_mask = (electors_df[cluster_by_col] == area_name) & (electors_df.index.isin(to_assign.index))
        area_indices = electors_df.index[area_mask]
        df_area = electors_df.loc[area_indices]

        if df_area.empty:
            continue

        area_walk_labels = recursive_kmeans(df_area, prefix=aprefix, max_walk_size=max_walk_size)
        hier_series = pd.Series(area_walk_labels, index=area_indices)
        electors_df.loc[area_indices, 'WalkName_hier'] = hier_series

        unique_label_map = {}
        serial_dict = {}  # ⚡ Faster, cleaner memory map dictionary to avoid loc insertion performance drops
        local_walk_count = 0

        for idx, raw_label in hier_series.items():
            label_key = str(raw_label).strip()
            if label_key not in unique_label_map:
                local_walk_count += 1
                unique_label_map[label_key] = f"{area_name}_{local_walk_count:02}"
            serial_dict[idx] = unique_label_map[label_key]

        electors_df.loc[area_indices, 'WalkName'] = pd.Series(serial_dict)

        # ---------------------------------------------------------
        # Zone Clustering
        # ---------------------------------------------------------
        walk_centers = electors_df.loc[area_indices].groupby('WalkName').agg({
            'Lat': 'mean',
            'Long': 'mean'
        })

        num_walks_in_area = len(walk_centers)
        N = min(8, num_walks_in_area)

        if N > 1:
            kmeans = KMeans(n_clusters=N, random_state=42, n_init='auto')
            walk_centers['ZoneLabel'] = kmeans.fit_predict(walk_centers[['Lat', 'Long']])
            zone_map = {walk: f"ZONE_{label + 1}" for walk, label in walk_centers['ZoneLabel'].items()}
            electors_df.loc[area_indices, 'Zone'] = electors_df.loc[area_indices, 'WalkName'].map(zone_map)
        else:
            electors_df.loc[area_indices, 'Zone'] = 'ZONE_1'

    if progress:
        update_progress(progress, "assign_walks", 1.0, f"Walk & zone assignment complete via {cluster_by_col} .")

    return electors_df


def check_columns_consistency(mainframe, *frames, verbose=True):
    """
    Ensure all frames have the same columns as mainframe. Mutates frames inside array elements.
    """
    main_cols = list(mainframe.columns)
    main_cols_set = set(main_cols)
    all_passed = True

    for i, frame in enumerate(frames):
        frame_cols_set = set(frame.columns)
        missing = main_cols_set - frame_cols_set
        extra = frame_cols_set - main_cols_set

        # Add missing columns
        for col in missing:
            frame[col] = None

        # Remove extra columns safely in-place
        if extra:
            frame.drop(columns=list(extra), inplace=True, errors='ignore')

        # 🩹 FIX: Reindex the frame columns in-place using assign or direct column override matching execution logic
        for col in main_cols:
            if col not in frame.columns:
                frame[col] = None

        if verbose:
            if missing: print(f"Frame {i+1}: Added missing columns -> {missing}")
            if extra: print(f"Frame {i+1}: Removed extra columns -> {extra}")

        if list(frame.columns) != main_cols:
            all_passed = False

    return all_passed


# Ensure your normalname helper is imported/accessible
# from standardiser import normalname



def background_normalise(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table):
    """
    Full background normalisation routine with targeted dynamic pre-flight
    spatial exploration and vectorized spatial join operations.
    """
    import logging
    import os
    import traceback
    import re
    import pandas as pd
    import geopandas as gpd
    from shapely.geometry import Point, Polygon, shape  # Fixed missing shape import
    from elector import electors, shapecolumn
    from layers import ensure_treepolys_with_index
    from state import progress, DQstats, update_progress
    from elections import CurrentElection
    from layers import create_boundary_geom

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        filename = LOG_FILE
    )
    logger = logging.getLogger(__name__)

    try:
        mainframes, deltaframes, aviframes, pledge_frames, DQstatslist = [], [], [], [], []
        ROOT = "ROOT"

        # =========================================================================
        # --- Stage 1: Sourcing & Path Resolution ---
        # =========================================================================
        update_progress(progress, "sourcing", 0.0, "Sourcing raw data...")

        current_election = session_data.get('current_election', 'UNKNOWN')
        CElection = CurrentElection.load(current_election)
        resolved_levels = CElection.resolved_levels
        parent_levels = CElection.parent_levels
        territory_path = CElection['territory']
        lastfilepath = CElection['mapfiles'][-1]


        # Unpack the active levels mapping dictionary
        (_, elevels), = resolved_levels.items()

        sorted_items = sorted(meta_data.items(), key=lambda x: int(x[1]['order']))

        # =========================================================================
        # --- Stage 2: Process Raw File Imports ---
        # =========================================================================
        total_files = len(sorted_items)
        for idx, (index, data) in enumerate(sorted_items):
            file_path = data.get('saved_path') or data.get('stored_path', '')
            if file_path and not os.path.isabs(file_path):
                try:
                    workdir = config.workdirectories['workdir']
                except NameError:
                    workdir = session_data.get('workdir', os.getcwd())
                file_path = os.path.join(workdir, file_path)

            if not os.path.exists(file_path):
                continue

            purpose = data.get('purpose')
            fixlevel = int(data.get('fixlevel', 0)) if data.get('fixlevel') else 0

            # Calculate granular progress through file parsing
            stage_frac = round((idx / max(total_files, 1)) * 0.30, 2)
            update_progress(progress, "processing", stage_frac, message=f"Processing file {idx + 1} of {total_files}...")
            if file_path.upper().endswith('.CSV'):
                dfx = pd.read_csv(file_path, sep=None, engine='python', encoding='ISO-8859-1', keep_default_na=False, on_bad_lines='warn')
            elif file_path.upper().endswith('.XLSX'):
                dfx = pd.read_excel(file_path, engine='openpyxl', keep_default_na=False)
            else:
                continue

            # Clean column names
            dfx.columns = [c.encode('ascii', 'ignore').decode('ascii').strip() for c in dfx.columns]

            results = normz(progress, RunningVals, Lookups, data.get('election'), file_path, dfx, fixlevel, purpose)
            temp_df = pd.DataFrame(results[0])
            DQstatslist.append(results[1])

            if purpose == 'main': mainframes.append(temp_df)
            elif purpose == 'delta': deltaframes.append(temp_df)
            elif purpose == 'avi': aviframes.append(temp_df)
            elif purpose == 'pledge': pledge_frames.append(temp_df)

        all_new = mainframes + deltaframes
        if not all_new:
            update_progress(progress, "error", 1.0, "No valid electoral files", status="error")
            return

        # =========================================================================
        # --- Stage 2.1: Pre-Flight Spatial Discovery Pass ---
        # =========================================================================
        update_progress(progress, "spatial_discovery", 0.35, "Computing PD-centroid Convex Hull...")
        preflight_df = pd.concat(all_new, ignore_index=True)
        preflight_df['latitude'] = pd.to_numeric(preflight_df.get('latitude', preflight_df.get('Lat')), errors='coerce')
        preflight_df['longitude'] = pd.to_numeric(preflight_df.get('longitude', preflight_df.get('Long')), errors='coerce')

        # Filter valid coordinates
        valid_coords_df = preflight_df[preflight_df['latitude'].notna() & preflight_df['longitude'].notna()].copy()

        pd_column = 'PD'
        hull_geometry = None
        unique_anchors = []

        if not valid_coords_df.empty:
            gdf = gpd.GeoDataFrame(
                valid_coords_df,
                geometry=gpd.points_from_xy(valid_coords_df['longitude'], valid_coords_df['latitude']),
                crs="EPSG:4326"
            )

            if pd_column in gdf.columns:
                centroids_per_pd = gdf.groupby(pd_column).geometry.apply(lambda g: g.unary_union.centroid)
                centroid_union = centroids_per_pd.unary_union
            else:
                centroid_union = gdf.geometry.unary_union

            hull_geometry = centroid_union.convex_hull

            if hull_geometry.geom_type == 'Polygon':
                unique_anchors = [[y, x] for x, y in hull_geometry.exterior.coords]
            elif hull_geometry.geom_type == 'LineString':
                unique_anchors = [[y, x] for x, y in hull_geometry.coords]
            elif hull_geometry.geom_type == 'Point':
                unique_anchors = [[hull_geometry.y, hull_geometry.x]]

        def prepare_here_parameter(hull_geometry):
            if hull_geometry is None or hull_geometry.is_empty:
                return None
            centroid = hull_geometry.centroid
            return (centroid.y, centroid.x)

        here_loc = prepare_here_parameter(hull_geometry)

        # =========================================================================
        # --- Stage 2.2: Pre-Flight Treepolys Hydration Pass ---
        # =========================================================================
        print(f"📡 PRE-FLIGHT: Computed PD-centroid Convex Hull ({here_loc}) ")
        update_progress(progress, "spatial_discovery", 0.5, "Uploading data centric geometries  ...")

        lastfilepath, layers.Geo_index = ensure_treepolys_with_index(
            sourcepath=None,
            here=here_loc,
            resolved_levels=resolved_levels,
            parent_levels=parent_levels,
            areaelectors=preflight_df
        )

        print(f"📡 PRE-FLIGHT: completed ({lastfilepath}) ")
        update_progress(progress, "spatial_discovery", 1, "Commencing point-in-polygon vector analysis ...", status="complete")

#         current_node = nodes.MapRoot.ping_node(resolved_levels, lastfilepath, create=True, accumulate=False)
        new_df = preflight_df.copy()
        persist(layers.Treepolys, layers.Geo_index)

        from pathlib import Path

        # 1. Execute preflight / tree resolution first
        # lastfilepath, treepolys = ensure_treepolys(territory_path)

        # 2. Extract path components from the validated lastfilepath
        geo_parts = stepify(lastfilepath)

        # 3. Construct schema levels dynamically
        schema_levels = ["Country", "Nation", "County"]
        max_index = max(max(elevels.keys(), default=0) + 1, len(geo_parts))

        for idx in range(3, max_index):
            if idx in elevels:
                layer_raw_token = elevels[idx]
                primary_layer = [l.strip() for l in layer_raw_token.split('/') if l.strip()][0]
                canonical = shapecolumn.get(primary_layer.lower(), primary_layer.capitalize())
                schema_levels.append(canonical)
            else:
                schema_levels.append("Constituency" if idx == 3 else f"Level_{idx}")

        # 4. Build static geo_context from guaranteed directory parts
        geo_context = {
            schema_levels[i]: geo_parts[i]
            for i in range(len(geo_parts))
            if i < len(schema_levels)
        }

        print(f"🔍 DEBUG [1/5] Path Resolution:")
        print(f"   > Cleaned Geo Directory Parts: {geo_parts}")
        print(f"   > Mapped Schema Columns: {schema_levels}")
        print(f"   > Resolved Geo Context: {geo_context}")

        # =========================================================================
        # --- Stage 2.5: Vectorized Spatial Join & Hierarchy Assignment ---
        # =========================================================================
        update_progress(progress, "spatial_join", 0.2, "Commencing point-in-polygon vector analysis...")
        print("\n🌐 [STAGE 2.5] SPATIAL ENGINE: Commencing point-in-polygon vector analysis...")

        # 1. Inject static top-level geo context
        print("📌 DEBUG [2.5.1] Injecting static top-level geo context...")
        for col_name, val_str in geo_context.items():
            if col_name not in new_df.columns:
                new_df[col_name] = val_str
                print(f"   + Added column '{col_name}' with value '{val_str}'")
            else:
                new_df[col_name] = new_df[col_name].replace("", None).fillna(val_str)
                print(f"   ~ Filled column '{col_name}' defaults with '{val_str}'")

        # 2. Build spatial boundary records using tree traversal truth
        print("\n🌲 DEBUG [2.5.2] Processing Treepolys dictionary...")
        poly_records = []
        skipped_nodes_count = 0
        skipped_geoms_count = 0
        total_tree_entries = 0

        for level_key, polys_dict in Treepolys.items():
            if not isinstance(polys_dict, dict):
                print(f"   ⚠️ Skipping non-dict level_key in Treepolys: {level_key}")
                continue

            print(f"   ► Processing level_key '{level_key}' ({len(polys_dict)} potential shapes)")
            total_tree_entries += len(polys_dict)

            for unique_path, geom_obj in polys_dict.items():
                # 🌲 Resolve exact node structural truth
                target_node = find_node_by_path(unique_path)
                if not target_node:
                    skipped_nodes_count += 1
                    print(f"     ❌ Node resolution failed for path: {unique_path}")
                    continue

                # Parse spatial geometry
                actual_geom = None
                try:
                    if isinstance(geom_obj, gpd.GeoDataFrame):
                        actual_geom = geom_obj.geometry.unary_union
                    elif isinstance(geom_obj, gpd.GeoSeries):
                        actual_geom = geom_obj.unary_union
                    elif isinstance(geom_obj, pd.Series) and 'geometry' in geom_obj:
                        actual_geom = geom_obj['geometry']
                    elif isinstance(geom_obj, dict):
                        actual_geom = shape(geom_obj)
                    else:
                        actual_geom = geom_obj

                    if actual_geom is None or getattr(actual_geom, "is_empty", True):
                        skipped_geoms_count += 1
                        print(f"     ⚠️ Empty or null geometry skipped: {unique_path}")
                        continue
                except Exception as e:
                    skipped_geoms_count += 1
                    print(f"     ⚠️ Exception parsing shape for {unique_path}: {e}")
                    continue

                # Build record starting with geometry
                record = {"_full_path": unique_path, "geometry": actual_geom}

                # Walk up the tree lineage to populate EXACT column targets dynamically
                cur = target_node
                lineage_mapped = []
                while cur:
                    col = shapecolumn.get(cur.type, cur.type.capitalize())
                    record[col] = cur.value
                    lineage_mapped.append(f"{col}={cur.value}")
                    cur = cur.parent

                poly_records.append(record)

        print(f"   📊 Treepolys Summary: Total Entries={total_tree_entries} | Missing Nodes={skipped_nodes_count} | Invalid Geoms={skipped_geoms_count} | Valid Boundaries={len(poly_records)}")

        # 3. Perform Spatial Join & Fill DataFrame
        print("\n🗺️ DEBUG [2.5.3] Executing Spatial Join...")
        update_progress(progress, "spatial_join", 0.5, "Executing Spatial Join ...")

        if not poly_records:
            print("   ⚠️ CRITICAL: No valid polygon records were extracted! Spatial join will be skipped.")
        else:
            boundaries_gdf = gpd.GeoDataFrame(poly_records, geometry="geometry", crs="EPSG:4326")
            print(f"   ► Created Boundaries GeoDataFrame: Shape={boundaries_gdf.shape}")

            # Collect all target hierarchy columns present in the spatial records
            target_cols = [c for c in boundaries_gdf.columns if c not in ["_full_path", "geometry"]]
            print(f"   ► Spatial Target Hierarchy Columns: {target_cols}")

            for col in target_cols:
                if col not in new_df.columns:
                    new_df[col] = ""
                    print(f"   + Initialized missing target column in DataFrame: '{col}'")

            lat_col = next((c for c in ['latitude', 'Lat', 'LAT'] if c in new_df.columns), None)
            lon_col = next((c for c in ['longitude', 'Long', 'LONG'] if c in new_df.columns), None)
            print(f"   ► Coordinate Columns Detected: Latitude='{lat_col}' | Longitude='{lon_col}'")

            if not lat_col or not lon_col:
                print("   ❌ CRITICAL: Could not identify latitude and longitude columns in DataFrame!")
            else:
                spatial_valid_mask = new_df[lat_col].notna() & new_df[lon_col].notna()
                valid_coords_count = spatial_valid_mask.sum()
                print(f"   ► Valid Coordinate Rows: {valid_coords_count} of {len(new_df)}")

                if valid_coords_count == 0:
                    print("   ⚠️ No valid coordinates found in DataFrame for spatial join.")
                else:
                    points_gdf = gpd.GeoDataFrame(
                        new_df[spatial_valid_mask].copy(),
                        geometry=gpd.points_from_xy(
                            new_df.loc[spatial_valid_mask, lon_col],
                            new_df.loc[spatial_valid_mask, lat_col]
                        ),
                        crs="EPSG:4326"
                    )

                    print(f"   ► Performing `gpd.sjoin` (predicate='within')...")
                    joined = gpd.sjoin(
                        points_gdf,
                        boundaries_gdf,
                        how="left",
                        predicate="within",
                        lsuffix="left",
                        rsuffix="right"
                    )
                    print(f"   ► Spatial Join Result Shape: {joined.shape}")

                    # Map matched spatial boundary values back to new_df
                    for col in target_cols:
                        match_col = f"{col}_right" if f"{col}_right" in joined.columns else col
                        if match_col in joined.columns:
                            pre_fill_matched = joined[match_col].notna().sum()

                            new_df.loc[spatial_valid_mask, col] = (
                                joined[match_col]
                                .fillna(new_df.loc[spatial_valid_mask, col])
                            )
                            print(f"     ✓ Column '{col}': Successfully mapped {pre_fill_matched} matches from spatial layer '{match_col}'")
                        else:
                            print(f"     ⚠️ Column '{col}': Match column '{match_col}' missing from join result!")

                    print("🎯 SPATIAL ENGINE COMPLETE: Vector join finished successfully.")
                    update_progress(progress, "spatial_join", 0.8, "Spatial Join created...")

        # --- Safe Vectorized Fallback PD Assignment ---
        pd_col = shapecolumn.get('polling_district', 'PD')
        ward_col = shapecolumn.get('ward', 'Ward')
        div_col = shapecolumn.get('division', 'Division')
        const_col = shapecolumn.get('constituency', 'Constituency')

        unassigned_mask = (
            new_df[ward_col].astype(str).str.strip().eq("") |
            new_df[ward_col].astype(str).str.strip().eq("OUTSIDE") |
            new_df[ward_col].isna()
        ) if ward_col in new_df.columns else pd.Series(False, index=new_df.index)

        if unassigned_mask.any() and pd_col in new_df.columns:
            valid_assigned = new_df[~unassigned_mask & new_df[pd_col].notna() & (new_df[pd_col].astype(str).str.strip() != "")]

            if not valid_assigned.empty:
                lookup_cols = [c for c in [ward_col, div_col, const_col] if c in valid_assigned.columns]
                pd_lookup = valid_assigned.groupby(pd_col)[lookup_cols].first()

                for col in lookup_cols:
                    mapped_vals = new_df.loc[unassigned_mask, pd_col].map(pd_lookup[col]).fillna("OUTSIDE")
                    new_df.loc[unassigned_mask, col] = mapped_vals

        if ward_col in new_df.columns:
            new_df[ward_col] = new_df[ward_col].replace("", "OUTSIDE").fillna("OUTSIDE")

        # Clean up any residual duplicate lowercase columns if present
        duplicate_cols = [c for c in new_df.columns if c.islower() and c.capitalize() in new_df.columns]
        if duplicate_cols:
            new_df.drop(columns=duplicate_cols, inplace=True)
        update_progress(progress, "spatial_join", 1.0, "Injecting AVI and Pledge tags ...",status="complete")
        # =========================================================================
        # --- Stage 3: Tag Injection (AVI & Pledge) ---
        # =========================================================================
        update_progress(progress, "tagging", 0.7, "Injecting AVI and Pledge tags...")

        def apply_tags(target_df, source_frames, tag_code, label):
            if not source_frames or 'ENOP' not in target_df.columns:
                return target_df

            combined_source = pd.concat(source_frames, ignore_index=True)
            if 'ENOP' not in combined_source.columns:
                return target_df

            target_df['ENOP'] = target_df['ENOP'].astype(str).str.strip()
            valid_enops = set(combined_source['ENOP'].astype(str).str.strip().unique()) - {"", "nan", "None"}

            if 'Tags' not in target_df.columns:
                target_df['Tags'] = ""

            mask = target_df['ENOP'].isin(valid_enops)

            def append_tag(val):
                val_str = str(val).strip() if pd.notna(val) else ""
                if not val_str or val_str == "nan":
                    return tag_code
                existing = [t.strip() for t in re.split(r'[,;|]', val_str)]
                return val_str if tag_code in existing else f"{val_str}, {tag_code}"

            target_df.loc[mask, 'Tags'] = target_df.loc[mask, 'Tags'].apply(append_tag)
            print(f"   > Injected '{tag_code}' tag into {mask.sum()} records.")
            return target_df

        new_df = apply_tags(new_df, aviframes, 'AV', 'AVI')
        new_df = apply_tags(new_df, pledge_frames, 'PL', 'Pledge')
        update_progress(progress, "tagging", 1.0, "Merging and deduplicating elector records...", status="complete")

        # =========================================================================
        # --- Stage 4: Safe Merge & Deduplication ---
        # =========================================================================
        update_progress(progress, "deduplication", 0.8, "Merging and deduplicating elector records...")
        existing_all = pd.concat(electors.elections.values(), ignore_index=True) if electors.elections else pd.DataFrame()
        new_df['is_new_import'] = True
        if not existing_all.empty:
            existing_all['is_new_import'] = False

        combined = pd.concat([existing_all, new_df], ignore_index=True)

        if 'ENOP' in combined.columns:
            has_enop = combined['ENOP'].astype(str).str.strip().ne("") & combined['ENOP'].notna()
            df_with_enop = combined[has_enop].drop_duplicates(subset='ENOP', keep='last')
            df_without_enop = combined[~has_enop]
            combined = pd.concat([df_with_enop, df_without_enop], ignore_index=True)
        update_progress(progress, "deduplication", 1.0, "Merging and deduplicating elector records...", status="complete")

        # =========================================================================
        # --- Stage 5: Spatial Assignment & Persistence ---
        # =========================================================================
        update_progress(progress, "assignment", 0.9, "Assigning walks, zones, and persisting data...")
        new_only_df = combined[combined['is_new_import'] == True].copy()

        assigned_df = assign_areas_by_polling_district(new_only_df, resolved_levels, progress=progress)

        teamsize = int(CElection.get('teamsize', 5))
        max_walk_size = CElection.get('walksize', 300)

        assigned_df = assign_walks_and_zones(
            electors_df=assigned_df,
            teamsize=teamsize,
            territory_path=territory_path,
            rlevels=resolved_levels,
            aprefix=state.selprefix(current_election),
            max_walk_size=max_walk_size,
            cluster_by_col='PD',
            progress=progress
        )


        electors.add_or_update(current_election, assigned_df)
        electors.save()
        assigned_df.to_csv("zonedelectors.csv", sep='\t', encoding='utf-8', index=False)

        # Signal completed status via update_progress
        update_progress(
            progress,
            "assignment",
            1.0,
            "New data imported",
            status="complete"
        )

    except Exception as e:
        print("❌ Exception:", e)
        print(traceback.format_exc())
        update_progress(
            progress,
            "error",
            1.0,
            str(e),
            status="error"
        )
# --------------------------
# Utility Functions
# --------------------------

def compute_font_size(days_to_event):
    days = -days_to_event
    if days <= -35: return 10
    if days <= -20: return 14
    if days <= -10: return 18
    return 22

def offset_latlong(lat, lon, bearing_deg, distance_m=100):
    try:
        bearing_deg = float(bearing_deg)
        if math.isnan(bearing_deg):
            bearing_deg = 0
    except:
        bearing_deg = 0

    R = 6371000
    b = math.radians(bearing_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    d = distance_m / R

    new_lat = math.asin(
        math.sin(lat_r)*math.cos(d) +
        math.cos(lat_r)*math.sin(d)*math.cos(b)
    )
    new_lon = lon_r + math.atan2(
        math.sin(b)*math.sin(d)*math.cos(lat_r),
        math.cos(d) - math.sin(lat_r)*math.sin(new_lat)
    )

    return math.degrees(new_lat), math.degrees(new_lon)

def get_latlong(postcode, lat, lon):
    # Fast path: valid input coordinates
    print(f"___Postcode {postcode} Lat {lat} Long: {lon}")

    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        if not math.isnan(lat) and not math.isnan(lon):
            return round(lat, 6), round(lon, 6)

    # Fallback: no postcode → centroid
    if not postcode:
        return node.latlongroid

    # API lookup
    url = f"http://api.getthedata.com/postcode/{postcode.replace(' ', '+')}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            j = r.json()
            if j.get("status") == "match":
                return (round(float(j["data"]["latitude"]), 6),
                        round(float(j["data"]["longitude"]), 6))
    except:
        pass

    # Fallback on failure
    return node.latlongroid

def generate_place_code(prefix):
    return ''.join(re.findall(r'\b\w', prefix)).upper()

# tables.py

def fetch_table(rlevels,table_name, current_node):
    """
    Returns a tuple (column_headers, rows_dict, title) for the requested table.
    `create_node` determines whether to recreate path nodes if last node not found.
    """
    # Local helpers for standard tables
    from state import DQstats

    def get_resources_table():
        return pd.DataFrame(resources)

    def get_report_table():
        try:
            if DQstats:
                return pd.DataFrame(DQstats)
        except:
            pass
        return pd.DataFrame(DQstats or [])

    def get_places_table():
        if not places:
            return pd.DataFrame()
        if isinstance(places, dict):
            return pd.DataFrame.from_dict(places, orient='index')
        elif isinstance(places, list):
            return pd.DataFrame(places)
        else:
            raise TypeError("places must be a dict or list")

    print(f"____retrieving table: {table_name} for node: {current_node.value}")
    # Mapping table names to functions
    table_map = {
        "DQstats": get_report_table,
        "resources": get_resources_table,
        "places": get_places_table
    }

    # Handle dynamic tables like _layer or _xref
    if table_name.endswith("_layer"):
        tabtype = table_name.removesuffix("_layer")
        print(f"FINDNODE AT TYPE: {tabtype}")
        tabnode = current_node.findnodeparenting_type(tabtype)
        column_headers, rows, title = get_layer_table(
            tabnode.childrenoftype(tabtype),
            str(tabtype) + "s",
            rlevels
        )
        return column_headers, rows.to_dict(orient="records"), title

    elif table_name.endswith("_xref"):
            # The lowest data tier where raw electors and houses live
            TARGET_DATA_LEVEL = 5

            # Determine what type of node lives at the targeted leaf level
            r_dict = next(iter(rlevels.values()))
            tabtype = r_dict.get(TARGET_DATA_LEVEL, r_dict[current_node.level + 1])

            # Recursive helper to drill down and gather all leaf nodes under this branch
            def gather_leaf_nodes(node, target_level):
                if node.level == target_level:
                    return [node]

                leaf_accumulator = []
                if hasattr(node, 'children') and node.children:
                    for child in node.children:
                        leaf_accumulator.extend(gather_leaf_nodes(child, target_level))
                return leaf_accumulator

            # If we are above the data tier, recursively fetch all matching leaf children
            if current_node.level < TARGET_DATA_LEVEL:
                nodelist = gather_leaf_nodes(current_node, TARGET_DATA_LEVEL)
            else:
                # Fallback if we are already at or below the data level
                nodelist = current_node.childrenoftype(tabtype)

            print(f"___table:{current_node.value} (Level {current_node.level}) -> Gathered {len(nodelist)} Level {TARGET_DATA_LEVEL} leaf nodes")

            column_headers, rows, title = get_layer_table(
                nodelist,
                str(tabtype) + "s",
                rlevels
            )
            return column_headers, rows.to_dict(orient="records"), title

    elif table_name in table_map:
        df = table_map[table_name]()
        column_headers = list(df.columns)
        rows = df.to_dict(orient="records")
        title = table_name.replace("_", " ").title()
        return column_headers, rows, title

    else:
        raise ValueError(f"Table '{table_name}' not found")


# 1. Create the app instance
app = Flask(
    __name__,
    static_folder='/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/static',
    static_url_path='/static'
)
# 2. Basic Flask & Path configurations
sys.path.append(r'/Users/newbrie/Documents/ReformUK/GitHub/Electtrek')
app.config['SECRET_KEY'] = 'rosebutt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/newbrie/Documents/ReformUK/GitHub/Electtrek/trekusers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = '/Users/newbrie/Sites'
app.config['APPLICATION_ROOT'] = '/Users/newbrie/Documents/ReformUK/GitHub/Electtrek'
app.config['TESTING'] = False

# 3. Initialize SQLAlchemy FIRST so we can use the 'db' object in session config
db = SQLAlchemy(app)

# 4. Session configurations (Must come AFTER db initialization)
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db  # Now 'db' is defined!
app.config['SESSION_SQLALCHEMY_TABLE'] = 'flask_sessions'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True

# 5. Cookie & Security configurations
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True if using HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['USE_SESSION_FOR_NEXT'] = False

# 6. Initialize Extensions (CORS, Session, Login)
CORS(app, supports_credentials=True)
Session(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "<h1>You really need to login!!</h1>"
login_manager.refresh_view = "index"
login_manager.needs_refresh_message = "<h1>You really need to re-login to access this page</h1>"
login_manager.login_message_category = "info"

# 7. Create database tables (including the new session table)
with app.app_context():
    db.create_all()

# Password used by server to protect files
SERVER_PASSWORD = os.environ.get("CAL_PROTECT_PASSWORD", "secret123")


login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = "<h1>You really need to login!!</h1>"
login_manager.refresh_view = "index"
login_manager.needs_refresh_message = "<h1>You really need to re-login to access this page</h1>"
login_manager.login_message_category = "info"

def validate_election_root(root, election):
    expected = state.ROOT_LEVEL[election["territories"]]
    if root.level != expected:
        raise ValueError(
            f"Election root level {root.level} "
            f"does not match territories {election['territories']} "
            f"(expected {expected})"
        )




# eventually extract calendar areas directly from the associated MAP

def find_children_at(level):
    [x.value for x in current_node.childrenoftype('walk')]
    return dropdownlist


import config
from jinja2 import Environment, FileSystemLoader
templateLoader = FileSystemLoader(searchpath=config.workdirectories['templdir'])
environment = Environment(loader=templateLoader,auto_reload=True)



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self,password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user

@login_manager.unauthorized_handler     # In unauthorized_handler we have a callback URL
def unauthorized_callback():            # In call back url we can specify where we want to
    return render_template("index.html") # redirect the user in my case it is login page!


# From here on we have backend route definitions
#
#

@app.route("/reverse_geocode")
@login_required
def reverse_geocode():
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    print(f"____Route/reverse_geocode - {lat}:{lng} ")
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}&addressdetails=1"
    response = requests.get(url, headers={"User-Agent": "YourAppName"})
    data = response.json()

    address = data.get("display_name", "Unknown location")
    postcode = data.get("Address1", {}).get("Postcode", "N/A")
    print(f"latlng - {lat}:{lng} url:{url} - addr:{address} - pc:{postcode}")
    return jsonify({"Address1": address, "Postcode": postcode})


@app.route('/add_marker', methods=['POST'])
@login_required
def add_marker():
    data = request.get_json()
    key = len(places) + 1
    places[key] = data
    print(f"Places updated: {places}")  # for debug
    return jsonify({'status': 'ok', 'id': key})


@app.route('/delete_node', methods=['POST'])
@login_required
def delete_node():
    from layers import Geo_index

    if not request.is_json:
        return jsonify(status="error", message="JSON required"), 415

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    data = request.get_json()
    nid = (data.get("nid") or "").strip()

    if not nid:
        return jsonify(status="error", message="Node id required"), 400

    node_to_delete = nodes.TREK_NODES_BY_ID.get(nid)

    if not node_to_delete:
        return jsonify(status="error", message="Node not found"), 404

    if not node_to_delete.parent:
        return jsonify(status="error", message="Cannot delete root node"), 400

    if node_to_delete.children:
        return jsonify(status="error",
                       message="Cannot delete node with children"), 400

    parent = node_to_delete.parent

    try:
        # Remove from tree
        parent.children.remove(node_to_delete)
        node_to_delete.parent = None
        parent.last_modified = datetime.utcnow()

        # Remove registry entry
        nodes.TREK_NODES_BY_ID.pop(node_to_delete.nid, None)

        # Regenerate parent map
        current_election = CurrentElection.get_lastused()
        CElection = CurrentElection.load(current_election)
        rlevels = CElection.resolved_levels
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"
        # The clean unpack
        (c_election, elevels), = rlevels.items()

        map, totalleaf = parent.create_node_map(CElection,layers.Geo_index,rlevels, static=False)

        parent.visit_node(CElection)

        save_nodes(TREKNODE_FILE)
        persist(layers.Treepolys, layers.Geo_index)

    except Exception:
        current_app.logger.exception("Node deletion failed")
        return jsonify(status="error", message="Deletion failed"), 500

    return jsonify({
        "status": "success",
        "message": "Node deleted",
        "mapfile": url_for("thru", path=parent.mapfile())
    })



@app.route('/reassign_parent', methods=['POST'])
@login_required
def reassign_parent():
    from elector import electors


    if not request.is_json:
        return jsonify(status="error", message="JSON required"), 415

    data = request.get_json()
    nid = (data.get("nid") or "").strip()
    new_parent_nid = (data.get("new_parent_nid") or "").strip()

    if not nid or not new_parent_nid:
        return jsonify(status="error",
                       message="Node ids required"), 400

    # ---- Restore state FIRST ----
    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels

    # ---- Lookup nodes ----
    subject_node = nodes.TREK_NODES_BY_ID.get(nid)
    new_parent_node = nodes.TREK_NODES_BY_ID.get(new_parent_nid)

    if not subject_node:
        return jsonify(status="error",
                       message="Subject node not found"), 404

    if not new_parent_node:
        return jsonify(status="error",
                       message="New parent not found"), 404

    old_parent_node = subject_node.parent

    if not old_parent_node:
        return jsonify(status="error",
                       message="Cannot reassign root"), 400

    if old_parent_node.nid == new_parent_node.nid:
        return jsonify(status="error",
                       message="Already assigned to that parent"), 400

    # ---- Optional structural validation ----
    if new_parent_node.parent != old_parent_node.parent:
        return jsonify(status="error",
                       message="Invalid reassignment level"), 400

    try:
        # Perform reassignment
        print(f"_____subject node : {subject_node.value} from oldparent{old_parent_node.value} to newparent {new_parent_node.value}")
        subject_node.set_parent(new_parent_node)
        allelectors = electors.elector_for_path(rlevels,old_parent_node.mapfile())
        # Regenerate affected maps
        map,totalleaf = old_parent_node.create_node_map(CElection,layers.Geo_index,rlevels, static=False)
        map,totalleaf = new_parent_node.create_node_map(CElection,layers.Geo_index,rlevels, static=False)

        # Persist AFTER successful mutation
        persist(layers.Treepolys, layers.Geo_index)

    except Exception:
        current_app.logger.exception("Reassignment failed")
        return jsonify(status="error",
                       message="Reassignment failed"), 500

    return jsonify({
        "status": "success",
        "message": "Node reassigned",
        "mapfile": url_for("thru", path=old_parent_node.mapfile())
    })






# Optional: handle user ping
@app.route("/api/user-ping", methods=["POST"])
def user_ping():
    global active_users
    active_users = {}
    data = request.json
    user_id = data.get("user_id")
    name = data.get("display_name") or "Anonymous"
    print(f" under {state.route()} user_id: {user_id} ")
    if user_id:
        active_users[user_id] = {
            "name": name,
            "last_seen": datetime.utcnow()
        }
        return jsonify(ok=True)
    return jsonify(ok=False), 400

# Optional: return list of active users
@app.route("/api/active-users", methods=["GET"])
def active_users_list():
    global active_users
    threshold = datetime.utcnow() - timedelta(seconds=60)
    users = [
        {"id": uid, "name": info["name"]}
        for uid, info in active_users.items()
        if info["last_seen"] > threshold
    ]
    print(f" under {state.route()} users: {users} ")
    return jsonify(users)



@app.route('/updateResourcing', methods=['POST'])
@login_required
def update_walk():

    from elector import electors
    global layeritems


    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    data = request.json
    walk_name = data.get('walkName')
    new_resource = data.get('newResource')

    idx = allelectors[allelectors['walkName'] == walk_name].index
    if not idx.empty:
        allelectors.at[idx[0], 'Resource'] = new_resource
        persist(layers.Treepolys, layers.Geo_index)
        return jsonify(success=True)
    else:
        return jsonify(success=False, error="Walk not found"), 404

@app.route('/kanban')
@login_required
def kanban():
    from elector import electors
    global layeritems


# campaign plan is only available to westminster elections at level 3 and others at level 4.
# every election should acquire an election node(ping to its mapfile) to which this route should take you
    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    rlevels = CElection.resolved_levels
    session['current_node_id'] = current_node.nid

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())
    print("____Route/kanban/AreaElectors shape:", current_election, current_node.value, areaelectors.shape, CElection['mapfiles'][-1] )
    print("Sample of areaelectors:", areaelectors.head())
    print("Sample raw Tags values:")
    print(areaelectors['Tags'].dropna().head(10).tolist())
    # Example DataFrame
    df = areaelectors
    gotv = float(CElection['GOTV'])
    turnout = 0.3  # assuming this is between 0–1

    df['VI_Party'] = df['VI'].apply(lambda vi: 1 if vi == CElection['yourparty'] else 0)
    df['VI_Canvassed'] = df['VI'].apply(lambda vi: 1 if isinstance(vi, str) else 0)
    df['VI_L1Done'] = df['Tags'].apply(lambda tags: 1 if isinstance(tags, str) and "Leaflet1" in tags.split() else 0)
    df['VI_Voted'] = df['Tags'].apply(lambda tags: 1 if isinstance(tags, str) and "Houseboard1" in tags.split() else 0)
    g = {'ENOP': 'count', 'Kanban': 'first', 'VI_Party': 'sum', 'VI_Voted': 'sum', 'VI_L1Done': 'sum','VI_Canvassed': 'sum'}
    grouped = df.groupby('WalkName').agg(g).reset_index()
    print("Unique WalkNames:", df['WalkName'].dropna().unique())
    # Compute dynamic GOTV target per group
    grouped['VI_Target'] = (((grouped['ENOP'] * turnout) / 2 + 1) / gotv).round().astype(int)
    grouped['VI_Pledged'] = (grouped['VI_Party'] - grouped['VI_Voted']).clip(lower=0)
    grouped['VI_ToGet_Pos'] = (grouped['VI_Target'] - grouped['VI_Party'] ).clip(lower=0)
    grouped['VI_ToGet_Neg'] = (grouped['VI_Target'] - grouped['VI_Party'] ).clip(upper=0).abs()
    print("Grouped Walks data:", len(grouped), grouped[['WalkName','Kanban','ENOP', 'VI_Voted','VI_Pledged','VI_ToGet_Pos','VI_ToGet_Neg','VI_L1Done','VI_Canvassed' ]].head());
    filepath = current_node.mapfile()
    title = current_node.value+" details"
    items = current_node.childrenoftype('walk')
    layeritems = get_layer_table(items,title, rlevels)
    print("___Layeritems: ",[x.value for x in items] )


    # ✅ Step 1: Define tags of interest
    input_tags = [t for t in CElection['Tags'] if t.startswith('L')]
    output_tags = [t for t in CElection['Tags'] if t.startswith('M')]
    all_tags = input_tags + output_tags

    print("Known tags:", all_tags[:10])  # Sanity check

    # ✅ Step 2: Explode Tags column into rows
    clean_tags_df = (
        areaelectors.assign(
            Tags_list=lambda df: df['Tags']
                .fillna('')  # ✅ Ensures str operations won't fail
                .astype(str)
                .str.replace(r'[;,]', ' ', regex=True)
                .str.split()
        )
        .explode('Tags_list')
    )

    # Filter known tags
    filtered = clean_tags_df[
        clean_tags_df['Tags_list'].isin(all_tags) &
        clean_tags_df['WalkName'].notna()
    ]

    # Group/tag counts
    walk_tag_counts = (
        filtered
        .groupby(['WalkName', 'Tags_list'])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient='index')
    )

    print("Filtered sample:")
    print(filtered[['WalkName', 'Tags_list']].head(10))  # Debug output

    # ✅ Step 4: Count tags per WalkName
    walk_tag_counts = (
        filtered.groupby(['WalkName', 'Tags_list'])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient='index')
    )


    # ✅ Step 5: Verify results
    print("walk_tag_counts sample:")
    for k, v in list(walk_tag_counts.items())[:5]:
        print(k, v)

    # Normalize and explode tags
    walk_tag_counts = (
        areaelectors.assign(
            Tags_list=lambda df: df['Tags']
                .fillna('')
                .str.replace(r'[;,]', ' ', regex=True)
                .str.split()
        )
        .explode('Tags_list')
        .query("Tags_list in @all_tags")
        .groupby(['WalkName', 'Tags_list'])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient='index')
    )

    return render_template('kanban.html',
        grouped_walks=grouped.to_dict('records'),
        kanban_options=state.kanban_options,
        walk_tag_counts=walk_tag_counts,
        tag_labels=CElection['Tags']
    )


@app.route('/update-walk-kanban', methods=['POST'])
@login_required
def update_walk_kanban():
    from elector import electors

    global CElection

    data = request.get_json()
    walk_name = data.get('walk_name')
    new_kanban = data.get('kanban')

    # Check if inputs are valid
    if not walk_name or not new_kanban:
        return jsonify(success=False, error="Missing data"), 400

    # Restore context
    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels
    Territory_node = current_node.ping_node(rlevels,layers.Geo_index,CElection['territory'], create=True, accumulate=False)

    areaelectors = electors.elector_for_path(rlevels,Territory_node.mapfile())


    if not mask.any():
        print(f"WalkName '{walk_name}' not found in area '{Territory_node.value}'")
        return jsonify(success=False, error="WalkName not found"), 404

    # Update Kanban status
    allelectors.loc[mask, 'Kanban'] = new_kanban
    print(f"Updated WalkName '{walk_name}' to KanBan '{new_kanban}' for {mask.sum()} rows.")

    persist(layers.Treepolys, layers.Geo_index)

    return jsonify(success=True)

@app.route('/telling')
@login_required
def telling():
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())
    valid_tags = CElection['Tags']
    leaflet_tags = {}
    marked_tags = {}
    activity_tags = {}

    for tag, description in activity_tags.items():
        activity_tags[tag] = description
        if tag.startswith('L'):
            leaflet_tags[tag] = description
        elif tag.startswith('M'):
            marked_tags[tag] = description
    print("____Tags v l m:",activity_tags,leaflet_tags, marked_tags)
    return render_template(
        'telling.html',
        activity_tags=activity_tags,
        leaflet_tags=leaflet_tags,
        marked_tags=marked_tags
        )

@app.route('/leafletting')
@login_required
def leafletting():
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())
    valid_tags = CElection['Tags']
    leaflet_tags = {}
    marked_tags = {}
    activity_tags = {}

    for tag, description in activity_tags.items():
        activity_tags[tag] = description
        if tag.startswith('L'):
            leaflet_tags[tag] = description
        elif tag.startswith('M'):
            marked_tags[tag] = description
    print("____Tags v l m:",activity_tags,leaflet_tags, marked_tags)
    return render_template(
        'leafletting.html',
        activity_tags=activity_tags,
        leaflet_tags=leaflet_tags,
        marked_tags=marked_tags
    )

@app.route('/check_enop/<enop>', methods=['GET'])
@login_required
def check_enop(enop):
    global CElection
    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    # Check if ENOP exists in the DataFrame
    if enop in allelectors['ENOP'].values:
        # Get the current Tags for the ENOP
        current_tags = allelectors.loc[allelectors['ENOP'] == enop, 'Tags'].iloc[0]

        # If "M1" is not in the current Tags, add it
        if "M1" not in current_tags.split():
            current_tags = f"{current_tags} M1".strip()
            allelectors.loc[allelectors['ENOP'] == enop, 'Tags'] = current_tags
            persist(layers.Treepolys, layers.Geo_index)
        return jsonify({'exists': True, 'message': f'ENOP found, M1 tag added. Current Tags: {current_tags}'})
    else:
        return jsonify({'exists': False, 'message': 'ENOP not found in electors.'})

def area_search(query, df, search_type):
    """
    Filters for unique street/area or walk/area combinations across updated
    geographical structures (PD, Ward, Division), optimized for consistent
    frontend dropdown results.
    """
    if df.empty or not query:
        return []

    # 🎯 1. Map the search type to the primary target column
    col = "StreetName" if search_type == "street" else "WalkName"

    if col not in df.columns:
        return []

    # 🎯 2. Filter rows by the query string (case-insensitive)
    mask = df[col].astype(str).str.contains(query, case=False, na=False)
    matches = df[mask]

    if matches.empty:
        return []

    # 🎯 3. Anchor geography to search context, falling back only if data is entirely missing
    # Default priority ordering based on data granularity
    geo_col = 'Area'

    # Context-driven defaults: Walks belong to PDs; Streets are usually understood by Wards
    preferred_order = ['PD', 'Ward', 'Division'] if search_type == 'walk' else ['Ward', 'PD', 'Division']

    for candidate in preferred_order:
        # Hard validation: Ensure column exists AND has at least one valid, non-outside value in our match slice
        if candidate in matches.columns:
            valid_slice = matches[candidate].dropna().astype(str).str.upper()
            valid_slice = valid_slice[~valid_slice.isin(['', 'NAN', 'NONE', 'OUTSIDE'])]

            if not valid_slice.empty:
                geo_col = candidate
                break

    # 🎯 4. Group by target column AND verified tier to secure unique item pairs
    unique_pairs = matches.groupby([col, geo_col], dropna=False).size().reset_index()

    results = []
    for _, row in unique_pairs.iterrows():
        name_val = str(row[col]).strip()
        area_val = str(row[geo_col]).strip() if pd.notna(row[geo_col]) else "UNKNOWN"

        # Explicitly skip corrupted tokens or unassigned artifacts
        if name_val.lower() in ['nan', 'none', ''] or name_val.upper() == 'OUTSIDE':
            continue

        if area_val.upper() in ['NAN', 'NONE', '']:
            area_val = "UNKNOWN"

        results.append({
            "name": name_val,
            "area": area_val,
            "display_name": f"{name_val} ({area_val})"  # e.g., "HIGH STREET (CENTRAL WARD)"
        })

    # Sort alphabetically by display string for smooth UI presentation
    return sorted(results, key=lambda x: x['display_name'])

@app.route('/update_location_tags', methods=['POST'])
@login_required
def update_location_tags():
    from elector import electors  # Import the manager instance

    data = request.get_json()
    l_type = data.get('location_type')
    l_name = data.get('location_name')
    l_area = data.get('location_area')  # e.g., "PD_A", "Central Ward"
    delivery_tag = data.get('tag')

    col = "StreetName" if l_type == "street" else "WalkName"

    current_election = CurrentElection.get_lastused()
    master_df = electors.get(current_election)

    # 🎯 STEP 1: Build the location name mask
    name_mask = master_df[col].astype(str).str.upper() == str(l_name).upper()

    # 🎯 STEP 2: Dynamically find the correct structural column (PD, Ward, or Division)
    # Because your system split 'Area' into three distinct structural tiers, we check which
    # column matches the incoming area string.
    l_area_upper = str(l_area).upper()

    if l_area_upper in master_df['PD'].astype(str).str.upper().unique():
        area_mask = master_df['PD'].astype(str).str.upper() == l_area_upper
    elif l_area_upper in master_df['Ward'].astype(str).str.upper().unique():
        area_mask = master_df['Ward'].astype(str).str.upper() == l_area_upper
    elif l_area_upper in master_df['Division'].astype(str).str.upper().unique():
        area_mask = master_df['Division'].astype(str).str.upper() == l_area_upper
    elif 'Area' in master_df.columns:
        # Fallback safeguard in case legacy columns are floating around in memory
        area_mask = master_df['Area'].astype(str).str.upper() == l_area_upper
    else:
        # Final fallback: If no structural tier matches, match everything to prevent silent drop
        area_mask = pd.Series(True, index=master_df.index)

    # Combine masks safely
    mask = name_mask & area_mask
    affected_indices = master_df[mask].index

    updated_count = 0

    # 🎯 STEP 3: In-place string token updates
    for idx in affected_indices:
        current_tags = str(master_df.at[idx, 'Tags']) if pd.notna(master_df.at[idx, 'Tags']) else ""
        tags_list = current_tags.split()

        if delivery_tag not in tags_list:
            tags_list.append(delivery_tag)
            # Apply update directly to the underlying election store reference
            electors._elections[current_election].at[idx, 'Tags'] = ' '.join(tags_list)
            updated_count += 1

    # 🎯 STEP 4: Persist and sync
    if updated_count > 0:
        electors.save()
        electors.rebuild_combined()  # Keep cross-election states in perfect alignment

    return jsonify({
        'message': f'Success: {updated_count} electors in {l_name} ({l_area}) tagged with {delivery_tag}.'
    })

@app.route('/locationsearch')
@login_required
def location_search():
    from elector import electors
    from elections import CurrentElection

    # 1. Get Context
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    # 2. Get Data for this node
    area_electors = electors.elector_for_path(rlevels,current_node.mapfile())

    # 3. Get Params
    query = request.args.get("query", "").strip()
    search_type = request.args.get("type", "street").lower()

    # 4. Use the General Searcher
    try:
        results = area_search(query, area_electors, search_type)
        return jsonify(results)
    except Exception as e:
        print(f"❌ Error in general_search: {e}")
        return jsonify({'error': str(e)}), 500

def textnorm(s):
    return ''.join(c.lower() for c in s if c.isalnum() or c.isspace())


def search_electors(df, query):
    """Search elector dataframe for matches in Surname, Firstname, or StreetName."""
    norm_query = textnorm(query)

    def row_matches(row):
        return (
            norm_query in textnorm(row['Surname']) or
            norm_query in textnorm(row['Firstname']) or
            norm_query in textnorm(row['StreetName'])
        )

    mask = df.apply(row_matches, axis=1)
    return df[mask]


@app.route('/api/search', methods=['GET'])
@login_required
def search_api():
    from elector import electors
    from elections import CurrentElection

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    allelectors = electors.elector_for_path(rlevels,current_node.mapfile())

    # SAFETY: Check if we have any data before proceeding
    if allelectors is None or allelectors.empty:
        return jsonify({'columns': [], 'data': []})

    # Optional: ensure we have persistence if data exists
    restore_from_persist(layers.Treepolys, layers.Geo_index)

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'columns': [], 'data': []})

    norm_query = textnorm(query)
    norm_parts = norm_query.split()

    def row_matches(row):
        try:
            # Added AddressPrefix and AddressNumber to the searchable haystack
            haystack = ' '.join([
                str(getattr(row, 'AddressPrefix', '')),
                str(getattr(row, 'AddressNumber', '')),
                str(getattr(row, 'StreetName', '')),
                str(getattr(row, 'Surname', '')),
                str(getattr(row, 'Firstname', ''))
            ])
            normalized_haystack = textnorm(haystack)
            return all(part in normalized_haystack for part in norm_parts)
        except Exception as e:
            return False

    try:
        print(f"___Route/search for of allelectors: {len(allelectors)}")

        # Perform the search
        matches = allelectors[allelectors.apply(row_matches, axis=1)]

        # 1. Define all potential columns you want to show
        display_cols = [
            'AddressPrefix', 'AddressNumber', 'StreetName',
            'Surname', 'Firstname', 'Postcode', 'Tags', 'ENOP'
        ]

        # 2. Filter for only those that actually exist in the dataframe
        existing_cols = [c for c in display_cols if c in matches.columns]
        trimmed = matches[existing_cols].copy()

        # 3. Clean up the AddressNumber (remove .0 if it's a float)
        if 'AddressNumber' in trimmed.columns:
            trimmed['AddressNumber'] = trimmed['AddressNumber'].astype(str).replace(r'\.0$', '', regex=True)

        # 4. Fill NaNs with empty strings
        trimmed = trimmed.fillna('')

        # Ensure all values are JSON-safe
        def convert(v):
            try:
                if isinstance(v, (float, int, str)):
                    return v
                elif hasattr(v, 'item'):  # numpy scalar
                    return v.item()
                else:
                    return str(v)
            except Exception:
                return str(v)

        cleaned_data = [
            {col: convert(row[col]) for col in trimmed.columns}
            for _, row in trimmed.iterrows()
        ]

        return jsonify({
            'columns': list(trimmed.columns),
            'data': cleaned_data
        })

    except Exception as e:
        print("❗ Exception in /api/search:", e)
        import traceback
        traceback.print_exc() # Useful for debugging exactly which line failed
        return jsonify({'columns': [], 'data': [], 'error': str(e)}), 500


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():

    from elector import electors
    results = []
    query = request.form.get('query', '')

    if request.method == 'POST' and query:
        norm_query = textnorm(query)
        norm_parts = norm_query.split()
        mask = allelectors.apply(lambda row: all(
            any(p in textnorm(str(row[field])) for field in ['Surname', 'Firstname', 'StreetName'])
            for p in norm_parts
        ), axis=1)
        results = allelectors[mask].to_dict(orient='records')

    return render_template('search.html', query=query, results=results)


@app.route('/location')
@login_required
def location():
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    lat = 54.9783
    long = 1.6178

    current_node.latlongroid = (lat,long)
    print(f"Received location: Latitude={lat}, Longitude={lon}")
    return f"Received location: Latitude={lat}, Longitude={lon}"

@app.errorhandler(HTTPException)
@login_required
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    response = {
        "code": e.code,
        "name": e.name,
        "description": e.description,
        "url": request.url  # ← This gives the full URL that caused the error
    }
    return jsonify(response), e.code


@app.route('/get-backend-url', methods=['GET'])
@login_required
def get_backend_url():

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    program = ProgramContext()
    election = ElectionContext(CElection)
    options = resolve_ui_context(program, election, current_node)
    constants = CElection

    print(f"__url: {request.host_url}")
    print(f"__election: {current_election} __current_node: {current_node.value}")
    print(f"__program opts: {program}")
    print(f"__election opts: {election}")

    return jsonify({
    'backend_url': request.host_url,
    'constants': constants,
    'options': options,
    'current_election': current_election
    })

@app.route('/add_tag', methods=['POST'])
@login_required
def add_tag():
    global CElection
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    try:
        data = request.get_json()
        tag = data.get("tag", "").strip()
        label = data.get("label", "").strip()

        if not tag or not label:
            return jsonify({"success": False, "error": "Missing tag or label"}), 400

        tag_exists = tag in CElection['Tags']

        if not tag_exists:
            CElection['Tags'][tag] = label
            CElection.save()

        return jsonify({
            "success": True,
            "exists": tag_exists,
            "tag": tag,
            "label": label
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/reset_Elections', methods=['POST'])
@login_required
def reset_Elections():
    global streamrag
    from elector import electors

    global layeritems
    global DQstats
    global progress


    fixed_path = ELECTOR_FILE  # Set your path
    print("____Route/Reset-Election")

    if not fixed_path or not os.path.exists(fixed_path):
        return jsonify({'message': 'Elections reset unnessary - no election data '}), 404

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    arch_path = fixed_path.replace(".csv", "-ARCHIVE.csv")
    allelectors.to_csv(arch_path,sep='\t', encoding='utf-8', index=False)
    formdata = {}

    print("trying to reset elections at node:", current_node.value)
    if not GENESYS_FILE or not os.path.exists(GENESYS_FILE):
        return jsonify({'message': 'Elections reset unnessary - no election data '}), 404
    allelectors = pd.read_excel(GENESYS_FILE)
    allelectors.drop(allelectors.index, inplace=True)

    persist(layers.Treepolys, layers.Geo_index)
    allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

    DQstats = pd.DataFrame()
    progress["percent"] = 0
    progress["status"] =  "idle"
    progress["message"] = "No data yet selected for processing"
    progress['dqstats_html'] = render_template('partials/dqstats_rows.html', DQstats=DQstats)
    print(" new DQstats displayed:",progress['dqstats_html'])
    text = "NO DATA - please select an electoral roll data stream to load"
    layeritems = get_layer_table(pd.DataFrame(),text )

    return jsonify({'message': 'Election data archived and reset successfully.'}), 200


@app.route("/election-report")
@login_required
def election_report():
    from flask import session
    global report_data
    program = ProgramContext()
    election = ElectionContext(CElection)
    OPTIONS = resolve_ui_context(program,election, current_node)

    resources = OPTIONS['resources']
    # Define the absolute path to the 'static/data' directory
    elections_dir = os.path.join(config.workdirectories['workdir'], 'static', 'data')
    report_data = []

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    reportfile = "UNITED_KINGDOM/ENGLAND/SURREY/SURREY-MAP.html"
    rlevels = CElection.resolved_levels


    # Check if the elections directory exists
    if not os.path.exists(elections_dir):
        return f"Error: The directory {elections_dir} does not exist!"

    # Example mapping for party abbreviations to full names (update as needed)

    # Process each election file in the directory
    nodemolist = os.listdir(elections_dir)
    for filename in nodemolist:
        if filename.startswith("Elections-") and filename.endswith(".json") and filename.find("DEMO") < 0 and filename.find("GA1") < 0 :
            election_name = filename[len("Elections-"):-len(".json")]
            file_path = os.path.join(elections_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Concatenate Firstname and Surname for Candidate and Campaign Manager
                candidate_key = f"{data.get('candidate', '')}"
                candidate = resources.get(candidate_key, {})
                candidate_name = f"{candidate.get('Surname', 'Unknown')} {candidate.get('Firstname', 'Unknown')}"

                campaign_mgr_key = f"{data.get('campaignMgr', '')}"
                campaign_mgr = resources.get(campaign_mgr_key, {})
                campaign_mgr_name = f"{campaign_mgr.get('Surname', 'Unknown')} {campaign_mgr.get('Firstname', 'Unknown')}"
                campaignMgremail = campaign_mgr.get('campaignMgremail')
                mobile = campaign_mgr.get('Mobile')

                mapfiles = data.get("mapfiles", [])
                territory_path = mapfiles[-1] if mapfiles else ""

                if territory_path:
                    # Extract only the filename (no directories)
                    territory_filename = os.path.basename(territory_path)

                    # Remove suffixes from the filename
                    for suffix in ['-MAP.html', '-CAL.html','-PDS.html', '-WALKS.html','-WARDS.html','-DIVS.html', '-DEMO.html']:
                        if territory_filename.endswith(suffix):
                            territory_filename = territory_filename[:-len(suffix)]


                # In your route handler
                election_node = current_node.ping_node(rlevels,layers.Geo_index,territory_path, create=True,accumulate=session.get("accumulate", False))
                print(f"____election territory path:{territory_path} elect:{election_node.value}")
                # Get full party name from the abbreviation
                selected_party_key = election_node.party
                incumbent_party = OPTIONS['yourparty'].get(selected_party_key, 'Independent')
                # Extract the filename from the 'territory' path and remove the suffix

                def ordinal(n):
                    if 10 <= n % 100 <= 20:
                        suffix = 'th'
                    else:
                        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
                    return f"{n}{suffix}"

                # Convert election date
                raw_date = data.get("electiondate", "")
                try:
                    dt = datetime.strptime(raw_date, "%Y-%m-%d")
                    election_date = f"{ordinal(dt.day)} {dt.strftime('%b')}"  # e.g. "16th Oct"
                except ValueError:
                    election_date = "Invalid Date"

                report_data.append({
                    "name": election_name,
                    "territory": territory_filename,  # Updated territory field with filename only
                    "electiondate": election_date,
                    "candidate": candidate_name,  # Concatenated name for candidate
                    "campaign_mgr": campaign_mgr_name,  # Concatenated name for campaign manager
                    "campaignMgremail": campaignMgremail,
                    "mobile" : mobile,
                    "incumbent_party": incumbent_party
                })
            except Exception as e:
                print(f"⚠️ Error reading {filename}: {e}")


    print(f"XXXXMarkers at election {current_election} at node {current_node.value}")
    map,totalleaf = current_node.create_node_map(CElection,layers.Geo_index,rlevels, static=False)
    reportdate = datetime.strptime(str(date.today()), "%Y-%m-%d").strftime('%d/%m/%Y')

    return render_template("election_report.html", reportdate=reportdate, mapfile=reportfile, report_data=report_data)


@app.route("/set-election", methods=['GET', 'POST'])
@login_required
def set_election():

    from layers import ExtendedFeatureGroup
    from layers import ensure_treepolys_with_index
    from flask import session
    from elections import CurrentElection


    try:
        print("____Route/set-election/top ")
        session.pop("accumulated_nodes", None)
        session["accumulate"] = False
#        clear_treepolys()  # 🔥 FULL RESET
        restore_from_persist(layers.Treepolys, layers.Geo_index)
        data = request.get_json(force=True)  # <-- ensure JSON parsing
        print(f"____Route/set-election/data {data} ")

        if not data or "election" not in data:
            return jsonify(success=False, error="No election provided"), 400

        current_election = data["election"]
        session['current_election'] = current_election
        CElection = CurrentElection.load(current_election)
        if not CElection:
            return jsonify(success=False, error="Election not found"), 404

        rlevels = CElection.resolved_levels
        plevels = CElection.parent_levels

        lastfilepath = CElection['mapfiles'][-1]
        print(f"____Route/set-election- breadcrumb: {lastfilepath}")

        steps = stepify(lastfilepath)
        target_path = "/".join(steps)

        logger.info("[SET ELECTION STEP 1] Stepified path: %s -> Target path: '%s'", steps, target_path)

        # 2. Direct O(1) node lookup using the clean node path
        current_node = nodes.TREK_NODES_BY_PATH.get(target_path)
        # make sure we have the map boundaries for the new election:
        lastfilepath, layers.Geo_index = ensure_treepolys_with_index(
            sourcepath=lastfilepath,
            here=None,
            resolved_levels=rlevels,
            parent_levels= plevels
        )
        # At the start of a different election:
        print(f"____Route/set-election- path: {lastfilepath},Loaded election: {current_election} CE data: {CElection}")

        # make sure we have the nodes for the last path traversed in the new election:

        current_node = MapRoot.ping_node(rlevels,layers.Geo_index,lastfilepath, create=True, accumulate=session.get("accumulate", False)) # go to the first node

        print(f"____Route/set-election- last node: {current_node.value},Loaded election: {current_election}")
        CElection['previousParty'] = current_node.party

        if not current_node:
            return jsonify(success=False, error="No current node for election"), 500

        # make sure we have the mapfile for the last path traversed in the new election:

        created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels, lastfilepath, static=False)

        options = resolve_ui_context(ProgramContext(),ElectionContext(CElection), current_node)
        constants = CElection
        print(f"____Route/set-election- post resolve {current_node.value} Loaded election: {current_election} ")

        if not current_node.visit_node(CElection):
            flash("That node is outside of the election Territory")
            print("That node is outside of the election Territory:")
        persist(layers.Treepolys, layers.Geo_index)
# Convert your custom object into a clean dictionary for JSON parsing
        # Use whatever serialization method your class provides:
        if hasattr(CElection, 'to_dict'):
            constants_dict = CElection.to_dict()
        elif hasattr(CElection, 'data'):
            constants_dict = CElection.data
        else:
            # Fallback wrapper if it acts strictly like a dictionary sub-class
            constants_dict = dict(CElection)

        return jsonify({
            'success': True,
            'constants': constants_dict, # Now cleanly serializable!
            'options': options,
            'current_election': current_election
        })


    except Exception as e:
        print("____Route/set-election/exception", e)
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

# GET /current-election?election=...
@app.route('/current-election', methods=['GET'])
@login_required
def get_current_election_data():
    # received a call to return election data constants and options

    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = request.args.get("election")

    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    program = ProgramContext()
    election = ElectionContext(CElection)
    OPTIONS = resolve_ui_context(program,election, current_node)

    resources = OPTIONS['resources']
    rlevels = CElection.resolved_levels

    plan = CElection.get("calendar_plan", {})

    # Ensure it always has slots
    if not isinstance(plan, dict):
        plan = {"slots": {}}
    elif "slots" not in plan:
        plan["slots"] = {}

    return jsonify({"calendar_plan": plan,
            'constants': CElection,
            'options': OPTIONS,
            'current_election': current_election
        })

# POST /current-election
@app.route('/current-election', methods=['POST'])
@login_required
def update_current_election():
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)

    try:
        data = request.get_json()
        print("📥 Incoming data:", data)

        # Extract calendar_plan, fallback to data itself
        plan = data.get("calendar_plan", data)

        # --- Validate structure ---
        if not isinstance(plan, dict) or "slots" not in plan:
            return jsonify({
                "success": False,
                "error": "Invalid calendar_plan structure: must be a dict with 'slots'"
            }), 400

        # Save normalized plan
        CElection['calendar_plan'] = plan
        CElection.save()

        print("💾 Saved calendar_plan:", plan)
        return jsonify({"success": True})

    except Exception as e:
        print("🚨 Error in /current-election:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/get-constants', methods=["GET"])
@login_required
def get_constants():
    print("____Route/get_constants" )
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    print(f"__get constants for election: {current_election}")
    if not current_election:
        return jsonify({'error': 'Invalid election'}), 400

    options = resolve_ui_context(ProgramContext(), ElectionContext(CElection), current_node)
    constants = CElection

    return jsonify({
        'constants': constants,
        'options': options,
        'current_election': current_election
    })


@app.route("/set-constant", methods=["POST"])
@login_required
def set_constant():

    from layers import ExtendedFeatureGroup
    from elections import CurrentElection

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    data = request.get_json()
    name = data.get("name")
    value = data.get("value")
    current_election = data.get("election")

    print("____Back End election constants update:",
          current_election, ":", name, "-", value)

    CElection = CurrentElection.load(current_election)

    if not CElection:
        return jsonify(success=False, error="Election not found"), 400

    # Special handling
    if name == "resources":
        if not isinstance(value, list):
            value = [value] if value else []
    elif name == "mapfiles":
        CElection.add_breadcrumb(value)
    elif name == "adminmode":
        value = bool(value)
        CElection[name] = value
    elif name == "accumulate":
        value = bool(value)
        session["accumulate"] = value
        CElection[name] = value
    else:
        # Store in backing dict only
        CElection[name] = value
    CElection.save()

    print(f"____Current Election choices saved: "
          f"{current_election} - {name} = {value}")

    return jsonify({
        "success": True,
        "constants": CElection
    })



@app.route("/delete-election", methods=["POST"])
@login_required
def delete_election():
# delete selected election if not DEMO, then select DEMO as next election
    global formdata

    restore_from_persist(layers.Treepolys, layers.Geo_index)
    ELECTIONS = get_available_elections()
    data = request.get_json()
    election_to_delete = data.get("election")


    print(f"Received delete-election request:{election_to_delete} from:{ELECTIONS}" )

    if election_to_delete == "DEMO" or not election_to_delete or election_to_delete not in ELECTIONS:
        return jsonify(success=False, error="Election not found"+election_to_delete)

    # Remove from dict
    try:
        filename = os.path.join(config.workdirectories['workdir'],'static','data',"Elections-"+election_to_delete+".json")
        os.remove(filename)
        deletedata = ELECTIONS.pop(election_to_delete)
        current_election = "DEMO"
        session['current_election'] = current_election

        persist(layers.Treepolys, layers.Geo_index)
    except OSError:
        jsonify(success=False, message="osdeletion error for file:"+filename)


    # Update current election if needed

    if current_election == election_to_delete:
        current_election = "DEMO"

    # Re-render tabs
    electiontabs_html = render_template("partials/electiontabs.html",
                                        ELECTIONS=ELECTIONS,
                                        current_election=current_election)
    print("____electiontabs",electiontabs_html)


    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)


    return jsonify(success=True, electiontabs_html=electiontabs_html)


@app.route("/add-election", methods=["POST"])
@login_required
def add_election():

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    # no have Current Election data loaded
    # Load existing elections

    ELECTIONS = get_available_elections()

    # Get name for new election
    data = request.get_json()
    new_election = data.get("election")

    session['current_election'] = new_election

    if not new_election or new_election in ELECTIONS:
        return jsonify(success=False, error="Invalid or duplicate election name.")


    current_election = "DEMO"
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    mapfile = CElection['mapfiles'][-1]

    CElection['previousParty'] = current_node.party

    print(f"___new_election + CElection: {new_election} + {CElection}")

    # Create a new election file with new_election name
    CElection.save(new_election)

    ELECTIONS = get_available_elections()
    print("____ELECTIONS:", ELECTIONS)
    formdata = render_template('partials/electiontabs.html', ELECTIONS=ELECTIONS, current_election=current_election)
    program = ProgramContext()
    election = ElectionContext(CElection)
    OPTIONS = resolve_ui_context(program,election, current_node)

    resources = OPTIONS['resources']

    print("election-tabs:",formdata)

    return jsonify({'success': True,
        'constants': CElection,
        'options': OPTIONS,
        'election_name': new_election,
        'electiontabs_html':formdata
    })

@app.route("/load_election/<ename>")
@login_required
def load_election(ename):
    # fetch your single election data from disk or DB
    # for example, read a JSON file for the election
    path = BASEX_FILE.parent / f"Elections-{ename}.json"
    if not path.exists():
        return jsonify({"error": "Election not found"}), 404

    data = json.loads(path.read_text())

    # Ensure structure matches front-end expectation
    return jsonify({
        "stream_processing": {
            "files": data.get("files", []),
            "last_run": data.get("last_run"),
            "status": data.get("status", "idle")
        }
    })


@app.route("/last-election")
@login_required
def last_election():
    result = get_available_elections()[0]
    return jsonify(result)

@app.route("/get_elections")
@login_required
def get_elections_route():
    results = get_elections()
    return jsonify(results)

@app.route("/update-territory", methods=["POST"])
@login_required
def update_territory():
    from elections import CurrentElection

    data = request.get_json()
    mapfile = data.get("mapfile")
    print(f"______/update-territory mapfile:{mapfile}")

    if not mapfile:
        return jsonify({"error": "No mapfile provided"}), 400

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=True)
    rlevels = CElection.resolved_levels
    # mapfiles last entry is what we need to bookmark.


    CElection['territory'] = mapfile

    created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels, mapfile,static=False)

    CElection.save()
    print(f"______election:{current_election} Bookmarks : {CElection['mapfiles']} Updated-territory: {current_node.mapfile()}")

    return jsonify(success=True, constants=CElection)

@app.route("/get_streamrag")
@login_required
def get_streamrag():
    """
    Endpoint to return the current stream processing RAG data.
    """

    # Call the class method, passing the elections dictionary and the ElectorManager instance
    rag_data = CurrentElection.getstreamrag(electors)

    return jsonify(rag_data)



@app.route("/save_stream_processing/<ename>", methods=["POST"])
@login_required
def save_stream_processing(ename):
    """
    Save the stream_processing structure sent from the front end.
    """
    from elections import CurrentElection  # adjust import as needed

    updated_stream_processing = request.get_json()
    if not updated_stream_processing:
        return jsonify({"error": "No data provided"}), 400

    CElection = CurrentElection.load(ename)
    if not CElection:
        return jsonify({"error": "Election not found"}), 404

    CElection['stream_processing'] = updated_stream_processing
    CElection.save()

    return jsonify(success=True)




@app.route('/validate_tags', methods=['POST'])
@login_required
def validate_tags():

    global CElection
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    # Ensure the valid tags list is a list of strings
    tags_data = CElection['Tags']
    print("____Standard Tag options for election",tags_data)

    valid_tags = set(tags_data)  # E.g. {'M1', 'M2', 'Leafletting1', 'L3'}
    print("____Standard Tag options as set",valid_tags)

    # Parse input from frontend
    data = request.get_json()
    current_tags = data.get('tags', '')  # e.g. "M1 Leafletting1 X99"
    original = data.get('original', '')
    print("_____elector data and original",current_tags,original)

    # Normalize and split input tags
    tag_list = current_tags.strip().split()  # ['M1', 'Leafletting1', 'X99']
    print("____New Tag settings for elector",tag_list, valid_tags)

    # Check for any invalid tags
    invalid_tags = [tag for tag in tag_list if tag not in valid_tags]

    if invalid_tags:
        return jsonify(valid=False, invalid_tags=invalid_tags, original=original)
    else:
        return jsonify(valid=True)


@app.route("/", methods=['POST', 'GET'])
def index():
    global streamrag
    global TABLE_TYPES
    global constants
    from baked_data import baked_manager

    ELECTIONS = get_available_elections()  # This seems to be a function fetching available elections

    if 'username' in session:
        flash("__________Session Alive:" + session['username'])
        print("__________Session Alive:" + session['username'])
        formdata = {}

        # Fetch the stream processing status using the new method
        streamrag = CurrentElection.getstreamrag(electors)  # This is your new way of getting stream processing data

        # You may have to handle cases where streamrag is empty or has no valid data
        if not streamrag:
            streamrag = {
                'No Elections': {
                    'Alive': False,
                    'Elect': 0,
                    'Files': 0,
                    'RAG': 'white'
                }
            }

        # Restore the persisted state (Treepolys)
        restore_from_persist(layers.Treepolys, layers.Geo_index)
        BAKED_DATA = baked_manager.load()
        # Load the current election context
        current_election = CurrentElection.get_lastused()
        CElection = CurrentElection.load(current_election)
        resolved_levels = CElection.resolved_levels

        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # The clean unpack you like
        (c_election, elevels), = resolved_levels.items()

        current_node = get_last_node(CElection,layers.Geo_index,create=False)

        # Set up the program and election context
        program = ProgramContext()
        election = ElectionContext(CElection)
        OPTIONS = resolve_ui_context(program, election, current_node)

        # Log the current state for debugging
        print(f"🧪 Index level {current_election} - current_node mapfile:{current_node.mapfile()}")

        return render_template(
            "Dash0.html",
            table_types=TABLE_TYPES,
            ELECTIONS=ELECTIONS,
            current_election=current_election,
            options=OPTIONS,
            constants=CElection,
            baked_data=BAKED_DATA,
            mapfile=current_node.mapfile(),
            streamrag=streamrag  # Pass streamrag to the template for rendering
        )

    # If no session or no username, render the default index page
    return render_template("index.html")

#login
@app.route('/login', methods=['POST', 'GET'])
def login():


    if session.get('username'):
        msg = f"User already logged in: {session['username']} at {current_node.value}"
        flash(msg)
        print("_______ROUTE/Already logged in:", session['username'])
        return redirect(url_for('firstpage'))    # Collect info from forms in the login db
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    print("_______ROUTE/login page", username, user)


    print("Flask Current time:", datetime.utcnow())

    # Check if it exists
    if not user:
        flash("_______ROUTE/login User not found", username)
        print("_______ROUTE/login User not found", username)
        return render_template("index.html")
    elif user and user.check_password(password):
        # Successful login
        session["username"] = username
        session["user_id"] = user.id
        print("🔑 app.secret_key:", app.secret_key)
        print("👤 user.get_id():", user.get_id())
        login_user(user)
        print("get-id-after",user.get_id())
        session.modified = True
        # Debugging: Check the session and cookies
        print("Session after login:", dict(session))  # Print session content

        # Debugging session user ID
        print(f"🧍 current_user.id: {current_user.id if current_user.is_authenticated else 'Anonymous'}")
        print(f"🧪 Logging in user with ID: {current_user.id}")
        print("🧪 session keys after login:", dict(session))
        next = request.args.get('next')
        return redirect(url_for('get_location'))
#        return redirect(url_for('firstpage'))

    else:
        flash('Not logged in!')
        return render_template("index.html")

@app.route('/get_location')
@login_required
def get_location():
    """
    Only call this route if there is no sourcepath for the election.
    It prompts the user for geolocation and redirects to /firstpage
    with lat/lon as query parameters.
    """
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Locating You...</title>
        <style>
            body { margin:0; padding:0; height:100%; background:#00bed6; color:white; font-family:sans-serif; text-align:center; }
            .road { position:relative; width:100%; height:100vh; overflow:hidden; }
            .footprint { position:absolute; width:40px; opacity:0; animation:stepFade 4s ease-in-out infinite; }
            .left { left:45%; transform:rotate(-12deg); }
            .right { left:52%; transform:rotate(12deg); }
            @keyframes stepFade { 0%,10%{opacity:1;} 70%,100%{opacity:0;} }
        </style>
    </head>
    <body>
        <h2>elecTrek is finding democracy in your area ...</h2>
        <div class="road">
        {% for i in range(8) %}
            {% set is_left = i % 2 == 0 %}
            <img src="{{ url_for('static', filename='left_foot.svg') if is_left else url_for('static', filename='right_foot.svg') }}"
                 class="footprint {{ 'left' if is_left else 'right' }}"
                 style="top: {{ 10 + i*10 }}%; animation-delay: {{ i*0.7 }}s;">
        {% endfor %}
        </div>
        <script>
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(pos) {
                        const lat = pos.coords.latitude;
                        const lon = pos.coords.longitude;
                        // Redirect to your page, passing lat/lon
                        window.location.href = `/firstpage?lat=${lat}&lon=${lon}&loadTable=nodelist_xref`;
                    },
                    function(err) {
                        alert("Location access denied. Using default map.");
                        window.location.href = `/firstpage?lat=${lat}&lon=${lon}&loadTable=nodelist_xref`;
                    }
                );
            } else {
                alert("Geolocation not supported. Using default map.");
                window.location.href = `/firstpage?lat=${lat}&lon=${lon}&loadTable=nodelist_xref`;
            }
        </script>
    </body>
    </html>
    """)



@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():

    current_node = nodes.TREK_NODES_BY_ID.get(session.get('current_node_id',None))

    flash("🔓 Logging out user:"+ current_user.get_id())
    print("🔓 Logging out user:", current_user.get_id())

    # Always log out the user
    logout_user()

    # Clear the entire session to remove 'username', 'user_id', etc.
    session.clear()

    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET','POST'])
@login_required
def dashboard():

    from elector import electors
    global streamrag
    global formdata
    global CElection
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels
    print ("___Route/Dashboard : ")
    if 'username' in session:
        print(f"_______ROUTE/dashboard: {session['username']} is already logged in at {session.get('current_node_id','UNITED_KINGDOM')}")

        path = CElection['mapfiles'][-1]
        previous_node = current_node
        print ("____Dashboard CElection: ",path, previous_node.value)
        # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers


        print ("___Dashboard persisted filename: ",current_node.mapfile())
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()
        created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels,current_node.mapfile(),static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" Route/dashboard File not found: {fullpath}")
            print (f"_________ROUTE/dashboard at {current_node.value} display file created:{fullpath}")

        if not current_node.visit_node(CElection):
            flash("That node is outside of the election Territory")
            print("That node is outside of the election Territory:")
        persist(layers.Treepolys, layers.Geo_index)

        print (f"_________ROUTE/dashboard at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)


    flash('_______ROUTE/dashboard no login session ')

    return redirect(url_for('index'))


@app.route('/downbut/<path:path>', methods=['GET','POST'])
@login_required
def downbut(path):
    from layers import ensure_treepolys_with_index
    from flask import session
    from elector import electors
    from layers import ExtendedFeatureGroup
    from elections import CurrentElection
    import nodes

    global layeritems
    global constants

    logger.info("=== [DOWNBUT START] Incoming path: '%s' ===", path)
    print("____Route/downbut:", path)

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    session["current_election"] = current_election
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels

    # 1. Use stepify to clean suffixes and ignorable containers (like 'WARDS') automatically
    steps = stepify(path)
    target_path = "/".join(steps)

    logger.info("[DOWNBUT STEP 1] Stepified path: %s -> Target path: '%s'", steps, target_path)

    # 2. Direct O(1) node lookup using the clean node path
    current_node = nodes.TREK_NODES_BY_PATH.get(target_path)

    # Guard against missing node
    if current_node is None:
        flash(f"Target node not found for path: {path}")
        logger.error("❌ [DOWNBUT ERROR] Failed to resolve target node for path: %s", path)
        abort(404, f"Target node not found for path: {path}")

    session["current_node_id"] = current_node.nid
    target_nid = getattr(current_node, "nid", None)
    logger.info("[DOWNBUT STEP 3] SUCCESS! Resolved Node NID: '%s' (value: '%s')", target_nid, getattr(current_node, "value", None))

    previous_node = current_node
    areaelectors = electors.elector_for_path(rlevels, current_node.mapfile())

    plevels = CElection.parent_levels
    breadcrumb = path

    # 3. Index & Boundary sync
    filepath, layers.Geo_index = ensure_treepolys_with_index(
        sourcepath=breadcrumb,
        here=None,
        resolved_levels=rlevels,
        parent_levels=plevels,
        areaelectors=areaelectors
    )

    # Use ping to populate the next level of nodes for boundary/marker repainting
    current_node = previous_node.ping_node(rlevels, layers.Geo_index, path, create=True, accumulate=session.get("accumulate", False))

    if current_node.level > 4 and len(areaelectors) == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}")
        raise Exception("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])
        fullpath = base / current_node.mapfile()
        created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels, current_node.mapfile(), static=False)
        if created:
            if not fullpath.exists():
                abort(404, f"Route/downbut File not found: {fullpath}")
            print(f"_________ROUTE/downbut at {current_node.value} display file created:{fullpath}")

        if not current_node.visit_node(CElection):
            flash("That node is outside of the election Territory")
            print("That node is outside of the election Territory:")

        persist(layers.Treepolys, layers.Geo_index)

        print(f"_________ROUTE/downbut at sending file:{fullpath}")
        logger.info("_________ROUTE/downbut sending file: %s", fullpath)
        return send_file(fullpath, as_attachment=False)

@app.route('/downbulk', methods=['POST'])
@login_required
def downbulk():
    from flask import request, session, jsonify
    from pathlib import Path
    import config

    print("\n" + "="*40)
    print("🚀 ENTERING ROUTE: /downbulk")
    print("="*40)

    # 1. Unpack payload parameters
    data = request.json or {}
    nids = data.get('nids', [])
    selected_election = data.get('election') # 🎯 Plucked from your new JS payload

    print(f"🗳️ Client-selected election tab: {selected_election}")
    print(f"📦 Payload received: {len(nids)} NIDs")
    print(f"🔍 Raw NID list: {nids}")

    if not nids:
        print("❌ ERROR: No NIDs provided in request.")
        return jsonify({"success": False, "error": "No nodes selected"}), 400

    print("🔄 Restoring state from persist...")
    restore_from_persist(layers.Treepolys, layers.Geo_index)

    # 2. Convert NIDs to actual Node objects
    nodelist = []
    missing_nids = []
    for nid in nids:
        node = nodes.TREK_NODES_BY_ID.get(nid)
        if node:
            nodelist.append(node)
        else:
            missing_nids.append(nid)

    print(f"✅ Successfully resolved {len(nodelist)} Node objects.")
    if missing_nids:
        print(f"⚠️ WARNING: Could not find objects for NIDs: {missing_nids}")

    if not nodelist:
        return jsonify({"success": False, "error": "None of the selected NIDs could be resolved."}), 400

    # 3. Setup Election context (Triage selected tab vs system fallback)
    if selected_election:
        current_election = selected_election
    else:
        current_election = CurrentElection.get_lastused()
        print(f"ℹ️ No explicit tab sent. Falling back to last used: {current_election}")

    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels
    print(f"🗳️ Active Election Context: {current_election} | Resolved Levels: {rlevels}")

    # Set up the context node (The "Parent" container for the render)
    current_node = get_last_node(CElection,layers.Geo_index,create=True)
    print(f"📍 Context Node: {current_node.value} (NID: {current_node.nid})")

    # ==================================================================
    # 🧠 FIX: Explicitly flag the structural accumulation state
    # ==================================================================
    session['accumulate'] = True
    session['accumulated_nodes'] = nids
    session.modified = True
    print(f"💾 Session updated with bulk accumulation flags for {current_election}")
    # ==================================================================

    # 4. Ensure all nodes exist using clean Node paths
    for node in nodelist:
        get_trek_root().ping_node(
            rlevels,
            node.node_path,
            create=True,
            accumulate=session.get("accumulate", False)  # This will now safely read True!
        )

    # 5. Trigger the map creation
    target_parent = nodelist[0].parent
    map_filename = target_parent.mapfile()
    print(f"🛠️ Triggering endpoint_created for: {map_filename}")

    created, totalleaf = target_parent.endpoint_created(CElection,layers.Geo_index,rlevels, map_filename, static=True)
    print(f"📊 Render Result: File: {map_filename} Created={created}, Total Leaf Nodes={totalleaf}")

    # 6. File verification
    target_parent.parent.visit_node(CElection)
    base = Path(config.workdirectories['workdir'])
    fullpath = base / map_filename

    print(f"📂 Checking for file at: {fullpath}")
    if fullpath.exists():
        print(f"✨ File verified! Size: {fullpath.stat().st_size} bytes")
    else:
        print(f"🚨 ALERT: File does not exist after creation attempt!")

    persist(layers.Treepolys, layers.Geo_index)
    print("💾 State persisted. Sending response to frontend.")
    print("="*40 + "\n")

    return jsonify({
        "success": True,
        "count": totalleaf,
        "map_url": f"/transfer/{map_filename}"
    })

@app.route('/transfer/<path:path>', methods=['GET','POST'])
@login_required
def transfer(path):
    from flask import session
    from elector import electors
    from layers import ExtendedFeatureGroup

    from elections import CurrentElection
    global layeritems
    global constants

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels
    prev = nodes.TREK_NODES_BY_ID.get(CElection['cid'])

# transfering to another any other node with siblings listed below
# use ping to populate the destination node with which to repaint the screen node map and markers
    current_node = get_trek_root().ping_node(rlevels,layers.Geo_index,path, create=True, accumulate=session.get("accumulate", False))

    created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels, current_node.mapfile(),static=False)

    current_node.visit_node(CElection)
    base = Path(config.workdirectories['workdir'])  # or wherever files live
    fullpath = base / current_node.mapfile()
    persist(layers.Treepolys, layers.Geo_index)
    print (f"_________ROUTE/transfer at sendinf file:{fullpath}")
    return send_file(fullpath, as_attachment=False)




@app.route('/downMWbut/<path:path>', methods=['GET','POST'])
@login_required
def downMWbut(path):
    from layers import ensure_treepolys_with_index
    from flask import session
    from elector import electors
    from layers import ExtendedFeatureGroup
    from elections import CurrentElection
    global layeritems
    global constants


# so this is the button which creates the nodes and map of equal sized walks for the troops

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels
    assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

    # The clean unpack you like
    (c_election, elevels), = rlevels.items()

    print (f"_________ROUTE/downMWbut1 CE {current_election}", current_node.value, path)

    previous_node = current_node
    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())

    # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(rlevels,layers.Geo_index,path, create=True, accumulate=session.get("accumulate", False))

    print (f"_________ROUTE/downMWbut CE {current_election} from: {previous_node.value} to {current_node.value} mapfile: {current_node.mapfile()}")
    flash ("_________ROUTE/downMWbut ")

    plevels = CElection.parent_levels
    breadcrumb = current_node.mapfile()

    # 3. Index & Boundary sync
    filepath, layers.Geo_index = ensure_treepolys_with_index(
        sourcepath=breadcrumb,
        here=None,
        resolved_levels=rlevels,
        parent_levels=plevels,
        areaelectors=areaelectors
    )
    if current_node.level > 4 and len(areaelectors)  == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}" )
        raise Exception ("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()

        created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels,current_node.mapfile(), static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" Route/downMW File not found: {fullpath}")
            print (f"_________ROUTE/downMW at {current_node.value} display file created:{fullpath}")

        if not current_node.visit_node(CElection):
            flash("That MW node is outside of the election Territory")
            print("That MW node is outside of the election Territory:")
        persist(layers.Treepolys, layers.Geo_index)

        print (f"_________ROUTE/downMW at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)




@app.route('/STupdate/<path:path>', methods=['GET','POST'],strict_slashes=False)
@login_required
def STupdate(path):
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global CElection

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels
#    steps = path.split("/")
#    filename = steps.pop()
#    current_node = selected_childnode(current_node,steps[-1])
    fileending = "-SDATA.csv"
    if path.find("/PDS/") < 0:
        fileending = "-WDATA.csv"

    session['next'] = 'STupdate/'+path
# use ping to precisely locate the node for which data is to be collected on screen
    current_node = current_node.ping_node(rlevels,layers.Geo_index,path, create=True, accumulate=session.get("accumulate", False))
    session['current_node_id'] = current_node.nid
    print(f"____Route/STUpdate - passed target path to: {path}")
    print(f"Selected street node: {current_node.value} type: {current_node.type}")

    street_node = current_node
    allelectors = elector_for_path(rlevels,street_node.mapfile())
    streetelectors = allelectors[mask]



    if request.method == 'POST':
    # Get JSON data from request
#        VIdata = request.get_json()  # Expected format: {'viData': [{...}, {...}]}
        try:
            print(f"📥 Incoming request to update street: {path} (from all {len(allelectors)} in terr {CElection['mapfiles'][-1]}) with source data {len(streetelectors)} ")

            # ✅ Print raw request data (useful for debugging)
            print("📄 Raw request data:", request.data)

            # ✅ Ensure JSON request
            if not request.is_json:
                print("❌ Request did not contain JSON")
                return jsonify({"error": "Invalid JSON format"}), 400

            VIdata = request.get_json()
            print(f"✅ Received JSON: {data}")
            changelist =[]
            path = config.workdirectories['workdir']+current_node.parent.value+"-INDATA"
            headtail = os.path.split(path)
            path2 = headtail[0]


            if "viData" in VIdata and isinstance(VIdata["viData"], list):  # Ensure viData is a list
                changefields = pd.DataFrame(columns=['ENOP','ElectorName','VR','VI','Notes','Tags','cdate','Electrollfile'])
                i = 0

                for item in VIdata["viData"]:  # Loop through each elector entry
                    electID = str(item.get("electorID","")).strip()
                    ElectorName = item.get("ElectorName","").strip()
                    VR_value = item.get("vrResponse", "").strip() # Extract vrResponse, "" if none
                    VI_value = item.get("viResponse", "").strip()  # Extract viResponse, "" if none
                    Notes_value = item.get("notesResponse", "").strip()  # Extract viResponse, "" if none
                    Tags_value = item.get("tagsResponse", "").strip()  # 👈 Expect a string like "D1 M4"
                    print("VIdata item:",item)  # Print each elector entry to see if duplicates exist

                    if not electID:  # Skip if electorID is missing
                        print("Skipping entry with missing electorID")
                        continue
                    print("_____columns:",allelectors.columns)
                    # Find the row where ENO matches electID
                    allelectors["ENOP"] = allelectors["ENOP"].astype(str)
                    mask = allelectors["ENOP"] == electID
                    changefields.loc[i,'Path'] = street_node.mapfile()
                    changefields.loc[i,'Lat'] = street_node.latlongroid[0]
                    changefields.loc[i,'Long'] = street_node.latlongroid[1]
                    changefields.loc[i,'ENOP'] = electID
                    changefields.loc[i,'ElectorName'] = ElectorName

                    if mask.any():
                        # Update only if viResponse is non-empty
                        if VR_value != "":
                            allelectors.loc[mask, "VR"] = VR_value
                            street_node.updateVR(VR_value)
                            changefields.loc[i,'VR'] = VR_value
                        if VI_value != "":
                            allelectors.loc[mask, "VI"] = VI_value
                            street_node.sumupVI(VI_value)
                            changefields.loc[i,'VI'] = VI_value
                        if Notes_value != "":
                            allelectors.loc[mask, "Notes"] = Notes_value
                            changefields.loc[i,'Notes'] = Notes_value
                        if Tags_value != "":
                            allelectors.loc[mask, "Tags"] = Tags_value
                            changefields.loc[i,'Tags'] = Tags_value
                        print(f"Updated elector {electID} with VI = {VI_value} Notes {Notes_value} and Tags = {Tags_value}")
                        print("ElectorVI", allelectors.loc[mask, "ENOP"], allelectors.loc[mask, "Tags"])
                    else:
                        print(f"Skipping elector {electID}, empty viResponse")

                    changefields.loc[i,'cdate'] = get_creation_date("")
                    changefields.loc[i,'Electrollfile'] = allelectors.loc[0,'Source_ID']
                    changefields.loc[i,'Username'] = session.get('username')

                    i = i+1

                base_path = path2+"/INDATA"
                base_name = current_node.mapfile().replace("-PRINT.html",fileending.replace(".html",""))
                changefields = changefields.drop_duplicates(subset=['ENOP', 'ElectorName'])

                versioned_filename = get_versioned_filename(base_path, base_name, ".csv")

                # Save DataFrame to the new file
                changefields.to_csv(versioned_filename, sep='\t', encoding='utf-8', index=False)
                allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

                print(f"✅ CSV saved as: {versioned_filename}")
            else:
                print("Error: Incorrect JSON format")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return jsonify({"error": str(e)}), 500

# this is for get and post calls
    print("_____Where are we: ", current_node.value, current_node.type, allelectors.columns)


    formdata['tabledetails'] = current_node.value+ "s street details"

#    url = url_for('newstreet',path=mapfile)

    sheetfile = current_node.create_streetsheet(current_election, rlevels,streetelectors)
    pathfile = current_node.dir+"/"+sheetfile
    flash(f"Creating new streetfile:{sheetfile}", "info")
    print(f"Creating new streetfile:{sheetfile}")
    persist(layers.Treepolys, layers.Geo_index)
    return current_node.render_face(current_election,CElection,True)



@app.route('/walkdownST/<path:path>', methods=['GET','POST'])
@login_required
def walkdownST(path):
    from layers import  ensure_treepolys_with_index
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global constants


    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)

    rlevels = CElection.resolved_levels
# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers

    current_node = MapRoot.ping_node(rlevels,layers.Geo_index,path, create=True, accumulate=session.get("accumulate", False))

    walk_node = current_node

# now pointing at the STREETS.html node containing a map of street markers

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())
    print(f"__walkdownST- lenwalk {len(areaelectors)}")
    streetnodelist = walk_node.childrenoftype('street')


    plevels = CElection.parent_levels
    breadcrumb = current_node.mapfile()

    print(f"🔍 [walkdownST] current_node.value = '{current_node.value}' | current_node.level = {current_node.level}")
    print(f"🔍 [walkdownST] breadcrumb = '{breadcrumb}'")
    print(f"🔍 [walkdownST] streetnodelist count = {len(streetnodelist)}")

    # 3. Index & Boundary sync
    filepath, layers.Geo_index = ensure_treepolys_with_index(
        sourcepath=breadcrumb,
        here=None,
        resolved_levels=rlevels,
        parent_levels=plevels,
        areaelectors=areaelectors
    )
    if len(areaelectors) == 0 :
        flash("Can't find any elector data for this Walk.")
        print("Can't find any elector data for this Walk.",len(streetnodelist))
        if os.path.exists(current_node.mapfile()):
            os.remove(current_node.mapfile())
    else:
        flash(f"________in {walk_node.value} there are {len(streetnodelist)} streetnode and markers added")
        print(f"________in {walk_node.value} there are {len(streetnodelist)} streetnode and markers added")

#    for street_node in streetnodelist:
#        mask3 = areaelectors['StreetName'] == street_node.value
#        streetelectors = areaelectors[mask3]
#        print("____Street node value",street_node.value)
#        print(f"Streetelectors Walk electors {len(areaelectors)} streetnodes{len(streetnodelist)} and data {len(streetelectors)} ")
#        street_node.create_streetsheet(current_election,rlevels,streetelectors)

#           only create a map if the branch does not already exist

    print ("________Heading for the Streets in Walk :  ",filepath, walk_node.mapfile())


    print(f"__walkdownST- {current_node.mapfile()} - Walk {current_node.value}, len walk {len(areaelectors)}")

    print ("_________ROUTE/walkdownST/",path, request.method)

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    if current_node.level > 4 and len(areaelectors)  == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}" )
        raise Exception ("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()

        created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels,current_node.mapfile(),static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" Route/walkdownST at level {current_node.level} File not found: {fullpath}")
            print (f"_________ROUTE/walkdownST at {current_node.value} display file created:{fullpath}")

        if not current_node.visit_node(CElection):
            flash("That street is outside of the election Territory")
            print("That street node is outside of the election Territory:")
        persist(layers.Treepolys, layers.Geo_index)

        print (f"_________ROUTE/walkdownST at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)

@app.route('/LGdownST/<path:path>', methods=['GET','POST'])
@login_required
def LGdownST(path):
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global CElection

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels
    T_level = CElection['level']

# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(rlevels,layers.Geo_index,path, create=True, accumulate=session.get("accumulate", False))

    PD_node = current_node
# now pointing at the STREETS.html node containing a map of street markers

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())
    mask2 = areaelectors['PD'] == PD_node.value
    PDelectors = areaelectors[mask2]
    if request.method == 'GET':
    # we only want to plot with single streets , so we need to establish one street record with pt data to plot
        atype = Election.node_type(current_node.level)

        flash("No data for the selected election available!")
        flash("Can't find any elector data for this Polling District.")
        print("Can't find any elector data for this Polling District.")
        if os.path.exists(current_node.mapfile()):
            os.remove(current_node.mapfile())

        streetnodelist = PD_node.childrenoftype('street')
        for street_node in streetnodelist:
            mask = PDelectors['StreetName'] == street_node.value
            streetelectors = PDelectors[mask]
            street_node.create_streetsheet(current_election,rlevels,streetelectors)

        map,totalleaf = PD_node.create_node_map(CElection,layers.Geo_index,rlevels, static=False)


    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.mapfile())


    persist(layers.Treepolys, layers.Geo_index)

    return current_node.render_face(current_election,CElection,True)



@app.route('/WKdownST/<path:path>', methods=['GET','POST'])
@login_required
def WKdownST(path):
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global constants

    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels

    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(rlevels,layers.Geo_index,path, create=True, accumulate=session.get("accumulate", False)) # takes to the clicked node in the territory
    session['current_node_id'] = current_node.nid


    walk_node = current_node

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())

# if there is a selected file , then areaelectors will be full of records
    print("________PDMarker",walk_node.type,"|", walk_node.mapfile())

    flash("No data for the selected election available!")
    walklegnodelist = walk_node.childrenoftype('walkleg')
    print ("________Walklegs",walk_node.value,len(walklegnodelist))
# for each walkleg node(partial street), add a walkleg node marker to the walk_node parent layer (ie PD_node.level+1)
    for walkleg_node in walklegnodelist:
        mask = areaelectors['StreetName'] == walkleg_node.value
        streetelectors = areaelectors[mask]
        walkleg_node.create_streetsheet(current_election,rlevels,streetelectors)

        map,totalleaf = walk_node.create_node_map(CElection,layers.Geo_index,rlevels, static=False)

    if current_node.level > 4 and len(areaelectors)  == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}" )
        raise Exception ("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()

        created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels,current_node.mapfile(),static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" _________ROUTE/WKdownST File not found: {fullpath}")
            print (f"_________ROUTE/WKdownST at {current_node.value} display file created:{fullpath}")

        if not current_node.visit_node(CElection):
            flash("That street is outside of the election Territory")
            print("That street node is outside of the election Territory:")
        persist(layers.Treepolys, layers.Geo_index)

        print (f"_________ROUTE/WKdownST at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)

@app.route('/wardreport/<path:path>',methods=['GET','POST'])
@login_required
def wardreport(path):

    global layeritems
    global formdata
    global CElection
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels
    session['current_node_id'] = current_node.nid

    flash('_______ROUTE/wardreport')
    print('_______ROUTE/wardreport')

    print("________layeritems  :  ", layeritems)

    i = 0
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s  details"
    layeritems = get_layer_table(current_node.create_map_branch(session,'constituency'),formdata['tabledetails'],rlevels)
    for group_node in current_node.childrenoftype('constituency'):

        layeritems = get_layer_table(group_node.create_map_branch(session,'ward'),rlevels)

        for temp in group_node.childrenoftype('ward'):
            if temp.value not in alreadylisted:
                alreadylisted.append(item.value)
                temp.loc[i,'No']= i
                temp.loc[i,'Area']=  item.value
                temp.loc[i,'Constituency']=  group_node.value
                temp.loc[i,'Candidate']=  "Joe Bloggs"
                temp.loc[i,'Email']=  "xxx@reforumuk.com"
                temp.loc[i,'Mobile']=  "07789 342456"
                i = i + 1
        layeritems = [list(temp.columns.values), temp,formdata['tabledetails'] ]

    persist(layers.Treepolys, layers.Geo_index)
    return current_node.parent.render_face(current_election,CElection,False)



# Electtrek.py or routes.py

@app.route("/get_table/<table_name>", methods=["GET"])
@login_required
def get_table(table_name):
    from elections import CurrentElection
    from state import DQstats
    # Load current election if not provided
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels

    # Determine current node
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    try:
        print(f"_______ get table {table_name}")
        columns, rows, title = fetch_table(rlevels,table_name, current_node)
        print(f"_______ get table result {columns}* {rows}* {title}")
        return jsonify([columns, rows, title])
    except Exception as e:
        raise ValueError("Table retrieval fails")
        return jsonify({"error": str(e)}), 500


@app.route('/divreport/<path:path>',methods=['GET','POST'])
@login_required
def divreport(path):

    global layeritems
    global formdata
    global CElection

    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    rlevels = CElection.resolved_levels
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers

    session['current_node_id'] = current_node.nid

    flash('_______ROUTE/divreport')
    print('_______ROUTE/divreport')

    i = 0
    layeritems = pd.DataFrame()
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s details"
    layeritems = get_layer_table(current_node.create_map_branch(session,'constituency'),formdata['tabledetails'],rlevels)

    for group_node in current_node.childrenoftype('division'):

        layeritems = get_layer_table(group_node.create_map_branch(session,'division'),formdata['tabledetails'],rlevels)

#        for item in Featurelayers['division']._children:
#            if item.value not in alreadylisted:
#                alreadylisted.append(item.value)
#                temp.loc[i,'No']= i
#                temp.loc[i,'Area']=  item.value
#                temp.loc[i,'Constituency']=  group_node.value
#                temp.loc[i,'Candidate']=  "Joe Bloggs"
#                temp.loc[i,'Email']=  "xxx@reforumuk.com"
#                temp.loc[i,'Mobile']=  "07789 342456"
#                i = i + 1
#        formdata['tabledetails'] = "Other Division Details"
#        layeritems = [list(temp.columns.values), temp, formdata['tabledetails']]


    persist(layers.Treepolys, layers.Geo_index)
    return current_node.parent.render_face(current_election,CElection,False)


@app.route('/upbut/<path:path>', methods=['GET', 'POST'])
@login_required
def upbut(path):
    from elector import electors
    from elections import CurrentElection
    from layers import ensure_treepolys_with_index

    global environment, layeritems, constants

    logger.info("=== [UPBUT START] Incoming path: '%s' ===", path)

    restore_from_persist(layers.Treepolys, layers.Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels

    # 1. Clean file extension and derive parent path
    clean_path = path.replace("-MAP.html", "").replace(".html", "")
    steps = stepify(clean_path)
    parent_steps = steps[:-1]
    parent_path = clean_path

    logger.info("[UPBUT STEP 1] Parsed steps: %s", steps)
    logger.info("[UPBUT STEP 1] Derived parent_steps: %s", parent_steps)

    current_node = None

    if parent_steps:
        parent_path = "/".join(parent_steps)
        logger.info("[UPBUT STEP 2] O(1) Lookup for parent_path in TREK_NODES_BY_PATH: '%s'", parent_path)

        # Direct O(1) node resolution via path index
        current_node = nodes.TREK_NODES_BY_PATH.get(parent_path)
    else:
        # Default to Root Node (e.g., UNITED_KINGDOM)
        logger.info("[UPBUT STEP 2] parent_steps is empty. Fetching Root Node.")
        map_root = nodes.get_trek_root()
        current_node = nodes.TREK_NODES_BY_PATH.get(map_root.node_path)


    # 2. Guard against missing node
    if current_node is None:
        flash(f"Parent node not found for path: {path}")
        logger.error("❌ [UPBUT ERROR] Failed to resolve parent node for path: %s", path)
        abort(404, f"Parent node not found for path: {path}")

    target_nid = getattr(current_node, "nid", None)
    logger.info("[UPBUT STEP 3] SUCCESS! Resolved Node NID: '%s' (value: '%s')", target_nid, getattr(current_node, "value", None))

    # 3. Mapfile extraction using the resolved node
    if hasattr(current_node, "mapfile"):
        map_file = current_node.mapfile()
    else:
        map_file = f"{getattr(current_node, 'value', 'MAP')}-MAP.html"


    areaelectors = electors.elector_for_path(rlevels, current_node.mapfile())

    plevels = CElection.parent_levels
    breadcrumb = parent_path

    # 3. Index & Boundary sync
    filepath, layers.Geo_index = ensure_treepolys_with_index(
        sourcepath=breadcrumb,
        here=None,
        resolved_levels=rlevels,
        parent_levels=plevels,
        areaelectors=areaelectors
    )

    logger.info("_______ROUTE/upbut path: %s -> Target Node NID: %s, Mapfile: %s", path, target_nid, map_file)

    base = Path(config.workdirectories['workdir'])
    fullpath = base / map_file

    if not fullpath.exists() and hasattr(current_node, "create_node_map"):
        flash("No data for the selected node available, generating map...")
        current_node.create_node_map(CElection,layers.Geo_index,rlevels, static=False)

    if hasattr(current_node, "endpoint_created"):
        created, _ = current_node.endpoint_created(CElection,layers.Geo_index,rlevels, map_file, static=False)
        if created and not fullpath.exists():
            abort(404, f"Route/upbut File not found after creation: {fullpath}")

    if hasattr(current_node, "visit_node"):
        if not current_node.visit_node(CElection):
            flash("That node is outside of the election Territory")

    persist(layers.Treepolys, layers.Geo_index)
    logger.info("_________ROUTE/upbut sending file: %s", fullpath)
    return send_file(fullpath, as_attachment=False)

#Register user
@app.route('/register', methods=['POST'])
def register():
    flash('_______ROUTE/register')

    username = request.form['username']
    password = request.form['password']
    print("Register", username)
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    user = User.query.filter_by(username=username).first()
    if user:
        print("existinuser", user)
        session['current_node_id'] = current_node.nid
        return render_template("index.html",error="User already exists")
    else:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        print("new user", new_user, username)
        login_user(new_user)
        flash('Logged in successfully.')

        next = request.args.get('next')
        session['current_node_id'] = current_node.nid
        return redirect(url_for('get_location'))


@app.route("/calendar_partial/<path:path>")
@login_required
def calendar_partial(path):
    global places, resources, constants
    from baked_data import baked_manager

    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)

    ctype = CElection.node_type(current_node.level)


    # Track used IDs across both existing and new entries
#        places = build_place_lozenges(markerframe)

#        restore_from_persist(layers.Treepolys, layers.Geo_index)
#        current_node = get_current_node(session)
#        CE = CurrentElection.get_lastused()

    program = ProgramContext()
    election = ElectionContext(CElection)
    OPTIONS = resolve_ui_context(program,election,current_node)

    selectedResources = {
            k: v for k, v in OPTIONS['resources'].items()
            if k in CElection['resources']
        }


    print(f"___resources in election {current_election}  node: {current_node.value} Resources: {selectedResources} ")


    # share input and outcome tags
    valid_tags = CElection['Tags']
    task_tags, outcome_tags, all_tags = CElection.get_tags()

    print(f"___ Task Tags {valid_tags} Outcome Tags: {outcome_tags} ")
    print(f"🧪 calendar partial level {current_election} - current_node mapfile:{current_node.mapfile()} ")
    BAKED_DATA = baked_manager.load()

    return render_template(
        "Dash0.html",
        table_types=TABLE_TYPES,
        ELECTIONS=ELECTIONS,
        current_election=current_election,
        options=OPTIONS,
        constants=CElection,
        baked_data=BAKED_DATA,
        mapfile=current_node.mapfile()
    )


@app.route('/thru/<path:path>')
@login_required
def thru(path):
    base = Path(config.workdirectories['workdir'])  # or wherever files live
    fullpath = base / path

    print("_________ROUTE/thru display file:", fullpath)

    if not fullpath.exists():
        abort(404, f" Route/Thru File not found: {fullpath}")
    print ("_________ROUTE/thru display file:",path)
    return send_file(fullpath, as_attachment=False)



@app.route('/showmore/<path:path>', methods=['GET','POST'])
@login_required
def showmore(path):
# is not moving nodes but just changing from wards to div or walks to PD render
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    steps = path.split("/")
    last = steps.pop().split("--")
    current_node = selected_childnode(current_node,last[1])
    flash ("_________ROUTE/showmore"+path)
    print ("_________showmore",path)

    session['current_node_id'] = current_node.nid

    return current_node.parent.render_face(current_election,CElection,True)

@app.route('/upload_data', methods=['POST'])
@login_required
def upload_data():
    from baked_data import baked_manager  # Import your local instance

    print("\n" + "="*60)
    print("📥 [DEBUG] /upload_data route triggered!")
    print("="*60)

    # Safely get JSON payload (handling missing or invalid Content-Type headers)
    try:
        data = request.get_json(force=True) or []
    except Exception as e:
        print(f"⚠️ [DEBUG] Failed to parse request JSON: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

    # --- FIX: Support BOTH raw lists and dictionary wrappers ---
    if isinstance(data, list):
        print("📦 [DEBUG] Detected raw array payload from frontend.")
        incoming_events = data
    elif isinstance(data, dict):
        print("📦 [DEBUG] Detected wrapped object payload from frontend.")
        incoming_events = data.get('events', data.get('baked_data', []))
    else:
        incoming_events = []

    file_path = DATA_FILE

    print(f"🔍 [DEBUG] Path to file being read: {os.path.abspath(file_path)}")
    print(f"📦 [DEBUG] Total incoming events received: {len(incoming_events)}")
    if incoming_events:
        print(f"   📋 [DEBUG] First incoming sample: {incoming_events[0]}")

    raw_parsed_data = []

    # 1. Load and parse the wrapped JavaScript file safely
    if os.path.exists(file_path):
        print(f"📁 [DEBUG] Target file exists. Attempting to parse...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                print(f"   📄 [DEBUG] File character length: {len(content)}")
                print(f"   📄 [DEBUG] First 50 chars of file: '{content[:50]}'")

                # Strip out "window.BAKED_DATA =" and trailing characters to isolate the JSON
                json_string = re.sub(r'^window\.BAKED_DATA\s*=\s*', '', content)
                if json_string.endswith(';'):
                    json_string = json_string[:-1]

                decoded = json.loads(json_string.strip())
                print(f"   ✅ [DEBUG] json.loads() successful. Type decoded: {type(decoded)}")

                # Make sure the decoded target is actually a list
                if isinstance(decoded, list):
                    raw_parsed_data = decoded
                elif isinstance(decoded, dict):
                    raw_parsed_data = [decoded]

                print(f"   📊 [DEBUG] Total historical records loaded from file: {len(raw_parsed_data)}")
        except Exception as e:
            print(f"⚠️ Warning: Could not parse existing data file. Starting fresh. Error: {e}")
            raw_parsed_data = []
    else:
        print(f"❌ [DEBUG] Target file DOES NOT exist yet at path. Starting completely fresh.")

    # Filter out anything that isn't a dictionary to protect against the AttributeError
    existing_data = [item for item in raw_parsed_data if isinstance(item, dict)]
    print(f"🛡️ [DEBUG] Total valid historical dict items after filter: {len(existing_data)}")

    # 2. Update status of incoming batch items to true and append safely
    updates_count = 0
    appends_count = 0

    for idx, event in enumerate(incoming_events):
        if not isinstance(event, dict):
            print(f"   ⚠️ [DEBUG] Skipped item index {idx} because it was not a dictionary.")
            continue  # Protect against malformed incoming events

        event['synced'] = True

        # Pull key timestamps for explicit tracking logs
        incoming_ts = event.get('ts')

        # De-duplication check: Look up via timestamp safely
        existing_match = next((item for item in existing_data if item.get('ts') == incoming_ts), None)

        if existing_match:
            print(f"   🔄 [DEBUG] MATCH FOUND for timestamp '{incoming_ts}'. Overwriting entry in place.")
            existing_match.update(event) # Update the record in place
            updates_count += 1
        else:
            print(f"   ➕ [DEBUG] NO MATCH found for timestamp '{incoming_ts}'. Appending to array.")
            existing_data.append(event)  # Add new unique record
            appends_count += 1

    print(f"🏁 [DEBUG] Loop complete. Merged array now has: {len(existing_data)} total elements.")
    print(f"   📊 [DEBUG] Detail: {updates_count} updated in-place, {appends_count} appended cleanly.")

    # 3. Wrap it back up in the JavaScript assignment layout and save
    try:
        print(f"💾 [DEBUG] Writing combined list back to disk...")
        with open(file_path, 'w', encoding='utf-8') as f:
            raw_json = json.dumps(existing_data, indent=4)
            f.write(f"window.BAKED_DATA = {raw_json};")
        print(f"🚀 [DEBUG] Write successful!")
    except Exception as e:
        print(f"❌ [DEBUG] Critical Write Error: {e}")
        return jsonify({"status": "error", "message": f"Failed to write file: {str(e)}"}), 500

    print("="*60 + "\n")
    return jsonify({"status": "success"}), 200

@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file received'}), 400

    filename = secure_filename(file.filename)
    print("_______After Secure filename check: ",file.filename)
    save_path = os.path.join(config.workdirectories['workdir'], filename)
    file.save(save_path)
    session['current_node_id'] = current_node.nid

    return jsonify({'message': 'File uploaded', 'path': save_path})


@app.route('/filelist/<filetype>', methods=['POST','GET'])
@login_required
def filelist():

    from elector import electors

    global environment

    global formdata
    global layeritems
    global CElection

    flash('_______ROUTE/filelist',filetype)
    print('_______ROUTE/filelist',filetype)
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    if filetype == "maps":
        return jsonify({"message": "Success", "file": url_for('thru', path=mapfile)})



@app.route('/progress')
@login_required
def get_progress():
    from state import progress
    # 1. Read completion status safely
    status = progress.get('status', 'idle')

    # 2. Lazy-load and render DQStats ONCE if completed and not yet generated
    if status == 'complete' and not progress.get('dqstats_html'):
        target_file = progress.get('targetfile', '')
        if target_file:
            dq_file_path = os.path.join(
                config.workdirectories['workdir'],
                subending(target_file, "DQ.csv")
            )
            if os.path.exists(dq_file_path):
                dq_df = pd.read_csv(
                    dq_file_path,
                    sep='\t',
                    engine='python',
                    encoding='utf-8',
                    keep_default_na=False,
                    na_values=['']
                )
                progress['dqstats_html'] = render_template(
                    'partials/dqstats_rows.html',
                    DQstats=dq_df
                )

    # 3. Construct clean response payload directly
    response = {
        'election': progress.get('election', ''),
        'percent': progress.get('percent', 0),
        'status': status,
        'current_stage': progress.get('current_stage', ''),
        'stage_progress': progress.get('stage_progress', 0),
        'stages': progress.get('stages', {}),
        'message': progress.get('message', ''),
        'targetfile': progress.get('targetfile', ''),
        'dqstats_html': progress.get('dqstats_html', '')
    }

    return jsonify(response)


@app.route('/deactivate_election/<election_name>', methods=['POST'])
@login_required
def deactivate_election(election_name):
    from elections import CurrentElection
    from elector import electors

    try:
        restore_from_persist(layers.Treepolys, layers.Geo_index)
        CElection = CurrentElection.load(election_name)
        territory_path = CElection['territory']
        rlevels = CElection.resolved_levels
        print(f" Deactivate after restore: {election_name} path {territory_path} rlevels {rlevels}")

        # Resolve the territory node for subtree pruning
        territory_node = MapRoot.ping_node(
            rlevels,
            territory_path,
            create=False,
            accumulate=session.get("accumulate", False)
        )
        print(f" Deactivate : {election_name} node: {territory_node.mapfile()}")

        # ✅ FIXED: Purge electors directly by election name (bypasses broken spatial columns/OUTSIDE records)
        deleted_count = electors.delete_by_election(election_name)
        print(f" Deactivate PURGED: {deleted_count} elector records for '{election_name}'")

        print(f"Deactivate PRUNING {territory_node.value}")
        prune_subtree(territory_node)

        save_nodes(TREKNODE_FILE)
        persist(layers.Treepolys, layers.Geo_index)

        return jsonify({
            "success": True,
            "message": f"Election {election_name} deactivated successfully.",
            "deleted_count": deleted_count
        })

    except Exception as e:
        import traceback
        print(f"❌ Error deactivating election {election_name}: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/walks', methods=['POST','GET'])
@login_required
def walks():

    from elector import electors
    from baked_data import baked_manager


    global streamrag
    global CElection
    global TABLE_TYPES


    global environment
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    resolved_levels = CElection.resolved_levels

    assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

    # The clean unpack you like
    (c_election, elevels), = resolved_levels.items()

    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    flash('_______ROUTE/walks',session)
    BAKED_DATA = baked_manager.load()

    if len(request.form) > 0:
        formdata = {}
        formdata['importfile'] = request.files['importfile']
        formdata['electiondate'] = request.form["electiondate"]
        electwalks = prodwalks(current_node,formdata['importfile'], formdata,layers.Treepolys, environment)
        formdata = electwalks[1]
        print("_________Mapfile",electwalks[2])
        group = electwalks[0]

#    formdata['username'] = session['username']
        session['current_node_id'] = current_node.nid

        return render_template('Dash0.html',  formdata=formdata,table_types=TABLE_TYPES, current_election=current_election, baked_data=BAKED_DATA,group=allelectors , streamrag=streamrag ,mapfile=current_node.mapfile())
    return redirect(url_for('dashboard'))

@app.route('/postcode', methods=['POST','GET'])
@login_required
def postcode():
# the idea of this service is to locate people's branches using their postcode.
# first get lat long, then search through constit boundaries and pull up the NAME of the one that its IN


    global CElection
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = get_last_node(CElection,layers.Geo_index,create=False)
    rlevels = CElection.resolved_levels
    flash('__ROUTE/Findpostcode')

    pthref = current_node.mapfile()
    postcodeentry = request.form["postcodeentry"]
    if len(postcodeentry) > 8:
        postcodeentry = str(postcodeentry).replace(" ","")
    dfx = pd.read_csv(config.workdirectories['bounddir']+"National_Statistics_Postcode_Lookup_UK_20241022.csv")
    df1 = dfx[['Postcode 1','Latitude','Longitude']]
    df1 = df1.rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
    df1['Lat'] = df1['Lat'].astype(float)
    df1['Long'] = df1['Long'].astype(float)
    lookuplatlong = df1[df1['Postcode'] == postcodeentry]
    here = [float(f"{lookuplatlong.Lat.values[0]:.6f}"), float(f"{lookuplatlong.Long.values[0]:.6f}")]
    pfile = Treepolys[current_node.child_type(rlevels)]
    polylocated = find_boundary(pfile,here)
    flash(f'___The branch that contains this postcode is:{polylocated.NAME}')

    return redirect(url_for('dashboard'))

import csv
from state import clean_text, clean_mobile


def convert_csv_to_clean_json(csv_path):
    resources = {}
    existing_codes = set()

    # 1. Convert to Path object
    raw_path = Path(csv_path)

    # 2. If it's a relative path, anchor it to the current file's directory
    if not raw_path.is_absolute():
        base_dir = Path(__file__).resolve().parent
        csv_path = base_dir / raw_path
    else:
        csv_path = raw_path

    json_path = csv_path.with_suffix(".json")

    # Debug statement to see exact absolute path being evaluated
    print(f"🔍 [convert_csv_to_clean_json] Checking path: {csv_path.absolute()}")

    if not csv_path.exists():
        logging.warning(f"❌ Resource CSV file not found at {csv_path.absolute()}")
        return resources

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            firstname = clean_text(row.get("Firstname"))
            surname = clean_text(row.get("Surname"))

            if not firstname and not surname:
                continue

            code = clean_text(row.get("Code"))
            if not code:
                code = generate_code(firstname, surname, existing_codes)

            existing_codes.add(code)
            resources[code] = {
                "Firstname": firstname,
                "Surname": surname,
                "Postcode": clean_text(row.get("Postcode")),
                "Address1": clean_text(row.get("Address1")),
                "Address2": clean_text(row.get("Address2")),
                "campaignMgremail": clean_text(row.get("campaignMgremail")),
                "Mobile": clean_mobile(row.get("Mobile")),
                "Role": clean_text(row.get("Role"))
            }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resources, f, indent=2)

    print(f"✅ Clean JSON written to {json_path}")
    return resources



@app.route('/firstpage', methods=['GET', 'POST'])
@login_required
def firstpage():
    from elector import electors
    from layers import ensure_treepolys_with_index
    from elections import CurrentElection
    from baked_data import baked_manager
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point

    # 1. Resource synchronization
    resource_file = globals().get('RESOURCE_FILE', 'resources.csv')
    logger.info("▶️ ROUTE/firstpage called")
    print(f"print ROUTE/firstpage called resource file:{resource_file}")
    try:
        convert_csv_to_clean_json(resource_file)
    except Exception as e:
        logger.error(f"Failed converting resource CSV to JSON: {e}")

    # 2. State & Election restore
    restore_from_persist(layers.Treepolys, layers.Geo_index)
    current_election = CurrentElection.get_lastused()
    session["current_election"] = current_election

    CElection = CurrentElection.load(current_election)
    if not CElection:
        return jsonify(success=False, error="Election not found"), 404

    rlevels = CElection.resolved_levels
    assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"
    (c_election, elevels), = rlevels.items()
    plevels = CElection.parent_levels

    current_node = get_last_node(CElection,layers.Geo_index,create=True)
    session["current_node_id"] = current_node.nid

    program = ProgramContext()
    election_ctx = ElectionContext(CElection)
    OPTIONS = resolve_ui_context(program, election_ctx, current_node)

    areaelectors = electors.elector_for_path(rlevels, current_node.path_at_level(3))

    breadcrumb = CElection['mapfiles'][-1] if CElection.get('mapfiles') else None

    lat = CElection.get('cidLat')
    lon = CElection.get('cidLong')
    here = (lat, lon) if (lat is not None and lon is not None) else None

    # Determine Walk File Path
    walk_geom_file = globals().get('WALK_GEOM_FILE', 'walk_geoms.geojson')

    # Step A: Initial call to ensure_treepolys_with_index
    filepath, layers.Geo_index = ensure_treepolys_with_index(
        sourcepath=breadcrumb,
        here=here,
        resolved_levels=rlevels,
        parent_levels=plevels,
        areaelectors=areaelectors
    )

    flash(f"ROUTE /firstpage filepath: {filepath}", "info")
    logger.info(f"ROUTE /firstpage filepath {filepath}")

    map_obj, totalleaf = current_node.create_node_map(CElection,layers.Geo_index,rlevels, static=False)

    ELECTIONS = get_available_elections()
    BAKED_DATA = baked_manager.load()

    persist(layers.Treepolys, layers.Geo_index)

    return render_template(
        "Dash0.html",
        table_types=TABLE_TYPES,
        ELECTIONS=ELECTIONS,
        current_election=current_election,
        options=OPTIONS,
        constants=CElection,
        baked_data=BAKED_DATA,
        mapfile=current_node.mapfile()
    )

@app.route('/cards', methods=['POST','GET'])
@login_required
def cards():

    from elector import electors
    from baked_data import baked_manager


    global streamrag
    global environment
    global TABLE_TYPES

    flash('_______ROUTE/canvasscards',session, request.form, current_node.level)


    if len(request.form) > 0:
        formdata = {}
        formdata['country'] = "UNITED_KINGDOM"
        formdata['importfile'] = request.files['importfile']
        formdata['electiondate'] = request.form["electiondate"]
        if current_node.level > 2:
            formdata['constituency'] = current_node.value
            formdata['county'] = current_node.parent.value
            formdata['nation'] = current_node.parent.parent.value
            formdata['country'] = current_node.parent.parent.parent.value

            prodcards = canvasscards.prodcards(current_node,formdata['importfile'], formdata, Treepolys, environment)
            formdata = prodcards[1]
            print('_______Formdata:',formdata)

            if formdata['streets'] > 0 :
                print("_________formdata",formdata)
                flash ( "Electoral data for" + formdata['constituency'] + " can now be explored.")

                group = prodcards[0]
                ELECTIONS = get_available_elections()
                return render_template('Dash0.html',  table_types=TABLE_TYPES,formdata=formdata,current_election=CElection[session.get("current_election","DEMO")], ELECTIONS=ELECTIONS, baked_data=BAKED_DATA, group=allelectors , streamrag=streamrag ,mapfile=current_node.mapfile())
            else:
                flash ( "Data file does not match selected constituency!")
                print ( "Data file does not match selected constituency!")
        else:
            flash ( "Data file does not match selected area!")
            print ( "Data file does not match selected area!")
    session['current_node_id'] = current_node.nid
    return redirect(url_for('dashboard'))


# Sample file info data (replace with your actual data)
file_info = [
    {'Order': 1, 'Election': 'A', 'Filename': 'BEEP_ElectoralRoll.xlsx', 'Type': 'xlsx', 'Purpose': 'main', 'Fixlevel': '1'},
    {'Order': 2, 'Election': 'A', 'Filename': 'BEEP_AbsentVoters.csv', 'Type': 'csv', 'Purpose': 'avi', 'Fixlevel': '2'},
    {'Order': 1, 'Election': 'B', 'Filename': 'WokingRegister.xlsx', 'Type': 'xlsx', 'Purpose': 'main', 'Fixlevel': '3'},
    {'Order': 2, 'Election': 'B', 'Filename': 'WokingAVlist.csv', 'Type': 'csv', 'Purpose': 'avi', 'Fixlevel': '1'},
    # Add more file data as needed
]


@app.route('/normalise', methods=['POST'])
@login_required
def normalise():
    from elector import electors
    from elections import CurrentElection
    from state import progress, update_progress
    """
    Launch background normalisation using frontend JSON payload.
    """
    payload = request.get_json()  # JSON instead of form
    if not payload:
        return jsonify({"error":"Missing JSON payload"}), 400

    ename = payload.get("ename")
    if not ename:
        return jsonify({"error": "Election name is required"}), 400

    files = payload.get("files", [])
    if not files:
        return jsonify({"error": "No files provided"}), 400

    # --- Load election ---
    CElection = CurrentElection.load(ename)
    print(f"DEBUG ENAME BEFORE SESSION: '{ename}'")

    if 'stream_processing' not in CElection:
        CElection['stream_processing'] = {"files": [], "last_run": None, "status": "idle"}

    # --- Build meta_data expected by  ---
    meta_data = {}
    for idx, f in enumerate(files):
        meta_data[str(idx)] = {
            "stored_path": f.get("stored_path"),
            "order": f.get("order"),
            "type": f.get("type"),
            "purpose": f.get("purpose"),
            "fixlevel": f.get("fixlevel"),
            "election": ename
        }





    # --- Build other arguments ---
    request_form = {"election": ename}
    request_files = {}  # no file uploads; we just have stored paths
    session['current_election'] = ename
    session_data = dict(session)

    if ename in CurrentElection.get_all():
        print(f"⛔ Election '{ename}' already exists. Aborting import.")

        progress.update({
            "percent": 100,
            "status": "error",
            "message": f"Election '{ename}' already loaded"
        })
        return

    RunningVals = {
        'Mean_Lat' : 51.240299,
        'Mean_Long' : -0.562301,
        'Last_Lat'  : 51.240299,
        'Last_Long' : -0.562301
    }

    Lookups = {}

    Lookups['Elevation'] = pd.read_csv(
        config.workdirectories['bounddir'] + "/open_postcode_elevation.csv"
        )

    Lookups['Elevation'].columns = ["Postcode", "Elevation"]
#    dfw = pd.read_csv(POSTCODE_FILE)
    dfw = pd.read_csv(POSTCODE_FILE, low_memory=False, encoding='utf-8-sig')
    print(f"DEBUG: CSV Headers found are: {dfw.columns.tolist()}")
    Lookups['LatLong'] = dfw[['pcd7','lat','long']]
    Lookups['LatLong'] = Lookups['LatLong'].rename(
            columns={'pcd7':'Postcode','lat':'Lat','long':'Long'}
        )

    stream_table = []
    streams = [f.get("stored_path") for f in files]  # just for thread usage

    # --- Start background thread ---
    threading.Thread(
        target=background_normalise,
        args=(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table)
    ).start()

    return jsonify({"message": "Normalization started"})


@app.route('/get_territory_data')
@login_required
def get_territory_data():
    node_path = request.args.get('nodepath', 'UNITED_KINGDOM')

    if node_path not in Geo_index:
        return jsonify({"error": "Node not found"}), 404

    current_node = Geo_index[node_path]
    parent_path = current_node['parent']

    # Helper to turn a path into a dict with NID and Path
    def get_node_info(path):
        return {
            "path": path,
            "nid": Geo_index[path].get('nid'),
            "name": path.split('/').pop().replace('_', ' ')
        }

    # 1. Get Children with metadata
    children_info = [get_node_info(c) for c in current_node['children']]

    # 2. Get Siblings with metadata
    siblings_info = []
    if parent_path and parent_path in Geo_index:
        siblings_info = [
            get_node_info(s) for s in Geo_index[parent_path]['children']
            if s != node_path
        ]


    created, totalleaf = current_node.endpoint_created(CElection,layers.Geo_index,rlevels, lastfilepath, static=False)
    return jsonify({
        "current_name": current_node['name'],
        "current_path": node_path,
        "parent_path": parent_path,
        "children": children_info,  # Now a list of dicts
        "siblings": siblings_info,  # Now a list of dicts
        "map_url": f"/thru/{node_path}.html"
    })

@app.route("/get_stream_processing/<ename>")
@login_required
def get_stream_processing(ename):
    """
    Load the stream_processing structure for a given election name.
    If none exists, return a default structure.
    """
    from elections import CurrentElection  # adjust import as needed

    CElection = CurrentElection.load(ename)  # loads the election dict

    if CElection and "stream_processing" in CElection:
        stream_processing = CElection["stream_processing"]
    else:
        # Default structure if nothing exists yet
        stream_processing = {
            "files": [],
            "last_run": None,
            "status": "idle"
        }

    # Ensure files is always a list (prevents frontend errors)
    if "files" not in stream_processing or not isinstance(stream_processing["files"], list):
        stream_processing["files"] = []

    return jsonify(stream_processing)

@app.route('/stream_input')
@login_required
def stream_input():
    from elector import electors  # If needed for election data

    DQstats = pd.DataFrame()

    # Get elections from the get_elections function
    elections = get_elections()  # This will call the new function to get elections data

    # Optionally build stream paths if needed
    base_path = "/your/base/path"  # Replace with the actual base directory
    for row in elections:
        election = row.get("cid", "")
        if election:
            row["stream_path"] = str(Path(base_path) / election)
        else:
            row["stream_path"] = ""

    ELECTIONS = get_available_elections()  # Assuming this fetches available elections for front end
    streams = list(ELECTIONS)

    return render_template(
        'stream_processing_input.html',
        ELECTIONS=ELECTIONS,   # Pass elections list to the template
        stream_table=elections,  # You can pass this as stream_table, since it's now the same data
        DQstats=DQstats
    )


# server.py (Flask)

from pathlib import Path
from flask import Flask, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename

# Very important: protect this route with authentication in production
@app.route("/api/upload-and-protect", methods=["POST"])
def upload_and_protect():
    global SERVER_PASSWORD
    # Basic checks
    if "file" not in request.files:
        return "Missing file", 400

    file = request.files["file"]
    orig_filename = secure_filename(file.filename or "calendar.html")

    # Optional: restrict filename pattern to avoid abuse
    if not orig_filename.lower().endswith(".html"):
        return "Only .html files allowed", 400

    # Save to server (overwrite if exists)
    save_path = config.workdirectories['workdir']+"/"+orig_filename
    try:
        file.save(save_path)
    except Exception as e:
        current_app.logger.exception("Failed saving uploaded file")
        return jsonify({"ok": False, "error": "save_failed"}), 500

    # Option: return JSON with saved path or a download URL
    return jsonify({"ok": True, "path": str(save_path), "filename": orig_filename})



if __name__ in '__main__':
    with app.app_context():
        print("__________Starting up", os.getcwd())
        db.create_all()
#        app.run(host='0.0.0.0', port=5000)
        app.run(debug=True, threaded=False, processes=1, use_reloader=True)



# 'method' is a function that is present in a file called 'file.py'
