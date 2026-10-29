"""List BOM lines for the bus capacitors (2.2u, 10u, 47u) with MPNs. python bom_caps.py <bom.xlsx>"""
import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
for ws in wb.worksheets:
    rows = list(ws.iter_rows(values_only=True))
    if not rows: continue
    print('== sheet', ws.title, '| header:', rows[0])
    for r in rows[1:]:
        s = ' | '.join('' if v is None else str(v) for v in r)
        if any(k in s for k in ('2.2u', '2.2 u', '10u', '47u', '2u2', '10µ', '47µ', '2.2µ')) or 'C1' in s[:6]:
            print('  ', s[:260])
