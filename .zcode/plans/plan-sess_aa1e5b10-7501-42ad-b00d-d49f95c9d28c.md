## 目标
修复 3 处逻辑问题：#1 分页拉取避免丢消息、#2+#3 去重 fail-loud 与 sort 格式、#4 去重键改为统计日期（「日期」列改存统计日期）。

## 改动清单

### 1. `src/telegram_reader.py` — 修复 #1（分页拉取）
`_fetch` 内从「单次 `get_messages(limit=N)`」改为**分页循环**：
- 用 `max_id` 游标逐页向下拉，每页 `limit` 条；每页拿完后把游标设为该页最旧消息 ID（`max_id` 为开区间，天然递减）。
- 当某页返回条数 `< limit`（或为空）时停止。
- 最后 `reversed()` 返回升序。
- 效果：不再受 200 条上限截断，正常同步/回补会取回**全部**新消息；`main.py` 的 `state.save_last_id(max(...))` 也会推进到真实最新 ID。

### 2. `src/lark_writer.py` — 修复 #2+#3（去重）
`get_recent_timestamps`：
- 顶部加 `import json`。
- `sort` 参数改为官方对象格式：`json.dumps([{"field_name": field_name, "desc": True}], ensure_ascii=False)`。
- HTTP 错误用 `resp.raise_for_status()`，飞书 `code != 0` 时 `raise RuntimeError(...)`——**不再 `return set()` 静默跳过去重**，让去重基准读取失败时中止写入（fail loud）。

### 3. `config/parser_config_nuworld.json` — 修复 #4（去重键=统计日期）
`report_date` 字段：
- `pattern` 从「播报时间」改为「统计日期」：`统计日期[：:]\s*(\d{4}-\d{2}-\d{2})`
- `type` 从 `datetime_ms` 改为 `date_ms`
- `_comment` 同步更新
- `field_labels` 里 `report_date → 日期` 不变；`row_order` 不变
- 结果：「日期」列存**统计日期（date-only）**，`main.py:103-104` 的去重（按「日期」）随之变成「每天一条」。

### 4. `src/parser.py` — 清理 `datetime_ms`（#4 的连带后果）
`datetime_ms` 是为「播报时间」专门加的，现在无任何配置使用，删除该分支（保留 `date_ms`）。避免留下死代码。

### 5. `tests/test_nuworld_parser.py` — 更新断言
- 「日期」断言从「播报时间毫秒」改为「统计日期 `2026-08-13` 的 `date_ms` 毫秒值」（实现时用 Python 精确算出）。
- 其余字段断言不变。

### 6. `README.md` — 同步文档
- 字段映射表：「日期」列含义改为「统计日期」。
- 类型说明表移除 `datetime_ms`（保留 `date_ms`）。

## 验证
- `python -m unittest tests.test_nuworld_parser -v`（日期值改为统计日期后应通过）
- `python -m py_compile main.py src/parser.py src/telegram_reader.py src/lark_writer.py`
- 逻辑上确认：#1 分页后不再丢消息；#2+#3 读取失败即中止、不重复写入；#4 去重粒度=统计日期。

## 不在本次范围
- 不恢复/修改 `.github/workflows/sync.yml` 的 cron。
- 不处理 Telegram 限流（`FloodWaitError`）的重试（原 #7，未选）。
- 不 commit / push（沿用你之前「自行提交」的方式）。