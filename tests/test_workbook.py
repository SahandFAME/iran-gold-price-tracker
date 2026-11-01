import datetime as dt
import io
import re
import zipfile

from gold_updater.workbook import update_workbook


def _minimal_workbook() -> bytes:
    rows = []
    for row in range(1, 1051):
        if row < 7:
            rows.append(f'<row r="{row}"></row>')
            continue
        if row > 1048:
            rows.append(f'<row r="{row}"><c r="D{row}" s="12"><v>0</v></c></row>')
            continue
        date = 45000 + row
        cells = [f'<c r="C{row}" s="8"><v>{date}</v></c>', f'<c r="D{row}" s="12"><v>{row * 100}</v></c>']
        if row >= 376:
            values = {"E": row, "F": row, "G": row, "H": row, "I": row, "K": row, "L": row}
            for column, value in values.items():
                shared = {"I": 421, "E": 422, "F": 423, "G": 424, "H": 425, "K": 426, "L": 427}[column]
                if row == 1048:
                    formula = f'<f t="shared" si="{shared}"/>'
                else:
                    formula = f'<f t="shared" si="{shared}"/>'
                cells.append(f'<c r="{column}{row}">{formula}<v>{value}</v></c>')
        rows.append(f'<row r="{row}">{"".join(cells)}</row>')
    sheet = '<worksheet><sheetData>' + ''.join(rows) + '</sheetData></worksheet>'
    anchors = {
        421: ("I1000:I1048", "AVERAGE(D631:D1000)"),
        422: ("E1000:E1048", "AVERAGE(D761:D1000)"),
        423: ("F1000:F1048", "I1000*1.3"),
        424: ("G1000:G1048", "I1000*1.6"),
        425: ("H1000:H1048", "I1000*1.1"),
        426: ("K1000:K1048", "AVERAGE(D916:D1000)"),
        427: ("L1000:L1048", "AVERAGE(D936:D1000)"),
    }
    for shared, (reference, formula) in anchors.items():
        sheet = sheet.replace(
            f'<f t="shared" si="{shared}"/>',
            f'<f t="shared" ref="{reference}" si="{shared}">{formula}</f>',
            1,
        )
    chart = (
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
        '<c:numRef><c:f>Sheet!$C$376:$C$1048</c:f><c:numCache><c:formatCode>General</c:formatCode>'
        '<c:ptCount val="1"/><c:pt idx="0"><c:v>1</c:v></c:pt></c:numCache></c:numRef></c:chartSpace>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as workbook:
        workbook.writestr("xl/worksheets/sheet1.xml", sheet)
        workbook.writestr("xl/workbook.xml", '<workbook><calcPr calcId="1"/></workbook>')
        workbook.writestr("xl/vbaProject.bin", b"macro")
        workbook.writestr("xl/charts/chart1.xml", chart)
    return output.getvalue()


def test_carries_forward_and_preserves_vba():
    workbook = _minimal_workbook()
    last_date = dt.date(1899, 12, 30) + dt.timedelta(days=45000 + 1048)
    today = last_date + dt.timedelta(days=2)
    observed = {last_date + dt.timedelta(days=1): 999_000}

    updated, audit = update_workbook(workbook, today, observed)

    assert audit["appended_dates"] == [
        (last_date + dt.timedelta(days=1)).isoformat(),
        today.isoformat(),
    ]
    assert audit["carried_dates"] == [today.isoformat()]
    assert audit["last_price_toman"] == 999_000
    with zipfile.ZipFile(io.BytesIO(updated)) as package:
        assert package.read("xl/vbaProject.bin") == b"macro"
        sheet = package.read("xl/worksheets/sheet1.xml").decode()
        assert '<c r="D1050" s="12"><v>999000</v></c>' in sheet
        chart = package.read("xl/charts/chart1.xml").decode()
        assert "$C$376:$C$1050" in chart
