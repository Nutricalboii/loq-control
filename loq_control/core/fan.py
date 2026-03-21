"""
Fan / platform profile control via ACPI platform_profile sysfs.
All functions return True on success, False on failure.
"""

import subprocess

_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"


def get_current_mode() -> str:
    """Read the active platform profile."""
    try:
        with open(_PROFILE_PATH, "r") as f:
            return f.read().strip()
    except (OSError, FileNotFoundError):
        return "unknown"


def quiet() -> bool:
    result = subprocess.run(
        f"echo low-power | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def balanced() -> bool:
    result = subprocess.run(
        f"echo balanced | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def performance() -> bool:
    result = subprocess.run(
        f"echo performance | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def custom() -> bool:
    result = subprocess.run(
        f"echo custom | sudo tee {_PROFILE_PATH}",
        shell=True, capture_output=True,
    )
    return result.returncode == 0


def set_manual_pwm(fan_id: int, percent: int) -> bool:
    """
    Abstractions for fine-grained PWM writes.
    Translates percentage (0-100) to actual EC register logic or hwmon standard.
    For Phase 3 framework building, this handles formatting the abstract payload.
    """
    from loq_control.core.logger import LoqLogger
    log = LoqLogger.get()

    percent = max(0, min(100, percent))
    pwm_val = int(255 * (percent / 100))
    
    # Safe stub: logs the target write dynamically prior to exact byte arrays
    # TODO: In future phases this invokes `ec_manager` ACPI byte streams.
    log.firmware("info", f"EC PWM STUB WRITE: Fan {fan_id} -> {percent}% ({pwm_val}/255)")
    return True

