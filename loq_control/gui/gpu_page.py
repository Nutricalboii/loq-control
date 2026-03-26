import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
import threading

class GPUPage(Gtk.Box):
    def __init__(self, controller, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.ctrl = controller
        self.window = window

        # Title
        title = Gtk.Label(label="<b>NVIDIA Telemetry &amp; Control</b>", use_markup=True, halign=Gtk.Align.START)
        title.add_css_class("heading")
        self.append(title)

        # Metrics Card
        metrics_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        metrics_box.add_css_class("industrial-card")
        self.append(metrics_box)

        self.usage_lbl = self._metric("Usage", "0%")
        self.temp_lbl = self._metric("Temp", "0°C")
        self.clock_lbl = self._metric("Clock", "0MHz")

        metrics_box.append(self.usage_lbl)
        metrics_box.append(self.temp_lbl)
        metrics_box.append(self.clock_lbl)

        # Switcher
        self.append(Gtk.Separator())
        self.append(Gtk.Label(label="Mode Switching", halign=Gtk.Align.START))
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.append(btn_box)

        igpu = Gtk.Button(label="Integrated")
        hybrid = Gtk.Button(label="Hybrid")
        nvidia = Gtk.Button(label="NVIDIA Only")

        for b in [igpu, hybrid, nvidia]: btn_box.append(b)

        igpu.connect("clicked", lambda x: self._gpu_switch("integrated"))
        hybrid.connect("clicked", lambda x: self._gpu_switch("hybrid"))
        nvidia.connect("clicked", lambda x: self._gpu_switch("nvidia"))

        # Battery Panel (Priority 4)
        self.append(Gtk.Separator())
        self.append(Gtk.Label(label="Battery Intelligence", halign=Gtk.Align.START))
        
        self.bat_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.bat_card.add_css_class("industrial-card")
        self.append(self.bat_card)
        
        self.bat_status = Gtk.Label(label="Status: Calculating...", halign=Gtk.Align.START)
        self.bat_time = Gtk.Label(label="Estimated: -- min remaining", halign=Gtk.Align.START)
        self.bat_draw = Gtk.Label(label="Discharge Rate: -- W", halign=Gtk.Align.START)
        
        self.bat_card.append(self.bat_status)
        self.bat_card.append(self.bat_time)
        self.bat_card.append(self.bat_draw)

        GLib.timeout_add(1000, self._update)

    def _metric(self, name, val):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_hexpand(True)
        lbl_n = Gtk.Label(label=name)
        lbl_n.add_css_class("caption")
        lbl_v = Gtk.Label(label=val)
        lbl_v.add_css_class("heading")
        box.append(lbl_n)
        box.append(lbl_v)
        return lbl_v

    def _update(self):
        self.usage_lbl.set_text(f"{self.ctrl.gpu_usage()}%")
        self.temp_lbl.set_text(f"{self.ctrl.gpu_temp()}°C")
        self.clock_lbl.set_text(f"{self.ctrl.gpu_clock()}MHz")
        
        bat = self.ctrl.battery_status()
        if bat:
            status = "Charging" if bat['charging'] else "Discharging"
            self.bat_status.set_text(f"Status: {status} ({bat['capacity']}%)")
            self.bat_time.set_text(f"Estimated: {bat['time_left']} min remaining" if not bat['charging'] else "Est: Charging...")
            self.bat_draw.set_text(f"Power Draw: {bat['power_draw']} W")
            
        return True

    def _gpu_switch(self, mode: str):
        def _do():
            result = self.ctrl.switch_gpu(mode)
            if result.success and result.needs_reboot:
                GLib.idle_add(self.window._show_reboot_dialog)
            elif result.success:
                GLib.idle_add(self.window.update_stats)
            elif not result.success:
                GLib.idle_add(self.window._show_error, result.message)

        threading.Thread(target=_do, daemon=True).start()
