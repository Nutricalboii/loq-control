"""
Low-level GPU mode switching via prime-select.
All functions return True on success, False on failure.
"""

import subprocess
import shutil


from loq_control.core.priv_helper import run_privileged

def _nvidia_exists():
    return shutil.which("nvidia-smi") is not None


def get_current_mode() -> str:
    """Query the currently active prime-select profile."""
    try:
        out = subprocess.check_output(
            ["prime-select", "query"], stderr=subprocess.DEVNULL
        ).decode().strip().lower()
        
        # Normalise prime-select output
        if out in ("intel", "integrated"):
            return "integrated"
        elif out in ("on-demand", "hybrid"):
            return "hybrid"
        elif out == "nvidia":
            return "nvidia"
    except Exception:
        pass
    return "unknown"


def set_integrated() -> bool:
    """Switch to Intel/Integrated graphics."""
    # Try 'intel' first, then fallback to 'integrated' (common in newer prime-select)
    ok = run_privileged(["prime-select", "intel"])
    if not ok:
        ok = run_privileged(["prime-select", "integrated"])
    return ok


def set_hybrid() -> bool:
    """Switch to Hybrid (On-demand) graphics."""
    return run_privileged(["prime-select", "on-demand"])


def set_nvidia() -> bool:
    """Switch to NVIDIA-only graphics."""
    if not _nvidia_exists():
        return False
    return run_privileged(["prime-select", "nvidia"])
