# LOQ Control: Hardware Stability & Software Safety

> [!WARNING]
> This application performs hardware-level writes to CPU power limits, GPU runtime states, and fan PWM controllers. Use at your own risk.

## Smart Fan Deadman Switch
To prevent thermal runaway, LOQ Control implements a **Deadman Switch** safety protocol:
1. **Telemetry Check**: If thermal sensors return `NaN` or become unreachable for > 3 ticks, the engine immediately halts.
2. **Critical Threshold**: If any core or junction sensor hits **95°C**, the software instantly relinquishes control.
3. **BIOS Rescue**: On a safety trigger, the command `echo performance > platform_profile` is forced to the kernel, engaging the native manufacturer fan curves for immediate cooling.

## Stability Validation
Prior to enabling the Smart Fan engine in production, it is recommended to run the `loq_control/core/diagnostic_tool.py` to ensure your system does not exhibit fan oscillations or state-lock contention.
