import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from loq_control.version import APP_NAME, VERSION, AUTHOR, GITHUB


def show_about(parent):

    dialog = Gtk.AboutDialog()

    dialog.set_transient_for(parent)
    dialog.set_modal(True)

    dialog.set_program_name(APP_NAME)
    dialog.set_version(VERSION)
    dialog.set_comments(
        "Advanced Hardware Control Center for Lenovo LOQ laptops on Linux.\n"
        "GPU modes • Power tuning • Thermal monitoring • Automation"
    )

    dialog.set_website(GITHUB)
    dialog.set_authors([AUTHOR])

    dialog.present()
