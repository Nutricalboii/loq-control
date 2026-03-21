import subprocess
import re


def cpu_temp():
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        match = re.search(r'Package id 0:\s+\+([0-9.]+)', out)
        if match:
            return match.group(1)
    except:
        pass
    return "N/A"
