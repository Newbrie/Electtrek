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

import sys
sys.path
sys.path.append('/Users/newbrie/Documents/ReformUK/GitHub/Electtrek/Electtrek.py')
print(sys.path)

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

def getlayeritems(nodelist):
    dfy = pd.DataFrame()
    i = 0
    for x in nodelist:
        dfy.loc[i,'No']= x.tagno
        for party in x.VI:
         dfy.loc[i,party] = x.VI[party]
        dfy.loc[i,x.type]=  x.value
        dfy.loc[i,x.parent.type] =  x.parent.value
        i = i + 1
    return dfy


def subending(filename, ending):
  stem = filename.replace("-MAP", "@@@").replace("-PRINT", "@@@").replace("-WALKS", "@@@").replace("-STREETS", "@@@")
  return stem.replace("@@@", ending)

VID = {"R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"Independent","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}
data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))


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
        self.bbox = [[],[]]
        self.map = {}
        self.source = ""
        self.VI = VIC.copy()

    def updateVI(self,viValue):
        print ("_____VIstatus:",self.value,self.type,self.VI)
        if self.type == 'street' or self.type == 'walk':
            sumnode = self
            for x in range(self.level+1):
                sumnode.VI[viValue] = sumnode.VI[viValue] + 1
                print ("_____VInode:",sumnode.value,sumnode.level,sumnode.VI)
                sumnode = sumnode.parent
        return

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
        geometry = gpd.points_from_xy(namepoints.Long.values,namepoints.Lat.values, crs="EPSG:4326")
        block = gpd.GeoDataFrame(
            namepoints, geometry=geometry
            )
        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]

        self.map = folium.Map(location=[self.centroid.y, self.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(min(self.level,5)+0.75)*2)))
        fam_nodes = self.childrenoftype(electtype)

        for index, limb  in namepoints.iterrows():
            datafid = abs(hash(limb.Name))
            newnode = TreeNode(limb.Name,datafid, Point(limb.Long,limb.Lat))
            newnode.source = self.source
            print('______Data nodes',newnode.value,newnode.fid, newnode.centroid)
            self.davail = True
            egg = self.add_Tchild(newnode, electtype)
            egg.file = subending(egg.file,ending)
            fam_nodes.append(egg)

        print('______Data frame:',namepoints, fam_nodes)
        return fam_nodes

    def create_map_branch(self,electtype):
        global Treepolys
        block = pd.DataFrame()
        self.bbox = self.get_bounding_box(block)[0]
        self.centroid = self.get_bounding_box(block)[1]
        ChildPolylayer = Treepolys[self.level+1]
#.cx[xmin:xmax, ymin:ymax]
        self.map = folium.Map(location=[self.centroid.y, self.centroid.x], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=int((4+(self.level+0.75)*2)))

        print("_______CXofTreepoly level", self.level+1, ChildPolylayer.shape)
        print ("________new branch elements in bbox:",self.value,self.level,"**", self.bbox)
    # there are 2-0 (3) relative levels - absolute level are UK(0),nations(1), constituency(2), ward(3)
        index = 0
        i = 0
        fam_nodes = self.childrenoftype(electtype)
        childtable = pd.DataFrame()
        if len(fam_nodes) == 0:
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

                    fam_nodes.append(self.add_Tchild(childnode,electtype))
#                    childtable.loc[i,'No']= i
#                    childtable.loc[i,electtype]=  childnode.value
#                    childtable.loc[i,self.type] =  self.value
                    i = i + 1

    #        for limb in fam_nodes:
    #            childtable.loc[i,'No']= i
    #            childtable.loc[i,limb.type]=  limb.value
    #            childtable.loc[i,self.type] =  self.value
    #            i = i + 1

        print ("_________fam_nodes :", fam_nodes )
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
      if self.level < 5:
          pfile = Treepolys[self.level]
          pb = pfile[pfile['FID']==self.fid]
          swne = pb.geometry.total_bounds
          swne = [swne[1],swne[0],swne[3],swne[2]]
          roid = pb.dissolve().centroid
          swne =[[float('%.6f'%(swne[0])),float('%.6f'%(swne[1]))],[float('%.6f'%(swne[2])),float('%.6f'%(swne[3]))]]
# minx, miny, maxx, maxy
          print("_______Bbox swnemap",swne, pb, self.fid, self.value, self.level)
      else:
#          swne = self.set_bounding_box(block)
          swne = block.geometry.total_bounds
          swne = [swne[1],swne[0],swne[3],swne[2]]
          roid = block.dissolve().centroid
          swne =[[float('%.6f'%(swne[0])),float('%.6f'%(swne[1]))],[float('%.6f'%(swne[2])),float('%.6f'%(swne[3]))]]
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
        child_node.file = child_node.value+"-MAP.html"
        child_node.tagno = len([ x for x in self.children if x.type == etype])
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
        World_Bound_layer = gpd.read_file(workdirectories['bounddir']+"/"+'World_Countries_(Generalized)_9029012925078512962.geojson', bbox=(-7.57216793459, 49.959999905, 1.68153079591, 58.6350001085))
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
        self.id = id

    def layeradd_walkshape (self,herenode,type,datablock):
        global Treepolys
        global levelcolours
        global allelectors

        def create_enclosing_gdf(gdf, buffer_size=0.0005):
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
                enclosed_shape = points[0].buffer(buffer_size)

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
                    enclosed_shape = p1.buffer(buffer_size)
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


            enclosing_gdf = gpd.GeoDataFrame(
                {"NAME":gdf.NAME, "FID":gdf.FID, "LAT":gdf.LAT.values[0],"LONG":gdf.LONG.values[0],"geometry": [enclosed_shape]},  # Assign shape as geometry
                crs=gdf.crs  # Use the same CRS as the input GeoDataFrame
            )

            return enclosing_gdf


        print('_______Walk Shape', herenode.value, herenode.level, herenode.fid, len(datablock))

        points = [Point(lon, lat) for lon, lat in zip(datablock['Long'], datablock['Lat'])]

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
        limb = create_enclosing_gdf(gdf)


        if type == 'polling district':
            showmessageST = "showMore(&#39;/PDshowST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('polling district'))
            downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
#            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,herenode.source, herenode.dir+"/"+herenode.file)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limb['UPDOWN'] = uptag1 +"<br>"+ downST+"<br>"+ downWK
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno, gdf)
        elif type == 'walk':
            showmessage = "showMore(&#39;/showmore/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file, herenode.value,getchildtype('walk'))
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
            downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limb['UPDOWN'] =  uptag1 +"<br>"+ downtag+"<br>"
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)


#        herenode.tagno = len(self.fg._children)+1
        numtag = str(herenode.tagno)+" "+str(herenode.value)
        num = str(herenode.tagno)
        tag = str(herenode.value)
        typetag = "from <br>"+str(herenode.type)+": "+str(herenode.value)+"<br> move :"
        here = [float('%.6f'%(herenode.centroid.y)),float('%.6f'%(herenode.centroid.x))]
        fill = levelcolours["C"+str(random.randint(4,15))]
        print("______addingPoly:",herenode.value, limb.NAME, here)
        mapfile = current_node.dir+"/"+current_node.file

#            self.children.append(herenode)

        folium.GeoJson(
            limb,
            smooth_factor=1,
            highlight_function=lambda feature: {"fillColor": "blue"},
            popup=folium.GeoJsonPopup(fields=['UPDOWN'], aliases=[typetag]),
            style_function=lambda feature: {
                "fillColor": fill,
                "color": herenode.col,
                "dashArray": "5, 5",
                "weight": 3,
                "fillOpacity": 0.4,
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
                        padding: 5px;
                        white-space: nowrap;">
                        <span style="background: black; padding: 1px 3px; border-radius: 5px;
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
        print('_______HereNode', herenode.value, herenode.level, herenode.fid)
        for c in [x for x in herenode.children if x.type == type]:
            print("______Display children:",herenode.value, herenode.level,type)
            print('_______MAPLinesandMarkers')
#            layerfids = [x.fid for x in self.children if x.type == type]
#            if c.fid not in layerfids:
            if c.level <= len(Treepolys)-1:
                pfile = Treepolys[c.level]
                limb = pfile[pfile['FID']==c.fid]
                if herenode.level == 0:
                    downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"COUNTIES",12)
#                    res = "<p  width=50 id='results' style='font-size: {0}pt;color: gray'> </p>".format(12)
                    limb['UPDOWN'] = "<br>"+c.value+"<br>"  + downtag
#                    c.tagno = len(self.fg._children)+1
                    print("_________new child boundary value and tagno:  ",c.type, c.value, c.tagno)
                    mapfile = "/map/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 1:
                    wardreportmess = "moveDown(&#39;/wardreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    divreportmess = "moveDown(&#39;/divreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype(c.type))
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
                    wardreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(wardreportmess,"WARD Report",12)
                    divreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(divreportmess,"DIV Report",12)
                    downconstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"CONSTITUENCIES",12)
                    uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                    limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ wardreporttag + divreporttag+"<br>"+ downconstag
#                    c.tagno = len(self.fg._children)+1
                    print("_________new split child boundary value and tagno:  ",c.type,c.value, c.tagno)
                    mapfile = "/map/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 2:
                    downwardmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" ward", c.value,"ward")
                    downdivmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file+" division", c.value,"division")
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
                    downwardstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downwardmessage,"WARDS",12)
                    downdivstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downdivmessage,"DIVS",12)
                    uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                    limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ downwardstag + " " + downdivstag
#                    c.tagno = len(self.fg._children)+1
                    print("_________new split child boundary value and tagno:  ",c.type, c.value, c.tagno)
                    mapfile = "/map/"+c.dir+"/"+c.file
#                        self.children.append(c)
                elif herenode.level == 3:
                    downPDmessage = "moveDown(&#39;/downPDbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file, c.value,getchildtype('ward/division'))
                    upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file, herenode.parent.value,herenode.parent.type)
                    PDbtn = "<input type='submit' form='uploadPD' value='Polling Districts' class='btn btn-norm' onclick='{0}'/>".format(downPDmessage)
                    upload = "<form id='uploadPD' action= '/downPDbut/{0}' method='GET'><input type='file' name='importfile' placeholder={2} style='font-size: {1}pt;color: gray' enctype='multipart/form-data'></input></form>".format(c.dir+"/"+c.file,12,c.source)
                    uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                    limb['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ upload+PDbtn
#                    c.tagno = len(self.fg._children)+1
                    print("_________new Ward value and tagno:  ",c.type,c.value, c.tagno, PDbtn)
                    mapfile = "/map/"+c.dir+"/"+c.file
#                        self.children.append(c)


                numtag = str(c.tagno)+" "+str(c.value)
                num = str(c.tagno)
                tag = str(c.value)
                here = [ float('%.6f'%(c.centroid.y)),float('%.6f'%(c.centroid.x))]
                fill = levelcolours["C"+str(random.randint(4,15))]
                print("______addingMarker:",c.value, limb.NAME)

                folium.GeoJson(limb,highlight_function=lambda feature: {"fillColor": ("yellow"),},
                  popup=folium.GeoJsonPopup(fields=['UPDOWN',],aliases=["Move:",]),popup_keep_highlighted=False,
                  style_function=lambda feature: {"fillColor": fill,"color": c.col,"dashArray": "5, 5","weight": 3,"fillOpacity": 0.4,},
                  ).add_to(self.fg)

                mapfile = "/map/"+c.dir+"/"+c.file


                self.fg.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(
                            html='''
                            <a href='{2}'><div style="
                                color: white;
                                font-size: 10pt;
                                font-weight: bold;
                                text-align: center;
                                padding: 5px;
                                white-space: nowrap;">
                                <span style="background: black; padding: 1px 3px; border-radius: 5px;
                                border: 2px solid black;">{0}</span>
                                {1}</div></a>
                                '''.format(num,tag,mapfile),

                               )
                               )
                               )


        print("________Layer map polys",herenode.value,herenode.level,self.fg._children, Featurelayers[herenode.level].fg._children)

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
            fill = levelcolours["C"+str(random.randint(4,15))]
            mapfile = str("/showmore/"+c.dir+"/"+c.file)

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
                            padding: 5px;
                            white-space: nowrap;">
                            <span style="background: black; padding: 1px 3px; border-radius: 5px;
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
PDelectors = pd.DataFrame()
layeritems = pd.DataFrame()
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
layeritems = getlayeritems(MapRoot.create_map_branch('nation'))

Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
Featurelayers[current_node.level].layeradd_nodemaps(current_node, 'nation')

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
#    """Return JSON instead of HTML for HTTP errors."""
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
    global layeritems

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
        england.create_map_branch('county')
        layeritems = getlayeritems(england.create_map_branch('county'))
        mapfile = current_node.dir+"/"+current_node.file
        return redirect(url_for('candidates'))
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
    global layeritems

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

    layeritems = getlayeritems(current_node.create_map_branch(atype))
    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
    Featurelayers[current_node.level].layeradd_nodemaps(current_node, atype)
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
    global layeritems

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file


    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)

    if request.method == 'GET':
        print ("_________ROUTE/downPDbut", current_node.source, len(allelectors))
        if len(current_node.childrenoftype('polling district')) == 0:
            print ("_________Requestformfile",request.values['importfile'])
            flash ("_________Requestformfile"+request.values['importfile'])
            filename = request.values['importfile']
            allelectors = pd.read_csv(workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
            current_node.source = filename
            allelectors['VI'] = ""

        pfile = Treepolys[current_node.level]
        Level3boundary = pfile[pfile['FID']==current_node.fid]
        PDs = set(allelectors.PD.values)
        print("PDsfull", PDs)
#            Featurelayers[current_node.level].fg._children.extend(PDnodelist)
        frames = []
#            Dont know if PDs are within selected ward yet.
        for PD in PDs:
          PDnodeelectors = getblock(allelectors,'PD',PD)
          maplongx = PDnodeelectors.Long.values[0]
          maplaty = PDnodeelectors.Lat.values[0]

        # for all PDs - pull together all PDs which are within the Conboundary constituency boundary
          if Level3boundary.geometry.contains(Point(float('%.6f'%(maplongx)),float('%.6f'%(maplaty)))).item():
              Area = list(Level3boundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.replace(" ","_").str.upper())[0]
              allelectors['Area'] = Area
              frames.append(PDnodeelectors)

        print("_______displayed PD markers",Featurelayers[current_node.level].fg._children)
        allelectors = pd.concat(frames)
        PDPtsdf0 = pd.DataFrame(allelectors, columns=['PD', 'Long', 'Lat'])
        PDPtsdf1 = PDPtsdf0.rename(columns= {'PD': 'Name'})
        PDPtsdf = PDPtsdf1.groupby(['Name']).mean()
        if len(current_node.childrenoftype('polling district')) == 0:
            WardPDnodelist = current_node.create_data_branch('polling district',PDPtsdf.reset_index(),"-MAP")
    # if there is a selected file , then allelectors will be full of records
            for PD_node in WardPDnodelist:
                  PDnodeelectors = getblock(allelectors,'PD',PD_node.value)
                  Featurelayers[current_node.level].layeradd_walkshape(PD_node, 'polling district',PDnodeelectors)
                  print("_______new PD Display node",PD_node,"|", Featurelayers[current_node.level].fg._children)

#            areaelectors = getblock(allelectors,'Area',current_node.value)

        if len(allelectors) == 0 or len(Featurelayers[current_node.level].fg._children) == 0:
            flash("Can't find any elector data for this Area.")
        else:
            map = current_node.create_area_map(Featurelayers,allelectors,"-MAP")
            flash("________PDs added  :  "+str(len(Featurelayers[current_node.level].fg._children)))
            print("________PDs added  :  "+str(len(Featurelayers[current_node.level].fg._children)))

        mapfile = current_node.dir+"/"+current_node.file
        layeritems = getlayeritems(current_node.childrenoftype('polling district'))
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)
#    return redirect(url_for('map',path=mapfile))
#    return render_template("dash1.html", context = {  "current_node" : current_node, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})
@app.route('/STupdate/<path:selnode>', methods=['GET','POST'])
def STupdate(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    global PDelectors
    global environment
    global filename
    global layeritems
#    steps = selnode.split("/")
#    filename = steps.pop()
#    current_node = selected_childnode(current_node,steps[-1])
    steps = selnode.split("/")
    leaves = steps.pop().split("-")
    current_node = selected_childnode(current_node,leaves[1])

    street_node = current_node
    mapfile = current_node.dir+"/"+current_node.file


    if request.method == 'POST':
    # Get JSON data from request
#        VIdata = request.get_json()  # Expected format: {'viData': [{...}, {...}]}
        try:
            VIdata = request.get_json()
            if VIdata is None:
                raise ValueError("No JSON received")
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            return jsonify({"error": "Invalid JSON"}), 400
        if "viData" in VIdata and isinstance(VIdata["viData"], list):  # Ensure viData is a list
            for item in VIdata["viData"]:  # Loop through each elector entry
                electIDpair = str(item.get("electorID")).strip().split(".")
                suffix = int(electIDpair.pop())# Extract suffix as string and convert to int
                electID = int(electIDpair.pop())# Extract elector ID as string and convert to int
                VI_value = item.get("viResponse", "").strip()  # Extract viResponse
                print("____Received electIDpair",electIDpair,electID,suffix)
                if suffix == 0:
                    if not electID:  # Skip if electorID is missing
                        print("Skipping entry with missing electorID")
                        continue
                    print("_____columns:",PDelectors.columns)
                    # Find the row where ENO matches electID
                    selected = PDelectors.query("ENO == @electID")

                    if not selected.empty:
                        # Update only if viResponse is non-empty
                        if VI_value:
                            allelectors.loc[selected.index, "VI"] = VI_value
                            current_node.updateVI(VI_value)
                            print(f"Updated elector {electID} with VI = {VI_value}")
                            print("ElectorVI", allelectors.loc[selected.index, "ENO"], PDelectors.loc[selected.index, "VI"])
                        else:
                            print(f"Skipping elector {electID}, empty viResponse")
                    else:
                        print(f"Warning: No match found for ENO = {electID}")
                else:
                        print(f"Warning: Suffix > 0 = {suffix}")

        else:
            print("Error: Incorrect JSON format")

    print("_____Where are we: ", current_node.value, current_node.type, PDelectors.columns)

    street = current_node.value
    electorwalks = pd.DataFrame()

    if current_node.type == 'street':
        electorwalks = getblock(PDelectors, 'StreetName',current_node.value)
    elif current_node.type == 'walk':
        electorwalks = getblock(PDelectors,'WalkName',current_node.value)

    if electorwalks.empty:
        print("⚠️ Error: electorwalks DataFrame is empty!", current_node.value)
        return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


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
    prodstats['groupelectors'] = groupelectors
    prodstats['climb'] = climb
    prodstats['houses'] = houses
    prodstats['streets'] = streets
    prodstats['housedensity'] = housedensity
    prodstats['leafhrs'] = round(leafhrs,2)
    prodstats['canvasshrs'] = round(canvasshrs,2)

    electorwalks['ENOP'] =  electorwalks['ENO']+ electorwalks['Suffix']*0.1
    target = current_node.locmappath("")
    results_filename = walk_name+"-PRINT.html"

    datafile = current_node.dir+"/"+walk_name+"-DATA.html"


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
    #           only create a map if the branch does not already exist
    current_node = current_node.parent
    if current_node.type == 'street':
        layeritems = getlayeritems(current_node.childrenoftype('street'))
    elif current_node.type == 'walk':
        layeritems = getlayeritems(current_node.childrenoftype('walk'))
    mapfile = current_node.dir+"/"+current_node.file
    return  jsonify({"message": "Success", "file": url_for('map', path=mapfile)})


@app.route('/PDshowST/<path:selnode>', methods=['GET','POST'])
def PDshowST(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    global PDelectors
    global environment
    global filename
    global layeritems

    def firstnameinlist(name,list):
        posn = list.index(name)
        return list[posn]

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file
    frames = []

    PDelectors = getblock(allelectors, 'PD',current_node.value)
    if request.method == 'GET':
        if len(current_node.childrenoftype('street')) == 0:

    # we only want to plot with single streets , so we need to establish one street record with pt data to plot

            StreetPts = [(x[0],x[1],x[2]) for x in PDelectors[['StreetName','Long','Lat']].drop_duplicates().values]
            Streetdf0 = pd.DataFrame(StreetPts, columns=['Name', 'Long', 'Lat'])
            Streetdf = Streetdf0.groupby(['Name']).mean()

            if len(current_node.childrenoftype('street')) == 0:
                Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
                streetnodelist = current_node.create_data_branch('street',Streetdf.reset_index(),"-PRINT")
                Featurelayers[current_node.level].layeradd_nodemarks(current_node, 'street')

            if len(allelectors) == 0 or len(Featurelayers[current_node.level].fg._children) == 0:
                flash("Can't find any elector data for this Polling District.")
                print("Can't find any elector data for this Polling District.")
            else:
                flash("________streets added  :  "+str(len(Featurelayers[current_node.level].fg._children)))
                print("________streets added  :  "+str(len(Featurelayers[current_node.level].fg._children)))


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
    #           only create a map if the branch does not already exist
            map = current_node.create_area_map(Featurelayers,PDelectors,"-STREETS")
    layeritems = getlayeritems(current_node.childrenoftype('street'))
    current_node.file = subending(current_node.file,"-STREETS")
    mapfile = current_node.dir+"/"+current_node.file
    print ("________Heading for the Streets in PD :  ",current_node.value, current_node.file)
    if len(Featurelayers[current_node.level].fg._children) == 0:
        flash("Can't find any Streets for this PD.")
    else:
        flash("________Streets added  :  "+str(len(Featurelayers[current_node.level].fg._children)))

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/PDshowWK/<path:selnode>', methods=['GET','POST'])
def PDshowWK(selnode):
    global Treepolys
    global current_node
    global Featurelayers
    global workdirectories
    global allelectors
    global PDelectors
    global environment
    global filename
    global layeritems

    allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    frames = []

    PDelectors = getblock(allelectors, 'PD',current_node.value)
    if request.method == 'GET':
# if there is a selected file , then allelectors will be full of records
        if len(current_node.childrenoftype('walk')) == 0:
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
            print ("____________walks",walkdfs)

    # clear down the layer to which we want to add walks
            if len(current_node.childrenoftype('walk')) == 0:
                Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)
        #  add the walk nodes
                walknodelist = current_node.create_data_branch('walk',walkdfs.reset_index(),"-PRINT")

        #        map = current_node.create_area_map(Featurelayers,PDelectors)
        #        mapfile = current_node.dir+"/"+current_node.file

    # for each walk node, add a walk node convex hull to the walk_node parent layer (ie current_node.level+1)
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

                  StreetPts = [(x[0],x[1],x[2]) for x in walkelectors[['StreetName','Long','Lat']].drop_duplicates().values]
                  streetdf0 = pd.DataFrame(StreetPts, columns=['StreetName', 'Long', 'Lat'])
                  streetdf1 = streetdf0.rename(columns= {'StreetName': 'Name'})
                  streetdf = streetdf1.groupby(['Name']).mean()
                  print ("____________walklegs",streetdf)

        # add walk legs for each street to the walk node

                  streetnodelist = walk_node.create_data_branch('walkleg',streetdf.reset_index(),"-PRINT")

                  type_colour = allowed[walk_node.value]

            #      marker_cluster = MarkerCluster().add_to(Walkmap)
                  # Iterate through the street-postcode list and add a marker for each unique lat long, color-coded by its Cluster.

                  Featurelayers[current_node.level].layeradd_walkshape(walk_node, 'walk',streetdf.reset_index())
    #              Featurelayers[walk_node.level+1].layeradd_nodemaps(walk_node, 'walk')
                  print("_______new Walk Display node",walk_node,"|", Featurelayers[current_node.level].fg._children)


                  for walkleg in walk_node.childrenoftype('walkleg'):
                        # in the Walk map add Street-postcode groups to the walk map with controls to go back up to the PD map or down to the Walk addresses
                    print("________WalklegMarker",walkleg.type,"|", walkleg.dir, "|",walkleg.file)
                    downtag = "<form action= '/downwalkbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(walkleg.dir+"/"+walkleg.file,"Streets",12)
                    uptag = "<form action= '/upwalkbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(walkleg.parent.dir+"/"+walkleg.parent.file,"Walks",12)
                #            Wardboundary['UPDOWN'] = "<br>"+walk_node.value+"<br>"+ uptag +"<br>"+ downtag
                #        c.tagno = len(self.children)+1
                    Postcode = walkelectors.loc[0].Postcode

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
                  current_node.file = subending(current_node.file,"-WALKS")
                  mapfile = current_node.dir+"/"+current_node.file

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
#           only create a map file if branch does not already exist
            map = current_node.create_area_map(Featurelayers,PDelectors, "-WALKS")


        layeritems = getlayeritems(current_node.childrenoftype('walk'))
        current_node.file = subending(current_node.file,"-WALKS")
        mapfile = current_node.dir+"/"+current_node.file
        if len(PDelectors) == 0 or len(Featurelayers[current_node.level].fg._children) == 0:
            flash("Can't find any elector data for this Polling District.")
            print("Can't find any elector data for this Polling District.")
        else:
            flash("________walks added  :  "+str(len(Featurelayers[current_node.level].fg._children)))
            print("________walks added  :  "+str(len(Featurelayers[current_node.level].fg._children)))

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)


@app.route('/wardreport/<path:selnode>',methods=['GET','POST'])
def wardreport(selnode):
    global current_node
    global layeritems

    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])

    flash('_______ROUTE/wardreport')
    print('_______ROUTE/wardreport')
    mapfile = current_node.dir+"/"+current_node.file
    print("________layeritems  :  ", layeritems)

    i = 0
    alreadylisted = []
    add_boundaries('constituency',current_node)

    layeritems = getlayeritems(current_node.create_map_branch('constituency'))
    for group_node in current_node.childrenoftype('constituency'):
        add_boundaries('ward',group_node)

        layeritems = getlayeritems(group_node.create_map_branch('ward'))

        for item in group_node.childrenoftype('ward'):
            if item.value not in alreadylisted:
                alreadylisted.append(item.value)
                layeritems.loc[i,'No']= i
                layeritems.loc[i,'Area']=  item.value
                layeritems.loc[i,'Constituency']=  group_node.value
                layeritems.loc[i,'Candidate']=  "Joe Bloggs"
                layeritems.loc[i,'Email']=  "xxx@reforumuk.com"
                layeritems.loc[i,'Mobile']=  "07789 342456"
                i = i + 1
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)
#  #    mapfile = current_node.parent.dir+"/"+current_node.parent.file
#    print("________layeritems  :  ", layeritems)

#    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)
#    return redirect(url_for('map',path=mapfile))


@app.route('/displayareas',methods=['POST', 'GET'])
def displayareas():
    global layeritems
    print('_______ROUTE/displayareas')
    json_data = layeritems.to_json(orient='records', lines=False)
    # Convert JSON string to Python list
    python_data = json.loads(json_data)
    # Return the Python list using jsonify
    print('_______ROUTE/displayarea data', python_data)
    return  jsonify(python_data)
#    return render_template("Areas.html", context = { "layeritems" :layeritems, "session" : session, "formdata" : formdata, "allelectors" : allelectors , "mapfile" : mapfile})

@app.route('/divreport/<path:selnode>',methods=['GET','POST'])
def divreport(selnode):
    global current_node
    global layeritems


    steps = selnode.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    mapfile = current_node.dir+"/"+current_node.file

    flash('_______ROUTE/divreport')
    print('_______ROUTE/divreport')

    i = 0
    layeritems = pd.DataFrame()
    alreadylisted = []
    add_boundaries('constituency',current_node)

    layeritems = getlayeritems(current_node.create_map_branch('constituency'))

    for group_node in current_node.childrenoftype('division'):
        add_boundaries('division',group_node)

        layeritems = getlayeritems(group_node.create_map_branch('division'))

        for item in Featurelayers[group_node.level].fg._children:
            if item.value not in alreadylisted:
                alreadylisted.append(item.value)
                layeritems.loc[i,'No']= i
                layeritems.loc[i,'Area']=  item.value
                layeritems.loc[i,'Constituency']=  group_node.value
                layeritems.loc[i,'Candidate']=  "Joe Bloggs"
                layeritems.loc[i,'Email']=  "xxx@reforumuk.com"
                layeritems.loc[i,'Mobile']=  "07789 342456"
                i = i + 1

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/upbut/<path:selnode>', methods=['GET','POST'])
def upbut(selnode):
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment
    global layeritems

    flash('_______ROUTE/upbut',selnode)

    formdata = {}
# a up button on a node has been selected on the map, so the parent map must be displayed with new up/down options
# the selected node has to be found from the selected button URL
#
#    Featurelayers[current_node.level].fg = folium.FeatureGroup(id=str(current_node.level+1),name=Featurelayers[current_node.level].name, overlay=True, control=True, show=True)

    layeritems = getlayeritems(current_node.parent.childrenoftype(current_node.type))

    current_node = current_node.parent
    print("_________current+parent_node",current_node.value, current_node.parent.value)
# the selected  boundary options need to be added to the layer
    mapfile = current_node.dir+"/"+current_node.file
# the selected node boundary options need to be added to the layer

    #formdata['username'] = session["username"]
    formdata['country'] = 'UNITED_KINGDOM'
    formdata['candfirst'] = "Firstname"
    formdata['candsurn'] = "Surname"
    formdata['electiondate'] = "DD-MMM-YY"
    formdata['filename'] = "NONE"

    print("________chosen node url",mapfile)

    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)
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
    steps = path.split("/")
    steps.pop()
    current_node = selected_childnode(current_node,steps[-1])
    flash ("_________ROUTE/map"+path)
    print ("_________ROUTE/map",path, current_node.dir)

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
    global layeritems

    formdata = {}
    formdata['country'] = "UNITED_KINGDOM"
    flash('_______ROUTE/captains')
    print('_______ROUTE/captains')
    formdata['importfile'] = "Captains.xlsx"
    if len(request.form) > 0:
        formdata['importfile'] = request.files['importfile'].filename
    layeritems = pd.read_excel(workdirectories['workdir']+"/"+formdata['importfile'])
    mapfile = current_node.dir+"/"+current_node.file
    return send_from_directory(app.config['UPLOAD_FOLDER'],mapfile, as_attachment=False)

@app.route('/candidates', methods=['POST','GET'])
def candidates():
    global workdirectories
    global Directories
    global MapRoot
    global current_node
    global allelectors
    global Treepolys
    global Featurelayers
    global environment
    global layeritems

    formdata = {}
    formdata['country'] = "UNITED_KINGDOM"
    flash('_______ROUTE/candidates')
    print('_______ROUTE/candidates')
    formdata['importfile'] = "SCC-CandidateSelection.xlsx"
    if len(request.form) > 0:
        formdata['importfile'] = request.files['importfile'].filename
    layeritems = pd.read_excel(workdirectories['workdir']+"/"+formdata['importfile'])
    mapfile = current_node.dir+"/"+current_node.file
    return render_template("candidates.html", context = {  "session" : session, "formdata" : formdata, "group" : layeritems , "mapfile" : mapfile})


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
