from canvasscards import prodcards, getblock, find_boundary
from walks import prodwalks
#import electwalks, locmappath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
import config
from normalised import normz
#import normz
import folium
from json import JSONEncoder
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
from folium import FeatureGroup
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPoint
from shapely import crosses, contains, union, envelope, intersection
import numpy as np
import statistics
from sklearn.cluster import KMeans
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
from datetime import datetime, timedelta
import geocoder
from matplotlib.colors import to_hex, to_rgb
import colorsys
from collections import defaultdict
import requests



sys.path
sys.path.append('/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Electtrek.py')
print(sys.path)

levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

levels = ['country','nation','county','constituency','ward/division','polling_district/walk','street/walkleg','elector']


# want to equate levels with certain types, eg 4 is ward and div
# want to look up the level of a type ,and the types in a level


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

    route = subending(path, "").replace(".html","")
    parts = route.split("/")
    last = parts.pop() #eg KA-SMITH_STREET or BAGSHOT-MAP
    if last.find("-") > 0:
        parts.append(last.split("-").pop()) #eg SMITH_STREET
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
    global levels
    moretype = ""
    dest = path
    if path.find(" ") > -1:
        dest_path = path.split(" ")
        moretype = dest_path.pop() # take off any trailing parameters
        dest = dest_path[0]
    deststeps = list(stepify(dest)) # lowest left - UK right

    type = levels[level]
    if type == 'ward/division' and path.find("/WARDS") >= 0:
        type = 'ward'
    elif type == 'ward/division' and path.find("/DIVS") >= 0:
        type = 'division'
    elif type == 'ward/division':
        type = 'ward'
    elif type == 'polling_district/walk'and path.find("/PDS") >= 0:
        type = 'polling_district'
    elif type == 'polling_district/walk'and path.find("/WALKS") >= 0:
        type = 'walk'
    elif type == 'street/walkleg'and path.find("/PDS") >= 0:
        type = 'street'
    elif type == 'street/walkleg'and path.find("/WALKS") >= 0:
        type = 'walkleg'
    elif type == 'street/walkleg':
        type = 'street'
    elif type == 'polling_district/walk'and path.find("-MAP.html") >= 0:
        type = 'polling_district'
    elif type == 'polling_district/walk'and path.find("-PDS.html") >= 0:
        type = 'polling_district'
    elif type == 'polling_district/walk'and path.find("-WALKS.html") >= 0:
        type = 'walk'
    elif type == 'polling_district/walk':
        type = 'polling_district'
    print(f"____check len steps {deststeps} vs level {level}+1 to override {moretype}")

    if len(deststeps) >= level and moretype != "":
        type = moretype # this is the type override syntax if node level+1 >= len steps
    return type


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url,target))
    return test_url.scheme in ('http', 'https') and \
            ref_url.netloc == test_url.netloc

def getlayeritems(nodelist,title):
    global ElectionSettings

    dfy = pd.DataFrame()
    if isinstance(nodelist, pd.DataFrame):
        dfy = nodelist
        title = "Load data from Dataframe rows: "+str(len(dfy))
    elif isinstance(nodelist, list) and nodelist != []:
        dfy = pd.DataFrame()
        i = 0
        for x in nodelist:
            dfy.loc[i,'No']= x.tagno
            options = x.VI
            for party in options:
                dfy.loc[i,party] = x.VI[party]

            dfy.loc[i,x.type]=  f'<a href="#" onclick="changeIframeSrc(&#39;/transfer/{x.dir}/{x.file}&#39;); return false;">{x.value}</a>'
            dfy.loc[i,x.parent.type] =  f'<a href="#" onclick="changeIframeSrc(&#39;/transfer/{x.parent.dir}/{x.parent.file}&#39;); return false;">{x.parent.value}</a>'
            dfy.loc[i,'elect'] = x.electorate
            dfy.loc[i,'hous'] = x.houses
            dfy.loc[i,'turn'] = '%.2f'%(x.turnout)
            dfy.loc[i,'gotv'] = '%.2f'%(float(ElectionSettings['GOTV']))
            dfy.loc[i,'toget'] = int(((x.electorate*x.turnout)/2+1)/float(ElectionSettings['GOTV']))-int(x.VI[ElectionSettings['yourparty']])
            i = i + 1

    print("___existing getlayeritems",list(dfy.columns.values), dfy, title)
    return [list(dfy.columns.values),dfy, title]

def subending(filename, ending):
  stem = filename.replace("-WDATA", "@@@").replace("-SDATA", "@@@").replace("-MAP", "@@@").replace("-PRINT", "@@@").replace("-WALKS", "@@@").replace("-PDS", "@@@").replace("-DIVS", "@@@").replace("-WARDS", "@@@")
  return stem.replace("@@@", ending)


Historynodelist = []
Historytitle = ""


ElectionOptions = {"W":"Westminster","C":"County","B":"Borough","P":"Parish","U":"Unitary"}
VID = {"R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"Independent","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}
VNORM = {"O":"O","REFORM" : "R" , "REFORM DERBY" : "R" ,"REFORM UK" : "R" ,"REF" : "R", "RUK" : "R","R" :"R","CONSERVATIVE AND UNIONIST" : "C","CONSERVATIVE" : "C", "CON" : "C", "C":"C","LABOUR PARTY" : "S","LABOUR" : "S", "LAB" :"S", "L" : "L", "LIBERAL DEMOCRATS" :"LD" ,"LIBDEM" :"LD" , "LIB" :"LD","LD" :"LD", "GREEN PARTY" : "G" ,"GREEN" : "G" ,"G":"G", "INDEPENDENT" : "I", "IND" : "I" ,"I" : "I" ,"PLAID CYMRU" : "PC" ,"PC" : "PC" ,"SNP": "SNP" ,"MAYBE" : "Z" ,"WONT VOTE" : "W" ,"WON'T SAY" : "X" , "SDLP" : "S", "SINN FEIN" : "SF", "SPK": "N", "TUV" : "C", "UUP" : "C", "DUP" : "C","APNI" : "N", "INET": "I", "NIP": "I","PBPA": "I","WPB": "S","OTHER" : "O"}
VCO = {"O" : "brown","R" : "cyan","C" : "blue","S" : "red","LD" :"yellow","G" :"limegreen","I" :"indigo","PC" : "darkred","SD" : "orange","Z" : "lightgray","W" :  "white", "X" :  "darkgray"}
onoff = {"on" : 1, 'off': 0}

SelectedTags = {"M1":"FirstLeaflet","M2":"SecondLeaflet"}

OPTIONS = {
    "elections": ElectionOptions,
    "yourparty": VID,
    "Tags": SelectedTags,
    "autofix" : onoff
    # Add more mappings here if needed
}

data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))
VID_json = json.dumps(VID)  # Convert to JSON string

# This prints a script tag you can paste into your HTML
print(f'<script>const VID_json = {VID_json};</script>')

class TreeNode:
    def __init__(self, value, fid, roid, lev):
        global levelcolours
        self.value = normalname(str(value))
        self.children = []
        self.type = 'country'
        self.parent = None
        self.fid = fid
        self.level = lev
        self.file = self.value+"-MAP.html"
        self.dir = self.value
        self.davail = True
        self.col = levelcolours["C"+str(self.level+4)]
        self.tagno = 1
        self.centroid = Point(roid.x,roid.y)
        self.bbox = []
        self.map = folium.Map(location=[roid.y, roid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(lev,5)+0.75)*2)))
        self.VR = VIC.copy()
        self.VI = VIC.copy()
        self.turnout = 0
        self.electorate = 0
        self.houses = 0
        self.target = 1

    def upto(self,deststeps):
        node = self
        while node.value not in deststeps:
            if node.level == 0:
                break
            else:
                node = node.parent
        return node

    def ping_node(self,dest_path):
        global Treepolys
        global Fullpolys
        global levels
        global current_node
# used to grab the node in the node tree at which an operation is to be conducted
# the dest_path provides the steps to get from the top to the destination leaf
#  in dest_path the moretype values -  ward, etc if you want to create nodes of certain type at the end of the search
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
        while steps:
# shuffle down child nodes looking for the 'next' = child.value
            next = steps.pop()
# set the next level type according to the path OR if specified the moretype parameter

            print(f"____In path {dest_path} after pop next {next} vs newnodes {[x.value for x in newnodes]} :")
            if next in ["PDS","WALKS","DIVS","WARDS"]:
                pass
            else:
                # node is a polling_district data node - check they exist and exit, or read file and create
                i = i+1
                options = [node]
                if node.children:
                    options.extend(node.children)
                catch = [x for x in options if x.value == next]
                print(f"____Ping Loop Test - Next:{next} vs Node{node.value} at node lev {node.level}", "node children:",[x.value for x in node.children],"Catch:", catch)
                if catch:
                    node = catch[0]
                    print("____ EXISTING NODE FOUND  ",node.value,catch[0].value, moretype)
                    if steps == []:
                        ntype = gettypeoflevel(dest_path,node.level+1)
                        if moretype != "":
                            ntype = moretype
        # ping also used to retrieve children of destination node of dest_path type
                        print(f"____ Creating new nodes at {node.value} / {catch[0].value} lev {node.level} of type: {ntype}")
                        if node.level < 4:
# set the next level type according to the path OR if specified the moretype parameter
                            Treepolys[ntype] = Fullpolys[ntype]
                            newnodes = node.create_map_branch(ntype)
                            if len(newnodes) == 0:
                                print(f"____ Error1 - cant find any map children {newnodes} in {node.value} of type {ntype} ")
                        else:
                            newnodes = node.create_data_branch(ntype)
                            if len(newnodes) == 0:
                                print(f"____ Data Leaf - no data children {newnodes}  in {node.value} of type {ntype} ")
                elif node.level < 4:
    # No catch so add new map branch nodes and add next back to the queue
                    steps.append(next)
                    ntype = gettypeoflevel(dest_path, node.level+1)
                    print("____ TRYING NEW MAP NODES AT ", node.value,node.level,ntype,dest_path)
                    newnodes = node.create_map_branch(ntype)
                    print(f"____ NEW NODES AT {node.value} lev {node.level} newnodes {[x.value for x in newnodes]} and children {[x.value for x in node.children]}")
                    if len(newnodes) == 0:
                        print(f"____ Error2 - cant find any map children {newnodes}  in {node.value} of type {ntype} ")
                        node = self
                elif node.level == 4:
    #No catch under ward/div level so add 'next' back into the queue after the following data nodes have been added to tree
                    steps.append(next)
    # This is ward/division level - lower data nodes will be both PDs(polling_districts) or Walks (from kmeans)
                    ntype = gettypeoflevel(dest_path, node.level+1)
                    print(f"____ TRYING NEW DATA L4 NODES AT {node.value} ",node.level,ntype,dest_path)
                    newnodes = node.create_data_branch(ntype)
                    print(f"____ NEW DATA L4 NODES AT {node.value} lev {node.level} newnodes {[x.value for x in newnodes]} and children {[x.value for x in node.children]}")
                    if len(newnodes) == 0:
                        print(f"____ Error - cant find any data children {newnodes}  in {node.value} of type {ntype} ")
                        node = self
                elif node.level == 5:
                    ntype = gettypeoflevel(dest_path, node.level+1)
                    print(f"____ TRYING NEW DATA L5 NODES AT {node.value} ",node.level,ntype,dest_path)
                    newnodes = node.create_data_branch(ntype)
                    print(f"____ NEW DATA L5 NODES AT {node.value} lev {node.level} newnodes {[x.value for x in newnodes]} and children {[x.value for x in node.children]}")
                    if len(newnodes) == 0:
                        print(f"____ cant find any data children {newnodes}  in {node.value} of type {ntype} ")
                        node = self
    #this is the walk/PD level - add 'next' back into the queue after lower (street/walkleg) nodes have been added
                else :
    #this is base/street/walkleg level so child type is the actual elector for which there are no lower nodes
                    break
                    #
        print("____ping end:", node.value, node.level,next, steps)
        return node

    def getselectedlayers(self,path):
        global Featurelayers
        #add children, eg wards,constituencies, counties
        ctype = gettypeoflevel(path,self.level+1)
        selectc = Featurelayers[ctype]
        selected = [selectc]
        print(f"_____layerstest0 type:{ctype}",list(reversed(selected)), len(selected[0]._children))
        if self.level > 0:
            #add siblings
            selects = Featurelayers[self.type]
            if len(selects._children) == 0:
                # parent children = siblings, eg constituencies, counties, nations
                 selects.reset()
                 selects.add_nodemaps(self.parent, self.type)
            selected.append(selects)
            print(f"_____layerstest1 type:{self.type}",list(reversed(selected)), len(selected[0]._children), len(selected[1]._children))
        if self.level > 1:
            #add parents, eg counties, nations, country
            selectp = Featurelayers[self.parent.type]
            if len(selectp._children) == 0:
                 selectp.reset()
                 selectp.add_nodemaps(self.parent.parent, self.parent.type)
            selected.append(selectp)
            print(f"_____layerstest2 type:{self.parent.type}",list(reversed(selected)), len(selected[0]._children), len(selected[1]._children), len(selected[2]._children))
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
            print ("_____VRnode:",sumnode.value,sumnode.level,sumnode.VR)
        self = origin
        print ("_____VRstatus:",self.value,self.type,self.VR)
        return

    def updateTurnout(self):
        global MapRoot
        global ElectionSettings
        global VNORM
        global VCO
        sname = self.value
        origin = self
        casnode = origin
        print("____Turnout for Election Type:",ElectionSettings['elections'] )
        if ElectionSettings['elections'] == 'W':
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
            print ("___Nat Turnout:",self.value,self.level,self.turnout)
        else:
#cascade last council ward turnout figure to all streets(children)
            if self.level == 4:
                selected = Ward_Results_data.query('NAME == @sname')
                self.turnout = float('%.6f'%(selected['TURNOUT'].values[0]))
                for l in range(origin.level):
                    casnode.parent.turnout = 0
                    i=1
                    for x in casnode.parent.childrenoftype(gettypeoflevel(casnode.dir,casnode.level)):
                        casnode.parent.turnout = (casnode.parent.turnout + x.turnout)/i
                        print ("_____LGTurnoutlevel:",casnode.level,casnode.value,casnode.turnout)
                        i = i+1
                    casnode = casnode.parent
            elif self.level > 4:
                casnode.turnout = casnode.parent.turnout

            self = origin
            print ("___LG Turnout:",self.value,self.turnout)
        return

    def updateParty(self):
        global MapRoot
        global ElectionSettings
        global VNORM
        global VCO
        sname = self.value
        pname = self.parent.value
        party = "O"
        if self.type == 'ward' and sname in Ward_Results_data['NAME'].to_list():
            selected = Ward_Results_data.query('NAME == @sname')
            party = selected['FIRST'].values[0]
        elif self.type == 'constituency' and sname in Con_Results_data['NAME'].to_list():
            selected = Con_Results_data.query('NAME == @sname')
            party = selected['FIRST'].values[0]
        if party not in VNORM.keys():
            party = "O"
        party = VNORM[party]
        self.col = VCO[party]
        print("______VNORM:", self.value, party, self.col, self.parent.value, self.parent.childrenoftype('walk'))
        print("_______Electorate:", self.value,self.electorate, self.houses)

        return

    def updateElectorate(self,pop):
        global MapRoot
        global ElectionSettings
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

        print ("_____OriginElectorate:",MapRoot.electorate,self.value,self.type,self.electorate)
        return

    def updateHouses(self,pop):
        global MapRoot
        global ElectionSettings
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

        print ("_____OriginHouses:",MapRoot.houses,self.value,self.type,self.houses)
        return

    def childrenoftype(self,electtype):
        typechildren = [x for x in self.children if x.type == electtype]
        return typechildren


    def locmappath(self,real):
        global levelcolours

        target = config.workdirectories['workdir'] + "/" + self.dir + "/" + self.file
        dir = os.path.dirname(target)
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

    def create_name_nodes(self,nodetype,namepoints,ending):
        fam_nodes = []
        print(f"____Namepoints nodes:{namepoints}")
        geometry = gpd.points_from_xy(namepoints.Long.values,namepoints.Lat.values, crs="EPSG:4326")
        block = gpd.GeoDataFrame(
            namepoints, geometry=geometry
            )
        fam_nodes = self.childrenoftype(nodetype)
        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]

        for index, limb  in namepoints.iterrows():
            fam_values = [x.value for x in fam_nodes]
            if limb['Name'] not in fam_values:
                datafid = abs(hash(limb['Name']))
                newnode = TreeNode(normalname(limb['Name']),datafid, Point(limb['Long'],limb['Lat']),self.level+1)
                self.davail = True
                egg = self.add_Tchild(newnode, nodetype)
                egg.file = subending(egg.file,ending)
                egg.bbox = self.bbox
                egg.updateParty()
                egg.updateTurnout()
                egg.updateElectorate(limb['ENOP'])
                print('______Data nodes',egg.value,egg.fid, egg.electorate,egg.houses,egg.target,egg.bbox)
                fam_nodes.append(egg)

    #    self.aggTarget()
        print('______Data frame:',namepoints, fam_nodes)
        return fam_nodes

    def find_Level4(self):
        node = self
        while True:
            if node.level == 4:
                break
            node = node.parent
        return node

    def create_data_branch(self, electtype):
        global allelectors00
        global allelectors
        global areaelectors
        global workdirectories

# if called from within ping, then this module should aim to return the next level of nodes of selected type underneath self.
# the new data namepoints must be derived from the electoral file - name is stored in session['importfile']
# if the electoral file hasn't been loaded yet then that needs to be done first.



        def fast_spatial_chunking(X, max_cluster_size=400, cell_size=0.008, label_prefix="G1_"):
            """
            Fast spatial partitioning by rounding Lat/Long into grid cells and grouping points.

            Parameters:
                X (pd.DataFrame): Must contain 'Lat' and 'Long' columns
                max_cluster_size (int): Maximum items per final cluster
                cell_size (float): Grid resolution in degrees (smaller = finer)
                label_prefix (str): Prefix for cluster labels

            Returns:
                np.ndarray: Cluster labels as strings
            """
            assert 'Lat' in X.columns and 'Long' in X.columns

            df = X.copy()
            df['lat_bin'] = (df['Lat'] / cell_size).astype(int)
            df['lon_bin'] = (df['Long'] / cell_size).astype(int)

            cluster_labels = [''] * len(df)
            cluster_counter = 0

            for (lat_bin, lon_bin), group in df.groupby(['lat_bin', 'lon_bin']):
                group_size = len(group)
                num_subclusters = int(np.ceil(group_size / max_cluster_size))

                # Split the group into subclusters if needed
                for i, chunk_idx in enumerate(np.array_split(group.index, num_subclusters)):
                    label = f"{label_prefix}{cluster_counter}"
                    for idx in chunk_idx:
                        cluster_labels[idx] = label
                    cluster_counter += 1

            return np.array(cluster_labels)



        def recursive_kmeans_latlon(X, max_cluster_size=400, depth=2, prefix='K'):
            """
            Recursively cluster a DataFrame with 'Lat' and 'Long' columns
            so that no resulting cluster exceeds max_cluster_size.

            Parameters:
                X (pd.DataFrame): Must contain 'Lat' and 'Long' columns
                max_cluster_size (int): Maximum allowed number of points per cluster
                depth (int): Used internally for recursion
                prefix (str): Prefix for hierarchical cluster IDs

            Returns:
                dict: {index -> cluster_label}
            """
            if len(X) <= max_cluster_size:
                return {i: f"{prefix}" for i in X.index}

            # Number of clusters needed to keep all below threshold
            k = int(np.ceil(len(X) / max_cluster_size))

            # KMeans on Lat and Long
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            coords = X[['Lat', 'Long']].values
            labels = kmeans.fit_predict(coords)

            label_map = {}
            for i in range(1,k+1,1):
                idx = X.index[labels == i]
                sub_data = X.loc[idx]
                sub_labels = recursive_kmeans_latlon(sub_data, max_cluster_size, depth + 1, prefix=f"{prefix}{i}")
                label_map.update(sub_labels)

            return label_map



        from sklearn.cluster import MiniBatchKMeans


        def greedy_balanced_kmeans_latlon(X, max_cluster_size, random_state=42, label_prefix=""):
            """
            Greedy approximation of balanced KMeans on 'Lat' and 'Long', ensuring no cluster exceeds size limit.

            Parameters:
                X (pd.DataFrame): DataFrame with 'Lat' and 'Long' columns
                max_cluster_size (int): Maximum elements per cluster
                random_state (int): Random seed
                label_prefix (str): Prefix to apply to cluster labels (e.g. "G1_")

            Returns:
                np.ndarray: Cluster labels as strings with optional prefix
            """
            assert 'Lat' in X.columns and 'Long' in X.columns, "DataFrame must contain 'Lat' and 'Long' columns"

            coords = X[['Lat', 'Long']].values
            n_points = len(X)
            initial_k = int(np.ceil(n_points / max_cluster_size))

            # Step 1: Run initial clustering
            kmeans = MiniBatchKMeans(n_clusters=initial_k, random_state=random_state, batch_size=1024)
            initial_labels = kmeans.fit_predict(coords)
            centers = kmeans.cluster_centers_

            df = X.copy()
            df['index'] = df.index
            df['cluster'] = initial_labels
            df['dist'] = np.linalg.norm(coords - centers[initial_labels], axis=1)

            # Step 2: Greedy assignment
            df = df.sort_values(by='dist')  # Assign closer points first
            assignments = {}
            cluster_bins = defaultdict(list)
            cluster_counter = 0
            cluster_id_map = {}

            for _, row in df.iterrows():
                orig_cluster = row['cluster']
                assigned = False

                # Check if original cluster can take more
                if len(cluster_bins[orig_cluster]) < max_cluster_size:
                    assigned = True
                    bin_id = orig_cluster
                else:
                    # Try any other existing bin with space
                    for cid, members in cluster_bins.items():
                        if len(members) < max_cluster_size:
                            bin_id = cid
                            assigned = True
                            break

                if not assigned:
                    # Make a new cluster ID
                    bin_id = f"extra_{cluster_counter}"
                    cluster_counter += 1

                # Label string: prefix + unique ID
                if bin_id not in cluster_id_map:
                    cluster_id_map[bin_id] = f"{label_prefix}{len(cluster_id_map)}"

                label = cluster_id_map[bin_id]
                assignments[row['index']] = label
                cluster_bins[bin_id].append(row['index'])

            # Return as array in correct order
            return np.array([assignments[i] for i in X.index])



        nodelist = []

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], "ActiveElectoralRoll.csv")
        if not file_path or not os.path.exists(file_path):
            print('_______Redirect to upload_form', file_path)
            flash("Please upload a file or provide the name of the electoral roll file.", "error")
            return nodelist


# ward/division level for first time in the loop so import data and calc populations in postcodes

        allelectors0 = pd.read_csv(file_path, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
        alldf0 = pd.DataFrame(allelectors0, columns=['Postcode', 'ENOP','Long', 'Lat'])
        alldf1 = alldf0.rename(columns= {'ENOP': 'Popz'})
# we group electors by each polling_district, calculating mean lat , long for PD centroids and population of each PD for node.electorate
        g = {'Popz':'count'}
        alldf = alldf1.groupby(['Postcode']).agg(g).reset_index()
        alldf['Popz'] = alldf['Popz'].rdiv(1)

        allelectors00 = allelectors0.merge(alldf, on='Postcode',how='left' )

# this section is common after data has been loaded: get filter area from node, PDs from data and the test if in area

        pfile = Treepolys[gettypeoflevel(self.dir,4)]
        Level4node = self.find_Level4()
        Level4boundary = pfile[pfile['FID']== Level4node.fid]
        PDs = set(allelectors00.PD.values)
        frames = []
        for PD in PDs:
            PDelectors = getblock(allelectors00,'PD',PD)
            maplongx = PDelectors.Long.values[0]
            maplaty = PDelectors.Lat.values[0]
            print(f"____PD: {PD} Postcode: {PDelectors.loc[1,'Postcode']} lat: {maplaty}, long: {maplongx} at node:",Level4node.value, Level4node.fid)
        # for all PDs - pull together all PDs which are within the Conboundary constituency boundary
            if Level4boundary.geometry.contains(Point(float('%.6f'%(maplongx)),float('%.6f'%(maplaty)))).item():
                Area = normalname(Level4boundary['NAME'].values[0])
                PDelectors['Area'] = Area
                frames.append(PDelectors)

        if len(frames) > 0:
            allelectors = pd.concat(frames)
            areaelectors = getblock(allelectors,'Area',Level4node.value)

            print("____lenallelectors+areaelectors:",Level4node.value,len(allelectors),len(areaelectors))

#            gdf = gpd.GeoDataFrame(areaelectors, geometry=gpd.points_from_xy(areaelectors.Long, areaelectors.Lat), crs="EPSG:4326")

            # Project to Web Mercator (meters)
#            gdf = gdf.to_crs(epsg=3857)

            # Use projected coordinates for clustering
#            kmeans_data = np.array(list(zip(gdf.geometry.x, gdf.geometry.y)))

            # Define number of clusters (walkset)
#            walkset = min(math.ceil(ElectionSettings['teamsize']), 35)

#            kmeans = KMeans(n_clusters=walkset, random_state=42)
#            kmeans.fit(kmeans_data)
            newlabels = recursive_kmeans_latlon(areaelectors,400)
            # Assign WalkName from labels
#            gdf["WalkName"] = newlabels
            areaelectors["WalkName"] = newlabels
            areaelectors.to_csv(config.workdirectories['workdir']+"/malcolmtest.csv", sep='\t', encoding='utf-8', index=False)

    # so all data is now loaded and we are able to filter by PDs(L5) , walks(L5), streets(L6), walklegs(L6)

    # already have data so node is ward/division level children should be PDs or Walks
            if electtype == 'polling_district':
                PDPtsdf0 = pd.DataFrame(areaelectors, columns=['PD', 'ENOP','Long', 'Lat'])
                PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
    # we group electors by each polling_district, calculating mean lat , long for PD centroids and population of each PD for self.electorate
                g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                PDPtsdf = PDPtsdf1.groupby(['Name']).agg(g).reset_index()
                nodelist = self.create_name_nodes('polling_district',PDPtsdf.reset_index(),"-PDS") #creating PD_nodes with mean PD pos and elector counts
            elif electtype == 'walk':
#                walkPts = [(x[0],x[1],x[2], x[3]) for x in areaelectors[['WalkName','Long','Lat', 'ENOP']].drop_duplicates().values]
                walkdf0 = pd.DataFrame(areaelectors, columns=['WalkName', 'ENOP','Long', 'Lat'])
                walkdf1 = walkdf0.rename(columns= {'WalkName': 'Name'})
    # we group electors by each walk, calculating mean lat , long for walk centroids and population of each walk for self.electorate
                g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                walkdfs = walkdf1.groupby(['Name']).agg(g).reset_index()
                nodelist = self.create_name_nodes('walk',walkdfs.reset_index(),"-WALKS") #creating walk_nodes with mean walk centroid and elector counts
            elif electtype == 'street':
                PDelectors = getblock(areaelectors,'PD',self.value)
    #            StreetPts = [(x[0],x[1],x[2],x[3]) for x in PDelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                streetdf0 = pd.DataFrame(PDelectors, columns=['StreetName','ENOP', 'Long', 'Lat'])
                streetdf1 = streetdf0.rename(columns= {'StreetName': 'Name'})
                g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                streetdf = streetdf1.groupby(['Name']).agg(g).reset_index()
                nodelist = self.create_name_nodes('street',streetdf.reset_index(),"-PRINT") #creating street_nodes with mean street pos and elector counts
            elif electtype == 'walkleg':
                walkelectors = getblock(areaelectors,'WalkName',self.value)
#                WalklegPts = [(x[0],x[1],x[2],x[3]) for x in walkelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                walklegdf0 = pd.DataFrame(walkelectors, columns=['StreetName','ENOP', 'Long', 'Lat'])
                walklegdf1 = walklegdf0.rename(columns= {'StreetName': 'Name'})
                g = {'Lat':'mean','Long':'mean','ENOP':'count'}
                walklegdf = walklegdf1.groupby(['Name']).agg(g).reset_index()
                nodelist = self.create_name_nodes('walkleg',walklegdf,"-PRINT") #creating walkleg_nodes with mean street pos and elector counts
        else:
            print("_____ Electoral file contains no relevant data for this area - Please load correct file")
            nodelist = []
        return nodelist

    def create_map_branch(self,electtype):
        global Treepolys
        global Fullpolys
        Overlaps = {
        "country" : 1,
        "nation" : 0.1,
        "county" : 0.009,
        "constituency" : 0.008,
        "ward" : 0.00005,
        "division" : 0.00005,
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
            Treepolys[self.type] = Fullpolys[self.type]
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
        bbox = self.bbox

        ChildPolylayer = Treepolys[electtype]
        print(f"____Full ChildPolylayer for {electtype}" )
        index = 0
        i = 0
        fam_nodes = self.childrenoftype(electtype)

        for index,limb in ChildPolylayer.iterrows():
            fam_values = [x.value for x in fam_nodes]
            newname = normalname(limb.NAME)
            here = limb.geometry.centroid
#            if parent_geom.intersects(limb.geometry) and parent_geom.intersection(limb.geometry).area > 0.0001:
            if parent_geom.intersection(limb.geometry).area > Overlaps[electtype] and newname not in fam_values:
                egg = TreeNode(newname, limb.FID, here,self.level+1)
                print ("________limb selected and added:",electtype,newname, self.level+1)
                egg = self.add_Tchild(egg, electtype)
                egg.bbox = egg.get_bounding_box(block)[0]
                fam_nodes.append(egg)
                egg.updateParty()
                egg.updateTurnout()
                egg.updateElectorate("0")

            i = i + 1

        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]
        if len(fam_nodes) == 0:
            print (f"________no children of type:{electtype} at lev {self.level+1} for {self.value}")

        print (f"___ at {self.value} lev {self.level} revised {electtype} type fam nodes:{fam_nodes}")

        print ("_________fam_nodes :", i, fam_nodes )
        return fam_nodes

    def create_area_map (self,flayers):
      if self.level > 0:
          title = self.parent.value+"-"+self.value+" set at level "+str(self.bbox)+" "+str(self.centroid)
      else:
          title = self.value+" Level "+str(self.level)+ " "+str(self.bbox)+" "+str(self.centroid)
      title_html = '''<h1 style="z-index:1100;color: black;position: fixed;left:100px;">{0}</h1>'''.format(title)
      print("_____before adding title:",len(self.map._children), self.value, self.level)
      self.map.get_root().html.add_child(folium.Element(title_html))
# just save the r-1,r,
      for layer in flayers:
          self.map.add_child(layer)

      has_layer_control = any(isinstance(child, folium.map.LayerControl) for child in self.map._children.values())

      if not has_layer_control:
          self.map.add_child(folium.LayerControl())
      else:
          self.map = folium.Map(location=[self.centroid.y, self.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(self.level,5)+0.75)*2)))
          self.map.get_root().html.add_child(folium.Element(title_html))
          for layer in flayers:
              self.map.add_child(layer)
          self.map.add_child(folium.LayerControl())
          print(f"____New map created for {self.value} with new layer control")
# the folium save file reference must be a url
      self.map.add_css_link("electtrekprint","https://newbrie.github.io/Electtrek/static/print.css")
      self.map.add_css_link("electtrekstyle","https://newbrie.github.io/Electtrek/static/style.css")
      self.map.add_js_link("electtrekmap","https://newbrie.github.io/Electtrek/static/map.js")
      target = self.locmappath("")
      print("_____before saved map file:",target, len(self.map._children), self.value, self.level)
      if self.level == 4:
          print("_____bboxcheck",self.value,self.bbox)
      self.map.fit_bounds(self.bbox, padding = (0, 0))
      self.map.save(target)
      print("_____saved map file:",target,len(flayers), self.value, self.dir,self.file)

      return self.map

    def set_bounding_box(self,block):
      longmin = block.Long.min()
      latmin = block.Lat.min()
      longmax = block.Long.max()
      latmax = block.Lat.max()
      print("______Bounding Box:",longmin,latmin,longmax,latmax)
      return [Point(latmin,longmin),Point(latmax,longmax)]

    def get_bounding_box(self, block):
      global Treepolys
      global Fullpolys

# for level = 0 use present
# for level < 5 use geometry
# else use supplied data_bbox
      if self.level < 3:
          print(f"___Treepolys at {self.value} lev {self.level} id: {self.fid}",  )
          pfile = Treepolys[gettypeoflevel(self.dir,self.level)]
          pb = pfile[pfile['FID']==self.fid]
          swne = pb.geometry.total_bounds
          swne = [swne[1]+(swne[3]-swne[1])/5,swne[0]+(swne[2]-swne[0])/5,swne[3]-(swne[3]-swne[1])/5,swne[2]-(swne[2]-swne[0])/5]
          roid = pb.dissolve().centroid
          swne =[(float('%.6f'%(swne[0])),float('%.6f'%(swne[1]))),(float('%.6f'%(swne[2])),float('%.6f'%(swne[3])))]
# minx, miny, maxx, maxy
          print("_______Bbox swnemap",swne, pb, self.fid, self.value, self.level)
      elif self.level < 5:
          pfile = Treepolys[gettypeoflevel(self.dir,self.level)]
          pb = pfile[pfile['FID']==self.fid]
          swne = pb.geometry.total_bounds
          swne = [swne[1],swne[0],swne[3],swne[2]]
          roid = pb.dissolve().centroid
          swne =[(float('%.6f'%(swne[0])),float('%.6f'%(swne[1]))),(float('%.6f'%(swne[2])),float('%.6f'%(swne[3])))]
# minx, miny, maxx, maxy
          print("_______Bbox swnemap",swne, pb, self.fid, self.value, self.level)
      else:
#          swne = self.set_bounding_box(block)
          swne = block.geometry.total_bounds
          swne = [swne[1],swne[0],swne[3],swne[2]]
          roid = block.dissolve().centroid
          swne =[(float('%.6f'%(swne[0])),float('%.6f'%(swne[1]))),(float('%.6f'%(swne[2])),float('%.6f'%(swne[3])))]
          print("_______Bbox swnedata",swne, len(block), self.parent.fid, self.parent.value, self.parent.level)
      return [swne,roid]

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
        d = ''.join(d.insert(0,url_for('map',path="UNITED_KINGDOM")))
        return d

    def add_Tchild(self, child_node, etype):
        # creates parent-child relationship
        self.child = child_node
        self.davail = True
        child_node.parent = self
        self.children.append(child_node)
        child_node.type = etype
        child_node.level = child_node.parent.level + 1
        child_node.dir = self.dir+"/"+child_node.value
        child_node.tagno = len([ x for x in self.children if x.type == etype])

        if etype == 'constituency':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'ward':
            child_node.dir = self.dir+"/WARDS/"+child_node.value
            child_node.file = child_node.value+"-WARDS.html"
        elif etype == 'nation':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'county':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'division':
            child_node.dir = self.dir+"/DIVS/"+child_node.value
            child_node.file = child_node.value+"-DIVS.html"
        elif etype == 'polling_district':
            child_node.dir = self.dir+"/PDS/"+child_node.value
            child_node.file = child_node.value+"-PDS.html"
        elif etype == 'walk':
            child_node.dir = self.dir+"/WALKS/"+child_node.value
            child_node.file = child_node.value+"-WALKS.html"
        elif etype == 'street':
            child_node.dir = self.dir
            child_node.file = self.value+"-"+child_node.value+"-PRINT.html"
        elif etype == 'walkleg':
            child_node.dir = self.dir
            child_node.file = self.value+"-"+child_node.value+"-PRINT.html"

        child_node.davail = False

        print("_________new child node dir:  ",child_node.dir)
        return child_node

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

    def traverse(self,leaf):
    # moves through each node referenced from self downwards
        nodes_to_visit = [self]
        count = 0
        node_list = []
        while len(nodes_to_visit) > 0:
          current_node = nodes_to_visit.pop()
          node_list.append(current_node)
#          print("_________Traverse node  ",current_node.value,current_node.fid,current_node.level )
          if current_node.parent is not None:
              if current_node.file == leaf:
                  return c
              print("_________Parent node  ",current_node.parent.value,current_node.parent.fid,current_node.parent.level )
          nodes_to_visit += current_node.children
          count = count+1

        print("_________leafnodes  ",count)
        return sorted (node_list, key=lambda TreeNode: TreeNode.level, reverse=True)
    # Iterative DFS function
    # Run DFS starting from node 'A'
    def find_node(self, start, target):
        visited = set()  # Track visited nodes
        stack = [start]  # Stack for DFS

        while stack:  # Continue until stack is empty
            node = stack.pop()  # Pop a node from the stack
            if node not in visited:
                visited.add(node)  # Mark node as visited
                if node.type == 'street' or node.type == 'walk':
                    PDstreet = node.parent.value+"-"+node.value
                    print("_____find visited node:",PDstreet, target)        # Print the current node (for illustration)
                    if PDstreet == target:
                        return node
                else:
                    print("_____find visited node:",node.value, target)        # Print the current node (for illustration)
                    if node.value == target:
                        return node
                stack.extend(reversed(node.children))  # Add child nodes to stack
        return None

    # Run path directed establishment of node 'A'

    def create_enclosing_gdf(self, gdf, buffer_size=0.0001):
        global current_node
        """
        Create a GeoDataFrame containing the enclosing shape around a set of geographic points.

        Parameters:
            gdf (GeoDataFrame): A GeoDataFrame with Point geometries.
            buffer_size (float, optional): Buffer size for single-point cases (default: 0.001).

        Returns:
            GeoDataFrame: A GeoDataFrame with one row containing the enclosing shape.
        """
        if gdf.empty:
            return gpd.GeoDataFrame(columns=['geometry'], crs=gdf.crs)

        # Extract the MultiPoint geometry from the GeoDataFrame
        multi_point = gdf.iloc[0].geometry

        if multi_point.is_empty:
            return gpd.GeoDataFrame(columns=['geometry'], crs=gdf.crs)

        points = list(multi_point.geoms)

        if len(points) == 1:
            # If there's only one point, apply a small buffer
            enclosed_shape = points[0]

        elif len(points) == 2:
    # If there are exactly 2 points, generate a third artificial point
            p1, p2 = points

            # Compute midpoint of segment AB
            mid_x = (p1.x + p2.x) / 2
            mid_y = (p1.y + p2.y) / 2

            # Compute distance between p1 and p2
            d = np.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

            if d == 0:
                # Edge case where both points are identical (shouldn't happen but safeguard)
                enclosed_shape = p1
            else:
                # Compute height of equilateral triangle
                h = d / np.sqrt(3)

                # Compute perpendicular direction unit vector
                dx = (p2.y - p1.y) / d
                dy = -(p2.x - p1.x) / d

                # Compute two possible third points (above or below the segment)
                p3_a = Point(mid_x + h * dx, mid_y + h * dy)
                p3_b = Point(mid_x - h * dx, mid_y - h * dy)

                # Choose one of the two third points (by default picking p3_a)
                p3 = p3_a

                if p3.is_empty:
                    raise ValueError("Computed third point is empty, check coordinate system and precision issues.")

                # Create a convex hull with the three points

                enclosed_shape = MultiPoint([p1, p2, p3]).convex_hull

        else:
            # For 3+ points, use a convex hull
            enclosed_shape = MultiPoint(points).convex_hull

        # Final smoothing buffer — applied to all cases
#        smoothing_radius = 0.0002 * (self.bbox[1][0] - self.bbox[0][0])
        smoothing_radius = 0.0002
        rounded_shape = enclosed_shape.buffer(buffer_size if len(points) == 1 else smoothing_radius)
        enclosing_gdf = gpd.GeoDataFrame(
            {"NAME":gdf.NAME, "FID":gdf.FID, "LAT":gdf.LAT.values[0],"LONG":gdf.LONG.values[0],"geometry": [rounded_shape]},  # Assign shape as geometry
            crs=gdf.crs  # Use the same CRS as the input GeoDataFrame
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


class ExtendedFeatureGroup(FeatureGroup):
    def __init__(self, name=None, overlay=True, control=True, show=True, type=None, id=None, **kwargs):
        # Pass standard arguments to the base class
        super().__init__(name=name, overlay=overlay, control=control, show=show, **kwargs)
        self.name = name
        self.id = id
        self.type = type

    def reset(self):
        # This clears internal children before rendering
        self._children.clear()
        print("____reset the layer",len(self._children), self)
        return self

    def add_walkshape (self,herenode,type,datablock):
        global levelcolours
        global allelectors
        global areaelectors

        points = [Point(lon, lat) for lon, lat in zip(datablock['Long'], datablock['Lat'])]
        print('_______Walk Shape', herenode.value, herenode.level, len(datablock), points)

        # Create a single MultiPoint geometry that contains all the points
        multi_point = MultiPoint(points)

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
            limbX['UPDOWN'] =  uptag1 +"<br>"+ downtag+"<br>"
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)


#        herenode.tagno = len(self._children)+1
        numtag = str(herenode.tagno)+" "+str(herenode.value)
        num = str(herenode.tagno)
        tag = str(herenode.value)
        typetag = "from <br>"+str(herenode.type)+": "+str(herenode.value)+"<br> move :"
        here = [float('%.6f'%(multi_point.centroid.y)),float('%.6f'%(multi_point.centroid.x))]

        pathref = herenode.dir+"/"+herenode.file
        mapfile = '/transfer/'+pathref

        limb = limbX.iloc[[0]].__geo_interface__  # Ensure this returns a GeoJSON dictionary for the row

        # Ensure 'properties' exists in the GeoJSON and add 'col'
        print("GeoJSON Convex creation:", limb)
        if 'properties' not in limb:
            limb['properties'] = {}

        # Now you can use limb_geojson as a valid GeoJSON feature
        print("GeoJSON Convex Hull Feature:", limb)
        tcol = get_text_color(to_hex(herenode.col))
        bcol = adjust_boundary_color(to_hex(herenode.col),0.7)
        fcol = invert_black_white(tcol)

        folium.GeoJson(
            limb,  # This is the GeoJSON feature (not the GeoDataFrame)
            highlight_function=lambda x: {"fillColor": 'lightgray'},  # Access 'col' in the properties
            popup=folium.GeoJsonPopup(
                fields=['UPDOWN'],  # Reference to the 'UPDOWN' property
                aliases=[typetag],   # This is the label for the 'UPDOWN' field in the popup
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


    def add_nodemaps (self,herenode,type):
        global Treepolys
        global Fullpolys

        global levelcolours
        global allelectors
        global areaelectors
        global Con_Results_data
        print("_________Nodemap:",herenode.value,type, [x.type for x in herenode.children],len(herenode.children), len(herenode.childrenoftype(type)))
        for c in herenode.childrenoftype(type):
            print("______Display children:",herenode.value, c.value,type)
#            layerfids = [x.fid for x in self._children if x.type == type]
#            if c.fid not in layerfids:
            if c.level+1 <= 5:
    #need to select the children boundaries associated with the children nodes - to paint
                pfile = Treepolys[type]
                limbX = pfile[pfile['FID']==c.fid].copy()
                print("______Add_Nodes Treepolys type:",type)
#
                limbX['col'] = c.col

                if herenode.level == 0:
                    downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" county", c.value,getchildtype(c.type))
                    downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,getchildtype(c.type),12)
#                    res = "<p  width=50 id='results' style='font-size: {0}pt;color: gray'> </p>".format(12)
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"  + downtag
#                    c.tagno = len(self._children)+1
                    mapfile = "/transfer/"+c.dir+"/"+c.file
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
                    mapfile = "/transfer/"+c.dir+"/"+c.file
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
                    mapfile = "/transfer/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 3:
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
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
                    pathref = c.dir+"/"+c.file
                    mapfile = '/transfer/'+pathref
#                        self.children.append(c)


                numtag = str(c.tagno)+" "+str(c.value)
                num = str(c.tagno)
                tag = str(c.value)
                here = [ float('%.6f'%(c.centroid.y)),float('%.6f'%(c.centroid.x))]

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

                pathref = c.dir+"/"+c.file
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
                                '''.format(num,tag,mapfile,tcol,fcol),

                               )
                               )
                               )


        print("________Layer map polys",herenode.value,herenode.level, len(Featurelayers[gettypeoflevel(herenode.dir,herenode.level+1)]._children))

        return

    def add_nodemarks (self,herenode,type):
        global levelcolours
        global allelectors
        global areaelectors


        for c in [x for x in herenode.children if x.type == type]:
            print('_______MAP Markers')
#            layerfids = [x.fid for x in self.children if x.type == type]
#            if c.fid not in layerfids:
            numtag = str(c.tagno)+" "+str(c.value)
            num = str(c.tagno)
            tag = str(c.value)
            here = [ float('%.6f'%(c.centroid.y)),float('%.6f'%(c.centroid.x))]
            fill = herenode.col
            pathref = c.dir+"/"+c.file
            mapfile = '/transfer/'+pathref

    #        query = f"""
    #        [out:json][timeout:60];
    #        rel(109202);
    #        map_to_area -> .searchArea;
    #        way["highway"]["name"=\'{str(c.value).title().replace("_"," ")}\']["highway"~"^(residential|unclassified|service|tertiary|motorway|trunk|primary|secondary)$"](area.searchArea);
#
    #        out geom;
    #        """

    #        response = requests.post(
    #            "https://overpass-api.de/api/interpreter",
    #            data=query.encode('utf-8'),
    #            headers={"Content-Type": "text/plain"}
    #        )

    #        if response.status_code == 200:
    #            with open("results.json", "wb") as f:
    #                f.write(response.content)
    #            print("Data retrieved as results.json : ", response.content)
    #        else:
    #            print(f"OpenStreet Map street vector Error:{query} gives: {response.status_code}")

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


        print("________Layer map points",herenode.value,herenode.level,self._children)

        return herenode

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
    global workdirectories
    allelectorscopy = electorsVI
    path = config.workdirectories['workdir']+"/INDATA"
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
#upload street and walk VI and Notes saved updates
    for filename in all_files:
        inDatadf = pd.read_csv(filename,sep="[,\t]")
        print("____inDatadf:",inDatadf.head())

        full_revamped.append(inDatadf)
        pathval = inDatadf['Path'][0]
        Lat = inDatadf['Lat'][0]
        Long = inDatadf['Long'][0]
        roid = Point(Long,Lat)
        session['importfile'] = inDatadf['Electrollfile'][0]
        print("____pathval param:",pathval,Long,Lat,ElectionSettings['importfile'])
#use ping to precisely locate the node for which this update appies
        street_node = MapRoot.ping_node(pathval)
        if street_node:
            for index,entry in inDatadf.iterrows():
                street_node.updateVI(entry['VI'])
                street_node.updateVR(entry['VR'])
                print("line VI update:",street_node.value,street_node.VI, entry['VI'])
                print("line VR update:",street_node.value,street_node.VR, entry['VR'])
            print("file VI update:",street_node.value,street_node.VI, entry['VI'])
            print("file VR update:",street_node.value,street_node.VR, entry['VI'])
            street_node.updateElectorate(street_node.electorate)
            street_node.updateTurnout()
        else:
            print("______No StreetNode found for this update:",nodeval)

        print ("uploaded mergefile:",filename)

    if len(full_revamped) > 0:
        dfx = pd.concat(full_revamped,sort=False)
        VIelectors = dfx[['Path','ENOP','VI','Notes','cdate']].sort_values(by='cdate', ascending=False).drop_duplicates(subset=['ENOP'],keep='last')
        VIelectors.to_csv(path2+"/"+indatamerge, sep='\t', encoding='utf-8', index=False)
        print("______original data",allelectors.columns, allelectors.head())
        print("______unmerged imported data ",VIelectors.columns, VIelectors.head())
        allelectorsX = allelectorscopy.merge(VIelectors, on='ENOP',how='left' )
        print("______merged and imported data",allelectors.columns, allelectors.head())
        allelectorsX.to_excel(path2+"/"+merge)
    else:
        allelectorsX = []
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
    latitude =roid.y
    longitude = roid.x
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
    latitude =roid.y
    longitude = roid.x
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
    parent_geom = parent_gdf.unary_union  # creates a single shapely geometry

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

def getstreamrag(electorframe):
    ef = electorframe
    table_data = []
    streamtable = []
    if os.path.exists(TABLE_FILE):
        with open(TABLE_FILE) as f:
            table_data = json.load(f)
        g = {'filename' : 'count', 'active' : 'count'}
        table_df = pd.DataFrame(table_data)
        streamtable = table_df.groupby(['stream']).agg(g).reset_index()

    streamdash = pd.DataFrame()
    activestreams = []
    if len(ef) > 0:
        ef = pd.DataFrame(ef,columns=['Stream', 'ENOP'])
        # we group electors by Streams, calculating totals in each stream
        g = {'ENOP':'count' }
        streamdash = ef.groupby(['Stream']).agg(g)
        activestreams = list(set(ef['Stream'].values))
        print("_____Activestreams1:",ef.head(), streamdash.head())
    print("_____Activestreams2:",activestreams)
    if len(table_data) > 0:
        g = {'filename' : 'count', 'active' : 'count'}
        table_df = pd.DataFrame(table_data)
        streamtable = table_df.groupby(['stream']).agg(g)
        potentialstreams = sorted(set(row['stream'] for row in table_data))
    else:
        streamtable = pd.DataFrame()
        potentialstreams = []

    rag = defaultdict(dict)
    for stream in potentialstreams:
# for each stream in the table
        rag[stream]['Stream'] = stream.upper()
        if stream.upper() in activestreams: # if used to load allelectors
            rag[stream]['Alive'] = True
            rag[stream]['Elect'] = int(streamdash.loc[stream.upper(),'ENOP']) # can do because its been groupby'ed
        else:
            rag[stream]['Alive'] = False
            rag[stream]['Elect'] = 1
        rag[stream]['Loaded'] = float(int(streamtable.loc[stream.upper(),'active'])/int(streamtable.loc[stream.upper(),'filename']))
# set the RAG status Alive and 100% loaded = GREEN, Alive < 100% AMBER, else RED
        if rag[stream]['Alive'] and rag[stream]['Loaded'] == 1:
            rag[stream]['RAG'] = 'green'
        elif rag[stream]['Alive']:
            rag[stream]['RAG'] = 'amber'
        else:
            rag[stream]['RAG'] = 'red'
    return rag

# create and configure the app
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


ElectionSettings = {}
ElectionSettings['GOTV'] = 0.50
ElectionSettings['yourparty'] = "R"
ElectionSettings['walksize'] = 200
ElectionSettings['teamsize'] = 5
ElectionSettings['elections'] = "W"
ElectionSettings['selectedTags'] = "M1"
ElectionSettings['importfile'] = ""
ElectionSettings['autofix'] = 0
ElectionSettings['candfirst'] = ""
ElectionSettings['candsurn'] = ""
ElectionSettings['electiondate'] = "01/01/2030"

main_index = None # for file processing
TABLE_FILE = os.path.join(config.workdirectories['workdir'],'stream_data.json')

Featurelayers = {
"country": ExtendedFeatureGroup(name='Country Boundaries', overlay=True, control=True, show=True),
"nation": ExtendedFeatureGroup(name='Nation Boundaries', overlay=True, control=True, show=True),
"county": ExtendedFeatureGroup(name='County Boundaries', overlay=True, control=True, show=True),
"constituency": ExtendedFeatureGroup(name='Constituency Boundaries', overlay=True, control=True, show=True),
"ward": ExtendedFeatureGroup(name='Ward Boundaries', overlay=True, control=True, show=True),
"division": ExtendedFeatureGroup(name='Division Boundaries', overlay=True, control=True, show=True),
"polling_district": ExtendedFeatureGroup(name='Polling District Areas', overlay=True, control=True, show=True),
"walk": ExtendedFeatureGroup(name='Walk Areas', overlay=True, control=True, show=True),
"walkleg": ExtendedFeatureGroup(name='Walkleg Electors', overlay=True, control=True, show=True),
"street": ExtendedFeatureGroup(name='Street Electors', overlay=True, control=True, show=True),
"result": ExtendedFeatureGroup(name='Results', overlay=True, control=True, show=True),
"target": ExtendedFeatureGroup(name='Targets', overlay=True, control=True, show=True),
"data": ExtendedFeatureGroup(name='Data', overlay=True, control=True, show=True),
"special": ExtendedFeatureGroup(name='Special Markers', overlay=True, control=True, show=True)
}

#or i, (key, fg) in enumerate(Featurelayers.items(), start=1):
#    fg.id = i
#    fg.type = [
#        'country','nation', 'county', 'constituency', 'ward', 'division', 'polling_district',
#        'walk', 'walkleg', 'street', 'result', 'target', 'data', 'special'
#    ][i - 1]


formdata = {}
filename = "Surrey_HeathRegister.csv"
allelectors = pd.DataFrame()
PDelectors = pd.DataFrame()
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

#        Con_Results_data = Con_Bound_layer.merge(Con_Results_data, how='left', on='NAME' )

print("_________HoC Results data: ",Con_Results_data.columns)
print("_________HoC Results data: ",Ward_Results_data.columns)


longmean = statistics.mean([-7.57216793459,  1.68153079591])
latmean = statistics.mean([ 49.959999905, 58.6350001085])
roid = Point(longmean,latmean)
MapRoot = TreeNode("UNITED_KINGDOM",238, roid, 0)
MapRoot.dir = "UNITED_KINGDOM"
MapRoot.file = "UNITED_KINGDOM-MAP.html"
current_node = MapRoot
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
    user = User.query.get(int(user_id))
    return user

@login_manager.unauthorized_handler     # In unauthorized_handler we have a callback URL
def unauthorized_callback():            # In call back url we can specify where we want to
    return render_template("index.html") # redirect the user in my case it is login page!


@app.route('/location')
def location():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    lat = 54.9783
    long = 1.6178
    current_node.centroid = Point(lon,lat)
    print(f"Received location: Latitude={lat}, Longitude={lon}")
    return f"Received location: Latitude={lat}, Longitude={lon}"

@app.errorhandler(HTTPException)
def handle_exception(e):
    global current_node
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    mapfile = current_node.dir+"/"+current_node.file
    if current_node.level > 0:
        mapfile = current_node.parent.dir+"/"+current_node.parent.file
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/add_tag', methods=['POST'])
@login_required
def add_tag():
    try:
        data = request.get_json()
        new_tag = data.get("tag", "").strip()
        if new_tag and new_tag not in ElectionSettings['selectedTags']:
            ElectionSettings['selectedTags'].append(new_tag)

            # Optional: persist to file
            with open("electionsettings.json", "w") as f:
                json.dump(ElectionSettings, f, indent=2)

        return jsonify({"success": True, "tags": ElectionSettings['selectedTags']})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/streamrag')
@login_required
def get_streamrag():
    global streamrag
    global allelectors
    streamrag = getstreamrag(allelectors)
    print("___JSONIFYED streamrag:",jsonify(streamrag))
    return jsonify(streamrag)

@app.route("/get-constants", methods=["GET"])
@login_required
def get_constants():
    global ElectionSettings
    return jsonify({
        "constants": ElectionSettings,
        "options": OPTIONS
    })

@app.route("/set-constant", methods=["POST"])
@login_required
def set_constant():
    global ElectionSettings
    data = request.get_json()
    name = data.get("name")
    value = data.get("value")
    print("____Back End1:",name,"-",value)
    if name in ElectionSettings:
        print("____Back End2:",name,"-",value)
        ElectionSettings[name] = value
        print("____ElectionSettings:",ElectionSettings['elections'])
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid constant name"), 400

@app.route("/", methods=['POST', 'GET'])
def index():
    global Treepolys
    global Fullpolys

    global MapRoot
    global current_node
    global streamrag


    if 'username' in session:
        flash("__________Session Alive:"+ session['username'])
        print("__________Session Alive:"+ session['username'])
        formdata = {}
        allelectors = []
        streamrag = getstreamrag(allelectors)

        mapfile = current_node.dir+"/"+current_node.file
#        redirect(url_for('captains'))

        return render_template("Dash0.html",  formdata=formdata, group=allelectors ,streamrag=streamrag ,mapfile=mapfile)

    return render_template("index.html")


#login
@app.route('/login', methods=['POST', 'GET'])
def login():
    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys
    global streamrag


    global environment
    global layeritems
    global ElectionSettings

    if 'username' in session:
        flash("User already logged in:", session['username'], " at ", current_node.value)
        print("_______ROUTE/Already logged in:", session['username'], " at ", current_node.value)
        return redirect(url_for('firstpage'))
    # Collect info from forms in the login db
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    print("_______ROUTE/login page", username, user)
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
    flash("🔓 Logging out user:"+ current_user.get_id())
    print("🔓 Logging out user:", current_user.get_id())

    # Always log out the user
    logout_user()

    # Clear the entire session to remove 'username', 'user_id', etc.
    session.clear()

    return redirect(url_for('index'))



@app.route('/dashboard', methods=['GET','POST'])
@login_required
def dashboard ():
    #formdata['username'] = session["username"]
    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys
    global streamrag


    global formdata
    global ElectionSettings

    if 'username' in session:
        print('_______ROUTE/dashboard'+ session['username'] + ' is already logged in at ', current_node.value)
        formdata = {}

        streamrag = getstreamrag(allelectors)

        path = current_node.dir+"/"+current_node.file
#        redirect(url_for('captains'))
        return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)

    flash('_______ROUTE/dashboard no login session ')

    return redirect(url_for('index'))


@app.route('/downbut/<path:path>', methods=['GET','POST'])
@login_required
def downbut(path):
    global current_node
    global ElectionSettings
    global formdata
    global Treepolys
    global Fullpolys
    global Featurelayers
    global layeritems
    formdata = {}
# a down button on a node has been selected on the map, so the new map must be displayed with new down options

# the selected node has to be found from the selected button URL

    if current_node.level < 4:
        Treepolys[gettypeoflevel(path,current_node.level+1)] = Fullpolys[gettypeoflevel(path,current_node.level+1)]
        print(f"____Maxing up Treepoly to Fullpolys for :{gettypeoflevel(path,current_node.level+1)}")
    previous_node = current_node

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
    current_node = previous_node.ping_node(path)
    print("____Route/downbut:",previous_node.value,current_node.value, path)
    atype = gettypeoflevel(path,current_node.level+1)

# the map under the selected node map needs to be configured
# the selected  boundary options need to be added to the layer
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+gettypeoflevel(path,current_node.level+1)+" details"
    print(f"_________layeritems for {current_node.value} of type {atype} are {current_node.childrenoftype(atype)} for lev {current_node.level}")
    layeritems = getlayeritems(current_node.childrenoftype(atype),formdata['tabledetails'] )
    mapfile = current_node.dir+"/"+current_node.file
    if atype == 'ward':
        current_node.file = subending(current_node.file,"-WARDS")
        mapfile = current_node.dir+"/"+current_node.file
        print("_____ward map test:",mapfile)
        focuslayer = Featurelayers[atype].reset()
        focuslayer.add_nodemaps(current_node, atype)
        current_node.create_area_map(current_node.getselectedlayers(path))
    elif atype == 'division':
        current_node.file = subending(current_node.file,"-DIVS")
        mapfile = current_node.dir+"/"+current_node.file
        print("_____division map test:",mapfile)
        focuslayer = Featurelayers[atype].reset()
        focuslayer.add_nodemaps(current_node, atype)
        current_node.create_area_map(current_node.getselectedlayers(path))

    #formdata['username'] = session["username"]
    formdata['country'] = "UNITED_KINGDOM"
    formdata['GOTV'] = ElectionSettings['GOTV']
    formdata['walksize'] = ElectionSettings['walksize']
    formdata['teamsize'] = ElectionSettings['teamsize']
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""

    return   send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/transfer/<path:path>', methods=['GET','POST'])
@login_required
def transfer(path):
    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys
    global Featurelayers


    global environment
    global levels
    global layeritems
    global ElectionSettings
    global formdata



    formdata = {}
# transfering to another any other node with siblings listed below
    previous_node = current_node

# use ping to populate the destination node with which to repaint the screen node map and markers

    current_node = previous_node.ping_node(path)
    mapfile = current_node.dir +"/"+ current_node.file
    print("____Route/transfer:",previous_node.value,current_node.value, path)
    if current_node.level < 5:
            formdata = {}
            atype = gettypeoflevel(path,current_node.level+1)
        # the map under the selected node map needs to be configured
            print("_________selected node",atype,current_node.value, current_node.level,current_node.file)
        # the selected  boundary options need to be added to the layer

            formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
            layeritems = getlayeritems(current_node.children,formdata['tabledetails'] )
            if not os.path.exists(config.workdirectories['workdir']+"/"+mapfile):
                focuslayer = Featurelayers[atype].reset()
                focuslayer.add_nodemaps(current_node, atype)
                current_node.create_area_map(current_node.getselectedlayers(path))
            #formdata['username'] = session["username"]
            formdata['country'] = "UNITED_KINGDOM"
            formdata['GOTV'] = ElectionSettings['GOTV']
            formdata['walksize'] = ElectionSettings['walksize']
            formdata['teamsize'] = ElectionSettings['teamsize']
            formdata['candfirst'] = "Firstname"
            formdata['candsurn'] = "Surname"
            formdata['electiondate'] = "DD-MMM-YY"
            formdata['importfile'] = ""

    else:
        formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
        layeritems = getlayeritems(current_node.parent.children,formdata['tabledetails'] )

    return redirect(url_for('map',path=mapfile))


@app.route('/downPDbut/<path:path>', methods=['GET','POST'])
@login_required
def downPDbut(path):
    global Treepolys
    global Fullpolys
    global Featurelayers
    global current_node
    global MapRoot
    global ElectionSettings
    global allelectors
    global areaelectors
    global filename
    global layeritems

    print ("_________ROUTE/downPDbut/",path, request.method)
    if request.method == 'GET':

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        previous_node = current_node
        current_node = previous_node.ping_node(path)
        current_node.file = subending(current_node.file,"-PDS")
        mapfile = current_node.dir+"/"+current_node.file

        current_node.map = folium.Map(location=[current_node.centroid.y, current_node.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(current_node.level,5)+0.75)*2)))

        shapelayer = Featurelayers['polling_district'].reset()
        print("_____ Before creation - PD display markers ", current_node.level, len(Featurelayers['polling_district']._children))

        WardPDnodelist = current_node.childrenoftype('polling_district')
# if there is a selected file , then allelectors will be full of records
        for PD_node in WardPDnodelist:
            PDelectors = getblock(areaelectors,'PD',PD_node.value)
            Streetsdf0 = pd.DataFrame(PDelectors, columns=['StreetName', 'ENOP','Long', 'Lat'])
            Streetsdf1 = Streetsdf0.rename(columns= {'StreetName': 'Name'})
            g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
            Streetsdf = Streetsdf1.groupby(['Name']).agg(g).reset_index()
            print ("______PDPtsdf:",Streetsdf)
            shapelayer.add_walkshape(PD_node, 'polling_district',Streetsdf)
            print("_______new PD Display node",PD_node,"|", Streetsdf, current_node.level, len(Featurelayers['polling_district']._children))

#            areaelectors = getblock(allelectors,'Area',current_node.value)

        if len(WardPDnodelist) == 0:
            flash("Can't find any elector data for this Area.")
            print("Can't find any elector data for this Area.",current_node.type,Featurelayers['polling_district']._children )
        else:
            print("_______just before create_area_map call:",current_node.level, len(Featurelayers['polling_district']._children))

            current_node.create_area_map(current_node.getselectedlayers(path))
            flash("________PDs added  :  "+str(len(Featurelayers['polling_district']._children)))
            print("________After map created PDs added  :  ",current_node.level, len(Featurelayers['polling_district']._children))


            moredata = importVI(allelectors.copy())
            if len(moredata) > 0:
                allelectors = moredata

    print("________PD markers After importVI  :  "+str(len(Featurelayers['polling_district']._children)))

    formdata['tabledetails'] = "Click for "+current_node.value + "\'s polling_district details"
    layeritems = getlayeritems(current_node.childrenoftype('polling_district'),formdata['tabledetails'] )

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/downWKbut/<path:path>', methods=['GET','POST'])
@login_required
def downWKbut(path):
    global Treepolys
    global Fullpolys
    global Featurelayers

    global current_node

    global MapRoot
    global ElectionSettings
    global allelectors
    global areaelectors
    global filename
    global layeritems

    print ("_________ROUTE/downWKbut Requestformfile")
    flash ("_________ROUTE/downWKbut Requestformfile")

    if request.method == 'GET':
# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        previous_node = current_node
        current_node = previous_node.ping_node(path)
        current_node.file = subending(current_node.file,"-WALKS")
        mapfile = current_node.dir+"/"+current_node.file

        current_node.map = folium.Map(location=[current_node.centroid.y, current_node.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(current_node.level,5)+0.75)*2)))

        shapelayer = Featurelayers['walk'].reset()

        print("_______already displayed WALK markers",str(len(Featurelayers['walk']._children)))

        WardWalknodelist = current_node.childrenoftype('walk')
# if there is a selected file , then areaelectors will be full of records for the ward/div
        for walk_node in WardWalknodelist:
            walkelectors = getblock(areaelectors,'WalkName',walk_node.value)
            walksdf0 = pd.DataFrame(walkelectors, columns=['StreetName', 'ENOP','Long', 'Lat'])
            walksdf1 = walksdf0.rename(columns= {'StreetName': 'Name'})
            g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
            walksdf = walksdf1.groupby(['Name']).agg(g).reset_index()
            print ("______walksdf:",walk_node.value, walkelectors.columns, walksdf)

            shapelayer.add_walkshape(walk_node, 'walk',walksdf)
            print("_______new Walk Display node",walk_node.value,"|", walksdf)

#            areaelectors = getblock(allelectors,'Area',current_node.value)

        if len(WardWalknodelist) == 0:
            flash("Can't find any elector data for this Area.")
            print("Can't find any elector data for this Area.",current_node.type,Featurelayers['walk']._children )
        else:
            print("_______just before walk create_area_map call:")
            current_node.create_area_map(current_node.getselectedlayers(path))
            flash("________Walks added  :  "+str(len(Featurelayers['walk']._children)))
            print("________Walks added  :  "+str(len(Featurelayers['walk']._children)))

    moredata = importVI(allelectors.copy())
    if len(moredata) > 0:
        allelectors = moredata

    print("________ Walk markers After importVI  :  "+str(len(Featurelayers['walk']._children)))
    formdata['tabledetails'] = "Click for "+current_node.value+ "\'s walk details"
    layeritems = getlayeritems(current_node.childrenoftype('walk'),formdata['tabledetails'] )

    print("_______writing to file:", mapfile)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/STupdate/<path:path>', methods=['GET','POST'],strict_slashes=False)
@login_required
def STupdate(path):
    global Treepolys
    global Fullpolys

    global current_node


    global allelectors
    global areaelectors
    global environment
    global filename
    global layeritems
    global ElectionSettings

#    steps = path.split("/")
#    filename = steps.pop()
#    current_node = selected_childnode(current_node,steps[-1])
    fileending = "-SDATA.html"
    if path.find("/PDS") < 0:
        fileending = "-WDATA.html"

    session['next'] = 'STupdate/'+path
# use ping to precisely locate the node for which data is to be collected on screen
    current_node = current_node.ping_node(path)
    print(f"passed target path to: {path}")
    print(f"Selected street node: {current_node.value} type: {current_node.type}")

    street_node = current_node
    mapfile = current_node.dir+"/"+current_node.file

    if request.method == 'POST':
    # Get JSON data from request
#        VIdata = request.get_json()  # Expected format: {'viData': [{...}, {...}]}
        try:
            print(f"📥 Incoming request for: {path}")

            # ✅ Print raw request data (useful for debugging)
            print("📄 Raw request data:", request.data)

            # ✅ Ensure JSON request
            if not request.is_json:
                print("❌ Request did not contain JSON")
                return jsonify({"error": "Invalid JSON format"}), 400

            VIdata = request.get_json()
            print(f"✅ Received JSON: {data}")
            changelist =[]
            path = config.workdirectories['workdir']+"/"+current_node.parent.value+"-INDATA"
            headtail = os.path.split(path)
            path2 = headtail[0]

            if "viData" in VIdata and isinstance(VIdata["viData"], list):  # Ensure viData is a list
                changefields = pd.DataFrame(columns=['ENOP','ElectorName','VI','Notes','cdate','Electrollfile'])
                i = 0

                for item in VIdata["viData"]:  # Loop through each elector entry
                    electID = item.get("electorID","").strip()
                    ElectorName = item.get("ElectorName","").strip()
                    VR_value = item.get("vrResponse", "").strip() # Extract vrResponse, "" if none
                    VI_value = item.get("viResponse", "").strip()  # Extract viResponse, "" if none
                    Notes_value = item.get("notesResponse", "").strip()  # Extract viResponse, "" if none
                    Tags_value = item.get("tagsResponse", "")  # 👈 Expect a string like "D1 M4"
                    print("VIdata item:",item)  # Print each elector entry to see if duplicates exist

                    if not electID:  # Skip if electorID is missing
                        print("Skipping entry with missing electorID")
                        continue
                    print("_____columns:",allelectors.columns)
                    # Find the row where ENO matches electID
                    selected = allelectors.query("ENOP == @electID")
                    changefields.loc[i,'Path'] = street_node.dir+"/"+street_node.file
                    changefields.loc[i,'Lat'] = street_node.centroid.y
                    changefields.loc[i,'Long'] = street_node.centroid.x
                    changefields.loc[i,'ENOP'] = electID
                    changefields.loc[i,'ElectorName'] = ElectorName
                    if not selected.empty:
                        # Update only if viResponse is non-empty
                        if VR_value:
                            allelectors.loc[selected.index, "VR"] = VR_value
                            street_node.updateVR(VR_value)
                            changefields.loc[i,'VR'] = VR_value
                        if VI_value:
                            allelectors.loc[selected.index, "VI"] = VI_value
                            street_node.updateVI(VI_value)
                            changefields.loc[i,'VI'] = VI_value
                        if Notes_value:
                            allelectors.loc[selected.index, "Notes"] = Notes_value
                            changefields.loc[i,'Notes'] = Notes_value
                            print(f"Updated elector {electID} with VI = {VI_value} and Notes = {Notes_value}")
                            print("ElectorVI", allelectors.loc[selected.index, "ENOP"], allelectors.loc[selected.index, "VI"])
                        if Tags_value:
                            allelectors.loc[selected.index, "tags"] = Tags_value
                        else:
                            print(f"Skipping elector {electID}, empty viResponse")

                        changefields.loc[i,'cdate'] = get_creation_date("")
                        changefields.loc[i,'Electrollfile'] = session.get('importfile')
                        changefields.loc[i,'Username'] = session.get('username')

                    else:
                        print(f"Warning: No match found for ENOP = {electID}")
                    i = i+1

                base_path = path2+"/INDATA"
                base_name = current_node.file.replace("-PRINT.html",fileending.replace(".html",""))
                changefields = changefields.drop_duplicates(subset=['ENOP', 'ElectorName', 'VI', 'Notes'])
# Example Usage
# base_path = "/your/output/directory"
# base_name = "changefile"
# extension = ".csv"

                versioned_filename = get_versioned_filename(base_path, base_name, ".csv")

                # Save DataFrame to the new file
                changefields.to_csv(versioned_filename, sep='\t', encoding='utf-8', index=False)

                print(f"✅ CSV saved as: {versioned_filename}")
            else:
                print("Error: Incorrect JSON format")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return jsonify({"error": str(e)}), 500

# this is for get and post calls
    print("_____Where are we: ", current_node.value, current_node.type, allelectors.columns)

    street = current_node.value
    electorwalks = pd.DataFrame()

    if current_node.type == 'street':
        electorwalks = getblock(allelectors, 'StreetName',current_node.value)
    elif current_node.type == 'walk':
        electorwalks = getblock(allelectors,'WalkName',current_node.value)

    if electorwalks.empty:
        print("⚠️ Error: electorwalks DataFrame is empty!", current_node.value)
        return jsonify({"message": "Success", "file": url_for('map', path=mapfile)})

    STREET_ = current_node.value

    Postcode = electorwalks.loc[0].Postcode

    walk_name = current_node.value
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

    electorwalks['Team'] = ""
    electorwalks['M1'] = ""
    electorwalks['M2'] = ""
    electorwalks['M3'] = ""
    electorwalks['M4'] = ""
    electorwalks['M5'] = ""
    electorwalks['M6'] = ""
    electorwalks['M7'] = ""
    electorwalks['Notes'] = ""

    groupelectors = electorwalks.shape[0]
    if math.isnan(float('%.6f'%(electorwalks.Elevation.max()))):
      climb = 0
    else:
      climb = int(float('%.6f'%(electorwalks.Elevation.max())) - float('%.6f'%(electorwalks.Elevation.min())))

    x = electorwalks.AddressNumber.values
    y = electorwalks.StreetName
    z = electorwalks.AddressPrefix.values
    houses = len(list(set(zip(x,y,z))))+1
    streets = len(electorwalks.StreetName.unique())
    areamsq = 34*21.2*20*21.2
    avstrlen = 200
    housedensity = round(houses/(areamsq/10000),3)
    avhousem = 100*round(math.sqrt(1/housedensity),2)
    streetdash = avstrlen*streets/houses
    speed = 5*1000
    climbspeed = 5*1000 - climb*50/7
    leafmins = 0.5
    canvassmins = 5
    canvasssample = .5
    leafhrs = round(houses*(leafmins+60*streetdash/climbspeed)/60,2)
    canvasshrs = round(houses*(canvasssample*canvassmins+60*streetdash/climbspeed)/60,2)
    prodstats = {}
    prodstats['ward'] = current_node.parent.parent.value
    prodstats['polling_district'] = current_node.parent.value
    prodstats['walk'] = ""
    prodstats['groupelectors'] = groupelectors
    prodstats['climb'] = climb
    prodstats['houses'] = houses
    prodstats['streets'] = streets
    prodstats['housedensity'] = housedensity
    prodstats['leafhrs'] = round(leafhrs,2)
    prodstats['canvasshrs'] = round(canvasshrs,2)

#    electorwalks['ENOP'] =  electorwalks['PD']+"-"+electorwalks['ENO']+ electorwalks['Suffix']*0.1
    target = current_node.locmappath("")
    results_filename = walk_name+"-PRINT.html"
    mapfile = street_node.dir+"/"+street_node.file
    datafile = street_node.dir+"/"+walk_name+fileending


    context = {
        "group": electorwalks,
        "prodstats": prodstats,
        "mapfile": url_for('upbut',path=mapfile),
        "datafile": url_for('STupdate',path=datafile),
        "walkname": walk_name,
        }
    results_template = environment.get_template('canvasscard1.html')

    with open(results_filename, mode="w", encoding="utf-8") as results:
        results.write(results_template.render(context, url_for=url_for))
    #           only create a map if the branch does not already exist
#    current_node = current_node.parent
    mapfile = street_node.dir+"/"+street_node.file
    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
    if current_node.type == 'street':
        layeritems = getlayeritems(current_node.parent.childrenoftype('street'),formdata['tabledetails'])
        print('_______Street Data uploaded:-',url_for('map', path=mapfile))
    elif current_node.type == 'walk':
        print('_______Walk Data uploaded:-',url_for('map', path=mapfile))
        layeritems = getlayeritems(current_node.parent.childrenoftype('walk'),formdata['tabledetails'])
    print('_______Success mapfile:-',url_for('map', path=mapfile))


    return  jsonify({"message": "Success", "file": url_for('map', path=mapfile)})


@app.route('/PDdownST/<path:path>', methods=['GET','POST'])
@login_required
def PDdownST(path):
    global Treepolys
    global Fullpolys
    global Featurelayers

    global current_node


    global allelectors
    global areaelectors
    global environment
    global filename
    global layeritems

    def firstnameinlist(name,list):
        posn = list.index(name)
        return list[posn]
# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers

    PD_node = current_node.ping_node(path)
# now pointing at the STREETS.html node containing a map of street markers
    PDelectors = getblock(areaelectors, 'PD',PD_node.value)
    if request.method == 'GET':
    # we only want to plot with single streets , so we need to establish one street record with pt data to plot
        focuslayer = Featurelayers['street'].reset()
        focuslayer.add_nodemarks(PD_node, 'street')
        streetnodelist = PD_node.childrenoftype('street')

        if len(areaelectors) == 0 or len(Featurelayers['street']._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________streets added  :  "+str(Featurelayers['street']._children))
            print(f"________in {PD_node.value} there {len(streetnodelist)} streetnode and markers added = {len(Featurelayers['street']._children)}")

        for street_node in streetnodelist:
              street = street_node.value

              electorwalks = getblock(areaelectors, 'StreetName',street_node.value)

              STREET_ = street_node.value

              Postcode = electorwalks.loc[0].Postcode

              streetfile_name = street_node.parent.value+"-"+street_node.value
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

              electorwalks['Team'] = ""
              electorwalks['M1'] = ""
              electorwalks['M2'] = ""
              electorwalks['M3'] = ""
              electorwalks['M4'] = ""
              electorwalks['M5'] = ""
              electorwalks['M6'] = ""
              electorwalks['M7'] = ""
              electorwalks['Notes'] = ""

              groupelectors = electorwalks.shape[0]
              if math.isnan(float('%.6f'%(electorwalks.Elevation.max()))):
                  climb = 0
              else:
                  climb = int(float('%.6f'%(electorwalks.Elevation.max())) - float('%.6f'%(electorwalks.Elevation.min())))

              x = electorwalks.AddressNumber.values
              y = electorwalks.StreetName
              z = electorwalks.AddressPrefix.values
              houses = len(list(set(zip(x,y,z))))+1
              street_node.updateHouses(houses)
              streets = len(electorwalks.StreetName.unique())
              areamsq = 34*21.2*20*21.2
              avstrlen = 200
              housedensity = round(houses/(areamsq/10000),3)
              avhousem = 100*round(math.sqrt(1/housedensity),2)
              streetdash = avstrlen*streets/houses
              speed = 5*1000
              climbspeed = 5*1000 - climb*50/7
              leafmins = 0.5
              canvassmins = 5
              canvasssample = .5
              leafhrs = round(houses*(leafmins+60*streetdash/climbspeed)/60,2)
              canvasshrs = round(houses*(canvasssample*canvassmins+60*streetdash/climbspeed)/60,2)
              prodstats = {}
              prodstats['ward'] = PD_node.parent.value
              prodstats['polling_district'] = PD_node.value
              prodstats['groupelectors'] = groupelectors
              prodstats['climb'] = climb
              prodstats['walk'] = ""
              prodstats['houses'] = houses
              prodstats['streets'] = streets
              prodstats['housedensity'] = housedensity
              prodstats['leafhrs'] = round(leafhrs,2)
              prodstats['canvasshrs'] = round(canvasshrs,2)

#                  electorwalks['ENOP'] =  electorwalks['PD']+"-"+electorwalks['ENO']+ electorwalks['Suffix']*0.1
              target = street_node.locmappath("")
              results_filename = streetfile_name+"-PRINT.html"
              datafile = street_node.dir+"/"+streetfile_name+"-SDATA.html"
# mapfile is used for the up link to the PD streets list
              PD_node.file = subending(PD_node.file,"-PDS")
              mapfile = PD_node.dir+"/"+ PD_node.file
              electorwalks = electorwalks.fillna("")

#              These are the street nodes which are the street data collection pages


              context = {
                "group": electorwalks,
                "prodstats": prodstats,
                "mapfile": url_for('upbut',path=mapfile),
                "datafile": url_for('STupdate',path=datafile),
                "walkname": streetfile_name,
                }
              results_template = environment.get_template('canvasscard1.html')

              with open(results_filename, mode="w", encoding="utf-8") as results:
                results.write(results_template.render(context, url_for=url_for))
#           only create a map if the branch does not already exist

        PD_node.create_area_map(PD_node.getselectedlayers(path))
    mapfile = PD_node.dir+"/"+PD_node.file
    formdata['tabledetails'] = "Click for "+current_node.value+  "\'s street details"
    layeritems = getlayeritems(streetnodelist,formdata['tabledetails'])

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers['street']._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers['street']._children)))

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/LGdownST/<path:path>', methods=['GET','POST'])
@login_required
def LGdownST(path):
    global Treepolys
    global Fullpolys
    global Featurelayers

    global current_node


    global allelectors
    global areaelectors
    global environment
    global filename
    global layeritems

    def firstnameinlist(name,list):
        posn = list.index(name)
        return list[posn]
# use ping to populate the next level of street nodes with which to repaint the screen with boundaries and markers

    PD_node = current_node.ping_node(path)
# now pointing at the STREETS.html node containing a map of street markers
    PDelectors = getblock(areaelectors, 'PD',PD_node.value)
    if request.method == 'GET':
    # we only want to plot with single streets , so we need to establish one street record with pt data to plot
        focuslayer = Featurelayers['street'].reset()
        focuslayer.add_nodemarks(PD_node, 'street')

        if len(areaelectors) == 0 or len(Featurelayers['street']._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________streets added  :  "+str(Featurelayers['street']._children))
            print("________streets added  :  "+str(len(Featurelayers['street']._children)))

        streetnodelist = PD_node.childrenoftype('street')
        for street_node in streetnodelist:
              street = street_node.value

              electorwalks = getblock(areaelectors, 'StreetName',street_node.value)

              STREET_ = street_node.value

              Postcode = electorwalks.loc[0].Postcode

              streetfile_name = street_node.parent.value+"-"+street_node.value
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

              electorwalks['Team'] = ""
              electorwalks['M1'] = ""
              electorwalks['M2'] = ""
              electorwalks['M3'] = ""
              electorwalks['M4'] = ""
              electorwalks['M5'] = ""
              electorwalks['M6'] = ""
              electorwalks['M7'] = ""
              electorwalks['Notes'] = ""

              groupelectors = electorwalks.shape[0]
              if math.isnan(float('%.6f'%(electorwalks.Elevation.max()))):
                  climb = 0
              else:
                  climb = int(float('%.6f'%(electorwalks.Elevation.max())) - float('%.6f'%(electorwalks.Elevation.min())))

              x = electorwalks.AddressNumber.values
              y = electorwalks.StreetName
              z = electorwalks.AddressPrefix.values
              houses = len(list(set(zip(x,y,z))))+1
              street_node.updateHouses(houses)
              streets = len(electorwalks.StreetName.unique())
              areamsq = 34*21.2*20*21.2
              avstrlen = 200
              housedensity = round(houses/(areamsq/10000),3)
              avhousem = 100*round(math.sqrt(1/housedensity),2)
              streetdash = avstrlen*streets/houses
              speed = 5*1000
              climbspeed = 5*1000 - climb*50/7
              leafmins = 0.5
              canvassmins = 5
              canvasssample = .5
              leafhrs = round(houses*(leafmins+60*streetdash/climbspeed)/60,2)
              canvasshrs = round(houses*(canvasssample*canvassmins+60*streetdash/climbspeed)/60,2)
              prodstats = {}
              prodstats['ward'] = PD_node.parent.value
              prodstats['polling_district'] = PD_node.value
              prodstats['groupelectors'] = groupelectors
              prodstats['climb'] = climb
              prodstats['walk'] = ""
              prodstats['houses'] = houses
              prodstats['streets'] = streets
              prodstats['housedensity'] = housedensity
              prodstats['leafhrs'] = round(leafhrs,2)
              prodstats['canvasshrs'] = round(canvasshrs,2)

#                  electorwalks['ENOP'] =  electorwalks['PD']+"-"+electorwalks['ENO']+ electorwalks['Suffix']*0.1
              target = street_node.locmappath("")
              results_filename = streetfile_name+"-PRINT.html"
              datafile = street_node.dir+"/"+streetfile_name+"-SDATA.html"
# mapfile is used for the up link to the PD streets list
              PD_node.file = subending(PD_node.file,"-PDS")
              mapfile = PD_node.dir+"/"+ PD_node.file
              electorwalks = electorwalks.fillna("")

#              These are the street nodes which are the street data collection pages


              context = {
                "group": electorwalks,
                "prodstats": prodstats,
                "mapfile": url_for('upbut',path=mapfile),
                "datafile": url_for('STupdate',path=datafile),
                "walkname": streetfile_name,
                }
              results_template = environment.get_template('canvasscard1.html')

              with open(results_filename, mode="w", encoding="utf-8") as results:
                results.write(results_template.render(context, url_for=url_for))
#           only create a map if the branch does not already exist

        PD_node.create_area_map(PD_node.getselectedlayers(path))
    mapfile = PD_node.dir+"/"+PD_node.file
    formdata['tabledetails'] = "Click for "+current_node.value+  "\'s street details"
    layeritems = getlayeritems(streetnodelist,formdata['tabledetails'])

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers['street']._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers['street']._children)))

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)



@app.route('/WKdownST/<path:path>', methods=['GET','POST'])
@login_required
def WKdownST(path):
    global Treepolys
    global Fullpolys
    global Featurelayers

    global current_node
    global allelectors
    global areaelectors
    global environment
    global filename
    global layeritems

    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers

    walk_node = current_node.ping_node(path)
    walkelectors = getblock(areaelectors, 'WalkName',walk_node.value)
    walks = areaelectors.WalkName.unique()
    if request.method == 'GET':
# if there is a selected file , then allelectors will be full of records
        print("________PDMarker",walk_node.type,"|", walk_node.dir, "|",walk_node.file)

        focuslayer = Featurelayers['walkleg'].reset()
        focuslayer.add_nodemarks(walk_node, 'walkleg')
        walklegnodelist = walk_node.childrenoftype('walkleg')
        print ("________Walklegs",walk_node.value,len(walklegnodelist))
# for each walkleg node(partial street), add a walkleg node marker to the walk_node parent layer (ie PD_node.level+1)
        for walkleg_node in walklegnodelist:

          walkleg = walkleg_node.value
          walklegstreets = walkelectors.StreetName.unique()
          walklegelectors = getblock(walkelectors, 'StreetName',walkleg_node.value)


          print(f"________WalkMarker {walkleg_node.value} | electors {len(walklegelectors)}" )

# overpass query to return A constituencies road geometry
# Untested idea is that we can plot the actual street geometry in the maps rather than just convex hulls
#[out:json][timeout:60];
#rel(109202);
#map_to_area -> .searchArea;
#
#way["highway"]["name"="Elmbridge Lane"](area.searchArea);

#out geom;


          geometry = gpd.points_from_xy(walklegelectors.Long.values,walklegelectors.Lat.values, crs="EPSG:4326")
        # create a geo dataframe for the Walk Map
          geo_df1 = gpd.GeoDataFrame(
            walklegelectors, geometry=geometry
            )

        # Create a geometry list from the GeoDataFrame
          geo_df1_list = [[point.xy[1][0], point.xy[0][0]] for point in geo_df1.geometry]
          CL_unique_list = pd.Series(geo_df1_list).drop_duplicates().tolist()

#          type_colour = allowed[walk_node.value]

    #      marker_cluster = MarkerCluster().add_to(Walkmap)
          # Iterate through the street-postcode list and add a marker for each unique lat long, color-coded by its Cluster.


          print("_______new walkleg Display node",walkleg_node.value,"|", len(Featurelayers['walkleg']._children))

          walk_name = walk_node.value+"-"+walkleg_node.value
          type_colour = "indigo"

          walklegelectors['Team'] = ""
          walklegelectors['M1'] = ""
          walklegelectors['M2'] = ""
          walklegelectors['M3'] = ""
          walklegelectors['M4'] = ""
          walklegelectors['M5'] = ""
          walklegelectors['M6'] = ""
          walklegelectors['M7'] = ""
          walklegelectors['Notes'] = ""

          groupelectors = walklegelectors.shape[0]
          if math.isnan(float('%.6f'%(walklegelectors.Elevation.max()))):
              climb = 0
          else:
              climb = int(float('%.6f'%(walklegelectors.Elevation.max())) - float('%.6f'%(walklegelectors.Elevation.min())))

          x = walklegelectors.AddressNumber.values
          y = walklegelectors.StreetName
          z = walklegelectors.AddressPrefix.values
          houses = len(set(list(zip(x,y,z))))+1
          print(f"____HOUSES:{houses} ")
          walkleg_node.updateHouses(houses)
          streets = len(walklegelectors.StreetName.unique())
          areamsq = 34*21.2*20*21.2
          avstrlen = 200
          housedensity = round(houses/(areamsq/10000),3)
          avhousem = 100*round(math.sqrt(1/housedensity),2)
          streetdash = avstrlen*streets/houses
          speed = 5*1000
          climbspeed = 5*1000 - climb*50/7
          leafmins = 0.5
          canvassmins = 5
          canvasssample = .5
          leafhrs = round(houses*(leafmins+60*streetdash/climbspeed)/60,2)
          canvasshrs = round(houses*(canvasssample*canvassmins+60*streetdash/climbspeed)/60,2)
          prodstats = {}
          prodstats['ward'] = walk_node.parent.parent.value
          prodstats['polling_district'] = walk_node.parent.value
          prodstats['groupelectors'] = groupelectors
          prodstats['walk'] = walk_node.value
          prodstats['climb'] = climb
          prodstats['houses'] = houses
          prodstats['walks'] =  walks
          prodstats['streets'] = streets
          prodstats['housedensity'] = housedensity
          prodstats['leafhrs'] = round(leafhrs,2)
          prodstats['canvasshrs'] = round(canvasshrs,2)

#                  walklegelectors['ENOP'] =  walklegelectors['PD']+"-"+walklegelectors['ENO']+ walklegelectors['Suffix']*0.1
          target = walk_node.locmappath("")
          results_filename = walk_name+"-PRINT.html"

          datafile = walk_node.dir+"/"+walk_name+"-WDATA.html"
# mapfile will capture the walk streetmarkers map at node level
          walk_node.file = subending(walk_node.file,"-WALKS")
          mapfile = walk_node.dir+"/"+walk_node.file

          context = {
            "group": walklegelectors,
            "prodstats": prodstats,
            "mapfile": url_for('upbut',path=mapfile),
            "datafile": url_for('STupdate',path=datafile),
            "walkname": walk_name,
            }
          results_template = environment.get_template('canvasscard1.html')

          with open(results_filename, mode="w", encoding="utf-8") as results:
            results.write(results_template.render(context, url_for=url_for))

        walk_node.create_area_map(walk_node.getselectedlayers(path))

    mapfile = walk_node.dir+"/"+walk_node.file
    formdata['tabledetails'] = "Click for "+walk_node.value +  "\'s street details"
    layeritems = getlayeritems(walklegnodelist, formdata['tabledetails'])


    if len(areaelectors) == 0 or len(Featurelayers['walkleg']._children) == 0:
        flash("Can't find any elector data for this ward.")
        print("Can't find any elector data for this ward.")
    else:
        flash("________walks added  :  "+str(len(Featurelayers['walkleg']._children)))
        print("________walks added  :  "+str(len(Featurelayers['walkleg']._children)))

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/wardreport/<path:path>',methods=['GET','POST'])
@login_required
def wardreport(path):
    global current_node
    global layeritems
    global formdata

# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers

    current_node = current_node.ping_node(path)

    flash('_______ROUTE/wardreport')
    print('_______ROUTE/wardreport')
    mapfile = current_node.dir+"/"+current_node.file
    print("________layeritems  :  ", layeritems)

    i = 0
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
    layeritems = getlayeritems(current_node.create_map_branch('constituency'),formdata['tabledetails'])
    for group_node in current_node.childrenoftype('constituency'):

        layeritems = getlayeritems(group_node.create_map_branch('ward'))

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


    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/displayareas', methods=['POST', 'GET'])
@login_required
def displayareas():
    global current_node
    global layeritems
    global formdata
    global ElectionSettings

    if not layeritems or len(layeritems) < 3:
        return jsonify([[], [], "No data"])

    # --- Handle selected tag from request or session
    selected_tag = ElectionSettings['selectedTags']
    # Unpack layeritems
    df = layeritems[1].copy()
    column_headers = layeritems[0]
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

    # --- Add 'is_tag_set' column
    if selected_tag:
        df["is_tag_set"] = df["tags"].apply(lambda tags: selected_tag in tags)
    else:
        df["is_tag_set"] = False

    # --- Update layeritems for return
    layeritems[1] = df  # Optional if you want to preserve state
    data_json = df.to_json(orient='records', lines=False)
    cols_json = json.dumps(column_headers)
    title_json = json.dumps(title)

    # Return as structured list
    return jsonify([
        json.loads(cols_json),       # Column headers
        json.loads(data_json),       # Rows
        json.loads(title_json)       # Title
    ])
#    return render_template("Areas.html", context = { "layeritems" :layeritems, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

@app.route('/divreport/<path:path>',methods=['GET','POST'])
@login_required
def divreport(path):
    global current_node
    global layeritems
    global formdata
    global Featurelayers

# use ping to populate the next 2 levels of nodes with which to repaint the screen with boundaries and markers

    current_node = current_node.ping_node(path)
    mapfile = current_node.dir+"/"+current_node.file

    flash('_______ROUTE/divreport')
    print('_______ROUTE/divreport')

    i = 0
    layeritems = pd.DataFrame()
    alreadylisted = []
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
    layeritems = getlayeritems(current_node.create_map_branch('constituency'),formdata['tabledetails'])

    for group_node in current_node.childrenoftype('division'):

        layeritems = getlayeritems(group_node.create_map_branch('division'),formdata['tabledetails'])

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


    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/upbut/<path:path>', methods=['GET','POST'])
@login_required
def upbut(path):
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys
    global Featurelayers

    global environment
    global layeritems



    flash('_______ROUTE/upbut',path)
    print('_______ROUTE/upbut',path, current_node.value)
    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
# the selected node has to be found from the selected button URL
#
#    Featurelayers[current_node.level] = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)

    current_node = current_node.ping_node(path)

    if current_node.level < 3:
        Treepolys[current_node.type] = Fullpolys[current_node.type]

    mapfile = current_node.dir+"/"+current_node.file
# the selected node boundary options need to be added to the layer
    atype = gettypeoflevel(mapfile,current_node.level+1)
    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
    layeritems = getlayeritems(current_node.childrenoftype(atype),formdata['tabledetails'] )

    if not os.path.exists(config.workdirectories['workdir']+"/"+mapfile):
        focuslayer = Featurelayers[atype].reset()
        focuslayer.add_nodemaps(current_node, atype)
        current_node.create_area_map(current_node.getselectedlayers(mapfile))

    print("________chosen node url",mapfile)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


#Register user
@app.route('/register', methods=['POST'])
def register():
    flash('_______ROUTE/register')


    username = request.form['username']
    password = request.form['password']
    print("Register", username)

    user = User.query.filter_by(username=username).first()
    if user:
        print("existinuser", user)
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
        return redirect(url_for('get_location'))

@app.route('/map/<path:path>', methods=['GET','POST'])
@login_required
def map(path):
    global current_node
#    steps = path.split("/")
#    last = steps.pop()
#    current_node = selected_childnode(current_node,last)
    flash ("_________ROUTE/map:"+path)
    print ("_________ROUTE/map:",path, current_node.dir)

    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+gettypeoflevel(path,current_node.level)+" details"
    layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(path,current_node.level+1)),formdata['tabledetails'])

    if os.path.isfile(path):
        flash(f"Using existing file: {path}", "info")
        return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)
    else:
        flash(f"Could not find the mapfile:{path}", "warning")
        MapRoot.create_area_map(MapRoot.getselectedlayers(path))
        return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)



@app.route('/showmore/<path:path>', methods=['GET','POST'])
@login_required
def showmore(path):
    global current_node

    steps = path.split("/")
    last = steps.pop().split("-")
    current_node = selected_childnode(current_node,last[1])


    flash ("_________ROUTE/showmore"+path)
    print ("_________showmore",path)

    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
    layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])

    return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)


@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file received'}), 400

    filename = secure_filename(file.filename)
    print("_______After Secure filename check: ",file.filename)
    save_path = os.path.join(config.workdirectories['workdir'], filename)
    file.save(save_path)

    return jsonify({'message': 'File uploaded', 'path': save_path})

@app.route('/setgotv', methods=['POST'])
@login_required
def setgotv():
    global ElectionSettings
    global current_node
    global layeritems
    global allelectors
    global areaelectors
    global streamrag


    flash('_______ROUTE/setgotv',session)
    print('_______ROUTE/setgotv',session)
    selected = None
    streamrag = getstreamrag(allelectors)

    if request.method == 'POST':

        formdata = {}
        formdata = {
        key: value
        for key, value in request.form.items()
            if value.strip()  # Only keep non-empty inputs
            }

        print("User submitted:", formdata)
        # Now `filled_data` contains only the meaningful inputs

        # You can now process only what's been entered
        for field,value in formdata.items():
            ElectionSettings['field'] =  value

        GOTV = ElectionSettings['GOTV']
        autofix = ElectionSettings['autofix']
        mapfile = current_node.dir+"/"+current_node.file
        formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
        print('_______ElectionSettings:',ElectionSettings)
        layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])

        return render_template("Dash0.html",  formdata=formdata, group=allelectors ,streamrag=streamrag ,mapfile=mapfile)
    return ""

@app.route('/filelist/<filetype>', methods=['POST','GET'])
@login_required
def filelist():
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Fullpolys

    global areaelectors

    global environment
    global ElectionSettings
    global formdata
    global layeritems
    flash('_______ROUTE/filelist',filetype)
    print('_______ROUTE/filelist',filetype)

    if filetype == "maps":
        return jsonify({"message": "Success", "file": url_for('map', path=mapfile)})

@app.route('/normalise', methods=['POST'])
@login_required
def normalise():
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Fullpolys
    global allelectors
    global areaelectors
    global ElectionSettings
    global formdata
    global layeritems

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
    # Collect unique streams for dropdowns
    table_data = []
    if os.path.exists(TABLE_FILE):
        with open(TABLE_FILE) as f:
            table_data = json.load(f)
    else:
        table_data = []

    dfw = pd.read_csv(config.workdirectories['bounddir']+"/National_Statistics_Postcode_Lookup_UK_20250612.csv")
    Lookups['LatLong'] = dfw[['Postcode 1','Latitude','Longitude']]
    Lookups['LatLong'] = Lookups['LatLong'].rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
    Lookups['Elevation'] = pd.read_csv(config.workdirectories['bounddir']+"/open_postcode_elevation.csv")
    Lookups['Elevation'].columns = ["Postcode","Elevation"]

    # 1. Get uploaded files
    files = request.files.getlist('files')
    print(f"📂 Files received: {len(files)}")
    for i, f in enumerate(files):
        print(f"  File[{i}]: {f.filename}")

    # 2. Extract metadata and stored paths
    meta_data = {}

    for key, value in request.form.items():
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

    # 3. Combine files/paths with order metadata
    indexed_files = []
    for i, (index, meta) in enumerate(sorted(meta_data.items(), key=lambda x: int(x[0]))):
        file = files[i] if i < len(files) else None
        path = meta.get('stored_path')
        try:
            order = int(meta.get('order', 0))
        except (ValueError, TypeError):
            order = 0

        if file:
            indexed_files.append((order, file))
        elif path:
            indexed_files.append((order, path))
        else:
            print(f"⚠️ No file or stored path for index {i}")

    # 4. Sort files by order
    sorted_files = [file for _, file in sorted(indexed_files, key=lambda x: x[0])]
    print("____Indexed files:", indexed_files)
    print("____Sorted files:", sorted_files)

    # 5. Save uploaded files and record paths
    stored_paths = []
    for i, file in enumerate(sorted_files):
        if hasattr(file, 'filename') and file.filename:
            save_path = os.path.join(upload_dir, file.filename)
            file.save(save_path)
            stored_paths.append(save_path)
            meta_data[str(i)]['saved_path'] = save_path

    # 6. Process metadata (normalisation or routing)
    file_index = 0
    mainframe = pd.DataFrame()
    deltaframes = []
    aviframe = pd.DataFrame()
    DQstats = pd.DataFrame()

    print("___Route/normalise")
    for index, data in meta_data.items():
        print(f"\nRow index {index}")
        stream = str(data.get('stream', '')).upper()
        order = data.get('order')
        filetype = data.get('type')
        purpose = data.get('purpose')
        fixlevel = int(data.get('fixlevel', 0))
        file_path = data.get('stored_path', '')

        print(f"Stream: {stream}")
        print(f"Order: {order}")
        print(f"Type: {filetype}")
        print(f"Purpose: {purpose}")
        print(f"Fixlevel: {fixlevel}")
        print(f"Stored Path: {file_path}")

        formdata = {}
        ImportFilename = str(file_path)
        print("_____ reading file outside normz",ImportFilename)
        if os.path.exists(TABLE_FILE):
            with open(TABLE_FILE) as f:
                table_data = json.load(f)
        else:
            table_data = []
    # Collect unique streams for dropdowns
        streams = sorted(set(row['stream'] for row in table_data))
        streamrag = {}
        dfx = pd.DataFrame()

        try:
            if file_path and os.path.exists(file_path):
                if file_path.upper().endswith('.CSV'):
                    dfx = pd.read_csv(file_path, encoding='ISO-8859-1')
                    print("readingCSVfile outside normz")
                elif file_path.upper().endswith('.XLSX'):
                    dfx = pd.read_excel(file_path)
                    print("readingEXCELfile outside normz")
                else:
                    print("error-Unsupported file format")
                    return render_template('stream_processing_input.html', table_data=table_data, streamrag=streamrag, DQstats = DQstats)
            else:
                flash("error - File path does not exist or is not provided")
                print("error - File path does not exist or is not provided")
                return render_template('stream_processing_input.html', table_data=table_data, streamrag=streamrag, DQstats = DQstats)
        except Exception as e:
            flash("error-file access exception:"+str(e))
            print("error-file access exception:",str(e))
            return render_template('stream_processing_input.html', table_data=table_data, streamrag=streamrag, DQstats = DQstats)

        print("____entering normz:", file_path,dfx.columns)
    # normz delivers [normalised elector data df,stats dict,original data quality stats in df]

        if purpose == "main":
        # this is the main index
            results = normz(RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
            mainframe = results[0]
        elif purpose == 'delta':
        # this is one of many changes that needs to be applied to the main index
            dfx = dfx[dfx['ElectorCreatedMonth'] > 0] # filter out all records with no Postcode
            results = normz(RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
            deltaframes.append(results[0])
        elif purpose == 'avi':
        # this is an addition of columns to the main index
            results = normz(RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
            aviframe =  results[0]
        DQstats = pd.concat([DQstats,results[1]])
        formdata['tabledetails'] = "Electoral Roll File "+ImportFilename+" Details"
        layeritems = getlayeritems(results[0].head(), formdata['tabledetails'])
        print("__concat of DQstats", DQstats,results[1])
# full stream now received - need to apply changes to main
    if len(mainframe) > 0:
        print("__Processed main,delta,avi electors:", len(mainframe), len(deltaframes),len(aviframe), mainframe.columns)
        if len(deltaframes) > 0:
            Outcols = mainframe.columns.to_list()
            for deltaframe in deltaframes:
                deltaframe = pd.DataFrame(deltaframe,columns=Outcols)
                print("_____Deltaframe Details:", deltaframe)
                for index, change in deltaframe.iterrows():
                    print("_____Delta Change Details:", change)
                mainframe = pd.concat([mainframe, pd.DataFrame(deltaframe)], ignore_index=True)
                print("__Processed deltaframe electors:", len(deltaframe), mainframe.columns)
        if len(aviframe) > 0:

            mainframe = mainframe.merge(aviframe[['ENOP','AV']], on='ENOP',how='left' )
            print("__Processed aviframe:", len(aviframe), aviframe.columns)

    mainframe = mainframe.reset_index(drop=True)
    print(f"__concat of mainframe of length {len(mainframe)}- columns:",mainframe.columns )
    allelectors = pd.concat([allelectors, pd.DataFrame(mainframe)], ignore_index=True)
    print("____Final Loadable mainframe columns:",len(allelectors),allelectors.columns)
# assemble data for the RAG status of Streams in allelectors
    streamrag = getstreamrag(allelectors)
    print("__Streamrag2:", streamrag, allelectors.columns)
    targetfile = str(ImportFilename).upper().replace(".CSV","-NORMZ.csv").replace(".XLSX","-NORMZ.csv")
    mainframe.to_csv(targetfile)
    allelectors.to_csv("ActiveElectoralRoll.csv")
    ElectionSettings['importfile'] = targetfile
    #    formdata['username'] = session['username']
    mapfile = current_node.dir+"/"+current_node.file

    print('_______ROUTE/normalise/exit:',ImportFilename, allelectors.columns)
    return render_template('stream_processing_input.html', table_data=table_data, streamrag=streamrag, DQstats = DQstats)


@app.route('/walks', methods=['POST','GET'])
@login_required
def walks():
    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys
    global streamrag


    global environment
    flash('_______ROUTE/walks',session)
    streamrag = getstreamrag(allelectors)


    if len(request.form) > 0:
        formdata = {}
        formdata['importfile'] = request.files['importfile']
        formdata['candfirst'] =  request.form["candfirst"]
        formdata['candsurn'] = request.form["candsurn"]
        formdata['electiondate'] = request.form["electiondate"]
        electwalks = prodwalks(current_node,formdata['importfile'], formdata,Treepolys, environment, Featurelayers)
        formdata = electwalks[1]
        print("_________Mapfile",electwalks[2])
        mapfile = electwalks[2]
        group = electwalks[0]

#    formdata['username'] = session['username']
        formdata['tabledetails'] = getchildtype(current_node.type).upper()+ " Details"
        layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])

        return render_template('Dash0.html',  formdata=formdata, group=allelectors , streamrag=streamrag ,mapfile=mapfile)
    return redirect(url_for('dashboard'))

@app.route('/postcode', methods=['POST','GET'])
@login_required
def postcode():
    global current_node
    global Treepolys
    global Fullpolys
    global Featurelayers




    flash('_______ROUTE/postcode')

    pthref = current_node.dir+"/"+current_node.file
    mapfile = url_for('downbut',path=pathref)
    postcodeentry = request.form["postcodeentry"]
    if len(postcodeentry) > 8:
        postcodeentry = str(postcodeentry).replace(" ","")
    dfx = pd.read_csv(config.workdirectories['bounddir']+"National_Statistics_Postcode_Lookup_UK_20241022.csv")
    df1 = dfx[['Postcode 1','Latitude','Longitude']]
    df1 = df1.rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
    df1['Lat'] = df1['Lat'].astype(float)
    df1['Long'] = df1['Long'].astype(float)
    lookuplatlong = df1[df1['Postcode'] == postcodeentry]
    here = Point(float('%.6f'%(lookuplatlong.Long.values[0])),float('%.6f'%(lookuplatlong.Lat.values[0])))
    pfile = Treepolys[gettypeoflevel(current_node.dir,current_node.level+1)]
    polylocated = electorwalks.find_boundary(pfile,here)

    popuptext = '<ul style="font-size: {4}pt;color: gray;" >Lat: {0} Long: {1} Postcode: {2} Name: {3}</ul>'.format(lookuplatlong.Lat.values[0],lookuplatlong.Long.values[0], postcodeentry, polylocated['NAME'].values[0], 12)
    here1 = [here.y, here.x]
    # in the PD map add PD-cluster walks to the PD map with controls to go back up to the Ward map or down to the Walk map
    Featurelayers['special'].add_child(
      folium.Marker(
         location=here1,
         popup = popuptext,
         icon=folium.Icon(color = "yellow",  icon='search'),
         )
         )

    current_node.map.add_child(Featurelayers['special'])
    nodemapfile = current_node.dir+"/"+current_node.file
    target = current_node.locmappath("")
    current_node.map.save(target)
    return redirect(url_for('dashboard'))


@app.route('/firstpage', methods=['GET', 'POST'])
@login_required
def firstpage():
    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys
    global workdirectories
    global Featurelayers
    global environment
    global layeritems
    global streamrag


    print("🔍 Accessed /firstpage")
    print("🧪 current_user.is_authenticated:", current_user.is_authenticated)
    print("🧪 current_user:", current_user)
    print("🧪 current_node:", current_node.value)
    print("🧪 session keys:", list(session.keys()))
    print("🧪 full session content:", dict(session))

    lat = request.args.get('lat')
    lon = request.args.get('lon')

#    lat = 53.2730 - Runcorn
#    lon = -2.7694 - Runcorn


    if lat and lon:
        # Use lat/lon to filter data, e.g., find matching region in GeoJSON
        print(f"Using GPS: lat={lat}, lon={lon}")
        here = Point(lon, lat)
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
    # This section of code constructs the sourcepath to ping from a given lat long
        sourcepath = ""

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

        session['next'] = sourcepath
# use ping to populate the next level of nodes with which to repaint the screen with boundaries and markers
        current_node = MapRoot.ping_node(sourcepath)
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

        atype = gettypeoflevel(session['next'],current_node.level+1)
    # the map under the selected node map needs to be configured
    # the selected  boundary options need to be added to the layer

        formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
        layeritems = getlayeritems(current_node.children,formdata['tabledetails'] )
        newlayer = Featurelayers[atype].reset()
        newlayer.add_nodemaps(current_node, atype)
        streamrag = getstreamrag(allelectors)

        current_node.create_area_map(current_node.getselectedlayers(session['next']))
        print("______First selected node",atype,len(current_node.children),len(current_node.getselectedlayers(session['next'])[0]._children),current_node.value, current_node.level,current_node.file)

        mapfile = current_node.dir+"/"+current_node.file

        return render_template("Dash0.html", VID_json=VID_json,  formdata=formdata,  group=allelectors , streamrag=streamrag ,mapfile=mapfile)
    else:
        return redirect(url_for('login'))



@app.route('/cards', methods=['POST','GET'])
@login_required
def cards():


    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys
    global streamrag



    global environment
    flash('_______ROUTE/canvasscards',session, request.form, current_node.level)
    streamrag = getstreamrag(allelectors)


    if len(request.form) > 0:
        formdata = {}
        formdata['country'] = "UNITED_KINGDOM"
        formdata['importfile'] = request.files['importfile']
        formdata['candfirst'] =  request.form["candfirst"]
        formdata['candsurn'] = request.form["candsurn"]
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

        #    formdata['username'] = session['username']
                formdata['tabledetails'] = getchildtype(current_node.type).upper()+ " Details"
                layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])


                return render_template('Dash0.html',  formdata=formdata, group=allelectors , streamrag=streamrag ,mapfile=mapfile)
            else:
                flash ( "Data file does not match selected constituency!")
                print ( "Data file does not match selected constituency!")
        else:
            flash ( "Data file does not match selected area!")
            print ( "Data file does not match selected area!")
    return redirect(url_for('dashboard'))

@app.route('/save_table_data', methods=['POST'])
@login_required
def save_table_data():
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
    {'Order': 1, 'Stream': 'A', 'Filename': 'BEEP_ElectoralRoll.xlsx', 'Type': 'xlsx', 'Purpose': 'main', 'Fixlevel': '1'},
    {'Order': 2, 'Stream': 'A', 'Filename': 'BEEP_AbsentVoters.csv', 'Type': 'csv', 'Purpose': 'avi', 'Fixlevel': '2'},
    {'Order': 1, 'Stream': 'B', 'Filename': 'WokingRegister.xlsx', 'Type': 'xlsx', 'Purpose': 'main', 'Fixlevel': '3'},
    {'Order': 2, 'Stream': 'B', 'Filename': 'WokingAVlist.csv', 'Type': 'csv', 'Purpose': 'avi', 'Fixlevel': '1'},
    # Add more file data as needed
]

# Optional: Retire or Redirect `/get_import_table` route
@app.route('/get_import_table')
@login_required
def get_import_table():
    # Redirect to the new combined page
    DQstats = pd.DataFrame()
    return redirect(url_for('stream_processing_with_table', DQstats=DQstats))

# Route to handle stream processing form submission
@app.route('/process_stream', methods=['POST'])
@login_required
def process_stream():
    # Handle the form submission for stream processing
    stream_type = request.form.get('stream_type')
    file = request.files.get('file')
    DQstats = pd.DataFrame()

    if file:
        # Do something with the uploaded file, e.g., save or process it
        # For example, if you want to save the file:
        file.save(f'uploads/{file.filename}')
        flash(f"Stream {stream_type} processing for {file.filename} started.", 'success')
    else:
        flash('No file selected for stream processing.', 'error')

    # Redirect back to the combined page
    return redirect(url_for('stream_processing_with_table', DQstats=DQstats))


@app.route('/stream_input')
@login_required
def stream_input():
    global allelectors
    DQstats = pd.DataFrame()
    # Load table data
    table_data = []
    if os.path.exists(TABLE_FILE):
        with open(TABLE_FILE) as f:
            table_data = json.load(f)
    else:
        table_data = []

    streamrag = getstreamrag(allelectors)

    # Collect unique streams for dropdowns
    streams = sorted(set(row['stream'] for row in table_data))

    print("__Streamrag3",streamrag)

    return render_template('stream_processing_input.html', table_data=table_data, streamrag=streamrag, DQstats = DQstats)

if __name__ in '__main__':
    with app.app_context():
        print("__________Starting up", os.getcwd())
        db.create_all()
        app.run(debug=True)



# 'method' is a function that is present in a file called 'file.py'
