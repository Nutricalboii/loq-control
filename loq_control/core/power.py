"""
Power Profile Control
Priority:
  1. powerprofilesctl (D-Bus daemon — works WITHOUT root on Fedora/Ubuntu)
  2. sysfs direct write via pkexec (fallback for minimal distros)
"""

import shutil
import subprocess
from pathlib import Path

from loq_control.core.logger import get_logger
from loq_control.core.priv_helper import run_privileged

log = get_logger("loq-control.power")
ACPI_PROFILE = Path("/sys/firmware/acpi/platform_profile")

# Map our internal keys to powerprofilesctl profile names
_PPCTL_MAP = {
    "battery":     "power-saver",
    "balanced":    "balanced",
    "performance": "performance",
}

# Map internal keys to sysfs platform_profile choices (ordered by preference)
_SYSFS_MAP = {
    "battery":     ["low-power", "quiet", "power-saver"],
    "balanced":    ["balanced", "default", "middle"],
    "performance": ["max-power", "performance", "turbo", "high-performance"],
}


def get_current_profile() -> str:
    """Query the active power profile."""
    # Try powerprofilesctl first (most accurate)
    if shutil.which("powerprofilesctl"):
        try:
            out = subprocess.check_output(
                ["powerprofilesctl", "get"], stderr=subprocess.DEVNULL
            ).decode().strip()
            # Normalise powerprofilesctl output to our internal keys
            if out == "power-saver":
                return "power-saver"
            if out in ("balanced", "performance"):
                return out
        except Exception:
            pass

    # Sysfs fallback
    try:
        if ACPI_PROFILE.exists():
            val = ACPI_PROFILE.read_text().strip()
            if val == "low-power":
                return "power-saver"
            return val
    except Exception as e:
        log.error("Failed to read ACPI profile: %s", e)

    return "unknown"


def _set_profile(category: str) -> bool:
    """Apply power profile — tries powerprofilesctl first (no sudo needed)."""

    # 1. powerprofilesctl via D-Bus (NO root required on Fedora/Ubuntu)
    ppctl_target = _PPCTL_MAP.get(category)
    if ppctl_target and shutil.which("powerprofilesctl"):
        try:
            result = subprocess.run(
                ["powerprofilesctl", "set", ppctl_target],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                log.info("Power profile set via powerprofilesctl: %s", ppctl_target)
                return True
            log.error("powerprofilesctl failed (%d): %s",
                      result.returncode, result.stderr.decode().strip())
        except Exception as e:
            log.error("powerprofilesctl error: %s", e)

    # 2. Sysfs fallback via pkexec
    if not ACPI_PROFILE.exists():
        return False

    choices_path = Path("/sys/firmware/acpi/platform_profile_choices")
    try:
        choices = choices_path.read_text().split() if choices_path.exists() else []
    except Exception:
        choices = []

    target_hw = None
    for option in _SYSFS_MAP.get(category, []):
        if option in choices:
            target_hw = option
            break

    if target_hw:
        cmd = ["sh", "-c", f"echo {target_hw} > {ACPI_PROFILE}"]
        ok = run_privileged(cmd)
        if ok:
            log.info("Power profile set via sysfs: %s → %s", category, target_hw)
        return ok

    log.error("No hardware profile found for: %s", category)
    return False


def battery() -> bool:
    return _set_profile("battery")


def balanced() -> bool:
    return _set_profile("balanced")


def performance() -> bool:
    return _set_profile("performance")
