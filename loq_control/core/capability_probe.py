import os
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "loq-control"
CAP_FILE = CONFIG_DIR / "capabilities.json"


class CapabilityProbe:
    """
    Hardware capability discovery engine.

    Detects real kernel/sysfs/ACPI features and stores a cached capability map.
    Safe to run multiple times. Uses caching to avoid heavy probing on every boot.
    """

    _instance = None
    _lock = threading.Lock()

    CACHE_VALID_SECONDS = 3600 * 24  # 24 hours

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.capabilities = {}
        self.last_probe_time = 0

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = CapabilityProbe()
        return cls._instance

    # =========================
    # PUBLIC ENTRY POINT
    # =========================

    def load_or_probe(self, force=False):
        if CAP_FILE.exists() and not force:
            try:
                with open(CAP_FILE) as f:
                    data = json.load(f)
                    ts = data.get("_timestamp", 0)
                    if time.time() - ts < self.CACHE_VALID_SECONDS:
                        self.capabilities = data
                        return self.capabilities
            except Exception:
                pass

        return self.probe_all()

    def probe_all(self):
        caps = {}

        caps["gpu"] = self._probe_gpu()
        caps["power"] = self._probe_power()
        caps["thermal"] = self._probe_thermal()
        caps["battery"] = self._probe_battery()
        caps["vendor"] = self._probe_vendor_acpi()

        caps["_timestamp"] = int(time.time())

        self.capabilities = caps
        self._save()

        return caps

    # =========================
    # GPU CAPABILITIES
    # =========================

    def _probe_gpu(self):
        gpu = {}

        gpu["prime_select"] = shutil.which("prime-select") is not None
        gpu["nvidia_smi"] = shutil.which("nvidia-smi") is not None

        gpu["pci_runtime_pm"] = False
        for root, dirs, files in os.walk("/sys/bus/pci/devices"):
            if "power/control" in files:
                try:
                    with open(os.path.join(root, "vendor")) as f:
                        if "0x10de" in f.read():  # NVIDIA vendor ID
                            gpu["pci_runtime_pm"] = True
                except Exception:
                    pass

        gpu["mux_switch"] = os.path.exists(
            "/sys/kernel/debug/vgaswitcheroo/switch"
        )

        gpu["nvidia_power_limit"] = False
        if gpu["nvidia_smi"]:
            try:
                out = subprocess.run(
                    ["nvidia-smi", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if "Power Management" in out.stdout:
                    gpu["nvidia_power_limit"] = True
            except Exception:
                pass

        return gpu

    # =========================
    # POWER CAPABILITIES
    # =========================

    def _probe_power(self):
        power = {}

        power["platform_profile"] = os.path.exists(
            "/sys/firmware/acpi/platform_profile"
        )

        power["cpu_governor"] = os.path.exists(
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        )

        power["intel_pstate"] = os.path.exists(
            "/sys/devices/system/cpu/intel_pstate"
        )

        power["amd_pstate"] = os.path.exists(
            "/sys/devices/system/cpu/amd_pstate"
        )

        return power

    # =========================
    # THERMAL CAPABILITIES
    # =========================

    def _probe_thermal(self):
        thermal = {}

        thermal["zones"] = 0
        tz_base = Path("/sys/class/thermal")

        if tz_base.exists():
            for item in tz_base.iterdir():
                if "thermal_zone" in item.name:
                    thermal["zones"] += 1

        thermal["fan_pwm"] = False
        hwmon = Path("/sys/class/hwmon")
        if hwmon.exists():
            for chip in hwmon.iterdir():
                if (chip / "pwm1").exists():
                    thermal["fan_pwm"] = True

        thermal["fan_rpm"] = False
        if hwmon.exists():
            for chip in hwmon.iterdir():
                if (chip / "fan1_input").exists():
                    thermal["fan_rpm"] = True

        return thermal

    # =========================
    # BATTERY CAPABILITIES
    # =========================

    def _probe_battery(self):
        bat = {}

        bat["charge_threshold"] = False
        bat["charge_start_threshold"] = False
        bat["charge_end_threshold"] = False
        bat["rapid_charge"] = False
        
        base = Path("/sys/class/power_supply")

        if base.exists():
            for dev in base.iterdir():
                if "BAT" in dev.name:
                    if (dev / "charge_control_end_threshold").exists():
                        bat["charge_end_threshold"] = True
                        bat["charge_threshold"] = True
                    if (dev / "charge_control_start_threshold").exists():
                        bat["charge_start_threshold"] = True
                    
                    # Rapid Charge detection (Lenovo specific often via ideapad_laptop)
                    if (dev / "fast_charge").exists():
                        bat["rapid_charge"] = True

        # Fallback for Rapid Charge via ideapad_laptop
        if not bat["rapid_charge"]:
            if Path("/sys/bus/platform/drivers/ideapad_laptop/ideapad/fast_charge").exists():
                bat["rapid_charge"] = True

        # Conservation Mode (Legacy IdeaPad/VPC)
        bat["conservation_mode_v2"] = False
        vpc_path = "/sys/devices/pci0000:00/0000:00:1f.0/PNP0C09:00/VPC2004:00/conservation_mode"
        if os.path.exists(vpc_path) or os.path.exists("/sys/bus/platform/drivers/ideapad_laptop/ideapad/conservation_mode"):
            bat["conservation_mode_v2"] = True
            bat["charge_threshold"] = True
            bat["charge_end_threshold"] = True

        bat["power_now"] = False
        if base.exists():
            for dev in base.iterdir():
                if "BAT" in dev.name:
                    if (dev / "power_now").exists():
                        bat["power_now"] = True

        return bat

    # =========================
    # VENDOR ACPI CAPABILITIES
    # =========================

    def _probe_vendor_acpi(self):
        vendor = {}

        vendor["acpi_call"] = shutil.which("acpi_call") is not None

        vendor["ideapad_module"] = os.path.exists(
            "/sys/module/ideapad_laptop"
        )

        vendor["lenovo_wmi"] = os.path.exists(
            "/sys/module/lenovo_wmi"
        )

        vendor["wmi_bus"] = os.path.exists("/sys/bus/wmi")

        return vendor

    # =========================
    # SAVE
    # =========================

    def _save(self):
        try:
            with open(CAP_FILE, "w") as f:
                json.dump(self.capabilities, f, indent=4)
        except Exception:
            pass
