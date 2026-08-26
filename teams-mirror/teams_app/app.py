import os
import subprocess
import sys
import tkinter as tk
from . import theme
from . import icons
from .data import DemoData
from .channels import ChannelsScreen
from .chat import ChatScreen

EXCEL_MIRROR_MAIN = os.path.expanduser("~/thermofisher-austin-demo/excel-mirror/main.py")
EXCEL_SEED_DIR = os.path.expanduser("~/thermofisher-austin-demo/seed-files")


class TeamsApp(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Microsoft Teams")
        self.geometry("900x600")
        self.configure(bg=theme.CONTENT_BG)
        self.data = DemoData()
        self.event_log = []

        self._build_topbar()

        body = tk.Frame(self, bg=theme.CONTENT_BG)
        body.pack(side="top", fill="both", expand=True)

        rail = tk.Frame(body, bg=theme.SIDEBAR_BG, width=64)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        self._rail_icons = {
            "chat": icons.rail_icon("chat"),
            "teams": icons.rail_icon("teams"),
            "activity": icons.rail_icon("activity"),
            "calendar": icons.rail_icon("calendar"),
            "calls": icons.rail_icon("calls"),
            "files": icons.rail_icon("file", size=22),
            "apps": icons.rail_icon("apps", size=20),
            "plus": icons.rail_icon("plus", size=16),
            "profile": icons.person_icon(size=30),
        }
        tk.Label(rail, image=self._rail_icons["profile"], bg=theme.SIDEBAR_BG,
                 bd=0).pack(pady=(14, 16))

        # Rail items are Frame+Label, NOT tk.Button -- a native macOS Aqua
        # button with an image+text compound and no explicit pixel size
        # ignores its own `bg` option (confirmed live: every rail item
        # rendered as a light-gray block with the true dark rail color only
        # showing through the `pady` gaps between them, a striped look the
        # user flagged from a real screenshot). Frame/Label backgrounds are
        # respected reliably, so this sidesteps the bug entirely -- same
        # fix family as `icons.send_button_icon`'s baked-in circle, just
        # via plain widgets here since there's no image compositing need.
        self._rail_items = {}

        def rail_item(key, text, command=None, name=None, active=False):
            bg = theme.SIDEBAR_ACTIVE if active else theme.SIDEBAR_BG
            kwargs = {"name": name} if name else {}
            item = tk.Frame(rail, bg=bg, **kwargs)
            item.pack(fill="x")
            icon_lbl = tk.Label(item, image=self._rail_icons[key], bg=bg, bd=0)
            icon_lbl.pack(pady=(8, 2))
            # Skip a redundant text label when the icon glyph already says
            # it (the trailing "+" item -- a text label under a "+" icon
            # read as a visually doubled "+ / +").
            text_lbl = tk.Label(item, text=text, bg=bg, fg=theme.SIDEBAR_FG, font=theme.font(8))
            if text:
                text_lbl.pack(pady=(0, 8))
            else:
                icon_lbl.pack_configure(pady=(8, 8))
            handler = command or (lambda: None)
            for w in (item, icon_lbl, text_lbl):
                w.bind("<Button-1>", lambda e, h=handler: h())
            item.invoke = handler  # mirror_driver.click() calls w.invoke() like a real Button
            self._rail_items[key] = (item, icon_lbl, text_lbl)
            return item

        rail_item("activity", "Activity")  # decorative -- matches real Teams' rail order
        rail_item("chat", "Chat", command=self.show_chat, name="rail_chat", active=True)
        rail_item("teams", "Teams", command=self.show_channels, name="rail_teams")
        rail_item("calendar", "Calendar")  # decorative
        rail_item("calls", "Calls")  # decorative
        rail_item("files", "OneDrive")  # decorative

        tk.Frame(rail, bg=theme.SIDEBAR_BG).pack(fill="both", expand=True)  # spacer
        rail_item("apps", "Apps")  # decorative
        rail_item("plus", "")  # decorative, mirrors the real rail's trailing "+" (icon only)

        self.container = tk.Frame(body, bg=theme.CONTENT_BG)
        self.container.pack(side="left", fill="both", expand=True)

        self.channels_screen = None
        self.chat_screen = None
        self.show_chat()

    def _build_topbar(self):
        """The command bar above the rail/content: back/forward, a search
        box, and settings/help/profile icons on the right -- all decorative
        (no automation hook targets this row), matching real Teams' shell
        chrome that was completely missing from the earlier pass."""
        bar = tk.Frame(self, bg=theme.SIDEBAR_BG, height=44)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        nav = tk.Frame(bar, bg=theme.SIDEBAR_BG)
        nav.pack(side="left", padx=(12, 0))
        for kind in ("chevron_left", "chevron_right"):
            tk.Label(nav, image=icons.small_icon(kind, size=16, color="#C8C8E0"),
                     bg=theme.SIDEBAR_BG).pack(side="left", padx=4)

        search_wrap = tk.Frame(bar, bg=theme.SIDEBAR_BG)
        search_wrap.place(relx=0.5, rely=0.5, anchor="center")
        search_bg = icons.rounded_rect_outline(280, 28, radius=6, outline="#4A4A72",
                                                width_px=1, fill="#3B3A5E")
        search_canvas = tk.Canvas(search_wrap, width=280, height=28, bg=theme.SIDEBAR_BG,
                                   highlightthickness=0, bd=0)
        search_canvas.pack()
        search_canvas.create_image(0, 0, anchor="nw", image=search_bg)
        search_canvas._bg_ref = search_bg
        search_icon = icons.small_icon("search", size=14, color="#C8C8E0")
        search_canvas.create_image(12, 14, anchor="w", image=search_icon)
        search_canvas._search_icon_ref = search_icon
        search_canvas.create_text(34, 14, anchor="w", text="Search",
                                   fill="#C8C8E0", font=theme.font(9))

        right = tk.Frame(bar, bg=theme.SIDEBAR_BG)
        right.pack(side="right", padx=(0, 14))
        self._topbar_icons = {
            "settings": icons.small_icon("settings", size=17, color="#C8C8E0"),
            "help": icons.small_icon("help", size=17, color="#C8C8E0"),
            "profile": icons.person_icon(size=24),
        }
        tk.Label(right, image=self._topbar_icons["profile"], bg=theme.SIDEBAR_BG).pack(
            side="right", padx=(10, 0))
        tk.Label(right, image=self._topbar_icons["help"], bg=theme.SIDEBAR_BG).pack(
            side="right", padx=8)
        tk.Label(right, image=self._topbar_icons["settings"], bg=theme.SIDEBAR_BG).pack(
            side="right", padx=8)

    def show_channels(self):
        self._clear()
        self.log_event("Select Channels in Teams")
        self.channels_screen = ChannelsScreen(self.container, self)
        self.channels_screen.pack(fill="both", expand=True)
        self._set_rail_active("teams")

    def show_chat(self):
        self._clear()
        self.log_event("Open Chat Conversation in Teams")
        self.chat_screen = ChatScreen(self.container, self)
        self.chat_screen.pack(fill="both", expand=True)
        self._set_rail_active("chat")

    def _set_rail_active(self, which):
        for key in ("chat", "teams"):
            item, icon_lbl, text_lbl = self._rail_items[key]
            bg = theme.SIDEBAR_ACTIVE if key == which else theme.SIDEBAR_BG
            for w in (item, icon_lbl, text_lbl):
                w.config(bg=bg)

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def log_event(self, text):
        self.event_log.append(text)

    def open_excel_file(self, fname):
        path = os.path.join(EXCEL_SEED_DIR, fname)
        if os.path.exists(EXCEL_MIRROR_MAIN):
            subprocess.Popen([sys.executable, EXCEL_MIRROR_MAIN, path])
        else:
            # excel-mirror not built yet at the time this ran; button stays clickable/no-op.
            self.log_event(f"[stub] would open excel-mirror with {path}")


def main():
    root = tk.Tk()
    root.withdraw()
    app = TeamsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
