import subprocess
import os
import threading
import time
import json

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

from loq_control.core.custom_profile import CustomProfileConfig, CustomProfileApplicator

PROFILE_CYCLE_ORDER = ["quiet", "balanced", "performance", "custom"]

PROFILE_LED_MAP = {
    "quiet":       "blue",
    "balanced":    "white",
    "performance": "red",
    "custom":      "purple",
}

PLATFORM_PROFILE_MAP = {
    "quiet":       "low-power",
    "balanced":    "balanced",
    "performance": "performance",
    "custom":      "performance",
}

PLATFORM_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"
AC_ONLINE_PATH = "/sys/class/power_supply/AC/online"
STATE_PATH = os.path.expanduser("~/.config/loq-control/active_profile.json")


class PowerGuard:

    def __init__(self, profile_switch_callback):
        self._callback = profile_switch_callback
        self._on_ac = self._read_ac_status()
        self._monitor_thread = None
        self._running = False

    def _read_ac_status(self):
        try:
            with open(AC_ONLINE_PATH) as f:
                return f.read().strip() == "1"
        except Exception:
            return True

    def is_on_ac(self):
        return self._read_ac_status()

    def start_monitoring(self):
        if DBUS_AVAILABLE:
            self._start_upower_listener()
        else:
            self._start_poll_monitor()

    def _start_upower_listener(self):
        def listener_thread():
            try:
                DBusGMainLoop(set_as_default=True)
                bus = dbus.SystemBus()
                bus.add_signal_receiver(
                    self._on_upower_signal,
                    signal_name="PropertiesChanged",
                    dbus_interface="org.freedesktop.DBus.Properties",
                    path="/org/freedesktop/UPower/devices/line_power_AC",
                )
                from gi.repository import GLib
                loop = GLib.MainLoop()
                loop.run()
            except Exception:
                self._start_poll_monitor()

        t = threading.Thread(target=listener_thread, daemon=True)
        t.start()

    def _on_upower_signal(self, interface, changed_props, invalidated):
        if "Online" in changed_props:
            now_on_ac = bool(changed_props["Online"])
            was_on_ac = self._on_ac
            self._on_ac = now_on_ac
            if was_on_ac and not now_on_ac:
                self._callback("ac_disconnected")
            elif not was_on_ac and now_on_ac:
                self._callback("ac_connected")

    def _start_poll_monitor(self):
        self._running = True

        def poll():
            while self._running:
                current = self._read_ac_status()
                if current != self._on_ac:
                    prev = self._on_ac
                    self._on_ac = current
                    if prev and not current:
                        self._callback("ac_disconnected")
                    elif not prev and current:
                        self._callback("ac_connected")
                time.sleep(3)

        t = threading.Thread(target=poll, daemon=True)
        t.start()

    def stop(self):
        self._running = False


class ProfileCycleManager:

    def __init__(self, led_controller=None, daemon_apply_fn=None):
        self._led = led_controller
        self._daemon_apply = daemon_apply_fn
        self._current_idx = 1
        self._guard = PowerGuard(self._on_power_event)
        self._load_saved_profile()

    def _load_saved_profile(self):
        try:
            with open(STATE_PATH) as f:
                data = json.load(f)
                profile = data.get("active_profile", "balanced")
                if profile in PROFILE_CYCLE_ORDER:
                    self._current_idx = PROFILE_CYCLE_ORDER.index(profile)
        except Exception:
            self._current_idx = 1

    def _save_active_profile(self, profile):
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump({"active_profile": profile}, f)

    def start(self):
        self._guard.start_monitoring()

    def stop(self):
        self._guard.stop()

    def cycle_next(self):
        next_idx = (self._current_idx + 1) % len(PROFILE_CYCLE_ORDER)
        next_profile = PROFILE_CYCLE_ORDER[next_idx]

        if next_profile == "custom" and not self._guard.is_on_ac():
            next_idx = (next_idx + 1) % len(PROFILE_CYCLE_ORDER)
            next_profile = PROFILE_CYCLE_ORDER[next_idx]

        self.switch_to(next_profile)

    def switch_to(self, profile: str):
        if profile == "custom" and not self._guard.is_on_ac():
            profile = "balanced"

        self._current_idx = PROFILE_CYCLE_ORDER.index(profile)
        self._apply_profile(profile)
        self._save_active_profile(profile)

    def _apply_profile(self, profile: str):
        self._write_platform_profile(PLATFORM_PROFILE_MAP[profile])

        if self._led:
            self._led.set_color(PROFILE_LED_MAP[profile])

        if profile == "custom":
            config = CustomProfileConfig.load()
            applicator = CustomProfileApplicator(config)
            applicator.apply_all()

        if self._daemon_apply:
            self._daemon_apply(profile)

    def _write_platform_profile(self, profile_str: str):
        try:
            with open(PLATFORM_PROFILE_PATH, "w") as f:
                f.write(profile_str)
        except PermissionError:
            try:
                subprocess.run(
                    ["pkexec", "tee", PLATFORM_PROFILE_PATH],
                    input=profile_str,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                pass
        except Exception:
            pass

    def _on_power_event(self, event: str):
        if event == "ac_disconnected":
            current_profile = PROFILE_CYCLE_ORDER[self._current_idx]
            if current_profile == "custom":
                self.switch_to("balanced")

    @property
    def current_profile(self):
        return PROFILE_CYCLE_ORDER[self._current_idx]

    @property
    def current_led_color(self):
        return PROFILE_LED_MAP[self.current_profile]
