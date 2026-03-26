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
    """Best-effort match for a profile category and write it."""
    if not ACPI_PROFILE.exists():
        log.error("ACPI platform_profile not found")
        return False
        
    choices_path = Path("/sys/firmware/acpi/platform_profile_choices")
    choices = choices_path.read_text().split() if choices_path.exists() else []
    
    # Mapping table (Standardized -> Hardware Specific)
    mapping = {
        "battery": ["quiet", "low-power", "power-saver"],
        "balanced": ["balanced", "default", "middle"],
        "performance": ["performance", "turbo", "high-performance"]
    }
    
    target = None
    for option in mapping.get(category, []):
        if option in choices:
            target = option
            break
            
    if not target:
        # Fallback to the requested name itself if not in choices
        target = category
        
    cmd = ["sh", "-c", f"echo '{target}' > {ACPI_PROFILE}"]
    success = run_privileged(cmd)
    
    if not success:
        log.error("Failed to set profile %s (target: %s)", category, target)
    return success

def battery() -> bool:
    return _set_profile("battery")

def balanced() -> bool:
    return _set_profile("balanced")

def performance() -> bool:
    return _set_profile("performance")
