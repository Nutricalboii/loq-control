import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

import threading

from core import monitor, thermal
from core.gpu import modes as gpu
from core.power import modes as power
from services import auto_gpu
from utils.system import reboot
from gui.performance import PerformanceGraph


class Dashboard(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app)

        self.set_title("LOQ Control Center")
        self.set_default_size(500, 700)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)

        self.set_child(box)

        # ===== LIVE STATS =====
        self.cpu = Gtk.Label(label="CPU Usage")
        self.ram = Gtk.Label(label="RAM Usage")
        self.temp = Gtk.Label(label="CPU Temp")
        self.batt = Gtk.Label(label="Battery Draw")

        box.append(self.cpu)
        box.append(self.ram)
        box.append(self.temp)
        box.append(self.batt)

        GLib.timeout_add(2000, self.update_stats)

        # ===== GRAPH =====
        box.append(Gtk.Separator())

        graph = PerformanceGraph()
        box.append(graph)

        # ===== GPU =====
        box.append(Gtk.Separator())

        btn1 = Gtk.Button(label="iGPU Mode")
        btn1.connect("clicked", self.set_igpu)
        box.append(btn1)

        btn2 = Gtk.Button(label="Hybrid Mode")
        btn2.connect("clicked", self.set_hybrid)
        box.append(btn2)

        btn3 = Gtk.Button(label="NVIDIA Mode")
        btn3.connect("clicked", self.set_nvidia)
        box.append(btn3)

        # ===== POWER =====
        box.append(Gtk.Separator())

        btn4 = Gtk.Button(label="Battery Saver")
        btn4.connect("clicked", lambda x: power.battery())
        box.append(btn4)

        btn5 = Gtk.Button(label="Balanced")
        btn5.connect("clicked", lambda x: power.balanced())
        box.append(btn5)

        btn6 = Gtk.Button(label="Performance")
        btn6.connect("clicked", lambda x: power.performance())
        box.append(btn6)

        # ===== AUTO GPU THREAD =====
        threading.Thread(target=auto_gpu.run, daemon=True).start()

    # ===== GPU SWITCH =====
    def set_igpu(self, widget):
        gpu.igpu()
        self.ask_reboot()

    def set_hybrid(self, widget):
        gpu.hybrid()
        self.ask_reboot()

    def set_nvidia(self, widget):
        gpu.nvidia()
        self.ask_reboot()

    # ===== GTK4 REBOOT DIALOG =====
    def ask_reboot(self):

        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            text="Reboot Required",
            secondary_text="GPU mode change requires reboot. Reboot now?"
        )

        dialog.add_buttons(
            "No", Gtk.ResponseType.NO,
            "Yes", Gtk.ResponseType.YES
        )

        def response(dialog, response_id):
            if response_id == Gtk.ResponseType.YES:
                reboot()
            dialog.destroy()

        dialog.connect("response", response)
        dialog.show()

    # ===== UPDATE STATS =====
    def update_stats(self):

        self.cpu.set_text(f"CPU Usage: {monitor.cpu_usage()} %")
        self.ram.set_text(f"RAM Usage: {monitor.ram_usage()} %")
        self.temp.set_text(f"CPU Temp: {thermal.cpu_temp()} °C")
        self.batt.set_text(f"Battery Draw: {thermal.battery_draw()} W")

        return True


class App(Gtk.Application):

    def do_activate(self):
        win = Dashboard(self)
        win.present()


app = App()
app.run()
