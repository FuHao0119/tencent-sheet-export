// Replace __SHEET_NAMES__ with a JS array of exact sheet names from probe_sheets.js,
// e.g. ["双非", "27（985）"]. Then pass as evaluate_script's `function`.
// Tencent Docs only downloads a sheet's cells when its bottom tab is opened, so this
// clicks through the tabs and waits until each one is initialized.
async () => {
  const NAMES = __SHEET_NAMES__;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const wm = window.SpreadsheetApp.workbook.worksheetManager;
  const ids = wm.getSheetIdList(), names = wm.getSheetNameList();
  const idOf = {}; names.forEach((n, i) => { idOf[n] = ids[i]; });
  const isInit = id => (wm.getStringRepresentation().split(',').find(s => s.trim().startsWith(id + '(')) || '').includes('initialized');
  const findTab = nm => {
    const tabs = [...document.querySelectorAll('.tab-bar-item')];
    return tabs.find(e => e.textContent.trim() === nm)
        || tabs.find(e => e.textContent.trim().startsWith(nm))
        || tabs.find(e => e.textContent.trim().includes(nm.slice(0, 6)));
  };
  const log = [];
  for (const nm of NAMES) {
    const id = idOf[nm];
    if (!id) { log.push(nm + ': NO SUCH SHEET'); continue; }
    if (isInit(id)) { log.push(nm + ': already loaded'); continue; }
    const el = findTab(nm);
    if (!el) { log.push(nm + ': TAB ABSENT (hidden sheet — viewers cannot load it)'); continue; }
    el.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])
      el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window }));
    let ok = false;
    for (let i = 0; i < 16; i++) { await sleep(400); if (isInit(id)) { ok = true; break; } }
    log.push(nm + ': ' + (ok ? 'loaded' : 'TIMEOUT'));
  }
  return JSON.stringify({ log, loaded: ids.filter(isInit).length, total: ids.length });
}
