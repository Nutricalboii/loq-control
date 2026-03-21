"""
UI Controller — mediator between GUI ↔ HardwareService ↔ StateManager.

The GUI should NEVER import core modules directly.
All interactions go through this controller.
"""

from typing import Any, Callable, Dict

from loq_control.core.state_manager import StateManager
from loq_control.core.capability_probe import CapabilityProbe
from loq_control.core import monitor, thermals, hardware
from loq_control.services.hardware_service import HardwareService, HWResult
from loq_control.core.logger import get_logger

log = get_logger("loq-control.controller")


class AppController:
    """Single entry point for the GUI to interact with the system."""

    def __init__(self, state: StateManager, hw: HardwareService):
        self._state = state
        self._hw = hw
        self._capabilities = CapabilityProbe.get().load_or_probe()

    # ------------------------------------------------------------------
    # Hardware actions
    # ------------------------------------------------------------------

    def switch_gpu(self, mode: str) -> HWResult:
        return self._hw.switch_gpu(mode, source="gui")

    def set_power_profile(self, profile: str) -> HWResult:
        return self._hw.set_power_profile(profile, source="gui")

    def set_fan_mode(self, mode: str) -> HWResult:
        return self._hw.set_fan_mode(mode, source="gui")

    def set_conservation(self, enabled: bool) -> HWResult:
        return self._hw.set_conservation(enabled, source="gui")

    def apply_preset(self, preset: str) -> HWResult:
        return self._hw.apply_preset(preset, source="gui")

    # ------------------------------------------------------------------
    # Manual override
    # ------------------------------------------------------------------

    def set_manual_override(self):
        self._state.set_manual_override()

    def clear_manual_override(self):
        self._state.clear_manual_override()

    # ------------------------------------------------------------------
    # State & Capability queries
    # ------------------------------------------------------------------

    def get_capabilities(self) -> Dict[str, Any]:
        return self._capabilities

    def get_state(self) -> Dict[str, Any]:
        return self._state.get_state()

    def get_thermal_telemetry(self) -> Dict[str, Any]:
        from loq_control.core.thermal_manager import ThermalManager
        return ThermalManager.get().get_telemetry()
        
    def get_thermal_topology(self) -> Dict[str, Any]:
        from loq_control.core.thermal_manager import ThermalManager
        return ThermalManager.get().get_topology()

    def get(self, key: str) -> Any:
        return self._state.get(key)

    # ------------------------------------------------------------------
    # Monitoring (read-only sensor data)
    # ------------------------------------------------------------------

    def cpu_usage(self) -> float:
        return monitor.cpu_usage()

    def ram_usage(self) -> float:
        return monitor.ram_usage()

    def cpu_temp(self) -> float:
        return thermals.cpu_temp()

    def ssd_temp(self) -> float:
        return thermals.ssd_temp()

    def battery_power(self) -> float:
        return monitor.battery_power()

    def gpu_usage(self) -> float:
        return monitor.gpu_usage()

    # ------------------------------------------------------------------
    # Observer
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable):
        """Subscribe to state changes: callback(key, old, new, source)."""
        self._state.subscribe(callback)

    def unsubscribe(self, callback: Callable):
        self._state.unsubscribe(callback)
