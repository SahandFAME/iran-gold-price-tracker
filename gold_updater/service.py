from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from .microsoft import get_access_token
from .tgju import TGJUTemporarilyUnavailable, fetch_tgju_highs
from .workbook import latest_workbook_date, update_workbook


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"


def _graph_request(path: str, token: str, *, method: str = "GET", data: bytes | None = None, headers=None) -> bytes:
    request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
    request = urllib.request.Request(GRAPH_ROOT + path, data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Graph {method} {path} failed with {error.code}: {detail}") from error


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _download_workbook(path: str, token: str) -> bytes:
    """Follow Graph's storage redirect without forwarding its bearer token."""

    request = urllib.request.Request(GRAPH_ROOT + path, headers={"Authorization": f"Bearer {token}"})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Graph download failed with {error.code}: {detail}") from error
        location = error.headers["Location"]
    else:
        raise RuntimeError("Graph content endpoint did not return a download redirect")

    with urllib.request.urlopen(location, timeout=180) as response:
        return response.read()


def run_daily_update(today: dt.date | None = None) -> dict[str, object]:
    today = today or dt.datetime.now(ZoneInfo("Asia/Tehran")).date()
    token = get_access_token()
    drive_id = urllib.parse.quote(os.environ["GRAPH_DRIVE_ID"], safe="")
    item_id = urllib.parse.quote(os.environ["GRAPH_ITEM_ID"], safe="")
    item_path = f"/drives/{drive_id}/items/{item_id}"

    metadata = json.loads(_graph_request(item_path + "?$select=eTag,name,size,lastModifiedDateTime", token))
    workbook = _download_workbook(item_path + "/content", token)
    price_source_status = "available"
    try:
        observations = fetch_tgju_highs(latest_workbook_date(workbook) - dt.timedelta(days=14))
    except TGJUTemporarilyUnavailable as error:
        # A source outage must not create a gap in the daily series. The
        # workbook updater carries the last price forward, and its rolling
        # reconciliation corrects recent fallback rows on a later run.
        observations = {}
        price_source_status = "temporarily_unavailable"
        print(f"TGJU temporarily unavailable; carrying price forward: {error}", flush=True)
    updated, audit = update_workbook(workbook, today, observations, reconcile_days=14)
    audit["source_etag"] = metadata["eTag"]
    audit["file_name"] = metadata["name"]
    audit["price_source_status"] = price_source_status

    if not audit["updated"]:
        return audit

    _graph_request(
        item_path + "/content",
        token,
        method="PUT",
        data=updated,
        headers={
            "Content-Type": "application/vnd.ms-excel.sheet.macroEnabled.12",
            "If-Match": metadata["eTag"],
        },
    )
    return audit
