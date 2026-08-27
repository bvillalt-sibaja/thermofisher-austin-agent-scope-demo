*** Settings ***
Documentation     Maker Player entry point for the Thermo Fisher Austin Agent
...               Scope demo -- API-based Teams variant. Identical to
...               ../automation/thermofisher_demo.player.robot except for one
...               thing: Teams is integrated via a fake local Teams API
...               (../teams-api-mirror/server.py, real HTTP calls) instead of
...               driving the Teams GUI mirror (../teams-mirror/). There's no
...               Teams window in this variant -- every "get latest messages" /
...               "send message" call instead narrates itself through the Bot
...               Progress window, since that's the only place a human
...               watching this variant can see that activity happening.
...               Every other system (SAP GUI, JDE, Snipping Tool, Excel,
...               Word) is unchanged and still a GUI mirror.
...
...               Same fetch-from-GitHub-at-runtime mechanism as
...               thermofisher_demo.player.robot (Maker Player only uploads
...               this single file, not its sibling Python modules) -- see
...               that file's own Documentation for the full explanation of
...               why (dynamic Import Library, the Variables-table
...               ${OUTPUT_DIR} gotcha, the "--depth 1" argument-parsing
...               gotcha). This file only differs in the one line that calls
...               Run Full Demo with teams_mode=api.
...
...               Repo: https://github.com/bvillalt-sibaja/thermofisher-austin-agent-scope-demo
...               (public -- no credentials needed to clone it). See
...               automation/AUTOMATION_NOTES.md and teams-api-mirror/BUILD_NOTES.md
...               in that repo for what this variant actually does.
Library           Process
Library           OperatingSystem
Library           BuiltIn

*** Variables ***
${REPO_URL}       https://github.com/bvillalt-sibaja/thermofisher-austin-agent-scope-demo.git

*** Tasks ***
Run Thermo Fisher Agent Scope Demo (Teams via API)
    ${repo_dir}=    Fetch Dependencies
    Import Library    ${repo_dir}/automation/ThermoFisherDemoLib.py
    ${result}=    Run Full Demo    pace=0.4    visible=${TRUE}    teams_mode=api
    Log    Production orders created: ${result}[production_orders]
    Log    Teams messages in thread: ${result}[teams_chat_thread]
    Log    JDE last result: ${result}[jde_last_result]

*** Keywords ***
Fetch Dependencies
    [Documentation]    Shallow-clones the dependency repo into a scratch dir
    ...    under ${OUTPUT_DIR}, resolved here inside the keyword rather than
    ...    declared as a *** Variables *** default referencing ${OUTPUT_DIR}
    ...    -- Maker Player replays every declared Variables-table scalar back
    ...    as a --variable override using its own RAW SOURCE TEXT, so a
    ...    default like "${OUTPUT_DIR}/x" would come back as the literal,
    ...    unexpanded string "${OUTPUT_DIR}/x" (a documented gotcha -- see
    ...    build-rpa-automation.md section 10/11, same class of bug already
    ...    hit and fixed for the Bot Progress window's own state/script
    ...    paths). Re-clones into a fresh directory every run rather than
    ...    reusing/pulling an existing checkout, so a run always gets the
    ...    latest pushed code with no stale-dependency risk.
    ${repo_dir}=    Set Variable    ${OUTPUT_DIR}/thermofisher-austin-agent-scope-demo
    Run Keyword And Ignore Error    Remove Directory    ${repo_dir}    recursive=${TRUE}
    # "--depth=1" (one token) would be misparsed by Process as one of its own
    # config options (cwd=/shell=/etc, its own convention for extra settings
    # via positional args) rather than reaching git at all -- same class of
    # bug already hit and documented for the Bot Progress window's Tk-version
    # probe (build-rpa-automation.md section 10). Space-separated avoids it.
    ${result}=    Run Process    git    clone    --depth    1    ${REPO_URL}    ${repo_dir}
    Should Be Equal As Integers    ${result.rc}    0    msg=git clone failed: ${result.stderr}
    RETURN    ${repo_dir}
