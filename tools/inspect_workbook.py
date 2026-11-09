#!/usr/bin/env python3
"""Read-only, standard-library XLSM inspection for the project handoff."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


def inspect(path: Path, days: int = 14) -> dict[str, object]:
    sheet_ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    chart_ns = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
    epoch = dt.date(1899, 12, 30)
    with zipfile.ZipFile(path) as package:
        bad_part = package.testzip()
        if bad_part:
            raise ValueError(f"ZIP CRC failed: {bad_part}")
        tree = ET.fromstring(package.read("xl/worksheets/sheet1.xml"))
        numeric: dict[tuple[str, int], float] = {}
        date_rows: list[tuple[dt.date, int]] = []
        anchors = []
        for row in tree.findall("s:sheetData/s:row", sheet_ns):
            number = int(row.attrib["r"])
            for cell in row.findall("s:c", sheet_ns):
                coordinate = cell.attrib.get("r", "")
                match = re.fullmatch(r"([A-Z]+)\d+", coordinate)
                if not match:
                    continue
                value = cell.find("s:v", sheet_ns)
                if value is not None and value.text is not None and cell.attrib.get("t") not in {"s", "str", "e", "b"}:
                    try:
                        numeric[(match[1], number)] = float(value.text)
                    except ValueError:
                        pass
                formula = cell.find("s:f", sheet_ns)
                if formula is not None and formula.attrib.get("ref"):
                    anchors.append({"cell": coordinate, "range": formula.attrib["ref"], "formula": formula.text})
            if number >= 7 and ("C", number) in numeric and numeric.get(("D", number), 0) > 0:
                day = epoch + dt.timedelta(days=int(numeric[("C", number)]))
                date_rows.append((day, number))
        date_rows.sort()
        if not date_rows:
            raise ValueError("No dated positive price rows found")
        recent = []
        calculation_checks = []
        for day, row in date_rows[-days:]:
            recent.append({"date": day.isoformat(), "row": row, "values": {c: numeric.get((c, row)) for c in ("D", "E", "F", "G", "H", "I", "K", "L")}})
            expected = {}
            for column, window in {"E": 240, "I": 370, "K": 85, "L": 65}.items():
                values = [numeric.get(("D", r)) for r in range(row - window + 1, row + 1)]
                if all(v is not None for v in values):
                    expected[column] = sum(values) / window
            if "I" in expected:
                expected.update({"F": expected["I"] * 1.3, "G": expected["I"] * 1.6, "H": expected["I"] * 1.1})
            errors = {c: abs(numeric[(c, row)] - v) for c, v in expected.items() if (c, row) in numeric}
            calculation_checks.append({"row": row, "checked_columns": sorted(errors), "max_absolute_error": max(errors.values(), default=None)})
        charts = {}
        for name in sorted(package.namelist()):
            if re.fullmatch(r"xl/charts/chart\d+\.xml", name):
                chart = ET.fromstring(package.read(name))
                charts[name] = {
                    "numeric_references": [f.text for f in chart.findall(".//c:numRef/c:f", chart_ns)],
                    "cache_point_counts": [int(p.attrib["val"]) for p in chart.findall(".//c:ptCount", chart_ns)],
                }
        duplicates = sorted({day.isoformat() for day, _ in date_rows if sum(d == day for d, _ in date_rows) > 1})
        missing_recent = []
        available = {d for d, _ in date_rows}
        latest = date_rows[-1][0]
        for offset in range(days):
            day = latest - dt.timedelta(days=offset)
            if day not in available:
                missing_recent.append(day.isoformat())
        return {
            "file_name": path.name,
            "file_size_bytes": path.stat().st_size,
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "zip_integrity": "passed",
            "vba_present": "xl/vbaProject.bin" in package.namelist(),
            "vba_sha256": hashlib.sha256(package.read("xl/vbaProject.bin")).hexdigest() if "xl/vbaProject.bin" in package.namelist() else None,
            "last_date": latest.isoformat(),
            "last_row": date_rows[-1][1],
            "recent_rows": recent,
            "missing_recent_dates": missing_recent,
            "duplicate_dates": duplicates,
            "shared_formula_anchors": anchors,
            "calculation_checks": calculation_checks,
            "charts": charts,
            "scope": "Offline package inspection only; no TGJU comparison, macro execution or provider authentication.",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()
    if not 1 <= args.days <= 366:
        parser.error("--days must be between 1 and 366")
    print(json.dumps(inspect(args.workbook, args.days), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
