"""
Stability Report Generator
Reads telemetry CSV → analyses for oscillations, thermal overshoot, and policy spam.
Run: python3 -m loq_control.tools.stability_report [--session <file.csv>]
"""

import csv
import sys
import datetime
from pathlib import Path
from typing import List, Dict


TELEMETRY_DIR = Path.home() / ".local/state/loq-control/telemetry"


def load_session(path: Path) -> List[Dict]:
    """Load a telemetry CSV into a list of row dicts."""
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def analyse(rows: List[Dict]) -> Dict:
    """Analyse a session's telemetry for anomalies."""
    if not rows:
        return {}

    temps = [float(r["cpu_temp"]) for r in rows]
    watts = [float(r["cpu_wattage"]) for r in rows]
    policies = [r["policy_active"] for r in rows]

    # --- Thermal Statistics ---
    max_temp = max(temps)
    avg_temp = sum(temps) / len(temps)
    overshoot_count = sum(1 for t in temps if t > 88.0)

    # --- Thermal Runaway Detection ---
    runaway_events = []
    for i in range(1, len(temps)):
        slope = (temps[i] - temps[i-1])  # per second (1Hz)
        if slope > 1.5 and temps[i] > 80:
            runaway_events.append({"ts": rows[i]["timestamp"], "slope": round(slope, 2), "temp": temps[i]})

    # --- Policy Oscillation Detection ---
    policy_changes = 0
    oscillation_events = []
    for i in range(1, len(policies)):
        if policies[i] != policies[i-1]:
            policy_changes += 1
        # A-B-A in a 6s window = oscillation
        if i >= 2 and policies[i] == policies[i-2] and policies[i] != policies[i-1]:
            oscillation_events.append({"ts": rows[i]["timestamp"], "pattern": f"{policies[i-2]}→{policies[i-1]}→{policies[i]}"})

    # --- Power Statistics ---
    max_watt = max(watts)
    avg_watt = sum(watts) / len(watts)

    return {
        "samples": len(rows),
        "duration_min": round(len(rows) / 60, 1),
        "thermal": {
            "max_temp": max_temp,
            "avg_temp": round(avg_temp, 1),
            "overshoot_count": overshoot_count,
            "runaway_events": len(runaway_events),
        },
        "power": {
            "max_watt": max_watt,
            "avg_watt": round(avg_watt, 1),
        },
        "policy": {
            "total_changes": policy_changes,
            "oscillations": len(oscillation_events),
        },
        "health": _health_grade(overshoot_count, len(runaway_events), len(oscillation_events)),
    }


def _health_grade(overshoots: int, runaways: int, oscillations: int) -> str:
    score = 100
    score -= min(overshoots * 2, 30)
    score -= min(runaways * 15, 45)
    score -= min(oscillations * 5, 25)

    if score >= 90: return f"✅ EXCELLENT ({score}/100)"
    if score >= 70: return f"⚠️  GOOD ({score}/100)"
    if score >= 50: return f"🟡 MODERATE ({score}/100)"
    return f"❌ UNSTABLE ({score}/100)"


def print_report(path: Path, result: Dict):
    print(f"\n{'='*55}")
    print(f"  LOQ Control Stability Report")
    print(f"  Session: {path.name}")
    print(f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")
    print(f"  Total Samples:    {result['samples']} ({result['duration_min']} min)")
    print(f"\n  [THERMAL]")
    t = result["thermal"]
    print(f"    Max Temp:        {t['max_temp']}°C")
    print(f"    Avg Temp:        {t['avg_temp']}°C")
    print(f"    Overshoot:       {t['overshoot_count']} samples above 88°C")
    print(f"    Runaway Events:  {t['runaway_events']}")
    print(f"\n  [POWER]")
    p = result["power"]
    print(f"    Peak Wattage:    {p['max_watt']} W")
    print(f"    Avg Wattage:     {p['avg_watt']} W")
    print(f"\n  [POLICY GOVERNOR]")
    pol = result["policy"]
    print(f"    Total Shifts:    {pol['total_changes']}")
    print(f"    Oscillations:    {pol['oscillations']}")
    print(f"\n  System Health:   {result['health']}")
    print(f"{'='*55}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LOQ Control Stability Report Generator")
    parser.add_argument("--session", type=str, default=None, help="Path to session CSV (or uses latest)")
    args = parser.parse_args()

    if args.session:
        session_path = Path(args.session)
    else:
        # Use latest session
        sessions = sorted(TELEMETRY_DIR.glob("session_*.csv"), key=lambda p: p.stat().st_mtime)
        if not sessions:
            print(f"No telemetry sessions found in {TELEMETRY_DIR}")
            sys.exit(1)
        session_path = sessions[-1]

    print(f"Loading session: {session_path}")
    rows = load_session(session_path)
    result = analyse(rows)
    print_report(session_path, result)


if __name__ == "__main__":
    main()
