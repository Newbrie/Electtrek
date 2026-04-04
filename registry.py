Treepolys: dict[str, gpd.GeoDataFrame] = {}
Fullpolys: dict[str, gpd.GeoDataFrame] = {}
Geo_index = {}
print(f"DEBUG: Config Memory Address of Geo_index here: {id(Geo_index)}")
# Then check the ID inside the persist function


def clear_treepolys(from_level=None):

    if from_level is None:
        for k in Treepolys:
            Treepolys[k] = gpd.GeoDataFrame()
            Fullpolys[k] = gpd.GeoDataFrame()
    else:
        for layer in LAYERS[from_level:]:
            Treepolys[layer["key"]] = gpd.GeoDataFrame()
            Fullpolys[layer["key"]] = gpd.GeoDataFrame()


def select_parent_geoms(*, Treepolys, parent_key, sourcepath=None, here=None):
    parents = Treepolys.get(parent_key, gpd.GeoDataFrame())
    print(f"select_parent: raw Treepolys[{parent_key}] = {parents!r}")

    if parents.empty:
        return gpd.GeoDataFrame()

    # 1️⃣ Point-in-polygon
    if here is not None:
        pt = Point(here[1], here[0])  # (lon, lat)
        matches = parents[parents.contains(pt)]
        if not matches.empty:
            return matches

    # 2️⃣ Sourcepath/name match
    if sourcepath:
        steps = stepify(sourcepath)
        target_name = steps[-1].replace("_", " ")
        matches = parents[
            parents["NAME"].apply(state.normalname) == state.normalname(target_name)
        ]
        if not matches.empty:
            return matches
    # 3️⃣ fallback: return all parents
    return parents



def intersectingArea(
    source,
    sourcekey,
    parent_levels,
    child_level,
    elevels,
    destination,
    *,
    parent_row,
    select_child_name=None,
    roid=None,
    boundary_geom=None
):

    parent_name = state.normalname(parent_row["NAME"]) if parent_row is not None else "None"
    parent_type = parent_levels.get(child_level)

    if parent_type is None:
        raise ValueError(f"No parent type found for parent_level IN {parent_levels}")

    print(f"\n[DEBUG] intersectingArea | source={source}")
    print(f"[DEBUG] parent_name={parent_name} parent_type={parent_type}, roid={roid}, select_child_name={select_child_name}")

    # ------------------------------------------------------------------
    # 1. Load child layer
    # ------------------------------------------------------------------
    gdf_RAW = get_layer_gdf(source)
    gdf = ensure_4326(gdf_RAW)

    if sourcekey in gdf.columns:
        gdf = gdf.rename(columns={sourcekey: "NAME"})
    else:
        raise ValueError(f"No sourcekey {sourcekey} IN {gdf.columns}")

    if "OBJECTID" in gdf.columns:
        gdf = gdf.rename(columns={"OBJECTID": "FID"})

    all_child_polygons = gdf
    print(f"[DEBUG] Loaded {len(gdf)} child features and cols: {gdf.columns}")

    # ------------------------------------------------------------------
    # 2. Choose geometry (FIXED LOGIC)
    # ------------------------------------------------------------------
    if boundary_geom is not None:
        working_geom = boundary_geom
        print("[DEBUG] Using boundary_geom for intersection")

    elif parent_row is not None and not parent_row.geometry.is_empty:
        working_geom = parent_row.geometry
        print("[DEBUG] Using parent_row geometry")

    else:
        print(f"[DEBUG] under {route()} No geometry available → returning all children")
        return None, all_child_polygons, all_child_polygons

    # ------------------------------------------------------------------
    # 3. Intersection filter
    # ------------------------------------------------------------------
    child_type = elevels[child_level]
    threshold = Overlaps.get(child_type, 0)

    print(f"[DEBUG] Intersection threshold ({child_type}): {threshold}")

    candidates = gdf[gdf.geometry.intersects(working_geom)]

    print(f"[DEBUG] Candidates intersecting bbox: {len(candidates)}")

    if candidates.empty:
        return None, gpd.GeoDataFrame(), all_child_polygons

    # ------------------------------------------------------------------
    # 4. Project + overlap
    # ------------------------------------------------------------------
    proj_crs = "EPSG:3857"

    working_geom_proj = (
        gpd.GeoSeries([working_geom], crs="EPSG:4326")
        .to_crs(proj_crs)
        .iloc[0]
    )

    candidates_proj = candidates.to_crs(proj_crs)

    overlaps = candidates_proj.geometry.intersection(working_geom_proj).area
    mask = overlaps > threshold

    child_polygons_within_parent = candidates[mask].copy()

    print(f"[DEBUG] Children within parent above threshold: {len(child_polygons_within_parent)}")

    # ------------------------------------------------------------------
    # 5. Resolve selected child
    # ------------------------------------------------------------------
    selected_child_name = None

    if roid:
        lat, lon = roid
        pt = Point(lon, lat)

        hit = child_polygons_within_parent[
            child_polygons_within_parent.geometry.contains(pt)
        ]

        if not hit.empty:
            selected_child_name = state.normalname(hit.iloc[0]["NAME"])

    if not selected_child_name and select_child_name:
        hit = child_polygons_within_parent[
            child_polygons_within_parent["NAME"].apply(state.normalname)
            == state.normalname(select_child_name)
        ]

        if not hit.empty:
            selected_child_name = state.normalname(hit.iloc[0]["NAME"])

    if not selected_child_name and not child_polygons_within_parent.empty:
        selected_child_name = state.normalname(child_polygons_within_parent.iloc[0]["NAME"])

    # ------------------------------------------------------------------
    # 6. Save
    # ------------------------------------------------------------------
    if not child_polygons_within_parent.empty:
        child_polygons_within_parent.to_file(destination)

    return selected_child_name, child_polygons_within_parent, all_child_polygons
