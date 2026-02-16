import os
import json
from flask import has_request_context, request
from pathlib import Path
from config import ELECTIONS_FILE, BASE_FILE, TABLE_FILE, RESOURCE_FILE
import config
import state
import re
from shapely.geometry import Point
import logging


branchcolours = [
    "#D32F2F",  # 0 strong red
    "#1976D2",  # 1 strong blue
    "#388E3C",  # 2 strong green
    "#7B1FA2",  # 3 deep purple
    "#F57C00",  # 4 strong orange
    "#C2185B",  # 5 magenta
    "#00796B",  # 6 teal
    "#512DA8",  # 7 indigo
    "#455A64",  # 8 blue-grey
    "#000000",  # 9 black
    "#795548",  # 10 brown
    "#0097A7",  # 11 cyan
    "#AFB42B",  # 12 olive
]



def stepify(path):
    if not path:
        return []

    route = (
        path.replace('/WALKS/', '/')
            .replace('/PDS/', '/')
            .replace('/WARDS/', '/')
            .replace('/DIVS/', '/')
    )
    parts = route.split("/")
    last = parts.pop()

    if "-PRINT.html" in last:
        leaf = subending(last, "").split("--").pop()
        parts.append(leaf)

    print("____LEAFNODE:", path, parts)
    return parts


def route():
    if has_request_context():
        return request.endpoint
    return None  # or a default string like "no_request_context"

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



def capped_append(lst, item):
    max_size = 7
    if not isinstance(lst, list):
        return
    lst.append(item)
    if len(lst) > max_size:
        lst.pop(0)  # Remove oldest
    return lst


def get_available_elections():
    """
    Return a dict of all elections found in the elections directory
    """
    election_files = {}
    pattern = re.compile(r'^Elections-(.+)\.json$', re.IGNORECASE)

    # Use BASE_FILE.parent because we want the directory containing the JSONs
    for file in BASE_FILE.parent.iterdir():
        match = pattern.match(file.name)
        if match:
            name = match.group(1)
            election_files[name] = str(file)
    return election_files

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



class CurrentElection(dict):
    RESOURCE_FILE = RESOURCE_FILE
    BASE_FILE = BASE_FILE

    def __init__(self, data: dict, election_id: str):
        super().__init__(data)
        self.election_id = election_id
        self.name = election_id  # stable election identity

    def visit_node(self, node):
        from state import Treepolys, Fullpolys
        rlevels = self.resolved_levels
        # first check that the node is within the election territory
        territory = self.territory
        steps = stepify(territory)
        level = len(steps) - 1
        parent_row = Treepolys[rlevels[level]]

        # ----- LOOKUP BY LAT/LON ---------------------------------------
        latitude = node.latlongroid[0]
        longitude = node.latlongroid[1]
        point = Point(longitude, latitude)  # (lon, lat)
        matched = parent_row[parent_row.contains(point)]

        # ----- SAVE IF MATCHED ---------------------------------------------
#        if not matched.empty:
        if True:
            self['cid'] = node.nid
            self['cidLat'] = node.latlongroid[0]
            self['cidLong'] = node.latlongroid[1]
            self['mapfiles'] = capped_append(self['mapfiles'], node.mapfile(rlevels))
            self.save()
            print(f"=== VISIT NODE === {node.nid}")
            print(f"current children:{[c.value for c in node.children]}")
            print(
                f"___under {self.name} leaving breadcrumb: "
                f"{self['mapfiles'][-1]}"
            )
        else:
            return None

        return node.children

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
    def resolved_levels(self) -> dict[int, str]:
        """
        Lazily compute and cache resolved LEVELS for this election instance.
        """
        if not hasattr(self, "_resolved_levels"):
            resolved: dict[int, str] = {}

            for level, name in sorted(LEVELS.items(), key=lambda x: x[0]):
                if name == "ward/division":
                    resolved[level] = (
                        "division" if self.territories in ("C", "U") else "ward"
                    )
                elif name == "polling_district/walk":
                    resolved[level] = (
                        "polling_district" if self.adminmode else "walk"
                    )
                elif name == "street/walkleg":
                    resolved[level] = (
                        "street" if self.adminmode else "walkleg"
                    )
                else:
                    resolved[level] = name

            self._resolved_levels = resolved

        return self._resolved_levels

    @property
    def parent_levels(self) -> dict[int, str]:
        """
        Derive parent filtering levels from the resolved levels.
        """
        parent_levels: dict[int, str] = {}
        territory_level = len(stepify(self.territory)) - 1 if self.territory else -1
        logging.debug(f"[DEBUG] territory_level: {territory_level}")

        rlevels = self._resolved_levels
        for level, layer_type in rlevels.items():
            parent_level = max(0, min(level - 1, territory_level)) # clamp parent level using territory level
            parent_levels[level] = rlevels[parent_level]

            logging.debug(f"[DEBUG] level: {level}, layer_type: {layer_type}, parent_level: {parent_level}, parent_layer_type: {rlevels[parent_level]}")

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
        return cls.BASE_FILE.with_name(
            cls.BASE_FILE.name.replace("-DEMO.json", f"-{election_id}.json")
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
        elections_dir = cls.BASE_FILE.parent

        election_files = list(elections_dir.glob("Elections-*.json"))


        if not election_files:
            print(f"-------election directory:{elections_dir} - is empty")
            return "DEMO"
        latest_file = max(election_files, key=lambda p: p.stat().st_mtime)
        print(f"-------election directory:{elections_dir} - {latest_file}")
        return latest_file.stem.replace("Elections-", "")

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

    def save(self):
        """
        Persist election JSON to disk
        """
        if not self.name:
            raise ValueError("Cannot save election without election_id")

        path = self._file_for(self.name)

        print("Saving resources:", self.get("resources"))
        print("Resource count:", len(self.get("resources", {})))
        try:
            print(f"____Under route {route()} Saving Election File: {self.election_id} → {path}")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self, f, indent=2)
            print("✅ Election JSON written safely")

        except Exception as e:
            raise RuntimeError(f"❌ Failed to write Election JSON: {e}")


    # ---------- tag helpers ----------


    def get_tags(self):
        """
        Split tags into task_tags and outcome_tags
        """
        task_tags = {}
        outcome_tags = {}
        all_tags = {}

        for tag, description in self.get("tags", {}).items():
            if tag.startswith("L"):
                task_tags[tag] = description
            elif tag.startswith("M"):
                outcome_tags[tag] = description
            all_tags[tag] = description

        print(f"___Under route {route()} Dash Task Tags: {task_tags} Outcome Tags: {outcome_tags}")
        return task_tags, outcome_tags, all_tags





# the general list of  election data files and proessing streams
