import pytest
from unittest.mock import MagicMock
from loq_control.core.state_manager import StateManager
from loq_control.services.hardware_service import HardwareService
from loq_control.core.fnq_sync import FnQSync

class TestFnQSync:
    def test_sync_quiet_profile(self):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        hw.apply_preset = MagicMock()
        
        # Clean up any lingering singletons
        FnQSync._instance = None
        sync = FnQSync.init(sm, hw)
        
        # Simulate hardware event
        sm.request_transition("platform_profile", "quiet", source="udev")
        hw.apply_preset.assert_called_with("battery", source="fnq_sync")
        assert sm.can_daemon_act() is True

    def test_sync_ignores_gui_events(self):
        sm = StateManager(debounce_ms=0)
        hw = HardwareService(state=sm)
        hw.apply_preset = MagicMock()
        
        FnQSync._instance = None
        sync = FnQSync.init(sm, hw)
        
        sm.request_transition("platform_profile", "performance", source="gui")
        hw.apply_preset.assert_not_called()
