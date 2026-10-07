
from types import MappingProxyType
import pandas as pd
import os
from config import LAST_RESULTS_FILE, CANDIDATES_FILE
import json
import re
from flask import has_request_context, request, redirect

progress = {}


branchcolours = [
    "#006064",  # 0 Darkest Cyan (Cyan 900)
    "#00838F",  # 1 Deep Sea
    "#0097A7",  # 2 Original Cyan
    "#00ACC1",  # 3 Robin's Egg
    "#00BCD4",  # 4 Vivid Cyan
    "#26C6DA",  # 5 Bright Turquoise
    "#4DD0E1",  # 6 Sky Aqua
    "#80DEEA",  # 7 Soft Cyan
    "#B2EBF2",  # 8 Pale Mist
    "#E0F7FA",  # 9 Ice White-Cyan
    "#00E5FF",  # 10 Electric Cyan (High Saturation)
    "#18FFFF",  # 11 Neon Aqua
]


def route():
    if has_request_context():
        return request.endpoint
    return None  # or a default string like "no_request_context"

def resolve_here_or_redirect(here):
    if has_request_context():
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        if lat is not None and lon is not None:
            here = (lat, lon)

        if here is None:
            return None, redirect(url_for("get_location"))

    return here, None

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

def pathify(parts):
    """
    Takes a clean list of geographic parts and builds a node path.
    Automatically infers whether it's a MAP or a PRINT view based on array depth.
    """
    if not parts:
        return ""

    base_path = "/".join(parts)

    # Inference rules based on hierarchy depth:
    # Length 1-5: Country, Region, County, Constituency, Ward -> Always MAP overviews
    # Length 6+: Polling Districts (PDS) or Walks -> Swaps to PRINT sheets
    return f"{base_path}"

def extract_path_at_level(node_path: str, target_level: int) -> str | None:
    """
    Extracts a truncated sub-path up to the target_level (0-indexed)
    from a raw node_path string.
    """
    if not node_path or target_level < 0:
        return None

    # Clean out trailing filenames like '-MAP.html' if passed accidentally
    clean_path = node_path.split("-MAP.html")[0].strip("/")
    parts = [p for p in clean_path.split("/") if p]

    if not parts:
        return None

    if target_level >= len(parts):
        return "/".join(parts)

    return "/".join(parts[: target_level + 1])


def derive_territory(sourcepath: str) -> str | None:
    if not sourcepath:
        return None

    clean = sourcepath.split("-MAP.html")[0].strip("/")
    parts = [p for p in clean.split("/") if p]
    if not parts:
        return None

    depth = len(parts)
    target_level = 2 if depth >= 3 else (1 if depth == 2 else 0)

    base_path = extract_path_at_level(sourcepath, target_level)
    if not base_path:
        return None

    leaf_name = base_path.split("/")[-1]
    # Check if base_path already ends with leaf_name before building filename
    return f"{base_path}/{leaf_name}-MAP.html"  # Returns "UNITED_KINGDOM/ENGLAND-MAP.html"







def selprefix(election):
    from elections import list_elections

    election = election.upper()
    elections_list = list_elections()  # already sorted

    if election not in elections_list:
        raise ValueError(f"Election '{election}' not found")

    idx = elections_list.index(election)

    if idx >= 26:
        raise ValueError("Too many elections for single-letter prefix")

    return chr(65 + idx)

def make_upd(election, pd):
    eprefix = selprefix(election).strip().upper()
    pd = str(pd).strip().upper()

    if not eprefix:
        raise ValueError(f"Invalid election prefix for election={election}")

    if not pd:
        raise ValueError("Blank PD")

    return f"{eprefix}-{pd}"



def normalname(name):
    def clean(s):
        if pd.isna(s) or s is None:
            return ""

        s = str(s)
        s = s.replace(" & ", " AND ")

        # Allow alphanumeric, spaces, underscores, and parentheses
        s = re.sub(r"[^A-Za-z0-9 _\(\)]+", "", s)

        # Normalize whitespace and convert to underscores
        s = re.sub(r"\s+", " ", s).strip()
        s = s.replace(" ", "_")

        # Collapse duplicate and leading/trailing underscores
        s = re.sub(r"_+", "_", s).strip("_")

        return s.upper().removesuffix("_ED")

    # Handle Pandas Series vectorially
    if isinstance(name, pd.Series):
        return name.fillna("").astype(str).apply(clean)

    # Handle all scalar types (str, int, float, np.str_, np.int64, etc.)
    try:
        return clean(name)
    except Exception as e:
        print(f"______ERROR: Failed to process {type(name)}: {e}")
        return ""


def get_path_step(path, n):
    """
    Return the nth component of a node path (0-based index).

    Example:
        get_path_step("A/B/C", 1) -> "B"
    """
    if not path:
        return None

    parts = [p for p in path.strip("/").split("/") if p]

    if 0 <= n < len(parts):
        return parts[n]

    return None




def clean_text(value: str | None) -> str:
    """Remove hidden unicode chars and trim whitespace."""
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r'[\u202a-\u202e]', '', value)
    return value.strip()


def clean_mobile(value: str | None) -> str:
    """Normalize mobile numbers."""
    value = clean_text(value)
    return value.replace("M:", "").replace(" ", "").strip()


def generate_code(firstname: str, surname: str, existing_codes: set) -> str:
    """Generate a short unique identifier code."""
    base = (firstname[:1] + surname[:1]).upper()
    if base not in existing_codes:
        return base
    i = 1
    while f"{base}{i}" in existing_codes:
        i += 1
    return f"{base}{i}"


# ------------------------------------------------------------------------------
# 🗺️ SPATIAL PIPELINE FUNCTIONS
# ------------------------------------------------------------------------------


import time

def t(msg, start=[time.perf_counter()]):
    now = time.perf_counter()
    print(f"[TIMER] {msg}: {now - start[0]:.3f}s")
    start[0] = now




def load_candidates():
    global Candidates
    # --- Candidates ---
    print(f"___Creating CANDIDATES data and file")
    if not os.path.exists(CANDIDATES_FILE) or os.path.getsize(CANDIDATES_FILE) == 0:

        Candidates_data = pd.read_excel(
            f"{workdirectories['candidatedir']}/Candidate_Placement_for_Surrey-2.xlsx"
        )

        for _, row in Candidates_data.iterrows():

            ward = row.get("Division")
            c1 = row.get("Candidate 1")
            c2 = row.get("Candidate 2")

            # Skip row if ward OR either candidate is missing
            if pd.isna(ward) or pd.isna(c1) or pd.isna(c2):
                continue

            # Now safe to normalise
            nodename = normalname(str(ward))
            C1 = normalname(str(c1))
            C2 = normalname(str(c2))

            Candidates["division"][nodename] = {
                "Candidate_1": C1,
                "Candidate_2": C2
            }


        with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
            json.dump(Candidates, f, indent=2, ensure_ascii=False)


    else:
        # Load from file without overwriting keys
        with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            Candidates["ward"].update(data.get("ward", {}))
            Candidates["division"].update(data.get("division", {}))
            Candidates["constituency"].update(data.get("constituency", {}))


def load_last_results():
    global LastResults

    if not os.path.exists(LAST_RESULTS_FILE) or os.path.getsize(LAST_RESULTS_FILE) == 0:
        # --- Constituencies ---
        Con_Results_data = pd.read_excel(
            f"{workdirectories['resultdir']}/HoC-GE2024-results-by-constituency.xlsx"
        )

        for _, row in Con_Results_data.iterrows():
            nodename = normalname(row["Constituency name"])
            party = normalname(row["First party"])
            electorate = int(row["Electorate"]) if pd.notna(row["Electorate"]) else None
            turnout = round(float(row["Turnout"]), 6) if "Turnout" in row and pd.notna(row["Turnout"]) else None

            LastResults["constituency"][nodename] = {
                "FIRST": party,
                "TURNOUT": turnout,
                "ELECTORATE": electorate
            }

        # --- Wards ---
        Ward_Results_data = pd.read_excel(
            f"{workdirectories['candidatedir']}/LEH-Candidates-2023.xlsx"
        )
        Ward_Results_data = Ward_Results_data.loc[Ward_Results_data["WINNER"] == 1]

        for _, row in Ward_Results_data.iterrows():
            nodename = normalname(row["NAME"])
            party = normalname(row["PARTYNAME"])
            electorate = int(row["ELECT"]) if pd.notna(row["ELECT"]) else None
            turnout = round(float(row["TURNOUT"]), 6) if "TURNOUT" in row and pd.notna(row["TURNOUT"]) else None

            LastResults["ward"][nodename] = {
                "FIRST": party,
                "TURNOUT": turnout,
                "ELECTORATE": electorate
            }

        # --- Divisions ---
        Level4_Results_data = pd.read_excel(
            f"{workdirectories['resultdir']}/opencouncildata_councillors.xlsx"
        )

        for _, row in Level4_Results_data.iterrows():
            nodename = normalname(row["Ward Name"])
            party = normalname(row["Party Name"])

            LastResults["division"][nodename] = {
                "FIRST": party
            }

        # --- Persist ---
        with open(LAST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(LastResults, f, indent=2, ensure_ascii=False)

    else:
        # Load from file without overwriting keys
        with open(LAST_RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            LastResults["ward"].update(data.get("ward", {}))
            LastResults["division"].update(data.get("division", {}))
            LastResults["constituency"].update(data.get("constituency", {}))


#Treepolys = {
#    'country': empty_gdf(),
#    'nation': empty_gdf(),
#    'county': empty_gdf(),
#    'constituency': empty_gdf(),
#    'ward': empty_gdf(),
#    'division': empty_gdf()
#}


# original dict
_LEVEL_ZOOM_MAP = {
    'country': 12,
    'nation': 13,
    'county': 14,
    'constituency': 15,
    'ward': 16,
    'division': 16,
    'polling_district': 17,
    'walk': 17,
    'street': 18
}

# share task and outcome tags for each election

OPTIONS = {
    "ACC": False,
    "DEVURLS": {},
    "territories": {},
    "yourparty": {},
    "previousParty": {},
    "resources" : {},
    "areas" : {},
    "candidate" : {},
    "chair" : {},
    "tags": {},
    "task_tags": {},
    "autofix" : {},
    "VNORM" : {},
    "VCO" : {},
    "streams" : {},
    "stream_table": {}
    # Add more mappings here if needed
}


TABLE_TYPES  = {
    "resources": "Resources",
    "events": "Event Markers",
    "DQstats": "Import Data Quality",
    "stream_table": "Import Data Streams",
    "nodelist_xref" : "Nodelist xref",
    "country_layer" : "Countries",
    "nation_layer" : "Nations",
    "county_layer" : "Counties",
    "constituency_layer" : "Constituencies",
    "ward_layer" : "Wards",
    "division_layer" : "Divisions",
    "polling_district_layer" : "Polling Districts",
    "walk_layer" : "Walks",
    "street_layer" : "Streets"
}
# make it read-only
LEVEL_ZOOM_MAP = MappingProxyType(_LEVEL_ZOOM_MAP)

ElectionTypes = {"W":"Westminster","C":"County","B":"Borough","P":"Parish","U":"Unitary"}
VID = {"U" : "Uncanvassed","R" : "Reform","C" : "Conservative","S" : "Labour","LD" :"LibDem","G" :"Green","I" :"Independent","PC" : "Plaid Cymru","SD" : "SDP","Z" : "Maybe","W" :  "Wont Vote", "X" :  "Won't Say"}
VNORM = {"OTHER":"O","REFORM" : "R" , "REFORM_DERBY" : "R" ,"REFORM_UK" : "R" ,"REF" : "R", "RUK" : "R","R" :"R","CONSERVATIVE_AND_UNIONIST" : "C","CONSERVATIVE" : "C", "CON" : "C", "C":"C","LABOUR_PARTY" : "S","LABOUR" : "S", "LAB" :"S", "L" : "S", "LIBERAL_DEMOCRATS" :"LD" ,"LIBDEM" :"LD" , "LIB" :"LD","LD" :"LD", "GREEN_PARTY" : "G" ,"GREEN" : "G" ,"G":"G", "INDEPENDENT" : "I", "IND" : "I" ,"I" : "I" ,"PLAID_CYMRU" : "PC" ,"PC" : "PC" ,"SNP": "SNP" ,"MAYBE" : "Z" ,"WONT_VOTE" : "W" ,"WONT_SAY" : "X" , "SDLP" : "S", "SINN_FEIN" : "SF", "SPK": "N", "TUV" : "C", "UUP" : "C", "DUP" : "C","APNI" : "N", "INET": "I", "NIP": "I","PBPA": "I","WPB": "S","OTHER" : "O"}
VCO = {
    "S": "#DC241F",   # Labour (Official Red)
    "C": "#0087DC",   # Conservative (Official Blue)
    "LD": "#FAA61A",  # Liberal Democrats (Official Gold/Yellow)
    "G": "#6AB023",   # Green Party (Official Green)
    "R": "#00BFFF",   # Reform UK (Official Turquoise/Cyan)
    "I": "#4B0082",   # Independent (Indigo)
    "PC": "#990033",  # Plaid Cymru (Official Party Crimson)
    "SD": "#E65C00",  # SDP (Orange)
    "O": "#8B4513",   # Other (Brown)
    "Z": "#7F8C8D",   # Maybe (Neutral Muted Grey)
    "W": "#DCDCDC",   # Won't Vote (Light Grey fallback - pure #FFFFFF is invisible on white lists!)
    "X": "#34495E"    # Won't Say (Dark Charcoal Grey)
}
onoff = {"on" : 1, 'off': 0}
data = [0] * len(VID)
VIC = dict(zip(VID.keys(), data))
autofix = {0,1,2,3,4}



levelcolours = {"C0" :'lightblue',"C1" :'darkred', "C2":'blue', "C3":'indigo', "C4":'red', "C5":'darkblue', "C6":'orange', "C7":'lightblue', "C8":'lightgreen', "C9":'purple', "C10":'pink', "C11":'cadetblue', "C12":'lightred', "C13":'#006064',"C14": 'green', "C15": 'beige',"C16": 'black', "C17":'lightgray', "C18":'darkpurple',"C19": 'darkgreen', "C20": 'orange', "C21":'lightpurple',"C22": 'limegreen', "C23": 'cyan',"C24": 'green', "C25": 'beige',"C26": 'black', "C27":'lightgray', "C28":'darkpurple',"C29": 'darkgreen', "C30": 'orange', "C31":'lightpurple',"C32": 'limegreen', "C33": 'cyan', "C34": 'orange', "C35":'lightpurple',"C36": 'limegreen', "C37": 'cyan' }



kanban_options = [
    {"code": "R", "label": "Resourcing"},
    {"code": "P", "label": "Post-Bundling"},
    {"code": "L", "label": "Informing"},
    {"code": "C", "label": "Canvassing"},
    {"code": "K", "label": "Klosing"},
    {"code": "T", "label": "Telling"}
]


ROOT_LEVEL = {
    "W": 3,
    "C": 2,
    "U": 2,
    "B": 4,
    "P": 4,
}


# Threshold configuration: (Intersection Area / Child Area) >= Threshold

Candidates = {
    "ward": {},
    "division": {},
    "constituency": {},
}


LastResults = {
    "ward": {},
    "division": {},
    "constituency": {},
}

areaoptions = ["UNITED_KINGDOM/ENGLAND/SURREY/SURREY_HEATH/SURREY_HEATH-MAP.html"]





#or i, (key, fg) in enumerate(Featurelayers.items(), start=1):
#    fg.id = i
#    fg.type = [
#        'country','nation', 'county', 'constituency', 'ward', 'division', 'polling_district',
#        'walk', 'street', 'result', 'target', 'data', 'special'
#    ][i - 1]

# Overall progress fractions for each stage


STAGE_FRACTIONS = {
    "sourcing": 0.10,
    "normz": 0.10,
    "address_norm":0.50,
    "spatial_discovery": 0.10,
    "spatial_join": 0.05,
    "tagging": 0.05,
    "deduplication": 0.05,
    "assignment": 0.05
}

progress = {
    "stages": STAGE_FRACTIONS,
    "election": "",
    "status": "idle",       # Can be 'idle', 'running', 'complete', 'error'
    "percent": 0,           # Integer from 0 to 100
    "targetfile": "test.csv",
    "message": "Waiting...", # Optional string
    "dqstats_html": ""
    }


def subending(filename, ending):
  stem = filename.replace(".XLSX", "@@@").replace(".CSV", "@@@").replace(".xlsx", "@@@").replace(".csv", "@@@").replace("-PRINT.html", "@@@").replace("-CAL.html", "@@@").replace("-MAP.html", "@@@").replace("-WALKS.html", "@@@").replace("-ZONES.html", "@@@").replace("-PDS.html", "@@@").replace("-DIVS.html", "@@@").replace("-WARDS.html", "@@@")
  print(f"____Subending test: from {filename} to {stem.replace('@@@', ending)}")
  return stem.replace("@@@", ending)

DQstats = {
"df": pd.DataFrame(),  # initially empty
}

def update_progress(progress, stage_name, stage_local_fraction, message="", status="running"):
    # 1. Normalize local stage fraction (handles both 0.0-1.0 and 0-100 ranges)
    if stage_local_fraction > 1.0:
        stage_local_fraction /= 100.0
    stage_local_fraction = max(0.0, min(1.0, float(stage_local_fraction)))

    # 2. Update status and message on the progress dictionary
    progress["status"] = status
    if message:
        progress["message"] = message

    # 3. Handle terminal statuses directly
    if status in ["complete", "error"]:
        progress["current_stage"] = stage_name
        progress["stage_progress"] = 100.0 if status == "complete" else progress.get("stage_progress", 0.0)
        progress["percent"] = 100.0 if status == "complete" else progress.get("percent", 0.0)
        return

    # 4. Sum weights of completed stages
    stages = progress.get("stages", STAGE_FRACTIONS)
    accumulated = 0.0
    for name, weight in stages.items():
        if name == stage_name:
            break
        accumulated += weight

    # 5. Calculate global percentage
    current_stage_weight = stages.get(stage_name, 0.0)
    overall_fraction = accumulated + (stage_local_fraction * current_stage_weight)

    # 6. Apply stage progress state
    progress["current_stage"] = stage_name
    progress["stage_progress"] = round(stage_local_fraction * 100.0, 1)
    progress["percent"] = round(min(100.0, overall_fraction * 100.0), 1)




layeritems = []
#allelectors = pd.read_csv(config.workdirectories['workdir']+"/"+ filename, engine='python',skiprows=[1,2], encoding='utf-8',keep_default_na=False, na_values=[''])
# need a keyed dict indicating last recorded winning first party name for a given normalised node name



load_last_results()
load_candidates()
