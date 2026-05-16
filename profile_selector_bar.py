import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk
from loq_control.core.profile_cycle_manager import ProfileCycleManager, PROFILE_CYCLE_ORDER


PROFILE_META = {
    "quiet": {
        "label": "Quiet",
        "sub": "Silent, low power",
        "led_color": "#4A9EF5",
        "led_glow": "rgba(74, 158, 245, 0.35)",
        "icon": "🔵",
        "css_class": "profile-btn-blue",
    },
    "balanced": {
        "label": "Balanced",
        "sub": "Auto / Default",
        "led_color": "#E8E8E8",
        "led_glow": "rgba(232, 232, 232, 0.25)",
        "icon": "⚪",
        "css_class": "profile-btn-white",
    },
    "performance": {
        "label": "Performance",
        "sub": "Max power, AC needed",
        "led_color": "#F54A4A",
        "led_glow": "rgba(245, 74, 74, 0.35)",
        "icon": "🔴",
        "css_class": "profile-btn-red",
    },
    "custom": {
        "label": "Custom",
        "sub": "Your tuned settings",
        "led_color": "#A855F7",
        "led_glow": "rgba(168, 85, 247, 0.4)",
        "icon": "🟣",
        "css_class": "profile-btn-purple",
    },
}

PROFILE_SELECTOR_CSS = """
.profile-selector-bar {
    background: alpha(currentColor, 0.04);
    border-radius: 12px;
    padding: 8px;
}

.profile-btn {
    border-radius: 10px;
    padding: 10px 16px;
    min-width: 90px;
    transition: all 200ms ease;
}

.profile-btn-blue:checked,
.profile-btn-blue.active {
    background: rgba(74, 158, 245, 0.18);
    border: 2px solid rgba(74, 158, 245, 0.7);
    color: #4A9EF5;
}

.profile-btn-white:checked,
.profile-btn-white.active {
    background: rgba(232, 232, 232, 0.12);
    border: 2px solid rgba(232, 232, 232, 0.6);
    color: #E8E8E8;
}

.profile-btn-red:checked,
.profile-btn-red.active {
    background: rgba(245, 74, 74, 0.18);
    border: 2px solid rgba(245, 74, 74, 0.7);
    color: #F54A4A;
}

.profile-btn-purple:checked,
.profile-btn-purple.active {
    background: rgba(168, 85, 247, 0.2);
    border: 2px solid rgba(168, 85, 247, 0.8);
    color: #A855F7;
}

.profile-led-dot {
    border-radius: 50%;
    min-width: 10px;
    min-height: 10px;
}

.profile-shortcut-label {
    font-size: 9px;
    opacity: 0.5;
}

.profile-sub-label {
    font-size: 10px;
    opacity: 0.65;
}
"""


class ProfileButton(Gtk.ToggleButton):

    def __init__(self, profile_key: str, group=None):
        super().__init__()
        self.profile_key = profile_key
        meta = PROFILE_META[profile_key]

        if group:
            self.set_group(group)

        self.add_css_class("profile-btn")
        self.add_css_class(meta["css_class"])

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_halign(Gtk.Align.CENTER)

        icon_lbl = Gtk.Label(label=meta["icon"])
        icon_lbl.set_halign(Gtk.Align.CENTER)

        name_lbl = Gtk.Label(label=meta["label"])
        name_lbl.set_halign(Gtk.Align.CENTER)

        sub_lbl = Gtk.Label(label=meta["sub"])
        sub_lbl.set_halign(Gtk.Align.CENTER)
        sub_lbl.add_css_class("profile-sub-label")

        box.append(icon_lbl)
        box.append(name_lbl)
        box.append(sub_lbl)

        self.set_child(box)


class ProfileSelectorBar(Gtk.Box):

    def __init__(self, cycle_manager: ProfileCycleManager, on_custom_open=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._cycle_manager = cycle_manager
        self._on_custom_open = on_custom_open
        self._buttons = {}
        self._suppress_signals = False

        self._load_css()
        self._build()
        self._sync_active(self._cycle_manager.current_profile)

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(PROFILE_SELECTOR_CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build(self):
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Performance Profile")
        title.set_halign(Gtk.Align.START)

        shortcut = Gtk.Label(label="Fn+Q to cycle")
        shortcut.set_halign(Gtk.Align.END)
        shortcut.set_hexpand(True)
        shortcut.add_css_class("profile-shortcut-label")

        title_row.append(title)
        title_row.append(shortcut)
        self.append(title_row)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.add_css_class("profile-selector-bar")
        btn_row.set_halign(Gtk.Align.CENTER)

        group_btn = None
        for profile in PROFILE_CYCLE_ORDER:
            btn = ProfileButton(profile, group=group_btn)
            if group_btn is None:
                group_btn = btn
            btn.connect("toggled", self._on_button_toggled)
            self._buttons[profile] = btn
            btn_row.append(btn)

        self.append(btn_row)

        self._status_label = Gtk.Label(label="")
        self._status_label.set_halign(Gtk.Align.CENTER)
        self._status_label.add_css_class("dim-label")
        self.append(self._status_label)

    def _on_button_toggled(self, btn):
        if self._suppress_signals:
            return
        if not btn.get_active():
            return

        profile = btn.profile_key
        self._cycle_manager.switch_to(profile)
        self._update_status(profile)

        if profile == "custom" and self._on_custom_open:
            self._on_custom_open()

    def _sync_active(self, profile: str):
        self._suppress_signals = True
        for key, btn in self._buttons.items():
            btn.set_active(key == profile)
        self._suppress_signals = False
        self._update_status(profile)

    def _update_status(self, profile: str):
        meta = PROFILE_META[profile]
        ac = self._check_ac()
        if profile == "custom" and not ac:
            self._status_label.set_text("Custom mode requires AC — reverted to Balanced")
            self._sync_active("balanced")
        else:
            self._status_label.set_text(
                f"{meta['icon']} {meta['label']} active  ·  LED: {meta['led_color']}"
            )

    def _check_ac(self):
        try:
            with open("/sys/class/power_supply/AC/online") as f:
                return f.read().strip() == "1"
        except Exception:
            return True

    def notify_profile_changed(self, profile: str):
        self._sync_active(profile)

    def get_current_profile(self):
        return self._cycle_manager.current_profile
