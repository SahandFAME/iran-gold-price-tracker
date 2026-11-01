from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api.common import send_json


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        send_json(self, 200, {"ok": True})
