import os
import json
from pathlib import Path
from config import ELECTIONS_FILE, BASEX_FILE, RESOURCE_FILE
import config
import state
import re
from shapely.geometry import Point
import logging
from state import route, stepify, resolve_here_or_redirect
from state import normalname

from pathlib import Path
from typing import Optional


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


class CurrentElection(dict):
    RESOURCE_FILE = RESOURCE_FILE
    BASEX_FILE = BASEX_FILE

    def __init__(self, data: dict, election_id: str):
        super().__init__(data)
        self.election_id = election_id
        self.name = election_id  # stable election identity


    @classmethod
    def getstreamrag(cls, election_manager=None):
        rag = {}
        # Fetch all elections automatically using cls.get_all()
        elections_list = cls.get_all()

        for election in elections_list:
            # Assuming each election object has a name or identifier attribute (e.g., election.name or election.id)
            name = getattr(election, 'name', getattr(election, 'id', 'UNKNOWN'))

            # 1. Alive check
            alive = bool(
                getattr(election, 'stream_processing', None)
                and election.stream_processing.get("files")
            )

            # 2. Access the manager's internal election dict safely
            data = getattr(election_manager, '_elections', {}) if election_manager else {}
            election_data = data.get(name)

            # 3. Accurate Loaded/Count check
            if election_data is not None and not election_data.empty:
                loaded = True
                elect_count = len(election_data)
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
        LEVEL_INDEX = {
            "country": 0,
            "nation": 1,
            "county": 2,
            "constituency": 3,
            "ward": 4,
            "division": 4,
            "walk": 5,
            "street": 6,
            "elector": 7,
        }

        LEVELS = {
            0: "country",
            1: "nation",
            2: "county",
            3: "constituency",
            4: "ward/division",
            5: "walk",
            6: "street",
            7: "elector",
        }
        if not hasattr(self, "_resolved_levels"):
            resolved: dict[int, str] = {}
            for level, name in sorted(LEVELS.items(), key=lambda x: x[0]):
                resolved[level] = name

            self._resolved_levels = {self.name: resolved}
        return self._resolved_levels

    @property
    def parent_levels(self) -> dict[int, str | None]:
        """
        Dynamically compute parent_levels using the active election's resolved_levels.
        For any level N, its parent is the resolved layer name at level N - 1.
        """
        if not hasattr(self, "_parent_levels"):
            # Get the inner dict of {level: "name"} for this specific election
            election_levels = self.resolved_levels.get(self.name, {})

            parent_map: dict[int, str | None] = {0: None}

            # Sort levels to guarantee we resolve them sequentially
            sorted_levels = sorted(election_levels.keys())

            for level in sorted_levels:
                if level == 0:
                    continue

                # Determine the parent's level index (typically level - 1)
                parent_level_idx = level - 1

                # Retrieve the raw parent name (e.g., "ward/division" or "county")
                raw_parent_name = election_levels.get(parent_level_idx)

                if raw_parent_name:
                    # Keep the full composite name (e.g., 'ward/division')
                    parent_map[level] = raw_parent_name.strip()
                else:
                    parent_map[level] = None

            self._parent_levels = parent_map

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
            print(f"____Under route {state.route()} Saving New Election File: {self.election_id} → {path}")
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

        print(f"___Under route {state.route()} Dash Task Tags: {task_tags} Outcome Tags: {outcome_tags}")

        return task_tags, outcome_tags, all_tags





# the general list of  election data files and proessing streams
