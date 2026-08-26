"""Windows Snipping Tool mirror.

Mirrors the ~7 recorded steps: open Snipping Tool over a SAP Stock Overview
window, capture a region, pick the Shapes/highlighter annotation tool, mark
up the capture, then hand the annotated image off so the Teams mirror can
attach it to a chat message.

Handoff contract (consumed by ~/thermofisher-austin-demo/teams-mirror):
  - Image written to:  ~/thermofisher-austin-demo/shared_state/latest_snip.png
  - Metadata written to: ~/thermofisher-austin-demo/shared_state/latest_snip.json
    {"timestamp": "<iso8601>", "source": "Stock Overview - SAP", "annotated": true}
Real screen capture (macOS `screencapture`) is unreliable in this dev
sandbox (has hung indefinitely mid-session before, see project memory), so
"New Snip" renders a synthetic placeholder of a SAP Stock Overview window
via PIL instead of grabbing the real screen -- visually equivalent for
demo purposes, avoids the hang.

Visual pass (2026-08-26): restyled to look like the modern Windows 11
Snipping Tool (light theme, rounded icon toolbar, thin-bordered canvas,
Save/Copy/Share row) instead of the earlier plain gray Tk toolbar. Also
fixes a real gap: annotations drawn on the canvas are now actually
rasterized into the saved PNG (previously `save_and_handoff` just re-saved
the untouched base image, silently dropping every shape/highlighter mark).
Automation contract (`new_snip()`, `set_mode()`, `save_and_handoff()`) is
unchanged.
"""
import json
import os
import tkinter as tk
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont, ImageTk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(ROOT, "shared_state")
SNIP_PNG = os.path.join(SHARED, "latest_snip.png")
SNIP_JSON = os.path.join(SHARED, "latest_snip.json")

CANVAS_W, CANVAS_H = 640, 360

BG = "#FAFAFA"
TOOLBAR_BG = "#F3F3F3"
BORDER = "#D6D6D6"
ACCENT = "#0067C0"  # Win11 accent blue


def render_stock_overview_placeholder():
    """Build a fake 'captured' SAP Stock Overview screenshot with PIL."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), "#F0F0F0")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, CANVAS_W, 28], fill="#003366")
    d.text((8, 6), "Stock Overview: Basic List   Material A42362", fill="white")
    rows = [
        ("Stor. loc.", "Batch", "Unrestricted", "UOM"),
        ("1000", "L2026041", "5.100", "L"),
        ("1000", "L2026039", "12.400", "L"),
    ]
    y = 44
    for r in rows:
        d.text((12, y), f"{r[0]:<12}{r[1]:<14}{r[2]:<14}{r[3]}", fill="black")
        y += 20
    return img


# --------------------------------------------------------------- icon set
def _icon(draw_fn, size=20, color="#3B3B3B"):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_fn(d, size, color)
    return ImageTk.PhotoImage(img)


def _icon_new(d, s, c):
    d.rectangle([3, 3, s - 4, s - 4], outline=c, width=2)


def _icon_rect_mode(d, s, c):
    d.rectangle([3, 5, s - 4, s - 6], outline=c, width=2)


def _icon_freeform(d, s, c):
    d.arc([2, 2, s - 3, s - 3], start=20, end=340, fill=c, width=2)


def _icon_window(d, s, c):
    d.rectangle([3, 3, s - 4, s - 4], outline=c, width=2)
    d.line([3, 8, s - 4, 8], fill=c, width=2)


def _icon_fullscreen(d, s, c):
    corner = 5
    d.line([2, corner, 2, 2, corner, 2], fill=c, width=2, joint="curve")
    d.line([s - 1 - corner, 2, s - 3, 2, s - 3, corner], fill=c, width=2, joint="curve")
    d.line([2, s - 1 - corner, 2, s - 3, corner, s - 3], fill=c, width=2, joint="curve")
    d.line([s - 1 - corner, s - 3, s - 3, s - 3, s - 3, s - 1 - corner], fill=c, width=2, joint="curve")


def _icon_save(d, s, c):
    d.rectangle([3, 3, s - 4, s - 4], outline=c, width=2)
    d.rectangle([6, 3, s - 7, 9], fill=c)


def _icon_copy(d, s, c):
    d.rectangle([2, 5, s - 8, s - 3], outline=c, width=2)
    d.rectangle([7, 2, s - 3, s - 8], outline=c, width=2)


def _icon_share(d, s, c):
    d.ellipse([2, 2, 8, 8], outline=c, width=2)
    d.ellipse([2, s - 9, 8, s - 3], outline=c, width=2)
    d.ellipse([s - 9, s // 2 - 3, s - 3, s // 2 + 3], outline=c, width=2)
    d.line([7, 5, s - 6, s // 2], fill=c, width=2)
    d.line([7, s - 6, s - 6, s // 2], fill=c, width=2)


class SnippingToolApp(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Snipping Tool")
        self.geometry(f"{CANVAS_W + 40}x{CANVAS_H + 110}")
        self.configure(bg=BG)
        self.base_image = None
        self.tk_image = None
        self.draw_mode = "shapes"
        self.capture_mode = "rectangular"
        self.start_xy = None
        self.pending_shape = None
        # Completed annotations, baked into the saved PNG on handoff:
        # each entry is (mode, x0, y0, x1, y1) in canvas/image-pixel coords
        # (1:1 -- the image is drawn at canvas (0,0) with no scaling).
        self.shapes = []
        self._icons = {}

        self._build_toolbar()
        self._build_canvas()
        self._build_status()

        self.new_snip()

    # ------------------------------------------------------------ toolbar
    def _mkicon(self, key, draw_fn, color="#3B3B3B"):
        img = _icon(draw_fn, color=color)
        self._icons[key] = img  # keep a reference, Tk drops unreferenced PhotoImages
        return img

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg=TOOLBAR_BG, highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x")
        pad = dict(padx=3, pady=6)

        def tool_btn(key, draw_fn, command, active=False, tip=""):
            icon = self._mkicon(key, draw_fn, color="white" if active else "#3B3B3B")
            btn = tk.Button(
                toolbar,
                image=icon,
                command=command,
                relief="flat",
                bg=ACCENT if active else TOOLBAR_BG,
                activebackground="#E5E5E5",
                bd=0,
                width=28,
                height=28,
            )
            btn.image = icon
            btn.pack(side="left", **pad)
            return btn

        self.new_btn = tool_btn("new", _icon_new, self.new_snip, active=True)
        tool_btn("rect", _icon_rect_mode, lambda: self._set_capture_mode("rectangular"))
        tool_btn("freeform", _icon_freeform, lambda: self._set_capture_mode("freeform"))
        tool_btn("window", _icon_window, lambda: self._set_capture_mode("window"))
        tool_btn("fullscreen", _icon_fullscreen, lambda: self._set_capture_mode("fullscreen"))

        sep = tk.Frame(toolbar, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", padx=6, pady=4)

        self.shapes_btn = tool_btn("shapes", _icon_rect_mode, lambda: self.set_mode("shapes"), active=True)
        self.highlight_btn = tool_btn("highlighter", _icon_freeform, lambda: self.set_mode("highlighter"))

        tool_btn("share", _icon_share, self.save_and_handoff)
        tool_btn("copy", _icon_copy, self.save_and_handoff)
        tool_btn("save", _icon_save, self.save_and_handoff)

        # Keep a text button too, matching the previous automation-facing
        # affordance, right-aligned like the real app's overflow action.
        tk.Button(
            toolbar, text="Save / Send to Teams", command=self.save_and_handoff,
            relief="flat", bg=TOOLBAR_BG, fg=ACCENT, font=("Segoe UI", 9, "bold"),
        ).pack(side="right", padx=8)

    def _set_capture_mode(self, mode):
        self.capture_mode = mode
        self.status.config(text=f"Capture mode: {mode}")

    # ------------------------------------------------------------- canvas
    def _build_canvas(self):
        frame = tk.Frame(self, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(padx=12, pady=12)
        self.canvas = tk.Canvas(
            frame, width=CANVAS_W, height=CANVAS_H, bg="white", cursor="crosshair",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def _build_status(self):
        self.status = tk.Label(
            self, text="Click New Snip to capture.", bg=BG, fg="#5B5B5B", font=("Segoe UI", 9)
        )
        self.status.pack(fill="x", padx=12)

    # ------------------------------------------------------------- actions
    def set_mode(self, mode):
        self.draw_mode = mode
        self.status.config(text=f"Annotation tool: {mode}")

    def new_snip(self):
        self.base_image = render_stock_overview_placeholder()
        self.tk_image = ImageTk.PhotoImage(self.base_image)
        self.shapes = []
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.status.config(text="Captured Stock Overview (SAP). Choose Shapes/Highlighter to mark up.")

    def on_press(self, event):
        self.start_xy = (event.x, event.y)

    def on_drag(self, event):
        if not self.start_xy:
            return
        if self.pending_shape:
            self.canvas.delete(self.pending_shape)
        x0, y0 = self.start_xy
        color = "#FF0000" if self.draw_mode == "shapes" else "#FFFF00"
        width = 3 if self.draw_mode == "shapes" else 14
        stipple = "" if self.draw_mode == "shapes" else "gray50"
        if self.draw_mode == "shapes":
            self.pending_shape = self.canvas.create_rectangle(
                x0, y0, event.x, event.y, outline=color, width=width
            )
        else:
            self.pending_shape = self.canvas.create_line(
                x0, y0, event.x, event.y, fill=color, width=width, stipple=stipple
            )

    def on_release(self, event):
        if self.start_xy and self.pending_shape:
            x0, y0 = self.start_xy
            self.shapes.append((self.draw_mode, x0, y0, event.x, event.y))
        self.pending_shape = None
        self.start_xy = None

    def _rasterize_shapes(self, base):
        """Bake every completed annotation into a copy of `base` with PIL,
        matching what the canvas visually shows. Rectangles for 'shapes'
        (opaque red outline), semi-transparent yellow strokes for
        'highlighter', same coords/widths the canvas used."""
        composed = base.convert("RGBA")
        overlay = Image.new("RGBA", composed.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        for mode, x0, y0, x1, y1 in self.shapes:
            if mode == "shapes":
                d.rectangle([x0, y0, x1, y1], outline=(255, 0, 0, 255), width=3)
            else:
                d.line([x0, y0, x1, y1], fill=(255, 255, 0, 130), width=14)
        return Image.alpha_composite(composed, overlay).convert("RGB")

    def save_and_handoff(self):
        os.makedirs(SHARED, exist_ok=True)
        composed = self._rasterize_shapes(self.base_image)
        composed.save(SNIP_PNG)
        meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "Stock Overview - SAP",
            "annotated": bool(self.shapes),
        }
        with open(SNIP_JSON, "w") as f:
            json.dump(meta, f, indent=2)
        self.status.config(text=f"Saved to {SNIP_PNG} -- ready for Teams to attach.")


if __name__ == "__main__":
    _root = tk.Tk()
    _root.withdraw()
    SnippingToolApp(_root)
    _root.mainloop()
