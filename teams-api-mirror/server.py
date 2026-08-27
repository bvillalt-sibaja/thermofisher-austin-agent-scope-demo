"""Fake Teams API server -- a local HTTP stand-in for a real Microsoft
Teams Bot/Graph API integration, used by the API-based demo variant
(thermofisher_demo.teams_api.robot) instead of driving the Teams GUI
mirror (teams-mirror/). Exposes REST-like endpoints over plain stdlib
http.server, so the automation makes genuine HTTP calls (see
orchestrator.py's TeamsApiClient) -- the whole point of this variant is
to demonstrate calling an API instead of clicking through a UI, so a
Python-function-call simulation wouldn't actually show that.

Seeded from the SAME data the Teams GUI mirror uses
(../teams-mirror/data/seed.json), so both demo variants show identical
SKUs/messages/replies -- only HOW the bot gets/sends them differs.

Endpoints:
  GET  /sku                     -> {"pending_sku": ..., "second_sku": ...}
  GET  /messages                -> {"messages": [...]}  (full chat thread so far)
  POST /messages                body {"text": ..., "image_path": ...} -> the created message (201)
  POST /messages/deliver-reply  -> delivers the canned reply if one is pending -> {"reply": {...} | null}

Standalone usage: `python3 server.py <port>` (default 8765), Ctrl+C to stop.
"""
import http.server
import json
import os
import socketserver
import sys

SEED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "teams-mirror", "data", "seed.json",
)


class ApiState:
    def __init__(self):
        with open(SEED_PATH) as f:
            seed = json.load(f)
        self.chat_thread = list(seed["chat_thread"])
        self.pending_sku = seed["pending_sku"]
        self.second_sku = seed["second_sku"]
        self.canned_reply = seed["canned_reply"]
        self._reply_pending = False

    def send_message(self, text, image_path=None):
        entry = {"sender": "me", "mine": True, "text": text}
        if image_path:
            entry["image"] = image_path
        self.chat_thread.append(entry)
        self._reply_pending = True
        return entry

    def deliver_reply_if_pending(self):
        if self._reply_pending:
            entry = {"sender": "Dominguez, Analisa", "mine": False, "text": self.canned_reply}
            self.chat_thread.append(entry)
            self._reply_pending = False
            return entry
        return None


STATE = ApiState()


class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/sku":
            self._json({"pending_sku": STATE.pending_sku, "second_sku": STATE.second_sku})
        elif self.path == "/messages":
            self._json({"messages": STATE.chat_thread})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        if self.path == "/messages":
            entry = STATE.send_message(payload.get("text", ""), payload.get("image_path"))
            self._json(entry, 201)
        elif self.path == "/messages/deliver-reply":
            entry = STATE.deliver_reply_if_pending()
            self._json({"reply": entry})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        pass  # keep stdout clean -- the orchestrator narrates calls via the Bot Progress window instead


class Server(socketserver.TCPServer):
    # Without this, the OS holds the port in TIME_WAIT for a while after
    # the previous run's server closes it, and a demo run started shortly
    # after fails with "Address already in use" even though no process is
    # actually still holding the port (confirmed live via `lsof`) -- plain
    # TCPServer defaults this to False; HTTPServer sets it True, but this
    # uses the plainer TCPServer base.
    allow_reuse_address = True


def main(port):
    with Server(("127.0.0.1", port), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
