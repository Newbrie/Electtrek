from config import DATA_FILE
import os
import json

class BakedDataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename

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
        # 1. Merge logic (Note: use 'existing' to keep previous data!)
        existing = self.load()

        for walk_id, streets in incoming_data.items():
            if walk_id not in existing:
                existing[walk_id] = {}
            for street_id, houses in streets.items():
                if street_id not in existing[walk_id]:
                    existing[walk_id][street_id] = {}
                for house_id, details in houses.items():
                    existing[walk_id][street_id][house_id] = details

        # 2. Write as a JS file
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("window.BAKED_DATA = ")
            # Save 'existing' (the merged result), not just 'incoming_data'
            json.dump(existing, f, indent=4)
            f.write(";")


# Usage in routes
baked_data = BakedDataManager()
