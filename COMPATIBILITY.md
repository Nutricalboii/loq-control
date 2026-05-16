# 🎮 LOQ Control Compatibility Matrix

## Hardware Support
| Model | Series | CPU Support | GPU Support | Fn+Q Sync | Smart Fan |
|-------|--------|-------------|-------------|-----------|-----------|
| Lenovo LOQ 15IRH8 | Intel | PL1/PL2 | NVIDIA Gating | Verified | Verified |
| Lenovo LOQ 15APH8 | AMD | P-State | NVIDIA Gating | Verified | Verified |
| Lenovo Legion 5 (Recent) | Mixed | Partial | Verified | Experimental | Experimental |

*Note: Models with `ideapad_laptop` kernel drivers are prioritized.*

---

## 🐧 OS & Distro Compatibility
LOQ Control is designed to be **Universal** across the Linux ecosystem for Lenovo LOQ hardware.

| Distribution | Status | Notes |
|--------------|--------|-------|
| **Ubuntu / Debian** | ✅ Native | Optimized for `prime-select` and `apt`. |
| **Fedora** | ✅ Supported | Requires `python3-gobject` and `gtk4`. |
| **Arch Linux** | ✅ Supported | AUR package coming soon. |
| **Pop!_OS** | ✅ Native | Full support for System76 power profiles. |

> [!TIP]
> While GPU switching defaults to `prime-select` (Ubuntu-style), the core thermal and power management features work universally on any distro with a 5.15+ kernel.

