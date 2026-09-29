import os
import logging
from pathlib import Path

import pandas as pd
import threading
import state
from config import ELECTOR_FILE, LOG_FILE


# ------------------------
# Logging Setup
# ------------------------
# Ensure parent directory exists before initializing FileHandler
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename=LOG_FILE,
    force=True  # 👈 Prevents Flask/libraries from ignoring this config
)

logger = logging.getLogger(__name__)

_lock = threading.RLock()

shapecolumn = {
    "elector": "ElectorName",
    "street": "StreetName",
    "polling_district": "PD",
    "walk": "WalkName",
    "ward": "Ward",
    "division": "Division",
    "constituency": "Constituency",
    "county": "County",
    "nation": "Nation",
    "country": "Country"
}

# 🛠️ Centralized normalization helper function
def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Modifies the target structural columns of the dataframe in-place for high-speed indexing."""
    columns_to_norm = ["Country", "Nation", "County", "Constituency", "Ward", "Division", "PD", "WalkName", "StreetName"]
    for col in columns_to_norm:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

def find_node_by_path(basepath: str, debug=False):
    import state
    from nodes import get_trek_root

    if debug:
        print(f"[DEBUG] find_node_by_path: {basepath}")

    if not basepath:
        return None

    parts = state.stepify(basepath)
    if not parts:
        return None

    root = get_trek_root()

    if root.value != parts[0]:
        if debug:
            print(f"[DEBUG] Root mismatch: expected {root.value}, got {parts[0]}")
        return None

    node = root
    for part in parts[1:]:
        cleaned_part = state.clean_path_part(part)

        if cleaned_part is None:
            continue

        if cleaned_part == node.value:
            continue

        match = next((c for c in node.children if c.value == cleaned_part), None)

        if not match:
            if debug:
                print(f"[DEBUG] Traversal broke at segment: '{cleaned_part}' (raw: '{part}') under node: '{node.value}'")
                print(f"[DEBUG] Raw target part bytes: {repr(part)}")
                print(f"[DEBUG] Available children details: {[(repr(c.value), c.type) for c in node.children]}")
            return None

        node = match

    return node

def resolve_targets(df, uiScope, region_value, street, house):
    scope_col = shapecolumn.get(uiScope)
    if not scope_col:
        return df.iloc[0:0].index

    # ✅ Super fast direct equality matches because everything is pre-normalized!
    region_match = df[scope_col] == state.normalname(region_value).upper()
    street_match = df['StreetName'] == state.normalname(street).upper()

    house_norm = state.normalname(str(house)).upper()
    house_num_match = df['AddressNumber'].astype(str).str.strip().str.upper() == house_norm if 'AddressNumber' in df.columns else pd.Series(False, index=df.index)
    house_name_match = df['AddressPrefix'].astype(str).str.strip().str.upper() == house_norm if 'AddressPrefix' in df.columns else pd.Series(False, index=df.index)

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
            existing = {t.strip() for t in existing_raw.split(',') if t.strip()}

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
        logger.info("Initializing ElectorManager")

        if os.path.exists(ELECTOR_FILE):
            try:
                df = pd.read_csv(ELECTOR_FILE, sep='\t', encoding='utf-8')

                if 'Election' in df.columns:
                    df['Election'] = df['Election'].astype(str).str.strip()

                for ename, group in df.groupby('Election'):
                    group_df = group.copy()

                    # 🚀 PRE-NORMALIZE HERE (On file initialization setup)
                    normalize_dataframe_columns(group_df)

                    self._elections[ename.strip()] = group_df

                # 1. Bake the progress tags into memory once
                self._inject_baked_data()

                # 2. Build the combined view
                self.rebuild_combined()
                logger.info(f"Elections loaded and baked: {list(self._elections.keys())}")

            except Exception as e:
                logger.exception(f"Could not load {ELECTOR_FILE}: {e}")

    def _inject_baked_data(self, specific_ename=None):
        from baked_data import baked_manager

        try:
            all_events = baked_manager.load()
        except Exception as e:
            print(f"⚠️ [INJECT] Failed to load baked data file from disk: {e}")
            return

        if not all_events:
            print("⚠️ [INJECT] No historical events returned from baked_manager.load(). Skipping.")
            return

        print(f"📦 [DEBUG] Total fresh events loaded from baked_data: {len(all_events)}")

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

            walk_lookup = {}
            pd_lookup = {}

            if 'WalkName' in df.columns:
                zipped_walk = zip(df.index, df['WalkName'], df['StreetName'], df.get('AddressPrefix', df.get('AddressNumber', df.index)))
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

            if 'PD' in df.columns:
                zipped_pd = zip(df.index, df['PD'], df['StreetName'], df.get('AddressPrefix', df.get('AddressNumber', df.index)))
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

            tags_dict = df['Tags'].astype(str).replace(['nan', 'None', '0', '0.0'], '').to_dict() if 'Tags' in df.columns else {}
            vi_dict = df['VI'].astype(str).replace(['nan', 'None'], '').to_dict() if 'VI' in df.columns else {}

            processed_count = 0
            matched_count = 0
            unmatched_samples = 0

            for ev in all_events:
                if not isinstance(ev, dict):
                    print(f"❌ [DEBUG] Event skipped - expected dict, got: {type(ev)}")
                    continue

                if 'election' in ev and str(ev.get('election')).strip() != ename:
                    continue

                processed_count += 1
                ui_scope = str(ev.get('uiScope', 'walk')).lower()

                event_key = (
                    str(ev.get('region')).strip().upper(),
                    str(ev.get('street')).strip().upper(),
                    str(ev.get('house')).strip().upper()
                )

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

            df['Tags'] = pd.Series(tags_dict, dtype=object)
            df['VI'] = pd.Series(vi_dict, dtype=object)

            self._elections[ename] = df
            print(f"💾 [SUCCESS] Replay completed for target ledger collection: '{ename}'")

    def refresh_baked_data(self):
        with _lock:
            logger.info("Refreshing baked data in memory...")
            self._inject_baked_data()
            self.rebuild_combined()

    def rebuild_combined(self):
        if not self._elections:
            self._combined = pd.DataFrame()
            return
        combined = pd.concat(self._elections.values(), ignore_index=True)

        # 🚀 PRE-NORMALIZE HERE (Ensures master compound dataframe matches indices perfectly)
        normalize_dataframe_columns(combined)

        self._combined = combined

    def elector_for_path(self, resolved_levels, raw_path):
        from elections import CurrentElection
        with _lock:
            assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

            (c_election, elevels), = resolved_levels.items()
            df = self._elections.get(c_election)
            if df is None or df.empty:
                logger.error(f"❌ Election '{c_election}' NOT FOUND in memory.")
                return pd.DataFrame()

            # Clean and upper-case segments to match the pre-normalized dataframe structure
            raw_segments = state.stepify(raw_path)
            clean_segments = [str(seg).strip().upper() for seg in raw_segments]
            logger.info(f"🔍 START DETERMINISTIC FILTER:")
            logger.info(f"   - Raw Path: {raw_path}")
            logger.info(f"   - Clean Segments ({len(clean_segments)}): {clean_segments}")
            logger.info(f"   - Resolved Levels Mapping: {resolved_levels}")
            logger.info(f"   - DataFrame Shape: {df.shape}")

            # 🛠️ Lightning fast vectorized index masking! No dynamic string formats.
            mask = pd.Series(True, index=df.index)
            initial_count = len(df)

            # Map standard field lookups dynamically from elevels dictionary and shapecolumn
            for idx, target_val in enumerate(clean_segments):
                if idx not in elevels:
                    logger.warning(f"⚠️ Index {idx} ('{target_val}') is out of range for resolved_levels mapping.")
                    break

                level_name = elevels[idx]
                sub_levels = [s.strip().lower() for s in level_name.split("/")]
                logger.debug(f"--------------------------------------------------")
                logger.debug(f"👉 Processing Index [{idx}] -> Segment Value: '{target_val}' (Level Type: '{level_name}')")

                level_matched = False
                for sub_level in sub_levels:
                    col_name = shapecolumn.get(sub_level)
                    logger.debug(f"   - Checking sub-level '{sub_level}' mapped to column '{col_name}'")

                    if col_name is None:
                        logger.debug(f"     ❌ No column mapping found in shapecolumn for sub_level '{sub_level}'")
                        continue

                    if col_name not in df.columns:
                        logger.debug(f"     ❌ Column '{col_name}' NOT found in DataFrame columns. Available columns: {list(df.columns)}")
                        continue

                    # Log unique values preview in this column to catch mismatch issues (e.g., spaces vs underscores)
                    sample_vals = df[col_name].dropna().astype(str).unique()[:5]
                    logger.debug(f"     ℹ️ Column '{col_name}' sample values in DF: {list(sample_vals)}")

                    sub_mask = mask & (df[col_name].astype(str).str.strip().str.upper() == target_val)
                    matched_count = sub_mask.sum()
                    logger.debug(f"     📊 Test match for '{target_val}' on '{col_name}': {matched_count} rows matched.")

                    if matched_count > 0:
                        mask = sub_mask
                        level_matched = True
                        logger.debug(f"     ✅ MATCH SUCCESSFUL at index {idx} using column '{col_name}'")
                        break

                if not level_matched:
                    parent_val = clean_segments[idx - 1] if idx - 1 >= 0 else "ROOT"
                    logger.warning(f"⚠️ Filter for level '{level_name}' (value '{target_val}') matched 0 electors under parent '{parent_val}'.")

            filtered_df = df[mask]
            final_count = len(filtered_df)
            logger.info(f"🏁 FILTER COMPLETE: Initial rows={initial_count} -> Final rows={final_count}")

            if final_count == 0:
                logger.error("❌ Deep hierarchy filter resulted in 0 rows returned.")
                return pd.DataFrame()

            if final_count == initial_count:
                logger.error("❌ Deep hierarchy filter left 100% of rows untouched (Filter did nothing!).")
                return pd.DataFrame()

            return filtered_df

    def delete_by_election(self, election_id: str) -> int:
        """Completely removes all elector records for a given election ID.

        Bypasses spatial hierarchy matching to prevent orphaned records or
        unmatched 'OUTSIDE' rows from lingering during deactivation.
        """
        with _lock:
            # 1. Normalize key representation if needed
            c_election = str(election_id).strip()

            # 2. Check if the election DataFrame exists
            if c_election not in self._elections:
                logger.warning(f"⚠️ Deactivate/Delete skipped: Election '{c_election}' not found in manager.")
                return 0

            df = self._elections[c_election]
            deleted_count = len(df) if df is not None else 0

            # 3. Purge the election dataset completely from memory
            del self._elections[c_election]

            # 4. Rebuild combined indices and persist state if records were purged
            if deleted_count > 0:
                self.rebuild_combined()
                self.save()
                logger.info(f"🗑️ Deactivated '{c_election}': Purged all {deleted_count} elector records.")
            else:
                logger.info(f"Deactivated '{c_election}': Election contained 0 records.")

            return deleted_count


    def delete_elector_for_path(self, resolved_levels, raw_path):
        from elections import CurrentElection
        import pandas as pd

        with _lock:
            assert len(resolved_levels) == 1, f"Expected 1 election, got {len(resolved_levels)}"

            (c_election, elevels), = resolved_levels.items()
            df = self._elections.get(c_election)
            if df is None or df.empty:
                logger.warning(f"No data found for election '{c_election}'")
                return 0

            target_node = find_node_by_path(raw_path, debug=False)
            if not target_node:
                logger.error(f"❌ Failed to resolve tree layout for deletion: {raw_path}")
                return 0

            node_type = target_node.type
            node_value = state.normalname(target_node.value).upper()

            col = shapecolumn.get(node_type)
            if not col or col not in df.columns:
                logger.warning(f"Spatial column for '{node_type}' not found.")
                return 0

            original_len = len(df)

            # ✅ Optimized direct match without inner loop casting overhead
            path_mask = df[col] == node_value

            if path_mask.any():
                self._elections[c_election] = df[~path_mask].copy()
                deleted_count = original_len - len(self._elections[c_election])
            else:
                deleted_count = 0

            if deleted_count > 0:
                self.rebuild_combined()
                self.save()
                logger.info(f"🗑️ Deleted {deleted_count} electors from '{c_election}' for territory: {node_value}")
            else:
                logger.info(f"No electors found to delete for territory: {node_value}")

            return deleted_count

    @staticmethod
    def add_household_vi(df, indexes, vi, votes):
        if not indexes:
            return

        try:
            vote_count = int(votes or 0)
        except (ValueError, TypeError):
            vote_count = 0

        target_indexes = indexes[:vote_count]

        for idx in indexes:
            if idx in df.index:
                if idx in target_indexes:
                    df.at[idx, 'VI'] = str(vi)
                else:
                    df.at[idx, 'VI'] = ''

    def add_or_update(self, election, df: pd.DataFrame):
        with _lock:
            df_copy = df.copy()

            # 🚀 PRE-NORMALIZE HERE (On hot API updates)
            normalize_dataframe_columns(df_copy)

            self._elections[election] = df_copy
            self._inject_baked_data(election)
            self.rebuild_combined()
            self.save()
            logger.info(f"Election '{election}' updated, normalized, and baked.")

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
        return self._elections

# Single instance
electors = ElectorManager()
