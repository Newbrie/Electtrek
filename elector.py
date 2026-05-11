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
        self._elections = {}
        logger.debug("Initializing ElectorManager")

        if os.path.exists(ELECTOR_FILE):
            try:
                df = pd.read_csv(ELECTOR_FILE, sep='\t', encoding='utf-8')

                if 'Election' in df.columns:
                    df['Election'] = df['Election'].astype(str).str.strip()

                for ename, group in df.groupby('Election'):
                    self._elections[ename.strip()] = group.copy()

                # 1. Bake the progress tags into memory once
                self._inject_baked_data()

                # 2. Build the combined view
                self.rebuild_combined()
                logger.debug(f"Elections loaded and baked: {list(self._elections.keys())}")

            except Exception as e:
                logger.exception(f"Could not load {ELECTOR_FILE}: {e}")

    def _inject_baked_data(self, specific_ename=None):
        """
        Internal method to apply 'y' tags from baked_data to DataFrames.
        Targeted by specific_ename to avoid redundant full-dataset processing.
        """
        from baked_data import baked_data
        all_baked = baked_data.load()
        if not all_baked:
            return

        # 1. Decide which elections to process
        if specific_ename:
            targets = [specific_ename] if specific_ename in self._elections else []
        else:
            targets = self._elections.keys()

        for ename in targets:
            df = self._elections[ename]

            def apply_tags(row):
                # --- IDENTIFIERS ---
                # Match the 'walk_id' used in save()
                area_key = str(row.get('WalkName', '')).strip().upper()

                # Normalize and force UPPER to match JSON keys
                raw_street = row.get('StreetName', '')
                street = state.normalname(raw_street).upper() if raw_street else ""

                # --- NAVIGATION ---
                area_block = all_baked.get(area_key, {})
                street_block = area_block.get(street, {})

                # If street_block is not a dict (e.g., street_weight metadata), exit early
                if not isinstance(street_block, dict):
                    val = str(row.get('Tags', ''))
                    return val if val.lower() != 'nan' else ""

                # House identifiers
                house_num = str(row.get('AddressNumber', '')).strip().upper()
                house_name = state.normalname(row.get('AddressPrefix', '')).upper()

                house_info = None

                # ✅ 1. Try numeric match
                if house_num:
                    house_info = street_block.get(house_num)

                # ✅ 2. Try house name match
                if not house_info and house_name:
                    house_info = street_block.get(house_name)

                # ✅ 3. Fallback: Loose key search
                if not house_info:
                    for k, v in street_block.items():
                        if k == house_num or k == house_name:
                            house_info = v
                            break

                # No data found for this specific house
                if not house_info or not isinstance(house_info, dict):
                    val = str(row.get('Tags', ''))
                    return val if val.lower() != 'nan' else ""

                # --- TAG EXTRACTION & MERGING ---
                tags_dict = house_info.get('tags', {})
                active_codes = [c for c, s in tags_dict.items() if str(s).lower() == 'y']

                # Clean existing tags (handle 'nan', 'none', and numeric types)
                existing_raw = str(row.get('Tags', '')).strip()
                if existing_raw.lower() in ['nan', 'none', '', '0', '0.0']:
                    existing_tags = []
                else:
                    # split and strip to remove whitespace around commas
                    existing_tags = [t.strip() for t in existing_raw.split(',') if t.strip()]

                if active_codes:
                    # Use a set to prevent duplicate tags
                    merged_set = set(active_codes) | set(existing_tags)
                    return ", ".join(sorted(list(merged_set)))

                # If no 'y' tags found, return existing tags (cleaned)
                return ", ".join(existing_tags)

            # Apply changes back to the stored DataFrame
            self._elections[ename]['Tags'] = df.apply(apply_tags, axis=1)

    def refresh_baked_data(self):
        """Call this after a save to sync the in-memory electors with the disk."""
        with _lock:
            logger.debug("Refreshing baked data in memory...")
            self._inject_baked_data()
            self.rebuild_combined()

    def rebuild_combined(self):
        if not self._elections:
            self._combined = pd.DataFrame()
            return
        combined = pd.concat(self._elections.values(), ignore_index=True)
        for col in ["PD", "WalkName", "Area", "StreetName"]:
            if col in combined.columns:
                combined[col] = combined[col].astype(str).str.strip().str.upper()
        self._combined = combined

    def elector_for_path(self, resolved_levels, raw_path):
        with _lock:
            assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

            # The clean unpack you like
            (c_election, elevels), = resolved_levels.items()


            df = self._elections.get(c_election)
            if df is None or df.empty:
                logger.error(f"❌ Election '{c_election}' NOT FOUND in memory.")
                return pd.DataFrame()

            parts = state.stepify(raw_path)

            logger.debug(f"🔍 START FILTER: Path={parts} | Election={c_election}")

            filtered_df = df.copy()

            for depth, value in enumerate(parts):
                if depth == 0:
                    continue # Usually root/nation

                node_type = elevels[depth]
                col = shapecolumn.get(node_type)
                target_val = state.normalname(value)

                if not col:
                    logger.debug(f"   Step {depth}: No column mapping for type '{node_type}'. Skipping.")
                    continue

                if col not in filtered_df.columns:
                    logger.warning(f"   Step {depth}: Column '{col}' missing from DataFrame! (Type: {node_type})")
                    continue

                # --- The Decision Path Debug ---
                # Get unique values currently in the column to see what we are comparing against
                available_values = filtered_df[col].unique()[:5] # Show first 5 unique samples

                logger.debug(
                    f"   Step {depth} ({node_type}): Column='{col}' | Target='{target_val}'"
                )

                mask = filtered_df[col].astype(str).str.strip().str.upper() == target_val
                new_filtered = filtered_df[mask]

                if new_filtered.empty:
                    # Logic failure alert: Show exactly why the match failed
                    logger.error(
                        f"   ❌ FILTER BREAK at Step {depth} ({node_type})!\n"
                        f"      Column: '{col}'\n"
                        f"      Target Value: '{target_val}'\n"
                        f"      Sample Values in Column: {available_values}\n"
                        f"      Rows before: {len(filtered_df)} | Rows after: 0"
                    )
                    return pd.DataFrame()

                filtered_df = new_filtered
                logger.debug(f"   ✅ Match! Remaining rows: {len(filtered_df)}")

            logger.debug(f"🏁 FILTER COMPLETE: Found {len(filtered_df)} electors.")
            return filtered_df

    def delete_elector_for_path(self, resolved_levels, raw_path):
        from elections import CurrentElection
        """
        Deletes electors by intersecting levels Step 1 (Constituency) and below.
        """
        with _lock:
            assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

            # The clean unpack you like
            (c_election, elevels), = resolved_levels.items()

            # 1. Access the specific election data
            df = self._elections.get(c_election)
            if df is None or df.empty:
                logger.warning(f"No data found for election '{c_election}'")
                return 0

            # 2. Get the clean steps
            parts = state.stepify(raw_path)
            if len(parts) < 2:
                logger.warning(f"Path too shallow for targeted deletion: {raw_path}")
                return 0

            # 3. Load mapping

            original_len = len(df)

            # 4. Build the "Intersection Mask"
            # Start by selecting everything, then narrow it down
            path_mask = pd.Series([True] * len(df), index=df.index)

            for depth, value in enumerate(parts):
                # --- REFACTOR: Skip Country Level ---
                if depth == 0:
                    continue

                node_type = elevels.get(depth)
                if not node_type:
                    continue

                col = shapecolumn.get(node_type)
                if col and col in df.columns:
                    target_val = state.normalname(value)

                    # Boolean AND: narrowing the target area
                    level_match = df[col].astype(str).str.strip().str.upper() == target_val
                    path_mask = path_mask & level_match

            # 5. Execute Deletion
            # Check if we actually matched anything before re-assigning
            if path_mask.any():
                # Keep only what is NOT in the path_mask
                self._elections[c_election] = df[~path_mask].copy()
                deleted_count = original_len - len(self._elections[c_election])
            else:
                deleted_count = 0

            if deleted_count > 0:
                # 6. Housekeeping
                self.rebuild_combined()
                self.save()
                logger.info(f"Deleted {deleted_count} electors from '{c_election}' for path: {raw_path}")
            else:
                logger.debug(f"No electors found to delete for path: {raw_path}")

            return deleted_count


    def add_or_update(self, election, df: pd.DataFrame):
        with _lock:
            self._elections[election] = df.copy()
            # 🔑 Inject tags immediately into the new election data
            self._inject_baked_data(election)
            self.rebuild_combined()
            self.save()
            logger.info(f"Election '{election}' updated and baked.")

    def save(self):
        with _lock:
            all_df = []
            for ename, df in self._elections.items():
                df_copy = df.copy()
                df_copy['Election'] = ename
                all_df.append(df_copy)
            if all_df:
                combined = pd.concat(all_df, ignore_index=True)
                combined.to_csv(ELECTOR_FILE, sep='\t', encoding='utf-8', index=False)

    def get(self, election):
        with _lock:
            result = self._elections.get(election)
            return result.copy() if result is not None else pd.DataFrame()


    @property
    def elections(self):
        """Read-only property for combined elections dictionary."""
        return self._elections
# Single instance
electors = ElectorManager()
