"""Change the look of Porcupine's GUI.

This plugin doesn't do anything to the colors used in the main editing area.
Those are handled by pygments_style and highlight plugins.
"""
import tkinter

import ttkthemes

from porcupine import get_main_window, menubar
from porcupine.settings import global_settings


# TODO: modernize this code a bit, so that it actually matches ttkthemes docs
def setup() -> None:
    style = ttkthemes.ThemedStyle()

    if get_main_window().tk.call("tk", "windowingsystem") == "x11":
        # Default theme sucks on linux
        global_settings.add_option("ttk_theme", "black")
    else:
        global_settings.add_option("ttk_theme", style.theme_use())

    var = tkinter.StringVar()

    theme_names = sorted(style.get_themes())
    theme_names.remove("breeze")  # messes with font of text widgets and causes lots of errors
    for name in theme_names:
        # TODO: capitalize theme names?
        menubar.get_menu("UI Themes").add_radiobutton(label=name, value=name, variable=var)

    # Connect style and var
    var.trace_add("write", lambda *junk: style.set_theme(var.get()))

    # Connect var and settings
    get_main_window().bind(
        "<<GlobalSettingChanged:ttk_theme>>",
        lambda event: var.set(global_settings.get("ttk_theme", str)),
        add=True,
    )
    var.set(global_settings.get("ttk_theme", str))
    var.trace_add("write", lambda *junk: global_settings.set("ttk_theme", var.get()))
