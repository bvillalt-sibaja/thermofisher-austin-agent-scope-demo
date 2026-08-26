# SAP GUI mirror — Thermo Fisher Austin (Agent Scope process)

Launch: `cd ~/thermofisher-austin-demo/sap-mirror && python3 main.py`

Fresh Python/Tkinter build (not a copy of `~/sap-ecc-demo`, per explicit scope choice),
following that app's architecture style: a shell (`sap_app/app.py`) with a
"Transaction:" command field + toolbar, content area that swaps screen frames,
status bar. Screens live in `sap_app/screens.py` (one `build_*` function per
screen), popups in `sap_app/popups.py`, dummy data in `data/materials.json`
loaded once per run via `sap_app/data.py::DemoData` (nothing persisted to disk).

## Widget-naming convention for RPA targeting
Every interactive widget gets a Tkinter `name=`, stable and descriptive, so a
later automation can locate it by name/label rather than pixel coordinates:
- Entry fields: `field_<screen>_<field>` (e.g. `field_material`, `field_po_material`, `field_po_total_quant`)
- Buttons: `btn_<action>` (e.g. `btn_stock_req_enter`, `btn_po_save`, `btn_matdoc_execute`, `btn_new_window`, `btn_other_window`)
- Read-only/linkable values: `val_<name>` (e.g. `val_available_qty`, `val_batch`, `val_mrp_element`) — linkable ones are double-click bound
- Confirm dialogs: `<name>_yes` / `<name>_no` (e.g. `auto_batch_confirm_yes`)
- Matdoc list rows: `row_order_<order_no>`

## Screens implemented (functional)
Login select ("070. LSG Prodcution" list, typo preserved from the recording) →
system list → username/password → SAP Easy Access → Stock/Requirements List
(MD04-style, `mode=general|individual`) → Stock Overview (Stor. loc. popup,
Batch → Batch Classification) → Change Material (Basic Data / Plant data-stor. /
Additional Data → Document link) → Production Order Create (tabs: Component
Overview, Allocation Operations/Sequence, Long Text, Goods recept. + Create
Automatic Batch confirm popup, General with Release/Save) → Production Order
Change (Component Overview, Long Text, General with Print → print preview) →
Material Document List (MB51-style, Execute → order rows, double-click drills
into a read-only Display Material Document/Component Overview) → t-code
shortcuts (MD04, CO01, CO02, MB51 typeable in the Transaction field).

"Select Other SAP Window" is modeled as real multi-window: `New Window` opens
a second `Toplevel` running its own independent `SAPSession`, sharing the same
`DemoData` instance so an order created in one window is visible from the
other; `Other SAP Window` raises/focuses the most-recently-opened other
session. This matches the recording's repeated alt-tabbing between two live
SAP sessions.

Seeded materials: `A42362` (5.1 L, matches the recording's "5.1 L of this lot"
Teams exchange) and `A35989C` (matches the recorded CSAB SKU), plus two extra
plausible materials (`A50021`, `A61190`) for variety.

**Update (2026-08-26):** `A35989C` now also gets a pre-existing production
order (`410892`, seeded in `DemoData._seed_existing_orders`) -- the
recording reviews an EXISTING order for this material via Material
Document List, it doesn't create a new one (unlike `A42362`, which does
get a brand-new order created live). Without this seed, Material Document
List would have nothing to find for `A35989C`. See
`../automation/AUTOMATION_NOTES.md`'s "Structural rebuild" section for the
full re-derivation of which material plays which role.

## Simplifications vs. the full recording (flagged, not silently dropped)
- Storage-location and batch-classification popups are single-field info
  displays, not full multi-tab SAP popups.
- "Double-click Batch → Select Batch classification" (an intermediate
  context-menu click in the recording) is collapsed to one double-click
  straight into Batch Classification.
- MRP-element "Additional Data" popup is collapsed into a single Yes/No
  "Edit?" confirm that routes straight to the order (Change if one exists,
  else Create) rather than a full separate MRP-element screen.
- Only one component per production order is modeled (no full multi-line
  Component Overview grid) — sufficient for the single-component demo pass:
  the automation building on this should treat "Review another component?"
  as re-running the same Stock/Requirements → Create/Change Order sequence
  for a second material number, not as a literal in-screen table loop.
- JDE "Find (Ctrl+Alt+I)" lookup and Word document open are NOT in this app
  (out of scope — those are separate mirror pieces per the build plan).

## Verification performed
Headless: instantiated `SAPSession` directly and drove it through the full
path — login → MD04 lookup (A42362) → Stock Overview → Batch Classification →
back-navigation (fixed a real bug: history was never being pushed, so `Back`
did nothing after the first screen — `SAPSession.show()` now always pushes
the previous screen unless there wasn't one yet) → create a production order
via the Save button (order `411050`, verified in `DemoData.production_orders`)
→ MB51 lookup finds that order → drill into Display Material Document → t-code
shortcut (`MD04` in the Transaction field) → open a second window (`New
Window`, confirmed `SAPSession._windows` has 2 entries) → PO_CHANGE loads the
just-created order and its Print button reaches the print preview → an
unknown material number is handled without a crash.

Real launch: `python3 main.py &`, confirmed via `ps` (process alive) and
`osascript ... System Events ... count windows` (returned 1) that the window
actually mapped to the screen, not just that the process started. Killed
cleanly afterward.

## Visual fidelity pass (2026-08-26)
Reskinned to look much closer to real SAP GUI, with zero changes to any
widget `name=`, screen behavior, or method signature the automation
(`~/thermofisher-austin-demo/automation/orchestrator.py` /
`mirror_driver.py`) relies on:
- `theme.py`: SAP-blue title/header bar (`#005696`), classic
  gray-beige toolbar (`#ECE9D8`)/window chrome, pale-yellow required-field
  entry background, grid header/alt-row colors, status-light colors.
- New `icons.py` (same hand-drawn `PhotoImage` pixel-grid technique as
  `~/sap-ecc-demo/sap_app/icons.py`, not unicode/emoji): Enter, Save, Back,
  Print, Exit, Cancel icons on toolbar/nav/popup buttons.
- `app.py`: added a real title bar above the toolbar; toolbar buttons now
  carry icons; status bar got a colored status-light dot (green/red/gray,
  driven by the existing `set_status(..., ok=...)` param, previously
  ignored) plus a session label on the right.
- `screens.py`: sunken/bordered entry fields, bordered nav/toolbar frames,
  a real header rule line, alternating-row + header-shaded Material
  Document List grid, folder-icon-style Easy Access favorites list, styled
  Listboxes (blue selection highlight) on both login screens.
- `popups.py`: confirm/info dialogs now have the same SAP-blue title bar
  and icon buttons as the main window.

Verified: re-ran the full documented headless path above (login through
PO_CHANGE/print, second window, unknown-material handling) against the
reskinned app — all assertions pass unchanged. One environment note found
while re-verifying (not a regression from this pass): `mirror_driver.py`'s
`press_return()` only fires a bound `<Return>` handler on a widget that
already holds Tk keyboard focus in this Tk build; the orchestrator already
avoids this by clicking `btn_toolbar_enter` instead of pressing Return on
the t-code field (see `orchestrator.py`'s `sap_matdoc_and_display`/
`sap_change_order_and_print`), so this doesn't affect the real automation
path. Real launch (`python3 main.py &`) confirmed via `ps` + `osascript`
System Events window count (1) that it still renders, no stderr, killed
cleanly.

## Open questions for whoever builds the automation on top of this
- Confirm the two seeded SKUs (`A42362`, `A35989C`) are the right ones to
  drive the demo's one-representative-pass automation, or whether different
  values are wanted.
- The "Component Overview" simplification above (single component, not a
  literal repeating grid) needs the automation's own loop logic to re-invoke
  the Stock/Requirements → Order flow per component rather than clicking
  through an in-app repeating list.
