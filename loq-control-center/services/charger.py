import time
import subprocess
import psutil

def auto_gpu():
    while True:
        battery = psutil.sensors_battery()
        if battery.power_plugged:
            subprocess.run("prime-select on-demand", shell=True)
        else:
            subprocess.run("prime-select intel", shell=True)
        time.sleep(20)
