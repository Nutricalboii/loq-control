import json
import os
import subprocess
import shutil
from dataclasses import dataclass, asdict, field
from typing import List, Tuple, Optional

CONFIG_DIR = os.path.expanduser("~/.config/loq-control")
CUSTOM_PROFILE_PATH = os.path.join(CONFIG_DIR, "custom_profile.json")

GPU_PRESETS = {
    "RTX 3050 6GB":   {"ctgp_max": 80,  "ctgp_default": 70,  "boost_max": 15, "core_max": 300, "mem_max": 1000},
    "RTX 3050 4GB":   {"ctgp_max": 80,  "ctgp_default": 65,  "boost_max": 15, "core_max": 300, "mem_max": 1000},
    "RTX 4050":       {"ctgp_max": 115, "ctgp_default": 95,  "boost_max": 20, "core_max": 300, "mem_max": 1000},
    "RTX 4060":       {"ctgp_max": 115, "ctgp_default": 100, "boost_max": 25, "core_max": 300, "mem_max": 1000},
    "RTX 4070":       {"ctgp_max": 115, "ctgp_default": 105, "boost_max": 25, "core_max": 300, "mem_max": 1000},
    "RTX 2050":       {"ctgp_max": 60,  "ctgp_default": 50,  "boost_max": 10, "core_max": 200, "mem_max": 800},
    "MX570":          {"ctgp_max": 25,  "ctgp_default": 20,  "boost_max": 5,  "core_max": 150, "mem_max": 500},
    "Unknown":        {"ctgp_max": 80,  "ctgp_default": 60,  "boost_max": 15, "core_max": 200, "mem_max": 800},
}

CPU_PRESETS = {
    "i5-12450HX": {"pl1_default": 45, "pl1_max": 95,  "pl2_default": 95,  "pl2_max": 115, "tdp": 45},
    "i5-13420H":  {"pl1_default": 45, "pl1_max": 95,  "pl2_default": 95,  "pl2_max": 115, "tdp": 45},
    "i5-13450HX": {"pl1_default": 45, "pl1_max": 95,  "pl2_default": 95,  "pl2_max": 115, "tdp": 45},
    "i5-14450HX": {"pl1_default": 45, "pl1_max": 95,  "pl2_default": 95,  "pl2_max": 115, "tdp": 45},
    "i7-12650H":  {"pl1_default": 55, "pl1_max": 105, "pl2_default": 105, "pl2_max": 125, "tdp": 45},
    "i7-13650HX": {"pl1_default": 55, "pl1_max": 105, "pl2_default": 105, "pl2_max": 125, "tdp": 55},
    "i7-14650HX": {"pl1_default": 55, "pl1_max": 105, "pl2_default": 105, "pl2_max": 125, "tdp": 55},
    "Ryzen 5 7535HS":  {"pl1_default": 45, "pl1_max": 88,  "pl2_default": 88,  "pl2_max": 88,  "tdp": 45},
    "Ryzen 7 7435HS":  {"pl1_default": 45, "pl1_max": 88,  "pl2_default": 88,  "pl2_max": 88,  "tdp": 45},
    "Ryzen 5 8645HS":  {"pl1_default": 45, "pl1_max": 88,  "pl2_default": 88,  "pl2_max": 88,  "tdp": 45},
    "Ryzen 7 8845HS":  {"pl1_default": 54, "pl1_max": 88,  "pl2_default": 88,  "pl2_max": 88,  "tdp": 54},
    "Unknown":         {"pl1_default": 45, "pl1_max": 95,  "pl2_default": 95,  "pl2_max": 115, "tdp": 45},
}

DEFAULT_FAN_CURVE = [
    [30, 0],
    [40, 20],
    [50, 35],
    [60, 55],
    [70, 75],
    [80, 90],
    [90, 100],
]

PERFORMANCE_FAN_CURVE = [
    [30, 20],
    [40, 35],
    [50, 55],
    [60, 70],
    [70, 85],
    [80, 95],
    [90, 100],
]

SILENT_FAN_CURVE = [
    [30, 0],
    [40, 10],
    [50, 20],
    [60, 35],
    [70, 55],
    [80, 80],
    [90, 100],
]


@dataclass
class CustomProfileConfig:
    cpu_pl1_watts: int = 45
    cpu_pl2_watts: int = 95
    cpu_thermal_limit_c: int = 90
    gpu_ctgp_watts: int = 70
    gpu_dynamic_boost_watts: int = 15
    gpu_oc_enabled: bool = False
    gpu_core_offset_mhz: int = 0
    gpu_mem_offset_mhz: int = 0
    fan_curve: List[List[int]] = field(default_factory=lambda: [list(p) for p in DEFAULT_FAN_CURVE])
    detected_cpu: str = "Unknown"
    detected_gpu: str = "Unknown"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CUSTOM_PROFILE_PATH, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load(cls):
        if not os.path.exists(CUSTOM_PROFILE_PATH):
            cfg = cls()
            cfg.detected_cpu, cfg.detected_gpu = _detect_hardware()
            _apply_hardware_defaults(cfg)
            cfg.save()
            return cfg
        with open(CUSTOM_PROFILE_PATH, "r") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def reset_to_performance(cls):
        cfg = cls.load()
        cpu_preset = CPU_PRESETS.get(cfg.detected_cpu, CPU_PRESETS["Unknown"])
        gpu_preset = GPU_PRESETS.get(cfg.detected_gpu, GPU_PRESETS["Unknown"])
        cfg.cpu_pl1_watts = cpu_preset["pl1_max"]
        cfg.cpu_pl2_watts = cpu_preset["pl2_max"]
        cfg.cpu_thermal_limit_c = 95
        cfg.gpu_ctgp_watts = gpu_preset["ctgp_max"]
        cfg.gpu_dynamic_boost_watts = gpu_preset["boost_max"]
        cfg.fan_curve = [list(p) for p in PERFORMANCE_FAN_CURVE]
        return cfg

    @classmethod
    def reset_to_silent(cls):
        cfg = cls.load()
        cpu_preset = CPU_PRESETS.get(cfg.detected_cpu, CPU_PRESETS["Unknown"])
        gpu_preset = GPU_PRESETS.get(cfg.detected_gpu, GPU_PRESETS["Unknown"])
        cfg.cpu_pl1_watts = cpu_preset["pl1_default"]
        cfg.cpu_pl2_watts = cpu_preset["pl2_default"]
        cfg.cpu_thermal_limit_c = 85
        cfg.gpu_ctgp_watts = gpu_preset["ctgp_default"]
        cfg.gpu_dynamic_boost_watts = 5
        cfg.fan_curve = [list(p) for p in SILENT_FAN_CURVE]
        return cfg

    def get_cpu_preset(self):
        return CPU_PRESETS.get(self.detected_cpu, CPU_PRESETS["Unknown"])

    def get_gpu_preset(self):
        return GPU_PRESETS.get(self.detected_gpu, GPU_PRESETS["Unknown"])


def _detect_hardware():
    cpu = "Unknown"
    gpu = "Unknown"

    try:
        result = subprocess.run(
            ["cat", "/proc/cpuinfo"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            if "model name" in line.lower():
                raw = line.split(":")[1].strip()
                for key in CPU_PRESETS:
                    if key != "Unknown" and key.lower() in raw.lower():
                        cpu = key
                        break
                if cpu == "Unknown":
                    if "12450HX" in raw or "12450hx" in raw:
                        cpu = "i5-12450HX"
                break
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        raw_gpu = result.stdout.strip()
        for key in GPU_PRESETS:
            if key != "Unknown" and key.lower() in raw_gpu.lower():
                gpu = key
                break
        if gpu == "Unknown" and "3050" in raw_gpu and "6" in raw_gpu:
            gpu = "RTX 3050 6GB"
        elif gpu == "Unknown" and "3050" in raw_gpu:
            gpu = "RTX 3050 4GB"
    except Exception:
        pass

    return cpu, gpu


def _apply_hardware_defaults(cfg: CustomProfileConfig):
    cpu_preset = CPU_PRESETS.get(cfg.detected_cpu, CPU_PRESETS["Unknown"])
    gpu_preset = GPU_PRESETS.get(cfg.detected_gpu, GPU_PRESETS["Unknown"])
    cfg.cpu_pl1_watts = cpu_preset["pl1_default"]
    cfg.cpu_pl2_watts = cpu_preset["pl2_default"]
    cfg.gpu_ctgp_watts = gpu_preset["ctgp_default"]
    cfg.gpu_dynamic_boost_watts = gpu_preset["boost_max"]


class CustomProfileApplicator:

    RAPL_BASE = "/sys/class/powercap/intel-rapl/intel-rapl:0"
    BATTERY_PATH = "/sys/class/power_supply/AC/online"
    PLATFORM_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"

    def __init__(self, config: CustomProfileConfig):
        self.config = config

    def is_on_ac(self) -> bool:
        try:
            with open(self.BATTERY_PATH) as f:
                return f.read().strip() == "1"
        except Exception:
            return True

    def apply_all(self) -> dict:
        results = {}
        results["cpu_pl"] = self._apply_cpu_power_limits()
        results["cpu_thermal"] = self._apply_cpu_thermal_limit()
        results["gpu_power"] = self._apply_gpu_power_limit()
        results["fan_curve"] = self._apply_fan_curve()
        if self.config.gpu_oc_enabled:
            results["gpu_oc"] = self._apply_gpu_overclock()
        return results

    def _apply_cpu_power_limits(self) -> bool:
        pl1_uw = self.config.cpu_pl1_watts * 1_000_000
        pl2_uw = self.config.cpu_pl2_watts * 1_000_000
        try:
            pl1_path = os.path.join(self.RAPL_BASE, "constraint_0_power_limit_uw")
            pl2_path = os.path.join(self.RAPL_BASE, "constraint_1_power_limit_uw")
            with open(pl1_path, "w") as f:
                f.write(str(pl1_uw))
            with open(pl2_path, "w") as f:
                f.write(str(pl2_uw))
            return True
        except (PermissionError, FileNotFoundError):
            return self._apply_via_pkexec_write(
                pl1_path, str(pl1_uw),
                pl2_path, str(pl2_uw)
            )

    def _apply_cpu_thermal_limit(self) -> bool:
        try:
            result = subprocess.run(
                ["pkexec", "tee",
                 "/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq"],
                input="", capture_output=True, text=True, timeout=10
            )
            return True
        except Exception:
            return False

    def _apply_gpu_power_limit(self) -> bool:
        if not shutil.which("nvidia-smi"):
            return False
        try:
            subprocess.run(
                ["pkexec", "nvidia-smi", "-pl",
                 str(self.config.gpu_ctgp_watts)],
                capture_output=True, text=True, timeout=10
            )
            return True
        except Exception:
            return False

    def _apply_gpu_overclock(self) -> bool:
        if not shutil.which("nvidia-settings"):
            return False
        core = self.config.gpu_core_offset_mhz
        mem = self.config.gpu_mem_offset_mhz
        try:
            subprocess.run(
                ["nvidia-settings", "-a",
                 f"[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels={core}"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["nvidia-settings", "-a",
                 f"[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels={mem}"],
                capture_output=True, timeout=10
            )
            return True
        except Exception:
            return False

    def _apply_fan_curve(self) -> bool:
        legion_fan = "/sys/bus/platform/drivers/legion-laptop/PNP0C09:00/fan_curve"
        if os.path.exists(legion_fan):
            try:
                points = self.config.fan_curve
                curve_str = " ".join(f"{t}:{s}" for t, s in points)
                with open(legion_fan, "w") as f:
                    f.write(curve_str)
                return True
            except Exception:
                pass

        thinkpad_fan = "/sys/devices/platform/thinkpad_acpi/hwmon/hwmon*/fan1_min"
        import glob
        paths = glob.glob(thinkpad_fan)
        if paths:
            try:
                with open(paths[0], "w") as f:
                    f.write("1")
                return True
            except Exception:
                pass

        return False

    def _apply_via_pkexec_write(self, *path_value_pairs) -> bool:
        try:
            args = list(path_value_pairs)
            subprocess.run(
                ["pkexec", "python3", "-c",
                 f"open('{args[0]}','w').write('{args[1]}'); open('{args[2]}','w').write('{args[3]}')"],
                capture_output=True, timeout=10
            )
            return True
        except Exception:
            return False

    def reset_gpu_oc(self) -> bool:
        if not shutil.which("nvidia-settings"):
            return False
        try:
            subprocess.run(
                ["nvidia-settings", "-a",
                 "[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels=0"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["nvidia-settings", "-a",
                 "[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels=0"],
                capture_output=True, timeout=10
            )
            return True
        except Exception:
            return False
