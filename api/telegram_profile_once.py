from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api.common import authorized, send_json
from gold_updater.telegram_profile import sync_bot_profile


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not authorized(self.headers.get("Authorization"), "CRON_SECRET"):
            send_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        try:
            send_json(self, 200, {"ok": True, "profile_updated": sync_bot_profile()})
        except Exception as error:
            print(f"Telegram profile cron failed: {type(error).__name__}: {error}", flush=True)
            send_json(self, 502, {"ok": False, "error": type(error).__name__})
