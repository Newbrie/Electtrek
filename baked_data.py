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
        print("\n--- 💾 BACKEND SAVE START ---")
        existing = self.load()

        # DEBUG: Show us the top-level keys coming from the browser
        print(f"DEBUG: Incoming top-level keys: {list(incoming_data.keys())}")

        for walk_id, streets in incoming_data.items():
            print(f"  📂 Processing Walk: '{walk_id}'")

            # If the JS is flat, 'streets' will actually be house data (not a dict)
            if not isinstance(streets, dict):
                print(f"  ⚠️ ERROR: Expected a dictionary of streets for '{walk_id}', but got: {type(streets)}")
                continue

            if walk_id not in existing:
                print(f"    🆕 Creating new Walk drawer for: {walk_id}")
                existing[walk_id] = {}

            for street_id, houses in streets.items():
                print(f"    🛣️  Processing Street: '{street_id}'")

                if street_id not in existing[walk_id]:
                    print(f"      🆕 Creating new Street folder for: {street_id}")
                    existing[walk_id][street_id] = {}

                for house_id, details in houses.items():
                    print(f"      🏠 Saving House: {house_id} -> {details.get('vi', '?')}")
                    # Update specific house details
                    existing[walk_id][street_id][house_id] = details

        print("--- ✅ BACKEND SAVE COMPLETE ---\n")

        with open(self.filename, 'w') as f:
            json.dump(existing, f, indent=4)

# Usage in routes
baked_data = BakedDataManager()
