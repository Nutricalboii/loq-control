"""
hardware.py — thin wrappers that delegate to thermals.py (sysfs-based, no stderr noise).
"""

from loq_control.core.thermals import cpu_temp as _cpu_temp, ssd_temp as _ssd_temp


def battery_power() -> str:
    """Battery/charger power draw — delegated to monitor.py battery_power."""
    try:
        from loq_control.core.monitor import battery_power as _bp
        return str(round(_bp(), 1))
    except Exception:
        return "0"


def ssd_temp() -> str:
    """NVMe SSD temperature — uses sysfs via thermals.py (no sensors spam)."""
    try:
        t = _ssd_temp()
        return str(round(t, 1)) if t > 0 else "N/A"
    except Exception:
        return "N/A"
