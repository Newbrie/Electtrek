import folium
from json import JSONEncoder
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
import numpy as np
import statistics
from sklearn.cluster import KMeans
from IPython.display import HTML, display
import io
from PIL import Image
import re
from decimal import Decimal
import matplotlib.path as mpltPath
from pyproj import Proj
from flask import Flask,render_template
import os, sys, math, stat, json , jinja2
from os import listdir, system
templdir = "/Users/newbrie/Documents/ReformUK/GitHub/ElectorWalks/templates"
workdir = "/Users/newbrie/Sites"
bounddir = "/Users/newbrie/Documents/ReformUK/Code/Boundaries"


from flask import Flask
from markupsafe import escape

app = Flask(__name__)

@app.route("/<name>")

def hello(name):
    return f"Hello, {escape(name)}!"

class TreeNode:
    def __init__(self, data):
        self.data = data
        self.children = []
    def add_child(self, child):
        self.children.append(child)



root = TreeNode("UK Parliamentary Constituencies")

# Add children to root

fg0 = folium.FeatureGroup(name='Street-Postcodes', overlay=True, control=True, show=True)
fg1 = folium.FeatureGroup(name='Constituency Boundaries', overlay=True, control=True, show=True)
fg4 = folium.FeatureGroup(name='Ward Boundaries', overlay=True, control=True, show=True)
fg5 = folium.FeatureGroup(name='Division Boundaries', overlay=True, control=True, show=True)

# fg1/2/3 list maintains a cumulative list of ward and div boundaries to be added as the constituency poly layer in f4 anf f5
# fg2w/p/c fg3w/p/c are overwritten single value poly + div polygons added to each Ward , PDmap and Walk maps - no lists needed
fg1list = []
fg2list = []
fg3list = []
DivMapfilelist = []

# for each group of electorwalks create a MAP and TEXT file.

from jinja2 import Environment, FileSystemLoader


def square_area(lats,lons):
# Returns the area in square meters of a lat long spheriod coonverted to a trapezium abcd (anto-clockwise labelled from minmin)
  xs,ys = reproject(lats, lons)
  print("lat,lon:",lats,lons)
  print("xs,ys:",xs,ys)
# trapezium is half (ab+cd)*average diff of ys
  ab = np.diff(xs)
  cd = ab
  h = np.diff(ys)
  if lats[0] == lats[1]:
    areamsq = [50*50]
  else:
    areamsq = (ab+cd)*h/2
  print("ab,cd,h,areamsq:",ab,cd,h,areamsq)
  return areamsq[0]

def getblock(source,joincol, colvalue):
  colvalfilter = pd.DataFrame([[colvalue]], columns=[joincol])
# create a group dataframe based on a filtering join of a column value of all electors
  group = pd.merge(source, colvalfilter, on=joincol)
  return(group)

def locmappath(target,real):
  if real == "":
    if not os.path.exists(target):
      os.mkdir(target)
      print("Folder %s created!" % target)
    else:
      print("Folder %s already exists" % target)
  else:
    if not os.path.exists(target):
      os.system("ln -s "+real+" "+ target)
      print("Symbolic Folder %s created!" % target)
    else:
      print("Folder %s already exists" % target)
  os.system("cd -P target")
  return target

def create_area_map (map_title,subset,zoom):
  maplongx = statistics.mean(subset.Long.values)
  maplaty = statistics.mean(subset.Lat.values)
  subsetmap = folium.Map(location=[maplaty, maplongx], trackResize = "false",tiles="OpenStreetMap", crs="EPSG3857",zoom_start=zoom)
  sw = subset[['Lat', 'Long']].min().values.tolist()
  ne = subset[['Lat', 'Long']].max().values.tolist()
  subsetmap.fit_bounds([sw, ne], padding = (20, 20))

  title_html = '''<h1 style="z-index:1200;color: black;position: fixed;left:150px;"></h1>'''.format(map_title)
  subsetmap.get_root().html.add_child(folium.Element(title_html))

  return subsetmap

def create_div_map(map_title,geom,zoom):
  print("CreateDiv",geom.bounds['maxx'].values,geom.representative_point().get_coordinates().values[0])
  Dmap = folium.Map(location=geom.representative_point().get_coordinates().values.tolist()[0], trackResize = "true",tiles="OpenStreetMap", zoom_start=zoom)
  title_html = '''<h1 style="z-index:1200;color: black;position:absolute;left:150px;">{}</h1>'''.format(map_title)
  Dmap.get_root().html.add_child(folium.Element(title_html))
  sw = [geom.bounds['miny'].values[0],geom.bounds['minx'].values[0]]
  ne = [geom.bounds['maxy'].values[0],geom.bounds['maxx'].values[0]]
  Dmap.fit_bounds([sw,ne], padding = (30, 30))

  return Dmap

def find_boundary(polyfile,here):
  for index, ppath in polyfile.iterrows():
    path = ppath['geometry']
    if path.contains(here):
      return polyfile[polyfile['FID']==index+1]
  return

def goup (startpoint, upfile, text, size):
  returnfile = ""
  if startpoint == "CON":
    returnfile = "../"+upfile
  elif startpoint == "WARD":
    returnfile = "../"+upfile
  elif startpoint == "DIV":
    returnfile = "../"+upfile
  elif startpoint == "DIVPD":
    returnfile = "../"+upfile
  elif startpoint == "PD" :
    returnfile = "../"+upfile
  elif startpoint == "WALK" :
    returnfile = "../"+upfile
  elif startpoint == "STREET" :
    returnfile = "../"+upfile

  print("ReturnfileUp:", startpoint, returnfile)
  return "<form action= '{0}' ><button type='submit' style='font-size: {2}pt;'>{1}</button></form>".format(returnfile,text, size)


def godown (startpoint,name,text,size):
  returnfile = ""
  if startpoint == "COUNTY" :
    returnfile =  name+"/"+name+"-MAP.html"
  if startpoint == "CON" :
    returnfile =  name+"/"+name+"-MAP.html"
  elif startpoint == "WARD":
    returnfile =  name+"/"+name+"-MAP.html"
  elif startpoint == "DIV":
    returnfile =  name+"/"+name+"-MAP.html"
  elif startpoint ==  "PD":
    returnfile =   name.split("-")[1]+"/"+name.split("-")[0]+"-"+name.split("-")[1]+"-MAP.html"
  elif startpoint == "WALK" :
    returnfile =   name.split("-")[0]+"-"+name.split("-")[1]+"-TEXT.html"
  elif startpoint ==  "STREET":
    returnfile =  name.split("-")[0]+"-"+name.split("-")[1]+"-TEXT.html"
  print("ReturnfileDown:", startpoint, returnfile)
  return "<form action= '{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(returnfile,text,size)


def add_to_con_layer(boundary,uptag,layer):
  if boundary.iloc[0]['FID'] not in fg1list:
    fg1list.append(boundary.iloc[0]['FID'])
    print("FG1 Poly details:",boundary)
    folium.GeoJson(boundary,highlight_function=lambda feature: {"fillColor": ("green"),},
      popup=folium.GeoJsonPopup(fields=[uptag,],aliases=["Move:",]),popup_keep_highlighted=True,
      style_function=lambda feature: {"fillColor": "indigo","color": "indigo","weight": 3,"fillOpacity": 0.1,},
      ).add_to(layer)
  return

def TabletoDF (T):
# extract into a dataframe from all column names in meta and attrubute section from the source Orange Table
  block = T
  domain = block.domain
  vars = []
  vars_ = []

  varvalues = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
  tvx = block.Y.shape[1]
  tvy = block.X.shape[1]
  tvm = block.metas.shape[1]

  for d in domain:
    print ("-",d)
  for d in domain:
    vars.append(d.name)
    vars_.append(d.name.replace(" ","_"))

  DF = pd.DataFrame()
  # for every elector in the block extract the variable values into a dataframe
  i = 0
  for var in vars:
      for elector in block:
        varvalues[i].append(elector[var].value)
      DF.insert(i, vars_[i], varvalues[i])
      i=i+1

  return DF

allelectors = TabletoDF (in_data)

Clabel = DiscreteVariable("Clabel", values={"C0","C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12","C13","C14","C15","C16","C17","C18","C19","C20","C21","C22","C23","C24","C25","C26","C27","C28","C29","C30","C31","C32","C33","C34","C35","C36","C37"})

#domain = in_data.domain
#new_domain1 = Domain(attributes=domain.attributes + (Clabel,), metas=domain.metas , class_vars=domain.class_vars)

#newblock = in_data.transform(new_domain1)
Country_Bound_layer = gpd.read_file(bounddir+"/"+'Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson')

County_Bound_layer = gpd.read_file(bounddir+"/"+'Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson')

Division_Bound_layer = gpd.read_file( bounddir+"/"+'County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson')

Con_Bound_layer = gpd.read_file(bounddir+"/"+'Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson')

Country_Long = -0.562301
Country_Lat = 51.240299
Countryboundary = find_boundary(Country_Bound_layer,Point(Decimal(Con_Long),Decimal(Con_Lat)))
country = list(Country_Bound_layer['PCON24NM'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.upper())[0]
print("Country",country)
Codir = locmappath(workdir+"/"+str(country),"")
Ward_Bound_layer = gpd.read_file(bounddir+"/"+'Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson')

CountryMapfile = country+"-MAP.html"
Countrymap = create_area_map ("UK Pariamentary Constituencies", allelectors,11)
Countrymap.save(CountryMapfile)
