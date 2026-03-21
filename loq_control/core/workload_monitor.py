"""
Workload Monitor — Analyzes resource intensity to classify user activity.
"""

import time
import psutil
from typing import Dict, List

class WorkloadMonitor:
    def __init__(self):
        self._cpu_history: List[float] = []
        self._gpu_history: List[float] = []
        
    def get_current_metrics(self) -> Dict:
        """Collect current resource usage levels."""
        cpu = psutil.cpu_percent(interval=None)
        
        # Try to get GPU usage from system sensors or nvidia-smi
        from loq_control.core import monitor
        gpu = monitor.gpu_usage()
        
        self._cpu_history.append(cpu)
        self._gpu_history.append(gpu)
        
        if len(self._cpu_history) > 60:
            self._cpu_history.pop(0)
            self._gpu_history.pop(0)
            
        return {
            "cpu_avg": sum(self._cpu_history) / len(self._cpu_history),
            "gpu_avg": sum(self._gpu_history) / len(self._gpu_history),
            "power": monitor.cpu_wattage(),
            "active_window": self._get_active_window_class()
        }

    def _get_active_window_class(self) -> str:
        """Heuristic for determining if a game or office app is in focus."""
        # TODO: Implement X11/Wayland window property check
        return "unknown"
