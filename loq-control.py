import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio
import subprocess

def run(cmd):
    subprocess.Popen(cmd, shell=True)

class ControlWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("LOQ Control Center")
        self.set_default_size(420, 500)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)

        # GPU Buttons
        igpu = Gtk.Button(label="iGPU Only")
        igpu.connect("clicked", self.igpu_mode)
        box.append(igpu)

        hybrid = Gtk.Button(label="Hybrid Mode")
        hybrid.connect("clicked", self.hybrid_mode)
        box.append(hybrid)

        nvidia = Gtk.Button(label="NVIDIA Only")
        nvidia.connect("clicked", self.nvidia_mode)
        box.append(nvidia)

        # Power Profiles
        saver = Gtk.Button(label="Battery Saver")
        saver.connect("clicked", self.battery_mode)
        box.append(saver)

        perf = Gtk.Button(label="Performance Mode")
        perf.connect("clicked", self.performance_mode)
        box.append(perf)

        self.set_child(box)

    def igpu_mode(self, btn):
        run("sudo prime-select intel")
        self.msg("iGPU mode applied. Reboot recommended.")

    def hybrid_mode(self, btn):
        run("sudo prime-select on-demand")
        self.msg("Hybrid mode applied.")

    def nvidia_mode(self, btn):
        run("sudo prime-select nvidia")
        self.msg("NVIDIA mode applied. Reboot required.")

    def battery_mode(self, btn):
        run("powerprofilesctl set power-saver")
        self.msg("Battery saver enabled.")

    def performance_mode(self, btn):
        run("powerprofilesctl set performance")
        self.msg("Performance mode enabled.")

    def msg(self, text):
        dialog = Gtk.MessageDialog(transient_for=self,
                                   modal=True,
                                   text=text)
        dialog.add_button("OK", Gtk.ResponseType.OK)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()

class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="loq.control.center")

    def do_activate(self):
        win = ControlWindow(self)
        win.present()

app = App()
app.run(None)
