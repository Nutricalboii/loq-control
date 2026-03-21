import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

class DashboardPage(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        self.set_margin_top(30)
        self.set_margin_start(30)

        title = Gtk.Label(label="System Overview")
        title.set_css_classes(["title-1"])

        cpu = Gtk.Label(label="CPU Usage")
        ram = Gtk.Label(label="RAM Usage")
        temp = Gtk.Label(label="Temperature")

        self.append(title)
        self.append(cpu)
        self.append(ram)
        self.append(temp)
