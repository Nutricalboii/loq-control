import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loq_control.core.state_manager import StateManager
from loq_control.core.logger import LoqLogger
from loq_control.core import battery
from loq_control.core.capability_probe import CapabilityProbe

log = LoqLogger.get()
CONFIG_DIR = Path.home() / ".config" / "loq-control"
BATTERY_CONFIG = CONFIG_DIR / "battery.json"


class BatteryChargeManager:
    """
    Intelligent manager for battery charging.
    
    Handles:
    1. Conservation Mode (hysteresis-aware)
    2. Smart Overnight Charging (schedule-based)
    3. Rapid Charge Safety
    4. Battery Health Tracking
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, state_manager: StateManager):
        self._state = state_manager
        self._config: Dict[str, Any] = self._load_config()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Internal state for health tracking
        self._last_telemetry_time = 0
        self._accumulated_heat = 0.0
        
        # Sync initial state to SM
        self._sync_to_state_manager()

    @classmethod
    def get(cls, state_manager: Optional[StateManager] = None):
        with cls._lock:
            if cls._instance is None:
                sm = state_manager or StateManager()
                cls._instance = BatteryChargeManager(sm)
        return cls._instance

    def _load_config(self) -> Dict[str, Any]:
        defaults = {
            "conservation_enabled": False,
            "conservation_end": 80,
            "conservation_start": 75,
            "smart_charge_enabled": False,
            "wake_time": "08:00",
            "rapid_charge_preferred": False,
            "health_score": 100,
        }
        if BATTERY_CONFIG.exists():
            try:
                with open(BATTERY_CONFIG, "r") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception as e:
                log.daemon("error", f"Failed to load battery config: {e}")
        return defaults

    def _save_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(BATTERY_CONFIG, "w") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            log.daemon("error", f"Failed to save battery config: {e}")

    def _sync_to_state_manager(self):
        """Seed StateManager with values from config."""
        self._state.force_set("conservation_mode", self._config["conservation_enabled"])
        self._state.force_set("battery_start_threshold", self._config["conservation_start"])
        self._state.force_set("battery_end_threshold", self._config["conservation_end"])
        self._state.force_set("smart_charge_active", self._config["smart_charge_enabled"])
        self._state.force_set("smart_charge_wake_time", self._config["wake_time"])
        self._state.force_set("rapid_charge_active", self._config["rapid_charge_preferred"])

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="battery-mgr")
        self._thread.start()
        log.daemon("info", "Battery Charge Manager started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _worker_loop(self):
        """Background loop for health tracking and smart schedule."""
        while self._running:
            try:
                self._update_logic()
            except Exception as e:
                log.daemon("error", f"Battery manager loop error: {e}")
            time.sleep(30)  # Check every 30s

    def _update_logic(self):
        caps = CapabilityProbe.get().load_or_probe()
        info = battery.get_battery_info()
        now = datetime.now()
        
        # 1. Smart Overnight Charging Logic
        if self._config["smart_charge_enabled"]:
            self._handle_smart_charge(info, now)
            
        # 2. Health tracking (Heat exposure)
        if info["temp"] > 45.0:
            # Heat stress tracking
            self._accumulated_heat += (info["temp"] - 45.0)
            if self._accumulated_heat > 1000:
                self._config["health_score"] = max(0, self._config["health_score"] - 1)
                self._accumulated_heat = 0
                self._save_config()

        # 3. Rapid Charge Safety Override
        if self._state.get("rapid_charge_active") and info["temp"] > 48.0:
            log.daemon("warning", f"Battery temp {info['temp']}C too high! Disabling Rapid Charge.")
            from loq_control.services.hardware_service import HardwareService
            HardwareService().set_rapid_charge(False, source="safety")

    def _handle_smart_charge(self, info: Dict, now: datetime):
        """
        Logic: 
        - If far from wake time: hold at 75-80% (Conservation Mode behavior)
        - If within 60-90 min of wake time: allow 100%
        """
        try:
            wake_h, wake_m = map(int, self._config["wake_time"].split(":"))
            wake_dt = now.replace(hour=wake_h, minute=wake_m, second=0, microsecond=0)
            
            # If wake time has passed today, it's for tomorrow
            if wake_dt < now:
                from datetime import timedelta
                wake_dt += timedelta(days=1)
                
            diff_min = (wake_dt - now).total_seconds() / 60.0
            
            from loq_control.services.hardware_service import HardwareService
            hw = HardwareService()
            
            if 0 < diff_min < 90:
                # Within 90 mins of wake: Enable 100% charging
                if self._state.get("conservation_mode"):
                    log.daemon("info", f"Smart Charge: Within wake window ({diff_min:.0f}m). Lifting limit.")
                    hw.set_conservation(False, source="smart_charge")
            else:
                # Outside wake window: Enforce conservation if enabled
                if self._config.get("smart_charge_enabled") and not self._state.get("conservation_mode"):
                    # Only enable if it's currently at/above the hold level to prevent frequent toggling
                    if info["level"] >= 75:
                        log.daemon("info", "Smart Charge: Outside wake window. Holding charge.")
                        hw.set_conservation(True, source="smart_charge")

        except Exception as e:
            log.daemon("error", f"Smart charge logic failed: {e}")

    # --- CLI/GUI API ---

    def update_settings(self, settings: Dict[str, Any]):
        """Update settings and save config."""
        self._config.update(settings)
        self._save_config()
        self._sync_to_state_manager()
        
        # React immediately to threshold changes if conservation is on
        if "conservation_start" in settings or "conservation_end" in settings:
            if self._config["conservation_enabled"]:
                from loq_control.services.hardware_service import HardwareService
                HardwareService().set_battery_thresholds(
                    self._config["conservation_start"], 
                    self._config["conservation_end"]
                )
