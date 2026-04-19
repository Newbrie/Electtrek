from config import DATA_FILE
import os
import json

class BakedDataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename

    def load(self):
            if os.path.exists(self.filename):
                try:
                    with open(self.filename, 'r') as f:
                        data = json.load(f)
                        # Optional: Ensure the result is actually a dict
                        return data if isinstance(data, dict) else {}
                except (json.JSONDecodeError, IOError):
                    # If the file is empty or mangled, return empty dict
                    # so the app doesn't crash on startup
                    print(f"⚠️ Warning: {self.filename} was empty or corrupted. Starting fresh.")
                    return {}
            return {}

    def save(self, incoming_data):
        existing = self.load() # Load existing baked_data.json

        for walk_id, streets in incoming_data.items():
            if walk_id not in existing:
                existing[walk_id] = {}

            for street_id, houses in streets.items():
                if street_id not in existing[walk_id]:
                    existing[walk_id][street_id] = {}

                for house_id, details in houses.items():
                    # Update specific house details only
                    existing[walk_id][street_id][house_id] = details

        with open(self.filename, 'w') as f:
            json.dump(existing, f, indent=4)

# Usage in routes
baked_data = BakedDataManager()
