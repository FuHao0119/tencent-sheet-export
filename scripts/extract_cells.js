// Replace __SHEET_IDS__ with exact ids from probe_sheets.js, e.g. ["000001", "000003"].
// Then pass as evaluate_script's `function` together with `filePath` so the payload is
// written to disk instead of streaming into the conversation.
// Keep each call to roughly <= 3000 rows to stay well inside the tool timeout.
async () => {
  const IDS = __SHEET_IDS__;
  const wm = window.SpreadsheetApp.workbook.worksheetManager;
  const isInit = id => (wm.getStringRepresentation().split(',').find(s => s.trim().startsWith(id + '(')) || '').includes('initialized');
  const cellText = c => {
    if (c == null) return '';
    const v = c.value, fv = c.formattedValue;
    // formattedValue carries what the sheet actually shows: dates, fixed decimals, etc.
    if (fv && fv.value != null && typeof fv.value !== 'object') return String(fv.value);
    if (v == null) return '';
    if (typeof v !== 'object') return String(v);
    if (Array.isArray(v.r)) return v.r.map(x => x == null ? '' : (typeof x === 'object'
      ? (x.t != null ? String(x.t) : (x.v != null ? String(x.v) : '')) : String(x))).join('');
    return '';
  };
  const out = [];
  for (const id of IDS) {
    const s = wm.getSheetBySheetId(id);
    if (!s) { out.push({ id, error: 'sheet not found' }); continue; }
    if (!isInit(id)) { out.push({ id, name: wm.getSheetNameBySheetId(id), error: 'not initialized, run load_sheets.js first' }); continue; }
    const R = s.getRowCount(), C = s.getColCount();
    let lastRow = -1, lastCol = -1;
    const grid = [];
    for (let r = 0; r < R; r++) {
      const line = [];
      let any = false;
      for (let c = 0; c < C; c++) {
        const t = cellText(s.getCellDataAtPosition(r, c));
        line.push(t);
        if (t !== '') { any = true; if (c > lastCol) lastCol = c; }
      }
      if (any) lastRow = r;
      grid.push(line);
    }
    const data = grid.slice(0, lastRow + 1).map(row => row.slice(0, lastCol + 1));
    out.push({ id, name: wm.getSheetNameBySheetId(id), rows: data.length, cols: lastCol + 1, data });
  }
  return JSON.stringify(out);
}
