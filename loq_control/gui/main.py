print("GUI STARTED")
"""
LOQ Control Center — GTK4 Main Window
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk

from loq_control.services import daemon
from loq_control.gui.controller import AppController
from loq_control.gui.dashboard_page import DashboardPage
from loq_control.gui.gpu_page import GPUPage
from loq_control.gui.power_page import PowerPage
from loq_control.gui.thermals_page import ThermalsPage
from loq_control.gui.log_viewer_page import LogViewerPage

# Bootstrap all services
daemon.start()

# Build the controller
_state = daemon.get_state()
_hw = daemon.get_hw_service()
controller = AppController(state=_state, hw=_hw)

class MainWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app)

        self.set_title("LOQ Control Center v0.7 — Premium Performance")
        self.set_default_size(1100, 700)
        self.ctrl = controller

        # Load CSS
        self._load_css()

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
        self._add_nav_button(sidebar, "Live Logs", "logs")

        # ================= STACK =================
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        root.append(self.stack)

        # ================= PAGES =================
        self.dash_page = DashboardPage(self.ctrl)
        self.gpu_page = GPUPage(self.ctrl, self)
        self.power_page = PowerPage(self.ctrl, self)
        self.thermals_page = ThermalsPage(self.ctrl)
        self.logs_page = LogViewerPage(self.ctrl)

        self.stack.add_named(self.dash_page, "dash")
        self.stack.add_named(self.gpu_page, "gpu")
        self.stack.add_named(self.power_page, "power")
        self.stack.add_named(self.thermals_page, "thermals")
        self.stack.add_named(self.logs_page, "logs")

        self.stack.set_visible_child_name("dash")
        GLib.timeout_add(2000, self.update_stats)

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
        return True

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

    def _show_error(self, message: str):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Hardware Action Failed",
        )
        dialog.format_secondary_text(message)
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()


def main():
    app = Gtk.Application(application_id="com.loqcontrol.app")
    
    def on_activate(app):
        win = MainWindow(app)
        win.present()
        
    app.connect("activate", on_activate)
    print("GUI STARTED")
    app.run(None)


if __name__ == "__main__":
    main()

