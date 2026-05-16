import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
import cairo
import math
from loq_control.core.custom_profile import (
    CustomProfileConfig,
    CustomProfileApplicator,
    CPU_PRESETS,
    GPU_PRESETS,
    PERFORMANCE_FAN_CURVE,
    SILENT_FAN_CURVE,
    DEFAULT_FAN_CURVE,
)


class FanCurveEditor(Gtk.DrawingArea):

    PADDING = 40
    POINT_RADIUS = 8
    MIN_FAN_AT_HOT = 60
    HOT_THRESHOLD = 80

    def __init__(self, curve_points):
        super().__init__()
        self.points = [list(p) for p in curve_points]
        self.dragging_idx = None
        self.set_content_width(420)
        self.set_content_height(220)
        self.set_draw_func(self._draw)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

        self.on_curve_changed = None

    def set_curve(self, points):
        self.points = [list(p) for p in points]
        self.queue_draw()

    def get_curve(self):
        return [list(p) for p in self.points]

    def _temp_to_x(self, t, w):
        return self.PADDING + (t - 30) / 70.0 * (w - 2 * self.PADDING)

    def _speed_to_y(self, s, h):
        return h - self.PADDING - s / 100.0 * (h - 2 * self.PADDING)

    def _x_to_temp(self, x, w):
        return 30 + (x - self.PADDING) / (w - 2 * self.PADDING) * 70

    def _y_to_speed(self, y, h):
        return 100 - (y - self.PADDING) / (h - 2 * self.PADDING) * 100

    def _draw(self, area, cr, w, h):
        cr.set_source_rgba(0.12, 0.12, 0.15, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        cr.set_source_rgba(0.25, 0.25, 0.30, 1.0)
        cr.set_line_width(0.5)
        for i in range(5):
            gx = self.PADDING + i * (w - 2 * self.PADDING) / 4
            cr.move_to(gx, self.PADDING)
            cr.line_to(gx, h - self.PADDING)
            cr.stroke()
            gy = self.PADDING + i * (h - 2 * self.PADDING) / 4
            cr.move_to(self.PADDING, gy)
            cr.line_to(w - self.PADDING, gy)
            cr.stroke()

        hot_x = self._temp_to_x(self.HOT_THRESHOLD, w)
        cr.set_source_rgba(0.8, 0.3, 0.3, 0.15)
        cr.rectangle(hot_x, self.PADDING, w - self.PADDING - hot_x, h - 2 * self.PADDING)
        cr.fill()

        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(9)
        cr.set_source_rgba(0.5, 0.5, 0.6, 1.0)
        for t in [30, 40, 50, 60, 70, 80, 90, 100]:
            gx = self.PADDING + (t - 30) / 70.0 * (w - 2 * self.PADDING)
            if gx <= w - self.PADDING + 1:
                cr.move_to(gx - 6, h - self.PADDING + 14)
                cr.show_text(str(t))
        for s in [0, 25, 50, 75, 100]:
            gy = h - self.PADDING - s / 100.0 * (h - 2 * self.PADDING)
            cr.move_to(2, gy + 4)
            cr.show_text(str(s))

        cr.set_source_rgba(0.6, 0.6, 0.65, 0.8)
        cr.set_font_size(8)
        cr.move_to(self.PADDING + 2, h - self.PADDING + 26)
        cr.show_text("Temperature (°C)")
        cr.move_to(3, self.PADDING - 5)
        cr.show_text("Fan %")

        if self.points:
            pts_px = [(self._temp_to_x(p[0], w), self._speed_to_y(p[1], h)) for p in self.points]

            cr.set_source_rgba(0.55, 0.25, 0.85, 0.3)
            cr.move_to(pts_px[0][0], h - self.PADDING)
            for px, py in pts_px:
                cr.line_to(px, py)
            cr.line_to(pts_px[-1][0], h - self.PADDING)
            cr.close_path()
            cr.fill()

            cr.set_source_rgba(0.7, 0.4, 1.0, 1.0)
            cr.set_line_width(2.0)
            cr.move_to(*pts_px[0])
            for px, py in pts_px[1:]:
                cr.line_to(px, py)
            cr.stroke()

            for i, (px, py) in enumerate(pts_px):
                if i == self.dragging_idx:
                    cr.set_source_rgba(1.0, 0.85, 0.2, 1.0)
                    cr.arc(px, py, self.POINT_RADIUS + 2, 0, 2 * math.pi)
                else:
                    cr.set_source_rgba(0.7, 0.4, 1.0, 1.0)
                    cr.arc(px, py, self.POINT_RADIUS, 0, 2 * math.pi)
                cr.fill()
                cr.set_source_rgba(0.1, 0.1, 0.12, 1.0)
                cr.arc(px, py, self.POINT_RADIUS - 3, 0, 2 * math.pi)
                cr.fill()

    def _find_nearest_point(self, x, y, w, h):
        best_idx = None
        best_dist = float("inf")
        for i, pt in enumerate(self.points):
            px = self._temp_to_x(pt[0], w)
            py = self._speed_to_y(pt[1], h)
            dist = math.hypot(x - px, y - py)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        if best_dist < 20:
            return best_idx
        return None

    def _on_drag_begin(self, gesture, x, y):
        w = self.get_width()
        h = self.get_height()
        self.dragging_idx = self._find_nearest_point(x, y, w, h)
        self._drag_start_x = x
        self._drag_start_y = y
        self._drag_orig = list(self.points[self.dragging_idx]) if self.dragging_idx is not None else None

    def _on_drag_update(self, gesture, dx, dy):
        if self.dragging_idx is None or self._drag_orig is None:
            return
        w = self.get_width()
        h = self.get_height()
        nx = self._drag_start_x + dx
        ny = self._drag_start_y + dy
        new_speed = max(0, min(100, self._y_to_speed(ny, h)))

        orig_temp = self._drag_orig[0]
        is_hot = orig_temp >= self.HOT_THRESHOLD
        if is_hot:
            new_speed = max(self.MIN_FAN_AT_HOT, new_speed)

        self.points[self.dragging_idx][1] = int(round(new_speed))
        self.queue_draw()

        if self.on_curve_changed:
            self.on_curve_changed(self.get_curve())

    def _on_drag_end(self, gesture, dx, dy):
        self.dragging_idx = None
        self.queue_draw()


class CustomModePanel(Gtk.Box):

    def __init__(self, on_profile_apply=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.on_profile_apply = on_profile_apply
        self._config = CustomProfileConfig.load()
        self._warning_shown = False
        self._build_ui()

    def _build_ui(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(16)
        content.set_margin_bottom(16)

        content.append(self._build_hardware_info_row())
        content.append(self._build_section_header("CPU Power Limits", "🔵"))
        content.append(self._build_cpu_section())
        content.append(self._build_section_header("GPU Power & Overclock", "🟢"))
        content.append(self._build_gpu_section())
        content.append(self._build_section_header("Fan Curve Editor", "🌀"))
        content.append(self._build_fan_section())
        content.append(self._build_action_bar())

        scroll.set_child(content)
        self.append(scroll)

    def _build_hardware_info_row(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("custom-hw-info")

        cpu_label = Gtk.Label(label=f"CPU: {self._config.detected_cpu}")
        cpu_label.set_halign(Gtk.Align.START)
        cpu_label.add_css_class("dim-label")

        gpu_label = Gtk.Label(label=f"GPU: {self._config.detected_gpu}")
        gpu_label.set_halign(Gtk.Align.START)
        gpu_label.add_css_class("dim-label")

        row.append(cpu_label)
        row.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        row.append(gpu_label)

        ac_status = "AC ✓" if self._check_ac() else "Battery ⚠"
        self._ac_label = Gtk.Label(label=ac_status)
        self._ac_label.set_halign(Gtk.Align.END)
        self._ac_label.set_hexpand(True)
        if not self._check_ac():
            self._ac_label.add_css_class("warning-label")
        row.append(self._ac_label)

        return row

    def _build_section_header(self, title, icon):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(8)

        lbl = Gtk.Label(label=f"{icon}  {title}")
        lbl.add_css_class("section-header-label")
        lbl.set_halign(Gtk.Align.START)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_hexpand(True)
        sep.set_valign(Gtk.Align.CENTER)

        box.append(lbl)
        box.append(sep)
        return box

    def _build_cpu_section(self):
        cpu_preset = self._config.get_cpu_preset()
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        self._pl1_scale, pl1_row = self._make_slider_row(
            "PL1 — Long Term (Sustained)",
            15, cpu_preset["pl1_max"],
            self._config.cpu_pl1_watts,
            "W",
            tooltip="The sustained power budget your CPU settles into after ~2 min of load. Lower = cooler, fewer FPS drops."
        )

        self._pl2_scale, pl2_row = self._make_slider_row(
            "PL2 — Short Term (Burst)",
            15, cpu_preset["pl2_max"],
            self._config.cpu_pl2_watts,
            "W",
            tooltip="Peak burst power for a few seconds. Keep high for snappy app launches."
        )

        self._thermal_scale, thermal_row = self._make_slider_row(
            "CPU Thermal Limit",
            70, 100,
            self._config.cpu_thermal_limit_c,
            "°C",
            tooltip="Temperature ceiling at which CPU throttles itself. 90°C is safe for long sessions."
        )

        grid.attach(pl1_row, 0, 0, 1, 1)
        grid.attach(pl2_row, 0, 1, 1, 1)
        grid.attach(thermal_row, 0, 2, 1, 1)

        card = self._wrap_in_card(grid)
        return card

    def _build_gpu_section(self):
        gpu_preset = self._config.get_gpu_preset()
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        self._ctgp_scale, ctgp_row = self._make_slider_row(
            "cTGP — GPU Base Power",
            20, gpu_preset["ctgp_max"],
            self._config.gpu_ctgp_watts,
            "W",
            tooltip="Base GPU power budget. Lowering by 10W drops temps ~8°C with minimal FPS loss."
        )

        self._boost_scale, boost_row = self._make_slider_row(
            "Dynamic Boost (CPU→GPU)",
            0, gpu_preset["boost_max"],
            self._config.gpu_dynamic_boost_watts,
            "W",
            tooltip="Extra wattage the system can steal from CPU and give to GPU when GPU-limited."
        )

        grid.attach(ctgp_row, 0, 0, 1, 1)
        grid.attach(boost_row, 0, 1, 1, 1)

        oc_frame = self._build_oc_section(gpu_preset)
        grid.attach(oc_frame, 0, 2, 1, 1)

        card = self._wrap_in_card(grid)
        return card

    def _build_oc_section(self, gpu_preset):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(4)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._oc_check = Gtk.CheckButton(label="Enable GPU Overclock")
        self._oc_check.set_active(self._config.gpu_oc_enabled)
        self._oc_check.connect("toggled", self._on_oc_toggled)

        oc_warn = Gtk.Label(label="⚠ Unstable settings may crash GPU driver")
        oc_warn.add_css_class("dim-label")
        oc_warn.set_halign(Gtk.Align.END)
        oc_warn.set_hexpand(True)

        header.append(self._oc_check)
        header.append(oc_warn)
        box.append(header)

        self._oc_sliders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._oc_sliders_box.set_sensitive(self._config.gpu_oc_enabled)

        self._core_scale, core_row = self._make_slider_row(
            "Core Clock Offset",
            -200, gpu_preset["core_max"],
            self._config.gpu_core_offset_mhz,
            "MHz",
            tooltip="Bump GPU core clock. Start at +100 and test for crashes."
        )
        self._mem_scale, mem_row = self._make_slider_row(
            "Memory Clock Offset",
            -500, gpu_preset["mem_max"],
            self._config.gpu_mem_offset_mhz,
            "MHz",
            tooltip="Boost VRAM bandwidth. +200 MHz is a safe starting point."
        )

        reset_oc_btn = Gtk.Button(label="Reset OC to 0")
        reset_oc_btn.connect("clicked", self._on_reset_oc)
        reset_oc_btn.set_halign(Gtk.Align.START)

        self._oc_sliders_box.append(core_row)
        self._oc_sliders_box.append(mem_row)
        self._oc_sliders_box.append(reset_oc_btn)
        box.append(self._oc_sliders_box)

        return box

    def _build_fan_section(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        info = Gtk.Label(
            label="Drag points to adjust. Red zone (≥80°C) enforces minimum 60% fan speed."
        )
        info.add_css_class("dim-label")
        info.set_halign(Gtk.Align.START)
        info.set_wrap(True)
        box.append(info)

        self._fan_editor = FanCurveEditor(self._config.fan_curve)
        self._fan_editor.on_curve_changed = self._on_fan_curve_changed
        box.append(self._fan_editor)

        preset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preset_row.set_margin_top(4)

        lbl = Gtk.Label(label="Presets:")
        lbl.add_css_class("dim-label")
        preset_row.append(lbl)

        perf_btn = Gtk.Button(label="Performance Curve")
        perf_btn.connect("clicked", lambda _: self._load_fan_preset(PERFORMANCE_FAN_CURVE))
        silent_btn = Gtk.Button(label="Silent Curve")
        silent_btn.connect("clicked", lambda _: self._load_fan_preset(SILENT_FAN_CURVE))
        default_btn = Gtk.Button(label="Default Curve")
        default_btn.connect("clicked", lambda _: self._load_fan_preset(DEFAULT_FAN_CURVE))

        preset_row.append(perf_btn)
        preset_row.append(silent_btn)
        preset_row.append(default_btn)
        box.append(preset_row)

        card = self._wrap_in_card(box)
        return card

    def _build_action_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.set_margin_top(8)

        reset_perf = Gtk.Button(label="Reset to Performance Defaults")
        reset_perf.connect("clicked", self._on_reset_to_performance)

        reset_silent = Gtk.Button(label="Reset to Silent Defaults")
        reset_silent.connect("clicked", self._on_reset_to_silent)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)

        self._apply_btn = Gtk.Button(label="Apply & Save")
        self._apply_btn.add_css_class("suggested-action")
        self._apply_btn.connect("clicked", self._on_apply)

        bar.append(reset_perf)
        bar.append(reset_silent)
        bar.append(spacer)
        bar.append(self._apply_btn)
        return bar

    def _make_slider_row(self, label_text, min_val, max_val, current_val, unit, tooltip=None):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label_text)
        lbl.set_halign(Gtk.Align.START)
        if tooltip:
            lbl.set_tooltip_text(tooltip)

        value_lbl = Gtk.Label(label=f"{current_val} {unit}")
        value_lbl.set_halign(Gtk.Align.END)
        value_lbl.set_hexpand(True)
        value_lbl.add_css_class("numeric-label")

        header.append(lbl)
        header.append(value_lbl)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_val, max_val, 1)
        scale.set_value(current_val)
        scale.set_hexpand(True)
        scale.set_draw_value(False)

        def on_change(s, lbl=value_lbl, u=unit):
            lbl.set_text(f"{int(s.get_value())} {u}")

        scale.connect("value-changed", on_change)

        row.append(header)
        row.append(scale)
        return scale, row

    def _wrap_in_card(self, child):
        frame = Gtk.Frame()
        frame.set_child(child)
        child.set_margin_start(12)
        child.set_margin_end(12)
        child.set_margin_top(10)
        child.set_margin_bottom(10)
        return frame

    def _on_oc_toggled(self, check):
        self._oc_sliders_box.set_sensitive(check.get_active())

    def _on_reset_oc(self, btn):
        self._core_scale.set_value(0)
        self._mem_scale.set_value(0)

    def _on_fan_curve_changed(self, curve):
        self._config.fan_curve = curve

    def _load_fan_preset(self, preset):
        self._fan_editor.set_curve(preset)
        self._config.fan_curve = [list(p) for p in preset]

    def _on_reset_to_performance(self, btn):
        cfg = CustomProfileConfig.reset_to_performance()
        self._config = cfg
        self._refresh_ui_from_config()

    def _on_reset_to_silent(self, btn):
        cfg = CustomProfileConfig.reset_to_silent()
        self._config = cfg
        self._refresh_ui_from_config()

    def _refresh_ui_from_config(self):
        self._pl1_scale.set_value(self._config.cpu_pl1_watts)
        self._pl2_scale.set_value(self._config.cpu_pl2_watts)
        self._thermal_scale.set_value(self._config.cpu_thermal_limit_c)
        self._ctgp_scale.set_value(self._config.gpu_ctgp_watts)
        self._boost_scale.set_value(self._config.gpu_dynamic_boost_watts)
        self._core_scale.set_value(self._config.gpu_core_offset_mhz)
        self._mem_scale.set_value(self._config.gpu_mem_offset_mhz)
        self._oc_check.set_active(self._config.gpu_oc_enabled)
        self._fan_editor.set_curve(self._config.fan_curve)

    def _collect_config_from_ui(self):
        self._config.cpu_pl1_watts = int(self._pl1_scale.get_value())
        self._config.cpu_pl2_watts = int(self._pl2_scale.get_value())
        self._config.cpu_thermal_limit_c = int(self._thermal_scale.get_value())
        self._config.gpu_ctgp_watts = int(self._ctgp_scale.get_value())
        self._config.gpu_dynamic_boost_watts = int(self._boost_scale.get_value())
        self._config.gpu_oc_enabled = self._oc_check.get_active()
        self._config.gpu_core_offset_mhz = int(self._core_scale.get_value())
        self._config.gpu_mem_offset_mhz = int(self._mem_scale.get_value())
        self._config.fan_curve = self._fan_editor.get_curve()

    def _check_ac(self):
        try:
            with open("/sys/class/power_supply/AC/online") as f:
                return f.read().strip() == "1"
        except Exception:
            return True

    def _on_apply(self, btn):
        if not self._warning_shown:
            self._show_warning_dialog()
            return
        self._do_apply()

    def _show_warning_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Enable Custom Power Mode?",
        )
        dialog.format_secondary_text(
            "Custom Mode enables advanced CPU and GPU power controls.\n\n"
            "Incorrect settings may cause system instability or higher temperatures. "
            "Hardware safety limits are still enforced by firmware — you cannot damage "
            "your hardware through this interface.\n\n"
            "Custom Mode requires AC power. It will automatically revert to Balanced "
            "if you unplug the charger."
        )
        dialog.connect("response", self._on_warning_response)
        dialog.present()

    def _on_warning_response(self, dialog, response):
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self._warning_shown = True
            self._do_apply()

    def _do_apply(self):
        if not self._check_ac():
            self._show_ac_error()
            return

        self._collect_config_from_ui()
        self._config.save()

        self._apply_btn.set_label("Applying…")
        self._apply_btn.set_sensitive(False)

        applicator = CustomProfileApplicator(self._config)
        results = applicator.apply_all()

        GLib.idle_add(self._on_apply_done, results)

    def _on_apply_done(self, results):
        self._apply_btn.set_label("Apply & Save")
        self._apply_btn.set_sensitive(True)

        if self.on_profile_apply:
            self.on_profile_apply("custom", self._config)

        return False

    def _show_ac_error(self):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="AC Power Required",
        )
        dialog.format_secondary_text(
            "Custom Mode only works when the laptop is plugged into AC power.\n"
            "Please connect the charger and try again."
        )
        dialog.connect("response", lambda d, _: d.destroy())
        dialog.present()

    def refresh_hardware_detection(self):
        from loq_control.core.custom_profile import _detect_hardware
        cpu, gpu = _detect_hardware()
        self._config.detected_cpu = cpu
        self._config.detected_gpu = gpu
