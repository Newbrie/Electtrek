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
        self._elections = {}  # Elections will be part of the instance
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

    def getstreamrag(self):
        """
        Get the stream processing status of elections using data from ElectorManager.
        """
        print("____getstreamrag entered")

        rag = {}

        # Fetch all current election instances from the ElectorManager class (self._elections)
        for election_name, electors_data in self._elections.items():
            print(f"Processing election: {election_name}")

            # Get stream processing data for the election from current election instance
            stream_processing = electors_data.get("stream_processing", {})
            files = stream_processing.get('files', [])

            # Initialize lists for active, deprecated, and deactivated streams
            active_streams = []
            deprecated_streams = []
            deactivated_streams = []

            if files:
                livestreamlabels = electors_data['Election'].unique()  # Elections that are live

                # Check for active, deprecated, and deactivated streams
                for file in files:
                    filename = file.get('file_path')
                    if filename in livestreamlabels:
                        active_streams.append(filename)
                    else:
                        deprecated_streams.append(filename)

                # Assign RAG status based on streams
                for election_name in active_streams:
                    rag[election_name] = {
                        'Alive': True,
                        'Elect': len(livestreamlabels),  # Or compute based on election data
                        'Files': ', '.join([file['file_path'] for file in files]),
                        'RAG': 'limegreen'
                    }
                for election_name in deprecated_streams:
                    rag[election_name] = {
                        'Alive': False,
                        'Elect': 0,
                        'Files': ', '.join([file['file_path'] for file in files]),
                        'RAG': 'red'
                    }
                for election_name in deactivated_streams:
                    rag[election_name] = {
                        'Alive': False,
                        'Elect': 0,
                        'Files': ', '.join([file['file_path'] for file in files]),
                        'RAG': 'amber'
                    }
            else:
                # Handle cases with no stream processing files
                rag[election_name] = {
                    'Alive': False,
                    'Elect': 0,
                    'Files': 0,
                    'RAG': 'white'
                }

        if not rag:
            rag['No Elections'] = {
                'Alive': False,
                'Elect': 0,
                'Files': 0,
                'RAG': 'white'
            }

        print("Final stream RAG status:", rag)
        return rag

    def get(self, election):
        # Your existing get method for accessing election data
        with _lock:
            result = self._elections.get(election)
            if result is None:
                return pd.DataFrame()  # Return empty DataFrame if election is not found
            return result.copy()

    def add_or_update(self, election, df: pd.DataFrame):
        # Your existing method for adding or updating election data
        with _lock:
            if election in self._elections:
                self._elections[election] = pd.concat([self._elections[election], df], ignore_index=True)
            else:
                self._elections[election] = df.copy()
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
