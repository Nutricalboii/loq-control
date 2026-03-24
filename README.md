# 🛰️ LOQ Control Center v1.2.0

> **A Secure, High-Performance Persistence Layer for Lenovo LOQ Hardware on Linux.**

---

### 🔱 **The Unharming Blueprint**
LOQ Control Center is designed by **Vaibhav Pandit** as a non-destructive, "Safe Elevation" blueprint for hardware management. It replaces high-risk terminal commands with a secure, Polkit-gated enterprise architecture that prioritizes system longevity and user safety.

---

### ⚡ **Core Capabilities**

*   **🛡️ Multi-Point Security**: Zero-sudo GUI architecture using `pkexec` for granular privilege escalation.
*   **🧠 Thermal Intelligence**: An adaptive "Brain" (Policy Engine) that automatically escalates cooling before heat-soak occurs.
*   **🎨 Dynamic Aesthetics**: A modern GTK4 interface with persistent Dark/Light/System theme synchronization.
*   **📊 Native Telemetry**: High-precision, real-time Cairo-rendered performance graphs for CPU, GPU, and Power Draw.
*   **🔋 Battery Intelligence**: Advanced MUX switching logic (Hybrid/Integrated/NVIDIA) and conservation mode persistence.

---

### 🛠️ **Terminal Installation (The Fast Way)**

Experience the blueprint in seconds. Copy and paste these commands into your terminal:

```bash
# 1. Clone the Blueprint
git clone https://github.com/nutricalboii/loq-control.git && cd loq-control

# 2. Install Dependencies (Linux/Ubuntu/Debian)
sudo apt update && sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 python3-psutil

# 3. Deploy the Environment
pip3 install -e .

# 4. Launch the Dashboard
loq-gui
```

---

### 🧬 **Architecture of Persistence**

LOQ Control is separated into three distinct high-integrity layers:
1.  **`loq-daemon`**: The low-level background observer (Persistence).
2.  **`loq-gui`**: The high-fidelity GTK4 Dashboard (Control).
3.  **`loq-control`**: The direct-access CLI for hardware probing (Discovery).

---

### 🏷️ **Developer & Credits**

**Architected & Developed by:**  
👤 **Vaibhav Pandit** (nutricalboii)  

*“This project is more than a tool—it is a secure blueprint for how hardware and software should interact on Linux.”*

---

*Verified on Lenovo LOQ 2023/2024 Platforms.*  
*Status: Production Ready | v1.2.0*
