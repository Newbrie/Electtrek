import pandas as pd
import threading
import os
import logging
import state
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

shapecolumn = {
    "street": "StreetName",
    "walkleg": "StreetName",
    "polling_district": "PD",
    "walk": "WalkName",
    "ward": "Area",
    "division": "Area",
    "constituency": "Constituency",
    "county": "County",
    "nation": "Nation",
    "country": "Country"
}


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

    def elector_for_path(self, election_name, raw_path):
        from elections import CurrentElection
        from baked_data import baked_data

        with _lock:
            # 1. Access the specific election data
            df = self._elections.get(election_name)
            if df is None or df.empty:
                return pd.DataFrame()

            # 2. Get the clean steps
            parts = state.stepify(raw_path)

            # 3. Load mapping for this election
            CElection = CurrentElection.load(election_name)
            levels_map = CElection.resolved_levels

            filtered_df = df.copy()

            # 4. Filter DF level-by-level
            for depth, value in enumerate(parts):
                if depth == 0: continue
                node_type = levels_map.get(depth)
                col = shapecolumn.get(node_type)

                if col and col in filtered_df.columns:
                    target_val = str(value).strip().upper()
                    filtered_df = filtered_df[
                        filtered_df[col].astype(str).str.strip().str.upper() == target_val
                    ]
                    if filtered_df.empty:
                        return pd.DataFrame()

            # --- BAKED DATA INJECTION (Mirrors add_ghosts logic) ---
            if len(parts) >= 5:
                # In your system, WalkName is at index 4 (the 5th step)
                region_id = str(parts[4]).strip() # region_id in add_ghosts
                all_baked = baked_data.load()
                region_info = all_baked.get(region_id, {})

                if region_info:
                    def apply_baked_tags(row):
                        street_name = str(row.get('StreetName', '')).strip().upper()
                        house_num = str(row.get('AddressNumber', '')).strip()

                        # Get street data (e.g., QUEENS_ROAD)
                        street_data = region_info.get(street_name, {})

                        # Mirror add_ghosts: only look at u if it is a dict (a house)
                        # This skips 'street_weight' or other metadata
                        if isinstance(street_data, dict):
                            house_info = street_data.get(house_num, {})

                            if isinstance(house_info, dict):
                                tags_dict = house_info.get('tags', {})
                                # Extract all keys where status is 'y' (e.g., L1, L2)
                                active_codes = [
                                    code for code, status in tags_dict.items()
                                    if status == 'y'
                                ]

                                # Clean existing CSV tags
                                existing = str(row.get('Tags', '')).strip()
                                if existing.lower() in ['nan', 'none', '']:
                                    existing = ""

                                new_tag_str = ", ".join(active_codes)

                                if existing and new_tag_str:
                                    return f"{existing}, {new_tag_str}"
                                return new_tag_str or existing

                        return str(row.get('Tags', '')) if str(row.get('Tags', '')) != 'nan' else ""

                    filtered_df['Tags'] = filtered_df.apply(apply_baked_tags, axis=1)

            return filtered_df.copy()


    def delete_elector_for_path(self, election_name, raw_path):
        from elections import CurrentElection
        """
        Deletes electors by intersecting levels Step 1 (Constituency) and below.
        """
        with _lock:
            # 1. Access the specific election data
            df = self._elections.get(election_name)
            if df is None or df.empty:
                logger.warning(f"No data found for election '{election_name}'")
                return 0

            # 2. Get the clean steps
            parts = state.stepify(raw_path)
            if len(parts) < 2:
                logger.warning(f"Path too shallow for targeted deletion: {raw_path}")
                return 0

            # 3. Load mapping
            CElection = CurrentElection.load(election_name)
            levels_map = CElection.resolved_levels.get(election_name, {})
            original_len = len(df)

            # 4. Build the "Intersection Mask"
            # Start by selecting everything, then narrow it down
            path_mask = pd.Series([True] * len(df), index=df.index)

            for depth, value in enumerate(parts):
                # --- REFACTOR: Skip Country Level ---
                if depth == 0:
                    continue

                node_type = levels_map.get(depth)
                if not node_type:
                    continue

                col = shapecolumn.get(node_type)
                if col and col in df.columns:
                    target_val = str(value).strip().upper()

                    # Boolean AND: narrowing the target area
                    level_match = df[col].astype(str).str.strip().str.upper() == target_val
                    path_mask = path_mask & level_match

            # 5. Execute Deletion
            # Check if we actually matched anything before re-assigning
            if path_mask.any():
                # Keep only what is NOT in the path_mask
                self._elections[election_name] = df[~path_mask].copy()
                deleted_count = original_len - len(self._elections[election_name])
            else:
                deleted_count = 0

            if deleted_count > 0:
                # 6. Housekeeping
                self.rebuild_combined()
                self.save()
                logger.info(f"Deleted {deleted_count} electors from '{election_name}' for path: {raw_path}")
            else:
                logger.debug(f"No electors found to delete for path: {raw_path}")

            return deleted_count


    def add_or_update(self, election, df: pd.DataFrame):
        """
        Overwrites the current election data with the new provided DataFrame.
        This prevents duplicate rows from accumulating.
        """
        with _lock:
            # ✅ SWAP: Direct assignment replaces the old data with the new data
            self._elections[election] = df.copy()

            self.rebuild_combined()
            self.save()
            logger.info(f"Election '{election}' updated. Current count: {len(df)}")


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
