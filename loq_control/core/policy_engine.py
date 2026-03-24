"""
Policy Engine — The "Brain" of LOQ Control.
Orchestrates global hardware states based on workload classification.
"""

import threading
import time
from enum import Enum
from loq_control.core.state_manager import StateManager
from loq_control.core.workload_monitor import WorkloadMonitor
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()

class WorkloadType(Enum):
    OFFICE = "office"
    PROGRAMMING = "programming"
    GAMING = "gaming"
    IDLE = "idle"

class PolicyEngine:
    _instance = None

    def __init__(self, state: StateManager):
        self._state = state
        self._monitor = WorkloadMonitor()
        self._running = False
        self._thread = None
        self._current_policy = WorkloadType.IDLE

    @classmethod
    def init(cls, state: StateManager):
        if cls._instance is None:
            cls._instance = PolicyEngine(state)
        return cls._instance

    @classmethod
    def get(cls):
        return cls._instance

    def get_current_policy(self) -> WorkloadType:
        return self._current_policy

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="policy-engine")
        self._thread.start()
        log.daemon("info", "Policy Engine (The Brain) started")

    def _loop(self):
        while self._running:
            time.sleep(5.0) # Check every 5s
            metrics = self._monitor.get_current_metrics()
            
            new_policy = self._classify(metrics)
            if new_policy != self._current_policy:
                log.daemon("info", f"Policy shift detected: {self._current_policy.value} -> {new_policy.value}")
                self._apply_policy(new_policy)
                self._current_policy = new_policy

    def _classify(self, m: dict) -> WorkloadType:
        if m["cpu_avg"] < 5 and m["gpu_avg"] < 2:
            return WorkloadType.IDLE
        if m["cpu_avg"] > 40 or m["gpu_avg"] > 30:
            return WorkloadType.GAMING
        if m["cpu_avg"] > 10:
            return WorkloadType.PROGRAMMING
        return WorkloadType.OFFICE

    def _apply_policy(self, policy: WorkloadType):
        if policy == WorkloadType.GAMING:
            self._state.request_transition("power_profile", "performance", source="policy")
            self._state.request_transition("smart_fan_active", True, source="policy")
        elif policy == WorkloadType.IDLE or policy == WorkloadType.OFFICE:
            self._state.request_transition("power_profile", "quiet", source="policy")
            self._state.request_transition("smart_fan_active", False, source="policy")
