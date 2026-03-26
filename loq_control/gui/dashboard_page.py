import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from loq_control.gui.widgets.native_graph import NativePerformanceGraph as PerformanceGraph
from loq_control.gui.widgets.hex_status import HexStatus
from loq_control.gui.widgets.heat_bar import HeatBar
from loq_control.gui.widgets.mode_badge import ModeBadge
from loq_control.gui.widgets.status_badge import StatusBadge

class DashboardPage(Gtk.Box):
    def __init__(self, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.ctrl = controller

        # ================= TOP SECTION: INDUSTRIAL COMMAND =================
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        top_box.set_halign(Gtk.Align.CENTER)
        self.append(top_box)

        # CPU Hex
        self.cpu_hex = HexStatus("CPU LOAD", "#ff7a18")
        top_box.append(self.cpu_hex)

        # Center Mode Badge
        self.main_mode = ModeBadge("PERFORMANCE", "badge-orange")
        top_box.append(self.main_mode)

        # GPU Hex
        self.gpu_hex = HexStatus("GPU LOAD", "#00d4ff")
        top_box.append(self.gpu_hex)

        # ================= SECONDARY STATUS =================
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        status_row.set_halign(Gtk.Align.CENTER)
        self.append(status_row)

        self.gpu_status = StatusBadge("HYBRID", "badge-blue")
        self.ac_status = StatusBadge("AC", "badge-grey")
        self.safety_status = StatusBadge("SHIELD", "badge-green")
        self.brain_status = StatusBadge("BRAIN: OFF", "badge-grey")

        status_row.append(self.gpu_status)
        status_row.append(self.ac_status)
        status_row.append(self.safety_status)
        status_row.append(self.brain_status)

        # ================= THERMAL MONITOR =================
        thermal_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=40)
        thermal_card.add_css_class("industrial-card")
        self.append(thermal_card)

        self.cpu_heat = HeatBar("CPU CORE", 100)
        self.gpu_heat = HeatBar("GPU CHIP", 100)
        thermal_card.append(self.cpu_heat)
        thermal_card.append(self.gpu_heat)

        # ================= TELEMETRY GRAPH =================
        graph_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        graph_card.add_css_class("industrial-card")
        graph_card.set_vexpand(True)
        self.append(graph_card)

        graph_hdr = Gtk.Label(label="LIVE TELEMETRY PATH", halign=Gtk.Align.START)
        graph_hdr.add_css_class("monospace")
        graph_hdr.add_css_class("caption")
        graph_card.append(graph_hdr)

        self.graph = PerformanceGraph(controller=self.ctrl)
        graph_card.append(self.graph)

    def update_stats(self):
        try:
            # 1. Update Hex Widgets
            self.cpu_hex.set_value(self.ctrl.cpu_usage())
            self.gpu_hex.set_value(self.ctrl.gpu_usage())
    
            # 2. Update Thermal Bars
            self.cpu_heat.set_temp(self.ctrl.cpu_temp())
            self.gpu_heat.set_temp(self.ctrl.gpu_temp())
    
            # 3. Update Mode Badge
            state = self.ctrl.get_state()
            p = state.get('power_profile', 'balanced')
            if p == "performance": 
                self.main_mode.update_mode("PERFORMANCE", "badge-red")
            elif p in ("balanced", "default"): 
                self.main_mode.update_mode("BALANCED", "badge-blue")
            elif p in ("power-saver", "quiet", "low-power"): 
                self.main_mode.update_mode("SILENT", "badge-green")
            else:
                self.main_mode.update_mode("QUIET", "badge-green")
    
            # 4. Update Status Badges
            self.gpu_status.set_status(state['gpu_mode'].upper(), "badge-blue")
            self.ac_status.set_status("AC" if state['charger_connected'] else "BATT", "badge-grey")
            
            safety = self.ctrl.get_safety_status()
            self.safety_status.set_status(f"SHIELD: {safety.upper()}", "badge-green" if safety == "ok" else "badge-red")
            
            is_smart = state.get('smart_fan_active', False)
            self.brain_status.set_status("BRAIN: ACTIVE" if is_smart else "BRAIN: OFF", "badge-orange" if is_smart else "badge-grey")
        except Exception as e:
            print(f"[LOQ] UI Update Error: {e}")


