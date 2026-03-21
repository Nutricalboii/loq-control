"""
Unit tests for services/hardware_service.py

All hardware writes are mocked — no real subprocess calls.
"""

import threading
import pytest
from unittest.mock import patch, MagicMock

from loq_control.core.state_manager import StateManager
from loq_control.services.hardware_service import HardwareService, HWResult


@pytest.fixture(autouse=True)
def fresh():
    StateManager.reset()
    HardwareService.reset()
    yield
    StateManager.reset()
    HardwareService.reset()


class TestGPUSwitch:

    @patch("loq_control.core.gpu.set_integrated", return_value=True)
    def test_switch_integrated_success(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.switch_gpu("integrated", source="test")
        assert r.success is True
        assert r.needs_reboot is True
        assert sm.get("gpu_mode") == "integrated"
        mock_set.assert_called_once()

    @patch("loq_control.core.gpu.set_nvidia", return_value=False)
    def test_switch_nvidia_failure(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.switch_gpu("nvidia", source="test")
        assert r.success is False
        assert "failed" in r.message.lower()
        # State should NOT have changed
        assert sm.get("gpu_mode") == "hybrid"

    def test_invalid_mode_rejected(self):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.switch_gpu("RTX_9090", source="test")
        assert r.success is False

    @patch("loq_control.core.gpu.set_integrated", return_value=True)
    @patch("loq_control.core.gpu.set_nvidia", return_value=True)
    def test_concurrent_switch_rejected(self, mock_nv, mock_int):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)

        # Manually lock to simulate another transition in progress
        sm.lock_transition("other")
        r = hw.switch_gpu("nvidia", source="test")
        assert r.success is False
        assert "transition" in r.message.lower()
        sm.unlock_transition()

    @patch("loq_control.core.gpu.set_integrated", return_value=True)
    def test_switch_sets_manual_override(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        hw.switch_gpu("integrated", source="gui")
        assert sm.get("manual_override") is True

    @patch("loq_control.core.gpu.set_integrated", return_value=True)
    def test_daemon_switch_no_manual_override(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        hw.switch_gpu("integrated", source="daemon")
        assert sm.get("manual_override") is False


class TestPowerProfile:

    @patch("loq_control.core.power.performance", return_value=True)
    def test_set_performance(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.set_power_profile("performance", source="test")
        assert r.success is True
        assert sm.get("power_profile") == "performance"

    @patch("loq_control.core.power.battery", return_value=False)
    def test_profile_failure_no_state_change(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.set_power_profile("power-saver", source="test")
        assert r.success is False
        assert sm.get("power_profile") == "balanced"  # unchanged


class TestFanMode:

    @patch("loq_control.core.fan.performance", return_value=True)
    def test_set_performance(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.set_fan_mode("performance", source="test")
        assert r.success is True
        assert sm.get("fan_mode") == "performance"


class TestConservation:

    @patch("loq_control.core.battery.conservation_on", return_value=True)
    def test_conservation_on(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.set_conservation(True, source="test")
        assert r.success is True
        assert sm.get("conservation_mode") is True


class TestPresets:

    @patch("loq_control.core.power.battery", return_value=True)
    @patch("loq_control.core.fan.quiet", return_value=True)
    def test_battery_preset(self, mock_fan, mock_power):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        r = hw.apply_preset("battery", source="test")
        assert r.success is True
        assert sm.get("power_profile") == "power-saver"
        assert sm.get("fan_mode") == "quiet"


class TestTransitionUnlockOnError:

    @patch("loq_control.core.gpu.set_nvidia", side_effect=RuntimeError("kaboom"))
    def test_unlock_on_exception(self, mock_set):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        try:
            hw.switch_gpu("nvidia", source="test")
        except RuntimeError:
            pass
        # Transition must be unlocked even if exception happened
        assert sm.in_transition is False
