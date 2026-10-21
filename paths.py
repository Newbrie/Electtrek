import layers

IGNORABLE_SEGMENTS = {"PDS", "WALKS", "DIVS", "WARDS"}

FILE_SUFFIXES = [
    "-PRINT.html", "-MAP.html","-CAL.html", "-WALKS.html",
    "-ZONES.html", "-PDS.html", "-DIVS.html", "-WARDS.html"
]

def clean_path_part(part):
    """Clean file suffixes, or return None if ignorable/empty."""
    if part in IGNORABLE_SEGMENTS:
        return None
    for suffix in FILE_SUFFIXES:
        if part.endswith(suffix):
            return None
    return part

def stepify(path_str):
    """Split path string, clean each segment, and remove sequential duplicates."""
    parts = path_str.strip().split("/")
    cleaned = []

    for part in parts:
        cleaned_part = clean_path_part(part)
        if cleaned_part:
            # Only append if it's the first element OR not a duplicate of the previous element
            if not cleaned or cleaned[-1] != cleaned_part:
                cleaned.append(cleaned_part)

    return cleaned

TYPE_SEGMENT = {"ward": "WARDS", "division": "DIVS"}
TYPED_PARENT_LEVELS = {"constituency"}

def is_typed_parent(parent_path):
    entry = layers.Geo_index.get(parent_path)
    return bool(entry) and str(entry.get("level", "")).lower() in TYPED_PARENT_LEVELS

def make_child_path(parent_path, layer_type, child_name):
    """Used when BUILDING the index: add the type segment under a constituency."""
    seg = TYPE_SEGMENT.get(str(layer_type).lower())
    if seg and is_typed_parent(parent_path):
        return f"{parent_path}/{seg}/{child_name}"
    return f"{parent_path}/{child_name}"

def typed_split(path_str):
    """Like stepify, but KEEPS the WARDS/DIVS type segments (for index traversal)."""
    keep = set(TYPE_SEGMENT.values())
    out = []
    for part in path_str.strip().split("/"):
        if not part or any(part.endswith(s) for s in FILE_SUFFIXES):
            continue
        if part in IGNORABLE_SEGMENTS and part not in keep:
            continue
        out.append(part)
    return out

def pathify(parts, leaf_type=None, branch="ward"):
    """Rebuild a typed index path from level-aligned parts (stepify output).
    leaf_type: type of the last part ('ward' or 'division').
    branch: type assumed for any intermediate node below a constituency
            (walks hang off wards, so the default is 'ward')."""
    if not parts:
        return ""
    path = parts[0]
    for i, part in enumerate(parts[1:], start=1):
        is_last = i == len(parts) - 1
        seg = TYPE_SEGMENT.get(leaf_type if (is_last and leaf_type) else branch)
        if seg and is_typed_parent(path):
            path = f"{path}/{seg}/{part}"
        else:
            path = f"{path}/{part}"
    return path

def derive_territory(sourcepath: str) -> str | None:
    if not sourcepath:
        return None

    depth = len(stepify(sourcepath))        # level-aligned: no filename, no type segment
    if depth == 0:
        return None

    target_level = min(depth - 1, 2)         # country=0, nation=1, county=2 at most

    base_path = extract_path_at_level(sourcepath, target_level)
    if not base_path:
        return None

    leaf_name = base_path.split("/")[-1]
    return f"{base_path}/{leaf_name}-MAP.html"


def extract_path_at_level(node_path: str, target_level: int) -> str | None:
    """
    Truncate a raw node_path to the given level (0-indexed). Type segments
    (WARDS/DIVS) belong to the node after them and are not counted as a level.
    Trailing map filenames (e.g. 'GODSTONE-MAP.html') are ignored.
    """
    if not node_path or target_level < 0:
        return None

    parts = [p for p in node_path.strip("/").split("/") if p]

    # Drop a trailing filename segment such as 'GODSTONE-MAP.html'
    if parts and parts[-1].endswith(".html"):
        parts.pop()

    if not parts:
        return None

    type_segments = set(TYPE_SEGMENT.values())     # {"WARDS", "DIVS"}

    # Index of the last part of each level (a type segment is folded into the next part)
    level_ends = [
        i for i, part in enumerate(parts)
        if not (0 < i < len(parts) - 1 and part in type_segments)
    ]

    end = level_ends[min(target_level, len(level_ends) - 1)]
    return "/".join(parts[: end + 1])

def get_areaTree(node_path: str, geo_index: dict, max_depth: int = 2) -> dict:
    """
    Build an area tree starting at the county level of the given node path.

    Children of a constituency are grouped by type, because a ward and a
    division can share a name:
        EAST_SURREY: {"WARDS": {"GODSTONE": {...}}, "DIVS": {"GODSTONE": {...}}}

    The WARDS/DIVS grouping level is NOT counted towards max_depth.
    max_depth=1: county and its constituencies
    max_depth=2: ... and their wards/divisions (grouped)
    max_depth=3: ... and their children (walks)
    """
    # County is level 2. A shorter path clamps to the node itself, as the
    # old fallback did. Filenames and type segments are handled by the helper.
    county_path = extract_path_at_level(node_path, 2)
    if not county_path:
        return {}

    group_names = set(TYPE_SEGMENT.values())          # {"WARDS", "DIVS"}

    def _recursive_build(path, depth):
        node = layers.Geo_index.get(path)
        if not node:
            print(f"Missing geo_index path: {path!r}")
            return {}

        name = node.get("name", path.split("/")[-1])

        # At the requested depth, stop without adding empty placeholder children.
        if depth >= max_depth:
            return {name: {}}

        typed_parent = str(node.get("level", "")).lower() in TYPED_PARENT_LEVELS
        children_dict = {}

        for child_path in node.get("children", []):
            child_tree = _recursive_build(child_path, depth + 1)
            if not child_tree:
                continue

            group = child_path.split("/")[-2] if typed_parent else None
            if group in group_names:
                children_dict.setdefault(group, {}).update(child_tree)
            else:
                children_dict.update(child_tree)

        return {name: children_dict}

    return _recursive_build(county_path, depth=0)
