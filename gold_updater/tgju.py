from __future__ import annotations

import datetime as dt
import time
import urllib.parse

import httpx


TGJU_URL = "https://api.tgju.org/v1/market/indicator/summary-table-data/geram18"
TGJU_LIVE_URLS = (
    "https://call2.tgju.org/ajax.json",
    "https://call3.tgju.org/ajax.json",
    "https://call1.tgju.org/ajax.json",
)


class TGJUTemporarilyUnavailable(RuntimeError):
    """Raised after retryable TGJU failures have exhausted their retries."""


def _fetch_page(
    client: httpx.Client,
    query: str,
    delays: tuple[int, ...] = (0, 2, 5, 10),
) -> dict[str, object]:
    last_error = "unknown error"
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            time.sleep(delay)
        try:
            response = client.get(TGJU_URL + "?" + query)
            if response.status_code == 429 or response.status_code >= 500:
                last_error = f"HTTP {response.status_code}"
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("TGJU returned a non-object JSON response")
            return payload
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            last_error = f"{type(error).__name__}: {error}"

    raise TGJUTemporarilyUnavailable(
        f"TGJU remained unavailable after {len(delays)} attempts ({last_error})"
    )


def fetch_tgju_highs(cutoff: dt.date) -> dict[dt.date, int]:
    """Fetch TGJU 18K-gold daily highs in toman through the present."""

    observations: dict[dt.date, int] = {}
    start = 0
    page_size = 200
    with httpx.Client(
        headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.tgju.org/profile/geram18/history",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
            },
        timeout=httpx.Timeout(60),
        follow_redirects=True,
    ) as client:
        while True:
            query = urllib.parse.urlencode(
                {
                    "lang": "fa",
                    "draw": 1,
                    "start": start,
                    "length": page_size,
                    "search": "",
                    "order_col": "timestamp",
                    "order_dir": "desc",
                    "convert_to_ad": 1,
                }
            )
            payload = _fetch_page(client, query)

            rows = payload.get("data", [])
            if not isinstance(rows, list):
                raise ValueError("TGJU response has no data list")
            if not rows:
                break

            oldest: dt.date | None = None
            for row in rows:
                day = dt.datetime.strptime(row[6], "%Y/%m/%d").date()
                oldest = day if oldest is None else min(oldest, day)
                # TGJU publishes rials; this workbook stores toman.
                observations[day] = int(row[2].replace(",", "")) // 10

            if oldest is not None and oldest <= cutoff:
                break
            start += len(rows)
            if start >= int(payload.get("recordsFiltered", 0)):
                break

    return observations


def fetch_latest_tgju_high() -> tuple[dt.date, int]:
    """Return TGJU's newest published 18K daily high with a short bot timeout."""

    query = urllib.parse.urlencode(
        {
            "lang": "fa",
            "draw": 1,
            "start": 0,
            "length": 10,
            "search": "",
            "order_col": "timestamp",
            "order_dir": "desc",
            "convert_to_ad": 1,
        }
    )
    with httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.tgju.org/profile/geram18/history",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
        },
        timeout=httpx.Timeout(12),
        follow_redirects=True,
    ) as client:
        payload = _fetch_page(client, query, delays=(0, 1))

    rows = payload.get("data", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("TGJU response has no price rows")
    newest = max(rows, key=lambda row: dt.datetime.strptime(row[6], "%Y/%m/%d"))
    day = dt.datetime.strptime(newest[6], "%Y/%m/%d").date()
    return day, int(newest[2].replace(",", "")) // 10


def fetch_current_tgju_price() -> int:
    """Return TGJU's live 18K-gold quote in toman."""

    last_error = "unknown error"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Didban-Tala-Sekke/1.0)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.tgju.org/",
    }
    with httpx.Client(headers=headers, timeout=httpx.Timeout(8), follow_redirects=True) as client:
        for url in TGJU_LIVE_URLS:
            try:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("TGJU live response is not an object")
                table = payload.get("current", payload)
                if not isinstance(table, dict):
                    raise ValueError("TGJU live response has no current table")
                item = table.get("geram18")
                if not isinstance(item, dict):
                    raise ValueError("TGJU live response has no geram18 item")
                raw_price = item.get("p")
                price_rial = int(str(raw_price).replace(",", ""))
                if price_rial <= 0:
                    raise ValueError("TGJU live price is not positive")
                return price_rial // 10
            except (httpx.HTTPError, TypeError, ValueError) as error:
                last_error = f"{type(error).__name__}: {error}"

    raise TGJUTemporarilyUnavailable(f"TGJU live quote is unavailable ({last_error})")
