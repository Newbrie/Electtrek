from canvasscards import prodcards, getblock, find_boundary
from walks import prodwalks
#import electwalks, locmappath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
import config
from normalised import normz
#import normz
import folium
import numpy
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



import sys


sys.path
sys.path.append('/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Electtrek.py')
print(sys.path)

levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

levels = ['country','nation','county','constituency','ward/division','polling district/walk','street/walkleg','elector']


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
    route = path.replace("/PDS","").replace("/WALKS","")
    route = subending(route, "")
    parts = route.split("/")
    last = parts.pop() #eg KA-SMITH_STREET or BAGSHOT-MAP
    if last.find("-") > 0:
        parts.append(last.split("-").pop()) #eg SMITH_STREET
    return parts


def getchildtype(parent):
    global levels
    if parent == 'ward' or parent == 'division':
        parent = 'ward/division'
    elif parent == 'walk' or parent == 'polling district':
        parent = 'polling district/walk'
    elif parent == 'street' or parent == 'walkleg':
        parent = 'street/walkleg'
    lev = min(levels.index(parent)+1,7)
    return levels[lev]
#    matches = [index for index, x in enumerate(levels) if x.find(parent) > -1  ]
#    return levels[matches[0]+1]

def gettypeoflevel(path,level):
    global levels
    type = levels[level]
    if path.find(" ") > -1:
        type = path.split(" ")[1] # this is the path syntax override
    if type == 'ward/division' and path.find("_ED/") < 0:
        return 'ward'
    elif type == 'ward/division' and path.find("_ED/") >= 0:
        return 'division'
    elif type == 'polling district/walk'and path.find("/WALKS") < 0:
        return 'polling district'
    elif type == 'polling district/walk'and path.find("/WALKS") >= 0:
        return 'walk'
    elif type == 'street/walkleg'and path.find("/WALKS") < 0:
        return 'street'
    elif type == 'street/walkleg'and path.find("/WALKS") >= 0:
        return 'walkleg'

    return type


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url,target))
    return test_url.scheme in ('http', 'https') and \
            ref_url.netloc == test_url.netloc

def getlayeritems(nodelist,title):
    global ElectionSettings
    global Historynodelist
    global Historytitle
    dfy = pd.DataFrame()
    if isinstance(nodelist, list) and nodelist == []:
        nodelist = Historynodelist
        title = Historytitle
    else:
        Historynodelist = nodelist
        Historytitle = title
    if isinstance(nodelist, pd.DataFrame):
        dfy = nodelist
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
            dfy.loc[i,'turn'] = '%.2f'%(x.turnout)
            dfy.loc[i,'gotv'] = '%.2f'%(float(ElectionSettings['GOTV']))
            dfy.loc[i,'toget'] = int(((x.electorate*x.turnout)/2+1)/float(ElectionSettings['GOTV']))-int(x.VI[ElectionSettings['yourparty']])
            i = i + 1

    return [list(dfy.columns.values),dfy, title]

def subending(filename, ending):
  stem = filename.replace("-WDATA", "@@@").replace("-SDATA", "@@@").replace("-MAP", "@@@").replace("-PRINT", "@@@").replace("-WALKS", "@@@").replace("-PDS", "@@@")
  return stem.replace("@@@", ending)


Historynodelist = []
Historytitle = ""


ElectionOptions = {"W":"Westminster","C":"County","B":"Borough","P":"Parish","U":"Unitary"}
VID = {"R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"getlayeritems","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}
VNORM = {"O":"O","REFORM" : "R" , "REFORM DERBY" : "R" ,"REFORM UK" : "R" ,"REF" : "R", "RUK" : "R","R" :"R","CONSERVATIVE AND UNIONIST" : "C","CONSERVATIVE" : "C", "CON" : "C", "C":"C","LABOUR PARTY" : "S","LABOUR" : "S", "LAB" :"S", "L" : "L", "LIBERAL DEMOCRATS" :"LD" ,"LIBDEM" :"LD" , "LIB" :"LD","LD" :"LD", "GREEN PARTY" : "G" ,"GREEN" : "G" ,"G":"G", "INDEPENDENT" : "I", "IND" : "I" ,"I" : "I" ,"PLAID CYMRU" : "PC" ,"PC" : "PC" ,"SNP": "SNP" ,"MAYBE" : "Z" ,"WONT VOTE" : "W" ,"WON'T SAY" : "X" , "SDLP" : "S", "SINN FEIN" : "SF", "SPK": "N", "TUV" : "C", "UUP" : "C", "DUP" : "C","APNI" : "N", "INET": "I", "NIP": "I","PBPA": "I","WPB": "S","OTHER" : "O"}
VCO = {"O" : "brown","R" : "cyan","C" : "blue","S" : "red","LD" :"yellow","G" :"limegreen","I" :"indigo","PC" : "darkred","SD" : "orange","Z" : "lightgray","W" :  "white", "X" :  "darkgray"}
onoff = {"on" : 1, 'off': 0}


OPTIONS = {
    "elections": ElectionOptions,
    "yourparty": VID,
    "autofix" : onoff
    # Add more mappings here if needed
}

data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))
VID_json = json.dumps(VID)  # Convert to JSON string

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
        self.source = ""
        self.VI = VIC.copy()
        self.turnout = 0
        self.electorate = 0
        self.target = 1

    def upby(self,notch):
        node = self
        for i in range(notch):
            node = self.parent
        return node

    def ping_node(self, path,electrollfile, all):
        global Treepolys
        global Fullpolys
        global levels
        global allelectors00
        global allelectors
        global areaelectors
        global current_node

        all = bool(all)
        path2 = path
        if path.find(" ") > -1:
            path3 = path.split(" ")
            path3.pop() # take off any trailing parameters
            path2 = path3[0]

        steps = list(reversed(stepify(path2))) # make the top the first node
        trunk = self.path_intersect(path2)
        node = self.upby(self.level-len(trunk)+1) # the start node for the depth first search - mostly MapNode

        print("____ping steps -next, trunk vs steps:", node.value, list(reversed(trunk)), " int ",steps)
        block = pd.DataFrame()
        newnodes = [node]
        #if self.value is in not in steps, then error
        i = 0
        next = ""
        while steps:
            # move the node to the next step along the path(starting at MapRoot)
            next = steps.pop()
            print("____After pop next vs newnodes :",next," vs ",[x.value for x in newnodes])
            i = i+1
            catch = [x for x in newnodes if x.value == next]
            print("____Ping Loop Test:",node.value, next, "children",node.children,"Catch", catch)
            if catch:
                node = catch[0]
                print("____ EXISTNG NODE FOUND  ",node.value,catch[0].value)
                if node.level < 4:
                    ntype = gettypeoflevel(node.dir, node.level+1)
                    newnodes = node.create_map_branch(ntype)
                    if len(newnodes) == 0:
                        print(f"____ cant find any children in {node.value} of type {ntype} ")
            elif node.level < 4:
                # add new map branch nodes and add next back to the queue
                ntype = gettypeoflevel(path, node.level+1)
                print("____ TRYING NEW NODES AT ", node.value,node.level,ntype,path)
                newnodes = node.create_map_branch(ntype)
                steps.append(next)
                print("____ NEW NODES AT ",node.value,[x.value for x in newnodes], [x.value for x in node.children])
            elif node.level == 4:
                #add next back into the queue after data nodes have been added
                # new data nodes will be both PDs(polling districts) or Walks (from kmeans)

                try:
                    test = len(allelectors00)
                # catch when df1 is None
                except AttributeError:
                    print(" allelectors is None")
                    test = 0
                    pass
                # catch when it hasn't even been defined
                except NameError:
                    print(" allelectors is not defined")
                    test = 0
                    pass

                if  test == 0 and electrollfile != "":
                # ward/division level for first time in the loop so import data and calc populations in postcodes

                    node.parent.source = electrollfile
                    allelectors0 = pd.read_csv(config.workdirectories['workdir']+"/"+ electrollfile, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
                    alldf0 = pd.DataFrame(allelectors0, columns=['Postcode', 'ENOP','Long', 'Lat'])
                    alldf1 = alldf0.rename(columns= {'ENOP': 'Popz'})
        # we group electors by each polling district, calculating mean lat , long for PD centroids and population of each PD for node.electorate
                    g = {'Popz':'count'}
                    alldf = alldf1.groupby(['Postcode']).agg(g).reset_index()
                    alldf['Popz'] = alldf['Popz'].rdiv(1)

                    allelectors00 = allelectors0.merge(alldf, on='Postcode',how='left' )
                elif electrollfile == "":
                    break
    # this section is common after data has been loaded: get filter area from node, PDs from data and the test if in area
                pfile = Treepolys[gettypeoflevel(path,node.level)]
                Level3boundary = pfile[pfile['FID']==node.fid]
                PDs = set(allelectors00.PD.values)
                print("____ward - PDs:",node.value,PDs)
                frames = []
                for PD in PDs:
                    PDelectors = getblock(allelectors00,'PD',PD)
                    maplongx = PDelectors.Long.values[0]
                    maplaty = PDelectors.Lat.values[0]

                # for all PDs - pull together all PDs which are within the Conboundary constituency boundary
                    if Level3boundary.geometry.contains(Point(float('%.6f'%(maplongx)),float('%.6f'%(maplaty)))).item():
                        Area = normalname(Level3boundary['NAME'].values[0])
                        PDelectors['Area'] = Area
                        frames.append(PDelectors)

                allelectors = pd.concat(frames)
                areaelectors = getblock(allelectors,'Area',node.value)

                print("____lenallelectors+areaelectors:",len(allelectors),len(areaelectors))

                x = areaelectors.Long.values
                y = areaelectors.Lat.values

                areaelectors['WalkName'] = ""
                kmeans_dist_data = list(zip(x, y))
    #                        walkset = min(math.ceil(PDelectors.shape[0]/int(ElectionSettings['walksize'])),35)
                walkset = min(math.ceil(ElectionSettings['teamsize']),35)
                kmeans = KMeans(n_clusters=walkset)
                kmeans.fit(kmeans_dist_data)

                klabels1 = np.char.mod('C%d', kmeans.labels_)
                klabels = klabels1.tolist()

                areaelectors["WalkName"]= klabels
    #                if gettypeoflevel(path,node.level+1) == 'polling district':
                PDPtsdf0 = pd.DataFrame(areaelectors, columns=['PD', 'ENOP','Long', 'Lat'])
                PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
    #  group electors by each polling district, calculating mean lat , long for PD centroids and population of each PD for node.electorate
                g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                PDPtsdf = PDPtsdf1.groupby(['Name']).agg(g).reset_index()
                WardPDnodelist = node.create_data_branch('polling district',PDPtsdf.reset_index(),"-MAP")
                print("____- Walks:",ElectionSettings['teamsize'],list(set(klabels)))
    #                    elif gettypeoflevel(path,node.level+1) == 'walk':
                walkPts = [(x[0],x[1],x[2], x[3]) for x in areaelectors[['WalkName','Long','Lat', 'ENOP']].drop_duplicates().values]
                walkdf0 = pd.DataFrame(walkPts, columns=['WalkName', 'Long', 'Lat', 'ENOP'])
                walkdf1 = walkdf0.rename(columns= {'WalkName': 'Name'})
    #  group electors by each walk, calculating mean lat , long for walk centroids and population of each walk for node.electorate
                g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                walkdfs = walkdf1.groupby(['Name']).agg(g).reset_index()
                walknodelist = node.create_data_branch('walk',walkdfs.reset_index(),"-MAP")
    # already have data so node is ward/division level children should be either PDs and Walks
                if gettypeoflevel(path,node.level) == 'polling district':
                    PDPtsdf0 = pd.DataFrame(areaelectors, columns=['PD', 'ENOP','Long', 'Lat'])
                    PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
    # we group electors by each polling district, calculating mean lat , long for PD centroids and population of each PD for node.electorate
                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                    PDPtsdf = PDPtsdf1.groupby(['Name']).agg(g).reset_index()
                    WardPDnodelist = node.create_data_branch('polling district',PDPtsdf.reset_index(),"-MAP")
                elif gettypeoflevel(path,node.level) == 'walk':
                    walkPts = [(x[0],x[1],x[2], x[3]) for x in areaelectors[['WalkName','Long','Lat', 'ENOP']].drop_duplicates().values]
                    walkdf0 = pd.DataFrame(walkPts, columns=['WalkName', 'Long', 'Lat', 'ENOP'])
                    walkdf1 = walkdf0.rename(columns= {'WalkName': 'Name'})
    # we group electors by each walk, calculating mean lat , long for walk centroids and population of each walk for node.electorate
                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                    walkdfs = walkdf1.groupby(['Name']).agg(g).reset_index()
                    walknodelist = node.create_data_branch('walk',walkdfs.reset_index(),"-MAP")
            elif node.level == 5:
                #add next back into the queue after these nodes have been added
                #this is walk/PD level so child node type will be street so add street nodes
                if gettypeoflevel(path,node.level) == 'polling district':
                    areaelectors = getblock(areaelectors,'PD',node.parent.value)
                # street level , so create street nodes
                    StreetPts = [(x[0],x[1],x[2],x[3]) for x in PDelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                    Streetdf0 = pd.DataFrame(StreetPts, columns=['StreetName', 'Long', 'Lat','ENOP'])
                    Streetdf1 = Streetdf0.rename(columns= {'StreetName': 'Name'})
                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                    Streetdf = Streetdf1.groupby(['Name']).agg(g).reset_index()
                    streetnodelist = node.create_data_branch('street',Streetdf.reset_index(),"-PRINT")
                elif gettypeoflevel(path,node.level) == 'walk':
                    print(len(areaelectors))
                    areaelectors = getblock(areaelectors,'WalkName',node.parent.value)
                # street level , so create street nodes
                    StreetPts = [(x[0],x[1],x[2],x[3]) for x in areaelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                    Streetdf0 = pd.DataFrame(StreetPts, columns=['StreetName', 'Long', 'Lat','ENOP'])
                    Streetdf1 = Streetdf0.rename(columns= {'StreetName': 'Name'})
                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                    Streetdf = Streetdf1.groupby(['Name']).agg(g).reset_index()
                    streetnodelist = node.create_data_branch('walkleg',Streetdf.reset_index(),"-PRINT")
            elif node.level == 6 and gettypeoflevel(path,node.level+1) == 'elector':
            #this is street level so child node type is the actual elector for whcih there are noe nodes
                break
                #

        print("____ping end:", node.value, node.level,next, steps)
        return node

    def getselectedlayers(self):
        global Featurelayers
        #add children, eg wards,constituencies, counties
        ftype = gettypeoflevel(self.dir,self.level+1)
        selected = [Featurelayers[ftype]]
        print("_____layerstest0",list(reversed(selected)), len(selected[0]._children))
        if self.level > 0:
            #add siblings
            ptype = gettypeoflevel(self.dir,self.parent.level+1)
            selectp = Featurelayers[ptype]
            if len(selectp._children) == 0:
                # parent children = siblings, eg constituencies, counties, nations
                 selectp = Featurelayers[ptype].reset()
                 selectp.add_nodemaps(self.parent, self.type)
            selected.append(selectp)
            print("_____layerstest1",list(reversed(selected)),selected[1].type, len(selected[0]._children), len(selected[1]._children))
        if self.level > 1:
            #add parents, eg counties, nations, country
            gptype = gettypeoflevel(self.parent.dir,self.parent.parent.level+1)
            selectgp = Featurelayers[gptype]
            if len(selectgp._children) == 0:
                 selectgp = Featurelayers[gptype].reset()
                 selectgp.add_nodemaps(self.parent.parent, self.parent.type)
            selected.append(selectgp)
            print("_____layerstest2",list(reversed(selected)),selected[1].type, len(selected[0]._children), len(selected[1]._children), len(selected[2]._children))
        return list(reversed(selected))

    def updateVI(self,viValue):
        origin = self
        if self.type == 'street' or self.type == 'walk':
            sumnode = origin
            for x in range(origin.level+1):
                sumnode.VI[viValue] = sumnode.VI[viValue] + 1
                print ("_____VInode:",sumnode.value,sumnode.level,sumnode.VI)
                sumnode = sumnode.parent
        self = origin
        print ("_____VIstatus:",self.value,self.type,self.VI)
        return

    def updateTurnout(self):
        global MapRoot
        global ElectionSettings
        global VNORM
        global VCO
        sname = self.value
        origin = self
        casnode = origin
        if ElectionSettings['elections'] == 'Westminster':
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
        print("______VNORM:", self.value, party, self.col)
        print("_______Electorate:", self.value,self.electorate)

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
                    print ("_____Electoratelevel:",sumnode.level,sumnode.value,sumnode.electorate)
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


    def childrenoftype(self,electtype):
        global ward_div
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

    def create_data_branch(self, electtype, namepoints, ending):
        geometry = gpd.points_from_xy(namepoints.Long.values,namepoints.Lat.values, crs="EPSG:4326")
        block = gpd.GeoDataFrame(
            namepoints, geometry=geometry
            )
        fam_nodes = self.childrenoftype(electtype)
        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]

        for index, limb  in namepoints.iterrows():
            fam_values = [x.value for x in fam_nodes]
            if limb.Name not in fam_values:
                datafid = abs(hash(limb.Name))
                newnode = TreeNode(normalname(limb.Name),datafid, Point(limb.Long,limb.Lat),self.level+1)
                self.davail = True
                egg = self.add_Tchild(newnode, electtype)
                egg.file = subending(egg.file,ending)
                egg.bbox = self.bbox
                egg.updateParty()
                egg.updateTurnout()
                egg.updateElectorate(limb.ENOP)
                print('______Data nodes',egg.value,egg.fid, egg.electorate,egg.target,egg.bbox)
                fam_nodes.append(egg)

    #    self.aggTarget()
        print('______Data frame:',namepoints, fam_nodes)
        return fam_nodes

    def create_map_branch(self,electtype):
        global Treepolys
        global Fullpolys
        block = pd.DataFrame()
        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]
        parent_poly = Treepolys[self.type]
#        parent_geom = parent_poly[parent_poly["FID"] == self.fid].geometry.values[0]

        # Filter the parent geometry based on the FID
        parent_geom = parent_poly[parent_poly["FID"] == self.fid]
        print(f"geometry for {self.value} FID {self.fid} is ",parent_geom)

        # If no matching geometry is found, handle the case where parent_geom is empty
        if parent_geom.empty:
            print(f"Adding back in Full boundaries for {self.value} FID {self.fid}, for {electtype}")
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
        print("____Full ChildPolylayer",Treepolys[electtype] )

            # there are 2-0 (3) relative levels - absolute level are UK(0),nations(1), constituency(2), ward(3)
        index = 0
        i = 0
        fam_nodes = self.childrenoftype(electtype)
        print ("________new branch elements to fam nodes:",self.value,self.level,"**", electtype, fam_nodes)

        if fam_nodes == []:
            Treepolys[electtype] = Fullpolys[electtype]
            fam_nodes = self.childrenoftype(electtype)

        for index,limb in ChildPolylayer.iterrows():
            fam_values = [x.value for x in fam_nodes]
            newname = normalname(limb.NAME)
            here = limb.geometry.centroid
#            if parent_geom.intersects(limb.geometry) and parent_geom.intersection(limb.geometry).area > 0.0001:
            if parent_geom.intersection(limb.geometry).area > 0.0001 and newname not in fam_values:
                egg = TreeNode(newname, limb.FID, here,self.level+1)
                print ("________limb selected:",newname)
                egg = self.add_Tchild(egg, electtype)
                egg.bbox = egg.get_bounding_box(block)[0]
                fam_nodes.append(egg)
                egg.updateParty()
                egg.updateTurnout()
                egg.updateElectorate("0")

            #                    childtable.loc[i,'No']= i
    #                    childtable.loc[i,electtype]=  childnode.value
    #                    childtable.loc[i,self.type] =  self.value
            i = i + 1

    #        for limb in fam_nodes:
    #            childtable.loc[i,'No']= i
    #            childtable.loc[i,limb.type]=  limb.value
    #            childtable.loc[i,self.type] =  self.value
    #            i = i + 1

        print ("_________fam_nodes :", i, fam_nodes )
        return fam_nodes

    def create_area_map (self,flayers,ending):
      self.file = subending(self.file, ending)
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
# the folium save file reference must be a url
      self.map.add_css_link("electtrekprint","https://newbrie.github.io/Electtrek/static/print.css")
      self.map.add_css_link("electtrekstyle","https://newbrie.github.io/Electtrek/static/style.css")
      self.map.add_js_link("electtrekmap","https://newbrie.github.io/Electtrek/static/map.js")
      target = self.locmappath("")
      print("_____before saved map file:",len(self.map._children), self.value, self.level)
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
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'nation':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'county':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'division':
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'polling district':
            child_node.dir = self.dir+"/PDS/"+child_node.value
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'walk':
            child_node.dir = self.dir+"/WALKS/"+child_node.value
            child_node.file = child_node.value+"-MAP.html"
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
        d = dict(sorted(d3.items()))
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
            'LAT': [herenode.centroid.y],  # You can modify this name to fit your case
            'LONG': [herenode.centroid.x],  # FID can be a unique value for the row
            'geometry': [multi_point]  # The geometry field contains the MultiPoint geometry
        }, crs="EPSG:4326")


#            limb = gpd.GeoDataFrame(df, geometry= [convex], crs='EPSG:4326')
#        limb = gpd.GeoDataFrame(df, geometry= [circle], crs="EPSG:4326")
        # Generate enclosing shape
        limbX = herenode.create_enclosing_gdf(gdf)
        limbX['col'] = herenode.col

        if type == 'polling district':
            showmessageST = "showMore(&#39;/PDdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
#            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
#            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
#            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,herenode.source, herenode.dir+"/"+herenode.file)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limbX['UPDOWN'] = uptag1 +"<br>"+ downST
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno, gdf)
        elif type == 'walk':
            showmessage = "showMore(&#39;/WKdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('walk'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
            downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limbX['UPDOWN'] =  uptag1 +"<br>"+ downtag+"<br>"
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)


#        herenode.tagno = len(self._children)+1
        numtag = str(herenode.tagno)+" "+str(herenode.value)
        num = str(herenode.tagno)
        tag = str(herenode.value)
        typetag = "from <br>"+str(herenode.type)+": "+str(herenode.value)+"<br> move :"
        here = [float('%.6f'%(herenode.centroid.y)),float('%.6f'%(herenode.centroid.x))]

        pathref = herenode.dir+"/"+herenode.file
        mapfile = '/transfer/'+pathref

        limb = limbX.iloc[[0]].__geo_interface__  # Ensure this returns a GeoJSON dictionary for the row

        # Ensure 'properties' exists in the GeoJSON and add 'col'
        print("GeoJSON Convex creation:", limb)
        if 'properties' not in limb:
            limb['properties'] = {}

        # Now you can use limb_geojson as a valid GeoJSON feature
        print("GeoJSON Convex Hull Feature:", limb)

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
                "color": 'lightgray',      # Same for the border color
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
                        color: white;
                        font-size: 10pt;
                        font-weight: bold;
                        text-align: center;
                        padding: 2px;
                        white-space: nowrap;">
                        <span style="background: black; padding: 1px 2px; border-radius: 5px;
                        border: 2px solid black;">{0}</span>
                        {1}</div></a>
                        '''.format(num,tag,mapfile),
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
        for c in [x for x in herenode.children if x.type == type]:
            print("______Display children:",herenode.value, c.value,type)
#            layerfids = [x.fid for x in self._children if x.type == type]
#            if c.fid not in layerfids:
            if c.level+1 <= 6:
                pfile = Fullpolys[gettypeoflevel(herenode.dir,herenode.level+1)]
                limbX = pfile[pfile['FID']==c.fid].copy()
                print("______line 1068:")
#
                limbX['col'] = c.col

                if herenode.level == 0:
                    downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,getchildtype(c.type),12)
#                    res = "<p  width=50 id='results' style='font-size: {0}pt;color: gray'> </p>".format(12)
                    print("______line 1076:")
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"  + downtag
#                    c.tagno = len(self._children)+1
                    mapfile = "/transfer/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 1:
                    wardreportmess = "moveDown(&#39;/wardreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    divreportmess = "moveDown(&#39;/divreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
                    wardreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(wardreportmess,"WARD Report",12)
                    divreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(divreportmess,"DIV Report",12)
                    downconstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"CONSTITUENCIES",12)
                    uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                    print("______line 1090:")
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
                    print("______line 1102:")
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ downwardstag + " " + downdivstag
#                    c.tagno = len(self._children)+1
                    mapfile = "/transfer/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 3:
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
                    upload = "<input id='shared_importfile' type='file' name='importfile' placeholder='{1}' style='font-size: {0}pt;color: gray'></input>".format(12, herenode.source)

                    PDbtn = """
                        <form id='PDForm' method='POST' enctype='multipart/form-data' style='display: none;' action=''>
                            <!-- Form to submit the file, hidden from user -->
                        </form>
                        <button type='button' class='guil-button' onclick='moveDown("/downPDbut/{0}", "{1}", "polling district");' class='btn btn-norm'>
                            POLLING DISTRICTS
                        </button>
                    """.format(c.dir+"/"+c.file, c.value)

                    WKbtn = """
                        <form id='WKForm' method='POST' enctype='multipart/form-data' style='display: none;' action=''>
                            <!-- Form to submit the file, hidden from user -->
                        </form>
                        <button type='button' class='guil-button' onclick='moveDown("/downWKbut/{0}", "{1}", "walk");' class='btn btn-norm'>
                            WALKS
                        </button>
                    """.format(c.dir+"/"+c.file, c.value)


                    uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size:{2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                    print("______line 1131:")
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ upload+"<br>"+PDbtn+" "+WKbtn
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
                    print("______line 1150:")
                    limb['properties'] = {}

                # Now you can use limb_geojson as a valid GeoJSON feature
#                print("GeoJSON Feature:", limb)

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
                        "color": 'lightgray',      # Same for the border color
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
                                color: white;
                                font-size: 10pt;
                                font-weight: bold;
                                text-align: center;
                                padding: 2px;
                                white-space: nowrap;">
                                <span style="background: black; padding: 1px 2px; border-radius: 5px;
                                border: 2px solid black;">{0}</span>
                                {1}</div></a>
                                '''.format(num,tag,mapfile),

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

            print("______Display childrenx:",c.value, c.level,type,c.centroid )

            self.add_child(folium.Marker(
                 location=here,
                 icon = folium.DivIcon(
                        html='''
                        <a href='{2}'><div style="
                            color: white;
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: black; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{0}</span>
                            {1}</div></a>
                            '''.format(num,tag,mapfile),
                       )
                       )
                       )


        print("________Layer map points",herenode.value,herenode.level,self._children)

        return herenode



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
        electrollfile = inDatadf['Electrollfile'][0]
        print("____pathval param:",pathval,Long,Lat,electrollfile)
        street_node = MapRoot.ping_node(pathval,electrollfile,False)
        if street_node:
            for index,entry in inDatadf.iterrows():
                street_node.updateVI(entry['VI'])
                print("line VI update:",street_node.value,street_node.VI, entry['VI'])
            print("file VI update:",street_node.value,street_node.VI, entry['VI'])
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
ElectionSettings['elections'] = 'Westminster'
ElectionSettings['importfile'] = ""
ElectionSettings['autofix'] = 0
ElectionSettings['candfirst'] = ""
ElectionSettings['candsurn'] = ""
ElectionSettings['electiondate'] = "01/01/2030"

ward_div = 'ward'


Featurelayers = {
"country": ExtendedFeatureGroup(name='Country Boundaries', overlay=True, control=True, show=True),
"nation": ExtendedFeatureGroup(name='Nation Boundaries', overlay=True, control=True, show=True),
"county": ExtendedFeatureGroup(name='County Boundaries', overlay=True, control=True, show=True),
"constituency": ExtendedFeatureGroup(name='Constituency Boundaries', overlay=True, control=True, show=True),
"ward": ExtendedFeatureGroup(name='Ward Boundaries', overlay=True, control=True, show=True),
"division": ExtendedFeatureGroup(name='Division Boundaries', overlay=True, control=True, show=True),
"polling district": ExtendedFeatureGroup(name='Polling District Areas', overlay=True, control=True, show=True),
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
#        'country','nation', 'county', 'constituency', 'ward', 'division', 'polling district',
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
        print("____ElectionSettings:",ElectionSettings['teamsize'])
        ElectionSettings[name] = value
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid constant name"), 400

@app.route("/", methods=['POST', 'GET'])
def index():
    global Treepolys
    global Fullpolys

    global MapRoot
    global current_node


    if 'username' in session:
        flash("__________Session Alive:"+ session['username'])
        print("__________Session Alive:"+ session['username'])
        formdata = {}
        allelectors = []

        mapfile = current_node.dir+"/"+current_node.file
#        redirect(url_for('captains'))
        DQstats = pd.DataFrame()
        return render_template("Dash0.html", session=session, formdata=formdata, group=allelectors ,DQstats=DQstats ,mapfile=mapfile)

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
                padding-top: 50px;
            }

            .road {
                position: relative;
                width: 100%;
                height: 800px;
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
                transform: rotate(-15deg);
            }

            .right {
                left: 52%;
                transform: rotate(15deg);
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
        <h2>elecTrek is finding democracy at your location...</h2>
        <div class="road">
    {% for i in range(12) %}
    {% set is_left = i % 2 == 0 %}
    <img src="{{ url_for('static', filename='left_foot.svg') if is_left else url_for('static', filename='right_foot.svg') }}"
         class="footprint {{ 'left' if is_left else 'right' }}"
         style="
            top: {{ 800 - i * 100 }}px;
            animation-delay: {{ i * 0.5 }}s;
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


    global formdata
    global ElectionSettings

    mapfile  = current_node.dir+"/"+current_node.file
    if 'username' in session:
        print('_______ROUTE/dashboard'+ session['username'] + ' is already logged in at ', current_node.value)
        formdata = {}
        allelectors = []

        DQstats = pd.DataFrame()

        mapfile = current_node.dir+"/"+current_node.file
#        redirect(url_for('captains'))
        return render_template("Dash0.html", context = {  "session" : session, "formdata" : formdata, "DQstats" : DQstats, "group" : allelectors , "mapfile" : mapfile})

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

    previous_node = current_node
    current_node = previous_node.ping_node(path,previous_node.source,False)
    print("____Route/downbut:",previous_node.value,current_node.value, path)

    atype = gettypeoflevel(path,current_node.level+1)

# the map under the selected node map needs to be configured
    print("_________selected node",path,atype,current_node.value, current_node.level)
    path = path.replace("/PDS","").replace("/WALKS","")
# the selected  boundary options need to be added to the layer
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
    layeritems = getlayeritems(current_node.children,formdata['tabledetails'] )
    nodelayer = Featurelayers[atype].reset()
    nodelayer.add_nodemaps(current_node, atype)

    map = current_node.create_area_map(current_node.getselectedlayers(),"-MAP")


    #formdata['username'] = session["username"]
    formdata['country'] = "UNITED_KINGDOM"
    formdata['GOTV'] = ElectionSettings['GOTV']
    formdata['walksize'] = ElectionSettings['walksize']
    formdata['teamsize'] = ElectionSettings['teamsize']
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""
    mapfile = current_node.dir+"/"+current_node.file

    return   redirect(url_for('map',path=mapfile))

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
    current_node = MapRoot.ping_node(path,current_node.source,False)
    mapfile = current_node.dir +"/"+ current_node.file
    print("____Route/transfer:",previous_node.value,current_node.value, path)
    if current_node.level < 5:
            formdata = {}
            path = path.replace("/PDS","").replace("/WALKS","")
            atype = gettypeoflevel(path,current_node.level+1)
        # the map under the selected node map needs to be configured
            print("_________selected node",atype,current_node.value, current_node.level,current_node.file)
        # the selected  boundary options need to be added to the layer

            formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
            layeritems = getlayeritems(current_node.children,formdata['tabledetails'] )
            focuslayer = Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)].reset()
            focuslayer.add_nodemaps(current_node, atype)
            if not os.path.exists(mapfile):
                map = current_node.create_area_map(current_node.getselectedlayers(),"-MAP")
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
    print('_______Requestformfile',request.files['importfile'].filename)
    flash ("_________Requestformfile"+request.files['importfile'].filename)
    if request.method == 'POST':
        electrollfile = request.files['importfile'].filename
        print ("_________ROUTE/downPDbut/",request.method, electrollfile)

        current_node = current_node.ping_node(path,electrollfile,False)
        current_node.map = folium.Map(location=[current_node.centroid.y, current_node.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(current_node.level,5)+0.75)*2)))

        shapelayer = Featurelayers[gettypeoflevel(current_node.dir, current_node.level+1)].reset()
        print("_____ Before creation - PD display markers ", current_node.level, len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children))

        WardPDnodelist = current_node.childrenoftype('polling district')
# if there is a selected file , then allelectors will be full of records
        for PD_node in WardPDnodelist:
            PDelectors = getblock(areaelectors,'PD',PD_node.value)
            Streetsdf0 = pd.DataFrame(PDelectors, columns=['StreetName', 'ENOP','Long', 'Lat'])
            Streetsdf1 = Streetsdf0.rename(columns= {'StreetName': 'Name'})
            g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
            Streetsdf = Streetsdf1.groupby(['Name']).agg(g).reset_index()
            print ("______PDPtsdf:",Streetsdf)
            shapelayer.add_walkshape(PD_node, 'polling district',Streetsdf)
            print("_______new PD Display node",PD_node,"|", Streetsdf, current_node.level, len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children))

#            areaelectors = getblock(allelectors,'Area',current_node.value)

        if len(areaelectors) == 0:
            flash("Can't find any elector data for this Area.")
            print("Can't find any elector data for this Area.", len(areaelectors),current_node.type,Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children )
        else:
            print("_______just before create_area_map call:",current_node.level, len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children))

            map = current_node.create_area_map(current_node.getselectedlayers(),"-PDS")
            flash("________PDs added  :  "+str(len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children)))
            print("________After map created PDs added  :  ",current_node.level, len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children))


    moredata = importVI(allelectors.copy())
    if moredata != []:
        allelectors = moredata

    print("________PD markers After importVI  :  "+len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children))

    formdata['tabledetails'] = "Click for "+current_node.value + "\'s polling district details"
    layeritems = getlayeritems(current_node.childrenoftype('polling district'),formdata['tabledetails'] )

    mapfile = current_node.dir+"/"+current_node.file
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

    print ("_________ROUTE/downWKbut Requestformfile",request.files['importfile'].filename)
    flash ("_________ROUTE/downWKbut Requestformfile"+request.files['importfile'].filename)

    if request.method == 'POST':
        electrollfile = request.files['importfile'].filename

        current_node = current_node.ping_node(path,electrollfile,False)
        current_node.map = folium.Map(location=[current_node.centroid.y, current_node.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(current_node.level,5)+0.75)*2)))

        shapelayer = Featurelayers[gettypeoflevel(current_node.dir, current_node.level+1)].reset()

        print("_______already displayed WALK markers",str(len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children)))

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

        if len(areaelectors) == 0:
            flash("Can't find any elector data for this Area.")
            print("Can't find any elector data for this Area.",len(areaelectors),current_node.type,Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children )
        else:
            print("_______just before walk create_area_map call:")

            map = current_node.create_area_map(current_node.getselectedlayers(),"-WALKS")
            flash("________Walks added  :  "+str(len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children)))
            print("________Walks added  :  "+str(len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children)))

    moredata = importVI(allelectors.copy())
    if moredata != []:
        allelectors = moredata

    print("________ Walk markers After importVI  :  "+str(len(Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)]._children)))
    formdata['tabledetails'] = "Click for "+current_node.value+ "\'s walk details"
    layeritems = getlayeritems(current_node.childrenoftype('walk'),formdata['tabledetails'] )

    mapfile = current_node.dir+"/"+current_node.file
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


    current_node = current_node.ping_node(path,current_node.parent.source,False)
    path = path.replace("/PDS","").replace("/WALKS","")
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
                    VI_value = item.get("viResponse", "").strip()  # Extract viResponse, "" if none
                    Notes_value = item.get("notesResponse", "").strip()  # Extract viResponse, "" if none
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
                        if VI_value:
                            allelectors.loc[selected.index, "VI"] = VI_value
                            street_node.updateVI(VI_value)
                            changefields.loc[i,'VI'] = VI_value
                        if Notes_value:
                            allelectors.loc[selected.index, "Notes"] = Notes_value
                            changefields.loc[i,'Notes'] = Notes_value
                            print(f"Updated elector {electID} with VI = {VI_value} and Notes = {Notes_value}")
                            print("ElectorVI", allelectors.loc[selected.index, "ENOP"], allelectors.loc[selected.index, "VI"])

                        else:
                            print(f"Skipping elector {electID}, empty viResponse")

                        changefields.loc[i,'cdate'] = get_creation_date("")
                        changefields.loc[i,'Electrollfile'] = street_node.parent.source
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
    prodstats['polling district'] = current_node.parent.value
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

    path = path.replace("/PDS","").replace("/WALKS","").replace("-MAP.html","").replace("-PDS.html","").replace("-WALKS.html","")
    steps = path.split("/")
    current_node = selected_childnode(current_node,steps[-1])
# now pointing at the STREETS.html node containing a map of street markers

    current_node.file = subending(current_node.file,"-MAP")
    PD_node = current_node
    PDelectors = getblock(areaelectors, 'PD',current_node.value)
    if request.method == 'GET':

    # we only want to plot with single streets , so we need to establish one street record with pt data to plot

        StreetPts = [(x[0],x[1],x[2],x[3]) for x in PDelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
        Streetdf0 = pd.DataFrame(StreetPts, columns=['Name', 'Long', 'Lat','ENOP'])

        g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
        Streetdf = Streetdf0.groupby(['Name']).agg(g).reset_index()


        streetnodelist = PD_node.create_data_branch('street',Streetdf.reset_index(),"-PRINT")
        focuslayer = Featurelayers[gettypeoflevel(PD_node.dir,PD_node.level+1)].reset()
        focuslayer.add_nodemarks(PD_node, 'street')

        if len(allelectors) == 0 or len(Featurelayers[gettypeoflevel(PD_node.dir,PD_node.level+1)]._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________streets added  :  "+str(Featurelayers[gettypeoflevel(PD_node.dir,PD_node.level+1)]._children))
            print("________streets added  :  "+str(len(Featurelayers[gettypeoflevel(PD_node.dir,PD_node.level+1)]._children)))


        for street_node in PD_node.childrenoftype('street'):
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
              prodstats['polling district'] = PD_node.value
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
              mapfile = street_node.dir+"/"+street_node.file
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

        map = PD_node.create_area_map(PD_node.getselectedlayers(),"-MAP")
    mapfile = PD_node.dir+"/"+PD_node.file
    formdata['tabledetails'] = "Click for "+current_node.value+  "\'s street details"
    layeritems = getlayeritems(streetnodelist,formdata['tabledetails'])

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers[gettypeoflevel(PD_node.dir,PD_node.level+1)]._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers[gettypeoflevel(PD_node.dir,PD_node.level+1)]._children)))

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

    path = path.replace("/PDS","").replace("/WALKS","").replace("-MAP.html","")
    steps = path.split("/")
    current_node = selected_childnode(current_node,steps[-1])
#

#    current_node.file = subending(current_node.file,"-WALKS")
    walk_node = current_node
    walkelectors = getblock(areaelectors, 'WalkName',walk_node.value)
    walks = walkelectors.WalkName.unique()
    if request.method == 'GET':
# if there is a selected file , then allelectors will be full of records
        print("________PDMarker",walk_node.type,"|", walk_node.dir, "|",walk_node.file)

        StreetPts = [(x[0],x[1],x[2],x[3]) for x in walkelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
        streetdf0 = pd.DataFrame(StreetPts, columns=['StreetName', 'Long', 'Lat','ENOP'])
        streetdf1 = streetdf0.rename(columns= {'StreetName': 'Name'})
        g = {'Lat':'mean','Long':'mean','ENOP':'count'}
        streetdf = streetdf1.groupby(['Name']).agg(g).reset_index()
        walklegnodelist = walk_node.create_data_branch('walkleg',streetdf,"-PRINT")
        focuslayer = Featurelayers[gettypeoflevel(walk_node.dir,walk_node.level+1)].reset()
        focuslayer.add_nodemarks(walk_node, 'walkleg')
        print ("____________walklegs",walk_node.type,streetdf)
# for each walk node, add a walk node convex hull to the walk_node parent layer (ie PD_node.level+1)
        for walkleg_node in walklegnodelist:
          print("________WalkMarker",walkleg_node.type,"|", walkleg_node.dir, "|",walkleg_node.file)

          walkleg = walkleg_node.value
          walk_name = walkleg_node.value

          geometry = gpd.points_from_xy(walkelectors.Long.values,walkelectors.Lat.values, crs="EPSG:4326")
        # create a geo dataframe for the Walk Map
          geo_df1 = gpd.GeoDataFrame(
            walkelectors, geometry=geometry
            )

        # Create a geometry list from the GeoDataFrame
          geo_df1_list = [[point.xy[1][0], point.xy[0][0]] for point in geo_df1.geometry]
          CL_unique_list = pd.Series(geo_df1_list).drop_duplicates().tolist()

#          type_colour = allowed[walk_node.value]

    #      marker_cluster = MarkerCluster().add_to(Walkmap)
          # Iterate through the street-postcode list and add a marker for each unique lat long, color-coded by its Cluster.

          if len(streetdf.reset_index()) > 0:
              print("_______new walkleg Display node",walkleg_node.value,"|", len(Featurelayers[gettypeoflevel(walkleg_node.dir,walkleg_node.level)]._children))

              walk_name = walk_node.value+"-"+walkleg_node.value
              type_colour = "indigo"

              walkelectors['Team'] = ""
              walkelectors['M1'] = ""
              walkelectors['M2'] = ""
              walkelectors['M3'] = ""
              walkelectors['M4'] = ""
              walkelectors['M5'] = ""
              walkelectors['M6'] = ""
              walkelectors['M7'] = ""
              walkelectors['Notes'] = ""

              groupelectors = walkelectors.shape[0]
              if math.isnan(float('%.6f'%(walkelectors.Elevation.max()))):
                  climb = 0
              else:
                  climb = int(float('%.6f'%(walkelectors.Elevation.max())) - float('%.6f'%(walkelectors.Elevation.min())))

              x = walkelectors.AddressNumber.values
              y = walkelectors.StreetName
              z = walkelectors.AddressPrefix.values
              houses = len(list(set(zip(x,y,z))))+1
              streets = len(walkelectors.StreetName.unique())
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
              prodstats['polling district'] = walk_node.parent.value
              prodstats['groupelectors'] = groupelectors
              prodstats['walk'] = walk_node.value
              prodstats['climb'] = climb
              prodstats['houses'] = houses
              prodstats['walks'] =  walks
              prodstats['streets'] = streets
              prodstats['housedensity'] = housedensity
              prodstats['leafhrs'] = round(leafhrs,2)
              prodstats['canvasshrs'] = round(canvasshrs,2)

#                  walkelectors['ENOP'] =  walkelectors['PD']+"-"+walkelectors['ENO']+ walkelectors['Suffix']*0.1
              target = walk_node.locmappath("")
              results_filename = walk_name+"-PRINT.html"

              datafile = walk_node.dir+"/"+walk_name+"-WDATA.html"
              mapfile = walk_node.dir+"/"+walkleg_node.file

              context = {
                "group": walkelectors,
                "prodstats": prodstats,
                "mapfile": url_for('upbut',path=mapfile),
                "datafile": url_for('STupdate',path=datafile),
                "walkname": walk_name,
                }
              results_template = environment.get_template('canvasscard1.html')

              with open(results_filename, mode="w", encoding="utf-8") as results:
                results.write(results_template.render(context, url_for=url_for))
#           only create a map file if branch does not already exist
          else:
              print("________ERROR empty walk  :",streetdf.reset_index())


        map = walk_node.create_area_map(walk_node.getselectedlayers(), "-MAP")

        mapfile = walkleg_node.dir+"/"+walkleg_node.file
        formdata['tabledetails'] = "Click for "+walk_node.value +  "\'s street details"
        layeritems = getlayeritems(walklegnodelist, formdata['tabledetails'])


        if len(areaelectors) == 0 or len(Featurelayers[gettypeoflevel(walk_node.dir,walk_node.level+1)]._children) == 0:
            flash("Can't find any elector data for this ward.")
            print("Can't find any elector data for this ward.")
        else:
            flash("________walks added  :  "+str(len(Featurelayers[gettypeoflevel(walk_node.dir,walk_node.level+1)]._children)))
            print("________walks added  :  "+str(len(Featurelayers[gettypeoflevel(walk_node.dir,walk_node.level+1)]._children)))

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/wardreport/<path:path>',methods=['GET','POST'])
@login_required
def wardreport(path):
    global current_node
    global layeritems
    global formdata

    steps = path.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])

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
#  #    mapfile = current_node.parent.dir+"/"+current_node.parent.file
#    print("________layeritems  :  ", layeritems)

#    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)
#    return redirect(url_for('map',path=mapfile))


@app.route('/displayareas',methods=['POST', 'GET'])
@login_required
def displayareas():
    global current_node
    global layeritems
    global formdata
    print('_______ROUTE/displayareas:', layeritems[2])
    layeritems = getlayeritems([],"")
    json_data = layeritems[1].to_json(orient='records', lines=False)
    json_cols = json.dumps(layeritems[0])
    json_title = json.dumps(layeritems[2])
    # Convert JSON string to Python list
    python_data3 = json.loads(json_title)
    python_data2 = json.loads(json_data)
    python_data1 = json.loads(json_cols)
    # Return the Python list using jsonify
#    print('_______ROUTE/displayarea data', python_data1 ,python_data2)
    return  jsonify([python_data1, python_data2,python_data3])
#    return render_template("Areas.html", context = { "layeritems" :layeritems, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

@app.route('/divreport/<path:path>',methods=['GET','POST'])
@login_required
def divreport(path):
    global current_node
    global layeritems
    global formdata
    global Featurelayers


    steps = path.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
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

        for item in Featurelayers[gettypeoflevel(group_node.dir,group_node.level+1)]._children:
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

    if current_node.level > 0:
        current_node = current_node.parent
    mapfile = current_node.dir+"/"+current_node.file
# the selected node boundary options need to be added to the layer
    atype = gettypeoflevel(path,current_node.level+1)
    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""
    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
    layeritems = getlayeritems(current_node.create_map_branch(atype),formdata['tabledetails'] )
    focuslayer = Featurelayers[gettypeoflevel(current_node.dir,current_node.level+1)].reset()
    focuslayer.add_nodemaps(current_node, atype)

    if not os.path.exists(current_node.dir+"/"+current_node.file):
        map = current_node.create_area_map(current_node.getselectedlayers(),"-MAP")

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

    formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
    layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])

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


@app.route('/upload', methods=['POST','GET'])
@login_required
def upload():
    flash('_______ROUTE/upload')


    print("Upload", username)
    ImportFilename = ""
    if Env1.find("Orange")<=0:
        return render_template('upload.html')
    return redirect(url_for('dashboard'))

@app.route('/setgotv', methods=['POST'])
@login_required
def setgotv():
    global ElectionSettings
    global current_node
    global layeritems
    global allelectors
    global areaelectors


    flash('_______ROUTE/setgotv',session)
    print('_______ROUTE/setgotv',session)
    selected = None
    if request.method == 'POST':

        formdata = {}
        formdata = {
        key: value
        for key, value in request.form.items()
            if value.strip()  # Only keep non-empty inputs
            }

        DQstats = pd.DataFrame()
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

        return render_template("Dash0.html", session=session, formdata=formdata, group=allelectors ,DQstats=DQstats ,mapfile=mapfile)
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



@app.route('/normalise', methods=['POST','GET'])
@login_required
def normalise():
    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys

    global environment
    global ElectionSettings
    global formdata
    global layeritems

    flash('_______ROUTE/normalise',session)
    print('_______ROUTE/normalise',session)


    formdata = {}
    DQstats = pd.DataFrame()
    ElectionSettings['importfile'] = request.files['importfile'].filename
    print("Import filename:",ElectionSettings['importfile'])
    results = normz(request.files['importfile'], formdata,ElectionSettings['autofix'])
# normz delivers [normalised elector data df,stats dict,original data quality stats in df]
    formdata = results[1]
    DQstats = results[2]
    mapfile = current_node.dir+"/"+current_node.file
    group = results[0]
#    formdata['username'] = session['username']
    print('_______ROUTE/normalise/exit:',ElectionSettings['importfile'],DQstats)
    formdata['tabledetails'] = "Electoral Roll File "+ElectionSettings['importfile']+" Details"
    layeritems = getlayeritems(group.head(), formdata['tabledetails'])
    return render_template('Dash0.html', session=session, formdata=formdata, group=allelectors , DQstats=DQstats ,mapfile=mapfile)

@app.route('/walks', methods=['POST','GET'])
@login_required
def walks():
    global MapRoot
    global current_node
    global allelectors
    global areaelectors
    global Treepolys
    global Fullpolys


    global environment
    flash('_______ROUTE/walks',session)


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
        DQstats = pd.DataFrame()
#    formdata['username'] = session['username']
        formdata['tabledetails'] = getchildtype(current_node.type).upper()+ " Details"
        layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])

        return render_template('Dash0.html', session=session, formdata=formdata, group=allelectors , DQstats=DQstats ,mapfile=mapfile)
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
    print("🔍 Accessed /firstpage")
    print("🧪 current_user.is_authenticated:", current_user.is_authenticated)
    print("🧪 current_user:", current_user)
    print("🧪 current_node:", current_node.value)
    print("🧪 session keys:", list(session.keys()))
    print("🧪 full session content:", dict(session))

    lat = request.args.get('lat')
    lon = request.args.get('lon')

    lat = 53.2730
    lon = -2.7694

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
        [step,Treepolys['nation'],Fullpolys['nation']] = intersectingArea(config.workdirectories['bounddir']+"/"+"Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson",'CTRY21NM',here,Treepolys['country'], config.workdirectories['bounddir']+"/"+"Nation_Boundaries.geojson")
        sourcepath = sourcepath+"/"+step
        [step,Treepolys['county'],Fullpolys['county']] = filterArea(config.workdirectories['bounddir']+"/"+"Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson",'CTYUA23NM',here, config.workdirectories['bounddir']+"/"+"County_Boundaries.geojson")
        sourcepath = sourcepath+"/"+step
        [step,Treepolys['constituency'],Fullpolys['constituency']] = intersectingArea(config.workdirectories['bounddir']+"/"+"Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson",'PCON24NM',here,Treepolys['county'], config.workdirectories['bounddir']+"/"+"Constituency_Boundaries.geojson")
        sourcepath = sourcepath+"/"+step
        [step,Treepolys['ward'],Fullpolys['ward']] = intersectingArea(config.workdirectories['bounddir']+"/"+"Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson",'WD24NM',here,Treepolys['constituency'], config.workdirectories['bounddir']+"/"+"Ward_Boundaries.geojson")
        sourcepath = sourcepath+"/"+step+"/"+step+"-MAP.html"
        [step,Treepolys['division'],Fullpolys['division']] = intersectingArea(config.workdirectories['bounddir']+"/"+"County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson",'CED23NM',here,Treepolys['constituency'], config.workdirectories['bounddir']+"/"+"Division_Boundaries.geojson")

        current_node = MapRoot.ping_node(sourcepath,"",False)
        print("____Firstpage Sourcepath",sourcepath, current_node.value)

    if current_user.is_authenticated:
        formdata = {}
        formdata['country'] = "UNITED_KINGDOM"
        flash('_______ROUTE/firstpage')
        print('_______ROUTE/firstpage at :',current_node.value )
        formdata['importfile'] = "SCC-CandidateSelection.xlsx"
        if len(request.form) > 0:
            formdata['importfile'] = request.files['importfile'].filename
        df1 = pd.read_excel(config.workdirectories['workdir']+"/"+formdata['importfile'])
        formdata['tabledetails'] = "Candidates File "+formdata['importfile']+" Details"
        layeritems =[list(df1.columns.values),df1, formdata['tabledetails']]

        atype = gettypeoflevel(sourcepath,current_node.level+1)
        newlayer = Featurelayers[atype].reset()
    # the map under the selected node map needs to be configured
    # the selected  boundary options need to be added to the layer

        formdata['tabledetails'] = "Click for "+current_node.value +  "\'s "+getchildtype(current_node.type)+" details"
        layeritems = getlayeritems(current_node.children,formdata['tabledetails'] )
        newlayer.add_nodemaps(current_node, atype)

        map = current_node.create_area_map(current_node.getselectedlayers(),"-MAP")
        print("______First selected node",atype,len(current_node.children),len(current_node.getselectedlayers()[0]._children),current_node.value, current_node.level,current_node.file)

        mapfile = current_node.dir+"/"+current_node.file
        DQstats = pd.DataFrame()
        return render_template("Dash0.html", VID_json=VID_json, session=session, formdata=formdata,  group=allelectors , DQstats=DQstats ,mapfile=mapfile)
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


    global environment
    flash('_______ROUTE/canvasscards',session, request.form, current_node.level)


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

                DQstats = pd.DataFrame()
        #    formdata['username'] = session['username']
                formdata['tabledetails'] = getchildtype(current_node.type).upper()+ " Details"
                layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])


                return render_template('Dash0.html', session=session, formdata=formdata, group=allelectors , DQstats=DQstats ,mapfile=mapfile)
            else:
                flash ( "Data file does not match selected constituency!")
                print ( "Data file does not match selected constituency!")
        else:
            flash ( "Data file does not match selected area!")
            print ( "Data file does not match selected area!")
    return redirect(url_for('dashboard'))


# Add children to root

if __name__ in '__main__':
    with app.app_context():
        print("__________Starting up", os.getcwd())
        db.create_all()
        app.run(debug=True)



# 'method' is a function that is present in a file called 'file.py'
