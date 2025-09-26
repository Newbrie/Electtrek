from canvasscards import prodcards, find_boundary
from walks import prodwalks
#import electwalks, locmappath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
import config
from config import TABLE_FILE,OPTIONS_FILE,ELECTIONS_FILE,TREEPOLY_FILE,GENESYS_FILE,ELECTOR_FILE,TREKNODE_FILE,FULLPOLY_FILE,MARKER_FILE, RESOURCE_FILE
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
    max_size = 3
    if not isinstance(lst, list):
        return
    if item not in lst:
        lst.append(item)
    if len(lst) > max_size:
        lst.pop(0)  # Remove oldest

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
  stem = filename.replace(".XLSX", "@@@").replace(".CSV", "@@@").replace(".xlsx", "@@@").replace(".csv", "@@@").replace("-PRINT.html", "@@@").replace("-MAP.html", "@@@").replace("-WALKS.html", "@@@").replace("-ZONES.html", "@@@").replace("-PDS.html", "@@@").replace("-DIVS.html", "@@@").replace("-WARDS.html", "@@@")
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
            election_files[name] = None  # or any other value you want

    return election_files

def get_current_election(session=None, session_data=None):
    global CurrentElection
# the sourc eof current election mu reflect what the user sees as the active tab or what is in session_data
    try:
        if not session or 'current_election' not in session:
            current_election = "DEMO"
        elif not session_data or 'current_election' not in session_data:
            current_election = "DEMO"
    except Exception as e:
        current_election = "DEMO"
        print(f"___System error: No session or current_election: {e} ")

    """
    Returns the current election from session data.
    """

    if session and 'current_election' in session and session.get('current_election') in ELECTIONS:
        current_election = session.get('current_election')
        print("[Main Thread] current_election from session:", current_election)
    elif session_data and 'current_election' in session_data and session_data.get('current_election') in ELECTIONS:
        current_election = session_data.get('current_election')
        print("[Background Thread] current_election from session_data:", current_election)
    else:
        current_election = "DEMO"
        print("⚠️ current_election not found in session so using DEMO")

    CurrentElection = get_election_data(current_election)

    return current_election

def get_election_data(current_election):
    file_path = ELECTIONS_FILE.replace(".json",f"-{current_election}.json")
    print("____Reading CurrentElection File:",ELECTIONS_FILE.replace(".json",f"-{current_election}.json" ))
    if  os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, 'r') as f:
                CurrentElection = json.load(f)
            print(f"___Loaded CurrentElection Data:{ current_election }: {CurrentElection }" )
            return CurrentElection
        except Exception as e:
            print(f"❌ Failed to read Election JSON: {e}")
    return None

def save_election_data (c_election,ELECTION):
    file_path = ELECTIONS_FILE.replace(".json",f"-{c_election}.json")
    try:
        if  os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print("____Saving Election File:",c_election,"-",ELECTION)
            with open(file_path, 'w') as f:
                json.dump(ELECTION, f, indent=2)
            print(f"✅ JSON written safely to {file_path}")
        else:
            with open(file_path, 'w') as f:
                json.dump(ELECTION, f, indent=2)
            print(f"✅ New Election JSON: {file_path}")
    except Exception as e:
        print(f"❌ Failed to write Election JSON: {e}")
    return

def get_current_node(session=None, session_data=None):
    global TREK_NODES
    try:
        if not session or 'current_node_id' not in session:
            print(f"___System error: No session or current_node: ")
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
        current_node_id = session.get('current_node_id')
        print("[Main Thread] current_node_id from session:", session.get('current_node_id'))
        node = TREK_NODES.get(session.get('current_node_id'))
    elif session_data and 'current_node_id' in session_data and session_data.get('current_node_id'):
        print("[Background Thread] current_node_id from session_data:", session_data.get('current_node_id'))
        current_node_id = session_data.get('current_node_id')
        node = TREK_NODES.get(session_data.get('current_node_id'))
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
    global resources
    global CurrentElection

    if  os.path.exists(TREEPOLY_FILE) and os.path.getsize(TREEPOLY_FILE) > 0:
        with open(TREEPOLY_FILE, 'rb') as f:
            Treepolys = pickle.load(f)
    if  os.path.exists(FULLPOLY_FILE) and os.path.getsize(FULLPOLY_FILE) > 0:
        with open(FULLPOLY_FILE, 'rb') as f:
            Fullpolys = pickle.load(f)
    if  os.path.exists(MARKER_FILE) and os.path.getsize(MARKER_FILE) > 0:
        with open(MARKER_FILE, 'r',encoding="utf-8") as f:
            markerframe = json.load(f)
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
    global markerframe
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

    print('___persisting node ', node.value)
    session['current_node_id'] = node.fid
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


Historynodelist = []
Historytitle = ""


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


main_index = None # for file processing

#with open(OPTIONS_FILE, "r") as f:
#    OPTIONS = json.load(f)
print("🔍 type of json5:", type(json))
with open(TABLE_FILE, "r") as f:
    stream_table = json.load(f)

data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))
VID_json = json.dumps(VID)  # Convert to JSON string

if  os.path.exists(config.workdirectories['workdir']+"Resources.csv") and os.path.getsize(config.workdirectories['workdir']+"Resources.csv") > 0:
    resourcesdf = pd.read_csv(config.workdirectories['workdir']+"Resources.csv",sep='\t', engine='python')
    resources = resourcesdf.set_index('Code').to_dict(orient='index')
    print("____Resources file read in")
    # need to save to ELECTIONS
    with open(RESOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(resources, f, indent=2)
with open(RESOURCE_FILE, 'r', encoding="utf-8") as f:
    resources = json.load(f)

def find_children_at(level):
    [x.value for x in current_node.childrenoftype('walk')]
    return dropdownlist

areaoptions = ["UNITED_KINGDOM/ENGLAND/SURREY/SURREY_HEATH/SURREY_HEATH-MAP.html"]

OPTIONS = {
    "territories": ElectionTypes,
    "territoryoptions": areaoptions,
    "yourparty": VID,
    "previousParty": VID,
    "resources" : resources,
    "candidate" : resources,
    "chair" : resources,
    "tags": CurrentElection['tags'],
    "autofix" : onoff,
    "VNORM" : VNORM,
    "VCO" : VCO,
    "streams" : ELECTIONS,
    "stream_table": stream_table
    # Add more mappings here if needed
}


with open(OPTIONS_FILE, 'w') as f:
    json.dump(OPTIONS, f, indent=2)

IGNORABLE_SEGMENTS = {"PDS", "WALKS", "DIVS", "WARDS"}

FILE_SUFFIXES = [
    "-PRINT.html", "-MAP.html", "-WALKS.html",
    "-ZONES.html", "-PDS.html", "-DIVS.html", "-WARDS.html"
]

LEVEL_ZOOM_MAP = {
    'country': 12, 'nation': 13, 'county': 14, 'constituency': 15,
    'ward': 16, 'division': 16, 'polling_district': 17,
    'walk': 17, 'walkleg': 18, 'street': 18
}

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


    def ping_node(self, c_election, dest_path):
        global Treepolys
        global Fullpolys
        global levels
        global TREK_NODES
        global allelectors
        global areaelectors
        global CurrentElection
        def strip_filename_from_path(path):
            for suffix in [
                "-PRINT.html", "-MAP.html", "-WALKS.html", "-ZONES.html",
                "-PDS.html", "-DIVS.html", "-WARDS.html", "-DEMO.html"
            ]:
                path = path.replace(suffix, "@@@")
            return path
        def split_clean_path(path):
            path = strip_filename_from_path(path)
            return [part for part in path.strip("/").split("/") if part not in ["DIVS", "PDS", "WALKS", "WARDS", ""] and "@@@" not in part]

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

        print(f"   🪜 self_path: {self_path}")
        print(f"   🪜 dest_path_parts: {dest_path_parts}")

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

            print(f"   ➡️ Looking for part: '{part}' at level {next_level} (ntype={ntype})")

            # Expand children dynamically
            if next_level <= 4:
                print(f"      🛠 create_map_branch({ntype})")
                node.create_map_branch(c_election, ntype)
            elif next_level <= 6:
                print(f"      🛠 create_data_branch({ntype})")
                node.create_data_branch(c_election, ntype)

            # Try to find a matching child
            matches = [child for child in node.children if child.value == part]
            if not matches:
                print(f"   ❌ No match for '{part}' under node '{node.value}'. Returning original node: {self.value}")
                return self

            node = matches[0]
            print(f"   ✅ Descended to: {node.value} (level {node.level})")

        # Step 5: Handle optional zoom keyword
        if keyword in LEVEL_ZOOM_MAP:
            node.zoom_level = LEVEL_ZOOM_MAP[keyword]
            print(f"   🔍 Set zoom level to {node.zoom_level} due to keyword '{keyword}'")

        print(f"✅ Reached destination node: {node.value} (level {node.level})")
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
                print("   ✅ create_data_branch() called")
            else:
                print("   ℹ️ No further branching at this level.")
        except Exception as e:
            print(f"   ⚠️ Failed to create child branches: {e}")

        with open(TREKNODE_FILE, 'wb') as f:
            pickle.dump(TREK_NODES, f)
        return node



    def ping_node2(self,c_election,dest_path):
        global Treepolys
        global Fullpolys
        global levels
        global TREK_NODES
        global allelectors
        global areaelectors
        global CurrentElection

# used to grab the node in the node tree at which an operation is to be conducted
# the dest_path provides the steps to get from the top to the destination leaf
#  in dest_path the moretype values -  ward, etc if you want to create nodes of certain type at the end of the search

        print(f"_____Treepolys in {c_election} for ping:{TREEPOLY_FILE}")
        moretype = ""
        dest = dest_path
        if dest_path.find(" ") > -1:
            dest_path3 = dest_path.split(" ")
            moretype = dest_path3.pop() # take off any trailing parameters
            dest = dest_path3[0]
# dest not provides the first part of the part only (no moretype)

        deststeps = list(reversed(stepify(dest)))
#dest steps is a list of steps from lowest(level) to highest(level) leaf
#        sourcetrunk = list(reversed(self.path_intersect(dest))) # lowest left - UK right
#sourcetrunk is the overlapping steps of the start(self node) with the dest path
        node = self.upto(deststeps) # the start node for the depth first Ping_node search
#so node will be the node at which to start the ping search len(trunk will range from 1 to level)
# the steps to cycle through will be the last trunk node plus remaining steps in dest_path
        steps = list(deststeps[0:len(deststeps)-node.level]) # lowest level righ( UK pops first)
        print(f"____ping self: {self.value} start: {node.value}  deststeps: { deststeps} vs remaining steps: {steps} :")
        block = pd.DataFrame()
        newnodes = [node]
#starting at the bottom of the trunk
        i = 0
        next = ""
        if len(steps) == 0:
            print("____ping self: {self.value} invalid path ABORT:")
            return None
        while steps:
# shuffle down child nodes starting at top looking for the 'next' = child.value
            next = steps.pop()
# set the next level of selected type driven by the target path + moretype parameter

            print(f"____In path {dest_path} after pop next {next} vs newnodes {[x.value for x in newnodes]} :")
            if next in ["PDS","WALKS","DIVS","WARDS"]: # just ignore these steps in the path
                pass
            else:
                # start with the topmost node + children
                i = i+1
                options = [node.children]
                catch = [x for x in options if x.value == next]
                print(f"____Ping Loop Test in {c_election}- Next:{next} vs Node:{node.value} at node lev {node.level}", "node children:",[x.value for x in node.children],"Catch:", catch)
                if catch:
                    node = catch[0]
                    print("____ EXISTING NODE FOUND  ",node.value,catch[0].value, moretype)
                    if steps == []:
# caught node but no more in tree so either create new map nodes (level < 4) or create new data nodes (>=4)
                        ntype = gettypeoflevel(dest_path,node.level+1)
# ping also used to retrieve children of destination node in dest_path
                        print(f"____ Creating new nodes at {node.value} / {catch[0].value} lev {node.level} of type: {ntype}")
                        if node.level < 4:
# catch but another map layer poss so create map children
                            newnodes = node.create_map_branch(c_election,ntype)
                            if len(newnodes) == 0:
                                print(f"____ Error1 - cant find any map children {newnodes} in {node.value} of type {ntype} ")
                        elif node.level < 6:
# catch but beyond map level, and within data level so create data children
                            newnodes = node.create_data_branch(c_election,ntype)
                            if len(newnodes) == 0:
                                print(f"____ Data Leaf - no data children {newnodes}  in {node.value} of type {ntype} ")
                elif node.level < 4:
                    steps.append(next)
# No catch at ward/div level < 4 so back next node so add branch to tree from map
                    ntype = gettypeoflevel(dest_path, node.level+1)
                    print("____ TRYING NEW MAP NODES AT ", node.value,node.level,ntype,dest_path)
                    newnodes = node.create_map_branch(c_election,ntype)
                    print(f"____ NEW NODES AT {node.value} lev {node.level} newnodes {[x.value for x in newnodes]} and children {[x.value for x in node.children]}")
                    if len(newnodes) <= 1:
                        print(f"____ Error2 - cant find any map children {newnodes}  in {node.value} of type {ntype} ")
                        node = self
                        return node
                elif node.level == 4:
                    steps.append(next)
# No catch at PD/Walk level so add a data branch of type PDs(polling_districts) or Walks (from kmeans)
                    ntype = gettypeoflevel(dest_path, node.level+1)
                    print(f"____ TRYING NEW DATA L4 NODES AT {node.value} ",node.level,ntype,dest_path)
                    newnodes = node.create_data_branch(c_election,ntype)
                    print(f"____ NEW DATA L4 NODES AT {node.value} lev {node.level} newnodes {[x.value for x in newnodes]} and children {[x.value for x in node.children]}")
                    if len(newnodes) == 0:
                        print(f"____ Error - cant find any data children {newnodes}  in {node.value} of type {ntype} ")
                        node = self
                        return node
                elif node.level == 5:
                    steps.append(next)
# No catch at street level so add a data branch - lower data nodes will be streets or walklegs
                    ntype = gettypeoflevel(dest_path, node.level+1)
                    print(f"____ TRYING NEW DATA L5 NODES AT {node.value} ",node.level,ntype,dest_path)
                    newnodes = node.create_data_branch(c_election,ntype)
                    print(f"____ NEW DATA L5 NODES AT {node.value} lev {node.level} newnodes {[x.value for x in newnodes]} and children {[x.value for x in node.children]}")
                    if len(newnodes) <= 1:
                        print(f"____ cant find any data children {newnodes}  in {node.value} of type {ntype} ")
                        node = self
                        return node
                else :
#No catch at elector level so exit
                    break
                    #

        print("____ping end:", node.value, node.level,next, steps, )


        return node

    def getselectedlayers(self,path):
        global Featurelayers
        global markerframe
#add children layer(level+1), eg wards,constituencies, counties
        print(f"_____layerstest0 type:{self.value},{self.type} path: {path}")

        selected = []
        childtype = gettypeoflevel(path,self.level+1)
        if childtype == 'elector':
            selected = []
        else:
            selectc = Featurelayers[childtype]
            selected = [selectc]
            print(f"_____layerstest1 {self.value} type:{childtype} layers: {list(reversed(selected))}")
        if self.level > 0 :
#add siblings layer = self.level eg constituencies
    #        if len(selects._children) == 0:
            # parent children = siblings, eg constituencies, counties, nations
            print(f"_____layerstest20 {self.parent.value} type:{self.type} layers: {list(reversed(selected))}")
            selects = Featurelayers[self.type].create_layer(current_election,self.parent,self.type)
            selected.append(selects)
            print(f"_____layerstest2 {self.parent.value} type:{self.type} layers: {list(reversed(selected))}")
        if self.level > 1:
#add parents layer, eg counties, nations, country
#            if len(selectp._children) == 0:
            print(f"_____layerstest30 {self.parent.parent.value} type:{self.parent.type} layers: {list(reversed(selected))}")
            selectp = Featurelayers[self.parent.type].create_layer(current_election,self.parent.parent,self.parent.type)
            selected.append(selectp)
            print(f"_____layerstest3 {self.parent.parent.value} type:{self.parent.type} layers: {list(reversed(selected))}")


        print(f"_____layerstest40 {self.findnodeat_Level(2).value} markers layers: {list(reversed(selected))}")
        markerlayer = Featurelayers['marker']
        print(f"_____layerstest401 {markerlayer} markers layers: {list(reversed(selected))}")
        selected.append(markerlayer)
        print(f"_____layerstest4 {self.findnodeat_Level(2).value} markers layers: {list(reversed(selected))}")
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
            typechildren = [x for x in self.children if x.type == electtype and x.election == session.get('current_election')]
        else:
            typechildren = [x for x in self.children if x.type == electtype]
        print(f"__for node:{self.value} at level {self.level} there are {len(self.children)} of which  {len(typechildren)} are type {electtype} ")

        return typechildren


    def locmappath(self,real):
        global levelcolours

        dir = self.dir
        if self.type == 'polling_district'and dir.find("/PDS") <= 0:
                dir = self.dir+"/PDS"
        elif self.type == 'walk'and dir.find("/WALKS") <= 0:
                dir = self.dir+"/WALKS"
        target = config.workdirectories['workdir'] + dir + "/" + self.file

        dir = os.path.dirname(target)
        print(f"____target director {dir} and filename:{self.file}")
        os.chdir(config.workdirectories['workdir'])
        if real == "":
            if not os.path.exists(dir):
              os.makedirs(dir)
              print("_______Folder %s created!" % dir)
              os.chdir(dir)
            else:
              print("________Folder %s already exists" % dir)
              os.chdir(dir)
        else:
            if not os.path.exists(dir):
              os.system("ln -s "+real+" "+ target)
              os.system("cd -P "+dir)
              print("______Symbolic Folder %s created!" % dir)
            else:
              os.system("cd -P "+dir)
              print("_______Folder %s already exists" % dir)
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
            print("⚠️ 'Zone' column missing from namepoints. Defaulting all nodes to black.")
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
        print('______Create Nodelist :',nodetype,[x.value for x in fam_nodes])

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

        mask = allelectors['Election'] == c_election
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
                    streetdf0 = pd.DataFrame(PDelectors, columns=['Election','StreetName','ENOP', 'Long', 'Lat'])
                    streetdf1 = streetdf0.rename(columns= {'StreetName': 'Name'})
                    g = {'Election':'first','Lat':'mean','Long':'mean', 'ENOP':'count'}
                    streetdf = streetdf1.groupby(['Name']).agg(g).reset_index()
                    print("____Street df: ",streetdf)
                    nodelist = self.create_name_nodes(c_election,'street',streetdf,"-PRINT.html") #creating street_nodes with mean street pos and elector counts
                elif electtype == 'walkleg':
                    mask = areaelectors['WalkName'] == self.value
                    walkelectors = areaelectors[mask]
    #                WalklegPts = [(x[0],x[1],x[2],x[3]) for x in walkelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                    walklegdf0 = pd.DataFrame(walkelectors, columns=['Election','StreetName','ENOP', 'Long', 'Lat'])
                    walklegdf1 = walklegdf0.rename(columns= {'StreetName': 'Name'})
                    g = {'Election':'first','Lat':'mean','Long':'mean','ENOP':'count'}
                    walklegdf = walklegdf1.groupby(['Name']).agg(g).reset_index()
                    print("____Walkleg df: ",walklegdf)
                    print("____Walkleg elector df: ",walklegdf1)
                    nodelist = self.create_name_nodes(c_election,'walkleg',walklegdf,"-PRINT.html") #creating walkleg_nodes with mean street pos and elector counts
            except Exception as e:
                print("❌ Error during data branch generation:", e)
                return []
        else:
            print("_____ Electoral file contains no relevant data for this area - Please load correct file",len(allelectors), len(areaelectors))
            nodelist = []
        print(f"____Created Data Branch for Election: {c_election} in area: {self.value} creating: {len(nodelist)} of child type {electtype} from: {len(areaelectors)} electors")

        return nodelist

    def create_map_branch(self,c_election,electtype):
        global Treepolys
        global Fullpolys
        global TREK_NODES

        current_election = c_election
        Overlaps = {
        "country" : 1,
        "nation" : 0.1,
        "county" : 0.009,
        "constituency" : 0.0035,
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
        if parent_geom.empty:
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


    def create_area_map(self, flayers):
        from folium import IFrame
        from branca.element import Element, MacroElement

        LEVEL_ZOOM_MAP = {
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
        # Construct map title


        move_close_button_css = """
        <style>
        /* Move close button to top-left */
        .leaflet-popup-close-button {
            right: auto !important;
            left: 10px !important;
            top: 10px !important;
        }

        /* Optional: style it differently */
        .leaflet-popup-close-button {
            font-size: 16px;
            color: #444;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 4px;
            padding: 2px 5px;
        }
        </style>
        """

        # Step 3: Inject JavaScript to stop scroll propagation
        script = """
        <script>
        document.addEventListener('DOMContentLoaded', function () {
            const popupElements = document.querySelectorAll('.leaflet-popup-content');
            popupElements.forEach(function (popup) {
                popup.addEventListener('wheel', function (e) {
                    e.stopPropagation();
                });
            });
        });
        </script>
        """
        # Wrap scrollfix as a Folium Element and add to map
        js_element = Element(script)


        title = f"{self.value} MAP"

        title_html = f'''<h1 style="z-index:1100;color: black;position: fixed;left:100px;">{title}</h1>'''
        print("_____before adding title at:", self.value, self.level)

        # Create map centered on centroid with appropriate zoom
        map_center = self.centroid  # [lat, lon]
        zoom = LEVEL_ZOOM_MAP[self.type]  # Fallback to 13 if level not found

        Map = folium.Map(
            location=map_center,
            trackResize=False,
            tiles="OpenStreetMap",
            crs="EPSG3857",
            zoom_start=zoom,
            width='100%',
            height='800px'
        )

        # Add the map title
        Map.get_root().html.add_child(folium.Element(title_html))
        Map.get_root().html.add_child(folium.Element(move_close_button_css))
        Map.get_root().html.add_child(js_element)

        # Add all layers
        for layer in flayers:
            Map.add_child(layer)

        # Ensure there's only one LayerControl
        if not any(isinstance(child, folium.map.LayerControl) for child in Map._children.values()):
            Map.add_child(folium.LayerControl())

        # Add custom CSS/JS
        Map.add_css_link("electtrekprint", "https://newbrie.github.io/Electtrek/static/print.css")
        Map.add_css_link("electtrekstyle", "https://newbrie.github.io/Electtrek/static/style.css")
        Map.add_js_link("electtrekmap", "https://newbrie.github.io/Electtrek/static/map.js")

        # Fit map to bounding box
        print("_____before saving map file:", self.locmappath(""), len(Map._children), self.value, self.level)
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
                    Map.location = self.centroid
                    Map.zoom_start = LEVEL_ZOOM_MAP.get(self.type, 13)
                else:
                    print("✅ BBox is valid, applying fit_bounds")
                    Map.fit_bounds([sw, ne], padding=(0, 0))

            except (TypeError, ValueError) as e:
                print(f"⚠️ Invalid bbox values: {self.bbox} | Error: {e}")
        else:
            print(f"⚠️ BBox is missing or badly formatted: {self.bbox}")


        dir = self.dir
        # Save to file
        target = self.locmappath("")
        Map.save(target)
        print("Centroid raw:", self.centroid)
        print("_____saved map file:", target, len(flayers), self.value, self.dir, self.file)

        return Map


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
        child_node.tagno = len([ x for x in self.children if x.type == etype])

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
        target = self.locmappath("")
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

def build_street_list_html(streets_df):
    html = '''
    <div style="
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 10px;
        background-color: white !important;
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
                    <th style="text-align:left; padding: 4px; border-bottom: 1px solid #ddd; font-size: 8pt;">Street Name</th>
                    <th style="text-align:left; padding: 4px; border-bottom: 1px solid #ddd;font-size: 8pt;">Houses</th>
                    <th style="text-align:left; padding: 4px; border-bottom: 1px solid #ddd;font-size: 8pt;">Number</th>
                    <th style="text-align:left; padding: 4px; border-bottom: 1px solid #ddd;font-size: 8pt;">Prefix</th>
                </tr>
            </thead>
            <tbody>
    '''

    for _, row in streets_df.iterrows():
        nums = sorted(set(
            n.strip() for n in row['AddressNumber'].split(',')
            if n.strip() and n.strip().lower() != 'nan'
        )) if pd.notna(row['AddressNumber']) else []

        pres = sorted(set(
            p.strip() for p in row['AddressPrefix'].split(',')
            if p.strip() and p.strip().lower() != 'nan'
        )) if pd.notna(row['AddressPrefix']) else []

        hos = len(nums) + len(pres)

        # 🔢 Convert number strings to actual numbers (when possible)
        num_values = []
        for n in nums:
            try:
                num_val = int(''.join(filter(str.isdigit, n)))
                num_values.append(num_val)
            except:
                pass  # skip non-numeric

        # 🧾 Format the min-max display or fallback to "-"
        if num_values:
            min_val = min(num_values)
            max_val = max(num_values)
            num_display = f"({min_val} - {max_val})"
        else:
            num_display = "( - )"

        # Prefix dropdown remains the same
        pre_select = f"<select>{''.join(f'<option>{p}</option>' for p in pres)}</select>"

        html += f'''
            <tr>
                <td style="padding: 4px;font-size: 8pt;"><b>{row['Name']}</b></td>
                <td style="padding: 4px;font-size: 8pt;"><i>{hos}</i></td>
                <td style="padding: 4px;font-size: 8pt;">{num_display}</td>
                <td style="padding: 4px;font-size: 8pt;">{pre_select}</td>
            </tr>
        '''

    html += '''
            </tbody>
        </table>
    </div>
    '''
    return html




class ExtendedFeatureGroup(FeatureGroup):
    def __init__(self, name=None, overlay=True, control=True, show=True, type=None, id=None, **kwargs):
        # Pass standard arguments to the base class
        super().__init__(name=name, overlay=overlay, control=control, show=show, **kwargs)
        self.name = name
        self.id = id

    def reset(self):
        # This clears internal children before rendering
        self._children.clear()
        print("____reset the layer",len(self._children), self)
        return self


    def generate_voronoi_with_geovoronoi(self, c_election, target_node, vtype, add_to_map=True, color="#3388ff"):
        global allelectors
        shapecolumn = { 'polling_district' : 'PD','walk' : 'WalkName' ,'ward' : 'Area', 'division' : 'Area', 'constituency' : 'Area'}

        print("📍 Starting generate_voronoi_with_geovoronoi")
        current_node = get_current_node(session)
        print(f"🔄 Retrieved current_node: {current_node}")

        CurrentElection = get_election_data(c_election)
        print(f"🗳️ Loaded election data for: {c_election}")

        territory_path = CurrentElection['territory']
        print(f"📁 Territory path: {territory_path}")

        Territory_node = current_node.ping_node(c_election, territory_path)
        print(f"📌 Territory node: {Territory_node}")

        ttype = gettypeoflevel(territory_path, Territory_node.level)
        print(f"📂 Territory type: {ttype}")

        pfile = Treepolys[ttype]
        print(f"🗺️ Loaded polygon file for type '{ttype}', records: {len(pfile)}")

        # Select boundary by FID
        Territory_boundary = pfile[pfile['FID'] == Territory_node.fid]
        print(f"🧭 Filtered territory boundary by FID = {Territory_node.fid}, matches: {len(Territory_boundary)}")

        # Get the shapely polygon for area
        if hasattr(Territory_boundary, 'geometry'):
            area_shape = Territory_boundary.union_all()
            print("✅ Retrieved union of territory boundary geometry")
        else:
            area_shape = Territory_boundary
            print("⚠️ Warning: Territory_boundary has no .geometry — using raw")

        children = target_node.childrenoftype(vtype)
        print(f"👶 Found {len(children)} children of type '{vtype}'")

        if not children:
            print("⚠️ No children found — exiting early")
            return []

        # Build coords array from centroids
        from shapely.ops import nearest_points

        mask = (
                (allelectors['Election'] == c_election) &
                (allelectors['Area'] == target_node.value)
            )
        nodeelectors = allelectors[mask]


        coords = []
        valid_children = []

        for child in children:
            cent = child.centroid
            if isinstance(cent, (tuple, list)) and len(cent) == 2:
                lon, lat = cent[1], cent[0]  # Note: [lon, lat] = [x, y]
            elif hasattr(cent, 'x') and hasattr(cent, 'y'):
                lon, lat = cent.x, cent.y
            else:
                continue

            point = Point(lon, lat)

            # Ensure it's within the polygon
            if not area_shape.contains(point):
                child = child.ping_node(c_election,child.dir)
                cent = child.child.centroid
                point = Point(cent[1],cent[0])
#                point, _ = nearest_points(area_shape, point)

            coords.append([point.x, point.y])  # Ensure only 2D coords
            valid_children.append((child, point))




        # Clip Voronoi regions to area_shape
        try:
            print("🧮 Generating Voronoi regions using geovoronoi...")
            # Pass coords as a list of Point objects
            coords = np.array(coords)
            # Ensure 2D shape
            if coords.shape[1] != 2:
                raise ValueError(f"Expected 2D coordinates, got shape: {coords.shape}")

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
                matched_child.voronoi_region = region_polygon
                print(f"✅ Region {region_index} assigned to child: {matched_child.value}")
                voronoi_regions.append({'child': matched_child, 'region': region_polygon})
            else:
                print(f"⚠️ No matching child found for region index {region_index}")


            if add_to_map:
                label = str(child.value)

                # Here, we dynamically assign a color, either from the child or default to color
                fill_color = getattr(child, "col", color)  # If no color assigned, default to passed color

                # You can also dynamically generate colors based on the child or other parameters
                # For example, using a hash of the child's value to generate a unique color:
                # fill_color = '#' + hashlib.md5(str(child.value).encode()).hexdigest()[:6]

                mask1 = nodeelectors[shapecolumn[vtype]] == child.value
                region_electors = nodeelectors[mask1]

                if not region_electors.empty and len(region_electors.dropna(how="all")) > 0:
                    Streetsdf0 = pd.DataFrame(region_electors, columns=['StreetName', 'ENOP','Long', 'Lat', 'Zone','AddressNumber','AddressPrefix' ])
                    Streetsdf1 = Streetsdf0.rename(columns= {'StreetName': 'Name'})
                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count', 'Zone' : 'first', 'AddressNumber': Hconcat , 'AddressPrefix' : Hconcat,}
                    Streetsdf = Streetsdf1.groupby(['Name']).agg(g).reset_index()
                    streetstag = build_street_list_html(Streetsdf)
                    print ("______Voronoi Streetsdf:",len(Streetsdf), streetstag)
                    print (f" {len(Streetsdf)} streets exist in {target_node.value} under {c_election} election for the {shapecolumn[vtype]} column with this value {child.value}")
                else:
                    streetstag = ""
                    flash("no data exists for this election at this location")
                    print (f" no streets exist at {target_node.value} under this {c_election} election for this {shapecolumn[vtype]} column with this value {child.value}")



                gj = GeoJson(
                    data=region_polygon.__geo_interface__,
                    style_function=lambda feature, col=fill_color: {
                        'fillColor': col,
                        'color': 'black',
                        'weight': 1,
                        'fillOpacity': 0.4,
                    },
                    name=f"Voronoi {label}",
                    tooltip=Tooltip(label),
                    popup=Popup(streetstag),
                )
                gj.add_to(self)
                print(f"🖼️ Added GeoJson for child: {label} nodecol: {child.col} with color: {fill_color}")



                centroid = region_polygon.centroid
                cent = [centroid.y, centroid.x]  # folium expects (lat, lon)

                tag = child.value
                mapfile = child.mapfile()
                tcol = get_text_color(to_hex(fill_color))
                bcol = adjust_boundary_color(to_hex(fill_color), 0.7)
                fcol = invert_black_white(tcol)
                self.add_child(folium.Marker(
                     location=[cent[0], cent[1]],
                     icon = folium.DivIcon(
                            html=f'''
                            <a href='{mapfile}'><div style="
                                color: {tcol};
                                font-size: 10pt;
                                font-weight: bold;
                                text-align: center;
                                padding: 2px;
                                white-space: nowrap;">
                                <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                border: 2px solid black;">{tag} </span>
                                </div></a>
                                ''',
                           )
                           )
                           )
                print(f"🖼️ Added walk area marker: {tag} with color: {tcol}")

            voronoi_regions.append({
                'child': child,
                'region': region_polygon
            })

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
                        html='''
                        <a href='{2}'><div style="
                            color: {3};
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: {4}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{0}</span>
                            {1}</div></a>
                            '''.format(tag,"",mapfile,tcol,fcol),
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
                        html='''
                        <a href='{2}'><div style="
                            color: {3};
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: {4}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{0}</span>
                            {1}</div></a>
                            '''.format(num,tag,mapfile,tcol,fcol),
                       )
                       )
                       )
        print("________Layer map polys",herenode.value,herenode.level,self._children)
        return self._children

    def create_layer(self, c_election, node, intention_type):
        global allelectors
        print(f"__Layer id:{self.id} value:{node.value} type: {intention_type} layer children:{len(self._children)} node children:{len(node.children)}")
        if intention_type == 'marker':
            # always regen markers ev
            self._children.clear()
            self.id = node.fid
            self.add_genmarkers(node,'marker')
            return self
# each layer content is identified by the node id at which it created, so new node new content, same node old content
        if self.id != node.value:
            self._children.clear()
            self.id = node.value
    # create the content for an existing layer derived from the node children and required type
            if intention_type == 'street' or intention_type == 'walkleg':
                self.add_nodemarks(node,intention_type)
            elif intention_type == 'polling_district' or intention_type == 'walk':
                print(f"calling creation of voronoi in {c_election} - node {node.value} type {intention_type}")
#                self.add_shapenodes(c_election,node,intention_type)
                self.generate_voronoi_with_geovoronoi(c_election,node,intention_type)
            elif intention_type == 'marker':
                self.add_genmarkers(node,'marker')
            else:
                self.add_nodemaps(node, intention_type)
        else:
        # each layer content is identified by the node id at which it created, so new node new content, same node old content
            self.id = "XXXX-Replace_XXXX"
            print("___New Layer with node.value = self.id ie it already exists :", self.id)
            #the exist id = the new id , dont do anything
        return self


    def add_genmarkers(self,node,type):
        def compute_font_size(days):
            if days <= -35:
                return 10
            elif days > -35 and days <= -20:
                return 14
            elif days > -20 and days <= -10:
                return 18
            else:
                return 22


        def offset_latlong(lat, lon, bearing_deg, distance_m=100):
            """
            Offsets a latitude and longitude by a distance (in meters) in a given bearing.
            No external libraries used.
            """
            R = 6371000  # Radius of Earth in meters

            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)
            bearing_rad = math.radians(bearing_deg)

            delta = distance_m / R

            new_lat_rad = math.asin(math.sin(lat_rad) * math.cos(delta) +
                                    math.cos(lat_rad) * math.sin(delta) * math.cos(bearing_rad))

            new_lon_rad = lon_rad + math.atan2(
                math.sin(bearing_rad) * math.sin(delta) * math.cos(lat_rad),
                math.cos(delta) - math.sin(lat_rad) * math.sin(new_lat_rad)
            )

            return math.degrees(new_lat_rad), math.degrees(new_lon_rad)


        def get_latlong(Postcode, Lat, Long):
            # Only call API if Lat or Long is NaN or missing
            if Lat is not None and Long is not None and not (math.isnan(Lat) or math.isnan(Long)):
                return [round(Lat, 6), round(Long, 6)]

            # If postcode empty or None, fallback immediately
            if not Postcode:
                print("Empty postcode; using default lat/long")
                Long = statistics.mean([-7.57216793459, 1.68153079591])
                Lat = statistics.mean([49.959999905, 58.6350001085])
                return [round(Lat, 6), round(Long, 6)]

            url = "http://api.getthedata.com/postcode/" + str(Postcode).replace(" ", "+")
            try:
                myResponse = requests.get(url, timeout=5)
                print("retrieving postcode latlong", url)
                if myResponse.status_code == 200:
                    latlong = myResponse.json()
                    if latlong.get('status') == 'match' and 'data' in latlong:
                        Lat = float(latlong['data']['latitude'])
                        Long = float(latlong['data']['longitude'])
                        print(f"MATCH for postcode {Postcode}, {Lat} {Long}")
                    else:
                        print(f"No match for postcode {Postcode}, using default lat/long")
                        Long = statistics.mean([-7.57216793459, 1.68153079591])
                        Lat = statistics.mean([49.959999905, 58.6350001085])
                else:
                    print(f"Failed to fetch latlong for postcode {Postcode}, status code: {myResponse.status_code}")
                    Long = statistics.mean([-7.57216793459, 1.68153079591])
                    Lat = statistics.mean([49.959999905, 58.6350001085])
            except Exception as e:
                print(f"Exception fetching latlong for postcode {Postcode}: {e}")
                Long = statistics.mean([-7.57216793459, 1.68153079591])
                Lat = statistics.mean([49.959999905, 58.6350001085])

            return [round(Lat, 6), round(Long, 6)]


        print("___MARKER_FILE:", MARKER_FILE)

        if  not os.path.exists(MARKER_FILE) or os.path.getsize(MARKER_FILE) == 0:
            raise FileNotFoundError(f"MARKER_FILE not found: {MARKER_FILE}")

        with open(MARKER_FILE, 'r', encoding="utf-8") as f:
            markerframe = json.load(f)  # This is a list of dicts

        today = datetime.today().date()

        if len(markerframe) > 0:
            for row in markerframe:
                lat = row.get("Lat", float('nan'))
                lng = row.get("Long", float('nan'))
                postcode = row.get("Postcode", "")
                offset_deg = row.get("Off", 0)  # Default to 0 if not present

                # Get original lat/lng if needed
                lat, lng = get_latlong(postcode, lat, lng)

                # Apply offset if valid lat/lng
                if not math.isnan(lat) and not math.isnan(lng):
                    lat, lng = offset_latlong(lat, lng, offset_deg, 200)  # 100m radius

                row["Lat"] = lat
                row["Long"] = lng

                raw_date = str(row.get("EventDate", "")).strip()

                try:
                    # Parse date from string like "21Aug25"
                    parsed_date = datetime.strptime(raw_date, "%d%b%y").date()
                except Exception as e:
                    print(f"Failed to parse date '{raw_date}': {e}")

                    # Fallback: today + 35 days
                    parsed_date = datetime.today().date() + timedelta(days=35)

                    # Store fallback in same string format as raw date
                    raw_date = parsed_date.strftime("%d%b%y")
                    row["EventDate"] = raw_date  # Store as string fallback
                else:
                    # Store parsed_date back as string, consistent format
                    row["EventDate"] = parsed_date.strftime("%d%b%y")

                # Calculate DaysTo from today to parsed_date
                today = datetime.today().date()
                row["DaysTo"] = (parsed_date - today).days


                # Debug print to check values
                print(f"Processed row: rawdate: {raw_date} EventDate={row['EventDate']}, DaysTo={row['DaysTo']}")


            print("____Markerframe:",markerframe )

            # Step 2: Assign ProximityRank manually
            # Sort by DaysTo and rank them
            sorted_rows = sorted([r for r in markerframe if isinstance(r["DaysTo"], int)], key=lambda x: x["DaysTo"])
            for rank, row in enumerate(sorted_rows, start=1):
                row["ProximityRank"] = rank

            # Step 3: Create markers
            for row in markerframe:
                if not isinstance(row.get("DaysTo"), int):
                    continue  # Skip rows with invalid or missing EventDate

                num = str(row["DaysTo"])
                tag = row.get("AddressPrefix", "")
                postcode = row.get("Postcode", "")
                mapfile = row.get("url", "#")
                lat = row.get("Lat", float('nan'))
                lng = row.get("Long", float('nan'))

                here = [lat, lng]
                fontsize = str(compute_font_size(-row["DaysTo"]))

                print(f"FONT TEST => DaysTo: {row['DaysTo']}, fontsize: {fontsize}")
                print(f"EventDate: {row['EventDate']}, DaysTo: {row['DaysTo']}, Fontsize: {fontsize}")
                print("______Markers:", tag, type, lat, lng, here)

                tcol = "yellow"
                bcol = "blue"
                fcol = "red"

                try:
                    event_date_obj = datetime.strptime(row['EventDate'], "%d%b%y").date()
                    tooltip_text = f"{tag} ({event_date_obj.strftime('%Y-%m-%d')})"
                except Exception:
                    tooltip_text = tag

                # then in folium.Marker:
                tooltip=tooltip_text,

                self.add_child(folium.Marker(
                    location=here,
                    tooltip= tooltip_text,
                    icon=folium.DivIcon(
                        html='''
                        <a href='{2}'><div style="
                            color: {3};
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="font-size: {5}px;background: {4}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{0}</span>
                            {1}</div></a>
                        '''.format(num, tag, mapfile, tcol, fcol, fontsize),
                    )
                ))
            try:
                with open(MARKER_FILE, "w", encoding="utf-8") as f:
                    json.dump(markerframe, f, indent=2)
                print(f"Successfully saved values {markerframe}")
            except Exception as e:
                print(f"❌ Failed to write to {MARKER_FILE}: {e}")
        return


    def add_nodemaps (self,herenode,type):
        global Treepolys
        global levelcolours
        global Con_Results_data


        print("_________Nodemap:",herenode.value,type, [x.type for x in herenode.children],len(herenode.children), len(herenode.childrenoftype(type)))

        for c in herenode.childrenoftype(type):
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


                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size:{2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)

                        limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+PDbtn+" "+WKbtn
    #                    c.tagno = len(self._children)+1
                        pathref = c.mapfile()
                        mapfile = '/transfer/'+pathref
    #                        self.children.append(c)


                    party = "("+c.party+")"
                    num = str(c.tagno)
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
                            "fillOpacity": 0.4
                        }
                    ).add_to(self)

                    pathref = c.mapfile()
                    mapfile = '/transfer/'+pathref


                    self.add_child(folium.Marker(
                         location=here,
                         icon = folium.DivIcon(
                                html='''
                                <a href='{2}'><div style="
                                    color: {3};
                                    font-size: 10pt;
                                    font-weight: bold;
                                    text-align: center;
                                    padding: 2px;
                                    white-space: nowrap;">
                                    <span style="background: {4}; padding: 1px 2px; border-radius: 5px;
                                    border: 2px solid black;">{0}</span>
                                    {1}</div></a>
                                    '''.format(num,numtag,mapfile,tcol,fcol),

                                   )
                                   )
                                   )


        print("________Layer map polys",herenode.value,herenode.level, len(Featurelayers[gettypeoflevel(herenode.dir,herenode.level+1)]._children))

        return self._children

    def add_nodemarks (self,herenode,type):
        global levelcolours
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

            self.add_child(folium.Marker(
                 location=here,
                 icon = folium.DivIcon(
                        html='''
                        <a href='{2}'><div style="
                            color: {3};
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: {4}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{0}</span>
                            {1}</div></a>
                            '''.format(num,tag,mapfile, tcol, fcol),
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

def visit_node(c_elect,CurrEL, mapfile):
    # Access the first key from the dictionary
    print("___visiting mapfile:", c_elect,CurrEL, mapfile)
    capped_append(CurrEL['mapfiles'], mapfile)
    save_election_data(c_elect, CurrEL)
    print("___visited mapfile:", mapfile)
    return



def reset_nodes():
    global TREK_NODES
    TREK_NODES = {}
    with open(TREKNODE_FILE, 'wb') as f:
        pickle.dump(TREK_NODES, f)
    return

def get_L4area(node,pointposition):
    global _____Treepolys
    global Fullpolys
    if node.level == 4:
        return node.value
    else:
        pfile = Fullpolys[gettypeoflevel(node.dir,node.level+1)]
        polylocated = electorwalks.find_boundary(pfile,pointposition)
        if not polylocated:
            print("____No Level 4 boundary found for electors in this file")
            RaiseException ('No Level 4')
            return None
    return polylocated.NAME

def add_zone_Level4 ( teamsize, unzonedelectors):
    walkcolumn = {
        'polling_district': 'PD',
        'walk': 'Name',
        'ward': 'Area',
        'division': 'Area',
        'constituency': 'Area'
    }

    print("🧹 Cleaning lat/lon data")
    print(f"✅ {len(unzonedelectors)} walk centroids before cleaning")
    unzonedelectors = unzonedelectors[np.isfinite(unzonedelectors['Lat']) & np.isfinite(unzonedelectors['Long'])]
    unzonedelectors = unzonedelectors[(unzonedelectors['Lat'].between(-90, 90)) & (unzonedelectors['Long'].between(-180, 180))]
    print(f"✅ {len(unzonedelectors)} valid walk centroids after cleaning")

    coords = unzonedelectors[['Lat', 'Long']].values
    num_walks = len(coords)
    N = min(teamsize, num_walks)
    print(f"🎯 Clustering into {N} zones (teamsize={teamsize}, walks={num_walks})")

    if N > 1:
        kmeans = KMeans(n_clusters=N, random_state=42)
        unzonedelectors['Zone'] = kmeans.fit_predict(coords)
        unzonedelectors['Zone'] = unzonedelectors['Zone'].map(lambda z: f"ZONE_{z + 1}")
        print("🎨 Assigned zones via KMeans clustering")
        print("___unzonedelectors Zone column preview:\n", unzonedelectors[['WalkName', 'Zone']].dropna().head())
    else:
        unzonedelectors['Zone'] = ['ZONE_0'] * num_walks
        print("⚠️ Only one walk — all assigned to ZONE_0")


    print("🎨 Assigning colours to walk electors")
    walks = unzonedelectors['WalkName'].unique()
    for walk in walks:
        colname = walkcolumn['walk']
        if colname not in unzonedelectors.columns:
            print(f"❌ Column '{colname}' not found in unzonedelectors!")
            print(f"Available columns: {list(unzonedelectors.columns)}")
            continue

        print(f"🔍 Matching walk_node.value '{walk}' to column '{colname}'")
        print(f"📏 Types — column: {unzonedelectors[colname].dtype}, walk_node.value: {type(walk)}")

        mask2 = unzonedelectors[colname] == walk
        walkelectors = unzonedelectors[mask2].copy()

        print(f"👣 walk_node: {walk}, children: {len(walks)}, match electors: {len(walkelectors)}")

        if not walkelectors.empty and len(walkelectors.dropna(how="all")) > 0:
            walkelectors['Zone'] = walk_to_zone.get(walk, "ZONE_0")
            unzonedelectors.loc[mask2, 'Zone'] = walkelectors['Zone']
        else:
            flash("⚠️ No data exists for this election at this location")
            print(f"⚠️ Nodes exist at {walk} but no matching electors for election {c_election} and column '{colname}' = {walk}")
    return unzonedelectors

def background_normalise(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table):
    global TREK_NODES, allelectors, Treepolys, Fullpolys, current_node,formdata, layeritems, progress, markerframe

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

        import logging

        # Setup logger
        logging.basicConfig(
            level=logging.DEBUG,  # or INFO
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        logger = logging.getLogger(__name__)

        # 6. Process metadata for all files in selected stream( does not have to be current election)
        file_index = 0
        mainframe = pd.DataFrame()
        deltaframes = []
        aviframe = pd.DataFrame()
        DQstats = pd.DataFrame()
        stream = "DEMO" # default - drives the filtering of all imported data - entered by user

        progress["percent"] = 1
        progress["status"] = "sourcing"
        progress["message"] = "Sourcing data from instruction files ..."


        print("___Route/normalise")
        total = len(meta_data)
        for idx, (index, data) in enumerate(sorted(meta_data.items(), key=lambda x: int(x[0]))):
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

            print(f"___Selected {stream} election and session node id: ", session_data.get('current_node_id'))
            SelectedElection = get_election_data(stream)  # essential for election specific processing

            order = data.get('order')
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
            # this is the main index
                progress["percent"] = 25
                progress["status"] = "running"
                progress["message"] = "Normalising main file ..."
                results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                DQstats = pd.concat([DQstats, results[1]])
                mainframe = results[0]
                mainframe = pd.DataFrame(mainframe,columns=Outcols)
            elif purpose == 'delta':
            # this is one of many changes that needs to be applied to the main index
                progress["percent"] = 40
                progress["status"] = "running"
                progress["message"] = "Normalising delta files ..."
                if 'ElectorCreatedMonth' in dfx.columns:
                    dfx = dfx[dfx['ElectorCreatedMonth'] > 0] # extract all new registrations
                    results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                    DQstats = pd.concat([DQstats, results[1]])
                    deltaframes.append(results[0])
                else:
                    progress["percent"] = 60
                    progress["status"] = "completing"
                    progress["message"] = "Normalising delta files ..."
                    print("NO NEW REGISTRATIONS IN DELTA FILE", dfx.columns)
            elif purpose == 'avi':
            # this is an addition of columns to the main index
                progress["percent"] = 60
                progress["status"] = "running"
                progress["message"] = "Normalising avi file ..."
                results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                DQstats = pd.concat([DQstats, results[1]])
                aviframe =  results[0]
                aviframe = aviframe[['ENOP','AV']]
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

        fullsum = len(mainframe)+len(deltaframes)+len(aviframe)
        if fixlevel == 3 and len(mainframe) > 0:
            print("__Processed main,delta,avi electors:", len(mainframe), len(deltaframes),len(aviframe), mainframe.columns)
            len1 = len(mainframe)
            if len(deltaframes) > 0:
                progress["percent"] = 75
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised main file ..."

                Outcols = mainframe.columns.to_list()
                for deltaframe in deltaframes:
                    progress["percent"] = 80
                    progress["status"] = "running"
                    progress["message"] = "Pipelining normalised delta files ..."

                    deltaframe = pd.DataFrame(deltaframe,columns=Outcols)
                    print("_____Deltaframe Details:", deltaframe)
                    for index, change in deltaframe.iterrows():
                        print("_____Delta Change Details:", change)
                        mainframe = pd.concat([mainframe, pd.DataFrame(deltaframe)], ignore_index=True)
                    print("__Processed deltaframe electors:", len(deltaframe), mainframe.columns)
            if len(aviframe) > 0:
                progress["percent"] = 85
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised avi file ..."

                print(f"____compare merge length before: {len1} after {len(mainframe)}")
                mainframe = mainframe.merge(aviframe, on='ENOP',how='left', indicator=True )
                mainframe = mainframe.rename(columns= {'AV_y': 'AV'})

                aviframe.to_csv("avitest.csv",sep='\t', encoding='utf-8', index=False)

                print("__Processed aviframe:", len(aviframe), aviframe.columns)


            progress["percent"] = 90
            progress["status"] = "running"
            progress["message"] = "Normalised all source files now clustering ..."

            mainframe = pd.DataFrame(mainframe,columns=Outcols)

            current_election = stream
            CurrentElection = get_election_data(stream)
            restore_from_persist(session_data=session_data)
            current_node = get_current_node(session_data=session_data)

            territory_path = CurrentElection['territory'] # this is the node at which the imported data is to be filtered through
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
                if Territoryboundary.geometry.contains(spot).item():
                    Area = get_L4area(Territory_node,spot)
                    PDelectors['Area'] = Area
                    frames.append(PDelectors)

    # so if there are electors within the area(ward or division) then the Area name needs to be updated
            if len(frames) > 0:
                mainframe = pd.concat(frames)
            mainframe = mainframe.reset_index(drop=True)

            print("____Final Loadable mainframe columns:",len(mainframe),mainframe.columns)
        # now generate walkname labels according to a max zone size (electors) defined for the stream(election)

            label_dict = recursive_kmeans_latlon(mainframe[['Lat', 'Long']], max_cluster_size=int(SelectedElection['walksize']), MAX_DEPTH=15)

# ---- ADD Zones for all Level 4 areas within Level 3 areas in the import

            L4groups = mainframe['Area'].unique()

            for L4group in L4groups:
                maskX = mainframe['Area'] == L4group
                L4electors = mainframe[maskX]  # gets only the L4 electors in your ward/division
                Zonedelectors = add_zone_Level4(CurrentElection['teamsize'],L4electors)
                Zonedelectors.to_csv("zonedelectors.csv",sep='\t', encoding='utf-8', index=False)
                mainframe = Zonedelectors
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

# -------- Import Data into Allelectors

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




# ____XXXXX create and configure the app
app = Flask(__name__, static_url_path='/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/static')

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



db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = "<h1>You really need to login!!</h1>"
login_manager.refresh_view = "index"
login_manager.needs_refresh_message = "<h1>You really need to re-login to access this page</h1>"
login_manager.login_message_category = "info"


Featurelayers = {
"country": ExtendedFeatureGroup(name='Countries', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"nation": ExtendedFeatureGroup(name='Nations', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"county": ExtendedFeatureGroup(name='Counties', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"constituency": ExtendedFeatureGroup(name='Constituencies', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"ward": ExtendedFeatureGroup(name='Wards', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"division": ExtendedFeatureGroup(name='Divisions', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"polling_district": ExtendedFeatureGroup(name='Polling Districts', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"walk": ExtendedFeatureGroup(name='Walks', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"walkleg": ExtendedFeatureGroup(name='Walklegs', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"street": ExtendedFeatureGroup(name='Streets', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"result": ExtendedFeatureGroup(name='Results', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"target": ExtendedFeatureGroup(name='Targets', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"data": ExtendedFeatureGroup(name='Data', overlay=True, control=True, show=True, id='UNITED_KINGDOM'),
"marker": ExtendedFeatureGroup(name='Special Markers', overlay=True, control=True, show=True, id='UNITED_KINGDOM')
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
if os.path.exists(config.workdirectories['workdir'] + "Markers.csv") and os.path.getsize(config.workdirectories['workdir'] + "Markers.csv") > 0:
    markerframe = pd.read_csv(config.workdirectories['workdir'] + "Markers.csv", sep='\t', engine='python')
    with open(MARKER_FILE, "w", encoding="utf-8") as f:
        json.dump(markerframe.to_dict(orient='records'), f, indent=2)
    with open(MARKER_FILE, 'r', encoding="utf-8") as f:
        markerframe = json.load(f)

    print("___Marker columns",list(markerframe[0].keys()))


MapRoot = get_current_node(session=None)
RootPath = MapRoot.dir+"/"+MapRoot.file
Featurelayers['marker'].create_layer("DEMO",MapRoot,'marker')

MapRoot.create_area_map(MapRoot.getselectedlayers(RootPath))
print(f"MAPROOT:{MapRoot.value} ROOTPATH: {RootPath}")

formdata = {}
allelectors = pd.read_excel(GENESYS_FILE)
allelectors.drop(allelectors.index, inplace=True)

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
resources = {}

import os

resources_csv_path = os.path.join(config.workdirectories['workdir'], "Resources.csv")

print(f"🔍 Looking for Resources.csv at: {resources_csv_path}")
print(f"📁 Exists? {os.path.exists(resources_csv_path)}")
print(f"📏 Size: {os.path.getsize(resources_csv_path) if os.path.exists(resources_csv_path) else 'N/A'} bytes")

if  os.path.exists(config.workdirectories['workdir']+"Resources.csv") and os.path.getsize(config.workdirectories['workdir']+"Resources.csv") > 0:
    resourcesdf = pd.read_csv(config.workdirectories['workdir']+"Resources.csv",sep='\t', engine='python')
    resources = resourcesdf.set_index('Code').to_dict(orient='index')
    print("____Resources file read in")
    # need to save to ELECTIONS
    with open(RESOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(resources, f, indent=2)

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

@app.route('/reassign_parent', methods=['POST'])
@login_required
def reassign_parent():
    print(">>> /reassign_parent called")
    current_node = get_current_node(session)

    restore_from_persist(session)
    print("✔ Restored from persist")

    print(f"✔ Current node: {current_node.value if current_node else 'None'}")

    current_election = get_current_election(session)
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
    old_parent_node.parent.create_area_map(old_parent_node.parent.getselectedlayers(mapfile0))

    print(f"🔁 Regenerating map for old parent: {mapfile1}")
    old_parent_node.create_area_map(old_parent_node.getselectedlayers(mapfile1))

    print(f"🔁 Regenerating map for new parent: {mapfile2}")
    new_parent_node.create_area_map(new_parent_node.getselectedlayers(mapfile2))

    # Update session and persist
    session['current_node_id'] = old_parent_node.parent.fid
    persist(new_parent_node.parent)
    CurrentElection = get_election_data(current_election)
    visit_node(current_election,CurrentElection, mapfile0)

    print("✅ Reassignment complete")
    return jsonify({
        'status': 'success',
        'mapfile': f"{mapfile0}",
        'message': f"Node '{subject_name}' reassigned from '{old_parent_name}' to '{new_parent_name}'"
    })



@app.route('/resourcing')
@login_required
def resourcing():
    global current_node
    global allelectors
    global layeritems

    global TREK_NODES
    global resources

    with open(RESOURCE_FILE, 'r', encoding="utf-8") as f:
        resources = json.load(f)


    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)

    selectedResources = {
            k: v for k, v in resources.items()
            if k in CurrentElection['resources']
        }

    Territory_node = current_node.ping_node(current_election,CurrentElection['territory'])
    session['current_node_id'] = Territory_node.fid

    print(f"___Route/resourcing election {current_election} Territory node: {Territory_node.value} Resources: {selectedResources} ")
    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]

    walks = set(areaelectors.WalkName.values)

    # share input and outcome tags
    valid_tags = CurrentElection['tags']
    task_tags = {}
    outcome_tags = {}

    for tag, description in valid_tags.items():
        if tag.startswith('L'):
            task_tags[tag] = description
        elif tag.startswith('M'):
            outcome_tags[tag] = description
    print(f"___Route/resourcing Task Tags {task_tags} Outcome Tags: {outcome_tags} walks:{walks}")

    return render_template('resourcing.html', resources=selectedResources, task_tags=task_tags, walks=walks )

@app.route('/updateResourcing', methods=['POST'])
@login_required
def update_walk():
    global current_node
    global allelectors
    global layeritems

    global TREK_NODES
    global resources

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
    global resources

# campaign plan is only available to westminster elections at level 3 and others at level 4.
# every election should acquire an election node(ping to its mapfile) to which this route should take you
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    current_node = current_node.ping_node(current_election,CurrentElection['territory'])
    session['current_node_id'] = current_node.fid
    mask = (allelectors['Election'] == current_election)

    areaelectors = allelectors[mask]
    print("____Route/kanban/AreaElectors shape:", current_election, current_node.value, allelectors.shape, areaelectors.shape, CurrentElection['territory'] )
    print("Sample of areaelectors:", areaelectors.head())
    print("Sample raw Tags values:")
    print(areaelectors['Tags'].dropna().head(10).tolist())
    # Example DataFrame
    df = areaelectors
    gotv = float(CurrentElection['GOTV'])
    turnout = 0.3  # assuming this is between 0–1

    df['VI_Party'] = df['VI'].apply(lambda vi: 1 if vi == CurrentElection['yourparty'] else 0)
    df['VI_Canvassed'] = df['VI'].apply(lambda vi: 1 if isinstance(vi, str) else 0)
    df['VI_L1Done'] = df['Tags'].apply(lambda tags: 1 if isinstance(tags, str) and "L1" in tags.split() else 0)
    df['VI_Voted'] = df['Tags'].apply(lambda tags: 1 if isinstance(tags, str) and "M1" in tags.split() else 0)
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
    formdata['tabledetails'] = current_node.value+" details"
    items = current_node.childrenoftype('walk')
    layeritems = get_layer_table(items,formdata['tabledetails'] )
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
    Territory_node = current_node.ping_node(current_election,Current_Election['territory'])
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
    mask = (allelectors['Election'] == current_election)
    areaelectors = allelectors[mask]
    valid_tags = CurrentElection['tags']
    leaflet_tags = {}
    marked_tags = {}

    for tag, description in valid_tags.items():
        if tag.startswith('L'):
            leaflet_tags[tag] = description
        elif tag.startswith('M'):
            marked_tags[tag] = description
    print("____Tags v l m:",valid_tags,leaflet_tags, marked_tags)
    return render_template(
        'telling.html',
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

    for tag, description in valid_tags.items():
        if tag.startswith('L'):
            leaflet_tags[tag] = description
        elif tag.startswith('M'):
            marked_tags[tag] = description

    return render_template(
        'leafletting.html',
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
    tags = CurrentElection['tags']

    # tags is assumed to be a dict: { "L1": "FirstLeaflet", ... }
    tag_list = [{"code": code, "label": label} for code, label in tags.items()]

    return jsonify(tags=tag_list)


@app.route('/add_tag', methods=['POST'])
@login_required
def add_tag():
    global CurrentElection
    restore_from_persist(session=session)
    current_node = get_current_node(session=session)
    current_election = get_current_election(session=session)

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
    election = request.json.get('election')
    CurrentElection = get_election_data(election)
    current_node = get_current_node(session)
    delete_path = CurrentElection['territory']
    delete_node = current_node.ping_node(election,delete_path)
    if not election:
        return jsonify({'status': 'error', 'message': 'Missing election parameter'}), 400

    # Example: Remove all electors for the given election
    global allelectors
    if 'Election' in allelectors.columns:
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

    return jsonify({'status': 'success', 'election': election})



@app.route('/reset_Elections', methods=['POST'])
@login_required
def reset_Elections():
    global streamrag
    global allelectors
    global markerframe
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
    global resources
    global markerframe
    resources = OPTIONS['resources']
    # Define the absolute path to the 'static/data' directory
    elections_dir = os.path.join(config.workdirectories['workdir'], 'static', 'data')
    report_data = []
    markerframe = []


    current_node = get_current_node(session)
    current_election = get_current_election(session)
    reportfile = "UNITED_KINGDOM/ENGLAND/SURREY/SURREY-MAP.html"
    current_node = current_node.ping_node(current_election,reportfile)


    # Check if the elections directory exists
    if not os.path.exists(elections_dir):
        return f"Error: The directory {elections_dir} does not exist!"

    # Example mapping for party abbreviations to full names (update as needed)

    # Process each election file in the directory
    nodemolist = os.listdir(elections_dir)
    for filename in nodemolist:
        if filename.startswith("Elections-") and filename.endswith(".json") and filename.find("DEMO") < 0:
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

                territory_path = data.get("territory", "")
                if territory_path:
                    # Extract only the filename (no directories)
                    territory_filename = os.path.basename(territory_path)

                    # Remove suffixes from the filename
                    for suffix in ['-MAP.html', '-PDS.html', '-WALKS.html','-WARDS.html','-DIVS.html', '-DEMO.html']:
                        if territory_filename.endswith(suffix):
                            territory_filename = territory_filename[:-len(suffix)]

                # In your route handler
                election_node = current_node.ping_node("DEMO",territory_path)
                print(f"____election territory path:{territory_path} elect:{election_node.value}")
                # Get full party name from the abbreviation
                selected_party_key = election_node.party
                incumbent_party = OPTIONS['yourparty'].get(selected_party_key, 'U')
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
                markerframe.append({
                        'EventDate': election_date,
                        'AddressPrefix': election_name +":"+ territory_filename,
                        'Address1': candidate_name,
                        'Address2': campaign_mgr_name,
                        'Postcode': "",
                        'url': "",
                        'Lat': election_node.centroid[0],
                        'Long': election_node.centroid[1]
                        })
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

    with open(MARKER_FILE, "w", encoding="utf-8") as f:
        json.dump(markerframe, f, indent=2)


    Featurelayers['marker'].create_layer(current_election,current_node,'marker')
    selectedlayers = current_node.getselectedlayers(reportfile)
    current_node.create_area_map(selectedlayers)
    reportdate = datetime.strptime(str(date.today()), "%Y-%m-%d").strftime('%d/%m/%Y')

    return render_template("election_report.html", reportdate=reportdate, mapfile=reportfile, report_data=report_data)


@app.route("/set-election", methods=["POST"])
@login_required
def set_election():
    global CurrentElection
    global OPTIONS
    global constants
# so change current_election and return current election constants and options
    data = request.get_json()
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    session['current_election'] = data.get("election")
    print(f"____switching from election: {current_election} to {session['current_election']}")
    current_election = data.get("election")
    CurrentElection = get_election_data(current_election)
    CurrentElection['previousParty'] = current_node.party
    print(f"____CurrentElection: at {current_node.value} for {current_election} path:{CurrentElection['territory']} details:{CurrentElection} " )
    if CurrentElection:
        mapfile = CurrentElection['territory']
        current_node = current_node.ping_node(current_election,mapfile)
        visit_node(current_election,CurrentElection,mapfile)
        session['current_node_id'] = current_node.fid
        print(f"____Route/set_election/success: at {current_node.value} for {current_election} constants:{CurrentElection} path:{CurrentElection['territory']}" )
        return jsonify({
            'constants': CurrentElection,
            'options': OPTIONS,
            'current_election': current_election
        })
    print("____Route/set_election/failure" , current_election, CurrentElection)
    return jsonify(success=False, error="Election not found", current_election=current_election)

# GET /current-election
@app.route('/current-election', methods=['GET'])
@login_required
def retrieve_current_election():
    current_election = get_current_election()
    calendar_plan = CurrentElection['calendar_plan']
    return jsonify(CurrentElection)

# POST /current-election
@app.route('/current-election', methods=['POST'])
@login_required
def update_current_election():
    current_node = get_current_node(session=session)
    current_election = get_current_election(session=session)
    try:
        data = request.get_json()
        # You could add validation here if needed
        CurrentElection['calendar_plan'] = data
        save_election_data(current_election,CurrentElection)
        return jsonify({"success": True})
    except Exception as e:
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
    data = request.get_json()
    name = data.get("name")
    value = data.get("value")
    current_election = data.get("election")

    print("____Back End1 election constants update:",current_election,":",name,"-",value)

    CurrentElection = get_election_data(current_election)

    if name in CurrentElection:
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

    CurrentElection['territory'] = current_node.mapfile()

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

    CurrentElection['territory'] = CurrentElection['mapfiles'][-1]

    new_path = CurrentElection['territory']

    current_node = current_node.ping_node(current_election, new_path)
    mapfile = current_node.mapfile()

    save_election_data(current_election,CurrentElection)
    print("______election: {current_election} Updated-territory:",mapfile)

    return jsonify(success=True, constants=CurrentElection)


@app.route("/", methods=['POST', 'GET'])
def index():
    global TREK_NODES
    global streamrag


    ELECTIONS = get_election_names()
    if 'username' in session:
        flash("__________Session Alive:"+ session['username'])
        print("__________Session Alive:"+ session['username'])
        formdata = {}
        streamrag = getstreamrag()
        restore_from_persist(session=session)
        current_node = get_current_node(session)
        current_election = get_current_election(session)

        mapfile = current_node.mapfile()
#        redirect(url_for('captains'))

        return render_template("Dash0.html",  formdata=formdata,current_election=current_election, ELECTIONS=ELECTIONS, group=allelectors ,streamrag=streamrag ,mapfile=mapfile)

    return render_template("index.html")


@app.route('/validate_tags', methods=['POST'])
@login_required
def validate_tags():

    global CurrentElection
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)

    # Ensure the valid tags list is a list of strings
    tags_data = CurrentElection['tags']
    print("____Standard Tag options for election",tags_data)

    valid_tags = set(tags_data)  # E.g. {'M1', 'M2', 'L1', 'L3'}
    print("____Standard Tag options as set",valid_tags)

    # Parse input from frontend
    data = request.get_json()
    current_tags = data.get('tags', '')  # e.g. "M1 L1 X99"
    original = data.get('original', '')
    print("_____elector data and original",current_tags,original)

    # Normalize and split input tags
    tag_list = current_tags.strip().split()  # ['M1', 'L1', 'X99']
    print("____New Tag settings for elector",tag_list, valid_tags)

    # Check for any invalid tags
    invalid_tags = [tag for tag in tag_list if tag not in valid_tags]

    if invalid_tags:
        return jsonify(valid=False, invalid_tags=invalid_tags, original=original)
    else:
        return jsonify(valid=True)


#login
@app.route('/login', methods=['POST', 'GET'])
def login():
    global TREK_NODES
    global streamrag
    global environment
    global layeritems
    global CurrentElection

    current_election = session.get('current_election')
    if current_election:
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
        return redirect(url_for('get_location'))  # Don't go to Dash0 yet
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
            body {
                background: #00bed6;
                color: white;
                font-family: sans-serif;
                text-align: center;
            height: 100%;
            margin: 0;
            padding: 0;}

            .road {
                position: relative;
                width: 100%;
                height: 100vh;
                margin: 0 auto;
                background: #00bed6;
                overflow: hidden;
            }

            .footprint {
                position: absolute;
                width: 40px;
                opacity: 0;
                animation: stepFade 4s ease-in-out infinite;
            }

            .left {
                left: 45%;
                transform: rotate(-12deg);
            }

            .right {
                left: 52%;
                transform: rotate(12deg);
            }

            @keyframes stepFade {
            0%   { opacity: 1; }
            10%  { opacity: 1; }
            70%  { opacity: 0; }
            100% { opacity: 0; }
            }
        </style>
    </head>
    <body>
        <h2>elecTrek is finding democracy in your area ...</h2>
        <div class="road">
    {% for i in range(8) %}
    {% set is_left = i % 2 == 0 %}
    <img src="{{ url_for('static', filename='left_foot.svg') if is_left else url_for('static', filename='right_foot.svg') }}"
         class="footprint {{ 'left' if is_left else 'right' }}"
         style="
            top: {{ 800 - i * 100 }}px;
            animation-delay: {{ i * 0.7 }}s;
         ">
         {% endfor %}
        </div>

<script>
navigator.geolocation.getCurrentPosition(
    function(pos) {
        console.log("Location received");
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        window.location.href = `/firstpage?lat=${lat}&lon=${lon}`;
    },
    function(err) {
        console.error("Geolocation error:", err);
        alert("Location access denied.");
        window.location.href = "/firstpage";
    }
);
</script>
    </body>
    </html>
    """)

@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():

    current_node = TREK_NODES.get(session.get('current_node_id'))

    flash("🔓 Logging out user:"+ current_user.get_id())
    print("🔓 Logging out user:", current_user.get_id())

    # Always log out the user
    logout_user()

    # Clear the entire session to remove 'username', 'user_id', etc.
    session.clear()

    return redirect(url_for('index'))

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
        print(f"_______ROUTE/dashboard: {session['username']} is already logged in at {session.get('current_node_id')}")
        formdata = {}
        current_node = TREK_NODES.get(session.get('current_node_id'))
        if not current_node:
            current_node = TREK_NODES.get(next(iter(TREK_NODES), None)).findnodeat_Level(0)
        streamrag = getstreamrag()
        print ("allelectors len after streamrag: ",len(allelectors))
        path = CurrentElection['territory']
        previous_node = current_node
        print ("____Dashboard CurrentElection: ",path, previous_node.value)
        # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        current_node = previous_node.ping_node(current_election,path)
        print ("allelectors len after ping: ",len(allelectors))

        mapfile = current_node.mapfile()
        print ("___Dashboard persisted filename: ",mapfile)
        persist(current_node)

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
    session['current_node_id'] = current_node.fid
    print("____Route/downbut:",previous_node.value,current_node.value, path)
    atype = gettypeoflevel(path,current_node.level+1)
    FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html",'walk' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
    current_node.file = subending(current_node.file,FACEENDING[atype]) # face is driven by intention type
    print(f" target type: {atype} current {current_node.value} type: {current_node.type} FACEFILE:{FACEENDING[current_node.type]}")
# the map under the selected node map needs to be configured
# the selected  boundary options need to be added to the layer
    Featurelayers[atype].create_layer(current_election,current_node,atype)
    selectedlayers = current_node.getselectedlayers(path)
    current_node.create_area_map(selectedlayers)
    print(f"_________layeritems for {current_node.value} of type {atype} are {current_node.childrenoftype(atype)} for lev {current_node.level}")

    mapfile = current_node.mapfile()

    visit_node(current_election,CurrentElection,mapfile)

    persist(current_node)

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

    formdata = {}
# transfering to another any other node with siblings listed below
    previous_node = current_node
# use ping to populate the destination node with which to repaint the screen node map and markers
    current_node = previous_node.ping_node(current_election,path)

    atype = gettypeoflevel(path, current_node.level+1)

    mapfile = current_node.mapfile()
    CurrentElection = get_election_data(current_election)
    visit_node(current_election,CurrentElection, mapfile)
    print("____Route/transfer:",previous_node.value,current_node.value,current_node.type, path)
    if not os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
        session['current_node_id'] = current_node.fid
        print("___Typemaker:",atype, TypeMaker[atype] )
        return redirect(url_for(TypeMaker[atype],path=mapfile))
    else:
        session['current_node_id'] = current_node.fid
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

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)

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
            shapelayer = Featurelayers['polling_district'].create_layer(current_election,current_node, 'polling_district')
            if len(shapelayer._children) == 0:
                current_node.file = subending(current_node.file,"-MAP.html")
                mapfile = current_node.mapfile()
            else:
                print("_______just before create_area_map call:",current_node.level, len(Featurelayers['polling_district']._children), mapfile)
                current_node.create_area_map(current_node.getselectedlayers(mapfile))
                flash("________PDs added:  "+str(len(shapelayer._children)))
                print("________After map created PDs added  :  ",current_node.level, len(shapelayer._children))

#    face_file = subending(current_node.file,"-MAP.html")
#    mapfile = current_node.dir+"/"+face_file
# if this route is from a redirection rather than a service call , then create file if doesnt exist

    if not os.path.exists(PDpathfile):
        print ("_________New PD mapfile/",current_node.value, mapfile)
        Featurelayers[previous_node.type].create_layer(current_election,current_node,previous_node.type) #from upnode children type of prev node
    #        current_node.file = face_file
        current_node.create_area_map(current_node.getselectedlayers(mapfile))

    print("________PD markers After importVI  :  "+str(len(Featurelayers['polling_district']._children)))

    session['current_node_id'] = current_node.fid

    persist(current_node)
    visit_node(current_election,CurrentElection,mapfile)
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
# so this is the button which creates the nodes and map of equal sized walks for the troops
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    print (f"_________ROUTE/downWKbut1 CE {current_election}", current_node.value, path)

    previous_node = current_node
    # use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(current_election,path)
    session['current_node_id'] = current_node.fid
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
            shapelayer = Featurelayers['walk'].create_layer(current_election,current_node, 'walk')
            if len(shapelayer._children) == 0:
                current_node.file = subending(current_node.file,"-MAP.html")
                mapfile = current_node.mapfile()
            else:
                print("_______just before Walk create_area_map call:",current_node.level, len(Featurelayers['walk']._children))
                current_node.create_area_map(current_node.getselectedlayers(path))
                flash("________Walks added:  "+str(len(shapelayer._children)))
                print("________After map created Walks added  :  ",current_node.level, len(shapelayer._children))

    #            allelectors = getblock(allelectors,'Area',current_node.value)

    if not os.path.exists(walkpathfile):
#        simple transfer from another node -
        print ("_________New WK mapfile/",current_node.value, mapfile)
        Featurelayers[previous_node.type].create_layer(current_election,current_node,'walk') #from upnode children type of prev node
    #        current_node.file = face_file
        current_node.create_area_map(current_node.getselectedlayers(mapfile))

    #    moredata = importVI(allelectors.copy())
    #    if len(moredata) > 0:
    #        allelectors = moredata

        print("________ Walk markers After importVI  :  "+str(len(Featurelayers['walk']._children)))
        print("_______writing to file:", mapfile)

    persist(current_node)
    visit_node(current_election,CurrentElection,mapfile)

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
    current_election = get_current_election(session)
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
            print(f"📥 Incoming request to update street: {path} (from all {len(allelectors)} in terr {CurrentElection['territory']}) with source data {len(streetelectors)} ")

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

    session['current_node_id'] = current_node.fid
    sheetfile = current_node.create_streetsheet(current_election,streetelectors)
    mapfile = current_node.dir+"/"+sheetfile
    visit_node(current_election,CurrentElection,mapfile)
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

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)

# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers


    current_node = current_node.ping_node(current_election,path)
    session['current_node_id'] = current_node.fid
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

        PD_node.create_area_map(PD_node.getselectedlayers(path))
    mapfile = PD_node.mapfile()

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers['street']._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers['street']._children)))
    visit_node(current_election,CurrentElection,mapfile)
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
    current_election = get_current_election(session)
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

        if len(areaelectors) == 0 or len(Featurelayers['street']._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
            if os.path.exists(mapfile):
                os.remove(mapfile)
        else:
            flash("________streets added  :  "+str(Featurelayers['street']._children))
            print("________streets added  :  "+str(len(Featurelayers['street']._children)))

        streetnodelist = PD_node.childrenoftype('street')
        for street_node in streetnodelist:
            mask = PDelectors['StreetName'] == street_node.value
            streetelectors = PDelectors[mask]
            street_node.create_streetsheet(current_election,streetelectors)

        PD_node.create_area_map(PD_node.getselectedlayers(path))
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
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)


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
        walklegnodelist = walk_node.childrenoftype('walkleg')
        print ("________Walklegs",walk_node.value,len(walklegnodelist))
# for each walkleg node(partial street), add a walkleg node marker to the walk_node parent layer (ie PD_node.level+1)
        for walkleg_node in walklegnodelist:
            mask = walkelectors['StreetName'] == walkleg_node.value
            streetelectors = walkelectors[mask]
            walkleg_node.create_streetsheet(current_election,streetelectors)

        walk_node.create_area_map(walk_node.getselectedlayers(path))

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
    global resources
    global markerframe
    global stream_table
    global layertable
    global VCO
    global VNORM

    def get_resources_table():
        return pd.DataFrame(resources)

    def get_markers_table():
        print(f"Markerframe type: {type(markerframe)}")
        print(f"Markerframe content: {markerframe}")
        print(f"pd.DataFrame: {pd.DataFrame}, type: {type(pd.DataFrame)}")
        if markerframe is None or not markerframe:
            raise ValueError("markerframe is not defined")

        # Check if markerframe is a dictionary or a list
        if isinstance(markerframe, dict):
            return pd.DataFrame.from_dict(markerframe, orient='index')

        elif isinstance(markerframe, list):
            # Ensure each item in the list is a dictionary (if it's a list of dicts)
            if all(isinstance(item, dict) for item in markerframe):
                return pd.DataFrame(markerframe)
            else:
                raise ValueError("Each item in markerframe list must be a dictionary.")

        else:
            raise TypeError("markerframe must be either a dictionary or a list.")

    def get_stream_table():
        print(f"Markerframe type: {type(stream_table)}")
        print(f"Markerframe content: {stream_table}")
        if isinstance(stream_table, dict):
            return pd.DataFrame.from_dict(stream_table, orient='index')
        else:
            return pd.DataFrame(stream_table)

    current_node = get_current_node(session)
    current_election = get_current_election(session)

    mask = allelectors['Election'] == current_election
    areaelectors = allelectors[mask]

    # Table mapping
    table_map = {
        "resources" : get_resources_table,
        "markerframe" : get_markers_table,
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
            tabtype = gettypeoflevel(path,current_node.level+1)
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
    global TREK_NODES
    global layeritems
    global formdata

    global markerframe

    current_node = get_current_node(session=session)
    current_election = get_current_election(session=session)
    print(f"____Route/displayareas for {current_node.value} in election {current_election} ")
    if current_election == "DEMO":
        if len(markerframe) > 0:
            formdata['tabledetails'] = "Click for details of uploaded markers, markers and events"
            layeritems = get_layer_table(pd.DataFrame(markerframe) ,formdata['tabledetails'])
            print(f" Number of displayed markframe items - {len(markerframe)} ")
        else:
            formdata['tabledetails'] = "No data to display - please upload"
            layeritems = get_layer_table(pd.DataFrame(markerframe),formdata['tabledetails'])
    else:
        path = current_node.dir+"/"+current_node.file
        ctype = gettypeoflevel(path, current_node.level+1)

        formdata['tabledetails'] = current_node.value +getchildtype(current_node.type)+"s"
        tablenodes = current_node.childrenoftype(ctype)
        if len(tablenodes) == 0:
            if current_node.level > 0:
                ctype = gettypeoflevel(path, current_node.level)
                tablenodes = current_node.parent.childrenoftype(ctype)
            else:
                return jsonify([[], [], "No data"])
        layeritems = get_layer_table(tablenodes ,formdata['tabledetails'])
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

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)
    CurrentElection = get_election_data(current_election)
    flash('_______ROUTE/upbut',path)
    print('_______ROUTE/upbut',path, current_node.value)
    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
# for PDs the up button should take you to the -PDS file, for walks the -WALKS file
#
    previous_node = current_node
    current_node = previous_node.ping_node(current_election,path)
    session['current_node_id'] = current_node.fid

    if current_node.level < 3:
        restore_fullpolys(current_node.type)


# the previous node's type determines the 'face' of the destination node
    atype = gettypeoflevel(path,current_node.level+1) # destination type
    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""

    FACEENDING = {'street' : "-PRINT.html",'walkleg' : "-PRINT.html",'walk' : "-PRINT.html", 'polling_district' : "-PDS.html", 'walk' :"-WALKS.html",'ward' : "-WARDS.html", 'division' :"-DIVS.html", 'constituency' :"-MAP.html", 'county' : "-MAP.html", 'nation' : "-MAP.html", 'country' : "-MAP.html" }
    face_file = subending(current_node.file,FACEENDING[previous_node.type])
    print(f" previous: {previous_node.value} type: {previous_node.type} current {current_node.value} type: {current_node.type} FACEFILE:{FACEENDING[previous_node.type]}")

    mapfile = current_node.dir+"/"+face_file
    if not os.path.exists(os.path.join(config.workdirectories['workdir'],face_file)):
        Featurelayers[previous_node.type].create_layer(current_election,current_node,previous_node.type) #from upnode children type of prev node
        current_node.file = face_file
        current_node.create_area_map(current_node.getselectedlayers(mapfile))

    print("________chosen node url",mapfile)
    visit_node(current_election,CurrentElection,mapfile)
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
    session['current_node_id'] = current_node.fid
    if path.find(" "):
        mapfile = current_node.mapfile()
    else:
        mapfile = path

    if os.path.exists(os.path.join(config.workdirectories['workdir'],mapfile)):
        flash(f"Using existing file: {mapfile}", "info")
        print(f"Using existing file: {mapfile} and CurrentElection: {CurrentElection}")
        visit_node(current_election,CurrentElection,mapfile)
        return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)
    else:
        flash(f"Creating new mapfile:{mapfile}", "info")
        print(f"Creating new mapfile:{mapfile}")
        current_node.create_area_map(current_node.getselectedlayers(mapfile))
        visit_node(current_election,CurrentElection,mapfile)
        return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/showmore/<path:path>', methods=['GET','POST'])
@login_required
def showmore(path):
    global TREK_NODES
    global CurrentElection

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)

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
    for key, value in progress.items():
        print(f"Progress2-{key} => {value}")
    return jsonify({
        'election' : progress['election'],
        'percent': progress['percent'],
        'status': progress['status'],
        'message': progress['message'],
        'dqstats_html': progress['dqstats_html']
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


    global environment
    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)

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

        return render_template('Dash0.html',  formdata=formdata, current_election=current_election, group=allelectors , streamrag=streamrag ,mapfile=mapfile)
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
    polylocated = electorwalks.find_boundary(pfile,here)
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
    global markerframe
    global CurrentElection

    restore_from_persist(session=session)
    current_node = get_current_node(session)
    current_election = get_current_election(session)

    print("🔍 Accessed /firstpage")
    print("🧪 current_user.is_authenticated:", current_user.is_authenticated)
    print("🧪 current_user:", current_user)
    print("🧪 current_election:", current_election)
    print("🧪 session keys:", list(session.keys()))
    print("🧪 full session content:", dict(session))
    print("🧪 full currentelection content:", CurrentElection)

    lat = request.args.get('lat')
    lon = request.args.get('lon')

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
        sourcepath = sourcepath+"/"+step+"-MAP.html"
        [step,Treepolys['division'],Fullpolys['division']] = intersectingArea(config.workdirectories['bounddir']+"/"+"County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson",'CED23NM',here,Treepolys['constituency'], config.workdirectories['bounddir']+"/"+"Division_Boundaries.geojson")

        with open(TREEPOLY_FILE, 'wb') as f:
            pickle.dump(Treepolys, f)
        with open(FULLPOLY_FILE, 'wb') as f:
            pickle.dump(Fullpolys, f)
        print(f"🧪 current election 0 {current_election} - current_node:{current_node.value}")

        session['next'] = sourcepath
# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        current_node = MapRoot.ping_node(current_election,sourcepath)
        session['current_node_id'] = current_node.fid
        print(f"🧪 current election 1 {current_election} - current_node:{current_node.value}")

        print("____Firstpage Sourcepath",sourcepath, current_node.value)

    if current_user.is_authenticated:
        formdata = {}
        formdata['country'] = "UNITED_KINGDOM"
        flash('_______ROUTE/firstpage')
        print('_______ROUTE/firstpage at :',current_node.value )
        formdata['importfile'] = "SCC-CandidateSelection.xlsx"
        if len(request.form) > 0:
            formdata['importfile'] = request.files['importfile'].filename
#        df1 = pd.read_excel(config.workdirectories['workdir']+"/"+formdata['importfile'])
#        formdata['tabledetails'] = "Candidates File "+formdata['importfile']+" Details"
#        layeritems =[list(df1.columns.values),df1, formdata['tabledetails']]

        atype = gettypeoflevel(sourcepath,current_node.level+1)
    # the map under the selected node map needs to be configured
    # the selected  boundary options need to be added to the layer
        Featurelayers[atype].create_layer(current_election,current_node,atype)
        streamrag = getstreamrag()
        print(f"🧪 current election 2 {current_election} - current_node:{current_node.value} - atype:{atype} - name {Featurelayers[atype].name} - id {Featurelayers[atype].id}")
        flayers = current_node.getselectedlayers(sourcepath)
        current_node.create_area_map(flayers)
        print("______First selected node",atype,len(current_node.children),current_node.value, current_node.level,current_node.file)

        if CurrentElection['territory']:
            mapfile = CurrentElection['territory']
        else:
            mapfile = current_node.dir+"/"+current_node.file
            capped_append(CurrentElection['mapfiles'],mapfile)

#        CurrentElection['mapfiles'][-1] = mapfile

        ELECTIONS = get_election_names()

        session['current_node_id'] = current_node.fid
        persist(current_node)

        print(f"🧪 current election 3 {current_election} - current_node mapfile:{mapfile}")

        return render_template("Dash0.html", VID_json=VID_json, current_election=current_election, ELECTIONS=ELECTIONS, formdata=formdata,mapfile=mapfile)
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
                return render_template('Dash0.html',  formdata=formdata,current_election=CurrentElection[session.get("current_election")], ELECTIONS=ELECTIONS, group=allelectors , streamrag=streamrag ,mapfile=mapfile)
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

    target_election = session_data.get('current_election')
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

if __name__ in '__main__':
    with app.app_context():
        print("__________Starting up", os.getcwd())
        db.create_all()
#        app.run(host='0.0.0.0', port=5000)
        app.run(debug=True, use_reloader=True)



# 'method' is a function that is present in a file called 'file.py'
