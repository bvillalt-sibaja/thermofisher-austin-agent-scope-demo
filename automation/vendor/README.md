# Vendored Tcl/Tk 8.6.12 script library

Pure-Tcl script files only (`library/` from each project's own source tree)
-- no compiled binaries. Pulled from the official upstream release tags:
- https://github.com/tcltk/tcl/tree/core-8-6-12/library
- https://github.com/tcltk/tk/tree/core-8-6-12/library

**Why this is here:** Maker Player's embedded Python runtime ships the
`tkinter`/`_tkinter` C extension compiled against Tcl/Tk **8.6.12**
specifically, but doesn't bundle that version's script library alongside
it -- confirmed live, the first Maker Player upload-and-run failed with
`TclError: Can't find a usable init.tcl`. Pointing `TCL_LIBRARY` at
*some* Tcl 8.6 install on the machine isn't enough either: a stock
`init.tcl` does a `package require -exact Tcl 8.6.12` version check that
fails against any other 8.6.x point release (confirmed live against a
local Homebrew Tcl/Tk 8.6.18 -- exact same error class, different
version numbers). Vendoring the exact matching version sidesteps needing
the right point release to already exist on whatever machine runs this,
which nothing here can otherwise guarantee.

See `../orchestrator.py`'s `_resolve_tcl_tk_library()` for how this gets
selected -- it's tried as one candidate among several (system-search
first, this vendored copy as a fallback), validated via a subprocess
probe before committing to it, so a normal local `robot` run on a
machine with its own working Tcl/Tk 8.6.x is unaffected.

License: `LICENSE.tcl-tk.txt` (Tcl/Tk's own permissive license terms,
copied verbatim from the upstream release).
