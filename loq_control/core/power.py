import subprocess


def battery():
    subprocess.Popen("powerprofilesctl set power-saver", shell=True)


def balanced():
    subprocess.Popen("powerprofilesctl set balanced", shell=True)


def performance():
    subprocess.Popen("powerprofilesctl set performance", shell=True)
