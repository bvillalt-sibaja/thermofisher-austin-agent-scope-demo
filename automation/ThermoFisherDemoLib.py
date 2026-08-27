"""Robot Framework library wrapping the Thermo Fisher Austin 'Agent Scope'
demo orchestrator (orchestrator.py) as RF keywords."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import run as _run


class ThermoFisherDemoLib:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def run_full_demo(self, pace="0.0", visible=True, teams_mode="gui", gemini_api_key=""):
        """Runs the full two-material Agent Scope demo end to end against
        the 6 mirror apps/services + Excel workbooks. Returns a summary
        dict (production orders created, Teams chat thread, JDE result,
        etc.). `teams_mode`: "gui" drives the Teams mirror window (default);
        "api" talks to the fake Teams API server instead (no Teams window --
        that activity narrates through the Bot Progress window).
        `gemini_api_key`: if set, Gemini understands the incoming Teams
        request and composes the reply instead of using the scripted
        text -- falls back to scripted text automatically if empty or if
        any Gemini call fails."""
        orch, result = _run(pace=float(pace), visible=str(visible).lower() not in ("false", "0", "no"),
                             teams_mode=teams_mode, gemini_api_key=gemini_api_key)
        self._orch = orch
        return result

    def close_demo_windows(self):
        """Closes all mirror app windows opened by Run Full Demo."""
        if getattr(self, "_orch", None) is not None:
            self._orch.close()
