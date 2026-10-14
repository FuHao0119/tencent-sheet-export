# tencent-sheet-export

把腾讯文档表格（`https://docs.qq.com/sheet/...`）整本导出成本地 `.xlsx`，多工作表、含隐藏表识别与逐格回归校验。
Export Tencent Docs spreadsheets to a local multi-sheet `.xlsx`, cell-verified.

## 为什么需要它

腾讯文档的表格不是 HTML `<table>`，直接抓网页拿不到数据：

| 常见尝试 | 结果 |
|---|---|
| 解析页面 DOM | ❌ 表格是 canvas 绘制的，DOM 里没有单元格 |
| 请求 `dop-api/opendoc` | ❌ 返回 base64 + zlib + protobuf 二进制，解不出行列位置 |
| 手动复制粘贴 | ❌ 游客身份常被禁用，且大表复制不全 |
| 读前端模型 `window.SpreadsheetApp` | ✅ 页面已经把二进制解码成对象，直接逐格取显示值 |

难点在于**单元格是懒加载的**：只有点过底部工作表标签，客户端才会向服务端请求那张表的数据。本项目用一套鼠标事件模拟点击来触发加载（`element.click()` 单独派发无效）。

## 环境要求

- [Qoder](https://qoder.com) CLI + `browser-use` MCP（内置浏览器）
- `python3`（标准库即可，**不需要** openpyxl / pandas）
- 可选：`soffice`（LibreOffice），用于 `validate.py` 逐格校验

## 安装为 Qoder 技能

```bash
git clone https://github.com/FuHao0119/tencent-sheet-export.git \
  ~/.qoder/skills/tencent-sheet-export
```

在 Qoder 里执行 `/skills reload`（或重启会话），然后：

```
/tencent-sheet-export https://docs.qq.com/sheet/xxxxxxxx
```

## 不用 Qoder，直接手动跑

1. 浏览器打开表格链接并等待加载完成，按 F12 打开控制台。
2. 粘贴 `scripts/probe_sheets.js` 全文回车，得到所有工作表的 `id / name / rows / state`。
3. 粘贴 `scripts/load_sheets.js`，先把 `__SHEET_NAMES__` 换成精确表名数组，例如 `["Sheet1", "成绩表"]`，回车触发各表加载。
4. 粘贴 `scripts/extract_cells.js`，把 `__SHEET_IDS__` 换成 id 数组，例如 `["000001", "000002"]`；用 `copy()` 或把返回值存成 `b1.json`。单次建议不超过 3000 行。
5. 合成与校验：

```bash
python3 scripts/build_xlsx.py --in './b*.json' --out ./out.xlsx
python3 scripts/validate.py   --xlsx ./out.xlsx  --in './b*.json'
# RESULT: PASS (20/20 sheets match)
```

## 取值语义

- 显示值优先取 `cell.formattedValue.value`，日期、小数位、百分比与页面所见一致；不是对象时才回落到 `cell.value`。
- `cell.value` 为对象时是富文本，走 `value.r` 数组拼接，超链接以文本形式保留。
- `build_xlsx.py` 只把纯数字字符串转成数字单元格；`081200` 这类带前导零的专业代码保持文本，不会丢零。
- 每张表会裁掉尾部全空行/列；`getRowCount()` 是文档声明的尺寸，不等于实际数据量。

## 已知限制

- **隐藏工作表取不到。** `state` 不为 `"1"` 的表不出现在底部标签栏，DOM 里没有可点元素，只读访客的前端会话永远不会拉取它的数据。`prepareSwitchSheet()`、`reInitSheetBySheetId()`、直接改 `sheetProperties.state` 均已实测无效。请文档作者取消隐藏后重跑。
- 本工具全程只读，不对共享文档做任何写入。
- 需要登录才能查看的文档，请先在内置浏览器里完成登录。
- 只支持 `docs.qq.com/sheet/...`；文档（doc）、智能表格、收集表不在覆盖范围内。

## 文件

```
SKILL.md                     Qoder 技能入口（流程、坑、校验要求）
scripts/probe_sheets.js      列出工作表与加载/隐藏状态
scripts/load_sheets.js       点标签触发懒加载
scripts/extract_cells.js     逐格导出显示值 JSON
scripts/build_xlsx.py        JSON 分片 -> 多表 xlsx（纯标准库）
scripts/validate.py          LibreOffice 反导 CSV 并逐格比对
```

## License

MIT
