#!/usr/bin/env python3
"""Verify an exported .xlsx round-trips: LibreOffice re-exports every sheet to CSV and
this script diffs those cells against the source chunk JSON.

usage: python3 validate.py --xlsx ~/Downloads/out.xlsx --in '/tmp/tc/b*.json'
Needs `soffice` on PATH. Exits non-zero on any mismatch.
"""
import argparse, csv, glob, json, os, re, subprocess, sys, tempfile

FILTER = 'csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,true,false,false,-1'
SAFE = re.compile(r'[\[\]\:\*\?\/\\]')


def chunks(pattern):
    out = {}
    for path in sorted(glob.glob(os.path.expanduser(pattern))):
        raw = json.load(open(path, encoding='utf-8'))
        data = json.loads(raw) if isinstance(raw, str) else raw
        for sh in ([data] if isinstance(data, dict) else data):
            out[str(sh.get('name') or sh.get('id'))] = sh['data']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx', required=True)
    ap.add_argument('--in', dest='inp', required=True)
    a = ap.parse_args()
    xlsx = os.path.expanduser(a.xlsx)
    src = chunks(a.inp)
    stem = os.path.splitext(os.path.basename(xlsx))[0]

    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, HOME=os.environ.get('HOME', td))
        cmd = ['soffice', '-env:UserInstallation=file://' + os.path.join(td, 'lo'),
               '--headless', '--convert-to', FILTER, '--outdir', td, xlsx]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        if r.returncode != 0:
            print('soffice failed:', r.stderr.strip()[:400]); return 2

        bad = 0
        for name, data in src.items():
            csvname = os.path.join(td, '%s-%s.csv' % (stem, SAFE.sub('_', name)))
            if not os.path.exists(csvname):
                alt = [p for p in glob.glob(os.path.join(td, '*.csv'))
                       if SAFE.sub('_', name) in os.path.basename(p)]
                if not alt:
                    print('%-30s MISSING csv' % name); bad += 1; continue
                csvname = alt[0]
            rows = list(csv.reader(open(csvname, encoding='utf-8')))
            n = min(len(rows), len(data))
            diffs = [i for i in range(n)
                     if [c.strip() for c in data[i]] != [c.strip() for c in rows[i][:len(data[i])]]]
            status = 'OK' if not diffs and len(rows) == len(data) else 'DIFF rows=%d/%d cells=%d' % (
                len(rows), len(data), len(diffs))
            if status != 'OK':
                bad += 1
                if diffs:
                    i = diffs[0]
                    print('   first diff row %d\n     src %r\n     csv %r' % (i, data[i][:5], rows[i][:5]))
            print('%-30s %s' % (name, status))
        print('RESULT: %s (%d/%d sheets match)' % ('PASS' if bad == 0 else 'FAIL', len(src) - bad, len(src)))
        return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
