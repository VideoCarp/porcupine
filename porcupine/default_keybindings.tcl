# This file contains Tcl code that is executed when Porcupine starts.

# Use Command on mac, Control on other systems
if {[tk windowingsystem] == "aqua"} {
    set contmand Command
    event add "<<RightClick>>" <Button-2>
    event add "<<RightClick>>" <Control-Button-1>
    event add "<<WheelClick>>" <Button-3>
} else {
    set contmand Control
    event add "<<RightClick>>" <Button-3>
    event add "<<WheelClick>>" <Button-2>
    if {[tk windowingsystem] == "win32"} {
        event add "<<MenuKey>>" <App>
    } elseif {[tk windowingsystem] == "x11"} {
        event add "<<MenuKey>>" <Menu>
    }
}

event add "<<Menubar:File/New File>>" <$contmand-n>
event add "<<Menubar:File/Open>>" <$contmand-o>
event add "<<Menubar:File/Save>>" <$contmand-s>
event add "<<Menubar:File/Save As>>" <$contmand-S>   ;# uppercase S means you need to hold down shift
event add "<<Menubar:File/Close>>" <$contmand-w>
event add "<<Menubar:File/Quit>>" <$contmand-q>
event add "<<Menubar:View/Bigger Font>>" <$contmand-plus>
event add "<<Menubar:View/Smaller Font>>" <$contmand-minus>
event add "<<Menubar:View/Reset Font Size>>" <$contmand-0>

# run plugin
event add "<<Menubar:Run/Show//hide output>>" <F4>
event add "<<Menubar:Run/Kill process>>" <Shift-F4>
# Many separate events because if you bind many keys to the same virtual
# event, it is hard to figure out what key was pressed to trigger it
event add "<<Run:AskAndRun0>>" <Shift-F5>
event add "<<Run:AskAndRun1>>" <Shift-F6>
event add "<<Run:AskAndRun2>>" <Shift-F7>
event add "<<Run:AskAndRun3>>" <Shift-F8>
event add "<<Run:Repeat0>>" <F5>
event add "<<Run:Repeat1>>" <F6>
event add "<<Run:Repeat2>>" <F7>
event add "<<Run:Repeat3>>" <F8>

# gotoline plugin
event add "<<Menubar:Edit/Go to Line>>" <$contmand-l>

# google search plugin
event add "<<Menubar:Tools/Search selected text on Google>>" <$contmand-g>

# fullscreen plugin
event add "<<Menubar:View/Full Screen>>" <F11>

# find plugin
event add "<<Menubar:Edit/Find and Replace>>" <$contmand-f>

# fold plugin
event add "<<Menubar:Edit/Fold>>" <Alt-f>

# anchor plugin
event add "<<Menubar:Edit/Anchors/Add or remove on this line>>" <Alt-A>
event add "<<Menubar:Edit/Anchors/Jump to previous>>" <Alt-Shift-Up>
event add "<<Menubar:Edit/Anchors/Jump to next>>" <Alt-Shift-Down>
event add "<<Menubar:Edit/Anchors/Clear>>" <Alt-C>
event add "<<Menubar:Edit/Anchors/Add to error//warning lines>>" <Alt-E>

# tab_order plugin
# Prior = Page Up, Next = Page Down
event add "<<TabOrder:SelectLeft>>" <$contmand-Prior>
event add "<<TabOrder:SelectRight>>" <$contmand-Next>
event add "<<TabOrder:MoveLeft>>" <$contmand-Shift-Prior>
event add "<<TabOrder:MoveRight>>" <$contmand-Shift-Next>
for {set i 1} {$i <= 9} {incr i} {
    # e.g. Alt+2 to select second tab
    event add "<<TabOrder:SelectTab$i>>" <Alt-Key-$i>
}

# tab_closing plugin
event add "<<TabClosing:XButtonClickClose>>" <Button-1>

# sort plugin
event add "<<Menubar:Edit/Sort Lines>>" <Alt-s>

# poppingtabs plugin
event add "<<Menubar:View/Pop Tab>>" <$contmand-P>

# directory tree plugin (don't use <Alt-t>, see #425)
event add "<<Menubar:View/Focus directory tree>>" <Alt-T>

# filemanager plugin
event add "<<FileManager:Rename>>" <F2>
event add "<<FileManager:Trash>>" <Delete>
event add "<<FileManager:Delete>>" <Shift-Delete>
event add "<<FileManager:New file>>" <$contmand-n>

# jump_to_definition plugin (used by langserver and urls)
# cursor moves between button press and release, don't bind to press
event add "<<Menubar:Edit/Jump to definition>>" <$contmand-Return>
event add "<<Menubar:Edit/Jump to definition>>" <$contmand-ButtonRelease-1>

# more_plugins/terminal.py
# upper-case T means Ctrl+Shift+T or Command+Shift+T
# I use non-shifted ctrl+t for swapping two characters before cursor while editing
event add "<<Menubar:Tools/Terminal>>" <$contmand-T>

# more_plugins/pythonprompt.py
event add "<<Menubar:Run/Interactive Python prompt>>" <$contmand-i>
event add "<<PythonPrompt:KeyboardInterrupt>>" <$contmand-c>
event add "<<PythonPrompt:Copy>>" <$contmand-C>
# FIXME: conflicts with gotoline plugin
#event add "<<PythonPrompt:Clear>>" <$contmand-l>
event add "<<PythonPrompt:Clear>>" <$contmand-L>
event add "<<PythonPrompt:SendEOF>>" <$contmand-d> <$contmand-D>


# Text widgets have confusing control-click behaviour by default. Disabling it
# here makes control-click same as just click.
bind Text <$contmand-Button-1> {}

# Also, by default, Control+Slash selects all and Control+A goes to beginning.
event delete "<<LineStart>>" <$contmand-a>
event add "<<SelectAll>>" <$contmand-a>

# Ctrl+A for treeviews
bind Treeview <$contmand-a> {
    if {[%W cget -selectmode] == "extended"} {
        # The treeview supports selecting multiple items
        %W selection set [%W children {}]
    }
}

# Don't select all the way to end (issue #382)
bind Text <<SelectAll>> {
    %W tag remove sel 1.0 end
    %W tag add sel 1.0 {end - 1 char}
}

bind Text <$contmand-Delete> {
    try {%W delete sel.first sel.last} on error {} {
        set start [%W index insert]
        event generate %W <<NextWord>>
        %W delete $start insert
    }
}

bind Text <BackSpace> {
    try {%W delete sel.first sel.last} on error {} {
        set beforecursor [%W get {insert linestart} insert]
        if {[bind %W <<Dedent>>] != "" && $beforecursor != "" && [string is space $beforecursor]} {
            event generate %W <<Dedent>>
        } else {
            %W delete {insert - 1 char} insert
        }
    }
}

bind Text <$contmand-BackSpace> {
    try {%W delete sel.first sel.last} on error {} {
        set end [%W index insert]
        event generate %W <<PrevWord>>
        %W delete insert $end
    }
}

bind Text <Shift-$contmand-Delete> {
    try {%W delete sel.first sel.last} on error {} {
        if {[%W index insert] == [%W index {insert lineend}]} {
            %W delete insert
        } else {
            %W delete insert {insert lineend}
        }
    }
}

bind Text <Shift-$contmand-BackSpace> {
    try {%W delete sel.first sel.last} on error {} {
        if {[%W index insert] == [%W index {insert linestart}]} {
            %W delete {insert - 1 char} insert
        } else {
            %W delete {insert linestart} insert
        }
    }
}

# When pasting, delete what was selected. Here + adds to end of existing binding.
bind Text <<Paste>> {+
    catch {%W delete sel.first sel.last}
}

# Alt and arrow keys to scroll
set scroll_amount 2
bind Text <Alt-Up> {
    %W yview scroll -$scroll_amount units
    %W mark set insert @0,[expr [winfo height %W] / 2]
}
bind Text <Alt-Down> {
    %W yview scroll $scroll_amount units
    %W mark set insert @0,[expr [winfo height %W] / 2]
}

# Do not do weird stuff when selecting text with shift+click. See #429
bind Text <Shift-Button-1> {
    if {[%W tag ranges sel] == ""} {
        set select_between_clicked_and_this [%W index insert]
    } else {
        # Something already selected, keep the end of selection where cursor is not
        if {[%W index insert] == [%W index sel.first]} {
            set select_between_clicked_and_this [%W index sel.last]
        } else {
            set select_between_clicked_and_this [%W index sel.first]
        }
    }

    %W mark set insert @%x,%y
    %W tag remove sel 1.0 end
    if {[%W compare insert < $select_between_clicked_and_this]} {
        %W tag add sel insert $select_between_clicked_and_this
    } else {
        %W tag add sel $select_between_clicked_and_this insert
    }
}

# https://core.tcl-lang.org/tcl/info/f1253530cd
if {[tk windowingsystem] == "win32"} {
    catch {tcl_endOfWord}
    set tcl_wordchars {\w}
    set tcl_nonwordchars {\W}
}
