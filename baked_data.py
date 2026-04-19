from config import DATA_FILE
import os
import json

class BakedDataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return {}

    def save(self, data):
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=4)

# Usage in routes
baked_data = BakedDataManager()
