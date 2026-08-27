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
import time
import urllib.error
import urllib.request


import tkinter as tk


def _tcl_tk_candidates(vendor_dir):
    """Yields (tcl_dir, tk_dir) pairs to try, in order. `tk_dir` may be
    None if no matching Tk library was found alongside a given Tcl one.

    Needed specifically for Maker Player's embedded Python runtime:
    confirmed live (two real upload-and-run attempts), it ships the
    `tkinter`/`_tkinter` C extension but not a matching Tcl/Tk script
    library. Two distinct failures were hit in sequence:
    1. No TCL_LIBRARY configured at all -> `Can't find a usable init.tcl`
       (Tk can't initialize whatsoever -- different and more severe than
       the already-documented "macOS system Tcl/Tk 8.5 renders blank
       windows" gotcha in the `rpa` plugin's Bot Progress window template,
       where Tk at least initializes).
    2. Pointed at a real but WRONG-VERSION Tcl/Tk (Homebrew 8.6.18) ->
       still `Can't find a usable init.tcl`, this time because a stock
       `init.tcl` does `package require -exact Tcl 8.6.12` and refuses
       any other 8.6.x point release. Maker Player's compiled `_tkinter`
       needs exactly 8.6.12, confirmed from its own error output.
    Neither is fixable with `pip install` -- Tcl's script library isn't a
    Python package. `vendor/tcl8.6` + `vendor/tk8.6` (this same directory)
    are a vendored, license-included copy of the exact 8.6.12 release
    (https://github.com/tcltk/tcl and .../tk, tag core-8-6-12) pulled in
    specifically as a guaranteed-version-matched fallback, since nothing
    here can otherwise guarantee that exact point release exists on
    whatever machine actually runs this.

    Ordered so anything already configured, then a modern system-installed
    Tcl/Tk, gets tried before the vendored exact-match fallback -- a local
    `robot` run on a machine with its own working Tcl/Tk (this dev Mac's
    rpa-env uses Homebrew 8.6.x) should never need the vendored copy at
    all. Ancient macOS system Tcl 8.5 is included last (initializes but
    renders zero widget content, confirmed elsewhere) -- better than a
    hard crash if every other candidate fails."""
    seen = set()

    def dedup(tcl_dir):
        if tcl_dir in seen or not os.path.isfile(os.path.join(tcl_dir, "init.tcl")):
            return None
        seen.add(tcl_dir)
        tk_dir = tcl_dir.replace("tcl8.", "tk8.").replace("Tcl.framework", "Tk.framework")
        return (tcl_dir, tk_dir if os.path.isdir(tk_dir) else None)

    existing = os.environ.get("TCL_LIBRARY")
    if existing:
        c = dedup(existing)
        if c:
            yield c

    for tcl_dir in (
        glob.glob("/opt/homebrew/opt/tcl-tk/lib/tcl8.*") +
        glob.glob("/opt/homebrew/Cellar/tcl-tk*/*/lib/tcl8.*") +
        glob.glob("/usr/local/opt/tcl-tk/lib/tcl8.*") +
        glob.glob("/usr/local/Cellar/tcl-tk*/*/lib/tcl8.*") +
        glob.glob("/Library/Frameworks/Python.framework/Versions/3.*/lib/tcl8.*")
    ):
        c = dedup(tcl_dir)
        if c:
            yield c

    c = dedup(os.path.join(vendor_dir, "tcl8.6"))
    if c:
        yield c

    for tcl_dir in glob.glob("/System/Library/Frameworks/Tcl.framework/Versions/*/Resources/Scripts"):
        c = dedup(tcl_dir)
        if c:
            yield c


def _create_tk_root(vendor_dir):
    """Tries each Tcl/Tk candidate in order, actually attempting a real
    `tk.Tk()` for each one (not just checking a file exists) until one
    works, returning the first successful root.

    Retries IN-PROCESS rather than via a subprocess probe -- confirmed
    empirically safe (a failed/version-mismatched `tk.Tk()` attempt does
    not corrupt the process for a later successful one, tested against
    both a nonexistent path and a deliberately version-mismatched
    init.tcl). Deliberately does NOT spawn a subprocess to validate a
    candidate first: this project's own Bot Progress window template
    already documents, from a real reverted attempt, that re-invoking
    `sys.executable` under Maker Player's embedded runner can kill the
    entire execution ("Execution cancelled or timed out; embedded Python
    runtime was terminated") -- not a safe technique to reuse here, and a
    probe run under some OTHER interpreter wouldn't actually validate
    compatibility with THIS process's own compiled `_tkinter` anyway."""
    last_error = None
    for tcl_dir, tk_dir in _tcl_tk_candidates(vendor_dir):
        os.environ["TCL_LIBRARY"] = tcl_dir
        if tk_dir:
            os.environ["TK_LIBRARY"] = tk_dir
        elif "TK_LIBRARY" in os.environ:
            del os.environ["TK_LIBRARY"]
        try:
            return tk.Tk()
        except tk.TclError as e:
            last_error = e
            continue
    # Every candidate failed (or none were found) -- fall through to
    # whatever's compiled-in/already configured, so a genuine remaining
    # problem surfaces as its own real error rather than being masked.
    if last_error:
        raise last_error
    return tk.Tk()

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


class TeamsApiClient:
    """Stands in for the Teams GUI mirror in the API-based demo variant
    (thermofisher_demo.teams_api.robot): talks to the fake Teams API
    server (../teams-api-mirror/server.py, launched as its own subprocess
    -- same pattern as the Bot Progress window, a separate process rather
    than a thread) over real HTTP instead of clicking through a chat
    window. There's no window for a human to watch here, so every call
    narrates itself through the Bot Progress window (`show_progress`)
    instead -- that's the whole point of this variant: showing what
    "integrate via API" looks like versus "automate the UI", side by side
    with the GUI version.

    Talks plain `urllib.request` (stdlib, no extra dependency) rather than
    `RPA.HTTP` -- this class is plain Python driven from Python
    (orchestrator.py), not Robot Framework keywords, so pulling in an RF
    library here would be backwards; the .robot task itself only ever
    calls the single `Run Full Demo` keyword, same as every other variant."""

    def __init__(self, base_url, show_progress, step):
        self.base_url = base_url
        self._show_progress = show_progress
        self._step = step

    def _get(self, path):
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=10) as r:
            return json.loads(r.read())

    def _post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def wait_until_ready(self, timeout=10):
        deadline = time.time() + timeout
        last_error = None
        while time.time() < deadline:
            try:
                self._get("/sku")
                return
            except (urllib.error.URLError, ConnectionError) as e:
                last_error = e
                time.sleep(0.2)
        raise RuntimeError(f"Teams API server never came up: {last_error}")

    def read_sku(self, which):
        self._show_progress("Calling Teams API", "GET /sku -- checking for a SKU to look up.")
        self._step("Teams API: GET /sku")
        sku = self._get("/sku")[which]
        self._step(f"Teams API: {which} -> {sku}")
        return sku

    def send_message(self, text, image_path=None):
        preview = text if len(text) <= 60 else text[:57] + "..."
        self._show_progress("Calling Teams API", f'POST /messages -- sending: "{preview}"')
        self._step(f"Teams API: POST /messages (text={text!r}, image_path={image_path!r})")
        self._post("/messages", {"text": text, "image_path": image_path})
        self._show_progress("Reading Teams API Reply", "POST /messages/deliver-reply -- checking for a response.")
        result = self._post("/messages/deliver-reply", {})
        reply = result.get("reply")
        reply_text = reply["text"] if reply else None
        self._step(f"Teams API: reply -> {reply_text!r}")
        return reply_text


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
    def __init__(self, pace=0.0, visible=True, teams_mode="gui"):
        if teams_mode not in ("gui", "api"):
            raise ValueError(f"teams_mode must be 'gui' or 'api', got {teams_mode!r}")
        self.pace = pace
        self.visible = visible
        self.teams_mode = teams_mode
        self.log = []
        sap_popups.confirm_dialog = _auto_confirm
        sap_screens.confirm_dialog = _auto_confirm

        self.root = _create_tk_root(os.path.join(AUTOMATION_DIR, "vendor"))  # this IS the primary SAP window
        self.root.title("SAP Easy Access - Session 1")
        if not visible:
            self.root.withdraw()
        self.sap_data = SAPData()
        self.sap = SAPSession(self.root, self.sap_data, start_screen="LOGIN_SELECT")

        self.teams = None
        self.teams_api = None
        self._teams_api_proc = None
        if teams_mode == "gui":
            self.teams = TeamsApp(self.root)
            self.teams.open_excel_file = self._open_excel_via_teams  # bypass subprocess spawn
        else:
            self._start_teams_api()

        # Both modes need the seed data (outgoing message text) -- the GUI
        # mirror wraps it in TeamsApp.data, the API client's own server
        # reads the same file independently, so just load it directly here
        # rather than adding a third way to reach it.
        seed_path = os.path.join(DEMO_ROOT, "teams-mirror", "data", "seed.json")
        with open(seed_path) as f:
            self._teams_seed = json.load(f)

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

    def _start_teams_api(self):
        """Launches the fake Teams API server as its own OS process (same
        pattern as the Bot Progress window -- a real separate process, not
        a thread, so this is a genuine local HTTP service the automation
        calls into, not an in-process shortcut) and waits for it to accept
        connections before returning."""
        server_script = os.path.join(DEMO_ROOT, "teams-api-mirror", "server.py")
        port = 8765
        self._teams_api_proc = subprocess.Popen([sys.executable, server_script, str(port)])
        self.teams_api = TeamsApiClient(f"http://127.0.0.1:{port}", self.show_progress, self.step)
        self.teams_api.wait_until_ready()

    def _stop_teams_api(self):
        if self._teams_api_proc is not None:
            try:
                self._teams_api_proc.terminate()
                self._teams_api_proc.wait(timeout=3)
            except Exception:
                pass
            self._teams_api_proc = None

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
        if self.teams_mode == "api":
            return self.teams_api.read_sku(which)
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
        self.step("Snipping Tool: New Snip over Stock Overview")
        self.snip.new_snip()
        self.snip.set_mode("shapes")
        self.snip.save_and_handoff()
        snip_path = os.path.join(DEMO_ROOT, "shared_state", "latest_snip.png")

        if self.teams_mode == "api":
            return self.teams_api.send_message(message, image_path=snip_path)

        self._focus(self.teams)
        self.teams.show_chat()
        self._pump()
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

    def _open_shared_excel_file(self, fname, team_name, file_widget):
        """Opens an Excel-mirror window for a file 'shared' in Teams.
        GUI mode clicks through the Teams window to get there (matching
        the recording); API mode has no Teams window to click through, so
        it calls the fake Teams API for the file reference instead and
        opens the Excel mirror directly -- narrated via Bot Progress since
        there's nothing on screen to show that step happening."""
        if self.teams_mode == "api":
            self.show_progress("Calling Teams API", f"GET shared file reference for {fname}.")
            self.step(f"Teams API: fetched shared file reference for {fname}")
            self._open_excel_via_teams(fname)
            return
        self._focus(self.teams)
        self.step(f"Teams: open {fname} (Shared files)")
        self.teams.show_channels()
        self.teams.channels_screen.select_team(team_name)
        self.teams.channels_screen.show_tab("files")
        click(self.teams, file_widget)

    def excel_update_production_tracker(self, sku):
        self._open_shared_excel_file("Production Tracker 2026.xlsx", "General", "file_production_tracker_2026")

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
        self._open_shared_excel_file(
            "Customer Service Alert Board 2026.xlsx", "CSAB", "file_customer_service_alert_board_2026")

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
            message1 = self._teams_seed["outgoing_message_1"]
            message2 = self._teams_seed["outgoing_message_2"]

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
            self._stop_teams_api()

    def summarize(self):
        if self.teams_mode == "api":
            chat_thread = self.teams_api._get("/messages")["messages"]
        else:
            chat_thread = list(self.teams.data.chat_thread)
        return {
            "log": list(self.log),
            "production_orders": dict(self.sap_data.production_orders),
            "teams_chat_thread": chat_thread,
            "jde_last_result": self.jde.result,
            "word_opened": getattr(self, "_word_opened", False),
        }

    def close(self):
        self.stop_bot_progress()
        self._stop_teams_api()
        try:
            for w in list(SAPSession._windows):
                w.win.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def run(pace=0.0, visible=True, teams_mode="gui"):
    orch = Orchestrator(pace=pace, visible=visible, teams_mode=teams_mode)
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
    parser.add_argument("--teams-mode", choices=["gui", "api"], default="gui")
    args = parser.parse_args()

    orch, result = run(pace=args.pace, visible=not args.headless, teams_mode=args.teams_mode)
    print(f"\n{len(result['log'])} steps logged.")
    print(f"Production orders created: {list(result['production_orders'].keys())}")
    print(f"Teams messages in thread: {len(result['teams_chat_thread'])}")
    print(f"JDE last result: {result['jde_last_result']}")
    print(f"Word opened: {result['word_opened']}")

    if args.keep_open and not args.headless:
        orch.root.mainloop()
    else:
        orch.close()
