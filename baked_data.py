from config import DATA_FILE
import os
import json

class BakedDataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self._data = self.load()  # Load into memory immediately on boot

    def get_scope_data(self, scope, region_id):
        # This reads out of memory. If memory isn't updated by save(), this stays stale!
        return (
            self._data
            .get(scope, {})
            .get(region_id, {})
        )

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

        # 1. Load current physical disk state
        existing = self.load()
        if not isinstance(existing, list):
            existing = []

        # 2. Extract and append incoming canvassing data
        events = incoming_payload.get("events", [])
        if not isinstance(events, list):
            events = []

        existing.extend(events)

        # ------------------------------------------------------------------
        # 🪐 THE FIX: Synchronize both the disk file and the memory buffer!
        # ------------------------------------------------------------------
        # Step A: Update the backend's active working memory state tracker
        self._data = existing

        # Step B: Bake the JS file structure asset for the frontend browser UI
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
