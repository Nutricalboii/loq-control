"""
Auto GPU service — switches GPU mode based on charger state.

Respects manual override via StateManager.can_daemon_act().
Triggered by EventEngine charger state changes, with a fallback poll loop.
"""

import time
import threading
from typing import Optional

from loq_control.core.state_manager import StateManager
from loq_control.core.logger import get_logger
from loq_control.core.gpu_runtime_manager import GPURuntimeManager

log = get_logger("loq-control.auto-gpu")


class AutoGPU:
    """
    Watches charger_connected state and auto-switches GPU mode:
      - On AC  → hybrid (or nvidia if user configured it)
      - On bat → integrated

    Only acts if StateManager.can_daemon_act() is True.
    """

    def __init__(
        self,
        state: StateManager,
        hw_service=None,
        check_interval: float = 10.0,
    ):
        self._state = state
        self._hw = hw_service        # set by daemon after HardwareService init
        self._interval = check_interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Subscribe to state changes for instant reaction
        self._state.subscribe(self._on_state_change)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="auto-gpu"
        )
        self._thread.start()
        log.info("AutoGPU started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        log.info("AutoGPU stopped")

    def set_hw_service(self, hw_service):
        self._hw = hw_service

    # ------------------------------------------------------------------
    # Reactive path (instant)
    # ------------------------------------------------------------------

    def _on_state_change(self, key, old_val, new_val, source):
        """Called by StateManager when any state key changes."""
        if key != "charger_connected" or source == "force":
            return
        if not self._state.can_daemon_act():
            log.info("AutoGPU: charger changed but manual override active, ignoring")
            return
        if self._hw is None:
            return

        mgr = GPURuntimeManager.get()

        if new_val:  # AC plugged
            log.info("AutoGPU: AC connected → switching to hybrid/nvidia")
            if not mgr.resume_gpu(source="daemon"):
                # Fallback
                self._hw.switch_gpu("hybrid", source="daemon")
        else:  # Battery
            log.info("AutoGPU: AC disconnected → switching to integrated")
            if not mgr.suspend_gpu(source="daemon"):
                # Fallback
                self._hw.switch_gpu("integrated", source="daemon")

    # ------------------------------------------------------------------
    # Fallback poll loop
    # ------------------------------------------------------------------

    def _run(self):
        """Fallback loop — in case event engine is not available."""
        while not self._stop.is_set():
            self._stop.wait(self._interval)
