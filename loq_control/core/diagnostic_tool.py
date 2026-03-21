"""
Diagnostic Tool — Scans logs for hardware stability signals.
Analyzes transition frequency, oscillation patterns, and thermal anomalies.
"""

from pathlib import Path
import re
from datetime import datetime
from typing import List, Dict

class LogAuditor:
    def __init__(self, log_dir: str = "~/.local/state/loq-control/logs"):
        self.log_path = Path(log_dir).expanduser() / "daemon.log"

    def audit(self) -> Dict:
        if not self.log_path.exists():
            return {"error": "No logs found"}

        with open(self.log_path, "r") as f:
            lines = f.readlines()

        results = {
            "total_lines": len(lines),
            "transitions": [],
            "oscillations": [],
            "deadman_events": [],
            "status": "Healthy"
        }

        # Regex for state transitions
        # [2026-03-21 15:00:00] [DAEMON] [INFO] State transition accepted: power_profile -> performance by gui
        trans_re = re.compile(r"State transition accepted: (.*?) -> (.*?) by (.*)")
        deadman_re = re.compile(r"SmartFan DEADMAN SWITCH")

        for line in lines:
            if deadman_re.search(line):
                results["deadman_events"].append(line.strip())
            
            match = trans_re.search(line)
            if match:
                results["transitions"].append({
                    "key": match.group(1),
                    "val": match.group(2),
                    "src": match.group(3)
                })

        # Check for fan oscillations (frequency check)
        # If the same key changes > 5 times in a sliding window
        # (Simplified for this diagnostic tool)
        if len(results["transitions"]) > 20:
             # Basic check: are the last 10 transitions of the same key?
             last_keys = [t["key"] for t in results["transitions"][-10:]]
             if last_keys.count("fan_mode") > 5 or last_keys.count("platform_profile") > 5:
                 results["oscillations"].append("Warning: High frequency mode switching detected!")
                 results["status"] = "Warning: Oscillation detected"

        if results["deadman_events"]:
            results["status"] = "Critical: Hardware Failsafe Triggered"

        return results

if __name__ == "__main__":
    auditor = LogAuditor()
    report = auditor.audit()
    print("--- LOQ CONTROL DIAGNOSTIC REPORT ---")
    print(f"Status: {report['status']}")
    print(f"Total Logged Events: {report['total_lines']}")
    print(f"Detected Transitions: {len(report['transitions'])}")
    
    if report["deadman_events"]:
        print(f"\nCRITICAL: {len(report['deadman_events'])} Deadman failsafes detected!")
        for e in report["deadman_events"]:
            print(f"  > {e}")

    if report["oscillations"]:
        print(f"\nOSCILLATIONS: {len(report['oscillations'])} warnings.")
