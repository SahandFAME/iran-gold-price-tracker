from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api.common import authorized, send_json
from gold_updater.service import run_daily_update


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not authorized(self.headers.get("Authorization"), "CRON_SECRET", "SETUP_SECRET"):
            send_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        try:
            send_json(self, 200, {"ok": True, **run_daily_update()})
        except Exception as error:
            print(f"daily update failed: {type(error).__name__}: {error}")
            send_json(self, 500, {"ok": False, "error": type(error).__name__})
