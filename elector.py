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

# 🛠️ Centralized normalization helper function
def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Modifies the target structural columns of the dataframe in-place for high-speed indexing."""
    columns_to_norm = ["Country", "Nation", "County", "Constituency", "Ward", "Division", "PD", "WalkName", "StreetName"]
    for col in columns_to_norm:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

def find_node_by_path(basepath: str, debug=False):
    from nodes import get_trek_root
    import state

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
        logger.debug("Initializing ElectorManager")

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
                logger.debug(f"Elections loaded and baked: {list(self._elections.keys())}")

            except Exception as e:
                logger.exception(f"Could not load {ELECTOR_FILE}: {e}")

    def _inject_baked_data(self, specific_ename=None):
        from baked_data import baked_data

        try:
            all_events = baked_data.load()
        except Exception as e:
            print(f"⚠️ [INJECT] Failed to load baked data file from disk: {e}")
            return

        if not all_events:
            print("⚠️ [INJECT] No historical events returned from baked_data.load(). Skipping.")
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
            logger.debug("Refreshing baked data in memory...")
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
            clean_segments = [str(seg).strip().upper() for seg in state.stepify(raw_path)]
            logger.debug(f"🔍 START DETERMINISTIC FILTER: Path={clean_segments}")

            # 🛠️ Lightning fast vectorized index masking! No dynamic string formats.
            mask = pd.Series(True, index=df.index)

            # 1. Base geographic hierarchy (Levels 0-3)
            base_mappings = ["Country", "Nation", "County", "Constituency"]
            for idx, col_name in enumerate(base_mappings):
                if idx >= len(clean_segments):
                    break
                if col_name in df.columns:
                    mask &= (df[col_name] == clean_segments[idx])

            if not mask.any():
                logger.error("❌ Base geography filter left 0 rows. Path mismatch.")
                return pd.DataFrame()

            # Level 4: Ward vs Division
            if len(clean_segments) >= 5:
                target_ward_div = clean_segments[4]
                level_4_filtered = False

                if "Ward" in df.columns:
                    ward_mask = mask & (df["Ward"] == target_ward_div)
                    if ward_mask.any():
                        mask = ward_mask
                        level_4_filtered = True

                if not level_4_filtered and "Division" in df.columns:
                    div_mask = mask & (df["Division"] == target_ward_div)
                    if div_mask.any():
                        mask = div_mask

            # Level 5: Polling District / Walk Dynamic Fallback
            if len(clean_segments) >= 6:
                target_value = clean_segments[5]
                level_5_filtered = False

                if "PD" in df.columns:
                    pd_mask = mask & (df["PD"] == target_value)
                    if pd_mask.any():
                        mask = pd_mask
                        level_5_filtered = True

                if not level_5_filtered and "WalkName" in df.columns:
                    walk_mask = mask & (df["WalkName"] == target_value)
                    if walk_mask.any():
                        mask = walk_mask

            filtered_df = df[mask]
            if filtered_df.empty:
                logger.error("❌ Deep hierarchy filter broke. 0 rows returned.")
                return pd.DataFrame()

            logger.debug(f"🏁 FILTER COMPLETE: Found {len(filtered_df)} electors.")
            return filtered_df

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
                logger.debug(f"No electors found to delete for territory: {node_value}")

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
