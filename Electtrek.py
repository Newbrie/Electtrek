from canvasscards import prodcards, find_boundary
from walks import prodwalks
#import electwalks, locfilepath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
import config
from config import TABLE_FILE,LAST_RESULTS_FILE,OPTIONS_FILE,ELECTIONS_FILE,TREEPOLY_FILE,GENESYS_FILE,ELECTOR_FILE,TREKNODE_FILE,FULLPOLY_FILE,RESOURCE_FILE, DEVURLS
from normalised import normz
#import normz

from json import JSONEncoder, JSONDecodeError
import pandas as pd
import geopandas as gpd

import numpy as np
from numpy import ceil
import statistics
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import io
import re
from decimal import Decimal
from pyproj import Proj
from flask import Flask,render_template, request, redirect, session, url_for, send_from_directory, jsonify, flash, render_template_string
import os, sys, math, stat, json , jinja2, random
from os import listdir, system
import glob
from markupsafe import escape
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask import json, get_flashed_messages, make_response
from werkzeug.exceptions import HTTPException
from datetime import datetime, timedelta, date
import geocoder

from collections import defaultdict
import requests
import threading
import traceback
import unidecode
from flask import Response
import copy
import json
from geovoronoi import voronoi_regions_from_coords

import locale

import logging
logging.getLogger("pyproj").setLevel(logging.WARNING)


import state
from state import STATICSWITCH,TABLE_TYPES,LEVEL_ZOOM_MAP, LastResults,load_last_results, levelcolours, subending, normalname
import nodes
from nodes import restore_from_persist, persist, gettypeoflevel,parent_level_for, get_last
from layers import Featurelayers
import layers
from elections import get_election_data, get_tags_json, route

locale.setlocale(locale.LC_TIME, 'en_GB.UTF-8')


sys.path
sys.path.append('/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Electtrek.py')
print(sys.path)


def child_type_for(parent_type, estyle):
    LEVEL_INDEX = {
        'country': 0,
        'nation': 1,
        'county': 2,
        'unitary': 2,
        'constituency': 3,
        'ward': 4,
        'division': 4,
        'polling_district': 5,
        'walk': 5,
        'street': 6,
        'walkleg': 6,
        'elector': 7
    }

    if parent_type not in LEVEL_INDEX:
        raise ValueError(f"Unknown parent type: {parent_type}")

    parent_level = LEVEL_INDEX[parent_type]
    child_level = parent_level + 1

    if child_level not in LEVEL_TYPES:
        return None  # no children

    # If estyle defines a preference, use it
    preferred = ESTYLE_CHILD_PREFERENCE.get(estyle, {}).get(child_level)
    if preferred:
        return preferred

    # Otherwise return the first valid child type
    return LEVEL_TYPES[child_level][0]


def get_election_names():
    """
    Scans a directory for files like 'Elections-<name>.json'
    and returns a dict with names as keys.

    Example return: { 'name1': None, 'name2': None }
    """
    election_files = {}
    pattern = re.compile(r'^Elections-(.+)\.json$')

    for filename in os.listdir(os.path.join(config.workdirectories['workdir'],'static','data')):
        match = pattern.match(filename)
        if match:
            name = match.group(1)
            election_files[name] = str(filename)

    return election_files

def lastElection():
    ELECTIONS_DIR = config.workdirectories['workdir']
    """
    Return the most recently accessed election file.
    Fallback: session-stored current election or first available election.
    """
    # 1. Try session first
    last = "DEMO"

    # 2. List elections from filesystem and sort by last access time
    election_files = get_election_names()  # returns list of election names
    print(f"____election files: {election_files}")

    if election_files:
        # map names to full paths
        paths = [os.path.join(ELECTIONS_DIR, f"{name}.json") for name in election_files]
        # filter out missing files just in case
        paths = [p for p in paths if os.path.exists(p)]
        if paths:
            # sort descending by access time
            paths.sort(key=lambda p: os.path.getatime(p), reverse=True)
            latest_name = os.path.splitext(os.path.basename(paths[0]))[0]
            # Override session if latest exists
            last = last or latest_name

    print(f"____last election: {last}")

    return last

def get_current_election(session=None, session_data=None):
    global CurrentElection
# the sourc eof current election mu reflect what the user sees as the active tab or what is in session_data
    try:
        if not session or 'current_election' not in session:
                current_election = lastElection()
                print("/get_election1 data: ",current_election)
                if not current_election:
                    current_election = "DEMO"
        elif not session_data or 'current_election' not in session_data:
                current_election = lastElection()
                print("/get_election2 data: ",current_election)
                if not current_election:
                    current_election = "DEMO"
    except Exception as e:
        current_election = "DEMO"
        print(f"___System error: No session or current_election: {e} in route {route()}")

    """
    Returns the current election from session data.
    """

    if session and 'current_election' in session and session.get('current_election',"DEMO") in ELECTIONS:
        current_election = session.get('current_election',"DEMO")
        print(f"[Main Thread] current_election from session: in route {route()} for:", current_election)
    elif session_data and 'current_election' in session_data and session_data.get('current_election') in ELECTIONS:
        current_election = session_data.get('current_election',"DEMO")
        print(f"[Background Thread] current_election from session_data:in route {route()} for:", current_election)
    else:
        current_election = "DEMO"
        print(f"⚠️ current_election not found in session so using DEMO in route {route()}")

    return current_election



def save_election_data (c_election,ELECTION):
    file_path = ELECTIONS_FILE.replace(".json",f"-{c_election}.json")
    try:
        if  os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print("____Saving Election File:",c_election,"-",file_path)
            with open(file_path, 'w') as f:
                json.dump(ELECTION, f, indent=2)
            print(f"✅ JSON written safely  {ELECTION}")
        else:
            with open(file_path, 'w') as f:
                json.dump(ELECTION, f, indent=2)
            print(f"✅ New Election JSON: {ELECTION}")
    except Exception as e:
        print(f"❌ Failed to write Election JSON: {e}")
    return








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
        print("____pathval param:",pathval,Long,Lat,CurrentElection['importfile'])
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


def getstreamrag():
# if allstreams.csv exists then we have a RAG dataframe, otherwise black - empty
    file_path = ELECTOR_FILE
    print("____getstreamrag entered", file_path)
    rag = {}
    if file_path and os.path.exists(file_path):
        # we have an active pre-loaded set electors, created by one or more streams
        ef = pd.read_csv(file_path,sep='\t', engine='python',encoding='utf-8')
        stream_table = []
        livestreamdash = pd.DataFrame()
        activestreams = []
    # a empty or missing allelectors.csv is a farm waiting to be harvested WHITE circle
    # a empty or missing STREAMS TABLE is a dessert indicated by a BLACK circle
    # deactivated streams are potential streams found in table but not in allelectors are AMBER
    # active streams are streams found in both table AND allelectors indicated by LIMEGREEN
    # deprecated streams are streams with no definition - RED
    # a stream can be deactivated by marking a file and as inactive the set up page.

        ef = pd.DataFrame(ef,columns=['Election', 'ENOP'])
        # we group electors by Election, calculating totals in each election list
        g = {'ENOP':'count' }
        livestreamdash = ef.groupby(['Election']).agg(g)
        livestreamlabels = list(set(ef['Election'].values))
        print("__LIVESTREAMLABELS: ", livestreamlabels)
        rag = {}
        if len(livestreamdash) > 0 and len(livestreamlabels) > 0:
            print("🔍 type of json1:", type(json))
            print(json)
            if os.path.exists(TABLE_FILE):
                with open(TABLE_FILE) as f:
                    stream_table = json.load(f)
    # so we are in business with stream labels - if they are defined as streams in the table and used in elector file
                g = {'filename' : 'count', 'loaded' : 'count'}
                table_df = pd.DataFrame(stream_table)
                print("____we have allelectors and streamtable file :")
                defined_streamlabels = table_df['election'].to_list() #elections are defined
                active_streams = list({x for x in defined_streamlabels if x in livestreamlabels }) # elections are defined and live
                depreciated_streams = [x for x in livestreamlabels if x not in defined_streamlabels] # elections are live but not defined
                deactivated_streams = list({x for x in defined_streamlabels if x not in livestreamlabels}) #elections are defined but not live
                print(f"____actives:{active_streams}, deprec:{depreciated_streams}, deactiv: {deactivated_streams}")

                for election in active_streams:
                    election = str(election).upper()
                    mask = table_df['election'] == election
                    rag[election] = {}
                    rag[election]['Alive'] = True
                    rag[election]['Elect'] = int(livestreamdash.loc[election,'ENOP']) # can do because its been groupby'ed
                    rag[election]['Files'] = rag[election]['Files'] = ', '.join(str(x) for x in table_df.loc[mask, 'order'].dropna().unique())
                    rag[election]['RAG'] = 'limegreen'
                    print("_____Active Streams:",election, active_streams, rag)
                for election in depreciated_streams:
                    election = str(election).upper()
                    mask = table_df['election'] == election
                    rag[election] = {}
                    rag[election]['Alive'] = False
                    rag[election]['Elect'] = 0
                    rag[election]['Files'] = rag[election]['Files'] = ', '.join(str(x) for x in table_df.loc[mask, 'order'].dropna().unique())
                    rag[election]['RAG'] = 'red'
                    print("_____Depreciated Streams:",election, depreciated_streams,rag)
                for election in deactivated_streams:
                    election = str(election).upper()
                    mask = table_df['election'] == election
                    rag[election] = {}
                    rag[election]['Alive'] = False
                    rag[election]['Elect'] = 0
                    rag[election]['Files'] = rag[election]['Files'] = ', '.join(str(x) for x in table_df.loc[mask, 'order'].dropna().unique())
                    rag[election]['RAG'] = 'amber'
                    print("_____Deactivated Streams:",election, deactivated_streams,rag )
            else:
                election = 'NO DATA STREAMS'
                rag[election] = {}
                rag[election]['Alive'] = False
                rag[election]['Elect'] = 0
                rag[election]['Files'] = 0
                rag[election]['RAG'] = 'gray'
                print("_____No Streams defined yet!:",election, rag)
        else:
            election = 'NO LIVE DATA'
            rag[election] = {}
            rag[election]['Alive'] = False
            rag[election]['Elect'] = 0
            rag[election]['Files'] = 0
            rag[election]['RAG'] = 'white'
            print("_____No Active electors file:", election, rag)
    else:
        election = 'NO LIVE DATA'
        rag[election] = {}
        rag[election]['Alive'] = False
        rag[election]['Elect'] = 0
        rag[election]['Files'] = 0
        rag[election]['RAG'] = 'white'
        print("_____No Active electors file:", election, rag)
    return rag

def capped_append(lst, item):
    max_size = 7
    if not isinstance(lst, list):
        return
    lst.append(item)
    if len(lst) > max_size:
        lst.pop(0)  # Remove oldest
    return lst


def visit_node(v_node, c_elect,CurrEL):
    from flask import send_file, abort
    from pathlib import Path
    # Access the first key from the dictionary
    print(f"___under {c_elect} visiting mapfile:", v_node.mapfile())
    CurrEL2 = CurrEL
    CurrEL2['cid'] = v_node.nid
    CurrEL2['cidLat'] = v_node.latlongroid[0]
    CurrEL2['cidLong'] = v_node.latlongroid[1]
    CurrEL2['mapfiles'] = capped_append(CurrEL['mapfiles'], v_node.mapfile())
    save_election_data(c_elect, CurrEL2)

    session['current_election'] = c_elect
    session['current_node_id'] = v_node.nid
    print(f"___under {c_elect} visiting from {CurrEL['mapfiles'][-1]} to mapfile: {CurrEL2['mapfiles'][-1]}")
    print("=== VISIT NODE ===", v_node.mapfile())
    print("current children:",
          [c.value for c in v_node.children])
    estyle = CurrEL['territories']
    mapfile = v_node.mapfile()
    atype = gettypeoflevel(estyle,mapfile, v_node.level+1)
    fullpath = Path(app.config['UPLOAD_FOLDER']) / mapfile
    if not fullpath.is_file():
        print("___map Typemaker:",atype, state.TypeMaker[atype] )
        return redirect(url_for(state.TypeMaker[atype],path=mapfile))
    print("___map Exists:", fullpath)
    return send_file(fullpath, as_attachment=False)




def get_L4area(nodelist, here):
    from state import Treepolys, Fullpolys

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


def add_zone_Level4(teamsize, unzonedelectors):
    walkcolumn = {
        'polling_district': 'PD',
        'walk': 'WalkName',
        'ward': 'Area',
        'division': 'Area',
        'constituency': 'Area'
    }

    print("🧹 Cleaning lat/lon data")
    print(f"✅ {len(unzonedelectors)} walk centroids before cleaning")
    unzonedelectors = unzonedelectors[
        np.isfinite(unzonedelectors['Lat']) & np.isfinite(unzonedelectors['Long'])
    ]
    unzonedelectors = unzonedelectors[
        (unzonedelectors['Lat'].between(-90, 90)) &
        (unzonedelectors['Long'].between(-180, 180))
    ]
    print(f"✅ {len(unzonedelectors)} valid walk centroids after cleaning")

    if unzonedelectors.empty:
        print("❌ No valid coordinates to cluster.")
        return unzonedelectors

    coords = unzonedelectors[['Lat', 'Long']].values
    num_walks = len(coords)
    N = min(teamsize, num_walks)

    print(f"🎯 Clustering {num_walks} walks into {N} zones (teamsize={teamsize})")

    if N > 1:
        kmeans = KMeans(n_clusters=N, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(coords)
        unzonedelectors['Zone'] = [f"ZONE_{label + 1}" for label in labels]

        print("🎨 Assigned zones via KMeans clustering")
        print("___Zone column preview:\n", unzonedelectors[['WalkName', 'Zone']].dropna().head())
    else:
        unzonedelectors['Zone'] = 'ZONE_0'
        print("⚠️ Only one walk — all assigned to ZONE_0")

    return unzonedelectors



def background_normalise(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table):
    from nodes import allelectors, Treepolys, Fullpolys, current_node,formdata, layeritems, progress

    from sklearn.metrics.pairwise import haversine_distances


    def recursive_kmeans_latlon(X, max_cluster_size, MAX_DEPTH=5, depth=0, prefix='K'):
        """
        Recursively cluster a DataFrame with 'Lat' and 'Long' columns using KMeans,
        splitting any clusters larger than max_cluster_size. Skips empty clusters.
        """
        if depth >= MAX_DEPTH:
            logger.info(f"Max depth {MAX_DEPTH} reached at cluster {prefix}, size {len(X)}")
            return {i: f"{prefix}" for i in X.index}

        if len(X) <= max_cluster_size:
            logger.debug(f"Cluster {prefix} is within size limit. Size: {len(X)}")
            return {i: f"{prefix}" for i in X.index}

        # Estimate number of clusters needed to stay under max_cluster_size
        k = min(int(np.ceil(len(X) / max_cluster_size)), len(X))  # Prevent over-splitting
        coords = X[['Lat', 'Long']].values

        logger.info(f"[Depth {depth}] Splitting {len(X)} points into {k} clusters (prefix: {prefix})")

        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(coords)

        label_map = {}
        for i in range(k):
            idx = X.index[labels == i]

            # ✅ Skip clusters with no members
            if len(idx) == 0:
                logger.warning(f"Cluster {prefix}-{i+1} is empty. Skipping.")
                continue

            sub_data = X.loc[idx]
            new_prefix = f"{prefix}-{i+1}"

            logger.debug(f"Cluster {new_prefix} | Size: {len(sub_data)}")

            sub_labels = recursive_kmeans_latlon(
                sub_data,
                max_cluster_size=max_cluster_size,
                MAX_DEPTH=MAX_DEPTH,
                depth=depth + 1,
                prefix=new_prefix
            )
            label_map.update(sub_labels)

        return label_map

    try:

        # Simulate step progress throughout your pipeline
        # All your existing code from the route goes here, replacing request.form/files/session

        # ⚠️ Use `request_form`, `request_files`, and `session_data` instead of Flask globals
        # e.g. replace `request.form` → `request_form`
        # e.g. replace `session['current_node_id']` → `session_data['current_node_id']`



        # Setup logger
        logging.basicConfig(
            filename = "electtrek.log",
            level=logging.INFO,  # or INFO
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        logger = logging.getLogger(__name__)

        # 6. Process metadata for all files in selected stream( does not have to be current election)
        file_index = 0
        mainframes = []
        deltaframes = []
        aviframes = []
        DQstatslist =[]
        mainframe = pd.DataFrame()
        deltaframe = pd.DataFrame()
        aviframe = pd.DataFrame()
        DQstats = pd.DataFrame()

        progress["percent"] = 0
        progress["status"] = "sourcing"
        progress["message"] = "Sourcing data from instruction files ..."


        print("___Route/normalise: ",meta_data.items())
        total = len(meta_data)
        for idx, (index, data) in enumerate(sorted(meta_data.items(), key=lambda x: int(x[1]['order']))):
            progress["percent"] = int((idx / total) * 100)
            progress["status"] = "processing"
            progress["message"] = f"Processing sourced data (file {idx + 1} of {total})..."

            print(f"\nRow index {index} data {data}")

            stream = str(data.get('election', '')).upper()
            ELECTIONS = get_election_names()
            if stream not in ELECTIONS:
                progress["percent"] = 100
                progress["status"] = "error"
                progress["message"] = f"Error: Election '{stream}' not recognized."
                print(progress["message"])
                return

            print(f"___Selected {stream} election and session node id: ", session_data.get('current_node_id',"UNITED_KINGDOM"))
            SelectedElection = get_election_data(stream)  # essential for election specific processing

            order = int(data.get('order'))
            filetype = data.get('type')
            purpose = data.get('purpose')
            try:
                fixlevel = int(data.get('fixlevel', 0))
            except ValueError:
                fixlevel = 0
            file_path = data.get('saved_path') or data.get('stored_path', '')

            print(f"Election: {stream}")
            print(f"Order: {order}")
            print(f"Type: {filetype}")
            print(f"Purpose: {purpose}")
            print(f"Fixlevel: {fixlevel}")
            print(f"File path: {file_path}")

            if not file_path or not os.path.exists(file_path):
                print(f"❌ File path does not exist: {file_path}")
                continue  # skip to next file

            formdata = {}
            ImportFilename = str(file_path)
            print("_____ reading file outside normz",ImportFilename)
            print("🔍 type of json2:", type(json))
            if os.path.exists(TABLE_FILE):
                with open(TABLE_FILE) as f:
                    stream_table = json.load(f)
            else:
                stream_table = []
        # Collect all possible unique stream names for dropdowns
            streams = sorted(set(row['election'] for row in stream_table))
            streamrag = {}
            dfx = pd.DataFrame()

            try:
                if file_path and os.path.exists(file_path):
                    progress["percent"] = 0
                    progress["status"] = "Running"
                    progress["message"] = f"Reading file{file_path}"

                    if file_path.upper().endswith('.CSV'):
                        print("readingCSVfile outside normz", file_path)
                        dfx = pd.read_csv(
                            file_path,
                            sep=',',                   # Use comma as the separator
                            encoding='ISO-8859-1'      # Keep this if needed for special characters
                        )
                    elif file_path.upper().endswith('.XLSX'):
                        print("readingEXCELfile outside normz", file_path)
                        dfx = pd.read_excel(file_path, engine='openpyxl')
                    else:
                        e="error-Unsupported file format"
                        print(e)
                        progress["percent"] = 100
                        progress["status"] = "error"
                        progress["message"] = f"Error: {str(e)}"
                        return
                    if "EventDate" in dfx.columns:
                        dfx["EventDate"] = pd.to_datetime(dfx["EventDate"], errors="coerce")
                    progress["percent"] = 5
                    progress["status"] = "Running"
                    progress["message"] = f"File injested {file_path}"

                else:
                    print("error - File path does not exist or is not provided: ", file_path)
                    progress["percent"] = 100
                    progress["status"] = "error"
                    progress["message"] = f"Error file path: {file_path}"
                    return
            except Exception as e:
                print("error-file access exception:",str(e))
                tb = traceback.format_exc()
                print("❌ Exception in background_normalise:", e)
                print(tb)
                progress["percent"] = 100
                progress["status"] = "error"
                progress["message"] = f"Error: {str(e)}"
                return
    # progress update finished sorting through instructions,  now starting normalisation stream data
            progress["election"] = stream
            progress["status"] = "running"
            progress["percent"] = 0
            progress["message"] = "Starting normalisation..."

    # normz delivers [normalised elector data df,stats dict,original data quality stats in df]
            Outcomes = pd.read_excel(GENESYS_FILE)
            Outcols = Outcomes.columns.to_list()
            if purpose == "main":
            # this is one of the main index files (1+)
                progress["percent"] = 25
                progress["status"] = "running"
                progress["message"] = "Normalising main file :"+ ImportFilename
                results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                temp = pd.DataFrame(results[0],columns=Outcols)
                mainframes.append(temp)
                DQstatslist.append(results[1])
            elif purpose == 'delta':
            # this is one of many changes that may  be applied to the main index
                progress["percent"] = 40
                progress["status"] = "running"
                progress["message"] = "Normalising delta files :"+ImportFilename
                if 'ElectorCreatedMonth' in dfx.columns:
                    dfx = dfx[dfx['ElectorCreatedMonth'] > 0] # extract all new registrations
                    results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                    temp = pd.DataFrame(results[0],columns=Outcols)
                    deltaframes.append(temp)
                    DQstatslist.append(results[1])
                else:
                    progress["percent"] = 60
                    progress["status"] = "completing"
                    progress["message"] = "Normalising delta files :"+ImportFilename
                    print("NO NEW REGISTRATIONS IN DELTA FILE", dfx.columns)
                    results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                    temp = pd.DataFrame(results[0],columns=Outcols)
                    deltaframes.append(temp)
                    DQstatslist.append(results[1])
            elif purpose == 'avi':
            # this is an addition of columns to the main index
                progress["percent"] = 60
                progress["status"] = "running"
                progress["message"] = "Normalising avi file :"+ImportFilename
                results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                temp = aviframe[['ENOP','AV']]
                aviframes.append(temp)
                DQstatslist.append(results[1])
            elif purpose == 'resource':
                progress["percent"] = 60
                progress["status"] = "running"
                progress["message"] = "Normalising resource file ..."
                if os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.CSV'):
                    print("readingCSVfile resources outside normz", file_path)
                    dfx = pd.read_csv(file_path,sep='\t',engine='python',encoding='ISO-8859-1')
                elif os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.XLSX'):
                    print("readingEXCELfile resources outside normz", file_path)
                    dfx = pd.read_excel(file_path, engine='openpyxl')
                required_columns = ['Code','Email','Mobile','Status','Address1', 'Address2', 'Postcode', 'Firstname','Surname']
                if not all(col in dfx.columns.tolist() for col in required_columns):
                    raise ValueError(f"Not all {dfx.columns.tolist()} in {required_columns}")
                print(f"___Resources {len(dfx)} imported: {dfx.columns}")
            elif purpose == 'mark':
                progress["percent"] = 60
                progress["status"] = "running"
                progress["message"] = "Normalising resource file ..."
                if os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.CSV'):
                    print("readingCSVfile markers outside normz", file_path)
                    dfx = pd.read_csv(file_path,sep='\t',engine='python',encoding='ISO-8859-1')
                elif os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.XLSX'):
                    print("readingEXCELfile markers outside normz", file_path)
                    dfx = pd.read_excel(file_path, engine='openpyxl')
                required_columns = ['EventDate','AddressPrefix','Address1','Address2','Postcode','url','Lat','Long']

                if not all(col in dfx.columns.tolist() for col in required_columns):
                    raise ValueError(f"Not all {dfx.columns.tolist()} in {required_columns}")
                print(f"___Markers {len(dfx)} imported: {dfx.columns}")

    # full stream now received - need to apply changes to main

        fullsum = sum(len(x) for x in mainframes + deltaframes + aviframes)

        if fixlevel == 3:
            for DQ in DQstatslist:
                DQstats = pd.concat([DQstats, DQ])

            for i,mf in enumerate(mainframes):
                progress["percent"] = round(((i + 1) / len(mainframes)) * 100, 2)
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised delta files ..."
                print("__Processed main,delta,avi electors:", len(mf), len(deltaframes),len(aviframe), mf.columns)
                mainframe = pd.concat([mainframe, pd.DataFrame(mf)], ignore_index=True)
                len1 = len(mf)
                print("__Processed mainframe electors:", len(mf), mf.columns)


            for i,df in enumerate(deltaframes):
                progress["percent"] = round(((i + 1) / len(mainframes)) * 100, 2)
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised delta files ..."
                print("_____Deltaframe Details:", df)
                for index, change in df.iterrows():
                    print("_____Delta Change Details:", change)
                mainframe = pd.concat([mainframe, pd.DataFrame(df)], ignore_index=True)
                print("__Processed deltaframe electors:", len(df), df.columns)

            for i,af in enumerate(aviframes):
                progress["percent"] = 85
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised avi file ..."
                print(f"____compare merge length before: {len1} after {len(mainframe)}")
                mainframe = mainframe.merge(af, on='ENOP',how='left', indicator=True )
                mainframe = mainframe.rename(columns= {'AV_y': 'AV'})
                af.to_csv("avitest.csv",sep='\t', encoding='utf-8', index=False)
                print("__Processed aviframe:", len(af), af.columns)

            progress["percent"] = 90
            progress["status"] = "running"
            progress["message"] = "Normalised all source files now clustering ..."

            mainframe = pd.DataFrame(mainframe,columns=Outcols)

            current_election = stream
            CurrentElection = get_election_data(current_election)
            current_node = get_last(current_election,CurrentElection)
            print('___persisting file ', ELECTOR_FILE, len(allelectors))
            allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)


            territory_path = CurrentElection['mapfiles'][-1] # this is the node at which the imported data is to be filtered through
            Territory_node = current_node.ping_node(estyle,current_election,territory_path)
            ttype = gettypeoflevel(estyle,territory_path,Territory_node.level)
            #        Territory_node = self
            #        ttype = electtype
            pfile = Treepolys[ttype]
            Territoryboundary = pfile[pfile['FID']== Territory_node.fid]

            print(f"____Territory limited to :{territory_path} for election {current_election}")

            PDs = set(mainframe.PD.values)
            frames = []
            for PD in PDs:
                mask = mainframe['PD'] == PD
                PDelectors = mainframe[mask]
                print(f"__PD: {PD} PDElectors: {len(PDelectors)}")
                PDmaplongx = PDelectors.Long.mean()
                PDmaplaty = PDelectors.Lat.mean()
                print(f"____PD: {PD} Postcode: {PDelectors['Postcode'].iloc[0]} lat: {PDmaplaty}, long: {PDmaplongx} at node:",Territory_node.value, Territory_node.fid)
    # Need to add L4-AREA value - for all PDs - pull together all PDs which are within the area(ward or division) boundary
                spot = Point(float('%.6f'%(PDmaplongx)),float('%.6f'%(PDmaplaty)))

                areatypecolumn = {
                    '-DIVS.html': 'division',
                    '-MAP.html': 'ward',
                    '-WARDS.html': 'ward',
                    '-MAP.html': 'constituency'
                }

                if Territoryboundary.geometry.contains(spot).item():
                    if Territory_node.level == 3:
                        areatype = next(
                            (value for key, value in areatypecolumn.items() if territory_path.endswith(key)),
                            'ward'  # Default if no match found
                            )
                        tpath = territory_path +" "+ areatype
                        Territory_node.ping_node(estyle,current_election,tpath)
                        Area = get_L4area(Territory_node.childrenoftype(areatype),spot)
                    else:
                        Area = Territory_node.value
                        areatype = next(
                            (value for key, value in areatypecolumn.items() if territory_path.endswith(key)),
                            'ward'  # Default if no match found
                            )
                        tpath = territory_path
                    print(f"__New L4 Area:{Area} of type {areatype} at {tpath}")
                    PDelectors['Area'] = Area
                    frames.append(PDelectors)

    # so if there are electors within the area(ward or division) then the Area name needs to be updated
            if len(frames) > 0:
                mainframe = pd.concat(frames)
            mainframe = mainframe.reset_index(drop=True)

            print("____Final Loadable mainframe Areas:",len(mainframe),mainframe['Area'])
        # now generate walkname labels according to a max zone size (electors) defined for the stream(election)

            label_dict = recursive_kmeans_latlon(mainframe[['Lat', 'Long']], max_cluster_size=int(SelectedElection['walksize']), MAX_DEPTH=15)


# ----- Serialise Labels

            newlabels = pd.Series(label_dict)

            unique_label_map = {}
            serial_labels = []

            for raw_label in newlabels:
                label_key = str(raw_label).strip()  # Keep structure; no .replace('-', '')

                if label_key not in unique_label_map:
                    unique_label_map[label_key] = f"K{len(unique_label_map)+1:02}"

                serial_labels.append(unique_label_map[label_key])

            # Convert to Series, matching newlabels index
            serial_label_series = pd.Series(serial_labels, index=newlabels.index)

            # 🔍 Optional: Print the mapping
            print("📌 Unique label mapping (original → serialised):")
            for k, v in unique_label_map.items():
                print(f"   {k} → {v}")

            mainframe["WalkName"] = mainframe.index.map(serial_label_series)
# K2-3-4    mainframe["WalkName"] = mainframe.index.map(newlabels)

# ---- ADD Zones for all Level 4 areas within Level 3 areas in the import

            L4groups = mainframe['Area'].unique()
            print("____L4groups:",len(mainframe),L4groups)

            zonedelectors =pd.DataFrame()
            frames = []
            for L4group in L4groups:
                maskX = mainframe['Area'] == L4group
                L4electors = mainframe[maskX]  # gets only the L4 electors in your ward/division
                print("L4Group {L4group} in {L4groups}:",len(L4electors),L4electors.columns)
                zonedelectors = add_zone_Level4(CurrentElection['teamsize'],L4electors)
                frames.append(zonedelectors)

            if len(frames) > 0:
                zonedelectors = pd.concat(frames)
            zonedelectors.to_csv("zonedelectors.csv",sep='\t', encoding='utf-8', index=False)

            mainframe = zonedelectors.copy()

# -------- Import Data into allelectors
            print("__details of Outcoles and DQstats", Outcols,DQstats)
            DQstats.loc[Outcols.index('WalkName'),'P3'] = 1
            formdata['tabledetails'] = "Electoral Roll File "+ImportFilename+" Details"
            layeritems = get_layer_table(results[0].head(), formdata['tabledetails'])
            print("__concat of DQstats", DQstats)
            DQstats.to_csv(subending(ImportFilename,"DQ.csv"),sep='\t', encoding='utf-8', index=False)

            print(f"__concat of mainframe of length {len(mainframe)}- columns:",mainframe.columns )
            allelectors = pd.concat([allelectors, pd.DataFrame(mainframe)], ignore_index=True)
            allelectors = allelectors.reset_index(drop=True)
            allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

        else:
            print(f"Low fix level {fixlevel} or zero {len(allelectors)} electors to process:")


        print('_______ROUTE/normalise/exit:',ImportFilename, allelectors.columns)
        progress["percent"] = 100
        progress["status"] = "complete"
        progress["targetfile"] = ImportFilename
        progress["message"] = "load complete."

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ Exception in background_normalise:", e)
        print(tb)
        progress["percent"] = 100
        progress["status"] = "complete"
        progress["message"] = f"Error: {str(e)}"

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



from flask_cors import CORS
# ____XXXXX create and configure the app
app = Flask(__name__, static_url_path='/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/static')

CORS(app)  # <-- This enables CORS for all routes

sys.path.append(r'/Users/newbrie/Documents/ReformUK/GitHub/Electtrek')
# Configure Alchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/newbrie/Documents/ReformUK/GitHub/Electtrek/trekusers.db'
app.config['SECRET_KEY'] = 'rosebutt'
app.config['USE_SESSION_FOR_NEXT'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = '/Users/newbrie/Sites'
app.config['APPLICATION_ROOT'] = '/Users/newbrie/Documents/ReformUK/GitHub/Electtrek'
#app.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)
#app.config['SESSION_PROTECTION'] = 'strong'  # Stronger session protection
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True if using HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Try 'None' if cross-origin
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['TESTING'] = False
app.config['SESSION_COOKIE_PATH'] = '/'


# Password used by server to protect files (read from env)
SERVER_PASSWORD = os.environ.get("CAL_PROTECT_PASSWORD", "secret123")


db = SQLAlchemy(app)
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

# add the root nodes.TreeNode to the node tree
nodes.reset_nodes()

# Get al the Elections Names
ELECTIONS = get_election_names()

current_election = lastElection()
CurrentElection = get_election_data(current_election)
print("🔍 Last election data:", CurrentElection)
current_node = get_last(current_election,CurrentElection)
#election constants , nodes, event values are now loaded up
constants = CurrentElection
places =  CurrentElection['places']
print("🔍 constants:", constants)

# the general list of  election data files and proessing streams
stream_table = {}
if  os.path.exists(TABLE_FILE) and os.path.getsize(TABLE_FILE) > 0:
    with open(TABLE_FILE, "r") as f:
        stream_table = json.load(f)

resources = {}
task_tags, outcome_tags = get_tags_json(CurrentElection['tags'])
areas = current_node.get_areas()
# override if RESOURCES_FILE(.csv) exists because it initialises resources if options file deleted
resourcesdf = pd.DataFrame()
if  os.path.exists(RESOURCE_FILE) and os.path.getsize(RESOURCE_FILE) > 0:
    with open(RESOURCE_FILE, 'r', encoding="utf-8") as f:
        resources = json.load(f)
    selectResources = resources
    print("____Resources file read in")
    # need to save to ELECTIONS)


# OPTIONS template

selectedResources = resources

# override if OPTIONS(.json) exists because it contains memorised option for areas, resources and tags data
if  os.path.exists(OPTIONS_FILE) and os.path.getsize(OPTIONS_FILE) > 0:
    with open(OPTIONS_FILE, 'r', encoding="utf-8") as f:
        OPTIONS = json.load(f)
    areas =  current_node.get_areas()
    task_tags, outcome_tags =  get_tags_json(CurrentElection['tags'])
    resources = OPTIONS['resources']

# eventually extract calendar areas directly from the associated MAP

def find_children_at(level):
    [x.value for x in current_node.childrenoftype('walk')]
    return dropdownlist

areaoptions = ["UNITED_KINGDOM/ENGLAND/SURREY/SURREY_HEATH/SURREY_HEATH-MAP.html"]

# save all places, resources in a new options file
with open(OPTIONS_FILE, 'w') as f:
    json.dump(OPTIONS, f, indent=2)

IGNORABLE_SEGMENTS = {"PDS", "WALKS", "DIVS", "WARDS"}

FILE_SUFFIXES = [
    "-PRINT.html", "-MAP.html","-CAL.html", "-WALKS.html",
    "-ZONES.html", "-PDS.html", "-DIVS.html", "-WARDS.html"
]

from state import LEVEL_ZOOM_MAP



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
mapfile = ""


load_last_results()


print("_________HoC Con Results data:", len(LastResults["constituency"]))
print("_________HoC Ward Results data:", len(LastResults["ward"]))
print("_________HoC Division Results data:", len(LastResults["division"]))


from jinja2 import Environment, FileSystemLoader
templateLoader = jinja2.FileSystemLoader(searchpath=config.workdirectories['templdir'])
environment = jinja2.Environment(loader=templateLoader,auto_reload=True)



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


@app.route('/reassign_parent', methods=['POST'])
@login_required
def reassign_parent():
    """
    Reassigns a node from one parent to another in the tree.
    Updates TREK_NODES_BY_ID, allelectors, and regenerates relevant maps.
    """
    global OPTIONS, constants

    print(">>> /reassign_parent called")

    # Restore persisted state
    restore_from_persist(session)
    print("✔ Restored from persist")

    # Get current election and settings
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election, CurrentElection)
    print(f"✔ Current node: {current_node.value if current_node else 'None'}")

    estyle = CurrentElection['territories']
    print(f"✔ Current election: {current_election}, estyle: {estyle}")

    # Get request data
    data = request.get_json()
    old_parent_name = data['old_parent']
    new_parent_name = data['new_parent']
    subject_name = data['subject']
    print(f"📥 Request to move node '{subject_name}' from '{old_parent_name}' to '{new_parent_name}'")

    # --------------------------
    # 1. Find nodes in tree
    # --------------------------
    def find_nodes(node):
        if node.value == subject_name:
            # Check parent matches old_parent_name
            if node.parent and node.parent.value == old_parent_name:
                parent = node.parent
                grandparent = parent.parent
                if grandparent:
                    new_parent = next((n for n in grandparent.children if n.value == new_parent_name), None)
                    if new_parent:
                        return node, parent, new_parent
            return None
        # Recurse through children
        for child in node.children:
            result = find_nodes(child)
            if result:
                return result
        return None

    nodes = find_nodes(current_node)
    if not nodes:
        print(f"❌ Node '{subject_name}' not found or parents mismatch")
        return jsonify({'status': 'error', 'message': f"Node '{subject_name}' not found"}), 404

    subject_node, old_parent_node, new_parent_node = nodes
    print(f"✔ Found subject node: {subject_node.value}, old parent: {old_parent_node.value}, new parent: {new_parent_node.value}")

    # --------------------------
    # 2. Remove from old parent
    # --------------------------
    # Determine election type for child
    etype = 'ward' if estyle in ("B", "P", "W") else 'division'

    print("=== BEFORE MOVE ===")
    print("Old parent children:",
          [c.value for c in old_parent_node.children])
    print("New parent children:",
          [c.value for c in new_parent_node.children])
    print("Subject parent:",
          subject_node.parent.value if subject_node.parent else None)

    # Reassign parent using set_parent (handles removal, addition, and recompute)
    subject_node.set_parent(new_parent_node)

    print("=== AFTER MOVE ===")
    print("Old parent children:",
          [c.value for c in old_parent_node.children])
    print("New parent children:",
          [c.value for c in new_parent_node.children])
    print("Subject parent:",
          subject_node.parent.value if subject_node.parent else None)

    # Update type if needed
    subject_node.type = etype
    subject_node.election = subject_node.election  # usually already set, but keep consistent

    print(f"✔ Reassigned node '{subject_node.value}' to new parent '{new_parent_node.value}' with etype '{etype}'")

    # --------------------------
    # 4. Update allelectors table
    # --------------------------
    mask_subject = (
        (allelectors['Election'] == current_election) &
        (allelectors['WalkName'] == old_parent_name) &
        (allelectors['StreetName'] == subject_name)
    )

    if mask_subject.any():
        allelectors.loc[mask_subject, 'WalkName'] = new_parent_name
        print(f"✔ Updated allelectors: '{subject_name}' now under '{new_parent_name}'")
    else:
        print(f"⚠ No allelectors rows found for subject '{subject_name}' under old parent '{old_parent_name}'")

    # --------------------------
    # 5. Regenerate maps
    # --------------------------
    # Map files
    mapfile_old_parent = old_parent_node.mapfile()
    mapfile_new_parent = new_parent_node.mapfile()
    mapfile_grandparent = old_parent_node.parent.mapfile() if old_parent_node.parent else None

    for node, mapfile in [
        (old_parent_node, mapfile_old_parent),
        (new_parent_node, mapfile_new_parent),
    ]:
        etype_node = gettypeoflevel(estyle, mapfile, node.level)
        Featurelayers[etype_node].reset()
        Featurelayers[etype_node].create_layer(current_election, node, etype_node)
        node.create_area_map(node.getselectedlayers(estyle, current_election, mapfile),
                             current_election, CurrentElection)
        print(f"🔁 Regenerated map for node '{node.value}'")

    # Regenerate grandparent layer if exists
    if mapfile_grandparent:
        etype_gp = gettypeoflevel(estyle, mapfile_grandparent, old_parent_node.parent.level)
        Featurelayers[etype_gp].create_layer(current_election, old_parent_node.parent, etype_gp)
        old_parent_node.parent.create_area_map(
            old_parent_node.parent.getselectedlayers(estyle, current_election, mapfile_grandparent),
            current_election, CurrentElection
        )
        print(f"🔁 Regenerated map for grandparent '{old_parent_node.parent.value}'")

    # --------------------------
    # 6. Save changes
    # --------------------------
    save_nodes(TREKNODE_FILE)  # persists TREK_NODES_BY_ID and relationships
    visit_node(old_parent_node, current_election, CurrentElection)
    print("✅ Reassignment complete")

    return jsonify({
        'status': 'success',
        'mapfile': url_for('thru', path=mapfile_old_parent),
        'message': f"Node '{subject_name}' reassigned from '{old_parent_name}' to '{new_parent_name}'"
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

    from nodes import allelectors
    global layeritems


    global OPTIONS

    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    data = request.json
    walk_name = data.get('walkName')
    new_resource = data.get('newResource')

    idx = allelectors[allelectors['walkName'] == walk_name].index
    if not idx.empty:
        allelectors.at[idx[0], 'Resource'] = new_resource
        persist(current_node)
        return jsonify(success=True)
    else:
        return jsonify(success=False, error="Walk not found"), 404

@app.route('/kanban')
@login_required
def kanban():
    from nodes import allelectors
    global layeritems


    global areaelectors
    global OPTIONS

# campaign plan is only available to westminster elections at level 3 and others at level 4.
# every election should acquire an election node(ping to its mapfile) to which this route should take you
    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']
    current_node = current_node.ping_node(estyle,current_election,CurrentElection['mapfiles'][-1])
    session['current_node_id'] = current_node.nid
    mask = (allelectors['Election'] == current_election)

    areaelectors = allelectors[mask]
    print("____Route/kanban/AreaElectors shape:", current_election, current_node.value, allelectors.shape, areaelectors.shape, CurrentElection['mapfiles'][-1] )
    print("Sample of areaelectors:", areaelectors.head())
    print("Sample raw Tags values:")
    print(areaelectors['Tags'].dropna().head(10).tolist())
    # Example DataFrame
    df = areaelectors
    gotv = float(CurrentElection['GOTV'])
    turnout = 0.3  # assuming this is between 0–1

    df['VI_Party'] = df['VI'].apply(lambda vi: 1 if vi == CurrentElection['yourparty'] else 0)
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
    mapfile = current_node.mapfile()
    title = current_node.value+" details"
    items = current_node.childrenoftype('walk')
    layeritems = get_layer_table(items,title )
    print("___Layeritems: ",[x.value for x in items] )


    # ✅ Step 1: Define tags of interest
    input_tags = [t for t in CurrentElection['tags'] if t.startswith('L')]
    output_tags = [t for t in CurrentElection['tags'] if t.startswith('M')]
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
        tag_labels=CurrentElection['tags']
    )


@app.route('/update-walk-kanban', methods=['POST'])
@login_required
def update_walk_kanban():
    from nodes import allelectors

    global CurrentElection

    data = request.get_json()
    walk_name = data.get('walk_name')
    new_kanban = data.get('kanban')

    # Check if inputs are valid
    if not walk_name or not new_kanban:
        return jsonify(success=False, error="Missing data"), 400

    # Restore context
    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    Territory_node = current_node.ping_node(estyle,current_election,CurrentElection['mapfiles'][-1])
    mask = (
            (allelectors['Election'] == current_election) &
            (allelectors['WalkName'] == walk_name)
        )
    areaelectors = allelectors[mask]


    if not mask.any():
        print(f"WalkName '{walk_name}' not found in area '{Territory_node.value}'")
        return jsonify(success=False, error="WalkName not found"), 404

    # Update Kanban status
    allelectors.loc[mask, 'Kanban'] = new_kanban
    print(f"Updated WalkName '{walk_name}' to KanBan '{new_kanban}' for {mask.sum()} rows.")

    persist(current_node)

    return jsonify(success=True)

@app.route('/telling')
@login_required
def telling():
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    mask = (allelectors['Election'] == current_election)
    areaelectors = allelectors[mask]
    valid_tags = CurrentElection['tags']
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
    mask = (allelectors['Election'] == current_election)
    areaelectors = allelectors[mask]
    valid_tags = CurrentElection['tags']
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
    global CurrentElection
    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    # Check if ENOP exists in the DataFrame
    if enop in allelectors['ENOP'].values:
        # Get the current Tags for the ENOP
        current_tags = allelectors.loc[allelectors['ENOP'] == enop, 'Tags'].iloc[0]

        # If "M1" is not in the current Tags, add it
        if "M1" not in current_tags.split():
            current_tags = f"{current_tags} M1".strip()
            allelectors.loc[allelectors['ENOP'] == enop, 'Tags'] = current_tags
            persist(current_node)
        return jsonify({'exists': True, 'message': f'ENOP found, M1 tag added. Current Tags: {current_tags}'})
    else:
        return jsonify({'exists': False, 'message': 'ENOP not found in electors.'})

# Backend route to search for street names (filter on frontend for faster search)
def search_streets(query):
    global areaelectors
    street_data = (
        areaelectors[['StreetName']]
        .drop_duplicates()
        .reset_index()  # This keeps the original index in case it's needed
        .rename(columns={'index': 'index'})  # Explicit naming
    )

    street_data['name'] = street_data['StreetName']  # For frontend compatibility

    if query:
        street_data = street_data[
            street_data['name'].str.lower().str.contains(query.lower())
        ]

    return street_data[['name', 'index']].to_dict(orient='records')

def search_walks(query):
    global areaelectors
    walk_data = (
        areaelectors[['WalkName']]
        .drop_duplicates()
        .reset_index()  # This keeps the original index in case it's needed
        .rename(columns={'index': 'index'})  # Explicit naming
    )

    walk_data['name'] = walk_data['WalkName']  # For frontend compatibility

    if query:
        walk_data = walk_data[
            walk_data['name'].str.lower().str.contains(query.lower())
        ]

    return walk_data[['name', 'index']].to_dict(orient='records')



@app.route('/update_location_tags', methods=['POST'])
@login_required
def update_location_tags():
    from nodes import allelectors
    global areaelectors
    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    mask = (allelectors['Election'] == current_election)
    areaelectors = allelectors[mask]

    data = request.get_json()

    location_type = data.get('location_type')  # 'street' or 'walk'
    index = data.get('location_index')
    delivery_tag = data.get('tag')

    if location_type not in ['street', 'walk']:
        return jsonify({'error': 'Invalid location type'}), 400

    if index is None or index < 0:
        return jsonify({'error': 'Invalid index'}), 400

    affected_electors = pd.DataFrame()

    if location_type == 'street':
        if index >= len(areaelectors):
            return jsonify({'error': 'Street index out of range'}), 400
        selected_street = areaelectors.iloc[index]['StreetName']
        affected_electors = areaelectors[areaelectors['StreetName'] == selected_street]
        location_name = selected_street

    elif location_type == 'walk':
        if index >= len(areaelectors):
            return jsonify({'error': 'Walk index out of range'}), 400
        selected_walk = areaelectors.iloc[index]['WalkName']
        affected_electors = areaelectors[areaelectors['WalkName'] == selected_walk]
        location_name = selected_walk

    updated_count = 0

    for idx, row in affected_electors.iterrows():
        current_tags = row.get('Tags', '')
        current_tags_list = str(current_tags).split() if current_tags else []

        if delivery_tag not in current_tags_list:
            current_tags_list.append(delivery_tag)
            allelectors.at[idx, 'Tags'] = ' '.join(current_tags_list)
            updated_count += 1

    persist(current_node)

    return jsonify({
        'message': f'{updated_count} electors in {location_type} "{location_name}" updated with tag "{delivery_tag}".'
    })

@app.route('/locationsearch')
@login_required
def location_search():
    from nodes import allelectors
    global areaelectors
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    mask = (allelectors['Election'] == current_election)
    areaelectors = allelectors[mask]
    query = request.args.get("query", "").strip()
    search_type = request.args.get("type", "street")

    if search_type == "street":
        results = search_streets(query)
        return jsonify(results)

    elif search_type == "walk":
        results = search_walks(query)
        return jsonify(results)

    else:
        return jsonify({'error': 'Invalid search type'}), 400


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
    from nodes import allelectors

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    if len(allelectors) != 0:
        restore_from_persist(session=session)

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'columns': [], 'data': []})

    norm_query = textnorm(query)
    norm_parts = norm_query.split()

    def row_matches(row):
        try:
            haystack = ' '.join([
                textnorm(str(row.Surname)),
                textnorm(str(row.Firstname)),
                textnorm(str(row.StreetName))
            ])
            return all(part in haystack for part in norm_parts)
        except Exception as e:
            print("❌ Error processing row:", e)
            return False

    try:
        print("___Route/search len of allelectors:", len(allelectors))

        matches = allelectors[allelectors.apply(row_matches, axis=1)]

        # Select and clean columns
        trimmed = matches[['Surname', 'Firstname', 'StreetName', 'Postcode', 'Tags', 'ENOP']].copy()
        trimmed = trimmed.fillna('')  # Replace NaN with empty strings

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
        return jsonify({'columns': [], 'data': [], 'error': str(e)}), 500



@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():

    from nodes import allelectors
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
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
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

@app.route('/get_tags')
@login_required
def get_tags():
    global CurrentElection
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    tags = CurrentElection['tags']
    task_tags, outcome_tags =  get_tags_json(CurrentElection['tags'])

    # tags is assumed to be a dict: { "leafletting1": "FirstLeaflet", ... }
    tag_list = [{"code": code, "label": label} for code, label in tags.items()]

    return jsonify(tags=tag_list)


@app.route('/add_tag', methods=['POST'])
@login_required
def add_tag():
    global CurrentElection
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    try:
        data = request.get_json()
        tag = data.get("tag", "").strip()
        label = data.get("label", "").strip()

        if not tag or not label:
            return jsonify({"success": False, "error": "Missing tag or label"}), 400

        tag_exists = tag in CurrentElection['tags']

        if not tag_exists:
            CurrentElection['tags'][tag] = label
            save_election_data(current_election,CurrentElection)

        return jsonify({
            "success": True,
            "exists": tag_exists,
            "tag": tag,
            "label": label
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/streamrag_api')
@login_required
def streamrag_api():
    global streamrag
    from nodes import allelectors
    streamrag = getstreamrag()
    html = render_template('partials/streamtab_rows.html', streamrag=streamrag)
    print("___JSONIFYED streamrag:",streamrag)
    return jsonify({'streamrag':streamrag,'html':html})


#@app.route('/get_streamtab')
#@login_required
#def get_streamtab():
# this refreshes the table in stream_processing html
#    streamrag = getstreamrag()
#    return render_template('partials/streamtab_rows.html', streamrag=streamrag)

@app.route('/deactivate_stream', methods=['POST'])
@login_required
def deactivate_stream():
    # Example: Remove all electors for the given election
    from nodes import allelectors
    election = request.json.get('election')
    ELECTIONS = get_election_names()

    if os.path.exists(TABLE_FILE):
        try:
            with open(TABLE_FILE) as f:
                stream_table = json.load(f)
                stream_table2 = [row for row in stream_table if row.get('stream') != election]
                if len(stream_table) < len(stream_table2):
                    # Save to JSON file
                    with open(TABLE_FILE, 'w') as f:
                        json.dump(stream_table2, f, indent=2)

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500


    if election not in ELECTIONS.keys():
        return jsonify({'status': 'error', 'message': 'Election does not exist','html':html}), 400
    current_election = election
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    delete_path = CurrentElection['mapfiles'][-1]
    estyle = CurrentElection['territories']
    delete_node = current_node.ping_node(estyle,election,delete_path)

    before_count = len(allelectors)
    allelectors = allelectors[allelectors['Election'] != election]
    after_count = len(allelectors)
    print(f"Deactivated election {election}. Removed {before_count - after_count} electors.")

    # remove the  child data nodes under the delete nodes
    ttype = gettypeoflevel(estyle,delete_path,delete_node.level+1)
    Featurelayers[ttype].reset()
    for datanode in delete_node.children:
        delete_node.children.remove(datanode)

    # Optionally persist this change
    allelectors.to_csv(ELECTOR_FILE, sep='\t', index=False, encoding='utf-8')
    streamrag = getstreamrag()
    html = render_template('partials/streamtab_rows.html', streamrag=streamrag)
    print(f"____Deactivate table :{streamrag} in html {html} ")
    return jsonify({'status': 'success', 'election': election,'streamrag':streamrag,'html':html }), 200


@app.route('/reset_Elections', methods=['POST'])
@login_required
def reset_Elections():
    global streamrag
    from nodes import allelectors

    global layeritems
    global DQstats
    global progress


    from state import Treepolys, Fullpolys


    fixed_path = ELECTOR_FILE  # Set your path
    print("____Route/Reset-Election")

    if not fixed_path or not os.path.exists(fixed_path):
        return jsonify({'message': 'Elections reset unnessary - no election data '}), 404

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    arch_path = fixed_path.replace(".csv", "-ARCHIVE.csv")
    allelectors.to_csv(arch_path,sep='\t', encoding='utf-8', index=False)
    formdata = {}

    print("trying to reset elections at node:", current_node.value)
    if not GENESYS_FILE or not os.path.exists(GENESYS_FILE):
        return jsonify({'message': 'Elections reset unnessary - no election data '}), 404
    allelectors = pd.read_excel(GENESYS_FILE)
    allelectors.drop(allelectors.index, inplace=True)

    persist(current_node)
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
    global OPTIONS
    global report_data
    resources = OPTIONS['resources']
    # Define the absolute path to the 'static/data' directory
    elections_dir = os.path.join(config.workdirectories['workdir'], 'static', 'data')
    report_data = []

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']
    reportfile = "UNITED_KINGDOM/ENGLAND/SURREY/SURREY-MAP.html"
    estyle = CurrentElection['territories']
    current_node = current_node.ping_node(estyle,current_election,reportfile)


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
                election_node = current_node.ping_node(estyle,"DEMO",territory_path)
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
    Featurelayers['marker'].create_layer(current_election,current_node,'marker')
#    flash("No marker data for the selected election available!")
    selectedlayers = current_node.getselectedlayers(estyle,current_election,reportfile)
    current_node.create_area_map(selectedlayers, current_election, CurrentElection)
    reportdate = datetime.strptime(str(date.today()), "%Y-%m-%d").strftime('%d/%m/%Y')

    return render_template("election_report.html", reportdate=reportdate, mapfile=reportfile, report_data=report_data)


@app.route("/set-election", methods=["POST"])
@login_required
def set_election():
    global constants, OPTIONS, constants, Treepolys, Featurelayers
    import json


    def make_json_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_serializable(i) for i in obj]
        elif isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        else:
            return str(obj)

    try:
        print("____Route/set-election/top ")

#        clear_treepolys()  # 🔥 FULL RESET
        restore_from_persist(session)
        data = request.get_json(force=True)  # <-- ensure JSON parsing
        print(f"____Route/set-election/data {data} ")

        if not data or "election" not in data:
            return jsonify(success=False, error="No election provided"), 400


        current_election = data["election"]
        session['current_election'] = current_election
        CurrentElection = get_election_data(current_election)
        if not CurrentElection:
            return jsonify(success=False, error="Election not found"), 404

        current_node = get_last(current_election,CurrentElection)

        if not current_node:
            return jsonify(success=False, error="No current node for election"), 500

        estyle = CurrentElection['territories']
        print(f"____Route/set-election/constantsX {current_node.value}, election: {current_election} CE data: {CurrentElection}")

        if not CurrentElection:
            return jsonify(success=False, error="Election not found", current_election=current_election), 404

        CurrentElection['previousParty'] = current_node.party
        mapfile = CurrentElection['mapfiles'][-1]
        print(f"post election load pre- ping: {mapfile}")
        current_node = current_node.ping_node(estyle,current_election, mapfile)
        print(f"post ping: {current_node.mapfile()}")
        persist(current_node)
        visit_node(current_node, current_election, CurrentElection)

        safe_constants = make_json_serializable(CurrentElection)
        return jsonify({
            'success': True,
            'constants': safe_constants,
            'options': OPTIONS,
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
    global OPTIONS

    resources = OPTIONS['resources']

    restore_from_persist(session)
    current_election = request.args.get("election")

    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    target_node = current_node.ping_node(estyle,current_election,CurrentElection['mapfiles'][-1])

    plan = CurrentElection.get("calendar_plan", {})

    # Ensure it always has slots
    if not isinstance(plan, dict):
        plan = {"slots": {}}
    elif "slots" not in plan:
        plan["slots"] = {}

    print("📥 Route current_election/constants:", current_election, CurrentElection)
    return jsonify({"calendar_plan": plan,
            'constants': CurrentElection,
            'options': OPTIONS,
            'current_election': current_election
        })

# POST /current-election
@app.route('/current-election', methods=['POST'])
@login_required
def update_current_election():
    current_election = get_current_election(session=session)
    CurrentElection = get_election_data(current_election)
    estyle = CurrentElection['territories']

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
        CurrentElection['calendar_plan'] = plan
        save_election_data(current_election, CurrentElection)

        print("💾 Saved calendar_plan:", plan)
        return jsonify({"success": True})

    except Exception as e:
        print("🚨 Error in /current-election:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/get-constants', methods=["GET"])
@login_required
def get_constants():
    global OPTIONS
    global CurrentElection
    print("____Route/get_constants" )
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']
    if  os.path.exists(OPTIONS_FILE) and os.path.getsize(OPTIONS_FILE) > 0:
        with open(OPTIONS_FILE, 'r',encoding="utf-8") as f:
            OPTIONS = json.load(f)

    print(f"__get constants for election: {current_election}")
    if not current_election:
        return jsonify({'error': 'Invalid election'}), 400
    print('__constants:', CurrentElection )
    return jsonify({
        'constants': CurrentElection,
        'options': OPTIONS,
        'current_election': current_election
    })


@app.route("/set-constant", methods=["POST"])
@login_required
def set_constant():

    global OPTIONS

    global Featurelayers
    data = request.get_json()
    name = data.get("name")
    value = data.get("value")

    current_election = data.get("election")

    print("____Back End1 election constants update:",current_election,":",name,"-",value)

    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    counters = get_counters(session)

    if name in CurrentElection:
        if name == "ACC":
            OPTIONS['ACC'] = value
            # Assuming you want to reset to 0 for the 1-based indexing logic (0 -> 1)
            for layer_instance in Featurelayers.values():
                layer_instance.reset()
            counters = get_counters(session)


        print("____Back End2:",name,"-",value)
        if name == 'mapfiles':
            move_item(CurrentElection['mapfiles'],int(value),len(CurrentElection['mapfiles']))
        else:
            CurrentElection[name] = value

        save_election_data(current_election,CurrentElection)

        print("____CurrentElection:",current_election)
        return jsonify(success=True)

    return jsonify(success=False, error="Invalid constant name"), 400


@app.route("/delete-election", methods=["POST"])
@login_required
def delete_election():
# delete selected election if not DEMO, then select DEMO as next election
    global formdata

    restore_from_persist(session)
    ELECTIONS = get_election_names()
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

        persist(current_node)
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


    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    with open(OPTIONS_FILE, 'w') as f:
        json.dump(OPTIONS, f, indent=2)

    return jsonify(success=True, electiontabs_html=electiontabs_html)


@app.route("/add-election", methods=["POST"])
@login_required
def add_election():
    global OPTIONS
    global CurrentElection
    restore_from_persist(session)

    # no have Current Election data loaded
    # Load existing elections

    ELECTIONS = get_election_names()

    # Get name for new election
    data = request.get_json()
    new_election = data.get("election")

    session['current_election'] = new_election

    if not new_election or new_election in ELECTIONS:
        return jsonify(success=False, error="Invalid or duplicate election name.")


    current_election = "DEMO"
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']

    mapfile = CurrentElection['mapfiles'][-1]

    CurrentElection['previousParty'] = current_node.party

    print(f"___new_election + CurrentElection: {new_election} + {CurrentElection}")

    # Write updated elections back
    save_election_data(new_election,CurrentElection)

    ELECTIONS = get_election_names()
    print("____ELECTIONS:", ELECTIONS)
    formdata = render_template('partials/electiontabs.html', ELECTIONS=ELECTIONS, current_election=current_election)

    OPTIONS['streams'] = ELECTIONS

    # Optional: set session to the new election
    with open(OPTIONS_FILE, 'w') as f:
        json.dump(OPTIONS, f, indent=2)


    print("election-tabs:",formdata)

    return jsonify({'success': True,
        'constants': CurrentElection,
        'options': OPTIONS,
        'election_name': new_election,
        'electiontabs_html':formdata
    })


@app.route("/last-election")
@login_required
def last_election():
    result = lastElection()
    return jsonify(result)



@app.route("/update-territory", methods=["POST"])
@login_required
def update_territory():

    from nodes import allelectors
    global CurrentElection
    global constants
    global OPTIONS
    data = request.get_json()
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']
    # mapfiles last entry is what we need to bookmark.

    new_path = CurrentElection['mapfiles'][-1]

    current_node = current_node.ping_node(estyle,current_election, new_path)
    mapfile = current_node.mapfile()

    save_election_data(current_election,CurrentElection)
    print(f"______election:{current_election} Bookmarks : {CurrentElection['mapfiles']} Updated-territory: {new_path}")

    return jsonify(success=True, constants=CurrentElection)



@app.route('/validate_tags', methods=['POST'])
@login_required
def validate_tags():

    global CurrentElection
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']
    # Ensure the valid tags list is a list of strings
    tags_data = CurrentElection['tags']
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
    global OPTIONS
    global constants


    ELECTIONS = get_election_names()
    if 'username' in session:
        flash("__________Session Alive:"+ session['username'])
        print("__________Session Alive:"+ session['username'])
        formdata = {}
        streamrag = getstreamrag()
        restore_from_persist(session=session)
        current_election = get_current_election(session)
        CurrentElection = get_election_data(current_election)
        current_node = get_last(current_election,CurrentElection)
        estyle = CurrentElection['territories']
        mapfile = current_node.mapfile()


    #       Track used IDs across both existing and new entries
    #        places = build_place_lozenges(markerframe)

    #        restore_from_persist(session=session)
    #        current_node = get_current_node(session)
    #        CE = get_current_election(session)

        print(f"🧪 Index level {current_election} - current_node mapfile:{mapfile}")

        return render_template(
            "Dash0.html",
            table_types=TABLE_TYPES,
            ELECTIONS=ELECTIONS,
            current_election=current_election,
            options=OPTIONS,
            constants=CElection,
            mapfile=mapfile
        )
    return render_template("index.html")

#login
@app.route('/login', methods=['POST', 'GET'])
def login():

    global streamrag
    global environment
    global layeritems
    global CurrentElection



    if 'gtagno_counters' not in session:
        session['gtagno_counters'] = {}
        # Example: {'marker': 0, 'country': 0, ...}

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    if session.get('username'):
        msg = f"User already logged in: {session['username']} at {current_node.value}"
        flash(msg)
        print("_______ROUTE/Already logged in:", session['username'], "at", current_node.value)
        return redirect(url_for('firstpage'))    # Collect info from forms in the login db
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    print("_______ROUTE/login page", username, user)

    estyle = CurrentElection['territories']
    print("Flask Current time:", datetime.utcnow(), " at ", current_node.value)

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


        session['current_node_id'] = current_node.nid
        if 'next' in session:
            next = session['next']
            print("_______ROUTE/login next found", next)
            return next

        print("_______ROUTE/login User found", username, "at ",current_node.value)

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
                        window.location.href = `/firstpage?lat=${lat}&lon=${lon}`;
                    },
                    function(err) {
                        alert("Location access denied. Using default map.");
                        window.location.href = "/firstpage";
                    }
                );
            } else {
                alert("Geolocation not supported. Using default map.");
                window.location.href = "/firstpage";
            }
        </script>
    </body>
    </html>
    """)



@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    from nodes import TREK_NODES_BY_ID,TREK_NODES_BY_VALUE

    current_node = TREK_NODES_BY_ID.get(session.get('current_node_id',None))

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

    from nodes import allelectors
    global streamrag
    global formdata
    global CurrentElection
    from nodes import TREK_NODES_BY_ID,TREK_NODES_BY_VALUE
    restore_from_persist(session=session)

    current_election = "DEMO"
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    print ("___Route/Dashboard allelectors len: ",len(allelectors))
    if 'username' in session:
        print(f"_______ROUTE/dashboard: {session['username']} is already logged in at {session.get('current_node_id','UNITED_KINGDOM')}")
        formdata = {}
        current_node = TREK_NODES_BY_ID.get(CurrentElection['cid'])
        if not current_node:
            raise Exception ("Current Election node does not exist")
        streamrag = getstreamrag()
        print ("allelectors len after streamrag: ",len(allelectors))
        path = CurrentElection['mapfiles'][-1]
        previous_node = current_node
        print ("____Dashboard CurrentElection: ",path, previous_node.value)
        # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        current_node = previous_node.ping_node(estyle,current_election,path)
        print ("allelectors len after ping: ",len(allelectors))

        mapfile = current_node.mapfile()
        print ("___Dashboard persisted filename: ",mapfile)
        persist(current_node)
        if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
            selectedlayers = current_node.getselectedlayers(estyle,current_election,mapfile)
            current_node.create_area_map(selectedlayers,current_election,CurrentElection)

#        redirect(url_for('captains'))
    return   send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

    flash('_______ROUTE/dashboard no login session ')

    return redirect(url_for('index'))


@app.route('/downbut/<path:path>', methods=['GET','POST'])
@login_required
def downbut(path):
    global formdata
    from state import Treepolys, Fullpolys
    from nodes import allelectors

    global Featurelayers
    global layeritems
    global constants
    global OPTIONS

    print("____Route/downbut:", path)

    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    formdata = {}
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]
# a down button on a node has been selected on the map, so the new map must be displayed with new down options

    previous_node = current_node

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(estyle,current_election,path)

    mapfile = current_node.mapfile()
    print("____Route/downbut:",previous_node.value,current_node.value, mapfile)
    atype = gettypeoflevel(estyle,mapfile,current_node.level+1)
#    FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html",'walk' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
#    current_node.file = subending(current_node.file,FACEENDING[atype]) # face is driven by intention type
    print(f" target type: {atype} current {current_node.value} type: {current_node.type} ")
# the map under the selected node map needs to be configured
# the selected  boundary options need to be added to the layer

    Featurelayers[atype].create_layer(current_election,current_node,atype)
    print(f"____/DOWN OPTIONS areas for calendar node {current_node.value} are {OPTIONS['areas']} ")
    selectedlayers = current_node.getselectedlayers(estyle,current_election,mapfile)
    current_node.create_area_map(selectedlayers,current_election,CurrentElection)
    print(f"_________layeritems for {current_node.value} of type {atype} are {current_node.childrenoftype(atype)} for lev {current_node.level}")
    persist(current_node)
    return visit_node(current_node,current_election,CurrentElection)


#    if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
#        selectedlayers = current_node.getselectedlayers(current_election,mapfile)
#        current_node.create_area_map(selectedlayers,current_election,CurrentElection)

#    if not os.path.exists(config.workdirectories['workdir']+"/"+mapfile):
#    print(f"_____creating mapfile for {atype} map file path :{mapfile} for path:{path}" )

@app.route('/transfer/<path:path>', methods=['GET','POST'])
@login_required
def transfer(path):

    from state import Treepolys, Fullpolys
    from nodes import allelectors
    global Featurelayers
    global environment
    global levels
    global layeritems
    global formdata
    global CurrentElection

    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    formdata = {}
# transfering to another any other node with siblings listed below
    previous_node = current_node

# use ping to populate the destination node with which to repaint the screen node map and markers
    current_node = previous_node.ping_node(estyle,current_election,path)


    mapfile = current_node.mapfile()
    CurrentElection = get_election_data(current_election)
    return visit_node(current_node,current_election,CurrentElection)


@app.route('/downPDbut/<path:path>', methods=['GET','POST'])
@login_required
def downPDbut(path):
    from state import Treepolys, Fullpolys

    global Featurelayers
    from nodes import allelectors
    global areaelectors
    global filename
    global layeritems
    global constants
    global OPTIONS

    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    previous_node = current_node

    estyle = CurrentElection['territories']
    current_node = previous_node.ping_node(estyle,current_election,path) #aligns with election data and takes you to the clicked node
    session['current_node_id'] = current_node.nid
#    current_node.file = subending(current_node.file,"-PDS.html") # forces looking for PDs file

    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]

    mapfile = current_node.mapfile()
    print(f"__downPD- {mapfile}-l4area {current_node.value}, lenAll {len(allelectors)}, len area {len(areaelectors)}")
    PDpathfile = os.path.join(config.workdirectories['workdir'],mapfile)

    print ("_________ROUTE/downPDbut/",path, request.method)
    if request.method == 'GET':

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        if len(areaelectors)  == 0:
            flash("Can't find any elector data for this Area.")
            print(f"Can't find elector data at {current_node.value} for election {current_election}" )
            if os.path.exists(mapfile):
                os.remove(mapfile)
        else:
            print("_____ Before creation - PD display markers ", current_node.level, len(Featurelayers['polling_district']._children))
            Featurelayers['polling_district'].create_layer(current_election,current_node, 'polling_district')
            mapfile = current_node.mapfile()
            print("_______just before create_area_map call:",current_node.level, len(Featurelayers['polling_district']._children), mapfile)
            current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,mapfile),current_election,CurrentElection)
            flash("________PDs added:  "+str(len(Featurelayers['polling_district']._children)))
            print("________After map created PDs added  :  ",current_node.level, len(Featurelayers['polling_district']._children))

#    face_file = subending(current_node.file,"-MAP.html")
#    mapfile = current_node.dir+"/"+face_file
# if this route is from a redirection rather than a service call , then create file if doesnt exist

    if not os.path.exists(PDpathfile):
        print ("_________New PD mapfile/",current_node.value, mapfile)
        Featurelayers[previous_node.type].create_layer(current_election,current_node,previous_node.type) #from upnode children type of prev node
        current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,mapfile),current_election,CurrentElection)
    print("________PD markers After importVI  :  "+str(len(Featurelayers['polling_district']._children)))

    persist(current_node)
    return visit_node(current_node,current_election,CurrentElection)


@app.route('/downWKbut/<path:path>', methods=['GET','POST'])
@login_required
def downWKbut(path):
    from state import Treepolys, Fullpolys

    global Featurelayers
    from nodes import allelectors
    global areaelectors
    global filename
    global layeritems
    global constants
    global OPTIONS

# so this is the button which creates the nodes and map of equal sized walks for the troops
    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    previous_node = current_node
    print (f"_________ROUTE/downWKbut1 CE {current_election}", current_node.value, path)

    estyle = CurrentElection['territories']
    # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(estyle,current_election,path)

#    current_node.file = subending(current_node.file,"-WALKS.html")
 # the node which binds the election data

    mapfile = current_node.mapfile()
    print (f"_________ROUTE/downWKbut2 CE {current_election}",previous_node.value, current_node.value, path)
    flash ("_________ROUTE/downWKbut ")
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]
    walkpathfile = os.path.join(config.workdirectories['workdir'],mapfile)

    if request.method == 'GET':
        if len(areaelectors)  == 0:
            flash("Can't find any elector data for this Area.")
            print(f"Can't find elector data at {current_node.value} for election {current_election}" )
            if os.path.exists(mapfile):
                os.remove(mapfile)
        else:
            print(f"_____ Before creation - Walk display markers at CE {current_election} ",current_node.level, len(Featurelayers['walk']._children))

            Featurelayers['walk'].create_layer(current_election,current_node, 'walk')
            print(f"____/DOWN OPTIONS1 areas for calendar node {current_node.value} are {OPTIONS['areas']} ")
            print(f"____/DOWN OPTIONS2 areas for calendar node {current_node.value} are {Featurelayers['ward'].areashtml} ")
            print(f"____/DOWN OPTIONS3 areas for calendar node {current_node.value} are {Featurelayers['constituency'].areashtml} ")

            print("_______just before Walk create_area_map call:",current_node.level, len(Featurelayers['walk']._children))
            current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,path),current_election,CurrentElection)
            flash("________Walks added:  "+str(len(Featurelayers['walk']._children)))
            print("________After map created Walks added  :  ",current_node.level, len(Featurelayers['walk']._children))

    #            allelectors = getblock(allelectors,'Area',current_node.value)

    if not os.path.exists(walkpathfile):
#        simple transfer from another node -
        print ("_________New WK mapfile/",current_node.value, mapfile)
        Featurelayers[previous_node.type].create_layer(current_election,current_node,'walk') #from upnode children type of prev node
        print(f"____/DOWN OPTIONS21 areas for calendar node {current_node.value} are {OPTIONS['areas']} ")
        print(f"____/DOWN OPTIONS22 areas for calendar node {current_node.value} are {Featurelayers['ward'].areashtml} ")
        print(f"____/DOWN OPTIONS23 areas for calendar node {current_node.value} are {Featurelayers['constituency'].areashtml} ")

    #        current_node.file = face_file
        current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,mapfile),current_election,CurrentElection)

    #    moredata = importVI(allelectors.copy())
    #    if len(moredata) > 0:
    #        allelectors = moredata

        print("________ Walk markers After importVI  :  "+str(len(Featurelayers['walk']._children)))
        print("_______writing to file:", mapfile)

    persist(current_node)
    return visit_node(current_node,current_election,CurrentElection)

@app.route('/downMWbut/<path:path>', methods=['GET','POST'])
@login_required
def downMWbut(path):
    from state import Treepolys, Fullpolys

    global Featurelayers

    global areaelectors
    global filename
    global layeritems
    global constants
    global STATICSWITCH
    global OPTIONS
# so this is the button which creates the nodes and map of equal sized walks for the troops

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    print (f"_________ROUTE/downMWbut1 CE {current_election}", current_node.value, path)

    previous_node = current_node
    # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(estyle,current_election,path)

#    current_node.file = subending(current_node.file,"-WALKS.html")
 # the node which binds the election data

    mapfile = current_node.mapfile()
    print (f"_________ROUTE/downMWbut2 CE {current_election} from: {previous_node.value} to {current_node.value} mapfile: {mapfile}")
    flash ("_________ROUTE/downMWbut ")
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]
    walkpathfile = os.path.join(config.workdirectories['workdir'],mapfile)

    if request.method == 'GET':
        if len(areaelectors)  == 0:
            flash("Can't find any elector data for this Area.")
            print(f"Can't find elector data at {current_node.value} for election {current_election}" )
            if os.path.exists(walkpathfile):
                os.remove(walkpathfile)
        else:
            print(f"_____ Before creation - Static Walk display markers at CE {current_election} ",current_node.level, len(Featurelayers['walk']._children))
            Featurelayers['walk'].create_layer(current_election,current_node, 'walk',static=True)

            print("_______just before Static Walk create_area_map call:",current_node.level, len(Featurelayers['walk']._children))
            STATICSWITCH = True
            current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,path),current_election,CurrentElection)
            STATICSWITCH = False
            flash("________Static Walks added:  "+str(len(Featurelayers['walk']._children)))
            print("________After map created Static Walks added  :  ",current_node.level, len(Featurelayers['walk']._children))

    #            allelectors = getblock(allelectors,'Area',current_node.value)

    if not os.path.exists(walkpathfile):
#        simple transfer from another node -
        print ("_________New MW mapfile/",current_node.value, walkpathfile)
        Featurelayers['walk'].create_layer(current_election,current_node,'walk', static=True) #from upnode children type of prev node

        STATICSWITCH = True
        current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,path),current_election,CurrentElection)
        STATICSWITCH = False
    #    moredata = importVI(allelectors.copy())
    #    if len(moredata) > 0:
    #        allelectors = moredata
        print("________ Static Walk markers After importVI  :  "+str(len(Featurelayers['walk']._children)))
        print("_______writing to file:", walkpathfile)

    persist(current_node)
    return visit_node(current_node,current_election,CurrentElection)


@app.route('/STupdate/<path:path>', methods=['GET','POST'],strict_slashes=False)
@login_required
def STupdate(path):
    from state import Treepolys, Fullpolys


    from nodes import allelectors
    global environment
    global filename
    global layeritems
    global CurrentElection

    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
#    steps = path.split("/")
#    filename = steps.pop()
#    current_node = selected_childnode(current_node,steps[-1])
    fileending = "-SDATA.csv"
    if path.find("/PDS/") < 0:
        fileending = "-WDATA.csv"

    session['next'] = 'STupdate/'+path
# use ping to precisely locate the node for which data is to be collected on screen
    current_node = current_node.ping_node(estyle,current_election,path)
    session['current_node_id'] = current_node.nid
    print(f"____Route/STUpdate - passed target path to: {path}")
    print(f"Selected street node: {current_node.value} type: {current_node.type}")

    street_node = current_node
    mask = (
        (allelectors['Election'] == current_election) &
        (allelectors['StreetName'] == street_node.value)
    )
    streetelectors = allelectors[mask]

    mapfile = current_node.mapfile()

    if request.method == 'POST':
    # Get JSON data from request
#        VIdata = request.get_json()  # Expected format: {'viData': [{...}, {...}]}
        try:
            print(f"📥 Incoming request to update street: {path} (from all {len(allelectors)} in terr {CurrentElection['mapfiles'][-1]}) with source data {len(streetelectors)} ")

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
                    changefields.loc[i,'Path'] = street_node.dir+"/"+street_node.file
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
                            street_node.updateVI(VI_value)
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
                base_name = current_node.file.replace("-PRINT.html",fileending.replace(".html",""))
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

    sheetfile = current_node.create_streetsheet(current_election,streetelectors)
    mapfile = current_node.dir+"/"+sheetfile
    return visit_node(current_node,current_election,CurrentElection)
    flash(f"Creating new street/walklegfile:{sheetfile}", "info")
    print(f"Creating new street/walklegfile:{sheetfile}")
    persist(current_node)
    return  jsonify({"message": "Success", "file": sheetfile})


@app.route('/PDdownST/<path:path>', methods=['GET','POST'])
@login_required
def PDdownST(path):
    from state import Treepolys, Fullpolys

    global Featurelayers

    global areaelectors
    global environment
    global filename
    global layeritems
    global constants
    global OPTIONS

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']
# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(estyle,current_election,path)

    PD_node = current_node

# now pointing at the STREETS.html node containing a map of street markers
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]
    mapfile = PD_node.mapfile()
    mask2 = areaelectors['PD'] == PD_node.value
    PDelectors = areaelectors[mask2]
    print(f"__PDdownST- lenAll {len(allelectors)}, len area {len(areaelectors)} lenPD {len(PDelectors)}")
    if request.method == 'GET':
    # we only want to plot with single streets , so we need to establish one street record with pt data to plot
        Featurelayers['street'].create_layer(current_election,PD_node,'street')

        streetnodelist = PD_node.childrenoftype('street')

        if len(PDelectors) == 0 or len(Featurelayers['street']._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.",len(streetnodelist))
            if os.path.exists(mapfile):
                os.remove(mapfile)
        else:
            flash(f"________in {PD_node.value} there {len(streetnodelist)} streetnode and markers added = {len(Featurelayers['street']._children)}")
            print(f"________in {PD_node.value} there {len(streetnodelist)} streetnode and markers added = {len(Featurelayers['street']._children)}")

        for street_node in streetnodelist:
            mask3 = PDelectors['StreetName'] == street_node.value
            streetelectors = PDelectors[mask3]
            print("____Street node value",street_node.value)
            print(f"Streetelectors PDelectors {len(PDelectors)} streetnodes{len(streetnodelist)} and data {len(streetelectors)} ")
            street_node.create_streetsheet(current_election,streetelectors)

#           only create a map if the branch does not already exist

        PD_node.create_area_map(PD_node.getselectedlayers(estyle,current_election,path),current_election,CurrentElection)
    mapfile = PD_node.mapfile()

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers['street']._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers['street']._children)))
    persist(current_node)

    return visit_node(current_node,current_election,CurrentElection)

@app.route('/LGdownST/<path:path>', methods=['GET','POST'])
@login_required
def LGdownST(path):
    from state import Treepolys, Fullpolys

    global Featurelayers

    global areaelectors
    global environment
    global filename
    global layeritems
    global CurrentElection

    restore_from_persist(session=session)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    T_level = CurrentElection['level']

# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(estyle,current_election,path)

    PD_node = current_node
# now pointing at the STREETS.html node containing a map of street markers
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]
    mask2 = areaelectors['PD'] == PD_node.value
    PDelectors = areaelectors[mask2]
    if request.method == 'GET':
    # we only want to plot with single streets , so we need to establish one street record with pt data to plot
        atype = gettypeoflevel(estyle,path, current_node.level)
        Featurelayers['street'].create_layer(current_election,PD_node,'street')

        flash("No data for the selected election available!")
        flash("Can't find any elector data for this Polling District.")
        print("Can't find any elector data for this Polling District.")
        if os.path.exists(mapfile):
            os.remove(mapfile)
        flash("________streets added  :  "+str(Featurelayers['street']._children))
        print("________streets added  :  "+str(len(Featurelayers['street']._children)))

        streetnodelist = PD_node.childrenoftype('street')
        for street_node in streetnodelist:
            mask = PDelectors['StreetName'] == street_node.value
            streetelectors = PDelectors[mask]
            street_node.create_streetsheet(current_election,streetelectors)

        PD_node.create_area_map(PD_node.getselectedlayers(estyle,current_election,path),current_election,CurrentElection)
    mapfile = PD_node.mapfile()

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers['street']._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers['street']._children)))


    persist(current_node)

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)



@app.route('/WKdownST/<path:path>', methods=['GET','POST'])
@login_required
def WKdownST(path):
    from state import Treepolys, Fullpolys

    global Featurelayers

    global areaelectors
    global environment
    global filename
    global layeritems
    global constants
    global OPTIONS
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']

    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(estyle,current_election,path) # takes to the clicked node in the territory
    session['current_node_id'] = current_node.nid


    walk_node = current_node
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]

    mask2 = areaelectors['WalkName'] == walk_node.value
    walkelectors = areaelectors[mask2]

    walks = areaelectors.WalkName.unique()
    if request.method == 'GET':
# if there is a selected file , then areaelectors will be full of records
        print("________PDMarker",walk_node.type,"|", walk_node.dir, "|",walk_node.file)

        Featurelayers['walkleg'].create_layer(current_election,walk_node,'walkleg')

        flash("No data for the selected election available!")
        walklegnodelist = walk_node.childrenoftype('walkleg')
        print ("________Walklegs",walk_node.value,len(walklegnodelist))
# for each walkleg node(partial street), add a walkleg node marker to the walk_node parent layer (ie PD_node.level+1)
        for walkleg_node in walklegnodelist:
            mask = walkelectors['StreetName'] == walkleg_node.value
            streetelectors = walkelectors[mask]
            walkleg_node.create_streetsheet(current_election,streetelectors)

            walk_node.create_area_map(walk_node.getselectedlayers(estyle,current_election,path), current_election,CurrentElection)

    mapfile = walk_node.mapfile()


    if len(areaelectors) == 0 or len(Featurelayers['walkleg']._children) == 0:
        flash("Can't find any elector data for this ward.")
        print("Can't find any elector data for this ward.")
        if os.path.exists(mapfile):
            os.remove(mapfile)
    else:
        flash("________walks added  :  "+str(len(Featurelayers['walkleg']._children)))
        print("________walks added  :  "+str(len(Featurelayers['walkleg']._children)))


    persist(current_node)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/wardreport/<path:path>',methods=['GET','POST'])
@login_required
def wardreport(path):

    global layeritems
    global formdata
    global CurrentElection
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    current_node = current_node.ping_node(estyle,current_election,path)
    session['current_node_id'] = current_node.nid

    flash('_______ROUTE/wardreport')
    print('_______ROUTE/wardreport')
    mapfile = current_node.mapfile()
    print("________layeritems  :  ", layeritems)

    i = 0
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+child_type_of(current_node.type,estyle)+" details"
    layeritems = get_layer_table(current_node.create_map_branch(session,'constituency'),formdata['tabledetails'])
    for group_node in current_node.childrenoftype('constituency'):

        layeritems = get_layer_table(group_node.create_map_branch(session,'ward'))

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

    persist(current_node)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)



@app.route("/get_table/<table_name>", methods=["GET"])
@login_required
def get_table(table_name):
    global OPTIONS
    global report_data
    global stream_table
    global layertable
    from state import VNORM
    from nodes import TREK_NODES_BY_ID,TREK_NODES_BY_VALUE, get_layer_table


    def get_resources_table():
        return pd.DataFrame(resources)

    def get_report_table():
        try:
            if report_data:
                return pd.DataFrame(report_data)
        except:
            report_data = pd.DataFrame()
        return pd.DataFrame(report_data)

    def get_places_table():
        print(f"Places content: {places}")
        print(f"pd.DataFrame: {pd.DataFrame}, type: {type(pd.DataFrame)}")
        if places is None or not places:
            raise ValueError("places is not defined")

        # Check if places is a dictionary or a list
        if isinstance(places, dict):
            return pd.DataFrame.from_dict(places, orient='index')

        elif isinstance(places, list):
            # Ensure each item in the list is a dictionary (if it's a list of dicts)
            if all(isinstance(item, dict) for item in places):
                return pd.DataFrame(places)
            else:
                raise ValueError("Each item in places list must be a dictionary.")

        else:
            raise TypeError("places must be either a dictionary or a list.")

    def get_stream_table():
        print(f"Stream_table content: {stream_table}")
        if isinstance(stream_table, dict):
            return pd.DataFrame.from_dict(stream_table, orient='index')
        else:
            return pd.DataFrame(stream_table)

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']
    print(f"____Get Table1 {table_name} estyle {estyle}")

    # Table mapping
    table_map = {
        "report_data" : get_report_table,
        "resources" : get_resources_table,
        "places" : get_places_table,
        "stream_table" : get_stream_table
    }


    try:
        print(f"____GET TABLE  start: {current_node.value} table: {table_name} ")

        if table_name.endswith("_layer"):
            # eg for constituency_layer - look up children of county surrey
            tabtype = table_name.removesuffix("_layer")
            lev = parent_level_for(tabtype) # eg Surrey
            print(f"____NODELOOKUP  start: {current_node.value} table: {table_name} type {tabtype} level {lev} ")
            tabnode =current_node.findnodeat_Level(lev)
            print(f"____TABNODE: {tabnode.nid} - {tabnode.findnodeat_Level(lev).value} tabtype {tabtype} listNUM {len(tabnode.childrenoftype(tabtype))} - {len(tabnode.children)} ")
            print(f"____TREK_NODES_BY_ID: {TREK_NODES_BY_ID} ")

            [column_headers,rows, title] = get_layer_table(tabnode.childrenoftype(tabtype), str(tabtype)+"s")
            print(f"____NODELOOKUP {table_name} -COLS {column_headers} ROWS {rows} TITLE {title}")
            return jsonify([column_headers, rows.to_dict(orient="records"), title])
        elif table_name.endswith("_xref"):
            lev = current_node.level+1
            path = current_node.dir+"/"+current_node.file
            tabtype = gettypeoflevel(estyle,path,lev)
            print(f"____NODEXREF type {tabtype} level {lev} ")
            [column_headers,rows, title] = get_layer_table(current_node.childrenoftype(tabtype), str(tabtype)+"s")
            print(f"____NODEXREF -COLS {column_headers} ROWS {rows} TITLE {title}")
            return jsonify([column_headers, rows.to_dict(orient="records"), title])
        elif table_name is None or table_name not in table_map:
            print(f"____BAD TABLE {table_name} None or not in list ")
            return jsonify(["", "", f"Table '{table_name}' not found"]), 404
        df = table_map[table_name]()
        column_headers = list(df.columns)
        rows = df.to_dict(orient="records")
        title = table_name.replace("_", " ").title()
        print(f"____TABLENAME {table_name} -COLS {column_headers} ROWS {rows} TITLE {title}")
        return jsonify([column_headers, rows, title])
    except Exception as e:
        print(f"[ERROR] Failed to generate table '{table_name}': {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/fetch_areas', methods=['POST', 'GET'])
@login_required
def fetch_areas():

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    accordian = current_node.get_areas()
    print(f"_______ Fetch under {current_election} for {current_node.value} Areas {accordian}")

    return jsonify({ "areas": accordian })



@app.route('/displayareas', methods=['POST', 'GET'])
@login_required
def displayareas():
    #calc values in displayed table

    global layeritems
    global formdata

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    places = CurrentElection['places']
    print(f"____Route/displayareas for {current_node.value} in election {current_election} ")
    if current_election == "DEMO":
        if len(places) > 0:
            formdata['tabledetails'] = "Click for details of uploaded markers, markers and events"
            layeritems = get_layer_table(pd.DataFrame(places) ,formdata['tabledetails'])
            print(f" Number of displayed markframe items - {len(places)} ")
        else:
            formdata['tabledetails'] = "No data to display - please upload"
            layeritems = get_layer_table(pd.DataFrame(places),formdata['tabledetails'])
    else:
        path = current_node.dir+"/"+current_node.file
        ctype = gettypeoflevel(estyle,path, current_node.level+1)

        formdata = current_node.value +child_type_of(current_node.type,estyle)+"s"
        tablenodes = current_node.childrenoftype(ctype)
        if len(tablenodes) == 0:
            if current_node.level > 0:
                ctype = gettypeoflevel(estyle,path, current_node.level)
                tablenodes = current_node.parent.childrenoftype(ctype)
            else:
                return jsonify([[], [], "No data"])
        layeritems = get_layer_table(tablenodes ,formdata)
        print(f"Display layeritems area {current_node.value} - {ctype} - {len(tablenodes)}")

    if not layeritems or len(layeritems) < 3:
        return jsonify([[], [], "No data"])

    # --- Handle selected tag from request or session
    selected_tag = CurrentElection['tags']
    # Unpack layeritems
    df = layeritems[1].copy()
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
    global Featurelayers
    global CurrentElection

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers

    current_node = current_node.ping_node(estyle,current_election,path)
    session['current_node_id'] = current_node.nid
    mapfile = current_node.mapfile()

    flash('_______ROUTE/divreport')
    print('_______ROUTE/divreport')

    i = 0
    layeritems = pd.DataFrame()
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+child_type_of(current_node.type,estyle)+" details"
    layeritems = get_layer_table(current_node.create_map_branch(session,'constituency'),formdata['tabledetails'])

    for group_node in current_node.childrenoftype('division'):

        layeritems = get_layer_table(group_node.create_map_branch(session,'division'),formdata['tabledetails'])

        for item in Featurelayers['division']._children:
            if item.value not in alreadylisted:
                alreadylisted.append(item.value)
                temp.loc[i,'No']= i
                temp.loc[i,'Area']=  item.value
                temp.loc[i,'Constituency']=  group_node.value
                temp.loc[i,'Candidate']=  "Joe Bloggs"
                temp.loc[i,'Email']=  "xxx@reforumuk.com"
                temp.loc[i,'Mobile']=  "07789 342456"
                i = i + 1
        formdata['tabledetails'] = "Other Division Details"
        layeritems = [list(temp.columns.values), temp, formdata['tabledetails']]


    persist(current_node)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/upbut/<path:path>', methods=['GET','POST'])
@login_required
def upbut(path):

    from nodes import allelectors
    from state import Treepolys, Fullpolys

    global Featurelayers
    global environment
    global layeritems
    global constants
    global OPTIONS

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']

    flash('_______ROUTE/upbut',path)
    print('_______ROUTE/upbut',path, current_node.value)
    trimmed_path = path
    if path.find(" ") > -1:
        dest_path = path.split(" ")
        moretype = dest_path.pop() # take off any trailing parameters
        trimmed_path = dest_path[0]

    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
# for PDs the up button should take you to the -PDS file, for walks the -WALKS file
#
    previous_node = current_node
    current_node = previous_node.parent.ping_node(estyle,current_election,path)

    if current_node.level < 3:
        restore_fullpolys(current_node.type)

# the previous node's type determines the 'face' of the destination node
    atype = gettypeoflevel(estyle,path,current_node.level+1) # destination type
    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""

#    FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html",'walk' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
#    face_file = subending(trimmed_path,FACEENDING[previous_node.type])
#    print(f" previous: {previous_node.value} type: {previous_node.type} current {current_node.value} type: {current_node.type} FACEFILE:{FACEENDING[previous_node.type]}")

    mapfile = current_node.mapfile()
    if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
        Featurelayers[previous_node.type].create_layer(current_election,current_node,previous_node.type) #from upnode children type of prev node

        flash("No data for the selected node available,attempting to generate !")
        print("No data for the selected node available,attempting to generate !")
        current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,mapfile), current_election,CurrentElection)

    print("________chosen node url",mapfile)
    persist(current_node)
    return visit_node(previous_node.parent,current_election,CurrentElection)


#Register user
@app.route('/register', methods=['POST'])
def register():
    flash('_______ROUTE/register')

    username = request.form['username']
    password = request.form['password']
    print("Register", username)
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

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
    global places, resources, constants, OPTIONS

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    ctype = gettypeoflevel(estyle,path, current_node.level + 1)




    with open(OPTIONS_FILE, 'r', encoding="utf-8") as f:
        OPTIONS = json.load(f)


    # Track used IDs across both existing and new entries
#        places = build_place_lozenges(markerframe)

#        restore_from_persist(session=session)
#        current_node = get_current_node(session)
#        CE = get_current_election(session)

    selectedResources = {
            k: v for k, v in OPTIONS['resources'].items()
            if k in CElection['resources']
        }


    print(f"___resources in election {current_election}  node: {current_node.value} Resources: {selectedResources} ")

    areas = current_node.get_areas()
    print(f"caldata for {current_node.value} of length {len(areas)} ")

    # share input and outcome tags
    valid_tags = CElection['tags']
    task_tags, outcome_tags = get_tags_json(CElection['tags'])

    print(f"___ Task Tags {valid_tags} Outcome Tags: {outcome_tags} areas:{areas}")
    print(f"🧪 calendar partial level {current_election} - current_node mapfile:{mapfile} - OPTIONS html {OPTIONS['areas']}")


    return render_template(
        "Dash0.html",
        table_types=TABLE_TYPES,
        ELECTIONS=ELECTIONS,
        current_election=current_election,
        options=OPTIONS,
        constants=CElection,
        mapfile=mapfile
    )


@app.route('/thru/<path:path>', methods=['GET','POST'])
@login_required
def thru(path):

    global CurrentElection
# map is just a straight transfer to the given path
#    steps = path.split("/")
#    last = steps.pop()
#    current_node = selected_childnode(current_node,last)
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    estyle = CurrentElection['territories']
    mapfile = current_node.mapfile()
    flash ("_________ROUTE/thru:"+mapfile)
    print ("_________ROUTE/thru:",mapfile, CurrentElection)
    current_node = current_node.ping_node(estyle,current_election,mapfile)
    if os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
        flash(f"Using existing file: {mapfile}", "info")
        print(f"Using existing file: {mapfile} and CurrentElection: {CurrentElection}")
        return visit_node(current_node,current_election,CurrentElection)
    else:
        flash(f"Creating new mapfile:{mapfile}", "info")
        print(f"Creating new mapfile:{mapfile}")
#        fileending = "-"+mapfile.split("-").pop()
#        current_node.file = subending(current_node.file,fileending)
        current_node.create_area_map(current_node.getselectedlayers(estyle,current_election,mapfile), current_election,CurrentElection)
        print(f"____/THRU OPTIONS areas for calendar node {current_node.value} are {Featurelayers['street'].areashtml} ")
        print(f"____/THRU OPTIONS2 areas for calendar node {current_node.value} are {Featurelayers['walk'].areashtml} ")
        print(f"____/THRU OPTIONS3 areas for calendar node {current_node.value} are {Featurelayers['ward'].areashtml} ")
        return visit_node(current_node,current_election,CurrentElection)

@app.route('/showmore/<path:path>', methods=['GET','POST'])
@login_required
def showmore(path):

    global CurrentElection

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    steps = path.split("/")
    last = steps.pop().split("--")
    current_node = selected_childnode(current_node,last[1])


    flash ("_________ROUTE/showmore"+path)
    print ("_________showmore",path)

    session['current_node_id'] = current_node.nid

    return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)


@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
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

    from nodes import allelectors
    from state import Treepolys, Fullpolys

    global environment

    global formdata
    global layeritems
    global CurrentElection

    flash('_______ROUTE/filelist',filetype)
    print('_______ROUTE/filelist',filetype)
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    if filetype == "maps":
        return jsonify({"message": "Success", "file": url_for('thru', path=mapfile)})



from flask import jsonify, render_template
import os
import pandas as pd

@app.route('/progress')
@login_required
def get_progress():
    global DQstats, progress

    if progress['status'] != 'complete':
        for key, value in progress.items():
            print(f"Progress1-{key} => {value}")
        return jsonify({
            'election' : progress['election'],
            'percent': progress['percent'],
            'status': progress['status'],
            'message': progress['message'],
            'targetfile' : progress['targetfile'],
            'dqstats_html': progress['dqstats_html']
        })

    # Normalisation complete

    dq_file_path = os.path.join(config.workdirectories['workdir'], subending(progress['targetfile'], "DQ.csv"))
    print("____DQ FILE EXISTS: ",dq_file_path )
    if os.path.exists(dq_file_path):
        DQstats = pd.read_csv(dq_file_path, sep='\t', engine='python', encoding='utf-8', keep_default_na=False, na_values=[''])
        progress['dqstats_html'] = render_template('partials/dqstats_rows.html', DQstats=DQstats)
    else:
        progress['dqstats_html'] = ""

    # Update progress object with HTML
    progress['percent'] = 100
    progress['status'] = 'complete'
    progress['message'] = 'Normalization Complete'
    progress['election'] = progress['election']
    streamrag = getstreamrag()
    html = render_template('partials/streamtab_rows.html', streamrag=streamrag)
    print("___JSONIFYED streamrag:",streamrag)


    for key, value in progress.items():
        print(f"Progress2-{key} => {value}")
    return jsonify({
        'election' : progress['election'],
        'percent': progress['percent'],
        'status': progress['status'],
        'message': progress['message'],
        'dqstats_html': progress['dqstats_html'],
        'html': html,
        'streamrag' :streamrag

    })
  # Send whole object as JSON



@app.route('/walks', methods=['POST','GET'])
@login_required
def walks():

    from nodes import allelectors
    from state import Treepolys, Fullpolys

    global streamrag
    global CurrentElection
    global TABLE_TYPES


    global environment
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    flash('_______ROUTE/walks',session)
    streamrag = getstreamrag()


    if len(request.form) > 0:
        formdata = {}
        formdata['importfile'] = request.files['importfile']
        formdata['electiondate'] = request.form["electiondate"]
        electwalks = prodwalks(current_node,formdata['importfile'], formdata,Treepolys, environment, Featurelayers)
        formdata = electwalks[1]
        print("_________Mapfile",electwalks[2])
        mapfile = electwalks[2]
        group = electwalks[0]

#    formdata['username'] = session['username']
        session['current_node_id'] = current_node.nid

        return render_template('Dash0.html',  formdata=formdata,table_types=TABLE_TYPES, current_election=current_election, group=allelectors , streamrag=streamrag ,mapfile=mapfile)
    return redirect(url_for('dashboard'))

@app.route('/postcode', methods=['POST','GET'])
@login_required
def postcode():
# the idea of this service is to locate people's branches using their postcode.
# first get lat long, then search through constit boundaries and pull up the NAME of the one that its IN

    from state import Treepolys, Fullpolys
    global Featurelayers
    global CurrentElection
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    flash('__ROUTE/Findpostcode')

    pthref = current_node.dir+"/"+current_node.file
    mapfile = url_for(downtoType[current_node.type],path=pathref)
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
    pfile = Treepolys[gettypeoflevel(estyle,current_node.dir,current_node.level+1)]
    polylocated = find_boundary(pfile,here)
    flash(f'___The branch that contains this postcode is:{polylocated.NAME}')

    return redirect(url_for('dashboard'))


@app.route('/firstpage', methods=['GET', 'POST'])
@login_required
def firstpage():

    from nodes import allelectors
    from state import Treepolys, Fullpolys

    global workdirectories
    global Featurelayers
    global environment
    global layeritems
    global streamrag
    global CurrentElection
    global TABLE_TYPES
    global OPTIONS
    global constants


    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)
    estyle = CurrentElection['territories']

    print("🔍 Accessed /firstpage")
    print("🧪 current_user.is_authenticated:", current_user.is_authenticated)
    print("🧪 current_user:", current_user)
    print("🧪 current_election:", current_election)
    print("🧪 session keys:", list(session.keys()))
    print("🧪 full session content:", dict(session))
    print("🧪 full currentelection content:", CurrentElection)

    formdata = {}
    formdata['country'] = "UNITED_KINGDOM"
    flash('_______ROUTE/firstpage')
    print('_______ROUTE/firstpage at :',current_node.value )

    mapfile = CurrentElection['mapfiles'][-1]
# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = current_node.ping_node(estyle,current_election,mapfile)

    print(f"🧪 current election 1 {current_election} - current_node:{current_node.value}")
    print("____Firstpage Mapfile",mapfile, current_node.value)
    atype = gettypeoflevel(estyle,mapfile,current_node.level+1)
# the map under the selected node map needs to be configured
# the selected  boundary options need to be added to the layer

    Featurelayers['marker'].create_layer(current_election,current_node,'marker')
    print(f"XXXXMarkers {len(Featurelayers['marker']._children)} at election {current_election} at node {current_node.value}")

    Featurelayers[atype].create_layer(current_election,current_node,atype)
    print(f"____/FIRST OPTIONS areas for calendar node {current_node.value} are {OPTIONS['areas']} ")
    streamrag = getstreamrag()
    print(f"🧪 current election 2 {current_election} - current_node:{current_node.value} - atype:{atype} - name {Featurelayers[gettypeoflevel(estyle,mapfile, current_node.level+1)].name} - areas: {Featurelayers[gettypeoflevel(estyle,mapfile, current_node.level)].areashtml}")
    flayers = current_node.getselectedlayers(estyle,current_election,mapfile)
    current_node.create_area_map(flayers, current_election,CurrentElection)
    print("______First selected node",atype,len(current_node.children),current_node.value, current_node.level,current_node.file)

#        CurrentElection['mapfiles'][-1] = mapfile

    ELECTIONS = get_election_names()

#    return visit_node(current_node,current_election, CurrentElection)
#    persist(current_node)
    print(f"🧪 firstpage level {current_election} - current_node mapfile:{mapfile} - OPTIONS html {OPTIONS['areas']}")

    return render_template(
        "Dash0.html",
        table_types=TABLE_TYPES,
        ELECTIONS=ELECTIONS,
        current_election=current_election,
        options=OPTIONS,
        constants=CurrentElection,
        mapfile=mapfile
    )



@app.route('/cards', methods=['POST','GET'])
@login_required
def cards():

    from nodes import allelectors
    from state import Treepolys, Fullpolys

    global streamrag
    global environment
    global TABLE_TYPES


    flash('_______ROUTE/canvasscards',session, request.form, current_node.level)
    streamrag = getstreamrag()


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

            prodcards = canvasscards.prodcards(current_node,formdata['importfile'], formdata, Treepolys, environment, Featurelayers)
            formdata = prodcards[1]
            print('_______Formdata:',formdata)

            if formdata['streets'] > 0 :
                print("_________formdata",formdata)
                flash ( "Electoral data for" + formdata['constituency'] + " can now be explored.")
                mapfile =  prodcards[2]
                group = prodcards[0]
                ELECTIONS = get_election_names()
                return render_template('Dash0.html',  table_types=TABLE_TYPES,formdata=formdata,current_election=CurrentElection[session.get("current_election","DEMO")], ELECTIONS=ELECTIONS, group=allelectors , streamrag=streamrag ,mapfile=mapfile)
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

    # Save request/form/session to avoid issues inside thread
    request_form = request.form.to_dict(flat=True)
    request_files = request.files.to_dict(flat=False)  # Getlist-style access
    restore_from_persist(session=session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = get_last(current_election,CurrentElection)

    stream = str(request_form.get('election')).upper()
    streamrag = getstreamrag()
    if streamrag.get(stream, {}).get('Alive') == True:
        print(f"This election data is already loaded and live: {stream}" )
        progress["percent"] = 100
        progress["status"] = "complete"
        progress["targetfile"] = ""
        progress["message"] = f"This election data is already loaded and live: {stream}"
        return jsonify({"message": "Success", "message": f"This election data is already loaded and live: {stream}" })

    session['current_election'] = stream
    print("___TESTING TESTING", session['current_election'], request_form.get('election') )


    session_data = dict(session)

    RunningVals = {
        'Mean_Lat' : 51.240299,
        'Mean_Long' : -0.562301,
        'Last_Lat'  : 51.240299,
        'Last_Long' : -0.562301
    }

    Lookups = {
        'LatLong': {},
        'Elevation': {}
    }

    dfw = pd.read_csv(config.workdirectories['bounddir']+"/National_Statistics_Postcode_Lookup_UK_20250612.csv")
    Lookups['LatLong'] = dfw[['Postcode 1','Latitude','Longitude']]
    Lookups['LatLong'] = Lookups['LatLong'].rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
    Lookups['Elevation'] = pd.read_csv(config.workdirectories['bounddir']+"/open_postcode_elevation.csv")
    Lookups['Elevation'].columns = ["Postcode","Elevation"]

    DQstats = pd.DataFrame()
    streamrag = getstreamrag()
    # Collect unique streams for dropdowns
    stream_table = []
    print("🔍 type of json3:", type(json))
    if os.path.exists(TABLE_FILE):
        with open(TABLE_FILE) as f:
            stream_table = json.load(f)
    else:
        stream_table = []
    streams = sorted(set(row['election'] for row in stream_table))

    streamtablehtml =  render_template('partials/streamtable.html', stream_table=stream_table)

    print("Form Data:", request_form)
    print("Form Files:", request_files)

    target_election = session_data.get('current_election',"DEMO")
    files = []

    # 3. Extract metadata and stored paths
    meta_data = {}

    for key, value in request_form.items():
        if key.startswith('meta_'):
            parts = key.split('_')
            if len(parts) < 3:
                continue  # malformed key
            index = parts[1]
            field = '_'.join(parts[2:])
            meta_data.setdefault(index, {})[field] = value
            print("___META:", field, "**", value)

        elif key.startswith('stored_path_'):
            index = key.replace('stored_path_', '')
            meta_data.setdefault(index, {})['stored_path'] = value
            print(f"📁 Stored path for index {index}: {value}")

    # Step 1.5: Match files and paths with metadata and collect by index
    indexed_files = []
    for index_str, meta in meta_data.items():
        try:
            index = int(index_str)
        except ValueError:
            print(f"⚠️ Skipping malformed index: {index_str}")
            continue

        # Check for uploaded files for this index
        file_key = f'files_{index}'
        file_obj = None
        if file_key in request_files:
            file_list = request_files[file_key]
            if file_list:
                file_obj = file_list[0]
                print(f"📁 File matched for index {index}: {file_obj.filename}")

        # If no uploaded file, check for stored path
        stored_path = meta.get('stored_path')
        if file_obj:
            indexed_files.append((index, file_obj))
        elif stored_path and os.path.exists(stored_path):
            indexed_files.append((index, stored_path))
        else:
            print(f"⚠️ No file or valid stored path for index {index}")

    # Sort files by index before saving
    stored_paths = []
    for index, file_or_path in sorted(indexed_files, key=lambda x: x[0]):
        if hasattr(file_or_path, 'filename') and file_or_path.filename:
            filename = secure_filename(file_or_path.filename)
            save_path = os.path.join(config.workdirectories['workdir'], filename)
            file_or_path.save(save_path)
        else:
            save_path = file_or_path  # already stored path

        stored_paths.append(save_path)

        # Assign saved_path to corresponding meta_data entry
        meta = meta_data.get(str(index), {})
        meta['saved_path'] = save_path
        meta_data[str(index)] = meta
        print(f"✅ Assigned saved_path to meta index {index}: {save_path}")

    print("📁 Stored paths:", stored_paths)
    print("📦 Meta Data (post-save):")
    for k, v in meta_data.items():
        print(f"  Index {k}: {v.get('saved_path')}")

    # Start background thread
    threading.Thread(
        target=background_normalise,
        args=(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table)
    ).start()

    dqstats_html = render_template('partials/dqstats_rows.html', DQstats=DQstats)

    return jsonify({"message": "Success", "html": dqstats_html })


from pathlib import Path

@app.route('/stream_input')
@login_required
def stream_input():
    from nodes import allelectors
    global stream_table

    restore_from_persist(session=session)

    DQstats = pd.DataFrame()

    # Load table data
    stream_table = []
    if os.path.exists(TABLE_FILE):
        with open(TABLE_FILE) as f:
            stream_table = json.load(f)
    else:
        print("🔍 Can't open stream_table file:", TABLE_FILE)
        stream_table = []

    # Build stream path into each row
    base_path = "/your/base/path"  # Replace with the actual base directory
    for row in stream_table:
        election = row.get("election", "")
        if election:
            row["stream_path"] = str(Path(base_path) / election)
        else:
            row["stream_path"] = ""

    streamrag = getstreamrag()
    ELECTIONS = get_election_names()
    streams = list(ELECTIONS)

    return render_template(
        'stream_processing_input.html',
        ELECTIONS=ELECTIONS,
        stream_table=stream_table,
        streamrag=streamrag,
        DQstats=DQstats,
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
