"""Generic Tkinter widget-name driver shared across all 4 mirror apps.

All mirror apps give their interactive widgets a stable Tkinter `name=`
(see each app's BUILD_NOTES.md). This module drives them the same way an
RPA tool would target named controls -- by widget name, not pixel
coordinates and not OS-level accessibility APIs (macOS accessibility
permissions are not reliably available in this dev environment; the
approach below works identically on Windows since it never leaves the
Tcl/Tk widget tree).
"""
import time


def find_named(root, name):
    """Depth-first search of the Tk widget tree (includes Toplevels, since
    a Toplevel is registered as a child of whatever widget it was created
    with) for a widget with the given Tkinter name."""
    try:
        if root.winfo_name() == name:
            return root
    except Exception:
        pass
    for child in root.winfo_children():
        found = find_named(child, name)
        if found is not None:
            return found
    return None


def require(root, name):
    w = find_named(root, name)
    if w is None:
        raise RuntimeError(f"widget not found by name: {name!r}")
    return w


def click(root, name, pump=None):
    w = require(root, name)
    w.invoke()
    _pump(root, pump)


def double_click(root, name, pump=None):
    """Tk's event_generate refuses the Double-Button-1 *pattern* directly
    ("Double, Triple, or Quadruple modifier not allowed") -- that modifier
    is only valid in bind() patterns, not as a synthesizable event. Instead,
    fire two immediate Button-1 press/release pairs, which Tk's own
    multi-click detector combines into the double-click binding, same as a
    real double-click would."""
    import tkinter as _tk
    w = require(root, name)
    if isinstance(w, _tk.Listbox) and not w.curselection():
        # Synthetic click events don't reliably drive Listbox's own
        # class-level selection binding (no real pointer position) -- select
        # explicitly first, same end state a real double-click would leave.
        w.selection_set(0)
    # Tk's own event-position defaults (x=0, y=0) fall outside an unmapped
    # widget's realized geometry and get silently ignored by some widget
    # classes (Label) even though Listbox tolerates it -- pass the widget's
    # actual center so the click lands "on" it, matching a real double-click.
    w.update_idletasks()
    x = w.winfo_width() // 2 or 5
    y = w.winfo_height() // 2 or 5
    for _ in range(2):
        try:
            w.event_generate("<ButtonPress-1>", x=x, y=y)
            w.event_generate("<ButtonRelease-1>", x=x, y=y)
            root.update()
        except _tk.TclError:
            # The double-click's own handler (e.g. screen navigation) can
            # destroy this widget mid-sequence, as a side effect of the
            # second press already being recognized as the completing click
            # -- that means the action already fired, nothing left to do.
            break
    _pump(root, pump)


DEFAULT_TYPE_DELAY = 0.02


def type_into(widget, value, root=None, pump=None, type_delay=DEFAULT_TYPE_DELAY, multiline=False):
    """Types `value` one character at a time (with a brief pump+pause after
    each keystroke) instead of inserting the whole string in one shot, so a
    human watching the demo sees the bot actually typing rather than text
    appearing all at once like a paste. `root` is what gets pumped between
    keystrokes (defaults to `widget` itself, but pass the app's Toplevel
    when `widget` is withdrawn/not a window)."""
    root = root if root is not None else widget
    if multiline:
        widget.delete("1.0", "end")
    else:
        widget.delete(0, "end")
    for ch in value:
        widget.insert("end", ch)
        _pump(root, type_delay)
    _pump(root, pump)


def set_entry(root, name, value, pump=None, type_delay=DEFAULT_TYPE_DELAY):
    w = require(root, name)
    type_into(w, value, root=root, pump=pump, type_delay=type_delay)


def set_text(root, name, value, pump=None, type_delay=DEFAULT_TYPE_DELAY):
    """For a Tk Text widget (multi-line long-text fields)."""
    w = require(root, name)
    type_into(w, value, root=root, pump=pump, type_delay=type_delay, multiline=True)


def press_return(root, name, pump=None):
    w = require(root, name)
    w.event_generate("<Return>")
    _pump(root, pump)


def get_label_text(root, name):
    return require(root, name).cget("text")


def _pump(root, pump):
    """Process pending Tk events so the GUI visibly updates as the
    automation runs, optionally pausing briefly for a watchable demo pace."""
    top = root.winfo_toplevel() if hasattr(root, "winfo_toplevel") else root
    try:
        top.update_idletasks()
        top.update()
    except Exception:
        pass
    if pump:
        time.sleep(pump)
