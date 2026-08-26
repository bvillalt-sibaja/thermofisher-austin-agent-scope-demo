"""Small hand-drawn PhotoImage toolbar icons.

Drawn as raw pixel grids rather than Unicode/emoji glyphs, which render as
blank "tofu" in this Tk/Tcl build (and would render inconsistently on a
Windows target anyway) -- same technique used in ~/sap-ecc-demo/sap_app/icons.py.
"""

import tkinter as tk

_SIZE = 16
_cache = {}


def _blank_grid(size=_SIZE, bg=None):
    bg = bg or "#ECE9D8"
    return [[bg] * size for _ in range(size)]


def _rect(grid, x0, y0, x1, y1, color):
    h, w = len(grid), len(grid[0])
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= y < h and 0 <= x < w:
                grid[y][x] = color


def _line(grid, x0, y0, x1, y1, color, thickness=1):
    h, w = len(grid), len(grid[0])
    steps = int(round(max(abs(x1 - x0), abs(y1 - y0), 1)))
    half = thickness // 2
    for i in range(steps + 1):
        t = i / steps
        cx = round(x0 + (x1 - x0) * t)
        cy = round(y0 + (y1 - y0) * t)
        for dy in range(-half, thickness - half):
            for dx in range(-half, thickness - half):
                x, y = cx + dx, cy + dy
                if 0 <= y < h and 0 <= x < w:
                    grid[y][x] = color


def _to_image(grid):
    size = len(grid)
    img = tk.PhotoImage(width=size, height=size)
    for y, row in enumerate(grid):
        for x, color in enumerate(row):
            img.put(color, (x, y))
    return img


def _icon_enter():
    g = _blank_grid()
    _line(g, 2, 8, 10, 8, "#1B6B1B", thickness=2)
    _line(g, 10, 8, 7, 5, "#1B6B1B", thickness=2)
    _line(g, 10, 8, 7, 11, "#1B6B1B", thickness=2)
    return _to_image(g)


def _icon_save():
    g = _blank_grid()
    _rect(g, 3, 3, 12, 12, "#3A6EA5")
    _rect(g, 5, 3, 10, 6, "#FFFFFF")
    _rect(g, 5, 9, 10, 12, "#CFE0F2")
    return _to_image(g)


def _icon_back():
    g = _blank_grid()
    _line(g, 11, 8, 4, 8, "#333333", thickness=2)
    _line(g, 4, 8, 7, 5, "#333333", thickness=2)
    _line(g, 4, 8, 7, 11, "#333333", thickness=2)
    return _to_image(g)


def _icon_exit():
    g = _blank_grid()
    _rect(g, 3, 3, 6, 12, "#8A6D1D")
    _line(g, 6, 3, 12, 5, "#8A6D1D", thickness=1)
    _line(g, 6, 12, 12, 10, "#8A6D1D", thickness=1)
    _line(g, 9, 3, 12, 5, "#C22222", thickness=2)
    _line(g, 9, 12, 12, 10, "#C22222", thickness=2)
    return _to_image(g)


def _icon_cancel():
    g = _blank_grid()
    _line(g, 4, 4, 12, 12, "#C22222", thickness=2)
    _line(g, 12, 4, 4, 12, "#C22222", thickness=2)
    return _to_image(g)


def _icon_print():
    g = _blank_grid()
    _rect(g, 4, 3, 11, 6, "#FFFFFF")
    _rect(g, 3, 6, 12, 10, "#7C7C7C")
    _rect(g, 5, 10, 10, 13, "#FFFFFF")
    return _to_image(g)


_BUILDERS = {
    "enter": _icon_enter,
    "save": _icon_save,
    "back": _icon_back,
    "exit": _icon_exit,
    "cancel": _icon_cancel,
    "print": _icon_print,
}


def get(name):
    """Return a cached PhotoImage for the given icon name (lazy: a Tk root
    must already exist before this is first called)."""
    if name not in _cache:
        _cache[name] = _BUILDERS[name]()
    return _cache[name]
