import threading
import time
from pathlib import Path

from loq_control.core.capability_probe import CapabilityProbe
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()


class ThermalManager:
    """
    Thermal Telemetry Framework

    Responsibilities:
    - Discover thermal zones
    - Discover hwmon chips
    - Map fan RPM sensors
    - Map PWM control capability
    - Provide normalized temperature telemetry
    """

    _instance = None
    _lock = threading.Lock()

    POLL_INTERVAL = 2.0

    def __init__(self):
        self.capabilities = CapabilityProbe.get().load_or_probe()

        self.hwmon_chips = []
        self.thermal_zones = []
        self.fans = []

        self.telemetry = {}
        self.running = False
        self.thread = None

        self._discover_topology()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = ThermalManager()
        return cls._instance

    # --------------------------------------------------
    # TOPOLOGY DISCOVERY
    # --------------------------------------------------

    def _discover_topology(self):
        self._discover_hwmon()
        self._discover_thermal_zones()
        self._discover_fans()

    def _discover_hwmon(self):
        base = Path("/sys/class/hwmon")
        if not base.exists():
            return

        for chip in base.iterdir():
            name_file = chip / "name"
            try:
                name = name_file.read_text().strip()
            except Exception:
                name = "unknown"

            self.hwmon_chips.append({
                "path": chip,
                "name": name
            })

    def _discover_thermal_zones(self):
        base = Path("/sys/class/thermal")
        if not base.exists():
            return

        for zone in base.iterdir():
            if "thermal_zone" in zone.name:
                type_file = zone / "type"
                try:
                    ztype = type_file.read_text().strip()
                except Exception:
                    ztype = "unknown"

                self.thermal_zones.append({
                    "path": zone,
                    "type": ztype
                })

    def _discover_fans(self):
        for chip in self.hwmon_chips:
            base = chip["path"]

            for i in range(1, 5):
                rpm_file = base / f"fan{i}_input"
                pwm_file = base / f"pwm{i}"

                if rpm_file.exists():
                    self.fans.append({
                        "chip": chip["name"],
                        "rpm_file": rpm_file,
                        "pwm_file": pwm_file if pwm_file.exists() else None
                    })

    # --------------------------------------------------
    # TELEMETRY ENGINE
    # --------------------------------------------------

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True, name="thermal-telemetry")
        self.thread.start()

    def stop(self):
        self.running = False

    def _poll_loop(self):
        while self.running:
            self._read_temperatures()
            self._read_fans()
            time.sleep(self.POLL_INTERVAL)

    # --------------------------------------------------
    # READERS
    # --------------------------------------------------

    def _read_temperatures(self):
        temps = {}

        for zone in self.thermal_zones:
            temp_file = zone["path"] / "temp"
            try:
                value = int(temp_file.read_text().strip()) / 1000.0
                temps[zone["type"]] = value
            except Exception:
                pass

        self.telemetry["temps"] = temps
        if temps:
            log.thermal("debug", f"Temp map {temps}")

    def _read_fans(self):
        fan_data = []

        for fan in self.fans:
            try:
                rpm = int(fan["rpm_file"].read_text().strip())
            except Exception:
                rpm = None

            fan_data.append({
                "chip": fan["chip"],
                "rpm": rpm,
                "controllable": fan["pwm_file"] is not None
            })

        self.telemetry["fans"] = fan_data

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def get_telemetry(self):
        return self.telemetry

    def get_topology(self):
        return {
            "hwmon": self.hwmon_chips,
            "zones": self.thermal_zones,
            "fans": self.fans
        }
    def get_cpu_temp(self) -> float:
        """Heuristic to return the most relevant CPU package temperature."""
        temps = self.telemetry.get("temps", {})
        # Common Lenovo/Intel/AMD sensor names
        for key in ("x86_pkg_temp", "cpu_thermal", "acpitz", "k10temp", "coretemp"):
            if key in temps:
                return temps[key]
        
        # Fallback to the first available sensor if others fail
        if temps:
            return next(iter(temps.values()))
        return 45.0 # safe baseline
