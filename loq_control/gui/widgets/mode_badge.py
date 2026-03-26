import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

class ModeBadge(Gtk.Box):
    """
    A glowing industrial badge for performance modes.
    """
    def __init__(self, mode_name="PERFORMANCE", css_class="badge-orange"):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class("industrial-card")
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.START)
        self.set_size_request(-1, 80)
        self.set_spacing(10)
        self.set_margin_top(10)
        self.set_margin_bottom(10)
        
        self.icon = Gtk.Image.new_from_icon_name("power-profile-performance-symbolic")
        self.icon.set_valign(Gtk.Align.CENTER)
        self.icon.set_halign(Gtk.Align.CENTER)
        self.append(self.icon)
        
        self.lbl = Gtk.Label(label=mode_name)
        self.lbl.add_css_class("heading")
        self.append(self.lbl)
        
        is_light = self.get_root() and self.get_root().has_css_class("light-theme")
        if is_light: self.lbl.set_css_classes(["heading", "text-dark"])
        
        self.add_css_class(css_class)

    def update_mode(self, name, css_class):
        self.lbl.set_label(name)
        
        # Theme-aware text color
        is_light = self.get_root() and self.get_root().has_css_class("light-theme")
        if is_light: self.lbl.set_css_classes(["heading", "text-dark"])
        else: self.lbl.set_css_classes(["heading"])

        # Update icons
        icon_map = {
            "PERFORMANCE": "power-profile-performance-symbolic",
            "BALANCED": "power-profile-balanced-symbolic",
            "SILENT": "power-profile-power-saver-symbolic",
            "QUIET": "power-profile-power-saver-symbolic",
            "POWER-SAVER": "power-profile-power-saver-symbolic",
        }
        self.icon.set_from_icon_name(icon_map.get(name, "power-profile-balanced-symbolic"))

        # Clear old classes
        for c in ["badge-blue", "badge-green", "badge-orange", "badge-red"]:
            self.remove_css_class(c)
        self.add_css_class(css_class)
