from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
import folium
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np
import os, sys, math, stat, json , jinja2
from os import listdir, system
import subprocess
import statistics
from sklearn.cluster import KMeans
import io
#from PIL import Image
import re
from decimal import Decimal
from pyproj import Proj
from flask import Flask,render_template, url_for, flash
#from electtrek import locmappath, TreeNode, workdirectories, flayers

def getblock(source,joincol, colvalue):
  colvalfilter = pd.DataFrame([[colvalue]], columns=[joincol])
# create a group dataframe based on a filtering join of a column value of all electors
  group = pd.merge(source, colvalfilter, on=joincol)
  return(group)

def find_boundary(polyfile,here):
    for index, ppath in polyfile.iterrows():
        path = ppath['geometry']
        if path.contains(here):
            return polyfile[polyfile['FID']==index+1]
    return


def prodcards(gapnode,filename, prodstats,TreeBounds, enviro, flayers):
    global workdirectories
    global Directories
    global MapRoot
    global allelectors
    global TreeNode


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


    Env1 = sys.base_prefix
    country = gapnode.parent.parent.parent.value
    nation = gapnode.parent.parent.value
    county = gapnode.parent.value
    constituency = gapnode.value

    Countrydir = gapnode.parent.parent.parent.locmappath("")
    prodstats['Mean_Lat'] = 51
    prodstats['Mean_Long'] = 0

    # fg1/2/3 list maintains a cumulative list of ward and div boundaries to be added as the constituency poly layer in f4 anf f5
    # fg2w/p/c flayers[4]w/p/c are overwritten single value poly + div polygons added to each Ward , PDmap and Walk maps - no lists needed
    # for each group of electorwalks create a MAP and TEXT file.

    if Env1.find("Orange")>0:
        from Orange.data import ContinuousVariable, StringVariable, DiscreteVariable, Domain
        from Orange.data import Table, Instance
        Clabel = DiscreteVariable("Clabel", values={"C0","C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12","C13","C14","C15","C16","C17","C18","C19","C20","C21","C22","C23","C24","C25","C26","C27","C28","C29","C30","C31","C32","C33","C34","C35","C36","C37"})
        allelectors = TabletoDF (in_data)
    else:
        Clabel ={ "Clabel" : ["C0","C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12","C13","C14","C15","C16","C17","C18","C19","C20","C21","C22","C23","C24","C25","C26","C27","C28","C29","C30","C31","C32","C33","C34","C35","C36","C37"]}
        allelectors = pd.read_csv(filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
        print(allelectors.columns)
    #Country configured on Electrek Dashboard

#    Nation_Long = statistics.mean(allelectors.Long.values)
#    Nation_Lat = statistics.mean(allelectors.Lat.values)
#    here = Point(Decimal(Nation_Long),Decimal(Nation_Lat))
    pfile = TreeBounds[gapnode.parent.parent.level]
    Nationboundary = pfile[pfile['FID']==gapnode.parent.parent.fid]
#    Nationboundary = find_boundary(TreeBounds[0],here)
    nation = gapnode.parent.parent.value
    print("________NATION:",nation)

    gapnode.parent.parent.locmappath("")


#    here = Point(Decimal(Con_Long),Decimal(Con_Lat))
    pfile = TreeBounds[gapnode.parent.level]
    downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(gapnode.dir+"/"+gapnode.file,"DOWN",18)
    uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(gapnode.parent.dir+"/"+gapnode.parent.file,"UP",18)

    Countyboundary = pfile[pfile['FID']==gapnode.parent.fid]
#    Countyboundary = find_boundary(TreeBounds[1],here)

    county = gapnode.parent.value
    print("________COUNTY:",county)

    pfile = TreeBounds[gapnode.level]
    Conboundary = pfile[pfile['FID']==gapnode.fid]
    Conboundary["UPDOWN"] = "<br>CON</br>"+ uptag +"<br>"+ downtag
    Con_Long = Decimal(Conboundary.LONG.values[0])
    Con_Lat = Decimal(Conboundary.LAT.values[0])
    constituency = gapnode.value
    print("________CON:",constituency)
    Countyboundary["UPDOWN"] = "<br>COUNTY</br>"+ uptag +"<br>"+ downtag
    add_to_top_layer(flayers[2].children, Conboundary,"UPDOWN",flayers[2].fg)

    County = county+"-MAP.html"
    add_to_top_layer(flayers[2].children, Countyboundary,"UPDOWN",flayers[2].fg)

    gapnode.parent.locmappath("")

#    here = Point(Decimal(Countyboundary["LONG"].values[0]),Decimal(Countyboundary["LAT"].values[0]))
#    sw = [Countyboundary.geometry.bounds.miny.to_list()[0],Countyboundary.geometry.bounds.minx.to_list()[0]]
#    ne = [Countyboundary.geometry.bounds.maxy.to_list()[0],Countyboundary.geometry.bounds.maxx.to_list()[0]]
#    swne = [sw,ne]
#
#    Countymap = create_area_map (swne)
#    Countymap.add_child(flayers[1].fg)
    print("______Directory:", os.getcwd())


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


    listofcons = next(os.walk('.'))[1]
    print("westminster con file:",listofcons,TreeBounds[gapnode.level].info())
    c1 = constituency
    conlist = []
    conlist = [x for x in listofcons if x != constituency]
    for child in gapnode.parent.children:
      if child.value in conlist:
          mask = TreeBounds[gapnode.level]['FID' == child.fid]
          print("ZZZ:",c1, child.value,"*",conlist,"*",listofcons,mask )
          downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(child.dir+"/"+child.file,"DOWN",15)
          uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(child.parent.dir+"/"+child.parent.file,"UP",18)
          mask["UP"] = "<br>"+child.value+"</br>"+uptag
          add_to_con_layer(flayers[3].children, mask,"UP",flayers[3].fg)
          flayers[3].fg.add_child(
            folium.Marker(
                location=[Decimal(mask["LAT"].iloc[0]),Decimal(mask["LONG"].iloc[0])],
                icon = folium.DivIcon(html="<b style='font-size: 12pt; color: orange'>"+
                downtag+
                "</b>\n",
                class_name = "leaflet-div-icon",
                icon_anchor=(5,30)),
              )
            )


    here = Point(Decimal(Conboundary["LONG"].values[0]),Decimal(Conboundary["LAT"].values[0]))
    print("CONSTITUENCY - longlat centroid:", here)

    sw = [Conboundary.geometry.bounds.miny.to_list()[0],Conboundary.geometry.bounds.minx.to_list()[0]]
    ne = [Conboundary.geometry.bounds.maxy.to_list()[0],Conboundary.geometry.bounds.maxx.to_list()[0]]
    swne = [sw,ne]
    Conmap = gapnode.create_area_map (flayers,allelectors)

    PDs = set(allelectors.PD.values)
    print("PDs", PDs)
    prodstats['PDs'] = len(PDs)
    frames = []
    PDWardlist =[]
    for PD in PDs:
      PDelectors = getblock(allelectors,'PD',PD)
      maplongx = statistics.mean(PDelectors.Long.values)
      maplaty = statistics.mean(PDelectors.Lat.values)
      PDcoordinates = [maplaty, maplongx]
# for all PDs - pull together all PDs which are within the Conboundary constituency boundary
      if Conboundary.geometry.convex_hull.contains(Point(Decimal(maplongx),Decimal(maplaty))).item():
          Wardboundary = find_boundary(TreeBounds[4],Point(Decimal(maplongx),Decimal(maplaty)))
          Ward = list(Wardboundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.replace(" ","_").str.upper())[0]
          PDelectors['Ward'] = Ward
          PDWardlist.append((PD,Ward, Wardboundary))
          frames.append(PDelectors)

    allelectors = pd.concat(frames)
    wards = set(x[1] for x in PDWardlist)
    prodstats['wards'] = len(wards)
    w = 0


    def dropchange (elementid, colvaluelist, text, size):
      return "<input id='{0}' type='button' value='{1}' style='font-size: {2}pt;' onclick='openForm();' />".format(elementid,text, size)


    def add_to_wards_layer(fglist, boundary,layer,downtag,layertag):
      tw = list(boundary['NAME'].str.replace(" & "," AND ").str.replace(r'[^A-Za-z0-9 ]+', '').str.replace(",","").str.replace(" ","_").str.upper())[0]
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
            downtag+
            "</b>\n",
            class_name = "leaflet-div-icon",
            icon_anchor=(5,30)),
          ).add_to(layer)
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
        Divlist.append([boundary.iloc[0]['FID'],Dmap,Divdir,Div])
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
            downtag+
            "</b>\n",
            class_name = "leaflet-div-icon",
            icon_anchor=(5,30)),
          ).add_to(layer)
      else:
        Dmap = [x[1] for x in Divlist if x[0] == boundary.iloc[0]['FID']][0]
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

    flayers[gapnode.level+1].children = []
    flayers[gapnode.level+1].fg = folium.FeatureGroup(id=str(gapnode.level+2),name=flayers[gapnode.level+1].name, overlay=True, control=True, show=True)
    flayers[gapnode.level+1].add_linesandmarkers(gapnode, 'data')
    print ("____________flayer objects:",len(flayers[gapnode.level+1].children))

#    uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(gapnode.parent.dir+"/"+gapnode.parent.file,"UP",15)
#    downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(gapnode.dir+"/"+gapnode.file,"DOWN",15)

#    Conboundary["UP"] = "<br>"+constituency+"</br>" + uptag
#    add_to_con_layer(flayers[3].children, Conboundary,"UP",flayers[3].fg)

#    flayers[4].fg.add_child(
#      folium.Marker(
#          location=[Decimal(Con_Lat),Decimal(Con_Long)],
#          icon = folium.DivIcon(html="<b style='font-size: 12pt; color: orange'>"+
#          downtag+
#          "</b>\n",
#          class_name = "leaflet-div-icon",
#          icon_anchor=(5,30)),
#        )
#      )
    prodstats['streets'] = 0
    wardchildren = list([x for x in gapnode.children if x.type == "ward"])
    for ward_node in wardchildren:
      Ward = ward_node.value
      flayers[4].children = []
      flayers[4].fg = folium.FeatureGroup(id='5',name='Ward Boundary', overlay=True, control=True, show=True)
#      flayers[4].fg = folium.FeatureGroup(name='Division Boundary', overlay=True, control=True, show=True)

      wardelectors = getblock(allelectors, 'Ward',Ward)
#      Ward = Ward.replace(r'[^A-Za-z0-9\& ]+', '').replace(",","").replace(" & "," AND ").upper().replace(" ","_")

      if len(wardelectors) >  0 :
          maplongx = statistics.mean(wardelectors.Long.values)
          maplaty = statistics.mean(wardelectors.Lat.values)
          wardcoordinates = [maplaty, maplongx]
          here = Point(Decimal(maplongx),Decimal(maplaty))


          sw = wardelectors[['Lat', 'Long']].min().values.tolist()
          ne = wardelectors[['Lat', 'Long']].max().values.tolist()
          swne = [sw,ne]

      Wardmap = ward_node.create_area_map (flayers,wardelectors)

      Ward = Ward+"-MAP.html"
      ward_node.locmappath("")

      allowed = {"C0" :'indigo',"C1" :'darkred', "C2":'white', "C3":'red', "C4":'blue', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'gray',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }

      type_colour = allowed["C0"]

      # in the Constituency map add the ward marker to the map with a ward title
      downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(ward_node.dir+"/"+ward_node.file,"DOWN",15)

      flayers[4].fg.add_child(
        folium.Marker(
            location=wardcoordinates,
            icon = folium.DivIcon(html="<b style='font-size: 12pt; color: orange'>"+
            downtag+
            "</b>\n",
            class_name = "leaflet-div-icon",
            icon_anchor=(5,30)),
          )
        )

      warddistricts = wardelectors.PD.unique()

      p = 0

      ward_node.create_data_branch('PD',warddistricts)
      ward_node.type = "ward"

      for PD_node in ward_node.children:
        PD = PD_node.value
        flayers[5].children = []
        flayers[5].fg = folium.FeatureGroup(id='6', name='PD Markers', overlay=True, control=True, show=True)
#        flayers[4].fg = folium.FeatureGroup(name='Division Boundary', overlay=True, control=True, show=True)

        PDelectors = getblock(allelectors,'PD',PD)
        maplongx = statistics.mean(PDelectors.Long.values)
        maplaty = statistics.mean(PDelectors.Lat.values)
    #    print("PDcoords:",maplongx, maplaty)
        PDcoordinates = [maplaty, maplongx]
        Wardboundary = list([x[2] for x in PDWardlist if x[0] == PD])[0]
    #    Wardboundary = find_boundary(TreeBounds[3],Point(Decimal(maplongx),Decimal(maplaty)))
        if Wardboundary is None:
          print("Cant find Wardboundary - Lat Long:",maplaty,maplongx)
        else:
          uppdtag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(ward_node.parent.dir+"/"+ward_node.parent.file,"UP",10)
          uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(ward_node.dir+"/"+ward_node.file,"UP",10)
          downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(ward_node.dir+"/"+ward_node.file,"DOWN",10)
          Wardboundary["Downcon"] =  "<br>"+Ward+"</br>"+ downtag
          Wardboundary["UP"] =  "<br>"+Ward+"</br>"+uptag
          Wardboundary["UPpd"] =  "<br>"+Ward+"</br>"+uppdtag
          add_to_wards_layer (flayers[4].children, Wardboundary, flayers[4].fg, "UP", Ward)
          add_to_ward_layer (Wardboundary, flayers[4].fg, "UP", Ward)
          add_to_ward_layer (Wardboundary, flayers[4].fg, "UPpd", Ward)

#        Divboundary = find_boundary(TreeBounds[4],Point(Decimal(maplongx),Decimal(maplaty)))

#        if Divboundary is None:
#          print("Cant find Divboundary - Lat Long:",maplaty,maplongx)
#        else:
#          Divname = str(Divboundary['NAME'].values[0]).replace(r'[^A-Za-z0-9\& ]+', '').replace(",","").replace(" & "," AND ").upper().replace(" ","_")
#          Divfid = Divboundary['FID'].values[0]
#          gapnode.create_data_branch(Divname)
#          div_node = gapnode.child
#          div_node.type = "div"
#          pfile = TreeBounds[4]
#          Divboundary = pfile[pfile['FID']==Divfid]

#          upfromdivtag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(div_node.parent.dir+"/"+div_node.parent.file,"UP",10)
#          upfrompdtag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(div_node.dir+"/"+div_node.file,"UP",10)
#          downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(div_node.dir+"/"+div_node.file,"DOWN",10)
#          downpdtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(PD_node.dir+"/"+PD_node.file,"DOWN",10)
#          Div = Divname+"-MAP.html"
#          Divboundary["Downcon"] =  "<br>"+Divname+"</br>"+downtag
#          Divboundary["Downdiv"] =  "<br>"+Divname+"</br>"+downpdtag
#          Divboundary["UPdiv"] =  "<br>"+Divname+"</br>"+upfromdivtag
#          Divboundary["UPpd"] =  "<br>"+Divname+"</br>"+upfrompdtag
#          Divdir = locmappath(Codir+"/"+Divname,"")
#          PDDivdir = locmappath(Divdir+"/"+str(PD),Wadir+"/"+str(PD))
#
#          Divmap = add_to_divs_layer (flayers[4].children, Divboundary, flayers[4].fg, "UPdiv",Divname)


#          add_to_div_layer (Divboundary, flayers[4].fg,"UPdiv", Divname)
#          add_to_div_layer (Divboundary, flayers[4].fg,"UPpd", Divname)

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


        here = Point(Decimal(x[0]),Decimal(y[0]))
        sw = PDelectors[['Lat', 'Long']].min().values.tolist()
        ne = PDelectors[['Lat', 'Long']].max().values.tolist()
        swne = [sw,ne]
        PDmap = PD_node.create_area_map (flayers,PDelectors)
        PDmap.add_css_link("electtrekcss","https://newbrie.github.io/Electtrek/static/print.css")
        PDmap.add_css_link("electtrekcss","https://newbrie.github.io/Electtrek/static/style.css")

        PDMapfile = PD_node.file
        PD_node.locmappath("")

        downpdtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(PD_node.dir+"/"+PD_node.file,PD_node.value,14)


            # in the wards map add PD polling districts to the ward map with controls to go back up to the constituency map or down to the PD map
        type_colour = allowed["C1"]
        flayers[5].fg.add_child(
          folium.Marker(
            location=PDcoordinates,
            icon = folium.DivIcon(html= downpdtag,
            class_name = "leaflet-div-icon",
            icon_size=(5,30),
            icon_anchor=(5,30)),
           )
          )

#        if Divboundary is not None:
#          Divmap.add_child(
#            folium.Marker(
#              location=PDcoordinates,
#              icon = folium.DivIcon(html= downpdtag,
#              class_name = "leaflet-div-icon",
#              icon_size=(5,30),
#              icon_anchor=(5,30)),
#              ))

        clusters = PDelectors.Clabel.unique()
        print ("____________clusters",clusters)
        c = 0

        CCstreets = PDelectors.StreetName.unique()
        prodstats['streets'] = int(prodstats['streets']) + len(CCstreets)

        streetsdir = PD_node.dir+"/STREETS/"

        PD_node.create_data_branch('street',CCstreets)

        for street_node in PD_node.children:
          street = street_node.value
          uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: gray'>{1}</button></form>".format(street_node.parent.dir+"/"+street_node.parent.file,"UP",10)
          flayers[6].children = []
          flayers[6].fg = folium.FeatureGroup(id=7, name='Street Markers', overlay=True, control=True, show=True)
#          flayers[4].fg = folium.FeatureGroup(name='Division Boundary', overlay=True, control=True, show=True)
          Wardboundary["UPstreet"] = "<br>"+Ward+"</br>"+ uptag
          add_to_ward_layer (Wardboundary, flayers[6].fg,"UPstreet", Ward)

#          if Divboundary is not None:
#            Divboundary["UPstreet"] =  "<br>"+Divname+"</br>"+uptag
#            add_to_div_layer (Divboundary, flayers[4].fg, "UPstreet", Divname)

          electorwalks = getblock(PDelectors, 'StreetName',street)
          maplongx = statistics.mean(electorwalks.Long.values)
          maplaty = statistics.mean(electorwalks.Lat.values)
          walkcoordinates = [maplaty, maplongx]
          STREET_ = street.replace(r'[^A-Za-z0-9\& ]+', '').replace(",","").replace(" & "," AND ").upper().replace(" ","_")


          here = Point(Decimal(maplongx),Decimal(maplaty))

          Postcode = electorwalks.loc[0].Postcode

          walk_name = PD+"-"+STREET_
          street_node.dir =  streetsdir
          street_node.file =  STREET_+"-PRINT.html"
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


    #      marker_cluster = MarkerCluster().add_to(Walkmap)
          # Iterate through the street-postcode list and add a marker for each unique lat long, color-coded by its Cluster.


          for streetcoordinates in CL_unique_list:
            uptag = "<form action= '/upbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(street_node.parent.dir+"/"+street_node.parent.file,"UP",12)
            downtag = "<form action= '/downbut/{0}' ><button type='submit' style='font-size: {2}pt;color: red'>{1}</button></form>".format(street_node.dir+"/"+street_node.file,street_node.value,12)

            # in the Walk map add Street-postcode groups to the walk map with controls to go back up to the PD map or down to the Walk addresses
            popuptext = '<ul style="font-size: {5}pt;color: gray;" >Ward: {0} WalkNo: {1} Postcode: {2} {3} {4}</ul>'.format(Ward,STREET_, Postcode, uptag, downtag,12)

            # in the PD map add PD-cluster walks to the PD map with controls to go back up to the Ward map or down to the Walk map
            flayers[6].fg.add_child(
              folium.Marker(
                 location=streetcoordinates,
                 popup = popuptext,
                 icon=folium.Icon(color = type_colour,  icon='search'),
                 )
                 )


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
          prodstats['ward'] = Ward
          prodstats['PD'] = PD
          prodstats['groupelectors'] = groupelectors
          prodstats['climb'] = climb
          prodstats['houses'] = houses
          prodstats['streets'] = streets
          prodstats['housedensity'] = housedensity
          prodstats['leafhrs'] = round(leafhrs,2)
          prodstats['canvasshrs'] = round(canvasshrs,2)

          electorwalks['ENOP'] =  electorwalks['ENO']+ electorwalks['Suffix']*0.1

          results_filename = walk_name+"-PRINT.html"


          context = {
            "group": electorwalks,
            "prodstats": prodstats,
            "mapfile": "../STREETS/"+PDMapfile,
            }
          results_template = enviro.get_template('canvasscard1.html')

          with open(results_filename, mode="w", encoding="utf-8") as results:
            results.write(results_template.render(context, url_for=url_for))


          c = c + 1
        target = PD_node.locmappath("")
        for r in range(5,7):
          PDmap.add_child(flayers[r].fg)
#        PDmap.add_child(folium.LayerControl())
        PDmap.save(target)
        p = p + 1
      target =  ward_node.locmappath("")
      for r in range(4,6):
         Wardmap.add_child(flayers[r].fg)
#      Wardmap.add_child(folium.LayerControl())
      Wardmap.save(target)
      w = w + 1
#      if w == 3:
#          raise Exception('XYZ')
#    for fid,fmap,fdir,fpath in DivMapfilelist:
     # print ("fmaplist:",fid,fmap,fdir,fpath)
#      fmap.add_child(flayers[0].fg)
#      fmap.add_child(flayers[1].fg)
#      fmap.add_child(flayers[2].fg)
#      fmap.add_child(flayers[3].fg)
#      fmap.add_child(flayers[4].fg)
#      fmap.add_child(folium.LayerControl())
#      target = div_node.locmappath("")
#      fmap.save(target)

    target = gapnode.locmappath("")
    for r in range(1,4):
        Conmap.add_child(flayers[r].fg)
#    Conmap.add_child(folium.LayerControl())
    Conmap.save(target)
    prodstats['status'] = "Street Cards generated"
    return [allelectors, prodstats,gapnode.dir+"/"+gapnode.file]

if __name__ == "__main__":
    # this won't be run when imported
    prodcards()
