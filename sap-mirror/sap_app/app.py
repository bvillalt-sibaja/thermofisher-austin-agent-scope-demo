"""SAP GUI mirror shell.

A `SAPSession` wraps either the root `tk.Tk` window or a `tk.Toplevel`
("New Window" / a second logged-on SAP session, mirroring the recording's
repeated "Select Other SAP Window" alt-tabbing between two live sessions).
All sessions share one `DemoData` instance so data created in one window
(e.g. a production order) is visible from the other.
"""

import tkinter as tk
from tkinter import ttk

from sap_app import theme, screens, icons
from sap_app.data import DemoData

SCREEN_BUILDERS = {
    "LOGIN_SELECT": screens.build_login_select,
    "LOGIN_SYSTEM_LIST": screens.build_login_system_list,
    "LOGIN_CREDS": screens.build_login_creds,
    "EASY_ACCESS": screens.build_easy_access,
    "STOCK_REQ": screens.build_stock_req,
    "STOCK_REQ_CHANGE": screens.build_stock_req_change,
    "STOCK_OVERVIEW": screens.build_stock_overview,
    "BATCH_CLASSIFICATION": screens.build_batch_classification,
    "DOCUMENT_VIEW": screens.build_document_view,
    "PO_CREATE": screens.build_po_create,
    "PO_CHANGE": screens.build_po_change,
    "PO_PRINT_PREVIEW": screens.build_po_print_preview,
    "MATDOC_LIST": screens.build_matdoc_list,
    "PO_DISPLAY": screens.build_po_display,
}

TCODES = {
    "MD04": ("STOCK_REQ", {"mode": "general"}),
    "CO01": ("PO_CREATE", {}),
    "CO02": ("PO_CHANGE", {}),
    "MB51": ("MATDOC_LIST", {}),
}


class SAPSession:
    """Shared behaviour for a single SAP window (root or secondary)."""

    _windows = []  # class-level registry of all open sessions, for "Other SAP Window"

    def __init__(self, win, data, current_material=None, start_screen="LOGIN_SELECT"):
        self.win = win
        self.data = data
        self.history = []
        self.ctx = {}
        self.current_material = current_material
        SAPSession._windows.append(self)
        win.protocol("WM_DELETE_WINDOW", self._on_close)

        self.win.configure(bg=theme.WINDOW_BG)
        self.win.geometry("900x640")

        self._build_titlebar()
        self._build_toolbar()
        self.content = tk.Frame(self.win, bg=theme.CONTENT_BG, name="content_area",
                                  highlightbackground=theme.GROUPBOX_BORDER, highlightthickness=1)
        self.content.pack(side="top", fill="both", expand=True, padx=1)
        self._build_statusbar()

        self.show(start_screen)

    # ---------------------------------------------------------------- chrome
    def _build_titlebar(self):
        bar = tk.Frame(self.win, bg=theme.TITLE_BG, name="title_bar")
        bar.pack(side="top", fill="x")
        tk.Label(bar, text=theme.APP_TITLE, bg=theme.TITLE_BG, fg=theme.TITLE_FG,
                  font=theme.FONT_BOLD, anchor="w").pack(side="left", padx=8, pady=3)

    def _build_toolbar(self):
        bar = tk.Frame(self.win, bg=theme.TOOLBAR_BG, name="toolbar",
                         highlightbackground=theme.GROUPBOX_BORDER, highlightthickness=1)
        bar.pack(side="top", fill="x")
        tk.Label(bar, text="Transaction:", bg=theme.TOOLBAR_BG, font=theme.FONT_SMALL).pack(
            side="left", padx=(6, 4), pady=5)
        self.cmd_var = tk.StringVar()
        entry = tk.Entry(bar, textvariable=self.cmd_var, font=theme.FONT_NORMAL, width=18,
                           name="command_field", relief="sunken", bd=2)
        entry.pack(side="left", padx=(0, 4), pady=5)
        entry.bind("<Return>", lambda e: self._run_tcode())
        tk.Button(bar, text=" Enter", name="btn_toolbar_enter", image=icons.get("enter"),
                   compound="left", command=self._run_tcode).pack(side="left", padx=(0, 14), pady=4)

        sep = tk.Frame(bar, bg=theme.GROUPBOX_BORDER, width=1)
        sep.pack(side="left", fill="y", pady=6, padx=4)

        for label, name, icon, cmd in [
            ("Save", "btn_toolbar_save", "save", lambda: self.set_status("Saved (demo).", ok=True)),
            ("Back", "btn_toolbar_cancel", "back", self.back),
            ("Print", "btn_toolbar_print", "print", lambda: self.set_status("Print not available here.", ok=True)),
            ("New Window", "btn_new_window", None, self.open_new_window),
            ("Other SAP Window", "btn_other_window", None, self.focus_other_window),
            ("Exit", "btn_exit", "exit", self._on_close),
        ]:
            img = icons.get(icon) if icon else None
            tk.Button(bar, text=" " + label, name=name, image=img, compound="left",
                       font=theme.FONT_SMALL, command=cmd).pack(side="left", padx=3, pady=4)

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Ready")
        bar = tk.Frame(self.win, bg=theme.STATUSBAR_BG, name="status_bar")
        bar.pack(side="bottom", fill="x")
        self.status_light = tk.Canvas(bar, width=12, height=12, bg=theme.STATUSBAR_BG,
                                        highlightthickness=0, name="status_light")
        self.status_light.pack(side="left", padx=(8, 4), pady=3)
        self._status_dot = self.status_light.create_oval(1, 1, 11, 11, fill=theme.STATUS_NEUTRAL,
                                                            outline="#666666")
        tk.Label(bar, textvariable=self.status_var, bg=theme.STATUSBAR_BG, font=theme.FONT_SMALL,
                  name="status_label", anchor="w").pack(side="left", padx=(0, 6), pady=2)
        tk.Label(bar, text=theme.APP_TITLE, bg=theme.STATUSBAR_BG, font=theme.FONT_SMALL,
                  fg="#555555", anchor="e").pack(side="right", padx=8, pady=2)

    def set_status(self, text, ok=None):
        self.status_var.set(text)
        color = theme.STATUS_NEUTRAL
        if ok is True:
            color = theme.STATUS_OK
        elif ok is False:
            color = theme.STATUS_ERR
        try:
            self.status_light.itemconfigure(self._status_dot, fill=color)
        except Exception:
            pass

    # ------------------------------------------------------------- navigate
    def show(self, screen_name, push_history=True, **ctx):
        if push_history and getattr(self, "_current_screen", None) is not None:
            self.history.append((self._current_screen, self.ctx))
        self._current_screen = screen_name
        self.ctx = ctx
        builder = SCREEN_BUILDERS[screen_name]
        builder(self, self.content)

    def back(self):
        if self.history:
            name, ctx = self.history.pop()
            self.show(name, push_history=False, **ctx)
        else:
            self.set_status("No further back navigation.")

    def _run_tcode(self):
        code = self.cmd_var.get().strip().upper()
        self.cmd_var.set("")
        if code in TCODES:
            name, ctx = TCODES[code]
            self.history = []
            self.show(name, **ctx)
        elif code:
            self.set_status(f"Transaction {code!r} does not exist.")

    def open_new_window(self):
        top = tk.Toplevel(self.win)
        top.title(theme.APP_TITLE + " - Session 2")
        SAPSession(top, self.data, current_material=self.current_material, start_screen="EASY_ACCESS")

    def focus_other_window(self):
        others = [w for w in SAPSession._windows if w is not self and w.win.winfo_exists()]
        if not others:
            self.open_new_window()
            return
        other = others[-1]
        other.win.deiconify()
        other.win.lift()
        other.win.focus_force()

    def _on_close(self):
        try:
            SAPSession._windows.remove(self)
        except ValueError:
            pass
        self.win.destroy()


def launch():
    root = tk.Tk()
    root.title(theme.APP_TITLE)
    data = DemoData()
    session = SAPSession(root, data, start_screen="LOGIN_SELECT")
    return root, session
