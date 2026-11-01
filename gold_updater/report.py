from __future__ import annotations

import json
import os
import urllib.parse

from .microsoft import get_access_token
from .service import _download_workbook, _graph_request
from .tgju import TGJUTemporarilyUnavailable, fetch_current_tgju_price
from .workbook import latest_workbook_snapshot


REPORT_FIELDS = (
    ("E", "قیمت آربیتراژی", "خرید چشم بسته که معمولاً در صورت دیده شدن بسیار کوتاه مدت خواهد بود"),
    ("F", "قیمت تعادلی جاری", "قیمت منصفانه فعلی"),
    ("G", "کران محاسباتی بالا", "قیمتی که حباب خیلی بالا است و ارزش خرید در مقطع کنونی ندارد"),
    ("I", "کف محاسباتی", "پایین ترین قیمتی که در مقطع کنونی میتوان متصور شد"),
    ("L", "قیمت حرکت چرخه ای", "قیمتی که معمولاً در صورت دیده شدن از همانجا یا کمی پایینتر قیمت برمیگردد"),
)


def get_report_data() -> dict[str, object]:
    token = get_access_token()
    drive_id = urllib.parse.quote(os.environ["GRAPH_DRIVE_ID"], safe="")
    item_id = urllib.parse.quote(os.environ["GRAPH_ITEM_ID"], safe="")
    item_path = f"/drives/{drive_id}/items/{item_id}"
    metadata = json.loads(_graph_request(item_path + "?$select=eTag,name", token))
    workbook = _download_workbook(item_path + "/content", token)
    snapshot = latest_workbook_snapshot(workbook)

    tgju: dict[str, object]
    try:
        price = fetch_current_tgju_price()
        tgju = {"available": True, "price_toman": price}
    except TGJUTemporarilyUnavailable:
        tgju = {"available": False}

    return {
        "tgju": tgju,
        "workbook": snapshot,
        "file_name": metadata["name"],
    }
