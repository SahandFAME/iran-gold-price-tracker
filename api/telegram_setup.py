from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler

from api.common import authorized, send_json
from gold_updater.telegram_api import telegram_api


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not authorized(self.headers.get("Authorization"), "SETUP_SECRET"):
            send_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        secret = os.environ["TELEGRAM_WEBHOOK_SECRET"]
        host = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", "iran-gold-price-tracker.vercel.app")
        webhook_url = f"https://{host}/api/telegram"
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
        user_commands = [
            {"command": "start", "description": "شروع و نمایش منوی اصلی"},
            {"command": "report", "description": "نمایش گزارش تحلیلی طلا"},
        ]
        commands = telegram_api(
            "setMyCommands",
            {"commands": user_commands, "language_code": "fa"},
        )
        admin_commands = telegram_api(
            "setMyCommands",
            {
                "commands": user_commands
                + [{"command": "admin", "description": "داشبورد مدیریت"}],
                "scope": {"type": "chat", "chat_id": int(os.environ["TELEGRAM_ADMIN_ID"])},
                "language_code": "fa",
            },
        )
        ok = bool(
            identity.get("ok")
            and webhook.get("ok")
            and commands.get("ok")
            and admin_commands.get("ok")
        )
        send_json(
            self,
            200 if ok else 502,
            {
                "ok": ok,
                "bot_username": (identity.get("result") or {}).get("username"),
                "webhook": bool(webhook.get("ok")),
                "commands": bool(commands.get("ok")),
            },
        )
