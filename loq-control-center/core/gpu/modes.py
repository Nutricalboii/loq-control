import subprocess
import os

def igpu():
    subprocess.run("sudo prime-select intel", shell=True)
    subprocess.run("sudo modprobe -r nvidia_drm nvidia_modeset nvidia", shell=True)

def nvidia():
    subprocess.run("sudo prime-select nvidia", shell=True)

def hybrid():
    subprocess.run("sudo prime-select on-demand", shell=True)

def shutdown_nvidia_pci():
    try:
        gpu = os.popen("lspci | grep -i nvidia | cut -d' ' -f1").read().strip()
        if gpu:
            subprocess.run(f"echo 1 | sudo tee /sys/bus/pci/devices/0000:{gpu}/remove", shell=True)
    except:
        pass
