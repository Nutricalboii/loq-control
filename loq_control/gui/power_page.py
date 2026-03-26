import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk
import threading
from typing import Dict

class PowerPage(Gtk.Box):
    def __init__(self, controller, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.set_margin_top(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.ctrl = controller
        self.window = window
        self.profile_widgets: Dict[str, Gtk.Box] = {}
        self._ignore_signals = False

        # --- Heading ---
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label="Power Domain Control", halign=Gtk.Align.START)
        title.add_css_class("heading")
        subtitle = Gtk.Label(label="Optimise performance and thermal efficiency", halign=Gtk.Align.START)
        subtitle.add_css_class("caption")
        title_box.append(title)
        title_box.append(subtitle)
        self.append(title_box)

        # --- Profile Selector ---
        self.append(Gtk.Label(label="System Mode", halign=Gtk.Align.START, margin_top=10, css_classes=["caption"]))
        
        self.profile_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.profile_grid.set_homogeneous(True)
        self.append(self.profile_grid)

        self._add_profile_card("power-saver", "Battery Saver", "Quiet / Low Power", "badge-blue")
        self._add_profile_card("balanced", "Balanced", "Daily / Multitasking", "badge-green")
        self._add_profile_card("performance", "Performance", "Gaming / High Load", "badge-red")

        # --- Battery Intelligence Section ---
        self.append(Gtk.Label(label="Battery Charging Intelligence", halign=Gtk.Align.START, margin_top=20, css_classes=["caption"]))
        
        bat_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        bat_card.add_css_class("industrial-card")
        self.append(bat_card)

        # 1. Conservation Mode
        self.cons_switch = self._add_toggle(bat_card, "Conservation Mode (50-80%)", "conservation_mode", self._on_conservation_toggle)
        # 2. Rapid Charge
        self.rapid_switch = self._add_toggle(bat_card, "Rapid Charge (80% in 60m)", "rapid_charge_active", self._on_rapid_toggle)
        # 3. Smart Overnight Charging
        self.smart_switch = self._add_toggle(bat_card, "Smart Overnight Optimization", "smart_charge_active", self._on_smart_toggle)

        # Wake Time Entry
        wake_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        wake_label = Gtk.Label(label="Target Wake Time", halign=Gtk.Align.START, hexpand=True)
        wake_label.add_css_class("caption")
        self.wake_entry = Gtk.Entry(text=self.ctrl.get("smart_charge_wake_time") or "08:00")
        self.wake_entry.set_placeholder_text("08:00")
        self.wake_entry.set_max_length(5)
        self.wake_entry.set_width_chars(6)
        self.wake_entry.connect("changed", self._on_wake_time_changed)
        wake_box.append(wake_label)
        wake_box.append(self.wake_entry)
        bat_card.append(wake_box)

        # Health Info
        self.health_label = Gtk.Label(label="Health: Calculating...", halign=Gtk.Align.START)
        self.health_label.add_css_class("dim-label")
        bat_card.append(self.health_label)

        # Initial Sync
        self.update_stats()

        # Subscribe to State Changes (for Fn+Q support)
        self.ctrl.subscribe(self._on_state_changed)

    def _add_profile_card(self, key, title, desc, badge_class):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("profile-card")
        card.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        
        # Click detection
        gesture = Gtk.GestureClick()
        gesture.connect("released", lambda *args: self._power_switch(key))
        card.add_controller(gesture)

        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=title, halign=Gtk.Align.START, hexpand=True)
        lbl.set_css_classes(["caption"])
        top_box.append(lbl)

        badge = Gtk.Label(label="ACTIVE")
        badge.set_css_classes(["status-badge", badge_class])
        badge.set_valign(Gtk.Align.CENTER)
        badge.set_visible(False)
        top_box.append(badge)

        card.append(top_box)
        
        sub = Gtk.Label(label=desc, halign=Gtk.Align.START)
        sub.set_css_classes(["caption-dim"])
        card.append(sub)

        self.profile_grid.append(card)
        self.profile_widgets[key] = {"card": card, "badge": badge}

    def _add_toggle(self, parent, label, state_key, callback):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=label, halign=Gtk.Align.START, hexpand=True)
        lbl.add_css_class("caption")
        sw = Gtk.Switch(active=bool(self.ctrl.get(state_key)))
        sw.connect("state-set", callback)
        box.append(lbl)
        box.append(sw)
        parent.append(box)
        return sw

    def _on_state_changed(self, key, old, new, source):
        """React to StateManager changes (Fn+Q or Daemon changes)."""
        if key in ("power_profile", "conservation_mode", "rapid_charge_active", "smart_charge_active"):
            GLib.idle_add(self.update_stats)

    def update_stats(self):
        """Update the UI to reflect current stateManager values."""
        if self._ignore_signals:
            return

        self._ignore_signals = True
        try:
            current = self.ctrl.get("power_profile")
            for key, widgets in self.profile_widgets.items():
                if key == current:
                    widgets["card"].add_css_class("profile-active")
                    widgets["badge"].set_visible(True)
                else:
                    widgets["card"].remove_css_class("profile-active")
                    widgets["badge"].set_visible(False)
            
            # Update switches
            self.cons_switch.set_active(bool(self.ctrl.get("conservation_mode")))
            self.rapid_switch.set_active(bool(self.ctrl.get("rapid_charge_active")))
            self.smart_switch.set_active(bool(self.ctrl.get("smart_charge_active")))
        finally:
            self._ignore_signals = False

    def _on_conservation_toggle(self, switch, state):
        if self._ignore_signals:
            return False

        switch.set_sensitive(False)
        def _do():
            res = self.ctrl.set_conservation(state)
            def _done():
                if not res.success:
                    self.window._show_error(res.message)
                self._ignore_signals = True
                switch.set_active(bool(self.ctrl.get("conservation_mode")))
                self._ignore_signals = False
                switch.set_sensitive(True)
            GLib.idle_add(_done)
        
        threading.Thread(target=_do, daemon=True).start()
        return True # Stop default signal emission

    def _on_rapid_toggle(self, switch, state):
        if self._ignore_signals:
            return False

        switch.set_sensitive(False)
        def _do():
            res = self.ctrl.set_rapid_charge(state)
            def _done():
                if not res.success:
                    self.window._show_error(res.message)
                self._ignore_signals = True
                switch.set_active(bool(self.ctrl.get("rapid_charge_active")))
                self._ignore_signals = False
                switch.set_sensitive(True)
            GLib.idle_add(_done)
        
        threading.Thread(target=_do, daemon=True).start()
        return True # Stop default signal emission

    def _on_smart_toggle(self, switch, state):
        if self._ignore_signals:
            return False
        self.ctrl.update_battery_settings({"smart_charge_enabled": state})
        return False

    def _on_wake_time_changed(self, entry):
        text = entry.get_text()
        if len(text) == 5 and ":" in text:
            self.ctrl.update_battery_settings({"wake_time": text})

    def _power_switch(self, profile: str):
        if self.ctrl.get("power_profile") == profile:
            return

        self.set_sensitive(False)
        
        # Optimistic UI update
        self.ctrl._state.force_set("power_profile", profile)
        self.update_stats()

        def _do():
            try:
                result = self.ctrl.set_power_profile(profile)
                if not result.success:
                    GLib.idle_add(self.window._show_error, result.message)
            finally:
                GLib.idle_add(lambda: self.set_sensitive(True))
                GLib.idle_add(self.update_stats)

        threading.Thread(target=_do, daemon=True).start()
