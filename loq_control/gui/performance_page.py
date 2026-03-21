import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from loq_control.core import hardware, thermals


class PerformancePage(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        title = Gtk.Label(label="Performance Control")
        title.set_margin_top(20)
        title.add_css_class("title-1")
        self.append(title)

        self.cpu = Gtk.Label()
        self.ram = Gtk.Label()
        self.temp = Gtk.Label()
        self.ssd = Gtk.Label()
        self.gpu = Gtk.Label()

        self.append(self.cpu)
        self.append(self.ram)
        self.append(self.temp)
        self.append(self.ssd)
        self.append(self.gpu)

        self.append(Gtk.Separator())

        btn1 = Gtk.Button(label="Quiet Mode")
        btn1.connect("clicked", lambda x: thermals.quiet())

        btn2 = Gtk.Button(label="Balanced Mode")
        btn2.connect("clicked", lambda x: thermals.balanced())

        btn3 = Gtk.Button(label="Performance Mode")
        btn3.connect("clicked", lambda x: thermals.performance())

        btn4 = Gtk.Button(label="Extreme Mode")
        btn4.connect("clicked", lambda x: thermals.extreme())

        self.append(btn1)
        self.append(btn2)
        self.append(btn3)
        self.append(btn4)

        GLib.timeout_add(1500, self.update_stats)

    def update_stats(self):

        self.cpu.set_text(f"CPU Usage: {hardware.cpu_usage()} %")
        self.ram.set_text(f"RAM Usage: {hardware.ram_usage()} %")

        temp = hardware.cpu_temp()
        self.temp.set_text(f"CPU Temp: {temp} °C")

        ssd = hardware.ssd_temp()
        self.ssd.set_text(f"SSD Temp: {ssd} °C")

        if hardware.nvidia_present():
            self.gpu.set_text(f"NVIDIA Power: {hardware.nvidia_power()} W")
        else:
            self.gpu.set_text("NVIDIA GPU: OFF")

        return True
