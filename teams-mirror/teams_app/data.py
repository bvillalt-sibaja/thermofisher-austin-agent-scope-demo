import json
import os

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seed.json")
STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "session_state.json")


class DemoData:
    """In-memory demo state, seeded from data/seed.json. Resets on restart."""

    def __init__(self):
        with open(SEED_PATH) as f:
            seed = json.load(f)
        self.teams = seed["teams"]
        self.contacts = seed["contacts"]
        self.chat_thread = list(seed["chat_thread"])
        self.pending_sku = seed["pending_sku"]
        self.second_sku = seed["second_sku"]
        self.outgoing_message_1 = seed["outgoing_message_1"]
        self.outgoing_message_2 = seed["outgoing_message_2"]
        self.canned_reply = seed["canned_reply"]
        self._reply_pending = False
        self._write_state()

    def send_message(self, text, image_path=None):
        entry = {"sender": "me", "mine": True, "text": text}
        if image_path:
            entry["image"] = image_path
        self.chat_thread.append(entry)
        self._reply_pending = True
        self._write_state()

    def deliver_reply_if_pending(self):
        """Called after Send to simulate the other party replying (used by app.py on a short delay)."""
        if self._reply_pending:
            self.chat_thread.append({"sender": "Dominguez, Analisa", "mine": False, "text": self.canned_reply})
            self._reply_pending = False
            self._write_state()
            return True
        return False

    def _write_state(self):
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump(
                {
                    "pending_sku": self.pending_sku,
                    "second_sku": self.second_sku,
                    "chat_thread": self.chat_thread,
                    "last_message": self.chat_thread[-1] if self.chat_thread else None,
                },
                f,
                indent=2,
            )
