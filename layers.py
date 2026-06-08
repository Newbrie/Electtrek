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
import elections
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

def create_boundary_geom(elector_df, buffer_meters=50):
    """
    Create a boundary geometry from a set of elector points.

    Parameters:
        elector_df (pd.DataFrame): Must have 'Lat' and 'Long' columns.
        buffer_meters (float): Optional buffer in meters around the convex hull.

    Returns:
        shapely Polygon: EPSG:4326 polygon covering all points.
    """
    if elector_df.empty:
        return None

    # Ensure Lat/Long columns exist
    if 'Lat' not in elector_df.columns or 'Long' not in elector_df.columns:
        raise ValueError("elector_df must have 'Lat' and 'Long' columns")

    # Create points
    points = [Point(lon, lat) for lon, lat in zip(elector_df['Long'], elector_df['Lat'])]
    multipoint = MultiPoint(points)

    # GeoSeries in WGS84
    gdf = gpd.GeoSeries([multipoint], crs="EPSG:4326")

    # Project to metric CRS for accurate buffer
    gdf_proj = gdf.to_crs("EPSG:3857")

    # Convex hull + buffer
    hull = gdf_proj.iloc[0].convex_hull
    hull_buffered = hull.buffer(buffer_meters)

    # Convert back to WGS84
    hull_wgs84 = gpd.GeoSeries([hull_buffered], crs="EPSG:3857").to_crs("EPSG:4326").iloc[0]

    return hull_wgs84


def build_street_list_html(reg_id, streets_df, street_stats, task_tags, uiScope="walk"):
    import json
    from state import VID

    # 1. Prepare dynamic tag headers (Styled with matching color syntax)
    sorted_task_codes = sorted(task_tags.keys())
    tag_headers_html = "".join([f'<th style="text-align:center; padding:8px; border-bottom:2px solid #00aaff; font-size:7pt; color:#00aaff;">{code}</th>' for code in sorted_task_codes])

    # Ensure ui_scope_json is strictly formatted
    ui_scope_json = json.dumps(uiScope)

    # ------------------------------------------------------------------
    # 2. COMPACT BOOTSTRAP TRIGGER (Control Panel Block Removed)
    # ------------------------------------------------------------------
    persistence_js = f'''
        <style>
            .tag-toggle {{ cursor: pointer; padding: 2px 6px; border-radius: 3px; font-weight: bold; font-size: 8pt; display: inline-block; min-width: 14px; text-align: center; border: 1px solid #555; }}
            .tag-active {{ background: #28a745; color: white; border-color: #1e7e34; }}
            .tag-inactive {{ background: #444; color: #999; border-color: #333; }}
        </style>

        <script>
        (function() {{
            var scope = {ui_scope_json};

            setTimeout(function() {{
                var parentWindow = window.parent || window;

                // Run centralized row initialization engine
                if (typeof parentWindow.initializeStreetRowState === 'function') {{
                    document.querySelectorAll('.unit-selector').forEach(function(sel) {{
                        parentWindow.initializeStreetRowState(sel, scope);
                    }});
                }}

                // Run map.js pop-up trace ledger replay loops
                if (typeof parentWindow.replayLocalBakedDataForPopup === 'function') {{
                    try {{
                        parentWindow.replayLocalBakedDataForPopup(document);
                    }} catch (err) {{
                        console.error("❌ Error running local replay engine modules:", err);
                    }}
                }}
            }}, 220);
        }})();
        <\/script>
    '''

    # 3. THE UI: Table Layout (Unified header color attributes)
    html = persistence_js + f'''
        <div style="border: 2px solid #002b5c; border-radius: 8px; padding: 14px; background-color: #003366; color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.25); max-width: 850px; overflow-x: auto; font-family: Arial, sans-serif; font-weight: 600; font-size: 8pt; white-space: nowrap;">
            <table style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background-color:#001f3f;">
                        <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#00aaff;">Street Name</th>
                        <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#00aaff;">Total</th>
                        <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#00aaff;">Range</th>
                        <th style="text-align:left; padding:8px; width:80px; border-bottom:2px solid #00aaff; color:#00aaff;">Unit</th>
                        {tag_headers_html}
                        <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#00aaff;">VI</th>
                        <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#00aaff;">Votes</th>
                        <th style="text-align:left; padding:8px; border-bottom:2px solid #00aaff; color:#00aaff;">Gaps</th>
                    </tr>
                </thead>
                <tbody>
    '''

    # 4. Build Rows
    for i, (street_name, data) in enumerate(street_stats.items()):
        try:
            pd_code = streets_df[streets_df['StreetName'] == street_name]['PD'].iloc[0]
        except (KeyError, IndexError):
            pd_code = "UNKNOWN"

        unit_list = data.get("unit_list", [])
        unit_counts = data.get("unit_counts", {})
        hos = data.get("houses", 0)
        num_display = f"({data['min_num']} - {data['max_num']})" if data.get("min_num") is not None else "( - )"
        house_gaps_display = data.get("house_gaps", 0)

        tags = data.get("tags", {})

        tag_cells = ""
        for code in sorted_task_codes:
            is_active = str(tags.get(code, 'n')).lower() == 'y'
            status_class = "tag-active" if is_active else "tag-inactive"
            display_char = "y" if is_active else "n"

            tag_cells += f'''
                <td style="text-align:center; padding:4px;">
                    <span class="tag-toggle {status_class}"
                          data-code="{code}"
                          data-value="{display_char}"
                          role="button"
                          tabindex="0"
                          onclick="parent.handleTagClick(this, '{uiScope}');
                                   (window.plotTaskProgress || parent.plotTaskProgress || function(){{}})('{reg_id}', '{code}', '{uiScope}');">
                        {display_char}
                    </span>
                </td>'''

        # Unit dropdown
        unit_dropdown = f'''
        <select class="unit-selector"
                onchange="parent.handleUnitChangeVIUpdate(this); parent.updateMaxVote(this); parent.loadHouseData(this); parent.updateTagToggles(this); parent.refreshRowVoteBadge(this.closest('.canvass-row'));"
                style="width:100%; font-size:9pt; padding:3px; background:#e6f2ff; color:#001f3f; border:1px solid #007acc;">
            {"".join(f'<option value="{u}" data-max="{unit_counts.get(u, 1)}">{u}</option>' for u in unit_list)}
        </select>
        '''

        unit_active_votes = data.get("unit_active_votes", {})
        first_unit = unit_list[0] if unit_list else None
        max_votes = unit_counts.get(first_unit, 1) if first_unit else 1

        default_vi_code = ""
        first_unit_votes = unit_active_votes.get(first_unit, {}) if first_unit else {}

        if first_unit_votes and isinstance(first_unit_votes, dict):
            valid_votes = {k: int(v) for k, v in first_unit_votes.items() if v is not None}
            if valid_votes:
                default_vi_code = max(valid_votes, key=valid_votes.get)
                default_vi_code = str(default_vi_code).upper()

        if not default_vi_code and VID:
            default_vi_code = str(next(iter(VID.keys()))).upper()

        vi_options = ""
        for key, value in VID.items():
            is_selected = "selected" if str(key).upper() == default_vi_code else ""
            vi_options += f'<option value="{key}" {is_selected}>{value}</option>'

        vi_select = f'''
        <select class="vi-selector"
                style="font-size:9pt; padding:3px; background:#e6f2ff; color:#001f3f; border:1px solid #007acc;"
                onchange="parent.updateVI(this); parent.refreshRowVoteBadge(this.closest('.canvass-row'));">
            {vi_options}
        </select>
        '''

        db_vote_value = first_unit_votes.get(default_vi_code) if first_unit_votes else None

        if db_vote_value is not None and str(db_vote_value).strip() != "":
            initial_votes = int(db_vote_value)
            initial_count_attr = str(initial_votes)
            visual_button_text = f"{initial_votes}/{max_votes}"
        else:
            initial_votes = 0
            initial_count_attr = ""
            visual_button_text = f"0/{max_votes}"

        vote_button = f'''
        <button class="vote-btn" onclick="parent.incrementVoteCount(this)"
                data-count="{initial_votes}"
                data-initial-count="{initial_count_attr}"
                data-max="{max_votes}"
                style="font-size:9pt; padding:4px 8px; background:#00aaff; color:#ffffff; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">
            {visual_button_text}
        </button>
        '''

        json_active_votes_db = json.dumps(unit_active_votes).replace('"', '&quot;')
        row_class = "street-row-even" if i % 2 == 0 else "street-row-odd"

        html += f'''
        <tr class="{row_class} canvass-row"
            data-scope="{uiScope}"
            data-region="{reg_id}"
            data-street="{street_name}"
            data-district="{pd_code}"
            data-initial-count="{initial_count_attr}"
            data-active-votes-db="{json_active_votes_db}">
            <td style="padding:8px;">
                <b data-name="{street_name}">{street_name}</b>
                <small style="color:#888;">({pd_code})</small>
            </td>
            <td style="padding:8px; font-size:7pt; text-align:center;"><i>{hos}</i></td>
            <td style="padding:8px; font-size:7pt; text-align:center;">{num_display}</td>
            <td style="padding:8px; width:60px;">{unit_dropdown}</td>
            {tag_cells}
            <td style="padding:8px;">{vi_select}</td>
            <td style="padding:8px;">{vote_button}</td>
            <td style="padding:8px; text-align:center;">{house_gaps_display}</td>
        </tr>
        '''

    html += "</tbody></table></div>"
    return html

def preprocess_streets(df, task_tags=None):
    import pandas as pd
    from collections import Counter

    df = df.copy()
    task_tags = task_tags or {}
    sorted_task_codes = sorted(task_tags.keys())

    # 1. CLEANING
    for col in ["AddressPrefix", "AddressNumber", "StreetName"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(["nan", "None", ""], pd.NA)

    # 2. UNIQUE IDENTIFIER
    def combine_unit(row):
        p = str(row["AddressPrefix"]).strip() if pd.notna(row["AddressPrefix"]) else ""
        n = str(row["AddressNumber"]).strip() if pd.notna(row["AddressNumber"]) else ""
        if p and n:
            return f"{p} {n}"
        return p or n or "Unknown"

    df["unit"] = df.apply(combine_unit, axis=1)

    # 3. EXPLODE (comma-separated units)
    exploded = df.assign(unit=df["unit"].str.split(",")).explode("unit")
    exploded["unit"] = exploded["unit"].str.strip()
    exploded = exploded[exploded["unit"].notna() & (exploded["unit"] != "Unknown")]

    # 4. NUMERIC EXTRACTION
    exploded["num"] = exploded["unit"].str.extract(r'(\d+)')[0].astype(float)

    street_data = {}

    # 5. PER-STREET PROCESSING
    for street, group in exploded.groupby("StreetName"):
        group = group.copy()

        # --- Units + counts (single pass) ---
        unit_counts = Counter(group["unit"])
        units = sorted(unit_counts.keys())
        actual_houses = len(units)

        # --- HOUSEHOLD ACTIVE VI VOTES COUNT ---
# --- 🌟 UPDATED: HOUSEHOLD ACTIVE VOTES BY SPECIFIC VI CODE ---
        unit_active_votes = {}
        for unit, unit_group in group.groupby("unit"):
            # Initialize a dictionary for this specific house number
            unit_active_votes[unit] = {}

            if 'VI' in unit_group.columns:
                # Clean up the VI series to remove empty strings or nan entries
                cleaned_vi = unit_group['VI'].astype(str).str.strip().str.upper()
                cleaned_vi = cleaned_vi.replace(['NAN', 'NONE', ''], pd.NA).dropna()

                # Count occurrences of every specific intention code found at this address
                vi_counts = cleaned_vi.value_counts().to_dict()

                # Save the counts (e.g., {"R": 2, "D": 1}) converted safely to plain integers
                unit_active_votes[unit] = {str(vi): int(count) for vi, count in vi_counts.items()}

            else:
                unit_active_votes[unit] = 0

        # --- FAST TAG PROCESSING ---
        if 'Tags' in group.columns:
            tag_series = (
                group['Tags']
                .dropna()
                .astype(str)
                .str.upper()
                .str.replace(',', ' ')
                .str.split()
                .explode()
                .str.strip()
            )
            tag_set = set(tag_series)
        else:
            tag_set = set()

        street_tags = {
            code: ("y" if str(code).strip().upper() in tag_set else "n")
            for code in sorted_task_codes if str(code).strip()
        }

        # --- NUMBER ANALYSIS (Safe parsing alternative) ---
        valid_nums = group["num"].dropna()
        if not valid_nums.empty:
            nums = valid_nums.astype(int).unique() # Clean conversion safety
            nums.sort()

            min_num, max_num = int(nums.min()), int(nums.max())

            # Detect even/odd pattern
            if len(nums) > 1 and all(n % 2 == nums[0] % 2 for n in nums):
                estimated_houses = ((max_num - min_num) // 2) + 1
                expected_numbers = set(range(min_num, max_num + 1, 2))
            else:
                estimated_houses = (max_num - min_num) + 1
                expected_numbers = set(range(min_num, max_num + 1))

            missing_numbers = sorted(expected_numbers - set(nums))
        else:
            min_num = max_num = None
            estimated_houses = actual_houses
            missing_numbers = []

        # --- BUILD OUTPUT ---
        street_data[street] = {
            "houses": actual_houses,
            "estimated_houses": estimated_houses,
            "house_gaps": max(0, estimated_houses - actual_houses),
            "missing_numbers": missing_numbers,
            "unit_list": units,
            "unit_counts": dict(unit_counts),
            "unit_active_votes": unit_active_votes,
            "min_num": min_num,
            "max_num": max_num,
            "tags": street_tags
        }

    total_houses_count = sum(data["houses"] for data in street_data.values())
    print("END OF PREPROCESSING OF STREET DATA")
    return street_data, total_houses_count

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

def get_children_within(parent_geom, children_gdf, threshold=0.5):
    import geopandas as gpd

    proj_crs = "EPSG:3857"

    # Project parent
    parent_geom_proj = (
        gpd.GeoSeries([parent_geom], crs="EPSG:4326")
        .to_crs(proj_crs)
        .iloc[0]
    )

    # Project children
    children_proj = children_gdf.to_crs(proj_crs)

    selected_idx = []

    for idx, row in children_proj.iterrows():
        name = row.get("name") or row.get("NAME")
        geom = row.geometry

        if geom is None or geom.is_empty:
            print(f"❌ {name}: no geometry")
            continue

        inter_area = geom.intersection(parent_geom_proj).area
        total_area = geom.area if geom.area > 0 else 1e-9

        overlap = inter_area / total_area

        print(f"{name}: overlap={overlap:.3f} {'✅' if overlap >= threshold else '❌'}")

        if overlap >= threshold:
            selected_idx.append(idx)

    return children_gdf.loc[selected_idx].copy()


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


    def _render_single_node(self, rlevels, node, static, counters):
        assert len(rlevels) == 1
        (c_election, elevels), = rlevels.items()

        intention_type = elevels.get(node.level + 1)

        # 🔍 DEBUG TRACKER: See exactly what levels are arriving
        print(f"DEBUG: RENDER Node ID: {getattr(node, 'nid', 'N/A')} | Node Level: {node.level} | Evaluated Key Level: {node.level + 1} | Found Intention: {intention_type}")

        # 🎯 intercept at the elector level
        if intention_type == "elector":
            # self is our ExtendedFeatureGroup context layer instance
            self.add_tag_layer(
                rlevels=rlevels,
                node=node,
                tags=['PL'],
                operator='OR',
                layer_name="Reform Pledges",
                icon_color="blue", icon_name="users", header_color="#2563EB",
                static=static
            )

        # Separate block for geometric structural drawings
        elif intention_type == "marker":
            self.add_genmarkers(rlevels, node, static)
        elif intention_type in ("street", "walkleg"):
            self.add_nodemarks(rlevels, node, static)
        elif intention_type in ("polling_district", "walk"):
            self.add_voronoi(rlevels, node, static)
        else:
            self.add_nodemaps(rlevels, node, static, counters)


    def add_ghosts(self, tag_code, baked_dict, nodes, branchcolours):
        """
        Populates this layer with ghost polygons based on baked data.
        Mirroring the logic of add_voronoi for high-fidelity data overlays.
        """
        import folium
        polygons_added = 0

        for node in nodes:
            region_id = str(node.value)

            # Guard: Only process if we have data for this region
            if region_id not in baked_dict:
                continue

            region_info = baked_dict[region_id]
            completed_weight = 0

            # -------------------------------------------------
            # 1. Calculate Tag Weight (The Logic Engine)
            # -------------------------------------------------
            for street_data in region_info.values():
                if isinstance(street_data, dict):
                    # Check 'y' status for this specific tag_code
                    has_tag = any(u.get('tags', {}).get(tag_code) == 'y'
                                 for u in street_data.values() if isinstance(u, dict))
                    if has_tag:
                        completed_weight += street_data.get('street_weight', 0)

            total_possible = region_info.get('region_total_houses', 1)
            opacity = (0.8 * (completed_weight / total_possible)) if total_possible > 0 else 0

            # -------------------------------------------------
            # 2. Build the Ghost Polygon
            # -------------------------------------------------
            if opacity > 0:
                try:
                    # Determine color from index (e.g., L1, L2)
                    color_idx = int(tag_code[1:]) if tag_code[1:].isdigit() else 0
                    fill_color = branchcolours[color_idx % 12]

                    # Create the GeoJson Feature
                    # Note: We use node.geometry which is already a Shapely object
                    ghost_gj = folium.GeoJson(
                        node.geometry,
                        name=f"ghost_{tag_code}_{region_id}",
                        style_function=lambda x, op=opacity, col=fill_color: {
                            'fillColor': col,
                            'color': 'transparent',
                            'fillOpacity': op,
                            'interactive': False  # Ghosts are non-interactive overlays
                        }
                    )

                    # 🔑 CRITICAL: Inject the ghost_id for your JavaScript findBucket logic
                    ghost_gj.ghost_id = f"ghost_{tag_code}_{region_id}"

                    # Add to self (this ExtendedFeatureGroup)
                    ghost_gj.add_to(self)
                    polygons_added += 1

                except Exception as e:
                    print(f"⚠️ Ghost Error: Failed adding ghost for {tag_code} in {region_id} -> {e}")

        print(f"DEBUG GHOSTS: Added {polygons_added} polygons to tag layer [{tag_code}]")
        return polygons_added

    def create_layer(self, rlevels, nodelist, static=False):
        from flask import session
        from state import Treepolys, Fullpolys, branchcolours

        from collections import defaultdict


        print(f"Layer {self.name} memory id:", id(self))
        counters = defaultdict(int)
        i = 0
        for n in nodelist:
            n.defcol = branchcolours[i%12]
            self._render_single_node(rlevels, n, static, counters)
            i = i+1

        return len(self._children)



    def reset(self):
        # This clears internal children before rendering
        self._children.clear()
        self.areashtml = {}
        print("____reset the layer",len(self._children), self)
        return self


    def add_voronoi(self, rlevels, node, static=False):
        from shapely.geometry import Point
        from shapely.ops import nearest_points
        import numpy as np
        from flask import url_for
        from geovoronoi import voronoi_regions_from_coords
        from state import Treepolys, Fullpolys
        import geopandas as gpd
        import pandas as pd
        import folium
        from elector import electors  # your ElectorManager instance
        from elections import CurrentElection
        zonecolour = {
            "ZONE_0": "#1A1A1B",  # Deep Charcoal (Better than pure black)
            "ZONE_1": "#E63946",  # Vibrant Red
            "ZONE_2": "#2A9D8F",  # Deep Teal (Cleaner than Lime)
            "ZONE_3": "#0077B6",  # Sapphire Blue
            "ZONE_4": "#2D6A4F",  # Hunter Green
            "ZONE_5": "#00B4D8",  # Sky Blue
            "ZONE_6": "#7209B7",  # Deep Royal Purple
            "ZONE_7": "#FB8500",  # Vivid Orange
            "ZONE_8": "#B5179E",  # Deep Pink/Magenta
            "ZONE_9": "#6F4E37",  # Coffee Brown
            "ZONE_10": "#4A4E69"  # Slate Blue-Gray
        }


        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")
        CE = CurrentElection.load(c_election)
        task_tags, outcome_tags, all_tags = CE.get_tags()

        pfile = Treepolys[elevels[node.level]]
        Territory_boundary = pfile[pfile['FID'] == int(node.fid)]
        node.geometry = Territory_boundary.union_all()

        # --- Parent boundary logic ---
        parent_boundary = node.geometry
        if parent_boundary is None:
            print("⚠️ Parent boundary missing")
            return

        # Ensure it's valid
        if not parent_boundary.is_valid:
            parent_boundary = parent_boundary.buffer(0)

        # CREATE A CALCULATION HULL
        # This bridges the islands so geovoronoi treats all 61 points as one set
        calc_hull = parent_boundary.convex_hull

        children = node.childrenoftype(elevels[node.level+1])
        if not children:
            print(f"⚠️ Node has no children of type {elevels[node.level+1]}")
            return

        # -------------------------------------------------
        # Build points from children
        # -------------------------------------------------

        points = []
        point_to_child = {}

        child_elector_map = {}

        for child in children:
            child_elector_map[child] = electors.elector_for_path(rlevels,child.mapfile())
            if child.latlongroid and len(child.latlongroid) == 2:
                child.centre = Point(child.latlongroid[1], child.latlongroid[0])  # lon, lat
            else:
                child.centre = None

            if not child.centre:
                continue

            pt = (round(float(child.centre.x), 6), round(float(child.centre.y), 6))
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
        # Move pts outside inside parent boundary for Voronoi
        # -------------------------------------------------


        # Ensure all points are inside the parent boundary
        fixed_points = []
        point_to_child_fixed = {}
        outside_points = []

        for pt in coords:
            point = Point(pt)

            if not parent_boundary.contains(point):
                nearest = nearest_points(parent_boundary, point)[0]
                new_pt = (round(nearest.x, 6), round(nearest.y, 6))
                outside_points.append(pt)
            else:
                new_pt = (round(pt[0], 6), round(pt[1], 6))

            fixed_points.append(new_pt)

            # 🔑 IMPORTANT: map the FIXED point, not original
            point_to_child_fixed[new_pt] = point_to_child.get(
                (round(pt[0], 6), round(pt[1], 6))
            )
        print(f"DEBUG: N273 in point_to_child? {'Yes' if any(c.value == 'N273' for c in point_to_child.values()) else 'NO'}")
        print(f"DEBUG: Number of unique points: {len(set(fixed_points))} out of {len(fixed_points)}")
        coords = np.array(fixed_points)
        point_to_child = point_to_child_fixed  # overwrite mapping
        # -------------------------------------------------
        # Generate Voronoi
        # -------------------------------------------------
        # Skip if too few points
        if len(coords) < 2:
            print(f"⚠️ Not enough points ({len(coords)}) to generate Voronoi for {node.value}")
            return

        # Clean the geometry to fix self-intersections or slivers
        if not parent_boundary.is_valid:
            print(f"⚠️ Fixing invalid geometry for {self.name} using buffer(0)")
            parent_boundary = parent_boundary.buffer(0)

        # Generate Voronoi using the Hull to prevent the "1 point in geometry" error
        region_polys, region_pts = voronoi_regions_from_coords(coords, calc_hull)

        print(f"DEBUG VORONOI: Generated {len(region_polys)} Voronoi polygons using Convex Hull")

        # -------------------------------------------------
        # Load electors
        # -------------------------------------------------

        nodeelectors = electors.elector_for_path(rlevels,node.mapfile())

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
        total_electorate = 0
        total_houses = 0

        # -------------------------------------------------
        # Loop regions
        # -------------------------------------------------

        for region_id, poly in region_polys.items():
            # ✂️ COOKIE CUTTER STEP
            # Intersect the Voronoi region with the ACTUAL multipolygon boundary
            # ✂️ COOKIE CUTTER STEP
            # This can sometimes create stray points or lines on the edges
            raw_intersection = poly.intersection(parent_boundary)

            if raw_intersection.is_empty:
                continue
            # 🛡️ THE FIX: Ensure we only have Polygons/MultiPolygons
            # This strips out stray Points or Lines that cause the JS crash
            if raw_intersection.geom_type == 'Polygon' or raw_intersection.geom_type == 'MultiPolygon':
                actual_shape_poly = raw_intersection
            elif raw_intersection.geom_type == 'GeometryCollection':
                # Extract ONLY the polygonal parts from the collection
                polys = [g for g in raw_intersection.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]
                if not polys:
                    print(f"DEBUG: Skipping region {region_id} - no valid polygons in collection")
                    continue
                from shapely.ops import unary_union
                actual_shape_poly = unary_union(polys)
            else:
                print(f"DEBUG: Skipping region {region_id} - geom_type was {raw_intersection.geom_type}")
                continue

            # Double-check: if it's still empty or invalid after filtering, skip it
            if actual_shape_poly.is_empty or not actual_shape_poly.is_valid:
                continue

            # 🔑 CRITICAL: Use 'actual_shape_poly' for your GeoJson, NOT 'poly'
            # From here on, replace 'poly' with 'actual_shape_poly' in your Folium code
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

            child.voronoi_region = actual_shape_poly

            # -------------------------
            # Electors
            # -------------------------


            region_electors = child_elector_map.get(child)

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
                    child.parent.dir + "/" + child.parent.file(elevels),
                    child.parent.value,
                    child.parent.type
                )
            )

            up_link = f'<a href="#" onclick="{upmessage}">⬆ Up</a>'

            if not static:

                showmessageST = (
                    "showMore('/PDdownST/{0}','{1}','street')"
                    .format(child.dir + "/" + child.file(elevels), child.value)
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
            # Before calling preprocess_streets
            print(f"DEBUG: Filtered DF size: {len(region_electors)}")
            print(f"DEBUG: Unique tags found in this slice: {region_electors['Tags'].unique()}")
            street_stats, house_count = preprocess_streets(region_electors,task_tags)
            missing_total = sum(d['house_gaps'] for d in street_stats.values())
            child.electorate = len(region_electors)
            child.houses = house_count
            total_electorate += len(region_electors)
            total_houses += house_count
            # --- NEW COLOR LOGIC ---
            # Get the Zone from the first elector in this region
            if not region_electors.empty:
                actual_zone = region_electors.iloc[0].get('Zone', 'MISSING')
                print(f"DEBUG: Child {child.value} has Zone: {actual_zone}") # Check your console for this!
                region_color = zonecolour.get(actual_zone, '#808080')
            else:
                region_color = 'black'
            # -----------------------

            # Build tooltip
            tooltip_html = f"""
            <b>{child.value}</b><br>
            Electors: {len(region_electors)}<br>
            Houses: {house_count}<br>
            Elector/house: {round(len(region_electors)/house_count,2) if house_count else 0}<br>
            House gaps: {missing_total}
            """



            # Build popup
            street_html = nav_html + "<hr>" + build_street_list_html(child.value,region_electors, street_stats, task_tags)

            # Update the style to use the NEW region_color
            style = {
                "fillColor": region_color,  # Driven by elector Zone, not child.defcol
                "color": "white",
                "weight": 1,
                "fillOpacity": 0.6,
            }
            # -------------------------
            # Polygon (with tooltip and nid)
            # -------------------------
    # -------------------------------------------------
            # Polygon (With Tooltip, Properties, and Direct Popup!)
            # -------------------------------------------------
            try:
                print(f"DEBUG POLYGON: Adding polygon for {child.value}")

                # Prepare properties for JS interaction
                feature_properties = {
                    'nid': child.nid,               # 🔑 THE KEY REF: Link to node in JS
                    'region_id': child.value,        # Human readable ID (e.g., PD tag)
                    'type': 'voronoi_poly',
                    'expected_houses': house_count,
                    'level': child.level             # Helpful for filtering in JS
                }

                if getattr(self, 'is_ghost', False):
                    feature_properties['style_type'] = 'grey_ghost'

                geojson_feature = {
                    "type": "Feature",
                    "geometry": actual_shape_poly.__geo_interface__,
                    "properties": feature_properties
                }

                gj = folium.GeoJson(
                    geojson_feature,
                    style_function=lambda x, s=style: s,
                    tooltip=folium.Tooltip(
                        tooltip_html,
                        sticky=False,             # 1️⃣ Stop tracking cursor movements
                        direction="bottom",       # 2️⃣ Force tooltip to anchor BELOW the target entry point
                        offset=(0, 15),           # 3️⃣ A tuple is cleaner for Folium's internal parser
                        style="""
                            background-color: white;
                            color: #333;
                            font-family: sans-serif;
                            border-radius: 4px;
                            padding: 6px;
                            border: 1px solid #ccc;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                        """
                    )
                )

                # 🎯 THE FIX: Attach the street list popup directly to the Polygon Layer shape!
                popup = folium.Popup(street_html, max_width=900, show=False)
                gj.add_child(popup)

                # Add to the ExtendedFeatureGroup (self)
                gj.add_to(self)
                polygons_added += 1

            except Exception as e:
                print(f"DEBUG ERROR: Failed adding polygon for {child.value} -> {e}")

        node.electorate = total_electorate
        node.houses = total_houses
        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        print("DEBUG SUMMARY:")
        print(f"Total regions processed: {total_regions}")
        print(f"Missing child matches: {missing_child}")
        print(f"Regions with no electors: {no_electors}")
        print(f"Polygons added to layer: {polygons_added}")
        print(f"Final layer child count: {len(self._children)}")




    def add_shapenodes (self,rlevels,herenode,stype):
        global allelectors
# add a convex hull for all zonal children nodes , using all street centroids contained in each zone
# zonal nodes are added at same time as walk nodes, zone nodes generated from zone grouped means of electors
# children of zones gnerated by a downZO route similar to downWK
# zone hull data generated from zone mask of areaelectors.
        from elector import electors, shapecolumn
# if there is a selected file , then allelectors will be full of records
        print(f"____adding_shapenodes in election {c_election} layer {self.id} for {herenode.value} of type {stype}:")

        nodeelectors = electors.electors_at_node(herenode.findnodeat_level(3))

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
        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")
        CE = CurrentElection.load(c_election)
        task_tags, outcome_tags, all_tags = CE.get_tags()

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
            showmessageST = "showMore(&#39;/PDdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(elevels) +" street", herenode.value,'street')
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file(elevels), herenode.parent.value,herenode.parent.type)
#            showmessageWK = "showMore(&#39;/PDshowWK/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(elevels), herenode.value,child_type_of('polling_district',estyle))
            downST = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageST,"STREETS",12)
#            downWK = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessageWK,"WALKS",12)
#            upload = "<form action= '/PDshowST/{2}'<input type='file' name='importfile' placeholder={1} style='font-size: {0}pt;color: gray' enctype='multipart/form-data'></input><button type='submit'>STREETS</button><button type='submit' formaction='/PDshowWK/{2}'>WALKS</button></form>".format(12,session.get('importfile'), herenode.dir+"/"+herenode.file(elevels))
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            limbX['UPDOWN'] = uptag1 +"<br>"+ downST
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno, gdf)
        elif type == 'walk':
            showmessage = "showMore(&#39;/WKdownST/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.dir+"/"+herenode.file(elevels)+" walkleg", herenode.value,'walkleg')
            upmessage = "moveUp(&#39;/upbut/{0}&#39;,&#39;{1}&#39;,&#39;{2}&#39;)".format(herenode.parent.dir+"/"+herenode.parent.file(elevels), herenode.parent.value,herenode.parent.type)
            downtag = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(showmessage,"STREETS",12)
            uptag1 = "<button type='button' id='message_button' onclick='{0}' style='font-size: {2}pt;color: gray'>{1}</button>".format(upmessage,"UP",12)
            streetstag = build_street_list_html(herenode.value,datablock, street_stats, task_tags)
            limbX['UPDOWN'] =  "<div style='white-space: normal'>" + uptag1 +"<br>"+ downtag+"<br>"+ streetstag+"<br></div>"
            print("_________new convex hull and tagno:  ",herenode.value, herenode.tagno)


#        herenode.tagno = len(self._children)+1
        numtag = str(herenode.tagno)+" "+str(herenode.value)
        num = str(herenode.tagno)
        tag = str(herenode.value)
        typetag = "streets in "+str(herenode.type)+" "+str(herenode.value)
        here = [float(f"{herenode.latlongroid[0]:.6f}"), float(f"{herenode.latlongroid[1]:.6f}")]
        pathref = herenode.mapfile()
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

    def add_tag_layer(self, rlevels, node, tags, operator, layer_name, icon_color, icon_name, header_color, target_cluster=None, static=False):
        """
        Advanced centralized backend filter engine on the ExtendedFeatureGroup class.
        Filters electors for the explicitly passed node and mounts them to the layer.
        """
        import pandas as pd
        import folium
        import logging
        from folium.plugins import MarkerCluster
        from elector import electors

        logger = logging.getLogger(__name__)

        # 🎯 FIX 1: Safely use the passed node to get the file path
        path = node.mapfile()
        node_electors = electors.elector_for_path(rlevels, path)

        if node_electors is None or node_electors.empty:
            return 0

        if 'Tags' not in node_electors.columns:
            logger.warning(f"Tags column missing for path: {path}")
            return 0

        # ... [Keep your exact same Pandas tag filtering logic here] ...
        if isinstance(tags, str):
            tags = [tags]
        tags = [t.strip() for t in tags if t.strip()]
        if not tags:
            return 0

        operator = operator.strip().upper()
        tags_series = node_electors['Tags'].astype(str)

        if len(tags) == 1 or operator == 'OR':
            combined_pattern = rf"\b({'|'.join(tags)})\b"
            mask = tags_series.str.contains(combined_pattern, na=False, regex=True)
        elif operator == 'AND':
            mask = pd.Series(True, index=node_electors.index)
            for tag in tags:
                mask &= tags_series.str.contains(rf"\b{tag}\b", na=False, regex=True)
        else:
            raise ValueError("Invalid operator selection. Use 'AND' or 'OR'.")

        filtered_electors = node_electors[mask]
        if filtered_electors.empty:
            return 0

        # 🎯 FIX 2: Cluster Management
        # If no cluster was passed down, look for an existing one or create it directly on self
        if target_cluster is None:
            # Try to fetch an existing cluster child from this ExtendedFeatureGroup to prevent duplicate groups
            existing_clusters = [child for child in self._children.values() if isinstance(child, MarkerCluster)]
            if existing_clusters:
                target_cluster = existing_clusters[0]
            else:
                # Initialize a clean cluster inside this ExtendedFeatureGroup container
                target_cluster = MarkerCluster(name=layer_name, control=False).add_to(self)

        markers_added = 0
        for _, elector in filtered_electors.iterrows():
            lat, lon = elector.get('Lat'), elector.get('Long')
            if pd.isna(lat) or pd.isna(lon):
                continue

            # --- Name & Address Construction ---
            fn = str(elector.get('Firstname', '')).replace('_', ' ').strip()
            init = str(elector.get('Initials', '')).replace('_', ' ').strip()
            sn = str(elector.get('Surname', '')).replace('_', ' ').strip()
            full_name = " ".join([p for p in [fn, init, sn] if p]).title()

            def get_val(k): return "" if pd.isna(elector.get(k, "")) else str(elector.get(k, "")).strip()
            pref, num, street, pc = get_val('AddressPrefix'), get_val('AddressNumber'), get_val('StreetName'), get_val('Postcode')
            main_line = " ".join([p for p in [f"{pref}," if pref else "", num, street] if p]).replace(" ,", ",")
            display_address = f"{main_line}, {pc}" if pc else main_line

            popup_html = f"""
                <div style="font-family: Arial, sans-serif; min-width: 200px; font-size: 13px; line-height: 1.4;">
                    <div style="background-color: {header_color}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; margin-bottom: 6px; text-align: center;">
                        {layer_name}
                    </div>
                    <div style="font-weight: bold; font-size: 14px; color: #111;">{full_name}</div>
                    <div style="color: #444; margin-bottom: 6px;">{display_address}</div>
                    <div style="border-top: 1px dotted #ccc; padding-top: 4px; font-size: 11px; color: #777;">
                        <strong>Elector No:</strong> {elector.get('ENOP', 'N/A')}
                    </div>
                </div>
            """

            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color=icon_color, icon=icon_name, prefix='fa'),
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=full_name
            ).add_to(target_cluster)
            markers_added += 1

        return markers_added

    def add_genmarkers(self,rlevels, node, static):
        eventlist = node.build_eventlist_dataframe(rlevels)
        print(f" ___GenMarkers: under {elections.route()} eventlist: {eventlist}")
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

    def add_nodemaps (self,rlevels, herenode,static, counters):
        from state import Treepolys, Fullpolys, Candidates, LastResults
        from flask import session, flash
        global levelcolours
        global Con_Results_data
        global OPTIONS

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")


        type = elevels[herenode.level+1]

        childlist = herenode.childrenoftype(type)
        allchildlist = herenode.children
        nodeshtml = build_nodemap_list_html(herenode)

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
            counters[elevels[herenode.level+1]] = 0

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
                    # Setup clean, consistent styling defaults
                    font_style = "style='font-size: 12pt; color: gray'"

                    # Resolve target paths and values cleanly up front
                    c_path = f"{c.dir}/{c.file(elevels)}"
                    here_path = f"{herenode.dir}/{herenode.file(elevels)}"

                    c_val = c.value
                    here_val = herenode.value

                    # ------------------------------------------------------------------
                    # LEVEL 0: Top Level Hierarchy
                    # ------------------------------------------------------------------
                    if herenode.level == 0:
                        down_js = f"moveDown('/downbut/{c_path}', '{c_val}', '{type}')"
                        up_js = f"moveUp('/upbut/{c_path}', '{c_val}', '{herenode.type}')"

                        uptag = f"<button type='button' id='btn_up_l0' onclick=\"{up_js}\" {font_style}>UP</button>"
                        downtag = f"<button type='button' id='btn_down_l0' onclick=\"{down_js}\" {font_style}>{type}</button>"

                        limbX['UPDOWN'] = f"{uptag}<br>{c_val}<br>{downtag}"
                        mapfile = f"/transfer/{c.mapfile()}"

                    # ------------------------------------------------------------------
                    # LEVEL 1: Regional / County Level
                    # ------------------------------------------------------------------
                    elif herenode.level == 1:
                        ward_js = f"moveDown('/wardreport/{c_path}', '{c_val}', '{type}')"
                        div_js = f"moveDown('/divreport/{c_path}', '{c_val}', '{type}')"
                        down_js = f"moveDown('/downbut/{c_path}', '{c_val}', '{type}')"
                        up_js = f"moveUp('/upbut/{here_path}', '{here_val}', '{herenode.type}')"

                        ward_tag = f"<button type='button' id='btn_ward_l1' onclick=\"{ward_js}\" {font_style}>WARD Report</button>"
                        div_tag = f"<button type='button' id='btn_div_l1' onclick=\"{div_js}\" {font_style}>DIV Report</button>"
                        down_tag = f"<button type='button' id='btn_down_l1' onclick=\"{down_js}\" {font_style}>CONSTITUENCIES</button>"
                        up_tag = f"<button type='button' id='btn_up_l1' onclick=\"{up_js}\" {font_style}>UP</button>"

                        limbX['UPDOWN'] = f"<br>{c_val}<br>{up_tag}<br>{ward_tag}{div_tag}<br>{down_tag}"
                        mapfile = f"/transfer/{c.mapfile()}"

                    # ------------------------------------------------------------------
                    # LEVEL 2: Constituency Level
                    # ------------------------------------------------------------------
                    elif herenode.level == 2:
                        ward_down_js = f"moveDown('/downbut/{c_path}', '{c_val}', 'ward')"
                        div_down_js = f"moveDown('/downbut/{c_path}', '{c_val}', 'division')"
                        up_js = f"moveUp('/upbut/{here_path}', '{here_val}', '{herenode.type}')"

                        ward_tag = f"<button type='button' id='btn_ward_l2' onclick=\"{ward_down_js}\" {font_style}>WARDS</button>"
                        div_tag = f"<button type='button' id='btn_div_l2' onclick=\"{div_down_js}\" {font_style}>DIVS</button>"
                        up_tag = f"<button type='button' id='btn_up_l2' onclick=\"{up_js}\" {font_style}>UP</button>"

                        limbX['UPDOWN'] = f"<br>{c_val}<br>{up_tag}<br>{ward_tag} {div_tag}"
                        mapfile = f"/transfer/{c.mapfile()}"

                    # ------------------------------------------------------------------
                    # LEVEL 3: Ward / Division Leaf Node Layout
                    # ------------------------------------------------------------------
                    elif herenode.level == 3:
                        up_js = f"moveUp('/upbut/{here_path}', '{here_val}', '{herenode.type}')"
                        up_tag = f"<button type='button' id='btn_up_l3' onclick=\"{up_js}\" {font_style}>UP</button>"

                        # 🪐 THE FIX: Passing scope strings as clean parameters, keeping the URL string intact!
                        sheet_btn = f"""
                            <button type='button' class='guil-button btn btn-norm' onclick="moveDown('/downbut/{c_path}', '{c_val}', 'polling_district');">
                                Sheets
                            </button>
                        """

                        app_btn = f"""
                            <button type='button' class='guil-button btn btn-norm' onclick="moveDown('/downMWbut/{c_path}', '{c_val}', 'walk');">
                                App
                            </button>
                        """

                        if not static:
                            limbX['UPDOWN'] = f"<br>{c_val}<br>{up_tag}<br>{sheet_btn} {app_btn}"
                        else:
                            limbX['UPDOWN'] = f"<br>{c_val}<br>"

                        mapfile = f"/transfer/{c.mapfile()}"

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

                    pathref = c.mapfile()
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

    def add_nodemarks (self,rlevels,herenode,static):
        global levelcolours

        # Guard: Ensure we have exactly one election to unpack
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()
        print(f"DEBUG: Unpacked election: {c_election}")

        type = elevels[herenode.level + 1]

        childlist = herenode.childrenoftype(type)
        nodeshtml = build_nodemap_list_html(herenode)

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
            pathref = c.mapfile()
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
    "elector": dict(name="elector", mytag="elector", overlay=True, control=True, show=False),
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
    Each layer has Python-only metadata: .key, .mytag, and .layer_type.
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

        # --- NEW: define the context / uiScope ---
        layer.layer_type = spec.get("type", "walk")  # walk / pd / ward

        layers[key] = layer

    return layers




def make_counters():
    return {key: 0 for key in FEATURE_LAYER_SPECS}
