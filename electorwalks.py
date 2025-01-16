import folium
from json import JSONEncoder
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np
import os, sys, math, stat, json , jinja2
from os import listdir, system
import statistics
from sklearn.cluster import KMeans
import io
#from PIL import Image
import re
from decimal import Decimal
from pyproj import Proj
from flask import Flask,render_template, url_for


def prodwalks(current_node, filename, normstats):
    global workdirectories
    global Directories
    global MapRoot
    global allelectors
    global TreeNode

    def goup (startpoint, name, text, size):
      returnfile = ""
      name = name.replace(r'[^A-Za-z0-9\&\ ]+', '').replace(" & "," AND ").replace(",","").replace(" ","_").upper()
      if startpoint == "COUNTY" :
        returnfile =  "../"+name+"-MAP.html"
      if startpoint == "CON":
        returnfile = "../"+name+"-MAP.html"
      elif startpoint == "WARD":
        returnfile = "../"+name+"-MAP.html"
      elif startpoint == "DIV":
        returnfile = "../"+name+"-MAP.html"
      elif startpoint == "DIVPD":
        returnfile = "../"+name+"-MAP.html"
      elif startpoint == "PD" :
        returnfile = "../"+name+"-MAP.html"
      elif startpoint == "WALK" :
        returnfile = "../"+name+"-MAP.html"
      elif startpoint == "STREET" :
        returnfile = "../"+name+"-MAP.html"

      print("ReturnfileUp:", startpoint, returnfile)
      return "<form action= '{0}' ><button type='submit' style='font-size: {2}pt;'>{1}</button></form>".format(returnfile,text, size)


    def godown (startpoint,name,text,size):
      returnfile = ""
      name = name.replace(r'[^A-Za-z0-9\&\ ]+', '').replace(" & "," AND ").replace(",","").replace(" ","_").upper()
      if startpoint == "COUNTRY" :
        returnfile =  name+"/"+name+"-MAP.html"
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

    def add_to_top_layer(layerlist, boundary,uptag,layer):
        def lookupcol(dict, item):
            if item in dict:
                return dict[item]
            else:
                return 'gray'
        print("FG0 Poly details:",boundary)
        flag = { "England":'white', "Wales":'red', "Scotland":'darkblue',  "Northern Ireland": 'green' }
        if boundary.iloc[0]['FID'] not in layerlist:
            layerlist.append(boundary.iloc[0]['FID'])
            folium.GeoJson(boundary,highlight_function=lambda feature: {"fillColor": ("yellow"),},
                popup=folium.GeoJsonPopup(fields=[uptag,],aliases=["Move5:",]),popup_keep_highlighted=True,
                style_function=lambda feature: {"fillColor": lookupcol(flag,boundary.iloc[0]['NAME']),"color": "indigo","weight": 2,"fillOpacity": 0.5,},
                ).add_to(layer)
        return


    def find_boundary(polyfile,here):
        for index, ppath in polyfile.iterrows():
            path = ppath['geometry']
            if here.within(path):
                if 'FID' in polyfile.columns:
                    return polyfile[polyfile['FID']==index+1]
        return

        country = 'United_Kingdom'
        Countrydir = current_node.locmappath("")
        normstats['Mean_Lat'] = 51
        normstats['Mean_Long'] = 0

    # fg1/2/3 list maintains a cumulative list of ward and div boundaries to be added as the constituency poly layer in f4 anf f5
    # fg2w/p/c fg3w/p/c are overwritten single value poly + div polygons added to each Ward , PDmap and Walk maps - no lists needed
    # for each group of electorwalks create a MAP and TEXT file.

    from jinja2 import Environment, FileSystemLoader
    if Env1.find("Orange")>0:
        from Orange.data import ContinuousVariable, StringVariable, DiscreteVariable, Domain
        from Orange.data import Table, Instance
        Clabel = DiscreteVariable("Clabel", values={"C0","C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12","C13","C14","C15","C16","C17","C18","C19","C20","C21","C22","C23","C24","C25","C26","C27","C28","C29","C30","C31","C32","C33","C34","C35","C36","C37"})
        allelectors = TabletoDF (in_data)
    else:
        Clabel ={ "Clabel" : ["C0","C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12","C13","C14","C15","C16","C17","C18","C19","C20","C21","C22","C23","C24","C25","C26","C27","C28","C29","C30","C31","C32","C33","C34","C35","C36","C37"]}
        allelectors = pd.read_csv(filename, skiprows=[1,2])
        print(allelectors.columns)
    #Country configured on Electrek Dashboard
    Country_Bound_layer = gpd.read_file(bounddir+"/"+'Countries_December_2021_UK_BGC_2022_-7786782236458806674.geojson')
    Country_Bound_layer = Country_Bound_layer.rename(columns = {'CTRY21NM': 'NAME'})


    County_Bound_layer = gpd.read_file(bounddir+"/"+'Counties_and_Unitary_Authorities_May_2023_UK_BGC_-1930082272963792289.geojson')
    County_Bound_layer = County_Bound_layer.rename(columns = {'CTYUA23NM': 'NAME'})

    Division_Bound_layer = gpd.read_file( bounddir+"/"+'County_Electoral_Division_May_2023_Boundaries_EN_BFC_8030271120597595609.geojson')
    Division_Bound_layer = Division_Bound_layer.rename(columns = {'CED23NM': 'NAME'})

    Con_Bound_layer = gpd.read_file(bounddir+"/"+'Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BFC_5018004800687358456.geojson')
    Con_Bound_layer = Con_Bound_layer.rename(columns = {'PCON24NM': 'NAME'})

    Con_Long = statistics.mean(allelectors.Long.values)
    Con_Lat = statistics.mean(allelectors.Lat.values)
    here = Point(Decimal(Con_Long),Decimal(Con_Lat))
    Countyboundary = find_boundary(County_Bound_layer,here)

    county = list(Countyboundary['NAME'].str.replace(r'[^A-Za-z0-9\&\, ]+', '').str.replace(" & "," AND ").str.replace(" ","_").str.upper())[0]
    print("________COUNTYX",county)
    Conboundary = find_boundary(Con_Bound_layer,here)

    constituency = list(Conboundary['NAME'].str.replace(r'[^A-Za-z0-9\&\, ]+', '').str.replace(" & "," AND ").str.replace(" ","_").str.upper())[0]
    normstats['constituency'] = constituency
    print("________Constituency",constituency)
    Countyboundary["UPDOWN"] = "<br>COUNTY</br>"+goup("COUNTY",country,"UP",18)+godown("COUNTY",constituency,"DOWN",18)
    add_to_top_layer(fg0list, Countyboundary,"UPDOWN",fg0)

    def reproject(latitude, longitude):
    # Returns the x & y coordinates in meters using a sinusoidal projection
        from math import pi, cos, radians
        earth_radius = 6371009 # in meters
        lat_dist = pi * earth_radius / 180.0

        y = [int(lat * lat_dist) for lat in latitude]
        x = [int(long * lat_dist * cos(radians(lat)))
                    for lat, long in zip(latitude, longitude)]
        return x, y

    def square_area(lats,lons):
    # Returns the area in square meters of a lat long spheriod coonverted to a trapezium abcd (anto-clockwise labelled from minmin)
      xs,ys = reproject(lats, lons)
    #  print("lat,lon:",lats,lons)
    #  print("xs,ys:",xs,ys)
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

    def create_div_map(map_title,geom,zoom):
      print("CreateDiv",geom.bounds['maxx'].values,geom.representative_point().get_coordinates().values[0])
      Dmap = folium.Map(location=geom.representative_point().get_coordinates().values.tolist()[0], trackResize = "true",tiles="OpenStreetMap", zoom_start=zoom)
      title_html = '''<h1 style="z-index:1200;color: black;position:absolute;left:150px;">{0}</h1>'''.format(map_title)
      Dmap.get_root().html.add_child(folium.Element(title_html))
      sw = [geom.bounds['miny'].values[0],geom.bounds['minx'].values[0]]
      ne = [geom.bounds['maxy'].values[0],geom.bounds['maxx'].values[0]]
      Dmap.fit_bounds([sw,ne], padding = (30, 30))

      return Dmap


    def add_to_con_layer(fglist, boundary,uptag,layer):
      print("add_to_con",boundary.info)
      if boundary.iloc[0]['FID'] not in fglist:
        fglist.append(boundary.iloc[0]['FID'])
        print("FG1 Poly details:",boundary)
        folium.GeoJson(boundary,highlight_function=lambda feature: {"fillColor": ("green"),},
          popup=folium.GeoJsonPopup(fields=[uptag,],aliases=["Move6:",]),popup_keep_highlighted=True,
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
      print("domain",block.domain)
      print("shape:",block.Y.shape, block.X.shape, block.metas.shape)
      tvx = block.Y.shape[0]
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

    County_Long = Con_Long
    County_Lat = Con_Lat

    here = Point(Decimal(County_Long),Decimal(County_Lat))
    normstats['location'] = here
    Countyboundary = find_boundary(County_Bound_layer,here)
    county = list(Countyboundary['NAME'].str.replace(r'[^A-Za-z0-9\& ]+', '').str.replace(" & "," AND ").str.replace(" ","_").str.upper())[0]
    normstats['county'] = county
    CountyMapfile = county+"-MAP.html"
    Countyboundary["DOWN"] = "<br>"+county+"</br>"+godown("COUNTY",county,"DOWN",18)
    add_to_top_layer(fg0list, Countyboundary,"DOWN",fg0)
    Countydir = current_node.locmappath("")

    here = Point(Decimal(Countyboundary["LONG"].values[0]),Decimal(Countyboundary["LAT"].values[0]))
    sw = [Countyboundary.geometry.bounds.miny.to_list()[0],Countyboundary.geometry.bounds.minx.to_list()[0]]
    ne = [Countyboundary.geometry.bounds.maxy.to_list()[0],Countyboundary.geometry.bounds.maxx.to_list()[0]]
    swne = [sw,ne]
    Countymap = current_node.create_area_map (swne)
    Countymap.add_child(fg0)


    Countydir = current_node.locmappath("")
    os.chdir(Countydir)
    listofcons = next(os.walk('.'))[1]
    print("westminster con file:",listofcons,Con_Bound_layer.info())
    c1 = Con_Bound_layer['NAME'].str.replace(r'[^A-Za-z0-9\& ]+', '').str.replace(" & "," AND ").str.replace(" ","_").str.upper()

    conlist = (x for x in listofcons if x != constituency)
    for con in conlist:
      mask = Con_Bound_layer[c1 == con]
      print("ZZZ:",c1, con,"*",conlist,"*",listofcons,mask )
      mask["UP"] = "<br>"+con+"</br>"+goup("CON",county,"UP",18)
      add_to_con_layer(fg1list, mask,"UP",fg1)
      fg1.add_child(
        folium.Marker(
            location=[Decimal(mask["LAT"].iloc[0]),Decimal(mask["LONG"].iloc[0])],
            icon = folium.DivIcon(html="<b style='font-size: 12pt; color: orange'>"+
            godown("COUNTY",con,con,15)+
            "</b>\n",
            class_name = "leaflet-div-icon",
            icon_anchor=(5,30)),
          )
        )

    ConMapfile = constituency+"-MAP.html"

    Ward_Bound_layer = gpd.read_file(bounddir+"/"+'Wards_May_2024_Boundaries_UK_BGC_-4741142946914166064.geojson')
    Ward_Bound_layer = Ward_Bound_layer.rename(columns = {'WD24NM': 'NAME'})

    Codir = current_node.locmappath("")
    os.chdir(Codir)

    here = Point(Decimal(Conboundary["LONG"].values[0]),Decimal(Conboundary["LAT"].values[0]))
    print("CONSTITUENCY - longlat centroid:", here)

    sw = [Conboundary.geometry.bounds.miny.to_list()[0],Conboundary.geometry.bounds.minx.to_list()[0]]
    ne = [Conboundary.geometry.bounds.maxy.to_list()[0],Conboundary.geometry.bounds.maxx.to_list()[0]]
    swne = [sw,ne]
    Conmap = current_node.create_area_map (swne)

    PDs = set(allelectors.PD.values)
    print("PDs", PDs)
    normstats['PDs'] = len(PDs)
    frames = []
    PDWardlist =[]
    for PD in PDs:
      PDelectors = getblock(allelectors,'PD',PD)
      maplongx = statistics.mean(PDelectors.Long.values)
      maplaty = statistics.mean(PDelectors.Lat.values)
      PDcoordinates = [maplaty, maplongx]
      Wardboundary = find_boundary(Ward_Bound_layer,Point(Decimal(maplongx),Decimal(maplaty)))

      Ward = list(Wardboundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.upper())[0]
      PDelectors['Ward'] = Ward
      PDWardlist.append((PD,Ward, Wardboundary))
      frames.append(PDelectors)

    allelectors = pd.concat(frames)
    wards = set(x[1] for x in PDWardlist)
    normstats['wards'] = len(wards)
    w = 0


    def dropchange (elementid, colvaluelist, text, size):
      return "<input id='{0}' type='button' value='{1}' style='font-size: {2}pt;' onclick='openForm();' />".format(elementid,text, size)


    def add_to_wards_layer(fglist, boundary,layer,downtag,layertag):
      tw = list(boundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.upper())[0]
      print("add_to_ward",tw)
      if boundary.iloc[0]['FID'] not in fglist:
        fglist.append(boundary.iloc[0]['FID'])
        folium.GeoJson(boundary,highlight_function=lambda feature: {"fillColor": ("green"),},
          popup=folium.GeoJsonPopup(fields=[downtag,],aliases=["Move1:",]),popup_keep_highlighted=True,
          style_function=lambda feature: {"fillColor": "indigo","color": "indigo","weight": 3,"fillOpacity": 0.1,},
    #      marker=folium.Marker(icon=folium.DivIcon(html="<b style='font-size: 12pt; color: black'>"+ layertag + "</b>\n"))
          ).add_to(layer)
        xy = boundary["geometry"].representative_point().get_coordinates().values.tolist()[0]
    #    print ("testingfg4",xy)
        folium.Marker(
            location= [xy[1],xy[0]],
            icon = folium.DivIcon(html="<b style='font-size: 12pt; color: red';>"+
            godown("CON",tw,tw,15)+
            "</b>\n",
            class_name = "leaflet-div-icon",
            icon_anchor=(5,30)),
          ).add_to(fg4)
      return

    def add_to_ward_layer(boundary,layer,uptag, layertag):
      folium.GeoJson(boundary,highlight_function=lambda feature: {"fillColor": ("green"),},
        popup=folium.GeoJsonPopup(fields=[uptag,],aliases=["Move2:",]),popup_keep_highlighted=True,
        style_function=lambda feature: {"fillColor": "indigo","color": "indigo","weight": 3,"fillOpacity": 0.1,},
        ).add_to(layer)

      return

    def add_to_divs_layer(fglist, boundary,layer,downtag,layertag):
      td = list(boundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.upper())[0]
      if boundary.iloc[0]['FID'] not in fglist:
        fglist.append(boundary.iloc[0]['FID'])
        Dmap = create_div_map(layertag,boundary['geometry'],12)
        DivMapfilelist.append([boundary.iloc[0]['FID'],Dmap,Divdir,DivMapfile])
        folium.GeoJson(boundary,highlight_function=lambda feature: {"fillColor": ("yellow"),},
          popup=folium.GeoJsonPopup(fields=[downtag,],aliases=["Move3:",]),popup_keep_highlighted=True,
          style_function=lambda feature: {"fillColor": "red","color": "red","weight": 3,"fillOpacity": 0.1,},
      #      marker=folium.Marker(icon=folium.DivIcon(html="<b style='font-size: 12pt; color: black'>"+ layertag + "</b>\n"))
          ).add_to(layer)
        xy = boundary["geometry"].representative_point().get_coordinates().values.tolist()[0]
    #    print ("testingfg5",xy)
        folium.Marker(
            location= [xy[1],xy[0]],
            icon = folium.DivIcon(html="<b style='font-size: 12pt;  color: red';>"+
            godown("CON",td,td,15)+
            "</b>\n",
            class_name = "leaflet-div-icon",
            icon_anchor=(5,30)),
          ).add_to(fg5)
      else:
        Dmap = [x[1] for x in DivMapfilelist if x[0] == boundary.iloc[0]['FID']][0]
      return Dmap

    def add_to_div_layer(boundary, layer, uptag, layertag):
      folium.GeoJson(boundary,highlight_function=lambda feature: {"fillColor": ("green"),},
        popup=folium.GeoJsonPopup(fields=[uptag,],aliases=["Move4:",]),popup_keep_highlighted=True,
        style_function=lambda feature: {"fillColor": "red","color": "red","weight": 3,"fillOpacity": 0.1,},
        ).add_to(layer)

      return



    def create_convexhull_polygon(
        map_object, list_of_points, layer_name, line_color, fill_color, weight, text
    ):

        # Since it is pointless to draw a convex hull polygon around less than 3 points check len of input
        if len(list_of_points) < 3:
            return

        # Create the convex hull using scipy.spatial
        form = [list_of_points[i] for i in ConvexHull(list_of_points).vertices]

        # Create feature group, add the polygon and add the feature group to the map
        fg = folium.FeatureGroup(name=layer_name)
        fg.add_child(
            folium.vector_layers.Polygon(
                locations=form,
                color=line_color,
                fill_color=fill_color,
                weight=weight,
                popup=(folium.Popup(text)),
            )
        )
        map_object.add_child(fg)

        return map_object


    Conboundary["UP"] = "<br>"+constituency+"</br>" + goup("CON",county,"UP",10)
    add_to_con_layer(fg1list, Conboundary,"UP",fg1)

    fg1.add_child(
      folium.Marker(
          location=[Decimal(Con_Lat),Decimal(Con_Long)],
          icon = folium.DivIcon(html="<b style='font-size: 12pt; color: orange'>"+
          godown("COUNTY",constituency,constituency,15)+
          "</b>\n",
          class_name = "leaflet-div-icon",
          icon_anchor=(5,30)),
        )
      )
    normstats['walks'] = 0
    for Ward in wards:

      fg2w = folium.FeatureGroup(name='Ward Boundary', overlay=True, control=True, show=True)
      fg3w = folium.FeatureGroup(name='Division Boundary', overlay=True, control=True, show=True)

      wardelectors = getblock(allelectors, 'Ward',Ward)
      Ward = Ward.replace(r'[^A-Za-z0-9\& ]+', '').replace(",","").replace(" & "," AND ").upper().replace(" ","_")

      maplongx = statistics.mean(wardelectors.Long.values)
      maplaty = statistics.mean(wardelectors.Lat.values)
      wardcoordinates = [maplaty, maplongx]
      here = Point(Decimal(maplongx),Decimal(maplaty))

      Wadir = current_node.locmappath("")
      sw = wardelectors[['Lat', 'Long']].min().values.tolist()
      ne = wardelectors[['Lat', 'Long']].max().values.tolist()
      swne = [sw,ne]

      Wardmap = current_node.create_area_map (swne)

      WardMapfile = Ward+"-MAP.html"

      allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

      type_colour = allowed["C0"]

      # in the Constituency map add the ward marker to the map with a ward title

      fg2w.add_child(
        folium.Marker(
            location=wardcoordinates,
            icon = folium.DivIcon(html="<b style='font-size: 12pt; color: orange'>"+
            godown("CON",Ward,Ward,15)+
            "</b>\n",
            class_name = "leaflet-div-icon",
            icon_anchor=(5,30)),
          )
        )

      warddistricts = wardelectors.PD.unique()

      p = 0

      for PD in warddistricts:
        fg2p = folium.FeatureGroup(name='Ward Boundary', overlay=True, control=True, show=True)
        fg3p = folium.FeatureGroup(name='Division Boundary', overlay=True, control=True, show=True)

        PDelectors = getblock(allelectors,'PD',PD)
        maplongx = statistics.mean(PDelectors.Long.values)
        maplaty = statistics.mean(PDelectors.Lat.values)
    #    print("PDcoords:",maplongx, maplaty)
        PDcoordinates = [maplaty, maplongx]
        Wardboundary = list([x[2] for x in PDWardlist if x[0] == PD])[0]
    #    Wardboundary = find_boundary(Ward_Bound_layer,Point(Decimal(maplongx),Decimal(maplaty)))
        if Wardboundary is None:
          print("Cant find Wardboundary - Lat Long:",maplaty,maplongx)
        else:
          Wardboundary["Downcon"] =  "<br>"+Ward+"</br>"+ godown("CON",Ward, "DOWN",15)
          Wardboundary["UPward"] =  "<br>"+Ward+"</br>"+goup("WARD",constituency,"UP",10)
          Wardboundary["UPpd"] =  "<br>"+Ward+"</br>"+goup("PD",Ward,"UP",10)
          add_to_wards_layer (fg4list, Wardboundary, fg4, "UPward", Ward)
          add_to_ward_layer (Wardboundary, fg2w, "UPward", Ward)
          add_to_ward_layer (Wardboundary, fg2p, "UPpd", Ward)

        Divboundary = find_boundary(Division_Bound_layer,Point(Decimal(maplongx),Decimal(maplaty)))
        if Divboundary is None:
          print("Cant find Divboundary - Lat Long:",maplaty,maplongx)
        else:
          Divname = str(Divboundary['NAME'].values[0]).replace(r'[^A-Za-z0-9\& ]+', '').replace(",","").replace(" & "," AND ").upper().replace(" ","_")
          DivMapfile = Divname+"-MAP.html"
          Divboundary["Downcon"] =  "<br>"+Divname+"</br>"+godown("CON", Divname,"DOWN",15)
          Divboundary["Downdiv"] =  "<br>"+Divname+"</br>"+godown("DIV", PD,"DOWN",15)
          Divboundary["UPdiv"] =  "<br>"+Divname+"</br>"+goup("DIV", constituency,"UP",10)
          Divboundary["UPpd"] =  "<br>"+Divname+"</br>"+goup("DIVPD", Divname,"UP",10)
          Divdir = current_node.locmappath("")
          PDDivdir = current_node.locmappath(Wadir+"/"+str(PD))

          Divmap = add_to_divs_layer (fg5list, Divboundary, fg5, "UPdiv",Divname)


          add_to_div_layer (Divboundary, fg3w,"UPdiv", Divname)
          add_to_div_layer (Divboundary, fg3p,"UPpd", Divname)


    # calc number of clusters in PDelectors and use kmeans to label them in a new column 'Clabel'
        x = PDelectors.Long.values
        y = PDelectors.Lat.values
        kmeans_dist_data = list(zip(x, y))

        walkset = min(math.ceil(PDelectors.shape[0]/100),35)

        kmeans = KMeans(n_clusters=walkset)
        kmeans.fit(kmeans_dist_data)

        klabels1 = np.char.mod('C%d', kmeans.labels_)
        klabels = klabels1.tolist()

        PDelectors.insert(0, "Clabel", klabels)

        PDdir = current_node.locmappath("")
        here = Point(Decimal(x[0]),Decimal(y[0]))
        sw = PDelectors[['Lat', 'Long']].min().values.tolist()
        ne = PDelectors[['Lat', 'Long']].max().values.tolist()
        swne = [sw,ne]
        PDmap = current_node.create_area_map (swne)
        PDmap.add_css_link("electtrekcss","https://newbrie.github.io/Electtrek/style.css")

        PDmap.add_js_link("electtrekjs","https://newbrie.github.io/Electtrek/electorwalks.js")

        PDMapfile = PD+"-MAP.html"
    # in the wards map add PD polling districts to the ward map with controls to go back up to the constituency map or down to the PD map
        type_colour = allowed["C1"]
        Wardmap.add_child(
          folium.Marker(
            location=PDcoordinates,
            icon = folium.DivIcon(html= godown("WARD",PD,PD,15),
            class_name = "leaflet-div-icon",
            icon_size=(5,30),
            icon_anchor=(5,30)),
           )
          )

        if Divboundary is not None:
          Divmap.add_child(
            folium.Marker(
              location=PDcoordinates,
              icon = folium.DivIcon(html= godown("DIV",PD,PD,15),
              class_name = "leaflet-div-icon",
              icon_size=(5,30),
              icon_anchor=(5,30)),
              ))

        clusters = PDelectors.Clabel.unique()
        print ("____________clusters",clusters)
        normstats['walks'] = int(normstats['walks']) + len(clusters)
        c = 0

        for cluster in clusters:

          fg2c = folium.FeatureGroup(name='Ward Boundary', overlay=True, control=True, show=True)
          fg3c = folium.FeatureGroup(name='Division Boundary', overlay=True, control=True, show=True)
          Wardboundary["UPcluster"] = "<br>"+Ward+"</br>"+ goup("WALK",PD,"UP",12)
          add_to_ward_layer (Wardboundary, fg2c,"UPcluster", Ward)

          if Divboundary is not None:
            Divboundary["UPcluster"] =  "<br>"+Divname+"</br>"+goup("CLUSTER",PD, "UP",12)
            add_to_div_layer (Divboundary, fg3c, "UPcluster", Divname)

          electorwalks = getblock(PDelectors, 'Clabel',cluster)
          maplongx = statistics.mean(electorwalks.Long.values)
          maplaty = statistics.mean(electorwalks.Lat.values)
          walkcoordinates = [maplaty, maplongx]

          Cldir = current_node.locmappath("")
          here = Point(Decimal(maplongx),Decimal(maplaty))

          sw = electorwalks[['Lat', 'Long']].min().values.tolist()
          ne = electorwalks[['Lat', 'Long']].max().values.tolist()
          swne = [sw,ne]
          Walkmap = current_node.create_area_map (swne)

          WalkMapfile = PD+"-"+cluster+"-MAP.html"

          Postcode = electorwalks.loc[0].Postcode

          walk_name = PD+"-"+cluster
          type_colour = allowed[cluster]

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

          type_colour = allowed[cluster]


    #      marker_cluster = MarkerCluster().add_to(Walkmap)
          # Iterate through the street-postcode list and add a marker for each unique lat long, color-coded by its Cluster.


          for streetcoordinates in CL_unique_list:

            # in the Walk map add Street-postcode groups to the walk map with controls to go back up to the PD map or down to the Walk addresses
            print("________WardMarker",Ward, "|",cluster)
            popuptext = '<ul style="font-size: {5}pt;color: gray;" >Ward: {0} WalkNo: {1} Postcode: {2} {3} {4}</ul>'.format(Ward,cluster, Postcode, goup("PD", Ward,"UP",12), godown("PD",PD+"-"+cluster, "DOWN",15),12)

            # in the PD map add PD-cluster walks to the PD map with controls to go back up to the Ward map or down to the Walk map
            PDmap.add_child(
              folium.Marker(
                 location=streetcoordinates,
                 popup = popuptext,
                 icon=folium.Icon(color = type_colour,  icon='search'),
                 )
                 )
            popuptext = '<ul style="font-size: {5}pt;color: gray;" >Ward: {0} WalkNo: {1} Postcode: {2} {3} {4}</ul>'.format(Ward,cluster, Postcode, goup("WALK",PD,"UP",12), godown("WALK",PD+"-"+cluster, "DATA",15),12)

            Walkmap.add_child(
                folium.Marker(
                    location=streetcoordinates,
                    popup= popuptext,
                    icon=folium.Icon(color = type_colour),
                )
                )

          os.chdir(Cldir)

          Walkmap.add_child(fg1)
          Walkmap.add_child(fg3c)
          Walkmap.add_child(fg2c)
          Walkmap.add_child(folium.LayerControl())
          Walkmap.save(WalkMapfile)
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
          electorwalks['HB'] = ""

          clusterelectors = electorwalks.shape[0]
          climb = electorwalks.Elevation.max() - electorwalks.Elevation.min()
          x = electorwalks.AddressNumber.values
          y = electorwalks.StreetName
          z = electorwalks.AddressPrefix.values
          houses = len(list(set(zip(x,y,z))))
          streets = len(electorwalks.StreetName.unique())
    #      longs = [electorwalks.Long.min(), electorwalks.Long.max()]
    #      lats = [electorwalks.Lat.min(),electorwalks.Lat.max()]

    # areamsq comes from zoom level 18 of leaflet tiles
          areamsq = 34*21.2*20*21.2

          avstrlen = 200

    #      streethousedensity = houses/(streets*avstrlen)
          housedensity = round(houses/(areamsq/10000),3)

          avhousem = 100*round(math.sqrt(1/housedensity),2)
    #      avhousem = 1/streethousedensity
          streetdash = avstrlen*streets/houses


    #      print ("climb, houses, streets, housedensity, avhousem, streetdash",climb, houses,streets, housedensity, avhousem, streetdash)

          speed = 5*1000
          climbspeed = 5*1000 - climb*50/7
          leafmins = 0.5
          canvassmins = 5
          canvasssample = .5
          leafhrs = round(houses*(leafmins+60*streetdash/climbspeed)/60,2)
          canvasshrs = round(houses*(canvasssample*canvassmins+60*streetdash/climbspeed)/60,2)
          normstats['constituency'] = constituency
          normstats['ward'] = Ward
          normstats['PD'] = PD
          normstats['groupelectors'] = clusterelectors
          normstats['climb'] = climb
          normstats['houses'] = houses
          normstats['streets'] = streets
          normstats['housedensity'] = housedensity
          normstats['leafhrs'] = round(leafhrs,2)
          normstats['canvasshrs'] = round(canvasshrs,2)

          electorwalks['ENOP'] =  electorwalks['ENO']+ electorwalks['Suffix']/10

          mapfull = WalkMapfile
          from jinja2 import Environment, FileSystemLoader
          templateLoader = jinja2.FileSystemLoader(searchpath=templdir)
          environment = jinja2.Environment(loader=templateLoader)

          results_filename = walk_name+"-TEXT.html"
          context = {
              "group": electorwalks,
              "prodstats": normstats,
              "mapfile": PDMapfile,
              }

          results_template = environment.get_template("canvasscard1.html")

          with open(results_filename, mode="w", encoding="utf-8") as results:
            results.write(results_template.render(context, url_for=url_for))
          c = c + 1
        os.chdir(PDdir)
        PDmap.add_child(fg1)
        PDmap.add_child(fg3p)
        PDmap.add_child(fg2p)
        PDmap.add_child(folium.LayerControl())
        PDmap.save(PDMapfile)
        p = p + 1
      os.chdir(Wadir)
      Wardmap.add_child(fg1)
      Wardmap.add_child(fg4)
      Wardmap.add_child(folium.LayerControl())
      Wardmap.save(WardMapfile)
      w = w + 1

    for fid,fmap,fdir,fpath in DivMapfilelist:
     # print ("fmaplist:",fid,fmap,fdir,fpath)
      fmap.add_child(fg1)
      fmap.add_child(fg5)
      fmap.add_child(folium.LayerControl())
      os.chdir(fdir)
      fmap.save(fpath)

    os.chdir(Codir)
    Conmap.add_child(fg1)
    Conmap.add_child(fg5)
    Conmap.add_child(fg4)
    Conmap.add_child(folium.LayerControl())
    Conmap.save(ConMapfile)
    os.chdir(Countydir)
    Countymap.add_child(fg1)
    Countymap.add_child(folium.LayerControl())
    Countymap.save(CountyMapfile)
    normstats['status'] = "Walk generation complete"
    return [allelectors, normstats, country+"/"+county+"/"+constituency+"/"+fg1]

if __name__ == "__main__":
    # this won't be run when imported
    produce()
