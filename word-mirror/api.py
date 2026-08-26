"""Headless API for the Word mirror — lets an automation confirm which
document loaded and read its content without any OCR/visual-read step,
mirroring the pattern excel-mirror/api.py established.

    ~/rpa-env/bin/python3 api.py "<path.docx>" text
    ~/rpa-env/bin/python3 api.py "<path.docx>" paragraphs
"""
import sys
from document_reader import read_full_text, read_paragraphs


def get_text(path):
    return read_full_text(path)


def get_paragraphs(path):
    return read_paragraphs(path)


def _main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    path, cmd = sys.argv[1], sys.argv[2]
    if cmd == "text":
        print(get_text(path))
    elif cmd == "paragraphs":
        for style, text in get_paragraphs(path):
            print(f"[{style}] {text}")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
