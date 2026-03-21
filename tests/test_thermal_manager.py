import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from loq_control.core.thermal_manager import ThermalManager
from loq_control.core.capability_probe import CapabilityProbe

@pytest.fixture(autouse=True)
def reset_managers():
    ThermalManager._instance = None
    CapabilityProbe._instance = None
    yield

class TestThermalManager:

    @patch("loq_control.core.thermal_manager.Path")
    def test_discover_topology(self, mock_path_cls):
        # We need to simulate /sys/class/hwmon and /sys/class/thermal iterdir
        
        # 1. Hwmon chip
        mock_hwmon_dir = MagicMock()
        mock_hwmon_chip1 = MagicMock()
        mock_hwmon_chip1.name = "hwmon0"
        
        mock_name_file = MagicMock()
        mock_name_file.read_text.return_value = "coretemp\n"
        
        # Fan bindings
        mock_fan1_rpm = MagicMock()
        mock_fan1_rpm.exists.return_value = True
        mock_fan1_pwm = MagicMock()
        mock_fan1_pwm.exists.return_value = True

        mock_fan2_rpm = MagicMock()
        mock_fan2_rpm.exists.return_value = False
        
        def hwmon_div(x):
            if x == "name": return mock_name_file
            if x == "fan1_input": return mock_fan1_rpm
            if x == "pwm1": return mock_fan1_pwm
            if x == "fan2_input": return mock_fan2_rpm
            return MagicMock(exists=MagicMock(return_value=False))
            
        mock_hwmon_chip1.__truediv__.side_effect = hwmon_div
        mock_hwmon_dir.exists.return_value = True
        mock_hwmon_dir.iterdir.return_value = [mock_hwmon_chip1]

        # 2. Thermal zone
        mock_thermal_dir = MagicMock()
        mock_zone1 = MagicMock()
        mock_zone1.name = "thermal_zone0"
        
        mock_type_file = MagicMock()
        mock_type_file.read_text.return_value = "x86_pkg_temp\n"
        
        def zone_div(x):
            if x == "type": return mock_type_file
            return MagicMock()
            
        mock_zone1.__truediv__.side_effect = zone_div
        mock_thermal_dir.exists.return_value = True
        mock_thermal_dir.iterdir.return_value = [mock_zone1]

        # Route the Path initializer
        def path_side_effect(p):
            if p == "/sys/class/hwmon": return mock_hwmon_dir
            if p == "/sys/class/thermal": return mock_thermal_dir
            return MagicMock()
            
        mock_path_cls.side_effect = path_side_effect
        
        # Setup Probe so it doesn't fail
        with patch.object(CapabilityProbe, "load_or_probe", return_value={}):
            mgr = ThermalManager.get()
            
        topology = mgr.get_topology()
        
        assert len(topology["hwmon"]) == 1
        assert topology["hwmon"][0]["name"] == "coretemp"
        
        assert len(topology["zones"]) == 1
        assert topology["zones"][0]["type"] == "x86_pkg_temp"
        
        assert len(topology["fans"]) == 1
        assert topology["fans"][0]["chip"] == "coretemp"
        assert topology["fans"][0]["pwm_file"] is not None

    @patch("loq_control.core.thermal_manager.Path")
    def test_read_telemetry(self, mock_path_cls):
        with patch.object(CapabilityProbe, "load_or_probe", return_value={}):
            mgr = ThermalManager.get()
            
            # Inject fake topology
            mock_temp_file = MagicMock()
            mock_temp_file.read_text.return_value = "45000\n" # 45 C
            
            mgr.thermal_zones = [{
                "path": MagicMock(__truediv__=MagicMock(return_value=mock_temp_file)),
                "type": "cpu"
            }]
            
            mock_rpm_file = MagicMock()
            mock_rpm_file.read_text.return_value = "3000\n"
            
            mgr.fans = [{
                "chip": "legion",
                "rpm_file": mock_rpm_file,
                "pwm_file": MagicMock()
            }]
            
            mgr._read_temperatures()
            mgr._read_fans()
            
            telemetry = mgr.get_telemetry()
            
            assert telemetry["temps"]["cpu"] == 45.0
            assert telemetry["fans"][0]["chip"] == "legion"
            assert telemetry["fans"][0]["rpm"] == 3000
            assert telemetry["fans"][0]["controllable"] is True
