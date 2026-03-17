from folium import FeatureGroup
from folium.features import DivIcon
from folium.utilities import JsCode
from folium.plugins import MarkerCluster
from folium import GeoJson, Tooltip, Popup
from shapely.geometry import Point, Polygon, MultiPoint
from shapely import crosses, contains,covers, union, envelope, intersection
from shapely.ops import nearest_points
from geovoronoi import voronoi_regions_from_coords
import numpy as np
import folium
from datetime import datetime, timedelta, date
from elections import route, CurrentElection, stepify
import json
import os
import html
import pandas as pd
import re
import math

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


def spread_coordinates_vertical(base_lat, base_lon, index, total, spread_lat=0.00005, spread_lon=0.00001):
    """
    Returns slightly offset coordinates to prevent marker overlap.
    Vertical-biased: spreads more in latitude than longitude.

    base_lat, base_lon : original coordinates
    index              : index of this marker in the group (0-based)
    total              : total markers sharing this area
    spread_lat         : max offset in latitude (vertical)
    spread_lon         : max offset in longitude (horizontal)

    Returns: (lat, lon)
    """

    # No need to offset if only one marker
    if total <= 1:
        return base_lat, base_lon

    # Evenly distribute along vertical "arc"
    angle = (math.pi / total) * index  # semi-circle vertically

    offset_lat = base_lat + spread_lat * math.cos(angle)
    offset_lon = base_lon + spread_lon * math.sin(angle)

    return offset_lat, offset_lon

def readable_text_color(hex_color, threshold=0.55):
    """Return a dark readable colour that contrasts with hex_color"""
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
    luminance = 0.2126*r + 0.7152*g + 0.0722*b

    # Always return a DARK tone for consistency
    return "#111111" if luminance > threshold else "#000000"



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

def create_enclosing_gdf(gdf, buffer_size=20):
    """
    Create a GeoDataFrame containing the enclosing shape around a set of geographic points.

    Parameters:
        gdf (GeoDataFrame): A GeoDataFrame with Point geometries (assumed to be EPSG:4326).
        buffer_size (float, optional): Buffer size in meters for single-point cases (default: 20m).

    Returns:
        GeoDataFrame: A GeoDataFrame with one row containing the enclosing shape in EPSG:3857.
    """
    if gdf.empty:
        return gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:3857")

    # Ensure CRS is set
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)

    # Convert to metric CRS for accurate geometry ops
    gdf_3857 = gdf.to_crs("EPSG:3857")

    multi_point = gdf_3857.iloc[0].geometry

    if multi_point.is_empty:
        return gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:3857")

    points = list(multi_point.geoms)

    if len(points) == 1:
        enclosed_shape = points[0]

    elif len(points) == 2:
        p1, p2 = points

        mid_x = (p1.x + p2.x) / 2
        mid_y = (p1.y + p2.y) / 2

        d = np.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

        if d == 0:
            enclosed_shape = p1
        else:
            h = d / np.sqrt(3)
            dx = (p2.y - p1.y) / d
            dy = -(p2.x - p1.x) / d
            p3 = Point(mid_x + h * dx, mid_y + h * dy)
            enclosed_shape = MultiPoint([p1, p2, p3]).convex_hull

    else:
        enclosed_shape = MultiPoint(points).convex_hull

    # Buffer for visual padding
    smoothing_radius = 3*buffer_size if len(points) == 1 else buffer_size * 2
    rounded_shape = enclosed_shape.buffer(smoothing_radius)

    # Build GeoDataFrame with same CRS (EPSG:3857)
    enclosing_gdf = gpd.GeoDataFrame(
        {
            "NAME": gdf.NAME,
            "FID": gdf.FID,
            "LAT": gdf.LAT.values[0],
            "LONG": gdf.LONG.values[0],
            "geometry": [rounded_shape]
        },
        crs="EPSG:3857"
    )

    return enclosing_gdf

def build_street_list_html(streets_df, street_stats):
    from state import VID
    from collections import Counter
    import pandas as pd
    import json

    html = '''
    <div style="
        border: 2px solid #002b5c;
        border-radius: 8px;
        padding: 14px;
        background-color: #003366;
        color: #ffffff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        max-width: 720px;
        overflow-x: auto;
        font-family: Arial, Helvetica, sans-serif;
        font-weight: 600;
        font-size: 8pt;
        white-space: nowrap;
    ">
        <table style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr style="background-color:#001f3f;">
                    <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#ffffff;">Street Name</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#ffffff;">Total</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#ffffff;">Range</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#ffffff;">Unit</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#ffffff;">VI</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#ffffff;">Votes</th>
                    <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#ffcc00;">Gaps</th>
                </tr>
            </thead>
            <tbody>
    '''

    # Loop over streets
    for i, (street_name, data) in enumerate(street_stats.items()):
        unit_list = data["unit_list"]
        unit_counts = data["unit_counts"]
        hos = data["houses"]

        # Range display
        if data["min_num"]:
            num_display = f"({data['min_num']} - {data['max_num']})"
        else:
            num_display = "( - )"

        # Count of gaps only
        house_gaps_display = data.get("house_gaps", 0)

        # Unit dropdown
        unit_dropdown = f'''
        <select onchange="updateMaxVote(this)"
                style="width:100%; font-size:9pt; padding:3px;
                       background:#e6f2ff; color:#001f3f;
                       border:1px solid #007acc;">
            {"".join(f'<option value="{u}" data-max="{unit_counts.get(u, 1)}">{u}</option>' for u in unit_list)}
        </select>
        '''

        # VI select
        vi_select = '<select style="font-size:9pt; padding:3px; background:#e6f2ff; color:#001f3f; border:1px solid #007acc;">' + \
                    ''.join(f'<option value="{key}">{value}</option>' for key, value in VID.items()) + '</select>'

        # Vote button
        first_unit = unit_list[0] if unit_list else None
        max_votes = unit_counts.get(first_unit, 1) if first_unit else 1
        vote_button = f'''
        <button onclick="incrementVoteCount(this)"
                data-count="0"
                data-max="{max_votes}"
                style="
                    font-size:9pt;
                    padding:4px 8px;
                    background:#00aaff;
                    color:#ffffff;
                    border:none;
                    border-radius:4px;
                    font-weight:bold;
                    cursor:pointer;">
            0/{max_votes}
        </button>
        '''

        # Row class for alternating colors
        row_class = "street-row-even" if i % 2 == 0 else "street-row-odd"

        html += f'''
        <tr class="{row_class}">
            <td style="padding:8px;">{street_name}</td>
            <td style="padding:8px;"><i>{hos}</i></td>
            <td style="padding:8px;">{num_display}</td>
            <td style="padding:8px;">{unit_dropdown}</td>
            <td style="padding:8px;">{vi_select}</td>
            <td style="padding:8px;">{vote_button}</td>
            <td style="padding:8px; color:#ffcc00;">{house_gaps_display}</td>
        </tr>
        '''

    html += '''
            </tbody>
        </table>
    </div>
    '''

    return html


#---------------------
# Helper for node electors
# ------------------------



def preprocess_streets(df):

    import pandas as pd
    from collections import Counter

    df = df.copy()

    prefix = df["AddressPrefix"].astype(str).str.strip()
    number = df["AddressNumber"].astype(str).str.strip()

    df["unit"] = prefix.where(
        prefix.notna() & (prefix.str.lower() != "nan") & (prefix != ""),
        number
    )

    df["unit"] = df["unit"].replace(["", "nan", "None"], pd.NA)

    exploded = (
        df.dropna(subset=["unit"])
        .assign(unit=df["unit"].str.split(","))
        .explode("unit")
    )

    exploded["unit"] = exploded["unit"].str.strip()

    exploded = exploded[
        exploded["unit"].notna() &
        (exploded["unit"].str.lower() != "nan")
    ]

    exploded["num"] = exploded["unit"].str.extract(r'(\d+)')[0].astype(float)

    street_data = {}

    for street, group in exploded.groupby("StreetName"):

        units = group["unit"].unique()
        nums = group["num"].dropna().astype(int)

        numbers = nums.unique()
        numbers.sort()

        actual_houses = len(units)

        if len(numbers):

            min_num = numbers.min()
            max_num = numbers.max()

            # detect odd/even numbering
            if len(numbers) > 1 and all(n % 2 == numbers[0] % 2 for n in numbers):

                estimated_houses = ((max_num - min_num) // 2) + 1

                expected_numbers = set(range(min_num, max_num + 1, 2))

            else:

                estimated_houses = (max_num - min_num) + 1

                expected_numbers = set(range(min_num, max_num + 1))

            missing_numbers = sorted(expected_numbers - set(numbers))

        else:

            min_num = None
            max_num = None
            estimated_houses = actual_houses
            missing_numbers = []

        missing_properties = max(0, estimated_houses - actual_houses)

        street_data[street] = {
            "houses": actual_houses,
            "estimated_houses": estimated_houses,
            "house_gaps": missing_properties,       # renamed here
            "missing_numbers": missing_numbers,
            "unit_list": sorted(units),
            "unit_counts": dict(Counter(group["unit"])),
            "min_num": min_num,
            "max_num": max_num
            }

    total_houses = exploded["unit"].nunique()

    return street_data, total_houses



def build_nodemap_list_html(herenode):
    """
    Build HTML tooltip listing all children of a node.
    Returns a string of safe HTML.
    """

    if not herenode or not getattr(herenode, "children", None):
        return "<em>No children</em>"

    items_html = []

    for child in herenode.children:

        label = getattr(child, "name", None) or getattr(child, "value", "") or "Unnamed"
        label = html.escape(str(label))

        missing = getattr(child, "house_gaps", None)

        if missing and missing > 0:
            label += f" <span style='color:#ffcc66'>(gap: {missing})</span>"

        items_html.append(f"<li>{label}</li>")

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

    def _render_single_node(self, c_election, node, static, counters):

        CElection = CurrentElection.load(c_election)
        rlevels = CElection.resolved_levels
        intention_type = rlevels[node.level+1]

        if intention_type == "marker":
            self.add_genmarkers(CElection, rlevels, node, "marker", static)

        elif intention_type in ("street", "walkleg"):
            self.add_nodemarks(c_election, rlevels, node, static)

        elif intention_type in ("polling_district", "walk"):
            self.add_voronoi(
                c_election, rlevels, node, static
            )
        else:
            self.add_nodemaps(c_election, rlevels, node, static, counters)


    def create_layer(self, c_election, nodelist, static=False):
        from flask import session
        from elections import branchcolours
        from state import Treepolys, Fullpolys

        from collections import defaultdict


        print(f"Layer {self.name} memory id:", id(self))
        counters = defaultdict(int)
        i = 0
        for n in nodelist:
            n.defcol = branchcolours[i]
            self._render_single_node(c_election, n, static, counters)
            i = i+1

        return len(self._children)



    def reset(self):
        # This clears internal children before rendering
        self._children.clear()
        self.areashtml = {}
        print("____reset the layer",len(self._children), self)
        return self


    def add_voronoi(self, c_election, rlevels, node, static=False):

        from elections import CurrentElection
        from flask import url_for
        from geovoronoi import voronoi_regions_from_coords
        from state import Treepolys, Fullpolys
        import geopandas as gpd
        import pandas as pd
        import folium
        from elector import electors  # your ElectorManager instance


        CElection = CurrentElection.load(c_election)
        pfile = Treepolys[rlevels[node.level]]
        Territory_boundary = pfile[pfile['FID'] == int(node.fid)]
        node.geometry = Territory_boundary.union_all()

        children = node.childrenoftype(rlevels[node.level+1])
        if not children:
            print(f"⚠️ Node has no children of type {rlevels[node.level+1]}")
            return

        # -------------------------------------------------
        # Build points from children
        # -------------------------------------------------

        points = []
        point_to_child = {}

        for child in children:
            if child.latlongroid and len(child.latlongroid) == 2:
                child.centre = Point(child.latlongroid[1], child.latlongroid[0])  # lon, lat
            else:
                child.centre = None

            if not child.centre:
                continue

            pt = (round(float(child.centre.x), 5), round(float(child.centre.y), 5))
            point_to_child[pt] = child
            points.append(pt)

        if not points:
            print("⚠️ No valid child centres")
            return

        coords = np.array(points)  # directly usable for geovoronoi


        # -------------------------------------------------
        # Parent boundary
        # -------------------------------------------------

        parent_boundary = node.geometry
        if parent_boundary is None:
            print("⚠️ Parent boundary missing")
            return

        # -------------------------------------------------
        # Generate Voronoi
        # -------------------------------------------------

        region_polys, region_pts = voronoi_regions_from_coords(coords, parent_boundary)

        print(f"DEBUG VORONOI: Generated {len(region_polys)} Voronoi polygons")

        # -------------------------------------------------
        # Load electors
        # -------------------------------------------------

        nodeelectors = electors.electors_for_node(node)

        if nodeelectors is None or nodeelectors.empty:
            print("DEBUG ELECTORS: ⚠️ No electors for node")
            return

        print(f"DEBUG ELECTORS: Loaded {len(nodeelectors)} electors for node {node.value}")

        # -------------------------------------------------
        # Counters
        # -------------------------------------------------

        total_regions = 0
        missing_child = 0
        no_electors = 0
        polygons_added = 0

        # -------------------------------------------------
        # Loop regions
        # -------------------------------------------------

        for region_id, poly in region_polys.items():

            total_regions += 1
            print(f"DEBUG REGION: Processing region {region_id}")

            idx = region_pts[region_id]

            if isinstance(idx, (list, np.ndarray)):
                idx = idx[0]

            print(f"DEBUG REGION: Coord index {idx}")

            coord = coords[idx]

            coord_key = (round(float(coord[0]), 6), round(float(coord[1]), 6))
            print(f"DEBUG REGION: Rounded coord key {coord_key}")

            child = point_to_child.get(coord_key)

            if child is None:
                print(f"DEBUG MATCH: ⚠️ No child found for coordinate {coord_key}")
                missing_child += 1
                continue

            print(f"DEBUG MATCH: Matched child {child.value}")

            child.voronoi_region = poly

            # -------------------------
            # Electors
            # -------------------------

            shapecolumn = {
                "polling_district": "PD",
                "walk": "WalkName",
                "ward": "Area",
                "division": "Area",
                "constituency": "Area"
            }

            if child.type not in shapecolumn:
                print(f"⚠️ Unknown node type: {node.type}")
                return pd.DataFrame()  # empty

            col = shapecolumn[child.type]

            region_electors = nodeelectors[nodeelectors[col] == child.value]

            print(f"DEBUG ELECTORS: {child.value} has {len(region_electors)} electors")

            if region_electors.empty:
                print(f"DEBUG ELECTORS: ⚠️ Skipping {child.value} (no electors)")
                no_electors += 1
                continue

            # -------------------------
            # Navigation links
            # -------------------------

            nav_html = ""

            upmessage = (
                "moveUp('/upbut/{0}','{1}','{2}')"
                .format(
                    child.parent.dir + "/" + child.parent.file(rlevels),
                    child.parent.value,
                    child.parent.type
                )
            )

            up_link = f'<a href="#" onclick="{upmessage}">⬆ Up</a>'

            if not static:

                showmessageST = (
                    "showMore('/PDdownST/{0}','{1}','street')"
                    .format(child.dir + "/" + child.file(rlevels), child.value)
                )

                street_link = f'<a href="#" onclick="{showmessageST}">Street view</a>'

                nav_html = f"""
                <div style="margin-bottom:8px; padding-left:22px; line-height:1.6;">
                {street_link}<br>
                {up_link}
                </div>
                """

            else:

                nav_html = f"""
                <div style="margin-bottom:8px; padding-left:22px; line-height:1.6;">
                {up_link}
                </div>
                """

            # -------------------------
            # Preprocess street data
            # -------------------------

            street_stats, house_count = preprocess_streets(region_electors)
            missing_total = sum(d["house_gaps"] for d in street_stats.values())


            # -------------------------
            # Build popup HTML
            # -------------------------

            print(f"DEBUG POPUP: Building popup for {child.value}")

            street_html = nav_html + "<hr>" + build_street_list_html(region_electors, street_stats)

            popup = folium.Popup(street_html, max_width=900, show=False)
            # -------------------------
            # Style
            # -------------------------

            style = {
                "fillColor": getattr(child, "defcol", "#3388ff"),
                "color": "white",
                "weight": 3,
                "fillOpacity": 0.5
            }

            print(f"DEBUG STYLE: Style for {child.value} = {style}")

            # -------------------------
            # Tooltip content
            # -------------------------


            elector_density = round(len(region_electors) / house_count, 2) if house_count else 0

            tooltip_html = f"""
            <b>{child.value}</b><br>
            Electors: {len(region_electors)}<br>
            Houses: {house_count}<br>
            Elector/house: {elector_density}<br>
            House gaps: {missing_total}
            """



            print(f"DEBUG TOOLTIP: {child.value} houses={house_count} density={elector_density}")

            # -------------------------
            # Polygon
            # -------------------------

            try:

                print(f"DEBUG POLYGON: Adding polygon for {child.value}")

                gj = folium.GeoJson(
                    poly.__geo_interface__,
                    style_function=lambda x, s=style: s
                )


                folium.Tooltip(
                    tooltip_html,
                    sticky=True,
                    interactive=False
                    ).add_to(gj)


                gj.add_child(popup)

                print(f"DEBUG LAYER: Children before add {len(self._children)}")

                gj.add_to(self)
                layer_name = gj.get_name()

                longpress_js = f"""
                var layer = {layer_name};
                var pressTimer;
                var longPressTriggered = false;

                // Remove Leaflet's automatic popup binding
                var popup = layer.getPopup();
                layer.unbindPopup();
                layer.bindPopup(popup);

                // CLICK → tooltip
                layer.on('click', function(e) {{
                    if (!longPressTriggered) {{
                        layer.openTooltip();
                    }}
                }});

                // LONG PRESS → popup
                layer.on('touchstart mousedown', function(e) {{
                    longPressTriggered = false;

                    pressTimer = setTimeout(function() {{
                        longPressTriggered = true;
                        layer.openPopup();
                    }}, 600);
                }});

                layer.on('touchend mouseup mouseleave touchcancel', function(e) {{
                    clearTimeout(pressTimer);
                }});
                """

                self.add_child(folium.Element(f"<script>{longpress_js}</script>"))


                print(f"DEBUG LAYER: Children after add {len(self._children)}")

                polygons_added += 1



            except Exception as e:

                print(f"DEBUG ERROR: Failed adding polygon for {child.value} -> {e}")
                continue

            # -------------------------
            # Name marker at centroid
            # -------------------------

            try:

                centre = poly.point_on_surface()

                tag = child.value
                fcol = getattr(child, "defcol", "#cccccc")

                mapfile = url_for("transfer", path=f"{child.dir}/{child.file(rlevels)}")

                print(f"DEBUG MARKER: Adding label marker for {tag}")

                folium.Marker(
                    location=[centre.y, centre.x],
                    icon=folium.DivIcon(
                        class_name="",
                        html=f"""
                            <div class="voronoi-label">
                            <span class="voronoi-tag" style="background:{fcol}">
                            {tag}
                            </span>
                            </div>
                            """
                    )
                ).add_to(self)

            except Exception as e:

                print(f"DEBUG ERROR: Failed adding marker for {child.value} -> {e}")

            print(f"DEBUG SUCCESS: Added Voronoi for {child.value}")

        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        print("DEBUG SUMMARY:")
        print(f"Total regions processed: {total_regions}")
        print(f"Missing child matches: {missing_child}")
        print(f"Regions with no electors: {no_electors}")
        print(f"Polygons added to layer: {polygons_added}")
        print(f"Final layer child count: {len(self._children)}")




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
        limbX = create_enclosing_gdf(gdf)
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
                            font-weight: 200;
                            text-align: center;
                            -webkit-text-stroke: 1px white;
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
                            font-weight: 200;
                            text-align: center;
                            -webkit-text-stroke: 1px white;
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

    def add_nodemaps (self,c_election,rlevels, herenode,static, counters):
        from state import Treepolys, Fullpolys, Candidates, LastResults
        from flask import session, flash
        global levelcolours
        global Con_Results_data
        global OPTIONS

        type = rlevels[herenode.level+1]

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
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels), c.value,type)
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
                        downmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels), c.value,type)
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
                        downwardmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels), c.value,"ward")
                        downdivmessage = "moveDown(&#39;/downbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(c.dir+"/"+c.file(rlevels), c.value,"division")
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

                        Sheetbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downbut/{0}", "{1}", "NOTUSED");' class='btn btn-norm'>
                                Sheets
                            </button>
                        """.format(c.dir+"/"+c.file(rlevels)+" polling_district", c.value)


                        Appbtn = """
                            <button type='button' class='guil-button' onclick='moveDown("/downMWbut/{0}", "{1}", "walk");' class='btn btn-norm'>
                                App
                            </button>
                        """.format(c.dir+"/"+c.file(rlevels)+" walk", c.value)


                        uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size:{2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)

                        if not static:
                            limbX['UPDOWN'] = "<br>"+c.value+"<br>"+ uptag1 +"<br>"+Sheetbtn+" "+Appbtn
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
                    htmlhalostatic =f'''
                    <a href="" data-name="{tag}">
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



                    if not static:
                        self.add_child(folium.Marker(
                             location=here,
                             icon = folium.DivIcon(
                                    html=htmlhalo,
                                       )
                                       )
                                       )
                    else:
                        self.add_child(folium.Marker(
                             location=here,
                             icon = folium.DivIcon(
                                    html=htmlhalostatic,
                                       )
                                       )
                                       )


        return self._children

    def add_nodemarks (self,c_election,rlevels,herenode,static):
        global levelcolours

        type = rlevels[herenode.level + 1]

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


        children = herenode.childrenoftype(type)

        for i, c in enumerate(children):

            base_lat = float(f"{c.latlongroid[0]:.6f}")
            base_lon = float(f"{c.latlongroid[1]:.6f}")

            lat, lon = spread_coordinates_vertical(
                base_lat,
                base_lon,
                i,
                len(children),
                spread_lat=0.0006,   # more vertical spacing
                spread_lon=0.00001    # minimal horizontal spacing
            )
            here = [lat, lon]

            print('_______MAP Markers')

            numtag = str(c.tagno)+" "+str(c.value)
            num = str(c.tagno)
            tag = str(c.value)
            fill = herenode.col
            pathref = c.mapfile(rlevels)
            mapfile = '/transfer/'+pathref

            print("______Display childrenx:",c.value, c.level,type,c.latlongroid )

            tcol = get_text_color(to_hex(c.col))
            bcol = adjust_boundary_color(to_hex(c.col),0.7)
            fcol = invert_black_white(tcol)

            node_col = to_hex(herenode.defcol)
            tcol_node = readable_text_color(node_col)
            print(f"_____Colour from {herenode.value} col:{herenode.defcol}")
            fcol_node = tcol_node
            poly_col_node = node_col


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

                </span>

              </div>
            </a>
            '''
            htmlhalostatic =f'''
            <a href="" data-name="{tag}">
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

                </span>

              </div>
            </a>
            '''

            if not static:
                self.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(
                            html=htmlhalo,
                           )
                           )
                           )
            else:
                self.add_child(folium.Marker(
                     location=here,
                     icon = folium.DivIcon(
                            html=htmlhalostatic,
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
