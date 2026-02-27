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
        self._elections = {}  # now part of the instance
        logger.debug("Initializing ElectorManager")
        logger.debug(f"ELECTOR_FILE path: {os.path.abspath(ELECTOR_FILE)}")

        if os.path.exists(ELECTOR_FILE):
            logger.debug("Elector file exists. Attempting to load.")
            try:
                df = pd.read_csv(ELECTOR_FILE, sep='\t', encoding='utf-8')
                logger.debug(f"Loaded file with {len(df)} rows and columns {list(df.columns)}")

                if 'Election' in df.columns:
                    df['Election'] = df['Election'].astype(str).str.strip()  # strip whitespace
                else:
                    logger.warning("'Election' column not found in file!")

                for ename, group in df.groupby('Election'):
                    clean_name = ename.strip()
                    logger.debug(f"Loading election '{clean_name}' with {len(group)} rows")
                    self._elections[clean_name] = group.copy()  # keep Election column

                logger.debug(f"Elections loaded into memory: {list(self._elections.keys())}")

            except Exception as e:
                logger.exception(f"Could not load {ELECTOR_FILE}: {e}")

    def get(self, election):
        logger.debug(f"GET called for election '{election}'")
        with _lock:
            logger.debug(f"Available elections: {list(self._elections.keys())}")
            result = self._elections.get(election)

            if result is None:
                logger.debug(f"No data found for '{election}'. Returning empty DataFrame.")
                return pd.DataFrame()

            logger.debug(f"Returning {len(result)} rows for '{election}'")
            return result.copy()

    def add_or_update(self, election, df: pd.DataFrame):
        logger.debug(f"ADD_OR_UPDATE called for election '{election}'")
        logger.debug(f"Incoming DataFrame rows: {len(df)}")

        with _lock:
            if 'Election' in df.columns:
                df['Election'] = df['Election'].astype(str)

            if election in self._elections:
                logger.debug(f"Election '{election}' exists. Appending data.")
                self._elections[election] = pd.concat(
                    [self._elections[election], df],
                    ignore_index=True
                )
            else:
                logger.debug(f"Election '{election}' does not exist. Creating new entry.")
                self._elections[election] = df.copy()

            self._elections[election]['Election'] = election

            logger.debug(f"Election '{election}' now has {len(self._elections[election])} rows")
            logger.debug(f"Current elections in memory: {list(self._elections.keys())}")

            self.save()

    def save(self):
        logger.debug("SAVE called")

        with _lock:
            all_df = []

            for ename, df in self._elections.items():
                logger.debug(f"Preparing '{ename}' with {len(df)} rows for save")
                df_copy = df.copy()
                df_copy['Election'] = ename
                all_df.append(df_copy)

            if all_df:
                combined = pd.concat(all_df, ignore_index=True)
                logger.debug(f"Writing {len(combined)} total rows to disk")

                combined.to_csv(
                    ELECTOR_FILE,
                    sep='\t',
                    encoding='utf-8',
                    index=False
                )

                logger.debug("Save completed successfully")
            else:
                logger.debug("No data to save (store is empty)")




# Single instance
electors = ElectorManager()

# ✅ Now this works
print(electors._elections.keys())
print(len(electors.get("DORK1")))
