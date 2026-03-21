import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

class StatusBadge(Gtk.Box):
    """
    A reusable pill-shaped badge for displaying system states (GPU, Power, etc.)
    """
    def __init__(self, label="Unknown", color="grey"):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.START)
        
        self._label = Gtk.Label(label=label)
        self._label.set_margin_start(10)
        self._label.set_margin_end(10)
        self._label.set_margin_top(4)
        self._label.set_margin_bottom(4)
        
        self.append(self._label)
        
        # We'll use CSS for the styling
        self.add_css_class("status-badge")
        self.set_status(label, color)

    def set_status(self, text: str, color: str):
        self._label.set_text(text.upper())
        
        # Remove old color classes
        for c in ["blue", "green", "red", "orange", "grey"]:
            self.remove_css_class(f"badge-{c}")
            
        self.add_css_class(f"badge-{color}")
