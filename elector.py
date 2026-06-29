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
    "elector": "ElectorName",
    "street": "StreetName",
    "walkleg": "StreetName",
    "polling_district": "PD",
    "walk": "WalkName",
    "ward": "Ward",
    "division": "Division",
    "constituency": "Constituency",
    "county": "County",
    "nation": "Nation",
    "country": "Country"
}



def find_node_by_path(basepath: str, debug=False):
    from nodes import get_trek_root
    if debug:
        print(f"[DEBUG] find_node_by_path: {basepath}")

    if not basepath:
        return None

    parts = state.stepify(basepath)
    if not parts:
        return None

    root = get_trek_root()

    # Verify the root anchor matches
    if root.value != parts[0]:
        if debug:
            print(f"[DEBUG] Root mismatch: expected {root.value}, got {parts[0]}")
        return None

    # Walk directly down the tree branches
    node = root
    for part in parts[1:]:
        match = next((c for c in node.children if c.value == part), None)

        if not match:
            if debug:
                print(f"[DEBUG] Traversal broke at segment: '{part}' under node: '{node.value}'")
                # Diagnostic: What EXACTLY is inside node.children?
                print(f"[DEBUG] Raw target part bytes: {repr(part)}")
                print(f"[DEBUG] Available children details: {[(repr(c.value), c.type) for c in node.children]}")
            return None

        node = match

    return node

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

        # 🪐 FIX 1: Bypass Python's module reload engine completely.
        # Call the instance's built-in .load() method to pull fresh text straight from disk.
        try:
            all_events = baked_data.load()
        except Exception as e:
            print(f"⚠️ [INJECT] Failed to load baked data file from disk: {e}")
            return

        if not all_events:
            print("⚠️ [INJECT] No historical events returned from baked_data.load(). Skipping.")
            return

        print(f"📦 [DEBUG] Total fresh events loaded from baked_data: {len(all_events)}")

        # Isolate election targets
        targets = (
            [specific_ename]
            if specific_ename and specific_ename in self._elections
            else list(self._elections.keys())
        )

        print(f"🚀 [INJECT] Initializing event logs replay against targets: {targets}")

        for ename in targets:
            print(f"📂 [ELECTION METRIC PROCESSING]: Replaying events onto '{ename}'...")
            df = self._elections[ename].copy()
            print(f"📊 [DEBUG] DataFrame shape for '{ename}': {df.shape}")

            # ------------------------------------------------------------------
            # STEP 2: Build Context-Aware Coordinate Lookup Indices
            # ------------------------------------------------------------------
            walk_lookup = {}
            pd_lookup = {}

            # Populate Walk Lookup: (WalkName, StreetName, AddressPrefix/Number)
            if 'WalkName' in df.columns:
                zipped_walk = zip(df.index, df['WalkName'], df['StreetName'], df.get('AddressPrefix', df.get('AddressNumber', df.index)))
                # --- For Walk Lookup ---
                for idx, wk, st, hs in zipped_walk:
                    key = (
                        state.normalname(wk),
                        state.normalname(st),
                        state.normalname(hs)
                    )
                    if key not in walk_lookup:
                        walk_lookup[key] = []
                    walk_lookup[key].append(idx)

                print(f"🔍 [DEBUG] Built walk_lookup index with {len(walk_lookup)} unique location keys.")
            else:
                print("⚠️ [DEBUG WARNING] 'WalkName' column missing from DataFrame!")

            # Populate Polling District Lookup: (PD, StreetName, AddressPrefix/Number)
            if 'PD' in df.columns:
                zipped_pd = zip(df.index, df['PD'], df['StreetName'], df.get('AddressPrefix', df.get('AddressNumber', df.index)))
                # --- For PD Lookup ---
                for idx, pd_code, st, hs in zipped_pd:
                    key = (
                        state.normalname(pd_code),
                        state.normalname(st),
                        state.normalname(hs)
                    )
                    if key not in pd_lookup:
                        pd_lookup[key] = []
                    pd_lookup[key].append(idx)
                print(f"🔍 [DEBUG] Built pd_lookup index with {len(pd_lookup)} unique location keys.")
            else:
                print("⚠️ [DEBUG WARNING] 'PD' column missing from DataFrame!")

            # ------------------------------------------------------------------
            # STEP 3: Setup Local Mutation Dict Buffers
            # ------------------------------------------------------------------
            tags_dict = df['Tags'].astype(str).replace(['nan', 'None', '0', '0.0'], '').to_dict() if 'Tags' in df.columns else {}
            vi_dict = df['VI'].astype(str).replace(['nan', 'None'], '').to_dict() if 'VI' in df.columns else {}

            processed_count = 0
            matched_count = 0
            unmatched_samples = 0

            # ------------------------------------------------------------------
            # STEP 4: Run Ledger Replay Engine Loop
            # ------------------------------------------------------------------
            for ev in all_events:
                if not isinstance(ev, dict):
                    print(f"❌ [DEBUG] Event skipped - expected dict, got: {type(ev)}")
                    continue

                # 🪐 FIX 2: Check target assignment immediately inside the loop boundary!
                if 'election' in ev and str(ev.get('election')).strip() != ename:
                    continue

                processed_count += 1

                ui_scope = str(ev.get('uiScope', 'walk')).lower()

                # Case-normalized lookup key alignment matching step 2 entries
                event_key = (
                    str(ev.get('region')).strip().upper(),
                    str(ev.get('street')).strip().upper(),
                    str(ev.get('house')).strip().upper()
                )

                # Route dynamically based on log scope mapping layout
                if ui_scope == 'walk':
                    indexes = walk_lookup.get(event_key)
                elif ui_scope == 'polling_district':
                    indexes = pd_lookup.get(event_key)
                else:
                    indexes = walk_lookup.get(event_key) or pd_lookup.get(event_key)

                if not indexes:
                    if unmatched_samples < 5:
                        print(f"🕵️‍♂️ [DEBUG UNMATCHED] No DataFrame row index found for Event Key: {event_key} (uiScope: {ui_scope})")
                        unmatched_samples += 1
                    elif unmatched_samples == 5:
                        print("🕵️‍♂️ [DEBUG UNMATCHED] ... more unmatched rows found (suppressing further samples).")
                        unmatched_samples += 1
                    continue

                matched_count += 1
                ev_type = ev.get('type')

                # --- CASE A: TAG OPERATIONS ---
                if ev_type in ['tag', 'elector_tag']:
                    code = ev.get('code')
                    if not code:
                        continue

                    canonical_idx = indexes[0]
                    existing_raw = tags_dict.get(canonical_idx, '')
                    existing = {t.strip() for t in existing_raw.split(',') if t.strip()}

                    if ev.get('value') == 'y':
                        existing.add(code)
                    else:
                        existing.discard(code)

                    tags_dict[canonical_idx] = ", ".join(sorted(existing))

                # --- CASE B: VOTING INTENTION (VI) EVALUATIONS ---
                elif ev_type == 'vi':
                    try:
                        vote_count = int(ev.get('votes') or 0)
                    except (ValueError, TypeError):
                        vote_count = 0

                    vi_val = ev.get('vi') or ev.get('value') or ''
                    target_indexes = indexes[:vote_count]

                    for idx in target_indexes:
                        vi_dict[idx] = vi_val

            print(f"📈 [DEBUG SUMMARY] Processed {processed_count} dict events. Successfully matched keys to rows {matched_count} times.")

            # ------------------------------------------------------------------
            # STEP 5: Flush Mutation State Maps to DataFrame Storage Array
            # ------------------------------------------------------------------
            # 🪐 FIX 3: Converting maps cleanly to full Pandas Series indexes prevents
            # unmutated entries from being overwritten or dropped out with NaN elements.
            df['Tags'] = pd.Series(tags_dict, dtype=object)
            df['VI'] = pd.Series(vi_dict, dtype=object)

            self._elections[ename] = df
            print(f"💾 [SUCCESS] Replay completed for target ledger collection: '{ename}'")

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
        from elections import CurrentElection
        with _lock:
            assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

            # 1. Unpack election context key
            (c_election, elevels), = resolved_levels.items()

            df = self._elections.get(c_election)
            if df is None or df.empty:
                logger.error(f"❌ Election '{c_election}' NOT FOUND in memory.")
                return pd.DataFrame()

            # 2. 🌲 Find the target node using structural truth
            target_node = find_node_by_path(raw_path, debug=True)
            if not target_node:
                logger.error(f"❌ Failed to find matching node tree object for path: {raw_path}")
                return pd.DataFrame()

            logger.debug(f"🔍 START FILTER: Node={target_node.value} | Type={target_node.type} | Election={c_election}")

            # 3. Climb up the node's lineage to collect the exact column-to-value targets
            filter_targets = {}
            cur = target_node
            while cur:
                # Look up what column in the DataFrame corresponds to this node's type
                col = shapecolumn.get(cur.type)
                if col:
                    filter_targets[col] = cur.value
                cur = cur.parent

            # 4. Apply vector filtering across all matching layers instantly
            filtered_df = df.copy()
            for col, target_val in filter_targets.items():
                if col not in filtered_df.columns:
                    logger.warning(f"⚠️ Column '{col}' missing from DataFrame! Skipping field filter.")
                    continue

                # Vectorized clean match filter
                mask = filtered_df[col].astype(str).str.strip().str.upper() == target_val.upper()
                filtered_df = filtered_df[mask]

                if filtered_df.empty:
                    logger.error(f"❌ FILTER BREAK! Column: '{col}' | Target Value: '{target_val}' left 0 rows.")
                    return pd.DataFrame()

            logger.debug(f"🏁 FILTER COMPLETE: Found {len(filtered_df)} electors.")
            return filtered_df

    def delete_elector_for_path(self, resolved_levels, raw_path):
        from elections import CurrentElection
        """
        Deletes electors by intersecting levels Step 1 (Constituency) and below.
        Uses truth-source tree traversal to maintain safe schema index alignment.
        """
        with _lock:
            assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

            # Unpack election context key
            (c_election, elevels), = resolved_levels.items()

            # 1. Access the specific election data
            df = self._elections.get(c_election)
            if df is None or df.empty:
                logger.warning(f"No data found for election '{c_election}'")
                return 0

            # 2. 🌲 RESOLVE ACTUAL LEVELS VIA TREE TRAVERSAL
            # Avoids index shifting traps caused by folder structural names
            target_node = find_node_by_path(raw_path, debug=False)

            if not target_node:
                logger.error(f"❌ Failed to resolve actual tree hierarchy layout for deletion path: {raw_path}")
                return 0

            # 3. Get the clean steps
            parts = state.stepify(raw_path)
            if len(parts) < 2:
                logger.warning(f"Path too shallow for targeted deletion: {raw_path}")
                return 0

            original_len = len(df)

            # 4. Build the "Intersection Mask"
            path_mask = pd.Series([True] * len(df), index=df.index)

            for depth, value in enumerate(parts):
                # --- Skip Country Level ---
                if depth == 0:
                    continue

                # 🔄 Use actual_levels first, fallback to elevels if deep-nested indexing shifts
                node_type = actual_levels.get(depth, elevels.get(depth))
                if not node_type:
                    continue

                col = shapecolumn.get(node_type)
                if col and col in df.columns:
                    target_val = state.normalname(value)

                    # Boolean AND: narrowing the target area
                    level_match = df[col].astype(str).str.strip().str.upper() == target_val
                    path_mask = path_mask & level_match

            # 5. Execute Deletion
            # Check if we actually matched anything before dropping records
            if path_mask.any():
                # Keep only what is NOT matched by the inverted path_mask
                self._elections[c_election] = df[~path_mask].copy()
                deleted_count = original_len - len(self._elections[c_election])
            else:
                deleted_count = 0

            if deleted_count > 0:
                # 6. Housekeeping & State Persistence
                self.rebuild_combined()
                self.save()
                logger.info(f"Deleted {deleted_count} electors from '{c_election}' for path: {raw_path}")
            else:
                logger.debug(f"No electors found to delete for path: {raw_path}")

            return deleted_count

    @staticmethod
    def add_household_vi(df, indexes, vi, votes):
        """
        Updates the Voting Intention (VI) for an entire household.

        Args:
            df (pd.DataFrame): The DataFrame slice for the current election.
            indexes (list): List of DataFrame row indices belonging to this household.
            vi (str): The voting intention party code/value.
            votes (int or str): Number of electors in the house matching this intention.
        """
        if not indexes:
            return

        # 1. Cleanly parse the vote target count safely
        try:
            vote_count = int(votes or 0)
        except (ValueError, TypeError):
            vote_count = 0

        # 2. Slice the household array down to the intended target quota
        # (e.g., if votes=2, target the first two row indices found at this location)
        target_indexes = indexes[:vote_count]

        # 3. Update the DataFrame directly using .at or .loc for stability
        for idx in indexes:
            if idx in df.index:
                if idx in target_indexes:
                    df.at[idx, 'VI'] = str(vi)
                else:
                    # Clear out or reset remaining electors in the house who didn't match the count
                    df.at[idx, 'VI'] = ''

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
