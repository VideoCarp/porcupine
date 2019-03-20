import teek

from porcupine import actions, get_main_window


def on_var_changed(var):
    # TODO: add 'wm attributes' to teek
    teek.tcl_call(None, 'wm', 'attributes', get_main_window().toplevel,
                  '-fullscreen', var.get())


def setup():
    action = actions.add_yesno("View/Full Screen", False, '<F11>')
    action.var.write_trace.connect(on_var_changed)
