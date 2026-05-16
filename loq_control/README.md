# LOQ Control Core Module
This directory contains the core logic and GUI components of the LOQ Control suite.

## Requirements
The modules within this package require:
- **Python 3.10+**
- **GTK4 / PyGObject** (for the `gui` subpackage)
- **psutil** & **matplotlib** (for telemetry and graphing)

## Structure
- `core/`: Low-level hardware interaction (ACPI, EC, GPU, Thermal).
- `gui/`: GTK4-based user interface.
- `services/`: Background daemons and automation logic.
- `utils/`: Common helper functions and logging.
- `widgets/`: Reusable UI components.

## Universal Design
The core logic is designed to be distribution-agnostic. It interacts directly with `/sys/fs` and `/sys/bus` where possible to ensure compatibility across Ubuntu, Fedora, and other Linux flavors.
