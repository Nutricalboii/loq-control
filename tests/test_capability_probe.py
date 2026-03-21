import os
import json
import time
from unittest.mock import patch, MagicMock, mock_open
import pytest

from loq_control.core.capability_probe import CapabilityProbe, CAP_FILE


@pytest.fixture(autouse=True)
def reset_probe():
    """Reset the singleton instance and timestamp before each test."""
    CapabilityProbe._instance = None
    yield
    CapabilityProbe._instance = None


class TestCapabilityProbe:

    @patch("loq_control.core.capability_probe.CAP_FILE")
    @patch.object(CapabilityProbe, "probe_all")
    def test_load_or_probe_forces_probe_if_no_file(self, mock_probe_all, mock_cap_file):
        mock_cap_file.exists.return_value = False
        probe = CapabilityProbe.get()
        probe.load_or_probe()
        mock_probe_all.assert_called_once()

    @patch("loq_control.core.capability_probe.CAP_FILE")
    def test_load_or_probe_uses_cache_if_valid(self, mock_cap_file):
        mock_cap_file.exists.return_value = True
        probe = CapabilityProbe.get()
        
        valid_data = {
            "_timestamp": int(time.time()),
            "gpu": {"test": True}
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(valid_data))):
            caps = probe.load_or_probe()
            
        assert caps["gpu"]["test"] is True
        assert probe.capabilities == valid_data

    @patch("loq_control.core.capability_probe.CAP_FILE")
    @patch.object(CapabilityProbe, "probe_all")
    def test_load_or_probe_probes_if_cache_expired(self, mock_probe_all, mock_cap_file):
        mock_cap_file.exists.return_value = True
        probe = CapabilityProbe.get()
        
        expired_data = {
            "_timestamp": int(time.time()) - (probe.CACHE_VALID_SECONDS + 100),
            "gpu": {"test": True}
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(expired_data))):
            probe.load_or_probe()
            
        mock_probe_all.assert_called_once()


class TestProbingLogic:
    
    @patch("shutil.which")
    @patch("os.walk")
    @patch("os.path.exists")
    @patch("subprocess.run")
    def test_probe_gpu(self, mock_run, mock_exists, mock_walk, mock_which):
        # Setup mocks
        mock_which.side_effect = lambda x: "/usr/bin/" + x if x in ("prime-select", "nvidia-smi") else None
        
        # Simulate /sys/bus/pci/devices/0000:01:00.0/power/control = "auto"
        mock_walk.return_value = [
            ("/sys/bus/pci/devices/0000:01:00.0", [], ["power/control", "vendor"])
        ]
        
        # Simulate mux switch
        mock_exists.side_effect = lambda x: x == "/sys/kernel/debug/vgaswitcheroo/switch"
        
        # Simulate nvidia-smi power limit support
        mock_proc = MagicMock()
        mock_proc.stdout = "Power Management: Supported"
        mock_run.return_value = mock_proc
        
        # We need another mock for reading the "vendor" file
        with patch("builtins.open", mock_open(read_data="0x10de\n")):
            probe = CapabilityProbe.get()
            gpu_caps = probe._probe_gpu()
            
        assert gpu_caps["prime_select"] is True
        assert gpu_caps["nvidia_smi"] is True
        assert gpu_caps["pci_runtime_pm"] is True
        assert gpu_caps["mux_switch"] is True
        assert gpu_caps["nvidia_power_limit"] is True

    @patch("os.path.exists")
    def test_probe_power(self, mock_exists):
        # Simulate some power features
        def fake_exists(path):
            return path in [
                "/sys/firmware/acpi/platform_profile",
                "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            ]
        mock_exists.side_effect = fake_exists
        
        probe = CapabilityProbe.get()
        power_caps = probe._probe_power()
        
        assert power_caps["platform_profile"] is True
        assert power_caps["cpu_governor"] is True
        assert power_caps["intel_pstate"] is False
        assert power_caps["amd_pstate"] is False
