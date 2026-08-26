"""Headless API for driving the Excel mirror without the Tkinter UI.

An RPA automation (or a test) can `import api` and call these directly
instead of clicking through the GUI, or can call this file from the CLI:

    python3 api.py <path.xlsx> get A1
    python3 api.py <path.xlsx> set A1 "hello"
    python3 api.py <path.xlsx> find "A42362"
    python3 api.py <path.xlsx> save
"""
import sys
from workbook import WorkbookModel


def open_workbook(path, sheet=None):
    return WorkbookModel(path, sheet)


def get_cell(model, ref):
    return model.get_ref(ref)


def set_cell(model, ref, value):
    model.set_ref(ref, value)


def find_and_replace(model, find_text, replace_text=None):
    pos = model.find_next(find_text)
    if pos and replace_text is not None:
        model.set(pos[0], pos[1], replace_text)
    return pos


def save(model, path=None):
    model.save(path)


def _main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    path, cmd = sys.argv[1], sys.argv[2]
    model = open_workbook(path)
    if cmd == "get":
        print(get_cell(model, sys.argv[3]))
    elif cmd == "set":
        set_cell(model, sys.argv[3], sys.argv[4])
        save(model)
        print("ok")
    elif cmd == "find":
        pos = model.find_next(sys.argv[3])
        print(pos)
    elif cmd == "save":
        save(model)
        print("ok")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
