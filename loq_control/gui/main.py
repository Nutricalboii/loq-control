"""
LOQ Control Center v2.0.2 — GTK4 Main Window
Architected by Vaibhav Sharma (Nutricalboii): An Unharming Blueprint for LOQ Hardware.

Launches as NORMAL USER. No sudo required.
Hardware writes escalate via pkexec when needed.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk
import threading

from loq_control.gui.controller import AppController
from loq_control.gui.dashboard_page import DashboardPage
from loq_control.gui.gpu_page import GPUPage
from loq_control.gui.power_page import PowerPage
from loq_control.gui.thermals_page import ThermalsPage
from loq_control.gui.log_viewer_page import LogViewerPage
from loq_control.gui.telemetry_page import TelemetryPage
from loq_control.gui.settings import GuiSettings
from loq_control.version import VERSION, AUTHOR


class MainWindow(Gtk.ApplicationWindow):

    def __init__(self, app, ctrl):
        super().__init__(application=app)

        self.set_title(f"LOQ Control Center v{VERSION}")
        self.set_default_size(1100, 700)
        self.ctrl = ctrl
        self.settings = GuiSettings.get()
        
        # Load CSS
        self._load_css()

        # Apply persistence theme
        self._apply_theme(self.settings.get_val("theme"))

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.set_child(root)

        # ================= SIDEBAR =================
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sidebar.set_size_request(220, -1)
        sidebar.add_css_class("sidebar")
        root.append(sidebar)

        lbl = Gtk.Label(label="LOQ CONTROL")
        lbl.add_css_class("heading")
        lbl.set_margin_top(20)
        lbl.set_margin_bottom(20)
        sidebar.append(lbl)

        self._add_nav_button(sidebar, "Dashboard", "dash")
        self._add_nav_button(sidebar, "GPU MUX", "gpu")
        self._add_nav_button(sidebar, "Power Profiles", "power")
        self._add_nav_button(sidebar, "Thermal Layout", "thermals")
        self._add_nav_button(sidebar, "Deep Analysis", "telemetry")
        self._add_nav_button(sidebar, "Live Logs", "logs")

        # ================= THEME SWITCHER =================
        sidebar.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        theme_box.set_margin_start(10)
        theme_box.set_margin_end(10)
        theme_box.set_margin_bottom(10)
        sidebar.append(theme_box)

        theme_lbl = Gtk.Label(label="UI Theme", halign=Gtk.Align.START)
        theme_lbl.add_css_class("caption")
        theme_box.append(theme_lbl)

        theme_combo = Gtk.DropDown.new_from_strings(["System", "Dark", "Light"])
        current_theme = self.settings.get_val("theme").capitalize()
        theme_map = {"System": 0, "Dark": 1, "Light": 2}
        theme_combo.set_selected(theme_map.get(current_theme, 0))
        theme_combo.connect("notify::selected", self._on_theme_changed)
        theme_box.append(theme_combo)

        # Spacer to push credits to the bottom
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar.append(spacer)

        # Developer Credits
        credit_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        credit_box.set_margin_bottom(10)
        credit_box.set_margin_start(10)
        credit_box.set_margin_end(10)
        
        dev_lbl = Gtk.Label(label=f"By {AUTHOR}")
        dev_lbl.add_css_class("caption")
        dev_lbl.set_halign(Gtk.Align.START)
        credit_box.append(dev_lbl)
        
        blue_lbl = Gtk.Label(label=f"Secure Blueprint v{VERSION}")
        blue_lbl.add_css_class("caption-dim")
        blue_lbl.set_halign(Gtk.Align.START)
        credit_box.append(blue_lbl)
        
        sidebar.append(credit_box)

        # ================= STACK =================
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(400)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        root.append(self.stack)

        # ================= PAGES =================
        self.dash_page = DashboardPage(self.ctrl)
        self.gpu_page = GPUPage(self.ctrl, self)
        self.power_page = PowerPage(self.ctrl, self)
        self.thermals_page = ThermalsPage(self.ctrl)
        self.telemetry_page = TelemetryPage(self.ctrl)
        self.logs_page = LogViewerPage(self.ctrl)

        self.stack.add_named(self.dash_page, "dash")
        self.stack.add_named(self.gpu_page, "gpu")
        self.stack.add_named(self.power_page, "power")
        self.stack.add_named(self.thermals_page, "thermals")
        self.stack.add_named(self.telemetry_page, "telemetry")
        self.stack.add_named(self.logs_page, "logs")

        self.stack.set_visible_child_name("dash")
        GLib.timeout_add(500, self.update_stats)

        # Subscribe to state changes for Fn+Q live sync
        self.ctrl.subscribe(self._on_state_changed)

    def _add_nav_button(self, box, label, name):
        btn = Gtk.Button(label=label)
        btn.add_css_class("sidebar-button")
        btn.connect("clicked", lambda x: self.stack.set_visible_child_name(name))
        box.append(btn)

    def _load_css(self):
        import os
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        if os.path.exists(css_path):
            provider = Gtk.CssProvider()
            provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def update_stats(self):
        self.dash_page.update_stats()
        self.thermals_page.update_stats()
        self.power_page.update_stats()
        return True

    def _on_state_changed(self, key, old, new, source):
        """React to hardware state changes (e.g. Fn+Q) and refresh GUI."""
        if key in ("power_profile", "gpu_mode", "fan_mode"):
            GLib.idle_add(self.update_stats)

    def set_hardware_mode(self, active: bool):
        """Prepares UI for privileged hardware write."""
        GLib.idle_add(self._set_hw_mode_idle, active)

    def _set_hw_mode_idle(self, active):
        if active:
            self.set_sensitive(False)
            self.add_css_class("hardware-busy")
            # Lower window so polkit dialog appears on top
            if self.get_surface():
                self.get_surface().lower()
        else:
            self.set_sensitive(True)
            self.remove_css_class("hardware-busy")
            # Restore window focus
            self.present()

    def _apply_theme(self, theme):
        settings = Gtk.Settings.get_default()
        if theme == "dark":
            settings.set_property("gtk-application-prefer-dark-theme", True)
            self.remove_css_class("light-theme")
        elif theme == "light":
            settings.set_property("gtk-application-prefer-dark-theme", False)
            self.add_css_class("light-theme")
        else:
            # System - reset to default
            settings.reset_property("gtk-application-prefer-dark-theme")
            # Auto-detect for CSS class
            is_dark = settings.get_property("gtk-application-prefer-dark-theme")
            if is_dark: self.remove_css_class("light-theme")
            else: self.add_css_class("light-theme")

    def _on_theme_changed(self, combo, pspec):
        idx = combo.get_selected()
        theme = ["system", "dark", "light"][idx]
        self.settings.set("theme", theme)
        self._apply_theme(theme)
        self.update_stats()

    def check_first_run(self):
        if self.settings.get_val("first_run"):
            GLib.idle_add(self._show_first_run_dialog)

    def _show_first_run_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text="Welcome to LOQ Control Center",
            secondary_text="Please choose your preferred UI theme to get started:",
        )
        
        dialog.add_button("Light Mode", Gtk.ResponseType.ACCEPT)
        dialog.add_button("Dark Mode", Gtk.ResponseType.YES)
        dialog.add_button("Use System Default", Gtk.ResponseType.CLOSE)

        def on_response(d, response):
            if response == Gtk.ResponseType.ACCEPT:
                theme = "light"
            elif response == Gtk.ResponseType.YES:
                theme = "dark"
            else:
                theme = "system"
            
            self.settings.set("theme", theme)
            self.settings.set("first_run", False)
            self._apply_theme(theme)
            d.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _show_reboot_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.YES_NO,
            text="GPU Mode Changed — Reboot Required",
        )
        dialog.set_markup(
            "<b>GPU Mode Changed</b>\n\n"
            "A reboot is required for the changes to take effect.\nReboot now?"
        )
        dialog.connect("response", self._on_reboot_response)
        dialog.present()

    def _on_reboot_response(self, dialog, response):
        dialog.close()
        if response == Gtk.ResponseType.YES:
            import subprocess
            subprocess.Popen("reboot", shell=True)

    def _bootstrap_privileges(self):
        """No longer needed — powerprofilesctl works without root via D-Bus.
        envycontrol GPU switching still needs pkexec, handled per-operation."""
        pass

    def _show_error(self, message: str):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Hardware Action Failed",
            secondary_text=message,
        )
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()


def main():
    """
    GUI entry point. Runs as a normal user. No sudo needed.
    Hardware services are initialized in the background.
    Privileged writes use pkexec (polkit) when triggered.
    """
    import threading
    from loq_control.core.state_manager import StateManager
    from loq_control.services.hardware_service import HardwareService

    # Start hardware backend in background — never block UI
    def _start_backend():
        try:
            from loq_control.services import daemon
            daemon.start()
        except Exception as e:
            # Non-fatal — GUI still shows, just without daemon features
            print(f"[LOQ] Daemon backend warning: {e}")

    threading.Thread(target=_start_backend, daemon=True).start()

    # Build controller with unprivileged state access
    _state = StateManager()
    _hw = HardwareService(state=_state)
    ctrl = AppController(state=_state, hw=_hw)

    app = Gtk.Application(application_id="com.loqcontrol.app")

    def on_activate(app):
        win = MainWindow(app, ctrl)
        win.present()
        win.check_first_run()

    app.connect("activate", on_activate)
    app.run(None)


if __name__ == "__main__":
    main()
