"""
Hardware Service — the single privileged executor for all hardware writes.

Every hardware change flows through here:
    GUI / Daemon / CLI  →  HardwareService  →  core/*.py

Implements the Transition Framework:
    1. Lock state
    2. Block daemon
    3. Execute hardware write
    4. Verify result
    5. Update state
    6. Unlock
"""

import threading
import time
from dataclasses import dataclass
from typing import Optional

from loq_control.core.state_manager import StateManager
from loq_control.core.logger import LoqLogger
from loq_control.core.cpu_power_manager import CPUPowerManager
from loq_control.core import gpu, power, fan, battery

log = LoqLogger.get()


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class HWResult:
    """Outcome of a hardware operation."""
    success: bool
    message: str
    needs_reboot: bool = False


# ---------------------------------------------------------------------------
# GPU mode ↔ module.function mapping (late-binding for testability)
# ---------------------------------------------------------------------------

_GPU_WRITERS = {
    "integrated": ("gpu", "set_integrated"),
    "hybrid": ("gpu", "set_hybrid"),
    "nvidia": ("gpu", "set_nvidia"),
}

_POWER_WRITERS = {
    "power-saver": ("power", "battery"),
    "balanced": ("power", "balanced"),
    "performance": ("power", "performance"),
}

_FAN_WRITERS = {
    "quiet": ("fan", "quiet"),
    "balanced": ("fan", "balanced"),
    "performance": ("fan", "performance"),
    "custom": ("fan", "custom"),
}

# Module references for late-binding lookups
_MODULES = {"gpu": gpu, "power": power, "fan": fan, "battery": battery}


def _call_hw(mapping: dict, key: str) -> bool:
    """Look up and call a hardware function by name (late-binding)."""
    mod_name, func_name = mapping[key]
    func = getattr(_MODULES[mod_name], func_name)
    return func()



# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class HardwareService:
    """Thread-safe privileged executor for hardware state changes."""

    _instance: Optional["HardwareService"] = None
    _init_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, state: Optional[StateManager] = None):
        if hasattr(self, "_initialised"):
            return
        self._initialised = True
        self._state = state or StateManager()

    @classmethod
    def reset(cls):
        """Destroy the singleton (for tests)."""
        with cls._init_lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Helper: Lock with Retry
    # ------------------------------------------------------------------

    def _lock_with_retry(self, source: str, timeout: float = 3.0) -> bool:
        """Retry locking the transition state for up to 'timeout' seconds."""
        iterations = int(timeout / 0.2)
        for _ in range(iterations):
            if self._state.lock_transition(source):
                return True
            time.sleep(0.2)
        return False

    # ------------------------------------------------------------------
    # Initialise state from actual hardware
    # ------------------------------------------------------------------

    def sync_state_from_hardware(self):
        """Read real hardware and seed the StateManager with ground truth."""
        gm = gpu.get_current_mode()
        if gm != "unknown":
            self._state.force_set("gpu_mode", gm)

        pp = power.get_current_profile()
        if pp in ("power-saver", "balanced", "performance"):
            self._state.force_set("power_profile", pp)

        fm = fan.get_current_mode()
        if fm in ("low-power", "quiet", "balanced", "performance", "custom"):
            normalised = "quiet" if fm == "low-power" else fm
            self._state.force_set("fan_mode", normalised)

        cm = battery.get_conservation_state()
        self._state.force_set("conservation_mode", cm)

        log.hardware("info", "State synced from hardware: %s", self._state.get_state())

    # ------------------------------------------------------------------
    # GPU
    # ------------------------------------------------------------------

    def switch_gpu(self, mode: str, source: str = "gui") -> HWResult:
        """Switch GPU mode with full transition framework."""
        if mode not in _GPU_WRITERS:
            return HWResult(False, f"Invalid GPU mode: {mode}")

        if self._state.get("gpu_mode") == mode:
            log.hardware("info", "[%s] GPU already in %s mode", source, mode)
            return HWResult(True, f"Already in {mode} mode", needs_reboot=False)

        if not self._lock_with_retry(source):
            return HWResult(False, "Another transition in progress (system is busy, please wait)")

        try:
            if source in ("gui", "cli"):
                self._state.set_manual_override()

            log.hardware("info", "[%s] GPU switch → %s", source, mode)
            ok = _call_hw(_GPU_WRITERS, mode)

            if not ok:
                log.hardware("error", "[%s] GPU switch to '%s' FAILED", source, mode)
                return HWResult(False, f"prime-select failed for '{mode}'")

            self._state.force_set("gpu_mode", mode)
            return HWResult(True, f"GPU → {mode}", needs_reboot=True)

        except Exception as e:
            log.hardware("error", "[%s] GPU switch CRASHED: %s", source, e)
            return HWResult(False, f"Internal error during GPU switch: {e}")
        finally:
            self._state.unlock_transition()

    # ------------------------------------------------------------------
    # Power profile
    # ------------------------------------------------------------------

    def set_power_profile(self, profile: str, source: str = "gui") -> HWResult:
        if profile not in _POWER_WRITERS:
            return HWResult(False, f"Invalid power profile: {profile}")

        if self._state.get("power_profile") == profile:
            log.hardware("info", "[%s] Power profile already %s", source, profile)
            return HWResult(True, f"Already in {profile}", needs_reboot=False)

        if not self._lock_with_retry(source):
            return HWResult(False, "Another transition in progress (system is busy, please wait)")

        try:
            if source in ("gui", "cli"):
                self._state.set_manual_override()

            log.hardware("info", "[%s] Power profile → %s", source, profile)

            # Apply CPU Limits first
            cpu_prof = "quiet" if profile == "power-saver" else profile
            CPUPowerManager.get().apply_profile(cpu_prof, source)

            # Then ACPI power profile script
            ok = _call_hw(_POWER_WRITERS, profile)
            if not ok:
                log.hardware("error", "[%s] Power profile '%s' FAILED", source, profile)
                return HWResult(False, f"powerprofilesctl failed for '{profile}'")

            self._state.force_set("power_profile", profile)
            return HWResult(True, f"Power → {profile}")

        except Exception as e:
            log.hardware("error", "[%s] Power profile CRASHED: %s", source, e)
            return HWResult(False, f"Internal error during power switch: {e}")
        finally:
            self._state.unlock_transition()

    # ------------------------------------------------------------------
    # Fan mode
    # ------------------------------------------------------------------

    def set_fan_mode(self, mode: str, source: str = "gui") -> HWResult:
        if mode not in _FAN_WRITERS:
            return HWResult(False, f"Invalid fan mode: {mode}")

        if not self._lock_with_retry(source):
            return HWResult(False, "Another transition in progress (system is busy, please wait)")

        try:
            log.hardware("info", "[%s] Fan mode → %s", source, mode)
            ok = _call_hw(_FAN_WRITERS, mode)
            if not ok:
                log.hardware("error", "[%s] Fan mode '%s' FAILED", source, mode)
                return HWResult(False, f"Platform profile write failed for '{mode}'")

            self._state.force_set("fan_mode", mode)
            return HWResult(True, f"Fan → {mode}")

        except Exception as e:
            log.hardware("error", "[%s] Fan mode CRASHED: %s", source, e)
            return HWResult(False, f"Internal error during fan switch: {e}")
        finally:
            self._state.unlock_transition()

    # ------------------------------------------------------------------
    # Battery conservation
    # ------------------------------------------------------------------

    def set_conservation(self, enabled: bool, source: str = "gui") -> HWResult:
        if not self._lock_with_retry(source):
            return HWResult(False, "Another transition in progress (system is busy, please wait)")

        try:
            log.hardware("info", "[%s] Conservation mode → %s", source, enabled)
            ok = battery.set_conservation_mode(enabled)
            if not ok:
                return HWResult(False, "Failed to set conservation mode")
                
            self._state.force_set("conservation_mode", enabled)
            return HWResult(True, f"Conservation → {'ON' if enabled else 'OFF'}")
        except Exception as e:
            return HWResult(False, f"Internal error during conservation switch: {e}")
        finally:
            self._state.unlock_transition()

    def set_smart_fan(self, active: bool, source: str = "gui") -> HWResult:
        """Toggle the adaptive smart fan (PolicyEngine)."""
        if not self._lock_with_retry(source):
            return HWResult(False, "Another transition in progress (system is busy, please wait)")

        try:
            log.hardware("info", "[%s] Smart Fan (Adaptive) → %s", source, active)
            if active and source in ("gui", "cli"):
                self._state.clear_manual_override()
                
            self._state.force_set("smart_fan_active", active)
            return HWResult(True, f"Smart Fan {'Enabled' if active else 'Disabled'}")
        except Exception as e:
            log.hardware("error", "[%s] Smart Fan toggle FAILED: %s", source, e)
            return HWResult(False, f"Internal error during smart fan toggle: {e}")
        finally:
            self._state.unlock_transition()

    # ------------------------------------------------------------------
    # Presets (compound operations)
    # ------------------------------------------------------------------

    def apply_preset(self, preset: str, source: str = "gui") -> HWResult:
        """Apply a named preset (battery / balanced / gaming / overclock / smart-fan)."""
        presets = {
            "battery": ("power-saver", "quiet", False),
            "balanced": ("balanced", "balanced", False),
            "gaming": ("performance", "performance", False),
            "overclock": ("performance", "custom", False),
            "smart-fan": ("balanced", "balanced", True),
        }
        if preset not in presets:
            return HWResult(False, f"Unknown preset: {preset}")

        profile, fan_mode, smart_active = presets[preset]

        # 1. Handle Smart Fan state
        r0 = self.set_smart_fan(smart_active, source)
        if not r0.success:
            return r0

        # 2. Handle Power profile
        r1 = self.set_power_profile(profile, source)
        if not r1.success:
            return r1

        # 3. Handle Fan mode
        r2 = self.set_fan_mode(fan_mode, source)
        if not r2.success:
            return HWResult(False, f"Power OK but fan failed: {r2.message}")

        return HWResult(True, f"Preset '{preset}' applied")
