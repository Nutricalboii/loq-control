"""
Persistent JSON configuration for LOQ Control.

Config file: ~/.config/loq-control/config.json
"""

import json
import os
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path.home() / ".config" / "loq-control"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

_DEFAULTS = {
    "default_gpu_mode": "hybrid",
    "default_power_profile": "balanced",
    "default_fan_mode": "balanced",
    "conservation_mode": False,
    "debounce_ms": 500,
    "event_poll_interval_s": 5,
    "log_level": "DEBUG",
}


class Config:
    """Simple JSON-backed config with defaults."""

    def __init__(self, path: Path | None = None):
        self._path = path or _CONFIG_FILE
        self._data: dict = {}
        self.load()

    def load(self):
        """Load config from disk, falling back to defaults."""
        self._data = dict(_DEFAULTS)
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    user = json.load(f)
                self._data.update(user)
            except (json.JSONDecodeError, OSError):
                pass  # corrupt file — use defaults

    def save(self):
        """Persist current config to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def as_dict(self) -> dict:
        return dict(self._data)
