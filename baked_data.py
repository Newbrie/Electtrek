from config import DATA_FILE
import os
import json


class BakedDataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename

        # 🔍 AGGRESSIVE DEBUG STATEMENTS:
        print("\n🔎 [BAKED DATA DEBUG] Booting up Manager...")
        print(f"   -> Raw configured filename: '{self.filename}'")

        try:
            absolute_path = os.path.abspath(self.filename)
            print(f"   -> Absolute system path mapped to: '{absolute_path}'")

            file_exists = os.path.exists(absolute_path)
            print(f"   -> Does file physically exist right now? {file_exists}")

            if not file_exists:
                print("   💥 File is MISSING! Attempting to create it now...")

                # Check directory structure
                directory = os.path.dirname(absolute_path)
                print(f"   -> Target directory: '{directory}'")

                if directory and not os.path.exists(directory):
                    print(f"   📁 Folder structure missing. Creating directory path: '{directory}'")
                    os.makedirs(directory, exist_ok=True)

                # Force physical write
                with open(absolute_path, 'w', encoding='utf-8') as f:
                    f.write("window.BAKED_DATA = [];")

                # Re-verify immediately after write
                if os.path.exists(absolute_path):
                    print(f"   🎉 SUCCESS! File verified on disk at: '{absolute_path}'")
                else:
                    print("   ❌ FAIL: Write completed but file is still missing from disk check!")
            else:
                print("   ℹ️ Skipping creation: File already exists at this location.")

        except Exception as e:
            print(f"   🚨 CRITICAL INITIALIZATION ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

        print("[BAKED DATA DEBUG] Initialization pass complete.\n")
        self._data = self.load()

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
