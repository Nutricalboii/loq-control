import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

import matplotlib.pyplot as plt
from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg as FigureCanvas

from core import monitor, thermal


class PerformanceGraph(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.cpu_data = []
        self.temp_data = []
        self.batt_data = []

        self.fig, self.ax = plt.subplots()

        self.canvas = FigureCanvas(self.fig)
        self.append(self.canvas)

        GLib.timeout_add(2000, self.update_graph)

    def update_graph(self):

        cpu = monitor.cpu_usage()
        temp = thermal.cpu_temp()
        batt = thermal.battery_draw()

        self.cpu_data.append(cpu)
        self.temp_data.append(temp)
        self.batt_data.append(batt)

        if len(self.cpu_data) > 30:
            self.cpu_data.pop(0)
            self.temp_data.pop(0)
            self.batt_data.pop(0)

        self.ax.clear()

        self.ax.plot(self.cpu_data, label="CPU %")
        self.ax.plot(self.temp_data, label="Temp °C")
        self.ax.plot(self.batt_data, label="Battery W")

        self.ax.legend()
        self.canvas.draw()

        return True
