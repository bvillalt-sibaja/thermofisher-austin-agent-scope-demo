*** Settings ***
Documentation     Maker Player entry point for the Thermo Fisher Austin Agent
...               Scope demo. Maker Player only uploads this single .robot
...               file, not the sibling Python modules a local `robot` run
...               already has on disk (all 6 mirror apps + orchestration) --
...               so this version fetches them fresh from the public GitHub
...               repo at run time, then dynamically imports the library
...               (`Import Library`, not a static *** Settings *** Library
...               line -- that's parsed before any Suite Setup/Task code can
...               run, too early to point at a not-yet-cloned path).
...
...               Use ../automation/thermofisher_demo.robot instead for local
...               iteration on this Mac -- it imports the sibling files
...               directly, no network fetch, faster to run repeatedly. This
...               file is the one to upload to Maker Player.
...
...               Repo: https://github.com/bvillalt-sibaja/thermofisher-austin-agent-scope-demo
...               (public -- no credentials needed to clone it). See that
...               repo's automation/AUTOMATION_NOTES.md for what this task
...               actually does and each mirror app's own BUILD_NOTES.md for
...               what it covers.
...
...               NOT YET VERIFIED VIA A REAL MAKER PLAYER UPLOAD-AND-RUN --
...               only via a local `robot` run of this exact file (which
...               genuinely exercises the clone + dynamic-import mechanism,
...               just not Maker Player's own embedded runtime/PATH). Two
...               known open risks a real upload-and-run would catch that a
...               local run can't: (1) Maker Player's embedded Python runtime
...               may not have openpyxl/Pillow/python-docx installed --
...               these mirror apps need all three, and there's no dependency
...               manifest/provisioning step here to guarantee them; (2) `git`
...               itself must be on whatever machine's PATH runs this.
Library           Process
Library           OperatingSystem
Library           BuiltIn

*** Variables ***
${REPO_URL}       https://github.com/bvillalt-sibaja/thermofisher-austin-agent-scope-demo.git

*** Tasks ***
Run Thermo Fisher Agent Scope Demo
    ${repo_dir}=    Fetch Dependencies
    Import Library    ${repo_dir}/automation/ThermoFisherDemoLib.py
    ${result}=    Run Full Demo    pace=0.15    visible=${TRUE}
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
