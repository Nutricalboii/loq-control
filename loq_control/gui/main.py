import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk

import subprocess
import psutil
import random

from loq_control.version import APP_NAME, VERSION


# ================= GRAPH =================

class PerformanceGraph(Gtk.DrawingArea):

    def __init__(self):
        super().__init__()
        self.set_content_width(420)
        self.set_content_height(120)

        self.cpu_points = [0]*60

        GLib.timeout_add(1000, self.update_graph)
        self.set_draw_func(self.draw)

    def update_graph(self):
        cpu = psutil.cpu_percent()
        self.cpu_points.pop(0)
        self.cpu_points.append(cpu)
        self.queue_draw()
        return True

    def draw(self, area, cr, width, height):

        cr.set_source_rgb(0.2,0.8,0.4)
        cr.set_line_width(2)

        step = width/len(self.cpu_points)

        for i,val in enumerate(self.cpu_points):
            x = i*step
            y = height - (val/100)*height

            if i==0:
                cr.move_to(x,y)
            else:
                cr.line_to(x,y)

        cr.stroke()


# ================= MAIN =================

class Dashboard(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app)

        self.set_title(f"{APP_NAME} v{VERSION} — Developed by Vaibhav Sharma")
        self.set_default_size(460,620)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(15)
        outer.set_margin_bottom(15)
        outer.set_margin_start(15)
        outer.set_margin_end(15)

        self.set_child(outer)

        title = Gtk.Label(label="LOQ Hardware Control Center")
        outer.append(title)

        # ===== GPU =====

        outer.append(Gtk.Separator())

        gpu_title = Gtk.Label(label="GPU Modes")
        outer.append(gpu_title)

        igpu = Gtk.Button(label="Integrated Mode")
        igpu.connect("clicked", self.set_igpu)
        outer.append(igpu)

        hybrid = Gtk.Button(label="Hybrid Mode")
        hybrid.connect("clicked", self.set_hybrid)
        outer.append(hybrid)

        nvidia = Gtk.Button(label="NVIDIA Mode")
        nvidia.connect("clicked", self.set_nvidia)
        outer.append(nvidia)

        # ===== POWER =====

        outer.append(Gtk.Separator())

        power_title = Gtk.Label(label="Power Profiles")
        outer.append(power_title)

        saver = Gtk.Button(label="Power Saver")
        saver.connect("clicked", lambda x: subprocess.run("powerprofilesctl set power-saver",shell=True))
        outer.append(saver)

        balanced = Gtk.Button(label="Balanced")
        balanced.connect("clicked", lambda x: subprocess.run("powerprofilesctl set balanced",shell=True))
        outer.append(balanced)

        performance = Gtk.Button(label="Performance")
        performance.connect("clicked", lambda x: subprocess.run("powerprofilesctl set performance",shell=True))
        outer.append(performance)

        # ===== STATS =====

        outer.append(Gtk.Separator())

        stat_title = Gtk.Label(label="System Monitoring")
        outer.append(stat_title)

        self.cpu = Gtk.Label()
        self.ram = Gtk.Label()
        self.batt = Gtk.Label()

        outer.append(self.cpu)
        outer.append(self.ram)
        outer.append(self.batt)

        # ===== GRAPH =====

        outer.append(Gtk.Separator())

        graph = PerformanceGraph()
        outer.append(graph)

        # ===== ABOUT =====

        outer.append(Gtk.Separator())

        about = Gtk.Button(label="About Developer")
        about.connect("clicked", self.show_about)
        outer.append(about)

        GLib.timeout_add_seconds(2,self.update_stats)

    # ================= GPU =================

    def set_igpu(self,widget):
        subprocess.run("sudo envycontrol -s integrated",shell=True)
        self.ask_reboot()

    def set_hybrid(self,widget):
        subprocess.run("sudo envycontrol -s hybrid",shell=True)
        self.ask_reboot()

    def set_nvidia(self,widget):
        subprocess.run("sudo envycontrol -s nvidia",shell=True)
        self.ask_reboot()

    # ================= DIALOG =================

    def ask_reboot(self):

        dialog = Gtk.Dialog(title="Reboot Required", transient_for=self)
        dialog.set_modal(True)

        box = dialog.get_content_area()
        label = Gtk.Label(label="GPU Mode changed.\nSystem reboot required.")
        box.append(label)

        reboot = Gtk.Button(label="Reboot Now")
        later = Gtk.Button(label="Later")

        reboot.connect("clicked", lambda x: subprocess.run("systemctl reboot",shell=True))
        later.connect("clicked", lambda x: dialog.close())

        box.append(reboot)
        box.append(later)

        dialog.present()

    def show_about(self,widget):

        dialog = Gtk.Dialog(title="About", transient_for=self)
        dialog.set_modal(True)

        box = dialog.get_content_area()

        txt = Gtk.Label(label=
        "LOQ Control Center\n\n"
        "Version: "+VERSION+"\n"
        "Developer: Vaibhav Sharma\n"
        "GitHub: nutricalboii\n\n"
        "Open Source Project"
        )

        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda x: dialog.close())

        box.append(txt)
        box.append(close)

        dialog.present()

    # ================= STATS =================

    def update_stats(self):

        self.cpu.set_text(f"CPU Usage: {psutil.cpu_percent()} %")
        self.ram.set_text(f"RAM Usage: {psutil.virtual_memory().percent} %")

        b = psutil.sensors_battery()

        if b:
            self.batt.set_text(f"Battery: {round(b.percent)} %")
        else:
            self.batt.set_text("Battery: AC Connected")

        return True


class App(Gtk.Application):

    def __init__(self):
        super().__init__()

    def do_activate(self):
        win = Dashboard(self)
        win.present()


app = App()
app.run()
