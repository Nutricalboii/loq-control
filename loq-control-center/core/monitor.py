import psutil
import subprocess

def cpu_usage():
    return psutil.cpu_percent()

def ram_usage():
    return psutil.virtual_memory().percent

def gpu_usage():
    try:
        out = subprocess.check_output(
            "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits",
            shell=True
        )
        return int(out.decode().strip())
    except:
        return 0
