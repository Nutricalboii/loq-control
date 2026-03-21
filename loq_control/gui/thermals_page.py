import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

class ThermalsPage(Gtk.Box):
    def __init__(self, controller):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.set_margin_top(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.ctrl = controller

        self.append(Gtk.Label(label="<b>Thermal Zones &amp; Fan RPM</b>", use_markup=True, halign=Gtk.Align.START, xalign=0))

        self.grid = Gtk.Grid(column_spacing=20, row_spacing=12)
        self.append(self.grid)
        
        self.bars = {} # metric_name -> (label, level_bar)

    def update_stats(self):
        data = self.ctrl.get_thermal_telemetry()
        if not data:
            return

        metrics = []
        
        # 1. Parse Temperatures (Dict)
        temps = data.get("temps", {})
        for name, val in temps.items():
            metrics.append((f"TEMP {name}", val))
            
        # 2. Parse Fans (List)
        fans = data.get("fans", [])
        for i, f in enumerate(fans):
            rpm = f.get("rpm")
            if rpm is not None:
                metrics.append((f"FAN {i} RPM", rpm))

        # Update or Create widgets in the grid
        for i, (name, val) in enumerate(metrics):
            if name not in self.bars:
                # Create label
                lbl = Gtk.Label(label=name, halign=Gtk.Align.START)
                
                # Create LevelBar for temperatures/rpm
                bar = Gtk.LevelBar()
                bar.set_hexpand(True)
                bar.set_size_request(200, 10)
                
                # Set range based on type
                if "rpm" in name.lower():
                    bar.set_max_value(6000)
                else:
                    bar.set_max_value(100)
                    # Add heat offsets
                    bar.add_offset_value("high", 80)
                    bar.add_offset_value("critical", 92)

                self.grid.attach(lbl, 0, i, 1, 1)
                self.grid.attach(bar, 1, i, 1, 1)
                self.bars[name] = (lbl, bar)

            _, bar = self.bars[name]
            try:
                bar.set_value(float(val))
            except (ValueError, TypeError):
                pass

