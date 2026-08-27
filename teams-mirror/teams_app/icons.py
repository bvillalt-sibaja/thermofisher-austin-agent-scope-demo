"""PIL-rendered icons/avatars for the Teams mirror.

Drawn as raster images (not Unicode emoji/text glyphs) so the look is
identical across platforms instead of depending on whichever emoji font
the OS substitutes -- same rationale as ~/sap-ecc-demo/sap_app/icons.py,
just using Pillow (already a dependency of the Snipping Tool mirror in
this project) instead of hand-rolled pixel grids.
"""

import io

from PIL import Image, ImageDraw, ImageFont

_cache = {}


def _to_photo(img):
    """Converts a PIL image to a `tkinter.PhotoImage` via an in-memory PNG
    round-trip, NOT `PIL.ImageTk.PhotoImage` -- that goes through PIL's
    separate `_imagingtk` C bridge, which registers a custom Tcl command
    ("PyImagingPhoto") into the running interpreter. Confirmed live: under
    Maker Player's bundled Pillow build, that registration silently fails
    (mismatched Tcl/Tk ABI the wheel was built against vs. what's actually
    loaded at runtime), and the *next* call into it raises `_tkinter.TclError:
    invalid command name "PyImagingPhoto"`, which PIL's own exception
    handling then re-raises as an opaque `TypeError: bad argument type for
    built-in operation` -- no mention of Tcl/Tk anywhere in that message.
    `tkinter.PhotoImage(data=...)` is part of `_tkinter` itself (the same
    module handling every other widget here), so it can't be out of sync
    with the running Tcl/Tk the way a separately-compiled bridge can."""
    import tkinter as tk
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return tk.PhotoImage(data=buf.getvalue())


def _font(size, bold=True):
    names = (
        ["Arial Bold.ttf", "Arial.ttf"] if bold else ["Arial.ttf"]
    )
    for name in names:
        for base in ("/System/Library/Fonts/Supplemental/", "/System/Library/Fonts/"):
            try:
                return ImageFont.truetype(base + name, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _centered_text(draw, xy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx, cy = xy
    draw.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), text, font=font, fill=fill)


def avatar(initials, bg="#6264A7", fg="#FFFFFF", size=32):
    """Circular avatar with initials. Returns a PhotoImage (cached)."""
    key = ("avatar", initials, bg, fg, size)
    if key in _cache:
        return _cache[key]
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, big - 1, big - 1), fill=bg)
    _centered_text(d, (big / 2, big / 2 + 1), initials, _font(int(big * 0.38)), fg)
    img = img.resize((size, size), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo


def square_avatar(initials, bg="#6264A7", fg="#FFFFFF", size=32):
    """Rounded-square team icon with initials -- distinct from the circular
    person avatar() used for contacts, matching real Teams' visual
    distinction between a team and a person."""
    key = ("square_avatar", initials, bg, fg, size)
    if key in _cache:
        return _cache[key]
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, big - 1, big - 1), radius=big * 0.22, fill=bg)
    _centered_text(d, (big / 2, big / 2 + 1), initials, _font(int(big * 0.38)), fg)
    img = img.resize((size, size), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo


def rail_icon(kind, size=26, color="#FFFFFF"):
    """Simple silhouette icon for the left rail: 'chat' or 'teams'."""
    key = ("rail", kind, size, color)
    if key in _cache:
        return _cache[key]
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(2, big // 12)
    if kind == "chat":
        # rounded speech-bubble with tail
        pad = big * 0.08
        d.rounded_rectangle((pad, pad, big - pad, big * 0.72), radius=big * 0.18,
                             outline=color, width=lw)
        tail = [(big * 0.28, big * 0.68), (big * 0.20, big * 0.92), (big * 0.44, big * 0.70)]
        d.polygon(tail, fill=color)
    elif kind == "teams":
        # two overlapping "people" circles
        r1 = big * 0.22
        c1 = (big * 0.38, big * 0.34)
        c2 = (big * 0.62, big * 0.34)
        for cx, cy, r in ((c1[0], c1[1], r1 * 0.85), (c2[0], c2[1], r1)):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=lw)
        d.arc((big * 0.14, big * 0.55, big * 0.62, big * 1.05), 200, 340, fill=color, width=lw)
        d.arc((big * 0.34, big * 0.50, big * 0.90, big * 1.05), 200, 340, fill=color, width=lw)
    elif kind == "file":
        pad = big * 0.16
        d.rectangle((pad, pad * 0.6, big - pad, big - pad * 0.6), outline=color, width=lw)
        for i in range(3):
            y = big * (0.38 + i * 0.16)
            d.line((pad * 1.6, y, big - pad * 1.6, y), fill=color, width=max(1, lw - 1))
    elif kind == "paperclip":
        # single continuous hook, like a real paperclip -- the previous
        # 3-piece version (two disjoint arcs + a straight line) read as a
        # stray squiggle rather than a paperclip at small sizes.
        d.arc((big * 0.34, big * 0.06, big * 0.86, big * 0.58), 90, 405, fill=color, width=lw)
        d.line((big * 0.34, big * 0.32, big * 0.34, big * 0.78), fill=color, width=lw)
        d.arc((big * 0.16, big * 0.55, big * 0.52, big * 0.91), 90, 270, fill=color, width=lw)
        d.line((big * 0.52, big * 0.55, big * 0.52, big * 0.22), fill=color, width=lw)
    elif kind == "activity":
        # bell
        pad = big * 0.18
        d.pieslice((pad, pad * 0.6, big - pad, big * 0.85), 180, 360, outline=color, width=lw)
        d.line((pad, big * 0.72, big - pad, big * 0.72), fill=color, width=lw)
        d.line((big * 0.42, big * 0.85, big * 0.58, big * 0.85), fill=color, width=lw)
        d.ellipse((big * 0.40, big * 0.88, big * 0.60, big * 1.02), outline=color, width=max(1, lw - 1))
    elif kind == "calendar":
        pad = big * 0.14
        d.rounded_rectangle((pad, big * 0.22, big - pad, big - pad * 0.6), radius=big * 0.06,
                             outline=color, width=lw)
        d.line((pad, big * 0.4, big - pad, big * 0.4), fill=color, width=lw)
        d.line((big * 0.32, pad * 0.6, big * 0.32, big * 0.3), fill=color, width=lw)
        d.line((big * 0.68, pad * 0.6, big * 0.68, big * 0.3), fill=color, width=lw)
    elif kind == "calls":
        d.arc((big * 0.14, big * 0.10, big * 0.95, big * 0.95), 120, 300, fill=color, width=lw)
        d.line((big * 0.16, big * 0.30, big * 0.30, big * 0.16), fill=color, width=lw)
        d.line((big * 0.70, big * 0.84, big * 0.84, big * 0.70), fill=color, width=lw)
    elif kind == "apps":
        s = big * 0.16
        for cx in (big * 0.28, big * 0.72):
            for cy in (big * 0.28, big * 0.72):
                d.rounded_rectangle((cx - s, cy - s, cx + s, cy + s), radius=s * 0.3, outline=color, width=lw)
    elif kind == "plus":
        d.line((big * 0.5, big * 0.18, big * 0.5, big * 0.82), fill=color, width=lw)
        d.line((big * 0.18, big * 0.5, big * 0.82, big * 0.5), fill=color, width=lw)
    img = img.resize((size, size), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo


def person_icon(size=22, color="#5B5FC7"):
    """Generic profile-picture placeholder: a white person silhouette on a
    colored circle. `color` is the circle's background -- must NOT be white,
    since the silhouette itself is always drawn white and would disappear
    against a same-color background (this was a real bug: both call sites
    omitted `color`, inheriting an old white default, making the avatar
    render as a blank white circle)."""
    key = ("person", size, color)
    if key in _cache:
        return _cache[key]
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, big - 1, big - 1), fill=color)
    head_r = big * 0.16
    d.ellipse((big / 2 - head_r, big * 0.24, big / 2 + head_r, big * 0.24 + 2 * head_r),
              fill="#FFFFFF")
    d.pieslice((big * 0.24, big * 0.56, big * 0.76, big * 1.10), 180, 360, fill="#FFFFFF")
    img = img.resize((size, size), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo


def small_icon(kind, size=16, color="#5B5B5B"):
    """Small monochrome glyphs for the top command bar, chat header actions,
    and the compose-box formatting toolbar."""
    key = ("small", kind, size, color)
    if key in _cache:
        return _cache[key]
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(2, big // 12)
    if kind == "chevron_left":
        d.line((big * 0.62, big * 0.18, big * 0.34, big * 0.5), fill=color, width=lw)
        d.line((big * 0.34, big * 0.5, big * 0.62, big * 0.82), fill=color, width=lw)
    elif kind == "chevron_right":
        d.line((big * 0.38, big * 0.18, big * 0.66, big * 0.5), fill=color, width=lw)
        d.line((big * 0.66, big * 0.5, big * 0.38, big * 0.82), fill=color, width=lw)
    elif kind == "search":
        d.ellipse((big * 0.14, big * 0.14, big * 0.62, big * 0.62), outline=color, width=lw)
        d.line((big * 0.58, big * 0.58, big * 0.88, big * 0.88), fill=color, width=lw)
    elif kind == "settings":
        cx = cy = big / 2
        r = big * 0.20
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=lw)
        import math
        for i in range(8):
            a = i * math.pi / 4
            x0, y0 = cx + r * 1.15 * math.cos(a), cy + r * 1.15 * math.sin(a)
            x1, y1 = cx + r * 1.55 * math.cos(a), cy + r * 1.55 * math.sin(a)
            d.line((x0, y0, x1, y1), fill=color, width=lw)
    elif kind == "help":
        d.ellipse((big * 0.08, big * 0.08, big * 0.92, big * 0.92), outline=color, width=lw)
        _centered_text(d, (big * 0.5, big * 0.52), "?", _font(int(big * 0.5)), color)
    elif kind == "video":
        d.rounded_rectangle((big * 0.1, big * 0.28, big * 0.62, big * 0.72), radius=big * 0.06,
                             outline=color, width=lw)
        d.polygon([(big * 0.64, big * 0.38), (big * 0.9, big * 0.24), (big * 0.9, big * 0.76),
                   (big * 0.64, big * 0.62)], outline=color, width=lw)
    elif kind == "phone":
        # Simple mobile-phone glyph (rounded-rect body + speaker notch).
        # Two earlier attempts at a classic diagonal handset silhouette (an
        # arc-plus-ticks crescent, then a rotated bow-tie/dumbbell) both
        # blurred into an unrecognizable blob at this icon's actual 16px
        # render size -- a upright phone-body outline stays crisp and
        # unambiguous that small.
        d.rounded_rectangle((big * 0.28, big * 0.06, big * 0.72, big * 0.94), radius=big * 0.10,
                             outline=color, width=lw)
        d.line((big * 0.42, big * 0.16, big * 0.58, big * 0.16), fill=color, width=lw)
    elif kind == "emoji":
        d.ellipse((big * 0.08, big * 0.08, big * 0.92, big * 0.92), outline=color, width=lw)
        eye_r = big * 0.05
        for ex in (big * 0.35, big * 0.65):
            d.ellipse((ex - eye_r, big * 0.36 - eye_r, ex + eye_r, big * 0.36 + eye_r), fill=color)
        d.arc((big * 0.28, big * 0.40, big * 0.72, big * 0.74), 15, 165, fill=color, width=lw)
    elif kind == "gif":
        d.rounded_rectangle((big * 0.05, big * 0.28, big * 0.95, big * 0.72), radius=big * 0.08,
                             outline=color, width=lw)
        _centered_text(d, (big * 0.5, big * 0.51), "GIF", _font(int(big * 0.32)), color)
    elif kind == "sticker":
        d.rounded_rectangle((big * 0.14, big * 0.14, big * 0.86, big * 0.86), radius=big * 0.16,
                             outline=color, width=lw)
        # folded corner
        d.line((big * 0.60, big * 0.86, big * 0.86, big * 0.60), fill=color, width=lw)
        d.line((big * 0.60, big * 0.86, big * 0.60, big * 0.62), fill=color, width=lw)
        d.line((big * 0.62, big * 0.60, big * 0.86, big * 0.60), fill=color, width=lw)
    elif kind == "more":
        for cx in (big * 0.2, big * 0.5, big * 0.8):
            r = big * 0.07
            d.ellipse((cx - r, big * 0.5 - r, cx + r, big * 0.5 + r), fill=color)
    elif kind == "bold":
        _centered_text(d, (big * 0.5, big * 0.52), "B", _font(int(big * 0.62)), color)
    elif kind == "italic":
        f = _font(int(big * 0.62))
        _centered_text(d, (big * 0.5, big * 0.52), "I", f, color)
    elif kind == "underline":
        _centered_text(d, (big * 0.5, big * 0.42), "U", _font(int(big * 0.55)), color)
        d.line((big * 0.22, big * 0.82, big * 0.78, big * 0.82), fill=color, width=lw)
    elif kind == "link":
        d.rounded_rectangle((big * 0.08, big * 0.34, big * 0.5, big * 0.66), radius=big * 0.14,
                             outline=color, width=lw)
        d.rounded_rectangle((big * 0.5, big * 0.34, big * 0.92, big * 0.66), radius=big * 0.14,
                             outline=color, width=lw)
    elif kind == "list":
        for y in (big * 0.26, big * 0.5, big * 0.74):
            r = big * 0.045
            d.ellipse((big * 0.1 - r, y - r, big * 0.1 + r, y + r), fill=color)
            d.line((big * 0.24, y, big * 0.88, y), fill=color, width=max(1, lw - 1))
    elif kind == "send":
        # paper-airplane tip pointing right (the direction a sent message
        # travels), matching real Teams' send-icon orientation.
        d.polygon([(big * 0.88, big * 0.5), (big * 0.14, big * 0.16), (big * 0.38, big * 0.5),
                   (big * 0.14, big * 0.84)], fill=color)
    img = img.resize((size, size), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo


def send_button_icon(diameter=28, bg="#6264A7", fg="#FFFFFF"):
    """A filled circular send button (accent-colored disc + white
    paper-plane), baked into one PhotoImage.

    macOS Aqua's native Tk button chrome ignores a `tk.Button`'s `bg` option
    for a compact image-only button with explicit pixel width/height
    (confirmed live: `tk.Button(image=..., bg=ACCENT, width=30, height=26)`
    rendered as a plain white/gray square, not the accent purple, even
    though the exact same `bg=` pattern worked fine on the rail buttons --
    those use `compound='top'` with a text label and no explicit pixel
    size, a different native rendering path). Baking the circle into the
    image itself sidesteps the widget-chrome issue entirely: the button's
    own `bg` only needs to match its surrounding panel color."""
    key = ("send_btn", diameter, bg, fg)
    if key in _cache:
        return _cache[key]
    scale = 4
    big = diameter * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, big - 1, big - 1), fill=bg)
    d.polygon([(big * 0.70, big * 0.5), (big * 0.32, big * 0.28), (big * 0.44, big * 0.5),
               (big * 0.32, big * 0.72)], fill=fg)
    img = img.resize((diameter, diameter), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo


def rounded_rect_outline(w, h, radius, outline, width_px=1, fill=None):
    """A rounded-rectangle PhotoImage used as a bordered box background
    (search field, compose box) -- like rounded_rect_bg but stroked, with
    an optional fill."""
    key = ("outline", w, h, radius, outline, width_px, fill)
    if key in _cache:
        return _cache[key]
    scale = 3
    img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((width_px * scale / 2, width_px * scale / 2,
                          w * scale - 1 - width_px * scale / 2, h * scale - 1 - width_px * scale / 2),
                         radius=radius * scale, outline=outline, width=max(1, width_px * scale), fill=fill)
    img = img.resize((w, h), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo


def rounded_rect_bg(w, h, radius, fill):
    """A rounded-rectangle PhotoImage used as a chat-bubble background."""
    key = ("bubble", w, h, radius, fill)
    if key in _cache:
        return _cache[key]
    scale = 3
    img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w * scale - 1, h * scale - 1), radius=radius * scale, fill=fill)
    img = img.resize((w, h), Image.LANCZOS)
    photo = _to_photo(img)
    _cache[key] = photo
    return photo
