#!/usr/bin/env python3
"""
LOQ Control CLI Wrappper

Usage:
  loq-control.py --probe   : Run hardware capability discovery engine and print JSON
  loq-control.py           : Launch the GTK4 GUI
"""

import sys
import json
from loq_control.core.capability_probe import CapabilityProbe

def run_probe():
    print("LOQ Control Hardware Discovery Engine")
    print("-------------------------------------")
    print("Scanning hardware capabilities... (bypassing cache)")
    
    probe = CapabilityProbe.get()
    caps = probe.probe_all()  # Force execution
    
    # Remove large timestamp for cleaner output
    caps_out = dict(caps)
    if "_timestamp" in caps_out:
        del caps_out["_timestamp"]
        
    print("\n" + json.dumps(caps_out, indent=4))
    print("\nCapabilities saved to ~/.config/loq-control/capabilities.json")
    sys.exit(0)

def main():
    if "--probe" in sys.argv:
        run_probe()
    else:
        # Launch GUI
        import asyncio
        from loq_control.gui.main import main as start_gui
        
        # Start the GUI
        sys.exit(start_gui())

if __name__ == "__main__":
    main()
