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

    def save(self, incoming_data):

        existing = self.load()

        for scope, regions in incoming_data.items():

            if not isinstance(regions, dict):
                continue

            existing.setdefault(scope, {})

            for region_id, streets in regions.items():

                if not isinstance(streets, dict):
                    continue

                existing[scope].setdefault(region_id, {})

                for street_id, street_obj in streets.items():

                    if not isinstance(street_obj, dict):
                        continue

                    existing[scope][region_id][street_id] = street_obj

        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("window.BAKED_DATA = ")
            json.dump(existing, f, indent=4)
            f.write(";")


# Usage in routes
baked_data = BakedDataManager()
