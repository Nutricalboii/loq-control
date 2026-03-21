"""
Unit tests for core/state_manager.py

Tests thread safety, debounce, transition locking, manual override,
and observer pattern.
"""

import threading
import time
import pytest

from loq_control.core.state_manager import StateManager, TransitionResult


@pytest.fixture(autouse=True)
def fresh_state():
    """Reset the singleton before each test."""
    StateManager.reset()
    yield
    StateManager.reset()


class TestStateManagerBasics:

    def test_singleton(self):
        a = StateManager(debounce_ms=0)
        b = StateManager(debounce_ms=0)
        assert a is b

    def test_default_state(self):
        sm = StateManager(debounce_ms=0)
        state = sm.get_state()
        assert state["gpu_mode"] == "hybrid"
        assert state["power_profile"] == "balanced"
        assert state["fan_mode"] == "balanced"
        assert state["manual_override"] is False

    def test_get_single_key(self):
        sm = StateManager(debounce_ms=0)
        assert sm.get("gpu_mode") == "hybrid"
        assert sm.get("nonexistent") is None

    def test_get_state_returns_copy(self):
        sm = StateManager(debounce_ms=0)
        s1 = sm.get_state()
        s1["gpu_mode"] = "HACKED"
        assert sm.get("gpu_mode") == "hybrid"


class TestTransitions:

    def test_valid_transition(self):
        sm = StateManager(debounce_ms=0)
        r = sm.request_transition("gpu_mode", "nvidia", source="test")
        assert r.success is True
        assert sm.get("gpu_mode") == "nvidia"
        assert r.previous_value == "hybrid"
        assert r.new_value == "nvidia"

    def test_invalid_key(self):
        sm = StateManager(debounce_ms=0)
        r = sm.request_transition("nonexistent", "value", source="test")
        assert r.success is False
        assert "Unknown" in r.message

    def test_invalid_value(self):
        sm = StateManager(debounce_ms=0)
        r = sm.request_transition("gpu_mode", "RTX_9090", source="test")
        assert r.success is False
        assert "Invalid" in r.message

    def test_noop_if_same_value(self):
        sm = StateManager(debounce_ms=0)
        r = sm.request_transition("gpu_mode", "hybrid", source="test")
        assert r.success is True
        assert "already" in r.message.lower()

    def test_debounce_blocks_rapid_transitions(self):
        sm = StateManager(debounce_ms=1000)  # 1 second debounce
        r1 = sm.request_transition("gpu_mode", "nvidia", source="test")
        assert r1.success is True

        r2 = sm.request_transition("gpu_mode", "integrated", source="test")
        assert r2.success is False
        assert "Debounce" in r2.message

    def test_debounce_allows_after_window(self):
        sm = StateManager(debounce_ms=50)  # 50ms debounce
        r1 = sm.request_transition("gpu_mode", "nvidia", source="test")
        assert r1.success is True

        time.sleep(0.1)  # wait past debounce

        r2 = sm.request_transition("gpu_mode", "integrated", source="test")
        assert r2.success is True


class TestTransitionLocking:

    def test_lock_blocks_transition(self):
        sm = StateManager(debounce_ms=0)
        assert sm.lock_transition("test") is True
        r = sm.request_transition("gpu_mode", "nvidia", source="test")
        assert r.success is False
        assert "in progress" in r.message.lower()
        sm.unlock_transition()

    def test_unlock_allows_transition(self):
        sm = StateManager(debounce_ms=0)
        sm.lock_transition("test")
        sm.unlock_transition()
        r = sm.request_transition("gpu_mode", "nvidia", source="test")
        assert r.success is True

    def test_double_lock_fails(self):
        sm = StateManager(debounce_ms=0)
        assert sm.lock_transition("test") is True
        assert sm.lock_transition("test2") is False
        sm.unlock_transition()


class TestManualOverride:

    def test_set_and_clear(self):
        sm = StateManager(debounce_ms=0)
        assert sm.can_daemon_act() is True

        sm.set_manual_override()
        assert sm.can_daemon_act() is False

        sm.clear_manual_override()
        assert sm.can_daemon_act() is True

    def test_in_transition_blocks_daemon(self):
        sm = StateManager(debounce_ms=0)
        sm.lock_transition("test")
        assert sm.can_daemon_act() is False
        sm.unlock_transition()
        assert sm.can_daemon_act() is True


class TestObservers:

    def test_subscriber_called(self):
        sm = StateManager(debounce_ms=0)
        events = []
        sm.subscribe(lambda k, o, n, s: events.append((k, o, n, s)))
        sm.request_transition("gpu_mode", "nvidia", source="test")
        assert len(events) == 1
        assert events[0] == ("gpu_mode", "hybrid", "nvidia", "test")

    def test_subscriber_error_does_not_crash(self):
        sm = StateManager(debounce_ms=0)

        def bad_cb(k, o, n, s):
            raise RuntimeError("boom")

        sm.subscribe(bad_cb)
        # Should NOT raise
        r = sm.request_transition("gpu_mode", "nvidia", source="test")
        assert r.success is True

    def test_unsubscribe(self):
        sm = StateManager(debounce_ms=0)
        events = []
        cb = lambda k, o, n, s: events.append(1)
        sm.subscribe(cb)
        sm.request_transition("gpu_mode", "nvidia", source="test")
        assert len(events) == 1

        sm.unsubscribe(cb)
        sm.request_transition("gpu_mode", "integrated", source="test")
        assert len(events) == 1  # no new event


class TestThreadSafety:

    def test_concurrent_transitions(self):
        """10 threads all trying to change gpu_mode at once."""
        sm = StateManager(debounce_ms=0)
        results = []
        barrier = threading.Barrier(10)

        def _worker(mode):
            barrier.wait()
            r = sm.request_transition("gpu_mode", mode, source="thread")
            results.append(r)

        modes = ["integrated", "nvidia"] * 5
        threads = [threading.Thread(target=_worker, args=(m,)) for m in modes]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At least one must succeed, and the final state must be valid
        successes = [r for r in results if r.success]
        assert len(successes) >= 1
        assert sm.get("gpu_mode") in ("integrated", "nvidia", "hybrid")


class TestForceSet:

    def test_force_set_bypasses_debounce(self):
        sm = StateManager(debounce_ms=5000)
        sm.request_transition("gpu_mode", "nvidia", source="test")
        # Normally blocked by debounce, but force_set bypasses it
        sm.force_set("gpu_mode", "integrated")
        assert sm.get("gpu_mode") == "integrated"

    def test_force_set_validates(self):
        sm = StateManager(debounce_ms=0)
        sm.force_set("gpu_mode", "RTX_9090")  # invalid — should be silently ignored
        assert sm.get("gpu_mode") == "hybrid"
