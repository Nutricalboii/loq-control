import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
import threading

class GPUPage(Gtk.Box):
    def __init__(self, controller, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_top(20)
        self.set_margin_start(20)
        self.ctrl = controller
        self.window = window

        self.append(Gtk.Label(label="Select active GPU pipeline:", halign=Gtk.Align.START))

        igpu = Gtk.Button(label="Integrated Mode (Power Saver)")
        hybrid = Gtk.Button(label="Hybrid Mode (Dynamic)")
        nvidia = Gtk.Button(label="NVIDIA Only (Gaming)")

        self.append(igpu)
        self.append(hybrid)
        self.append(nvidia)

        igpu.connect("clicked", lambda x: self._gpu_switch("integrated"))
        hybrid.connect("clicked", lambda x: self._gpu_switch("hybrid"))
        nvidia.connect("clicked", lambda x: self._gpu_switch("nvidia"))

    def _gpu_switch(self, mode: str):
        def _do():
            result = self.ctrl.switch_gpu(mode)
            if result.success and result.needs_reboot:
                GLib.idle_add(self.window._show_reboot_dialog)
            elif not result.success:
                GLib.idle_add(self.window._show_error, result.message)

        threading.Thread(target=_do, daemon=True).start()
