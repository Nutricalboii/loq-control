import threading
from . import auto_gpu


def start():
    threading.Thread(target=auto_gpu.run, daemon=True).start()
