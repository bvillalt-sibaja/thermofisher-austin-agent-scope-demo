#!/usr/bin/env python3
"""Word-style document viewer mirror for the Thermo Fisher Austin RPA demo.

Usage:
    ~/rpa-env/bin/python3 main.py "<path-to-document.docx>"

Read-only viewer (the recording's own step here is "Read: Visual Read of
Document Application in Word", not an edit) styled to visually resemble
Microsoft Word: a blue title bar, a ribbon with a Home tab, and a white
"page" rendered on a gray backdrop with margins, showing the .docx's real
paragraph text and headings.

Needs python-docx, which is only installed in this project's rpa-env, not
the system python3 — always launch with ~/rpa-env/bin/python3.
"""
import os
import sys
import argparse
import tkinter as tk
from tkinter import font as tkfont

from document_reader import read_paragraphs

WORD_BLUE = "#2B579A"
DARK_BLUE = "#204070"
RIBBON_BG = "#F3F2F1"
PAGE_BG = "#FFFFFF"
BACKDROP = "#E8E8E8"

RIBBON_TABS = ["File", "Home", "Insert", "Design", "Layout", "References", "Review", "View"]

STYLE_FONTS = {
    "Title": ("Calibri Light", 28, "bold"),
    "Heading 1": ("Calibri Light", 18, "bold"),
    "Heading 2": ("Calibri Light", 14, "bold"),
    "Heading 3": ("Calibri Light", 12, "bold"),
    "Normal": ("Calibri", 11, "normal"),
}


class WordMirror(tk.Toplevel):
    def __init__(self, master, path):
        super().__init__(master)
        self.path = path
        self.filename = os.path.basename(path)
        self.title(f"{self.filename} - Word")
        self.geometry("980x760")
        self.configure(bg=BACKDROP)

        self._build_titlebar()
        self._build_ribbon()
        self._build_page()
        self.load_document(path)

    # ---------------------------------------------------------------- UI
    def _build_titlebar(self):
        bar = tk.Frame(self, bg=DARK_BLUE, height=32)
        bar.pack(side="top", fill="x")
        tk.Label(
            bar, text=f"  {self.filename} - Word", bg=DARK_BLUE, fg="white",
            font=("Segoe UI", 10), anchor="w",
        ).pack(side="left", fill="y", pady=4)

    def _build_ribbon(self):
        tabstrip = tk.Frame(self, bg=WORD_BLUE, height=26)
        tabstrip.pack(side="top", fill="x")
        for name in RIBBON_TABS:
            active = name == "Home"
            tk.Label(
                tabstrip, text=name, bg="white" if active else WORD_BLUE,
                fg=WORD_BLUE if active else "white",
                font=("Segoe UI", 9, "bold" if active else "normal"), padx=10, pady=4,
            ).pack(side="left")

        ribbon = tk.Frame(self, bg=RIBBON_BG, height=76, highlightthickness=1, highlightbackground="#c8c6c4")
        ribbon.pack(side="top", fill="x")

        def group(label):
            outer = tk.Frame(ribbon, bg=RIBBON_BG)
            outer.pack(side="left", fill="y", padx=(8, 0))
            inner = tk.Frame(outer, bg=RIBBON_BG)
            inner.pack(side="top", expand=True, fill="both", pady=(6, 0))
            tk.Label(outer, text=label, bg=RIBBON_BG, fg="#5f6368", font=("Segoe UI", 8)).pack(
                side="bottom", pady=(0, 3)
            )
            tk.Frame(ribbon, bg="#c8c6c4", width=1).pack(side="left", fill="y", pady=8)
            return inner

        clip = group("Clipboard")
        tk.Button(clip, text="Paste", relief="raised", width=6).pack(side="left", padx=3, pady=3)

        font_grp = group("Font")
        tk.Label(font_grp, text="Calibri", bg="white", relief="solid", bd=1, width=9, anchor="w").grid(
            row=0, column=0, columnspan=3, padx=2, pady=1, sticky="w"
        )
        for i, label in enumerate(("B", "I", "U")):
            weight = "bold" if label == "B" else "normal"
            slant = "italic" if label == "I" else "roman"
            tk.Button(
                font_grp, text=label, width=2,
                font=("Calibri", 9, weight if label != "U" else "normal"), relief="raised",
            ).grid(row=1, column=i, padx=1, pady=2)

        para_grp = group("Paragraph")
        for i, label in enumerate(("≡", "≡", "≡", "≡")):
            tk.Button(para_grp, text=label, width=2, relief="raised").grid(row=0, column=i, padx=1, pady=2)

        styles_grp = group("Styles")
        for i, name in enumerate(("Normal", "Heading 1", "Heading 2")):
            tk.Button(styles_grp, text=name, relief="raised").grid(row=0, column=i, padx=2, pady=2)

    def _build_page(self):
        outer = tk.Frame(self, bg=BACKDROP)
        outer.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BACKDROP, highlightthickness=0)
        vbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        page_holder = tk.Frame(canvas, bg=BACKDROP)
        canvas.create_window((0, 0), window=page_holder, anchor="n")
        page_holder.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # a white "page" with margins and a faint shadow, like Word's print layout
        shadow = tk.Frame(page_holder, bg="#c0c0c0")
        shadow.pack(pady=(20, 40), padx=(24, 16))
        page = tk.Frame(shadow, bg=PAGE_BG, width=760, height=1000)
        page.pack(padx=(0, 4), pady=(0, 4))
        page.pack_propagate(False)

        self.content = tk.Frame(page, bg=PAGE_BG)
        self.content.pack(fill="both", expand=True, padx=70, pady=60)

    # ------------------------------------------------------------ content
    def load_document(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.title(f"{self.filename} - Word")
        for child in self.content.winfo_children():
            child.destroy()

        self.paragraphs = read_paragraphs(path)
        for style, text in self.paragraphs:
            family, size, weight = STYLE_FONTS.get(style, STYLE_FONTS["Normal"])
            try:
                f = tkfont.Font(family=family, size=size, weight=weight)
            except tk.TclError:
                f = tkfont.Font(family="Helvetica", size=size, weight=weight)
            tk.Label(
                self.content, text=text, font=f, bg=PAGE_BG, fg="#1a1a1a",
                anchor="w", justify="left", wraplength=600,
            ).pack(fill="x", pady=(4, 10 if style != "Normal" else 4), anchor="w")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    root = tk.Tk()
    root.withdraw()
    WordMirror(root, args.path)
    root.mainloop()


if __name__ == "__main__":
    main()
