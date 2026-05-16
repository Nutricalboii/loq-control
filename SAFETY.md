# LOQ Control: Hardware Stability & Software Safety

> [!WARNING]
> This application performs hardware-level writes to CPU power limits, GPU runtime states, and fan PWM controllers. Use at your own risk.

## Smart Fan Deadman Switch
To prevent thermal runaway, LOQ Control implements a **Deadman Switch** safety protocol:
1. **Telemetry Check**: If thermal sensors return `NaN` or become unreachable for > 3 ticks, the engine immediately halts.
2. **Critical Threshold**: If any core or junction sensor hits **95°C**, the software instantly relinquishes control.
3. **BIOS Rescue**: On a safety trigger, the command `echo performance > platform_profile` is forced to the kernel, engaging the native manufacturer fan curves for immediate cooling.

## Stability & Universal Support
LOQ Control is tested for stability across multiple Linux distributions. While the underlying hardware calls are universal (ACPI/EC), the following safety measures ensure a consistent experience:

1. **Kernel Compatibility**: Requires Kernel 5.15+ for reliable `platform_profile` support.
2. **Distro-Agnostic Failbacks**: If a distro-specific utility (like `prime-select`) is missing, the engine gracefully disables the affected feature while maintaining core thermal protections.
3. **Permission Safety**: All hardware writes are gated behind `sudo` to prevent unauthorized EC manipulation.

