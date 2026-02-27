from folium import FeatureGroup
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
from folium import GeoJson, Tooltip, Popup
from shapely.geometry import Point, Polygon
from geovoronoi import voronoi_regions_from_coords
import numpy as np
import folium
from datetime import datetime, timedelta, date
from elections import route, CurrentElection, stepify
import json
import os
import html

import colorsys
from matplotlib.colors import to_hex, to_rgb

def Hconcat(house_list):
    # Make sure house_list is iterable and not accidentally a DataFrame or something else
    try:
        return ', '.join(sorted(set(map(str, house_list))))
    except Exception as e:
        print("❌ Error in Hconcat:", e)
        print("Type of house_list:", type(house_list))
        raise


import geopandas as gpd


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



def build_street_list_html(streets_df):
    # Voting intention map
    from state import VID
    from collections import Counter

    def count_units_from_column(df, column):
        # count of all unique house numbers or names in the column across all electors
        all_units = (
            unit.strip()
            for row in df[column].dropna()
            for unit in str(row).split(',')
            if unit.strip().lower() != 'nan' and unit.strip() != ''
        )
        return Counter(all_units)


    def extract_unit(row):
        # building a new unit column value by combining the contents of AddressNumber and AddressPrefix
        prefix = str(row['AddressPrefix']).strip() if pd.notna(row['AddressPrefix']) else ''
        number = str(row['AddressNumber']).strip() if pd.notna(row['AddressNumber']) else ''

        # Return the first valid field (not empty, not "nan")
        if prefix and prefix.lower() != 'nan':
            return prefix
        if number and number.lower() != 'nan':
            return number
        return None


    streets_df['unit'] = streets_df.apply(extract_unit, axis=1)
    print(f"____Street_df:{streets_df['unit']} ")

    html = '''
    <div style="
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 10px;
        background-color: black; !important;
        color: white; !important;
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
                    <th style="text-align:left; padding: 4px;">Street Name</th>
                    <th style="text-align:left; padding: 4px;">Total</th>
                    <th style="text-align:left; padding: 4px;">Range</th>
                    <th style="text-align:left; padding: 4px;">Unit</th>
                    <th style="text-align:left; padding: 4px;">VI</th>
                    <th style="text-align:left; padding: 4px;">Votes</th>
                </tr>
            </thead>
            <tbody>
    '''
    unit_set = set()
    num_values = set()

    # Now group by street name and extract per-unit counts
    for street_name, street_group in streets_df.groupby("StreetName"):
        # Inside your loop for street_name, street_group in streets_df.groupby("Name"):
        unit_counts = count_units_from_column(street_group, 'unit')

        # JSON version for embedding in HTML
        unit_counts_json = json.dumps(unit_counts)

        print(f"Street: {street_name}")
        print(f"Unit Counts: {unit_counts}")
        print(f"JSON: {unit_counts_json}")

        unit_set = set()
        num_values = []

        for _, row in street_group.iterrows():  # ✅ only iterate this street's rows
            if pd.notna(row['unit']):
                parts = str(row['unit']).split(',')
                for part in parts:
                    val = part.strip()
                    if val and val.lower() != 'nan':
                        unit_set.add(val)
                        match = re.search(r'\d+', val)
                        if match:
                            num_values.append(int(match.group()))

        unit_list = sorted(unit_set)
        total_units = len(unit_list) or 1
        hos = total_units

        # Address range display
        num_values = sorted(num_values)
        num_display = f"({min(num_values)} - {max(num_values)})" if num_values else "( - )"

        # Unit dropdown
        unit_dropdown = f'''
        <select onchange="updateMaxVote(this)" style='width: 100%; font-size: 8pt;'>
            {"".join(f'<option value="{u}" data-max="{unit_counts.get(u, 1)}">{u}</option>' for u in unit_list)}
        </select>
        '''

        # VI select
        vi_select = '<select style="font-size:8pt;">' + ''.join(
            f'<option value="{key}">{value}</option>' for key, value in VID.items()
            ) + '</select>'



        first_unit = unit_list[0] if unit_list else None
        max_votes = unit_counts.get(first_unit, 1) if first_unit else 1



        vote_button = f'''
            <button onclick="incrementVoteCount(this)" data-count="0" data-max="{max_votes}" style="font-size: 8pt;">0/{max_votes}</button>
        '''
        print(f"unit_dropdown: {unit_dropdown}")
        print(f"vi_select: {vi_select}")
        print(f"vote_button: {vote_button}")

        # Add row
        html += f'''
        <tr>
            <td style="padding: 4px; font-size: 8pt;"><b data-name="{street_name}" data-unit-counts='{unit_counts_json}'>{street_name} </b></td>
            <td style="padding: 4px; font-size: 8pt;"><i>{hos}</i></td>
            <td style="padding: 4px; font-size: 8pt;">{num_display}</td>
            <td style="padding: 4px;">{unit_dropdown}</td>
            <td style="padding: 4px;">{vi_select}</td>
            <td style="padding: 4px;">{vote_button}</td>
        </tr>
        '''

    html += '''
            </tbody>
        </table>
    </div>
    '''

    return html



def build_nodemap_list_html(herenode):
    """
    Build HTML tooltip listing all children of a node.
    Returns a string of safe HTML.
    """

    if not herenode or not getattr(herenode, "children", None):
        return "<em>No children</em>"

    items_html = []

    for child in herenode.children:
        # Safely escape for HTML
        label = getattr(child, "name", None) or getattr(child, "value", "") or "Unnamed"
        label = html.escape(str(label))

        items_html.append(f"<li>{label}</li>")

    # Wrap in tooltip-friendly minimal markup
    tooltip_html = "<ul style='margin:0; padding-left:1em;'>" + "".join(items_html) + "</ul>"

    return tooltip_html


class ExtendedFeatureGroup(FeatureGroup):
    def __init__(self, name=None, overlay=True, control=True, show=True):
        super().__init__(
            name=name,
            overlay=overlay,
            control=control,
            show=show
        )
        self.name = name         # <--- explicitly store it
        self.key = None
        self.mytag = None
        self.id = None
        self.areashtml = {}

    def _render_single_node(self, c_election, node, intention_type, static, counters):

        CElection = CurrentElection.load(c_election)
        rlevels = CElection.resolved_levels

        if intention_type == "marker":
            self.add_genmarkers(CElection, rlevels, node, "marker", static)

        elif intention_type in ("street", "walkleg"):
            self.add_nodemarks(c_election, rlevels, node, intention_type, static)

        elif intention_type in ("polling_district", "walk"):
            self.generate_voronoi_with_geovoronoi(
                c_election, rlevels, node, intention_type, static
            )

        else:
            self.add_nodemaps(c_election, rlevels, node, intention_type, static, counters)


    def create_layer(self, c_election, nodelist, intention_type, static=False):
        from flask import session
        from elections import branchcolours
        from state import Treepolys, Fullpolys

        from collections import defaultdict


        print(f"Layer {intention_type} memory id:", id(self))
        accumulate = session.get("accumulate", False)

        if not accumulate:
            print(f"CLEARING THE LAYER: {accumulate}", id(self))
            self._children.clear()  # Only clear if accumulate is off
        counters = defaultdict(int)
        i = 0
        for n in nodelist:
            n.defcol = branchcolours[i]
            self._render_single_node(c_election, n, intention_type, static, counters)
            i = i+1

        return len(self._children)



    def reset(self):
        # This clears internal children before rendering
        self._children.clear()
        self.areashtml = {}
        print("____reset the layer",len(self._children), self)
        return self


    def generate_voronoi_with_geovoronoi(self, c_election, rlevels,target_node, vtype, static=False, add_to_map=True, color="#3388ff"):
        global allelectors
        global levelcolours
        from state import Treepolys, Fullpolys
        from elector import electors

        allelectors = electors.get(c_election)
    # generate voronoi fields within the target_node Boundary
        shapecolumn = { 'polling_district' : 'PD','walk' : 'WalkName' ,'ward' : 'Area', 'division' : 'Area', 'constituency' : 'Area'}

        print("📍 Starting generate_voronoi_with_geovoronoi")

        CElection = CurrentElection.load(c_election)
        print(f"🗳️ Loaded election data for: {c_election}")

        target_path = target_node.mapfile(rlevels)
        print(f"📁 Target path: {target_path}")

        print(f"📌 Target node: {target_node.value}")

        ttype = target_node.type
        print(f"📂 Territory type: {ttype}")

        pfile = Treepolys[ttype]
        print(f"🗺️ Loaded polygon file for type '{ttype}', records: {len(pfile)}")

        # Select boundary by FID
        Territory_boundary = pfile[pfile['FID'] == int(target_node.fid)]
        print(f"🧭 Filtered territory boundary by FID = {target_node.fid}, matches: {len(Territory_boundary)}")

        # Get the shapely polygon for area
        if hasattr(Territory_boundary, 'geometry'):
            area_shape = Territory_boundary.union_all()
            print("✅ Retrieved union of territory boundary geometry")
        else:
            area_shape = Territory_boundary
            print("⚠️ Warning: Territory_boundary has no .geometry — using raw")

        children = target_node.childrenoftype(vtype)
        print(f"👶 Found {len(children)} children of type '{vtype}'")
    # children nodes are the target child Walks/PDs polygons which should fit into area_shape

        if not children:
            print("⚠️ No children found so no fields for the node— exiting early")
            # no children means no fields
            return []

        # Build coords array from centroids
        from shapely.ops import nearest_points

        mask = (
                (allelectors['Election'] == c_election) &
                (allelectors['Area'] == target_node.value)
            )
        nodeelectors = allelectors[mask]
# these are the electors within the area - the area being the Level 4 area(div/ward)

        coords = []
        valid_children = []

        for child in children:
# these are the centroids that will form the centre of each voronoi field
            cent = child.latlongroid
            if isinstance(cent, (tuple, list)) and len(cent) == 2:
                lon, lat = cent[1], cent[0]  # Note: [lon, lat] = [x, y]
            elif hasattr(cent, 'x') and hasattr(cent, 'y'):
                lon, lat = cent.x, cent.y
            else:
                continue

            point = Point(lon, lat)

# Ensure the child centroid is within the overall boundary else centroid of first street within
            if not area_shape.contains(point):
#                childx = target_node.ping_node(c_election,child.dir)
#                print(f"Point {point} is not in shape so looking at children:",[x.value for x in child.children])


                p1, _ = nearest_points(area_shape, point)
                point = p1  # now point is on area_shape
                print(f"Point {point} is not in shape {area_shape} so looking at nearest point")

#                for grandchild in child.children:
#                    cent = grandchild.latlongroid
#                    point = Point(cent[1],cent[0])
#                    if area_shape.contains(point):
#                        print("___Selecting right child within shape as field centroid", grandchild.dir, point)
#                       found a child inside the area
#                        break
    #                point, _ = nearest_points(area_shape, point)

            coords.append([point.x, point.y])  # Ensure only 2D coords
            valid_children.append((child, point))

        # Clip Voronoi regions to area_shape
        # ------------------------------
        # Prepare Voronoi diagnostics
        # ------------------------------

        print("🧮 Preparing Voronoi generation")

        print("---- AREA SHAPE ----")
        print("Type:", area_shape.geom_type)
        print("Has Z:", getattr(area_shape, "has_z", False))
        print("Is valid:", area_shape.is_valid)
        print("Bounds:", area_shape.bounds)
        print("Area:", area_shape.area)

        print("Children processed:", len(valid_children))
        print("Raw coord count:", len(coords))

        if len(coords) == 0:
            print("⚠️ No coordinates collected — aborting Voronoi.")
            return []

        # Convert AFTER loop
        coords = np.array(coords)

        print("---- COORDS ----")
        print("Shape:", coords.shape)

        # Remove duplicates safely
        unique_coords = np.unique(coords, axis=0)
        print("Unique coord count:", len(unique_coords))

        if len(unique_coords) < len(coords):
            print("⚠️ Duplicate coordinates detected.")

        coords = unique_coords

        if len(coords) < 2:
            print("⚠️ Not enough unique points for Voronoi (need ≥2).")
            return []

        # Spread diagnostics (NumPy 2 safe)
        lon_spread = np.ptp(coords[:, 0])
        lat_spread = np.ptp(coords[:, 1])

        print("Longitude range:", coords[:,0].min(), "→", coords[:,0].max(),
              " (spread:", lon_spread, ")")
        print("Latitude range:", coords[:,1].min(), "→", coords[:,1].max(),
              " (spread:", lat_spread, ")")

        if lon_spread < 1e-12 or lat_spread < 1e-12:
            print("⚠️ Points are collinear or nearly collinear.")

        print("------------------------------")

        # ------------------------------
        # Run Voronoi
        # ------------------------------

        print("🧮 Generating Voronoi regions using geovoronoi...")

        if coords.shape[1] != 2:
            raise ValueError(f"Expected 2D coordinates, got shape: {coords.shape}")

        try:
            region_polys, region_pts = voronoi_regions_from_coords(
                coords,
                area_shape,
                qhull_options="Qbb Qc Qz QJ"  # Joggle for robustness
            )
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
            #  one walk child matched to region_polygon
                matched_child.voronoi_region = region_polygon
                print(f"✅ Region {region_index} assigned to child: {matched_child.value}")
                voronoi_regions.append({'child': matched_child, 'region': region_polygon})
            else:
                print(f"⚠️ No matching child found for region index {region_index}")


            if matched_child and add_to_map:
                label = str(matched_child.value)

                # Here, we dynamically assign a color, either from the child or default to color
                fill_color = getattr(child, "col", color)  # If no color assigned, default to passed color

                # You can also dynamically generate colors based on the child or other parameters
                # For example, using a hash of the child's value to generate a unique color:
                # fill_color = '#' + hashlib.md5(str(child.value).encode()).hexdigest()[:6]

                mask1 = nodeelectors[shapecolumn[vtype]] == child.value
                region_electors = nodeelectors[mask1]
#________________________First get the data that the walk layer polygon fields requires
                if not region_electors.empty and len(region_electors.dropna(how="all")) > 0:
                    Streetsdf = pd.DataFrame(region_electors, columns=['StreetName', 'ENOP','Long', 'Lat', 'Zone','AddressNumber','AddressPrefix' ])
#                    Streetsdf1 = Streetsdf0.rename(columns= {'StreetName': 'Name'})
#                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count', 'Zone' : 'first', 'AddressNumber': Hconcat , 'AddressPrefix' : Hconcat,}
#                    g = {'Lat':'mean','Long':'mean', 'ENOP':'count', 'Zone' : 'first','AddressNumber': lambda x: ','.join(x.dropna().astype(str)),
#                        'AddressPrefix': lambda x: ','.join(x.dropna().astype(str))
#                        }
#                    Streetsdf = Streetsdf0.groupby(['StreetName']).agg(g).reset_index()
#    build the area html for dropdowns and tooltips
                    streetstag = build_street_list_html(Streetsdf)
                    streets = Streetsdf["StreetName"].unique().tolist()
                    self.areashtml[matched_child.value] = {
                                        "code": matched_child.value,
                                        "details": streets,
                                        "tooltip_html": streetstag
                                        }
                    print (f"______Voronoi html at : {matched_child.value} details {streets} tooltip html:{streetstag}")
                    print ("______Voronoi Streetsdf:",len(Streetsdf), streetstag)
                    print (f" {len(Streetsdf)} streets exist in {target_node.value} under {c_election} election for the {shapecolumn[vtype]} column with this value {child.value}")

                    points = [Point(lon, lat) for lon, lat in zip(Streetsdf['Long'], Streetsdf['Lat'])]
                    print('_______Walk Shape', matched_child.value, matched_child.level, len(Streetsdf), points)

                    # Create a single MultiPoint geometry that contains all the points
                    multi_point = MultiPoint(points)
                    centroid = multi_point.centroid

                    # Access coordinates
                    centroid_lon = centroid.x
                    centroid_lat = centroid.y
    #                target_node.latlongroid = (centroid_lat,centroid_lon)

                    # Create a new DataFrame for a single row GeoDataFrame
                    gdf = gpd.GeoDataFrame({
                        'NAME': [matched_child.value],  # You can modify this name to fit your case
                        'FID': [matched_child.fid],  # FID can be a unique value for the row
                        'LAT': [multi_point.centroid.y],  # You can modify this name to fit your case
                        'LONG': [multi_point.centroid.x],  # FID can be a unique value for the row
                        'geometry': [multi_point]  # The geometry field contains the MultiPoint geometry
                    }, crs="EPSG:4326")


                    #            limb = gpd.GeoDataFrame(df, geometry= [convex], crs='EPSG:4326')
                    #        limb = gpd.GeoDataFrame(df, geometry= [circle], crs="EPSG:4326")
                    # Generate enclosing shape
                    limbX = matched_child.create_enclosing_gdf(gdf)
                    limbX['col'] = matched_child.col
                    numtag = str(matched_child.tagno)+" "+str(matched_child.value)
                    num = str(matched_child.tagno)
                    tag = str(matched_child.value)
                    typetag = "streets in "+str(matched_child.type)+" "+str(matched_child.value)

                    popup_html = ""

                    if vtype == 'polling_district':
                        showmessageST = "showMore(&#39;/PDdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.dir+"/"+matched_child.file(rlevels) +" street", matched_child.value,'street')
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.parent.dir+"/"+matched_child.parent.file(rlevels), matched_child.parent.value,matched_child.parent.type)
                    #            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(target_node.dir+"/"+target_node.file(rlevels), target_node.value,child_type_of('polling_district',estyle))
                        downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
                    #            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
                    #            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,session.get('importfile'), target_node.dir+"/"+target_node.file(rlevels))
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limbX['UPDOWN'] = uptag1 +"<br>"+ downST
                        print("_________new PD convex hull and tagno:  ",matched_child.value, matched_child.tagno, gdf)

                        streetstag = ""
                    elif vtype == 'walk':
                        showmessage = "showMore(&#39;/WKdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.dir+"/"+matched_child.file(rlevels)+" walkleg", matched_child.value,'walkleg')
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(matched_child.parent.dir+"/"+matched_child.parent.file(rlevels), matched_child.parent.value,matched_child.parent.type)
                        downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        streetstag = build_street_list_html(Streetsdf)
                        limbX['UPDOWN'] =  "<div style='white-space: normal'>" + uptag1 +"<br>"+downtag+"</div>"
                        print("_________new Walk convex hull and tagno:  ",matched_child.value, matched_child.tagno)

    #________________________Now paint items onto the walk layer
                    if not static:
                        limbX = limbX.to_crs("EPSG:4326")
                        limb = limbX.iloc[[0]].__geo_interface__ # Ensure this returns a GeoJSON dictionary for the row

                        feature = limb['features'][0]
                        props = feature['properties']
                        popup_html = f"""
                        <div style='white-space: normal; text-align: center' >
                            <strong> {typetag}:<br></strong> {props.get('UPDOWN', 'N/A')}<br> {streetstag}<br>
                        </div>
                        """

                        popup = folium.Popup(popup_html, max_width=600)
                        #        target_node.tagno = len(self._children)+1
                        pathref = matched_child.mapfile(rlevels)
                        mapfile = '/transfer/'+pathref
                        # Turn into HTML list items

                        # Ensure 'properties' exists in the GeoJSON and add 'col'
                        print("GeoJSON Convex creation:", limb)
                        if 'properties' not in limb:
                            limb['properties'] = {}

                        # Add the color to properties — this is **required**
                        limb['properties']['col'] = to_hex(matched_child.col)

                        geojson_feature = {
                            "type": "Feature",
                            "properties": {"col": fill_color},
                            "geometry": region_polygon.__geo_interface__,
                        }
                        gj = folium.GeoJson(
                            data=json.loads(json.dumps(geojson_feature)),
                            style_function=lambda feature: {
                                'fillColor': feature["properties"]["col"],
                                'color': '#FFFFFF',     # white border
                                'weight': 4,            # thinner, adjustable
                                'fillOpacity': 0.4,
                                'opacity': 1.0,         # ensure stroke visible
                                'stroke': True,         # explicitly enable stroke
                            },
                            name=f"Voronoi {label}",
                            tooltip=folium.Tooltip(label),
                            popup=popup,
                        )
                        gj.add_to(self)
                        print(f"🖼️ Added Non-static GeoJson for child: {label} nodecol: {child.col} with color: {fill_color}")

                        centroid = region_polygon.centroid
                        cent = [centroid.y, centroid.x]  # folium expects (lat, lon)

                        tag = matched_child.value

                        mapfile = matched_child.mapfile(rlevels)

                        tcol = get_text_color(to_hex(fill_color))
                        bcol = adjust_boundary_color(to_hex(fill_color), 0.7)
                        fcol = invert_black_white(tcol)
                        self.add_child(folium.Marker(
                             location=[cent[0], cent[1]],
                             icon = folium.DivIcon(
                                    html=f'''
                                    <a href="{mapfile}" data-name="{tag}">
                                        <div style="
                                            color: {tcol};
                                            font-size: 10pt;
                                            font-weight: bold;
                                            text-align: center;
                                            padding: 2px;
                                            white-space: nowrap;">
                                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                            border: 2px solid black;">{tag}</span>
                                        </div>
                                    </a>
                                    '''
                                    ,
                                   )
                                   )
                                   )
                    else:
                        limbX = limbX.to_crs("EPSG:4326")
                        limb = limbX.iloc[[0]].__geo_interface__ # Ensure this returns a GeoJSON dictionary for the row

                        feature = limb['features'][0]
                        props = feature['properties']
                        popup_html = f"""
                        <div style='white-space: normal; text-align: center' >
                            <strong> {typetag}:<br></strong> <br> {streetstag}<br>
                        </div>
                        """
                        # Turn into HTML list items
                        popup = folium.Popup(popup_html, max_width=600)
                        #        target_node.tagno = len(self._children)+1
                        # Turn into HTML list items
                        # Ensure 'properties' exists in the GeoJSON and add 'col'
                        print("GeoJSON Convex creation:", limb)
                        if 'properties' not in limb:
                            limb['properties'] = {}

                        # Add the color to properties — this is **required**
                        limb['properties']['col'] = to_hex(matched_child.col)

                        geojson_feature = {
                            "type": "Feature",
                            "properties": {"col": fill_color},
                            "geometry": region_polygon.__geo_interface__,
                        }
                        gj = folium.GeoJson(
                            data=json.loads(json.dumps(geojson_feature)),
                            style_function=lambda feature: {
                                'fillColor': feature["properties"]["col"],
                                'color': '#FFFFFF',     # white border
                                'weight': 4,            # thinner, adjustable
                                'fillOpacity': 0.4,
                                'opacity': 1.0,         # ensure stroke visible
                                'stroke': True,         # explicitly enable stroke
                            },
                            name=f"Voronoi {label}",
                            tooltip=folium.Tooltip(label),
                            popup=popup,
                        )
                        gj.add_to(self)

                        print(f"🖼️ Added Static GeoJson for child: {label} nodecol: {child.col} with color: {fill_color}")

                        centroid = region_polygon.centroid
                        cent = [centroid.y, centroid.x]  # folium expects (lat, lon)

                        tag = matched_child.value

                        tcol = get_text_color(to_hex(fill_color))
                        bcol = adjust_boundary_color(to_hex(fill_color), 0.7)
                        fcol = invert_black_white(tcol)
                        self.add_child(folium.Marker(
                             location=[cent[0], cent[1]],
                             icon = folium.DivIcon(
                                    html=f'''
                                    <a data-name="{tag}">
                                        <div style="
                                            color: {tcol};
                                            font-size: 10pt;
                                            font-weight: bold;
                                            text-align: center;
                                            padding: 2px;
                                            white-space: nowrap;">
                                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                            border: 2px solid black;">{tag}</span>
                                        </div>
                                    </a>
                                    '''
                                    ,
                                   )
                                   )
                                   )
                    print(f"🖼️ Added walk area marker: {tag} with color: {tcol}")

                voronoi_regions.append({
                    'child': matched_child,
                    'region': region_polygon
                })
            else:
                flash("no data exists for this election at this location")
                print (f" no walks exist for this region {region_polygon} under this {c_election} election ")

        print("✅ Voronoi generation complete.")
        return voronoi_regions



    def add_shapenodes (self,c_election,rlevels,herenode,stype):
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
                self.add_shapenode(rlevels,shape_node, stype,Streetsdf)
                print("_______new shape node ",shape_node.value,shape_node.col,"|")
            else:
                flash("no data exists for this election at this location")
                print (f"_nodes exist at {herenode.value} but not for this {c_election} election and this {shapecolumn[stype]} column with this value {shape_node.value}")

        return self._children



    def add_shapenode (self,rlevels, herenode,type,datablock):
        global levelcolours

        points = [Point(lon, lat) for lon, lat in zip(datablock['Long'], datablock['Lat'])]
        print('_______Walk Shape', herenode.value, herenode.level, len(datablock), points)

        # Create a single MultiPoint geometry that contains all the points
        multi_point = MultiPoint(points)
        centroid = multi_point.centroid

        # Access coordinates
        centroid_lon = centroid.x
        centroid_lat = centroid.y
        herenode.latlongroid = (centroid_lat,centroid_lon)

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
            showmessageST = "showMore(&#39;/PDdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(rlevels) +" street", herenode.value,'street')
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file(rlevels), herenode.parent.value,herenode.parent.type)
#            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(rlevels), herenode.value,child_type_of('polling_district',estyle))
            downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
#            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
#            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,session.get('importfile'), herenode.dir+"/"+herenode.file(rlevels))
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limbX['UPDOWN'] = uptag1 +"<br>"+ downST
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno, gdf)
        elif type == 'walk':
            showmessage = "showMore(&#39;/WKdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(rlevels)+" walkleg", herenode.value,'walkleg')
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file(rlevels), herenode.parent.value,herenode.parent.type)
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
        here = [float(f"{herenode.latlongroid[0]:.6f}"), float(f"{herenode.latlongroid[1]:.6f}")]
        pathref = herenode.mapfile(rlevels)
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
                        html=f'''
                        <a href='{mapfile}' data-name='{tag}'><div style="
                            color: {tcol};
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{tag}</span>
                            </div></a>
                            ''',
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
                        html=f'''
                        <a href='{mapfile}' data-name='{tag}'><div style="
                            color: {tcol};
                            font-size: 10pt;
                            font-weight: bold;
                            text-align: center;
                            padding: 2px;
                            white-space: nowrap;">
                            <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                            border: 2px solid black;">{num}</span>
                            {tag}</div></a>
                            ''',
                       )
                       )
                       )
        print("________Layer map polys",herenode.value,herenode.level,self._children)
        return self._children

    def add_genmarkers(self, CE, rlevels, node, type, static):
        eventlist = node.build_eventlist_dataframe(CE)
        print(f" ___GenMarkers: under {route()} eventlist: {eventlist}")
        for _, row in eventlist.iterrows():

            for place in row["places"]:
                lat = place["lat"]
                lng = place["lng"]
                tag = place["prefix"]
                url = place["url"]

                days_to = (row["date"] - datetime.today().date()).days
                fontsize = compute_font_size(days_to)

                tooltip = f"{tag} ({row['date']})"
                print(f"___layer marker: {tag} at {lat},{lng} on {row['date']}")

                self.add_child(folium.Marker(
                    location=[lat, lng],
                    tooltip=tooltip,
                    icon=folium.DivIcon(html=f"""
                        <a href='{url}' data-name='{tag}'>
                            <div style="color:yellow;font-weight:bold;text-align:center;padding:2px;">
                                <span style="font-size:{fontsize}px;background:red;padding:1px 2px;
                                             border-radius:5px;border:2px solid black;">
                                    {days_to}
                                </span> {tag}
                            </div>
                        </a>
                    """)
                ))

        return eventlist

    def add_nodemaps (self,c_election,rlevels, herenode,type,static, counters):
        from state import Treepolys, Fullpolys, Candidates, LastResults

        from flask import session
        global levelcolours
        global Con_Results_data
        global OPTIONS

        childlist = herenode.childrenoftype(type)
        allchildlist = herenode.children
        nodeshtml = build_nodemap_list_html(herenode)
        CElection = CurrentElection.load(c_election)
        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
                            "code": herenode.value,
                            "details": details,
                            "tooltip_html": nodeshtml
                            }

        print(f"_________Nodemap: at {herenode.value} we have {len(childlist)} children of type:{type} they are {[x.value for x in childlist]}" )

# reset counters of child type to so that child tag = this node's childno
        accumulate = session.get("accumulate", False)
        if not accumulate:
            counters[rlevels[herenode.level+1]] = 0

        for c in childlist:
            print(f"______Displayed nodemaps:{len(childlist)} at {herenode.value} of type {c.value,type}")
            print(f"______All nodemaps:{len(allchildlist)} at {herenode.value}")

#            layerfids = [x.fid for x in self._children if x.type == type]
#            if c.fid not in layerfids:
            if c.level+1 <= 5:
                results = []
    #need to select the children boundaries associated with the children nodes - to paint
                pfile = Treepolys[type]
                print(f"______Add_Nodemap Treepolys type:{type} size:{len(pfile)}")
                mask = pfile['FID']==int(c.fid)
                limbX = pfile[mask].copy()

                print(
                    f"⚠️ Boundary rows for node {c.value} (FID={c.fid}): {len(limbX)}"
                )

                if len(limbX) > 0:
                    print("______Add_Nodes Treepolys type:",type)
    #
                    if herenode.level == 0:
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels)+" county", c.value,type)
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels), c.value,herenode.type)
                        downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,type,12)
    #                    res = "<p  width=50 id='results' style='font-size: {0}pt;color: gray'> </p>".format(12)
                        uptag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limbX['UPDOWN'] = uptag+"<br>"+c.value+"<br>"  + downtag
    #                    c.tagno = len(self._children)+1
                        mapfile = "/transfer/"+c.mapfile(rlevels)
    #                        self.children.append(c)
                    elif herenode.level == 1:
                        wardreportmess = "moveDown(&#39;/wardreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels), c.value,type)
                        divreportmess = "moveDown(&#39;/divreport/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels), c.value,type)
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels)+" constituency", c.value,type)
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(rlevels), herenode.value,herenode.type)
                        wardreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(wardreportmess,"WARD Report",12)
                        divreporttag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(divreportmess,"DIV Report",12)
                        downconstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downmessage,"CONSTITUENCIES",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
                        limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ wardreporttag + divreporttag+"<br>"+ downconstag
    #                    c.tagno = len(self._children)+1
                        mapfile = "/transfer/"+c.mapfile(rlevels)
    #                        self.children.append(c)
                    elif herenode.level == 2:
                        downwardmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels)+" ward", c.value,"ward")
                        downdivmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels)+" division", c.value,"division")
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(rlevels), herenode.value,herenode.type)
                        downwardstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downwardmessage,"WARDS",12)
                        downdivstag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(downdivmessage,"DIVS",12)
                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)

                        limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+ downwardstag + " " + downdivstag
    #                    c.tagno = len(self._children)+1
                        mapfile = "/transfer/"+c.mapfile(rlevels)
    #                        self.children.append(c)
                    elif herenode.level == 3:
                        upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(rlevels), herenode.value,herenode.type)
    #                upload = "<input id='importfile' type='file' name='importfile' placeholder='{1}' style='font-size: {0}pt;color: gray'></input>".format(12, session.get('importfile'))

                        PDbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downPDbut/{0}", "{1}", "polling_district");' class='btn btn-norm'>
                                PDs
                            </button>
                        """.format(c.dir+"/"+c.file(rlevels)+" polling_district", c.value)

                        WKbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downWKbut/{0}", "{1}", "walk");' class='btn btn-norm'>
                                WALKS
                            </button>
                        """.format(c.dir+"/"+c.file(rlevels)+" walk", c.value)

                        MWbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downMWbut/{0}", "{1}", "walk");' class='btn btn-norm'>
                                STAT
                            </button>
                        """.format(c.dir+"/"+c.file(rlevels)+" walk", c.value)


                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size:{2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)

                        if not static:
                            limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+PDbtn+" "+WKbtn+" "+MWbtn
                        else:
                            limbX['UPDOWN'] = "<br>"+c.value+"<br>"
    #                    c.tagno = len(self._children)+1
                        pathref = c.mapfile(rlevels)
                        mapfile = '/transfer/'+pathref
    #                        self.children.append(c)


                    party = "("+c.party+")"

                    counters[c.type] += 1
                    num = str(counters[c.type])


                    tag = str(c.value)
                    numtag = str(c.value)+party


                    here = [float(f"{c.latlongroid[0]:.6f}"), float(f"{c.latlongroid[1]:.6f}")]
                    # Convert the first row of the GeoDataFrame to a valid GeoJSON feature

                    # Now you can use limb_geojson as a valid GeoJSON feature
    #                print("GeoJSON Feature:", limb)

                    def readable_text_color(hex_color, threshold=0.55):
                        """Return a dark readable colour that contrasts with hex_color"""
                        hex_color = hex_color.lstrip("#")
                        r, g, b = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
                        luminance = 0.2126*r + 0.7152*g + 0.0722*b

                        # Always return a DARK tone for consistency
                        return "#111111" if luminance > threshold else "#000000"




                    # Add a property for the color to the GeoJSON


                    node_color = herenode.defcol
                    limbX["fillColor"] = node_color  # per-node property


                    node_col = to_hex(limbX['fillColor'].values[0])
                    tcol_node = readable_text_color(node_col)
                    print(f"_____Colour from {herenode.value} col:{herenode.defcol} and limbX {limbX['fillColor'].values[0]}")
                    fcol_node = tcol_node
                    poly_col_node = node_col
                    if c.type == 'division' and isinstance(c.candidates, dict):
                        c1 = c.candidates.get('Candidate_1', '')
                        c2 = c.candidates.get('Candidate_2', '')
                        candidates = f"[{c1},{c2}]"
                    else:
                        candidates = ""


                    htmlhalo =f'''
                    <a href="{mapfile}" data-name="{tag}">
                      <div style="
                        color: {tcol_node};
                        font-size: 10pt;
                        font-weight: bold;
                        text-align: center;
                        padding: 2px;
                        white-space: nowrap;

                        /* 🗺️ Cartographic halo */
                        text-shadow:
                          -1px -1px 0 #fff,
                           1px -1px 0 #fff,
                          -1px  1px 0 #fff,
                           1px  1px 0 #fff,
                           0px  0px 3px #fff;
                      ">
                        <span style="
                          background: {fcol_node};
                          padding: 1px 2px;
                          border-radius: 5px;
                          border: 2px solid black;
                        ">{num}</span>
                        {numtag}<br>
                        <span style="
                            font-size: 6pt;
                            font-weight: normal;
                        ">
                            {candidates}
                        </span>

                      </div>
                    </a>
                    '''

                    folium.GeoJson(
                        limbX,
                        style_function=lambda feature: {
                            "fillColor": feature["properties"]["fillColor"],
                            "color": adjust_boundary_color(feature["properties"]["fillColor"], 0.7),
                            "weight": 3,
                            "opacity": 1.0,
                            "fillOpacity": 0.4,
                            "stroke": True,
                            "dashArray": "5,5",
                        },
                        highlight_function=lambda _: {"fillColor": "lightgray", "fillOpacity": 0.4},
                        tooltip=folium.Tooltip(htmlhalo),
                        popup=folium.GeoJsonPopup(
                            fields=["UPDOWN"],
                            aliases=["Move:"],
                            labels=False,
                            localize=False,
                        ),
                    ).add_to(self)

                    pathref = c.mapfile(rlevels)
                    mapfile = '/transfer/'+pathref



#                    if not static:
#                        self.add_child(folium.Marker(
#                             location=here,
#                             icon = folium.DivIcon(
#                                    html=htmlhalo,
#                                       )
#                                       )
#                                       )
#                    else:
#                        self.add_child(folium.Marker(
#                             location=here,
#                             icon = folium.DivIcon(
#                                    html=htmlhalo,
#                                       )
#                                       )
#                                       )


        return self._children

    def add_nodemarks (self,c_election,rlevels,herenode,type,static):
        global levelcolours

        childlist = herenode.childrenoftype(type)
        nodeshtml = build_nodemap_list_html(herenode)
        CElection = CurrentElection.load(c_election)
        details = [c.value for c in childlist]
        self.areashtml[herenode.value] = {
                            "code": herenode.value,
                            "details": details,
                            "tooltip_html": nodeshtml
                            }
        num = len(herenode.childrenoftype(type))
        print(f"___creating {num} add_nodemarks of type {type} for {herenode.value} at level {herenode.level}")

        for c in [x for x in herenode.childrenoftype(type)]:
            print('_______MAP Markers')
#            layerfids = [x.fid for x in self.children if x.type == type]
#            if c.fid not in layerfids:
            numtag = str(c.tagno)+" "+str(c.value)
            num = str(c.tagno)
            tag = str(c.value)
            here = [float(f"{c.latlongroid[0]:.6f}"), float(f"{c.latlongroid[1]:.6f}")]
            fill = herenode.col
            pathref = c.mapfile(rlevels)
            mapfile = '/transfer/'+pathref

            print("______Display childrenx:",c.value, c.level,type,c.latlongroid )

            tcol = get_text_color(to_hex(c.col))
            bcol = adjust_boundary_color(to_hex(c.col),0.7)
            fcol = invert_black_white(tcol)

            if not static:
                self.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(
                            html=f'''
                            <a href="{mapfile}" data-name="{tag}"><div style="
                                color: {tcol};
                                font-size: 10pt;
                                font-weight: bold;
                                text-align: center;
                                padding: 2px;
                                white-space: nowrap;">
                                <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                border: 2px solid black;">{num}</span>
                                {tag}</div></a>
                                ''',
                           )
                           )
                           )
            else:
                self.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(
                            html=f'''
                            <a data-name="{tag}">
                            <div style="
                                color: {tcol};
                                font-size: 10pt;
                                font-weight: bold;
                                text-align: center;
                                padding: 2px;
                                white-space: nowrap;">
                                <span style="background: {fcol}; padding: 1px 2px; border-radius: 5px;
                                border: 2px solid black;">{num}</span>
                                {tag}</div></a>
                                ''',
                           )
                           )
                           )



        print("________Layer map points",herenode.value,herenode.level,len(self._children))

        return self._children




# -----------------------------
# Layer specs (cleaned up)
# -----------------------------
FEATURE_LAYER_SPECS = {
    "marker": dict(name="marker", mytag="marker", overlay=True, control=True, show=False),
    "country": dict(name="country", mytag="country", overlay=True, control=True, show=False),
    "nation": dict(name="nation", mytag="nation", overlay=True, control=True, show=False),
    "county": dict(name="county", mytag="county", overlay=True, control=True, show=False),
    "constituency": dict(name="constituency", mytag="constituency", overlay=True, control=True, show=False),
    "ward": dict(name="ward", mytag="ward", overlay=True, control=True, show=False),
    "division": dict(name="division", mytag="division", overlay=True, control=True, show=False),
    "polling_district": dict(name="polling_district", mytag="polling_district", overlay=True, control=True, show=False),
    "walk": dict(name="walk", mytag="walk", overlay=True, control=True, show=False),
    "walkleg": dict(name="walkleg", mytag="walkleg", overlay=True, control=True, show=False),
    "street": dict(name="street", mytag="street", overlay=True, control=True, show=False),
    "result": dict(name="result", mytag="result", overlay=True, control=True, show=False),
    "target": dict(name="target", mytag="target", overlay=True, control=True, show=False),
    "data": dict(name="data", mytag="data", overlay=True, control=True, show=False),
}


# -----------------------------
# Factory: make fresh layers per map
# -----------------------------
def make_feature_layers():
    """
    Returns a fresh dict of ExtendedFeatureGroup instances for a single map.
    Each layer has Python-only metadata: .key and .mytag.
    """
    layers = {}

    for key, spec in FEATURE_LAYER_SPECS.items():
        layer = ExtendedFeatureGroup(
            name=spec["name"],
            overlay=spec["overlay"],
            control=spec["control"],
            show=spec["show"],
        )

        # Python-side metadata only, safe to reuse in counters, logging, etc.
        layer.key = key
        layer.mytag = spec["mytag"]

        layers[key] = layer

    return layers




def make_counters():
    return {key: 0 for key in FEATURE_LAYER_SPECS}
