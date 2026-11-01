from __future__ import annotations

import asyncio
import functools
import logging
import os

import httpx
from vercel import connect


# Telegram places the bot credential in the request path. The default HTTPX
# INFO log would therefore disclose it in function logs.
logging.getLogger("httpx").setLevel(logging.WARNING)


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
    try:
        result = response.json()
    except ValueError:
        result = {}
    if not response.is_success or not result.get("ok"):
        description = str(result.get("description") or "provider error")
        raise RuntimeError(f"Telegram {method} failed ({response.status_code}): {description}")
    return result
