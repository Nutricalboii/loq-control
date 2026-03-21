import subprocess


def set_mode(mode):

    if mode not in [
        "low-power",
        "balanced",
        "balanced-performance",
        "performance",
        "custom"
    ]:
        return

    subprocess.run(
        f"echo {mode} | sudo tee /sys/firmware/acpi/platform_profile",
        shell=True
    )
