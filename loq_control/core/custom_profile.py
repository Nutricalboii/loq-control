"""
Custom Profile Engine — Purple Mode
Manages CPU PL1/PL2, GPU cTGP, and fan curve for Lenovo LOQ.

Hardware defaults tuned for i5-12450HX + RTX 3050 6GB.
Auto-detects other models via /proc/cpuinfo + nvidia-smi.
"""

import json
import shutil
import subprocess
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Tuple

from loq_control.core.logger import LoqLogger
from loq_control.core.priv_helper import run_privileged

log = LoqLogger.get()

CONFIG_PATH = Path.home() / ".config" / "loq-control" / "custom_profile.json"

# Fan curve: list of (temp_c, fan_pct) points
DEFAULT_FAN_CURVE: List[Tuple[int, int]] = [
    (30, 0), (40, 20), (50, 35), (60, 55), (70, 75), (80, 90), (90, 100)
]

# CPU presets: (pl1_watts, pl2_watts, thermal_limit_c)
CPU_PRESETS = {
    "i5-12450hx": (45, 95, 90),
    "i5-13450hx": (45, 95, 90),
    "i7-12650hx": (55, 110, 90),
    "i7-13650hx": (55, 110, 90),
    "i7-13700hx": (65, 120, 90),
    "ryzen 5 7535hs": (45, 88, 90),
    "ryzen 7 7745hx": (55, 110, 90),
    "ryzen 7 8845hs": (45, 88, 90),
    "default": (45, 95, 90),
}

# GPU presets: (ctgp_watts, dynamic_boost_watts)
GPU_PRESETS = {
    "rtx 3050": (70, 15),
    "rtx 3050 ti": (80, 15),
    "rtx 4050": (100, 20),
    "rtx 4060": (120, 25),
    "rtx 4070": (130, 25),
    "rtx 2050": (60, 10),
    "mx570": (25, 0),
    "default": (70, 15),
}

RAPL_BASE = Path("/sys/class/powercap")
ACPI_PROFILE = Path("/sys/firmware/acpi/platform_profile")


def _detect_cpu_preset() -> tuple:
    try:
        info = Path("/proc/cpuinfo").read_text().lower()
        for key, vals in CPU_PRESETS.items():
            if key in info:
                return vals
    except Exception:
        pass
    return CPU_PRESETS["default"]


def _detect_gpu_preset() -> tuple:
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode().strip().lower()
            for key, vals in GPU_PRESETS.items():
                if key in out:
                    return vals
        except Exception:
            pass
    return GPU_PRESETS["default"]


@dataclass
class CustomProfileConfig:
    cpu_pl1_watts: int = 45
    cpu_pl2_watts: int = 95
    cpu_thermal_limit_c: int = 90
    gpu_ctgp_watts: int = 70
    gpu_dynamic_boost_watts: int = 15
    gpu_core_offset_mhz: int = 100
    gpu_mem_offset_mhz: int = 200
    gpu_oc_enabled: bool = False
    fan_curve: List[List[int]] = field(default_factory=lambda: [list(p) for p in DEFAULT_FAN_CURVE])

    @classmethod
    def load(cls) -> "CustomProfileConfig":
        """Load from disk or create defaults based on detected hardware."""
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text())
                obj = cls(**data)
                return obj
            except Exception as e:
                log.firmware("warn", "Custom profile load failed, using defaults: %s", e)

        # Auto-detect hardware defaults
        pl1, pl2, thermal = _detect_cpu_preset()
        ctgp, dynboost = _detect_gpu_preset()
        return cls(
            cpu_pl1_watts=pl1,
            cpu_pl2_watts=pl2,
            cpu_thermal_limit_c=thermal,
            gpu_ctgp_watts=ctgp,
            gpu_dynamic_boost_watts=dynboost,
        )

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2))

    def reset_to_performance(self):
        pl1, pl2, thermal = _detect_cpu_preset()
        ctgp, dynboost = _detect_gpu_preset()
        self.cpu_pl1_watts = pl1
        self.cpu_pl2_watts = pl2
        self.cpu_thermal_limit_c = thermal
        self.gpu_ctgp_watts = ctgp
        self.gpu_dynamic_boost_watts = dynboost
        self.gpu_core_offset_mhz = 100
        self.gpu_mem_offset_mhz = 200
        self.gpu_oc_enabled = True
        self.fan_curve = [[30, 0], [40, 25], [50, 45], [60, 65], [70, 85], [80, 95], [90, 100]]

    def reset_to_silent(self):
        self.cpu_pl1_watts = 15
        self.cpu_pl2_watts = 35
        self.cpu_thermal_limit_c = 80
        self.gpu_ctgp_watts = 40
        self.gpu_dynamic_boost_watts = 0
        self.gpu_core_offset_mhz = 0
        self.gpu_mem_offset_mhz = 0
        self.gpu_oc_enabled = False
        self.fan_curve = [[30, 0], [40, 10], [50, 20], [60, 35], [70, 55], [80, 80], [90, 100]]


class CustomProfileApplicator:
    """Applies a CustomProfileConfig to the hardware."""

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> "CustomProfileApplicator":
        with cls._lock:
            if cls._instance is None:
                cls._instance = CustomProfileApplicator()
        return cls._instance

    def apply(self, cfg: CustomProfileConfig) -> bool:
        """Apply all settings. Returns True if at least CPU limits applied."""
        results = []
        results.append(self._apply_cpu_limits(cfg))
        self._apply_gpu_ctgp(cfg)
        if cfg.gpu_oc_enabled:
            self._apply_gpu_oc(cfg)
        self._apply_fan_curve(cfg)
        return any(results)

    def _find_rapl_path(self) -> Path | None:
        if not RAPL_BASE.exists():
            return None
        for zone in RAPL_BASE.glob("intel-rapl:*"):
            if ":" not in zone.name.split("intel-rapl:")[-1]:
                if (zone / "constraint_0_power_limit_uw").exists():
                    return zone
        return None

    def _apply_cpu_limits(self, cfg: CustomProfileConfig) -> bool:
        rapl = self._find_rapl_path()
        if not rapl:
            log.cpu("warn", "RAPL not available — skipping CPU PL1/PL2 write")
            return False
        try:
            pl1_path = rapl / "constraint_0_power_limit_uw"
            pl2_path = rapl / "constraint_1_power_limit_uw"
            pl1_uw = cfg.cpu_pl1_watts * 1_000_000
            pl2_uw = cfg.cpu_pl2_watts * 1_000_000

            cmd = ["sh", "-c",
                   f"echo {pl1_uw} > {pl1_path} && echo {pl2_uw} > {pl2_path}"]
            ok = run_privileged(cmd)
            if ok:
                log.cpu("info", "CPU PL1=%dW PL2=%dW applied", cfg.cpu_pl1_watts, cfg.cpu_pl2_watts)
            return ok
        except Exception as e:
            log.cpu("error", "CPU limit apply failed: %s", e)
            return False

    def _apply_gpu_ctgp(self, cfg: CustomProfileConfig):
        if not shutil.which("nvidia-smi"):
            return
        try:
            path = shutil.which("nvidia-smi")
            result = subprocess.run(
                [path, "-pl", str(cfg.gpu_ctgp_watts)],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                log.gpu("info", "GPU cTGP set to %dW", cfg.gpu_ctgp_watts)
            else:
                # needs root
                run_privileged([path, "-pl", str(cfg.gpu_ctgp_watts)])
        except Exception as e:
            log.gpu("warn", "GPU cTGP apply failed: %s", e)

    def _apply_gpu_oc(self, cfg: CustomProfileConfig):
        if not shutil.which("nvidia-settings"):
            return
        try:
            ns = shutil.which("nvidia-settings")
            core_arg = f"[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels={cfg.gpu_core_offset_mhz}"
            mem_arg = f"[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels={cfg.gpu_mem_offset_mhz}"
            subprocess.run([ns, "-a", core_arg], capture_output=True, timeout=5)
            subprocess.run([ns, "-a", mem_arg], capture_output=True, timeout=5)
            log.gpu("info", "GPU OC Core+%d Mem+%d applied",
                    cfg.gpu_core_offset_mhz, cfg.gpu_mem_offset_mhz)
        except Exception as e:
            log.gpu("warn", "GPU OC apply failed: %s", e)

    def _apply_fan_curve(self, cfg: CustomProfileConfig):
        """Write fan curve to platform_profile if custom is available, else best effort."""
        choices_path = Path("/sys/firmware/acpi/platform_profile_choices")
        try:
            choices = choices_path.read_text().split() if choices_path.exists() else []
            if "custom" in choices:
                cmd = ["sh", "-c", f"echo custom > {ACPI_PROFILE}"]
                run_privileged(cmd)
                log.firmware("info", "Fan curve: set platform_profile to custom")
            else:
                log.firmware("info", "Fan curve points stored; hardware custom mode unavailable")
        except Exception as e:
            log.firmware("warn", "Fan curve apply: %s", e)
