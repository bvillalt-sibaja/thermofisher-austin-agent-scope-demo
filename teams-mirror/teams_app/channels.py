import itertools
import tkinter as tk
from tkinter import ttk
from . import theme
from . import icons

_TEAM_COLORS = ["#5B5FC7", "#00847E", "#C4314B", "#986F0B", "#8764B8"]


class ChannelsScreen(tk.Frame):
    """Teams list -> channel -> Files/Shared tab, matching the recording's
    'Select General/CSAB in Teams' -> 'Select Shared in Teams' -> open file flow."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.CONTENT_BG)
        self.app = app
        self.data = app.data
        self.selected_team = None
        self._file_icon = icons.rail_icon("file", size=16, color=theme.ACCENT)

        # Left: teams list
        left = tk.Frame(self, bg=theme.PANEL_BG, width=230)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="Teams", bg=theme.PANEL_BG, fg=theme.TEXT,
                  font=theme.font(13, "bold"), anchor="w").pack(fill="x", padx=12, pady=(14, 8))

        self.team_buttons = {}
        colors = itertools.cycle(_TEAM_COLORS)
        for team in self.data.teams:
            name = team["name"]
            initials = "".join(w[0] for w in name.split()[:2]).upper()
            icon = icons.square_avatar(initials, bg=next(colors), size=26)
            btn = tk.Button(left, name=f"team_{name.lower().replace(' ', '_')}",
                             image=icon, compound="left", text=f"  {name}",
                             bg=theme.PANEL_BG, fg=theme.TEXT, bd=0, anchor="w",
                             font=theme.font(10), relief="flat", padx=10, pady=8,
                             activebackground=theme.SIDEBAR_ACTIVE_LIGHT,
                             command=lambda n=name: self.select_team(n))
            btn.image = icon
            btn.pack(fill="x")
            self.team_buttons[name] = btn

        # Right: channel content
        self.right = tk.Frame(self, bg=theme.CONTENT_BG)
        self.right.pack(side="left", fill="both", expand=True)

        self.header = tk.Label(self.right, text="Select a team", bg=theme.CONTENT_BG,
                                 fg=theme.TEXT, font=theme.font(15, "bold"), anchor="w")
        self.header.pack(fill="x", padx=18, pady=(18, 6))

        self.tabs = tk.Frame(self.right, bg=theme.CONTENT_BG)
        self.tabs.pack(fill="x", padx=16)
        self._tab_underline = tk.Frame(self.right, bg=theme.CONTENT_BG, height=2)
        self._tab_underline.pack(fill="x", padx=16)
        self.posts_btn = tk.Button(self.tabs, text="Posts", name="tab_posts", bd=0,
                                     bg=theme.CONTENT_BG, fg=theme.TEXT, highlightthickness=0,
                                     font=theme.font(10), padx=10, pady=6,
                                     command=lambda: self.show_tab("posts"))
        self.posts_btn.pack(side="left")
        self.files_btn = tk.Button(self.tabs, text="Files", name="tab_shared", bd=0,
                                     bg=theme.CONTENT_BG, fg=theme.TEXT, highlightthickness=0,
                                     font=theme.font(10), padx=10, pady=6,
                                     command=lambda: self.show_tab("files"))
        self.files_btn.pack(side="left")
        self._plus_icon = icons.rail_icon("plus", size=13, color=theme.TEXT_MUTED)
        tk.Label(self.tabs, image=self._plus_icon, bg=theme.CONTENT_BG).pack(
            side="left", padx=10)  # decorative "add tab" +, matches real Teams' tab strip

        self.body = tk.Frame(self.right, bg=theme.CONTENT_BG)
        self.body.pack(fill="both", expand=True, padx=16, pady=10)

        self.current_tab = "posts"
        self.status = tk.Label(self, text="", bg=theme.CONTENT_BG, fg=theme.TEXT_MUTED)

    def _mark_active_tab(self, tab):
        for name, btn in (("posts", self.posts_btn), ("files", self.files_btn)):
            btn.config(fg=theme.ACCENT if name == tab else theme.TEXT,
                       font=theme.font(10, "bold" if name == tab else "normal"))
        for w in self._tab_underline.winfo_children():
            w.destroy()
        underline_x = 0 if tab == "posts" else self.posts_btn.winfo_reqwidth()
        width = self.posts_btn.winfo_reqwidth() if tab == "posts" else self.files_btn.winfo_reqwidth()
        bar = tk.Frame(self._tab_underline, bg=theme.ACCENT, height=2, width=max(width, 1))
        bar.place(x=underline_x, y=0)

    def select_team(self, name):
        self.selected_team = name
        self.header.config(text=name)
        self.app.log_event(f"Select {name} in Teams")
        self.show_tab("posts")

    def show_tab(self, tab):
        self.current_tab = tab
        self._mark_active_tab(tab)
        for w in self.body.winfo_children():
            w.destroy()
        if not self.selected_team:
            return
        team = next(t for t in self.data.teams if t["name"] == self.selected_team)
        if tab == "posts":
            self.app.log_event(f"Show Posts in {self.selected_team} in Teams")
            tk.Label(self.body, text="No new posts.", bg=theme.CONTENT_BG,
                     fg=theme.TEXT_MUTED, font=theme.font(10)).pack(anchor="w")
        else:
            self.app.log_event(f"Select Shared in Teams")
            tk.Label(self.body, text="Shared files", bg=theme.CONTENT_BG,
                     fg=theme.TEXT_MUTED, font=theme.font(9, "bold")).pack(anchor="w", pady=(0, 8))
            for fname in team["files"]:
                row = tk.Frame(self.body, bg=theme.CONTENT_BG)
                row.pack(fill="x", pady=1)
                b = tk.Button(row, text=f"  {fname}", image=self._file_icon, compound="left",
                              name=f"file_{fname.split('.')[0].lower().replace(' ', '_')}",
                              bd=0, anchor="w", font=theme.font(10),
                              bg=theme.CONTENT_BG, fg=theme.TEXT, highlightthickness=0,
                              activebackground=theme.PANEL_BG, padx=6, pady=8,
                              command=lambda f=fname: self.open_file(f))
                b.pack(fill="x")
                tk.Label(row, text="Modified · Today", bg=theme.CONTENT_BG,
                         fg=theme.TEXT_MUTED, font=theme.font(8)).pack(anchor="w", padx=(38, 0))

    def open_file(self, fname):
        self.app.log_event(f"Open {fname} in Teams")
        self.app.open_excel_file(fname)
