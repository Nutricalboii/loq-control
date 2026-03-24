"""
Native Cairo Graph Widget — High-performance low-latency performance visualization.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
import cairo
import collections

class NativePerformanceGraph(Gtk.DrawingArea):
    def __init__(self, controller, max_points=100, mode="all"):
        super().__init__()
        self.ctrl = controller
        self.max_points = max_points
        self.mode = mode
        
        # Internal buffers
        self.cpu_history = collections.deque(maxlen=max_points)
        self.watt_history = collections.deque(maxlen=max_points)
        self.temp_history = collections.deque(maxlen=max_points)
        
        # Initialize with zeros
        for _ in range(max_points):
            self.cpu_history.append(0)
            self.watt_history.append(0)
            self.temp_history.append(40)
            
        self.set_draw_func(self._draw)
        
        # Update timer (500ms for responsiveness)
        GLib.timeout_add(500, self._on_timer)

    def _on_timer(self):
        if not self.ctrl: return True
        
        # Pull telemetry
        cpu = self.ctrl.cpu_usage()
        watt = self.ctrl.cpu_wattage()
        temp = self.ctrl.cpu_temp()
        
        self.cpu_history.append(cpu)
        self.watt_history.append(watt)
        self.temp_history.append(temp)
        
        self.queue_draw()
        return True

    def _draw(self, area, cr, width, height, *args):
        # 1. Background (Industrial Dark)
        cr.set_source_rgb(0.04, 0.06, 0.08)
        cr.paint()
        
        # Grid setup
        cr.select_font_face("JetBrains Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(9)

        # Draw subtle grid
        cr.set_line_width(0.5)
        grid_steps = 4
        for i in range(1, grid_steps):
            y = height * (i / float(grid_steps))
            cr.set_source_rgba(0.2, 0.3, 0.4, 0.2)
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()
            
            # Y-Axis Labels
            val = 100 - int((i / grid_steps) * 100)
            cr.set_source_rgba(0.5, 0.6, 0.7, 0.4)
            cr.move_to(width - 30, y - 4)
            cr.show_text(str(val))

        # 2. Draw Metrics
        legend_x = 20
        legend_y = 25
        
        if self.mode in ("all", "cpu"):
            self._plot_data(cr, self.cpu_history, 0, 100, width, height, (1.0, 0.48, 0.09)) # accent-cpu
            
        if self.mode in ("all", "temp"):
            self._plot_data(cr, self.temp_history, 30, 100, width, height, (1.0, 0.23, 0.23)) # accent-thermal
            
        if self.mode in ("all", "power"):
            self._plot_data(cr, self.watt_history, 0, 80, width, height, (0.55, 1.0, 0.0)) # accent-power

    def _plot_data(self, cr, data, min_val, max_val, width, height, color):
        if len(data) < 2: return
        
        dx = width / (self.max_points - 1)
        r, g, b = color
        
        def scale_y(val):
            norm = (val - min_val) / (max_val - min_val)
            norm = max(0, min(1, norm))
            return height - (norm * (height - 30)) - 15

        # 1. Glow Effect (Thick low-opacity line)
        cr.set_line_width(4.0)
        cr.set_source_rgba(r, g, b, 0.15)
        cr.move_to(0, scale_y(data[0]))
        for i, val in enumerate(data):
            cr.line_to(i * dx, scale_y(val))
        cr.stroke()

        # 2. Main Line
        cr.set_line_width(1.8)
        cr.set_source_rgba(r, g, b, 0.9)
        cr.move_to(0, scale_y(data[0]))
        for i, val in enumerate(data):
            cr.line_to(i * dx, scale_y(val))
        cr.stroke_preserve() # Keep path for fill

        # 3. Gradient Fill
        cr.line_to((len(data)-1) * dx, height)
        cr.line_to(0, height)
        cr.close_path()
        
        gradient = cairo.LinearGradient(0, 0, 0, height)
        gradient.add_color_stop_rgba(0, r, g, b, 0.2)
        gradient.add_color_stop_rgba(1, r, g, b, 0.0)
        cr.set_source(gradient)
        cr.fill()
