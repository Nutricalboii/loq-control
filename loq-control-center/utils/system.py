
import subprocess

def reboot():
    subprocess.run("systemctl reboot", shell=True)
