#!/usr/bin/env python3
"""Build an .xlsx workbook from the JSON chunks produced by extract_cells.js.

usage: python3 build_xlsx.py --in '/tmp/tc/b*.json' --out ~/Downloads/out.xlsx
Stdlib only (no openpyxl). Pure-number strings become real numeric cells; everything
else is written as inlineStr.
"""
import argparse, glob, json, os, re, sys, zipfile
from xml.sax.saxutils import escape

NUM = re.compile(r'^-?(0|[1-9]\d*)(\.\d+)?$')


def load_chunks(pattern):
    sheets = []
    for path in sorted(glob.glob(os.path.expanduser(pattern))):
        raw = json.load(open(path, encoding='utf-8'))
        # evaluate_script's filePath writes the returned string, so a JSON string is double encoded
        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, dict):
            data = [data]
        for sh in data:
            if not sh.get('data'):
                print('skip empty sheet:', sh.get('name'), file=sys.stderr)
                continue
            sheets.append(sh)
    if not sheets:
        raise SystemExit('no sheets found in %s' % pattern)
    return sheets


def colname(n):
    s = ''
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def safe_name(name, used):
    name = re.sub(r'[\[\]\:\*\?\/\\]', '_', str(name)).strip() or 'Sheet'
    name = name[:31]
    base, k = name, 2
    while name.lower() in used:
        name = '%s(%d)' % (base[:28], k)
        k += 1
    used.add(name.lower())
    return name


def sheet_xml(rows):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
           '<sheetData>']
    for ri, row in enumerate(rows, start=1):
        cells = []
        for ci, val in enumerate(row, start=1):
            if val is None or val == '':
                continue
            val = str(val)
            ref = '%s%d' % (colname(ci), ri)
            if NUM.match(val):
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, val))
            else:
                cells.append('<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                             % (ref, escape(val)))
        if cells:
            out.append('<row r="%d">' % ri + ''.join(cells) + '</row>')
    out.append('</sheetData></worksheet>')
    return ''.join(out)


def build(sheets, out_path):
    used, names = set(), []
    for sh in sheets:
        names.append(safe_name(sh.get('name') or sh.get('id'), used))
    out_path = os.path.expanduser(out_path)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
              '<Default Extension="xml" ContentType="application/xml"/>',
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>']
        for i in range(len(sheets)):
            ct.append('<Override PartName="/xl/worksheets/sheet%d.xml" '
                      'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1))
        ct.append('</Types>')
        z.writestr('[Content_Types].xml', ''.join(ct))
        z.writestr('_rels/.rels',
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                   'Target="xl/workbook.xml"/></Relationships>')
        wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
        for i, nm in enumerate(names):
            wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(nm), i + 1, i + 1))
        wb.append('</sheets></workbook>')
        z.writestr('xl/workbook.xml', ''.join(wb))
        rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i in range(len(sheets)):
            rels.append('<Relationship Id="rId%d" '
                        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                        'Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1))
        rels.append('</Relationships>')
        z.writestr('xl/_rels/workbook.xml.rels', ''.join(rels))
        for i, sh in enumerate(sheets):
            z.writestr('xl/worksheets/sheet%d.xml' % (i + 1), sheet_xml(sh['data']))
    return out_path, names


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True, help="glob of chunk json files")
    ap.add_argument('--out', required=True, help='output .xlsx path')
    a = ap.parse_args()
    sheets = load_chunks(a.inp)
    path, names = build(sheets, a.out)
    print('wrote %s (%.1f KB)' % (path, os.path.getsize(path) / 1024.0))
    for i, sh in enumerate(sheets):
        print('  %2d. %-32s %5d rows x %d cols' % (i + 1, names[i], len(sh['data']), max(len(r) for r in sh['data'])))
