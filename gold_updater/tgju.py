from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request


TGJU_URL = "https://api.tgju.org/v1/market/indicator/summary-table-data/geram18"


def fetch_tgju_highs(cutoff: dt.date) -> dict[dt.date, int]:
    """Fetch TGJU 18K-gold daily highs in toman through the present."""

    observations: dict[dt.date, int] = {}
    start = 0
    page_size = 200
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
        request = urllib.request.Request(
            TGJU_URL + "?" + query,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.tgju.org/profile/geram18/history",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read())

        rows = payload.get("data", [])
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
