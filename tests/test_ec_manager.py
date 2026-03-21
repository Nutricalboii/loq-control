import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from loq_control.core.ec_manager import ECManager
from loq_control.core.capability_probe import CapabilityProbe


@pytest.fixture(autouse=True)
def reset_managers():
    ECManager._instance = None
    CapabilityProbe._instance = None
    yield

class TestECManager:
    @patch("loq_control.core.ec_manager.Path")
    def test_get_topology(self, mock_path):
        with patch.object(CapabilityProbe, "load_or_probe", return_value={}):
            # Setup fake paths
            def path_side_effect(p):
                mock = MagicMock()
                if p == "/sys/bus/platform/drivers/ideapad_acpi":
                    mock.exists.return_value = True
                elif p == "/sys/bus/platform/devices/VPC2004:00":
                    mock.exists.return_value = False
                elif p == "/sys/firmware/acpi/platform_profile":
                    mock.exists.return_value = True
                else:
                    mock.exists.return_value = False
                return mock
                
            mock_path.side_effect = path_side_effect
            
            ec = ECManager.get()
            topology = ec.get_ec_topology()
            
            assert topology["ideapad_acpi_loaded"] is True
            assert topology["hardware_profiles_supported"] is True
            assert topology["vpc_device_found"] is False


    @patch("loq_control.core.ec_manager.Path")
    def test_get_charger_wattage(self, mock_path):
        with patch.object(CapabilityProbe, "load_or_probe", return_value={}):
            # Mock power_supply directory
            mock_ps_dir = MagicMock()
            mock_ps_dir.exists.return_value = True
            
            # Mock ADP1 folder
            mock_adp1 = MagicMock()
            mock_adp1.is_dir.return_value = True
            mock_adp1.name = "ADP1"
            
            # Mock power_now file
            mock_power_now = MagicMock()
            mock_power_now.exists.return_value = True
            mock_power_now.read_text.return_value = "230000000" # 230W
            
            def adp_div(x):
                if x == "power_now": return mock_power_now
                return MagicMock(exists=MagicMock(return_value=False))
            
            mock_adp1.__truediv__.side_effect = adp_div
            
            mock_ps_dir.iterdir.return_value = [mock_adp1]
            
            def path_side_effect(p):
                if p == "/sys/class/power_supply":
                    return mock_ps_dir
                return MagicMock()
                
            mock_path.side_effect = path_side_effect
            
            ec = ECManager.get()
            wattage = ec.get_charger_wattage()
            assert wattage == 230
