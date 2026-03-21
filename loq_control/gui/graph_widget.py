"""
Real-time performance graph widget.

Accepts an AppController reference instead of importing core modules directly.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg as FigureCanvas
from matplotlib.figure import Figure


class PerformanceGraph(Gtk.Box):

    def __init__(self, controller=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.set_margin_top(10)
        self.set_margin_bottom(10)
        self.set_margin_start(10)
        self.set_margin_end(10)

        self.ctrl = controller

        self.cpu_data = []
        self.ram_data = []
        self.power_data = []

        fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = fig.add_subplot(111)

        self.canvas = FigureCanvas(fig)
        self.append(self.canvas)

        GLib.timeout_add(1000, self.update)

    def update(self):
        if self.ctrl is None:
            return True

        cpu = self.ctrl.cpu_usage()
        ram = self.ctrl.ram_usage()

        try:
            pwr = float(self.ctrl.battery_power())
        except (ValueError, TypeError):
            pwr = 0.0

        self.cpu_data.append(cpu)
        self.ram_data.append(ram)
        self.power_data.append(pwr)

        if len(self.cpu_data) > 40:
            self.cpu_data.pop(0)
            self.ram_data.pop(0)
            self.power_data.pop(0)

        self.ax.clear()

        self.ax.plot(self.cpu_data, label="CPU %")
        self.ax.plot(self.ram_data, label="RAM %")
        self.ax.plot(self.power_data, label="Power W")

        self.ax.legend()
        self.ax.set_facecolor("#111111")

        self.canvas.draw()

        return True
