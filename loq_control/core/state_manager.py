"""
Central State Manager — single source of truth for all system state.

Thread-safe singleton with locking, debounce, manual override tracking,
and observer pattern for reactive UI updates.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from loq_control.core.logger import LoqLogger

log = LoqLogger.get()


# ---------------------------------------------------------------------------
# Result type returned from transition attempts
# ---------------------------------------------------------------------------

@dataclass
class TransitionResult:
    """Outcome of a state transition request."""
    success: bool
    message: str
    previous_value: Any = None
    new_value: Any = None


# ---------------------------------------------------------------------------
# State Manager
# ---------------------------------------------------------------------------

class StateManager:
    """Thread-safe singleton that tracks all hardware/system state."""

    _instance: Optional["StateManager"] = None
    _init_lock = threading.Lock()

    # ---- Valid values for each key ----
    VALID_VALUES = {
        "gpu_mode": {"integrated", "hybrid", "nvidia"},
        "power_profile": {"power-saver", "balanced", "performance"},
        "fan_mode": {"quiet", "balanced", "performance", "custom"},
        "charger_connected": {True, False},
        "conservation_mode": {True, False},
        "manual_override": {True, False},
        "platform_profile": {"quiet", "balanced", "performance"},
        "smart_fan_active": {True, False},
    }

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, debounce_ms: int = 500):
        # Guard against re-init on repeated __init__ calls
        if hasattr(self, "_initialised"):
            return
        self._initialised = True

        self._lock = threading.RLock()
        self._transition_lock = threading.Lock()
        self._in_transition = False
        self._debounce_s = debounce_ms / 1000.0

        # ---- Core state ----
        self._state: Dict[str, Any] = {
            "gpu_mode": "hybrid",           # sensible default
            "power_profile": "balanced",
            "fan_mode": "balanced",
            "charger_connected": True,
            "conservation_mode": False,
            "manual_override": False,
            "platform_profile": "balanced",
            "smart_fan_active": False,
        }

        self._last_transition_ts: float = 0.0
        self._subscribers: List[Callable] = []

    # ------------------------------------------------------------------
    # Reset (for testing only)
    # ------------------------------------------------------------------

    @classmethod
    def reset(cls):
        """Destroy the singleton so a fresh instance can be created.
        Intended for unit tests only."""
        with cls._init_lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Return a *snapshot* (copy) of current state."""
        with self._lock:
            return dict(self._state)

    def get(self, key: str) -> Any:
        """Return a single state value."""
        with self._lock:
            return self._state.get(key)

    @property
    def in_transition(self) -> bool:
        with self._lock:
            return self._in_transition

    @property
    def last_transition_ts(self) -> float:
        with self._lock:
            return self._last_transition_ts

    def report_failure(self, key: str, value: Any, error: str):
        """Notify the Safety Supervisor of a hardware write failure."""
        from loq_control.core.safety_supervisor import SafetySupervisor
        supervisor = SafetySupervisor.get()
        if supervisor:
            supervisor.handle_failure(key, value, error)

    # ------------------------------------------------------------------
    # Transitions (guarded)
    # ------------------------------------------------------------------

    def request_transition(
        self, key: str, value: Any, source: str = "unknown"
    ) -> TransitionResult:
        """
        Request a state change.

        Checks:
          1. Safety Supervisor approval (Rate limits, Thermal failsafe)
          2. Key is valid
          3. Value is valid for that key
          4. Not currently in a transition
          5. Debounce window has passed

        Returns TransitionResult indicating success/failure.
        """
        # 0. Safety Gatekeeper
        from loq_control.core.safety_supervisor import SafetySupervisor
        supervisor = SafetySupervisor.get()
        if supervisor and not supervisor.check_transition(key, value, source):
            return TransitionResult(
                success=False,
                message=f"Safety Check Failed — request from '{source}' blocked",
            )

        with self._lock:

            # Validate key
            if key not in self._state:
                return TransitionResult(
                    success=False,
                    message=f"Unknown state key: {key}",
                )

            # Validate value
            if key in self.VALID_VALUES and value not in self.VALID_VALUES[key]:
                return TransitionResult(
                    success=False,
                    message=f"Invalid value '{value}' for key '{key}'",
                )

            # Check transition lock
            if self._in_transition:
                return TransitionResult(
                    success=False,
                    message=f"Transition in progress — request from '{source}' rejected",
                )

            # Debounce check
            elapsed = time.monotonic() - self._last_transition_ts
            if elapsed < self._debounce_s:
                return TransitionResult(
                    success=False,
                    message=(
                        f"Debounce active ({elapsed:.0f}ms < {self._debounce_s*1000:.0f}ms) "
                        f"— request from '{source}' rejected"
                    ),
                )

            # No-op if value unchanged
            previous = self._state[key]
            if previous == value:
                return TransitionResult(
                    success=True,
                    message=f"'{key}' already set to '{value}'",
                    previous_value=previous,
                    new_value=value,
                )

            # Apply
            self._state[key] = value
            self._last_transition_ts = time.monotonic()
            log.daemon("debug", f"State transition accepted: {key} -> {value} by {source}")

        # Notify outside lock to avoid deadlocks
        self._notify_subscribers(key, previous, value, source)

        return TransitionResult(
            success=True,
            message=f"[{source}] {key}: {previous} → {value}",
            previous_value=previous,
            new_value=value,
        )

    def force_set(self, key: str, value: Any):
        """
        Unconditionally set a value — used internally by HardwareService
        after confirming a hardware write succeeded.  Bypasses debounce and
        transition lock, but still validates key/value.
        """
        with self._lock:
            if key not in self._state:
                return
            if key in self.VALID_VALUES and value not in self.VALID_VALUES[key]:
                return
            previous = self._state[key]
            self._state[key] = value
        self._notify_subscribers(key, previous, value, "force")

    # ------------------------------------------------------------------
    # Transition lock (used by HardwareService)
    # ------------------------------------------------------------------

    def lock_transition(self, source: str = "unknown") -> bool:
        """
        Acquire the transition lock.  Returns True if acquired,
        False if already locked.
        """
        # Safety Override: If a transition has been stuck for > 60s, force unlock
        with self._lock:
            if self._in_transition:
                stuck_time = time.monotonic() - self._last_transition_ts
                if stuck_time > 60:
                    log.hardware("warning", f"Transition STUCK for {stuck_time:.1f}s - Force unlocking!")
                    self._in_transition = False
                    try:
                        self._transition_lock.release()
                    except RuntimeError:
                        pass # wasn't locked but flag was True? sync it.

        acquired = self._transition_lock.acquire(blocking=False)
        if acquired:
            with self._lock:
                self._in_transition = True
                self._last_transition_ts = time.monotonic()
            return True
        return False

    def unlock_transition(self):
        """Release the transition lock."""
        with self._lock:
            self._in_transition = False
        try:
            self._transition_lock.release()
        except RuntimeError:
            pass  # wasn't locked

    # ------------------------------------------------------------------
    # Manual override (daemon control)
    # ------------------------------------------------------------------

    def set_manual_override(self):
        """Mark that the user manually chose a mode — daemon should not interfere."""
        with self._lock:
            self._state["manual_override"] = True

    def clear_manual_override(self):
        with self._lock:
            self._state["manual_override"] = False

    def can_daemon_act(self) -> bool:
        """Return True only if no manual override is active and no transition in progress."""
        with self._lock:
            return (
                not self._state["manual_override"]
                and not self._in_transition
            )

    # ------------------------------------------------------------------
    # Observer pattern
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable):
        """
        Register a callback: callback(key, old_value, new_value, source).
        Callbacks are invoked outside the state lock.
        """
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s is not callback]

    def _notify_subscribers(
        self, key: str, old_value: Any, new_value: Any, source: str
    ):
        """Fire all subscriber callbacks (best-effort, never raises)."""
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                log.daemon("info", f"Notifying '{key}' change: {old_value} -> {new_value} (from {source})")
                cb(key, old_value, new_value, source)
            except Exception as e:
                log.daemon("error", f"State observer error: {e}")
                pass  # subscriber errors must never crash the manager
