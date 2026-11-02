from __future__ import annotations

import datetime as dt
import hashlib
import html
import io
import re
import zipfile
from dataclasses import dataclass


MAIN_SHEET = "xl/worksheets/sheet1.xml"
WORKBOOK_XML = "xl/workbook.xml"
VBA_PROJECT = "xl/vbaProject.bin"
VALUE_COLUMNS = ("C", "D", "E", "F", "G", "H", "I", "K", "L")
FORMULA_SI = {"I": 421, "E": 422, "F": 423, "G": 424, "H": 425, "K": 426, "L": 427}
CELL_STYLE = {"C": 8, "D": 12, "E": 15, "F": 20, "G": 21, "H": 22, "I": 23, "K": 24, "L": 25}
EXCEL_EPOCH = dt.date(1899, 12, 30)
ROW_RE = re.compile(r'<row r="(\d+)"[^>]*>(.*?)</row>', re.S)
CELL_RE = re.compile(r'<c r="([A-Z]+)\d+"[^>]*>(.*?)</c>', re.S)


@dataclass(frozen=True)
class WorkbookState:
    sheet: str
    source: dict[tuple[str, int], float]
    date_rows: dict[dt.date, int]
    last_row: int
    last_date: dt.date


def _number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return format(float(value), ".15g")


def _excel_serial(day: dt.date) -> int:
    return (day - EXCEL_EPOCH).days


def _excel_date(value: float) -> dt.date:
    return EXCEL_EPOCH + dt.timedelta(days=int(value))


def _read_state(sheet: str) -> WorkbookState:
    source: dict[tuple[str, int], float] = {}
    date_rows: dict[dt.date, int] = {}

    for row_match in ROW_RE.finditer(sheet):
        row = int(row_match.group(1))
        if row < 7:
            continue
        for cell_match in CELL_RE.finditer(row_match.group(2)):
            column = cell_match.group(1)
            if column not in VALUE_COLUMNS:
                continue
            value_match = re.search(r"<v>(.*?)</v>", cell_match.group(2), re.S)
            if not value_match or value_match.group(1) in ("", "#N/A"):
                continue
            try:
                source[(column, row)] = float(value_match.group(1))
            except ValueError:
                continue
        if ("C", row) in source and ("D", row) in source and source[("D", row)] > 0:
            date_rows[_excel_date(source[("C", row)])] = row

    if not date_rows:
        raise ValueError("No dated price rows found in the workbook")
    last_date = max(date_rows)
    return WorkbookState(sheet, source, date_rows, date_rows[last_date], last_date)


def _replace_cell_value(row_xml: str, column: str, row: int, value: float) -> str:
    pattern = re.compile(rf'(<c r="{column}{row}"[^>]*>.*?<v>).*?(</v>.*?</c>)', re.S)
    updated, count = pattern.subn(rf"\g<1>{_number(value)}\2", row_xml, count=1)
    if count != 1:
        raise ValueError(f"Could not update {column}{row}")
    return updated


def _average(source: dict[tuple[str, int], float], row: int, window: int) -> float:
    values = [source[("D", index)] for index in range(row - window + 1, row + 1)]
    if len(values) != window:
        raise ValueError(f"Incomplete {window}-row window at row {row}")
    return sum(values) / window


def _recalculate_row(source: dict[tuple[str, int], float], row: int) -> None:
    source[("E", row)] = _average(source, row, 240)
    source[("I", row)] = _average(source, row, 370)
    source[("F", row)] = source[("I", row)] * 1.3
    source[("G", row)] = source[("I", row)] * 1.6
    source[("H", row)] = source[("I", row)] * 1.1
    source[("K", row)] = _average(source, row, 85)
    source[("L", row)] = _average(source, row, 65)


def _new_row_xml(source: dict[tuple[str, int], float], row: int) -> str:
    cells: list[str] = []
    for column in VALUE_COLUMNS:
        value = _number(source[(column, row)])
        style = CELL_STYLE[column]
        if column in FORMULA_SI:
            cells.append(
                f'<c r="{column}{row}" s="{style}"><f t="shared" si="{FORMULA_SI[column]}"/><v>{value}</v></c>'
            )
        else:
            cells.append(f'<c r="{column}{row}" s="{style}"><v>{value}</v></c>')
    return f'<row r="{row}" spans="3:12">{"".join(cells)}</row>'


def _extend_shared_formulas(sheet: str, old_last_row: int, new_last_row: int) -> str:
    if new_last_row == old_last_row:
        return sheet
    for shared_index in FORMULA_SI.values():
        pattern = rf'(<f t="shared" ref="[A-Z]+\d+:[A-Z]+){old_last_row}(" si="{shared_index}">)'
        sheet, count = re.subn(pattern, rf"\g<1>{new_last_row}\2", sheet, count=1)
        if count != 1:
            raise ValueError(f"Could not extend shared formula {shared_index}")
    return sheet


def _patch_rows(
    state: WorkbookState,
    today: dt.date,
    observed: dict[dt.date, int],
    reconcile_days: int,
) -> tuple[str, dict[tuple[str, int], float], dict[str, object]]:
    sheet = state.sheet
    source = dict(state.source)
    date_rows = dict(state.date_rows)
    changed_rows: set[int] = set()
    reconciled_dates: list[str] = []

    reconcile_from = max(min(date_rows), state.last_date - dt.timedelta(days=reconcile_days))
    existing_through = min(state.last_date, today)
    observed_existing_days = sorted(
        day
        for day in observed
        if reconcile_from <= day <= existing_through and day in date_rows
    )

    # Once the first published observation in the reconciliation window is
    # reached, rebuild every following existing day as either its TGJU high or
    # a carry-forward from the preceding day. This keeps previously appended
    # fallback rows consistent when TGJU later corrects/publishes an earlier
    # date. If the source is wholly unavailable (``observed`` is empty), no
    # existing history is rewritten.
    if observed_existing_days:
        repair_from = observed_existing_days[0]
        previous_price: int | None = None
        for day, row in sorted(date_rows.items()):
            if day < repair_from or day > existing_through:
                continue
            if day in observed:
                price = observed[day]
            elif previous_price is not None:
                price = previous_price
            else:
                price = int(source[("D", row)])

            if int(source[("D", row)]) != price:
                source[("D", row)] = float(price)
                changed_rows.add(row)
                reconciled_dates.append(day.isoformat())
            previous_price = price

    carried_dates: list[str] = []
    appended_dates: list[str] = []
    previous_price = int(source[("D", state.last_row)])
    day = state.last_date + dt.timedelta(days=1)
    next_row = state.last_row + 1
    while day <= today:
        if day in observed:
            price = observed[day]
        else:
            price = previous_price
            carried_dates.append(day.isoformat())
        source[("C", next_row)] = float(_excel_serial(day))
        source[("D", next_row)] = float(price)
        date_rows[day] = next_row
        changed_rows.add(next_row)
        appended_dates.append(day.isoformat())
        previous_price = price
        day += dt.timedelta(days=1)
        next_row += 1

    if not changed_rows:
        return sheet, source, {
            "updated": False,
            "last_date": state.last_date.isoformat(),
            "last_row": state.last_row,
            "appended_dates": [],
            "carried_dates": [],
            "reconciled_dates": [],
        }

    new_last_row = max(date_rows.values())
    first_changed_row = min(changed_rows)
    for row in range(first_changed_row, new_last_row + 1):
        _recalculate_row(source, row)

    sheet = _extend_shared_formulas(sheet, state.last_row, new_last_row)
    for row in range(first_changed_row, new_last_row + 1):
        match = re.search(rf'<row r="{row}"[^>]*>.*?</row>', sheet, re.S)
        if not match:
            raise ValueError(f"Missing worksheet row {row}")
        if row <= state.last_row:
            row_xml = match.group(0)
            for column in ("D", "E", "F", "G", "H", "I", "K", "L"):
                row_xml = _replace_cell_value(row_xml, column, row, source[(column, row)])
        else:
            row_xml = _new_row_xml(source, row)
        sheet = sheet[: match.start()] + row_xml + sheet[match.end() :]

    last_date = max(date_rows)
    return sheet, source, {
        "updated": True,
        "last_date": last_date.isoformat(),
        "last_row": new_last_row,
        "last_price_toman": int(source[("D", new_last_row)]),
        "appended_dates": appended_dates,
        "carried_dates": carried_dates,
        "reconciled_dates": reconciled_dates,
    }


def _rebuild_chart(chart: str, source: dict[tuple[str, int], float], last_row: int) -> str:
    pattern = re.compile(
        r'<c:numRef><c:f>(?P<ref>.*?)</c:f>(?P<cache><c:numCache>.*?</c:numCache>)</c:numRef>',
        re.S,
    )

    def replacement(match: re.Match[str]) -> str:
        reference = html.unescape(match.group("ref"))
        range_match = re.search(r'!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)$', reference)
        if not range_match or range_match.group(1) != range_match.group(3):
            return match.group(0)
        column = range_match.group(1)
        first_row = int(range_match.group(2))
        new_reference = re.sub(r'\$\d+$', "$" + str(last_row), reference)
        format_match = re.search(r'<c:formatCode>(.*?)</c:formatCode>', match.group("cache"), re.S)
        format_code = format_match.group(1) if format_match else "General"
        values = [source[(column, row)] for row in range(first_row, last_row + 1)]
        points = "".join(
            f'<c:pt idx="{index}"><c:v>{_number(value)}</c:v></c:pt>'
            for index, value in enumerate(values)
        )
        cache = (
            f'<c:numCache><c:formatCode>{format_code}</c:formatCode>'
            f'<c:ptCount val="{len(values)}"/>{points}</c:numCache>'
        )
        return f'<c:numRef><c:f>{html.escape(new_reference, quote=False)}</c:f>{cache}</c:numRef>'

    updated, count = pattern.subn(replacement, chart)
    if count == 0:
        raise ValueError("Chart contains no numeric references")
    return updated


def update_workbook(
    workbook: bytes,
    today: dt.date,
    observed_highs_toman: dict[dt.date, int],
    reconcile_days: int = 14,
) -> tuple[bytes, dict[str, object]]:
    """Update the macro-enabled workbook through ``today``.

    TGJU observations are applied when present. Every missing calendar date is
    filled with the last available price. VBA bytes and all unrelated package
    parts are preserved exactly.
    """

    with zipfile.ZipFile(io.BytesIO(workbook), "r") as source_zip:
        infos = source_zip.infolist()
        parts = {info.filename: source_zip.read(info.filename) for info in infos}

    if VBA_PROJECT not in parts:
        raise ValueError("The workbook has no VBA project")
    original_vba_hash = hashlib.sha256(parts[VBA_PROJECT]).hexdigest()
    state = _read_state(parts[MAIN_SHEET].decode("utf-8"))
    sheet, values, audit = _patch_rows(state, today, observed_highs_toman, reconcile_days)
    if not audit["updated"]:
        audit.update({"vba_sha256": original_vba_hash, "changed_parts": []})
        return workbook, audit

    changed_parts = [MAIN_SHEET]
    parts[MAIN_SHEET] = sheet.encode("utf-8")

    workbook_xml = parts[WORKBOOK_XML].decode("utf-8")
    workbook_xml = re.sub(
        r'<calcPr\b([^>]*)/>',
        lambda match: '<calcPr'
        + re.sub(r'\s+(fullCalcOnLoad|forceFullCalc)="[^"]*"', "", match.group(1))
        + ' fullCalcOnLoad="1" forceFullCalc="1"/>',
        workbook_xml,
        count=1,
    )
    parts[WORKBOOK_XML] = workbook_xml.encode("utf-8")
    changed_parts.append(WORKBOOK_XML)

    last_row = int(audit["last_row"])
    for name in sorted(parts):
        if re.fullmatch(r"xl/charts/chart\d+\.xml", name):
            parts[name] = _rebuild_chart(parts[name].decode("utf-8"), values, last_row).encode("utf-8")
            changed_parts.append(name)

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as destination:
        for info in infos:
            destination.writestr(info, parts[info.filename])

    updated = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(updated), "r") as verified:
        if verified.testzip() is not None:
            raise ValueError("Updated workbook failed ZIP integrity validation")
        updated_vba_hash = hashlib.sha256(verified.read(VBA_PROJECT)).hexdigest()
    if updated_vba_hash != original_vba_hash:
        raise ValueError("VBA project changed during the update")

    audit.update(
        {
            "vba_sha256": original_vba_hash,
            "changed_parts": changed_parts,
            "output_sha256": hashlib.sha256(updated).hexdigest(),
        }
    )
    return updated, audit


def latest_workbook_date(workbook: bytes) -> dt.date:
    """Return the most recent dated price row without modifying the package."""

    with zipfile.ZipFile(io.BytesIO(workbook), "r") as package:
        sheet = package.read(MAIN_SHEET).decode("utf-8")
    return _read_state(sheet).last_date


def latest_workbook_snapshot(workbook: bytes) -> dict[str, object]:
    """Return the latest input and cached calculation values for reporting."""

    with zipfile.ZipFile(io.BytesIO(workbook), "r") as package:
        sheet = package.read(MAIN_SHEET).decode("utf-8")
    state = _read_state(sheet)
    values = {
        column: state.source[(column, state.last_row)]
        for column in ("D", "E", "F", "G", "H", "I", "K", "L")
    }
    return {
        "date": state.last_date.isoformat(),
        "row": state.last_row,
        "values": values,
    }
