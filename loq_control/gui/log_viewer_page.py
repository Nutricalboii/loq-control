import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from pathlib import Path

class LogViewerPage(Gtk.Box):
    def __init__(self, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.ctrl = controller
        
        self.append(Gtk.Label(label="<b>Hardware Event Logs</b>", use_markup=True, halign=Gtk.Align.START))

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)

        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.add_css_class("monospace")
        scrolled.set_child(self.text_view)

        # Path to daemon log
        self.log_path = Path.home() / ".local/state/loq-control/logs/daemon.log"
        self._last_size = 0
        
        GLib.timeout_add(2000, self.refresh_logs)

    def refresh_logs(self):
        if not self.log_path.exists():
            return True
            
        current_size = self.log_path.stat().st_size
        if current_size == self._last_size:
            return True

        try:
            with open(self.log_path, "r") as f:
                # For efficiency, we just read the last 50 lines if the file is huge
                content = f.read()
                lines = content.splitlines()
                display_lines = lines[-100:] # Show last 100 lines
                
                buffer = self.text_view.get_buffer()
                buffer.set_text("\n".join(display_lines))
                
                # Auto scroll to bottom
                adj = self.text_view.get_vadjustment()
                if adj:
                    adj.set_value(adj.get_upper() - adj.get_page_size())
                    
        except Exception:
            pass

        self._last_size = current_size
        return True
