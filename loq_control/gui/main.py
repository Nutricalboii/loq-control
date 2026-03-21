"""
LOQ Control Center — GTK4 Main Window

All hardware interactions go through the AppController.
No direct imports of core/gpu, core/power, etc.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from loq_control.services import daemon
from loq_control.gui.controller import AppController
from loq_control.gui.graph_widget import PerformanceGraph

# Bootstrap all services (state manager, hardware service, event engine, auto GPU)
daemon.start()

# Build the controller the GUI will use
_state = daemon.get_state()
_hw = daemon.get_hw_service()
controller = AppController(state=_state, hw=_hw)


class MainWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app)

        self.set_title("LOQ Control Center v0.5 — Vaibhav Sharma")
        self.set_default_size(1100, 650)
        self.ctrl = controller

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_child(root)

        # ================= SIDEBAR =================
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_margin_start(12)
        sidebar.set_margin_top(12)
        root.append(sidebar)

        dash_btn = Gtk.Button(label="Dashboard")
        gpu_btn = Gtk.Button(label="GPU Modes")
        power_btn = Gtk.Button(label="Power Profiles")

        sidebar.append(dash_btn)
        sidebar.append(gpu_btn)
        sidebar.append(power_btn)

        # ================= STACK =================
        self.stack = Gtk.Stack()
        root.append(self.stack)

        # ================= DASHBOARD PAGE =================
        dash = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        dash.set_margin_top(20)
        dash.set_margin_start(20)

        self.cpu = Gtk.Label()
        self.ram = Gtk.Label()
        self.temp = Gtk.Label()
        self.ssd = Gtk.Label()
        self.power_draw = Gtk.Label()
        self.state_label = Gtk.Label()

        dash.append(self.cpu)
        dash.append(self.ram)
        dash.append(self.temp)
        dash.append(self.ssd)
        dash.append(self.power_draw)
        dash.append(self.state_label)

        graph = PerformanceGraph(controller=self.ctrl)
        dash.append(graph)

        self.stack.add_named(dash, "dash")

        # ================= GPU PAGE =================
        gpu_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        gpu_page.set_margin_top(20)

        igpu = Gtk.Button(label="Integrated Mode")
        hybrid = Gtk.Button(label="Hybrid Mode")
        nvidia = Gtk.Button(label="NVIDIA Mode")

        gpu_page.append(igpu)
        gpu_page.append(hybrid)
        gpu_page.append(nvidia)

        self.stack.add_named(gpu_page, "gpu")

        # ================= POWER PAGE =================
        power_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        power_page.set_margin_top(20)

        saver = Gtk.Button(label="Battery Saver")
        balanced = Gtk.Button(label="Balanced")
        perf = Gtk.Button(label="Performance")

        power_page.append(saver)
        power_page.append(balanced)
        power_page.append(perf)

        self.stack.add_named(power_page, "power")

        # ================= NAVIGATION =================
        dash_btn.connect("clicked", lambda x: self.stack.set_visible_child_name("dash"))
        gpu_btn.connect("clicked", lambda x: self.stack.set_visible_child_name("gpu"))
        power_btn.connect("clicked", lambda x: self.stack.set_visible_child_name("power"))

        # GPU actions — go through controller (thread-safe)
        igpu.connect("clicked", lambda x: self._gpu_switch("integrated"))
        hybrid.connect("clicked", lambda x: self._gpu_switch("hybrid"))
        nvidia.connect("clicked", lambda x: self._gpu_switch("nvidia"))

        # Power actions — go through controller
        saver.connect("clicked", lambda x: self._power_switch("power-saver"))
        balanced.connect("clicked", lambda x: self._power_switch("balanced"))
        perf.connect("clicked", lambda x: self._power_switch("performance"))

        self.stack.set_visible_child_name("dash")

        GLib.timeout_add(2000, self.update_stats)

    # ------------------------------------------------------------------
    # Hardware actions (via controller)
    # ------------------------------------------------------------------

    def _gpu_switch(self, mode: str):
        """Run GPU switch in a thread, then handle result on main thread."""
        import threading

        def _do():
            result = self.ctrl.switch_gpu(mode)
            if result.success and result.needs_reboot:
                GLib.idle_add(self._show_reboot_dialog)
            elif not result.success:
                GLib.idle_add(self._show_error, result.message)

        threading.Thread(target=_do, daemon=True).start()

    def _power_switch(self, profile: str):
        import threading

        def _do():
            result = self.ctrl.set_power_profile(profile)
            if not result.success:
                GLib.idle_add(self._show_error, result.message)

        threading.Thread(target=_do, daemon=True).start()

    # ------------------------------------------------------------------
    # Stats update
    # ------------------------------------------------------------------

    def update_stats(self):
        self.cpu.set_text(f"CPU Usage: {self.ctrl.cpu_usage()} %")
        self.ram.set_text(f"RAM Usage: {self.ctrl.ram_usage()} %")
        self.temp.set_text(f"CPU Temp: {self.ctrl.cpu_temp()} °C")
        self.ssd.set_text(f"SSD Temp: {self.ctrl.ssd_temp()} °C")
        self.power_draw.set_text(f"Battery Draw: {self.ctrl.battery_power()} W")

        state = self.ctrl.get_state()
        self.state_label.set_text(
            f"GPU: {state['gpu_mode']}  |  Power: {state['power_profile']}  "
            f"|  Fan: {state['fan_mode']}  |  AC: {'Yes' if state['charger_connected'] else 'No'}"
        )
        return True

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

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
            text="Operation Failed",
        )
        dialog.set_markup(f"<b>Error</b>\n\n{message}")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()


class App(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_activate(self):
        win = MainWindow(self)
        win.present()


app = App()
app.run()
