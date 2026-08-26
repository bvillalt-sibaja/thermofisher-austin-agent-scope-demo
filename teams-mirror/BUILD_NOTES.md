# Microsoft Teams mirror — build notes

Launch: `cd ~/thermofisher-austin-demo/teams-mirror && python3 main.py`
Verified live 2026-08-26: window renders ("Microsoft Teams" title, pid confirmed via
`osascript`/System Events), headless functional check passed (send message -> canned
reply appears, channel/file navigation, event log).

## Layout
- Left icon rail: Chat / Teams (channels) — `rail_chat` / `rail_teams` buttons.
- **Chat view** (default on launch): contact list (`contact_dominguez`, `contact_warner`),
  message thread (`chat_thread` frame), attach button (`attach_button`, paperclip),
  message entry (`message_entry`), send button (`send_button`).
- **Teams/channels view**: team list (`team_general`, `team_csab`, `team_metrics_carpet`),
  tabs (`tab_posts`, `tab_shared`), file buttons named `file_<slug>` e.g.
  `file_production_tracker_2026`, `file_customer_service_alert_board_2026`.

## Functional vs decorative
- Functional: team/channel selection, Files/Shared tab + file-open buttons, chat send
  (appends message, auto-delivers a canned reply after 500ms), image attach (pulls the
  newest file from `~/thermofisher-austin-demo/snipping-tool-mirror/captures/*.png`).
- Decorative: "Announcements"/"Escalations"/other channel names, Posts tab content
  (static "No new posts").

## Automation hooks
Primary path (matches how the real RPA automation should drive it, per the skill's
own image/coordinate-based pattern): click through the named widgets above like any
other desktop app.

Convenience state file (optional, read-only mirror of app state — NOT required, just
faster than OCR for a demo): `~/thermofisher-austin-demo/teams-mirror/state/session_state.json`,
rewritten on every state change. Fields: `pending_sku` (first SKU, "A42362"),
`second_sku` (second component in the loop, "A35989C"), `chat_thread` (full message
list), `last_message`.

- **Reading "next SKU to look up"**: read `pending_sku` / `second_sku` from that state
  file, or read it visually off the chat bubble text in `chat_thread` widget (matches
  the recording's "Read: SKU Number in Teams" step — first message in the seeded thread
  literally says "can you check on SKU A42362?").
- **Sending a message + attaching an image**: type into `message_entry`, click
  `attach_button` first if an image should be attached (auto-pulls latest Snipping Tool
  capture), then click `send_button`. Seeded outgoing message text (for literal replay)
  is in `data/seed.json` as `outgoing_message_1`/`outgoing_message_2`.

## Visual fidelity pass (2026-08-26)
Reskinned to look much closer to real Microsoft Teams — purple/indigo rail
(`#2D2C4E` rail, `#6264A7` accent), drawn (not emoji) rail icons for
Chat/Teams via new `teams_app/icons.py` (PIL-rendered, cached), circular
avatar-initials icons for contacts and teams, rounded-rectangle chat bubbles
(Canvas-backed) with sender name + synthetic timestamp above each one and an
image-attachment chip below, and a proper underlined active-tab indicator
(Posts/Files) in the channels view. Pure reskin — no widget names, method
signatures, or the `state/session_state.json` shape changed. Re-ran the full
headless functional check (send -> reply, all widget-name lookups incl.
`rail_chat`/`rail_teams`/`contact_*`/`chat_thread`/`attach_button`/
`message_entry`/`send_button`/`team_*`/`tab_*`/`file_*`, state-file fields)
— all pass. Re-verified a real `python3 main.py` launch renders exactly 1 OS
window with no stderr. Confirmed `automation/orchestrator.py` doesn't
reference anything that changed (it drives Teams via `show_chat`/
`show_channels`/`select_team`/`show_tab`/`msg_entry`/`send`/`attach_image`
method calls, plus the two `file_*` widget names — all unchanged).

## Second visual fidelity pass (2026-08-26) — the real Teams shell chrome
The first pass reskinned colors/bubbles/icons but was still missing the
actual Teams window *shell* — a real screenshot showed a bare rail with
only 2 icons, no top command bar at all, no header actions, and a cramped
compose row. This pass adds what was structurally missing:
- **Top command bar** (`TeamsApp._build_topbar`, `app.py`): back/forward
  chevrons, a rounded search box, and settings/help/profile icons —
  entirely decorative (no automation hook targets this row).
- **Fuller rail**: a profile-avatar circle at top, Activity (decorative),
  **Chat**/**Teams** (functional, now with a real active-state toggle via
  `_set_rail_active` instead of relying on incidental Tk focus styling),
  Calendar/Calls/OneDrive (decorative), and Apps/+ pinned to the bottom —
  matches real Teams' icon order.
- **Chat header actions**: video/phone/more icons next to the contact name
  (decorative), plus a 1px divider under the header.
- **Rebuilt compose box** (`chat.py`): a bordered card containing a
  formatting toolbar row (B/I/U/link/list, decorative) above the input row
  (paperclip `attach_button` — fixed a broken-looking paperclip glyph that
  read as a squiggle at small sizes — `message_entry`, emoji/gif/sticker
  decorative icons, and a circular accent `send_button` with a paper-plane
  glyph, fixed mid-pass to point right instead of left). Previously this
  row was a single cramped line with an oddly-rendered attach icon and a
  text-only Send button.
- **Channels view**: team icons switched from the circular `avatar()` (same
  shape as a person/contact) to a new `square_avatar()` — real Teams uses
  rounded squares for teams, circles for people — and a decorative "+" was
  added to the end of the Posts/Files tab strip.
- Removed a harmless but sloppy duplicate `attach_image` method left over
  from the first pass (the second definition silently shadowed the first;
  same body either way, no behavior change).

Still a pure reskin — every widget `name=`, method signature, and the
`state/session_state.json` shape are unchanged. Verified: re-ran the full
headless functional check (all pass, thread length correct after send);
re-ran `automation/orchestrator.py` twice (before and after the send-icon
fix) end to end — same evidence both times (2 production orders, 7 Teams
messages, Word opened). Visually verified with real `screencapture -x`
screenshots of both the Chat and Teams/Files views (own-window region,
captured by PID-scoped bounds to avoid overlap with other on-screen
windows) — confirmed the top bar, full rail, header actions, and rebuilt
compose box all actually render as designed, not just "doesn't crash."

## Third pass (2026-08-26) — icon bugs found by actually looking at a screenshot
The second pass's own screenshot review missed a few real bugs that only
showed up on closer visual inspection (cropped/zoomed screenshots) after the
user flagged the overall look was still off in specific spots:
- **Profile avatar rendered as a blank white circle.** `icons.person_icon()`
  drew a white silhouette on a circle filled with its own `color` parameter,
  which both call sites (rail avatar, topbar avatar) left at the function's
  old default of `"#FFFFFF"` — white-on-white, invisible. Fixed by changing
  the default background to a themed purple (`#5B5FC7`); the silhouette
  itself is always white regardless.
- **Emoji/GIF/sticker compose icons were all literally the same "more"
  (•••) icon** — `chat.py` built `{k: icons.small_icon("more", ...) for k in
  ("emoji", "gif", "sticker")}`, a placeholder that was never replaced with
  real glyphs. Added actual `emoji` (smiley face), `gif` (bordered "GIF"
  text box), and `sticker` (rounded square with a folded corner) icon kinds
  to `icons.py` and wired each button to its own.
- **Phone/call icon took three attempts to read correctly at its actual
  16px render size**, each verified with a real cropped-and-zoomed
  `screencapture` before moving on: an arc-plus-tick-marks shape rendered
  as an unrecognizable crescent; a diagonal dumbbell (thick line + round
  end-caps) read as a link/connector icon; a rotated bow-tie/hourglass
  silhouette blurred into a blob at this size. Settled on a simple upright
  mobile-phone glyph (rounded-rect body + speaker notch), which stays crisp
  and unambiguous that small — a realistic diagonal handset silhouette
  needs more pixels than a 16px icon has to spare.
- **Send button rendered as a plain white/gray square, not the accent
  purple circle** — a macOS Aqua quirk: a `tk.Button` with only an image
  (no text) and explicit pixel `width=`/`height=` ignores its `bg` option
  entirely (confirmed live; the rail buttons' `bg` changes work fine, but
  those use `compound="top"` with a text label and no explicit pixel size —
  a different native rendering path). Fixed by baking the purple circle +
  white paper-plane into one composited image (`icons.send_button_icon`)
  instead of relying on the Button widget's own background fill.

All four fixes are pure icon/pixel changes — no widget name, method
signature, or state-file shape touched. Re-verified after each fix with a
real cropped `screencapture` (not just "the code looks right"), then a full
headless functional check and a complete `robot thermofisher_demo.robot`
run (PASS, 1 task) at the end.

## Fourth pass (2026-08-26) — rail striping bug (from a user screenshot)
The user's own screenshot of the rail showed a striped look: light-gray
blocks per icon separated by dark-navy bands, instead of a clean uniform
dark rail. Root cause: **every** rail item (`rail_btn`, including the two
functional `rail_chat`/`rail_teams`) was a `tk.Button` with a compound
image+text and `bg=theme.SIDEBAR_BG`/`SIDEBAR_ACTIVE` — the same macOS Aqua
bug already found and fixed on the send button (a native-themed Button
ignores its own `bg`), just not caught on the rail during the second pass's
own screenshot review. Fixed by rebuilding every rail item as a
`tk.Frame` + two `tk.Label`s (icon, text) instead of a `Button` — Frame/
Label backgrounds are respected reliably. The two functional items
(`rail_chat`/`rail_teams`) keep their exact widget names and get an
`.invoke = handler` attribute assigned directly (plain Python attribute
assignment on a Tk widget instance) so `mirror_driver.click()`'s
`w.invoke()` call keeps working exactly as it did against the old Button —
confirmed live. Also dropped the redundant text label under the trailing
"+" item (a "+" icon glyph followed by a "+" text label read as a visually
doubled "+ / +" in the same screenshot) so it's icon-only, matching real
Teams. Re-verified: rail `.invoke()` contract + send flow both pass
headlessly, a real cropped `screencapture` shows a clean unstriped rail
with the correct active-state highlight, and the full `robot
thermofisher_demo.robot` run still passes.

## Typing simulation (2026-08-26, automation-side change)
Not a Teams-mirror change, but affects how this app is driven: `set_entry`
in `~/thermofisher-austin-demo/automation/mirror_driver.py` now types
character-by-character (with a short pump+pause per keystroke) instead of
inserting a whole string in one shot, so a human watching the demo sees
the bot actually typing rather than text appearing all at once like a
paste. `orchestrator.py`'s Teams message-compose step was switched from a
direct `msg_entry.insert(0, message)` to `set_entry(self.teams,
"message_entry", message)` to pick this up — same `message_entry` widget,
now typed instead of pasted. No widget name or method signature changed.

## Open items / integration dependencies
- Screenshot attach depends on `snipping-tool-mirror` writing PNGs to
  `~/thermofisher-austin-demo/shared_state/latest_snip.png` (see
  `orchestrator.py`'s Snipping Tool integration) — if that path ever
  changes, update `chat.py:attach_image()`'s glob path to match.
- Two chat sends are recorded (steps 37-43 and 232-236, same "Communicate Findings"
  text pattern) — same UI flow handles both; no separate screen needed.
