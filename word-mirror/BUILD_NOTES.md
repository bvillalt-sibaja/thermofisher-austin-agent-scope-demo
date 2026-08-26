# Word mirror — build notes

Fresh Python/Tkinter build, styled like Microsoft Word (blue title bar `#2B579A`,
Home-tab ribbon with decorative Font/Paragraph/Styles groups, a white "page" with
margins on a gray backdrop). Replaces the earlier approach of shelling out to the
real installed Word.app — this app is now a real mirror like the other four.

## Launch
```
~/rpa-env/bin/python3 main.py "<path-to-document.docx>"
```
**Must use `~/rpa-env/bin/python3`**, not system `python3` — this app needs
`python-docx`, which is only installed in this project's rpa-env (confirmed:
system `python3` raises `ModuleNotFoundError: No module named 'docx'`; rpa-env's
has both `python-docx` and `tkinter` working).

Default target: `~/thermofisher-austin-demo/seed-files/Material Specification Document.docx`.

## Functional vs decorative
- Functional: loading a real `.docx` and rendering its actual paragraph/heading
  text (via `python-docx`) into the page view, per-style fonts (Title/Heading
  1/2/3/Normal each get a distinct Calibri size+weight).
- Decorative: ribbon buttons (Paste/Bold/Italic/Underline/alignment/style
  buttons) — visual only, not wired to editing (this recording step is a
  *read*, "Read: Visual Read of Document Application in Word", not an edit).

## Automation hook
`api.py`, same pattern as `excel-mirror/api.py`:
```python
import api
api.get_text(path)         # -> full document text, newline-joined, headings included
api.get_paragraphs(path)   # -> [(style_name, text), ...] in document order
```
Or from the CLI: `~/rpa-env/bin/python3 api.py "<path>.docx" text` / `paragraphs`.
Lets the automation confirm the right document loaded and read its content
directly, without any OCR/visual-read simulation.

## Class contract (for wiring into orchestrator.py later)
`WordMirror(master, path)` — a `tk.Toplevel`, same shape as the other mirrors
(`ExcelMirror(master, path, sheet=None)` in excel-mirror, etc.) so it can be
opened under the same shared root the orchestrator already uses for the other
four apps. `main()` creates its own `tk.Tk()` root (withdrawn) and passes it as
master for standalone launch — same convention as `excel-mirror/main.py`.
Has a `load_document(path)` method to swap documents on an already-open window
without recreating it, and a `self.paragraphs` attribute (list of (style, text)
tuples) populated after each load, in case the automation wants to inspect the
already-open window's content directly instead of re-reading the file via `api.py`.

## Verification performed
- Headless: `document_reader.read_paragraphs()`/`read_full_text()` against the
  real seed doc — extracted 8 paragraphs, confirmed `"A35989C"` and `"5.1 L"`
  are present in the extracted text, confirmed `api.get_text()` matches exactly.
- Real launch: `~/rpa-env/bin/python3 main.py "<seed doc path>" &`, confirmed via
  `osascript`/System Events that exactly 1 window was on screen for the process,
  then killed cleanly.

## Not wired in
Per the directive, `orchestrator.py` was intentionally NOT touched — it still
opens the real Word.app for this step. Wiring this mirror in means: import
`WordMirror` the same way `excel-mirror`'s `ExcelMirror` is imported
(`_load_module` + `sys.path.insert` for `word-mirror`), open it as a `Toplevel`
under the shared root instead of shelling out, and swap the "Word doc" orchestrator
step over to `WordMirror(root, path)` / `win.load_document(path)`. Note the
interpreter requirement above — if the orchestrator itself doesn't already run
under `~/rpa-env/bin/python3` (it does, per this project's Robot Framework launch
convention), `python-docx` won't be importable.
