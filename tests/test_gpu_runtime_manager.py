import pytest
from unittest.mock import patch, MagicMock

from loq_control.core.gpu_runtime_manager import GPURuntimeManager
from loq_control.core.state_manager import StateManager
from loq_control.core.capability_probe import CapabilityProbe

@pytest.fixture(autouse=True)
def reset_managers():
    GPURuntimeManager._instance = None
    StateManager.reset()
    CapabilityProbe._instance = None
    yield

class TestGPURuntimeManager:

    @patch("loq_control.core.gpu_runtime_manager.subprocess.run")
    def test_gpu_in_use(self, mock_run):
        # We need to simulate init properly without scanning real PCI
        with patch.object(GPURuntimeManager, "_detect_nvidia_pci_path", return_value="/fake/pci"):
            mgr = GPURuntimeManager.get()
        
        # Test 1: nvidia-smi returns a pid
        mock_proc_smi = MagicMock()
        mock_proc_smi.stdout = "1234\n"
        mock_run.return_value = mock_proc_smi
        
        assert mgr.gpu_in_use() is True
        
        # Test 2: nvidia-smi empty, but lsof returns a pid
        mock_proc_empty = MagicMock()
        mock_proc_empty.stdout = ""
        mock_proc_lsof = MagicMock()
        mock_proc_lsof.stdout = "4321 user..."
        mock_run.side_effect = [mock_proc_empty, mock_proc_lsof]
        
        assert mgr.gpu_in_use() is True

        # Test 3: empty
        mock_run.side_effect = [mock_proc_empty, mock_proc_empty]
        assert mgr.gpu_in_use() is False

    @patch("loq_control.core.gpu_runtime_manager.time.sleep")
    @patch("loq_control.core.gpu_runtime_manager.subprocess.run")
    @patch("loq_control.core.gpu_runtime_manager.Path")
    def test_suspend_gpu_success(self, mock_path, mock_run, mock_sleep):
        # 1. Setup capabilities
        mock_caps = {"gpu": {"pci_runtime_pm": True}}
        with patch.object(CapabilityProbe, "load_or_probe", return_value=mock_caps):
            with patch.object(GPURuntimeManager, "_detect_nvidia_pci_path", return_value="/fake/pci"):
                mgr = GPURuntimeManager.get()

        # 2. Mock usage to False
        mgr.gpu_in_use = MagicMock(return_value=False)
        
        # 3. Path mock for Power Control write
        mock_power_control = MagicMock()
        mock_power_control.exists.return_value = True
        # Path('/fake/pci') / 'power' / 'control'
        mock_path.return_value.__truediv__.return_value.__truediv__.return_value = mock_power_control
        
        # 4. Act
        success = mgr.suspend_gpu()
        
        assert success is True
        assert mgr.gpu_state == "SUSPENDED"
        mock_run.assert_called_with(["prime-select", "intel"], stdout=-3, stderr=-3) # subprocess.DEVNULL
        mock_power_control.write_text.assert_called_with("auto")
        assert StateManager().get("gpu_mode") == "integrated"

    def test_suspend_gpu_fails_if_no_capability(self):
        mock_caps = {"gpu": {"pci_runtime_pm": False}}
        with patch.object(CapabilityProbe, "load_or_probe", return_value=mock_caps):
            with patch.object(GPURuntimeManager, "_detect_nvidia_pci_path", return_value="/fake/pci"):
                mgr = GPURuntimeManager.get()
        
        assert mgr.suspend_gpu() is False
