## 目标
新增 NU World 业务线：从 TG 群组（环境变量 `NU_TG_GROUP_ID`）读取 bot 播报消息（bot id `8156123678`，环境变量 `NU_BOT_USERNAME`），按正则解析后写入飞书多维表格（`NU_LARK_WIKI_NODE_TOKEN` + `NU_LARK_TABLE_ID`）。

已确认：飞书「日期」列为日期字段（毫秒时间戳），值取播报时间 `2026-08-14 00:20:11`，按 GMT+8 转毫秒。

## 改动清单

### 1. `src/parser.py` — 新增 `datetime_ms` 类型
在 `_cast()` 中 `date_ms` 之后新增 `datetime_ms` 分支，将 `YYYY-MM-DD HH:MM:SS` 按 GMT+8 转成毫秒时间戳（与 `date_ms` 一致的处理方式）。

### 2. `src/telegram_reader.py` — 支持数字 bot id
`from_user` 过滤目前把值当用户名字符串处理。改为：若 `bot_username`（去掉 `@`）是纯数字，则 `int()` 转成用户 ID 再传给 `from_user`，从而正确过滤 bot id `8156123678`。

### 3. 新建 `config/parser_config_nuworld.json`
字段（内部名 → 飞书列名）：
- `report_date` → 日期（播报时间，`datetime_ms`，required）
- `page_visits` → 页面访问（required）
- `visit_level` → 访问详情：/level
- `visit_home` → 访问详情：/home
- `visit_arena` → 访问详情：/arena
- `sessions` → 访问会话
- `new_users` → 新用户注册
- `active_users` → 活跃用户
- `quest_users` → 完成 Quest 用户
- `checkin_users` → 签到用户
- `nu_participants` → NU World 参与人数（不含机器人）
- `nu_volume` → NU World 成交总量（float）

`row_order` 按飞书列顺序：日期、页面访问、/level、/home、/arena、访问会话、新用户注册、活跃用户、完成 Quest 用户、签到用户、NU World 参与人数（不含机器人）、NU World 成交总量。

### 4. `main.py` — 添加 NU World target
- `build_targets()` 签名改为 `build_targets(lark_app_id, lark_app_secret)`（移除现已无用的 `default_group_id/default_bot_username` 参数）。
- `candidates` 加入 NU World target：`NU_TG_GROUP_ID` / `NU_BOT_USERNAME` / `NU_LARK_WIKI_NODE_TOKEN` / `NU_LARK_TABLE_ID` / `config/parser_config_nuworld.json` / `data/last_message_id_nuworld.txt`。
- `main()` 移除 `require_env("TG_GROUP_ID")` 与 `opt_env("BOT_USERNAME")`，调用改为 `build_targets(lark_app_id, lark_app_secret)`。

### 5. 新建 `tests/test_nuworld_parser.py`
用示例消息验证解析结果（日期毫秒值、页面访问 4432、/level 834、/home 976、/arena 797、成交总量 98.0 等）。

### 6. `README.md` — 更新状态与配置说明
- 状态从「已停用」改为「NU World 业务线已启用；其余业务线已停用」。
- 补充 NU World 环境变量：`NU_TG_GROUP_ID`、`NU_BOT_USERNAME`、`NU_LARK_WIKI_NODE_TOKEN`、`NU_LARK_TABLE_ID`。
- 补 `datetime_ms` 类型说明。

## 需要你之后在 CI/环境变量中配置的值（代码不写死）
- `NU_TG_GROUP_ID`：NU World 播报所在的 TG 群组 ID（负数 `-100...` 或 `@username`）
- `NU_BOT_USERNAME`：`8156123678`
- `NU_LARK_WIKI_NODE_TOKEN`、`NU_LARK_TABLE_ID`：NU World 飞书多维表格的 wiki node token 与 table ID

## 不做
- 不 commit、不 push（沿用你之前「仅本地改动」的选择）
- 不恢复已删除的 `.github/workflows/sync.yml`（如需要定时调度，需另行恢复 workflow）