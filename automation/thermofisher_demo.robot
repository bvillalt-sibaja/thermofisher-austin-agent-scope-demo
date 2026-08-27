*** Settings ***
Documentation     Thermo Fisher Austin - Process Order/Sku Flow (Agent Scope) demo.
...               Replays the recorded process (../recorded_steps.json) as one
...               continuous pass against 6 from-scratch local mirror apps --
...               A42362 gets a new SAP production order created, A35989C gets
...               an existing one reviewed (the recording's real "Review an
...               other component?" loop -- see sap_matdoc_and_display's
...               docstring in orchestrator.py) -- then Excel/Word/JDE/Teams
...               get updated accordingly. See ../automation/AUTOMATION_NOTES.md
...               for the full structural re-derivation.
...
...               Full source (all 6 mirror apps + this automation) is hosted at:
...               https://github.com/bvillalt-sibaja/thermofisher-austin-agent-scope-demo
...               (private repo). Dependency locations within it:
...               - SAP GUI mirror:        sap-mirror/          (sap-mirror/BUILD_NOTES.md)
...               - Microsoft Teams mirror: teams-mirror/        (teams-mirror/BUILD_NOTES.md)
...               - JD Edwards mirror:      jde-mirror/           (BUILD_NOTES_jde_snipping.md)
...               - Snipping Tool mirror:   snipping-tool-mirror/ (BUILD_NOTES_jde_snipping.md)
...               - Excel mirror + seeds:   excel-mirror/, seed-files/ (excel-mirror/BUILD_NOTES.md)
...               - Word mirror:            word-mirror/          (word-mirror/BUILD_NOTES.md)
...               - This orchestration:     automation/           (automation/AUTOMATION_NOTES.md)
...               Clone the repo to get every dependency this task imports (see
...               the sys.path.insert calls at the top of orchestrator.py) --
...               they're plain local Python imports, not fetched at run time.
Library           ThermoFisherDemoLib.py

*** Variables ***
${PACE}           0.4
${VISIBLE}        ${TRUE}

*** Tasks ***
Run Thermo Fisher Agent Scope Demo
    ${result}=    Run Full Demo    pace=${PACE}    visible=${VISIBLE}
    Log    Production orders created: ${result}[production_orders]
    Log    Teams messages in thread: ${result}[teams_chat_thread]
    Log    JDE last result: ${result}[jde_last_result]
