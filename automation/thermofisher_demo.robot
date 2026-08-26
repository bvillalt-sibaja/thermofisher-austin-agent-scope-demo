*** Settings ***
Documentation     Thermo Fisher Austin - Process Order/Sku Flow (Agent Scope) demo.
...               Replays the recorded process against 4 local mirror apps
...               (SAP GUI, Microsoft Teams, JD Edwards, Snipping Tool) plus
...               Excel-mirror workbooks and the real Word.app, for two
...               materials (the recording's "Review an other component?"
...               loop). See ../recorded_steps.json for the source recording
...               and BUILD_NOTES.md in each mirror app's directory for what
...               each one covers.
Library           ThermoFisherDemoLib.py

*** Variables ***
${PACE}           0.15
${VISIBLE}        ${TRUE}

*** Tasks ***
Run Thermo Fisher Agent Scope Demo
    ${result}=    Run Full Demo    pace=${PACE}    visible=${VISIBLE}
    Log    Production orders created: ${result}[production_orders]
    Log    Teams messages in thread: ${result}[teams_chat_thread]
    Log    JDE last result: ${result}[jde_last_result]
