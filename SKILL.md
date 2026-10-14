---
name: tencent-sheet-export
description: 把腾讯文档表格（docs.qq.com/sheet/...）整本导出成本地 xlsx。用于需要下载、爬取、批量抓取 docs.qq.com 在线表格数据，或复制被禁用、表格是 canvas 渲染抓不到 DOM、dop-api 只返回二进制等情况；支持多工作表、懒加载表、隐藏表识别与逐格回归校验。
argument-hint: <腾讯文档表格链接>
---

# 腾讯文档表格导出

## Overview

腾讯文档的表格不是 HTML `<table>`，而是 canvas 绘制；`dop-api/opendoc` 返回的是 base64+zlib+protobuf 二进制，位置字段无法还原成行列。可行的做法是打开页面后直接读前端已经解码好的数据模型 `window.SpreadsheetApp`，逐格取显示值，再用标准库合成 xlsx。

## 前置条件

- 需要 browser-use MCP（内置浏览器）可用；先 `mcp__browser-use__list_pages` 确认有页面，没有就让用户在应用内打开一个标签。
- 游客只读链接即可导出；若文档要求登录，请用户先在这个内置浏览器里登录，再继续。
- 本机需要 `python3`；逐格校验时需要 `soffice`（LibreOffice），没有则跳过校验并明确告知未校验。
- 全程只读，禁止对共享文档做任何写操作（不要改名、不要取消隐藏、不要编辑）。

## 流程

1. 打开链接并等待引擎就绪：
   - `navigate_page` 到 `https://docs.qq.com/sheet/<docId>`（保留用户给的 `?tab=` 参数）。
   - `evaluate_script` 轮询直到 `window.SpreadsheetApp && window.SpreadsheetApp.workbook.worksheetManager` 存在。页面顶部出现表名 `[xxx] 文档标题` 才算加载完成。

2. 列出工作表：把 `scripts/probe_sheets.js` 全文作为 `evaluate_script` 的 `function` 传入。得到每张表的 `id / name / rows / cols / initialized / state`。
   - `state: "1"` 为可见表；`state` 非 `"1"` 的是**隐藏表**，只读访客永远取不到它的数据，见「已知限制」。

3. 加载数据（关键步骤，别跳过）：表格单元格是懒加载的，只有点过底部标签才会向服务端取数。
   - 把 `scripts/load_sheets.js` 中的 `__SHEET_NAMES__` 替换成第 2 步得到的精确表名数组，例如 `["Sheet1", "2025成绩"]`，然后整体作为 `function` 传入。每次处理 5–8 张表，返回 `loaded / TIMEOUT / TAB ABSENT`。
   - 不要试图用 `dataCenterService.loadSheetData(id)` 代替点击——它以 `void` 返回且不会置为已加载。

4. 逐格取数并落盘：用 `scripts/extract_cells.js`，把 `__SHEET_IDS__` 替换成 `id` 数组。
   - **必须同时传 `filePath`**（如 `/tmp/tc/b1.json`），否则几 MB 的表格会灌进对话上下文。
   - 单次调用控制在约 3000 行以内，分多批写多个文件；文件内容是「JSON 字符串套 JSON」，读时要 `json.loads` 两次。
   - 每个文件的表顺序即最终 xlsx 的表顺序；用第 2 步的 `id` 顺序做最终排序。

5. 合成 xlsx 并校验：
   ```bash
   python3 scripts/build_xlsx.py --in '/tmp/tc/b*.json' --out ~/Downloads/<文档标题>.xlsx
   python3 scripts/validate.py --xlsx ~/Downloads/<文档标题>.xlsx --in '/tmp/tc/b*.json'
   ```
   `validate.py` 用 LibreOffice 把 xlsx 每张表反导成 CSV 并与抓取数据逐格比对，输出 `RESULT: PASS (n/n sheets match)`。只有 PASS 才算完成；已用标准库手写 OOXML，无需 openpyxl/pandas。

6. 汇报：给出本地文件绝对路径、表数量与总行数，并列出未导出的表及原因。

## 取值语义

- 单元格显示值优先取 `cell.formattedValue.value`（日期、小数位、百分比都按页面呈现），它不是对象时才回落到 `cell.value`。
- `cell.value` 为对象时是富文本，走 `value.r` 数组拼接；超链接会以文本形式出现在单元格里，无需额外处理。
- 空串单元格不写入 xlsx；每表裁掉尾部全空行/列，`getRowCount()` 是声明尺寸而非实际数据量。
- `build_xlsx.py` 只对 `^-?(0|[1-9]\d*)(\.\d+)?$` 形态的字符串转成数字单元格，带前导零的编码（如 `081200`）保持文本，避免丢零。

## 已知限制与坑

- **隐藏表取不到**：`state != "1"` 的表不出现在底部标签栏，DOM 里没有可点元素，前端也永远不会拉取它的数据。`sa.view.prepareSwitchSheet(id)`、`reInitSheetBySheetId(id)`、直接改 `sheetProperties.state` 都验证过无效或不适用。处理方式是如实告知用户，并请文档作者取消隐藏后重跑；不要为了取数去修改他人的共享文档。
- 标签名过长时 DOM 文本会被截断，`load_sheets.js` 已按 全等 → 前缀 → 6 字子串 三级兜底匹配；仍匹配不上时先 `take_snapshot` 看真实文本。
- 标签栏横向可滚动（`.docs-tab-bar-scrollable-scroller`），但滚动不会让隐藏表进入 DOM。
- 用 `MouseEvent` 依次派发 `pointerdown/mousedown/pointerup/mouseup/click` 才能触发 React 的切换；单独 `element.click()` 无效。
- 若用户只要一张表，仍然跑第 2 步，用它来确认目标表的 `id` 和尺寸。

## Resources

- `scripts/probe_sheets.js` — 列出全部工作表、尺寸、是否已加载、是否隐藏。
- `scripts/load_sheets.js` — 按表名点击标签触发懒加载；占位符 `__SHEET_NAMES__`。
- `scripts/extract_cells.js` — 按 id 逐格导出显示值 JSON；占位符 `__SHEET_IDS__`，配合 `filePath` 落盘。
- `scripts/build_xlsx.py` — 抓取分片 → 多表 xlsx，仅依赖标准库。
- `scripts/validate.py` — LibreOffice 反导 CSV 并逐格回归比对，输出 PASS/FAIL。
