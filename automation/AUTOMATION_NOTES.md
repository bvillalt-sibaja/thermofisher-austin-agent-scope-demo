# Thermo Fisher Austin "Agent Scope" demo automation

Two entry-point files, for two different execution contexts:
- **`thermofisher_demo.robot`** -- local iteration on this Mac. Imports the
  sibling Python modules directly (static `Library ThermoFisherDemoLib.py`),
  no network dependency. Launch: `~/rpa-env/bin/python3 -m robot thermofisher_demo.robot`
  (or directly: `python3 orchestrator.py [--pace 0.15] [--headless] [--keep-open]`).
- **`thermofisher_demo.player.robot`** -- the Maker Player upload target.
  Maker Player only takes this one file, not its siblings, so this version
  clones the full dependency tree from the public GitHub repo
  (https://github.com/bvillalt-sibaja/thermofisher-austin-agent-scope-demo)
  into `${OUTPUT_DIR}` at run time and dynamically `Import Library`s the
  freshly-cloned `ThermoFisherDemoLib.py` (a static Settings-table `Library`
  line can't reference a not-yet-cloned path -- it's parsed before any task
  code runs). **Verified locally** with a real (non-`--dryrun`) `robot` run
  of this exact file -- the clone and dynamic import genuinely worked,
  production orders/Teams/JDE/Word all came back correct.

**First real Maker Player upload-and-run (2026-08-26) found a genuine
bug the local run couldn't:** `TclError: Can't find a usable init.tcl` --
Maker Player's embedded Python runtime ships the `tkinter`/`_tkinter` C
extension but not Tcl's own script library alongside it, so the very
first `tk.Tk()` (creating the SAP mirror's root window) failed before any
of this project's own code ran. This is a different, more severe failure
than the already-documented "macOS system Tcl/Tk 8.5 renders blank
windows" gotcha (Bot Progress window template) -- there Tk initializes
fine, just renders nothing; here it can't initialize at all, and it's not
fixable with `pip install` since Tcl's script library isn't a Python
package.

**Fix:** `orchestrator.py` now resolves `TCL_LIBRARY`/`TK_LIBRARY` at
import time (`_resolve_tcl_tk_library()`, runs before `import tkinter`)
by searching known absolute install paths for a real Tcl/Tk on the same
machine -- same technique as the Bot Progress window's own
`Resolve Progress Python`, just pointing at a library directory instead
of choosing an interpreter. On this dev Mac it finds Homebrew's
`/opt/homebrew/Cellar/tcl-tk*/*/lib/tcl8.6` (the same one `rpa-env`'s own
Python already uses); the system's ancient Tcl 8.5 is included as a
last-resort fallback candidate (avoids the crash, but is already known to
render blank windows, so it's ordered after every modern candidate).
Respects an already-valid `TCL_LIBRARY` if one is set, so this never
overrides a deliberately-configured environment.

Re-verified after the fix: local `robot thermofisher_demo.robot` and
`robot thermofisher_demo.player.robot` runs both still pass (this
environment variable resolution is additive -- harmless when Tk already
works fine on its own, which is the case for both `rpa-env` and system
`python3` on this Mac). **Still not independently confirmed inside Maker
Player itself** -- that fix targets the exact error message from the
first real upload-and-run, but a second upload-and-run is the only way to
confirm it actually resolves there, and there may be a second layer of
missing dependencies (`openpyxl`/`Pillow`/`python-docx`) behind this one
that a local run still can't surface.

Replays the recorded process (`../recorded_steps.json`, 309 steps) against
all 6 mirror apps -- `../sap-mirror`, `../teams-mirror`, `../jde-mirror`,
`../snipping-tool-mirror`, `../excel-mirror` (driving the seeded `.xlsx`
files in `../seed-files/`), and `../word-mirror` -- for two materials
(`A42362` then `A35989C`) -- the recording's "Review an other component?"
loop. No real installed app (Word, Excel, ...) is used anywhere anymore;
every touched system is a from-scratch mirror, each individually reskinned
for visual fidelity to the real app it stands in for (see each mirror's own
BUILD_NOTES.md for its "Visual fidelity pass" notes).

## Structural rebuild (2026-08-26) — matching the recording's REAL flow
The original build (and its "one representative pass" / "full recording
including the loop" scoping) misread the recording's actual structure. Two
things were wrong, found by re-walking the source graph's real edges
(`~/Downloads/6a8f3e1642f163c09dac03d7.json`) rather than assuming:

1. **It's one continuous 309-step pass, not two repeats of the same
   sequence.** The recording naturally handles both materials within a
   single linear narrative -- it does NOT restart the whole
   stock-lookup-to-Excel-update sequence for a second material. The
   original build ran the entire pipeline twice (once per SKU), which
   meant JDE and the Safety Stock Metric sheet got touched twice each
   where the recording only touches them once, and it didn't capture that
   the two materials play genuinely different roles (see #2).
2. **The "Review an other component?" decision is a small loop reviewing
   multiple order rows within ONE Material Document List query** (its
   Yes-edge points back to "Double Click in Order value in Material
   Document List", not to the start of the recording) -- confirmed by
   reading the decision node's actual outgoing edges in the source graph,
   not inferred from the traversal script's "always take the non-loop
   edge" default. It is NOT a "process another material from scratch"
   loop.

**The real roles, re-derived from tracing every concrete recorded value
(`textValue`) to where it's written, in order:**
- **A42362**: stock/batch checked, findings shared on Teams, THEN a
  brand-new SAP production order is created (Production Order Create,
  full multi-tab flow) and changed/printed. Ends up as a **Production
  Tracker** row.
- **A35989C**: stock/batch checked, THEN an order **already in the
  system** is reviewed via Material Document List -> Display Material
  Document -> Component Overview (the real small loop lives here) --
  no new order gets created for it. Ends up as a **Customer Service
  Alert Board** row (flagged: "PR TBD" / "Open PR to consume beads to
  avoid $$$ scrap").
- JDE is queried once (for A42362, alongside its Plant Data/Stor.
  navigation). The Word document opens once (A42362's linked spec doc).
  The Safety Stock Metric sheet is touched once, at the very end, tied to
  A35989C's flagged status.

**What changed:** `sap-mirror/sap_app/data.py` now seeds a pre-existing
WIP order (`410892`) for A35989C, so Material Document List has something
real to find and review without the automation having created it (the
seed data previously had `production_order: null` for every material, so
without this, sku2's review step would find nothing). `sap_matdoc_and_display`
now genuinely loops over `find_orders_by_material(sku)` and logs a real
"Review an other component?" Yes/No per iteration (Yes when there's
another row; with one seeded order per material it naturally runs once and
answers "No" -- structurally correct even though it doesn't get exercised
with more than one iteration by the current data). `run_full_demo` was
rewritten from a `for sku in [sku1, sku2]:` loop running the identical
sequence twice, to two distinct sequences matching each material's real
role, with the three Excel updates called once each at the end (Tracker
for sku1, CSAB + Safety Stock for sku2).

**Not attempted:** replicating the exact click-by-click interleaving of
Production Order Create/Change screens and the many "Select Other SAP
Window" switches scattered through the raw recording (steps 78-244 in
particular). That level of alternation reflects the human's own working
style bouncing between two open SAP sessions, not a distinct business
action each time -- reproducing it wouldn't add real coverage, just
churn. Every distinct action/screen still happens once for the right
material; only the exact micro-ordering of window-switches differs from
the raw recording.

**Verified:** re-ran the full pipeline after the change --
`production_orders` now correctly shows `['410892', '411050']` (the
pre-existing seeded order plus the newly created one, not two freshly
created orders); `Production Tracker 2026.xlsx` has only A42362's row,
`Customer Service Alert Board 2026.xlsx` has only A35989C's row (both
re-read fresh from disk); JDE queried once (result is for A42362); Word
opened once; log shrank from 58 to 40 steps (removed the duplicated
JDE/Excel work, not removed coverage). Full `robot thermofisher_demo.robot`
run: PASS.

## Architecture
One shared Tk root (the SAP mirror's own window). Every other mirror app
(Teams, JDE, Snipping Tool, Excel-mirror) was patched to accept an optional
`master` and open as a `Toplevel` under that shared root instead of creating
its own `tk.Tk()`, so all windows are visible together and driven from one
Python process -- see `mirror_driver.py` for the generic widget-name driver
(click/double_click/set_entry/set_text/press_return) used across all of them,
matching each app's own documented `name=` convention (see their
BUILD_NOTES.md). No OS-level clicking or accessibility APIs are used
anywhere (works identically on Windows).

## Fixes made while integrating (beyond the mirror apps' own scope)
- `teams-mirror/teams_app/chat.py`: `attach_image()` was pointed at the
  wrong directory for the Snipping Tool's saved capture (`snipping-tool-mirror/captures/*.png`,
  which never existed) -- fixed to read `../shared_state/latest_snip.png`,
  matching what `snipping-tool-mirror/main.py` actually writes.
- `teams_app/app.py`, `jde-mirror/main.py`, `snipping-tool-mirror/main.py`,
  `excel-mirror/main.py`: each subclassed `tk.Tk()` directly; changed to
  `tk.Toplevel(master)` (standalone `python3 main.py` still works -- each now
  creates its own hidden root first) so the orchestrator can host all of them
  under one shared root instead of running multiple independent `tk.Tk()`
  instances in one process (fragile) or opaque subprocesses (no control
  channel, against the chosen interaction mode).
- SAP mirror's `sap_app.popups.confirm_dialog` is monkeypatched to
  auto-answer Yes (`orchestrator.py::_auto_confirm`) instead of trying to
  time a click against its blocking `wait_window()` modal. This replays the
  recording's judgment-call confirms (Edit MRP data? / Create batch
  automatically?) exactly as the human answered them, without a fragile
  `after()`-based timing race. If a future version of this demo needs the
  popup to visibly flash Yes/No on screen, this is the place to add that
  back in.

## A real bug found in the SAP mirror during integration
`PO_CHANGE`'s screen `ctx` (the order number) is only set via
`session.show(..., order=...)`, but the actual order-number entry on that
screen is read via its own "Enter" button (`on_enter` -> `render(o)`), which
never updates `session.ctx`. Round-tripping through Print Preview and back
(`Back` restores `("PO_CHANGE", {})` from history) lands on a blank
PO_CHANGE screen with no order loaded and no Save button. Worked around in
`orchestrator.py::sap_change_order_and_print` by re-entering the order
number after returning from Print before clicking Save, rather than patching
the mirror app itself (out of scope for this integration pass) -- flag if a
future user of the SAP mirror on its own hits the same thing.

## Bot Progress window
`bot_progress_window.py` (copied verbatim from the `rpa` plugin's own
`templates/bot_progress_window.robot` embedded payload, decoded from its
base64 form -- same Maker-brand dark window: `#150B27` background, Inter
font, Mimica mark icon) narrates the run for a human watching it, one step
at a time, in an always-on-top window in the bottom-right corner.

Launched as its own OS process (`subprocess.Popen([sys.executable, ...])`
in `Orchestrator.start_bot_progress`, called at the top of `run_full_demo`)
rather than a thread inside this process, for the same Tkinter-main-thread
reason the template itself documents. Runs under this same interpreter
(`sys.executable`, i.e. `~/rpa-env/bin/python3`) -- confirmed to have a
working Tcl/Tk 8.6, so none of the template's Maker-Player-specific
PATH-guessing (`Resolve Progress Python`) was needed; that logic exists to
work around Maker Player's own embedded-runtime child-process PATH, which
doesn't apply to this locally-launched demo.

`Orchestrator.show_progress(headline, body)` writes the state JSON at each
phase boundary inside `run_full_demo` (login, per-material stock lookup,
Teams findings, document open, order create, JDE lookup, spreadsheet
updates, "review another component", done) -- 15 narration points across
the two-material run, not a literal 1:1 per recorded micro-step, matching
the "collapse mechanical sub-steps into each meaningful action" guidance.
`stop_bot_progress()` runs in a `finally` around the whole demo (and again,
defensively, in `close()`) so the window always closes even if a step
raises.

**Verified live:** during a real `--pace 0.6` run, `osascript`/System
Events listed "Bot Progress" among the actual on-screen windows (alongside
SAP/JDE/Snipping Tool), the state file was observed changing in place
through the sequence ("Logging Into SAP" -> "Sharing Findings on Teams" ->
... -> "Done"), and no orphan `bot_progress_window.py` process remained
after the run completed.

## Snipping Tool stays hidden
`self.snip.withdraw()` right after creation in `Orchestrator.__init__` --
its `new_snip()`/`set_mode()`/`save_and_handoff()` methods don't touch the
real screen (a PIL-rendered placeholder + PIL-rasterized annotations,
entirely in-memory), so the automation drives the capture and hands the
resulting PNG to Teams without ever showing its own window. Teams itself
stays visible throughout (never withdrawn) -- verified live via a polled
`osascript`/System Events window list across a full run: "Microsoft Teams"
appears repeatedly, "Snipping Tool" never does.

## Windows come to the front as the bot uses them
`Orchestrator._focus(win)` (`.lift()` + `.focus_force()`, then `_pump()`)
is called at the start of every phase method that interacts with a
specific app (`run_login`, `sap_stock_lookup`, `teams_communicate_findings`,
`sap_open_second_window`, `sap_change_material_and_document`,
`sap_create_order`, `sap_matdoc_and_display`, `sap_change_order_and_print`,
`jde_lookup`, `excel_update_production_tracker`, `excel_update_csab`) so a
human watching the demo can always tell which app the bot is currently
working in. Word/Excel already lifted their own window on open (unchanged);
this extends the same behavior to SAP (both sessions), Teams, and JDE.
Verified live: polled the frontmost window every 1.5s across a full run --
it tracked the actual phase sequence exactly (JDE -> SAP login -> SAP stock
lookup -> Teams -> 2nd SAP session -> SAP -> Excel Tracker -> Excel CSAB ->
SAP...).

## Typing simulation, not copy-paste
`mirror_driver.set_entry`/`set_text` (used for every SAP field, the JDE
item search, and the Teams message box) now type character-by-character
via the new `type_into()` helper (~20ms/keystroke, with a GUI pump after
each one) instead of inserting the whole value in one call, so a human
watching the demo sees the bot actually typing. Three call sites that used
to bypass `set_entry` with a direct `.insert(0, ...)` (SAP password field,
JDE `item_entry`, Teams `message_entry`) were switched over so the effect
is consistent everywhere text gets entered; JDE's entry widget also picked
up a `name="item_entry"` it didn't have before, needed for the by-name
lookup. Excel cell writes are unchanged (direct `openpyxl` model
mutation + one `refresh_grid()`) -- there's no keystroke-level interaction
to simulate for a spreadsheet cell write in this design. Verified: a
`type_into` sanity check confirms the final value is correct and paced
(~22ms/char for a 6-char SKU), and a full `robot thermofisher_demo.robot`
run still passes end to end.

## Known simplifications / gaps (flagged, not silently dropped)
- Snipping Tool's saved PNG doesn't bake in the drawn shapes (canvas overlay
  is display-only) -- inherited from the Snipping Tool mirror's own scope
  note in `../BUILD_NOTES_jde_snipping.md`.
- Production order "Release" has no lasting effect in the PO_CREATE flow
  (the `order` object the Release button closes over is `None` until Save
  actually creates it) -- a pre-existing SAP-mirror modeling detail, not
  something this automation works around; orders end up `saved=True`,
  `released=False`.
- Each material's "Other SAP Window" pass opens a *new* secondary session
  rather than reusing one across both materials, so two secondary SAP
  windows accumulate over a full run (matches the recording's repeated
  alt-tabbing in spirit, just not window-for-window).
- `--headless` mode (root withdrawn, no visible windows) is unreliable for
  the double-click-driven navigation steps -- Tk does not deliver
  synthetic click coordinates correctly to an unmapped window on this
  platform. Real verification was done with `visible=True` (the default);
  treat `--headless` as best-effort only, not a substitute for a real run.
- Word.app opening is via `open -a "Microsoft Word" <path>` on macOS; the
  Windows branch (`os.startfile`) is written but untested here (no Windows
  box available in this environment).

## Verified (2026-08-26)
- Real `robot thermofisher_demo.robot` run (via `~/rpa-env/bin/robot`, RF
  7.4.2 / Python 3.11.15): 1 task, PASS, 0 failed. Dry-run also clean.
- After a real run: `production_orders` has 2 entries (411050/A42362,
  411051/A35989C, both `saved: True`); `Production Tracker 2026.xlsx` and
  `Customer Service Alert Board 2026.xlsx` on disk (re-opened fresh with
  openpyxl after the run, not from in-memory state) have both materials'
  rows with the recording's real values, updated in place on repeat runs
  (not duplicated); Teams chat thread has 7 messages incl. both
  "Communicate Findings" sends with a real attached-image path; JDE was
  queried for both materials; Word opened without error (`word_opened:
  True`).
- Live-visible run: confirmed via `osascript`/System Events that 8 real
  windows were on screen simultaneously (2 SAP sessions, 2 Excel-mirror
  workbooks, Teams, JDE, Snipping Tool, plus a second SAP session from the
  2nd material's pass) during a real `--keep-open` run.
