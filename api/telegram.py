from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler

from api.common import send_json
from gold_updater.telegram_bot import handle_update


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        supplied = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        if not expected or not hmac.compare_digest(supplied, expected):
            send_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
            update = json.loads(self.rfile.read(length))
            handle_update(update)
            send_json(self, 200, {"ok": True})
        except Exception as error:
            print(f"Telegram update failed: {type(error).__name__}: {error}", flush=True)
            send_json(self, 500, {"ok": False, "error": type(error).__name__})
