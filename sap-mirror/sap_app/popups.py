import tkinter as tk
from tkinter import ttk

from sap_app import theme, icons


def _titlebar(win, title):
    bar = tk.Frame(win, bg=theme.TITLE_BG)
    bar.pack(side="top", fill="x")
    tk.Label(bar, text=title, bg=theme.TITLE_BG, fg=theme.TITLE_FG,
              font=theme.FONT_BOLD, anchor="w").pack(side="left", padx=8, pady=4)


def confirm_dialog(parent, title, message, name="confirm_dialog"):
    """Blocking Yes/No popup. Returns True/False. Widget name set on the Yes/No buttons
    as f"{name}_yes" / f"{name}_no" for RPA targeting."""
    result = {"value": None}
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=theme.WINDOW_BG, highlightbackground=theme.GROUPBOX_BORDER, highlightthickness=1)
    win.transient(parent)
    win.grab_set()
    win.geometry("380x150")
    _titlebar(win, title)

    tk.Label(win, text=message, bg=theme.WINDOW_BG, font=theme.FONT_NORMAL,
              wraplength=340, justify="left").pack(padx=16, pady=(18, 14))

    btn_row = tk.Frame(win, bg=theme.WINDOW_BG)
    btn_row.pack(pady=8)

    def choose(val):
        result["value"] = val
        win.destroy()

    tk.Button(btn_row, text=" Yes", name=f"{name}_yes", width=10, image=icons.get("enter"),
              compound="left", font=theme.FONT_SMALL, command=lambda: choose(True)).pack(
        side="left", padx=6)
    tk.Button(btn_row, text=" No", name=f"{name}_no", width=10, image=icons.get("cancel"),
              compound="left", font=theme.FONT_SMALL, command=lambda: choose(False)).pack(
        side="left", padx=6)

    win.wait_window()
    return result["value"]


def info_popup(parent, title, message, name="info_popup"):
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=theme.WINDOW_BG, highlightbackground=theme.GROUPBOX_BORDER, highlightthickness=1)
    win.transient(parent)
    win.geometry("360x160")
    _titlebar(win, title)
    tk.Label(win, text=message, bg=theme.WINDOW_BG, font=theme.FONT_NORMAL,
              wraplength=320, justify="left").pack(padx=16, pady=(18, 12))
    tk.Button(win, text=" Close", name=f"{name}_close", width=10, image=icons.get("cancel"),
              compound="left", font=theme.FONT_SMALL, command=win.destroy).pack(pady=8)
    return win
