import subprocess
import re

def cpu_temp():
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        match = re.search(r'Package id 0:\s+\+([0-9.]+)', out)
        if match:
            return float(match.group(1))
    except:
        pass
    return 0

def battery_draw():
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        match = re.search(r'power1:\s+([0-9.]+)', out)
        if match:
            return float(match.group(1))
    except:
        pass
    return 0
