"""
Thermal sensors — uses sysfs/psutil primarily, sensors -j as fallback.
stderr from sensors is suppressed to avoid temp1_max_alarm spam.
"""

import subprocess
import json
from pathlib import Path

# ── sysfs fast paths ─────────────────────────────────────────────────────────

def _sysfs_cpu_temp() -> float:
    """Read CPU package temp from coretemp sysfs — zero-noise, no subprocess."""
    # Walk hwmon nodes looking for coretemp
    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            name = (hwmon / "name").read_text().strip()
            if "coretemp" in name:
                # temp1_input is usually the Package id 0
                t = (hwmon / "temp1_input").read_text().strip()
                return float(t) / 1000.0
        except (OSError, ValueError):
            continue
    return 0.0


def _sysfs_nvme_temp() -> float:
    """Read NVMe Composite temp from hwmon."""
    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            name = (hwmon / "name").read_text().strip()
            if "nvme" in name:
                t = (hwmon / "temp1_input").read_text().strip()
                return float(t) / 1000.0
        except (OSError, ValueError):
            continue
    return 0.0


# ── sensors JSON fallback (stderr silenced) ──────────────────────────────────

_sensors_cache: dict = {}
_sensors_cache_age: float = 0.0
_SENSORS_TTL = 2.0  # seconds between subprocess calls


def _sensors_json() -> dict:
    """Run 'sensors -j' once per TTL period, stderr suppressed."""
    import time
    global _sensors_cache, _sensors_cache_age
    now = time.monotonic()
    if now - _sensors_cache_age < _SENSORS_TTL:
        return _sensors_cache
    try:
        out = subprocess.check_output(
            ["sensors", "-j"],
            stderr=subprocess.DEVNULL,  # ← silences temp1_max_alarm spam
            timeout=2
        ).decode()
        _sensors_cache = json.loads(out)
        _sensors_cache_age = now
    except Exception:
        pass
    return _sensors_cache


# ── public API ────────────────────────────────────────────────────────────────

def cpu_temp() -> float:
    """CPU Package temperature in °C."""
    # Prefer sysfs (no subprocess, no stderr noise)
    t = _sysfs_cpu_temp()
    if t > 0:
        return t
    # Fallback: sensors JSON
    data = _sensors_json()
    try:
        return float(data["coretemp-isa-0000"]["Package id 0"]["temp1_input"])
    except (KeyError, TypeError, ValueError):
        pass
    return 0.0


def ssd_temp() -> float:
    """NVMe SSD Composite temperature in °C."""
    t = _sysfs_nvme_temp()
    if t > 0:
        return t
    # Fallback: sensors JSON
    data = _sensors_json()
    for chip, vals in data.items():
        if "nvme" in chip.lower():
            try:
                for feature, fdata in vals.items():
                    if isinstance(fdata, dict):
                        for sub, v in fdata.items():
                            if "temp" in sub and "input" in sub:
                                return float(v)
            except Exception:
                pass
    return 0.0
