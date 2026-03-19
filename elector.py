import pandas as pd
import threading
import os
import logging
from config import ELECTOR_FILE

# ------------------------
# Logging Setup
# ------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

_lock = threading.RLock()



class ElectorManager:
    def __init__(self):
        self._combined = pd.DataFrame()
        self._elections = {}  # Elections will be part of the instance
        logger.debug("Initializing ElectorManager")
        logger.debug(f"ELECTOR_FILE path: {os.path.abspath(ELECTOR_FILE)}")

        if os.path.exists(ELECTOR_FILE):
            logger.debug("Elector file exists. Attempting to load.")
            try:
                df = pd.read_csv(ELECTOR_FILE, sep='\t', encoding='utf-8')
                logger.debug(f"Loaded file with {len(df)} rows and columns {list(df.columns)}")

                if 'Election' in df.columns:
                    df['Election'] = df['Election'].astype(str).str.strip()
                else:
                    logger.warning("'Election' column not found in file!")

                for ename, group in df.groupby('Election'):
                    clean_name = ename.strip()
                    logger.debug(f"Loading election '{clean_name}' with {len(group)} rows")
                    self._elections[clean_name] = group.copy()  # keep Election column

                self.rebuild_combined()
                logger.debug(f"Elections loaded into memory: {list(self._elections.keys())}")

            except Exception as e:
                logger.exception(f"Could not load {ELECTOR_FILE}: {e}")

    def rebuild_combined(self):
        if not self._elections:
            self._combined = pd.DataFrame()
            return

        combined = pd.concat(self._elections.values(), ignore_index=True)

        # Normalise once (key improvement)
        for col in ["PD", "WalkName", "Area", "StreetName"]:
            if col in combined.columns:
                combined[col] = combined[col].astype(str).str.strip().str.upper()

        self._combined = combined

    def get(self, election):
        # Your existing get method for accessing election data
        with _lock:
            result = self._elections.get(election)
            if result is None:
                return pd.DataFrame()  # Return empty DataFrame if election is not found
            return result.copy()

    @property
    def elections(self):
        """Read-only property for combined elections dictionary."""
        return self._elections

    # -------------------------------
    # Updated method ignoring election
    # -------------------------------

    def electors_for_node(self, nodelist=None, elections=None):
        """
        Return electors matching nodes and/or elections.

        Parameters:
            nodelist (Node or list[Node], optional): Node(s) to filter.
            elections (str or list[str], optional): Election name(s) to filter.

        Returns:
            pd.DataFrame: Matching electors. Returns all if both nodelist and elections are None.
        """
        with _lock:
            # If nothing is provided, return all electors
            if nodelist is None and elections is None:
                return self._combined.copy() if not self._combined.empty else pd.DataFrame()

            # Normalize nodelist to list
            if nodelist is not None and not isinstance(nodelist, list):
                nodelist = [nodelist]

            # Normalize elections to list
            if elections is None:
                election_list = list(self._elections.keys())
            elif isinstance(elections, str):
                election_list = [elections]
            else:
                election_list = elections

            shapecolumn = {
                "street": "StreetName",
                "walkleg": "StreetName",
                "polling_district": "PD",
                "walk": "WalkName",
                "ward": "Area",
                "division": "Area",
                "constituency": "Area",
                "nation": "Area",
                "country": "Election"
            }

            frames = []

            for ename in election_list:
                df = self._elections.get(ename)
                if df is None or df.empty:
                    continue

                # If no nodes, just append the full election dataframe
                if nodelist is None:
                    frames.append(df)
                    continue

                for node in nodelist:
                    col = shapecolumn.get(node.type)
                    if col is None or col not in df.columns:
                        print(f"⚠️ Unknown or missing column for node type: {node.type}")
                        continue

                    # Determine key: either node value or election
                    key = str(node.value).strip().upper() if getattr(node, "parent", None) else str(ename).upper()

                    matched = df[df[col].astype(str).str.strip().str.upper() == key]
                    if not matched.empty:
                        frames.append(matched)

            if frames:
                result = pd.concat(frames, ignore_index=True)
                print(f"[DEBUG] Total rows matched: {len(result)}")
                return result
            else:
                print("[DEBUG] No matching rows found")
                return pd.DataFrame()

    def add_or_update(self, election, df: pd.DataFrame):
        # Your existing method for adding or updating election data
        with _lock:
            if election in self._elections:
                self._elections[election] = pd.concat([self._elections[election], df], ignore_index=True)
            else:
                self._elections[election] = df.copy()
            self.rebuild_combined()
            self.save()


    def deactivate_election(self, election_name):
        """
        Deactivates (deletes) all rows associated with the given election.
        """
        with _lock:
            # Check if the election exists
            if election_name in self._elections:
                del self._elections[election_name]  # Remove the election from memory
                logger.debug(f"Election '{election_name}' has been deactivated and removed.")
                self.save()  # Save the changes (i.e., update the file)
                self.rebuild_combined()
            else:
                logger.warning(f"Attempted to deactivate non-existent election '{election_name}'.")

    def save(self):
        # Existing save method to write data to file
        with _lock:
            all_df = []
            for ename, df in self._elections.items():
                df_copy = df.copy()
                df_copy['Election'] = ename
                all_df.append(df_copy)
            if all_df:
                combined = pd.concat(all_df, ignore_index=True)
                combined.to_csv(ELECTOR_FILE, sep='\t', encoding='utf-8', index=False)



# Single instance
electors = ElectorManager()

# ✅ Now this works
print(electors._elections.keys())
print(len(electors.get("DORK1")))
