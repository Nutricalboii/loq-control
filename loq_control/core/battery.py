import os
from typing import Dict, Optional
from loq_control.core.priv_helper import run_privileged
from loq_control.core.logger import get_logger

log = get_logger("loq-control.battery")

# --- Standard Battery Paths ---
_BAT_PATH = "/sys/class/power_supply/BAT0"
_THRESHOLD_END_PATH = f"{_BAT_PATH}/charge_control_end_threshold"
_THRESHOLD_START_PATH = f"{_BAT_PATH}/charge_control_start_threshold"
_FAST_CHARGE_PATH = f"{_BAT_PATH}/fast_charge"
_IDEAPAD_FAST_CHARGE = "/sys/bus/platform/drivers/ideapad_laptop/ideapad/fast_charge"

# --- IdeaPad Specific (Legacy/VPC) Paths ---
_IDEAPAD_CONSERVATION = "/sys/bus/platform/drivers/ideapad_laptop/ideapad/conservation_mode"
# Fallback for some LOQ models where it's deeply nested
_VPC_CONSERVATION = "/sys/devices/pci0000:00/0000:00:1f.0/PNP0C09:00/VPC2004:00/conservation_mode"

def _get_conservation_path() -> Optional[str]:
    """Find the first available conservation mode file."""
    for p in [_THRESHOLD_END_PATH, _IDEAPAD_CONSERVATION, _VPC_CONSERVATION]:
        if os.path.exists(p):
            return p
    # Deep search if standard paths fail
    return None

def get_conservation_state() -> bool:
    """Return True if conservation mode is active."""
    path = _get_conservation_path()
    if not path:
        return False
    
    try:
        with open(path, "r") as f:
            val = int(f.read().strip())
            # For standard threshold: active if < 100
            # For ideapad/VPC: active if == 1
            if "conservation_mode" in path:
                return val == 1
            return val < 100
    except Exception:
        return False

def get_rapid_charge_state() -> bool:
    """Return True if rapid charging is active."""
    path = _FAST_CHARGE_PATH if os.path.exists(_FAST_CHARGE_PATH) else _IDEAPAD_FAST_CHARGE
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip() == "1"
    except Exception:
        pass
    return False

def get_start_threshold() -> int:
    if os.path.exists(_THRESHOLD_START_PATH):
        try:
            with open(_THRESHOLD_START_PATH, "r") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 0

def get_end_threshold() -> int:
    path = _get_conservation_path()
    if not path:
        return 100
    try:
        with open(path, "r") as f:
            val = int(f.read().strip())
            if "conservation_mode" in path:
                return 80 if val == 1 else 100
            return val
    except Exception:
        pass
    return 100

def set_conservation_mode(enabled: bool) -> bool:
    """Set conservation mode on/off."""
    path = _get_conservation_path()
    if not path:
        log.error("No conservation mode path found")
        return False
    
    # Determine target value based on path type
    if "conservation_mode" in path:
        target = "1" if enabled else "0"
    else:
        target = "80" if enabled else "100"
    
    cmd = ["sh", "-c", f"echo {target} > {path}"]
    return run_privileged(cmd)

def set_charge_thresholds(start: int, end: int) -> bool:
    """Set both start and end charge thresholds."""
    success = True
    if os.path.exists(_THRESHOLD_START_PATH):
        cmd_s = ["sh", "-c", f"echo {start} > {_THRESHOLD_START_PATH}"]
        if not run_privileged(cmd_s):
            success = False
            
    # For end threshold, use the generic set_conservation_mode logic if it's VPC
    path = _get_conservation_path()
    if path:
        if "conservation_mode" in path:
            target = "1" if end < 100 else "0"
        else:
            target = str(end)
        
        cmd_e = ["sh", "-c", f"echo {target} > {path}"]
        if not run_privileged(cmd_e):
            success = False
            
    return success

def set_rapid_charge(enabled: bool) -> bool:
    """Enable or disable rapid/fast charging."""
    val = "1" if enabled else "0"
    path = _FAST_CHARGE_PATH if os.path.exists(_FAST_CHARGE_PATH) else _IDEAPAD_FAST_CHARGE
    
    if not os.path.exists(path):
        return False
        
    cmd = ["sh", "-c", f"echo {val} > {path}"]
    return run_privileged(cmd)

def get_battery_info() -> Dict:
    """Read comprehensive battery telemetry."""
    info = {
        "level": 0,
        "status": "Unknown",
        "temp": 0.0,
        "power_now": 0.0,
        "cycle_count": 0,
    }
    
    try:
        if not os.path.exists(_BAT_PATH):
            return info
            
        def read_val(name, default=None):
            p = os.path.join(_BAT_PATH, name)
            if os.path.exists(p):
                with open(p, "r") as f:
                    return f.read().strip()
            return default

        lvl = read_val("capacity", "0")
        info["level"] = int(lvl) if lvl.isdigit() else 0
        info["status"] = read_val("status", "Unknown")
        
        raw_temp = read_val("temp", "0")
        info["temp"] = int(raw_temp) / 10.0 if raw_temp.isdigit() else 0.0
        
        raw_power = read_val("power_now", "0")
        info["power_now"] = int(raw_power) / 1_000_000.0 if raw_power.isdigit() else 0.0
        
        cycles = read_val("cycle_count", "0")
        info["cycle_count"] = int(cycles) if cycles.isdigit() else 0
        
    except (OSError, ValueError):
        pass
        
    return info
