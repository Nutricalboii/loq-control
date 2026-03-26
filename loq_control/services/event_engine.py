"""
Event Engine — replaces polling with Linux kernel events.

Monitors:
  - AC adapter plug/unplug  (pyudev → fallback to sysfs poll)
  - Suspend/resume           (DBus login1 → best-effort)

Runs in its own daemon thread.  On event → StateManager → HardwareService.
"""

import os
import threading
import time
from typing import Optional

from loq_control.core.logger import LoqLogger
from loq_control.core.state_manager import StateManager

log = LoqLogger.get()

# ---------------------------------------------------------------------------
# Charger detection (sysfs fallback — always works)
# ---------------------------------------------------------------------------

_AC_PATHS = [
    "/sys/class/power_supply/AC0/online",
    "/sys/class/power_supply/ADP0/online",
    "/sys/class/power_supply/ADP1/online",
    "/sys/class/power_supply/ACAD/online",
]


def _read_charger_state() -> Optional[bool]:
    """Read AC adapter state from sysfs.  Returns None if unreadable."""
    for path in _AC_PATHS:
        try:
            with open(path, "r") as f:
                return f.read().strip() == "1"
        except (OSError, FileNotFoundError):
            continue
    return None

# ---------------------------------------------------------------------------
# Platform Profile (Fn+Q) detection
# ---------------------------------------------------------------------------

_PLATFORM_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"

def _read_platform_profile() -> Optional[str]:
    """Read hardware platform profile to detect Fn+Q external presses."""
    try:
        with open(_PLATFORM_PROFILE_PATH, "r") as f:
            return f.read().strip()
    except (OSError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# Event Engine
# ---------------------------------------------------------------------------

class EventEngine:
    """Lightweight event monitor thread."""

    def __init__(
        self,
        state: StateManager,
        poll_interval: float = 2.0,
    ):
        self._state = state
        self._poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._udev_monitor = None

        # Try to set up pyudev for instant charger events
        self._use_udev = False
        try:
            import pyudev
            ctx = pyudev.Context()
            self._udev_monitor = pyudev.Monitor.from_netlink(ctx)
            self._udev_monitor.filter_by(subsystem="power_supply")
            self._use_udev = True
            log.events("info", "EventEngine: pyudev available — using kernel events for charger")
        except ImportError:
            log.events("warn", 
                "EventEngine: pyudev not installed — falling back to %ss poll",
                self._poll_interval,
            )
        except Exception as e:
            log.events("warn", "EventEngine: pyudev setup failed (%s) — using poll", e)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="event-engine")
        self._thread.start()
        log.events("info", "EventEngine started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        log.events("info", "EventEngine stopped")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run(self):
        # Seed initial charger state
        initial = _read_charger_state()
        if initial is not None:
            self._state.force_set("charger_connected", initial)
            log.events("info", "Initial charger state: %s", initial)

        if self._use_udev:
            self._run_udev()
        else:
            self._run_poll()

    def _run_udev(self):
        """Block on udev events (instant, no CPU waste)."""
        import pyudev
        self._udev_monitor.start()

        while not self._stop.is_set():
            # poll with timeout so we can stop cleanly
            device = self._udev_monitor.poll(timeout=2)
            if device is None:
                continue

            # Re-read sysfs to get consolidated state
            new_state = _read_charger_state()
            if new_state is not None:
                old = self._state.get("charger_connected")
                if new_state != old:
                    self._state.force_set("charger_connected", new_state)
                    log.events("info", "Charger event: %s → %s", old, new_state)
                    
            new_prof = _read_platform_profile()
            if new_prof is not None:
                old_prof = self._state.get("platform_profile")
                if new_prof != old_prof:
                    self._state.force_set("platform_profile", new_prof)
                    log.events("info", "Fn+Q profile event (udev): %s → %s", old_prof, new_prof)

    def _run_poll(self):
        """Fallback: poll sysfs at a fixed interval."""
        while not self._stop.is_set():
            new_state = _read_charger_state()
            if new_state is not None:
                old = self._state.get("charger_connected")
                if new_state != old:
                    self._state.force_set("charger_connected", new_state)
                    log.events("info", "Charger poll: %s → %s", old, new_state)
                    
            new_prof = _read_platform_profile()
            if new_prof is not None:
                old_prof = self._state.get("platform_profile")
                if new_prof != old_prof:
                    self._state.force_set("platform_profile", new_prof)
                    log.events("info", "Fn+Q profile event (poll): %s → %s", old_prof, new_prof)

            self._stop.wait(self._poll_interval)
