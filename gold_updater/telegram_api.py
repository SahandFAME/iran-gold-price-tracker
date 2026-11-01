from __future__ import annotations

import functools
import os
import urllib.parse

import httpx


@functools.lru_cache(maxsize=1)
def telegram_token() -> str:
    """Request the bot credential from Vercel Connect using project OIDC."""

    connector = urllib.parse.quote(os.environ["TELEGRAM_CONNECTOR"], safe="")
    response = httpx.post(
        f"https://api.vercel.com/v1/connect/token/{connector}",
        headers={"Authorization": f"Bearer {os.environ['VERCEL_OIDC_TOKEN']}"},
        json={"subject": {"type": "app"}},
        timeout=30,
    )
    response.raise_for_status()
    token = str(response.json().get("token") or "")
    if not token:
        raise RuntimeError("Vercel Connect returned no Telegram token")
    return token


def telegram_api(method: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    response = httpx.post(
        f"https://api.telegram.org/bot{telegram_token()}/{method}",
        json=payload or {},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram {method} failed")
    return result
