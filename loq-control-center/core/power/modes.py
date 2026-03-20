import subprocess

def battery():
    subprocess.run("sudo powerprofilesctl set power-saver", shell=True)
    subprocess.run("sudo cpupower frequency-set -g powersave", shell=True)

def balanced():
    subprocess.run("sudo powerprofilesctl set balanced", shell=True)

def performance():
    subprocess.run("sudo powerprofilesctl set performance", shell=True)
