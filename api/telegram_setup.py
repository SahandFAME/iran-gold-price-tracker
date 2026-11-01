from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler

from api.common import authorized, send_json
from gold_updater.telegram_api import telegram_api
from gold_updater.telegram_profile import sync_bot_profile


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not authorized(self.headers.get("Authorization"), "SETUP_SECRET"):
            send_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        secret = os.environ["TELEGRAM_WEBHOOK_SECRET"]
        host = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", "iran-gold-price-tracker.vercel.app")
        webhook_url = f"https://{host}/api/telegram"
        try:
            identity = telegram_api("getMe")
            webhook = telegram_api(
                "setWebhook",
                {
                    "url": webhook_url,
                    "secret_token": secret,
                    "allowed_updates": ["message", "callback_query"],
                    "drop_pending_updates": False,
                },
            )
            commands = telegram_api(
                "setMyCommands",
                {
                    "commands": [
                        {"command": "start", "description": "شروع و نمایش منوی اصلی"},
                        {"command": "report", "description": "نمایش گزارش تحلیلی طلا"},
                    ],
                    "language_code": "fa",
                },
            )
            profile_updated = sync_bot_profile()
            send_json(
                self,
                200,
                {
                    "ok": True,
                    "bot_username": (identity.get("result") or {}).get("username"),
                    "webhook": bool(webhook.get("ok")),
                    "commands": bool(commands.get("ok")),
                    "profile_updated": profile_updated,
                },
            )
        except Exception as error:
            print(f"Telegram setup failed: {type(error).__name__}: {error}", flush=True)
            send_json(self, 502, {"ok": False, "error": type(error).__name__})
