Open-source hardware control suite for Lenovo LOQ laptops running Linux.

This project provides a unified control center for GPU modes, performance profiles,
thermal monitoring and system automation — similar to Lenovo Vantage on Windows.

Why this project exists

Modern performance laptops expose powerful hardware controls such as hybrid GPUs,
platform performance modes and intelligent battery behaviour.

On Linux these controls exist — but they are scattered across terminal utilities.

LOQ Control Center brings them together into a single clean interface.

Current Features

GPU Control
• Integrated GPU mode
• Hybrid (on-demand) mode
• Dedicated NVIDIA mode
• Automatic GPU switching based on charger state

Performance Modes
• Power Saver
• Balanced
• Performance
• Platform ACPI profile integration

Monitoring
• CPU usage
• RAM usage
• Temperature telemetry
• Battery power draw estimation
• Live performance graph

Architecture

The project follows a modular structure:

core → hardware control logic  
services → background automation  
gui → user interface  

This separation allows future deep hardware features without breaking UI.

Roadmap

• Fan curve control  
• GPU power gating  
• CPU power limit tuning  
• RGB keyboard control  
• system tray daemon 
• packaging (.deb / Flatpak)

Author

Vaibhav Sharma 
GitHub: nutricalboii
