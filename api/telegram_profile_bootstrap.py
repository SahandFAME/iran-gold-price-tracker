from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api.common import send_json
from gold_updater.telegram_profile import sync_bot_profile


class handler(BaseHTTPRequestHandler):
    """One-release bootstrap route; removed immediately after profile installation."""

    def do_POST(self) -> None:
        try:
            send_json(self, 200, {"ok": True, "profile_updated": sync_bot_profile()})
        except Exception as error:
            print(f"Telegram profile bootstrap failed: {type(error).__name__}: {error}", flush=True)
            send_json(self, 502, {"ok": False, "error": type(error).__name__})
