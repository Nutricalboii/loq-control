# 🚀 LOQ Control Center

**Version:** v0.5 (Engineering Build)  
**Developed by:** Vaibhav Sharma  
**GitHub:** https://github.com/nutricalboii/loq-control  

A modern hardware control suite for **Lenovo LOQ laptops on Linux**.

This project aims to provide a **Lenovo Vantage-like experience on Ubuntu / Linux** —  
with real hardware control, performance tuning, and system transparency.

---

## ✨ Overview

LOQ Control Center is an **open-source Linux hardware management application** designed specifically for Lenovo LOQ gaming laptops.

It provides:

- GPU mode switching  
- Power profile control  
- Thermal monitoring  
- Performance presets  
- Background automation  
- System performance visualization  

The goal is to build a **fully featured Linux control ecosystem** for gaming laptops.

---

## 🧠 Core Features

### 🎮 GPU Control
- Integrated Mode (Intel iGPU only)
- Hybrid Mode (Dynamic switching)
- NVIDIA Mode (Discrete GPU performance)
- Automatic GPU switching based on charger state
- NVIDIA usage detection

### ⚡ Power & Performance
- Battery Saver profile
- Balanced profile
- Performance profile
- Platform profile control (low-power / balanced / performance / custom)
- Performance preset engine (gaming / battery / overclock)

### 🌡 Thermal & Hardware Monitoring
- Real-time CPU usage monitoring
- RAM usage tracking
- CPU temperature monitoring
- SSD temperature monitoring
- Battery power draw estimation
- Live performance graphs

### 🔋 Battery Management
- Battery conservation mode (charge limit support)
- Power usage optimization
- Future EC-level battery tuning support

### 🌀 Background Services
- Auto GPU switching daemon
- Hardware monitoring backend
- Future system tray integration

---

## 🧱 Architecture

loq_control/
│
├── core/
│   ├── gpu.py
│   ├── power.py
│   ├── thermals.py
│   ├── monitor.py
│   ├── battery.py
│   ├── fan.py
│   ├── presets.py
│
├── services/
│   ├── auto_gpu.py
│   ├── daemon.py
│
├── gui/
│   ├── main.py
│   ├── dashboard_page.py
│   ├── gpu_page.py
│   ├── power_page.py
│   ├── thermals_page.py
│   ├── graph_widget.py
│
└── assets/

This design allows:

- Easy feature expansion  
- Hardware-specific tuning modules  
- Background services integration  
- Future packaging (.deb / Flatpak)

---

## 📊 Current UI Direction

- Sidebar navigation layout (Vantage-style)
- Dark minimal performance dashboard
- Live system graphing
- Modular control pages
- Developer credit branding inside UI

---

## 🔮 Roadmap

### Phase 1 — Hardware Depth
- EC fan control (real RPM curve tuning)
- GPU power gating via PCI runtime suspend
- CPU PL1 / PL2 tuning
- Undervolting interface
- NVIDIA clock control

### Phase 2 — UI Evolution
- Glass sidebar design
- Animated performance graphs
- GPU VRAM monitoring
- Thermal color indicators
- Gaming dashboard mode

### Phase 3 — System Integration
- System tray control
- Auto-start daemon installer
- PolicyKit privilege management
- Firmware / driver updater
- .deb and Flatpak packaging

### Phase 4 — LOQ Exclusive Features
- Fn+Q performance mode sync
- RGB keyboard control API
- Charger wattage detection
- MUX switch detection
- BIOS thermal profile sync

---

## ⚙ Installation (Development)

Clone repository:
git clone https://github.com/nutricalboii/loq-control.git⁠� cd loq-control

Install dependencies:
sudo apt install python3-gi python3-psutil lm-sensors pip install matplotlib

Run:
python3 -m loq_control.gui.main

---

## 🛡 Permissions

Some hardware controls require:

- sudo access  
- ACPI platform profile support  
- NVIDIA PRIME drivers  

---

## 🤝 Contributing

This project is **open source and actively evolving.**

Contributions welcome for:

- Hardware reverse engineering  
- UI design improvements  
- Thermal control tuning  
- Packaging and deployment  

---

## 📜 License

MIT License

---

## ⭐ Author

**Vaibhav Sharma**  
Linux enthusiast • System tinkerer • Performance engineer
