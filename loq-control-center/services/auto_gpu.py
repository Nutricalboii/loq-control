import psutil
import time
import subprocess

def run():

    last = None

    while True:

        battery = psutil.sensors_battery()

        if battery is not None:

            if battery.power_plugged and last != "ac":
                subprocess.run("prime-select on-demand", shell=True)
                last = "ac"

            elif not battery.power_plugged and last != "bat":
                subprocess.run("prime-select intel", shell=True)
                last = "bat"

        time.sleep(20)
