import json
import os
from pathlib import Path
from loq_control.core.logger import get_logger

log = get_logger("loq-control.settings")

DEFAULT_SETTINGS = {
    "theme": "dark",  # dark, light, system
    "first_run": True,
}

class GuiSettings:
    _instance = None
    
    def __init__(self):
        self.path = Path("~/.config/loq-control/gui_settings.json").expanduser()
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = GuiSettings()
        return cls._instance

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    self.settings.update(json.load(f))
            except Exception as e:
                log.error("Failed to load settings: %s", e)

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            log.error("Failed to save settings: %s", e)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def get_val(self, key):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))
