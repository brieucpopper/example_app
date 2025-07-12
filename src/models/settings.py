import os
import json

class Settings:
    def __init__(self):
        self.config_file = "storage/settings.json"
        self._load_settings()

    def _load_settings(self):
        os.makedirs("storage", exist_ok=True)
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                self.settings = json.load(f)
        else:
            self.settings = {"default_fps": 30.0}
            self._save_settings()

    def _save_settings(self):
        with open(self.config_file, "w") as f:
            json.dump(self.settings, f)

    def get_fps(self):
        return self.settings.get("default_fps", 30.0)

    def set_fps(self, value):
        self.settings["default_fps"] = value
        self._save_settings() 