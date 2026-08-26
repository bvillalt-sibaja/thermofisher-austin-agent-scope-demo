"""Reads a .docx into a plain list of (style, text) paragraph tuples.

Kept separate from the Tkinter UI so the automation (or a headless test) can
extract the same content without touching any UI code.
"""
from docx import Document


def read_paragraphs(path):
    """Returns [(style_name, text), ...] for every non-empty paragraph,
    in document order. style_name is e.g. 'Heading 1', 'Heading 2', 'Normal'."""
    doc = Document(path)
    out = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        style = p.style.name if p.style is not None else "Normal"
        out.append((style, text))
    return out


def read_full_text(path):
    """Returns the whole document as one newline-joined string (headings
    included), for a quick 'did the right document load' equality check."""
    return "\n".join(text for _, text in read_paragraphs(path))
