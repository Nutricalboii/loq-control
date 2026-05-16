from pathlib import Path
from loq_control.core.logger import get_logger
from loq_control.core.priv_helper import run_privileged

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


def _set_profile(category: str) -> bool:
    """Apply power profile using powerprofilesctl or sysfs fallback."""
    # Mapping for powerprofilesctl
    daemon_map = {
        "battery": "power-saver",
        "balanced": "balanced",
        "performance": "performance"
    }
    
    target_daemon = daemon_map.get(category)
    
    # 1. Try powerprofilesctl (The standard for Fedora/modern Ubuntu)
    if shutil.which("powerprofilesctl"):
        cmd = ["powerprofilesctl", "set", target_daemon]
        # powerprofilesctl sometimes needs pkexec depending on policy
        success = run_privileged(cmd)
        if success:
            return True

    # 2. Sysfs Fallback (For minimal distros or if daemon fails)
    if not ACPI_PROFILE.exists():
        return False
        
    choices_path = Path("/sys/firmware/acpi/platform_profile_choices")
    choices = choices_path.read_text().split() if choices_path.exists() else []
    
    hw_mapping = {
        "battery": ["low-power", "quiet", "power-saver"],
        "balanced": ["balanced", "default", "middle"],
        "performance": ["max-power", "performance", "turbo", "high-performance"]
    }
    
    target_hw = None
    for option in hw_mapping.get(category, []):
        if option in choices:
            target_hw = option
            break
            
    if target_hw:
        cmd = ["sh", "-c", f"echo {target_hw} > {ACPI_PROFILE}"]
        return run_privileged(cmd)
        
    return False

import shutil # Ensure shutil is available

def battery() -> bool:
    return _set_profile("battery")

def balanced() -> bool:
    return _set_profile("balanced")

def performance() -> bool:
    return _set_profile("performance")
