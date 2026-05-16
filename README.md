# 🛰️ LOQ Control Center v2.0.1
**The Ultimate Hardware Control Suite for Lenovo LOQ Laptops on Linux.**

> [!NOTE]
> **The Unharming Blueprint**: LOQ Control Center is designed as a non-destructive, "Safe Elevation" blueprint for hardware management. It replaces high-risk terminal commands with a secure, Polkit-gated architecture that prioritizes system longevity and user safety.

---

## 🚀 Key Features

- **🛡️ Multi-Point Security**: Zero-sudo GUI architecture using `pkexec` for granular privilege escalation.
- **🧠 Thermal Intelligence**: An adaptive Policy Engine that automatically escalates cooling before heat-soak occurs.
- **🎮 GPU Management**: Seamlessly switch between Integrated, Hybrid, and Dedicated NVIDIA modes.
- **⚡ Performance Profiles**: Instant access to Power Saver, Balanced, and Performance modes with ACPI integration.
- **🌡️ Advanced Monitoring**: High-precision, real-time telemetry for CPU/GPU temperatures and power draw.
- **🎨 Modern UI**: A sleek GTK4 interface with persistent theme synchronization.

---

## 🛠️ System Requirements

### Hardware
- **Lenovo LOQ Series** (Universal support for all models: 15IRH8, 15APH8, etc.)
- **Lenovo Legion Series** (Partial support for recent models)

### Software & Drivers
- **OS**: Ubuntu 22.04+, Fedora 38+, or any modern Linux distribution.
- **Kernel**: 5.15 or newer (for optimal ACPI support).
- **Python**: 3.10+
- **Drivers**: NVIDIA Proprietary Drivers (required for GPU control features).

---

## 📦 Installation & Setup

### 1. Install System Dependencies

#### **Ubuntu / Debian / Pop!_OS**
```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo libgtk-4-1 nvidia-prime python3-psutil
```

#### **Fedora**
```bash
sudo dnf install python3-gobject gtk4 python3-psutil
# Note: For GPU switching on Fedora, ensuring 'envycontrol' or 'supergfxctl' is available is recommended.
```

### 2. Deploy the Environment
```bash
git clone https://github.com/nutricalboii/loq-control.git
cd loq-control
pip install -e .
```

---

## 🕹️ Usage

Once installed via `pip`, you can use the following commands from anywhere:

| Command | Description |
|---------|-------------|
| `loq-gui` | Launch the GTK4 Control Center Dashboard |
| `loq-control --probe` | Run the hardware discovery engine (CLI) |
| `loq-daemon` | Start the background automation service |
| `loq-report` | Generate a system stability and thermal report |

---

## ⌨️ Terminal Shortcut (Portable)
If you prefer not to install the package via `pip`, you can use the included wrapper:
```bash
./setup_shortcut.sh
```
This creates a `loq-control` command that points directly to the source folder.

---

## ⚙️ Background Automation
To enable automatic profile switching and hardware monitoring on boot:

1. **Install the Daemon Service**:
   ```bash
   sudo cp loq-control-daemon.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now loq-control-daemon.service
   ```

---

## ⚠️ Safety & Compatibility
> [!IMPORTANT]
> This tool interacts directly with your hardware's Embedded Controller (EC). While we implement safety "deadman switches," always monitor your thermals when applying custom power limits.

- See [SAFETY.md](./SAFETY.md) for detailed safety protocols and "Deadman Switch" logic.
- See [COMPATIBILITY.md](./COMPATIBILITY.md) for the verified hardware list.

---

## 🏷️ Developer & Credits
**Architected & Developed by:**  
👤 **Vaibhav Pandit** ([@nutricalboii](https://github.com/nutricalboii))

*“This project is more than a tool—it is a secure blueprint for how hardware and software should interact on Linux.”*

**License**: MIT | **Status**: Production Ready | v2.0.1
