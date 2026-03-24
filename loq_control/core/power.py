"""
Power profile control via direct ACPI API.
Bypasses powerprofilesctl since power-profiles-daemon may be masked.
"""

from pathlib import Path
from loq_control.core.logger import get_logger

log = get_logger("loq-control.power")
ACPI_PROFILE = Path("/sys/firmware/acpi/platform_profile")

def get_current_profile() -> str:
    """Query the active power profile."""
    try:
        if ACPI_PROFILE.exists():
            val = ACPI_PROFILE.read_text().strip()
            # Map low-power to power-saver for UI consistency
            if val == "low-power": return "power-saver"
            return val
    except Exception as e:
        log.error("Failed to read ACPI profile: %s", e)
    return "unknown"


def _set_profile(profile: str) -> bool:
    try:
        if not ACPI_PROFILE.exists():
            log.error("ACPI platform_profile not found")
            return False
        ACPI_PROFILE.write_text(profile)
        return True
    except PermissionError:
        log.error("Permission denied writing to platform_profile")
        return False
    except Exception as e:
        log.error("Failed to set profile %s: %s", profile, e)
        return False


def battery() -> bool:
    return _set_profile("low-power")

def balanced() -> bool:
    return _set_profile("balanced")

def performance() -> bool:
    return _set_profile("performance")
