import subprocess

def igpu():
    subprocess.run("sudo prime-select intel", shell=True)

def hybrid():
    subprocess.run("sudo prime-select on-demand", shell=True)

def nvidia():
    subprocess.run("sudo prime-select nvidia", shell=True)
