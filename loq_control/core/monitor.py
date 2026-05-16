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
        out = subprocess.check_output(
            ["sensors", "-j"], stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        import json
        data = json.loads(out)
        for chip, vals in data.items():
            if isinstance(vals, dict):
                for feat, fdata in vals.items():
                    if isinstance(fdata, dict):
                        for sub, v in fdata.items():
                            if "power" in sub.lower() and "input" in sub.lower():
                                return float(v)
    except Exception:
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
    """Fetch CPU package power via RAPL sysfs (no subprocess needed)."""
    try:
        import glob
        # Find intel-rapl package zone energy counter
        for path in glob.glob("/sys/class/powercap/intel-rapl:*/energy_uj"):
            if path.count(":") == 2:  # package zone only, not sub-zones
                import time
                e1 = int(Path(path).read_text())
                time.sleep(0.1)
                e2 = int(Path(path).read_text())
                return round((e2 - e1) / 1e5, 1)  # µJ/0.1s → W
    except Exception:
        pass
    return 15.0  # safe fallback baseline


def battery_status() -> dict:
    """Fetch advanced battery metrics: discharge rate, percent, time left."""
    try:
        bat_root = None
        for name in ("BAT0", "BAT1"):
            p = Path(f"/sys/class/power_supply/{name}")
            if p.exists():
                bat_root = p
                break
                
        if not bat_root: return {}

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
