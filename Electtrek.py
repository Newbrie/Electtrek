from canvasscards import prodcards, getblock, find_boundary
import electorwalks
#import prodwalks, locmappath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
import normalised
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
from shapely import crosses, contains, union, envelope
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
from markupsafe import escape
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException


levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url,target))
    return test_url.scheme in ('http', 'https') and \
            ref_url.netloc == test_url.netloc


class TreeNode:
    def __init__(self, value, fid, roid):
        global levelcolours
        self.value = value.replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(",","").replace(" ","_").upper() # name
        self.children = []
        self.type = 'UK'
        self.parent = None
        self.fid = fid
        self.level = 0
        self.file = self.value+"-MAP.html"
        self.dir = self.value
        self.davail = True
        self.col = levelcolours["C"+str(self.level+4)]
        self.tagno = 1
        self.map = None
        self.centroid = roid
        self.source = ""

    def childrenoftype(self,electtype):
        typechildren = [x for x in self.children if x.type == electtype]
        return typechildren


    def locmappath(self,real):
        global Treepolys
        global levelcolours
        global workdirectories
        target = workdirectories['workdir'] + "/" + self.dir + "/" + self.file
        dir = os.path.dirname(target)
        os.chdir(workdirectories['workdir'])
        if real == "":
            if not os.path.exists(dir):
              os.mkdir(dir)
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

    def create_data_branch(self, electtype, namepoints):
      for (name,pt)  in namepoints:
        newnode = TreeNode(name,str(hash(name)), pt)
        print('______Data nodes',newnode.value,newnode.fid, newnode.centroid)
        self.davail = True
        self.add_Tchild(newnode, electtype)
      nodemapfile = self.dir+"/"+self.file
      return len(namepoints)

    def create_map_branch(self,electtype,block):
        global Treepolys
        xmin, ymin, xmax, ymax = self.get_bounding_box(block)
        ChildPolylayer = Treepolys[self.level+1].cx[xmin:xmax, ymin:ymax]
        print ("________new branch elements in bbox:",self.value,self.level,"**", xmin, ymin, xmax, ymax)
    # there are 2-0 (3) relative levels - absolute level are UK(0),nations(1), constituency(2), ward(3)
        index = 0

        if len(self.childrenoftype(electtype)) == 0:
            for index, limb in ChildPolylayer.iterrows():
                newname = limb.NAME.replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(",","").replace(" ","_").upper()
    #            if  newname != "UNITED_KINGDOM":
                print ("________child of",self.value,self.level)
                here = limb.geometry.centroid
                childnode = TreeNode(limb.NAME,limb.FID, here)
        #        here = Point(Decimal(limb.LONG),Decimal(limb.LAT))
        # make sure that the child centroid is within the node boundary
                pfile = Treepolys[self.level]
                poly = pfile[pfile['FID']==self.fid]
                print ("_________child :", limb.NAME )
                if poly.contains(here).item():
                    print("_________TESTED AS INSIDE ",self.level,limb.NAME, self.value)
                    self.add_Tchild(childnode,electtype)

        return index

    def create_area_map (self,flayers,block):
      roid = self.get_centroid(block)
      self.map = folium.Map(location=[roid.y, roid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(self.level+0.75)*2)))
      title_html = '''<h1 style="z-index:1100;color: black;position: fixed;right:100px;">{0}</h1>'''.format(self.value+" Level "+str(self.level))
      self.map.get_root().html.add_child(folium.Element(title_html))
# just save the r-1,r,
      self.map.add_child(flayers[self.level].fg)
      if self.level < 7:
          self.map.add_child(flayers[self.level+1].fg)
      self.map.add_child(folium.LayerControl())
#      self.map.fit_bounds(self.get_bounding_box(block), padding = (20, 20))
# the folium save file reference must be a url
      nodemapfile = self.dir+"/"+self.file
      self.map.add_css_link("electtrekcss","https://newbrie.github.io/Electtrek/static/print.css")
      self.map.add_css_link("electtrekcss","https://newbrie.github.io/Electtrek/static/style.css")

      target = self.locmappath("")
      self.map.save(target)
      print("_____saved map file:",target, self.level)
      return self.map

    def set_bounding_box(self,block):
      longmin = block.Long.min
      latmin = block.Lat.min
      longmax = block.Long.max
      latmax = block.Lat.max
# minx, miny, maxx, maxy
      return [longmin,latmin,longmax,latmax]

    def get_bounding_box(self, block):
      global Treepolys

# for level = 0 use present
# for level < 4 use geometry
# else use supplied data_bbox
      if self.level < 5:
          pfile = Treepolys[self.level]
          pb = pfile[pfile['FID']==self.fid]
          swne = pb.geometry.total_bounds
          swne =[Decimal(swne[0]),Decimal(swne[1]),Decimal(swne[2]),Decimal(swne[3])]
# minx, miny, maxx, maxy
          print("_______Bbox swne",swne, pb, self.fid, self.value, self.level)
      else:
          swne = self.set_bounding_box(block)
      return swne

    def get_centroid(self,block):
      global Treepolys
      if self.level < 5:
          pfile = Treepolys[self.level]
          pb = pfile[pfile['FID']==self.fid]
          roid = pb.geometry.centroid
      else:
          if len(block) > 0:
              longmean = statistics.mean(block.Long.values)
              latmean = statistics.mean(block.Lat.values)
              roid = Point(longmean,latmean)
          else:
              roid = Point(-7.57216793459,49.959999905)
      return roid

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

    def add_Tchild(self, child_node, type):
        # creates parent-child relationship
        self.child = child_node
        self.davail = True
        child_node.parent = self
        self.children.append(child_node)
        child_node.level = self.level + 1
        child_node.dir = self.dir+"/"+child_node.value
        child_node.file = child_node.value+"-MAP.html"
        if child_node.level == 6:
            child_node.dir = self.dir+"/STREETS"
            child_node.file = self.value+"-"+child_node.value+"-PRINT.html"
        child_node.davail = False
        child_node.type = type
        print("_________new child node dir:  ",child_node.dir)

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

    def traverse(self):
    # moves through each node referenced from self downwards
        nodes_to_visit = [self]
        count = 0
        node_list = []
        while len(nodes_to_visit) > 0:
          current_node = nodes_to_visit.pop()
          node_list.append(current_node)
          print("_________Traverse node  ",current_node.value,current_node.fid,current_node.level )
          if current_node.parent is not None:
              print("_________Parent node  ",current_node.parent.value,current_node.parent.fid,current_node.parent.level )
          nodes_to_visit += current_node.children
          count = count+1

        print("_________leafnodes  ",count)
        return sorted (node_list, key=lambda TreeNode: TreeNode.level, reverse=True)

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


def add_boundaries(shelf,node):
    global Treepolys
    global workdirectories
    if shelf == 'country':
        print("__________reading World_Countries_(Generalized)= [0]")
        World_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'World_Countries_(Generalized)_9029012925078512962.geojson', bbox=[-7.57216793459, 49.959999905, 1.68153079591, 58.6350001085])
        World_Bound_layer = World_Bound_layer.rename(columns = {'COUNTRY': 'NAME'})
        UK_Bound_layer = World_Bound_layer[World_Bound_layer['FID'] == 238]
        UK_Bound_layer['LAT'] = 54.4361
        UK_Bound_layer['LONG'] = -4.5481
        Treepolys[0] = UK_Bound_layer
        return UK_Bound_layer
    elif shelf == 'nation':
        print("__________reading Countries_December_2021_UK_BGC_2022_-7786782236458806674= [1]")
        Nation_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson')
        Nation_Bound_layer = Nation_Bound_layer.rename(columns = {'OBJECTID': 'FID'})
        Nation_Bound_layer = Nation_Bound_layer.rename(columns = {'CTRY21NM': 'NAME'})
        Treepolys[1] = Nation_Bound_layer
        return Nation_Bound_layer
    elif shelf == 'county':
        print("__________reading Counties_and_Unitary_Authorities_May_2023_UK_BGC_ = [2]")
        County_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson')
        County_Bound_layer = County_Bound_layer.rename(columns = {'CTYUA23NM': 'NAME'})
        Treepolys[2] = County_Bound_layer
        return County_Bound_layer
    elif shelf == 'constituency':
        print("__________reading Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK= [3]")
        Con_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson')
        Con_Bound_layer = Con_Bound_layer.rename(columns = {'PCON24NM': 'NAME'})
        Treepolys[3] = Con_Bound_layer
        return Con_Bound_layer
    elif shelf == 'ward':
        print("__________reading Wards_May_2024_Boundaries = [4]")
        Ward_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson')
        Ward_Bound_layer = Ward_Bound_layer.rename(columns = {'WD24NM': 'NAME'})
        Treepolys[4] = Ward_Bound_layer
        return Ward_Bound_layer
    elif shelf == 'division':
        print("__________reading County_Electoral_Division_May_2023_Boundaries = [4]")
        Division_Bound_layer = gpd.read_file( workdirectories['bounddir']+"/"+'County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson')
        Division_Bound_layer = Division_Bound_layer.rename(columns = {'CED23NM': 'NAME'})
        Treepolys[4] = Division_Bound_layer
        return Division_Bound_layer


class FGlayer:
    def __init__ (self, id, name):
        self.fg = folium.FeatureGroup(name=name, overlay=True, control=True, show=True)
        self.name = name
        self.children = []
        self.id = id

    def add_linesandmarkers (self,herenode,type):
        global Treepolys
        global levelcolours
        global allelectors
        print('_______HereNode', herenode.value, herenode.level, herenode.fid)
        if herenode.level <= 5:
            displayed = herenode.childrenoftype(type)
            print("______Display children:",herenode.value, herenode.level,type, len(displayed), displayed)
            print('_______MAPLinesandMarkers')
            for c in displayed:
                layerfids = [x.fid for x in self.children]
                if c.fid not in layerfids:
                    if c.level < 5:
                        pfile = Treepolys[c.level]
                        limb = pfile[pfile['FID']==c.fid]
                    else:
                        PDelectors = getblock(allelectors,'PD',c.value)
                        convex = MultiPoint(gpd.points_from_xy(PDelectors.Long.values,PDelectors.Lat.values)).convex_hull
        #                circle = c.centroid.buffer(0.005)
                        df = {'NAME': [c.value],'FID': [c.fid],'LAT': [c.centroid.y],'LONG': [c.centroid.x]}
                        limb = gpd.GeoDataFrame(df, geometry= [convex], crs="EPSG:4326")

                    if herenode.level == 0:
                        downtag = "<form action= '/downcountbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.dir+"/"+c.file,"COUNTIES",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ downtag
                        c.tagno = len(self.children)+1
                        print("_________new child boundary value and tagno:  ",c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    elif herenode.level == 1:
                        downconstag = "<form action= '/downconbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.dir+"/"+c.file,"CONSTITUENCIES",12)
                        uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.parent.dir+"/"+c.parent.file,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag +"<br>"+ downconstag
                        c.tagno = len(self.children)+1
                        print("_________new split child boundary value and tagno:  ",c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    elif herenode.level == 2:
                        downwardstag = "<form action= '/downwardbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.dir+"/"+c.file,"WARDS",12)
                        downdivstag = "<form action= '/downdivbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.dir+"/"+c.file,"DIVS",12)
                        uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.parent.dir+"/"+c.parent.file,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag +"<br>"+ downwardstag + " " + downdivstag
                        c.tagno = len(self.children)+1
                        print("_________new split child boundary value and tagno:  ",c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    elif herenode.level == 3:
                        upload = "<form id='upload' action= '/downPDbut/{0}' method='GET'><input type='file' name='importfile' placeholder={2} style='font-size: {1}pt;color: gray' enctype='multipart/form-data'></input><input type='submit' value='Polling Districts' class='btn btn-norm' onclick='''setActionForm('downPDbut')'''/></form>".format(c.dir+"/"+c.file,12,c.source)
                        uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.parent.dir+"/"+c.parent.file,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag +"<br>"+ upload
                        c.tagno = len(self.children)+1
                        print("_________new split child boundary value and tagno:  ",c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    elif herenode.level == 4:
                        upload = "<form id='upload' action= '/downSTbut/{0}' method='GET'><input type='file' name='importfile' placeholder={2} style='font-size: {1}pt;color: gray' enctype='multipart/form-data'></input><input type='submit' value='Streets' class='btn btn-norm' onclick='''setActionForm('downSTbut')'''/></form>".format(c.dir+"/"+c.file,12,c.parent.source)
                        uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.parent.dir+"/"+c.parent.file,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag +"<br>"+ upload
                        c.tagno = len(self.children)+1
                        print("_________new split child boundary value and tagno:  ",c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    else :
                        downtag = "<form action= '/downcountbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.dir+"/"+c.file,"DOWN",12)
                        uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(c.parent.dir+"/"+c.parent.file,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag +"<br>"+ downtag
                        c.tagno = len(self.children)+1
                        print("_________new child boundary value and tagno:  ",c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)

                    numtag = str(c.tagno)+" "+str(c.value)
                    here = [ Decimal(c.centroid.y),Decimal(c.centroid.x)]
                    fill = levelcolours["C"+str(random.randint(4,15))]
                    print("______addingMarker:",c.value, limb.NAME)

                    folium.GeoJson(limb,highlight_function=lambda feature: {"fillColor": ("green"),},
                      popup=folium.GeoJsonPopup(fields=['UPDOWN',],aliases=["Move:",]),popup_keep_highlighted=True,
                      style_function=lambda feature: {"fillColor": fill,"color": c.col,"dashArray": "5, 5","weight": 3,"fillOpacity": 0.4,},
                      ).add_to(self.fg)
                    self.fg.add_child(folium.Marker(
                         location=here,
                         icon = folium.DivIcon(html="<a href='{0}' style='text-wrap: nowrap; font-size: 12pt; color: indigo'>{1}</b>\n".format(mapfile,numtag),
                         class_name = "leaflet-div-icon",
                         icon_size=(24,24),
                         icon_anchor=(14,40)),
                       )
                     )
        else:
            print("______Flash:",flash("No Further Data!"))
            herenode = herenode.parent

        print("________2fgs",herenode.value,herenode.level,self.children, Featurelayers[herenode.level+1].children)

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



# create and configure the app
app = Flask(__name__, static_url_path='/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/static')

sys.path.append(r'/Users/newbrie/Documents/ReformUK/GitHub/Electtrek')
# Configure Alchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/newbrie/Documents/ReformUK/GitHub/Electtrek/trekusers.db'
app.config['SECRET_KEY'] = 'rosebutt'
#app.config['USE_SESSION_FOR_NEXT'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/Users/newbrie/Sites'
app.config['APPLICATION_ROOT'] = '/Users/newbrie/Documents/ReformUK/GitHub/Electtrek'
#app.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = '<h1>login</h1>'
login_manager.login_message = "<h1>You really need to login!!</h1>"
login_manager.refresh_view = "<h1>Login</h1>"
login_manager.needs_refresh_message = "<h1>You really need to re-login to access this page</h1>"


workdirectories = {}
workdirectories['testdir'] = "/Users/newbrie/Documents/ReformUK/ElectoralRegisters/Test"
workdirectories['staticdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek"
workdirectories['workdir'] = "/Users/newbrie/Sites"
workdirectories['templdir'] = "/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/templates"
workdirectories['bounddir'] = "/Users/newbrie/Documents/ReformUK/GitHub/ElecttrekReference/Boundaries/"

Featurelayers = []

Featurelayers.append(FGlayer(id=1,name='United Kingdom Boundary'))
Featurelayers.append(FGlayer(id=2,name='Nation Boundaries'))
Featurelayers.append(FGlayer(id=3,name='County Boundaries'))
Featurelayers.append(FGlayer(id=4,name='Constituency Boundaries'))
Featurelayers.append(FGlayer(id=5,name='Ward/Division Boundaries'))
Featurelayers.append(FGlayer(id=6,name='Polling District Markers'))
Featurelayers.append(FGlayer(id=7,name='Street Markers'))
Featurelayers.append(FGlayer(id=8,name='Special Markers'))

formdata = {}
allelectors = []
mapfile = ""
Directories = {}

longmean = statistics.mean([-7.57216793459,  1.68153079591])
latmean = statistics.mean([ 49.959999905, 58.6350001085])
roid = Point(longmean,latmean)
MapRoot = TreeNode("UNITED_KINGDOM",238, roid)
MapRoot.dir = "UNITED_KINGDOM"
MapRoot.file = "UNITED_KINGDOM-MAP.html"
Treepolys = [[],[],[],[],[],[]]
add_boundaries('country',MapRoot)
add_boundaries('nation',MapRoot)
MapRoot.create_map_branch('nation',allelectors)

current_node = MapRoot

Featurelayers[current_node.level+1].children = []
Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
Featurelayers[current_node.level+1].add_linesandmarkers(current_node, 'nation')

map = MapRoot.create_area_map(Featurelayers,allelectors)
mapfile = current_node.dir+"/"+current_node.dir

from jinja2 import Environment, FileSystemLoader
templateLoader = jinja2.FileSystemLoader(searchpath=workdirectories['templdir'])
environment = jinja2.Environment(loader=templateLoader,auto_reload=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self,password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash, password)


#@login_manager.user_loader
#def load_user(user_id):
#    return User.get_id(user_id)

@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.id == int(user_id)).first()

@login_manager.unauthorized_handler     # In unauthorized_handler we have a callback URL
def unauthorized_callback():            # In call back url we can specify where we want to
    return render_template("index.html") # redirect the user in my case it is login page!

#@app.errorhandler(404)
#def handle_error(error):
#    response = jsonify(error.to_dict())
#    response.status_code = error.status_code
#    formdata['status'] = response.status_code
#    flash("Not found: "+formdata['status'])
#    return render_template("dash0.html", context = { "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

@app.errorhandler(HTTPException)
def handle_exception(e):
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
    return response

@app.route("/index", methods=['POST', 'GET'])
def index():
    global Treepolys
    global MapRoot
    global current_node

    print('_______ROUTE/index')

    current_node = MapRoot

    if 'username' in session:
        flash("__________Session contents"+ session['username'])
        print("__________session", session['username'])
        print("__________Logged in ", os.getcwd())
        return redirect (url_for('dashboard'))

    return render_template("index.html")

#login
@app.route('/login', methods=['POST'])
def login():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment

    print('_______ROUTE/login')

    #collect info from forms in the login db
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
#check if it exists
    if not user:
        print("User not found", username)
        flash('Username does not exist.')
    elif user and user.check_password(password):

        session["username"] = username

        print("__________Username", session['username'])

        login_user(user)
        next = request.args.get('next')
        formdata = {}
        current_node = MapRoot

        formdata['country'] = 'UNITED_KINGDOM'
        formdata['candfirst'] = "Firstname"
        formdata['candsurn'] = "Surname"
        formdata['electiondate'] = "DD-MMM-YY"
        formdata['filename'] = "NONE"
        for england in MapRoot.children:
            if england.value == 'ENGLAND':
                break

        add_boundaries('county',england)
        england.create_map_branch('county',allelectors)
        mapfile = current_node.dir + "/" + current_node.file
        mapfile = url_for('map',path=mapfile)
        flash (session['username'] + ' is logged in at '+ mapfile)
        flash ("Drill down to the constituency of your interest ")

        return render_template("dash1.html", context = {  "current_node" : current_node, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})
    else:
        return render_template("index.html")

    session['next'] = request.args.get('next')

    return render_template ('index.html')

#dashboard

@app.route('/dashboard', methods=['GET'])
def dashboard ():
    #formdata['username'] = session["username"]
    global workdirectories
    global Directories
    global MapRoot
    global current_node

    global allelectors


    global Treepolys
    global Featurelayers

    print('_______ROUTE/dashboard')

    mapfile  = current_node.dir+"/"+current_node.file
    if 'username' in session:
        flash(session['username'] + ' is logged in at '+ mapfile)
        mapfile = url_for('map',path=mapfile)
        print("___________node map file dir",current_node.dir)
        return render_template("dash1.html", context = {  "current_node" : current_node, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})
    return redirect(url_for('index'))


@app.route('/downcountbut/<path:selnode>', methods=['GET'])
def downcountbut(selnode):
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment

    flash('_______ROUTE/downcountbut')
    print('_______ROUTE/downcountbut')

    formdata = {}
#    dat = request.base_url
# a down button on a node has been selected on the map, so the new map must be displayed with new down options

# the selected node has to be found from the selected button URL
    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])

# the map under the selected node map needs to be configured
    print("_________selected node",steps[-1],current_node.value, current_node.level,current_node.file)
# the selected  boundary options need to be added to the layer
    add_boundaries('county',current_node)
    current_node.create_map_branch('county',allelectors)
    Featurelayers[current_node.level+1].children = []
    Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+2),name=Featurelayers[current_node.level+1].name, overlay=True, control=True, show=True)
    Featurelayers[current_node.level+1].add_linesandmarkers(current_node, 'county')
    map = current_node.create_area_map(Featurelayers,allelectors)
    mapfile = current_node.dir+"/"+current_node.file
    print("________child nodes created",current_node.children)

# the selected node boundary options need to be added to the layer
    allelectors = []
    #formdata['username'] = session["username"]
    formdata['country'] = "UNITED_KINGDOM"
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['filename'] = "NONE"
#    return render_template("dash1.html", context = { "current_node" : current_node, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})
    flash ("Data is available for counties. Please explore!")
    print ("Data is available for counties. Please explore!")


    return redirect(url_for('map',path=mapfile))

@app.route('/downPDbut/<path:selnode>', methods=['GET'])
def downPDbut(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    print('_______ROUTE/downPDbut',selnode)

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file
    frames = []
    PDPts =[]
    PDWardlist =[]
    if request.method == 'GET':
        if current_node.source == "" or len(allelectors) == 0:
            print ("_________Requestformfile",request.values['importfile'])
            flash ("_________Requestformfile"+request.values['importfile'])
            filename = request.values['importfile']
            allelectors = pd.read_csv(workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
            pfile = Treepolys[current_node.level]
            Wardboundary = pfile[pfile['FID']==current_node.fid]
            PDs = set(allelectors.PD.values)
            print("PDsfull", PDs)
            for PD in PDs:
              PDelectors = getblock(allelectors,'PD',PD)
              maplongx = statistics.mean(PDelectors.Long.values)
              maplaty = statistics.mean(PDelectors.Lat.values)
              PDcoordinates = Point(Decimal(maplongx),Decimal(maplaty))
            # for all PDs - pull together all PDs which are within the Conboundary constituency boundary
              if Wardboundary.geometry.contains(Point(Decimal(maplongx),Decimal(maplaty))).item():
                  Ward = list(Wardboundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.replace(" ","_").str.upper())[0]
                  PDelectors['Ward'] = Ward
                  PDWardlist.append((PD,Ward, Wardboundary))
                  PDPts.append((PD,PDcoordinates))
                  frames.append(PDelectors)
            allelectors = pd.concat(frames)
# if there is a selected file , then allelectors will be full of records

        wardelectors = getblock(allelectors, 'Ward',current_node.value)
        PDs = wardelectors.PD.unique()
        print("PDsinward", PDPts)

        current_node.create_data_branch('PD',PDPts)
        current_node.source = filename
        Featurelayers[current_node.level+1].children = []
        Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+2),name=Featurelayers[current_node.level+1].name, overlay=True, control=True, show=True)
        Featurelayers[current_node.level+1].add_linesandmarkers(current_node, 'PD')
        map = current_node.create_area_map(Featurelayers,wardelectors)
        mapfile = current_node.dir+"/"+current_node.file

        if len(allelectors) == 0 or len(Featurelayers[current_node.level+1].children) == 0:
            flash("Can't find any elector data for this Ward.")
            print("Can't find any elector data for this Ward.")
            allelectors = []
        else:
            flash("________PDs added  :  "+str(len(Featurelayers[current_node.level+1].children)))
            print ("________PDs added  :  ",len(Featurelayers[current_node.level+1].children))


        mapfile = current_node.dir+"/"+current_node.file
        print ("________Heading for Polling District :  ",current_node.value)
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/downSTbut/<path:selnode>', methods=['GET'])
def downSTbut(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    global environment

    print('_______ROUTE/downSTbut',selnode)

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file
    frames = []
    PDPts =[]
    PDWardlist =[]
    if request.method == 'GET':
        if current_node.source == "" or len(allelectors) == 0:
            print ("_________Requestformfile",request.values['importfile'])
            flash ("_________Requestformfile"+request.values['importfile'])
            filename = request.values['importfile']
            allelectors = pd.read_csv(workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
            pfile = Treepolys[current_node.parent.level]
            Wardboundary = pfile[pfile['FID']==current_node.parent.fid]
            PDs = set(allelectors.PD.values)
            print("PDsfull", PDs)
            for PD in PDs:
              PDelectors = getblock(allelectors,'PD',PD)
              maplongx = statistics.mean(PDelectors.Long.values)
              maplaty = statistics.mean(PDelectors.Lat.values)
              PDcoordinates = Point(Decimal(maplongx),Decimal(maplaty))
            # for all PDs - pull together all PDs which are within the Conboundary constituency boundary
              if Wardboundary.geometry.contains(Point(Decimal(maplongx),Decimal(maplaty))).item():
                  Ward = list(Wardboundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.replace(" ","_").str.upper())[0]
                  PDelectors['Ward'] = Ward
                  PDWardlist.append((PD,Ward, Wardboundary))
                  PDPts.append((PD,PDcoordinates))
                  frames.append(PDelectors)
            allelectors = pd.concat(frames)
# if there is a selected file , then allelectors will be full of records
        PDelectors = getblock(allelectors, 'PD',current_node.value)

        CCstreets = PDelectors.StreetName.unique()
        StreetPts = [(x[0],Point(x[1],x[2])) for x in PDelectors[['StreetName','Long','Lat']].drop_duplicates().values]
        current_node.create_data_branch('street',StreetPts)
        Featurelayers[current_node.level+1].children = []
        Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+2),name=Featurelayers[current_node.level+1].name, overlay=True, control=True, show=True)
        Featurelayers[current_node.level+1].add_linesandmarkers(current_node, 'street')
        map = current_node.create_area_map(Featurelayers,PDelectors)
        mapfile = current_node.dir+"/"+current_node.file

        if len(allelectors) == 0 or len(Featurelayers[current_node.level+1].children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.",len(allelectors),len(Featurelayers[current_node.level+1].children))
        else:
            flash("________streets added  :  "+str(len(Featurelayers[current_node.level+1].children)))
            print ("________streets added  :  ",len(Featurelayers[current_node.level+1].children))

        for street_node in current_node.children:
              street = street_node.value
    #          uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(street_node.parent.dir+"/"+street_node.parent.file,"UP",10)
    #          flayers[6].children = []
    #          flayers[6].fg = folium.FeatureGroup(id=7, name='Street Markers', overlay=True, control=True, show=True)
    #          flayers[4].fg = folium.FeatureGroup(name='Division Boundary', overlay=True, control=True, show=True)
    #          Wardboundary["UPstreet"] = "<br>"+Ward+"</br>"+ uptag
    #          add_to_ward_layer (Wardboundary, flayers[6].fg,"UPstreet", Ward)

    #          if Divboundary is not None:
    #            Divboundary["UPstreet"] =  "<br>"+Divname+"</br>"+uptag
    #            add_to_div_layer (Divboundary, flayers[4].fg, "UPstreet", Divname)

              electorwalks = getblock(PDelectors, 'StreetName',street_node.value)
    #          maplongx = statistics.mean(electorwalks.Long.values)
    #          maplaty = statistics.mean(electorwalks.Lat.values)
    #          walkcoordinates = [maplaty, maplongx]
              STREET_ = street_node.value

#              here = Point(Decimal(maplongx),Decimal(maplaty))

    #          Postcode = electorwalks.loc[0].Postcode

              walk_name = current_node.value+"-"+STREET_
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

    #          for streetcoordinates in CL_unique_list:
    #            uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(street_node.parent.dir+"/"+street_node.parent.file,"UP",12)
    #            downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(street_node.dir+"/"+street_node.file,street_node.value,12)

                # in the Walk map add Street-postcode groups to the walk map with controls to go back up to the PD map or down to the Walk addresses
    #            popuptext = '<ul style="font-size: {5}pt;color: gray;" >Ward: {0} WalkNo: {1} Postcode: {2} {3} {4}</ul>'.format(Ward,STREET_, Postcode, uptag, downtag,12)

                # in the PD map add PD-cluster walks to the PD map with controls to go back up to the Ward map or down to the Walk map
    #            flayers[6].fg.add_child(
    #              folium.Marker(
    #                 location=streetcoordinates,
    #                 popup = popuptext,
    #                 icon=folium.Icon(color = type_colour,  icon='search'),
    #                 )
    #                 )


            #      img_data = Walkmap._to_png(1)
        #      img = Image.open(io.BytesIO(img_data))
        #      img.save(BMapImg)
        #      mapfull = BMapImg

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
              if math.isnan(Decimal(electorwalks.Elevation.max())):
                  climb = 0
              else:
                  climb = int(Decimal(electorwalks.Elevation.max()) - Decimal(electorwalks.Elevation.min()))

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
              prodstats['PD'] = current_node.parent.value
              prodstats['groupelectors'] = groupelectors
              prodstats['climb'] = climb
              prodstats['houses'] = houses
              prodstats['streets'] = streets
              prodstats['housedensity'] = housedensity
              prodstats['leafhrs'] = round(leafhrs,2)
              prodstats['canvasshrs'] = round(canvasshrs,2)

              electorwalks['ENOP'] =  electorwalks['ENO']+ electorwalks['Suffix']*0.1
              target = street_node.locmappath("")
              results_filename = walk_name+"-PRINT.html"

              data_filename = street_node.dir+"/"+walk_name+"-DATA.html"
              map_filename = street_node.parent.dir+"/"+street_node.parent.file

              context = {
                "group": electorwalks,
                "prodstats": prodstats,
                "mapfile": url_for('map',path=map_filename),
                "datafile": url_for('map',path=data_filename),
                "walkname": walk_name,
                }
              results_template = environment.get_template('canvasscard1.html')

              with open(results_filename, mode="w", encoding="utf-8") as results:
                results.write(results_template.render(context, url_for=url_for))

        print ("________Heading for the Streets in PD :  ",current_node.value)
        if len(Featurelayers[current_node.level].children) == 0:
            flash("Can't find any Streets for this PD.")
        else:
            flash("________Streets added  :  "+str(len(Featurelayers[current_node.level].children)))
            print ("________Streets added  :  ",len(Featurelayers[current_node.level].children))
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/downconbut/<path:selnode>', methods=['GET'])
def downconbut(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global allelectors
    print('_______ROUTE/downconbut',selnode)


    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    add_boundaries('constituency',current_node)
    current_node.create_map_branch('constituency',allelectors)
    Featurelayers[current_node.level+1].children = []
    Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+2),name=Featurelayers[current_node.level+1].name, overlay=True, control=True, show=True)
    Featurelayers[current_node.level+1].add_linesandmarkers(current_node, 'constituency')
    map = current_node.create_area_map(Featurelayers,allelectors)
    mapfile = current_node.dir+"/"+current_node.file

    print ("________Heading for Constituency :  ",current_node)
    if len(Featurelayers[current_node.level+1].children) == 0:
        flash("Can't find any constituencies for this county.")
    else:
        flash("________constituencies added  :  "+str(len(Featurelayers[current_node.level+1].children)))
        print ("________constituencies added  :  ",len(Featurelayers[current_node.level+1].children))
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/downwardbut/<path:selnode>', methods=['GET'])
def downwardbut(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    print('_______ROUTE/downwardbut')
    global allelectors


    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    if current_node.level == 3 :
        add_boundaries('ward',current_node)
        current_node.create_map_branch('ward',allelectors)
        Featurelayers[current_node.level+1].children = []
        Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+2),name=Featurelayers[current_node.level+1].name, overlay=True, control=True, show=True)
        Featurelayers[current_node.level+1].add_linesandmarkers(current_node, 'ward')
        map = current_node.create_area_map(Featurelayers,allelectors)
        mapfile = current_node.dir+"/"+current_node.file
        print ("________Heading for wards of :  ",current_node)
    if len(Featurelayers[current_node.level].children) == 0:
        flash("Can't find any wards for this Constituency.")
    else:
        flash("________wards added  :  "+str(len(Featurelayers[current_node.level].children)))
        print ("________wards added  :  ",len(Featurelayers[current_node.level].children))
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/downdivbut/<path:selnode>', methods=['GET'])
def downdivbut(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    print('_______ROUTE/downdivbut')
    global allelectors

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    if current_node.level == 3 :
        add_boundaries('division',current_node)
        current_node.create_map_branch('division',allelectors)
        Featurelayers[current_node.level+1].children = []
        Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+2),name=Featurelayers[current_node.level+1].name, overlay=True, control=True, show=True)
        Featurelayers[current_node.level+1].add_linesandmarkers(current_node,'division')
        map = current_node.create_area_map(Featurelayers,allelectors)
        mapfile = current_node.dir+"/"+current_node.file
        print ("________Heading for division : ",current_node)
    if len(Featurelayers[current_node.level].children) == 0:
        flash("Can't find any county divisions for this Constituency.")
    else:
        flash("________divisions added  :  "+str(len(Featurelayers[current_node.level+1].children)))
        print ("________divisions added  :  ",len(Featurelayers[current_node.level+1].children))
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/layeritems/',methods=['GET'])
def layeritems():
    global current_node

    print('_______ROUTE/layeritems')

    layernodelist = Featurelayers[current_node.level+1].children
    current_node = current_node.parent
    mapfile = url_for('downcountbut',selnode=current_node.dir+"/"+current_node.file)
    print("________laynodelist", current_node.level, current_node.value, Featurelayers[current_node.level+1].children)
    return render_template("dash1.html", context = { "layernodelist" :layernodelist, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

@app.route('/upbut/<path:selnode>', methods=['GET'])
def upbut(selnode):
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment
    print('_______ROUTE/upbut',selnode)

    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
    print("_________current+parent_node",current_node.value, current_node.parent.value)
# the selected node has to be found from the selected button URL


    Featurelayers[current_node.level].children = []
    Featurelayers[current_node.level+1].fg = folium.FeatureGroup(id=str(current_node.level+2),name=Featurelayers[current_node.level+1].name, overlay=True, control=True, show=True)

    current_node = current_node.parent
# the selected  boundary options need to be added to the layer
    nodemapfile = current_node.dir+"/"+current_node.file
# the selected node boundary options need to be added to the layer


    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['filename'] = "NONE"

    print("________chosen node url",nodemapfile)

    return redirect(url_for('map',path=nodemapfile))
#    return render_template("dash1.html", context = { "current_node" : current_node, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})


@app.route('/resetdashboard', methods=['POST', 'GET'])
def resetdashboard():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors

    global Treepolys
    global Featurelayers
    global environment

    formdata = {}
    print("__________setupdashboard", session)
    print("__________in session", "username")

#    County_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson')
#    County_Bound_layer = County_Bound_layer.rename(columns = {'PCON24NM': 'NAME'})


#        sw = [Country_Bound_layer.geometry.bounds.miny.to_list()[0],Country_Bound_layer.geometry.bounds.minx.to_list()[0]]
#        ne = [Country_Bound_layer.geometry.bounds.maxy.to_list()[0],Country_Bound_layer.geometry.bounds.maxx.to_list()[0]]

    area =  CountryMapfile.replace("-MAP.html","")
    mapfile = "/"+area+"/"+CountryMapfile

    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['filename'] = "NONE"
    return render_template("dash0.html", context = {  "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})
#    else:
#        print("__________no",  "in session", session)
#        return render_template("index.html")

#    username = request.form['username']
#    user = User.query.filter_by(username=username).first()
#    if not user:
#        return '<h1>User not found!</h1>'
#    login_user(user, remember=True)
#
#    if 'next' in session:
#        next = session['next']
#        if is_safe_url(next):
#            return redirect(next)
#    return '<h1> Hey '+ username+' - You are now logged in!</h1>'

#logout

@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    print('_______ROUTE/logout')

    print("Logout", session)
    if "username" in session:
        session.pop('username', None)
        logout_user()
        return "<h1> Hey - You are now logged out</h1>"
    return redirect(url_for('login'))

#Register user
@app.route('/register', methods=['POST'])
def register():
    print('_______ROUTE/register')

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

@app.route('/map/<path:path>', methods=['GET'])
def map(path):
    print('_______ROUTE/map')
    flash ("_________Nextmap"+path)
    print ("_________Nextmap",path)
    return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)

@app.route('/upload', methods=['POST','GET'])
def upload():
    print('_______ROUTE/upload')
    print("Upload", username)
    ImportFilename = ""
    if Env1.find("Orange")<=0:
        return render_template('upload.html')
    return redirect(url_for('dashboard'))

@app.route('/normalise', methods=['POST','GET'])
def normalise():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors


    global Treepolys
    global Featurelayers
    global environment

    print('_______ROUTE/normalise',session)
    formdata = {}
    formdata['importfile'] = request.files['importfile']
    formdata['candfirst'] =  request.form["candfirst"]
    formdata['candsurn'] = request.form["candsurn"]
    formdata['electiondate'] = request.form["electiondate"]
    results = normalised.normz(formdata['importfile'], formdata)
    formdata = results[1]
    group = results[0]
#    formdata['username'] = session['username']
    return render_template('dash0.html', context = {  "session" : session, "formdata" : formdata, "group" : allelectors , "mapfile" : mapfile})

@app.route('/walks', methods=['POST','GET'])
def walks():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors


    global Treepolys
    global Featurelayers
    global environment
    print('_______ROUTE/walks',session)

    if len(request.form) > 0:
        formdata = {}
        formdata['importfile'] = request.files['importfile']
        formdata['candfirst'] =  request.form["candfirst"]
        formdata['candsurn'] = request.form["candsurn"]
        formdata['electiondate'] = request.form["electiondate"]
        prodwalks = electorwalks.prodwalks(current_node,formdata['importfile'], formdata)
        formdata = prodwalks[1]
        print("_________Mapfile",prodwalks[2])
        mapfile = prodwalks[2]
        group = prodwalks[0]
#    formdata['username'] = session['username']
        return render_template('dash0.html', context = {  "session" : session, "formdata" : formdata, "group" : allelectors , "mapfile" : mapfile})
    return redirect(url_for('dashboard'))

@app.route('/postcode', methods=['POST','GET'])
def postcode():
    global current_node
    global Treepolys
    global Featurelayers
    global Directories
    global workdirectories
    print('_______ROUTE/postcode')

    layernodelist = Featurelayers[current_node.level+1].children

    mapfile = url_for('downcountbut',selnode=current_node.dir+"/"+current_node.file)
    postcodeentry = request.form["postcodeentry"]
    if len(postcodeentry) > 8:
        postcodeentry = str(postcodeentry).replace(" ","")
    dfx = pd.read_csv(workdirectories['bounddir']+"National_Statistics_Postcode_Lookup_UK_20241022.csv")
    df1 = dfx[['Postcode 1','Latitude','Longitude']]
    df1 = df1.rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
    df1['Lat'] = df1['Lat'].astype(float)
    df1['Long'] = df1['Long'].astype(float)
    lookuplatlong = df1[df1['Postcode'] == postcodeentry]
    here = Point(Decimal(lookuplatlong.Long.values[0]),Decimal(lookuplatlong.Lat.values[0]))
    pfile = Treepolys[current_node.level+1]
    polylocated = electorwalks.find_boundary(pfile,here)

    popuptext = '<ul style="font-size: {4}pt;color: gray;" >Lat: {0} Long: {1} Postcode: {2} Name: {3}</ul>'.format(lookuplatlong.Lat.values[0],lookuplatlong.Long.values[0], postcodeentry, polylocated['NAME'].values[0], 12)
    here1 = [here.y, here.x]
    # in the PD map add PD-cluster walks to the PD map with controls to go back up to the Ward map or down to the Walk map
    Featurelayers[7].fg.add_child(
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


@app.route('/cards', methods=['POST','GET'])
def cards():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment
    print('_______ROUTE/canvasscards',session, request.form, current_node.level)

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
                mapfile =  url_for('map',path=prodcards[2])
                group = prodcards[0]
                return render_template('dash1.html', context = { "current_node" : current_node, "session" : session, "formdata" : formdata, "group" : allelectors , "mapfile" : mapfile})
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
