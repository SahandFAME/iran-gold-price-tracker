from __future__ import annotations

import json
import os
import urllib.parse

from .microsoft import get_access_token
from .service import _download_workbook, _graph_request
from .tgju import TGJUTemporarilyUnavailable, fetch_latest_tgju_high
from .workbook import latest_workbook_snapshot


REPORT_FIELDS = (
    ("E", "خط آربیتراژی (میانگین ۲۴۰ روزه)", "میانگین بلندمدت برای سنجش فاصله قیمت بازار از روند آربیتراژی."),
    ("F", "تعادلی جاری", "برآورد سطح تعادلی جاری بر پایه ۱٫۳ برابر میانگین ۳۷۰ روزه."),
    ("G", "کران محاسباتی بالا", "برآورد سقف محاسباتی بر پایه ۱٫۶ برابر میانگین ۳۷۰ روزه."),
    ("H", "ارزش حدودی مقطعی", "برآورد کوتاه‌مدت بر پایه ۱٫۱ برابر میانگین ۳۷۰ روزه."),
    ("I", "میانگین متحرک ۳۷۰ روزه (کف محاسباتی)", "نمایی از روند بسیار بلندمدت و کف محاسباتی مدل."),
    ("K", "میانگین ۸۵ روزه (حرکت چرخه‌ای ۲)", "میانگین میان‌مدت برای مشاهده چرخه دوم حرکت قیمت."),
    ("L", "میانگین ۶۵ روزه (حرکت چرخه‌ای)", "میانگین کوتاه‌تر برای مشاهده تغییرات چرخه‌ای قیمت."),
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
        day, price = fetch_latest_tgju_high()
        tgju = {"available": True, "date": day.isoformat(), "price_toman": price}
    except TGJUTemporarilyUnavailable:
        tgju = {"available": False}

    return {
        "tgju": tgju,
        "workbook": snapshot,
        "file_name": metadata["name"],
    }
