# Telegram → Lark 数据同步

自动将 Telegram 群组中 bot 播报的消息同步到飞书（Lark）表格。

## 工作原理

1. GitHub Actions 定时触发（默认每 30 分钟）
2. 用 Telethon 读取 TG 群组中新的 bot 消息
3. 用正则规则解析消息内容
4. 将解析结果追加到飞书表格

---

## 快速开始

### 第一步：获取 Telegram API 凭证

1. 访问 https://my.telegram.org → 登录 → API development tools
2. 创建应用，获取 `api_id` 和 `api_hash`

### 第二步：生成 Telethon Session String（本地执行）

```bash
pip install telethon
python generate_session.py
```

按提示输入手机号和验证码，脚本会输出 session string。

### 第三步：获取飞书应用凭证

1. 访问飞书开放平台 https://open.feishu.cn/
2. 创建企业自建应用
3. 开通权限：`sheets:spreadsheet`（表格读写）
4. 发布应用，记录 `App ID` 和 `App Secret`
5. 在飞书表格右上角分享，添加应用为协作者（编辑权限）
6. 从表格 URL 获取 `spreadsheetToken`：
   - URL 格式：`https://xxx.feishu.cn/sheets/shtXXXXXXXX`
   - `shtXXXXXXXX` 即为 `LARK_SPREADSHEET_TOKEN`

### 第四步：在 GitHub 配置 Secrets 和 Variables

进入 GitHub repo → **Settings** → **Secrets and variables** → **Actions**

**Secrets（敏感信息）：**

| Name | 说明 |
|------|------|
| `TG_SESSION_STRING` | 第二步生成的 session string |
| `TG_API_ID` | Telegram API ID |
| `TG_API_HASH` | Telegram API Hash |
| `LARK_APP_ID` | 飞书应用 App ID |
| `LARK_APP_SECRET` | 飞书应用 App Secret |

**Variables（非敏感配置）：**

| Name | 示例值 | 说明 |
|------|--------|------|
| `TG_GROUP_ID` | `-1001234567890` | 群组 ID（负数）或 `@username` |
| `BOT_USERNAME` | `my_signal_bot` | 只读此 bot 的消息（留空则读所有人） |
| `LARK_SPREADSHEET_TOKEN` | `shtXXXXXXXX` | 飞书表格 token |
| `LARK_SHEET_ID` | `Sheet1` | 工作表名称 |

> 获取 TG 群组 ID：将 bot `@userinfobot` 加入群组，发送任意消息即可看到群组 ID

### 第五步：配置消息解析规则

编辑 [config/parser_config.json](config/parser_config.json) 以匹配你的 bot 消息格式。

示例 bot 消息：
```
Symbol: BTC/USDT
Action: BUY
Price: 65000.00
Amount: 0.1
Note: 突破关键阻力位
```

对应配置（默认配置已包含此示例）：
```json
{
  "strategy": "regex",
  "fields": [
    { "name": "timestamp" },
    { "name": "symbol", "pattern": "Symbol:\\s*(\\S+)", "group": 1 },
    { "name": "action", "pattern": "(BUY|SELL)", "group": 1 },
    { "name": "price", "pattern": "Price:\\s*([\\d,.]+)", "group": 1, "type": "float" }
  ],
  "row_order": ["timestamp", "symbol", "action", "price"]
}
```

如果消息格式无规律，可设置 `"strategy": "raw"` 将整条消息写入表格。

### 第六步：手动触发测试

1. 进入 GitHub repo → **Actions** → **Sync Telegram to Lark**
2. 点击 **Run workflow**
3. 查看日志确认运行正常

---

## 调整同步频率

编辑 [.github/workflows/sync.yml](.github/workflows/sync.yml) 中的 cron 表达式：

```yaml
schedule:
  - cron: '*/30 * * * *'  # 每 30 分钟
  # - cron: '0 * * * *'   # 每小时
  # - cron: '0 */6 * * *' # 每 6 小时
```

> GitHub Actions 免费版每月有 2000 分钟额度，每 30 分钟运行一次约需 ~1440 分钟/月（单次运行约 1 分钟）。

---

## 字段配置说明

| 字段属性 | 说明 |
|---------|------|
| `name` | 字段名，`timestamp`/`message_id`/`sender` 为内置虚拟字段 |
| `pattern` | Python 正则表达式 |
| `group` | 正则捕获组序号（0=整体匹配，1=第一个括号） |
| `type` | 类型转换：`str`（默认）、`float`、`int` |
| `required` | `true` 时若匹配失败则跳过整条消息 |
| `default` | 匹配失败时的默认值 |
