import subprocess


def conservation_on():
    subprocess.run(
        "echo 80 | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold",
        shell=True,
    )


def conservation_off():
    subprocess.run(
        "echo 100 | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold",
        shell=True,
    )
