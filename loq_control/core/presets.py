from . import power
from . import fan


def battery_mode():
    power.battery()
    fan.quiet()


def balanced_mode():
    power.balanced()
    fan.balanced()


def gaming_mode():
    power.performance()
    fan.performance()


def overclock_mode():
    power.performance()
    fan.custom()
