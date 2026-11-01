from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api.common import authorized, send_json
from gold_updater.microsoft import complete_device_authorization


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if not authorized(self.headers.get("Authorization"), "SETUP_SECRET"):
            send_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        try:
            result = complete_device_authorization()
            send_json(self, 200, {"ok": True, **result})
        except Exception as error:
            print(f"device authorization completion failed: {type(error).__name__}: {error}")
            send_json(self, 500, {"ok": False, "error": type(error).__name__})
