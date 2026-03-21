"""
Fn+Q Hardware Synchronization Engine

Maps ACPI platform_profile hardware states to LOQ Control software presets.
Listens to StateManager (driven by EventEngine) and overrides active profiles
when the user physically presses Fn+Q.
"""

import threading
from typing import Optional

from loq_control.core.state_manager import StateManager
from loq_control.services.hardware_service import HardwareService
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()

class FnQSync:
    """Synchronizes hardware profile events with internal daemon state."""

    _instance: Optional["FnQSync"] = None
    _lock = threading.Lock()

    def __init__(self, state: StateManager, hw: HardwareService):
        self._state = state
        self._hw = hw
        
        # We only care when the platform_profile changes from the hardware (events/poll)
        self._state.subscribe(self._on_profile_change)
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

    def _on_profile_change(self, key: str, old_val: str, new_val: str, source: str):
        if key != "platform_profile":
            return

        # We only act if this was triggered natively by the hardware event loop,
        # OR if it was explicitly passed down to be synced. If the GUI requested
        # 'performance', the GUI itself triggers the preset, so we ignore 'gui' or 'cli'.
        if source in ("gui", "cli", "test_mock"):
            return

        if old_val == new_val:
            return

        # If it's a daemon poll/udev event indicating physical Fn+Q switch:
        log.hardware("info", f"Physical Fn+Q press detected: {old_val} -> {new_val}")
        
        # Override any existing user software lock and return daemon to auto control
        self._state.clear_manual_override()

        # Route platform profile to our named software presets
        if new_val == "quiet":
            self._hw.apply_preset("battery", source="fnq_sync")
        elif new_val == "balanced":
            self._hw.apply_preset("balanced", source="fnq_sync")
        elif new_val == "performance":
            self._hw.apply_preset("gaming", source="fnq_sync")
        else:
            log.hardware("warn", f"Fn+Q Sync: Unknown profile '{new_val}'")
