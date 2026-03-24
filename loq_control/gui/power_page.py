import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
import threading

class PowerPage(Gtk.Box):
    def __init__(self, controller, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_top(20)
        self.set_margin_start(20)
        self.ctrl = controller
        self.window = window

        title = Gtk.Label(label="<b>Power Domain Control</b>", use_markup=True, halign=Gtk.Align.START)
        title.add_css_class("heading")
        self.append(title)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("industrial-card")
        self.append(card)

        saver = Gtk.Button(label="Battery Saver")
        balanced = Gtk.Button(label="Balanced")
        perf = Gtk.Button(label="Performance")

        card.append(saver)
        card.append(balanced)
        card.append(perf)

        saver.connect("clicked", lambda x: self._power_switch("power-saver"))
        balanced.connect("clicked", lambda x: self._power_switch("balanced"))
        perf.connect("clicked", lambda x: self._power_switch("performance"))

    def _power_switch(self, profile: str):
        def _do():
            result = self.ctrl.set_power_profile(profile)
            if not result.success:
                GLib.idle_add(self.window._show_error, result.message)

        threading.Thread(target=_do, daemon=True).start()
