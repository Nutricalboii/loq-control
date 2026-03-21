import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
import subprocess


class BatteryPage(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        self.set_margin_top(30)
        self.set_margin_start(30)

        title = Gtk.Label(label="Battery Modes")
        title.set_css_classes(["title-1"])

        saver = Gtk.Button(label="Power Saver")
        saver.connect("clicked", self.saver)

        balanced = Gtk.Button(label="Balanced")
        balanced.connect("clicked", self.balanced)

        perf = Gtk.Button(label="Performance")
        perf.connect("clicked", self.performance)

        self.append(title)
        self.append(saver)
        self.append(balanced)
        self.append(perf)

    def saver(self, btn):
        subprocess.run("powerprofilesctl set power-saver", shell=True)

    def balanced(self, btn):
        subprocess.run("powerprofilesctl set balanced", shell=True)

    def performance(self, btn):
        subprocess.run("powerprofilesctl set performance", shell=True)
