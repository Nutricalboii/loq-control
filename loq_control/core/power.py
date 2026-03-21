"""
Power profile control via powerprofilesctl.
All functions return True on success, False on failure.
"""

import subprocess


def get_current_profile() -> str:
    """Query the active power profile."""
    try:
        out = subprocess.check_output(
            "powerprofilesctl get", shell=True, stderr=subprocess.DEVNULL
        ).decode().strip()
        return out
    except Exception:
        return "unknown"


def battery() -> bool:
    result = subprocess.run(
        "powerprofilesctl set power-saver", shell=True, capture_output=True
    )
    return result.returncode == 0


def balanced() -> bool:
    result = subprocess.run(
        "powerprofilesctl set balanced", shell=True, capture_output=True
    )
    return result.returncode == 0


def performance() -> bool:
    result = subprocess.run(
        "powerprofilesctl set performance", shell=True, capture_output=True
    )
    return result.returncode == 0
