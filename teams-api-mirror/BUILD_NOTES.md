# Fake Teams API — build notes

A local HTTP server (`server.py`, stdlib `http.server` only, no extra
dependencies) standing in for a real Microsoft Teams Bot/Graph API
integration. Used by the API-based demo variant
(`../automation/thermofisher_demo.teams_api.robot`) instead of the Teams
GUI mirror (`../teams-mirror/`) -- same underlying data, different
integration style: this one talks HTTP, the GUI one gets clicked through.

## Launch
`python3 server.py [port]` (default 8765). In the demo it's launched as
its own subprocess by `orchestrator.py`'s `TeamsApiClient` (same pattern
as the Bot Progress window: a separate process, not a thread).

## Endpoints
- `GET /sku` -> `{"pending_sku": "A42362", "second_sku": "A35989C"}`
- `GET /messages` -> `{"messages": [...]}` (full chat thread so far)
- `POST /messages` body `{"text": ..., "image_path": ...}` -> the created
  message (201)
- `POST /messages/deliver-reply` -> `{"reply": {...} | null}` -- delivers
  the canned reply if one is pending (mirrors the GUI mirror's
  `deliver_reply_if_pending`, called explicitly by the automation instead
  of waiting on a timer)

## Seed data
Reads `../teams-mirror/data/seed.json` directly -- the SAME file the GUI
mirror uses -- so both demo variants show identical SKUs/messages/replies.
Not a copy; if that seed file changes, both variants pick it up.

## Functional vs decorative
Everything here is functional -- there's no UI to have a decorative part.
The "narration" a human would get from watching the Teams GUI mirror
instead comes from the Bot Progress window in this variant (see
`TeamsApiClient` in `../automation/orchestrator.py`), since there's no
window to look at for this integration.

## Not built
No auth, no real Teams/Graph API shape (message envelope, thread IDs,
etc.) -- this mirrors just enough of "get the latest messages" / "send a
message" to demonstrate the API-vs-GUI architectural difference, not a
faithful Graph API mock.
