"""
Named presets — compound operations that apply power + fan profiles.

Uses HardwareService for all writes (never calls core modules directly).
If no HardwareService is available, falls back to direct core calls
for standalone/testing use.
"""

from loq_control.core import power, fan


def battery_mode(hw_service=None):
    if hw_service:
        hw_service.apply_preset("battery", source="preset")
    else:
        power.battery()
        fan.quiet()


def balanced_mode(hw_service=None):
    if hw_service:
        hw_service.apply_preset("balanced", source="preset")
    else:
        power.balanced()
        fan.balanced()


def gaming_mode(hw_service=None):
    if hw_service:
        hw_service.apply_preset("gaming", source="preset")
    else:
        power.performance()
        fan.performance()


def overclock_mode(hw_service=None):
    if hw_service:
        hw_service.apply_preset("overclock", source="preset")
    else:
        power.performance()
        fan.custom()
