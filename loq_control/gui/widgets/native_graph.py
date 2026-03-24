"""
Native Cairo Graph Widget — High-performance low-latency performance visualization.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
import cairo
import collections

class NativePerformanceGraph(Gtk.DrawingArea):
    def __init__(self, controller, max_points=100):
        super().__init__()
        self.ctrl = controller
        self.max_points = max_points
        
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
        
        self.cpu_history.append(self.ctrl.cpu_usage())
        self.watt_history.append(self.ctrl.cpu_wattage())
        self.temp_history.append(self.ctrl.cpu_temp())
        
        self.queue_draw()
        return True

    def _draw(self, area, cr, width, height, *args):
        # 1. Background
        cr.set_source_rgb(0.05, 0.05, 0.05)
        cr.paint()
        
        # Grid lines
        cr.set_source_rgba(0.2, 0.2, 0.2, 0.5)
        cr.set_line_width(1.0)
        for i in range(1, 5):
            y = height * (i / 4.0)
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()

        # Data scales
        # CPU: 0-100%
        # Wattage: 0-100W (scaled)
        # Temp: 30-100C (scaled)
        
        # 2. Draw CPU (Blue)
        self._plot_data(cr, self.cpu_history, 0, 100, width, height, (0.2, 0.6, 1.0))
        
        # 3. Draw Wattage (Green)
        self._plot_data(cr, self.watt_history, 0, 80, width, height, (0.2, 0.9, 0.4))
        
        # 4. Draw Temp (Red)
        self._plot_data(cr, self.temp_history, 30, 100, width, height, (1.0, 0.3, 0.3))

    def _plot_data(self, cr, data, min_val, max_val, width, height, color):
        if not data: return
        
        cr.set_source_rgb(*color)
        cr.set_line_width(2.0)
        
        dx = width / (self.max_points - 1)
        
        def scale_y(val):
            norm = (val - min_val) / (max_val - min_val)
            norm = max(0, min(1, norm))
            return height - (norm * (height - 20)) - 10

        cr.move_to(0, scale_y(data[0]))
        for i, val in enumerate(data):
            cr.line_to(i * dx, scale_y(val))
            
        cr.stroke()
        
        # Subtle fill
        cr.line_to((len(data)-1) * dx, height)
        cr.line_to(0, height)
        cr.close_path()
        cr.set_source_rgba(color[0], color[1], color[2], 0.1)
        cr.fill()
