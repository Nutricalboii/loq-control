"""
Custom Mode Panel — Purple Profile (Lenovo Vantage-style)
GTK4 widget with CPU/GPU sliders and interactive Cairo fan curve editor.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk
import math
import cairo
import threading

from loq_control.core.custom_profile import CustomProfileConfig, CustomProfileApplicator


class FanCurveEditor(Gtk.DrawingArea):
    """Interactive 7-point fan curve editor rendered with Cairo."""

    POINT_RADIUS = 8
    SAFETY_FLOOR_TEMP = 80   # °C — below this, any fan% allowed
    SAFETY_FLOOR_PCT  = 60   # % — minimum fan speed above safety floor

    def __init__(self, curve: list):
        super().__init__()
        self.set_size_request(400, 200)
        self.set_hexpand(True)
        self.curve = [list(p) for p in curve]  # [[temp, pct], ...]
        self._drag_idx = None
        self._on_change = None

        # Drawing
        self.set_draw_func(self._draw)

        # Drag events
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

    def set_on_change(self, cb):
        self._on_change = cb

    def set_curve(self, curve):
        self.curve = [list(p) for p in curve]
        self.queue_draw()

    def get_curve(self):
        return [list(p) for p in self.curve]

    # ── coordinate helpers ─────────────────────────────────────────────────

    def _to_canvas(self, temp, pct, w, h):
        pad = 30
        x = pad + (temp - 30) / (100 - 30) * (w - 2 * pad)
        y = pad + (1 - pct / 100) * (h - 2 * pad)
        return x, y

    def _from_canvas(self, cx, cy, w, h):
        pad = 30
        temp = 30 + (cx - pad) / (w - 2 * pad) * (100 - 30)
        pct  = 100 * (1 - (cy - pad) / (h - 2 * pad))
        temp = max(30, min(100, int(round(temp))))
        pct  = max(0,  min(100, int(round(pct))))
        return temp, pct

    # ── drawing ────────────────────────────────────────────────────────────

    def _draw(self, area, cr, w, h):
        pad = 30

        # Background
        cr.set_source_rgba(0.06, 0.08, 0.11, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Safety zone (red overlay above 80°C)
        sx, _ = self._to_canvas(self.SAFETY_FLOOR_TEMP, 0, w, h)
        cr.set_source_rgba(0.9, 0.1, 0.1, 0.08)
        cr.rectangle(sx, pad, w - sx - pad, h - 2 * pad)
        cr.fill()

        # Grid lines
        cr.set_line_width(0.5)
        cr.set_source_rgba(1, 1, 1, 0.06)
        for temp in range(30, 101, 10):
            gx, _ = self._to_canvas(temp, 0, w, h)
            cr.move_to(gx, pad)
            cr.line_to(gx, h - pad)
        for pct in range(0, 101, 20):
            _, gy = self._to_canvas(30, pct, w, h)
            cr.move_to(pad, gy)
            cr.line_to(w - pad, gy)
        cr.stroke()

        # Axis labels
        cr.set_source_rgba(0.6, 0.6, 0.7, 1.0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(9)
        for temp in (40, 60, 80, 100):
            gx, _ = self._to_canvas(temp, 0, w, h)
            cr.move_to(gx - 8, h - pad + 14)
            cr.show_text(f"{temp}°")
        for pct in (25, 50, 75, 100):
            _, gy = self._to_canvas(30, pct, w, h)
            cr.move_to(2, gy + 4)
            cr.show_text(f"{pct}%")

        # Safety floor label
        cr.set_source_rgba(0.9, 0.3, 0.3, 0.8)
        cr.set_font_size(8)
        cr.move_to(sx + 3, pad + 12)
        cr.show_text("Safety Zone")

        # Curve fill
        cr.set_source_rgba(0.6, 0.2, 1.0, 0.12)
        pts = self.curve
        if pts:
            x0, y0 = self._to_canvas(pts[0][0], 0, w, h)
            cr.move_to(x0, h - pad)
            for temp, pct in pts:
                cx, cy = self._to_canvas(temp, pct, w, h)
                cr.line_to(cx, cy)
            xl, _ = self._to_canvas(pts[-1][0], 0, w, h)
            cr.line_to(xl, h - pad)
            cr.close_path()
            cr.fill()

        # Curve line
        cr.set_source_rgba(0.7, 0.3, 1.0, 0.9)
        cr.set_line_width(2.5)
        first = True
        for temp, pct in pts:
            cx, cy = self._to_canvas(temp, pct, w, h)
            if first:
                cr.move_to(cx, cy)
                first = False
            else:
                cr.line_to(cx, cy)
        cr.stroke()

        # Control points
        for i, (temp, pct) in enumerate(pts):
            cx, cy = self._to_canvas(temp, pct, w, h)
            # Glow
            cr.set_source_rgba(0.7, 0.3, 1.0, 0.25)
            cr.arc(cx, cy, self.POINT_RADIUS + 4, 0, 2 * math.pi)
            cr.fill()
            # Point
            cr.set_source_rgba(0.85, 0.5, 1.0, 1.0)
            cr.arc(cx, cy, self.POINT_RADIUS, 0, 2 * math.pi)
            cr.fill()
            # Tooltip
            cr.set_source_rgba(1, 1, 1, 0.8)
            cr.set_font_size(8)
            cr.move_to(cx - 10, cy - 12)
            cr.show_text(f"{temp}°/{pct}%")

    # ── drag interaction ───────────────────────────────────────────────────

    def _point_at(self, x, y, w, h):
        for i, (temp, pct) in enumerate(self.curve):
            cx, cy = self._to_canvas(temp, pct, w, h)
            if math.hypot(x - cx, y - cy) <= self.POINT_RADIUS + 6:
                return i
        return None

    def _on_drag_begin(self, gesture, sx, sy):
        w = self.get_width()
        h = self.get_height()
        self._drag_idx = self._point_at(sx, sy, w, h)
        self._drag_start_x = sx
        self._drag_start_y = sy
        self._drag_orig = list(self.curve[self._drag_idx]) if self._drag_idx is not None else None

    def _on_drag_update(self, gesture, ox, oy):
        if self._drag_idx is None:
            return
        w = self.get_width()
        h = self.get_height()
        cx = self._drag_start_x + ox
        cy = self._drag_start_y + oy
        temp, pct = self._from_canvas(cx, cy, w, h)

        # Enforce safety floor: above 80°C minimum 60%
        if temp >= self.SAFETY_FLOOR_TEMP:
            pct = max(pct, self.SAFETY_FLOOR_PCT)

        # Keep temperatures in order
        if self._drag_idx > 0:
            temp = max(temp, self.curve[self._drag_idx - 1][0] + 5)
        if self._drag_idx < len(self.curve) - 1:
            temp = min(temp, self.curve[self._drag_idx + 1][0] - 5)

        self.curve[self._drag_idx] = [temp, pct]
        self.queue_draw()
        if self._on_change:
            self._on_change(self.curve)

    def _on_drag_end(self, gesture, ox, oy):
        self._drag_idx = None


class _Slider(Gtk.Box):
    """Labeled horizontal slider with value display."""

    def __init__(self, label, min_val, max_val, step, value, unit="", on_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._on_change = on_change

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=label, halign=Gtk.Align.START, hexpand=True)
        lbl.add_css_class("caption")
        self.val_lbl = Gtk.Label(label=f"{value}{unit}")
        self.val_lbl.add_css_class("caption")
        top.append(lbl)
        top.append(self.val_lbl)
        self.append(top)

        self._unit = unit
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_val, max_val, step)
        self.scale.set_value(value)
        self.scale.set_hexpand(True)
        self.scale.set_draw_value(False)
        self.scale.connect("value-changed", self._changed)
        self.append(self.scale)

    def get_value(self):
        return self.scale.get_value()

    def set_value(self, v):
        self.scale.set_value(v)

    def _changed(self, scale):
        v = scale.get_value()
        self.val_lbl.set_label(f"{int(v)}{self._unit}")
        if self._on_change:
            self._on_change(v)


class CustomModePanel(Gtk.Box):
    """
    Full Lenovo Vantage-style Custom Mode UI.
    Shows CPU sliders, GPU sliders, GPU OC, and interactive fan curve.
    """

    def __init__(self, on_apply=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_margin_top(0)
        self.on_apply = on_apply
        self._first_open = True

        self.cfg = CustomProfileConfig.load()
        self._build_ui()
        self._sync_from_cfg()

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        self.append(scroll)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        inner.set_margin_top(24)
        inner.set_margin_start(24)
        inner.set_margin_end(24)
        inner.set_margin_bottom(24)
        scroll.set_child(inner)

        # ── Header ─────────────────────────────────────────────────────────
        head_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label="🟣  Custom Performance Tuner", halign=Gtk.Align.START)
        title.add_css_class("heading")
        sub = Gtk.Label(label="Fine-grained CPU, GPU, and fan control — Lenovo Vantage style",
                        halign=Gtk.Align.START)
        sub.add_css_class("caption")
        head_box.append(title)
        head_box.append(sub)
        inner.append(head_box)

        # ── Warning banner ──────────────────────────────────────────────────
        warn = Gtk.Label(
            label="⚠  Custom mode enables advanced power controls. Hardware safety limits remain enforced.",
            halign=Gtk.Align.START, wrap=True
        )
        warn.add_css_class("caption-dim")
        warn.set_margin_bottom(4)
        inner.append(warn)

        # ── CPU Card ───────────────────────────────────────────────────────
        inner.append(self._section_label("🖥  CPU Power Limits"))
        cpu_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        cpu_card.add_css_class("industrial-card")
        inner.append(cpu_card)

        self.pl1 = _Slider("PL1 — Long-Term (Sustained) Power Limit",
                           10, 120, 1, self.cfg.cpu_pl1_watts, "W")
        self.pl2 = _Slider("PL2 — Short-Term (Burst) Power Limit",
                           15, 160, 1, self.cfg.cpu_pl2_watts, "W")
        self.thermal = _Slider("CPU Thermal Limit",
                               70, 100, 1, self.cfg.cpu_thermal_limit_c, "°C")
        for s in (self.pl1, self.pl2, self.thermal):
            cpu_card.append(s)

        # CPU info
        pl_info = Gtk.Label(
            label="💡 Lower PL1 to 35–50W for cooler gaming. PL2 affects burst tasks like opening apps.",
            halign=Gtk.Align.START, wrap=True)
        pl_info.add_css_class("caption-dim")
        cpu_card.append(pl_info)

        # ── GPU Card ───────────────────────────────────────────────────────
        inner.append(self._section_label("🎮  GPU Power Tuning"))
        gpu_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        gpu_card.add_css_class("industrial-card")
        inner.append(gpu_card)

        self.ctgp = _Slider("cTGP — Base GPU Power Target",
                            30, 150, 1, self.cfg.gpu_ctgp_watts, "W")
        self.dynboost = _Slider("Dynamic Boost (CPU→GPU power shift)",
                                0, 30, 1, self.cfg.gpu_dynamic_boost_watts, "W")
        gpu_card.append(self.ctgp)
        gpu_card.append(self.dynboost)

        # GPU OC section
        oc_sep = Gtk.Separator()
        gpu_card.append(oc_sep)

        oc_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        oc_lbl = Gtk.Label(label="GPU Overclocking", halign=Gtk.Align.START, hexpand=True)
        oc_lbl.add_css_class("caption")
        self.oc_check = Gtk.CheckButton(label="Enable", active=self.cfg.gpu_oc_enabled)
        oc_header.append(oc_lbl)
        oc_header.append(self.oc_check)
        gpu_card.append(oc_header)

        self.core_oc = _Slider("Core Clock Offset", -200, 300, 1,
                               self.cfg.gpu_core_offset_mhz, " MHz")
        self.mem_oc = _Slider("Memory Clock Offset", -500, 1000, 1,
                              self.cfg.gpu_mem_offset_mhz, " MHz")

        self.oc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.oc_box.append(self.core_oc)
        self.oc_box.append(self.mem_oc)
        self.oc_box.set_sensitive(self.cfg.gpu_oc_enabled)
        gpu_card.append(self.oc_box)

        self.oc_check.connect("toggled", lambda c: self.oc_box.set_sensitive(c.get_active()))

        gpu_info = Gtk.Label(
            label="💡 Safe starting point: Core +100 MHz, Memory +200 MHz. Test stability in games.",
            halign=Gtk.Align.START, wrap=True)
        gpu_info.add_css_class("caption-dim")
        gpu_card.append(gpu_info)

        # ── Fan Curve Card ─────────────────────────────────────────────────
        inner.append(self._section_label("🌡  Fan Curve Editor"))
        fan_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        fan_card.add_css_class("industrial-card")
        inner.append(fan_card)

        fan_info = Gtk.Label(
            label="Drag points to set fan speed vs temperature. Red zone (≥80°C) enforces minimum 60%.",
            halign=Gtk.Align.START, wrap=True)
        fan_info.add_css_class("caption-dim")
        fan_card.append(fan_info)

        self.fan_editor = FanCurveEditor(self.cfg.fan_curve)
        fan_card.append(self.fan_editor)

        # Fan curve preset buttons
        preset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for label, fn in [("Performance Curve", "reset_to_performance"),
                          ("Silent Curve", "reset_to_silent")]:
            btn = Gtk.Button(label=label)
            btn.add_css_class("suggested-action" if "Performance" in label else "")
            btn.connect("clicked", self._fan_preset, fn)
            preset_row.append(btn)
        fan_card.append(preset_row)

        # ── Bottom Action Bar ──────────────────────────────────────────────
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        action_bar.set_margin_top(8)
        action_bar.set_margin_bottom(8)
        action_bar.set_halign(Gtk.Align.END)
        inner.append(action_bar)

        reset_perf = Gtk.Button(label="Reset to Performance Defaults")
        reset_perf.connect("clicked", lambda _: self._reset("reset_to_performance"))
        reset_silent = Gtk.Button(label="Reset to Silent Defaults")
        reset_silent.connect("clicked", lambda _: self._reset("reset_to_silent"))

        self.apply_btn = Gtk.Button(label="⚡  Apply & Save")
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.connect("clicked", self._apply)

        for w in (reset_perf, reset_silent, self.apply_btn):
            action_bar.append(w)

    def _section_label(self, text):
        lbl = Gtk.Label(label=text, halign=Gtk.Align.START, margin_top=8)
        lbl.add_css_class("caption")
        return lbl

    # ── Sync ───────────────────────────────────────────────────────────────

    def _sync_from_cfg(self):
        self.pl1.set_value(self.cfg.cpu_pl1_watts)
        self.pl2.set_value(self.cfg.cpu_pl2_watts)
        self.thermal.set_value(self.cfg.cpu_thermal_limit_c)
        self.ctgp.set_value(self.cfg.gpu_ctgp_watts)
        self.dynboost.set_value(self.cfg.gpu_dynamic_boost_watts)
        self.core_oc.set_value(self.cfg.gpu_core_offset_mhz)
        self.mem_oc.set_value(self.cfg.gpu_mem_offset_mhz)
        self.oc_check.set_active(self.cfg.gpu_oc_enabled)
        self.oc_box.set_sensitive(self.cfg.gpu_oc_enabled)
        self.fan_editor.set_curve(self.cfg.fan_curve)

    def _read_from_ui(self):
        self.cfg.cpu_pl1_watts = int(self.pl1.get_value())
        self.cfg.cpu_pl2_watts = int(self.pl2.get_value())
        self.cfg.cpu_thermal_limit_c = int(self.thermal.get_value())
        self.cfg.gpu_ctgp_watts = int(self.ctgp.get_value())
        self.cfg.gpu_dynamic_boost_watts = int(self.dynboost.get_value())
        self.cfg.gpu_core_offset_mhz = int(self.core_oc.get_value())
        self.cfg.gpu_mem_offset_mhz = int(self.mem_oc.get_value())
        self.cfg.gpu_oc_enabled = self.oc_check.get_active()
        self.cfg.fan_curve = self.fan_editor.get_curve()

    # ── Actions ────────────────────────────────────────────────────────────

    def _fan_preset(self, btn, method_name):
        tmp = CustomProfileConfig.load()
        getattr(tmp, method_name)()
        self.fan_editor.set_curve(tmp.fan_curve)

    def _reset(self, method_name):
        getattr(self.cfg, method_name)()
        self._sync_from_cfg()

    def _apply(self, btn):
        self._read_from_ui()
        self.cfg.save()
        self.apply_btn.set_label("Applying...")
        self.apply_btn.set_sensitive(False)

        cfg_snapshot = self.cfg

        def _do():
            ok = CustomProfileApplicator.get().apply(cfg_snapshot)
            GLib.idle_add(self._apply_done, ok)

        threading.Thread(target=_do, daemon=True).start()

    def _apply_done(self, ok):
        self.apply_btn.set_label("⚡  Apply & Save")
        self.apply_btn.set_sensitive(True)
        if self.on_apply:
            self.on_apply(ok)
