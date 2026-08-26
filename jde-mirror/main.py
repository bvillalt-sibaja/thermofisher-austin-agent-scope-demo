"""JD Edwards EnterpriseOne PROD environment mirror.

Minimal browser-chrome + item-search form mirroring the 3 recorded steps:
open JDE, type a P/N#/item number and press Find (Ctrl+Alt+I), read the
findings panel. Real recording hit a web JDE client at
https://e1lsgpd.amer.thermo.com/jde/E1Menu.maf ; this mirror fakes the
address bar for visual fidelity but is a plain Tkinter form underneath.

Visual pass (2026-08-26): restyled to look like JD Edwards EnterpriseOne's
classic web-client chrome (dark corporate-blue header/nav, boxy bordered
fields, a real grid-style results panel with a blue header row and
alternating row shading) instead of the earlier plain Text-dump findings
panel. Automation contract (`item_entry`, `find()`, `result`) is unchanged.
"""
import json
import os
import tkinter as tk
from tkinter import ttk

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
JDE_URL = (
    "https://e1lsgpd.amer.thermo.com/jde/E1Menu.maf?selectJPD920=*ALL&"
    "jdemafjasFrom=SessionTimeout&envRadioGroup=&RENDER_MAFLET=E1Menu&"
    "jdeowpBackButtonProtect=PROTECTED&jdemafjasLauncher=MafletContainer"
)

BG = "#EAF0F6"
HEADER = "#003057"  # JDE/Oracle dark blue
NAV = "#0F4C81"
ACCENT = "#0072CE"
GRID_HEADER = "#1F5C99"
ROW_A = "#FFFFFF"
ROW_B = "#DCE8F5"
FIELD_BORDER = "#7C97AE"

NAV_TABS = ["Fast Path", "My Work", "Favorites", "Address Book", "Inventory Management"]


def load_items():
    with open(os.path.join(DATA_DIR, "items.json")) as f:
        return json.load(f)


class JDEApp(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("JD Edwards EnterpriseOne - PROD")
        self.geometry("800x460")
        self.configure(bg=BG)
        self.items = load_items()
        self.result = None
        self._active_tab = 0
        self._build_chrome()
        self._build_nav()
        self._build_form()
        self._build_grid()
        self._render_grid(None)

    # ------------------------------------------------------------- chrome
    def _build_chrome(self):
        bar = tk.Frame(self, bg="#D9D9D9", height=30)
        bar.pack(fill="x", side="top")
        tk.Label(bar, text="Address:", bg="#D9D9D9", font=("Segoe UI", 9)).pack(
            side="left", padx=(8, 4), pady=5
        )
        addr = tk.Entry(bar, font=("Segoe UI", 9), relief="sunken", bd=1)
        addr.insert(0, JDE_URL)
        addr.configure(state="readonly")
        addr.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=5)

        header = tk.Frame(self, bg=HEADER, height=44)
        header.pack(fill="x", side="top")
        tk.Label(
            header,
            text="JD Edwards EnterpriseOne",
            bg=HEADER,
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=12, pady=8)
        tk.Label(
            header,
            text="Environment: PROD920 / LSG01",
            bg=HEADER,
            fg="#BFD6EA",
            font=("Segoe UI", 9),
        ).pack(side="right", padx=12)

    def _build_nav(self):
        nav = tk.Frame(self, bg=NAV, height=30)
        nav.pack(fill="x", side="top")
        self._tab_labels = []
        for i, name in enumerate(NAV_TABS):
            lbl = tk.Label(
                nav,
                text=name,
                bg=NAV if i else ACCENT,
                fg="white",
                font=("Segoe UI", 9, "bold" if i == 0 else "normal"),
                padx=12,
                pady=6,
                cursor="hand2",
            )
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, idx=i: self._select_tab(idx))
            self._tab_labels.append(lbl)

    def _select_tab(self, idx):
        # Decorative tab switching only -- Item Master Search is the only
        # functional tab; automation never drives this.
        for i, lbl in enumerate(self._tab_labels):
            lbl.configure(bg=ACCENT if i == idx else NAV, font=("Segoe UI", 9, "bold" if i == idx else "normal"))
        self._active_tab = idx

    # --------------------------------------------------------------- form
    def _build_form(self):
        title = tk.Frame(self, bg=BG)
        title.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(
            title, text="Item Master Search", bg=BG, fg=HEADER, font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        form = tk.Frame(self, bg=BG, highlightbackground=FIELD_BORDER, highlightthickness=1)
        form.pack(fill="x", padx=16, pady=(4, 8))
        inner = tk.Frame(form, bg=BG)
        inner.pack(fill="x", padx=10, pady=10)

        tk.Label(inner, text="P/N# / Item Number", bg=BG, font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w"
        )
        self.item_entry = tk.Entry(
            inner, name="item_entry", font=("Consolas", 10), width=30, relief="solid", bd=1,
            highlightbackground=FIELD_BORDER, highlightthickness=1,
        )
        self.item_entry.grid(row=0, column=1, sticky="w", padx=8)
        self.item_entry.bind("<Control-Alt-i>", lambda e: self.find())
        self.item_entry.bind("<Control-Alt-I>", lambda e: self.find())

        find_btn = tk.Button(
            inner, text="Find (Ctrl+Alt+I)", command=self.find, bg=ACCENT, fg="white",
            font=("Segoe UI", 9, "bold"), relief="raised", bd=1, padx=8,
        )
        find_btn.grid(row=0, column=2, padx=8)

    # --------------------------------------------------------------- grid
    def _build_grid(self):
        style = ttk.Style()
        style.theme_use(style.theme_use())
        style.configure(
            "JDE.Treeview.Heading",
            background=GRID_HEADER,
            foreground="white",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure("JDE.Treeview", rowheight=24, font=("Segoe UI", 10), fieldbackground=ROW_A)
        style.map("JDE.Treeview", background=[("selected", ACCENT)])

        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.grid_tree = ttk.Treeview(
            wrap, columns=("field", "value"), show="headings", style="JDE.Treeview", height=8
        )
        self.grid_tree.heading("field", text="Field")
        self.grid_tree.heading("value", text="Value")
        self.grid_tree.column("field", width=180, anchor="w")
        self.grid_tree.column("value", width=440, anchor="w")
        self.grid_tree.tag_configure("rowa", background=ROW_A)
        self.grid_tree.tag_configure("rowb", background=ROW_B)
        self.grid_tree.pack(fill="both", expand=True)

        # Backwards-compat: some callers/tests may still poke a `.findings`
        # Text-like status line -- keep a simple status label under that name
        # is *not* needed since orchestrator never touches it; this comment
        # documents that deliberately for future maintainers.

    def _render_grid(self, item):
        for row in self.grid_tree.get_children():
            self.grid_tree.delete(row)
        if item is None:
            self.grid_tree.insert("", "end", values=("Status", "No search performed yet."), tags=("rowa",))
            return
        rows = [
            ("Item Number", item["item_number"]),
            ("Description", item["description"]),
            ("UOM", item["uom"]),
            ("Status", item["status"]),
            ("Branch/Plant", item["branch_plant"]),
            ("On Hand Qty", item["on_hand_qty"]),
            ("Lot Status", item["lot_status"]),
        ]
        for i, (field, value) in enumerate(rows):
            tag = "rowa" if i % 2 == 0 else "rowb"
            self.grid_tree.insert("", "end", values=(field, value), tags=(tag,))

    # ------------------------------------------------------------- action
    def find(self):
        pn = self.item_entry.get().strip()
        item = self.items.get(pn)
        if item:
            self.result = item
            self._render_grid(item)
        else:
            self.result = None
            self.grid_tree.delete(*self.grid_tree.get_children())
            self.grid_tree.insert(
                "", "end", values=("Status", f"No item found matching '{pn}'."), tags=("rowa",)
            )


if __name__ == "__main__":
    _root = tk.Tk()
    _root.withdraw()
    JDEApp(_root)
    _root.mainloop()
