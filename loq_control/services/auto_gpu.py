import time
import os
import subprocess


def on_ac():
    return os.path.exists("/sys/class/power_supply/AC/online") and \
        open("/sys/class/power_supply/AC/online").read().strip() == "1"


def run():
    last = None
    while True:
        state = on_ac()
        if state != last:
            if state:
                subprocess.run("sudo prime-select on-demand", shell=True)
            else:
                subprocess.run("sudo prime-select intel", shell=True)
            last = state
        time.sleep(10)
