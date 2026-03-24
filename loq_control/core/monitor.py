"""
Monitor Module — Hardware telemetry for CPU, RAM, and GPU.
Defensive against missing dependencies.
"""

import subprocess
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None


def cpu_usage():
    if not psutil: return 10.0
    return psutil.cpu_percent()


def ram_usage():
    if not psutil: return 25.0
    return psutil.virtual_memory().percent


def battery_power():
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        for line in out.splitlines():
            if "power1:" in line:
                return float(line.split()[1])
    except:
        pass
    return 0


def gpu_usage():
    try:
        out = subprocess.check_output(
            "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits",
            shell=True
        ).decode().strip()
        return float(out)
    except:
        return 0


def gpu_temp():
    try:
        out = subprocess.check_output(
            "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits",
            shell=True
        ).decode().strip()
        return float(out)
    except:
        return 0


def gpu_clock():
    try:
        out = subprocess.check_output(
            "nvidia-smi --query-gpu=clocks.current.graphics --format=csv,noheader,nounits",
            shell=True
        ).decode().strip()
        return float(out)
    except:
        return 0


def cpu_wattage() -> float:
    """Fetch CPU package power via sensors (RAPL)."""
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        for line in out.splitlines():
            if "package id 0:" in line.lower() and "power" in line.lower():
                return float(line.split()[3])
    except:
        pass
    return 15.0  # safe fallback baseline


def battery_status() -> dict:
    """Fetch advanced battery metrics: discharge rate, percent, time left."""
    try:
        bat_root = Path("/sys/class/power_supply/BAT0")
        if not bat_root.exists(): return {}

        cap = int((bat_root / "capacity").read_text())
        is_charging = "Charging" in (bat_root / "status").read_text()

        power_now = int((bat_root / "power_now").read_text()) / 1_000_000   # W
        energy_now = int((bat_root / "energy_now").read_text()) / 1_000_000  # Wh

        time_left = 0
        if not is_charging and power_now > 0:
            time_left = (energy_now / power_now) * 60  # minutes

        return {
            "capacity": cap,
            "charging": is_charging,
            "power_draw": round(power_now, 2),
            "time_left": round(time_left),
        }
    except:
        return {}
