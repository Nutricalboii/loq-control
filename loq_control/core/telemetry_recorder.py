"""
Telemetry Recorder — High-frequency high-precision logging of system metrics.
"""

import csv
import time
import threading
from pathlib import Path
from typing import Dict, Optional
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()

class TelemetryRecorder:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, log_dir: str = "~/.local/state/loq-control/telemetry"):
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_file: Optional[Path] = None
        self._running = False
        self._thread = None
        self._interval = 1.0 # 1Hz default
        
        self._csv_writer = None
        self._file_handle = None

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = TelemetryRecorder()
        return cls._instance

    def start(self):
        if self._running: return
        self._running = True
        
        # Create new file for this session
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.current_file = self.log_dir / f"session_{timestamp}.csv"
        
        self._file_handle = open(self.current_file, "w", newline="")
        self._csv_writer = csv.writer(self._file_handle)
        
        # Header
        self._csv_writer.writerow([
            "timestamp", "cpu_wattage", "cpu_temp", "gpu_usage", 
            "fan_pwm", "power_profile", "policy_active"
        ])
        self._file_handle.flush()
        
        self._thread = threading.Thread(target=self._recording_loop, daemon=True, name="telemetry-recorder")
        self._thread.start()
        log.daemon("info", f"Telemetry recording started: {self.current_file}")

    def stop(self):
        self._running = False
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        log.daemon("info", "Telemetry recording stopped")

    def _recording_loop(self):
        from loq_control.core import monitor, thermals
        from loq_control.core.state_manager import StateManager
        from loq_control.core.policy_engine import PolicyEngine
        
        state = StateManager()
        
        while self._running:
            try:
                now = time.time()
                watt = monitor.cpu_wattage()
                temp = thermals.cpu_temp()
                gpu_use = monitor.gpu_usage()
                
                # Fetch fan info from state snapshot
                current_state = state.get_state()
                policy = PolicyEngine.get().get_current_policy().value
                
                self._csv_writer.writerow([
                    round(now, 2),
                    round(watt, 1),
                    round(temp, 1),
                    round(gpu_use, 1),
                    0, # placeholder for real PWM if EC detection allows
                    current_state.get("power_profile", "unknown"),
                    policy
                ])
                self._file_handle.flush()
                
            except Exception as e:
                log.daemon("error", f"Telemetry record error: {e}")
                
            time.sleep(self._interval)
