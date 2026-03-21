import subprocess
import threading
from pathlib import Path
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()


class ECDetection:
    """
    Lenovo Firmware / EC Capability Detection Framework

    Detects:
    - ideapad_laptop module
    - lenovo_wmi module
    - acpi_call usability
    - WMI bus
    - possible EC debug interfaces
    - MUX switch hints
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.capabilities = {}
        self._detect_all()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = ECDetection()
        return cls._instance

    # --------------------------------------------------
    # MASTER DETECTOR
    # --------------------------------------------------

    def _safe_exists(self, path: str) -> bool:
        try:
            return Path(path).exists()
        except PermissionError:
            return False

    def _detect_all(self):
        self.capabilities["ideapad_module"] = self._module_loaded("ideapad_laptop")
        self.capabilities["lenovo_wmi"] = self._module_loaded("lenovo_wmi")
        self.capabilities["acpi_call"] = self._acpi_call_available()
        self.capabilities["wmi_bus"] = self._safe_exists("/sys/bus/wmi")
        self.capabilities["ec_sys"] = self._safe_exists("/sys/kernel/debug/ec")
        self.capabilities["mux_hint"] = self._safe_exists("/sys/kernel/debug/vgaswitcheroo/switch")
        log.firmware("info", f"EC capabilities mapped: {self.capabilities}")

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def _module_loaded(self, name):
        try:
            output = subprocess.run(
                ["lsmod"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return name in output.stdout
        except Exception:
            return False

    def _acpi_call_available(self):
        try:
            subprocess.run(
                ["which", "acpi_call"],
                capture_output=True,
                timeout=2,
            )
            return True
        except Exception:
            return False

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------

    def get_capabilities(self):
        return self.capabilities
