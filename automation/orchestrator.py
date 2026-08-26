"""Orchestrates all 6 Thermo Fisher Austin mirror apps (SAP, Teams, JDE,
Snipping Tool, Excel, Word), to replay the "Agent Scope" Process Order/Sku
Flow recording end to end as ONE continuous pass. No real Office/Word app
is used -- every touched system is a mirror.

Single shared Tk root (the SAP mirror IS the root window); every other
mirror app is opened as a Toplevel under it so all windows are visible on
screen together, matching what the human in the recording actually saw.
Driven entirely through each app's own named widgets / Python objects
(see mirror_driver.py) -- no OS-level clicking, no subprocess black boxes.

The two materials play different roles, matching the recording's real
structure (re-derived from the source graph's actual decision edges, not
assumed -- see AUTOMATION_NOTES.md "Structural rebuild"): A42362 gets a
brand-new SAP production order created and printed, landing in the
Production Tracker; A35989C has an existing order already in the system
reviewed via Material Document List (where the recording's real "Review an
other component?" loop lives -- see sap_matdoc_and_display), landing on
the Customer Service Alert Board.

Usage:
    python3 orchestrator.py [--pace 0.0] [--headless]
"""
import argparse
import glob
import importlib.util
import json
import os
import subprocess
import sys


def _resolve_tcl_tk_library():
    """Points TCL_LIBRARY/TK_LIBRARY at a real, working Tcl/Tk install
    before `import tkinter` ever touches the interpreter's Tcl runtime.

    Needed specifically for Maker Player's embedded Python runtime:
    confirmed live, it ships the `tkinter`/`_tkinter` C extension but NOT
    Tcl's own script library alongside it, so the very first `tk.Tk()`
    fails with `TclError: Can't find a usable init.tcl` before any of this
    project's own code runs. This is a different, more severe failure than
    the already-documented "macOS system Tcl/Tk 8.5 renders blank
    windows" gotcha (see the `rpa` plugin's Bot Progress window template)
    -- there, Tk actually initializes; here it can't initialize at all.
    Since Tcl's script library isn't something pip can install, the fix is
    pointing at a complete Tcl/Tk already present elsewhere on the same
    machine, not changing interpreters or installing packages.

    Respects an already-valid TCL_LIBRARY (does nothing if it's already
    set to a directory containing init.tcl) -- this only fills the gap
    when the running interpreter has none configured. Ordered so a modern
    Homebrew/python.org Tcl/Tk 8.6+ wins over macOS's own ancient bundled
    8.5 if both are present (8.5 avoids the crash but is already confirmed
    elsewhere to render zero widget content)."""
    existing = os.environ.get("TCL_LIBRARY")
    if existing and os.path.isfile(os.path.join(existing, "init.tcl")):
        return
    candidates = (
        glob.glob("/opt/homebrew/opt/tcl-tk/lib/tcl8.*") +
        glob.glob("/opt/homebrew/Cellar/tcl-tk*/*/lib/tcl8.*") +
        glob.glob("/usr/local/opt/tcl-tk/lib/tcl8.*") +
        glob.glob("/usr/local/Cellar/tcl-tk*/*/lib/tcl8.*") +
        glob.glob("/Library/Frameworks/Python.framework/Versions/3.*/lib/tcl8.*") +
        glob.glob("/System/Library/Frameworks/Tcl.framework/Versions/*/Resources/Scripts")
    )
    for tcl_dir in candidates:
        if os.path.isfile(os.path.join(tcl_dir, "init.tcl")):
            os.environ["TCL_LIBRARY"] = tcl_dir
            tk_dir = tcl_dir.replace("tcl8.", "tk8.").replace(
                "Tcl.framework", "Tk.framework")
            if os.path.isdir(tk_dir):
                os.environ["TK_LIBRARY"] = tk_dir
            return


_resolve_tcl_tk_library()
import tkinter as tk  # noqa: E402 -- must follow _resolve_tcl_tk_library()

DEMO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_DIR = os.path.join(DEMO_ROOT, "seed-files")
AUTOMATION_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_SCRIPT = os.path.join(AUTOMATION_DIR, "bot_progress_window.py")
PROGRESS_STATE_PATH = os.path.join(AUTOMATION_DIR, "bot_progress_state.json")

sys.path.insert(0, os.path.join(DEMO_ROOT, "sap-mirror"))
sys.path.insert(0, os.path.join(DEMO_ROOT, "teams-mirror"))
sys.path.insert(0, os.path.join(DEMO_ROOT, "excel-mirror"))
sys.path.insert(0, os.path.join(DEMO_ROOT, "word-mirror"))

from sap_app.app import SAPSession
from sap_app.data import DemoData as SAPData
import sap_app.screens as sap_screens
from sap_app import popups as sap_popups
from teams_app.app import TeamsApp

from mirror_driver import click, double_click, set_entry, set_text, press_return, require, find_named


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _auto_confirm(parent, title, message, name="confirm_dialog"):
    """Replaces the blocking Yes/No SAP popup for unattended demo playback:
    the recording's judgment-call confirms (Edit MRP data? / Create batch
    automatically?) are always answered Yes, same as the human did in the
    recording. Avoids a wait_window()/after() timing race for a from-scratch
    build; documented simplification, see automation/AUTOMATION_NOTES.md."""
    return True


# Real recorded field values (see ~/thermofisher-austin-demo/recorded_steps.json)
MATERIALS = ["A42362", "A35989C"]
OUTGOING_MSG = {
    "A42362": None,  # filled from Teams seed at runtime (outgoing_message_1)
    "A35989C": None,  # outgoing_message_2
}
PO_FIELDS = {
    "A42362": {"item_category": "L", "total_quant": "5.1", "start_date": "2026-08-27", "finish_date": "2026-09-03"},
    "A35989C": {"item_category": "L", "total_quant": "231", "start_date": "2026-08-27", "finish_date": "2026-09-10"},
}
TRACKER_ROW = {
    "A42362": {"priority": "1", "wo": "WO-88291", "component": "COMP-4471",
               "notes": "Stock confirmed via Teams (Warner/Dominguez) - 5.1 L, date extended lot."},
    "A35989C": {"priority": "2", "wo": "WO-88355", "component": "COMP-4512",
                "notes": "Filling component, safety stock item - order created for CSAB follow-up."},
}
CSAB_ROW = {
    "A35989C": {"group": "PR TBD", "owner": "AD", "wo": "N/A",
                "notes": "4/23: Open PR to consume beads to avoid $$$ scrap",
                "wip_qty": "47", "stock_out_date": "6/29/2026", "target_due": "TBD", "line_pct": "97%"},
    "A42362": {"group": "Filling", "owner": "AD", "wo": "WO-88291",
               "notes": "Extended-date lot confirmed via Teams, proceeding to production order.",
               "wip_qty": "18", "stock_out_date": "9/15/2026", "target_due": "9/10/2026", "line_pct": "100%"},
}


class Orchestrator:
    def __init__(self, pace=0.0, visible=True):
        self.pace = pace
        self.visible = visible
        self.log = []
        sap_popups.confirm_dialog = _auto_confirm
        sap_screens.confirm_dialog = _auto_confirm

        self.root = tk.Tk()  # this IS the primary SAP window
        self.root.title("SAP Easy Access - Session 1")
        if not visible:
            self.root.withdraw()
        self.sap_data = SAPData()
        self.sap = SAPSession(self.root, self.sap_data, start_screen="LOGIN_SELECT")

        self.teams = TeamsApp(self.root)
        self.teams.open_excel_file = self._open_excel_via_teams  # bypass subprocess spawn

        jde_path = os.path.join(DEMO_ROOT, "jde-mirror", "main.py")
        jde_mod = _load_module("jde_main", jde_path)
        self.jde = jde_mod.JDEApp(self.root)

        snip_path = os.path.join(DEMO_ROOT, "snipping-tool-mirror", "main.py")
        snip_mod = _load_module("snip_main", snip_path)
        self.snip = snip_mod.SnippingToolApp(self.root)
        # Kept out of sight for the demo: its capture/annotate/save methods
        # (new_snip/set_mode/save_and_handoff) don't touch the real screen --
        # new_snip() renders a PIL placeholder and save_and_handoff() bakes
        # annotations onto it, entirely in-memory -- so the automation can
        # drive it and hand the resulting image to Teams without ever
        # flashing its own window on screen.
        self.snip.withdraw()

        self._excel_mod = _load_module("excel_main", os.path.join(DEMO_ROOT, "excel-mirror", "main.py"))
        self._workbook_mod = sys.modules.get("workbook") or _load_module(
            "workbook", os.path.join(DEMO_ROOT, "excel-mirror", "workbook.py"))
        self.excel_windows = {}

        self._word_mod = _load_module("word_main", os.path.join(DEMO_ROOT, "word-mirror", "main.py"))
        self.word_window = None

        self._progress_proc = None

        self._pump()

    # ------------------------------------------------------------- helpers
    def start_bot_progress(self):
        """Launches the always-on-top 'Bot Progress' narration window as its
        own OS process (Tkinter's Cocoa backend needs its event loop on a
        process's own main thread, not a thread inside this one -- see
        build-rpa-automation.md section 10). Runs under this same
        interpreter (sys.executable), which is rpa-env's python3 -- already
        confirmed to have a working Tcl/Tk 8.6, so no PATH-guessing needed
        here (that dance is specifically for Maker Player's embedded
        runtime, which doesn't apply to this local-run demo)."""
        with open(PROGRESS_STATE_PATH, "w") as f:
            f.write("{}")
        try:
            self._progress_proc = subprocess.Popen([sys.executable, PROGRESS_SCRIPT, PROGRESS_STATE_PATH])
        except Exception as e:
            self.step(f"Bot Progress window failed to start (non-fatal): {e}")
            self._progress_proc = None

    def show_progress(self, headline, body):
        """Updates the Bot Progress window with a new headline (3-6 words,
        present tense) and a one/two-sentence body. Safe to call even if the
        window failed to start or was closed by hand."""
        try:
            with open(PROGRESS_STATE_PATH, "w") as f:
                json.dump({"headline": headline, "body": body}, f)
        except OSError:
            pass

    def stop_bot_progress(self):
        if self._progress_proc is not None:
            try:
                self._progress_proc.terminate()
                self._progress_proc.wait(timeout=3)
            except Exception:
                pass
            self._progress_proc = None

    def _focus(self, win):
        """Raises the given window above all the others so a human watching
        the demo can see which app the bot is currently working in, then
        pumps the event loop so the raise actually takes effect before the
        next action runs."""
        try:
            win.lift()
            win.focus_force()
        except Exception:
            pass
        self._pump()

    def _pump(self):
        self.root.update_idletasks()
        self.root.update()
        if self.pace:
            import time
            time.sleep(self.pace)

    def step(self, text):
        self.log.append(text)
        self._pump()

    def _open_excel_via_teams(self, fname):
        """Replaces TeamsApp.open_excel_file's subprocess spawn with an
        in-process Toplevel so the automation can drive/verify it directly,
        per the chosen interaction mode (built-in hooks, not opaque
        subprocesses)."""
        path = os.path.join(SEED_DIR, fname)
        win = self.excel_windows.get(fname)
        if win is None or not win.winfo_exists():
            win = self._excel_mod.ExcelMirror(self.root, path)
            self.excel_windows[fname] = win
        else:
            win.model.wb = self._workbook_mod.WorkbookModel(path).wb  # reload from disk
            win.refresh_grid()
        win.lift()
        self._pump()
        return win

    def workbook_model(self, fname):
        return self._workbook_mod.WorkbookModel(os.path.join(SEED_DIR, fname))

    # ---------------------------------------------------------------- flow
    def run_login(self):
        self._focus(self.sap.win)
        self.step("SAP: select 070. LSG Prodcution system")
        double_click(self.sap.win, "system_list")
        self.step("SAP: select LSG Production (Austin) server")
        double_click(self.sap.win, "lsg_system_list")
        self.step("SAP: enter credentials")
        set_entry(self.sap.win, "field_username", os.environ.get("SAP_DEMO_USER", "DEMO_USER"))
        set_entry(self.sap.win, "field_password", "demo-password")
        click(self.sap.win, "btn_login_enter")
        self._pump()

    def read_sku_from_teams(self, which="pending_sku"):
        sku = getattr(self.teams.data, which)
        self.step(f"Teams: read SKU from chat -> {sku}")
        return sku

    def sap_stock_lookup(self, sku):
        self._focus(self.sap.win)
        self.sap.show("STOCK_REQ", mode="general")
        self.step(f"SAP: Display Stock/Requirements for {sku}")
        set_entry(self.sap.win, "field_material", sku)
        click(self.sap.win, "btn_stock_req_enter")
        double_click(self.sap.win, "val_available_qty", pump=self.pace)
        self.step("SAP: Stock Overview -> Stor. loc. popup")
        double_click(self.sap.win, "val_stor_loc")
        popup_close = find_named(self.sap.win, "stor_loc_popup_close")
        if popup_close:
            popup_close.invoke()
        self.step("SAP: Stock Overview -> Batch Classification")
        double_click(self.sap.win, "val_batch")
        click(self.sap.win, "btn_back")  # back to Stock Overview
        click(self.sap.win, "btn_back")  # back to Stock/Requirements results

    def teams_communicate_findings(self, sku, message):
        self._focus(self.teams)
        self.teams.show_chat()
        self._pump()
        self.step("Snipping Tool: New Snip over Stock Overview")
        self.snip.new_snip()
        self.snip.set_mode("shapes")
        self.snip.save_and_handoff()
        self.step("Teams: attach screenshot + send findings message")
        set_entry(self.teams, "message_entry", message)
        click(self.teams, "attach_button")
        click(self.teams, "send_button")
        # Deterministic reply (bypasses the 500ms `after` timer for automation)
        self.teams.data.deliver_reply_if_pending()
        self.teams.chat_screen.render_thread()
        self._pump()
        reply = self.teams.data.chat_thread[-1]["text"]
        self.step(f"Teams: read response -> {reply!r}")
        return reply

    def sap_open_second_window(self, sku):
        self.step("SAP: Select Other SAP Window (opens second session)")
        click(self.sap.win, "btn_new_window")
        other = [w for w in SAPSession._windows if w is not self.sap][-1]
        self._focus(other.win)
        other.show("STOCK_REQ", mode="individual")
        set_entry(other.win, "field_material", sku)
        click(other.win, "btn_stock_req_enter")
        self.step("SAP (2nd window): individual-access stock lookup + batch check")
        double_click(other.win, "val_available_qty")  # -> Stock Overview
        double_click(other.win, "val_batch")  # -> Batch Classification
        click(other.win, "btn_back")
        click(other.win, "btn_back")
        return other

    def sap_change_material_and_document(self, sku, open_word=False):
        self._focus(self.sap.win)
        self.sap.show("STOCK_REQ", mode="general")
        set_entry(self.sap.win, "field_material", sku)
        click(self.sap.win, "btn_stock_req_enter")
        self.step("SAP: Change Material -> Plant data/stor.")
        click(self.sap.win, "btn_change")
        tabs = require(self.sap.win, "change_tabs")
        tabs.select(1)  # Plant data / stor.
        self._pump()
        tabs.select(2)  # Additional Data
        self._pump()
        self.step("SAP: Additional Data -> Document Data -> open linked document")
        double_click(self.sap.win, "val_document_link")
        click(self.sap.win, "btn_open_document")
        if open_word:
            self._open_word_document()
        click(self.sap.win, "btn_back")  # back to change screen
        click(self.sap.win, "btn_back")  # back to stock/req

    def _open_word_document(self):
        """Opens the seed .docx in the Word mirror app (a Toplevel under the
        shared root), same interaction-mode/no-subprocess-blackbox choice
        already used for Excel -- not the real installed Word.app."""
        doc_path = os.path.join(SEED_DIR, "Material Specification Document.docx")
        self.step(f"Word: open {os.path.basename(doc_path)}")
        try:
            if self.word_window is None or not self.word_window.winfo_exists():
                self.word_window = self._word_mod.WordMirror(self.root, doc_path)
            else:
                self.word_window.load_document(doc_path)
            self.word_window.lift()
            self._pump()
            self._word_opened = True
            self._word_paragraphs = list(getattr(self.word_window, "paragraphs", []))
        except Exception as e:
            self.step(f"Word: open failed (non-fatal for demo) -> {e}")
            self._word_opened = False

    def sap_create_order(self, sku):
        self._focus(self.sap.win)
        self.sap.show("STOCK_REQ", mode="general")
        set_entry(self.sap.win, "field_material", sku)
        click(self.sap.win, "btn_stock_req_enter")
        self.step("SAP: MRP element -> Additional Data confirm -> Create Production Order")
        double_click(self.sap.win, "val_mrp_element")
        self._pump()
        po_fields = PO_FIELDS[sku]

        tabs = require(self.sap.win, "po_create_tabs")
        tabs.select(0)  # Component Overview
        self._pump()
        set_entry(self.sap.win, "field_po_material", sku)
        set_entry(self.sap.win, "field_po_item_category", po_fields["item_category"])
        set_entry(self.sap.win, "field_po_total_quant", po_fields["total_quant"])

        tabs.select(1)  # Allocation Operations/Sequence
        self._pump()
        click(self.sap.win, "btn_po_check")

        tabs.select(2)  # Long Text
        self._pump()
        set_text(self.sap.win, "field_po_long_text", f"Production order for {sku} - created via Agent Scope demo.")

        tabs.select(3)  # Goods recept.
        self._pump()
        click(self.sap.win, "btn_goods_receipt")
        click(self.sap.win, "btn_create_auto_batch")

        tabs.select(4)  # General
        self._pump()
        set_entry(self.sap.win, "field_po_start_date", po_fields["start_date"])
        set_entry(self.sap.win, "field_po_finish_date", po_fields["finish_date"])
        click(self.sap.win, "btn_po_release")
        click(self.sap.win, "btn_po_save")
        self._pump()

        order = next((o for o in self.sap_data.production_orders.values() if o["material"] == sku), None)
        self.step(f"SAP: Production Order {order['order_no'] if order else '?'} created for {sku}")
        return order

    def sap_matdoc_and_display(self, sku):
        """Matches the recording's real "Review an other component?" loop
        (a NodeDecision whose Yes-arm re-double-clicks another order row in
        Material Document List, not a restart of the whole process -- see
        AUTOMATION_NOTES.md). Loops over every existing order found for
        `sku`; with this demo's seed data that's exactly one order per
        material, so it naturally runs once and answers "No", but the loop
        is real and will drill into additional rows if more are ever
        seeded."""
        self._focus(self.sap.win)
        set_entry(self.sap.win, "command_field", "MB51")
        click(self.sap.win, "btn_toolbar_enter")
        self.step(f"SAP: Material Document List - Execute for {sku}")

        def run_query():
            set_entry(self.sap.win, "field_matdoc_material", sku)
            click(self.sap.win, "btn_matdoc_execute")

        run_query()
        orders = self.sap_data.find_orders_by_material(sku)
        last_order = None
        for i, order in enumerate(orders):
            double_click(self.sap.win, f"row_order_{order['order_no']}")
            self.step(f"SAP: Display Material Document - Order {order['order_no']}")
            double_click(self.sap.win, "val_component_overview")
            popup = find_named(self.sap.win, "component_overview_popup_close")
            if popup:
                popup.invoke()
            click(self.sap.win, "btn_back")
            last_order = order
            has_more = i < len(orders) - 1
            self.step(f'SAP: "Review an other component?" -> {"Yes" if has_more else "No"}')
            if has_more:
                run_query()
        return last_order

    def sap_change_order_and_print(self, order):
        if not order:
            return
        self._focus(self.sap.win)
        set_entry(self.sap.win, "command_field", "CO02")
        click(self.sap.win, "btn_toolbar_enter")
        self.step(f"SAP: Change Production Order {order['order_no']}")
        set_entry(self.sap.win, "field_po_order", order["order_no"])
        click(self.sap.win, "btn_po_change_enter")
        tabs = require(self.sap.win, "po_change_tabs")
        tabs.select(1)  # Long Text
        self._pump()
        set_text(self.sap.win, "field_po_long_text", f"Order {order['order_no']} reviewed and confirmed complete.")
        tabs.select(2)  # General
        self._pump()
        self.step("SAP: Print production order")
        click(self.sap.win, "btn_po_print")
        click(self.sap.win, "btn_back")
        # PO_CHANGE's screen ctx isn't preserved across the Print round-trip
        # (a real gap in the mirror app's own history handling -- the order
        # number was set via the "Enter" button, not session.show(), so it
        # never made it into session.ctx); re-supply it before Save.
        set_entry(self.sap.win, "field_po_order", order["order_no"])
        click(self.sap.win, "btn_po_change_enter")
        click(self.sap.win, "btn_po_save")

    def jde_lookup(self, sku):
        self._focus(self.jde)
        self.step(f"JDE: Find item {sku}")
        set_entry(self.jde, "item_entry", sku)
        self.jde.find()
        self._pump()
        return self.jde.result

    def excel_update_production_tracker(self, sku):
        self._focus(self.teams)
        self.step("Teams: open Production Tracker 2026.xlsx (Shared files)")
        self.teams.show_channels()
        self.teams.channels_screen.select_team("General")
        self.teams.channels_screen.show_tab("files")
        click(self.teams, "file_production_tracker_2026")

        model = self.workbook_model("Production Tracker 2026.xlsx")
        row = model.find_row_by_value(sku)
        if row is None:
            row = next(r for r in range(1, 200) if model.get(r, 2) in (None, ""))
        fields = TRACKER_ROW[sku]
        model.set(row, 0, fields["priority"])
        model.set(row, 1, self.sap_data.get_material(sku)["mrp_element"])
        model.set(row, 2, sku)
        model.set(row, 3, fields["wo"])
        model.set(row, 4, fields["component"])
        model.set(row, 5, fields["notes"])
        model.save()
        self.step(f"Excel: Production Tracker row {row + 1} updated for {sku}")
        win = self.excel_windows.get("Production Tracker 2026.xlsx")
        if win and win.winfo_exists():
            win.model = model
            win.refresh_grid()
        self._pump()

    def excel_update_csab(self, sku):
        self._focus(self.teams)
        self.step("Teams: open Customer Service Alert Board 2026.xlsx (CSAB)")
        self.teams.show_channels()
        self.teams.channels_screen.select_team("CSAB")
        self.teams.channels_screen.show_tab("files")
        click(self.teams, "file_customer_service_alert_board_2026")

        model = self.workbook_model("Customer Service Alert Board 2026.xlsx")
        row = model.find_row_by_value(sku)
        if row is None:
            row = next(r for r in range(1, 200) if model.get(r, 4) in (None, ""))
        fields = CSAB_ROW[sku]
        model.set(row, 0, fields["line_pct"])
        model.set(row, 1, fields["group"])
        model.set(row, 2, fields["owner"])
        model.set(row, 3, fields["wo"])
        model.set(row, 4, sku)
        model.set(row, 5, fields["notes"])
        model.set(row, 6, fields["wip_qty"])
        model.set(row, 7, fields["stock_out_date"])
        model.set(row, 8, fields["target_due"])
        model.save()
        self.step(f"Excel: CSAB row {row + 1} updated for {sku}")
        win = self.excel_windows.get("Customer Service Alert Board 2026.xlsx")
        if win and win.winfo_exists():
            win.model = model
            win.refresh_grid()
        self._pump()

    def excel_touch_safety_stock_metric(self, sku):
        self.step("Excel: V2 Trending Safety Stock Metric - Find & Replace Finish Good SKU")
        model = self.workbook_model("V2 Trending Safety Stock Metric GSD & BID.xlsx")
        pos = model.find_next(sku)
        self.step(f"Excel: Safety Stock metric lookup for {sku} -> {'found row ' + str(pos[0] + 1) if pos else 'not found'}")

    # --------------------------------------------------------------- driver
    def run_full_demo(self):
        """Single continuous pass, matching the recording's REAL structure
        (re-derived from the source graph's actual edges, not assumed) --
        NOT two repeats of the same sequence. The two materials play
        different roles:
          - sku1 (A42362): stock/batch checked, findings shared on Teams,
            then a brand-new SAP production order is created and printed.
          - sku2 (A35989C): stock/batch checked, then an EXISTING order
            already in the system is reviewed via Material Document List
            (the real "Review an other component?" loop -- see
            sap_matdoc_and_display's docstring -- lives here, not as a
            restart of the whole flow), findings shared on Teams again.
        Excel updates happen once at the end: sku1's new order populates a
        Production Tracker row, sku2's flagged status populates a CSAB row,
        and a single Safety Stock Metric lookup closes out the recording.
        See AUTOMATION_NOTES.md for the full re-derivation and why the
        earlier "run everything twice" version was wrong."""
        self.start_bot_progress()
        try:
            self.show_progress("Reading Teams for a SKU",
                                "The bot is checking Teams chat for messages flagging SKUs to look up.")
            self.step("=== Trigger: Teams message mentions a SKU to look up ===")
            sku1 = self.read_sku_from_teams("pending_sku")
            sku2 = self.read_sku_from_teams("second_sku")
            message1 = self.teams.data.outgoing_message_1
            message2 = self.teams.data.outgoing_message_2

            self.show_progress("Logging Into SAP", "The bot is signing into the LSG Production system in SAP.")
            self.run_login()

            # ---- Material 1: check stock, create a NEW production order ----
            self.step(f"\n--- Material 1/2: {sku1} (new production order) ---")
            self.show_progress(f"Checking Stock for {sku1}",
                                f"The bot is looking up stock and batch details for material {sku1} in SAP.")
            self.sap.current_material = sku1
            self.sap_stock_lookup(sku1)

            self.show_progress("Sharing Findings on Teams",
                                "The bot snipped the SAP stock overview and sent it to the team on Teams, "
                                "then read their reply.")
            self.teams_communicate_findings(sku1, message1)
            self.sap_open_second_window(sku1)

            self.show_progress(f"Checking JDE for {sku1}",
                                "The bot is looking up the item in JD Edwards to confirm it's active.")
            self.jde_lookup(sku1)

            self.show_progress("Opening Material Document",
                                f"The bot is opening the linked specification document for {sku1} in SAP.")
            self.sap_change_material_and_document(sku1, open_word=True)

            self.show_progress("Creating Production Order",
                                f"The bot is creating a new SAP production order for {sku1}.")
            order1 = self.sap_create_order(sku1)

            self.show_progress("Updating Production Order",
                                "The bot is changing and printing the production order in SAP.")
            self.sap_change_order_and_print(order1)

            # ---- Material 2: check stock, review an EXISTING order ----
            self.step(f"\n--- Material 2/2: {sku2} (review existing order) ---")
            self.show_progress(f"Checking Stock for {sku2}",
                                f"The bot is looking up stock and batch details for material {sku2} in SAP.")
            self.sap.current_material = sku2
            self.sap_stock_lookup(sku2)

            self.show_progress("Reviewing Material Document",
                                f"The bot is reviewing the existing production order on file for {sku2} in SAP, "
                                "checking whether there's another component to look at.")
            self.sap_matdoc_and_display(sku2)

            self.show_progress("Sharing Findings on Teams",
                                "The bot snipped the SAP stock overview and sent it to the team on Teams, "
                                "then read their reply.")
            self.teams_communicate_findings(sku2, message2)

            # ---- Spreadsheet updates: once each, for the right material ----
            self.show_progress("Updating Tracker Spreadsheets",
                                f"The bot is logging {sku1}'s new order in the Production Tracker, flagging "
                                f"{sku2}'s status on the Customer Service Alert Board, and checking the Safety "
                                "Stock Metric sheet.")
            self.excel_update_production_tracker(sku1)
            self.excel_update_csab(sku2)
            self.excel_touch_safety_stock_metric(sku2)

            self.show_progress("Done", "The bot finished processing both materials.")
            self.step("=== Stop ===")
            return self.summarize()
        finally:
            self.stop_bot_progress()

    def summarize(self):
        return {
            "log": list(self.log),
            "production_orders": dict(self.sap_data.production_orders),
            "teams_chat_thread": list(self.teams.data.chat_thread),
            "jde_last_result": self.jde.result,
            "word_opened": getattr(self, "_word_opened", False),
        }

    def close(self):
        self.stop_bot_progress()
        try:
            for w in list(SAPSession._windows):
                w.win.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def run(pace=0.0, visible=True):
    orch = Orchestrator(pace=pace, visible=visible)
    try:
        result = orch.run_full_demo()
    finally:
        pass
    return orch, result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pace", type=float, default=0.0)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    orch, result = run(pace=args.pace, visible=not args.headless)
    print(f"\n{len(result['log'])} steps logged.")
    print(f"Production orders created: {list(result['production_orders'].keys())}")
    print(f"Teams messages in thread: {len(result['teams_chat_thread'])}")
    print(f"JDE last result: {result['jde_last_result']}")
    print(f"Word opened: {result['word_opened']}")

    if args.keep_open and not args.headless:
        orch.root.mainloop()
    else:
        orch.close()
