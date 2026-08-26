#!/usr/bin/env python3
"""Lightweight Excel-style spreadsheet mirror for the Thermo Fisher Austin RPA demo.

Usage:
    python3 main.py <path-to-workbook.xlsx> [--sheet SHEET_NAME]

Opens a real .xlsx workbook (openpyxl) in a Tkinter grid styled loosely like
Excel (green ribbon, column letters / row numbers, a cell-reference box).
Supports functional Find & Replace and direct cell read/write, both from the
UI and programmatically (see api.py) so an RPA automation can drive it either
by clicking through the UI or by calling the API module directly.
"""
import sys
import argparse
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

from workbook import WorkbookModel

GREEN = "#217346"
DARK_GREEN = "#185c37"
LIGHT_GREEN = "#e8f3ee"
GRID_LINE = "#d4d4d4"
HEADER_BG = "#f3f2f1"
HEADER_ACTIVE_BG = "#c6e0d4"
SELECT_BG = "#caead9"
SELECT_BORDER = "#107c41"
FONT = ("Calibri", 10)
FONT_BOLD = ("Calibri", 10, "bold")
HEADER_FONT = ("Calibri", 9, "bold")

COLS = 12
ROWS = 40
CELL_W = 110
CELL_H = 22
ROW_HDR_W = 40

RIBBON_TABS = ["File", "Home", "Insert", "Page Layout", "Formulas", "Data", "Review", "View"]


def col_letter(idx):
    letters = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


class ExcelMirror(tk.Toplevel):
    def __init__(self, master, path, sheet=None):
        super().__init__(master)
        self.model = WorkbookModel(path, sheet)
        self.title(f"Excel Mirror — {self.model.filename}")
        self.geometry("1180x680")
        self.configure(bg="white")
        self.selected = (0, 0)  # row, col (0-indexed, data area)

        self._build_ribbon()
        self._build_formula_bar()
        self._build_sheet_tabs()
        self._build_grid()
        self.refresh_grid()

    # ---------------------------------------------------------------- UI
    def _build_ribbon(self):
        titlebar = tk.Frame(self, bg=DARK_GREEN, height=28)
        titlebar.pack(side="top", fill="x")
        tk.Label(
            titlebar, text=f"  {self.model.filename} — Excel", bg=DARK_GREEN, fg="white",
            font=("Segoe UI", 10), anchor="w",
        ).pack(side="left", fill="y", pady=3)

        tabstrip = tk.Frame(self, bg=GREEN, height=26)
        tabstrip.pack(side="top", fill="x")
        self._active_ribbon_tab = tk.StringVar(value="Home")
        for name in RIBBON_TABS:
            active = name == "Home"
            lbl = tk.Label(
                tabstrip, text=name, bg="white" if active else GREEN,
                fg=GREEN if active else "white", font=("Segoe UI", 9, "bold" if active else "normal"),
                padx=10, pady=4,
            )
            lbl.pack(side="left")

        ribbon = tk.Frame(self, bg="#f6fbf8", height=70, highlightthickness=1, highlightbackground=GRID_LINE)
        ribbon.pack(side="top", fill="x")

        def group(label):
            outer = tk.Frame(ribbon, bg="#f6fbf8")
            outer.pack(side="left", fill="y", padx=(6, 0))
            inner = tk.Frame(outer, bg="#f6fbf8")
            inner.pack(side="top", expand=True, fill="both", pady=(4, 0))
            tk.Label(outer, text=label, bg="#f6fbf8", fg="#5f6368", font=("Segoe UI", 8)).pack(
                side="bottom", pady=(0, 2)
            )
            tk.Frame(ribbon, bg=GRID_LINE, width=1).pack(side="left", fill="y", pady=6)
            return inner

        clip = group("Clipboard")
        ttk.Button(clip, text="Save (Ctrl+S)", command=self.save).pack(side="left", padx=3, pady=3)

        font_grp = group("Font")
        tk.Label(font_grp, text="Calibri", bg="white", relief="solid", bd=1, width=8, anchor="w").grid(
            row=0, column=0, padx=2, pady=2, sticky="w"
        )
        tk.Button(font_grp, text="B", font=("Calibri", 9, "bold"), width=2, relief="raised").grid(
            row=1, column=0, padx=1, pady=1, sticky="w"
        )
        fill_btn = tk.Menubutton(font_grp, text="Fill Color ▓", bg=self._current_fill_swatch(), relief="raised")
        fill_menu = tk.Menu(fill_btn, tearoff=0)
        for swatch_name, rgb in (("Amber", "FFC000"), ("Pale Yellow", "FFFF99"), ("No Fill", None)):
            fill_menu.add_command(label=swatch_name, command=lambda rgb=rgb: self.apply_fill(rgb))
        fill_btn.configure(menu=fill_menu)
        fill_btn.grid(row=0, column=1, rowspan=2, padx=6, pady=2, sticky="w")
        self.fill_btn = fill_btn

        align_grp = group("Alignment")
        ttk.Button(align_grp, text="Merge & Center", command=self.open_merge_dialog).grid(
            row=0, column=0, padx=3, pady=3
        )
        borders_menu_btn = tk.Menubutton(align_grp, text="Borders ⊞", relief="raised")
        borders_menu = tk.Menu(borders_menu_btn, tearoff=0)
        borders_menu.add_command(label="All Borders", command=lambda: self.apply_border("thin", None))
        borders_menu.add_command(
            label="Thick Outside Borders", command=lambda: self.apply_border("thick", "outline")
        )
        borders_menu_btn.configure(menu=borders_menu)
        borders_menu_btn.grid(row=1, column=0, padx=3, pady=3)

        editing_grp = group("Editing")
        ttk.Button(editing_grp, text="Find & Replace (Ctrl+H)", command=self.open_find_replace).pack(
            side="left", padx=3, pady=3
        )

        self.bind_all("<Control-h>", lambda e: self.open_find_replace())
        self.bind_all("<Control-s>", lambda e: self.save())

    def _current_fill_swatch(self):
        return "white"

    def _build_formula_bar(self):
        bar = tk.Frame(self, bg="white", height=26)
        bar.pack(side="top", fill="x")
        self.ref_box = tk.Label(bar, text="A1", width=8, relief="solid", bd=1, bg="white")
        self.ref_box.pack(side="left", padx=(4, 2), pady=2)
        self.formula_var = tk.StringVar()
        entry = tk.Entry(bar, textvariable=self.formula_var, relief="solid", bd=1)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=2)
        entry.bind("<Return>", self._commit_formula_bar)
        self.formula_entry = entry

    def _build_sheet_tabs(self):
        tabs = tk.Frame(self, bg=HEADER_BG, height=24)
        tabs.pack(side="bottom", fill="x")
        self.tab_buttons = {}
        for name in self.model.sheet_names():
            b = tk.Label(
                tabs, text=name, bg=SELECT_BG if name == self.model.active_sheet else HEADER_BG,
                relief="raised" if name == self.model.active_sheet else "flat", padx=8, pady=3,
            )
            b.pack(side="left", padx=1)
            b.bind("<Button-1>", lambda e, n=name: self.switch_sheet(n))
            self.tab_buttons[name] = b

    def switch_sheet(self, name):
        self.model.switch_sheet(name)
        for n, b in self.tab_buttons.items():
            b.configure(bg=SELECT_BG if n == name else HEADER_BG, relief="raised" if n == name else "flat")
        self.refresh_grid()

    def _build_grid(self):
        container = tk.Frame(self, bg="white")
        container.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(container, bg="white")
        vbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        hbar = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        vbar.pack(side="right", fill="y")
        hbar.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        grid = tk.Frame(canvas, bg="white")
        canvas.create_window((0, 0), window=grid, anchor="nw")
        grid.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.canvas = canvas
        self.grid_frame = grid
        self.cell_widgets = {}

        # corner + column headers
        tk.Label(grid, text="", width=6, bg=HEADER_BG, relief="flat", bd=0, height=1).grid(
            row=0, column=0
        )
        self.col_headers = {}
        for c in range(COLS):
            h = tk.Label(
                grid, text=col_letter(c), width=14, bg=HEADER_BG, fg="#444",
                font=HEADER_FONT, relief="flat", bd=0,
                highlightthickness=1, highlightbackground=GRID_LINE,
            )
            h.grid(row=0, column=c + 1, sticky="nsew")
            self.col_headers[c] = h

        self.row_headers = {}
        for r in range(ROWS):
            rh = tk.Label(
                grid, text=str(r + 1), width=6, bg=HEADER_BG, fg="#444",
                font=HEADER_FONT, relief="flat", bd=0,
                highlightthickness=1, highlightbackground=GRID_LINE,
            )
            rh.grid(row=r + 1, column=0, sticky="nsew")
            self.row_headers[r] = rh
            for c in range(COLS):
                lbl = tk.Label(
                    grid, text="", width=14, height=1, bg="white", anchor="w",
                    font=FONT, relief="flat", bd=0, padx=3,
                    highlightthickness=1, highlightbackground=GRID_LINE,
                )
                lbl.grid(row=r + 1, column=c + 1, sticky="nsew")
                lbl.bind("<Button-1>", lambda e, rr=r, cc=c: self.select_cell(rr, cc))
                lbl.bind("<Double-Button-1>", lambda e, rr=r, cc=c: self.edit_cell(rr, cc))
                self.cell_widgets[(r, c)] = lbl

    # ------------------------------------------------------------ actions
    def refresh_grid(self):
        merged_cover = {}  # (r, c) -> (anchor_r, anchor_c, rowspan, colspan)
        for r1, c1, r2, c2 in self.model.merged_ranges():
            for r in range(r1, min(r2, ROWS - 1) + 1):
                for c in range(c1, min(c2, COLS - 1) + 1):
                    merged_cover[(r, c)] = (r1, c1, r2 - r1 + 1, c2 - c1 + 1)

        for (r, c), lbl in self.cell_widgets.items():
            val = self.model.get(r, c)
            lbl.configure(text="" if val is None else str(val))

            fill = self.model.get_fill(r, c)
            bg = self._argb_to_tk(fill) if fill else "white"
            font = FONT_BOLD if fill else FONT
            border_hl = "black" if self.model.has_border(r, c) else GRID_LINE
            border_w = 1
            lbl.configure(bg=bg, font=font, highlightbackground=border_hl, highlightthickness=border_w)

            cover = merged_cover.get((r, c))
            if cover:
                ar, ac, rowspan, colspan = cover
                if (r, c) == (ar, ac):
                    lbl.grid(row=r + 1, column=c + 1, rowspan=rowspan, columnspan=colspan, sticky="nsew")
                    lbl.configure(anchor="center", justify="center")
                else:
                    lbl.grid_remove()
            else:
                lbl.grid(row=r + 1, column=c + 1, rowspan=1, columnspan=1, sticky="nsew")
                lbl.configure(anchor="w", justify="left")

        self._highlight_selection()
        self.title(f"Excel Mirror — {self.model.filename} — {self.model.active_sheet}")

    @staticmethod
    def _argb_to_tk(argb):
        """openpyxl fgColor.rgb is an 8-char ARGB hex string (or a theme-color
        object on some cells); return a Tk-safe '#RRGGBB' or 'white' fallback."""
        if not argb or not isinstance(argb, str) or len(argb) < 6:
            return "white"
        rgb = argb[-6:]
        return f"#{rgb}"

    def _highlight_selection(self):
        for (r, c), lbl in self.cell_widgets.items():
            if lbl is self.cell_widgets.get(self.selected):
                continue
            fill = self.model.get_fill(r, c)
            lbl.configure(highlightbackground="black" if self.model.has_border(r, c) else GRID_LINE)
        for h in self.col_headers.values():
            h.configure(bg=HEADER_BG)
        for h in self.row_headers.values():
            h.configure(bg=HEADER_BG)

        r, c = self.selected
        if (r, c) in self.cell_widgets:
            self.cell_widgets[(r, c)].configure(highlightbackground=SELECT_BORDER, highlightthickness=2)
        if c in self.col_headers:
            self.col_headers[c].configure(bg=HEADER_ACTIVE_BG)
        if r in self.row_headers:
            self.row_headers[r].configure(bg=HEADER_ACTIVE_BG)

        self.ref_box.configure(text=f"{col_letter(c)}{r + 1}")
        self.formula_var.set(self.model.get(r, c) or "")

    def apply_fill(self, rgb):
        r, c = self.selected
        if rgb is None:
            self.model.set_fill(r, c, "FFFFFFFF")
        else:
            self.model.set_fill(r, c, rgb)
        self.refresh_grid()

    def apply_border(self, style, mode):
        r, c = self.selected
        if mode == "outline":
            self.model.set_border_range(r, c, r, c, style=style, outline_only=True)
        else:
            self.model.set_border(r, c, style=style)
        self.refresh_grid()

    def open_merge_dialog(self):
        r, c = self.selected
        self.model.merge_and_center(r, c, r, c + 1)
        self.refresh_grid()

    def select_cell(self, r, c):
        self.selected = (r, c)
        self._highlight_selection()

    def edit_cell(self, r, c):
        self.selected = (r, c)
        current = self.model.get(r, c) or ""
        new_val = simpledialog.askstring("Edit cell", f"{col_letter(c)}{r + 1}:", initialvalue=current, parent=self)
        if new_val is not None:
            self.model.set(r, c, new_val)
            self.refresh_grid()

    def _commit_formula_bar(self, event=None):
        r, c = self.selected
        self.model.set(r, c, self.formula_var.get())
        self.refresh_grid()

    def open_find_replace(self):
        dlg = tk.Toplevel(self)
        dlg.title("Find and Replace")
        dlg.geometry("360x140")
        tk.Label(dlg, text="Find what:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        find_var = tk.StringVar()
        tk.Entry(dlg, textvariable=find_var, width=30).grid(row=0, column=1, padx=8, pady=6)
        tk.Label(dlg, text="Replace with:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        replace_var = tk.StringVar()
        tk.Entry(dlg, textvariable=replace_var, width=30).grid(row=1, column=1, padx=8, pady=6)

        result = {"row": None, "col": None}

        def find_next():
            pos = self.model.find_next(find_var.get())
            if pos:
                result["row"], result["col"] = pos
                self.selected = pos
                self.refresh_grid()
            else:
                messagebox.showinfo("Find and Replace", "No more matches found.", parent=dlg)

        def replace():
            if result["row"] is not None:
                self.model.set(result["row"], result["col"], replace_var.get())
                self.refresh_grid()

        btns = tk.Frame(dlg)
        btns.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Find Next", command=find_next).pack(side="left", padx=6)
        ttk.Button(btns, text="Replace", command=replace).pack(side="left", padx=6)
        ttk.Button(btns, text="Close", command=dlg.destroy).pack(side="left", padx=6)

    def save(self):
        self.model.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--sheet", default=None)
    args = parser.parse_args()
    root = tk.Tk()
    root.withdraw()
    ExcelMirror(root, args.path, args.sheet)
    root.mainloop()


if __name__ == "__main__":
    main()
