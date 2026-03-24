import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from loq_control.gui.widgets.native_graph import NativePerformanceGraph as Graph

class TelemetryPage(Gtk.Box):
    def __init__(self, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        
        self.ctrl = controller

        # Title
        title = Gtk.Label(label="<b>Deep Analysis & Telemetry</b>", use_markup=True, halign=Gtk.Align.START)
        title.add_css_class("heading")
        self.append(title)
        
        self.append(Gtk.Label(label="Isolated hardware metrics for accurate stability tracking.", halign=Gtk.Align.START))
        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        # Graphs Grid
        grid = Gtk.Grid(column_spacing=20, row_spacing=20)
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        self.append(grid)
        
        # CPU
        b1 = self._make_card("CPU Utilization Area", "cpu")
        grid.attach(b1, 0, 0, 1, 1)
        
        # Temp
        b2 = self._make_card("Core Thermal Analysis", "temp")
        grid.attach(b2, 1, 0, 1, 1)
        
        # Power
        b3 = self._make_card("Package Power Draw (RAPL)", "power")
        grid.attach(b3, 0, 1, 2, 1)


    def _make_card(self, title_text, mode):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("card")
        box.set_hexpand(True)
        box.set_vexpand(True)
        
        lbl = Gtk.Label(label=f"<b>{title_text}</b>", use_markup=True, halign=Gtk.Align.START)
        box.append(lbl)
        
        g = Graph(self.ctrl, mode=mode)
        g.set_size_request(-1, 200)
        box.append(g)
        
        return box
