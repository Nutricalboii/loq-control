"""
Fan / platform profile control via ACPI platform_profile sysfs.
All functions return True on success, False on failure.
"""

import subprocess

_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"


def get_current_mode() -> str:
    """Read the active platform profile."""
    try:
        with open(_PROFILE_PATH, "r") as f:
            return f.read().strip()
    except (OSError, FileNotFoundError):
        return "unknown"


def quiet() -> bool:
    result = subprocess.run(
        f"echo low-power | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def balanced() -> bool:
    result = subprocess.run(
        f"echo balanced | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def performance() -> bool:
    result = subprocess.run(
        f"echo performance | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def custom() -> bool:
    result = subprocess.run(
        f"echo custom | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0
