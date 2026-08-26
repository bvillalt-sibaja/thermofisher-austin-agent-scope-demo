import tkinter as tk
import itertools
import random
from . import theme
from . import icons


def _initials(name):
    parts = [p for p in name.replace(",", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


_AVATAR_COLORS = ["#6264A7", "#8764B8", "#C239B3", "#00B7C3", "#498205", "#CA5010"]


class ChatScreen(tk.Frame):
    """Chat conversation screen: read SKU, send message, attach screenshot, read reply."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.CONTENT_BG)
        self.app = app
        self.data = app.data
        self.pending_image = None
        self._avatar_color = {}
        self._color_cycle = itertools.cycle(_AVATAR_COLORS)
        self._minute = random.randint(0, 59)

        left = tk.Frame(self, bg=theme.PANEL_BG, width=210)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="Chat", bg=theme.PANEL_BG, fg=theme.TEXT,
                  font=theme.font(13, "bold"), anchor="w").pack(fill="x", padx=12, pady=(14, 8))
        for c in self.data.contacts:
            row = tk.Button(left, name=f"contact_{c['name'].split(',')[0].lower()}",
                             bg=theme.PANEL_BG, bd=0, anchor="w", relief="flat",
                             activebackground=theme.SIDEBAR_ACTIVE_LIGHT,
                             command=lambda n=c["name"]: self.select_contact(n))
            row.configure(image=self._avatar_for(c["name"]), compound="left",
                          text=f"  {c['name']}", fg=theme.TEXT, font=theme.font(10),
                          padx=8, pady=8)
            row.pack(fill="x")

        right = tk.Frame(self, bg=theme.CONTENT_BG)
        right.pack(side="left", fill="both", expand=True)

        header_row = tk.Frame(right, bg=theme.CONTENT_BG, highlightbackground=theme.BORDER,
                               highlightthickness=0)
        header_row.pack(fill="x")
        self.header = tk.Label(header_row, text="Dominguez, Analisa", bg=theme.CONTENT_BG,
                                 fg=theme.TEXT, font=theme.font(13, "bold"), anchor="w")
        self.header.pack(side="left", fill="x", expand=True, padx=14, pady=(12, 6))
        header_actions = tk.Frame(header_row, bg=theme.CONTENT_BG)
        header_actions.pack(side="right", padx=14, pady=(12, 6))
        self._header_icons = {
            "video": icons.small_icon("video", size=18, color=theme.TEXT_MUTED),
            "phone": icons.small_icon("phone", size=16, color=theme.TEXT_MUTED),
            "more": icons.small_icon("more", size=16, color=theme.TEXT_MUTED),
        }
        for key in ("video", "phone", "more"):
            tk.Label(header_actions, image=self._header_icons[key], bg=theme.CONTENT_BG).pack(
                side="left", padx=6)
        tk.Frame(right, bg=theme.BORDER, height=1).pack(fill="x")

        self.thread_frame = tk.Frame(right, bg=theme.CONTENT_BG, name="chat_thread")
        self.thread_frame.pack(fill="both", expand=True, padx=14)

        bottom = tk.Frame(right, bg=theme.CONTENT_BG)
        bottom.pack(fill="x", padx=14, pady=10)

        self.attach_label = tk.Label(bottom, text="", bg=theme.CONTENT_BG, fg=theme.TEXT_MUTED, font=theme.font(9))
        self.attach_label.pack(fill="x")

        # Bordered compose box (toolbar row + input row), like real Teams'
        # rounded compose card -- a plain bordered Frame renders far more
        # reliably in Tk than an Entry embedded inside a Canvas, while still
        # reading clearly as one distinct box instead of two loose rows.
        compose = tk.Frame(bottom, bg=theme.CONTENT_BG, highlightbackground=theme.BORDER,
                            highlightthickness=1, bd=0)
        compose.pack(fill="x", pady=(6, 0))

        toolbar = tk.Frame(compose, bg=theme.CONTENT_BG)
        toolbar.pack(fill="x", padx=8, pady=(6, 0))
        self._format_icons = {k: icons.small_icon(k, size=15, color=theme.TEXT_MUTED)
                               for k in ("bold", "italic", "underline", "link", "list")}
        for key in ("bold", "italic", "underline", "link", "list"):
            tk.Label(toolbar, image=self._format_icons[key], bg=theme.CONTENT_BG).pack(
                side="left", padx=(0, 10))

        entry_row = tk.Frame(compose, bg=theme.CONTENT_BG)
        entry_row.pack(fill="x", padx=8, pady=(4, 8))
        self._paperclip = icons.rail_icon("paperclip", size=18, color=theme.TEXT_MUTED)
        tk.Button(entry_row, image=self._paperclip, name="attach_button", bd=0,
                  bg=theme.CONTENT_BG, highlightthickness=0,
                  command=self.attach_image).pack(side="left", padx=(0, 8))
        self.msg_entry = tk.Entry(entry_row, name="message_entry", font=theme.font(10),
                                    relief="flat", bd=0, highlightthickness=0, bg=theme.CONTENT_BG)
        self.msg_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._extra_icons = {k: icons.small_icon(k, size=15, color=theme.TEXT_MUTED)
                              for k in ("emoji", "gif", "sticker")}
        for key in ("emoji", "gif", "sticker"):
            tk.Label(entry_row, image=self._extra_icons[key], bg=theme.CONTENT_BG).pack(
                side="left", padx=6)
        # Circle+glyph baked into one image (see icons.send_button_icon
        # docstring) -- a plain bg=ACCENT on this Button rendered as a
        # blank white/gray square on macOS Aqua for an image-only button
        # with explicit pixel width/height, confirmed live.
        self._send_icon = icons.send_button_icon(diameter=28, bg=theme.ACCENT, fg="#FFFFFF")
        send_btn = tk.Button(entry_row, image=self._send_icon, name="send_button", bd=0,
                              bg=theme.CONTENT_BG, activebackground=theme.CONTENT_BG,
                              highlightthickness=0, command=self.send)
        send_btn.pack(side="left", padx=(8, 0))

        self.render_thread()

    def _avatar_for(self, name):
        if name not in self._avatar_color:
            self._avatar_color[name] = next(self._color_cycle)
        return icons.avatar(_initials(name), bg=self._avatar_color[name], size=28)

    def select_contact(self, name):
        self.header.config(text=name)
        self.app.log_event(f"Select Contact ({name}) in Teams")

    def render_thread(self):
        for w in self.thread_frame.winfo_children():
            w.destroy()
        for i, msg in enumerate(self.data.chat_thread):
            mine = bool(msg.get("mine"))
            align = "e" if mine else "w"
            bubble_bg = theme.ACCENT if mine else theme.PANEL_BG
            fg = "white" if mine else theme.TEXT
            sender = "You" if mine else msg.get("sender", self.header.cget("text"))
            avatar_img = self._avatar_for(sender)
            ts = f"{9 + (i // 3):d}:{(self._minute + i * 3) % 60:02d} {'AM' if i < 6 else 'PM'}"

            outer = tk.Frame(self.thread_frame, bg=theme.CONTENT_BG)
            outer.pack(fill="x", pady=4, anchor=align)

            meta_row = tk.Frame(outer, bg=theme.CONTENT_BG)
            meta_row.pack(fill="x")
            tk.Label(meta_row, text=f"{sender}  ·  {ts}", bg=theme.CONTENT_BG,
                     fg=theme.TEXT_MUTED, font=theme.font(8)).pack(
                side="right" if mine else "left",
                padx=(0, 36) if mine else (36, 0))

            row = tk.Frame(outer, bg=theme.CONTENT_BG)
            row.pack(anchor=align)
            bubble_col = tk.Frame(row, bg=theme.CONTENT_BG)
            av = tk.Label(row, image=avatar_img, bg=theme.CONTENT_BG, bd=0)
            if mine:
                bubble_col.pack(side="left")
                av.pack(side="left", anchor="n", padx=(8, 0))
            else:
                av.pack(side="left", anchor="n", padx=(0, 8))
                bubble_col.pack(side="left")

            bubble = self._make_bubble(bubble_col, msg["text"], bubble_bg, fg)
            bubble.pack()

            if msg.get("image"):
                img_row = tk.Frame(outer, bg=theme.CONTENT_BG)
                img_row.pack(anchor=align, padx=(36, 0) if not mine else (0, 36))
                tk.Label(img_row, text="\U0001F5BC  " + msg["image"].split("/")[-1],
                         bg=theme.PANEL_BG, fg=theme.TEXT, font=theme.font(8),
                         padx=8, pady=4).pack(pady=(2, 0))

    def _make_bubble(self, master, text, bg, fg):
        """A rounded-rectangle chat bubble (Canvas-backed) sized to its text."""
        tmp = tk.Label(master, text=text, font=theme.font(10), wraplength=340,
                        justify="left", padx=12, pady=8)
        tmp.update_idletasks()
        w = max(40, tmp.winfo_reqwidth())
        h = max(28, tmp.winfo_reqheight())
        tmp.destroy()
        canvas = tk.Canvas(master, width=w, height=h, bg=theme.CONTENT_BG,
                            highlightthickness=0, bd=0)
        bg_img = icons.rounded_rect_bg(w, h, radius=12, fill=bg)
        canvas.create_image(0, 0, anchor="nw", image=bg_img)
        canvas._bg_img_ref = bg_img
        canvas.create_text(w / 2, h / 2, text=text, font=theme.font(10), fill=fg,
                            width=w - 24, justify="left")
        return canvas

    def attach_image(self):
        # In the real recording this comes from the Snipping Tool mirror saving a capture.
        # We just point at the most recent capture that app has written, if any.
        import os
        snip_path = os.path.expanduser("~/thermofisher-austin-demo/shared_state/latest_snip.png")
        self.pending_image = snip_path if os.path.exists(snip_path) else "screenshot.png"
        self.attach_label.config(text=f"Attached: {os.path.basename(self.pending_image)}")
        self.app.log_event("Screenshot from Snippingtool attached in Teams")

    def send(self):
        text = self.msg_entry.get()
        if not text and not self.pending_image:
            return
        self.data.send_message(text, image_path=self.pending_image)
        self.msg_entry.delete(0, "end")
        self.pending_image = None
        self.attach_label.config(text="")
        self.render_thread()
        self.app.log_event("Select Send in Teams")
        self.after(500, self.simulate_reply)

    def simulate_reply(self):
        if self.data.deliver_reply_if_pending():
            self.render_thread()
