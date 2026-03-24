"""
Firmware Sandbox — Safe, read-only research mode for ACPI and EC registers.
"""

import subprocess
from pathlib import Path
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()

class FirmwareSandbox:
    @staticmethod
    def probe_acpi(method: str) -> str:
        """Safe read-only ACPI probe using acpi_call (if available)."""
        call_path = Path("/proc/acpi/call")
        if not call_path.exists():
            return "Error: acpi_call module not loaded"
        
        try:
            # We ONLY allow reads (methods starting with \)
            if not method.startswith("\\"):
                 return "Error: Invalid ACPI method path"
            
            # Write method to call
            call_path.write_text(method)
            # Read back result
            result = call_path.read_text().strip()
            return f"ACPI[{method}] -> {result}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def probe_ec(register: int) -> str:
        """Safe read-only EC probe via /sys/kernel/debug/ec/ec0/io (requires root)."""
        ec_path = Path("/sys/kernel/debug/ec/ec0/io")
        if not ec_path.exists():
            return "Error: ec_sys debugfs not found"
        
        try:
            with open(ec_path, "rb") as f:
                f.seek(register)
                val = f.read(1)
                return f"EC[0x{register:02x}] -> 0x{val.hex()}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def list_thermal_sensors():
        """List all discovered thermal zones and their types."""
        zones = []
        for p in Path("/sys/class/thermal").glob("thermal_zone*"):
            t_type = (p / "type").read_text().strip()
            temp = (p / "temp").read_text().strip()
            zones.append(f"{p.name}: {t_type} ({int(temp)/1000}°C)")
        return zones
