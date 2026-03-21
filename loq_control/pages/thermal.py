import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class ThermalPage(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        self.set_margin_top(30)
        self.set_margin_start(30)

        title = Gtk.Label(label="Thermal Control")
        title.set_css_classes(["title-1"])

        fan = Gtk.Button(label="Fan Curve (Coming Soon)")
        cpu = Gtk.Button(label="Thermal Mode")

        self.append(title)
        self.append(fan)
        self.append(cpu)
