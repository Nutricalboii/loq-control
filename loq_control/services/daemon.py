"""
Daemon orchestrator — bootstraps StateManager, HardwareService,
EventEngine, and AutoGPU in the correct order.
"""

from loq_control.core.state_manager import StateManager
from loq_control.core.config import Config
from loq_control.core.logger import get_logger
from loq_control.core.capability_probe import CapabilityProbe
from loq_control.services.hardware_service import HardwareService
from loq_control.services.event_engine import EventEngine
from loq_control.services.auto_gpu import AutoGPU

log = get_logger("loq-control.daemon")

# Module-level singletons (lazy init)
_state: StateManager | None = None
_hw: HardwareService | None = None
_events: EventEngine | None = None
_auto_gpu: AutoGPU | None = None


def start():
    """Initialise all services and start background threads."""
    global _state, _hw, _events, _auto_gpu

    config = Config()

    # 0. Load or Probe capabilities
    caps = CapabilityProbe.get().load_or_probe()
    log.info("Capabilities loaded: %s", caps)

    # 1. Start Thermal Telemetry
    from loq_control.core.thermal_manager import ThermalManager
    ThermalManager.get().start()
    log.info("Thermal telemetry started")

    # 1. State manager
    _state = StateManager(debounce_ms=config.get("debounce_ms", 500))

    # 2. Hardware service — syncs real hardware into state
    _hw = HardwareService(state=_state)
    _hw.sync_state_from_hardware()

    # 3. Event engine — monitors charger, suspend, etc.
    _events = EventEngine(
        state=_state,
        poll_interval=config.get("event_poll_interval_s", 5),
    )
    _events.start()

    # 4. Auto GPU — reacts to charger changes
    _auto_gpu = AutoGPU(state=_state, hw_service=_hw)
    _auto_gpu.start()

    log.info("Daemon started — all services running")


def stop():
    """Gracefully shut down all services."""
    global _events, _auto_gpu
    if _auto_gpu:
        _auto_gpu.stop()
    if _events:
        _events.stop()
    log.info("Daemon stopped")


def get_state() -> StateManager | None:
    return _state


def get_hw_service() -> HardwareService | None:
    return _hw
