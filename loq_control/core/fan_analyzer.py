"""
Fan Analyzer — Tracks thermal efficiency and equilibrium points.
Correlates PWM targets with Wattage loads and resultant temperature stability.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()

@dataclass
class EquilibriumPoint:
    wattage: float
    pwm: int
    temp: float
    timestamp: float

class FanAnalyzer:
    _instance: Optional["FanAnalyzer"] = None

    def __init__(self):
        # Maps Wattage (rounded to 5W bins) -> EquilibriumPoint
        self.equilibrium_map: Dict[int, EquilibriumPoint] = {}
        self._history: List[Dict] = []
        self._history_limit = 300 # 5 mins at 1s intervals

    @classmethod
    def get(cls) -> "FanAnalyzer":
        if cls._instance is None:
            cls._instance = FanAnalyzer()
        return cls._instance

    def record_tick(self, wattage: float, pwm: int, temp: float):
        """Record a single telemetry slice."""
        self._history.append({
            "t": time.monotonic(),
            "w": wattage,
            "p": pwm,
            "temp": temp
        })
        if len(self._history) > self._history_limit:
            self._history.pop(0)

        self._analyze_equilibrium()

    def _analyze_equilibrium(self):
        """
        Check if we've been stable for the last 30 seconds.
        Stability = Temp variance < 2C, PWM unchanged, Wattage variance < 3W.
        """
        if len(self._history) < 30:
            return

        window = self._history[-30:]
        temps = [x["temp"] for x in window]
        pwms = [x["p"] for x in window]
        watts = [x["w"] for x in window]

        temp_stable = (max(temps) - min(temps)) < 2.0
        pwm_stable = (max(pwms) - min(pwms)) == 0
        watt_stable = (max(watts) - min(watts)) < 3.0

        if temp_stable and pwm_stable and watt_stable:
            avg_w = sum(watts) / len(watts)
            bin_w = int(round(avg_w / 5.0) * 5) # 5W bins
            
            point = EquilibriumPoint(
                wattage=avg_w,
                pwm=pwms[0],
                temp=temps[-1],
                timestamp=time.time()
            )
            
            # Learn or Refine
            if bin_w not in self.equilibrium_map:
                log.daemon("info", f"Learned Equilibrium: {bin_w}W load stabilized at {pwms[0]}% PWM ({temps[-1]}C)")
            self.equilibrium_map[bin_w] = point

    def get_predicted_pwm(self, wattage: float, target_temp: float = 75.0) -> Optional[int]:
        """
        Given a current wattage load, what PWM should we use to aim for target_temp?
        Uses learned equilibrium map or interpolation.
        """
        bin_w = int(round(wattage / 5.0) * 5)
        if bin_w in self.equilibrium_map:
            point = self.equilibrium_map[bin_w]
            # Simple heuristic: if learned temp was 80C at 40% PWM, and we want 75C,
            # we need to increase PWM. For now, return learned point as base.
            return point.pwm
            
        return None

    def get_efficiency_score(self) -> float:
        """Return a 0-1 score of current cooling efficiency."""
        if not self._history: return 1.0
        # Delta Temp / Delta Time vs PWM
        return 1.0 # TODO: Logic for thermal resistance
