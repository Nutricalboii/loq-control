"""
Smart Fan Control Engine

Evaluates thermal telemetry and interpolates a safe fan PWM target using
configurable curve mapping and hysteresis filtering. Includes a Deadman
Switch for catastrophic thermal events or telemetry failure.
"""

import threading
import time
from typing import List, Tuple, Optional

from loq_control.core.logger import LoqLogger
from loq_control.core import fan
from loq_control.core.state_manager import StateManager

log = LoqLogger.get()

class CurveEvaluator:
    def __init__(self, nodes: List[Tuple[float, float]]):
        # nodes is a list of (Temp C, PWM %) sorted by Temp
        self.nodes = sorted(nodes, key=lambda x: x[0])

    def evaluate(self, temp: float) -> float:
        if not self.nodes:
            return 50.0
        if temp <= self.nodes[0][0]:
            return self.nodes[0][1]
        if temp >= self.nodes[-1][0]:
            return self.nodes[-1][1]
            
        for i in range(len(self.nodes) - 1):
            t1, p1 = self.nodes[i]
            t2, p2 = self.nodes[i+1]
            if t1 <= temp <= t2:
                # Linear interpolation
                ratio = (temp - t1) / (t2 - t1)
                return p1 + ratio * (p2 - p1)
        return 100.0

class SmartFanEngine:
    _instance: Optional["SmartFanEngine"] = None
    _init_lock = threading.Lock()

    def __init__(self, state: StateManager):
        if hasattr(self, "_initialised"):
            return
        self._initialised = True
        self._state = state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._curve = CurveEvaluator([(40, 20), (60, 40), (80, 80), (95, 100)])
        self._history: List[float] = []
        self._history_len = 3
        self.DEADMAN_TEMP = 95.0
        
        self._state.subscribe(self._on_state_change)

    @classmethod
    def get(cls) -> Optional["SmartFanEngine"]:
        return cls._instance

    @classmethod
    def init(cls, state: StateManager) -> "SmartFanEngine":
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = SmartFanEngine(state)
            return cls._instance

    @classmethod
    def reset(cls):
        with cls._init_lock:
            if cls._instance:
                cls._instance.stop()
                cls._instance = None

    def _on_state_change(self, key: str, old_val, new_val, source: str):
        if key == "smart_fan_active":
            if new_val and not self._running:
                self.start()
            elif not new_val and self._running:
                self.stop()
        elif key == "fan_mode" and source != "smart_fan" and source != "deadman":
            # If user explicitly switched to "quiet" or "performance" via GUI/Fn+Q
            if new_val != "custom" and self._running:
                self._state.request_transition("smart_fan_active", False, source="daemon")

    def _trigger_deadman(self, reason: str):
        log.hardware("critical", f"SmartFan DEADMAN SWITCH: {reason}! Forcing BIOS limits.")
        fan.performance() # ACPI rescue
        self._state.force_set("fan_mode", "performance")
        self._state.request_transition("smart_fan_active", False, source="deadman")

    def start(self):
        if self._running:
            return
        self._history.clear()
        
        # Put EC into custom mode to accept manual granular PWM streams
        if not fan.custom():
            log.hardware("error", "SmartFan could not engage custom platform_profile! Curve aborted.")
            self._running = False
            return
            
        self._state.force_set("fan_mode", "custom")
        self._running = True
        
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SmartFan")
        self._thread.start()
        log.daemon("info", "Smart Fan Engine activated")

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            # Break blocking sleeps lightly without forcing process death
            self._thread.join(timeout=2.0)
        self._thread = None
        log.daemon("info", "Smart Fan Engine halted")

    def _loop(self):
        from loq_control.core.thermal_manager import ThermalManager
        from loq_control.core.fan_analyzer import FanAnalyzer
        from loq_control.core import monitor

        analyzer = FanAnalyzer.get()

        while self._running:
            time.sleep(1.0) # Faster loop for proactive response
            if not self._running:
                break
                
            telemetry = ThermalManager.get().get_telemetry()
            wattage = monitor.cpu_wattage() # Get real-time power draw
            
            if not telemetry:
                self._trigger_deadman("Telemetry unavailable")
                break
                
            try:
                cpu_t = telemetry.get("cpu", {}).get("temp", 0.0)
                gpu_t = telemetry.get("gpu", {}).get("temp", 0.0)
                max_temp = float(max(cpu_t, gpu_t))
            except Exception as e:
                self._trigger_deadman(f"Telemetry parse error: {e}")
                break
                
            if max_temp >= self.DEADMAN_TEMP:
                self._trigger_deadman(f"Max Temp {max_temp}C >= {self.DEADMAN_TEMP}C")
                break

            # 1. Update Analyzer
            # We record a tick at current PWM/Temp
            current_pwm = self._history[-1] if self._history else 0 # Placeholder for last sent PWM
            analyzer.record_tick(wattage, int(current_pwm), max_temp)

            # 2. Hysteresis Smoothing
            self._history.append(max_temp)
            if len(self._history) > self._history_len:
                self._history.pop(0)
            smoothed_temp = sum(self._history) / len(self._history)
            
            # 3. Adaptive Prediction vs Curve
            predicted_pwm = analyzer.get_predicted_pwm(wattage)
            curve_pwm = self._curve.evaluate(smoothed_temp)
            
            # Proactive Ramp: If wattage is very high, force a minimum PWM 
            # regardless of current temperature to prevent the spike.
            proactive_pwm = 0
            if wattage > 45.0: proactive_pwm = 50.0
            if wattage > 60.0: proactive_pwm = 80.0

            target_pwm = max(curve_pwm, proactive_pwm)
            if predicted_pwm:
                # Weighted average towards predicted equilibrium if confidence is high
                target_pwm = (target_pwm + predicted_pwm) / 2.0
            
            # 4. Dispatch abstraction
            ok1 = fan.set_manual_pwm(1, int(target_pwm))
            ok2 = fan.set_manual_pwm(2, int(target_pwm))
            
            if not ok1 and not ok2:
                pass

