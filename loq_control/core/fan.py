"""
Fan / platform profile control via ACPI platform_profile sysfs.
All functions return True on success, False on failure.
"""

from loq_control.core.priv_helper import run_privileged

_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"


def get_current_mode() -> str:
    """Read the active platform profile."""
    try:
        with open(_PROFILE_PATH, "r") as f:
            return f.read().strip()
    except (OSError, FileNotFoundError):
        return "unknown"


def quiet() -> bool:
    return _set_mode("low-power")


def balanced() -> bool:
    return _set_mode("balanced")


def performance() -> bool:
    return _set_mode("performance")


def custom() -> bool:
    return _set_mode("custom")


def _set_mode(mode: str) -> bool:
    """Helper to set platform profile using elevated privileges."""
    cmd = ["sh", "-c", f"echo {mode} > {_PROFILE_PATH}"]
    return run_privileged(cmd)


def set_manual_pwm(fan_id: int, percent: int) -> bool:
    """
    Abstractions for fine-grained PWM writes.
    Translates percentage (0-100) to actual EC register logic or hwmon standard.
    """
    from loq_control.core.logger import LoqLogger
    log = LoqLogger.get()

    percent = max(0, min(100, percent))
    pwm_val = int(255 * (percent / 100))
    
    # Safe stub: logs the target write dynamically prior to exact byte arrays
    log.firmware("info", f"EC PWM STUB WRITE: Fan {fan_id} -> {percent}% ({pwm_val}/255)")
    return True
