import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

class HeatBar(Gtk.Box):
    """
    A gradient progress bar for temperatures in LOQ Control v2.
    Changes color from Cyan (Cool) -> Green (Safe) -> Orange (Warn) -> Red (Hot).
    """
    def __init__(self, label="CPU", target_temp=100):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.target_temp = target_temp
        
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.lbl_name = Gtk.Label(label=label, halign=Gtk.Align.START)
        self.lbl_name.add_css_class("caption")
        
        self.lbl_val = Gtk.Label(label="--°C", halign=Gtk.Align.END, hexpand=True)
        self.lbl_val.add_css_class("monospace")
        
        header.append(self.lbl_name)
        header.append(self.lbl_val)
        self.append(header)

        is_light = self.get_root() and self.get_root().has_css_class("light-theme")
        if is_light: self.lbl_val.add_css_class("text-dark")
        
        self.bar = Gtk.LevelBar()
        self.bar.set_min_value(30)
        self.bar.set_max_value(target_temp)
        self.bar.add_css_class("thermal-meter")
        self.append(self.bar)

    def set_temp(self, temp):
        self.bar.set_value(temp)
        self.lbl_val.set_label(f"{int(temp)}°C")
        
        # Dynamic styling based on temp range
        self.bar.remove_css_class("badge-green")
        self.bar.remove_css_class("badge-orange")
        self.bar.remove_css_class("badge-red")
        
        if temp < 55:
            pass # Use default CSS var
        elif temp < 75:
            self.bar.add_css_class("badge-green")
        elif temp < 85:
            self.bar.add_css_class("badge-orange")
        else:
            self.bar.add_css_class("badge-red")
