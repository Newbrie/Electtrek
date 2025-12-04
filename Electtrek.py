from canvasscards import prodcards, find_boundary
from walks import prodwalks
#import electwalks, locfilepath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
import config
from config import TABLE_FILE,OPTIONS_FILE,ELECTIONS_FILE,TREEPOLY_FILE,GENESYS_FILE,ELECTOR_FILE,TREKNODE_FILE,FULLPOLY_FILE,RESOURCE_FILE, DEVURLS
from normalised import normz
#import normz
import folium
from json import JSONEncoder, JSONDecodeError
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
from folium import FeatureGroup
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPoint
from shapely import crosses, contains, union, envelope, intersection
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
from matplotlib.colors import to_hex, to_rgb
import colorsys
from collections import defaultdict
import requests
import pickle
import threading
import traceback
import unidecode
from flask import Response
import copy
import json
from geovoronoi import voronoi_regions_from_coords
from folium import GeoJson, Tooltip, Popup
import locale
from shapely.ops import nearest_points
import logging
from flask import has_request_context
import html
from folium import Map, Element



locale.setlocale(locale.LC_TIME, 'en_GB.UTF-8')


sys.path
sys.path.append('/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Electtrek.py')
print(sys.path)

levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

levels = ['country','nation','county','constituency','ward/division','polling_district/walk','street/walkleg','elector']

def find_level_containing(word):
    word = word.lower()
    for i, level in enumerate(levels):
        if word in level.lower():
            return i
    return -1  # Not found

# want to equate levels with certain types, eg 4 is ward and div
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

def capped_append(lst, item):
    max_size = 7
    if not isinstance(lst, list):
        return
    lst.append(item)
    if len(lst) > max_size:
        lst.pop(0)  # Remove oldest
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

def stepify(path):
    # turn path into steps removing directories and file ending ie 'WARDS, DIVS, PDS and WALKS'
    route = path.replace('/WALKS/','/').replace('/PDS/','/').replace('/WARDS/','/').replace('/DIVS/','/') # strip out all padding directories and file endings except -PRINT.html (leaves)
    parts = route.split("/")
    last = parts.pop() #eg KA>SMITH_STREET or BAGSHOT-MAP
    if last.find("-PRINT.html"):#only works for street-leaf nodes, not -WALKS etc nodes
        leaf = subending(last,"").split("--").pop()
        parts.append(leaf) #eg SMITH_STREET
        print("____LEAFNODE:", path,parts)
    return parts

def get_resources_json(election_data, resources):
    selectedResources = {
            k: v for k, v in resources.items()
            if k in election_data['resources']
        }
    print(f"___Resources: {selectedResources} ")

    return selectedResources


# share task and outcome tags for each election
def get_task_tags_json(election_data):
    valid_tags = election_data['tags']
    task_tags = {}
    outcome_tags = {}
    for tag, description in valid_tags.items():
        if tag.startswith('L'):
            task_tags[tag] = description
        elif tag.startswith('M'):
            outcome_tags[tag] = description
    print(f"___Dash  Task Tags {valid_tags} Outcome Tags: {outcome_tags}")
    return task_tags

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

def getchildtype(parent):
    global levels
    if parent == 'ward' or parent == 'division':
        parent = 'ward/division'
    elif parent == 'walk' or parent == 'polling_district':
        parent = 'polling_district/walk'
    elif parent == 'street' or parent == 'walkleg':
        parent = 'street/walkleg'
    lev = min(levels.index(parent)+1,7)
    return levels[lev]
#    matches = [index for index, x in enumerate(levels) if x.find(parent) > -1  ]
#    return levels[matches[0]+1]

def gettypeoflevel(path,level):
# returns the correct type for nodes at a given level along a given path
# the level will give type options , which are resolved by looking at the path content
    global levels
    moretype = ""
    dest = path
    if path.find(" ") > -1:
        dest_path = path.split(" ")
        moretype = dest_path.pop() # take off any trailing parameters
        dest = dest_path[0]
    deststeps = list(stepify(dest)) # lowest left - UK right

    if level > 6:
        level = 6
    type = levels[level] # could have type options that need to be resolved

    if type == 'ward/division':
        if path.find("/WARDS/") >= 0:
            type = 'ward'
        elif path.find("/DIVS/") >= 0:
            type = 'division'
        elif level+1 >= len(deststeps) and moretype != "":
        # if desired level is greater than path level then use 'new' override
            print(f"____override! len child level {level} > {len(deststeps)}  so override with {moretype}")
            type = moretype # this is the type override syntax if level is new - ie desired level great than path level
        else:
            type = 'ward' # default
    elif type == 'polling_district/walk':
        if path.find("/PDS/") >= 0 or path.endswith("-PDS.html"):
            type = 'polling_district'
        elif path.find("/WALKS/") >= 0 or path.endswith("-WALKS.html"):
            type = 'walk'
        elif level+1 >= len(deststeps) and moretype != "":
            print(f"____override! len child level {level} > {len(deststeps)}  so override with {moretype}")
            type = moretype # this is the type override syntax if level is new - ie desired level great than path level
        else:
            type = 'polling_district' #default
    elif type == 'street/walkleg':
        if path.find("/PDS/") >= 0:
            type = 'street'
        elif path.find("/WALKS/") >= 0:
            type = 'walkleg'
        elif level+1 >= len(deststeps) and moretype != "":
            print(f"____override! len child level {level} > {len(deststeps)}  so override with {moretype}")
            type = moretype # this is the type override syntax if level is new - ie desired level great than path level
        else:
            type = 'street' #default


    return type


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url,target))
    return test_url.scheme in ('http', 'https') and \
            ref_url.netloc == test_url.netloc

def get_layer_table(nodelist,title):
    global VCO
    global VNORM
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
            options = x.VI
            for party in options:
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

            dfy.loc[i,'elect'] = x.electorate
            dfy.loc[i,'hous'] = x.houses
            dfy.loc[i,'turn'] = '%.2f'%(x.turnout)
            dfy.loc[i,'gotv'] = '%.2f'%(float(CurrentElection['GOTV']))
            dfy.loc[i,'toget'] = int(((x.electorate*x.turnout)/2+1)/float(CurrentElection['GOTV']))-int(x.VI[CurrentElection['yourparty']])
            i = i + 1

        # Safely convert known numeric-looking columns

        # Step 1: Convert specific columns to numeric
        int_cols = ['elect', 'hous', 'toget']
        float_cols = ['turn', 'gotv']
        for col in int_cols + float_cols:
            dfy[col] = pd.to_numeric(dfy[col], errors='coerce')

        # Step 2: Create totals row by summing numeric columns
        totals_row = dfy[int_cols + float_cols].sum(numeric_only=True)

        # Step 3: Format totals row values
        formatted_row = {}
        for col in dfy.columns:
            if col == 'EL':
                formatted_row[col] = 'TOTAL'
            elif col in int_cols:
                val = totals_row.get(col, 0)
                formatted_row[col] = str(int(val)) if pd.notna(val) else ''
            elif col in float_cols:
                val = totals_row.get(col, 0.0)
                formatted_row[col] = f"{val:.2f}" if pd.notna(val) else ''
            else:
                formatted_row[col] = ''  # leave all other fields empty in totals row

        # Step 4: Append totals row to DataFrame
        dfy = pd.concat([dfy, pd.DataFrame([formatted_row])], ignore_index=True)

        # Step 5: Convert all numeric columns back to string with formatting
        for col in int_cols:
            dfy[col] = dfy[col].apply(lambda x: str(int(x)) if pd.notna(x) and x != '' else '')
        for col in float_cols:
            dfy[col] = dfy[col].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) and x != '' else '')

        # Step 6: Fill remaining NaNs with empty strings
        dfy = dfy.fillna('')


    print("___existing get_layer_tableX",list(dfy.columns.values), dfy, title)
    return [list(dfy.columns.values),dfy, title]



def subending(filename, ending):
  stem = filename.replace(".XLSX", "@@@").replace(".CSV", "@@@").replace(".xlsx", "@@@").replace(".csv", "@@@").replace("-PRINT.html", "@@@").replace("-CAL.html", "@@@").replace("-MAP.html", "@@@").replace("-WALKS.html", "@@@").replace("-ZONES.html", "@@@").replace("-PDS.html", "@@@").replace("-DIVS.html", "@@@").replace("-WARDS.html", "@@@")
  print(f"____Subending test: from {filename} to {stem.replace('@@@', ending)}")
  return stem.replace("@@@", ending)


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

def get_current_election(session=None, session_data=None):
    global CurrentElection
# the sourc eof current election mu reflect what the user sees as the active tab or what is in session_data
    try:
        if not session or 'current_election' not in session:
                current_election = last_election()
                print("/get_election1 data: ",current_election)
                if not current_election:
                    current_election = "DEMO"
        elif not session_data or 'current_election' not in session_data:
                current_election = last_election()
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

def get_election_data(current_election):
    file_path = ELECTIONS_FILE.replace(".json",f"-{current_election}.json")
    print("____Reading CurrentElection File:",file_path)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                CurrentElection = json.load(f)
            print(f"___Loaded CurrentElection Data:{ current_election }: {CurrentElection }" )
            return CurrentElection
        except Exception as e:
            print(f"❌ Failed to read {file_path} Election JSON: {e}")
    else:
        file_path = ELECTIONS_FILE.replace(".json",f"-DEMO.json")
        try:
            with open(file_path, 'r') as f:
                CurrentElection = json.load(f)
            print(f"___Loaded CurrentElection Data:{ current_election }: {CurrentElection }" )
            return CurrentElection
        except Exception as e:
            print(f"❌ Failed to read {file_path} Election JSON: {e}")
    return None

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

def get_counters(session=None, session_data=None):

    try:
        if not session or 'gtagno_counters' not in session:
            counters = {}
        elif not session_data or 'gtagno_counters' not in session_data:
            counters = {}
    except Exception as e:
        counters = {}
        print(f"___System error: No session or current_node: {e} ")
    """
    Returns the current node from TREK_NODES using either the Flask session or passed-in session_data.
    """

    if  os.path.exists(TREKNODE_FILE) and os.path.getsize(TREKNODE_FILE) > 0:
        with open(TREKNODE_FILE, 'rb') as f:
            TREK_NODES = pickle.load(f)

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
        for etype in Featurelayers.keys():
            counters[etype] = 0
    return counters


def get_current_node(session=None, session_data=None):
    global TREK_NODES

    try:
        if not session or 'current_node_id' not in session:
            node = None
        elif not session_data or 'current_node_id' not in session_data:
            node = None
    except Exception as e:
        node = None
        print(f"___System error: No session or current_node: {e} ")
    """
    Returns the current node from TREK_NODES using either the Flask session or passed-in session_data.
    """

    if  os.path.exists(TREKNODE_FILE) and os.path.getsize(TREKNODE_FILE) > 0:
        with open(TREKNODE_FILE, 'rb') as f:
            TREK_NODES = pickle.load(f)

    if session and 'current_node_id' in session:
        current_node_id = session.get('current_node_id',"UNITED_KINGDOM")
        print("[Main Thread] current_node_id from session:", session.get('current_node_id'))
        node = TREK_NODES.get(current_node_id)
    elif session_data and 'current_node_id' in session_data and session_data.get('current_node_id',"UNITED_KINGDOM"):
        print("[Background Thread] current_node_id from session_data:", session_data.get('current_node_id',"UNITED_KINGDOM"))
        current_node_id = session_data.get('current_node_id',"UNITED_KINGDOM")
        node = TREK_NODES.get(current_node_id)
    else:
        current_node_id = 0
        node = None
        print("⚠️ current_node_id not found in session or session_data:so id = ",238 )

    if node == None:
        longmean = statistics.mean([-7.57216793459,  1.68153079591])
        latmean = statistics.mean([ 49.959999905, 58.6350001085])
        roid = (latmean,longmean)
        MapRoot = TreeNode("UNITED_KINGDOM",238, roid, 0, "DEMO")
        MapRoot.dir = "UNITED_KINGDOM"
        MapRoot.file = "UNITED_KINGDOM-MAP.html"
        RootPath = MapRoot.dir+"/"+MapRoot.file
        TREK_NODES = {}
        register_node(MapRoot)
        node = MapRoot
        print (f" current_node_id: {current_node_id} not in TREK_NODES:",TREK_NODES)
        print("⚠️ current_node not found in stored TREK_NODES, so starting new MapRoot")

    return node



def restore_from_persist(session=None,session_data=None):
    global TREK_NODES

    global Treepolys
    global Fullpolys
    global allelectors
    global OPTIONS
    global CurrentElection

    OPTIONS = {}

    if  os.path.exists(TREEPOLY_FILE) and os.path.getsize(TREEPOLY_FILE) > 0:
        with open(TREEPOLY_FILE, 'rb') as f:
            Treepolys = pickle.load(f)
    if  os.path.exists(FULLPOLY_FILE) and os.path.getsize(FULLPOLY_FILE) > 0:
        with open(FULLPOLY_FILE, 'rb') as f:
            Fullpolys = pickle.load(f)
    if  os.path.exists(OPTIONS_FILE) and os.path.getsize(OPTIONS_FILE) > 0:
        with open(OPTIONS_FILE, 'r',encoding="utf-8") as f:
            OPTIONS = json.load(f)


    if not ELECTOR_FILE or not os.path.exists(ELECTOR_FILE):
        print('_______no elector data so creating blank', ELECTOR_FILE)
        Outcomes = pd.read_excel(GENESYS_FILE)
        Outcols = Outcomes.columns.to_list()
        allelectors = pd.DataFrame(Outcomes, columns=Outcols)
        allelectors.drop(allelectors.index, inplace=True)
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
    current_election = get_current_election(session=session,session_data=session_data)

    resources = OPTIONS['resources']
    print('_______allelectors size: ', len(allelectors), current_election)
    print('_______resources: ', resources)

    return

def persist(node):
    global TREK_NODES

    global allelectors
    global Treepolys
    global Fullpolys

    print('___persisting file ', TREEPOLY_FILE)
    with open(TREEPOLY_FILE, 'wb') as f:
        pickle.dump(Treepolys, f)
    print('___persisting file ', FULLPOLY_FILE)
    with open(FULLPOLY_FILE, 'wb') as f:
        pickle.dump(Fullpolys, f)

    print('___persisting file ', ELECTOR_FILE, len(allelectors))
    allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

    print('___persisting nodes ', node.value)
    with open(TREKNODE_FILE, 'wb') as f:
        pickle.dump(TREK_NODES, f)

    return

def restore_fullpolys(node_type):
    global Fullpolys
    global Treepolys
    global current_node

    if  os.path.exists(TREEPOLY_FILE) and os.path.getsize(TREEPOLY_FILE) > 0:
        with open(TREEPOLY_FILE, 'rb') as f:
            Treepolys = pickle.load(f)
    if  os.path.exists(FULLPOLY_FILE) and os.path.getsize(FULLPOLY_FILE) > 0:
        with open(FULLPOLY_FILE, 'rb') as f:
            Fullpolys = pickle.load(f)

    current_node = get_current_node(session)
    current_election = get_current_election(session)

    Treepolys[node_type] = Fullpolys[node_type]

    print('___persisting file ', TREEPOLY_FILE)
    with open(TREEPOLY_FILE, 'wb') as f:
        pickle.dump(Treepolys, f)
    print('___persisting file ', FULLPOLY_FILE)
    with open(FULLPOLY_FILE, 'wb') as f:
        pickle.dump(Fullpolys, f)

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

class TreeNode:
    def __init__(self, value, fid, roid, lev, elect):
        global levelcolours
        self.value = normalname(str(value))
        self.children = []
        self.type = 'country'
        self.parent = None
        self.fid = fid
        self.level = lev
        self.file = self.value+"-MAP.html"
        self.dir = self.value
        self.election = elect
        self.col = levelcolours["C"+str(self.level+4)]
        self.tagno = 1
        self.gtagno = 1
        self.centroid = roid
        self.bbox = []
        self.VR = VIC.copy()
        self.VI = VIC.copy()
        self.turnout = 0
        self.electorate = 0
        self.houses = 0
        self.target = 1
        self.party = "O"



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

    def calfile(self):
        return self.dir+"/"+subending(self.file,"-CAL.html")


    def ping_node(self, c_election, dest_path):
        global Treepolys
        global Fullpolys
        global levels
        global TREK_NODES
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
            ntype = gettypeoflevel(raw_path_for_types, next_level)

            print(f"   ➡️ under {route()} Looking for part: '{part}' at level {next_level} (ntype={ntype})")

            # Expand children dynamically
            if next_level <= 4:
                print(f"      🛠 create_map_branch({ntype})")
                node.create_map_branch(c_election, ntype)
            elif next_level <= 6:
                print(f"      🛠 create_data_branch for election {c_election}({ntype})")
                node.create_data_branch(c_election, ntype)

            # Try to find a matching child
            matches = [child for child in node.children if child.value == part]
            if not matches:
                print(f"   ❌ under {route()} No match for '{part}' in node '{node.value}' children. Returning original node: {self.value}")
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
        final_ntype = gettypeoflevel(raw_path_for_types, final_level + 1)

        print(f"   🌿 Expanding children of path {raw_path_for_types} final node '{node.value}' (level {final_level}) with type '{final_ntype}'")

        try:
            if final_level < 4:
                node.create_map_branch(c_election, final_ntype)
                print("   ✅ create_map_branch() called")
            elif final_level < 6:
                node.create_data_branch(c_election, final_ntype)
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



    def getselectedlayers(self,this_election,path):
        global Featurelayers
        global OPTIONS
#add children layer(level+1), eg wards,constituencies, counties
        print(f"_____layerstest0 type:{self.value},{self.type} path: {path}")

        selected = []
        childtype = gettypeoflevel(path,self.level+1)
        if childtype == 'elector':
            selected = []
        else:
            selectc = Featurelayers[childtype]
            selectc.show = True
            selected = [selectc]
            print(f"_____layerstest1 {self.value} layertype: {childtype} areas html:{OPTIONS['areas']}")
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

    def updateTurnout(self):
        global VNORM
        global VCO
        global CurrentElection
        sname = self.value
        origin = self
        casnode = origin
        current_election = self.election
        CurrentElection = get_election_data(current_election)
#        print(f"____Turnout in {current_election} with Election data {CurrentElection}" )
        print ("_____current_election:",current_election)
        print("____CurrentElection:",CurrentElection)
        if CurrentElection['territories'] == 'W':
#cascade last constituency turnout figure to all wards(children) and streets(children)

# electorate is for a constituency is derived from wards is derived from streets (if you have electoral roll uploaded )
# turnover is fixed for constituency(National) or wards(non-National) - streets inherit from either wards or constituency depending on election type - in set up
            if self.level == 3:
                selected = Con_Results_data.query('NAME == @sname')
                self.turnout = float('%.6f'%(selected['Turnout'].values[0]))
                for l in range(origin.level):
                    casnode.parent.turnout = .25
                    i=1
                    for x in casnode.parent.childrenoftype(gettypeoflevel(casnode.dir,casnode.level)):
                        casnode.parent.turnout = (casnode.parent.turnout + x.turnout)/i
                        print ("_____NatTurnoutlevel:",i,casnode.value,casnode.level,casnode.turnout)
                        i = i+1
                    casnode = casnode.parent
            elif self.level > 3:
                casnode.turnout = casnode.parent.turnout

            self = origin
#            print ("___Nat Turnout:",self.value,self.level,self.turnout)
        else:
#cascade last council ward turnout figure to all streets(children)
            if self.level == 4:
                selected = Ward_Results_data.query('NAME == @sname')
                if len(selected) > 0:
                    self.turnout = float('%.6f'%(selected['TURNOUT'].values[0]))
                else:
                    self.turnout = 0
                for l in range(origin.level):
                    casnode.parent.turnout = 0
                    i=1
                    for x in casnode.parent.childrenoftype(gettypeoflevel(casnode.dir,casnode.level)):
                        casnode.parent.turnout = (casnode.parent.turnout + x.turnout)/i
#                        print ("_____LGTurnoutlevel:",casnode.level,casnode.value,casnode.turnout)
                        i = i+1
                    casnode = casnode.parent
            elif self.level > 4:
                casnode.turnout = casnode.parent.turnout

            self = origin
#            print ("___LG Turnout:",self.value,self.turnout)
        return

    def updateParty(self):
        global VNORM
        global VCO
        sname = self.value
        pname = self.parent.value
        dname = sname.removesuffix("_ED")
        party = "OTHER"
        selected = []
        if self.type == 'ward':
            selected = Level4_Results_data.query('NAME == @sname')
        elif self.type == 'division':
            selected = Level4_Results_data.query('NAME == @dname')
        elif self.type == 'constituency':
            selected = Con_Results_data.query('NAME == @sname')
        if len(selected)>0:
            party = normalname(selected['FIRST'].values[0])
        else:
            party = "OTHER"
        if party not in VNORM.keys():
            party = "OTHER"
        party2 = VNORM[party]
        self.col = VCO[party2]
        self.party = party2
        print("______VNORM:",self.type, self.party, self.col, self.parent.value, self.parent.childrenoftype('walk'))
        print("_______Electorate:", self.value,self.electorate, self.houses)

        return

    def updateElectorate(self,pop):

        global VNORM
        global VCO
        sname = self.value
        pop = int(pop)
        if pop > 0:
            origin = self
            sumnode = origin
            sumnode.electorate = pop
# electorate is for a constituency is derived from wards is derived from streets (if you have electoral roll uploaded )
# turnover is fixed for constituency(National) or wards(non-National) - streets inherit from either wards or constituency depending on election type - in set up
            for l in range(origin.level):
                sumnode.parent.electorate = 0
                i=1
                for x in sumnode.parent.childrenoftype(gettypeoflevel(sumnode.dir,sumnode.level)):
                    sumnode.parent.electorate = sumnode.parent.electorate + x.electorate
                    print ("_____Electoratelevel:",x.level,x.value,x.electorate,sumnode.electorate)
                    i = i+1
                sumnode = sumnode.parent
                self = origin
        else:
            if self.type == 'constituency'and sname in Con_Results_data['NAME'].to_list():
                selected = Con_Results_data.query('NAME == @sname')
                self.electorate = int(selected['Electorate'].values[0])
            elif self.type == 'ward' and sname in Ward_Results_data['NAME'].to_list():
                selected = Ward_Results_data.query('NAME == @sname')
                self.electorate = int(selected['ELECT'].values[0])
            print ("___Results:",self.value,self.electorate)

        print ("_____OriginElectorate:",self.findnodeat_Level(0).electorate,self.value,self.type,self.electorate)
        return

    def updateHouses(self,pop):

        global VNORM
        global VCO
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
            for x in sumnode.parent.childrenoftype(gettypeoflevel(sumnode.dir,sumnode.level)):
                sumnode.parent.houses = sumnode.parent.houses + x.houses
                print ("_____Houseslevel:",x.level,x.value,x.houses,sumnode.houses)
                i = i+1
            sumnode = sumnode.parent
            self = origin

        print ("_____OriginHouses:",self.findnodeat_Level(0).houses,self.value,self.type,self.houses)
        return

    def childrenoftype(self,electtype):
        if self.level > 4:
            typechildren = [x for x in self.children if x.type == electtype and x.election == session.get('current_election',"DEMO")]
        else:
            typechildren = [x for x in self.children if x.type == electtype]
        print(f"__for node:{self.value} at level {self.level} there are {len(self.children)} of which {len(typechildren)} are type {electtype} available {[x.type for x in self.children]} ")

        return typechildren


    def locfilepath(self,file_text):
        global levelcolours

        dir = self.dir
        if self.type == 'polling_district'and dir.find("/PDS") <= 0:
                dir = self.dir+"/PDS"
        elif self.type == 'walk'and dir.find("/WALKS") <= 0:
                dir = self.dir+"/WALKS"
        elif self.type == 'division'and dir.find("/DIVS") <= 0:
                dir = self.dir+"/DIVS"
        elif self.type == 'ward'and dir.find("/WARDS") <= 0:
                dir = self.dir+"/WARDS"
        target = config.workdirectories['workdir'] + dir + "/" + file_text

        dir = os.path.dirname(target)
        print(f"____target director {dir} and filename:{file_text}")
        os.chdir(config.workdirectories['workdir'])
        if not os.path.exists(dir):
          os.makedirs(dir)
          print("_______Folder %s created!" % dir)
          os.chdir(dir)
        else:
          print("________Folder %s already exists" % dir)
          os.chdir(dir)
        return target

    def create_name_nodes(self,elect,nodetype,namepoints,ending):
        global TREK_NODES
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
        [self.bbox, self.centroid] = self.get_bounding_box(block)

        if 'Zone' not in namepoints.columns:
            print("⚠️ 'Zone' column missing from namepoints. Defaulting all nodes to black.", namepoints.columns)
            namepoints['Zone'] = 'ZONE_0'  # or whatever default you want


        for index, limb  in namepoints.iterrows():
            fam_values = [x.value for x in fam_nodes]
            if limb['Name'] not in fam_values:
                datafid = abs(hash(limb['Name']))
                newnode = TreeNode(normalname(limb['Name']),datafid, (limb['Lat'],limb['Long']),self.level+1,elect )
                egg = self.add_Tchild(newnode, nodetype,elect)
                egg.file = subending(egg.file,ending)
                egg.bbox = self.bbox
                egg.col = zonecolour.get(limb['Zone'],'black')
                print(f"🎨 Assigned color '{egg.col}' to walk_node '{egg.value}' for zone '{limb['Zone']}'")

                egg.updateTurnout()
                egg.updateElectorate(limb['ENOP'])
                print('______Data nodes',egg.value,egg.fid, egg.electorate,egg.houses,egg.target,egg.bbox)

                fam_nodes.append(egg)
                register_node(egg)

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


    def create_data_branch(self,c_election, electtype):
        global allelectors
        global areaelectors
        global workdirectories
        global Treepolys
        global CurrentElection
        global TREK_NODES

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
                    nodelist = self.create_name_nodes(c_election,'polling_district',PDPtsdf,"-PDS.html") #creating PD_nodes with mean PD pos and elector counts
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

                    nodelist = self.create_name_nodes(c_election, 'walk', nodeelectors, "-WALKS.html")
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
                    nodelist = self.create_name_nodes(c_election,'street',streetdf,"-PRINT.html") #creating street_nodes with mean street pos and elector counts
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
                    nodelist = self.create_name_nodes(c_election,'walkleg',walklegdf,"-PRINT.html") #creating walkleg_nodes with mean street pos and elector counts
            except Exception as e:
                print("❌ Error during data branch generation:", e)
                return []
        else:
            print(f"_____ Electoral file contains no  data for election {c_election} and {self.value} for {electtype} types - Please load correct file",len(allelectors), len(areaelectors))

            nodelist = []
        print(f"____Created Data Branch for Election: {c_election} in area: {self.value} creating: {len(nodelist)} of child type {electtype} from: {len(allelectors)} - {len(areaelectors)} electors")

        return nodelist

    def create_map_branch(self,c_election,electtype):
        global Treepolys
        global Fullpolys
        global TREK_NODES

        current_election = c_election
        Overlaps = {
        "country" : 1,
        "nation" : 0.1,
        "county" : 0.001,
        "constituency" : 0.0005,
        "ward" : 0.00005,
        "division" : 0.00001,
        "walk" : 0.005,
        "polling_district" : 0.005,
        "street" : 0.005,
        "walkleg" : 0.005
        }
        block = pd.DataFrame()
        parent_poly = Treepolys[self.type]
#        parent_geom = parent_poly[parent_poly["FID"] == self.fid].geometry.values[0]

        # Filter the parent geometry based on the FID
        parent_geom = parent_poly[parent_poly["FID"] == self.fid]
        print(f"geometry for {self.value} FID {self.fid} is ",parent_geom)

        # If no matching geometry is found, handle the case where parent_geom is empty
        if parent_geom.empty or self.level == 0:
            print(f"Adding back in Full {self.type} boundaries for {self.value} FID {self.fid}")
            restore_fullpolys(self.type)
            parent_poly = Treepolys[self.type]
            parent_geom = parent_poly[parent_poly["FID"] == self.fid]
            # Ensure that parent_geom has the desired geometry after the update
            if parent_geom.empty:
                print(f"Still no matching geometry found after adding new polygon for FID {self.fid}")
            else:
                parent_geom = parent_geom.geometry.values[0]
        else:
            # If geometry was found, proceed with the matching geometry
            parent_geom = parent_geom.geometry.values[0]
        [self.bbox, self.centroid] = self.get_bounding_box(block)

        ChildPolylayer = Treepolys[electtype]

        print(f"____Children of {self.value} bbox:[{self.bbox}] of type {electtype}" )
        index = 0
        i = 0
        fam_nodes = self.childrenoftype(electtype)

        for index,limb in ChildPolylayer.iterrows():
            fam_values = [x.value for x in fam_nodes]
            newname = normalname(limb.NAME)
            centroid_point = limb.geometry.centroid
            here = (centroid_point.y, centroid_point.x)
#            if parent_geom.intersects(limb.geometry) and parent_geom.intersection(limb.geometry).area > 0.0001:
            if parent_geom.intersection(limb.geometry).area > Overlaps[electtype] and newname not in fam_values:
                egg = TreeNode(newname, limb.FID, here,self.level+1,c_election)
                print ("________limb selected and added:",electtype,newname, self.level+1)
                egg = self.add_Tchild(egg, electtype, c_election)
                [egg.bbox, centroid] = egg.get_bounding_box(block)
                print (f"________bbox [{egg.bbox}] - child of type:{electtype} at lev {self.level+1} of {self.value}")
                fam_nodes.append(egg)
                egg.updateParty()
                egg.updateTurnout()
                egg.updateElectorate("0")
                register_node(egg)

            i = i + 1


        if len(fam_nodes) == 0:
            print (f"________no children of type:{electtype} at lev {self.level+1} for {self.value}")

        print (f"___ at {self.value} lev {self.level} revised {electtype} type fam nodes:{fam_nodes}")

        print ("_________fam_nodes :", i, fam_nodes )

        return fam_nodes




    def create_area_map(self, flayers, CE, CEdata):
        global SERVER_PASSWORD
        global STATICSWITCH
        global OPTIONS

        from folium import IFrame


        print(f"___BEFORE cal creation: in route {route()} creating cal for: ", self.value)


#        maptype = flayers[0].key
#        calfile = self.create_area_cal(CE,CEdata, maptype)
#        print(f"___AFTER cal creation: in route {route()} created file: ", calfile)

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
            location=self.centroid,
            zoom_start=LEVEL_ZOOM_MAP[self.type],
            width='100%',
            height='800px',
            crs='EPSG3857'
        )

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
                    FolMap.location = self.centroid
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

        print("Centroid raw:", self.centroid)
        print(f" ✅ _____saved map file in route: {route()}", target, len(flayers), self.value, self.dir, self.file)

        return FolMap


    def set_bounding_box(self,block):
      longmin = block.Long.min()
      latmin = block.Lat.min()
      longmax = block.Long.max()
      latmax = block.Lat.max()
      print("______Bounding Box:",longmin,latmin,longmax,latmax)
      return [Point(latmin,longmin),Point(latmax,longmax)]

    def get_bounding_box(self, block):
        global Treepolys

        if self.level < 3:
            pfile = Treepolys[gettypeoflevel(self.dir, self.level)]
            pb = pfile[pfile['FID'] == self.fid]
            minx, miny, maxx, maxy = pb.geometry.total_bounds
            pad_lat = (maxy - miny) / 5
            pad_lon = (maxx - minx) / 5
            swne = [
                (miny + pad_lat, minx + pad_lon),  # SW (lat, lon)
                (maxy - pad_lat, maxx - pad_lon)   # NE (lat, lon)
            ]
            roid = pb.dissolve().centroid.iloc[0]

        elif self.level < 5:
            pfile = Treepolys[gettypeoflevel(self.dir, self.level)]
            pb = pfile[pfile['FID'] == self.fid]
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

    def add_Tchild(self, child_node, etype, elect):
        global TREK_NODES
        # creates parent-child relationship
        self.child = child_node
        child_node.parent = self
        self.children.append(child_node)
        child_node.type = etype
        child_node.level = child_node.parent.level + 1
        child_node.dir = child_node.parent.dir+"/"+child_node.value
        child_node.tagno = len([x for x in self.children if etype == x.type])
        # --- Logic during node addition (Run for each HTTP call) ---

        counters = get_counters(session)
        # Ensure the counter for this type exists and starts at 0 for 1-based indexing
        if etype not in counters:
            raise Exception("layerCounter type does not exist!")

        # 1. Calculate gtagno (1-based)
        counters[etype] += 1
        child_node.gtagno = counters[etype]

        # The session object automatically saves the updated counters
        # when the response is sent.
        if etype == 'nation':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'county':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'constituency':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'ward':
            child_node.dir = child_node.parent.dir+"/WARDS/"+child_node.value
            child_node.file = child_node.value+"-WARDS.html"
        elif etype == 'division':
            child_node.dir = child_node.parent.dir+"/DIVS/"+child_node.value
            child_node.file = child_node.value+"-DIVS.html"
        elif etype == 'polling_district':
            child_node.dir = child_node.parent.dir+"/PDS/"+child_node.value
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'walk':
            child_node.dir = child_node.parent.dir+"/WALKS/"+child_node.value
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'street':
            child_node.dir = child_node.parent.dir
            child_node.file = child_node.parent.value+"--"+child_node.value+"-PRINT.html"
        elif etype == 'walkleg':
            child_node.dir = child_node.parent.dir
            child_node.file = child_node.parent.value+"--"+child_node.value+"-PRINT.html"

        child_node.election = elect

        print("_________new child node dir:  ",child_node.dir)
        register_node(child_node)

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

        self.file = results_filename
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
        first = stepify(self.dir+"/"+self.file)
        second = stepify(path)
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


from collections import defaultdict

def build_nodemap_list_html(herenode):
    """
    Build HTML tooltip listing all children of a node.
    Returns a string of safe HTML.
    """

    if not herenode or not getattr(herenode, "children", None):
        return "<em>No children</em>"

    items_html = []

    for child in herenode.children:
        # Safely escape for HTML
        label = getattr(child, "name", None) or getattr(child, "value", "") or "Unnamed"
        label = html.escape(str(label))

        items_html.append(f"<li>{label}</li>")

    # Wrap in tooltip-friendly minimal markup
    tooltip_html = "<ul style='margin:0; padding-left:1em;'>" + "".join(items_html) + "</ul>"

    return tooltip_html


def build_street_list_html(streets_df):
    # Voting intention map
    VID = {
        "R": "Reform", "C": "Conservative", "S": "Labour", "LD": "LibDem", "G": "Green",
        "I": "Independent", "PC": "Plaid Cymru", "SD": "SDP", "Z": "Maybe", "W": "Wont Vote", "X": "Won't Say"
    }

    from collections import Counter

    def count_units_from_column(df, column):
        # count of all unique house numbers or names in the column across all electors
        all_units = (
            unit.strip()
            for row in df[column].dropna()
            for unit in str(row).split(',')
            if unit.strip().lower() != 'nan' and unit.strip() != ''
        )
        return Counter(all_units)


    def extract_unit(row):
        # building a new unit column value by combining the contents of AddressNumber and AddressPrefix
        prefix = str(row['AddressPrefix']).strip() if pd.notna(row['AddressPrefix']) else ''
        number = str(row['AddressNumber']).strip() if pd.notna(row['AddressNumber']) else ''

        # Return the first valid field (not empty, not "nan")
        if prefix and prefix.lower() != 'nan':
            return prefix
        if number and number.lower() != 'nan':
            return number
        return None


    streets_df['unit'] = streets_df.apply(extract_unit, axis=1)
    print(f"____Street_df:{streets_df['unit']} ")

    html = '''
    <div style="
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 10px;
        background-color: black; !important;
        color: white; !important;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.1);
        max-width: 600px;
        overflow-x: auto;
        font-family: sans-serif;
        font-size: 8pt;
        white-space: nowrap;
    ">
        <table style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr>
                    <th style="text-align:left; padding: 4px;">Street Name</th>
                    <th style="text-align:left; padding: 4px;">Total</th>
                    <th style="text-align:left; padding: 4px;">Range</th>
                    <th style="text-align:left; padding: 4px;">Unit</th>
                    <th style="text-align:left; padding: 4px;">VI</th>
                    <th style="text-align:left; padding: 4px;">Votes</th>
                </tr>
            </thead>
            <tbody>
    '''
    unit_set = set()
    num_values = set()

    # Now group by street name and extract per-unit counts
    for street_name, street_group in streets_df.groupby("StreetName"):
        # Inside your loop for street_name, street_group in streets_df.groupby("Name"):
        unit_counts = count_units_from_column(street_group, 'unit')

        # JSON version for embedding in HTML
        unit_counts_json = json.dumps(unit_counts)

        print(f"Street: {street_name}")
        print(f"Unit Counts: {unit_counts}")
        print(f"JSON: {unit_counts_json}")

        unit_set = set()
        num_values = []

        for _, row in street_group.iterrows():  # ✅ only iterate this street's rows
            if pd.notna(row['unit']):
                parts = str(row['unit']).split(',')
                for part in parts:
                    val = part.strip()
                    if val and val.lower() != 'nan':
                        unit_set.add(val)
                        match = re.search(r'\d+', val)
                        if match:
                            num_values.append(int(match.group()))

        unit_list = sorted(unit_set)
        total_units = len(unit_list) or 1
        hos = total_units

        # Address range display
        num_values = sorted(num_values)
        num_display = f"({min(num_values)} - {max(num_values)})" if num_values else "( - )"

        # Unit dropdown
        unit_dropdown = f'''
        <select onchange="updateMaxVote(this)" style='width: 100%; font-size: 8pt;'>
            {"".join(f'<option value="{u}" data-max="{unit_counts.get(u, 1)}">{u}</option>' for u in unit_list)}
        </select>
        '''

        # VI select
        vi_select = '<select style="font-size:8pt;">' + ''.join(
            f'<option value="{key}">{value}</option>' for key, value in VID.items()
            ) + '</select>'



        first_unit = unit_list[0] if unit_list else None
        max_votes = unit_counts.get(first_unit, 1) if first_unit else 1



        vote_button = f'''
            <button onclick="incrementVoteCount(this)" data-count="0" data-max="{max_votes}" style="font-size: 8pt;">0/{max_votes}</button>
        '''
        print(f"unit_dropdown: {unit_dropdown}")
        print(f"vi_select: {vi_select}")
        print(f"vote_button: {vote_button}")

        # Add row
        html += f'''
        <tr>
            <td style="padding: 4px; font-size: 8pt;"><b data-name="{street_name}" data-unit-counts='{unit_counts_json}'>{street_name} </b></td>
            <td style="padding: 4px; font-size: 8pt;"><i>{hos}</i></td>
            <td style="padding: 4px; font-size: 8pt;">{num_display}</td>
            <td style="padding: 4px;">{unit_dropdown}</td>
            <td style="padding: 4px;">{vi_select}</td>
            <td style="padding: 4px;">{vote_button}</td>
        </tr>
        '''

    html += '''
            </tbody>
        </table>
    </div>
    '''

    return html

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


def process_lozenges(lozenges, CE):
    """
    Convert lozenges from calendar slots into readable forms.
    """

    activities = []
    resources = []
    tasks = []
    places = []
    areas = []  # kept separate in case area → place mapping is added later


    CE_resources = OPTIONS['resources']
    CE_task_tags = OPTIONS['task_tags']
    CE_areas = OPTIONS['areas']
    CE_places = CE.get("places", {})
    print(f"___Processing resources : {CE_resources} CE_task_tags : {CE_task_tags} CE_areas : {CE_areas} CE_places : {CE_places}")
    for loz in lozenges:
        ltype = loz.get("type")
        code = loz.get("code")

        # AREA ---------------
        if ltype == "area" and code in CE_areas:
            activities.append(CE_areas[code])

        # RESOURCES ----------
        elif ltype == "resource" and code in CE_resources:
            resources.append(code)

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


    return activities, resources, tasks, places, areas


def build_eventlist_dataframe(c_election):
    """
    Produce an eventlist dataframe matching the intent of the JS summary.
    """
    CurrentElection = get_election_data(c_election)

    slots = CurrentElection["calendar_plan"]["slots"]
    rows = []
    print("__Building events from slots:",slots)
    for key, slot in slots.items():
        dt = parse_slot_key(key)

        activities, resources, tasks, places, areas = process_lozenges(
            slot.get("lozenges", []),
            CurrentElection
        )
        if places == "" or places == []:
            continue
        print("datetime", dt,
        "date", dt.date() if dt else None,
        "time", dt.time() if dt else None,
        "places", places,   # contains lat/lng/url etc.
        "areas", areas)

        rows.append({
            "datetime": dt,
            "date": dt.date() if dt else None,
            "time": dt.time() if dt else None,
            "activities": activities,
            "resources": resources,
            "tasks": tasks,
            "places": places,   # contains lat/lng/url etc.
            "areas": areas,     # kept separate
            "availability": slot.get("availability"),
            "raw_key": key,
            "lozenges": slot.get("lozenges", [])
        })


    df = pd.DataFrame(rows, columns=["datetime",
                "date",
                "time",
                "activities",
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


class ExtendedFeatureGroup(FeatureGroup):
    def __init__(self, name=None, overlay=True, control=True, show=True, type=None, id=None, **kwargs):
        # Pass standard arguments to the base class
        super().__init__(name=name, overlay=overlay, control=control, show=show, **kwargs)
        self.name = name
        self.id = id
        self.areashtml = {}

    def reset(self):
        # This clears internal children before rendering
        self._children.clear()
        self.areashtml = {}
        print("____reset the layer",len(self._children), self)
        return self


    def generate_voronoi_with_geovoronoi(self, c_election, target_node, vtype, static=False, add_to_map=True, color="#3388ff"):
        global allelectors
        global levelcolours
    # generate voronoi fields within the target_node Boundary
        shapecolumn = { 'polling_district' : 'PD','walk' : 'WalkName' ,'ward' : 'Area', 'division' : 'Area', 'constituency' : 'Area'}

        print("📍 Starting generate_voronoi_with_geovoronoi")

        CurrentElection = get_election_data(c_election)
        print(f"🗳️ Loaded election data for: {c_election}")

        target_path = target_node.mapfile()
        print(f"📁 Target path: {target_path}")

        print(f"📌 Target node: {target_node.value}")

        ttype = target_node.type
        print(f"📂 Territory type: {ttype}")

        pfile = Treepolys[ttype]
        print(f"🗺️ Loaded polygon file for type '{ttype}', records: {len(pfile)}")

        # Select boundary by FID
        Territory_boundary = pfile[pfile['FID'] == target_node.fid]
        print(f"🧭 Filtered territory boundary by FID = {target_node.fid}, matches: {len(Territory_boundary)}")

        # Get the shapely polygon for area
        if hasattr(Territory_boundary, 'geometry'):
            area_shape = Territory_boundary.union_all()
            print("✅ Retrieved union of territory boundary geometry")
        else:
            area_shape = Territory_boundary
            print("⚠️ Warning: Territory_boundary has no .geometry — using raw")

        children = target_node.childrenoftype(vtype)
        print(f"👶 Found {len(children)} children of type '{vtype}'")
    # children nodes are the target child Walks/PDs polygons which should fit into area_shape

        if not children:
            print("⚠️ No children found so no fields for the node— exiting early")
            # no children means no fields
            return []

        # Build coords array from centroids
        from shapely.ops import nearest_points

        mask = (
                (allelectors['Election'] == c_election) &
                (allelectors['Area'] == target_node.value)
            )
        nodeelectors = allelectors[mask]
# these are the electors within the area - the area being the Level 4 area(div/ward)

        coords = []
        valid_children = []

        for child in children:
# these are the centroids that will form the centre of each voronoi field
            cent = child.centroid
            if isinstance(cent, (tuple, list)) and len(cent) == 2:
                lon, lat = cent[1], cent[0]  # Note: [lon, lat] = [x, y]
            elif hasattr(cent, 'x') and hasattr(cent, 'y'):
                lon, lat = cent.x, cent.y
            else:
                continue

            point = Point(lon, lat)

# Ensure the child centroid is within the overall boundary else centroid of first street within
            if not area_shape.contains(point):
#                childx = target_node.ping_node(c_election,child.dir)
#                print(f"Point {point} is not in shape so looking at children:",[x.value for x in child.children])


                p1, _ = nearest_points(area_shape, point)
                point = p1  # now point is on area_shape
                print(f"Point {point} is not in shape {area_shape} so looking at nearest point")

#                for grandchild in child.children:
#                    cent = grandchild.centroid
#                    point = Point(cent[1],cent[0])
#                    if area_shape.contains(point):
#                        print("___Selecting right child within shape as field centroid", grandchild.dir, point)
#                       found a child inside the area
#                        break
    #                point, _ = nearest_points(area_shape, point)

            coords.append([point.x, point.y])  # Ensure only 2D coords
            valid_children.append((child, point))

        # Clip Voronoi regions to area_shape

        print("🧮 Generating Voronoi regions using geovoronoi...")
        # Pass coords as a list of Point objects
        coords = np.array(coords)
        # Ensure 2D shape
        if coords.shape[1] != 2:
            raise ValueError(f"Expected 2D coordinates, got shape: {coords.shape}")
        try:
            region_polys, region_pts = voronoi_regions_from_coords(coords, area_shape)
            print(f"🗺️ Generated {len(region_polys)} Voronoi polygons")
        except Exception as e:
            print("❌ Error during Voronoi generation:", e)
            return []

        matched = set()
        voronoi_regions = []

        for region_index, region_polygon in region_polys.items():
            if region_polygon.is_empty or not region_polygon.is_valid:
                continue

            matched_child = None
            for child, centroid in valid_children:
                if centroid.within(region_polygon) and child not in matched:
                    matched_child = child
                    matched.add(child)
                    break

            if matched_child:
            #  one walk child matched to region_polygon
                matched_child.voronoi_region = region_polygon
                print(f"✅ Region {region_index} assigned to child: {matched_child.value}")
                voronoi_regions.append({'child': matched_child, 'region': region_polygon})
            else:
                print(f"⚠️ No matching child found for region index {region_index}")


            if matched_child and add_to_map:
                label = str(matched_child.value)

                # Here, we dynamically assign a color, either from the child or default to color
                fill_color = getattr(child, "col", color)  # If no color assigned, default to passed color

                # You can also dynamically generate colors based on the child or other parameters
                # For example, using a hash of the child's value to generate a unique color:
                # fill_color = '#' + hashlib.md5(str(child.value).encode()).hexdigest()[:6]

                mask1 = nodeelectors[shapecolumn[vtype]] == child.value
                region_electors = nodeelectors[mask1]
#________________________First get the data that the walk layer polygon fields requires
                if not region_electors.empty and len(region_electors.dropna(how="all")) > 0:
                    Streetsdf = pd.DataFrame(region_electors, columns=['StreetName', 'ENOP','Long', 'Lat', 'Zone','AddressNumber','AddressPrefix' ])
#                    Streetsdf1 = Streetsdf0.rename(columns= {'StreetName': 'Name'})
#                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count', 'Zone' : 'first', 'AddressNumber': Hconcat , 'AddressPrefix' : Hconcat,}
#                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count', 'Zone' : 'first','AddressNumber': lambda x: ','.join(x.dropna().astype(str)),
#                        'AddressPrefix': lambda x: ','.join(x.dropna().astype(str))
#                        }
#                    Streetsdf = Streetsdf0.groupby(['StreetName']).agg(g).reset_index()
#    build the area html for dropdowns and tooltips
                    streetstag = build_street_list_html(Streetsdf)
                    streets = Streetsdf["StreetName"].unique().tolist()
                    self.areashtml[matched_child.value] = {
                                        "code": matched_child.value,
                                        "details": streets,
                                        "tooltip_html": streetstag
                                        }
                    print (f"______Voronoi html at : {matched_child.value} details {streets} tooltip html:{streetstag}")
                    print ("______Voronoi Streetsdf:",len(Streetsdf), streetstag)
                    print (f" {len(Streetsdf)} streets exist in {target_node.value} under {c_election} election for the {shapecolumn[vtype]} column with this value {child.value}")

                    points = [Point(lon, lat) for lon, lat in zip(Streetsdf['Long'], Streetsdf['Lat'])]
                    print('_______Walk Shape', matched_child.value, matched_child.level, len(Streetsdf), points)

                    # Create a single MultiPoint geometry that contains all the points
                    multi_point = MultiPoint(points)
                    centroid = multi_point.centroid

                    # Access coordinates
                    centroid_lon = centroid.x
                    centroid_lat = centroid.y
    #                target_node.centroid = (centroid_lat,centroid_lon)

                    # Create a new DataFrame for a single row GeoDataFrame
                    gdf = gpd.GeoDataFrame({
                        'NAME': [matched_child.value],  # You can modify this name to fit your case
                        'FID': [matched_child.fid],  # FID can be a unique value for the row
                        'LAT': [multi_point.centroid.y],  # You can modify this name to fit your case
                        'LONG': [multi_point.centroid.x],  # FID can be a unique value for the row
                        'geometry': [multi_point]  # The geometry field contains the MultiPoint geometry
                    }, crs="EPSG:4326")


                    #            limb = gpd.GeoDataFrame(df, geometry= [convex], crs='EPSG:4326')
                    #        limb = gpd.GeoDataFrame(df, geometry= [circle], crs="EPSG:4326")
                    # Generate enclosing shape
                    limbX = matched_child.create_enclosing_gdf(gdf)
                    limbX['col'] = matched_child.col
                    numtag = str(matched_child.tagno)+" "+str(matched_child.value)
                    num = str(matched_child.tagno)
                    tag = str(matched_child.value)
                    typetag = "streets in "+str(matched_child.type)+" "+str(matched_child.value)
            #        here = [float(f"{target_node.centroid[0]:.6f}"), float(f"{target_node.centroid[1]:.6f}")]

                    popup_html = ""

                    if vtype == 'polling_district':
                        showmessageST = "showMore(&#39;/PDdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.dir+"/"+matched_child.file +" street", matched_child.value,'street')
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.parent.dir+"/"+matched_child.parent.file, matched_child.parent.value,matched_child.parent.type)
                    #            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(target_node.dir+"/"+target_node.file, target_node.value,getchildtype('polling_district'))
                        downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
                    #            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
                    #            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,session.get('importfile'), target_node.dir+"/"+target_node.file)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limbX['UPDOWN'] = uptag1 +"<br>"+ downST
                        print("_________new PD convex hull and tagno:  ",matched_child.value, matched_child.tagno, gdf)

                        streetstag = ""
                    elif vtype == 'walk':
                        showmessage = "showMore(&#39;/WKdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.dir+"/"+matched_child.file+" walkleg", matched_child.value,'walkleg')
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.parent.dir+"/"+matched_child.parent.file, matched_child.parent.value,matched_child.parent.type)
                        downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        streetstag = build_street_list_html(Streetsdf)
                        limbX['UPDOWN'] =  "<div style='white-space: normal'>" + uptag1 +"<br>"+downtag+"</div>"
                        print("_________new Walk convex hull and tagno:  ",matched_child.value, matched_child.tagno)

    #________________________Now paint items onto the walk layer
                    if not static:
                        limbX = limbX.to_crs("EPSG:4326")
                        limb = limbX.iloc[[0]].__geo_interface__ # Ensure this returns a GeoJSON dictionary for the row

                        feature = limb['features'][0]
                        props = feature['properties']
                        popup_html = f"""
                        <div style='white-space: normal; text-align: center' >
                            <strong> {typetag}:<br></strong> {props.get('UPDOWN', 'N/A')}<br> {streetstag}<br>
                        </div>
                        """

                        popup = folium.Popup(popup_html, max_width=600)
                        #        target_node.tagno = len(self._children)+1
                        pathref = matched_child.mapfile()
                        mapfile = '/transfer/'+pathref
                        # Turn into HTML list items

                        # Ensure 'properties' exists in the GeoJSON and add 'col'
                        print("GeoJSON Convex creation:", limb)
                        if 'properties' not in limb:
                            limb['properties'] = {}

                        # Add the color to properties — this is **required**
                        limb['properties']['col'] = to_hex(matched_child.col)

                        geojson_feature = {
                            "type": "Feature",
                            "properties": {"col": fill_color},
                            "geometry": region_polygon.__geo_interface__,
                        }
                        gj = folium.GeoJson(
                            data=json.loads(json.dumps(geojson_feature)),
                            style_function=lambda feature: {
                                'fillColor': feature["properties"]["col"],
                                'color': '#FFFFFF',     # white border
                                'weight': 4,            # thinner, adjustable
                                'fillOpacity': 0.4,
                                'opacity': 1.0,         # ensure stroke visible
                                'stroke': True,         # explicitly enable stroke
                            },
                            name=f"Voronoi {label}",
                            tooltip=folium.Tooltip(label),
                            popup=popup,
                        )
                        gj.add_to(self)
                        print(f"🖼️ Added Non-static GeoJson for child: {label} nodecol: {child.col} with color: {fill_color}")

                        centroid = region_polygon.centroid
                        cent = [centroid.y, centroid.x]  # folium expects (lat, lon)

                        tag = matched_child.value

                        mapfile = matched_child.mapfile()

                        tcol = get_text_color(to_hex(fill_color))
                        bcol = adjust_boundary_color(to_hex(fill_color), 0.7)
                        fcol = invert_black_white(tcol)
                        self.add_child(folium.Marker(
                             location=[cent[0], cent[1]],
                             icon = folium.DivIcon(
                                    html=f'''
                                    <a href="{mapfile}" data-name="{tag}">
                                        <div style="
                                            color: {tcol};
                                            font-size: 10pt;
                                            font-weight: bold;
                                            text-align: center;
                                            padding: 2px;
                                            white-space: nowrap;">
                                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                            border: 2px solid black;">{tag}</span>
                                        </div>
                                    </a>
                                    '''
                                    ,
                                   )
                                   )
                                   )
                    else:
                        limbX = limbX.to_crs("EPSG:4326")
                        limb = limbX.iloc[[0]].__geo_interface__ # Ensure this returns a GeoJSON dictionary for the row

                        feature = limb['features'][0]
                        props = feature['properties']
                        popup_html = f"""
                        <div style='white-space: normal; text-align: center' >
                            <strong> {typetag}:<br></strong> <br> {streetstag}<br>
                        </div>
                        """
                        # Turn into HTML list items
                        popup = folium.Popup(popup_html, max_width=600)
                        #        target_node.tagno = len(self._children)+1
                        # Turn into HTML list items
                        # Ensure 'properties' exists in the GeoJSON and add 'col'
                        print("GeoJSON Convex creation:", limb)
                        if 'properties' not in limb:
                            limb['properties'] = {}

                        # Add the color to properties — this is **required**
                        limb['properties']['col'] = to_hex(matched_child.col)

                        geojson_feature = {
                            "type": "Feature",
                            "properties": {"col": fill_color},
                            "geometry": region_polygon.__geo_interface__,
                        }
                        gj = folium.GeoJson(
                            data=json.loads(json.dumps(geojson_feature)),
                            style_function=lambda feature: {
                                'fillColor': feature["properties"]["col"],
                                'color': '#FFFFFF',     # white border
                                'weight': 4,            # thinner, adjustable
                                'fillOpacity': 0.4,
                                'opacity': 1.0,         # ensure stroke visible
                                'stroke': True,         # explicitly enable stroke
                            },
                            name=f"Voronoi {label}",
                            tooltip=folium.Tooltip(label),
                            popup=popup,
                        )
                        gj.add_to(self)

                        print(f"🖼️ Added Static GeoJson for child: {label} nodecol: {child.col} with color: {fill_color}")

                        centroid = region_polygon.centroid
                        cent = [centroid.y, centroid.x]  # folium expects (lat, lon)

                        tag = matched_child.value

                        tcol = get_text_color(to_hex(fill_color))
                        bcol = adjust_boundary_color(to_hex(fill_color), 0.7)
                        fcol = invert_black_white(tcol)
                        self.add_child(folium.Marker(
                             location=[cent[0], cent[1]],
                             icon = folium.DivIcon(
                                    html=f'''
                                    <a data-name="{tag}">
                                        <div style="
                                            color: {tcol};
                                            font-size: 10pt;
                                            font-weight: bold;
                                            text-align: center;
                                            padding: 2px;
                                            white-space: nowrap;">
                                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                            border: 2px solid black;">{tag}</span>
                                        </div>
                                    </a>
                                    '''
                                    ,
                                   )
                                   )
                                   )
                    print(f"🖼️ Added walk area marker: {tag} with color: {tcol}")

                voronoi_regions.append({
                    'child': matched_child,
                    'region': region_polygon
                })
            else:
                flash("no data exists for this election at this location")
                print (f" no walks exist for this region {region_polygon} under this {c_election} election ")

        print("✅ Voronoi generation complete.")
        return voronoi_regions



    def add_shapenodes (self,c_election,herenode,stype):
        global allelectors
# add a convex hull for all zonal children nodes , using all street centroids contained in each zone
# zonal nodes are added at same time as walk nodes, zone nodes generated from zone grouped means of electors
# children of zones gnerated by a downZO route similar to downWK
# zone hull data generated from zone mask of areaelectors.
        shapecolumn = { 'polling_district' : 'PD','walk' : 'WalkName' ,'ward' : 'Area', 'division' : 'Area', 'constituency' : 'Area'}
# if there is a selected file , then allelectors will be full of records
        print(f"____adding_shapenodes in election {c_election} layer {self.id} for {herenode.value} of type {stype}:")

        mask = allelectors['Election'] == c_election
        nodeelectors = allelectors[mask]
#        mask2 = areaelectors[shapecolumn[stype]] == herenode.value
#        nodeelectors = areaelectors[mask2]
        # Step 2: Group by WalkName and compute mean lat/long (already done)

# now produce the shapes - one for each walk in the area
        shapenodelist = herenode.childrenoftype(stype)
        for shape_node in shapenodelist:
            colname = shapecolumn[stype]

            if colname not in nodeelectors.columns:
                print(f"❌ Column '{colname}' not found in nodeelectors!")
                print(f"Available columns: {list(nodeelectors.columns)}")
                continue  # skip to next shape_node

            print(f"🔍 Comparing values in column '{colname}' to shape_node.value = {shape_node.value}")
            print(f"🔍 Unique values in column '{colname}': {nodeelectors[colname].unique()}")

            # Optional: check for type mismatch
            print(f"📏 Types — column: {nodeelectors[colname].dtype}, shape_node.value: {type(shape_node.value)}")

            mask2 = nodeelectors[shapecolumn[stype]] == shape_node.value
            shapeelectors = nodeelectors[mask2]
        #
            print (f"______shapenode:{shape_node.value} child type : {stype}  col {shapecolumn[stype]} siblings: {len(shapenodelist)} and election {shape_node.election}")
            print(f"___Zone type: {shapecolumn[stype]} at {shape_node.value} NodeNo: {len(shapeelectors)} AreaNo: {len(nodeelectors)} AllNo: {len(allelectors)}"  )
    #even though nodes have been created,the current election view might not match
            if not shapeelectors.empty and len(shapeelectors.dropna(how="all")) > 0:
                Streetsdf0 = pd.DataFrame(shapeelectors, columns=['StreetName', 'ENOP','Long', 'Lat', 'Zone','AddressNumber','AddressPrefix' ])
                Streetsdf1 = Streetsdf0.rename(columns= {'StreetName': 'Name'})
                g = {'Lat':'mean','Long':'mean', 'ENOP':'count', 'Zone' : 'first', 'AddressNumber': Hconcat , 'AddressPrefix' : Hconcat,}
                Streetsdf = Streetsdf1.groupby(['Name']).agg(g).reset_index()
                print ("______Streetsdf:",Streetsdf)
                self.add_shapenode(shape_node, stype,Streetsdf)
                print("_______new shape node ",shape_node.value,shape_node.col,"|")
            else:
                flash("no data exists for this election at this location")
                print (f"_nodes exist at {herenode.value} but not for this {c_election} election and this {shapecolumn[stype]} column with this value {shape_node.value}")

        return self._children



    def add_shapenode (self,herenode,type,datablock):
        global levelcolours

        points = [Point(lon, lat) for lon, lat in zip(datablock['Long'], datablock['Lat'])]
        print('_______Walk Shape', herenode.value, herenode.level, len(datablock), points)

        # Create a single MultiPoint geometry that contains all the points
        multi_point = MultiPoint(points)
        centroid = multi_point.centroid

        # Access coordinates
        centroid_lon = centroid.x
        centroid_lat = centroid.y
        herenode.centroid = (centroid_lat,centroid_lon)

        # Create a new DataFrame for a single row GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'NAME': [herenode.value],  # You can modify this name to fit your case
            'FID': [herenode.fid],  # FID can be a unique value for the row
            'LAT': [multi_point.centroid.y],  # You can modify this name to fit your case
            'LONG': [multi_point.centroid.x],  # FID can be a unique value for the row
            'geometry': [multi_point]  # The geometry field contains the MultiPoint geometry
        }, crs="EPSG:4326")


#            limb = gpd.GeoDataFrame(df, geometry= [convex], crs='EPSG:4326')
#        limb = gpd.GeoDataFrame(df, geometry= [circle], crs="EPSG:4326")
        # Generate enclosing shape
        limbX = herenode.create_enclosing_gdf(gdf)
        limbX['col'] = herenode.col

        if type == 'polling_district':
            showmessageST = "showMore(&#39;/PDdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file +" street", herenode.value,'street')
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
#            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling_district'))
            downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
#            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
#            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,session.get('importfile'), herenode.dir+"/"+herenode.file)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limbX['UPDOWN'] = uptag1 +"<br>"+ downST
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno, gdf)
        elif type == 'walk':
            showmessage = "showMore(&#39;/WKdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file+" walkleg", herenode.value,'walkleg')
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
            downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            streetstag = build_street_list_html(datablock)
            limbX['UPDOWN'] =  "<div style='white-space: normal'>" + uptag1 +"<br>"+ downtag+"<br>"+ streetstag+"<br></div>"
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)


#        herenode.tagno = len(self._children)+1
        numtag = str(herenode.tagno)+" "+str(herenode.value)
        num = str(herenode.tagno)
        tag = str(herenode.value)
        typetag = "streets in "+str(herenode.type)+" "+str(herenode.value)
        here = [float(f"{herenode.centroid[0]:.6f}"), float(f"{herenode.centroid[1]:.6f}")]
        pathref = herenode.mapfile()
        mapfile = '/transfer/'+pathref
        # Turn into HTML list items


        limbX = limbX.to_crs("EPSG:4326")
        limb = limbX.iloc[[0]].__geo_interface__ # Ensure this returns a GeoJSON dictionary for the row

        # Ensure 'properties' exists in the GeoJSON and add 'col'
        print("GeoJSON Convex creation:", limb)
        if 'properties' not in limb:
            limb['properties'] = {}

        # Add the color to properties — this is **required**
        limb['properties']['col'] = to_hex(herenode.col)

        # Now you can use limb_geojson as a valid GeoJSON feature
        print("GeoJSON Convex Hull Feature:", limb)
        tcol = get_text_color(to_hex(herenode.col))
        bcol = adjust_boundary_color(to_hex(herenode.col),0.7)
        fcol = invert_black_white(tcol)


        if herenode.type == 'walk':
            # Extract the only feature from the GeoJSON object
            feature = limb['features'][0]
            props = feature['properties']

            # Build custom HTML popup with styling
            popup_html = f"""
            <div style='white-space: normal; text-align: center' >
                <strong> {typetag}:<br></strong> {props.get('UPDOWN', 'N/A')}
            </div>
            """

            # Create folium.Popup from the HTML
            popup = folium.Popup(popup_html, max_width=600)

            # Add the feature to the map
            folium.GeoJson(
                data=feature,
                style_function=lambda x: {
                    "fillColor": x['properties']['col'],
                    "color": bcol,
                    "dashArray": "5, 5",
                    "weight": 3,
                    "fillOpacity": 0.5
                },
                highlight_function=lambda x: {"fillColor": 'lightgray'},
                popup=popup
            ).add_to(self)

            self.add_child(folium.Marker(
                 location=here,
                 icon = folium.DivIcon(
                        html=f'''
                        <a href='{mapfile}' data-name='{tag}'><div style="
                            color: {tcol};
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{tag}</span>
                            </div></a>
                            ''',
                       )
                       )
                       )
        else:
    # Extract the only feature from the GeoJSON object
            feature = limb['features'][0]
            props = feature['properties']

            # Build custom HTML popup content with centered styling
            popup_html = f"""
            <div style='white-space: normal;text-align: center;'>
                <strong> {typetag}:<br></strong> {props.get('UPDOWN', 'N/A')}
            </div>
            """.strip()

            # Create a folium.Popup using the HTML string
            popup = folium.Popup(popup_html, max_width=600)

            # Add the GeoJson feature with the popup to the map
            folium.GeoJson(
                data=feature,
                highlight_function=lambda x: {"fillColor": 'lightgray'},
                popup=popup,
                popup_keep_highlighted=False,
                style_function=lambda x: {
                    "fillColor": x['properties']['col'],
                    "color": bcol,
                    "dashArray": "5, 5",
                    "weight": 3,
                    "fillOpacity": 0.9
                }
            ).add_to(self)


            self.add_child(folium.Marker(
                 location=here,
                 icon = folium.DivIcon(
                        html=f'''
                        <a href='{mapfile}' data-name='{tag}'><div style="
                            color: {tcol};
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{num}</span>
                            {tag}</div></a>
                            ''',
                       )
                       )
                       )
        print("________Layer map polys",herenode.value,herenode.level,self._children)
        return self._children

    def create_layer(self, c_election, node, intention_type, static=False):
        global allelectors
        global places
        global OPTIONS
        CurrentElection = get_election_data(c_election)
        print(f"__Layer id:{self.id} value:{node.value} type: {intention_type} layer children:{len(self._children)} node children:{len(node.children)}")
        if intention_type == 'marker':
            # always regen markers if CurrentElection['accumulate'] is false
            if not CurrentElection['accumulate']:
                self._children.clear()
            entrylen = len(self._children)
            print("Markers . . ACCUMULATING from",entrylen)
            self.id = node.fid
            self.add_genmarkers(c_election,node,'marker',static)
            return len(self._children) - entrylen
        entrylen = len(self._children)
        if len(node.children) > 0:
    # each layer content is identified by the node id at which it created, so new node new content, same node old content
            if self.id != node.value: # new node new content
                if not CurrentElection['accumulate']:
                    self._children.clear()
                entrylen = len(self._children)
                print("ACCUMULATING from",entrylen)
                self.id = node.fid
        # create the content for an existing layer derived from the node children and required type
                if intention_type == 'street' or intention_type == 'walkleg':
                    self.add_nodemarks(node,intention_type,static)
                elif intention_type == 'polling_district' or intention_type == 'walk':
                    print(f"calling creation of voronoi in {c_election} - node {node.value} type {intention_type}")
    #                self.add_shapenodes(c_election,node,intention_type)
                    self.generate_voronoi_with_geovoronoi(c_election,node,intention_type, static)
                    print(f"created {len(self._children)} voronoi in {c_election} - node {node.value} type {intention_type} static:{static}")
                elif intention_type == 'marker':
                    print("Markers 2 ACCUMULATING from",entrylen)
                    self.add_genmarkers(node,'marker',static)
                else:
                    self.add_nodemaps(node, intention_type, static, ACC=OPTIONS['ACC'])
            else: #no change - same node old content
            # each layer content is identified by the node id at which it created, so new node new content, same node old content
                self.id = 0
                print("___New Layer with node.value = self.id ie it already exists :", self.id)
                #the exist id = the new id , dont do anything
        return len(self._children) - entrylen


    def add_genmarkers(self, c_election, node, type, static):

        eventlist = build_eventlist_dataframe(c_election)
        print(f" ___GenMarkers: from {c_election} to {eventlist}")
        for _, row in eventlist.iterrows():

            for place in row["places"]:
                lat = place["lat"]
                lng = place["lng"]
                tag = place["prefix"]
                url = place["url"]

                days_to = (row["date"] - datetime.today().date()).days
                fontsize = compute_font_size(days_to)

                tooltip = f"{tag} ({row['date']})"
                print(f"___layer marker: {tag} at {lat},{lng} on {row['date']}")

                self.add_child(folium.Marker(
                    location=[lat, lng],
                    tooltip=tooltip,
                    icon=folium.DivIcon(html=f"""
                        <a href='{url}' data-name='{tag}'>
                            <div style="color:yellow;font-weight:bold;text-align:center;padding:2px;">
                                <span style="font-size:{fontsize}px;background:red;padding:1px 2px;
                                             border-radius:5px;border:2px solid black;">
                                    {days_to}
                                </span> {tag}
                            </div>
                        </a>
                    """)
                ))

        return eventlist



    def add_nodemaps (self,herenode,type,static, ACC=False):
        global Treepolys
        global levelcolours
        global Con_Results_data
        global OPTIONS

        childlist = herenode.childrenoftype(type)
        nodeshtml = build_nodemap_list_html(herenode)
        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
                            "code": herenode.value,
                            "details": details,
                            "tooltip_html": nodeshtml
                            }

        print("_________Nodemap:",herenode.value,type, [x.type for x in childlist],len(herenode.children), len(childlist))

        for c in childlist:
            print("______Display children:",herenode.value, c.value,type)
#            layerfids = [x.fid for x in self._children if x.type == type]
#            if c.fid not in layerfids:
            if c.level+1 <= 5:
                results = []
    #need to select the children boundaries associated with the children nodes - to paint
                pfile = Treepolys[type]
                mask = pfile['FID']==c.fid
                limbX = pfile[mask].copy()
                if len(limbX) > 0:
                    print("______Add_Nodes Treepolys type:",type)
    #
                    limbX['col'] = c.col

                    if herenode.level == 0:
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" county", c.value,getchildtype(c.type))
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,herenode.type)
                        downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,getchildtype(c.type),12)
    #                    res = "<p  width=50 id='results' style='font-size: {0}pt;color: gray'> </p>".format(12)
                        uptag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limbX['UPDOWN'] = uptag+"<br>"+c.value+"<br>"  + downtag
    #                    c.tagno = len(self._children)+1
                        mapfile = "/transfer/"+c.mapfile()
    #                        self.children.append(c)
                    elif herenode.level == 1:
                        wardreportmess = "moveDown(&#39;/wardreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                        divreportmess = "moveDown(&#39;/divreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" constituency", c.value,getchildtype(c.type))
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
                        wardreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(wardreportmess,"WARD Report",12)
                        divreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(divreportmess,"DIV Report",12)
                        downconstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"CONSTITUENCIES",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ wardreporttag + divreporttag+"<br>"+ downconstag
    #                    c.tagno = len(self._children)+1
                        mapfile = "/transfer/"+c.mapfile()
    #                        self.children.append(c)
                    elif herenode.level == 2:
                        downwardmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" ward", c.value,"ward")
                        downdivmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" division", c.value,"division")
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
                        downwardstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downwardmessage,"WARDS",12)
                        downdivstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downdivmessage,"DIVS",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)

                        limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ downwardstag + " " + downdivstag
    #                    c.tagno = len(self._children)+1
                        mapfile = "/transfer/"+c.mapfile()
    #                        self.children.append(c)
                    elif herenode.level == 3:
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
    #                upload = "<input id='importfile' type='file' name='importfile' placeholder='{1}' style='font-size: {0}pt;color: gray'></input>".format(12, session.get('importfile'))

                        PDbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downPDbut/{0}", "{1}", "polling_district");' class='btn btn-norm'>
                                PDs
                            </button>
                        """.format(c.dir+"/"+c.file+" polling_district", c.value)

                        WKbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downWKbut/{0}", "{1}", "walk");' class='btn btn-norm'>
                                WALKS
                            </button>
                        """.format(c.dir+"/"+c.file+" walk", c.value)

                        MWbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downMWbut/{0}", "{1}", "walk");' class='btn btn-norm'>
                                STAT
                            </button>
                        """.format(c.dir+"/"+c.file+" walk", c.value)


                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size:{2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)

                        if not static:
                            limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+PDbtn+" "+WKbtn+" "+MWbtn
                        else:
                            limbX['UPDOWN'] = "<br>"+c.value+"<br>"
    #                    c.tagno = len(self._children)+1
                        pathref = c.mapfile()
                        mapfile = '/transfer/'+pathref
    #                        self.children.append(c)


                    party = "("+c.party+")"
                    if not OPTIONS['ACC']:
                        num = str(c.tagno)
                    else:
                        num = str(c.gtagno)

                    tag = str(c.value)
                    numtag = str(c.value)+party


                    here = [float(f"{c.centroid[0]:.6f}"), float(f"{c.centroid[1]:.6f}")]
                    # Convert the first row of the GeoDataFrame to a valid GeoJSON feature
                    limb = limbX.iloc[[0]].__geo_interface__  # Ensure this returns a GeoJSON dictionary for the row

                    # Ensure 'properties' exists in the GeoJSON and add 'col'
    #                print("GeoJSON creation:", limb)
                    if 'properties' not in limb:
                        limb['properties'] = {}

                    # Now you can use limb_geojson as a valid GeoJSON feature
    #                print("GeoJSON Feature:", limb)

                    tcol = get_text_color(to_hex(c.col))
                    bcol = adjust_boundary_color(to_hex(c.col),0.7)
                    fcol = invert_black_white(tcol)


                    folium.GeoJson(
                        limb,  # This is the GeoJSON feature (not the GeoDataFrame)
                        highlight_function=lambda x: {"fillColor": 'lightgray'},  # Access 'col' in the properties
                        popup=folium.GeoJsonPopup(
                            fields=['UPDOWN'],  # Reference to the 'UPDOWN' property
                            aliases=["Move:"],   # This is the label for the 'UPDOWN' field in the popup
                        ),
                        popup_keep_highlighted=False,
                        style_function=lambda x: {
                            "fillColor": x['properties']['col'],  # Access 'col' in the properties for the fill color
                            "color": bcol,      # Same for the border color
                            "dashArray": "5, 5",
                            "weight": 3,
                            "fillOpacity": 0.2
                        }
                    ).add_to(self)

                    pathref = c.mapfile()
                    mapfile = '/transfer/'+pathref


                    if not static:
                        self.add_child(folium.Marker(
                             location=here,
                             icon = folium.DivIcon(
                                    html=f'''
                                    <a href="{mapfile}" data-name="{tag}"><div style="
                                        color: {tcol};
                                        font-size: 10pt;
                                        font-weight: bold;
                                        text-align: center;
                                        padding: 2px;
                                        white-space: nowrap;">
                                        <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                        border: 2px solid black;">{num}</span>
                                        {numtag}</div></a>
                                        ''',
                                       )
                                       )
                                       )
                    else:
                        self.add_child(folium.Marker(
                             location=here,
                             icon = folium.DivIcon(
                                    html=f'''
                                    <a data-name="{tag}">
                                    <div style="
                                        color: {tcol};
                                        font-size: 10pt;
                                        font-weight: bold;
                                        text-align: center;
                                        padding: 2px;
                                        white-space: nowrap;">
                                        <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                        border: 2px solid black;">{num}</span>
                                        {numtag}</div></a>
                                        ''',
                                       )
                                       )
                                       )


        print("________Layer map polys",herenode.value,herenode.level, len(Featurelayers[gettypeoflevel(herenode.dir,herenode.level+1)]._children))

        return self._children

    def add_nodemarks (self,herenode,type,static):
        global levelcolours

        childlist = herenode.childrenoftype(type)
        nodeshtml = build_nodemap_list_html(herenode)
        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
                            "code": herenode.value,
                            "details": details,
                            "tooltip_html": nodeshtml
                            }
        num = len(herenode.childrenoftype(type))
        print(f"___creating {num} add_nodemarks of type {type} for {herenode.value} at level {herenode.level}")

        for c in [x for x in herenode.childrenoftype(type)]:
            print('_______MAP Markers')
#            layerfids = [x.fid for x in self.children if x.type == type]
#            if c.fid not in layerfids:
            numtag = str(c.tagno)+" "+str(c.value)
            num = str(c.tagno)
            tag = str(c.value)
            here = [float(f"{c.centroid[0]:.6f}"), float(f"{c.centroid[1]:.6f}")]
            fill = herenode.col
            pathref = c.mapfile()
            mapfile = '/transfer/'+pathref

            print("______Display childrenx:",c.value, c.level,type,c.centroid )
            tcol = get_text_color(to_hex(c.col))
            bcol = adjust_boundary_color(to_hex(c.col),0.7)
            fcol = invert_black_white(tcol)

            if not static:
                self.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(
                            html=f'''
                            <a href="{mapfile}" data-name="{tag}"><div style="
                                color: {tcol};
                                font-size: 10pt;
                                font-weight: bold;
                                text-align: center;
                                padding: 2px;
                                white-space: nowrap;">
                                <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                border: 2px solid black;">{num}</span>
                                {tag}</div></a>
                                ''',
                           )
                           )
                           )
            else:
                self.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(
                            html=f'''
                            <a data-name="{tag}">
                            <div style="
                                color: {tcol};
                                font-size: 10pt;
                                font-weight: bold;
                                text-align: center;
                                padding: 2px;
                                white-space: nowrap;">
                                <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                border: 2px solid black;">{num}</span>
                                {tag}</div></a>
                                ''',
                           )
                           )
                           )



        print("________Layer map points",herenode.value,herenode.level,len(self._children))

        return self._children


def Hconcat(house_list):
    # Make sure house_list is iterable and not accidentally a DataFrame or something else
    try:
        return ', '.join(sorted(set(map(str, house_list))))
    except Exception as e:
        print("❌ Error in Hconcat:", e)
        print("Type of house_list:", type(house_list))
        raise


def get_text_color(fill_hex):
    # Convert hex to RGB
    fill_hex = fill_hex.lstrip('#')
    r, g, b = [int(fill_hex[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

    # Calculate luminance
    def adjust(c): return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    lum = 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

    # Contrast against white and black
    white_contrast = (1.05) / (lum + 0.05)
    black_contrast = (lum + 0.05) / 0.05

    return '#ffffff' if white_contrast >= black_contrast else '#000000'

def invert_black_white(hex_color):
    hex_color = hex_color.strip().lower()
    if hex_color in ("#000000", "000000"):
        return "#ffffff"
    elif hex_color in ("#ffffff", "ffffff"):
        return "#000000"
    else:
        return None  # or raise ValueError("Not black or white")

def adjust_boundary_color(fill_hex, factor=0.7):
    fill_hex = fill_hex.lstrip('#')
    r, g, b = [int(fill_hex[i:i+2], 16) / 255.0 for i in (0, 2, 4)]

    # Convert to HLS (Hue, Lightness, Saturation)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Darken or lighten
    new_l = max(0, min(1, l * factor))
    new_r, new_g, new_b = colorsys.hls_to_rgb(h, new_l, s)

    # Back to hex
    return '#{:02x}{:02x}{:02x}'.format(int(new_r*255), int(new_g*255), int(new_b*255))


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

def filterArea(source,sourcekey,roid,destination):
    nodestep = None
# create destination Geojson file of polys which contain a lat long from source file
    gdf = gpd.read_file(source)

# Step 3: Define your lat/lon point
    latitude =roid[0]
    longitude = roid[1]
    point = Point(longitude, latitude)  # Note: Point(long, lat) for Shapely

# Step 4: Ensure same CRS
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    gdf = gdf.rename(columns= {sourcekey: 'NAME'})
    if 'OBJECTID' in gdf.columns:
        gdf = gdf.rename(columns = {'OBJECTID': 'FID'})
    print(" gdf cols:",gdf.columns)

# Step 5: Find matching polygon(s)
    matched = gdf[gdf.contains(point)]
#    print("____are data:",matched, point,gdf)
# Step 6: Save to new GeoJSON if found
    if not matched.empty:
        nodestep = normalname(matched['NAME'].values[0])
        output_path = destination

        matched.to_file(output_path, driver="GeoJSON")
        print(f"Found {len(matched)} matching feature(s). Saved to {output_path}")

    else:
        print("No matching country found for that lat/lon.")
    return [nodestep,matched,gdf]

def intersectingArea(source,sourcekey,roid,parent_gdf,destination):
    nodestep = None
# create destination Geojson file of polys which contain a lat long from source file
    gdf = gpd.read_file(source)
    latitude =roid[0]
    longitude = roid[1]
    point = Point(longitude, latitude)  # Note: Point(long, lat) for Shapely
# Step 1: Ensure same CRS
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf = gdf.rename(columns= {sourcekey: 'NAME'})
    if 'OBJECTID' in gdf.columns:
        gdf = gdf.rename(columns = {'OBJECTID': 'FID'})
    print(" gdf cols:",gdf.columns)

    # Step 2: Find parent intersecting polygon(s)
    parent_geom = parent_gdf.union_all()

    # Step 3 Ensure CRS match
    if gdf.crs != parent_gdf.crs:
        parent_geom = gpd.GeoSeries([parent_geom], crs=parent_gdf.crs).to_crs(gdf.crs).iloc[0]

    # Step 4: Spatial filter using intersects (fast)
    candidates = gdf[gdf.geometry.intersects(parent_geom)]
    matched = gdf[gdf.contains(point)]
    # Step 5: Accurate intersection area filter
    threshold = 0.0001
    filtered = candidates[candidates.geometry.intersection(parent_geom).area > threshold]

#  print("____are data:",matched, point,gdf)
# Step 7: Save to new GeoJSON if found
    if not matched.empty:
        nodestep = normalname(matched['NAME'].values[0])
        output_path = destination

# Step 6: Export to GeoJSON
        filtered.to_file(output_path)
        print(f"Found {len(filtered)} matching feature(s). Saved to {output_path}")

    else:
        print("No poly found to intersect with parent")
    return [nodestep,filtered,gdf]


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

def register_node(node):
    global TREK_NODES
    TREK_NODES[node.fid] = node
#    print("Trek Nodes:",TREK_NODES)
    return

def visit_node(v_node, c_elect,CurrEL, mapfile):
    # Access the first key from the dictionary
    print(f"___under {c_elect} visiting mapfile:", mapfile,CurrEL['mapfiles'])
    CurrEL2 = CurrEL
    CurrEL2['mapfiles'] = capped_append(CurrEL['mapfiles'], mapfile)
    save_election_data(c_elect, CurrEL2)
    session['current_election'] = c_elect
    session['current_node_id'] = v_node.fid
    print(f"___under {c_elect} changed from {CurrEL['mapfiles'][-1]} to mapfile: {CurrEL2['mapfiles'][-1]}")
    return



def reset_nodes():
    global TREK_NODES
    TREK_NODES = {}
    with open(TREKNODE_FILE, 'wb') as f:
        pickle.dump(TREK_NODES, f)
    return


def get_L4area(nodelist, here):
    global Treepolys

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

def route():
    if has_request_context():
        return request.endpoint
    return None  # or a default string like "no_request_context"


def background_normalise(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table):
    global TREK_NODES, allelectors, Treepolys, Fullpolys, current_node,formdata, layeritems, progress

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
            CurrentElection = get_election_data(stream)
            current_node = get_current_node(session_data)

            print('___persisting file ', ELECTOR_FILE, len(allelectors))
            allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)


            territory_path = CurrentElection['mapfiles'][-1] # this is the node at which the imported data is to be filtered through
            Territory_node = current_node.ping_node(current_election,territory_path)
            ttype = gettypeoflevel(territory_path,Territory_node.level)
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
                        Territory_node.ping_node(current_election,tpath)
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
        return node.centroid

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
    return node.centroid

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


ElectionTypes = {"W":"Westminster","C":"County","B":"Borough","P":"Parish","U":"Unitary"}
VID = {"R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"Independent","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}
VNORM = {"OTHER":"O","REFORM" : "R" , "REFORM_DERBY" : "R" ,"REFORM_UK" : "R" ,"REF" : "R", "RUK" : "R","R" :"R","CONSERVATIVE_AND_UNIONIST" : "C","CONSERVATIVE" : "C", "CON" : "C", "C":"C","LABOUR_PARTY" : "S","LABOUR" : "S", "LAB" :"S", "L" : "L", "LIBERAL_DEMOCRATS" :"LD" ,"LIBDEM" :"LD" , "LIB" :"LD","LD" :"LD", "GREEN_PARTY" : "G" ,"GREEN" : "G" ,"G":"G", "INDEPENDENT" : "I", "IND" : "I" ,"I" : "I" ,"PLAID_CYMRU" : "PC" ,"PC" : "PC" ,"SNP": "SNP" ,"MAYBE" : "Z" ,"WONT_VOTE" : "W" ,"WONT_SAY" : "X" , "SDLP" : "S", "SINN_FEIN" : "SF", "SPK": "N", "TUV" : "C", "UUP" : "C", "DUP" : "C","APNI" : "N", "INET": "I", "NIP": "I","PBPA": "I","WPB": "S","OTHER" : "O"}
VCO = {"O" : "brown","R" : "cyan","C" : "blue","S" : "red","LD" :"yellow","G" :"limegreen","I" :"indigo","PC" : "darkred","SD" : "orange","Z" : "lightgray","W" :  "white", "X" :  "darkgray"}
onoff = {"on" : 1, 'off': 0}

kanban_options = [
    {"code": "R", "label": "Resourcing"},
    {"code": "P", "label": "Post-Bundling"},
    {"code": "L", "label": "Informing"},
    {"code": "C", "label": "Canvassing"},
    {"code": "K", "label": "Klosing"},
    {"code": "T", "label": "Telling"}
]

# All Election Settings
ELECTIONS = get_election_names()

current_election = "DEMO"
CurrentElection = get_election_data(current_election)
#election constants and event values are now loaded up
constants = CurrentElection
places =  CurrentElection['places']
print("🔍 constants:", constants)

# the general list of elections and election data file proessing streams
stream_table = {}
if  os.path.exists(TABLE_FILE) and os.path.getsize(TABLE_FILE) > 0:
    with open(TABLE_FILE, "r") as f:
        stream_table = json.load(f)



data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))
VID_json = json.dumps(VID)  # Convert to JSON string

current_node = get_current_node(session)
current_election = get_election_data(current_election)

# override if OPTIONS(.json) exists because it contains memorised data
OPTIONS = {}
resources = {}
task_tags ={}
areas = {}
if  os.path.exists(OPTIONS_FILE) and os.path.getsize(OPTIONS_FILE) > 0:
    with open(OPTIONS_FILE, 'r', encoding="utf-8") as f:
        OPTIONS = json.load(f)
    resources = OPTIONS['resources']
    areas =  OPTIONS['areas']
    task_tags =  OPTIONS['task_tags']
# eventually extract calendar areas directly from the associated MAP


# override if RESOURCES_FILE(.csv) exists because it initialises resources
resourcesdf = pd.DataFrame()
if  os.path.exists(RESOURCE_FILE) and os.path.getsize(RESOURCE_FILE) > 0:
    with open(RESOURCE_FILE, 'r', encoding="utf-8") as f:
        resources = json.load(f)
    print("____Resources file read in")
    # need to save to ELECTIONS)
    OPTIONS['resources'] = resources
# eventually want to extract resources from # OPTIONS['resources']
# eventally want to make OPTIONS election specific , not generic


# eventually want to extract places from # OPTIONS['places']  from CurrentElection['calendar_plan']
selectedResources = resources
# OPTIONS spells out the options for the event and constant values in the election calendar plan
OPTIONS = {
    "ACC": False,
    "territories": ElectionTypes,
    "yourparty": VID,
    "previousParty": VID,
    "resources" : resources,
    'areas' : areas,
    "candidate" : selectedResources,
    "chair" : selectedResources,
    "tags": CurrentElection['tags'],
    "task_tags": task_tags,
    "autofix" : onoff,
    "VNORM" : VNORM,
    "VCO" : VCO,
    "streams" : ELECTIONS,
    "stream_table": stream_table
    # Add more mappings here if needed
}


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

LEVEL_ZOOM_MAP = {
    'country': 12, 'nation': 13, 'county': 14, 'constituency': 15,
    'ward': 16, 'division': 16, 'polling_district': 17,
    'walk': 17, 'walkleg': 18, 'street': 18
}

Featurelayers = {
"marker": ExtendedFeatureGroup(name='marker', options={'mytag': 'marker'},overlay=True, control=True, show=False),
"country": ExtendedFeatureGroup(name='country', options={'mytag': 'country'},overlay=True, control=True, show=False),
"nation": ExtendedFeatureGroup(name='nation', options={'mytag': 'nation'},overlay=True, control=True, show=False),
"county": ExtendedFeatureGroup(name='county', options={'mytag': 'county'},overlay=True, control=True, show=False),
"constituency": ExtendedFeatureGroup(name='constituency', options={'mytag': 'consituency'},overlay=True, control=True, show=False),
"ward": ExtendedFeatureGroup(name='ward', overlay=True, options={'mytag': 'ward'},control=True, show=False),
"division": ExtendedFeatureGroup(name='division', options={'mytag': 'division'},overlay=True, control=True, show=False),
"polling_district": ExtendedFeatureGroup(name='polling_district', options={'mytag': 'polling_district'},overlay=True, control=True, show=False),
"walk": ExtendedFeatureGroup(name='walk', options={'mytag': 'walk'},overlay=True, control=True, show=False),
"walkleg": ExtendedFeatureGroup(name='walkleg', options={'mytag': 'walkleg'},overlay=True, control=True, show=False),
"street": ExtendedFeatureGroup(name='street', options={'mytag': 'street'},overlay=True, control=True, show=False),
"result": ExtendedFeatureGroup(name='result', options={'mytag': 'result'},overlay=True, control=True, show=False),
"target": ExtendedFeatureGroup(name='target', options={'mytag': 'target'},overlay=True, control=True, show=False),
"data": ExtendedFeatureGroup(name='data', options={'mytag': 'data'},overlay=True, control=True, show=False)
}
counters = {}
for etype in Featurelayers.keys():
    counters[etype] = 0

for key, layer in Featurelayers.items():
    layer.key = key


# Setup logger
logging.basicConfig(
    level=logging.DEBUG,  # or INFO
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)



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

mapfile = ""

Con_Results_data = pd.read_excel(config.workdirectories['resultdir']+'/'+'HoC-GE2024-results-by-constituency.xlsx')
#Con_Results_data = pd.read_csv(config.workdirectories['resultdir']+'/'+'HoC_General_Election_2024_Results.csv',sep='\t')
Con_Results_data['NAME'] = normalname(Con_Results_data['Constituency name'])
Con_Results_data['FIRST'] = normalname(Con_Results_data['First party'])

Ward_Results_data = pd.read_excel(config.workdirectories['resultdir']+'/'+'LEH-Candidates-2023.xlsx')
Ward_Results_data.loc[Ward_Results_data['WINNER'] == 1]
Ward_Results_data['NAME'] = normalname(Ward_Results_data['WARDNAME'])
Ward_Results_data['FIRST'] = normalname(Ward_Results_data['PARTYNAME'])

Level4_Results_data = pd.read_excel(config.workdirectories['resultdir']+'/'+'opencouncildata_councillors.xlsx')
Level4_Results_data['NAME'] = normalname(Level4_Results_data['Ward Name'])
Level4_Results_data['FIRST'] = normalname(Level4_Results_data['Party Name'])


#        Con_Results_data = Con_Bound_layer.merge(Con_Results_data, how='left', on='NAME' )

print("_________HoC Results data: ",Con_Results_data.columns)
print("_________HoC Results data: ",Ward_Results_data.columns)
print("_________HoC Results data: ",Level4_Results_data.columns)


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
    print(">>> /reassign_parent called")
    current_node = get_current_node(session)

    restore_from_persist(session)
    print("✔ Restored from persist")

    print(f"✔ Current node: {current_node.value if current_node else 'None'}")

    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    print(f"✔ Current election: {current_election if current_election else 'None'}")

    data = request.get_json()
    old_parent_name = data['old_parent']
    new_parent_name = data['new_parent']
    subject_name = data['subject']
    print(f"📥 Received request to move node '{subject_name}' from '{old_parent_name}' to '{new_parent_name}'")

    # Recursively find the node being reassigned and the old/new parents
    def find_node_by_value(node, value, oldparent_value, newparent_value):
        if node.value == value:
            if node.parent and node.parent.value == oldparent_value:
                grandparent = node.parent.parent
                if grandparent:
                    newnode = next((n for n in grandparent.children if n.value == newparent_value), None)
                    if newnode:
                        return [node, node.parent, newnode]
            print("__current_node is not subject or parents not matching")
            return []
        if node.value == oldparent_value:
            subjectnode = next((n for n in node.children if n.value == value), None)
            newparentnode = next((n for n in node.parent.children if n.value == newparent_value), None)
            if subjectnode and newparentnode:
                return [subjectnode, node, newparentnode]
            print("__old parent node found, but subject or new parent not found")
            return []
        return []

    nodes = find_node_by_value(current_node, subject_name, old_parent_name, new_parent_name)
    if not nodes:
        print(f"❌ Node '{subject_name}' not found in tree")
        return jsonify({'status': 'error', 'message': f"Node '{subject_name}' not found"}), 404

    subject_node, old_parent_node, new_parent_node = nodes
    print(f"✔ Found subject node: {subject_node.value}, old parent: {old_parent_node.value}, new parent: {new_parent_node.value}")

    mapfile0 = old_parent_node.parent.mapfile()
    mapfile1 = old_parent_node.mapfile()
    mapfile2 = new_parent_node.mapfile()

    # Remove from old parent
    if subject_node in old_parent_node.children:
        old_parent_node.children.remove(subject_node)
        print(f"✔ Removed node '{subject_node.value}' from old parent '{old_parent_node.value}'")

    # Add to new parent
    new_parent_node.add_Tchild(subject_node, subject_node.type, subject_node.election)
    print(f"✔ Added node '{subject_node.value}' to new parent '{new_parent_node.value}'")

    # Modify allelectors
    mask1 = (
        (allelectors['Election'] == current_election) &
        (allelectors['WalkName'] == old_parent_name)
    )
    oldparentelectors = allelectors.loc[mask1].copy()  # important to avoid SettingWithCopyWarning

    if allelectors[allelectors['Election'] == current_election].empty:
        print(f"❌ No rows found in allelectors with election '{current_election}'")
        return jsonify({'status': 'error', 'message': f"No rows found for '{current_election}' in allelectors"}), 404

    if oldparentelectors.empty:
        print(f"❌ No rows found in allelectors with old parent '{current_election}{old_parent_name}'")
        return jsonify({'status': 'error', 'message': f"No rows found for '{current_election}{old_parent_name}' in allelectors"}), 404

    mask2 = (
        (allelectors['Election'] == current_election) &
        (allelectors['WalkName'] == new_parent_name)
    )
    newparentelectors = allelectors.loc[mask2].copy()

    if newparentelectors.empty:
        print(f"❌ No rows found in allelectors with new parent '{new_parent_name}'")
        return jsonify({'status': 'error', 'message': f"No rows found for '{new_parent_name}' in allelectors"}), 404

    print("____oldparentelectors beforeX:", len(oldparentelectors))
    print("____newparentelectors beforeX:", len(newparentelectors))

    # Change parent for the subject_node in allelectors
    # Filter only those rows that match the subject node
    # Mask for rows corresponding to the subject node under the old parent
    subject_mask = (
        (allelectors['Election'] == current_election) &
        (allelectors['WalkName'] == old_parent_name) &
        (allelectors['StreetName'] == subject_name)
    )

    # Debug before update
    print("✅ Rows before update:")
    print(allelectors.loc[subject_mask, ['StreetName', 'WalkName']])

    # Update 'WalkName' to new parent
    allelectors.loc[subject_mask, 'WalkName'] = new_parent_name
    print("____Modified WalkName for subject in allelectors")

    # Recalculate masks after update
    mask1_after = (
        (allelectors['Election'] == current_election) &
        (allelectors['WalkName'] == old_parent_name)
    )
    mask2_after = (
        (allelectors['Election'] == current_election) &
        (allelectors['WalkName'] == new_parent_name)
    )

    print("____oldparentelectors afterX:", len(allelectors.loc[mask1_after]))
    print("____newparentelectors afterX:", len(allelectors.loc[mask2_after]))

    # Confirm moved rows
    moved_rows = allelectors[
        (allelectors['Election'] == current_election) &
        (allelectors['StreetName'] == subject_name)
    ]
    print("✅ Moved row(s):")
    print(moved_rows[['StreetName', 'WalkName']])


    # Regenerate maps
    print(f"🔁 Regenerating map for grand parent: {mapfile0}")
    old_parent_node.parent.create_area_map(old_parent_node.parent.getselectedlayers(current_election,mapfile0), current_election, CurrentElection)

    print(f"🔁 Regenerating map for old parent: {mapfile1}")
    old_parent_node.create_area_map(old_parent_node.getselectedlayers(current_election,mapfile1), current_election, CurrentElection)

    print(f"🔁 Regenerating map for new parent: {mapfile2}")
    new_parent_node.create_area_map(new_parent_node.getselectedlayers(current_election,mapfile2), current_election, CurrentElection)

    # Update session and persist

    persist(new_parent_node.parent)
    visit_node(old_parent_node.parent, current_election,CurrentElection, mapfile0)

    print("✅ Reassignment complete")
    return jsonify({
        'status': 'success',
        'mapfile': f"{mapfile0}",
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
    global current_node
    global allelectors
    global layeritems

    global TREK_NODES
    global OPTIONS

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
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
    global allelectors
    global layeritems

    global TREK_NODES
    global areaelectors
    global OPTIONS

# campaign plan is only available to westminster elections at level 3 and others at level 4.
# every election should acquire an election node(ping to its mapfile) to which this route should take you
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = current_node.ping_node(current_election,CurrentElection['mapfiles'][-1])
    session['current_node_id'] = current_node.fid
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
        kanban_options=kanban_options,
        walk_tag_counts=walk_tag_counts,
        tag_labels=CurrentElection['tags']
    )


@app.route('/update-walk-kanban', methods=['POST'])
@login_required
def update_walk_kanban():
    global allelectors

    global CurrentElection

    data = request.get_json()
    walk_name = data.get('walk_name')
    new_kanban = data.get('kanban')

    # Check if inputs are valid
    if not walk_name or not new_kanban:
        return jsonify(success=False, error="Missing data"), 400

    # Restore context
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    Territory_node = current_node.ping_node(current_election,CurrentElection['mapfiles'][-1])
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
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    global allelectors
    global areaelectors
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    global allelectors
    global areaelectors
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    global current_node, allelectors

    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    global current_node
    global allelectors
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
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    lat = 54.9783
    long = 1.6178

    current_node.centroid = (lat,long)
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

    # tags is assumed to be a dict: { "leafletting1": "FirstLeaflet", ... }
    tag_list = [{"code": code, "label": label} for code, label in tags.items()]

    return jsonify(tags=tag_list)


@app.route('/add_tag', methods=['POST'])
@login_required
def add_tag():
    global CurrentElection
    restore_from_persist(session=session)
    current_node = get_current_node(session=session)
    current_election = get_current_election(session=session)
    CurrentElection = get_election_data(current_election)
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
    global allelectors
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
    global allelectors
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
    CurrentElection = get_election_data(election)
    current_node = get_current_node(session)
    delete_path = CurrentElection['mapfiles'][-1]
    delete_node = current_node.ping_node(election,delete_path)

    before_count = len(allelectors)
    allelectors = allelectors[allelectors['Election'] != election]
    after_count = len(allelectors)
    print(f"Deactivated election {election}. Removed {before_count - after_count} electors.")

    # remove the  child data nodes under the delete nodes
    ttype = gettypeoflevel(delete_path,delete_node.level+1)
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
    global allelectors
    global current_node
    global layeritems
    global DQstats
    global progress

    global TREK_NODES
    global Treepolys
    global Fullpolys

    fixed_path = ELECTOR_FILE  # Set your path
    print("____Route/Reset-Election")

    TREK_NODES = {}

    if not fixed_path or not os.path.exists(fixed_path):
        return jsonify({'message': 'Elections reset unnessary - no election data '}), 404
    current_node = get_current_node(session)
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

    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    reportfile = "UNITED_KINGDOM/ENGLAND/SURREY/SURREY-MAP.html"
    current_node = current_node.ping_node(current_election,reportfile)


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
                election_node = current_node.ping_node("DEMO",territory_path)
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
    selectedlayers = current_node.getselectedlayers(current_election,reportfile)
    current_node.create_area_map(selectedlayers, current_election, CurrentElection)
    reportdate = datetime.strptime(str(date.today()), "%Y-%m-%d").strftime('%d/%m/%Y')

    return render_template("election_report.html", reportdate=reportdate, mapfile=reportfile, report_data=report_data)


@app.route("/set-election", methods=["POST"])
@login_required
def set_election():
    global CurrentElection, OPTIONS, constants, TREK_NODES, Treepolys, Featurelayers
    import json

    try:
        def make_json_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(i) for i in obj]
            elif isinstance(obj, (str, int, float, bool)) or obj is None:
                return obj
            else:
                return str(obj)

        restore_from_persist(session)
        data = request.get_json(force=True)  # <-- ensure JSON parsing
        if not data or "election" not in data:
            return jsonify(success=False, error="No election provided"), 400

        current_node = get_current_node(session)
        current_election = data["election"]
        session['current_election'] = current_election

        CurrentElection = get_election_data(current_election)
        print("____Route/set-election/constantsX", current_election, CurrentElection)

        if not CurrentElection:
            return jsonify(success=False, error="Election not found", current_election=current_election), 404

        CurrentElection['previousParty'] = current_node.party
        mapfile = CurrentElection['mapfiles'][-1]

        current_node = current_node.ping_node(current_election, mapfile)
        visit_node(current_node, current_election, CurrentElection, mapfile)
        persist(current_node)
        ctype = gettypeoflevel(mapfile, current_node.level+1)
        safe_constants = make_json_serializable(CurrentElection)
        return jsonify({
            'success': True,
            'constants': CurrentElection,
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
    current_node = get_current_node(session)
    restore_from_persist(session)
    current_election = request.args.get("election")
    CurrentElection = get_election_data(current_election)
    target_node = current_node.ping_node(current_election,CurrentElection['mapfiles'][-1])

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
    current_node = get_current_node(session=session)
    current_election = get_current_election(session=session)
    CurrentElection = get_election_data(current_election)
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
    global current_node
    global Featurelayers
    data = request.get_json()
    name = data.get("name")
    value = data.get("value")
    current_node = get_current_node(session)
    current_election = data.get("election")

    print("____Back End1 election constants update:",current_election,":",name,"-",value)

    CurrentElection = get_election_data(current_election)
    counters = get_counters(session)

    if name in CurrentElection:
        if name == "ACC":
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
    current_node = get_current_node(session)
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
    with open(OPTIONS_FILE, 'w') as f:
        json.dump(OPTIONS, f, indent=2)

    return jsonify(success=True, electiontabs_html=electiontabs_html)


@app.route("/add-election", methods=["POST"])
@login_required
def add_election():
    global OPTIONS
    global CurrentElection
    restore_from_persist(session)
    current_node = get_current_node(session)
    # no have Current Election data loaded
    # Load existing elections

    ELECTIONS = get_election_names()

    # Get name for new election
    data = request.get_json()
    new_election = data.get("election")

    session['current_election'] = new_election

    if not new_election or new_election in ELECTIONS:
        return jsonify(success=False, error="Invalid or duplicate election name.")

    current_election = get_current_election(session)

    CurrentElection = get_election_data("DEMO")

    mapfile = CurrentElection['mapfiles'][-1]

    CurrentElection['previousParty'] = current_node.party

    print(f"___new_election + CurrentElection: {new_election} + {CurrentElection}")

    # Write updated elections back
    save_election_data(new_election,CurrentElection)

    ELECTIONS = get_election_names()
    print("____ELECTIONS:", ELECTIONS)
    formdata['electiontabs_html'] = render_template('partials/electiontabs.html', ELECTIONS=ELECTIONS, current_election=current_election)

    OPTIONS['streams'] = ELECTIONS

    # Optional: set session to the new election
    with open(OPTIONS_FILE, 'w') as f:
        json.dump(OPTIONS, f, indent=2)


    print("election-tabs:",formdata['electiontabs_html'])

    return jsonify({'success': True,
        'constants': CurrentElection,
        'options': OPTIONS,
        'election_name': new_election,
        'electiontabs_html':formdata['electiontabs_html']
    })


@app.route("/last-election")
@login_required
def last_election():
    ELECTIONS_DIR = config.workdirectories['workdir']
    """
    Return the most recently accessed election file.
    Fallback: session-stored current election or first available election.
    """
    # 1. Try session first
    last = session.get('current_election')

    # 2. List elections from filesystem and sort by last access time
    election_files = get_election_names()  # returns list of election names
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

    # 3. Final fallback
    if not last and election_files:
        last = election_files[0]

    print(f"____last election: {last}")

    return jsonify(last)




@app.route("/update-territory", methods=["POST"])
@login_required
def update_territory():
    global TREK_NODES
    global allelectors
    global CurrentElection
    global constants
    global OPTIONS
    data = request.get_json()
    current_node = get_current_node(session)
    current_election = data.get("election")
    CurrentElection = get_election_data(current_election)
    # mapfiles last entry is what we need to bookmark.

    new_path = CurrentElection['mapfiles'][-1]

    current_node = current_node.ping_node(current_election, new_path)
    mapfile = current_node.mapfile()

    save_election_data(current_election,CurrentElection)
    print(f"______election:{current_election} Bookmarks : {CurrentElection['mapfiles']} Updated-territory: {new_path}")

    return jsonify(success=True, constants=CurrentElection)



@app.route('/validate_tags', methods=['POST'])
@login_required
def validate_tags():

    global CurrentElection
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    global TREK_NODES
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
        current_node = get_current_node(session)
        current_election = get_current_election(session)
        CElection = get_election_data(current_election)
        mapfile = current_node.mapfile()
        calfile = current_node.calfile()

        from collections import defaultdict


    #       Track used IDs across both existing and new entries
    #        places = build_place_lozenges(markerframe)

    #        restore_from_persist(session=session)
    #        current_node = get_current_node(session)
    #        CE = get_current_election(session)

        print(f"🧪 Index level {current_election} - current_node mapfile:{mapfile} - OPTIONS html {OPTIONS['areas']}")

        return render_template(
            "Dash0.html",
            table_types=TABLE_TYPES,
            ELECTIONS=ELECTIONS,
            current_election=current_election,
            options=OPTIONS,
            constants=CElection,
            mapfile=mapfile,
            calfile=calfile,
            DEVURLS=config.DEVURLS
        )
    return render_template("index.html")

#login
@app.route('/login', methods=['POST', 'GET'])
def login():
    global TREK_NODES
    global streamrag
    global environment
    global layeritems
    global CurrentElection

    current_node = get_current_node(session)

    if 'gtagno_counters' not in session:
        session['gtagno_counters'] = {}
        # Example: {'marker': 0, 'country': 0, ...}

    current_election = get_current_election(session)
    if current_node.value != "UNITED_KINGDOM":
        flash("User already logged in:", session['username'], " at ", current_node.value)
        print("_______ROUTE/Already logged in:", session['username'], " at ", current_node.value)
        return redirect(url_for('firstpage'))
    # Collect info from forms in the login db
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    print("_______ROUTE/login page", username, user)
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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


        session['current_node_id'] = current_node.fid
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
                window.location.href = `/firstpage?lat=${lat}&lon=${lon}`;
            },
            function(err) {
                alert("Location access denied.");
                window.location.href = "/firstpage";
            }
        );
    } else {
        alert("Geolocation not supported.");
        window.location.href = "/firstpage";
    }
    </script>
    </body>
    </html>
    """)


@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():

    current_node = TREK_NODES.get(session.get('current_node_id',"UNITED_KINGDOM"))

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
    global TREK_NODES
    global allelectors
    global streamrag
    global formdata
    global CurrentElection

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = "DEMO"

    CurrentElection = get_election_data("DEMO")
    print ("___Route/Dashboard allelectors len: ",len(allelectors))
    if 'username' in session:
        print(f"_______ROUTE/dashboard: {session['username']} is already logged in at {session.get('current_node_id','UNITED_KINGDOM')}")
        formdata = {}
        current_node = TREK_NODES.get(session.get('current_node_id',"UNITED_KINGDOM"))
        if not current_node:
            current_node = TREK_NODES.get(next(iter(TREK_NODES), None)).findnodeat_Level(0)
        streamrag = getstreamrag()
        print ("allelectors len after streamrag: ",len(allelectors))
        path = CurrentElection['mapfiles'][-1]
        previous_node = current_node
        print ("____Dashboard CurrentElection: ",path, previous_node.value)
        # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        current_node = previous_node.ping_node(current_election,path)
        print ("allelectors len after ping: ",len(allelectors))

        mapfile = current_node.mapfile()
        print ("___Dashboard persisted filename: ",mapfile)
        persist(current_node)
        if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
            selectedlayers = current_node.getselectedlayers(current_election,mapfile)
            current_node.create_area_map(selectedlayers,current_election,CurrentElection)

#        redirect(url_for('captains'))
    return   send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

    flash('_______ROUTE/dashboard no login session ')

    return redirect(url_for('index'))


@app.route('/downbut/<path:path>', methods=['GET','POST'])
@login_required
def downbut(path):
    global TREK_NODES
    global formdata
    global Treepolys
    global Fullpolys
    global Featurelayers
    global layeritems
    global CurrentElection
    global OPTIONS

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    formdata = {}
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]
# a down button on a node has been selected on the map, so the new map must be displayed with new down options

# the selected node has to be found from the selected button URL

    if current_node.level < 4:
        restore_fullpolys(gettypeoflevel(path,current_node.level+1))
        print(f"____Maxing up Treepoly to Fullpolys for :{gettypeoflevel(path,current_node.level+1)}")
    previous_node = current_node

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(current_election,path)

    print("____Route/downbut:",previous_node.value,current_node.value, path)
    atype = gettypeoflevel(path,current_node.level+1)
    FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html",'walk' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
    current_node.file = subending(current_node.file,FACEENDING[atype]) # face is driven by intention type
    print(f" target type: {atype} current {current_node.value} type: {current_node.type} FACEFILE:{FACEENDING[current_node.type]}")
# the map under the selected node map needs to be configured
# the selected  boundary options need to be added to the layer
    Featurelayers[atype].create_layer(current_election,current_node,atype)
    print(f"____/DOWN OPTIONS areas for calendar node {current_node.value} are {OPTIONS['areas']} ")
    selectedlayers = current_node.getselectedlayers(current_election,path)
    current_node.create_area_map(selectedlayers,current_election,CurrentElection)
    print(f"_________layeritems for {current_node.value} of type {atype} are {current_node.childrenoftype(atype)} for lev {current_node.level}")

    mapfile = current_node.mapfile()

    visit_node(current_node,current_election,CurrentElection,mapfile)

    persist(current_node)
#    if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
#        selectedlayers = current_node.getselectedlayers(current_election,mapfile)
#        current_node.create_area_map(selectedlayers,current_election,CurrentElection)

#    if not os.path.exists(config.workdirectories['workdir']+"/"+mapfile):
    print(f"_____creating mapfile for {atype} map file path :{mapfile} for path:{mapfile}" )
    return   send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/transfer/<path:path>', methods=['GET','POST'])
@login_required
def transfer(path):
    global TREK_NODES
    global Treepolys
    global Fullpolys
    global Featurelayers
    global environment
    global levels
    global layeritems
    global formdata
    global CurrentElection
    TypeMaker = { 'nation' : 'downbut','county' : 'downbut', 'constituency' : 'downbut' , 'ward' : 'downbut', 'division' : 'downbut', 'polling_district' : 'downPDbut', 'walk' : 'downWKbut', 'street' : 'PDdownST', 'walkleg' : 'WKdownST'}

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    formdata = {}
# transfering to another any other node with siblings listed below
    previous_node = current_node
# use ping to populate the destination node with which to repaint the screen node map and markers
    current_node = previous_node.ping_node(current_election,path)

    atype = gettypeoflevel(path, current_node.level+1)

    mapfile = current_node.mapfile()
    CurrentElection = get_election_data(current_election)
    visit_node(current_node,current_election,CurrentElection, mapfile)
    print("____Route/transfer:",previous_node.value,current_node.value,current_node.type, path)
    if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
        print("___Typemaker:",atype, TypeMaker[atype] )
        return redirect(url_for(TypeMaker[atype],path=mapfile))
    else:
#    return redirect(url_for('thru',path=mapfile))
        return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/downPDbut/<path:path>', methods=['GET','POST'])
@login_required
def downPDbut(path):
    global Treepolys
    global Fullpolys
    global Featurelayers
    global TREK_NODES
    global areaelectors
    global filename
    global layeritems
    global CurrentElection
    global OPTIONS

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = (session)

    previous_node = current_node
    current_node = previous_node.ping_node(current_election,path) #aligns with election data and takes you to the clicked node
    session['current_node_id'] = current_node.fid
    current_node.file = subending(current_node.file,"-PDS.html") # forces looking for PDs file
    CurrentElection = get_election_data(current_election)
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
            current_node.create_area_map(current_node.getselectedlayers(current_election,mapfile),current_election,CurrentElection)
            flash("________PDs added:  "+str(len(Featurelayers['polling_district']._children)))
            print("________After map created PDs added  :  ",current_node.level, len(Featurelayers['polling_district']._children))

#    face_file = subending(current_node.file,"-MAP.html")
#    mapfile = current_node.dir+"/"+face_file
# if this route is from a redirection rather than a service call , then create file if doesnt exist

    if not os.path.exists(PDpathfile):
        print ("_________New PD mapfile/",current_node.value, mapfile)
        Featurelayers[previous_node.type].create_layer(current_election,current_node,previous_node.type) #from upnode children type of prev node
        current_node.create_area_map(current_node.getselectedlayers(current_election,mapfile),current_election,CurrentElection)
    print("________PD markers After importVI  :  "+str(len(Featurelayers['polling_district']._children)))

    persist(current_node)
    visit_node(current_node,current_election,CurrentElection,mapfile)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/downWKbut/<path:path>', methods=['GET','POST'])
@login_required
def downWKbut(path):
    global Treepolys
    global Fullpolys
    global Featurelayers
    global TREK_NODES
    global areaelectors
    global filename
    global layeritems
    global CurrentElection
    global OPTIONS

# so this is the button which creates the nodes and map of equal sized walks for the troops
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    print (f"_________ROUTE/downWKbut1 CE {current_election}", current_node.value, path)

    previous_node = current_node
    # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(current_election,path)

    current_node.file = subending(current_node.file,"-WALKS.html")
 # the node which binds the election data
    CurrentElection = get_election_data(current_election)
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

            mapfile = current_node.mapfile()
            print("_______just before Walk create_area_map call:",current_node.level, len(Featurelayers['walk']._children))
            current_node.create_area_map(current_node.getselectedlayers(current_election,path),current_election,CurrentElection)
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
        current_node.create_area_map(current_node.getselectedlayers(current_election,mapfile),current_election,CurrentElection)

    #    moredata = importVI(allelectors.copy())
    #    if len(moredata) > 0:
    #        allelectors = moredata

        print("________ Walk markers After importVI  :  "+str(len(Featurelayers['walk']._children)))
        print("_______writing to file:", mapfile)

    persist(current_node)
    visit_node(current_node,current_election,CurrentElection,mapfile)

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/downMWbut/<path:path>', methods=['GET','POST'])
@login_required
def downMWbut(path):
    global Treepolys
    global Fullpolys
    global Featurelayers
    global TREK_NODES
    global areaelectors
    global filename
    global layeritems
    global CurrentElection
    global STATICSWITCH
    global OPTIONS
# so this is the button which creates the nodes and map of equal sized walks for the troops

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    print (f"_________ROUTE/downMWbut1 CE {current_election}", current_node.value, path)

    previous_node = current_node
    # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(current_election,path)

    current_node.file = subending(current_node.file,"-WALKS.html")
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
            current_node.create_area_map(current_node.getselectedlayers(current_election,path),current_election,CurrentElection)
            STATICSWITCH = False
            flash("________Static Walks added:  "+str(len(Featurelayers['walk']._children)))
            print("________After map created Static Walks added  :  ",current_node.level, len(Featurelayers['walk']._children))

    #            allelectors = getblock(allelectors,'Area',current_node.value)

    if not os.path.exists(walkpathfile):
#        simple transfer from another node -
        print ("_________New MW mapfile/",current_node.value, walkpathfile)
        Featurelayers['walk'].create_layer(current_election,current_node,'walk', static=True) #from upnode children type of prev node

        STATICSWITCH = True
        current_node.create_area_map(current_node.getselectedlayers(current_election,path),current_election,CurrentElection)
        STATICSWITCH = False
    #    moredata = importVI(allelectors.copy())
    #    if len(moredata) > 0:
    #        allelectors = moredata
        print("________ Static Walk markers After importVI  :  "+str(len(Featurelayers['walk']._children)))
        print("_______writing to file:", walkpathfile)

    persist(current_node)
    visit_node(current_node,current_election,CurrentElection,mapfile)


    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/STupdate/<path:path>', methods=['GET','POST'],strict_slashes=False)
@login_required
def STupdate(path):
    global Treepolys
    global Fullpolys
    global TREK_NODES
    global allelectors
    global environment
    global filename
    global layeritems
    global CurrentElection

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = (session)
    CurrentElection = get_election_data(current_election)

#    steps = path.split("/")
#    filename = steps.pop()
#    current_node = selected_childnode(current_node,steps[-1])
    fileending = "-SDATA.csv"
    if path.find("/PDS/") < 0:
        fileending = "-WDATA.csv"

    session['next'] = 'STupdate/'+path
# use ping to precisely locate the node for which data is to be collected on screen
    current_node = current_node.ping_node(current_election,path)
    session['current_node_id'] = current_node.fid
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
                    changefields.loc[i,'Lat'] = street_node.centroid[0]
                    changefields.loc[i,'Long'] = street_node.centroid[1]
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
# Example Usage
# base_path = "/your/output/directory"
# base_name = "changefile"
# extension = ".csv"


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


    #           only create a map if the branch does not already exist
#    current_node = current_node.parent
    formdata['tabledetails'] = getchildtype(current_node.parent.type)+ "s street details"

#    url = url_for('newstreet',path=mapfile)

    sheetfile = current_node.create_streetsheet(current_election,streetelectors)
    mapfile = current_node.dir+"/"+sheetfile
    visit_node(current_node,current_election,CurrentElection,mapfile)
    flash(f"Creating new street/walklegfile:{sheetfile}", "info")
    print(f"Creating new street/walklegfile:{sheetfile}")
    register_node(current_node)
    persist(current_node)
    return  jsonify({"message": "Success", "file": sheetfile})


@app.route('/PDdownST/<path:path>', methods=['GET','POST'])
@login_required
def PDdownST(path):
    global Treepolys
    global Fullpolys
    global Featurelayers
    global TREK_NODES
    global areaelectors
    global environment
    global filename
    global layeritems
    global CurrentElection
    global OPTIONS

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = (session)
    CurrentElection = get_election_data(current_election)

# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(current_election,path)

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

        PD_node.create_area_map(PD_node.getselectedlayers(current_election,path),current_election,CurrentElection)
    mapfile = PD_node.mapfile()

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers['street']._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers['street']._children)))
    visit_node(current_node,current_election,CurrentElection,mapfile)
    persist(current_node)


    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/LGdownST/<path:path>', methods=['GET','POST'])
@login_required
def LGdownST(path):
    global Treepolys
    global Fullpolys
    global Featurelayers
    global TREK_NODES
    global areaelectors
    global environment
    global filename
    global layeritems
    global CurrentElection

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = (session)
    CurrentElection = get_election_data(current_election)
    T_level = CurrentElection['level']

# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers
    current_node = current_node.findnodeat_Level(T_level)

    current_node = current_node.ping_node(current_election,path)
    session['current_node_id'] = current_node.fid

    PD_node = current_node
# now pointing at the STREETS.html node containing a map of street markers
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]
    mask2 = areaelectors['PD'] == PD_node.value
    PDelectors = areaelectors[mask2]
    if request.method == 'GET':
    # we only want to plot with single streets , so we need to establish one street record with pt data to plot
        atype = gettypeoflevel(path, current_node.level)
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

        PD_node.create_area_map(PD_node.getselectedlayers(current_election,path),current_election,CurrentElection)
    mapfile = PD_node.mapfile()

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers['street']._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers['street']._children)))

    register_node(current_node)
    persist(current_node)

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)



@app.route('/WKdownST/<path:path>', methods=['GET','POST'])
@login_required
def WKdownST(path):
    global Treepolys
    global Fullpolys
    global Featurelayers

    global TREK_NODES
    global areaelectors
    global current_node
    global environment
    global filename
    global layeritems
    global CurrentElection
    global OPTIONS
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = (session)
    CurrentElection = get_election_data(current_election)


    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(current_election,path) # takes to the clicked node in the territory
    session['current_node_id'] = current_node.fid


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

            walk_node.create_area_map(walk_node.getselectedlayers(current_election,path), current_election,CurrentElection)

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
    global TREK_NODES
    global layeritems
    global formdata
    global CurrentElection
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    current_node = current_node.ping_node(current_election,path)
    session['current_node_id'] = current_node.fid

    flash('_______ROUTE/wardreport')
    print('_______ROUTE/wardreport')
    mapfile = current_node.mapfile()
    print("________layeritems  :  ", layeritems)

    i = 0
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
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
    global VCO
    global VNORM


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

    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)

    # Table mapping
    table_map = {
        "report_data" : get_report_table,
        "resources" : get_resources_table,
        "places" : get_places_table,
        "stream_table" : get_stream_table
    }
    print(f"____Get Table {table_name}")

    try:
        if table_name.endswith("_layer"):
            tabtype = table_name.removesuffix("_layer")
            lev = find_level_containing(tabtype)-1
            print(f"____NODELOOKUP {table_name} type {tabtype} level {lev} ")
            [column_headers,rows, title] = get_layer_table(current_node.findnodeat_Level(lev).childrenoftype(tabtype), str(tabtype)+"s")
            print(f"____NODELOOKUP {table_name} -COLS {column_headers} ROWS {rows} TITLE {title}")
            return jsonify([column_headers, rows.to_dict(orient="records"), title])
        elif table_name.endswith("_xref"):
            lev = current_node.level+1
            path = current_node.dir+"/"+current_node.file
            tabtype = gettypeoflevel(path,lev)
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



@app.route('/displayareas', methods=['POST', 'GET'])
@login_required
def displayareas():
    #calc values in displayed table
    global TREK_NODES
    global layeritems
    global formdata

    current_node = get_current_node(session=session)
    current_election = get_current_election(session=session)
    CurrentElection = get_election_data(current_election)
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
        ctype = gettypeoflevel(path, current_node.level+1)

        formdata = current_node.value +getchildtype(current_node.type)+"s"
        tablenodes = current_node.childrenoftype(ctype)
        if len(tablenodes) == 0:
            if current_node.level > 0:
                ctype = gettypeoflevel(path, current_node.level)
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
    global TREK_NODES
    global layeritems
    global formdata
    global Featurelayers
    global CurrentElection

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers

    current_node = current_node.ping_node(current_election,path)
    session['current_node_id'] = current_node.fid
    mapfile = current_node.mapfile()

    flash('_______ROUTE/divreport')
    print('_______ROUTE/divreport')

    i = 0
    layeritems = pd.DataFrame()
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
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
    global TREK_NODES
    global allelectors
    global Treepolys
    global Fullpolys
    global Featurelayers
    global environment
    global layeritems
    global CurrentElection
    global OPTIONS

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    current_node = previous_node.parent.ping_node(current_election,path)

    if current_node.level < 3:
        restore_fullpolys(current_node.type)

# the previous node's type determines the 'face' of the destination node
    atype = gettypeoflevel(path,current_node.level+1) # destination type
    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""

    FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html",'walk' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
    face_file = subending(trimmed_path,FACEENDING[previous_node.type])
    print(f" previous: {previous_node.value} type: {previous_node.type} current {current_node.value} type: {current_node.type} FACEFILE:{FACEENDING[previous_node.type]}")

    mapfile = trimmed_path
    if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
        Featurelayers[previous_node.type].create_layer(current_election,current_node,previous_node.type) #from upnode children type of prev node

        flash("No data for the selected node available,attempting to generate !")
        print("No data for the selected node available,attempting to generate !")
        current_node.create_area_map(current_node.getselectedlayers(current_election,mapfile), current_election,CurrentElection)

    print("________chosen node url",mapfile)
    visit_node(previous_node.parent,current_election,CurrentElection,mapfile)
    persist(current_node)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


#Register user
@app.route('/register', methods=['POST'])
def register():
    flash('_______ROUTE/register')

    username = request.form['username']
    password = request.form['password']
    print("Register", username)
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)

    user = User.query.filter_by(username=username).first()
    if user:
        print("existinuser", user)
        session['current_node_id'] = current_node.fid
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
        session['current_node_id'] = current_node.fid
        return redirect(url_for('get_location'))


@app.route("/calendar_partial/<path:path>")
@login_required
def calendar_partial(path):
    global places, resources, constants, OPTIONS

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CElection = get_election_data(current_election)
    ctype = gettypeoflevel(path, current_node.level + 1)

    from collections import defaultdict


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

    areas = Featurelayers[ctype].areashtml
    print(f"caldata for {current_node.value} of length {len(areas)} ")

    # share input and outcome tags
    valid_tags = CElection['tags']
    task_tags = {}
    outcome_tags = {}

    for tag, description in valid_tags.items():
        if tag.startswith('L'):
            task_tags[tag] = description
        elif tag.startswith('M'):
            outcome_tags[tag] = description
    print(f"___ Task Tags {valid_tags} Outcome Tags: {outcome_tags} areas:{areas}")
    print(f"🧪 calendar partial level {current_election} - current_node mapfile:{mapfile} - OPTIONS html {OPTIONS['areas']}")


    return render_template(
        "Dash0.html",
        table_types=TABLE_TYPES,
        ELECTIONS=ELECTIONS,
        current_election=current_election,
        options=OPTIONS,
        constants=CElection,
        mapfile=mapfile,
        calfile=calfile,
        DEVURLS=config.DEVURLS
    )


@app.route('/thru/<path:path>', methods=['GET','POST'])
@login_required
def thru(path):
    global TREK_NODES
    global CurrentElection
# map is just a straight transfer to the given path
#    steps = path.split("/")
#    last = steps.pop()
#    current_node = selected_childnode(current_node,last)
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)

    flash ("_________ROUTE/thru:"+path)
    print ("_________ROUTE/thru:",path, CurrentElection)
    current_node = current_node.ping_node(current_election,path)
    if os.path.exists(os.path.join(config.workdirectories['workdir'],path)):
        flash(f"Using existing file: {path}", "info")
        print(f"Using existing file: {path} and CurrentElection: {CurrentElection}")
        visit_node(current_node,current_election,CurrentElection,path)
        return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)
    else:
        flash(f"Creating new mapfile:{path}", "info")
        print(f"Creating new mapfile:{path}")
        fileending = "-"+path.split("-").pop()
        current_node.file = subending(current_node.file,fileending)
        current_node.create_area_map(current_node.getselectedlayers(current_election,path), current_election,CurrentElection)
        print(f"____/THRU OPTIONS areas for calendar node {current_node.value} are {Featurelayers['street'].areashtml} ")
        print(f"____/THRU OPTIONS2 areas for calendar node {current_node.value} are {Featurelayers['walk'].areashtml} ")
        print(f"____/THRU OPTIONS3 areas for calendar node {current_node.value} are {Featurelayers['ward'].areashtml} ")

        visit_node(current_node,current_election,CurrentElection,path)
        return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)

@app.route('/showmore/<path:path>', methods=['GET','POST'])
@login_required
def showmore(path):
    global TREK_NODES
    global CurrentElection

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    steps = path.split("/")
    last = steps.pop().split("--")
    current_node = selected_childnode(current_node,last[1])


    flash ("_________ROUTE/showmore"+path)
    print ("_________showmore",path)

    session['current_node_id'] = current_node.fid

    return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)


@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file received'}), 400

    filename = secure_filename(file.filename)
    print("_______After Secure filename check: ",file.filename)
    save_path = os.path.join(config.workdirectories['workdir'], filename)
    file.save(save_path)
    session['current_node_id'] = current_node.fid

    return jsonify({'message': 'File uploaded', 'path': save_path})


@app.route('/filelist/<filetype>', methods=['POST','GET'])
@login_required
def filelist():
    global TREK_NODES
    global allelectors
    global Treepolys
    global Fullpolys
    global environment

    global formdata
    global layeritems
    global CurrentElection

    flash('_______ROUTE/filelist',filetype)
    print('_______ROUTE/filelist',filetype)
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
    global TREK_NODES
    global allelectors
    global Treepolys
    global Fullpolys
    global streamrag
    global CurrentElection
    global TABLE_TYPES


    global environment
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
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
        session['current_node_id'] = current_node.fid
        calfile = current_node.calfile()

        return render_template('Dash0.html',  formdata=formdata,table_types=TABLE_TYPES, current_election=current_election, group=allelectors , streamrag=streamrag ,mapfile=mapfile,calfile=calfile)
    return redirect(url_for('dashboard'))

@app.route('/postcode', methods=['POST','GET'])
@login_required
def postcode():
# the idea of this service is to locate people's branches using their postcode.
# first get lat long, then search through constit boundaries and pull up the NAME of the one that its IN
    global TREK_NODES
    global Treepolys
    global Featurelayers
    global CurrentElection
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)

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
    pfile = Treepolys[gettypeoflevel(current_node.dir,current_node.level+1)]
    polylocated = find_boundary(pfile,here)
    flash(f'___The branch that contains this postcode is:{polylocated.NAME}')

    return redirect(url_for('dashboard'))


@app.route('/firstpage', methods=['GET', 'POST'])
@login_required
def firstpage():
    global TREK_NODES
    global allelectors
    global Treepolys
    global Fullpolys
    global workdirectories
    global Featurelayers
    global environment
    global layeritems
    global streamrag
    global CurrentElection
    global TABLE_TYPES
    global OPTIONS
    global constants

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)

    print("🔍 Accessed /firstpage")
    print("🧪 current_user.is_authenticated:", current_user.is_authenticated)
    print("🧪 current_user:", current_user)
    print("🧪 current_election:", current_election)
    print("🧪 session keys:", list(session.keys()))
    print("🧪 full session content:", dict(session))
    print("🧪 full currentelection content:", CurrentElection)

    lat = request.args.get('lat')
    lon = request.args.get('lon')
    sourcepath = current_node.dir+"/"+current_node.file
#    lat = 53.2730 - Runcorn
#    lon = -2.7694 - Runcorn
    if lat and lon:
        # Use lat/lon to filter data, e.g., find matching region in GeoJSON
        print(f"Using GPS: lat={lat}, lon={lon}")
        here = (lat, lon)
        Treepolys = {
            'country': {},
            'nation': {},
            'county': {},
            'constituency':{},
            'ward': {},
            'division': {}
        }
        Fullpolys = {
            'country': {},
            'nation': {},
            'county': {},
            'constituency': {},
            'ward': {},
            'division': {}
        }
    # This section of code constructs the homepage sourcepath to ping from a given lat long

        step = ""
        [step,Treepolys['country'],Fullpolys['country']] = filterArea(config.workdirectories['bounddir']+"/"+"World_Countries_(Generalized)_9029012925078512962.geojson",'COUNTRY',here, config.workdirectories['bounddir']+"/"+"Country_Boundaries.geojson")
        sourcepath = step
        [step,Treepolys['nation'],Fullpolys['nation']] = filterArea(config.workdirectories['bounddir']+"/"+"Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson",'CTRY21NM',here, config.workdirectories['bounddir']+"/"+"Nation_Boundaries.geojson")
        sourcepath = sourcepath+"/"+step
        [step,Treepolys['county'],Fullpolys['county']] = filterArea(config.workdirectories['bounddir']+"/"+"Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson",'CTYUA23NM',here, config.workdirectories['bounddir']+"/"+"County_Boundaries.geojson")
        sourcepath = sourcepath+"/"+step
        [step,Treepolys['constituency'],Fullpolys['constituency']] = intersectingArea(config.workdirectories['bounddir']+"/"+"Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson",'PCON24NM',here,Treepolys['county'], config.workdirectories['bounddir']+"/"+"Constituency_Boundaries.geojson")
        sourcepath = sourcepath+"/"+step
        [step,Treepolys['ward'],Fullpolys['ward']] = intersectingArea(config.workdirectories['bounddir']+"/"+"Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson",'WD24NM',here,Treepolys['constituency'], config.workdirectories['bounddir']+"/"+"Ward_Boundaries.geojson")
        sourcepath = sourcepath+"/WARDS/"+step+"/"+step+"-MAP.html"
        [step,Treepolys['division'],Fullpolys['division']] = intersectingArea(config.workdirectories['bounddir']+"/"+"County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson",'CED23NM',here,Treepolys['constituency'], config.workdirectories['bounddir']+"/"+"Division_Boundaries.geojson")

        with open(TREEPOLY_FILE, 'wb') as f:
            pickle.dump(Treepolys, f)
        with open(FULLPOLY_FILE, 'wb') as f:
            pickle.dump(Fullpolys, f)
        print(f"🧪 current election 0 {current_election} - current_node:{current_node.value}")

# geolocation has determined the mapfile (and node ) the you are at.
    if current_user.is_authenticated:
        formdata = {}
        formdata['country'] = "UNITED_KINGDOM"
        flash('_______ROUTE/firstpage')
        print('_______ROUTE/firstpage at :',current_node.value )

        mapfile = sourcepath
# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        current_node = current_node.ping_node(current_election,mapfile)

        print(f"🧪 current election 1 {current_election} - current_node:{current_node.value}")
        print("____Firstpage Mapfile",mapfile, current_node.value)
        atype = gettypeoflevel(mapfile,current_node.level+1)
    # the map under the selected node map needs to be configured
    # the selected  boundary options need to be added to the layer

        Featurelayers['marker'].create_layer(current_election,current_node,'marker')
        print(f"XXXXMarkers {len(Featurelayers['marker']._children)} at election {current_election} at node {current_node.value}")

        Featurelayers[atype].create_layer(current_election,current_node,atype)
        print(f"____/FIRST OPTIONS areas for calendar node {current_node.value} are {OPTIONS['areas']} ")
        streamrag = getstreamrag()
        print(f"🧪 current election 2 {current_election} - current_node:{current_node.value} - atype:{atype} - name {Featurelayers[gettypeoflevel(mapfile, current_node.level)].name} - areas: {Featurelayers[gettypeoflevel(mapfile, current_node.level)].areashtml}")
        flayers = current_node.getselectedlayers(current_election,mapfile)
        current_node.create_area_map(flayers, current_election,CurrentElection)
        print("______First selected node",atype,len(current_node.children),current_node.value, current_node.level,current_node.file)

#        CurrentElection['mapfiles'][-1] = mapfile

        ELECTIONS = get_election_names()

        visit_node(current_node,current_election, CurrentElection, mapfile)
        persist(current_node)
        calfile = current_node.calfile()
        print(f"🧪 firstpage level {current_election} - current_node mapfile:{mapfile} - OPTIONS html {OPTIONS['areas']}")

        return render_template(
            "Dash0.html",
            table_types=TABLE_TYPES,
            ELECTIONS=ELECTIONS,
            current_election=current_election,
            options=OPTIONS,
            constants=CurrentElection,
            mapfile=mapfile,
            calfile=calfile,
            DEVURLS=config.DEVURLS
        )
    else:
        return redirect(url_for('login'))



@app.route('/cards', methods=['POST','GET'])
@login_required
def cards():
    global TREK_NODES
    global allelectors
    global Treepolys
    global Fullpolys
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
                calfile = current_node.calfile()
                return render_template('Dash0.html',  table_types=TABLE_TYPES,formdata=formdata,current_election=CurrentElection[session.get("current_election","DEMO")], ELECTIONS=ELECTIONS, group=allelectors , streamrag=streamrag ,mapfile=mapfile,calfile=calfile)
            else:
                flash ( "Data file does not match selected constituency!")
                print ( "Data file does not match selected constituency!")
        else:
            flash ( "Data file does not match selected area!")
            print ( "Data file does not match selected area!")
    session['current_node_id'] = current_node.fid
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
    current_node = get_current_node(session)
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
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)

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
    global allelectors
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
