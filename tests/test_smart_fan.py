import pytest
from unittest.mock import MagicMock, patch
from loq_control.core.smart_fan import CurveEvaluator, SmartFanEngine
from loq_control.core.state_manager import StateManager

class TestCurveEvaluator:
    def test_evaluate_below_min(self):
        curve = CurveEvaluator([(40, 20), (80, 100)])
        assert curve.evaluate(30) == 20

    def test_evaluate_above_max(self):
        curve = CurveEvaluator([(40, 20), (80, 100)])
        assert curve.evaluate(90) == 100

    def test_evaluate_mid(self):
        curve = CurveEvaluator([(40, 20), (80, 100)])
        assert curve.evaluate(60) == 60.0

class TestSmartFanEngine:
    @patch("loq_control.core.smart_fan.fan")
    @patch("loq_control.core.thermal_manager.ThermalManager")
    def test_deadman_switch_triggers_on_high_temp(self, mock_tm_class, mock_fan):
        StateManager.reset()
        sm = StateManager(debounce_ms=0)
        
        # Clean up singletons
        SmartFanEngine.reset()
        engine = SmartFanEngine.init(sm)
        
        # Setup mock telemetry exceeding DEADMAN_TEMP
        mock_tm = MagicMock()
        mock_tm.get_telemetry.return_value = {"cpu": {"temp": 96.0}, "gpu": {"temp": 80.0}}
        mock_tm_class.get.return_value = mock_tm
        
        # Manual invocation representing the safety loop
        engine._trigger_deadman("Test Temp")
        
        # Assert BIOS native fallback was invoked
        mock_fan.performance.assert_called_once()
        assert sm.get("fan_mode") == "performance"
        
        # The daemon state should now correctly reflect the fallback
        assert sm.get("smart_fan_active") is False
