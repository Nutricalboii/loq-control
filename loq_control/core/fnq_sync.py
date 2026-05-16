"""
Fn+Q Hardware Synchronization Engine

Maps ACPI platform_profile hardware states to LOQ Control software presets.
Listens to StateManager (driven by EventEngine) and reflects physical Fn+Q presses
directly into the GUI via power_profile state updates.
"""

import threading
import shutil
import subprocess
from typing import Optional

from loq_control.core.state_manager import StateManager
from loq_control.services.hardware_service import HardwareService
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()

# Map hardware platform_profile values → our internal power_profile keys
_HW_TO_PROFILE = {
    "low-power":   "power-saver",
    "quiet":       "power-saver",
    "power-saver": "power-saver",
    "balanced":    "balanced",
    "default":     "balanced",
    "performance": "performance",
    "max-power":   "performance",
    "turbo":       "performance",
}

# Map internal power_profile keys → powerprofilesctl profile names (for reading)
_PPCTL_TO_PROFILE = {
    "power-saver": "power-saver",
    "balanced":    "balanced",
    "performance": "performance",
}


def _get_true_profile() -> Optional[str]:
    """Read current profile directly from powerprofilesctl or sysfs."""
    if shutil.which("powerprofilesctl"):
        try:
            out = subprocess.check_output(
                ["powerprofilesctl", "get"], stderr=subprocess.DEVNULL, timeout=2
            ).decode().strip()
            return _PPCTL_TO_PROFILE.get(out, out)
        except Exception:
            pass
    try:
        with open("/sys/firmware/acpi/platform_profile", "r") as f:
            raw = f.read().strip()
            return _HW_TO_PROFILE.get(raw, raw)
    except Exception:
        return None


class FnQSync:
    """Synchronizes hardware profile events with internal daemon state and GUI."""

    _instance: Optional["FnQSync"] = None
    _lock = threading.Lock()

    def __init__(self, state: StateManager, hw: HardwareService):
        self._state = state
        self._hw = hw

        # Subscribe to platform_profile changes (from event_engine polls)
        self._state.subscribe(self._on_platform_profile_change)

        # Also do a periodic poll specifically for Fn+Q (every 1s)
        # so the GUI stays in sync even if event_engine misses a rapid press
        self._stop = threading.Event()
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="fnq-poller"
        )
        self._poll_thread.start()

        log.daemon("info", "Fn+Q Sync engine initialized")

    @classmethod
    def get(cls) -> Optional["FnQSync"]:
        return cls._instance

    @classmethod
    def init(cls, state: StateManager, hw: HardwareService) -> "FnQSync":
        with cls._lock:
            if cls._instance is None:
                cls._instance = FnQSync(state, hw)
            return cls._instance

    def _poll_loop(self):
        """1-second polling loop to catch Fn+Q presses that event_engine misses."""
        while not self._stop.is_set():
            self._stop.wait(1.0)
            if self._stop.is_set():
                break
            try:
                true_profile = _get_true_profile()
                if true_profile is None:
                    continue
                current = self._state.get("power_profile")
                if current != true_profile:
                    log.hardware("info", "Fn+Q poll: profile changed %s → %s", current, true_profile)
                    # Update GUI-facing state directly
                    self._state.force_set("power_profile", true_profile, source="fnq_sync")
            except Exception as e:
                log.hardware("error", "FnQSync poll error: %s", e)

    def _on_platform_profile_change(self, key: str, old_val: str, new_val: str, source: str):
        """React to platform_profile changes reported by event_engine."""
        if key != "platform_profile":
            return

        # Ignore changes we ourselves triggered (not a physical Fn+Q press)
        if source in ("gui", "cli", "test_mock", "fnq_sync"):
            return

        if old_val == new_val:
            return

        # Translate hardware profile name to our internal key
        mapped = _HW_TO_PROFILE.get(new_val)
        if not mapped:
            log.hardware("warn", "Fn+Q Sync: Unknown platform profile '%s'", new_val)
            return

        log.hardware("info", "Physical Fn+Q press detected: %s → %s (mapped: %s)",
                     old_val, new_val, mapped)

        # Clear any manual override so daemon can take control again
        self._state.clear_manual_override()

        # Directly update power_profile in state → GUI will pick this up via subscribe
        current = self._state.get("power_profile")
        if current != mapped:
            self._state.force_set("power_profile", mapped, source="fnq_sync")

    def stop(self):
        self._stop.set()
