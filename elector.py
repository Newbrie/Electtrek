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


def resolve_targets(df, uiScope, region_value, street, house):

    scope_col = shapecolumn.get(uiScope)

    if not scope_col:
        return df.iloc[0:0].index

    region_match = (
        df[scope_col]
        .astype(str)
        .apply(state.normalname)
        .str.upper()
        == state.normalname(region_value).upper()
    )

    street_match = (
        df['StreetName']
        .astype(str)
        .apply(state.normalname)
        .str.upper()
        == state.normalname(street).upper()
    )

    house_norm = state.normalname(str(house)).upper()

    house_num_match = (
        df['AddressNumber']
        .astype(str)
        .apply(state.normalname)
        .str.upper()
        == house_norm
    )

    house_name_match = (
        df['AddressPrefix']
        .astype(str)
        .apply(state.normalname)
        .str.upper()
        == house_norm
    )

    return df[
        region_match &
        street_match &
        (house_num_match | house_name_match)
    ].index

def apply_mutation(df, indexes, tags):
    for idx in indexes:

        existing_raw = str(df.at[idx, 'Tags']).strip()

        if existing_raw.lower() in ['nan', 'none', '', '0', '0.0']:
            existing = set()
        else:
            existing = {
                t.strip()
                for t in existing_raw.split(',')
                if t.strip()
            }

        for code, stateval in tags.items():

            if str(stateval).lower() == 'y':
                existing.add(code)

            elif code in existing:
                existing.remove(code)

        df.at[idx, 'Tags'] = ", ".join(sorted(existing))

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
        from baked_data import baked_data

        all_events = baked_data.load()

        if not all_events:
            return

        targets = (
            [specific_ename]
            if specific_ename and specific_ename in self._elections
            else self._elections.keys()
        )

        # --------------------------------
        # Helper: household tag mutation
        # --------------------------------
        def add_task_tag(df, indexes, code, enabled=True):

            if len(indexes) == 0 or not code:
                return

            # Canonical household elector
            idx = indexes[0]

            existing_raw = str(df.at[idx, 'Tags']).strip()

            if existing_raw.lower() in ['nan', 'none', '', '0', '0.0']:
                existing = set()
            else:
                existing = {
                    t.strip()
                    for t in existing_raw.split(',')
                    if t.strip()
                }

            if enabled:
                existing.add(code)
            else:
                existing.discard(code)

            df.at[idx, 'Tags'] = ", ".join(sorted(existing))

        # --------------------------------
        # Helper: household VI assignment
        # --------------------------------
        def add_household_vi(df, indexes, vi=None, votes=None):

            if len(indexes) == 0:
                return

            try:
                vote_count = int(votes or 0)
            except:
                vote_count = 0

            # Only apply to first N electors
            target_indexes = indexes[:vote_count]

            for idx in indexes:

                if idx in target_indexes:
                    if vi is not None:
                        df.at[idx, 'VI'] = vi
                else:
                    # Clear VI for remaining household electors
                    df.at[idx, 'VI'] = ''

            # Store household vote count on canonical elector
            df.at[indexes[0], 'Votes'] = str(vote_count)

        # --------------------------------
        # Replay events into each election
        # --------------------------------
        for ename in targets:

            df = self._elections[ename].copy()

            for ev in all_events:

                if not isinstance(ev, dict):
                    continue

                uiScope = ev.get('uiScope', 'walk')
                region = ev.get('region')
                street = ev.get('street')
                house = ev.get('house')

                if not all([region, street, house]):
                    continue

                indexes = resolve_targets(
                    df,
                    uiScope,
                    region,
                    street,
                    house
                )
                print(
                    "🔎 MATCH CHECK:",
                    {
                        "scope": uiScope,
                        "region": region,
                        "street": street,
                        "house": house,
                        "matches": len(indexes)
                    }
                )
                if len(indexes) == 0:
                    continue

                ev_type = ev.get('type')

                # -----------------------------
                # TAG EVENTS
                # -----------------------------
                if ev_type in ['tag', 'elector_tag']:

                    add_task_tag(
                        df,
                        indexes,
                        ev.get('code'),
                        ev.get('value') == 'y'
                    )

                # -----------------------------
                # VI EVENTS
                # -----------------------------
                elif ev_type == 'vi':

                    add_household_vi(
                        df,
                        indexes,
                        ev.get('value'),
                        ev.get('votes')
                    )

            # Replace projected election
            self._elections[ename] = df


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

    def add_household_vi(df, indexes, vi, votes):

        if len(indexes) == 0:
            return

        # Normalize vote count
        try:
            vote_count = int(votes or 0)
        except (TypeError, ValueError):
            vote_count = 0

        # Clamp to available electors
        vote_count = max(0, min(vote_count, len(indexes)))

        # ---------------------------------
        # Clear all existing household VI
        # ---------------------------------
        for idx in indexes:

            df.at[idx, 'VI'] = ''
            df.at[idx, 'Votes'] = str(vote_count)

        # ---------------------------------
        # Apply VI to first N electors
        # ---------------------------------
        for idx in indexes[:vote_count]:

            df.at[idx, 'VI'] = vi

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
