"""
Battery conservation mode via charge_control_end_threshold sysfs.
All functions return True on success, False on failure.
"""

import subprocess

_THRESHOLD_PATH = "/sys/class/power_supply/BAT0/charge_control_end_threshold"


def get_conservation_state() -> bool:
    """Return True if conservation mode is active (threshold < 100)."""
    try:
        with open(_THRESHOLD_PATH, "r") as f:
            val = int(f.read().strip())
            return val < 100
    except (OSError, FileNotFoundError, ValueError):
        return False


def conservation_on() -> bool:
    result = subprocess.run(
        f"echo 80 | sudo tee {_THRESHOLD_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def conservation_off() -> bool:
    result = subprocess.run(
        f"echo 100 | sudo tee {_THRESHOLD_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0
