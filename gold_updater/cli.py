from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from .tgju import fetch_tgju_highs
from .workbook import latest_workbook_date, update_workbook


def _write_atomic(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(contents)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Update the 18K-gold macro workbook from TGJU")
    parser.add_argument("workbook", type=Path, help="Downloaded source .xlsm file")
    parser.add_argument("--output", type=Path, required=True, help="Destination .xlsm file")
    parser.add_argument("--audit-file", type=Path, help="Write the JSON audit to this path")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, help="Override today's Tehran date")
    args = parser.parse_args()

    source = args.workbook.read_bytes()
    today = args.as_of or dt.datetime.now(ZoneInfo("Asia/Tehran")).date()
    observations = fetch_tgju_highs(latest_workbook_date(source) - dt.timedelta(days=14))
    updated, audit = update_workbook(source, today, observations, reconcile_days=14)
    _write_atomic(args.output, updated)

    serialized = json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.audit_file:
        _write_atomic(args.audit_file, serialized.encode())
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
