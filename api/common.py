from __future__ import annotations

import hmac
import json
import os


def authorized(value: str | None, *environment_keys: str) -> bool:
    if not value or not value.startswith("Bearer "):
        return False
    supplied = value.removeprefix("Bearer ")
    return any(
        expected and hmac.compare_digest(supplied, expected)
        for expected in (os.environ.get(key, "") for key in environment_keys)
    )


def send_json(handler, status: int, value: dict[str, object]) -> None:
    payload = json.dumps(value, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(payload)
