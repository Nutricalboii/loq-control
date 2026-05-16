"""
Low-level GPU mode switching via prime-select.
All functions return True on success, False on failure.
"""

import subprocess
import shutil
from loq_control.core.priv_helper import run_privileged

def _nvidia_exists():
    return shutil.which("nvidia-smi") is not None

def _has_prime_select():
    return shutil.which("prime-select") is not None

def _has_envycontrol():
    return shutil.which("envycontrol") is not None

def get_current_mode() -> str:
    """Query the currently active graphics profile."""
    # 1. Try prime-select (Ubuntu/Debian)
    if _has_prime_select():
        try:
            out = subprocess.check_output(
                ["prime-select", "query"], stderr=subprocess.DEVNULL
            ).decode().strip().lower()
            if out in ("intel", "integrated"): return "integrated"
            if out in ("on-demand", "hybrid"): return "hybrid"
            if out == "nvidia": return "nvidia"
        except: pass

    # 2. Try envycontrol (Fedora/Arch/Universal)
    if _has_envycontrol():
        try:
            out = subprocess.check_output(
                ["envycontrol", "-q"], stderr=subprocess.DEVNULL
            ).decode().strip().lower()
            return out # integrated, hybrid, nvidia
        except: pass

    return "unknown"

def set_integrated() -> bool:
    """Switch to Integrated graphics."""
    if _has_envycontrol():
        path = shutil.which("envycontrol")
        return run_privileged([path, "-s", "integrated"])
    
    if _has_prime_select():
        path = shutil.which("prime-select")
        ok = run_privileged([path, "intel"])
        if not ok:
            ok = run_privileged([path, "integrated"])
        return ok
    
    return False

def set_hybrid() -> bool:
    """Switch to Hybrid graphics."""
    if _has_envycontrol():
        path = shutil.which("envycontrol")
        return run_privileged([path, "-s", "hybrid"])
    
    if _has_prime_select():
        path = shutil.which("prime-select")
        return run_privileged([path, "on-demand"])
    
    return False

def set_nvidia() -> bool:
    """Switch to NVIDIA-only graphics."""
    if not _nvidia_exists():
        return False
        
    if _has_envycontrol():
        path = shutil.which("envycontrol")
        return run_privileged([path, "-s", "nvidia"])
    
    if _has_prime_select():
        path = shutil.which("prime-select")
        return run_privileged([path, "nvidia"])
    
    return False
