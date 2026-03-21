import subprocess


def quiet():
    subprocess.run(
        "echo low-power | sudo tee /sys/firmware/acpi/platform_profile",
        shell=True,
    )


def balanced():
    subprocess.run(
        "echo balanced | sudo tee /sys/firmware/acpi/platform_profile",
        shell=True,
    )


def performance():
    subprocess.run(
        "echo performance | sudo tee /sys/firmware/acpi/platform_profile",
        shell=True,
    )


def custom():
    subprocess.run(
        "echo custom | sudo tee /sys/firmware/acpi/platform_profile",
        shell=True,
    )
