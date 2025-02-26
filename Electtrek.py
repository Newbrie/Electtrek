from canvasscards import prodcards, getblock, find_boundary
from walks import prodwalks
#import electwalks, locmappath, electorwalks.create_area_map, goup, godown, add_to_top_layer, find_boundary
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
from markupsafe import escape
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask import json, get_flashed_messages, request
from werkzeug.exceptions import HTTPException


levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

levels = ['country','nation','county','constituency','ward/division','polling district','walk/street','elector/walkleg','walkelector']


# want to equate levels with certain types, eg 4 is ward and div
# want to look up the level of a type ,and the types in a level

def getchildtype(parent):
    global levels
    matches = [index for index, x in enumerate(levels) if x.find(parent) > -1  ]
    return levels[matches[0]+1]

def getleveloftype(etype):
    global levels
    matches = [index for index, x in enumerate(levels) if x.find(etype) > -1  ]
    return matches[0]


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url,target))
    return test_url.scheme in ('http', 'https') and \
            ref_url.netloc == test_url.netloc

class TreeNode:
    def __init__(self, value, fid, roid):
        global levelcolours
        self.value = str(value).replace(" & "," AND ").replace(r'[^A-Za-z0-9 ]+', '').replace("'","").replace(",","").replace(" ","_").upper() # name
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
        self.centroid = Point(roid.x,roid.y)
        self.bbox = []
        self.map = {}
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
      newnode = self
      geometry = gpd.points_from_xy(namepoints.Long.values,namepoints.Lat.values, crs="EPSG:4326")
      block = gpd.GeoDataFrame(
        namepoints, geometry=geometry
        )
      self.bbox = self.get_bounding_box(block)[0]
      self.centroid = self.get_bounding_box(block)[1]
      self.map = folium.Map(location=[self.centroid.y, self.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(self.level,5)+0.75)*2)))
      print('______Data frame:',namepoints)
      for index, limb  in namepoints.iterrows():
        newnode = TreeNode(limb.Name,index+1, Point(limb.Long,limb.Lat))
        newnode.source = self.source
        print('______Data nodes',newnode.value,newnode.fid, newnode.centroid)
        self.davail = True
        egg = self.add_Tchild(newnode, electtype)
        egg.file = egg.file.replace("-MAP",ending)

      nodemapfile = self.dir+"/"+self.file
      return newnode

    def create_map_branch(self,electtype,block):
        global Treepolys
        self.bbox = self.get_bounding_box(block)[0]
        xmin, ymin, xmax, ymax = self.bbox
        self.centroid = self.get_bounding_box(block)[1]
        ChildPolylayer = Treepolys[self.level+1]
#.cx[xmin:xmax, ymin:ymax]
        self.map = folium.Map(location=[self.centroid.y, self.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(self.level+0.75)*2)))

        print("_______CXofTreepoly level", self.level+1, ChildPolylayer.shape)
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
                if intersection(poly.geometry,limb.geometry).item().area > 0.0001:
                    print("_________TESTED AS INSIDE ",self.level,limb.NAME, self.value)
                    self.add_Tchild(childnode,electtype)


        return index

    def create_area_map (self,flayers,block,ending):
      self.file = self.file.replace("-MAP", ending)
      if self.level > 0:
          title = self.parent.value+"-"+self.value+" "+ getchildtype(self.type)+ " set at level "+str(self.level)
      else:
          title = self.value+" Level "+str(self.level)
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
      self.map.fit_bounds(self.bbox, padding = (10, 10))
      self.map.save(target)
      print("_____saved map file:",target, self.level)

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
      if self.level < 5:
          pfile = Treepolys[self.level]
          pb = pfile[pfile['FID']==self.fid]
          swne = pb.geometry.total_bounds
          roid = pb.dissolve().centroid
          swne =[float('%.4f'%(swne[0])),float('%.4f'%(swne[1])),float('%.4f'%(swne[2])),float('%.4f'%(swne[3]))]
# minx, miny, maxx, maxy
          print("_______Bbox swnemap",swne, pb, self.fid, self.value, self.level)
      else:
#          swne = self.set_bounding_box(block)
          swne = block.geometry.total_bounds
          roid = block.dissolve().centroid
          swne =[float('%.4f'%(swne[0])),float('%.4f'%(swne[1])),float('%.4f'%(swne[2])),float('%.4f'%(swne[3]))]
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
        child_node.level = child_node.parent.level + 1
        child_node.dir = self.dir+"/"+child_node.value
        child_node.file = child_node.value+"-MAP.html"
        if etype == 'street':
            child_node.dir = self.dir+"/STREETS"
            child_node.file = self.value+"-"+child_node.value+"-MAP.html"
        elif etype == 'walk':
            child_node.dir = self.dir+"/WALKS"
            child_node.file = self.value+"-"+child_node.value+"-MAP.html"
        elif etype == 'walkleg':
            child_node.dir = self.dir
            child_node.file = self.value+"-"+child_node.value+"-MAP.html"

        child_node.davail = False
        child_node.type = etype
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
    global Con_Results_data
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
    elif shelf == 'ward' or shelf == 'division' or shelf == 'ward/division':
        if shelf == 'division':
            print("__________reading County_Electoral_Division_May_2023_Boundaries = [4]")
            Division_Bound_layer = gpd.read_file( workdirectories['bounddir']+"/"+'County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson')
            Division_Bound_layer = Division_Bound_layer.rename(columns = {'CED23NM': 'NAME'})
            Treepolys[4] = Division_Bound_layer
            return Division_Bound_layer
        else:
            print("__________reading Wards_May_2024_Boundaries = [4]")
            Ward_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson')
            Ward_Bound_layer = Ward_Bound_layer.rename(columns = {'WD24NM': 'NAME'})
            Treepolys[4] = Ward_Bound_layer
            return Ward_Bound_layer



class FGlayer:
    def __init__ (self, id, name):
        self.fg = folium.FeatureGroup(name=name, overlay=True, control=True, show=True)
        self.name = name
        self.children = []
        self.id = id

    def add_walkshape (self,herenode,type,datablock):
        global Treepolys
        global levelcolours
        global allelectors
        print('_______Convexhull', herenode.value, herenode.level, herenode.fid, len(datablock))
        convex = MultiPoint(gpd.points_from_xy(datablock.Long.values,datablock.Lat.values)).convex_hull
#        circle = herenode.centroid.buffer(0.005)
#        Twopts = maximum_inscribed_circle(MultiPoint(gpd.points_from_xy(datablock.Long.values,datablock.Lat.values)))
#        circle = Twopts[0].buffer(distance(Twopts[0],Twopts[1]))
        df = {'NAME': [herenode.value],'FID': [herenode.fid],'LAT': [herenode.centroid.y],'LONG': [herenode.centroid.x]}
        limb = gpd.GeoDataFrame(df, geometry= [convex], crs="EPSG:4326")
#        limb = gpd.GeoDataFrame(df, geometry= [circle], crs="EPSG:4326")


        if type == 'polling district':
            showmessageST = "showMore(&#39;/PDshowST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
#            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,herenode.source, herenode.dir+"/"+herenode.file)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limb['UPDOWN'] = uptag1 +"<br>"+ downST+"<br>"+ downWK
            herenode.tagno = len(self.children)+1
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)
            self.children.append(herenode)
        elif type == 'walk':
            showmessage = "showMore(&#39;/showmore/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('walk'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
            downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limb['UPDOWN'] =  uptag1 +"<br>"+ downtag+"<br>"
            herenode.tagno = len(self.children)+1
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)
            self.children.append(herenode)

        numtag = str(herenode.tagno)+" "+str(herenode.value)
        typetag = "from <br>"+str(herenode.type)+": "+str(herenode.value)+"<br> move :"
        here = [float('%.4f'%(herenode.centroid.y)),float('%.4f'%(herenode.centroid.x))]
        fill = levelcolours["C"+str(random.randint(4,15))]
        print("______addingPoly:",herenode.value, limb.NAME)

        folium.GeoJson(limb,smooth_factor=1,highlight_function=lambda feature: {"fillColor": ("blue"),},
          popup=folium.GeoJsonPopup(fields=['UPDOWN',],aliases=[typetag,]),popup_keep_highlighted=False,
          style_function=lambda feature: {"fillColor": fill,"color": herenode.col,"dashArray": "5, 5","weight": 3,"fillOpacity": 0.4,},
          ).add_to(self.fg)
        mapfile = "/map/"+herenode.dir+"/"+herenode.file
        self.fg.add_child(folium.Marker(
             location=here,
             icon = folium.DivIcon(html="<a href='{0}' style='text-wrap: nowrap; font-size: 12pt; color: indigo'>{1}</b>\n".format(mapfile,numtag),
             class_name = "leaflet-div-icon",
             icon_size=(24,24),
             icon_anchor=(14,40)),
           )
                 )
        print("________Layer map polys",herenode.value,herenode.level,self.children, Featurelayers[herenode.level].children)
        return herenode

    def add_mapboundaries (self,herenode,type):
        global Treepolys
        global levelcolours
        global allelectors
        global Con_Results_data
        print('_______HereNode', herenode.value, herenode.level, herenode.fid)
        for c in herenode.childrenoftype(type):
            print("______Display children:",herenode.value, herenode.level,type)
            print('_______MAPLinesandMarkers')
            layerfids = [x.fid for x in self.children if x.type == type]
            if c.fid not in layerfids:
                if c.level <= len(Treepolys)-1:
                    pfile = Treepolys[c.level]
                    limb = pfile[pfile['FID']==c.fid]
                    if herenode.level == 0:
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                        downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"COUNTIES",12)
    #                    res = "<p  width=50 id='results' style='font-size: {0}pt;color: gray'> </p>".format(12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>" + downtag
                        c.tagno = len(self.children)+1
                        print("_________new child boundary value and tagno:  ",c.type, c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    elif herenode.level == 1:
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
                        downconstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"CONSTITUENCIES",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ downconstag
                        c.tagno = len(self.children)+1
                        print("_________new split child boundary value and tagno:  ",c.type,c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    elif herenode.level == 2:
                        downwardmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" ward", c.value,getchildtype('ward'))
                        downdivmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" division", c.value,getchildtype('division'))
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
                        downwardstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downwardmessage,"WARDS",12)
                        downdivstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downdivmessage,"DIVS",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ downwardstag + " " + downdivstag
                        c.tagno = len(self.children)+1
                        print("_________new split child boundary value and tagno:  ",c.type, c.value, c.tagno)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)
                    elif herenode.level == 3:
                        downPDmessage = "moveDown(&#39;/downPDbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype('ward/division'))
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
                        PDbtn = "<input type='submit' form='uploadPD' value='Polling Districts' class='btn btn-norm' onclick='{0}'/>".format(downPDmessage)
                        upload = "<form id='uploadPD' action= '/downPDbut/{0}' method='GET'><input type='file' name='importfile' placeholder={2} style='font-size: {1}pt;color: gray' enctype='multipart/form-data'></input></form>".format(c.dir+"/"+c.file,12,c.source)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ upload+PDbtn
                        c.tagno = len(self.children)+1
                        print("_________new Ward value and tagno:  ",c.type,c.value, c.tagno, PDbtn)
                        mapfile = "/map/"+c.dir+"/"+c.file
                        self.children.append(c)


                    numtag = str(c.tagno)+" "+str(c.value)
                    here = [ float('%.4f'%(c.centroid.y)),float('%.4f'%(c.centroid.x))]
                    fill = levelcolours["C"+str(random.randint(4,15))]
                    print("______addingMarker:",c.value, limb.NAME)

                    folium.GeoJson(limb,highlight_function=lambda feature: {"fillColor": ("yellow"),},
                      popup=folium.GeoJsonPopup(fields=['UPDOWN',],aliases=["Move:",]),popup_keep_highlighted=False,
                      style_function=lambda feature: {"fillColor": fill,"color": c.col,"dashArray": "5, 5","weight": 3,"fillOpacity": 0.4,},
                      ).add_to(self.fg)

                    mapfile = "/map/"+c.dir+"/"+c.file


                    self.fg.add_child(folium.Marker(
                         location=here,
                         icon = folium.DivIcon(html="<a href='{0}' style='text-wrap: nowrap; font-size: 12pt; color: indigo'>{1}</b>\n".format(mapfile,numtag),
                         class_name = "leaflet-div-icon",
                         icon_size=(24,24),
                         icon_anchor=(14,40)),
                       )
                     )

        print("________Layer map polys",herenode.value,herenode.level,self.children, Featurelayers[herenode.level].children)

        return herenode

    def add_mapmarkers (self,herenode,type):
        global Treepolys
        global levelcolours
        global allelectors
        for c in herenode.childrenoftype(type):
            print('_______MAP Markers')
            layerfids = [x.fid for x in self.children if x.type == type]
            if c.fid not in layerfids:
                numtag = str(c.tagno)+" "+str(c.value)
                here = [ float('%.4f'%(c.centroid.y)),float('%.4f'%(c.centroid.x))]
                fill = levelcolours["C"+str(random.randint(4,15))]
                mapfile = "/map/"+c.dir+"/"+c.file
                print("______Display childrenx:",c.value, c.level,type,c.centroid )

                self.fg.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(html="<a href='{0}' style='text-wrap: nowrap; font-size: 12pt; color: indigo'>{1}</b>\n".format(mapfile,numtag),
                     class_name = "leaflet-div-icon",
                     icon_size=(24,24),
                     icon_anchor=(14,40)),
                   )
                 )

        print("________Layer map points",herenode.value,herenode.level,self.children, Featurelayers[herenode.level].children)

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
app.config['TEMPLATES_AUTO_RELOAD'] = True
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
#allelectors = pd.read_csv(workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])

mapfile = ""
Directories = {}
Con_Results_data = pd.read_csv(workdirectories['bounddir']+'/'+'HoC_General_Election_2024_Results.csv',sep='\t')
Con_Results_data = Con_Results_data.rename(columns = {'Constituency name': 'NAME'})
#        Con_Results_data = Con_Bound_layer.merge(Con_Results_data, how='left', on='NAME' )

print("_____Test Results data: ",Con_Results_data.columns)



longmean = statistics.mean([-7.57216793459,  1.68153079591])
latmean = statistics.mean([ 49.959999905, 58.6350001085])
roid = Point(longmean,latmean)
MapRoot = TreeNode("UNITED_KINGDOM",238, roid)
MapRoot.dir = "UNITED_KINGDOM"
MapRoot.file = "UNITED_KINGDOM-MAP.html"
Treepolys = [[],[],[],[],[],[]]
current_node = MapRoot
add_boundaries('country',MapRoot)
add_boundaries('nation',MapRoot)
MapRoot.create_map_branch('nation',allelectors)

Featurelayers[current_node.level].children = []
Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
Featurelayers[current_node.level].add_mapboundaries(current_node, 'nation')

map = MapRoot.create_area_map(Featurelayers,allelectors,"-MAP")
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
#    return render_template("Dash0.html", context = { "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

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
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route("/index", methods=['POST', 'GET'])
def index():
    global Treepolys
    global MapRoot
    global current_node

    current_node = MapRoot

    if 'username' in session:
        flash("__________Session Alive:"+ session['username'])
        print("__________Session Alive:"+ session['username'])

        return redirect (url_for('dashboard'))

    return render_template("index.html")


#login
@app.route('/login', methods=['POST', 'GET'])
def login():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment

    #collect info from forms in the login db
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
#check if it exists

    if not user:
        flash("_______ROUTE/login User not found", username)

        return render_template("index.html")
    elif user and user.check_password(password):

        session["username"] = username

        flash("_______ROUTE/login User found", session['username'])
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
        england = current_node
        for england in MapRoot.children:
            if england.value == 'ENGLAND':
                break

        add_boundaries('county',england)
        england.create_map_branch('county',allelectors)
        mapfile = current_node.dir+"/"+current_node.file
        return redirect(url_for('captains'))
    else:
        flash (' Not logged in ! ')

        return render_template("index.html")

    session['next'] = request.args.get('next')
    flash ('_____FLASH Found existing session ! ')

    return render_template ('index.html')

#dashboard

@app.route('/dashboard', methods=['GET','POST'])
def dashboard ():
    #formdata['username'] = session["username"]
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers


    mapfile  = current_node.dir+"/"+current_node.file
    if 'username' in session:
        flash('_______ROUTE/dashboard'+ session['username'] + ' is already logged in ')

        mapfile = current_node.dir+"/"+current_node.file
        redirect(url_for('captains'))
        return render_template("Dash0.html", context = {  "current_node" : current_node, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

    flash('_______ROUTE/dashboard no login session ')

    return redirect(url_for('index'))


@app.route('/downbut/<path:selnode>', methods=['GET','POST'])
def downbut(selnode):
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment
    global levels
    global Con_Results_data

    formdata = {}
# a down button on a node has been selected on the map, so the new map must be displayed with new down options

# the selected node has to be found from the selected button URL
    steps = selnode.split("/")
    last = steps.pop()

    current_node = selected_childnode(current_node,steps[-1])
    count = len(steps)
    atype = levels[count]
    if last.find(" ") > -1:
        atype = last.split(" ")[1]

# the map under the selected node map needs to be configured
    print("_________selected node",atype,steps,current_node.value, current_node.level,current_node.file)
# the selected  boundary options need to be added to the layer
    add_boundaries(atype,current_node)
    current_node.create_map_branch(atype,allelectors)
    Featurelayers[current_node.level].children = []
    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
    Featurelayers[current_node.level].add_mapboundaries(current_node, atype)
#    if current_node.level == 2:
#        Con_Results_data.columns = ["NAME","First party","Second party"]
#        Chorodata = Con_Results_data.rename(columns= {'First party': 'FIRST','Second party' : 'SECOND'})

#        Chorodata['NAME'] = Con_Results_data['NAME']
#        Chorodata['FIRST'] = Con_Results_data['First party'].index

#        folium.Choropleth(
#            geo_data=Treepolys[3],
#            data=Chorodata,
#            columns=["NAME", "FIRST"],
#            key_on="feature.properties.NAME",).add_to(current_node.map)

    map = current_node.create_area_map(Featurelayers,allelectors,"-MAP")
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

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/downPDbut/<path:selnode>', methods=['GET','POST'])
def downPDbut(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    global filename

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file
    frames = []
    PDArealist =[]

    Featurelayers[current_node.level].children = []
    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)

    if request.method == 'GET':
        print ("_________ROUTE/downPDbut", current_node.source, len(allelectors))
        if current_node.source == "" or len(allelectors) == 0:
            print ("_________Requestformfile",request.values['importfile'])
            flash ("_________Requestformfile"+request.values['importfile'])
            filename = request.values['importfile']
            allelectors = pd.read_csv(workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
            pfile = Treepolys[current_node.level]
            Level3boundary = pfile[pfile['FID']==current_node.fid]
            PDs = set(allelectors.PD.values)
            print("PDsfull", PDs)
            for PD in PDs:
              PDelectors = getblock(allelectors,'PD',PD)
              PDPtsdf0 = pd.DataFrame(PDelectors, columns=['PD', 'Long', 'Lat'])
              PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
              PDPtsdf = PDPtsdf1.groupby(['Name']).mean()
              maplongx = PDPtsdf.Long.values[0]
              maplaty = PDPtsdf.Lat.values[0]
            # for all PDs - pull together all PDs which are within the Conboundary constituency boundary
              if Level3boundary.geometry.contains(Point(float('%.4f'%(maplongx)),float('%.4f'%(maplaty)))).item():
                  Area = list(Level3boundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.replace(" ","_").str.upper())[0]
                  PDelectors['Area'] = Area
                  PDArealist.append((PD,Area, Level3boundary))
                  print("_______PDPoints",PDPtsdf)
                  newpd = current_node.create_data_branch('polling district',PDPtsdf.reset_index(),"-MAP")
                  frames.append(PDelectors)
                  Featurelayers[current_node.level].add_walkshape(newpd, 'polling district',PDelectors)
            allelectors = pd.concat(frames)
# if there is a selected file , then allelectors will be full of records

            areaelectors = getblock(allelectors, 'Area',current_node.value)

            current_node.source = filename
            map = current_node.create_area_map(Featurelayers,areaelectors,"-MAP")
            if len(allelectors) == 0 or len(Featurelayers[current_node.level].children) == 0:
                flash("Can't find any elector data for this Area.")
                allelectors = []
            else:
                flash("________PDs added  :  "+str(len(Featurelayers[current_node.level].children)))
                print("________PDs added  :  "+str(len(Featurelayers[current_node.level].children)))

        mapfile = current_node.dir+"/"+current_node.file
    return redirect(url_for('map',path=mapfile))
#    return render_template("dash1.html", context = {  "current_node" : current_node, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

@app.route('/PDshowST/<path:selnode>', methods=['GET','POST'])
def PDshowST(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    global environment
    global filename

    def firstnameinlist(name,list):
        posn = list.index(name)
        return list[posn]

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file
    frames = []

    PDArealist =[]
    if request.method == 'GET':
# if there is a selected file , then allelectors will be full of records
        PDelectors = getblock(allelectors, 'PD',current_node.value)

# we only want to plot with single streets , so we need to establish one street record with pt data to plot

        StreetPts = [(x[0],x[1],x[2]) for x in PDelectors[['StreetName','Long','Lat']].drop_duplicates().values]
        Streetdf0 = pd.DataFrame(StreetPts, columns=['Name', 'Long', 'Lat'])
        Streetdf = Streetdf0.groupby(['Name']).mean()

        Featurelayers[current_node.level].children = []
        Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)

        current_node.create_data_branch('street',Streetdf.reset_index(),"-PRINT")
        Featurelayers[current_node.level].add_mapmarkers(current_node, 'street')

        if len(allelectors) == 0 or len(Featurelayers[current_node.level].children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________streets added  :  "+str(len(Featurelayers[current_node.level].children)))
            print("________streets added  :  "+str(len(Featurelayers[current_node.level].children)))


        for street_node in current_node.childrenoftype('street'):
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
              if math.isnan(float('%.4f'%(electorwalks.Elevation.max()))):
                  climb = 0
              else:
                  climb = int(float('%.4f'%(electorwalks.Elevation.max())) - float('%.4f'%(electorwalks.Elevation.min())))

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

              datafile = street_node.dir+"/"+walk_name+"-DATA.html"
              mapfile = street_node.parent.dir+"/"+street_node.parent.file

#              map = street_node.create_area_map(Featurelayers,electorwalks)


              context = {
                "group": electorwalks,
                "prodstats": prodstats,
                "mapfile": url_for('map',path=mapfile),
                "datafile": url_for('map',path=datafile),
                "walkname": walk_name,
                }
              results_template = environment.get_template('canvasscard1.html')

              with open(results_filename, mode="w", encoding="utf-8") as results:
                results.write(results_template.render(context, url_for=url_for))

        map = current_node.create_area_map(Featurelayers,PDelectors,"-STREETS")
        mapfile = current_node.dir+"/"+current_node.file
        print ("________Heading for the Streets in PD :  ",current_node.value, current_node.file)
        if len(Featurelayers[current_node.level].children) == 0:
            flash("Can't find any Streets for this PD.")
        else:
            flash("________Streets added  :  "+str(len(Featurelayers[current_node.level].children)))


    return redirect(url_for('map',path=mapfile))

@app.route('/PDshowWK/<path:selnode>', methods=['GET','POST'])
def PDshowWK(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    global environment
    global filename

    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    frames = []

    PDArealist =[]
    if request.method == 'GET':
# if there is a selected file , then allelectors will be full of records
        PDelectors = getblock(allelectors, 'PD',current_node.value)
        print("________PDMarker",current_node.type,"|", current_node.dir, "|",current_node.file)

        x = PDelectors.Long.values
        y = PDelectors.Lat.values
        kmeans_dist_data = list(zip(x, y))

        walkset = min(math.ceil(PDelectors.shape[0]/100),35)

        kmeans = KMeans(n_clusters=walkset)
        kmeans.fit(kmeans_dist_data)

        klabels1 = np.char.mod('C%d', kmeans.labels_)
        klabels = klabels1.tolist()

        PDelectors.insert(0, "WalkName", klabels)

        walks = PDelectors.WalkName.unique()
        walkPts = [(x[0],x[1],x[2]) for x in PDelectors[['WalkName','Long','Lat']].drop_duplicates().values]
        walkdf0 = pd.DataFrame(walkPts, columns=['WalkName', 'Long', 'Lat'])
        walkdf1 = walkdf0.rename(columns= {'WalkName': 'Name'})
        walkdfs = walkdf1.groupby(['Name']).mean()
        print ("____________walks",walks)

# clear down the layer to which we want to add walks
        Featurelayers[current_node.level].children = []
        Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
#  add the walk nodes
        current_node.create_data_branch('walk',walkdfs.reset_index(),"-PRINT")

#        map = current_node.create_area_map(Featurelayers,PDelectors)
#        mapfile = current_node.dir+"/"+current_node.file


# for each walk node, add a walk node convex hull to the walk_node parent layer (ie current_node.level+1)
        for walk_node in current_node.childrenoftype('walk'):
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

              StreetPts = [(x[0],x[1],x[2]) for x in walkelectors[['StreetName','Long','Lat']].drop_duplicates().values]
              streetdf0 = pd.DataFrame(StreetPts, columns=['StreetName', 'Long', 'Lat'])
              streetdf1 = streetdf0.rename(columns= {'StreetName': 'Name'})
              streetdf = streetdf1.groupby(['Name']).mean()
              print ("____________walklegs",streetdf)


    # add walk legs for each street to the walk node

              current_node.create_data_branch('walkleg',streetdf.reset_index(),"-PRINT")

              type_colour = allowed[walk_node.value]

        #      marker_cluster = MarkerCluster().add_to(Walkmap)
              # Iterate through the street-postcode list and add a marker for each unique lat long, color-coded by its Cluster.

              Featurelayers[current_node.level].add_walkshape(walk_node, 'walk',walkelectors)
#              Featurelayers[walk_node.level+1].add_mapboundaries(walk_node, 'walk')


              for walkleg in walk_node.childrenoftype('walkleg'):
                    # in the Walk map add Street-postcode groups to the walk map with controls to go back up to the PD map or down to the Walk addresses
                    print("________WalklegMarker",walkleg.type,"|", walkleg.dir, "|",walkleg.file)
                    downtag = "<form action= '/downwalkbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(walkleg.dir+"/"+walkleg.file,"Streets",12)
                    uptag = "<form action= '/upwalkbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(walkleg.parent.dir+"/"+walkleg.parent.file,"Walks",12)
            #            Wardboundary['UPDOWN'] = "<br>"+walk_node.value+"<br>"+ uptag +"<br>"+ downtag
            #        c.tagno = len(self.children)+1
                    Postcode = walkelectors.loc[0].Postcode
#                    popuptext = '<ul style="font-size: {5}pt;color: gray;" >PD: {0} WalkNo: {1} Postcode: {2} {3} {4}</ul>'.format(walkleg.parent.value,walkleg.value, Postcode, uptag, downtag,12)

                    # in the PD map add PD-cluster walks to the PD map with controls to go back up to the Ward map or down to the Walk map
#                    Featurelayers[current_node.level+1].fg.add_child(
#                      folium.Marker(
#                         location=[walkleg.centroid.y,walkleg.centroid.x],
#                         popup = popuptext,
#                         icon=folium.Icon(color = type_colour,  icon='search'),
#                         )
#                         )
#                    popuptext = '<ul style="font-size: {5}pt;color: gray;" >Ward: {0} WalkNo: {1} Postcode: {2} {3} {4}</ul>'.format(walkleg.parent.parent.value,walkleg.value, Postcode, uptag, downtag,12)

#                    Featurelayers[current_node.level+1].fg.add_child(
#                        folium.Marker(
#                            location=[walkleg.centroid.y,walkleg.centroid.x],
#                            popup= popuptext,
#                            icon=folium.Icon(color = type_colour),
#                        )
#                        )
    #                map = walkleg.create_area_map(Featurelayers,PDelectors)

#              pclist = geo_df1.Postcode.tolist()
#              walklegs = zip(pclist,geo_df1_list)
#              plist =[]
#              walklegs_unique = []
#              for p,pt in walklegs:
#                  if p not in plist:
#                      plist.append(p)
#                      walklegs_unique.append([p,pt])



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
              if math.isnan(float('%.4f'%(walkelectors.Elevation.max()))):
                  climb = 0
              else:
                  climb = int(float('%.4f'%(walkelectors.Elevation.max())) - float('%.4f'%(walkelectors.Elevation.min())))

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
              prodstats['climb'] = climb
              prodstats['houses'] = houses
              prodstats['walks'] =  len(walks)
              prodstats['streets'] = streets
              prodstats['housedensity'] = housedensity
              prodstats['leafhrs'] = round(leafhrs,2)
              prodstats['canvasshrs'] = round(canvasshrs,2)

              walkelectors['ENOP'] =  walkelectors['ENO']+ walkelectors['Suffix']*0.1
              target = walk_node.locmappath("")
              results_filename = walk_name+"-PRINT.html"

              datafile = walk_node.dir+"/"+walk_name+"-DATA.html"
              mapfile = current_node.dir+"/"+current_node.file.replace("-MAP","-WALKS")

              context = {
                "group": walkelectors,
                "prodstats": prodstats,
                "mapfile": url_for('map',path=mapfile),
                "datafile": url_for('map',path=datafile),
                "walkname": walk_name,
                }
              results_template = environment.get_template('canvasscard1.html')

              with open(results_filename, mode="w", encoding="utf-8") as results:
                results.write(results_template.render(context, url_for=url_for))

        map = current_node.create_area_map(Featurelayers,PDelectors, "-WALKS")

        mapfile = current_node.dir+"/"+current_node.file

        if len(PDelectors) == 0 or len(Featurelayers[current_node.level].children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________walks added  :  "+str(len(Featurelayers[current_node.level].children)))
            print("________walks added  :  "+str(len(Featurelayers[current_node.level].children)))

    return redirect(url_for('map',path=mapfile))


@app.route('/layeritems/',methods=['GET','POST'])
def layeritems():
    global current_node

    flash('_______ROUTE/layeritems')


    layernodelist = Featurelayers[current_node.level].children
    current_node = current_node.parent
    mapfile = url_for('downbut',selnode=current_node.dir+"/"+current_node.file)
    print("________laynodelist", current_node.level, current_node.value, Featurelayers[current_node.level].children)
    return render_template("dash1.html", context = { "layernodelist" :layernodelist, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

@app.route('/upbut/<path:selnode>', methods=['GET','POST'])
def upbut(selnode):
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment
    flash('_______ROUTE/upbut',selnode)

    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
    print("_________current+parent_node",current_node.value, current_node.parent.value)
# the selected node has to be found from the selected button URL



    Featurelayers[current_node.level].children = []
    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)

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
    return render_template("Dash0.html", context = {  "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})
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
    flash('_______ROUTE/logout')


    print("Logout", session)
    if "username" in session:
        session.pop('username', None)
        logout_user()
        return "<h1> Hey - You are now logged out</h1>"
    return redirect(url_for('login'))

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
def map(path):
    global current_node
    flash ("_________ROUTE/map"+path)
    print ("_________Nextmap",path)
    steps = path.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])

    return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)


@app.route('/showmore/<path:path>', methods=['GET','POST'])
def showmore(path):
    global current_node

    flash ("_________ROUTE/showmore"+path)
    print ("_________showmore",path)

    return send_from_directory(app.config['UPLOAD_FOLDER'],path, as_attachment=False)


@app.route('/upload', methods=['POST','GET'])
def upload():
    flash('_______ROUTE/upload')


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

    flash('_______ROUTE/normalise',session)
    print('_______ROUTE/normalise',session)


    formdata = {}
    formdata['importfile'] = request.files['importfile']
    formdata['candfirst'] =  request.form["candfirst"]
    formdata['candsurn'] = request.form["candsurn"]
    formdata['electiondate'] = request.form["electiondate"]
    results = normalised.normz(formdata['importfile'], formdata)
    formdata = results[1]
    mapfile = current_node.dir+"/"+current_node.file
    group = results[0]
#    formdata['username'] = session['username']
    return render_template('Dash0.html', context = {  "session" : session, "formdata" : formdata, "group" : allelectors , "mapfile" : mapfile})

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
#    formdata['username'] = session['username']
        return render_template('Dash0.html', context = {  "session" : session, "formdata" : formdata, "group" : allelectors , "mapfile" : mapfile})
    return redirect(url_for('dashboard'))

@app.route('/postcode', methods=['POST','GET'])
def postcode():
    global current_node
    global Treepolys
    global Featurelayers
    global Directories
    global workdirectories
    flash('_______ROUTE/postcode')


    layernodelist = Featurelayers[current_node.level].children

    mapfile = url_for('downbut',selnode=current_node.dir+"/"+current_node.file)
    postcodeentry = request.form["postcodeentry"]
    if len(postcodeentry) > 8:
        postcodeentry = str(postcodeentry).replace(" ","")
    dfx = pd.read_csv(workdirectories['bounddir']+"National_Statistics_Postcode_Lookup_UK_20241022.csv")
    df1 = dfx[['Postcode 1','Latitude','Longitude']]
    df1 = df1.rename(columns= {'Postcode 1': 'Postcode', 'Latitude': 'Lat','Longitude': 'Long'})
    df1['Lat'] = df1['Lat'].astype(float)
    df1['Long'] = df1['Long'].astype(float)
    lookuplatlong = df1[df1['Postcode'] == postcodeentry]
    here = Point(float('%.4f'%(lookuplatlong.Long.values[0])),float('%.4f'%(lookuplatlong.Lat.values[0])))
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

@app.route('/captains', methods=['POST','GET'])
def captains():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment

    formdata = {}
    formdata['country'] = "UNITED_KINGDOM"
    flash('_______ROUTE/captains')
    print('_______ROUTE/captains')
    formdata['importfile'] = "Captains.xlsx"
    if len(request.form) > 0:
        formdata['importfile'] = request.files['importfile'].filename
    group = pd.read_excel(workdirectories['workdir']+"/"+formdata['importfile'])
    mapfile = current_node.dir+"/"+current_node.file
    return render_template("captains.html", context = {  "current_node" : current_node, "session" : session, "formdata" : formdata, "group" : group , "mapfile" : mapfile})


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
                return render_template('Dash0.html', context = { "current_node" : current_node, "session" : session, "formdata" : formdata, "group" : allelectors , "mapfile" : mapfile})
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
