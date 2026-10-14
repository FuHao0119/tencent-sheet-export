// Pass this whole file as the `function` argument of mcp__browser-use__evaluate_script.
// Returns every sheet's id / name / size / whether its cells are loaded yet.
async () => {
  const wm = window.SpreadsheetApp && window.SpreadsheetApp.workbook && window.SpreadsheetApp.workbook.worksheetManager;
  if (!wm) return JSON.stringify({ error: 'SpreadsheetApp not ready — wait for the sheet to finish loading, then retry' });
  const ids = wm.getSheetIdList(), names = wm.getSheetNameList();
  const seg = id => (wm.getStringRepresentation().split(',').find(s => s.trim().startsWith(id + '(')) || '');
  return JSON.stringify(ids.map((id, i) => {
    const s = wm.getSheetBySheetId(id), m = seg(id).match(/\((\d+)x(\d+)/);
    return {
      id, name: names[i],
      rows: m ? +m[1] : 0,
      cols: m ? +m[2] : 0,
      initialized: seg(id).includes('initialized'),
      // state "1" = visible tab, "2"/other = hidden: viewers can never load a hidden sheet
      state: s && s.sheetProperties ? String(s.sheetProperties.state) : null,
      active: window.SpreadsheetApp.workbook.activeSheetId === id
    };
  }));
}
