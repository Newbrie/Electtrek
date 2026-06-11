import os
import json
from pathlib import Path
from config import ELECTIONS_FILE, BASEX_FILE, TABLE_FILE, RESOURCE_FILE
import config
import state
import re
from shapely.geometry import Point
import logging
import nodes
from state import Treepolys, Fullpolys, Geo_index, normalname, route, stepify, resolve_here_or_redirect

from pathlib import Path
from typing import Optional

LEVEL_INDEX = {
    "country": 0,
    "nation": 1,
    "county": 2,
    "constituency": 3,
    "ward": 4,
    "division": 4,
    "polling_district": 5,
    "walk": 5,
    "street": 6,
    "walkleg": 6,
    "elector": 7,
}

LEVELS = {
    0: "country",
    1: "nation",
    2: "county",
    3: "constituency",
    4: "ward/division",
    5: "polling_district/walk",
    6: "street/walkleg",
    7: "elector",
}

class ProgramContext:
    def get_options(self):
        # on startup its possible to define a range of global options

        return {
            "LEVELS": LEVELS,
            "LEVEL_INDEX": LEVEL_INDEX,
            "LAYERS": state.LAYERS,
            "TABLE_TYPES": state.TABLE_TYPES,
            "DEVURLS": config.DEVURLS, #backend urls used on start up
            "VNORM": state.VNORM, #normalised party used everywhere
            "VCO": state.VCO, # party colours used everywhere
            "streams": get_available_elections(), # currently running elections
            "stream_table": get_stream_table() # all currently running data pipelines
        }

class ElectionContext:
    # when an election is chosen, a number of options exist for given selections
    def __init__(self, celection):
        self.ce = celection # all election option selections

    def get_options(self):
        task_tags, outcome_tags, all_tags = self.ce.get_tags()

        return {
            "territories": state.ElectionTypes, # all possible types of election used in elections
            "tags": all_tags, # all poss election tasks and outcomes
            "task_tags": task_tags, # all poss tasks
            "autofix": list(state.autofix), # stages of data quality cleaning
            "yourparty": state.VID, # party of interest
            "previousParty": state.VID, # incumbent party
            "places": self.ce.places, # the places used by the campaign team
            "resources": self.ce.resources, # the resources in the campaign team
            "selectResources": self.ce.resources, # the selected resources
            "calendar_plan": self.ce.calendar_plan, # the cal plan slots
            "candidate": self.ce.resources, # the selected candidate resources
            "chair": self.ce.resources, # the designated chair resource
            "campaignMgr": self.ce.resources, # the designated campaign manager
            "mapfiles": self.ce.mapfiles #a recent history of nodes navigated

            }



def list_elections():
    """
    Return a list of election names (strings) sorted alphabetically.
    """
    elections_dir = BASEX_FILE.parent  # directory containing election files
    pattern = re.compile(r'^Elections-(.+)\.json$', re.IGNORECASE)

    elections = []

    for file in elections_dir.iterdir():
        if file.is_file():
            match = pattern.match(file.name)
            if match:
                name = match.group(1).upper()
                elections.append(name)

    # Sort alphabetically
    elections.sort()

    return elections


def get_available_elections():
    """
    Return a list of election names found in the elections directory,
    sorted by last modified time (most recent first).
    """
    elections_dir = BASEX_FILE.parent  # directory containing JSON files
    pattern = re.compile(r'^Elections-(.+)\.json$', re.IGNORECASE)

    elections = []

    for file in elections_dir.iterdir():
        match = pattern.match(file.name)
        if match and file.is_file():
            name = match.group(1).upper()
            mtime = file.stat().st_mtime  # last modified time
            elections.append((name, mtime))

    # Sort by modification time, descending (most recent first)
    elections.sort(key=lambda x: x[1], reverse=True)

    # Return only the names
    return [name for name, _ in elections]


def get_elections():
    """
    Return a list of elections as objects with cid and name,
    sorted by last modified time (most recent first).
    """
    elections_dir = BASEX_FILE.parent  # directory containing JSON files
    pattern = re.compile(r'^Elections-(.+)\.json$', re.IGNORECASE)

    elections = []

    try:
        # Use glob for pattern matching (only .json files)
        for file in elections_dir.glob('Elections-*.json'):
            match = pattern.match(file.name)
            if match:
                name = match.group(1).upper()  # Extract election name
                mtime = file.stat().st_mtime  # Get last modified time
                elections.append({"cid": name, "name": name, "mtime": mtime})
    except Exception as e:
        print(f"⚠️ Error loading elections: {e}")

    # Sort by modification time, descending (most recent first)
    elections.sort(key=lambda x: x["mtime"], reverse=True)

    # Return only cid and name for front end
    return [{"cid": e["cid"], "name": e["name"]} for e in elections]


def get_stream_table():
    stream_table = {}
    if  os.path.exists(TABLE_FILE) and os.path.getsize(TABLE_FILE) > 0:
        with open(TABLE_FILE, "r") as f:
            stream_table = json.load(f)
    return stream_table

def resolve_ui_context(program, election, node):
    """
    Merge program, election, and node options into a single dict,
    converting any sets to lists so the result is JSON-serializable.
    """
    def make_json_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_json_serializable(v) for v in obj]
        elif isinstance(obj, set):
            return [make_json_serializable(v) for v in obj]
        else:
            return obj

    merged = {
        **program.get_options(),
        **election.get_options(),
        **node.get_options(program=program, electionctx=election),
    }

    return make_json_serializable(merged)

# This prints a script tag you can paste into your HTML



class CurrentElection(dict):
    RESOURCE_FILE = RESOURCE_FILE
    BASEX_FILE = BASEX_FILE

    def __init__(self, data: dict, election_id: str):
        super().__init__(data)
        self.election_id = election_id
        self.name = election_id  # stable election identity


    @classmethod
    def getstreamrag(cls, elections_dict, election_manager):
        rag = {}

        for name, election in elections_dict.items():
            # 1. Alive check
            alive = bool(
                election.stream_processing
                and election.stream_processing.get("files")
            )

            # 2. Access the manager's internal election dict
            # Adjust '_elections' to whatever your ElectorManager uses to store DFs
            data = getattr(election_manager, '_elections', {}).get(name)

            # 3. Accurate Loaded/Count check
            if data is not None and not data.empty:
                loaded = True
                elect_count = len(data)
            else:
                loaded = False
                elect_count = 0

            # 4. RAG Logic
            if alive and loaded:
                colour = "limegreen"
            elif alive and not loaded:
                colour = "yellow"
            else:
                colour = "red"

            rag[name] = {
                "Alive": alive,
                "Loaded": loaded,
                "Elect": elect_count,
                "RAG": colour
            }

        return rag


    def add_breadcrumb(self, item):
        def is_valid_mapfile_path(path):
            if not isinstance(path, str):
                return False
            if len(path) < 10:  # too short to be real
                return False
            if "/" not in path:
                return False
            if not path.endswith(".html"):
                return False
            return True

        max_size = 7

        if not isinstance(self.get('mapfiles'), list):
            self['mapfiles'] = []

        if is_valid_mapfile_path(item):
            self['mapfiles'].append(item)
            if len(self['mapfiles']) > max_size:
                self['mapfiles'].pop(0)
        else:
            raise Exception (f"in {self.name} Trying to post Invalid Path : {item}" )
        return self['mapfiles']

    @classmethod
    def get_all(cls):
        # Return a list of all current elections, for example, loaded from a directory or database
        elections_dir = cls.BASEX_FILE.parent
        election_files = list(elections_dir.glob("Elections-*.json"))
        elections = []
        for file in election_files:
            election = cls.load(file.stem.replace("Elections-", "").upper())  # assuming the filename contains election IDs
            elections.append(election)
        return elections



    def get_last_node(self, *, create=True):
        """
        Returns the last node for the current election using 4 sources.
        first source is election cid, but cid node memory might fail
        second source is browser GPS location , but this might not fire
        third source is the stored election sourcepath derived from breadcrumb, but this might be corrupted
        fourth source is the stored territory, which must ping.

        If `create=False`, do not call ping_node and return root if CID node is unavailable.
        """

        cid = self.get("cid")
        cidLat = self.get("cidLat")
        cidLong = self.get("cidLong")
        here = (cidLat, cidLong) if cidLat is not None and cidLong is not None else None

        # --- 1. CID lookup ---
        if cid and cid in nodes.TREK_NODES_BY_ID:
            last_node = nodes.TREK_NODES_BY_ID.get(cid,None)
            print(f"___under route: {route()} return to existing cid: {cid}")
            return last_node

        print(f"___under route: {route()} no cid looking to GPS:")

        # --- 2. Resolve location or redirect ---
        here, response = resolve_here_or_redirect(here)
        if response:
            return response  # redirect response


        # --- 3. Resolve node from sourcepath ---
        print(f"___No cid or GPS : {cid}  under {route()}")

        sourcepath = self.get("mapfiles", [None])[-1]
        steps = stepify(sourcepath)
        if not sourcepath or sourcepath == "" or len(steps)< 6:
            sourcepath = self.get("territory", "")

        print(f"___ Last node under {route()} for {self.name} sourcepath: {sourcepath} create:{create}")
        last_node = nodes.MapRoot.ping_node(
                self.resolved_levels,
                sourcepath,
                create=create,
                accumulate = False
            )

        # --- 4. Fallback to root ---
        if not last_node:
            print(f"⚠️ GAP: {cid in nodes.TREK_NODES_BY_ID} @FALLING BACK TO NEAREST NODE cid:{cid}- sp:{sourcepath}")
            print(f"⚠️ @NODE INDEX DUMP:{nodes.TREK_NODES_BY_ID} ")
            last_node = nodes.MapRoot

        print(
            f"___ RETRIEVED LAST DESTINATION - election: {self.name} "
            f"NODE {last_node.value} at loc: {here} "
            f"using source: {sourcepath}"
        )

        return last_node



    def visit_node(self, node):
        from state import Treepolys, Fullpolys, Geo_index
        rlevels = self.resolved_levels
        assert len(rlevels) == 1, f"Expected 1 election, got {len(rlevels)}"

        # The clean unpack
        (c_election, elevels), = rlevels.items()

        # first check that the node is within the election territory
        #   the node.nid must exist and be in the node list
        #   next(iter(rlevels.values()))[level] == node.type
        #   the territory path node must exist
        #   the territory node fid must be in Treepoly[node.type]
        #   the node.fid latlong must be within the Treepoly[node.type] geom
        try:
            territory = self.territory
            steps = stepify(territory)
            level = len(steps) - 1
            parent_row = Treepolys[elevels[level]]

            # ----- LOOKUP BY LAT/LON ---------------------------------------
            latitude = node.latlongroid[0]
            longitude = node.latlongroid[1]
            point = Point(longitude, latitude)  # (lon, lat)
            matched = parent_row[parent_row.contains(point)]
        except:
            print(
                f"___under election {self.name} in a {elevels[level]} at {node.value} territory check exception : "
            )

        self['cid'] = node.nid
        self['cidLat'] = node.latlongroid[0]
        self['cidLong'] = node.latlongroid[1]
        newlist = self.add_breadcrumb(node.mapfile())

        self.save()
        print(f"=== VISIT NODE === {node.nid}")
        print(f"current children:{[c.value for c in node.children]}")
        print(
            f"___under {self.name} leaving breadcrumb: "
            f"{self['mapfiles'][-1]}"
        )

        return True

    def resolve_ui_options(program, election_ctx, node):
        options = {}
        options.update(program.get_options())        # app-level options
        options.update(election_ctx.get_options())   # election-level options
        options.update(node.get_options())            # node-level options
        return options



    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    # ---------- derived flags ----------

    @property
    def adminmode(self) -> bool:
        return bool(self.get("adminmode", False))

    @property
    def stream_processing(self):
        return self.get("stream_processing", {})

    @property
    def pd_or_walk(self) -> str:
        return "polling_district" if self.adminmode else "walk"

    @property
    def street_or_leg(self) -> str:
        return "street" if self.adminmode else "walkleg"

    # ---------- persistence ----------

    # ---------- derived flags ----------

    @property
    def territories(self) -> str:
        return self.get("territories", "W")


    # ---------- resolved levels ----------

    @property
    def resolved_levels(self) -> dict[str, dict[int, str]]:
        """
        Lazily compute and cache resolved LEVELS wrapped in the election name.
        Keeps compound names intact for bivalent extraction downstream.
        """
        if not hasattr(self, "_resolved_levels"):
            resolved: dict[int, str] = {}
            for level, name in sorted(LEVELS.items(), key=lambda x: x[0]):
                resolved[level] = name

            self._resolved_levels = {self.name: resolved}
        return self._resolved_levels

    @property
    def parent_levels(self) -> dict[int, str]:
        """
        Derive parent filtering levels from the resolved levels.
        """
        parent_levels: dict[int, str] = {}
        territory_level = len(stepify(self.territory)) - 1 if self.territory else -1
        logging.debug(f"[DEBUG] territory_level: {territory_level}")
        # 1. Extract the inner mapping once
        # rlevels is now {'ElectionName': {0: 'country', 1: 'ward', ...}}
        election_name = next(iter(self._resolved_levels))
        inner_levels = self._resolved_levels[election_name]

        # 2. Loop through the actual integer levels
        for level, layer_type in inner_levels.items():
            # Clamp parent level
            parent_idx = max(0, min(level - 1, territory_level))

            # Access the parent type from our extracted dict
            parent_type = inner_levels[parent_idx]
            parent_levels[level] = parent_type

            logging.debug(
                f"[DEBUG] Election: {election_name} | level: {level} ({layer_type}) | "
                f"parent: {parent_idx} ({parent_type})"
            )

        self._parent_levels = parent_levels
        return self._parent_levels



    # ---------- node typing ----------


    def node_type(self, level: int) -> str | None:
        return self.resolved_levels.get(level)

    @classmethod
    def _file_for(cls, election_id: str) -> Path:
        """
        Return the path to the election JSON file for a given election_id.
        """
        return cls.BASEX_FILE.with_name(
            cls.BASEX_FILE.name.replace("-DEMO.json", f"-{election_id}.json")
        )

    @classmethod
    def _rfile_for(cls) -> Path:
        """
        Return the path to the election resource JSON file corresponding
        to the RESOURCE_FILE CSV. (Assumes same name but .json extension)
        """
        return cls.RESOURCE_FILE.with_name(
            cls.RESOURCE_FILE.name.replace(".csv", ".json")
        )

    @classmethod
    def get_lastused(cls) -> str:
        """
        Return the election_id of the most recently modified election file.
        """
        elections_dir = cls.BASEX_FILE.parent

        election_files = list(elections_dir.glob("Elections-*.json"))


        if not election_files:
            print(f"-------election directory:{elections_dir} - is empty")
            return "DEMO"
        latest_file = max(election_files, key=lambda p: p.stat().st_mtime)
        print(f"-------election directory:{elections_dir} - {latest_file}")
        return latest_file.stem.replace("Elections-", "").upper()

    @classmethod
    def load(cls, election_id: str) -> "CurrentElection":
        """
        Load election JSON and merge in global resources.
        Falls back to DEMO election if missing.
        """
        print(f"____Get election: {election_id}")

        path = cls._file_for(election_id)
        rpath = cls._rfile_for()

        if not path.exists():
            print("⚠️ Election not found, loading DEMO")
            path = cls._file_for("DEMO")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Ensure election has a resources dict
            data.setdefault('resources', {})

            # Merge global resources without overwriting local
            if rpath.exists():
                with open(rpath, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
                for code, person in rdata.items():
                    data['resources'].setdefault(code, person)

            print(f"✅ Loaded election and resources for {election_id}")
            return cls(data, election_id=election_id)

        except Exception as e:
            raise RuntimeError(f"❌ Failed to load election file {path}: {e}")

    def save(self,new_name=None):
        """
        Persist election JSON to disk
        """
        if new_name is not None:
            self.name = new_name

        path = self._file_for(self.name)
        try:
            print(f"____Under route {route()} Saving New Election File: {self.election_id} → {path}")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self, f, indent=2)
            print("✅ Election JSON written safely")

        except Exception as e:
            raise RuntimeError(f"❌ Failed to write Election JSON: {e}")


    # ---------- tag helpers ----------


    def get_tags(self):
        """
        Split tags into task_tags and outcome_tags, pre-seeded with mandatory election codes.
        """
        # 1. Pre-seed with your mandatory baseline task layers
        task_tags = {}

        # 2. Pre-seed with your baseline canvas outcome milestones
        outcome_tags = {
            "M1": "Member",
            "M2": "Pledge",
            "M3": "HouseBoard",
            "M4": "Postal Voter",
            "M5": "Marked"
        }

        all_tags = {}

        # 3. Pull dynamic incoming records from your model store
        raw_tags = self.get("tags") or {}

        for tag, description in raw_tags.items():
            clean_tag = str(tag).strip()

            # Route depending on campaign prefix matches
            if clean_tag.startswith("L") or clean_tag.startswith("V"):
                task_tags[clean_tag] = description
            elif clean_tag.startswith("M"):
                outcome_tags[clean_tag] = description

            all_tags[clean_tag] = description

        # Ensure baseline seeds are accurately tracked inside your master all_tags lookup ledger too
        all_tags.update({**task_tags, **outcome_tags})

        print(f"___Under route {route()} Dash Task Tags: {task_tags} Outcome Tags: {outcome_tags}")

        return task_tags, outcome_tags, all_tags





# the general list of  election data files and proessing streams
