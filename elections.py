import os
import json
from flask import has_request_context, request
from pathlib import Path
from config import ELECTIONS_FILE


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



class CurrentElection(dict):
    """
    Dict-backed election object with helpers
    """
    BASE_FILE = Path(ELECTIONS_FILE)

    DEFAULTS = {
        "adminview": False,
        "territories": "W",
        "walksize": 300,
        "teamsize": 6,
        "resources": [],
        "places": {},
        "tags": {},
        "calendar_plan": {"slots": {}},
    }

    # ---------- construction ----------

    def __init__(self, data: dict, election_id: str | None = None):
        merged = {**self.DEFAULTS, **data}
        super().__init__(merged)
        self.election_id = election_id
        self.name = election_id



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



    # ---------- node typing ----------

    def childnode_type(self, level: int) -> str | None:
        """
        Return the child node type for a given parent level,
        using this election's resolved levels.
        """
        next_level = level + 1
        if next_level > max(self.resolved_levels):
            return None
        return self.resolved_levels.get(next_level)

        return self.resolved_levels.get(next_level)

    def node_type(self, level: int) -> str | None:
        return self.resolved_levels.get(level)

    @classmethod
    def _file_for(cls, election_id: str) -> Path:
        """
        Return the path to the election JSON file for a given election_id.
        """
        return cls.BASE_FILE.with_name(
            cls.BASE_FILE.name.replace(".json", f"-{election_id}.json")
        )

    @classmethod
    def get_current_election(cls) -> str:
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
        Load election JSON from disk.
        Falls back to DEMO election if missing.
        """
        print(f"____Get election: {election_id}")

        path = cls._file_for(election_id)
        print(f"____Under route {route()} Reading CurrentElection from file: {path}")

        if not path.exists():
            print("⚠️ Election not found, loading DEMO")
            path = cls._file_for("DEMO")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✅ Loaded election {election_id}")
            return cls(data, election_id=election_id)

        except Exception as e:
            raise RuntimeError(f"❌ Failed to load election file {path}: {e}")

    def save(self):
        """
        Persist election JSON to disk
        """
        if not self.election_id:
            raise ValueError("Cannot save election without election_id")

        path = self._file_for(self.election_id)

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

        for tag, description in self.get("tags", {}).items():
            if tag.startswith("L"):
                task_tags[tag] = description
            elif tag.startswith("M"):
                outcome_tags[tag] = description

        print(f"___Under route {route()} Dash Task Tags: {task_tags} Outcome Tags: {outcome_tags}")
        return task_tags, outcome_tags

    @classmethod
    def get_available_elections(cls):
        """
        Return a dict of all elections found in the elections directory
        """
        import re

        election_files = {}
        pattern = re.compile(r'^elections-(.+)\.json$', re.IGNORECASE)

        for file in cls.BASE_FILE.parent.iterdir():  # directory where election JSONs are
            match = pattern.match(file.name)
            if match:
                name = match.group(1)
                election_files[name] = str(file)
        return election_files


    @classmethod
    def last_election(cls) -> str:
        """
        Return the most recently used election.
        Fallback to 'DEMO' if none found.
        """
        from pathlib import Path

        last = "DEMO"
        elections_dir = cls.BASE_FILE.parent

        election_files = cls.get_available_elections()  # dict: name → path
        print(f"____election files: {list(election_files.keys())} under route {route()}")

        if election_files:
            paths = [
                elections_dir / f"elections-{name}.json"
                for name in election_files
            ]

            paths = [p for p in paths if p.exists()]

            if paths:
                # 🔑 Use modification time, not access time
                paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                last = paths[0].stem.replace("elections-", "")

        print(f"____last election: {last}")
        return last





# the general list of  election data files and proessing streams
