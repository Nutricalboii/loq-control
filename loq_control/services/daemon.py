"""
Daemon orchestrator — bootstraps StateManager, HardwareService,
EventEngine, and AutoGPU in the correct order.
"""

from loq_control.core.state_manager import StateManager
from loq_control.core.config import Config
from loq_control.core.logger import LoqLogger
from loq_control.core.capability_probe import CapabilityProbe
from loq_control.services.hardware_service import HardwareService
from loq_control.services.event_engine import EventEngine
from loq_control.services.auto_gpu import AutoGPU
from loq_control.core.fnq_sync import FnQSync

log = LoqLogger.get()

# Module-level singletons (lazy init)
_state: StateManager | None = None
_hw: HardwareService | None = None
_events: EventEngine | None = None
_auto_gpu: AutoGPU | None = None
_smart_fan = None


def start():
    """Initialise all services and start background threads."""
    global _state, _hw, _events, _auto_gpu

    config = Config()

    # 0. Load or Probe capabilities
    caps = CapabilityProbe.get().load_or_probe()
    
    # Merge exact Firmware Intelligence detection
    from loq_control.core.ec_detection import ECDetection
    ec_caps = ECDetection.get().get_capabilities()
    caps.update(ec_caps)
    
    log.daemon("info", "Capabilities loaded: %s", caps)

    # 1. Start Thermal Telemetry
    from loq_control.core.thermal_manager import ThermalManager
    ThermalManager.get().start()
    log.daemon("info", "Thermal telemetry started")

    # 1. State manager
    _state = StateManager(debounce_ms=config.get("debounce_ms", 500))

    # 1.5 Safety Supervisor (Watcher of all)
    from loq_control.core.safety_supervisor import SafetySupervisor
    _safety = SafetySupervisor.get(state_manager=_state)
    _safety.start()

    # 2. Hardware service — syncs real hardware into state

    _hw = HardwareService(state=_state)
    _hw.sync_state_from_hardware()

    # 3. Event engine — monitors charger, suspend, etc.
    _events = EventEngine(
        state=_state,
        poll_interval=config.get("event_poll_interval_s", 5),
    )
    _events.start()

    # 4. Fn+Q Synchronization API
    _fnq = FnQSync.init(_state, _hw)

    # 5. Auto GPU — reacts to charger changes
    _auto_gpu = AutoGPU(state=_state, hw_service=_hw)
    _auto_gpu.start()

    # 5. Smart Fan Engine
    from loq_control.core.smart_fan import SmartFanEngine
    _fan_engine = SmartFanEngine.init(_state)
    _fan_engine.start()

    # 5.5 Telemetry Recorder (Priority 2)
    from loq_control.core.telemetry_recorder import TelemetryRecorder
    _recorder = TelemetryRecorder.get()
    _recorder.start()

    # 6. Global Policy Engine (The Brain)

    from loq_control.core.policy_engine import PolicyEngine
    _policy = PolicyEngine.init(_state)
    _policy.start()

    # 7. Battery Charge Manager
    from loq_control.core.battery_charge_manager import BatteryChargeManager
    _battery_mgr = BatteryChargeManager.get(_state)
    _battery_mgr.start()

    log.daemon("info", "Daemon started — all services running")


def stop():
    """Gracefully shut down all services."""
    global _events, _auto_gpu, _smart_fan
    # Policy engine is a singleton and daemon thread, no explicit stop needed but good practice
    if _smart_fan:
        _smart_fan.stop()
    if _auto_gpu:
        _auto_gpu.stop()
    if _events:
        _events.stop()
    log.daemon("info", "Daemon stopped")



def get_state() -> StateManager | None:
    return _state


def get_hw_service() -> HardwareService | None:
    return _hw
