import psutil
import subprocess


def cpu_usage():
    return psutil.cpu_percent()


def ram_usage():
    return psutil.virtual_memory().percent


def battery_power():
    try:
        out = subprocess.check_output("sensors", shell=True).decode()
        for line in out.splitlines():
            if "power1:" in line:
                return float(line.split()[1])
    except:
        pass
    return 0


def gpu_usage():
    try:
        out = subprocess.check_output(
            "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits",
            shell=True
        ).decode().strip()
        return float(out)
    except:
        return 0
