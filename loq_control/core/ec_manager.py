import threading
from pathlib import Path
from typing import Dict, Any, Optional

from loq_control.core.logger import LoqLogger
from loq_control.core.capability_probe import CapabilityProbe

log = LoqLogger.get()


class ECManager:
    """
    Embedded Controller (EC) Detection Framework.
    
    Responsibilities:
    - Detect Lenovo ACPI (VPC2004) presence.
    - Read true AC charger wattage.
    - Identify advanced MUX or fan curve control boundaries.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.ideapad_acpi_path = Path("/sys/bus/platform/drivers/ideapad_acpi")
        self.vpc_path = Path("/sys/bus/platform/devices/VPC2004:00")
        self.platform_profile_path = Path("/sys/firmware/acpi/platform_profile")
        
        self.capabilities = CapabilityProbe.get().load_or_probe()

    @classmethod
    def get(cls) -> "ECManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ECManager()
        return cls._instance

    # ------------------------------------------------------------------
    # Capability Detection
    # ------------------------------------------------------------------

    def is_ideapad_acpi_loaded(self) -> bool:
        """Check if ideapad_acpi kernel module is active."""
        return self.ideapad_acpi_path.exists()

    def has_hardware_profiles(self) -> bool:
        """Check if ACPI platform profiles (Fn+Q sync) are supported."""
        return self.platform_profile_path.exists()

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def get_charger_wattage(self) -> Optional[int]:
        """
        Attempt to read true AC adapter wattage.
        Lenovo laptops often expose this in the ACPI power_supply class.
        """
        ps_dir = Path("/sys/class/power_supply")
        if not ps_dir.exists():
            return None

        # Look for ACAD or ADP1
        for ps in ps_dir.iterdir():
            if ps.is_dir() and "AC" in ps.name or "ADP" in ps.name:
                # Sometimes exposed as power_now or energy_now
                power_file = ps / "power_now"
                if power_file.exists():
                    try:
                        # power_now is in microwatts
                        mw = int(power_file.read_text().strip())
                        return mw // 1000000
                    except Exception as e:
                        log.firmware("debug", "Failed to read charger wattage: %s", e)
        return None

    def get_ec_topology(self) -> Dict[str, Any]:
        """Return the mapped capabilities of the embedded controller."""
        return {
            "ideapad_acpi_loaded": self.is_ideapad_acpi_loaded(),
            "hardware_profiles_supported": self.has_hardware_profiles(),
            "vpc_device_found": self.vpc_path.exists(),
        }
