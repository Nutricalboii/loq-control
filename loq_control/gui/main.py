import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from loq_control.core import monitor, thermals, hardware, gpu, power
from loq_control.gui.graph_widget import PerformanceGraph
from loq_control.services import daemon

daemon.start()


class MainWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app)

        self.set_title("LOQ Control Center v0.4 — Vaibhav Sharma")
        self.set_default_size(1100, 650)

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

        dash.append(self.cpu)
        dash.append(self.ram)
        dash.append(self.temp)
        dash.append(self.ssd)
        dash.append(self.power_draw)

        graph = PerformanceGraph()
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

        # GPU actions — thread safe with reboot callback
        igpu.connect("clicked", lambda x: gpu.igpu(self.ask_reboot))
        hybrid.connect("clicked", lambda x: gpu.hybrid(self.ask_reboot))
        nvidia.connect("clicked", lambda x: gpu.nvidia(self.ask_reboot))

        # Power actions
        saver.connect("clicked", lambda x: power.battery())
        balanced.connect("clicked", lambda x: power.balanced())
        perf.connect("clicked", lambda x: power.performance())

        self.stack.set_visible_child_name("dash")

        GLib.timeout_add(2000, self.update_stats)

    def update_stats(self):
        self.cpu.set_text(f"CPU Usage: {monitor.cpu_usage()} %")
        self.ram.set_text(f"RAM Usage: {monitor.ram_usage()} %")
        self.temp.set_text(f"CPU Temp: {thermals.cpu_temp()} °C")
        self.ssd.set_text(f"SSD Temp: {hardware.ssd_temp()} °C")
        self.power_draw.set_text(f"Battery Draw: {hardware.battery_power()} W")
        return True

    def ask_reboot(self):
        GLib.idle_add(self._show_reboot_dialog)

    def _show_reboot_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.YES_NO,
            text="GPU Mode Changed — Reboot Required",
        )
        dialog.set_markup("<b>GPU Mode Changed</b>\n\nA reboot is required for the changes to take effect.\nReboot now?")
        dialog.connect("response", self._on_reboot_response)
        dialog.present()

    def _on_reboot_response(self, dialog, response):
        dialog.close()
        if response == Gtk.ResponseType.YES:
            import subprocess
            subprocess.Popen("reboot", shell=True)


class App(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_activate(self):
        win = MainWindow(self)
        win.present()


app = App()
app.run()
