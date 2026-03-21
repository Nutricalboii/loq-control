import subprocess
import threading


def _run(cmd):
    subprocess.run(cmd, shell=True)


def igpu(callback=None):
    def task():
        _run("sudo prime-select intel")
        if callback:
            callback()
    threading.Thread(target=task).start()


def hybrid(callback=None):
    def task():
        _run("sudo prime-select on-demand")
        if callback:
            callback()
    threading.Thread(target=task).start()


def nvidia(callback=None):
    def task():
        _run("sudo prime-select nvidia")
        if callback:
            callback()
    threading.Thread(target=task).start()
