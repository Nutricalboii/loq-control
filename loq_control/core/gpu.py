"""
Low-level GPU mode switching via prime-select.
All functions return True on success, False on failure.
"""

import subprocess
import shutil


def _nvidia_exists():
    return shutil.which("nvidia-smi") is not None


def get_current_mode() -> str:
    """Query the currently active prime-select profile."""
    try:
        out = subprocess.check_output(
            "prime-select query", shell=True, stderr=subprocess.DEVNULL
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
    result = subprocess.run(
        "sudo prime-select intel", shell=True, capture_output=True
    )
    return result.returncode == 0


def set_hybrid() -> bool:
    result = subprocess.run(
        "sudo prime-select on-demand", shell=True, capture_output=True
    )
    return result.returncode == 0


def set_nvidia() -> bool:
    if not _nvidia_exists():
        return False
    result = subprocess.run(
        "sudo prime-select nvidia", shell=True, capture_output=True
    )
    return result.returncode == 0
