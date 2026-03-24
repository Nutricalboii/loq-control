"""
Safety Supervisor — High-authority watchdog for hardware and policy safety.
"""

import time
import threading
from typing import Any, Dict, List, Optional
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()

class SafetyStatus:
    OK = "ok"
    THROTTLED = "throttled"
    SAFE_MODE = "safe_mode"

class SafetySupervisor:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, state_manager):
        self._state = state_manager
        self._status = SafetyStatus.OK
        
        # Rate Limiting
        self._decision_history: List[float] = []
        self._cooldown_until: float = 0.0
        
        # Thermal Watchdog
        self._last_temp = 40.0
        self._temp_slope = 0.0 # deg/sec
        
        # Policy Oscillation
        self._policy_history: List[str] = []
        
        # Failure Tracking (Self-Healing)
        self._failure_counts: Dict[str, int] = {}
        
        self._running = False
        self._thread = None

    @classmethod
    def get(cls, state_manager=None):
        with cls._lock:
            if cls._instance is None and state_manager:
                cls._instance = SafetySupervisor(state_manager)
        return cls._instance

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._watchdog_loop, daemon=True, name="safety-watchdog")
        self._thread.start()
        log.daemon("info", "Safety Supervisor (The Watchdog) active")

    def check_transition(self, key: str, value: Any, source: str) -> bool:
        """
        Gatekeeper for StateManager. 
        Returns True if transition is safe, False otherwise.
        """
        now = time.monotonic()
        
        # 1. Global Safe Mode Check
        if self._status == SafetyStatus.SAFE_MODE and source != "emergency":
            log.daemon("warning", f"Safety: Transition {key}={value} rejected - SAFE MODE ACTIVE")
            return False

        # 2. Cooldown Check
        if now < self._cooldown_until:
             log.daemon("warning", f"Safety: Transition {key}={value} rejected - COOLDOWN ACTIVE")
             return False

        # 3. Rate Limiting (Audit autonomous sources only)
        if source in ["policy", "smart-fan", "auto-gpu"]:
            self._decision_history = [t for t in self._decision_history if now - t < 20]
            self._decision_history.append(now)
            
            if len(self._decision_history) > 3:
                log.daemon("warning", "Safety: Rate limit hit (3 writes in 20s). Entering 60s cooldown.")
                self._cooldown_until = now + 60.0
                self._status = SafetyStatus.THROTTLED
                return False

        return True

    def handle_failure(self, key: str, value: Any, error: str):
        """Track hardware failures and trigger Safe Mode if persistent."""
        count = self._failure_counts.get(key, 0) + 1
        self._failure_counts[key] = count
        
        log.daemon("warning", f"Safety: Detected failure {count}/3 for {key}={value}: {error}")
        
        if count >= 3:
            self._enter_safe_mode(f"Persistent Hardware Failure: {key} failed 3 times")

    def _watchdog_loop(self):
        while self._running:
            time.sleep(2.0)
            self._check_thermals()
            self._check_daemon_health()

    def _check_thermals(self):
        from loq_control.core import thermals
        temp = thermals.cpu_temp()
        
        # Slope detection (2s interval)
        self._temp_slope = (temp - self._last_temp) / 2.0
        self._last_temp = temp
        
        # EMERGENCY: Thermal Runaway
        if temp > 93.0:
            if self._status != SafetyStatus.SAFE_MODE:
                self._enter_safe_mode(f"Thermal Overheat: {temp}C")
        
        elif temp > 88.0 and self._temp_slope > 1.5:
            # Rapid rise at high temp
            self._enter_safe_mode(f"Thermal Runaway Detected: +{self._temp_slope}C/s")

    def _enter_safe_mode(self, reason: str):
        log.daemon("critical", f"!!! SAFETY SUPERVISOR TRIGGERED: {reason} !!!")
        self._status = SafetyStatus.SAFE_MODE
        
        # Force hardware to safe state
        self._state.request_transition("power_profile", "power-saver", source="emergency")
        self._state.request_transition("fan_mode", "performance", source="emergency")
        self._state.request_transition("smart_fan_active", False, source="emergency")
        
    def _check_daemon_health(self):
        # Notify systemd if possible (sd_notify watchdog)
        # This keeps the daemon from being killed by systemd if it heartbeats
        try:
            from systemd import daemon
            daemon.notify("WATCHDOG=1")
        except (ImportError, Exception):
            pass # systemd package not installed or not running under systemd

    def get_status(self):
        return self._status
