from __future__ import annotations

import logging
import re
import sys
import tkinter
import webbrowser
from functools import partial
from pathlib import Path
from string import ascii_lowercase
from tkinter import filedialog
from typing import Any, Callable, Iterator

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from porcupine import settings, tabs, utils
from porcupine._state import filedialog_kwargs, get_main_window, get_tab_manager, quit
from porcupine.settings import global_settings

log = logging.getLogger(__name__)


# For some reason, binding <F4> on Windows also captures Alt+F4 presses.
# IMO applications shouldn't receive the window manager's special key bindings.
# Windows is weird...
def event_is_windows_alt_f4(event: tkinter.Event[tkinter.Misc]) -> bool:
    return (
        sys.platform == "win32"
        and isinstance(event.state, int)
        and bool(event.state & 0x20000)  # Alt key is pressed
        and event.keysym == "F4"
    )


# Try this:
#
#    import tkinter
#
#    def handler(event):
#        print("got event")
#        return 'break'
#
#    root = tkinter.Tk()
#    root.event_add('<<Foo>>', '<Control-w>')
#    root.bind('<<Foo>>', handler)
#    root.bind_class('Text', '<<Foo>>', handler)
#    text = tkinter.Text()
#    text.pack()
#    root.mainloop()
#
# Now type something, select some text in the text widget and press
# Control-w. The text gets deleted (stupid default binding) and "got event"
# gets printed (the event handler). But if you put
#
#    text.bind('<<Foo>>', handler)
#
# before root.mainloop(), then it works, so that has to be done for every
# text widget.
def _generate_event(name: str, event: tkinter.Event[tkinter.Misc]) -> Literal["break"]:
    if event_is_windows_alt_f4(event):
        quit()
    else:
        log.debug(f"Generating event: {name}")
        get_main_window().event_generate(name)
    return "break"


def _fix_text_widget_bindings(event: tkinter.Event[tkinter.Misc]) -> None:
    for virtual_event in event.widget.event_info():
        if virtual_event.startswith("<<Menubar:") and not event.widget.bind(virtual_event):
            # When the keys are pressed, generate the event on the main
            # window so the menu callback will trigger.
            event.widget.bind(virtual_event, partial(_generate_event, virtual_event), add=True)
            assert event.widget.bind(virtual_event)


def _init() -> None:
    log.debug("_init() starts")
    main_window = get_main_window()
    main_window.config(menu=tkinter.Menu(main_window, tearoff=False))
    main_window.bind("<<PluginsLoaded>>", (lambda event: update_keyboard_shortcuts()), add=True)
    main_window.bind_class("Text", "<FocusIn>", _fix_text_widget_bindings, add=True)
    _fill_menus_with_default_stuff()
    log.debug("_init() done")


_MENU_ITEM_TYPES_WITH_LABEL = {"command", "checkbutton", "radiobutton", "cascade"}


def _find_item(menu: tkinter.Menu, label: str) -> int | None:
    last_index = menu.index("end")
    if last_index is not None:  # menu not empty
        for index in range(last_index + 1):
            if (
                menu.type(index) in _MENU_ITEM_TYPES_WITH_LABEL
                and menu.entrycget(index, "label") == label
            ):
                return index
    return None


# "//" means literal backslash, lol
def _join(parts: list[str]) -> str:
    return "/".join(part.replace("/", "//") for part in parts)


def _split(string: str) -> list[str]:
    if not string:
        return []
    return [part.replace("//", "/") for part in re.split(r"(?<!/)/(?!/)", string)]


def _split_parent(string: str) -> tuple[str, str]:
    *parent_parts, child = _split(string)
    return (_join(parent_parts), child)


def get_menu(path: str) -> tkinter.Menu:
    """
    Find a menu widget, creating menus as necessary.

    For example, ``get_menu("Tools/Python")`` returns a submenu labelled
    *Python* from a menu named *Tools*. The *Tools* menu is created if it
    doesn't already exist.

    If *path* is the empty string, then the menubar itself is returned.
    """

    main_window = get_main_window()
    main_menu: tkinter.Menu = main_window.nametowidget(main_window["menu"])

    menu = main_menu
    for label in _split(path):
        submenu_index = _find_item(menu, label)
        if submenu_index is None:
            # Need to pass the menu as an explicit argument to tkinter.Menu.
            # Otherwise add_cascade() below tries to allocate a crazy amount of
            # memory and freezes everything when running tests (don't know why)
            submenu = tkinter.Menu(menu, tearoff=False)
            if menu == main_menu and menu.index("end") is not None:
                # adding something to non-empty main menu, don't add all the
                # way to end so that "Help" menu stays at very end
                last_index = menu.index("end")
                assert last_index is not None
                menu.insert_cascade(last_index, label=label, menu=submenu)
            else:
                menu.add_cascade(label=label, menu=submenu)
            menu = submenu

        else:
            menu = menu.nametowidget(menu.entrycget(submenu_index, "menu"))

    return menu


def add_config_file_button(path: Path, *, menu: str = "Settings/Config Files") -> None:
    """
    Add a button to *Settings/Config Files* (or some other menu)
    that opens a file in Porcupine when it's clicked.
    """
    get_menu(menu).add_command(
        label=f"Edit {path.name}", command=(lambda: get_tab_manager().open_file(path))
    )


def _walk_menu_contents(
    menu: tkinter.Menu, path_prefix: list[str] = []
) -> Iterator[tuple[str, tkinter.Menu, int]]:

    last_index = menu.index("end")
    if last_index is not None:  # menu not empty
        for index in range(last_index + 1):
            if menu.type(index) == "cascade":
                submenu: tkinter.Menu = menu.nametowidget(menu.entrycget(index, "menu"))
                new_prefix = path_prefix + [menu.entrycget(index, "label")]
                yield from _walk_menu_contents(submenu, new_prefix)
            elif menu.type(index) in _MENU_ITEM_TYPES_WITH_LABEL:
                path = path_prefix + [menu.entrycget(index, "label")]
                yield (_join(path), menu, index)


def _menu_event_handler(menu: tkinter.Menu, index: int, event: tkinter.Event[tkinter.Misc]) -> str:
    if event_is_windows_alt_f4(event):
        quit()
    else:
        menu.invoke(index)
    return "break"


def _update_keyboard_shortcuts_inside_submenus() -> None:
    main_window = get_main_window()
    for path, menu, index in _walk_menu_contents(get_menu("")):
        if menu.entrycget(index, "accelerator"):
            # Already done, or menu item uses some custom stuff e.g. run plugin
            continue

        event_name = f"<<Menubar:{path}>>"

        # show keyboard shortcuts in menus
        menu.entryconfig(index, accelerator=utils.get_binding(event_name, menu=True))

        # trigger menu items when <<Menubar:Foo/Bar>> events are generated
        if not main_window.bind(event_name):
            # FIXME: what if menu item is inserted somewhere else than to end, and indexes change?
            command = partial(_menu_event_handler, menu, index)
            main_window.bind(event_name, command, add=True)


# Make sure that alt+e opens edit menu
def _update_shortcuts_for_opening_submenus() -> None:
    used_letters = set()
    for virtual_event in get_main_window().event_info():
        for physical_event in get_main_window().event_info(virtual_event):
            match = re.fullmatch(r"<Alt-Key-([a-z])>", physical_event)
            if match is not None:
                used_letters.add(match.group(1))

    menu = get_menu("")
    last_index = menu.index("end")
    assert last_index is not None
    for submenu_index in range(last_index + 1):
        for letter_index, letter in enumerate(menu.entrycget(submenu_index, "label").lower()):
            if letter in ascii_lowercase and letter not in used_letters:
                menu.entryconfig(submenu_index, underline=letter_index)
                used_letters.add(letter)
                break
        else:
            menu.entryconfig(submenu_index, accelerator="")


def update_keyboard_shortcuts() -> None:
    """
    This function does several different things to each menu item. Here's what
    it does to the *Edit* menu and the *Find and Replace* menu item inside it:

        * Show *Ctrl+F* (or *⌘F* on Mac) next to *Find and Replace*.
        * Ensure that the menu item's callback runs when Ctrl+F (or Command+F) is pressed.
        * Allow the *Edit* menu to be accessed by pressing Alt+E.

    This has to be called when menus or keyboard shortcuts have been modified.
    It's called automatically when a plugin has been set up.
    """
    _update_keyboard_shortcuts_inside_submenus()
    _update_shortcuts_for_opening_submenus()


def set_enabled_based_on_tab(
    path: str, callback: Callable[[tabs.Tab | None], bool]
) -> Callable[..., None]:
    """Use this for disabling menu items depending on the currently selected tab.

    When the selected :class:`~porcupine.tabs.Tab` changes, ``callback`` will
    be called with the selected tab as an argument, or ``None`` if there are
    no tabs. If the callback returns ``False``, then the menu item given by
    *path* is disabled (so that it looks grayed out and can't be clicked).

    The *path* works similarly to :func:`get_menu`, except that it refers to a
    menu item rather than a submenu. For example, ``"Tools/Python/Black"``
    means a menu item labelled *Black* in the *Tools/Python* menu.

    For example, this creates a menu item ``Foo/Bar`` and disables it whenever
    the currently selected tab is not a :class:`porcupine.tabs.FileTab`::

        from porcupine import menubar, tabs

        def do_something():
            ...

        def setup():
            menubar.get_menu("Foo").add_command(label="Bar", command=do_something)
            menubar.set_enabled_based_on_tab("Foo/Bar", (lambda tab: isinstance(tab, tabs.FileTab)))

    Sometimes you need to update the enabled-ness of a menu item for other
    reasons than changing the currently selected tab. To do that, call the
    callback that this function returns. It's always called when the selected
    tab changes, but you can call it at other times too. The returned callback
    ignores all arguments given to it, which makes using it with ``.bind()``
    easier.
    """

    def update_enabledness(*junk: object) -> None:
        tab = get_tab_manager().select()
        parent, child = _split_parent(path)
        menu = get_menu(parent)
        index = _find_item(menu, child)
        if index is None:
            raise LookupError(f"menu item {path!r} not found")
        menu.entryconfig(index, state=("normal" if callback(tab) else "disabled"))

    update_enabledness()
    get_tab_manager().bind("<<NotebookTabChanged>>", update_enabledness, add=True)
    return update_enabledness


def _get_filetab() -> tabs.FileTab:
    tab = get_tab_manager().select()
    assert isinstance(tab, tabs.FileTab)
    return tab


def add_filetab_command(
    path: str, func: Callable[[tabs.FileTab], object] | None = None, **kwargs: Any
) -> None:
    """
    This is a convenience function that does several things:

    * Create a menu item at the given path.
    * Ensure the menu item is enabled only when the selected tab is a
      :class:`~porcupine.tabs.FileTab`.
    * Do something when the menu item is clicked. See below.

    If ``func`` is given, it is called with the selected tab as the only
    argument when the menu item is clicked. For example::

        from procupine import menubar, tabs

        def do_something(tab: tabs.FileTab) -> None:
            ...

        def setup() -> None:
            menubar.add_filetab_command("Edit/Do something", do_something)

    If ``func`` is not given, then an event is generated to the tab. The event
    is named so that if ``path`` is ``"Edit/Foo"``, then the event is
    ``<<FiletabCommand:Edit/Foo>>``. This is useful, for example, if you want
    to create an instance of a class for every new tab, and then call a method
    of the instance when a menu item is clicked. For example::

        from __future__ import annotations
        import tkinter
        from procupine import get_tab_manager, menubar, tabs

        class FooBar:
            def do_something(self, event: tkinter.Event[tabs.FileTab]) -> None:
                ...

        def on_new_filetab(tab: tabs.FileTab) -> None:
            foobar = FooBar()
            tab.bind("<<FiletabCommand:Edit/Do something>>", foobar.do_something, add=True)

        def setup() -> None:
            get_tab_manager().add_filetab_callback(on_new_filetab)
            menubar.add_filetab_command("Edit/Do something")

    You usually don't need to provide any keyword arguments in ``**kwargs``,
    but if you do, they are passed to :meth:`tkinter.Menu.add_command`.
    """
    if func is None:
        command = lambda: _get_filetab().event_generate(f"<<FiletabCommand:{path}>>")
    else:
        command = lambda: func(_get_filetab())  # type: ignore

    menu_path, item_text = _split_parent(path)
    get_menu(menu_path).add_command(label=item_text, command=command, **kwargs)
    set_enabled_based_on_tab(path, (lambda tab: isinstance(tab, tabs.FileTab)))


# TODO: pluginify?
def _fill_menus_with_default_stuff() -> None:
    # Make sure to get the order of menus right:
    #   File, Edit, <everything else>, Help
    get_menu("Help")  # handled specially in get_menu
    get_menu("File")
    get_menu("Edit")

    def new_file() -> None:
        get_tab_manager().add_tab(tabs.FileTab(get_tab_manager()))

    def open_files() -> None:
        # paths is "" or tuple
        paths = filedialog.askopenfilenames(**filedialog_kwargs)
        for path in map(Path, paths):
            get_tab_manager().open_file(path)

    def save_file(save_as: bool) -> None:
        tab = get_tab_manager().select()
        assert isinstance(tab, tabs.FileTab)
        if save_as:
            tab.save_as()
        else:
            tab.save()

    def close_selected_tab() -> None:
        tab = get_tab_manager().select()
        assert tab is not None
        if tab.can_be_closed():
            get_tab_manager().close_tab(tab)

    get_menu("File").add_command(label="New File", command=new_file)
    get_menu("File").add_command(label="Open", command=open_files)
    get_menu("File").add_command(label="Save", command=partial(save_file, False))
    get_menu("File").add_command(label="Save As", command=partial(save_file, True))
    get_menu("File").add_separator()
    get_menu("File").add_command(label="Close", command=close_selected_tab)
    get_menu("File").add_command(label="Quit", command=quit)

    set_enabled_based_on_tab("File/Save", (lambda tab: isinstance(tab, tabs.FileTab)))
    set_enabled_based_on_tab("File/Save As", (lambda tab: isinstance(tab, tabs.FileTab)))
    set_enabled_based_on_tab("File/Close", (lambda tab: tab is not None))
    set_enabled_based_on_tab("File/Quit", (lambda tab: tab is None))

    def change_font_size(how: Literal["bigger", "smaller", "reset"]) -> None:
        if how == "reset":
            global_settings.reset("font_size")
            return

        size = global_settings.get("font_size", int)
        if how == "bigger":
            size += 1
        else:
            size -= 1
            if size < 3:
                return

        global_settings.set("font_size", size)

    get_menu("View").add_command(label="Bigger Font", command=partial(change_font_size, "bigger"))
    get_menu("View").add_command(label="Smaller Font", command=partial(change_font_size, "smaller"))
    get_menu("View").add_command(
        label="Reset Font Size", command=partial(change_font_size, "reset")
    )
    set_enabled_based_on_tab("View/Bigger Font", (lambda tab: tab is not None))
    set_enabled_based_on_tab("View/Smaller Font", (lambda tab: tab is not None))
    set_enabled_based_on_tab("View/Reset Font Size", (lambda tab: tab is not None))

    get_menu("Settings").add_command(label="Porcupine Settings", command=settings.show_dialog)

    def add_link(menu_path: str, label: str, url: str) -> None:
        get_menu(menu_path).add_command(label=label, command=(lambda: webbrowser.open(url)))

    # TODO: porcupine starring button
    add_link("Help", "Porcupine Wiki", "https://github.com/Akuli/porcupine/wiki")
    add_link(
        "Help",
        "Report a problem or request a feature",
        "https://github.com/Akuli/porcupine/issues/new",
    )
    add_link(
        "Help/Python",
        "Free help chat",
        "https://kiwiirc.com/nextclient/irc.libera.chat/##learnpython",
    )
    add_link(
        "Help/Python",
        "My Python tutorial",
        "https://github.com/Akuli/python-tutorial/blob/master/README.md",
    )
    add_link("Help/Python", "Official documentation", "https://docs.python.org/")
