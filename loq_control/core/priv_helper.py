"""
Privilege Helper — Runs hardware commands as root using pkexec (PolicyKit).
No terminal needed. GUI-native password prompt appears automatically.

Usage:
    from loq_control.core.priv_helper import run_privileged
    ok = run_privileged(["prime-select", "nvidia"])
"""

import subprocess
import shutil
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()


def run_privileged(cmd: list[str]) -> bool:
    """
    Run a command with elevated privileges via pkexec.
    Shows a GUI password dialog — no terminal required.
    Returns True if the command succeeded.
    """
    if shutil.which("pkexec") is None:
        log.hardware("warning", "pkexec not found — falling back to subprocess (may fail)")
        return _run_direct(cmd)

    full_cmd = ["pkexec"] + cmd
    log.hardware("info", "Privilege escalation: %s", " ".join(full_cmd))
    try:
        result = subprocess.run(full_cmd, capture_output=True, timeout=30)
        if result.returncode == 0:
            return True
        log.hardware("error", "pkexec failed (%d): %s", result.returncode, result.stderr.decode())
        return False
    except subprocess.TimeoutExpired:
        log.hardware("error", "pkexec timed out for: %s", cmd)
        return False
    except Exception as e:
        log.hardware("error", "pkexec error: %s", e)
        return False


def _run_direct(cmd: list[str]) -> bool:
    """Fallback: run without root (will fail for /sys writes, non-fatal)."""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False
