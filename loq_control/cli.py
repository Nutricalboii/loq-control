"""
LOQ Control CLI — Unified command-line interface for all subsystems.
Entry point: loq-control
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="loq-control",
        description="LOQ Control — Advanced hardware management for Lenovo LOQ laptops",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  loq-control --probe           Probe hardware capabilities
  loq-control --daemon          Start the background daemon
  loq-control --ui              Launch the GTK dashboard
  loq-control --status          Show current hardware state
  loq-control --sandbox-probe   Run firmware sandbox probe
  loq-control --version         Show version
        """
    )

    parser.add_argument("--probe",          action="store_true", help="Run hardware capability probe")
    parser.add_argument("--daemon",         action="store_true", help="Start background daemon")
    parser.add_argument("--ui",             action="store_true", help="Launch GTK dashboard")
    parser.add_argument("--status",         action="store_true", help="Show live hardware status")
    parser.add_argument("--sandbox-probe",  action="store_true", help="Read-only ACPI/EC probe (root required)")
    parser.add_argument("--safety-status",  action="store_true", help="Show Safety Supervisor status")
    parser.add_argument("--version",        action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print("LOQ Control v0.9.0-rc1 (Phase 6.5 Validation)")
        return

    if args.probe:
        _do_probe()
    elif args.daemon:
        _do_daemon()
    elif args.ui:
        _do_ui()
    elif args.status:
        _do_status()
    elif args.sandbox_probe:
        _do_sandbox()
    elif args.safety_status:
        _do_safety_status()
    else:
        parser.print_help()


def _do_probe():
    print("🔍 Probing hardware capabilities...")
    from loq_control.core.capability_probe import CapabilityProbe
    caps = CapabilityProbe().probe_all()
    for category, features in caps.items():
        if category.startswith("_"): continue
        print(f"\n[{category.upper()}]")
        if isinstance(features, dict):
            for feat, val in features.items():
                status = "✅" if val else "❌"
                print(f"  {status} {feat}: {val}")
        else:
            print(f"  {features}")


def _do_daemon():
    print("🚀 Starting LOQ Control daemon (Ctrl-C to stop)...")
    from loq_control.services.daemon import start, stop
    import signal
    start()
    try:
        signal.pause()
    except KeyboardInterrupt:
        stop()
        print("\n🛑 Daemon stopped.")


def _do_ui():
    print("🖥️  Launching GUI dashboard...")
    from loq_control.gui.main import main as gui_main
    gui_main()


def _do_status():
    from loq_control.core.state_manager import StateManager
    from loq_control.core import monitor, thermals
    state = StateManager().get_state()
    print("📊 LOQ Control — Live Status")
    print("=" * 40)
    print(f"  GPU Mode:       {state.get('gpu_mode', 'unknown')}")
    print(f"  Power Profile:  {state.get('power_profile', 'unknown')}")
    print(f"  Fan Mode:       {state.get('fan_mode', 'unknown')}")
    print(f"  Smart Fan:      {'Active' if state.get('smart_fan_active') else 'Off'}")
    print(f"  CPU Temp:       {thermals.cpu_temp()}°C")
    print(f"  CPU Wattage:    {monitor.cpu_wattage()} W")
    print(f"  CPU Usage:      {monitor.cpu_usage()}%")


def _do_sandbox():
    print("⚠️  FIRMWARE SANDBOX — READ-ONLY RESEARCH MODE")
    print("=" * 50)
    from loq_control.core.sandbox import FirmwareSandbox
    zones = FirmwareSandbox.list_thermal_sensors()
    print(f"\n[THERMAL ZONES] ({len(zones)} found)")
    for z in zones:
        print(f"  {z}")
    print("\n[ACPI CALL TEST - READ ONLY]")
    result = FirmwareSandbox.probe_acpi("\\\\ACPI_TEST_READ")
    print(f"  {result}")


def _do_safety_status():
    from loq_control.core.safety_supervisor import SafetySupervisor
    sup = SafetySupervisor.get()
    if sup:
        print(f"🛡️  Safety Supervisor: {sup.get_status()}")
    else:
        print("Safety Supervisor not running (daemon not started).")


if __name__ == "__main__":
    main()
