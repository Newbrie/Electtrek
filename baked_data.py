from config import DATA_FILE
import os
import json

class BakedDataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self._data = self.load()  # Load into memory immediately

    def get_scope_data(self, scope, region_id):
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

    import json
    import os

    def save(self, incoming_payload):

        filepath = self.filename

        # --------------------------------
        # LOAD EXISTING EVENTS
        # --------------------------------
        existing = self.load()

        if not isinstance(existing, list):
            existing = []

        # --------------------------------
        # EXTRACT INCOMING EVENTS
        # --------------------------------
        events = incoming_payload.get("events", [])

        if not isinstance(events, list):
            events = []

        # --------------------------------
        # APPEND EVENTS
        # --------------------------------
        existing.extend(events)

        # --------------------------------
        # WRITE JS EVENT LOG
        # --------------------------------
        js_output = (
            "window.BAKED_DATA = "
            + json.dumps(existing, indent=4)
            + ";"
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(js_output)

        print(f"✅ Appended {len(events)} events")


# Usage in routes
baked_data = BakedDataManager()
