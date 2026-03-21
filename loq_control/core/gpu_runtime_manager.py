import os
import subprocess
import time
import threading
from pathlib import Path

from loq_control.core.state_manager import StateManager
from loq_control.core.capability_probe import CapabilityProbe


class GPURuntimeManager:
    """
    Runtime GPU power management framework.

    Handles safe suspend / resume of discrete GPU.
    Designed for NVIDIA first but architecture is vendor-agnostic.
    """

    _instance = None
    _lock = threading.Lock()

    GPU_VENDOR_NVIDIA = "0x10de"

    STATE_ACTIVE = "ACTIVE"
    STATE_IDLE = "IDLE"
    STATE_SUSPENDING = "SUSPENDING"
    STATE_SUSPENDED = "SUSPENDED"
    STATE_RESUMING = "RESUMING"
    STATE_FAILED = "FAILED"

    def __init__(self):
        self.state_manager = StateManager()
        self.capabilities = CapabilityProbe.get().load_or_probe()

        self.gpu_state = self.STATE_ACTIVE
        self.pci_path = self._detect_nvidia_pci_path()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = GPURuntimeManager()
        return cls._instance

    # --------------------------------------------------
    # Detection
    # --------------------------------------------------

    def _detect_nvidia_pci_path(self):
        base = Path("/sys/bus/pci/devices")
        if not base.exists():
            return None

        for dev in base.iterdir():
            try:
                vendor = (dev / "vendor").read_text().strip()
                if vendor == self.GPU_VENDOR_NVIDIA:
                    return str(dev)
            except Exception:
                pass
        return None

    # --------------------------------------------------
    # Usage Detection
    # --------------------------------------------------

    def gpu_in_use(self):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip():
                return True
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["lsof", "/dev/nvidia0"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip():
                return True
        except Exception:
            pass

        return False

    # --------------------------------------------------
    # Suspend Transaction
    # --------------------------------------------------

    def suspend_gpu(self, source="daemon"):
        if not self.capabilities["gpu"].get("pci_runtime_pm"):
            return False

        if not self.pci_path:
            return False

        if self.gpu_in_use():
            return False

        if not self.state_manager.lock_transition(source):
            return False

        try:
            self.gpu_state = self.STATE_SUSPENDING

            subprocess.run(
                ["prime-select", "intel"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            time.sleep(3)

            power_control = Path(self.pci_path) / "power" / "control"
            if power_control.exists():
                power_control.write_text("auto")

            time.sleep(2)

            self.gpu_state = self.STATE_SUSPENDED
            self.state_manager.force_set("gpu_mode", "integrated")
            return True

        except Exception:
            self.gpu_state = self.STATE_FAILED
            return False

        finally:
            self.state_manager.unlock_transition()

    # --------------------------------------------------
    # Resume Transaction
    # --------------------------------------------------

    def resume_gpu(self, source="daemon"):
        if not self.pci_path:
            return False

        if not self.state_manager.lock_transition(source):
            return False

        try:
            self.gpu_state = self.STATE_RESUMING

            power_control = Path(self.pci_path) / "power" / "control"
            if power_control.exists():
                power_control.write_text("on")

            subprocess.run(
                ["prime-select", "nvidia"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            time.sleep(3)

            test = subprocess.run(
                ["nvidia-smi"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            if test.returncode != 0:
                self.gpu_state = self.STATE_FAILED
                return False

            self.gpu_state = self.STATE_ACTIVE
            self.state_manager.force_set("gpu_mode", "nvidia")
            return True

        except Exception:
            self.gpu_state = self.STATE_FAILED
            return False

        finally:
            self.state_manager.unlock_transition()

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def get_state(self):
        return self.gpu_state
