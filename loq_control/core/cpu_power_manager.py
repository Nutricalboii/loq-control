import time
import threading
from pathlib import Path

from loq_control.core.state_manager import StateManager
from loq_control.core.capability_probe import CapabilityProbe
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()


class CPUPowerManager:
    """
    CPU Power Limit Framework

    Supports:
    - Intel RAPL PL1 / PL2 tuning
    - AMD P-State boost control (basic safe interface)
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.state = StateManager()
        self.caps = CapabilityProbe.get().load_or_probe()

        self.cpu_vendor = self._detect_vendor()
        self.rapl_path = self._detect_intel_rapl()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = CPUPowerManager()
        return cls._instance

    # --------------------------------------------------
    # Vendor Detection
    # --------------------------------------------------

    def _detect_vendor(self):
        try:
            text = Path("/proc/cpuinfo").read_text().lower()
            if "intel" in text:
                return "intel"
            if "amd" in text:
                return "amd"
        except Exception:
            pass
        return "unknown"

    # --------------------------------------------------
    # Intel RAPL Detection
    # --------------------------------------------------

    def _detect_intel_rapl(self):
        base = Path("/sys/class/powercap")
        if not base.exists():
            return None

        # Glob over potential powercaps. Note that intel-rapl could have children,
        # but typically the root domain is intel-rapl:0 or something analogous.
        for zone in base.glob("intel-rapl:*"):
            if ":" not in zone.name.split("intel-rapl:")[-1]:  # Get the package root, not subzones like core/uncore
                if (zone / "constraint_0_power_limit_uw").exists():
                    return zone
        return None

    # --------------------------------------------------
    # INTEL POWER LIMIT SET
    # --------------------------------------------------

    def set_intel_limits(self, pl1_watts: int, pl2_watts: int, source="gui"):
        if self.cpu_vendor != "intel":
            return False

        if not self.rapl_path:
            return False

        if not self.state.lock_transition(source):
            return False

        try:
            pl1 = self.rapl_path / "constraint_0_power_limit_uw"
            pl2 = self.rapl_path / "constraint_1_power_limit_uw"

            if pl1.exists():
                pl1.write_text(str(pl1_watts * 1_000_000))

            if pl2.exists():
                pl2.write_text(str(pl2_watts * 1_000_000))

            time.sleep(0.5)
            return True

        except Exception:
            return False

        finally:
            self.state.unlock_transition()

    # --------------------------------------------------
    # AMD BOOST CONTROL
    # --------------------------------------------------

    def set_amd_boost(self, enable: bool, source="gui"):
        if self.cpu_vendor != "amd":
            return False

        boost_file = Path(
            "/sys/devices/system/cpu/cpufreq/boost"
        )

        if not boost_file.exists():
            return False

        if not self.state.lock_transition(source):
            return False

        try:
            boost_file.write_text("1" if enable else "0")
            time.sleep(0.3)
            return True

        except Exception:
            return False

        finally:
            self.state.unlock_transition()

    # --------------------------------------------------
    # SAFE PRESETS
    # --------------------------------------------------

    def apply_profile(self, profile: str, source="gui"):
        """
        profile:
        - quiet
        - balanced
        - performance
        """
        log.cpu("info", f"Applying profile {profile} (vendor: {self.cpu_vendor})")

        if self.cpu_vendor == "intel":
            if profile == "quiet":
                return self.set_intel_limits(10, 25, source)

            if profile == "balanced":
                return self.set_intel_limits(25, 45, source)

            if profile == "performance":
                return self.set_intel_limits(45, 65, source)

        if self.cpu_vendor == "amd":
            if profile == "quiet":
                return self.set_amd_boost(False, source)

            if profile in ("balanced", "performance"):
                return self.set_amd_boost(True, source)

        return False
