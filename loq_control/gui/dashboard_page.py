import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from loq_control.gui.widgets.native_graph import NativePerformanceGraph as PerformanceGraph
from loq_control.gui.widgets.status_badge import StatusBadge

class DashboardPage(Gtk.Box):
    def __init__(self, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.ctrl = controller

        # Header with status badges
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.append(header)

        self.gpu_badge = StatusBadge("HYBRID", "green")
        self.power_badge = StatusBadge("BALANCED", "blue")
        self.fan_badge = StatusBadge("AUTO", "orange")
        self.ac_badge = StatusBadge("AC", "grey")
        self.policy_badge = StatusBadge("IDLE", "purple")
        self.safety_badge = StatusBadge("SHIELD", "green")


        header.append(self.gpu_badge)
        header.append(self.power_badge)
        header.append(self.fan_badge)
        header.append(self.ac_badge)
        header.append(self.policy_badge)
        header.append(self.safety_badge)



        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Adaptive Toggle
        adaptive_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        adaptive_box.set_margin_top(10)
        self.append(adaptive_box)
        
        adaptive_box.append(Gtk.Label(label="<b>Adaptive Smart Fan Learning</b>", use_markup=True))
        self.adaptive_switch = Gtk.Switch()
        self.adaptive_switch.set_active(False)
        self.adaptive_switch.connect("state-set", self._on_adaptive_toggled)
        adaptive_box.append(self.adaptive_switch)

        # Metrics Grid

        grid = Gtk.Grid(column_spacing=24, row_spacing=24)
        grid.set_margin_top(12)
        self.append(grid)

        self.cpu_usage = self._create_metric_card("CPU Usage", "%")
        self.ram_usage = self._create_metric_card("RAM Usage", "%")
        self.cpu_temp = self._create_metric_card("Core Temp", "°C")
        self.batt_draw = self._create_metric_card("Power Draw", "W")

        grid.attach(self.cpu_usage[0], 0, 0, 1, 1)
        grid.attach(self.ram_usage[0], 1, 0, 1, 1)
        grid.attach(self.cpu_temp[0], 0, 1, 1, 1)
        grid.attach(self.batt_draw[0], 1, 1, 1, 1)

        self.graph = PerformanceGraph(controller=self.ctrl)
        self.graph.set_vexpand(True)
        self.append(self.graph)

    def _create_metric_card(self, title, unit):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("card")
        
        t_lbl = Gtk.Label(label=title)
        t_lbl.add_css_class("caption")
        
        v_lbl = Gtk.Label(label=f"0 {unit}")
        v_lbl.add_css_class("heading")
        
        box.append(t_lbl)
        box.append(v_lbl)
        return box, v_lbl, unit

    def _on_adaptive_toggled(self, switch, state):
        def _do():
            # In Phase 4, we use 'smart_fan_active' as the state key
            self.ctrl.apply_preset("smart-fan" if state else "balanced")
        
        import threading
        threading.Thread(target=_do, daemon=True).start()
        return True # Fix: Returning True tells GTK to keep the requested state

    def update_stats(self):
        self.cpu_usage[1].set_text(f"{self.ctrl.cpu_usage()} %")
        self.ram_usage[1].set_text(f"{self.ctrl.ram_usage()} %")
        self.cpu_temp[1].set_text(f"{self.ctrl.cpu_temp()} °C")
        
        # Now showing CPU Package Wattage instead of Battery Draw in this slot
        self.batt_draw[1].set_text(f"{self.ctrl.cpu_wattage()} W")

        state = self.ctrl.get_state()
        is_smart = state.get('smart_fan_active', False)
        
        # Keep switch in sync with state if changed elsewhere (Fn+Q)
        if self.adaptive_switch.get_active() != is_smart:
            self.adaptive_switch.set_active(is_smart)

        self.gpu_badge.set_status(state['gpu_mode'], "green" if state['gpu_mode'] == 'hybrid' else "red" if state['gpu_mode'] == 'nvidia' else "grey")

        self.power_badge.set_status(state['power_profile'], "blue")
        
        is_smart = state.get('smart_fan_active', False)
        self.fan_badge.set_status("SMART" if is_smart else state['fan_mode'], "orange" if is_smart else "grey")
        self.ac_badge.set_status("AC" if state['charger_connected'] else "BATT", "grey" if state['charger_connected'] else "orange")
        
        policy = self.ctrl.get_current_policy()
        self.policy_badge.set_status(policy.upper(), "purple")

        safety = self.ctrl.get_safety_status()
        color = "green" if safety == "ok" else ("orange" if safety == "throttled" else "red")
        self.safety_badge.set_status(safety.upper(), color)


