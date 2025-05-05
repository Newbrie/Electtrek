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
from flask import Flask,render_template, request, redirect, session, url_for, send_from_directory, jsonify, flash
import os, sys, math, stat, json , jinja2, random
from os import listdir, system
import glob
from markupsafe import escape
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask import json, get_flashed_messages, request, make_response
from werkzeug.exceptions import HTTPException
from datetime import datetime, timedelta



import sys


sys.path
sys.path.append('/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Electtrek.py')
print(sys.path)

levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

levels = ['country','nation','county','constituency','ward/division','polling district','walk/street','elector/walkleg','walkelector']


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

def getchildtype(parent):
    global levels
    if parent == 'ward' or parent == 'division':
        parent = 'ward/division'
    elif parent == 'walk' or parent == 'street':
        parent = 'walk/street'
    lev = min(levels.index(parent)+1,8)
    return levels[lev]
#    matches = [index for index, x in enumerate(levels) if x.find(parent) > -1  ]
#    return levels[matches[0]+1]

def gettypeoflevel(path,level):
    global levels
    type = levels[level]
    if path.find(" ") > -1:
        type = path.split(" ")[1]
    if type == 'ward/division' and path.find("_ED/") < 0:
        return 'ward'
    elif type == 'ward/division' and path.find("_ED/") >= 0:
        return 'division'
    elif type == 'walk/street'and path.find("/WALKS") < 0:
        return 'street'
    elif type == 'walk/street'and path.find("/WALKS") >= 0:
        return 'walk'

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
  stem = filename.replace("-WDATA", "@@@").replace("-SDATA", "@@@").replace("-MAP", "@@@").replace("-PRINT", "@@@").replace("-WALKS", "@@@").replace("-STREETS", "@@@")
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
    def __init__(self, value, fid, roid):
        global levelcolours
        self.value = normalname(str(value))
        self.children = []
        self.type = 'country'
        self.parent = None
        self.fid = fid
        self.level = 0
        self.file = self.value+"-MAP.html"
        self.dir = self.value
        self.davail = True
        self.col = levelcolours["C"+str(self.level+4)]
        self.tagno = 1
        self.centroid = Point(roid.x,roid.y)
        self.bbox = []
        self.map = {}
        self.source = ""
        self.VI = VIC.copy()
        self.turnout = 0
        self.electorate = 0
        self.target = 1

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
        if electtype == 'ward/division' and ward_div == 'ward':
            electype = 'ward'
        elif electtype == 'ward/division' and ward_div == 'division':
            electype = 'division'
        elif electtype == 'walk/street':
            electype = 'street'
        typechildren = [x for x in self.children if x.type == electtype]
        return typechildren


    def locmappath(self,real):
        global Treepolys
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

        self.map = folium.Map(location=[self.centroid.y, self.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(self.level,5)+0.75)*2)))
        fam_nodes = self.childrenoftype(electtype)
        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]

        for index, limb  in namepoints.iterrows():
            fam_values = [x.value for x in fam_nodes]
            if limb.Name not in fam_values:
                datafid = abs(hash(limb.Name))
                newnode = TreeNode(normalname(limb.Name),datafid, Point(limb.Long,limb.Lat))
                self.davail = True
                egg = self.add_Tchild(newnode, electtype)
                egg.file = subending(egg.file,ending)
                egg.updateParty()
                egg.updateTurnout()
                egg.updateElectorate(limb.ENOP)
                print('______Data nodes',egg.value,egg.fid, egg.electorate,egg.target)
                fam_nodes.append(egg)

    #    self.aggTarget()
#        print('______Data frame:',namepoints, fam_nodes, self.value, self.bbox)
        return fam_nodes

    def create_map_branch(self,electtype):
        global Treepolys
        block = pd.DataFrame()
        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]
        parent_poly = Treepolys[self.level]
        parent_geom = parent_poly[parent_poly["FID"] == self.fid].geometry.values[0]

        bbox = self.bbox
        ChildPolylayer = Treepolys[self.level + 1].cx[bbox[0][0]:bbox[0][1],bbox[1][0] :bbox[1][1]]

#        ChildPolylayer = Treepolys[self.level+1]
#.cx[xmin:xmax, ymin:ymax]
        self.map = folium.Map(location=[self.centroid.y, self.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(self.level+1.2)*2)))

        print("_______CXofTreepoly level", self.level+1, ChildPolylayer.shape)
        print ("________new branch elements in bbox:",self.value,self.level,"**", self.bbox)
    # there are 2-0 (3) relative levels - absolute level are UK(0),nations(1), constituency(2), ward(3)
        index = 0
        i = 0
        fam_nodes = self.childrenoftype(electtype)
        childtable = pd.DataFrame()
        fam_values = [x.value for x in fam_nodes]

        for limb in ChildPolylayer.itertuples(index=False):
            newname = normalname(limb.NAME)
            here = limb.geometry.centroid

            if parent_geom.intersects(limb.geometry) and parent_geom.intersection(limb.geometry).area > 0.0001:
                egg = TreeNode(newname, limb.FID, here)
                egg = self.add_Tchild(egg, electtype)
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

#        print ("_________fam_nodes :", fam_nodes )
        return fam_nodes

    def create_area_map (self,flayers,block,ending):
      self.file = subending(self.file, ending)
      if self.level > 0:
          title = self.parent.value+"-"+self.value+" set at level "+str(self.bbox)+" "+str(self.centroid)
      else:
          title = self.value+" Level "+str(self.level)+ " "+str(self.bbox)+" "+str(self.centroid)
      title_html = '''<h1 style="z-index:1100;color: black;position: fixed;left:100px;">{0}</h1>'''.format(title)
      self.map.get_root().html.add_child(folium.Element(title_html))
# just save the r-1,r,
      if self.level > 1:
          self.map.add_child(flayers[self.level-2].fg)
      if self.level > 0:
          self.map.add_child(flayers[self.level-1].fg)
      self.map.add_child(flayers[self.level].fg)

      self.map.add_child(folium.LayerControl())
# the folium save file reference must be a url
      self.map.add_css_link("electtrekprint","https://newbrie.github.io/Electtrek/static/print.css")
      self.map.add_css_link("electtrekstyle","https://newbrie.github.io/Electtrek/static/style.css")
      self.map.add_js_link("electtrekmap","https://newbrie.github.io/Electtrek/static/map.js")
      target = self.locmappath("")

      self.map.fit_bounds(self.bbox, padding = (0, 0))
      self.map.save(target)
      print("_____saved map file:",target, self.level, self.bbox)

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
# for level = 0 use present
# for level < 5 use geometry
# else use supplied data_bbox
      if self.level < 3:
          print("___Treepolys",Treepolys[0],Treepolys[5], self.value,self.level, self.fid )
          pfile = Treepolys[self.level]
          pb = pfile[pfile['FID']==self.fid]
          swne = pb.geometry.total_bounds
          swne = [swne[1]+(swne[3]-swne[1])/5,swne[0]+(swne[2]-swne[0])/5,swne[3]-(swne[3]-swne[1])/5,swne[2]-(swne[2]-swne[0])/5]
          roid = pb.dissolve().centroid
          swne =[(float('%.6f'%(swne[0])),float('%.6f'%(swne[1]))),(float('%.6f'%(swne[2])),float('%.6f'%(swne[3])))]
# minx, miny, maxx, maxy
          print("_______Bbox swnemap",swne, pb, self.fid, self.value, self.level)
      elif self.level < 5:
          pfile = Treepolys[self.level]
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
            child_node.file = child_node.value+"-MAP.html"
        elif etype == 'street':
            child_node.dir = self.dir+"/STREETS"
            child_node.file = self.value+"-"+child_node.value+"-PRINT.html"
        elif etype == 'walk':
            child_node.dir = self.dir+"/WALKS"
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

    def ping_node(self, path,electrollfile):
        global Treepolys
        global levels
        global allelectors
        global PDelectors
        global current_node

        path.split(" ").pop()
        route = path.replace("/STREETS","").replace("/WALKS","").replace(".html","").replace(".HTML","")
        route = subending(route, "")
        steps = route.split("/")
        last = steps.pop() #eg KA-SMITH_STREET
        steps.append(last.split("-").pop()) #eg SMITH_STREET
        steps.reverse() # make the top the first node
        steps.pop() # MapRoot is already selected as the first node
        print("____ping steps", path, route,steps)
        node = self
        block = pd.DataFrame()
        frames = []

        while steps:
            next = steps.pop()
            nameoptions = [x.value for x in node.children]
            if not steps:
                next = next.split("-").pop()
            print("____Ping Loop Test:", next, steps, nameoptions)
            if next in nameoptions:
                for chip in [x for x in node.children if x.value == next]:
                    node = chip
                    print("____ EXISTNG NODE FOUND  ",node.type,node.value,node.file)
                    break
            if node.level < 4:
                print("____Treepolys Test",node.value, node.level,Treepolys[5] )
                if node.level+1 >= Treepolys[5] :
                    add_boundaries(gettypeoflevel(path,node.level+1))
                ChildPolylayer = Treepolys[node.level+1]
                [[xmin, ymin], [xmax, ymax]] = node.get_bounding_box(block)[0]
                ReducedPolylayer = ChildPolylayer.cx[xmin:xmax, ymin:ymax]
                for index, limb in ReducedPolylayer.iterrows():
                    newname = normalname(limb.NAME)
        #            if  newname != "UNITED_KINGDOM":
                    print ("________child of",node.value,node.level)
                    roid = node.get_bounding_box(block)[1]
                    if newname == next:
                        mtype = gettypeoflevel(path,node.level+1)
                        possnode = TreeNode(next,limb.FID, roid)
                        node.add_Tchild(possnode,mtype)
                        node = possnode
                        print("____ NEW MAP NODE CREATED  ",mtype,node.value,node.fid,node.file)
                        break
            elif node.level == 4:
                if len(node.children) == 0 and len(allelectors) == 0 and electrollfile != "":
                    allelectors0 = pd.read_csv(config.workdirectories['workdir']+"/"+ electrollfile, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
                    node.parent.source = electrollfile
                    alldf0 = pd.DataFrame(allelectors0, columns=['Postcode', 'ENOP','Long', 'Lat'])
                    alldf1 = alldf0.rename(columns= {'ENOP': 'Popz'})
        # we group electors by each polling district, calculating mean lat , long for PD centroids and population of each PD for node.electorate
                    g = {'Popz':'count'}
                    alldf = alldf1.groupby(['Postcode']).agg(g).reset_index()
                    alldf['Popz'] = alldf['Popz'].rdiv(1)

                    allelectors = allelectors0.merge(alldf, on='Postcode',how='left' )
                    print("____- Popz allelectors:",len(alldf), len(allelectors), len(allelectors0))
                    pfile = Treepolys[node.level]
                    Level3boundary = pfile[pfile['FID']==node.fid]
                    PDs = set(allelectors.PD.values)
                    print("____- PDs:",PDs)
                    for PD in PDs:
                        PDelectors = getblock(allelectors,'PD',PD)
                        maplongx = PDelectors.Long.values[0]
                        maplaty = PDelectors.Lat.values[0]

                    # for all PDs - pull together all PDs which are within the Conboundary constituency boundary
                        if Level3boundary.geometry.contains(Point(float('%.6f'%(maplongx)),float('%.6f'%(maplaty)))).item():
                            Area = normalname(Level3boundary['NAME'].values[0])
                            PDelectors['Area'] = Area

                            x = PDelectors.Long.values
                            y = PDelectors.Lat.values


                            kmeans_dist_data = list(zip(x, y))

    #                        walkset = min(math.ceil(PDelectors.shape[0]/int(ElectionSettings['walksize'])),35)
                            walkset = min(math.ceil(ElectionSettings['teamsize']),35)

                            kmeans = KMeans(n_clusters=walkset)
                            kmeans.fit(kmeans_dist_data)

                            klabels1 = np.char.mod('C%d', kmeans.labels_)
                            klabels = klabels1.tolist()

                            PDelectors.insert(0, "WalkName", klabels)
                            frames.append(PDelectors)

                    allelectors = pd.concat(frames)
                else:
                    PDelectors = getblock(allelectors,'PD',node.value)
                    if gettypeoflevel(path,node.level+1) == 'polling district':
                        PDPtsdf0 = pd.DataFrame(PDelectors, columns=['PD', 'ENOP','Long', 'Lat'])
                        PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
    # we group electors by each polling district, calculating mean lat , long for PD centroids and population of each PD for node.electorate
                        g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                        PDPtsdf = PDPtsdf1.groupby(['Name']).agg(g).reset_index()
                        WardPDnodelist = node.create_data_branch('polling district',PDPtsdf.reset_index(),"-WALKS")
            elif node.level == 5:
                PDelectors = getblock(allelectors,'PD',node.value)
                if gettypeoflevel(path,node.level+1) == 'street':
                    StreetPts = [(x[0],x[1],x[2],x[3]) for x in PDelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                    Streetdf0 = pd.DataFrame(StreetPts, columns=['Name', 'Long', 'Lat','ENOP'])
                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                    Streetdf = Streetdf0.groupby(['Name']).agg(g).reset_index()
                    streetnodelist = node.create_data_branch('street',Streetdf.reset_index(),"-PRINT")
                elif gettypeoflevel(path,node.level+1) == 'walk':
                    walkPts = [(x[0],x[1],x[2], x[3]) for x in PDelectors[['WalkName','Long','Lat', 'ENOP']].drop_duplicates().values]
                    walkdf0 = pd.DataFrame(walkPts, columns=['WalkName', 'Long', 'Lat', 'ENOP'])
                    walkdf1 = walkdf0.rename(columns= {'WalkName': 'Name'})
                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                    walkdfs = walkdf1.groupby(['Name']).agg(g).reset_index()
                    walknodelist = node.create_data_branch('walk',walkdfs.reset_index(),"-PRINT")
            elif node.level == 6 and gettypeoflevel(path,node.level+1) == 'walkleg':
                PDelectors = getblock(allelectors,'Area',node.parent.parent.value)
                walk_name = node.parent.value+"-"+node.value
                walkelectors = getblock(PDelectors, 'WalkName',node.value)
                StreetPts = [(x[0],x[1],x[2],x[3]) for x in PDelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
                Streetdf0 = pd.DataFrame(StreetPts, columns=['Name', 'Long', 'Lat','ENOP'])
                g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
                Streetdf = Streetdf0.groupby(['Name']).agg(g).reset_index()
                streetnodelist = node.create_data_branch('street',Streetdf.reset_index(),"-PRINT")
        print("____ping end:", node.value, node.level,next, steps, nameoptions)
        return node

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

def add_boundaries(shelf):
    global Treepolys
    global Con_Results_data

    if shelf == 'country':
        print("__________reading World_Countries_(Generalized)= [0]")
        World_Bound_layer = gpd.read_file(config.workdirectories['bounddir']+"/"+'World_Countries_(Generalized)_9029012925078512962.geojson', bbox=(-7.57216793459, 49.959999905, 1.68153079591, 58.6350001085), driver='GeoJSON')
        World_Bound_layer = World_Bound_layer.rename(columns = {'COUNTRY': 'NAME'})
        UK_Bound_layer = World_Bound_layer[World_Bound_layer['FID'] == 238]
        UK_Bound_layer['LAT'] = 54.4361
        UK_Bound_layer['LONG'] = -4.5481
        Treepolys[0] = UK_Bound_layer
        Treepolys[5] = 1
        return UK_Bound_layer
    elif shelf == 'nation':
        print("__________reading Countries_December_2021_UK_BGC_2022_-7786782236458806674= [1]")
        Nation_Bound_layer = gpd.read_file(config.workdirectories['bounddir']+"/"+'Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson',driver='GeoJSON')
        Nation_Bound_layer = Nation_Bound_layer.rename(columns = {'OBJECTID': 'FID'})
        Nation_Bound_layer = Nation_Bound_layer.rename(columns = {'CTRY21NM': 'NAME'})
        Treepolys[1] = Nation_Bound_layer
        Treepolys[5] = 2
        return Nation_Bound_layer
    elif shelf == 'county':
        print("__________reading Counties_and_Unitary_Authorities_May_2023_UK_BGC_ = [2]")
        County_Bound_layer = gpd.read_file(config.workdirectories['bounddir']+"/"+'Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson',driver='GeoJSON')
        County_Bound_layer = County_Bound_layer.rename(columns = {'CTYUA23NM': 'NAME'})
        Treepolys[2] = County_Bound_layer
        Treepolys[5] = 3
        return County_Bound_layer
    elif shelf == 'constituency':
        print("__________reading Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK= [3]")
        Con_Bound_layer = gpd.read_file(config.workdirectories['bounddir']+"/"+'Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson',driver='GeoJSON')
        Con_Bound_layer = Con_Bound_layer.rename(columns = {'PCON24NM': 'NAME'})
        Treepolys[3] = Con_Bound_layer
        Treepolys[5] = 4
        return Con_Bound_layer
    elif shelf == 'ward' or shelf == 'division' or shelf == 'ward/division':
        if shelf == 'division':
            print("__________reading County_Electoral_Division_May_2023_Boundaries = [4]")
            Division_Bound_layer = gpd.read_file( config.workdirectories['bounddir']+"/"+'County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson',driver='GeoJSON')
            Division_Bound_layer = Division_Bound_layer.rename(columns = {'CED23NM': 'NAME'})
            Treepolys[4] = Division_Bound_layer
            Treepolys[5] = 5
            return Division_Bound_layer
        else:
            print("__________reading Wards_May_2024_Boundaries = [4]")
            Ward_Bound_layer = gpd.read_file(config.workdirectories['bounddir']+"/"+'Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson',driver='GeoJSON')
            Ward_Bound_layer = Ward_Bound_layer.rename(columns = {'WD24NM': 'NAME'})
            Treepolys[4] = Ward_Bound_layer
            Treepolys[5] = 5
            return Ward_Bound_layer



class FGlayer:
    def __init__ (self, id, name):
        self.fg = folium.FeatureGroup(name=name, overlay=True, control=True, show=True)
        self.name = name
        self.id = id



    def layeradd_walkshape (self,herenode,type,datablock):
        global Treepolys
        global levelcolours
        global allelectors

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
            showmessageST = "showMore(&#39;/PDshowST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
#            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,herenode.source, herenode.dir+"/"+herenode.file)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limbX['UPDOWN'] = uptag1 +"<br>"+ downST+"<br>"+ downWK
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno, gdf)
        elif type == 'walk':
            showmessage = "showMore(&#39;/showmore/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('walk'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
            downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limbX['UPDOWN'] =  uptag1 +"<br>"+ downtag+"<br>"
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)


#        herenode.tagno = len(self.fg._children)+1
        numtag = str(herenode.tagno)+" "+str(herenode.value)
        num = str(herenode.tagno)
        tag = str(herenode.value)
        typetag = "from <br>"+str(herenode.type)+": "+str(herenode.value)+"<br> move :"
        here = [float('%.6f'%(herenode.centroid.y)),float('%.6f'%(herenode.centroid.x))]
        print("______addingPoly:",herenode.value, limbX.NAME, here)
        pathref = herenode.dir+"/"+herenode.file
        mapfile = '/map/'+pathref

        limb = limbX.iloc[[0]].__geo_interface__  # Ensure this returns a GeoJSON dictionary for the row

        # Ensure 'properties' exists in the GeoJSON and add 'col'
        print("GeoJSON Convex creation:", limb)
        if 'properties' not in limb:
            limb['properties'] = {}

        # Now you can use limb_geojson as a valid GeoJSON feature
        print("GeoJSON Convex Hull Feature:", limb)

#            self.children.append(herenode)
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
        ).add_to(self.fg)

        self.fg.add_child(folium.Marker(
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
        print("________Layer map polys",herenode.value,herenode.level,self.fg._children)
        return self.fg._children

    def layeradd_nodemaps (self,herenode,type):
        global Treepolys
        global levelcolours
        global allelectors
        global Con_Results_data
        for c in [x for x in herenode.children if x.type == type]:
            print("______Display children:",herenode.value, herenode.level,type)
#            layerfids = [x.fid for x in self.fg._children if x.type == type]
#            if c.fid not in layerfids:
            if c.level+1 <= Treepolys[5]:
                pfile = Treepolys[c.level]
                limbX = pfile[pfile['FID']==c.fid]
                limbX['col'] = c.col

                if herenode.level == 0:
                    downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"COUNTIES",12)
#                    res = "<p  width=50 id='results' style='font-size: {0}pt;color: gray'> </p>".format(12)
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"  + downtag
#                    c.tagno = len(self.fg._children)+1
                    mapfile = "/map/"+c.dir+"/"+c.file
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
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ wardreporttag + divreporttag+"<br>"+ downconstag
#                    c.tagno = len(self.fg._children)+1
                    mapfile = "/map/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 2:
                    downwardmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" ward", c.value,"ward")
                    downdivmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" division", c.value,"division")
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
                    downwardstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downwardmessage,"WARDS",12)
                    downdivstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downdivmessage,"DIVS",12)
                    uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ downwardstag + " " + downdivstag
#                    c.tagno = len(self.fg._children)+1
                    mapfile = "/map/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 3:
                    downPDmessage = "moveDown(&#39;/downPDbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype('ward/division'))
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,herenode.type)
                    PDbtn = "<input type='submit' form='uploadPD' value='Polling Districts' class='btn btn-norm' onclick='{0}'/>".format(downPDmessage)
                    upload = "<form id='uploadPD' action= '/downPDbut/{0}' method='GET'><input type='file' name='importfile' placeholder={2} style='font-size: {1}pt;color: gray' enctype='multipart/form-data'></input></form>".format(c.dir+"/"+c.file,12,c.parent.source)
                    uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                    limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ upload+PDbtn
#                    c.tagno = len(self.fg._children)+1
                    pathref = c.dir+"/"+c.file
                    mapfile = '/map/'+pathref
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
                ).add_to(self.fg)

                pathref = c.dir+"/"+c.file
                mapfile = '/map/'+pathref


                self.fg.add_child(folium.Marker(
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


        print("________Layer map polys",herenode.value,herenode.level,len(self.fg._children), len(Featurelayers[herenode.level].fg._children))

        return herenode

    def layeradd_nodemarks (self,herenode,type):
        global Treepolys
        global levelcolours
        global allelectors
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
            mapfile = '/map/'+pathref

            print("______Display childrenx:",c.value, c.level,type,c.centroid )

            self.fg.add_child(folium.Marker(
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


        print("________Layer map points",herenode.value,herenode.level,self.fg._children)

        return herenode

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
Featurelayers = []


Featurelayers.append(FGlayer(id=1,name='Nation Boundaries'))
Featurelayers.append(FGlayer(id=2,name='County Boundaries'))
Featurelayers.append(FGlayer(id=3,name='Constituency Boundaries'))
Featurelayers.append(FGlayer(id=4,name='Ward/Division Boundaries'))
Featurelayers.append(FGlayer(id=5,name='Polling District Markers'))
Featurelayers.append(FGlayer(id=6,name='Walk/Street Markers'))
Featurelayers.append(FGlayer(id=7,name='Street Electors'))
Featurelayers.append(FGlayer(id=8,name='Results'))
Featurelayers.append(FGlayer(id=9,name='Targets'))
Featurelayers.append(FGlayer(id=10,name='Data'))
Featurelayers.append(FGlayer(id=11,name='Special Markers'))

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
MapRoot = TreeNode("UNITED_KINGDOM",238, roid)
MapRoot.dir = "UNITED_KINGDOM"
MapRoot.file = "UNITED_KINGDOM-MAP.html"
Treepolys = [[],[],[],[],[],0]
current_node = MapRoot
add_boundaries('country')
add_boundaries('nation')

formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"

layeritems = getlayeritems(MapRoot.create_map_branch('nation'), formdata['tabledetails'])

Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
Featurelayers[current_node.level].layeradd_nodemaps(current_node, 'nation')

map = MapRoot.create_area_map(Featurelayers,allelectors,"-MAP")
mapfile = current_node.dir+"/"+current_node.dir

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
    if name in ElectionSettings:
        ElectionSettings[name] = value
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid constant name"), 400

@app.route("/index", methods=['POST', 'GET'])
def index():
    global Treepolys
    global MapRoot
    global current_node

    current_node = MapRoot

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
    global Treepolys
    global Featurelayers
    global environment
    global layeritems
    global ElectionSettings

    if 'username' in session:
        flash("User already logged in:", session['username'])
        print("_______ROUTE/Already logged in:", session['username'])
        return redirect(url_for('dashboard'))
    # Collect info from forms in the login db
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

        if 'next' in session:
            next = session['next']
            print("_______ROUTE/login next found", next)
            return next

        print("_______ROUTE/login User found", username)

        # Debugging session user ID
        print(f"🧍 current_user.id: {current_user.id if current_user.is_authenticated else 'Anonymous'}")
        print(f"🧪 Logging in user with ID: {current_user.id}")
        print("🧪 session keys after login:", dict(session))
        next = request.args.get('next')
        current_node = MapRoot

        return redirect(url_for('firstpage'))

    else:
        flash('Not logged in!')
        return render_template("index.html")


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
    global Treepolys
    global Featurelayers
    global formdata
    global ElectionSettings

    mapfile  = current_node.dir+"/"+current_node.file
    if 'username' in session:
        flash('_______ROUTE/dashboard'+ session['username'] + ' is already logged in ')
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
    global MapRoot
    global current_node
    global allelectors
    global ElectionSettings
    global formdata
    global Treepolys
    global Featurelayers
    global environment
    global levels
    global layeritems
    global ward_div

    formdata = {}
# a down button on a node has been selected on the map, so the new map must be displayed with new down options

# the selected node has to be found from the selected button URL

    current_node = current_node.ping_node(path,current_node.source)
    path = path.replace("/STREETS","").replace("/WALKS","")
    atype = gettypeoflevel(path,current_node.level+1)
# the map under the selected node map needs to be configured
    print("_________selected node",atype,current_node.value, current_node.level,current_node.file)
# the selected  boundary options need to be added to the layer
    add_boundaries(atype)
    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
    layeritems = getlayeritems(current_node.create_map_branch(atype),formdata['tabledetails'] )
    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
    Featurelayers[current_node.level].layeradd_nodemaps(current_node, atype)

    map = current_node.create_area_map(Featurelayers,allelectors,"-MAP")
    print("________child nodes created",len(current_node.children))

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
    global Treepolys
    global Featurelayers
    global environment
    global levels
    global layeritems
    global ElectionSettings
    global formdata


    formdata = {}
# transfering to another any other node with siblings listed below
    previous_node = current_node
    current_node = MapRoot.ping_node(path,current_node.source)
    mapfile = current_node.dir +"/"+ current_node.file
    print("____Route/transfer:",previous_node.value,current_node.value, path)
    if current_node.level < 5:
        redirect(url_for('downbut',path=mapfile))
    else:
        formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
        layeritems = getlayeritems(current_node.parent.children,formdata['tabledetails'] )
        return   redirect(url_for('map',path=mapfile))

    return redirect(url_for('map',path=mapfile))


@app.route('/downPDbut/<path:path>', methods=['GET','POST'])
@login_required
def downPDbut(path):
    global Treepolys
    global current_node
    global Featurelayers
    global MapRoot
    global ElectionSettings
    global allelectors
    global filename
    global layeritems


    if request.method == 'GET':
        print ("_________Requestformfile",request.values['importfile'])
        flash ("_________Requestformfile"+request.values['importfile'])
        electrollfile = request.values['importfile']
        current_node = current_node.ping_node(path,electrollfile)
        mapfile = current_node.dir+"/"+current_node.file

        Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)

        print("_______displayed PD markers",Featurelayers[current_node.level].fg._children)

        PDPtsdf0 = pd.DataFrame(allelectors, columns=['PD', 'ENOP','Long', 'Lat'])
        PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
        g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
        PDPtsdf = PDPtsdf1.groupby(['Name']).agg(g).reset_index()
        print ("______PDPtsdf:",PDPtsdf)

        WardPDnodelist = current_node.create_data_branch('polling district',PDPtsdf.reset_index(),"-WALKS")
# if there is a selected file , then allelectors will be full of records
        for PD_node in WardPDnodelist:
            PDnodeelectors = getblock(allelectors,'PD',PD_node.value)
            PDPtsdf0 = pd.DataFrame(PDnodeelectors, columns=['StreetName', 'ENOP','Long', 'Lat'])
            PDPtsdf1 = PDPtsdf0.rename(columns= {'StreetName': 'Name'})
            print ("______PDPtsdf1:",PDPtsdf1)
            g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
            PDPtsdf = PDPtsdf1.groupby(['Name']).agg(g).reset_index()
            Featurelayers[current_node.level].layeradd_walkshape(PD_node, 'polling district',PDPtsdf)
            print("_______new PD Display node",PD_node,"|", PDPtsdf)

#            areaelectors = getblock(allelectors,'Area',current_node.value)

        if len(allelectors) == 0 or len(Featurelayers[current_node.level].fg._children) == 0:
            flash("Can't find any elector data for this Area.")
        else:
            map = current_node.create_area_map(Featurelayers,allelectors,"-MAP")
            flash("________PDs added  :  "+str(len(Featurelayers[current_node.level].fg._children)))
            print("________PDs added  :  "+str(len(Featurelayers[current_node.level].fg._children)))

        allelectorscopy = allelectors.copy()
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
            street_node = MapRoot.ping_node(pathval,electrollfile)
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
            allelectors = allelectorscopy.merge(VIelectors, on='ENOP',how='left' )
            print("______merged and imported data",allelectors.columns, allelectors.head())
            allelectors.to_excel(path2+"/"+merge)
        else:
            print("______NO Data found to be imported ",full_revamped)


    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
    layeritems = getlayeritems(current_node.childrenoftype('polling district'),formdata['tabledetails'] )
    mapfile = current_node.dir+"/"+current_node.file
    return   redirect(url_for('map',path=mapfile))



@app.route('/STupdate/<path:path>', methods=['GET','POST'],strict_slashes=False)
@login_required
def STupdate(path):
    global Treepolys
    global current_node
    global Featurelayers

    global allelectors
    global PDelectors
    global environment
    global filename
    global layeritems
    global ElectionSettings

#    steps = path.split("/")
#    filename = steps.pop()
#    current_node = selected_childnode(current_node,steps[-1])
    fileending = "-SDATA.html"
    if path.find("/STREETS") < 0:
        fileending = "-WDATA.html"


    current_node = MapRoot.ping_node(path,current_node.parent.source)
    path = path.replace("/STREETS","").replace("/WALKS","")
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
                    print("_____columns:",PDelectors.columns)
                    # Find the row where ENO matches electID
                    selected = PDelectors.query("ENOP == @electID")
                    changefields.loc[i,'Path'] = street_node.dir+"/"+street_node.file
                    changefields.loc[i,'Lat'] = street_node.centroid.y
                    changefields.loc[i,'Long'] = street_node.centroid.x
                    changefields.loc[i,'ENOP'] = electID
                    changefields.loc[i,'ElectorName'] = ElectorName
                    if not selected.empty:
                        # Update only if viResponse is non-empty
                        if VI_value:
                            PDelectors.loc[selected.index, "VI"] = VI_value
                            street_node.updateVI(VI_value)
                            changefields.loc[i,'VI'] = VI_value
                        if Notes_value:
                            PDelectors.loc[selected.index, "Notes"] = Notes_value
                            changefields.loc[i,'Notes'] = Notes_value
                            print(f"Updated elector {electID} with VI = {VI_value} and Notes = {Notes_value}")
                            print("ElectorVI", PDelectors.loc[selected.index, "ENOP"], PDelectors.loc[selected.index, "VI"])

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
    print("_____Where are we: ", current_node.value, current_node.type, PDelectors.columns)

    street = current_node.value
    electorwalks = pd.DataFrame()

    if current_node.type == 'street':
        electorwalks = getblock(PDelectors, 'StreetName',current_node.value)
    elif current_node.type == 'walk':
        electorwalks = getblock(PDelectors,'WalkName',current_node.value)

    if electorwalks.empty:
        print("⚠️ Error: electorwalks DataFrame is empty!", current_node.value)
        return jsonify({"message": "Success", "file": url_for('map', path=mapfile)})

    STREET_ = current_node.value

    Postcode = electorwalks.loc[0].Postcode

    walk_name = current_node.parent.value+"-"+current_node.value
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


@app.route('/PDshowST/<path:path>', methods=['GET','POST'])
@login_required
def PDshowST(path):
    global Treepolys
    global current_node
    global Featurelayers

    global allelectors
    global PDelectors
    global environment
    global filename
    global layeritems

    def firstnameinlist(name,list):
        posn = list.index(name)
        return list[posn]

    steps = path.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
# now pointing at the STREETS.html node containing a map of street markers

    current_node.file = subending(current_node.file,"-STREETS")
    PD_node = current_node
    PDelectors = getblock(allelectors, 'PD',current_node.value)
    if request.method == 'GET':

    # we only want to plot with single streets , so we need to establish one street record with pt data to plot

        StreetPts = [(x[0],x[1],x[2],x[3]) for x in PDelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
        Streetdf0 = pd.DataFrame(StreetPts, columns=['Name', 'Long', 'Lat','ENOP'])

        g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
        Streetdf = Streetdf0.groupby(['Name']).agg(g).reset_index()


        Featurelayers[PD_node.level].fg = folium.FeatureGroup(id=str(PD_node.level+1),name=Featurelayers[PD_node.level].name, overlay=True, control=True, show=True)
        streetnodelist = PD_node.create_data_branch('street',Streetdf.reset_index(),"-PRINT")
        Featurelayers[PD_node.level].layeradd_nodemarks(PD_node, 'street')

        if len(allelectors) == 0 or len(Featurelayers[PD_node.level].fg._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________streets added  :  "+str(len(Featurelayers[PD_node.level].fg._children)))
            print("________streets added  :  "+str(len(Featurelayers[PD_node.level].fg._children)))


        for street_node in PD_node.childrenoftype('street'):
              street = street_node.value

              electorwalks = getblock(PDelectors, 'StreetName',street_node.value)

              STREET_ = street_node.value

              Postcode = electorwalks.loc[0].Postcode

              walk_name = street_node.parent.value+"-"+street_node.value
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
              results_filename = walk_name+"-PRINT.html"
              datafile = street_node.dir+"/"+walk_name+"-SDATA.html"
              mapfile = street_node.dir+"/"+street_node.file
              electorwalks = electorwalks.fillna("")

#              These are the street nodes which are the street data collection pages


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
        map = PD_node.create_area_map(Featurelayers,PDelectors,"-STREETS")
    mapfile = PD_node.dir+"/"+PD_node.file
    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
    layeritems = getlayeritems(PD_node.childrenoftype('street'),formdata['tabledetails'])

    print ("________Heading for the Streets in PD :  ",PD_node.value, PD_node.file)
    if len(Featurelayers[PD_node.level].fg._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers[PD_node.level].fg._children)))

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/PDshowWK/<path:path>', methods=['GET','POST'])
@login_required
def PDshowWK(path):
    global Treepolys
    global current_node
    global Featurelayers

    global allelectors
    global PDelectors
    global environment
    global filename
    global layeritems

    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

    steps = path.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])

    current_node.file = subending(current_node.file,"-WALKS")
    PD_node = current_node
    PDelectors = getblock(allelectors, 'PD',PD_node.value)
    if request.method == 'GET':
# if there is a selected file , then allelectors will be full of records
        print("________PDMarker",PD_node.type,"|", PD_node.dir, "|",PD_node.file)

        walks = PDelectors.WalkName.unique()
        walkPts = [(x[0],x[1],x[2], x[3]) for x in PDelectors[['WalkName','Long','Lat', 'ENOP']].drop_duplicates().values]
        walkdf0 = pd.DataFrame(walkPts, columns=['WalkName', 'Long', 'Lat', 'ENOP'])
        walkdf1 = walkdf0.rename(columns= {'WalkName': 'Name'})
        print("________walkdf1  :  ",walkdf1)
        g = {'Lat':'mean','Long':'mean', 'ENOP':'count'}
        walkdfs = walkdf1.groupby(['Name']).agg(g).reset_index()
        print ("____________walks",walkdfs)

# clear down the layer to which we want to add walks

        Featurelayers[PD_node.level].fg = folium.FeatureGroup(id=str(PD_node.level+1),name=Featurelayers[PD_node.level].name, overlay=True, control=True, show=True)
    #  add the walk nodes
        walknodelist = PD_node.create_data_branch('walk',walkdfs.reset_index(),"-PRINT")

    #        map = PD_node.create_area_map(Featurelayers,PDelectors)
    #        mapfile = PD_node.dir+"/"+PD_node.file

# for each walk node, add a walk node convex hull to the walk_node parent layer (ie PD_node.level+1)
        for walk_node in walknodelist:
          print("________WalkMarker",walk_node.type,"|", walk_node.dir, "|",walk_node.file)

          walk = walk_node.value
          walk_name = walk_node.parent.value+"-"+walk_node.value
          walkelectors = getblock(PDelectors, 'WalkName',walk_node.value)

          geometry = gpd.points_from_xy(walkelectors.Long.values,walkelectors.Lat.values, crs="EPSG:4326")
        # create a geo dataframe for the Walk Map
          geo_df1 = gpd.GeoDataFrame(
            walkelectors, geometry=geometry
            )

        # Create a geometry list from the GeoDataFrame
          geo_df1_list = [[point.xy[1][0], point.xy[0][0]] for point in geo_df1.geometry]
          CL_unique_list = pd.Series(geo_df1_list).drop_duplicates().tolist()

          StreetPts = [(x[0],x[1],x[2],x[3]) for x in walkelectors[['StreetName','Long','Lat','ENOP']].drop_duplicates().values]
          streetdf0 = pd.DataFrame(StreetPts, columns=['StreetName', 'Long', 'Lat','ENOP'])
          streetdf1 = streetdf0.rename(columns= {'StreetName': 'Name'})
          g = {'Lat':'mean','Long':'mean','ENOP':'count'}
          streetdf = streetdf1.groupby(['Name']).agg(g).reset_index()

          print ("____________walklegs",streetdf)
          streetnodelist = walk_node.create_data_branch('walkleg',streetdf,"-PRINT")
#
          type_colour = allowed[walk_node.value]

    #      marker_cluster = MarkerCluster().add_to(Walkmap)
          # Iterate through the street-postcode list and add a marker for each unique lat long, color-coded by its Cluster.

          if len(streetdf.reset_index()) > 0:
              Featurelayers[current_node.level].layeradd_walkshape(walk_node, 'walk',streetdf)
              Featurelayers[current_node.level+1].layeradd_nodemarks(walk_node, 'walkleg')
              print("_______new Walk Display node",walk_node,"|", Featurelayers[PD_node.level].fg._children)


#              for walkleg in walk_node.childrenoftype('walkleg'):
                    # in the Walk map add Street-postcode groups to the walk map with controls to go back up to the PD map or down to the Walk addresses
#                print("________WalklegMarker",walkleg.type,"|", walkleg.dir, "|",walkleg.file)
#                downtag = "<form action= '/downwalkbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(walkleg.dir+"/"+walkleg.file,"Streets",12)
#                uptag = "<form action= '/upwalkbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(walkleg.dir+"/"+walkleg.file,"Walks",12)
            #            Wardboundary['UPDOWN'] = "<br>"+walk_node.value+"<br>"+ uptag +"<br>"+ downtag
            #        c.tagno = len(self.children)+1
#                Postcode = walkelectors.loc[0].Postcode

              walk_name = walk_node.parent.value+"-"+walk_node.value
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
              prodstats['walks'] =  len(walks)
              prodstats['streets'] = streets
              prodstats['housedensity'] = housedensity
              prodstats['leafhrs'] = round(leafhrs,2)
              prodstats['canvasshrs'] = round(canvasshrs,2)

#                  walkelectors['ENOP'] =  walkelectors['PD']+"-"+walkelectors['ENO']+ walkelectors['Suffix']*0.1
              target = walk_node.locmappath("")
              results_filename = walk_name+"-PRINT.html"

              datafile = walk_node.dir+"/"+walk_name+"-WDATA.html"
              mapfile = walk_node.dir+"/"+walk_node.file

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

        map = PD_node.create_area_map(Featurelayers,PDelectors, "-WALKS")

        mapfile = PD_node.dir+"/"+PD_node.file
        formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
        layeritems = getlayeritems(PD_node.childrenoftype('walk'), formdata['tabledetails'])


        if len(PDelectors) == 0 or len(Featurelayers[PD_node.level].fg._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________walks added  :  "+str(len(Featurelayers[PD_node.level].fg._children)))
            print("________walks added  :  "+str(len(Featurelayers[PD_node.level].fg._children)))

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
    add_boundaries('constituency')
    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
    layeritems = getlayeritems(current_node.create_map_branch('constituency'),formdata['tabledetails'])
    for group_node in current_node.childrenoftype('constituency'):
        add_boundaries('ward')

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


    steps = path.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file

    flash('_______ROUTE/divreport')
    print('_______ROUTE/divreport')

    i = 0
    layeritems = pd.DataFrame()
    alreadylisted = []
    add_boundaries('constituency')
    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s' details"
    layeritems = getlayeritems(current_node.create_map_branch('constituency'),formdata['tabledetails'])

    for group_node in current_node.childrenoftype('division'):
        add_boundaries('division')

        layeritems = getlayeritems(group_node.create_map_branch('division'),formdata['tabledetails'])

        for item in Featurelayers[group_node.level].fg._children:
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
    global Treepolys
    global Featurelayers
    global environment
    global layeritems



    flash('_______ROUTE/upbut',path)
    print('_______ROUTE/upbut',path, current_node.value)
    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
# the selected node has to be found from the selected button URL
#
#    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
    layeritems = getlayeritems(current_node.parent.childrenoftype(gettypeoflevel(path,current_node.level)),formdata['tabledetails'])

    if current_node.level > 0:
        current_node = current_node.parent
    mapfile = current_node.dir+"/"+current_node.file
# the selected node boundary options need to be added to the layer

    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['importfile'] = ""

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
        return redirect(url_for('dashboard'))

@app.route('/map/<path:path>', methods=['GET','POST'])
@login_required
def map(path):
    global current_node
    steps = path.split("/")
    last = steps.pop()
    current_node = selected_childnode(current_node,last)
    flash ("_________ROUTE/map:"+path)
    print ("_________ROUTE/map:",path, current_node.dir)

    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
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

    formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
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
        formdata['tabledetails'] = "Click for "+getchildtype(current_node.type)+ "\'s details"
        print('_______ElectionSettings:',ElectionSettings)
        layeritems = getlayeritems(current_node.childrenoftype(gettypeoflevel(current_node.dir,current_node.level+1)),formdata['tabledetails'])

        return render_template("Dash0.html", session=session, formdata=formdata, group=allelectors ,DQstats=DQstats ,mapfile=mapfile)
    return ""

@app.route('/normalise', methods=['POST','GET'])
@login_required
def normalise():
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
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
    global Treepolys
    global Featurelayers
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
    pfile = Treepolys[current_node.level+1]
    polylocated = electorwalks.find_boundary(pfile,here)

    popuptext = '<ul style="font-size: {4}pt;color: gray;" >Lat: {0} Long: {1} Postcode: {2} Name: {3}</ul>'.format(lookuplatlong.Lat.values[0],lookuplatlong.Long.values[0], postcodeentry, polylocated['NAME'].values[0], 12)
    here1 = [here.y, here.x]
    # in the PD map add PD-cluster walks to the PD map with controls to go back up to the Ward map or down to the Walk map
    Featurelayers[8].fg.add_child(
      folium.Marker(
         location=here1,
         popup = popuptext,
         icon=folium.Icon(color = "yellow",  icon='search'),
         )
         )

    current_node.map.add_child(Featurelayers[4].fg)
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
    global Treepolys
    global Featurelayers
    global environment
    global layeritems
    print("🔍 Accessed /firstpage")
    print("🧪 current_user.is_authenticated:", current_user.is_authenticated)
    print("🧪 current_user:", current_user)
    print("🧪 session keys:", list(session.keys()))
    print("🧪 full session content:", dict(session))

    if current_user.is_authenticated:
        formdata = {}
        formdata['country'] = "UNITED_KINGDOM"
        flash('_______ROUTE/firstpage')
        print('_______ROUTE/firstpage')
        formdata['importfile'] = "SCC-CandidateSelection.xlsx"
        if len(request.form) > 0:
            formdata['importfile'] = request.files['importfile'].filename
        df1 = pd.read_excel(config.workdirectories['workdir']+"/"+formdata['importfile'])
        formdata['tabledetails'] = "Candidates File "+formdata['importfile']+" Details"
        layeritems =[list(df1.columns.values),df1, formdata['tabledetails']]
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
    global Treepolys
    global Featurelayers
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
