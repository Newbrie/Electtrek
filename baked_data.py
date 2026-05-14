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
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                    # 1. Strip the JS prefix: "window.BAKED_DATA = "
                    if content.startswith("window.BAKED_DATA ="):
                        # Find the first '{' and the last ';'
                        start_index = content.find('{')
                        end_index = content.rfind(';')
                        if end_index == -1: end_index = len(content)

                        json_string = content[start_index:end_index]
                        data = json.loads(json_string)
                    else:
                        # Fallback in case the file is still raw JSON
                        data = json.loads(content)

                    return data if isinstance(data, dict) else {}
            except Exception as e:
                print(f"⚠️ Warning: Could not parse {self.filename}: {e}")
                return {}
        return {}

    import json
    import os

    def save(self, incoming_payload):
        filepath = "baked_data.json"

        # 1. Load existing file so we don't lose old data
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                try:
                    master_data = json.load(f)
                except json.JSONDecodeError:
                    master_data = {}
        else:
            master_data = {}

        # 2. Extract events and scope from the payload
        # Expected JS payload: { "scope": "walk", "events": [...] }
        events = incoming_payload.get('events', [])
        ui_scope = incoming_payload.get('scope', 'walk')

        if ui_scope not in master_data:
            master_data[ui_scope] = {}

        # 3. Process each event (The "Re-hydration" Step)
        # 3. Process each event (event replay engine)

        for ev in events:

            reg = ev.get('region')
            st = ev.get('street')
            hs = ev.get('house')

            if not all([reg, st, hs]):
                continue

            # -----------------------------
            # ENSURE STRUCTURE
            # -----------------------------
            if reg not in master_data[ui_scope]:
                master_data[ui_scope][reg] = {}

            if st not in master_data[ui_scope][reg]:
                master_data[ui_scope][reg][st] = {}

            if hs not in master_data[ui_scope][reg][st]:
                master_data[ui_scope][reg][st][hs] = {
                    "vi": "",
                    "votes": "0",
                    "tags": {},
                    "ts": None
                }

            house = master_data[ui_scope][reg][st][hs]

            house.setdefault("tags", {})

            # -----------------------------
            # EVENT TYPE ROUTING
            # -----------------------------
            ev_type = ev.get("type")

            # -----------------------------
            # TAG EVENTS
            # -----------------------------
            if ev_type in ["tag", "elector_tag"]:

                code = ev.get("code")
                value = ev.get("value", "n")

                if code:
                    house["tags"][code] = value

            # -----------------------------
            # VI EVENTS
            # -----------------------------
            elif ev_type == "vi":

                house["vi"] = ev.get("value", "")

            # -----------------------------
            # VOTE EVENTS
            # -----------------------------
            elif ev_type == "votes":

                house["votes"] = str(ev.get("value", "0"))

            # -----------------------------
            # TIMESTAMP
            # -----------------------------
            house["ts"] = ev.get("ts")

        # 4. Write the merged result back to disk
        with open(filepath, 'w') as f:
            json.dump(master_data, f, indent=4)

        print(f"✅ Successfully merged {len(events)} events into {filepath}")


# Usage in routes
baked_data = BakedDataManager()
