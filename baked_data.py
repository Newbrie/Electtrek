from config import DATA_FILE
import os
import json

class BakedDataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename

        # 🪐 FIX 1: If the file is physically missing from disk, create an empty one immediately!
        if not os.path.exists(self.filename):
            print(f"📁 Data file missing. Initializing empty array at: {self.filename}")

            # Ensure folder paths exist first
            directory = os.path.dirname(os.path.abspath(self.filename))
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Write out a clean, empty initialization wrapper
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write("window.BAKED_DATA = [];")

        self._data = self.load()  # Load clean list into memory

    def get_scope_data(self, scope, region_id):
        # 🪐 FIX 2: Since self._data is a LIST, we filter it matching your dictionary lookups
        # Assuming your event objects look like: {"scope": "...", "region_id": "...", ...}
        results = []
        for event in self._data:
            if isinstance(event, dict):
                if event.get("scope") == scope and event.get("region_id") == region_id:
                    results.append(event)

        # Return matched data list or an empty fallback dict structure
        return results if results else {}

    def load(self):
        if not os.path.exists(self.filename):
            return []

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()

                if content.startswith("window.BAKED_DATA ="):
                    start = content.find('[')
                    end = content.rfind(';')

                    if end == -1:
                        end = len(content)

                    json_string = content[start:end]
                    data = json.loads(json_string)
                else:
                    data = json.loads(content)

                return data if isinstance(data, list) else []

        except Exception as e:
            print(f"⚠️ Could not parse {self.filename}: {e}")
            return []

    def save(self, incoming_payload):
        filepath = self.filename

        existing = self.load()
        if not isinstance(existing, list):
            existing = []

        events = incoming_payload.get("events", [])
        if not isinstance(events, list):
            events = []

        existing.extend(events)

        # Synchronize back to working list memory
        self._data = existing

        # Bake the JS file for the browser asset engine
        js_output = (
            "window.BAKED_DATA = "
            + json.dumps(existing, indent=4)
            + ";"
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(js_output)

        print(f"✅ Saved to disk & sync'd memory: Appended {len(events)} events (Total: {len(existing)})")

# Global instantiation utilized by routes and layout hooks
baked_data = BakedDataManager()
