import pytest
from unittest.mock import patch, MagicMock

from loq_control.core.cpu_power_manager import CPUPowerManager
from loq_control.core.state_manager import StateManager
from loq_control.core.capability_probe import CapabilityProbe

@pytest.fixture(autouse=True)
def reset_managers():
    CPUPowerManager._instance = None
    StateManager.reset()
    CapabilityProbe._instance = None
    yield

class TestCPUPowerManager:

    def test_detect_vendor_intel(self):
        with patch("loq_control.core.cpu_power_manager.Path.read_text", return_value="vendor_id : GenuineIntel\n"):
            mgr = CPUPowerManager.get()
            assert mgr.cpu_vendor == "intel"
            
    def test_detect_vendor_amd(self):
        with patch("loq_control.core.cpu_power_manager.Path.read_text", return_value="vendor_id : AuthenticAMD\n"):
            mgr = CPUPowerManager.get()
            assert mgr.cpu_vendor == "amd"

    @patch("loq_control.core.cpu_power_manager.time.sleep")
    def test_set_intel_limits(self, mock_sleep):
        with patch.object(CPUPowerManager, "_detect_vendor", return_value="intel"):
            # Set rapl_path to a MagicMock safely
            mock_rapl_path = MagicMock()
            
            with patch.object(CPUPowerManager, "_detect_intel_rapl", return_value=mock_rapl_path):
                mgr = CPUPowerManager.get()
                
                # Mock the path division to return mock files
                mock_pl1 = MagicMock()
                mock_pl2 = MagicMock()
                mock_pl1.exists.return_value = True
                mock_pl2.exists.return_value = True
                
                def path_div(x):
                    if x == "constraint_0_power_limit_uw": return mock_pl1
                    if x == "constraint_1_power_limit_uw": return mock_pl2
                    return MagicMock()
                mock_rapl_path.__truediv__.side_effect = path_div
                
                success = mgr.set_intel_limits(15, 25)
                
                assert success is True
                mock_pl1.write_text.assert_called_with("15000000")
                mock_pl2.write_text.assert_called_with("25000000")

    @patch("loq_control.core.cpu_power_manager.time.sleep")
    def test_set_amd_boost(self, mock_sleep):
        with patch.object(CPUPowerManager, "_detect_vendor", return_value="amd"):
            with patch.object(CPUPowerManager, "_detect_intel_rapl", return_value=None):
                mgr = CPUPowerManager.get()
                
                with patch("loq_control.core.cpu_power_manager.Path") as mock_path_cls:
                    mock_boost_file = MagicMock()
                    mock_boost_file.exists.return_value = True
                    mock_path_cls.return_value = mock_boost_file
                    
                    success = mgr.set_amd_boost(True)
                    assert success is True
                    mock_boost_file.write_text.assert_called_with("1")
                    
                    success = mgr.set_amd_boost(False)
                    assert success is True
                    mock_boost_file.write_text.assert_called_with("0")

    def test_apply_profile_routes_correctly_intel(self):
        with patch.object(CPUPowerManager, "_detect_vendor", return_value="intel"):
            mgr = CPUPowerManager.get()
            mgr.set_intel_limits = MagicMock(return_value=True)
            
            mgr.apply_profile("performance")
            mgr.set_intel_limits.assert_called_with(45, 65, "gui")
            
    def test_apply_profile_routes_correctly_amd(self):
        with patch.object(CPUPowerManager, "_detect_vendor", return_value="amd"):
            mgr = CPUPowerManager.get()
            mgr.set_amd_boost = MagicMock(return_value=True)
            
            mgr.apply_profile("quiet")
            mgr.set_amd_boost.assert_called_with(False, "gui")
