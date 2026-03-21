import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
import subprocess


class GPUPage(Gtk.Box):

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=15)

        self.set_margin_top(30)
        self.set_margin_start(30)

        title = Gtk.Label(label="GPU Control")
        title.set_css_classes(["title-1"])

        igpu = Gtk.Button(label="Integrated Mode")
        igpu.connect("clicked", self.set_igpu)

        hybrid = Gtk.Button(label="Hybrid Mode")
        hybrid.connect("clicked", self.set_hybrid)

        nvidia = Gtk.Button(label="NVIDIA Mode")
        nvidia.connect("clicked", self.set_nvidia)

        self.append(title)
        self.append(igpu)
        self.append(hybrid)
        self.append(nvidia)

    def set_igpu(self, btn):
        subprocess.run("sudo envycontrol -s integrated", shell=True)

    def set_hybrid(self, btn):
        subprocess.run("sudo envycontrol -s hybrid", shell=True)

    def set_nvidia(self, btn):
        subprocess.run("sudo envycontrol -s nvidia", shell=True)
