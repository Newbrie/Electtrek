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

    def _inject_baked_data(self):
        """
        Internal method to apply 'y' tags from baked_data to DataFrames.
        Mirrors the 'ghost' logic for street_weight and dictionary checks.
        """
        from baked_data import baked_data
        all_baked = baked_data.load()
        if not all_baked:
            return

        for ename, df in self._elections.items():
            def apply_tags(row):
                # We use WalkName as the region/bucket ID
                region_id = str(row.get('WalkName', '')).strip()
                street_name = str(row.get('StreetName', '')).strip().upper()
                house_num = str(row.get('AddressNumber', '')).strip()

                region_info = all_baked.get(region_id, {})
                street_data = region_info.get(street_name, {})

                # Check if it's a house dict (skip metadata like street_weight)
                if isinstance(street_data, dict):
                    house_info = street_data.get(house_num, {})
                    if isinstance(house_info, dict):
                        tags_dict = house_info.get('tags', {})
                        # Find all 'y' status tags (L1, L2, etc.)
                        active_codes = [c for c, s in tags_dict.items() if s == 'y']

                        existing = str(row.get('Tags', '')).strip()
                        if existing.lower() in ['nan', 'none', '']: existing = ""

                        new_tag_str = ", ".join(active_codes)
                        if existing and new_tag_str:
                            return f"{existing}, {new_tag_str}"
                        return new_tag_str or existing

                # Return original if no baked match
                val = str(row.get('Tags', ''))
                return val if val.lower() != 'nan' else ""

            df['Tags'] = df.apply(apply_tags, axis=1)

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
                target_val = str(value).strip().upper()

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

    def add_or_update(self, election, df: pd.DataFrame):
        with _lock:
            self._elections[election] = df.copy()
            # 🔑 Inject tags immediately into the new election data
            self._inject_baked_data()
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

# Single instance
electors = ElectorManager()
