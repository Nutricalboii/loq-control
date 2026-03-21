import subprocess
import re


def battery_power():
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        match = re.search(r'power1:\s+([0-9.]+)', out)
        if match:
            return match.group(1)
    except:
        pass
    return "0"


def ssd_temp():
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        match = re.search(r'Composite:\s+\+([0-9.]+)', out)
        if match:
            return match.group(1)
    except:
        pass
    return "N/A"
