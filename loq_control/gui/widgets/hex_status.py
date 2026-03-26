import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
import math
import cairo

class HexStatus(Gtk.DrawingArea):
    """
    A futuristic hexagonal status indicator for LOQ Control v2.
    Draws a sharp hex with a glowing outline and dynamic percentage fill.
    """
    def __init__(self, label="METRIC", color="#00d4ff"):
        super().__init__()
        self.label = label
        self.color = color
        self.percentage = 0.0 # 0.0 to 1.0
        
        self.set_content_width(120)
        self.set_content_height(140)
        self.set_draw_func(self._draw_cb)
        
    def set_value(self, val):
        self.percentage = max(0.0, min(1.0, val / 100.0))
        self.queue_draw()

    def _draw_cb(self, area, cr, width, height, *args):
        is_light = self.get_root() and self.get_root().has_css_class("light-theme")
        
        # 1. Background (Subtle Hex + Graticule)
        size = min(width, height) / 2.5
        cx, cy = width / 2, height / 2
        
        # Helper to draw hex path
        def draw_hex(ctx, r):
            for i in range(6):
                angle = math.radians(60 * i - 30)
                px = cx + r * math.cos(angle)
                py = cy + r * math.sin(angle)
                if i == 0: ctx.move_to(px, py)
                else: ctx.line_to(px, py)
            ctx.close_path()

        # Techy Rings (Background)
        cr.set_line_width(0.5)
        cr.set_source_rgba(1, 1, 1, 0.03)
        for r_factor in [0.7, 0.9, 1.1]:
            cr.arc(cx, cy, size * r_factor, 0, 2 * math.pi)
            cr.stroke()

        # Crosshair lines
        cr.set_source_rgba(1, 1, 1, 0.05)
        cr.move_to(cx - size*1.2, cy); cr.line_to(cx + size*1.2, cy); cr.stroke()
        cr.move_to(cx, cy - size*1.2); cr.line_to(cx, cy + size*1.2); cr.stroke()

        # Draw outer glowing border
        cr.set_line_width(2)
        r, g, b = self._hex_to_rgb(self.color)
        cr.set_source_rgba(r, g, b, 0.1)
        draw_hex(cr, size + 2)
        cr.stroke()

        # Draw main hex base
        cr.set_source_rgba(0.1, 0.15, 0.2, 0.5)
        draw_hex(cr, size)
        cr.fill_preserve()
        cr.set_source_rgba(r, g, b, 0.3)
        cr.stroke()

        # 2. Fill Effect (Bottom-up with Glow)
        if self.percentage > 0:
            cr.save()
            draw_hex(cr, size)
            cr.clip()
            
            fill_y = cy + size - (size * 2 * self.percentage)
            # Add a subtle gradient to the fill
            grad = cairo.LinearGradient(0, fill_y, 0, cy + size)
            grad.add_color_stop_rgba(0, r, g, b, 0.6)
            grad.add_color_stop_rgba(1, r, g, b, 0.2)
            cr.set_source(grad)
            cr.rectangle(0, fill_y, width, height)
            cr.fill()
            cr.restore()

        # 3. Label and Value
        cr.select_font_face("JetBrains Mono", 0, 0)
        
        # Value text
        cr.set_font_size(24)
        val_text = f"{int(self.percentage * 100)}%"
        ext = cr.text_extents(val_text)
        cr.move_to(cx - ext.width / 2, cy + ext.height / 3)
        if is_light: cr.set_source_rgba(0.1, 0.1, 0.1, 0.9)
        else: cr.set_source_rgba(1, 1, 1, 0.9)
        cr.show_text(val_text)

        # Label text
        cr.set_font_size(10)
        if is_light: cr.set_source_rgba(0.2, 0.2, 0.2, 0.7)
        else: cr.set_source_rgba(r, g, b, 0.7)
        ext = cr.text_extents(self.label)
        cr.move_to(cx - ext.width / 2, cy - size / 1.5)
        cr.show_text(self.label)

    def _hex_to_rgb(self, hex_val):
        hex_val = hex_val.lstrip('#')
        return tuple(int(hex_val[i:i+2], 16) / 255.0 for i in (0, 2, 4))
