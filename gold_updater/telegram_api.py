from __future__ import annotations

import asyncio
import functools
import os

import httpx
from vercel import connect


@functools.lru_cache(maxsize=1)
def telegram_token() -> str:
    """Request the bot credential from Vercel Connect using project OIDC."""

    return asyncio.run(
        connect.get_token(
            os.environ["TELEGRAM_CONNECTOR"],
            subject=connect.ConnectAppTokenSubject(),
        )
    )


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
