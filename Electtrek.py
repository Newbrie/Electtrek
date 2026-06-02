from canvasscards import prodcards, find_boundary
from walks import prodwalks
#import electwalks, locfilepath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
import config
from config import POSTCODE_FILE,TABLE_FILE,LAST_RESULTS_FILE,ELECTIONS_FILE,TREEPOLY_FILE,GENESYS_FILE,ELECTOR_FILE,TREKNODE_FILE,FULLPOLY_FILE,RESOURCE_FILE, DEVURLS, NATIONAL_DIVISION_FILE,DATA_FILE
from normalised import normz
#import normz

from json import JSONEncoder, JSONDecodeError
import pandas as pd
import geopandas as gpd
import numpy as np
from numpy import ceil
import statistics
from sklearn.cluster import KMeans
from shapely.geometry import Point
from sklearn.preprocessing import StandardScaler
import io
import re
from decimal import Decimal
from pyproj import Proj
import os, sys, math, stat, json , jinja2, random
from os import listdir, system
import glob
from markupsafe import escape
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask,render_template, request, redirect, session, url_for, send_from_directory, jsonify, flash, render_template_string
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask import abort
from flask import json, get_flashed_messages, make_response
from werkzeug.exceptions import HTTPException
from datetime import datetime, timedelta, date
import geocoder
from pathlib import Path
from shapely.geometry import Point, Polygon, MultiPolygon

from flask_session import Session
from flask_cors import CORS
from flask_login import LoginManager


from collections import defaultdict
import requests
import threading
import traceback
import unidecode
from flask import Response
import copy
import json


import locale

import logging
logging.getLogger("pyproj").setLevel(logging.WARNING)


import state
from state import VNORM,TABLE_TYPES,LEVEL_ZOOM_MAP, LastResults, levelcolours, subending, check_level4_gap
from state import Treepolys, Fullpolys,Geo_index,update_progress, normalname, route, stepify, resolve_here_or_redirect

import nodes
from nodes import get_layer_table, get_root,restore_from_persist, persist,parent_level_for, save_nodes, move_item
import layers
from elections import get_available_elections, get_elections, CurrentElection, ProgramContext, ElectionContext, resolve_ui_context
from elector import electors


locale.setlocale(locale.LC_TIME, 'en_GB.UTF-8')


sys.path
sys.path.append('/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Electtrek.py')
print(sys.path)

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
    from state import Treepolys, Fullpolys, Geo_index

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

# Recursive KMeans for hierarchical walks
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
            max_depth=max_depth,       # Use the variable, not hardcoded 10
            max_walk_size=max_walk_size # Pass this through or it will reset to 300!
        )
        label_map.update(sub_label_map)
    return label_map

def assign_areas(electors_df, rlevels, progress=None):
    import geopandas as gpd

    if progress:
        update_progress(progress, "assign_areas", 0.0, "Assigning areas (incremental)...")

    # -------------------------------------------------
    # Ensure Area column exists
    # -------------------------------------------------

    if 'Area' not in electors_df.columns:
        electors_df['Area'] = None

    # Only process:
    # - never assigned
    # - previously OUTSIDE
    mask = electors_df['Area'].isna() | (electors_df['Area'] == 'OUTSIDE')
    subset = electors_df.loc[mask].copy()

    if subset.empty:
        print("✅ No electors need area assignment")
        return electors_df

    print(f"🔄 Assigning areas for {len(subset)} electors")

    # -------------------------------------------------
    # Drop rows with no postcode (cannot process)
    # -------------------------------------------------

    no_pc_mask = subset['Postcode'].isna() | (subset['Postcode'] == "")

    if no_pc_mask.any():
        print(f"⚠️ {no_pc_mask.sum()} records have no postcode → forced OUTSIDE")

        electors_df.loc[subset[no_pc_mask].index, 'Area'] = 'OUTSIDE'

    subset = subset.loc[~no_pc_mask].copy()

    if subset.empty:
        return electors_df

    # -------------------------------------------------
    # Load polygons
    # -------------------------------------------------

    child_type = next(iter(rlevels.values()))[4]
    child_polys = Treepolys.get(child_type)

    if child_polys is None or len(child_polys) == 0:
        print(f"❌ No polygons for {child_type}")
        return electors_df

    child_polys = child_polys.copy()
    child_polys['NAME'] = child_polys['NAME'].apply(
        lambda x: normalname(x) if x else 'UNKNOWN'
    )

    gdf_polys = gpd.GeoDataFrame(child_polys, geometry='geometry')
    gdf_polys = gdf_polys.set_crs(child_polys.crs)
    gdf_polys['geometry'] = gdf_polys.buffer(0)
    gdf_polys = gdf_polys.to_crs("EPSG:4326")

    # -------------------------------------------------
    # Build GeoDataFrame (subset only)
    # -------------------------------------------------

    gdf_electors = gpd.GeoDataFrame(
        subset,
        geometry=gpd.points_from_xy(subset['Long'], subset['Lat']),
        crs="EPSG:4326"
    )

    # -------------------------------------------------
    # Group by postcode → representative point
    # -------------------------------------------------

    gdf_postcodes = (
        gdf_electors
        .groupby('Postcode')['geometry']
        .apply(lambda pts: pts.union_all().representative_point())
        .reset_index()
    )

    gdf_postcodes = gpd.GeoDataFrame(gdf_postcodes, geometry='geometry', crs="EPSG:4326")

    # -------------------------------------------------
    # Spatial join (NO snapping anymore)
    # -------------------------------------------------

    gdf_joined = gpd.sjoin(
        gdf_postcodes,
        gdf_polys[['NAME', 'geometry']],
        how='left',
        predicate='intersects'
    )

    gdf_joined = (
        gdf_joined
        .sort_values('index_right')
        .drop_duplicates(subset='Postcode', keep='first')
    )

    if 'index_right' in gdf_joined.columns:
        gdf_joined = gdf_joined.drop(columns=['index_right'])

    # 🔑 Key change: NO nearest snapping
    gdf_joined['NAME'] = gdf_joined['NAME'].fillna('OUTSIDE')

    # -------------------------------------------------
    # Map back
    # -------------------------------------------------

    postcode_to_area = dict(zip(gdf_joined['Postcode'], gdf_joined['NAME']))

    electors_df.loc[subset.index, 'Area'] = subset['Postcode'].map(postcode_to_area)

    # Final fill safety
    electors_df['Area'] = electors_df['Area'].fillna('OUTSIDE')

    outside_count = (electors_df['Area'] == 'OUTSIDE').sum()
    print(f"🔍 Area assignment complete. {outside_count} OUTSIDE")

    if progress:
        update_progress(progress, "assign_areas", 1.0, "Area assignment complete.")

    return electors_df

def assign_specific_area(electors_df, rlevels, area_name, progress=None):
    """
    Guarantees the same intersection test as assign_areas by using
    the identical sjoin predicate and geometry preparation.
    """
    import geopandas as gpd

    # 1. Get the specific polygon and apply the EXACT same prep as assign_areas
    child_type = next(iter(rlevels.values()))[4]
    child_polys = Treepolys.get(child_type)

    if child_polys is None or child_polys.empty:
        return electors_df

    # Filter for the specific polygon
    target_gdf = child_polys[child_polys['NAME'].apply(normalname) == normalname(area_name)].copy()

    if target_gdf.empty:
        return electors_df

    # --- IDENTICAL PREP START ---
    target_gdf = gpd.GeoDataFrame(target_gdf, geometry='geometry')
    target_gdf = target_gdf.set_crs(child_polys.crs)
    target_gdf['geometry'] = target_gdf.buffer(0) # Same "Fix" as assign_areas
    target_gdf = target_gdf.to_crs("EPSG:4326")   # Same Projection
    # --- IDENTICAL PREP END ---

    # 2. Identify target electors
    mask = electors_df['Area'].isna() | (electors_df['Area'] == 'OUTSIDE')
    subset = electors_df.loc[mask].copy()
    if subset.empty: return electors_df

    # 3. Build Elector GDF (Same points_from_xy method)
    gdf_electors = gpd.GeoDataFrame(
        subset,
        geometry=gpd.points_from_xy(subset['Long'], subset['Lat']),
        crs="EPSG:4326"
    )

    # 4. Postcode Grouping (Same representative_point method)
    gdf_postcodes = (
        gdf_electors
        .groupby('Postcode')['geometry']
        .apply(lambda pts: pts.union_all().representative_point())
        .reset_index()
    )
    gdf_postcodes = gpd.GeoDataFrame(gdf_postcodes, geometry='geometry', crs="EPSG:4326")

    # 5. THE IDENTICAL TEST: sjoin with predicate='intersects'
    # By using sjoin instead of a manual loop, we use the exact same spatial index logic
    gdf_joined = gpd.sjoin(
        gdf_postcodes,
        target_gdf[['NAME', 'geometry']],
        how='inner',            # 'inner' ensures we only get matches for this specific area
        predicate='intersects'  # EXACT same test as your latest assign_areas
    )

    # 6. Map back
    valid_postcodes = gdf_joined['Postcode'].unique()
    final_update_mask = mask & (electors_df['Postcode'].isin(valid_postcodes))
    electors_df.loc[final_update_mask, 'Area'] = area_name

    return electors_df


def assign_walks_and_zones(
    electors_df,
    teamsize,
    territory_path,
    rlevels,
    aprefix,
    max_walk_size=300,
    max_depth=10,
    progress=None
):
    from sklearn.cluster import KMeans
    import numpy as np
    import pandas as pd
    from state import update_progress

    # 🛡️ Safety: Ensure columns exist
    for col in ['WalkName', 'WalkName_hier', 'Zone']:
        if col not in electors_df.columns:
            electors_df[col] = np.nan

    # 1. Identify electors needing assignment
    mask_assign = (electors_df['Area'].notna()) & (electors_df['Area'] != 'OUTSIDE') & (
        electors_df['WalkName'].isna() | (electors_df['WalkName'] == '')
    )
    to_assign = electors_df.loc[mask_assign]

    if to_assign.empty:
        return electors_df

    # ---------------------------------------------------------
    # STEP 1: YOUR ORIGINAL WALK LOGIC (DO NOT CHANGE)
    # This generates the high-quality clusters and walk names
    # ---------------------------------------------------------
    walk_labels = recursive_kmeans(to_assign, prefix=aprefix, max_walk_size=max_walk_size)
    hier_series = pd.Series(walk_labels, index=to_assign.index)
    electors_df.loc[to_assign.index, 'WalkName_hier'] = hier_series

    unique_label_map = {}
    serial_series = pd.Series(index=to_assign.index, dtype=str)

    # Calculate global walk count to keep naming unique across the whole import
    existing_count = electors_df['WalkName'].dropna().nunique()

    for idx, raw_label in hier_series.items():
        label_key = str(raw_label).strip()
        if label_key not in unique_label_map:
            unique_label_map[label_key] = f"{aprefix}{len(unique_label_map) + existing_count + 1:02}"
        serial_series.loc[idx] = unique_label_map[label_key]

    electors_df.loc[to_assign.index, 'WalkName'] = serial_series

    # ---------------------------------------------------------
    # STEP 2: AREA-SPECIFIC ZONE LOGIC
    # Now we just divide the walks into 8 zones PER area
    # ---------------------------------------------------------
    unique_areas = to_assign['Area'].unique()

    for area_name in unique_areas:
        # Filter for only the walks we just created inside this specific Area
        area_mask = (electors_df['Area'] == area_name) & (electors_df.index.isin(to_assign.index))
        area_indices = electors_df.index[area_mask]

        # Get centers of the walks within this specific area
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
            # Apply zones only to electors in this Area
            electors_df.loc[area_indices, 'Zone'] = electors_df.loc[area_indices, 'WalkName'].map(zone_map)
        else:
            electors_df.loc[area_indices, 'Zone'] = 'ZONE_1'

    if progress:
        update_progress(progress, "assign_walks", 1.0, "Walk & zone assignment complete.")

    return electors_df

def check_columns_consistency(mainframe, *frames, verbose=True):
    """
    Ensure all frames have the same columns as mainframe.

    - Adds missing columns (set to None)
    - Removes extra columns
    - Reorders columns to match mainframe
    - Returns True if schemas match after alignment
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

        # Remove extra columns
        if extra:
            frame.drop(columns=list(extra), inplace=True)

        # Reorder columns to match mainframe
        frame = frame.reindex(columns=main_cols)

        if verbose:
            if missing:
                print(f"Frame {i+1}: Added missing columns -> {missing}")
            if extra:
                print(f"Frame {i+1}: Removed extra columns -> {extra}")

        # Final verification
        if list(frame.columns) != main_cols:
            if verbose:
                print(f"Frame {i+1}: ❌ Column mismatch remains after alignment.")
            all_passed = False
        else:
            if verbose:
                print(f"Frame {i+1}: ✅ Column check passed.")

    return all_passed



def background_normalise(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table):
    """
    Full background normalisation routine with targeted DEBUG instrumentation
    to track the Ashford data disappearance.
    """
    import logging, os, traceback, re, pandas as pd
    from shapely.geometry import Point, Polygon
    from elector import electors
    from state import Treepolys, Fullpolys, Geo_index, progress, DQstats, update_progress, check_level4_gap, ensure_treepolys_with_index
    from elections import CurrentElection
    from layers import create_boundary_geom

    logging.basicConfig(
        filename="electtrek.log",
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Outcols = pd.read_excel(GENESYS_FILE).columns # Assuming GENESYS_FILE is defined globally
        mainframes, deltaframes, aviframes, pledge_frames, DQstatslist = [], [], [], [], []

        # --- Stage 1: Sourcing & Path Resolution ---
        update_progress(progress, "sourcing", 0.0, "Sourcing data...")

        current_election = session_data.get('current_election', 'UNKNOWN')
        CElection = CurrentElection.load(current_election)
        resolved_levels = CElection.resolved_levels
        parent_levels = CElection.parent_levels
        territory_path = CElection['territory']
        lastfilepath = CElection['mapfiles'][-1]
        here = (CElection.get('cidLat', None), CElection.get('cidLong', None))

        # --- DEBUG 1: Path Cleanup ---
        # If Ashford is a division, the '.html' in the territory path might be blocking the hierarchy
        clean_territory = territory_path.replace("-DIVS.html", "").replace(".html", "")
        path_parts = stepify(clean_territory)

        print(f"🔍 DEBUG [1/5] Path Resolution:")
        print(f"   > Raw Territory: {territory_path}")
        print(f"   > Cleaned Parts: {path_parts}")

        lastfilepath, Geo_index = ensure_treepolys_with_index(
            territory=territory_path,
            sourcepath=lastfilepath,
            here=here,
            resolved_levels=resolved_levels,
            parent_levels=parent_levels
        )

        levels = ["Country", "Nation", "County", "Constituency", "Division"] # Added Division
        geo_context = {levels[i]: path_parts[i] for i in range(len(path_parts)) if i < len(levels)}

        sorted_items = sorted(meta_data.items(), key=lambda x: int(x[1]['order']))

        # --- Stage 2: Process files ---
        for idx, (index, data) in enumerate(sorted_items):
            file_path = data.get('saved_path') or data.get('stored_path', '')
            if file_path and not os.path.isabs(file_path):
                file_path = os.path.join(config.workdirectories['workdir'], file_path)

            if not os.path.exists(file_path):
                continue

            purpose = data.get('purpose')
            fixlevel = int(data.get('fixlevel', 0)) if data.get('fixlevel') else 0

            # --- DEBUG 2: File Loading ---
            is_ashford_file = "ASHFORD" in file_path.upper()
            if is_ashford_file:
                print(f"🔍 DEBUG [2/5] Ashford File Detected: {os.path.basename(file_path)}")

            if file_path.upper().endswith('.CSV'):
                dfx = pd.read_csv(file_path, sep=None, engine='python', encoding='ISO-8859-1', keep_default_na=False, on_bad_lines='warn')
            elif file_path.upper().endswith('.XLSX'):
                dfx = pd.read_excel(file_path, engine='openpyxl', keep_default_na=False)
            else:
                continue

            # Clean columns
            dfx.columns = [c.encode('ascii', 'ignore').decode('ascii').strip() for c in dfx.columns]

            results = normz(progress, RunningVals, Lookups, data.get('election'), file_path, dfx, fixlevel, purpose)
            temp_df = pd.DataFrame(results[0])
            DQstatslist.append(results[1])

            if is_ashford_file:
                print(f"   > Rows in raw file: {len(dfx)}")
                print(f"   > Rows surviving 'normz': {len(temp_df)}")

            if purpose == 'main': mainframes.append(temp_df)
            elif purpose == 'delta': deltaframes.append(temp_df)
            elif purpose == 'avi': aviframes.append(temp_df)
            elif purpose == 'pledge': pledge_frames.append(temp_df)

        # --- Combine Electoral Roll ---
        all_new = mainframes + deltaframes
        if not all_new:
            progress.update({"percent": 100, "status": "error", "message": "No valid electoral files"})
            return

        new_df = pd.concat(all_new, ignore_index=True)

        # Apply Context Hierarchy
        for i, value in enumerate(path_parts):
            if i < len(levels):
                new_df[levels[i]] = value

        # --- DEBUG 3: Post-Context & Pledge Check ---
        print(f"🔍 DEBUG [3/5] Pre-Deduplication State:")
        print(f"   > Total rows in new_df: {len(new_df)}")
        # Check if any row has Ashford in any column
        ashford_hits = new_df.astype(str).apply(lambda x: x.str.contains('ASHFORD', case=False)).any(axis=1).sum()
        print(f"   > Rows containing 'Ashford' string: {ashford_hits}")

        # --- Stage 4: Merge with Existing & Deduplicate ---
        existing_all = pd.concat(electors.elections.values(), ignore_index=True) if electors.elections else pd.DataFrame()
        new_df['is_new_import'] = True
        if not existing_all.empty:
            existing_all['is_new_import'] = False

        combined = pd.concat([existing_all, new_df], ignore_index=True)

        pre_dedupe_count = len(combined)
        if 'ENOP' in combined.columns:
            # Check for blank ENOPs which cause massive data loss in dedupe
            blanks = (combined['ENOP'] == "").sum()
            if blanks > 1:
                print(f"⚠️ WARNING: Found {blanks} blank ENOPs. These will be merged into ONE record.")
            combined = combined.drop_duplicates(subset='ENOP', keep='last')

        # --- DEBUG 4: Deduplication Impact ---
        print(f"🔍 DEBUG [4/5] Deduplication Results:")
        print(f"   > Rows before dedupe: {pre_dedupe_count}")
        print(f"   > Rows after dedupe: {len(combined)}")

        # --- Stage 5: Assignment ---
        new_only_df = combined[combined['is_new_import'] == True].copy()

        print(f"🔍 DEBUG [5/5] Spatial Assignment (Point-in-Polygon):")
        print(f"   > Handing {len(new_only_df)} records to 'assign_areas'...")

        assigned_df = assign_areas(new_only_df, resolved_levels, progress=progress)

        teamsize = int(CElection.get('teamsize', 5))
        max_walk_size = CElection.get('walksize', 300)

        assigned_df = assign_walks_and_zones(
            assigned_df,
            teamsize,
            territory_path,
            resolved_levels,
            state.selprefix(current_election),
            max_walk_size=max_walk_size,
            max_depth=10,
            progress=progress
        )


        # Save
        electors.add_or_update(current_election, assigned_df)
        electors.save()
        assigned_df.to_csv("zonedelectors.csv", sep='\t', encoding='utf-8', index=False)

        update_progress(progress, "assign_walks", 1.0, "All stages complete.")
        progress['status'] = 'complete'

    except Exception as e:
        print("❌ Exception:", e)
        print(traceback.format_exc())
        progress.update({"percent": 100, "status": "error", "message": str(e)})

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

    def get_stream_table():
        if isinstance(stream_table, dict):
            return pd.DataFrame.from_dict(stream_table, orient='index')
        return pd.DataFrame(stream_table)

    print(f"____retrieving table: {table_name} for node: {current_node.value}")
    # Mapping table names to functions
    table_map = {
        "DQstats": get_report_table,
        "resources": get_resources_table,
        "places": get_places_table,
        "stream_table": get_stream_table
    }

    # Handle dynamic tables like _layer or _xref
    if table_name.endswith("_layer"):
        tabtype = table_name.removesuffix("_layer")
        lev = parent_level_for(tabtype)
        tabnode = current_node.findnodeat_Level(lev)
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
app = Flask(__name__, static_url_path='/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/static')

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
    from state import Treepolys, Fullpolys, Geo_index

    if not request.is_json:
        return jsonify(status="error", message="JSON required"), 415

    restore_from_persist(Treepolys, Fullpolys, Geo_index)

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

        parent.create_area_map(rlevels, static=False)

        CElection.visit_node(parent)

        save_nodes(TREKNODE_FILE)
        persist(Treepolys, Fullpolys, Geo_index)

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
    from nodes import TreeNode
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
    from state import Treepolys, Fullpolys, Geo_index
    restore_from_persist(Treepolys, Fullpolys, Geo_index)

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
        old_parent_node.create_area_map(rlevels, static=False)
        new_parent_node.create_area_map(rlevels, static=False)

        # Persist AFTER successful mutation
        persist(Treepolys, Fullpolys, Geo_index)

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
    print(f" under {route()} user_id: {user_id} ")
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
    print(f" under {route()} users: {users} ")
    return jsonify(users)



@app.route('/updateResourcing', methods=['POST'])
@login_required
def update_walk():

    from elector import electors
    global layeritems


    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
    data = request.json
    walk_name = data.get('walkName')
    new_resource = data.get('newResource')

    idx = allelectors[allelectors['walkName'] == walk_name].index
    if not idx.empty:
        allelectors.at[idx[0], 'Resource'] = new_resource
        persist(Treepolys, Fullpolys, Geo_index)
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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels
    Territory_node = current_node.ping_node(rlevels,CElection['territory'], create=True, accumulate=False)

    areaelectors = electors.elector_for_path(rlevels,Territory_node.mapfile())


    if not mask.any():
        print(f"WalkName '{walk_name}' not found in area '{Territory_node.value}'")
        return jsonify(success=False, error="WalkName not found"), 404

    # Update Kanban status
    allelectors.loc[mask, 'Kanban'] = new_kanban
    print(f"Updated WalkName '{walk_name}' to KanBan '{new_kanban}' for {mask.sum()} rows.")

    persist(Treepolys, Fullpolys, Geo_index)

    return jsonify(success=True)

@app.route('/telling')
@login_required
def telling():
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
    # Check if ENOP exists in the DataFrame
    if enop in allelectors['ENOP'].values:
        # Get the current Tags for the ENOP
        current_tags = allelectors.loc[allelectors['ENOP'] == enop, 'Tags'].iloc[0]

        # If "M1" is not in the current Tags, add it
        if "M1" not in current_tags.split():
            current_tags = f"{current_tags} M1".strip()
            allelectors.loc[allelectors['ENOP'] == enop, 'Tags'] = current_tags
            persist(Treepolys, Fullpolys, Geo_index)
        return jsonify({'exists': True, 'message': f'ENOP found, M1 tag added. Current Tags: {current_tags}'})
    else:
        return jsonify({'exists': False, 'message': 'ENOP not found in electors.'})

# Backend route to search for street names (filter on frontend for faster search)
def area_search(query, df, search_type):
    """
    Filters for unique street/area combinations.
    """
    if df.empty or not query:
        return []

    # Map the search type to the primary column
    col = "StreetName" if search_type == "street" else "WalkName"

    if col not in df.columns:
        return []

    # 1. Filter rows by the query (case-insensitive)
    mask = df[col].str.contains(query, case=False, na=False)
    matches = df[mask]

    # 2. Group by BOTH the target column and the Area column to get unique pairs
    # This handles "High Street" in Ward A vs "High Street" in Ward B
    unique_pairs = matches.groupby([col, 'Area']).size().reset_index()

    results = []
    for _, row in unique_pairs.iterrows():
        name_val = str(row[col])
        area_val = str(row['Area'])

        results.append({
            "name": name_val,
            "area": area_val,
            "display_name": f"{name_val} ({area_val})" # e.g. "HIGH STREET (SURREY HEATH)"
        })

    # Sort alphabetically by the display name
    return sorted(results, key=lambda x: x['display_name'])


@app.route('/update_location_tags', methods=['POST'])
@login_required
def update_location_tags():
    from elector import electors # Import the manager instance

    data = request.get_json()
    l_type = data.get('location_type')
    l_name = data.get('location_name')
    l_area = data.get('location_area') # New parameter
    delivery_tag = data.get('tag')

    col = "StreetName" if l_type == "street" else "WalkName"

    current_election = CurrentElection.get_lastused()
    master_df = electors.get(current_election)

    # 🚨 THE CRITICAL SYNC: Filter by both Name AND Area
    mask = (master_df[col].astype(str).str.upper() == str(l_name).upper()) & \
           (master_df['Area'].astype(str).str.upper() == str(l_area).upper())

    affected_indices = master_df[mask].index

    updated_count = 0
    for idx in affected_indices:
        current_tags = str(master_df.at[idx, 'Tags']) if pd.notna(master_df.at[idx, 'Tags']) else ""
        tags_list = current_tags.split()

        if delivery_tag not in tags_list:
            tags_list.append(delivery_tag)
            # Update the manager's internal dataframe
            electors._elections[current_election].at[idx, 'Tags'] = ' '.join(tags_list)
            updated_count += 1

    # 4. Save the changes to the TSV/CSV file
    if updated_count > 0:
        electors.save()
        electors.rebuild_combined() # Keep memory in sync

    return jsonify({
        'message': f'Success: {updated_count} electors in {location_name} tagged with {delivery_tag}.'
    })

@app.route('/locationsearch')
@login_required
def location_search():
    from elector import electors
    from elections import CurrentElection

    # 1. Get Context
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

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
    from state import Treepolys, Fullpolys

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
    allelectors = electors.elector_for_path(rlevels,current_node.mapfile())

    # SAFETY: Check if we have any data before proceeding
    if allelectors is None or allelectors.empty:
        return jsonify({'columns': [], 'data': []})

    # Optional: ensure we have persistence if data exists
    restore_from_persist(Treepolys, Fullpolys, Geo_index)

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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
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
    current_node = CElection.get_last_node(create=False)

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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
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


    from state import Treepolys, Fullpolys, Geo_index


    fixed_path = ELECTOR_FILE  # Set your path
    print("____Route/Reset-Election")

    if not fixed_path or not os.path.exists(fixed_path):
        return jsonify({'message': 'Elections reset unnessary - no election data '}), 404

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    arch_path = fixed_path.replace(".csv", "-ARCHIVE.csv")
    allelectors.to_csv(arch_path,sep='\t', encoding='utf-8', index=False)
    formdata = {}

    print("trying to reset elections at node:", current_node.value)
    if not GENESYS_FILE or not os.path.exists(GENESYS_FILE):
        return jsonify({'message': 'Elections reset unnessary - no election data '}), 404
    allelectors = pd.read_excel(GENESYS_FILE)
    allelectors.drop(allelectors.index, inplace=True)

    persist(Treepolys, Fullpolys, Geo_index)
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
    current_node = CElection.get_last_node(create=False)

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
                election_node = current_node.ping_node(rlevels,territory_path, create=True,accumulate=session.get("accumulate", False))
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
    current_node.create_area_map(rlevels, static=False)
    reportdate = datetime.strptime(str(date.today()), "%Y-%m-%d").strftime('%d/%m/%Y')

    return render_template("election_report.html", reportdate=reportdate, mapfile=reportfile, report_data=report_data)


@app.route("/set-election", methods=["POST"])
@login_required
def set_election():
    from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
    from state import Treepolys, Fullpolys, Geo_index, ensure_treepolys_with_index
    from flask import session

    try:
        print("____Route/set-election/top ")
        session.pop("accumulated_nodes", None)
        session["accumulate"] = False
#        clear_treepolys()  # 🔥 FULL RESET
        restore_from_persist(Treepolys, Fullpolys, Geo_index)
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
        territory = CElection['territory']
        lastfilepath = CElection['mapfiles'][-1]
        print(f"____Route/set-election- breadcrumb: {lastfilepath}, territory:{territory}")

        here = (CElection.get('cidLat',None),CElection.get('cidLong',None))


        lastfilepath, Geo_index = ensure_treepolys_with_index(
            territory=territory,
            sourcepath=lastfilepath,
            here=here,
            resolved_levels=rlevels,
            parent_levels= plevels
        )

        # At the start of a fresh election:
        print(f"____Route/set-election- path: {lastfilepath},Loaded election: {current_election} CE data: {CElection}")

        current_node = nodes.MapRoot.ping_node(rlevels,lastfilepath, create=True, accumulate=session.get("accumulate", False)) # go to the first node

        print(f"____Route/set-election- last node: {current_node.value},Loaded election: {current_election}")
        CElection['previousParty'] = current_node.party

        if not current_node:
            return jsonify(success=False, error="No current node for election"), 500

        created, totalleaf = current_node.endpoint_created(rlevels, lastfilepath, static=False)

        options = resolve_ui_context(ProgramContext(),ElectionContext(CElection), current_node)
        constants = CElection
        print(f"____Route/set-election- post resolve {current_node.value} Loaded election: {current_election} ")

        if not CElection.visit_node(current_node):
            flash("That node is outside of the election Territory")
            print("That node is outside of the election Territory:")
        persist(Treepolys, Fullpolys, Geo_index)
        print(f"____Route/set-election/results {constants}, options: {options}")

        return jsonify({'success':True,
                'constants': constants,
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
    from state import Treepolys, Fullpolys, Geo_index
    # received a call to return election data constants and options

    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = request.args.get("election")

    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
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
    current_node = CElection.get_last_node(create=False)

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
    from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
    from state import Treepolys, Fullpolys, Geo_index
    from elections import CurrentElection

    restore_from_persist(Treepolys, Fullpolys, Geo_index)

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

    restore_from_persist(Treepolys, Fullpolys, Geo_index)
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

        persist(Treepolys, Fullpolys, Geo_index)
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
    current_node = CElection.get_last_node(create=False)


    return jsonify(success=True, electiontabs_html=electiontabs_html)


@app.route("/add-election", methods=["POST"])
@login_required
def add_election():

    restore_from_persist(Treepolys, Fullpolys, Geo_index)

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
    current_node = CElection.get_last_node(create=False)

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
    current_node = CElection.get_last_node(create=True)
    rlevels = CElection.resolved_levels
    # mapfiles last entry is what we need to bookmark.


    CElection['territory'] = mapfile

    created, totalleaf = current_node.endpoint_created(rlevels, mapfile,static=False)

    CElection.save()
    print(f"______election:{current_election} Bookmarks : {CElection['mapfiles']} Updated-territory: {current_node.mapfile()}")

    return jsonify(success=True, constants=CElection)

@app.route("/get_streamrag")
@login_required
def get_streamrag():
    """
    Endpoint to return the current stream processing RAG data.
    """
    # Get all current election instances
    elections_list = CurrentElection.get_all()  # returns a list of CurrentElection instances

    # Build a dict of {election_name: CurrentElection_instance} for getstreamrag
    elections_dict = {e.name: e for e in elections_list}

    # Call the class method, passing the elections dictionary and the ElectorManager instance
    rag_data = CurrentElection.getstreamrag(elections_dict, electors)

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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

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


from flask import render_template, flash, session
from elector import ElectorManager
from elections import CurrentElection
from baked_data import baked_data

@app.route("/", methods=['POST', 'GET'])
def index():
    global streamrag
    global TABLE_TYPES
    global constants

    ELECTIONS = get_available_elections()  # This seems to be a function fetching available elections

    if 'username' in session:
        flash("__________Session Alive:" + session['username'])
        print("__________Session Alive:" + session['username'])
        formdata = {}

        # Fetch the stream processing status using the new method
        electors = ElectorManager()  # Make sure the ElectorManager instance is initialized
        streamrag = electors.getstreamrag()  # This is your new way of getting stream processing data

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

        # Restore the persisted state (treepolys, fullpolys)
        restore_from_persist(Treepolys, Fullpolys, Geo_index)
        BAKED_DATA = baked_data.load()
        # Load the current election context
        current_election = CurrentElection.get_lastused()
        CElection = CurrentElection.load(current_election)
        resolved_levels = CurrentElection.resolved_levels

        assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

        # The clean unpack you like
        (c_election, elevels), = resolved_levels.items()

        current_node = CElection.get_last_node(create=False)

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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

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
        created, totalleaf = current_node.endpoint_created(rlevels,current_node.mapfile(),static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" Route/dashboard File not found: {fullpath}")
            print (f"_________ROUTE/dashboard at {current_node.value} display file created:{fullpath}")

        if not CElection.visit_node(current_node):
            flash("That node is outside of the election Territory")
            print("That node is outside of the election Territory:")
        persist(Treepolys, Fullpolys, Geo_index)

        print (f"_________ROUTE/dashboard at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)


    flash('_______ROUTE/dashboard no login session ')

    return redirect(url_for('index'))


@app.route('/downbut/<path:path>', methods=['GET','POST'])
@login_required
def downbut(path):
    from state import Treepolys, Fullpolys, Geo_index
    from flask import session
    from elector import electors
    from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
    from elections import CurrentElection
    global layeritems
    global constants


    print("____Route/downbut:", path)

    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    session["current_election"] = current_election
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node( create=True)
    session["current_node_id"] = current_node.nid

    rlevels = CElection.resolved_levels

# a down button on a node has been selected on the map, so the new map must be displayed with new down options
    session['current_election'] = current_election
    session['current_node_id'] = current_node.nid
    previous_node = current_node
    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(rlevels,path, create=True, accumulate=session.get("accumulate", False))


    if current_node.level > 4 and len(areaelectors)  == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}" )
        raise Exception ("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()
        created, totalleaf = current_node.endpoint_created(rlevels,current_node.mapfile(),static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" Route/downbut File not found: {fullpath}")
            print (f"_________ROUTE/downbut at {current_node.value} display file created:{fullpath}")

        if not CElection.visit_node(current_node):
            flash("That node is outside of the election Territory")
            print("That node is outside of the election Territory:")
        persist(Treepolys, Fullpolys, Geo_index)

        print (f"_________ROUTE/downbut at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)

@app.route('/downbulk', methods=['POST'])
@login_required
def downbulk():
    from state import Treepolys, Fullpolys, Geo_index
    from nodes import TREK_NODES_BY_ID
    from flask import request, session, jsonify
    from pathlib import Path
    import config

    print("\n" + "="*40)
    print("🚀 ENTERING ROUTE: /downbulk")
    print("="*40)

    # 1. Get the list of NIDs from the request body
    data = request.json
    nids = data.get('nids', [])
    print(f"📦 Payload received: {len(nids)} NIDs")
    print(f"🔍 Raw NID list: {nids}")

    if not nids:
        print("❌ ERROR: No NIDs provided in request.")
        return jsonify({"success": False, "error": "No nodes selected"}), 400

    print("🔄 Restoring state from persist...")
    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    # 2. Convert NIDs to actual Node objects
    nodelist = []
    missing_nids = []
    for nid in nids:
        node = TREK_NODES_BY_ID.get(nid)
        if node:
            nodelist.append(node)
        else:
            missing_nids.append(nid)

    print(f"✅ Successfully resolved {len(nodelist)} Node objects.")
    if missing_nids:
        print(f"⚠️ WARNING: Could not find objects for NIDs: {missing_nids}")

    # 3. Setup Election context
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels
    print(f"🗳️ Election: {current_election} | Resolved Levels: {rlevels}")

    # Set up the context node (The "Parent" container for the render)
    current_node = CElection.get_last_node(create=True)
    print(f"📍 Context Node: {current_node.value} (NID: {current_node.nid})")

    # Update Session
    session['accumulated_nodes'] = nids
    session.modified = True
    print(f"💾 Session updated with 'accumulated_nodes'")

    # 4. ensure all nodes exist
    for node in nodelist:
        get_root().ping_node(rlevels,node.mapfile(), create=True, accumulate=session.get("accumulate", False))
    # 4. Trigger the map creation
    map_filename = nodelist[0].parent.mapfile()
    print(f"🛠️ Triggering endpoint_created for: {map_filename}")

    # We pass the nodelist explicitly to create_layer (if endpoint_created uses it)
    # or ensure current_node knows to render its 'accumulated' children.
    created, totalleaf = nodelist[0].parent.endpoint_created(rlevels, map_filename, static=False)

    print(f"📊 Render Result: Created={created}, Total Leaf Nodes={totalleaf}")

    # 5. File verification
    CElection.visit_node(nodelist[0].parent.parent)
    base = Path(config.workdirectories['workdir'])
    fullpath = base / map_filename

    print(f"📂 Checking for file at: {fullpath}")
    if fullpath.exists():
        print(f"✨ File verified! Size: {fullpath.stat().st_size} bytes")
    else:
        print(f"🚨 ALERT: File does not exist after creation attempt!")

    persist(Treepolys, Fullpolys, Geo_index)
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
    from state import Treepolys, Fullpolys, Geo_index
    from flask import session
    from elector import electors
    from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
    from elections import CurrentElection
    global layeritems
    global constants

    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels
    prev = nodes.TREK_NODES_BY_ID.get(CElection['cid'])

# transfering to another any other node with siblings listed below
# use ping to populate the destination node with which to repaint the screen node map and markers
    current_node = get_root().ping_node(rlevels,path, create=True, accumulate=session.get("accumulate", False))

    created, totalleaf = current_node.endpoint_created(rlevels, current_node.mapfile(),static=False)

    CElection.visit_node(current_node)
    base = Path(config.workdirectories['workdir'])  # or wherever files live
    fullpath = base / current_node.mapfile()
    persist(Treepolys, Fullpolys, Geo_index)
    print (f"_________ROUTE/transfer at sendinf file:{fullpath}")
    return send_file(fullpath, as_attachment=False)




@app.route('/downMWbut/<path:path>', methods=['GET','POST'])
@login_required
def downMWbut(path):
    from state import Treepolys, Fullpolys, Geo_index
    from flask import session
    from elector import electors
    from layers import FEATURE_LAYER_SPECS, ExtendedFeatureGroup
    from elections import CurrentElection
    global layeritems
    global constants


# so this is the button which creates the nodes and map of equal sized walks for the troops

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels
    assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

    # The clean unpack you like
    (c_election, elevels), = rlevels.items()

    print (f"_________ROUTE/downMWbut1 CE {current_election}", current_node.value, path)

    previous_node = current_node
    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())

    # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(rlevels,path, create=True, accumulate=session.get("accumulate", False))

    print (f"_________ROUTE/downMWbut CE {current_election} from: {previous_node.value} to {current_node.value} mapfile: {current_node.mapfile()}")
    flash ("_________ROUTE/downMWbut ")

    if current_node.level > 4 and len(areaelectors)  == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}" )
        raise Exception ("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()

        created, totalleaf = current_node.endpoint_created(rlevels,current_node.mapfile(), static=True)
        if created:
            if not fullpath.exists():
                abort(404, f" Route/downMW File not found: {fullpath}")
            print (f"_________ROUTE/downMW at {current_node.value} display file created:{fullpath}")

        if not CElection.visit_node(current_node):
            flash("That MW node is outside of the election Territory")
            print("That MW node is outside of the election Territory:")
        persist(Treepolys, Fullpolys, Geo_index)

        print (f"_________ROUTE/downMW at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)




@app.route('/STupdate/<path:path>', methods=['GET','POST'],strict_slashes=False)
@login_required
def STupdate(path):
    from state import Treepolys, Fullpolys, Geo_index
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global CElection

    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels
#    steps = path.split("/")
#    filename = steps.pop()
#    current_node = selected_childnode(current_node,steps[-1])
    fileending = "-SDATA.csv"
    if path.find("/PDS/") < 0:
        fileending = "-WDATA.csv"

    session['next'] = 'STupdate/'+path
# use ping to precisely locate the node for which data is to be collected on screen
    current_node = current_node.ping_node(rlevels,path, create=True, accumulate=session.get("accumulate", False))
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
                    changefields.loc[i,'Path'] = street_node.dir+"/"+street_node.file(rlevels)(rlevels)
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
                base_name = current_node.file(rlevels).replace("-PRINT.html",fileending.replace(".html",""))
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
    flash(f"Creating new street/walklegfile:{sheetfile}", "info")
    print(f"Creating new street/walklegfile:{sheetfile}")
    persist(Treepolys, Fullpolys, Geo_index)
    return current_node.render_face(current_election,CElection,True)





@app.route('/PDdownST/<path:path>', methods=['GET','POST'])
@login_required
def PDdownST(path):
    from state import Treepolys, Fullpolys, Geo_index
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global constants


    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)

    rlevels = CElection.resolved_levels
# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers

    areaelectors = electors.elector_for_path(rlevels,path)
    current_node = nodes.MapRoot.ping_node(rlevels,path, create=True, accumulate=session.get("accumulate", False))

    PD_node = current_node

# now pointing at the STREETS.html node containing a map of street markers

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())
    print(f"__PDdownST- lenPD {len(areaelectors)}")
    streetnodelist = PD_node.childrenoftype('street')

    if len(areaelectors) == 0 :
        flash("Can't find any elector data for this Polling District.")
        print("Can't find any elector data for this Polling District.",len(streetnodelist))
        if os.path.exists(current_node.mapfile()):
            os.remove(current_node.mapfile())
    else:
        flash(f"________in {PD_node.value} there are {len(streetnodelist)} streetnode and markers added")
        print(f"________in {PD_node.value} there are {len(streetnodelist)} streetnode and markers added")

    for street_node in streetnodelist:
        mask3 = areaelectors['StreetName'] == street_node.value
        streetelectors = areaelectors[mask3]
        print("____Street node value",street_node.value)
        print(f"Streetelectors PDelectors {len(areaelectors)} streetnodes{len(streetnodelist)} and data {len(streetelectors)} ")
        street_node.create_streetsheet(current_election,rlevels,streetelectors)

#           only create a map if the branch does not already exist

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file(rlevels))


    print(f"__PDdownST- {current_node.mapfile()}-l4area {current_node.value}, len area {len(areaelectors)}")

    print ("_________ROUTE/PDdownST/",path, request.method)

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    if current_node.level > 4 and len(areaelectors)  == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}" )
        raise Exception ("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()

        created, totalleaf = current_node.endpoint_created(rlevels,current_node.mapfile(),static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" Route/PDdownST at level {current_node.level} File not found: {fullpath}")
            print (f"_________ROUTE/PDdownST at {current_node.value} display file created:{fullpath}")

        if not CElection.visit_node(current_node):
            flash("That street is outside of the election Territory")
            print("That street node is outside of the election Territory:")
        persist(Treepolys, Fullpolys, Geo_index)

        print (f"_________ROUTE/PDdownST at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)

@app.route('/LGdownST/<path:path>', methods=['GET','POST'])
@login_required
def LGdownST(path):
    from state import Treepolys, Fullpolys, Geo_index
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global CElection

    restore_from_persist(Treepolys, Fullpolys, Geo_index)

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels
    T_level = CElection['level']

# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(rlevels,path, create=True, accumulate=session.get("accumulate", False))

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

        PD_node.create_area_map(rlevels, static=False)


    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file(rlevels))


    persist(Treepolys, Fullpolys, Geo_index)

    return current_node.render_face(current_election,CElection,True)



@app.route('/WKdownST/<path:path>', methods=['GET','POST'])
@login_required
def WKdownST(path):
    from state import Treepolys, Fullpolys, Geo_index
    from flask import session
    from elector import electors
    global environment
    global filename
    global layeritems
    global constants

    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels

    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(rlevels,path, create=True, accumulate=session.get("accumulate", False)) # takes to the clicked node in the territory
    session['current_node_id'] = current_node.nid


    walk_node = current_node

    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())

# if there is a selected file , then areaelectors will be full of records
    print("________PDMarker",walk_node.type,"|", walk_node.dir, "|",walk_node.file(rlevels))

    flash("No data for the selected election available!")
    walklegnodelist = walk_node.childrenoftype('walkleg')
    print ("________Walklegs",walk_node.value,len(walklegnodelist))
# for each walkleg node(partial street), add a walkleg node marker to the walk_node parent layer (ie PD_node.level+1)
    for walkleg_node in walklegnodelist:
        mask = areaelectors['StreetName'] == walkleg_node.value
        streetelectors = areaelectors[mask]
        walkleg_node.create_streetsheet(current_election,rlevels,streetelectors)

        walk_node.create_area_map(rlevels, static=False)

    if current_node.level > 4 and len(areaelectors)  == 0:
        flash("Can't find any elector data for this Area.")
        print(f"Can't find elector data at {current_node.value} for election {current_election}" )
        raise Exception ("Can't find any elector data for this Area.")
    else:
        base = Path(config.workdirectories['workdir'])  # or wherever files live
        fullpath = base / current_node.mapfile()

        created, totalleaf = current_node.endpoint_created(rlevels,current_node.mapfile(),static=False)
        if created:
            if not fullpath.exists():
                abort(404, f" _________ROUTE/WKdownST File not found: {fullpath}")
            print (f"_________ROUTE/WKdownST at {current_node.value} display file created:{fullpath}")

        if not CElection.visit_node(current_node):
            flash("That street is outside of the election Territory")
            print("That street node is outside of the election Territory:")
        persist(Treepolys, Fullpolys, Geo_index)

        print (f"_________ROUTE/WKdownST at sendinf file:{fullpath}")
        return send_file(fullpath, as_attachment=False)

@app.route('/wardreport/<path:path>',methods=['GET','POST'])
@login_required
def wardreport(path):

    global layeritems
    global formdata
    global CElection
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels
    session['current_node_id'] = current_node.nid

    flash('_______ROUTE/wardreport')
    print('_______ROUTE/wardreport')

    print("________layeritems  :  ", layeritems)

    i = 0
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+current_node.child_type(rlevels)+" details"
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

    persist(Treepolys, Fullpolys, Geo_index)
    return current_node.parent.render_face(current_election,CElection,False)



# Electtrek.py or routes.py

@app.route("/get_table/<table_name>", methods=["GET"])
@login_required
def get_table(table_name):
    from elections import CurrentElection
    from state import Treepolys, Fullpolys, DQstats, Geo_index
    # Load current election if not provided
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels

    # Determine current node
    current_node = CElection.get_last_node(create=False)

    try:
        print(f"_______ get table {table_name}")
        columns, rows, title = fetch_table(rlevels,table_name, current_node)
        print(f"_______ get table result {columns}* {rows}* {title}")
        return jsonify([columns, rows, title])
    except Exception as e:
        raise ValueError("Table retrieval fails")
        return jsonify({"error": str(e)}), 500


@app.route('/fetch_areas', methods=['POST', 'GET'])
@login_required
def fetch_areas():
    from elections import CurrentElection
    from flask import session
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
    accumulate = session.get("accumulate", False)

    if accumulate:
        node_ids = session.get("accumulated_nodes", [])
        valid_nodes = []

        for nid in node_ids:
            node = nodes.TREK_NODES_BY_ID.get(nid)
            if node and node.parent:   # ensure parent exists
                valid_nodes.append(node)

        nodelist = valid_nodes

    else:
        # Move up to constituency level
        current_node = current_node.findnodeat_Level(3)
        nodelist = [current_node]

    accordion = current_node.get_areas(nodelist=nodelist)

    print(f"_______ Fetch under {current_election} for {current_node.value} Areas {accordion}")
    try:
        json.dumps(accordion)
    except Exception as e:
        print("❌ JSON SERIALIZATION ERROR:", e)
    return jsonify({ "areas": accordion })



@app.route('/displayareas', methods=['POST', 'GET'])
@login_required
def displayareas():
    #calc values in displayed table

    global layeritems
    global formdata

    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
    rlevels = CElection.resolved_levels
    places = CElection['places']
    print(f"____Route/displayareas for {current_node.value} in election {current_election} ")
    if current_election == "DEMO":
        if len(places) > 0:
            formdata['tabledetails'] = "Click for details of uploaded markers, markers and events"
            layeritems = get_layer_table(pd.DataFrame(places) ,formdata['tabledetails'],rlevels)
            print(f" Number of displayed markframe items - {len(places)} ")
        else:
            formdata['tabledetails'] = "No data to display - please upload"
            layeritems = get_layer_table(pd.DataFrame(places),formdata['tabledetails'],rlevels)
    else:
        path = current_node.dir+"/"+current_node.file(rlevels)
        ctype = current_node.child_type(rlevels)

        formdata = current_node.value +current_node.child_type(rlevels)+"s"
        tablenodes = current_node.childrenoftype(ctype)
        if len(tablenodes) == 0:
            if current_node.level > 0:
                ctype = CElection.node_type(current_node.level)
                tablenodes = current_node.parent.childrenoftype(ctype)
            else:
                return jsonify([[], [], "No data"])
        layeritems = get_layer_table(tablenodes ,formdata,rlevels)
        print(f"Display layeritems area {current_node.value} - {ctype} - {len(tablenodes)}")

    if not layeritems or len(layeritems) < 3:
        return jsonify([[], [], "No data"])

    # --- Handle selected tag from request or session
    selected_tag = CElection['Tags']

# Unpack layeritems
    df = layeritems[1].copy()

    # --- 🔥 NEW: Inject NIDs into the DataFrame ---
    # We map the NID from the original tablenodes list onto the DataFrame
    if 'tablenodes' in locals() and len(tablenodes) == len(df):
        df['nid'] = [node.nid for node in tablenodes]
    # ----------------------------------------------

    column_headers = layeritems[0]

    # --- Ensure 'nid' is in the headers but maybe hidden in UI ---
    if "nid" not in column_headers:
        column_headers = list(column_headers) + ["nid"]

    # ... rest of your existing tag logic ...

    column_headers = layeritems[0]
    print(f"___Displayitems selected tag:{selected_tag} column_headers:{column_headers}" )
    title = str(layeritems[2])

    # --- Ensure "tags" column exists and is parsed
    if "tags" not in df.columns:
        df["tags"] = [[] for _ in range(len(df))]

    def parse_tags(val):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return []
        elif isinstance(val, list):
            return val
        return []

    df["tags"] = df["tags"].apply(parse_tags)

    # --- Add 'tags','is_tag_set' column
    column_headers = list(column_headers) + ["tags", "is_tag_set"]


    if selected_tag:
        df["is_tag_set"] = df["tags"].apply(lambda tags: selected_tag in tags)
    else:
        df["is_tag_set"] = False

    if "tags" not in column_headers:
        column_headers.append("tags")
    if "is_tag_set" not in column_headers:
        column_headers.append("is_tag_set")

    # --- Update layeritems for return
    valid_columns = [col for col in column_headers if col in df.columns]
    data_json = df[valid_columns].to_json(orient='records')

    cols_json = json.dumps(column_headers)
    title_json = json.dumps(title)

    print("Final df.columns:", list(df.columns))
    print("Requested column_headers:", column_headers)
    print("Missing in df:", [col for col in column_headers if col not in df.columns])

    return jsonify([
        json.loads(json.dumps(valid_columns)),  # headers
        json.loads(data_json),                  # rows
        title                                   # simple string
    ])

#    return render_template("Areas.html", context = { "layeritems" :layeritems, "session" : session, "formdata" : formdata, "areaelectors" : areaelectors , "mapfile" : mapfile})

@app.route('/divreport/<path:path>',methods=['GET','POST'])
@login_required
def divreport(path):

    global layeritems
    global formdata
    global CElection

    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers

    session['current_node_id'] = current_node.nid

    flash('_______ROUTE/divreport')
    print('_______ROUTE/divreport')

    i = 0
    layeritems = pd.DataFrame()
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+current_node.child_type(rlevels)+" details"
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


    persist(Treepolys, Fullpolys, Geo_index)
    return current_node.parent.render_face(current_election,CElection,False)

@app.route('/upbut/<path:path>', methods=['GET','POST'])
@login_required
def upbut(path):

    from elector import electors
    from state import Treepolys, Fullpolys, Geo_index
    from elections import CurrentElection

    global environment
    global layeritems
    global constants


    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    previous_node = CElection.get_last_node(create=False)

    rlevels = CElection.resolved_levels

    flash('_______ROUTE/upbut',path)
    print('_______ROUTE/upbut',path, previous_node.value)
    trimmed_path = path
    if path.find(" ") > -1:
        dest_path = path.split(" ")
        moretype = dest_path.pop() # take off any trailing parameters
        trimmed_path = dest_path[0]

    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
# for PDs the up button should take you to the -PDS file, for walks the -WALKS file
#

    current_node = previous_node.parent

    base = Path(config.workdirectories['workdir'])  # or wherever files live
    fullpath = base / current_node.mapfile()
# the previous node's type determines the 'face' of the destination node
    atype = CElection.node_type(current_node.level) # destination type
    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""

#    FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html",'walk' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
#    face_file = subending(trimmed_path,FACEENDING[previous_node.type])
#    print(f" previous: {previous_node.value} type: {previous_node.type} current {current_node.value} type: {current_node.type} FACEFILE:{FACEENDING[previous_node.type]}")


    if not os.path.exists(os.path.join(config.workdirectories['workdir'],current_node.mapfile())):

        flash("No data for the selected node available,attempting to generate !")
        print("No data for the selected node available,attempting to generate !")
        current_node.create_area_map(rlevels, static=False)

    print("________chosen node url",current_node.mapfile())
    base = Path(config.workdirectories['workdir'])  # or wherever files live
    fullpath = base / current_node.mapfile()
    created, totalleaf = current_node.endpoint_created(rlevels,current_node.mapfile(),static=False)
    if created:
        if not fullpath.exists():
            abort(404, f" Route/upbut File not found: {fullpath}")
        print (f"_________ROUTE/upbut from {previous_node.value} to endpoint at {current_node.value} display file created:{fullpath}")
    if not CElection.visit_node(current_node):
        flash("That node is outside of the election Territory")
        print("That node is outside of the election Territory:")

    persist(Treepolys, Fullpolys, Geo_index)
    print (f"_________ROUTE/upbut at sendinf file:{fullpath}")
    return send_file(fullpath, as_attachment=False)


#Register user
@app.route('/register', methods=['POST'])
def register():
    flash('_______ROUTE/register')

    username = request.form['username']
    password = request.form['password']
    print("Register", username)
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

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

    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)

    ctype = CElection.node_type(current_node.level)


    # Track used IDs across both existing and new entries
#        places = build_place_lozenges(markerframe)

#        restore_from_persist(Treepolys, Fullpolys, Geo_index)
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



    areas = current_node.get_areas()
    print(f"caldata for {current_node.value} of length {len(areas)} ")

    # share input and outcome tags
    valid_tags = CElection['Tags']
    task_tags, outcome_tags, all_tags = CElection.get_tags()

    print(f"___ Task Tags {valid_tags} Outcome Tags: {outcome_tags} areas:{areas}")
    print(f"🧪 calendar partial level {current_election} - current_node mapfile:{current_node.mapfile()} - OPTIONS html {OPTIONS['areas']}")
    BAKED_DATA = baked_data.load()

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
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
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
    from baked_data import baked_data  # Import your local instance

    print("\n" + "="*60)
    print("📥 [DEBUG] /upload_data route triggered!")
    print("="*60)

    data = request.get_json()
    incoming_events = data.get('events', [])
    file_path = DATA_FILE

    print(f"🔍 [DEBUG] Path to file being read: {os.path.abspath(file_path)}")
    print(f"📦 [DEBUG] Total incoming events received from frontend: {len(incoming_events)}")
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
    current_node = CElection.get_last_node(create=False)
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
    from state import Treepolys, Fullpolys, Geo_index

    global environment

    global formdata
    global layeritems
    global CElection

    flash('_______ROUTE/filelist',filetype)
    print('_______ROUTE/filelist',filetype)
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
    if filetype == "maps":
        return jsonify({"message": "Success", "file": url_for('thru', path=mapfile)})


from flask import jsonify, render_template
import os
import pandas as pd

@app.route('/progress')
@login_required
def get_progress():
    from state import DQstats, progress
    import os

    # -----------------------------
    # Always prepare base response
    response = {
        'election': progress.get('election', ''),
        'percent': progress.get('percent', 0),                # overall 0–100
        'status': progress.get('status', 'idle'),
        'current_stage': progress.get('current_stage', ''),
        'stage_progress': progress.get('stage_progress', 0),  # 0–100 inside stage
        'stages': progress.get('stages', {}),                 # stage fractions
        'message': progress.get('message', ''),
        'targetfile': progress.get('targetfile', ''),
        'dqstats_html': progress.get('dqstats_html', '')
    }

    # ----------------------------------
    # If still running — just return live state
    if progress['status'] != 'complete':

        for key, value in response.items():
            print(f"Progress1-{key} => {value}")

        return jsonify(response)

    # ----------------------------------
    # If complete — load DQ + stream updates

    dq_file_path = os.path.join(
        config.workdirectories['workdir'],
        subending(progress['targetfile'], "DQ.csv")
    )

    if os.path.exists(dq_file_path):
        DQstats = pd.read_csv(
            dq_file_path,
            sep='\t',
            engine='python',
            encoding='utf-8',
            keep_default_na=False,
            na_values=['']
        )

        progress['dqstats_html'] = render_template(
            'partials/dqstats_rows.html',
            DQstats=DQstats
        )
    else:
        progress['dqstats_html'] = ""

    # Force final state
    progress['percent'] = 100
    progress['stage_progress'] = 100
    progress['current_stage'] = 'complete'
    progress['status'] = 'complete'
    progress['message'] = 'Normalization Complete'


    # Update response after completion
    response.update({
        'percent': 100,
        'stage_progress': 100,
        'current_stage': 'complete',
        'status': 'complete',
        'message': 'Normalization Complete',
        'dqstats_html': progress['dqstats_html']
    })


    for key, value in response.items():
        print(f"Progress2-{key} => {value}")

    return jsonify(response)


@app.route('/deactivate_election/<election_name>', methods=['POST'])
@login_required
def deactivate_election(election_name):
    from nodes import save_nodes
    from elections import CurrentElection
    from elector import electors
    from state import Treepolys, Geo_index
    try:
        restore_from_persist(Treepolys, Fullpolys, Geo_index)
        CElection = CurrentElection.load(election_name)
        territory_path = CElection['territory']
        rlevels = CElection.resolved_levels
        print(f" Deactivate after restore: {election_name} path {territory_path} rlevels {rlevels}")
        territory_node = nodes.MapRoot.ping_node(rlevels,territory_path, create=False,accumulate=session.get("accumulate", False))
        print(f" Deactivate : {election_name} node: {territory_node.mapfile()}")

        electors.delete_elector_for_path(rlevels,territory_node.mapfile())

#        electors.deactivate_election(election_name)  # Call the method to deactivate the election
        print(f"Deactivate PRUNING {territory_node.value}")
        prune_subtree(territory_node)
        save_nodes(TREKNODE_FILE)
        persist(Treepolys, Fullpolys, Geo_index )
        return jsonify({"success": True, "message": f"Election {election_name} deactivated successfully."})
    except Exception as e:
        logger.error(f"Error deactivating election {election_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Error deactivating election {election_name}: {str(e)}"}), 500



@app.route('/walks', methods=['POST','GET'])
@login_required
def walks():

    from elector import electors
    from state import Treepolys, Fullpolys, Geo_index
    from baked_data import baked_data


    global streamrag
    global CElection
    global TABLE_TYPES


    global environment
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    resolved_levels = CurrentElection.resolved_levels

    assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

    # The clean unpack you like
    (c_election, elevels), = resolved_levels.items()

    current_node = CElection.get_last_node(create=False)
    flash('_______ROUTE/walks',session)
    BAKED_DATA = baked_data.load()

    if len(request.form) > 0:
        formdata = {}
        formdata['importfile'] = request.files['importfile']
        formdata['electiondate'] = request.form["electiondate"]
        electwalks = prodwalks(current_node,formdata['importfile'], formdata,Treepolys, environment)
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

    from state import Treepolys, Fullpolys, Geo_index
    global CElection
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    CElection = CurrentElection.load(current_election)
    current_node = CElection.get_last_node(create=False)
    rlevels = CElection.resolved_levels
    flash('__ROUTE/Findpostcode')

    pthref = current_node.dir+"/"+current_node.file(rlevels)
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


@app.route('/firstpage', methods=['GET', 'POST'])
@login_required
def firstpage():

    from elector import electors
    from state import Treepolys, Fullpolys, Geo_index, ensure_treepolys_with_index
    global workdirectories
    global environment
    global layeritems
    global streamrag
    global TABLE_TYPES

    import csv
    import json
    import re
    from pathlib import Path
    from baked_data import baked_data


    def clean_text(value):
        """Remove hidden unicode chars and trim whitespace."""
        if value is None:
            return ""

        value = str(value)

        # Remove unicode direction control characters
        value = re.sub(r'[\u202a-\u202e]', '', value)

        # Remove leading/trailing whitespace
        value = value.strip()

        return value


    def clean_mobile(value):
        """Normalise mobile numbers."""
        value = clean_text(value)

        # Remove "M:" prefix if present
        value = value.replace("M:", "").strip()

        # Remove spaces
        value = value.replace(" ", "")

        return value


    def generate_code(firstname, surname, existing_codes):
        """Generate a short unique code like MH or RB1."""
        base = (firstname[:1] + surname[:1]).upper()

        if base not in existing_codes:
            return base

        # Add numeric suffix if needed
        i = 1
        while f"{base}{i}" in existing_codes:
            i += 1

        return f"{base}{i}"


    def convert_csv_to_clean_json(csv_path):
        resources = {}
        existing_codes = set()
        from pathlib import Path

        csv_path = Path(csv_path)
        json_path = csv_path.with_suffix(".json")


        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter="\t")

            for row in reader:
                firstname = clean_text(row.get("Firstname"))
                surname = clean_text(row.get("Surname"))

                if not firstname and not surname:
                    continue  # skip empty rows

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

    convert_csv_to_clean_json(RESOURCE_FILE)


# restore the last used local geometries, location name index, election data
    restore_from_persist(Treepolys, Fullpolys, Geo_index)
    current_election = CurrentElection.get_lastused()
    session["current_election"] = current_election
    CElection = CurrentElection.load(current_election)
    rlevels = CElection.resolved_levels # driven by election type

    assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

    # The clean unpack you like
    (c_election, elevels), = rlevels.items()


    plevels = CElection.parent_levels
    territory = CElection['territory'] # limits election breadcrumbs and caps election geometries
    breadcrumb = CElection['mapfiles'][-1]
    here = (CElection.get('cidLat',None),CElection.get('cidLong',None)) # last breadcrumb lat long
    if not CElection:
        return jsonify(success=False, error="Election not found"), 404

    missing_layer = check_level4_gap(elevels)

    if missing_layer:
        filepath, Geo_index = ensure_treepolys_with_index(
                territory=territory,
                sourcepath= breadcrumb,
                here=here,
                resolved_levels=rlevels,
                parent_levels=plevels
            )
        print(f"____Route/firstpage- path: {filepath},Loaded election: {current_election} CE data: {CElection}")

# nodes - will be restored throught load nodes process in restore_from_persist
# cid should exist so why not just load from last_used_node
    current_node = CElection.get_last_node(create=True)
    session["current_node_id"] = current_node.nid

    program = ProgramContext()            # app-wide possible options
    election_ctx = ElectionContext(CElection)  # election-scoped possible options
    OPTIONS = resolve_ui_context(program,election_ctx,current_node)

    resources = OPTIONS['resources']
    print('_______Node: ', current_node.value)
    areaelectors = electors.elector_for_path(rlevels,current_node.mapfile())
    print('_______areaelectors size: ', len(areaelectors))
    print('_______resources: ', resources)

    print("🔍 Accessed /firstpage")
    print("🧪 current_user.is_authenticated:", current_user.is_authenticated)
    print("🧪 current_user:", current_user)
    print("🧪 current_election:", current_election)
    print("🧪 session keys:", list(session.keys()))
    print("🧪 full session content:", dict(session))
    print("🧪 full CElection content:", CElection)
    print("🧪 Geo_index:", Geo_index)

    flash('_______ROUTE/firstpage')
    print('_______ROUTE/firstpage at :',current_node.value )

    print(f"🧪 current election 1 {current_election} - current_node:{current_node.value}")
    print("____Firstpage Mapfile",current_node.mapfile(), current_node.value)
    atype = current_node.child_type(rlevels)
# the map under the selected node map needs to be configured
# the selected  boundary options need to be added to the layer
    print(f"____/FIRST OPTIONS areas for calendar node {current_node.value} are {OPTIONS['areas']} ")

    print(f"🧪 current election 2 {current_election} - current_node:{current_node.value} - atype:{atype} ")
    current_node.create_area_map(rlevels, static=False)
    print("______First selected node",atype,len(current_node.children),current_node.value, current_node.level,current_node.file(rlevels))


    ELECTIONS = get_available_elections()

    BAKED_DATA = baked_data.load()

#
    print(f"🧪 firstpage level {current_election} - current_node mapfile:{current_node.mapfile()} - OPTIONS html {OPTIONS['areas']}")
    persist(Treepolys,Fullpolys, Geo_index)
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
    from state import Treepolys, Fullpolys, Geo_index
    from baked_data import baked_data


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

@app.route('/save_stream_table', methods=['POST'])
@login_required
def save_stream_table():
    data = request.get_json().get('data', [])

    try:
        # Save to JSON file
        with open(TABLE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        return jsonify({"status": "success", "message": "Data saved successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    except Exception as e:
        # Handle any errors that might occur
        print(f"Error while saving data: {e}")
        return jsonify({"status": "error", "message": str(e)})

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

    # --- Build meta_data expected by background_normalise ---
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
    from state import Geo_index
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


    created, totalleaf = current_node.endpoint_created(rlevels, lastfilepath, static=False)
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
    from state import Treepolys, Fullpolys, Geo_index  # Assuming this is needed for your logic

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
        app.run(debug=True, use_reloader=True)



# 'method' is a function that is present in a file called 'file.py'
