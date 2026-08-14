# Telegram → Lark 数据同步

> **当前状态：NU World 业务线已启用。** 原有的 BTG、BTG VN、X、Other、LevelUp / ANOME ONE 五条业务线均已停止使用；当前仅保留 NU World 一条业务线。仓库保留了通用的「Telegram → 飞书多维表格」同步框架，供日后新增业务线时复用。

## 通用框架

| 文件 | 作用 |
|------|------|
| `main.py` | 主入口：组装配置、编排「拉取 → 解析 → 去重 → 写入 → 保存状态」流程 |
| `src/telegram_reader.py` | 用 Telethon 从 Telegram 群组拉取新消息，带重试 |
| `src/parser.py` | 配置驱动的正则解析器，把消息文本解析为字段字典并转为表格记录 |
| `src/lark_writer.py` | 飞书 API 封装：鉴权、wiki node 解析、去重查询、批量写入 |
| `src/state.py` | 持久化「最后已处理的消息 ID」，实现增量同步 |
| `generate_session.py` | 本地交互式生成 Telethon session string |

依赖仅两个：`telethon`、`requests`（见 `requirements.txt`）。

## 当前业务线：NU World

从 TG 群组读取 bot 播报消息，解析后写入飞书多维表格。

### 环境变量

**Secrets（敏感信息）：**

| Name | 说明 |
|------|------|
| `TG_SESSION_STRING` | Telethon session string |
| `TG_API_ID` | Telegram API ID |
| `TG_API_HASH` | Telegram API Hash |
| `LARK_APP_ID` | 飞书应用 App ID |
| `LARK_APP_SECRET` | 飞书应用 App Secret |

**Variables（非敏感配置）：**

| Name | 示例值 | 说明 |
|------|--------|------|
| `NU_TG_GROUP_ID` | `-1001234567890` | NU World 播报所在的 TG 群组 ID（负数）或 `@username` |
| `NU_BOT_USERNAME` | `@Levelupnetwork_bot` | 只读此 bot 的消息（bot 用户名） |
| `NU_LARK_WIKI_NODE_TOKEN` | `wikcn...` | NU World 飞书多维表格 wiki node token |
| `NU_LARK_TABLE_ID` | `tbl...` | NU World 多维表格 table ID |

> 获取 TG 群组 ID：将 bot `@userinfobot` 加入群组，发送任意消息即可看到群组 ID。

### 运行方式（GitHub Actions）

在 GitHub repo → **Settings** → **Secrets and variables** → **Actions** 中配置上述 Secrets 与 Variables，由 `.github/workflows/sync.yml` 定时或手动触发运行。

### 飞书表格列与消息字段对应

| 飞书列名 | 消息字段 | 类型 |
|---------|---------|------|
| 日期 | 统计日期 `2026-08-13` | 日期（毫秒时间戳，GMT+8，用于去重） |
| 页面访问 | `1. 页面访问：4,432` | int |
| 访问详情：/level | `/level 834 次` | int |
| 访问详情：/home | `/home 976 次` | int |
| 访问详情：/arena | `/arena 797 次` | int |
| 访问会话 | `2. 访问会话：458` | int |
| 新用户注册 | `3. 新用户注册：15` | int |
| 活跃用户 | `4. 活跃用户：198` | int |
| 完成 Quest 用户 | `5. 完成 Quest 用户：13` | int |
| 签到用户 | `6. 签到用户：49` | int |
| NU World 参与人数（不含机器人） | `7. NU World 参与人数（不含机器人）：42` | int |
| NU World 成交总量 | `8. NU World 成交总量：98.00 USDT` | float |

解析规则见 `config/parser_config_nuworld.json`。

## 工作原理（框架层面）

1. 用 Telethon 读取 TG 群组中新的 bot 消息
2. 用正则规则解析消息内容
3. 将解析结果追加到飞书多维表格

## 如何新增一条业务线

1. **新建解析配置** `config/parser_config_<name>.json`，字段结构见下文「字段配置说明」。
2. **在 `main.py` 的 `build_targets()` 中新增一个 target**，填入 `name`、`parser_config`、`group_id`、`bot_username`、`state_file`、`wiki_node_token`、`table_id`。
3. **配置环境变量**（Telegram 凭证、飞书凭证、群组 ID、wiki node token、table ID）。
4. **恢复定时调度**：重新添加 `.github/workflows/sync.yml`（包含 cron 与状态提交步骤）。

## 字段配置说明

| 字段属性 | 说明 |
|---------|------|
| `name` | 字段名，`timestamp`/`message_id`/`sender` 为内置虚拟字段 |
| `pattern` | Python 正则表达式 |
| `group` | 正则捕获组序号（0=整体匹配，1=第一个括号） |
| `type` | 类型转换：`str`（默认）、`float`、`int`、`date_ms`（`YYYY-MM-DD` 转 GMT+08:00 毫秒） |
| `required` | `true` 时若匹配失败则跳过整条消息 |
| `default` | 匹配失败时的默认值 |
| `strategy` | `regex`（按字段解析）或 `raw`（整条消息写入单列） |
| `field_labels` | 解析字段名到飞书列名的映射 |
| `row_order` | 输出到表格的字段顺序 |

## Telegram API 凭证与 Session

1. 访问 https://my.telegram.org → 登录 → API development tools，获取 `api_id` 和 `api_hash`。
2. 本地执行 `python generate_session.py` 生成 session string。
3. 将 session string 与 `api_id`、`api_hash` 配置为环境变量。

## 飞书应用凭证

1. 访问飞书开放平台 https://open.feishu.cn/ 创建企业自建应用。
2. 开通权限 `sheets:spreadsheet`（表格读写），发布应用，记录 `App ID` 与 `App Secret`。
3. 在飞书表格右上角分享，添加应用为协作者（编辑权限）。
4. 从表格 URL 获取 `spreadsheetToken`（`https://xxx.feishu.cn/sheets/shtXXXXXXXX` 中的 `shtXXXXXXXX`）。
5. 获取多维表格 wiki node token 与 table ID。
