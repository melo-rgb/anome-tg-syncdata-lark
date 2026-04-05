#!/usr/bin/env python3
"""
Telegram → Lark Bitable sync
Reads new bot messages from a Telegram group and syncs to multiple Bitable tables.
"""

import os
import sys

from src import state
from src.lark_writer import LarkWriter
from src.parser import MessageParser
from src.telegram_reader import fetch_new_messages


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"[error] Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def opt_env(name: str) -> str:
    return os.environ.get(name, "").strip()


def build_targets(lark_app_id: str, lark_app_secret: str) -> list:
    """
    Define all sync targets. Each target needs:
      - name: display name for logs
      - parser_config: path to parser config JSON
      - wiki_node_token: Lark wiki node token
      - table_id: Bitable table ID
    Targets with missing env vars are skipped automatically.
    """
    candidates = [
        {
            "name": "BTG",
            "parser_config": "config/parser_config.json",
            "wiki_node_token": opt_env("LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("LARK_TABLE_ID"),
        },
        {
            "name": "BTG VN",
            "parser_config": "config/parser_config_btgvn.json",
            "wiki_node_token": opt_env("BTGVN_LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("BTGVN_LARK_TABLE_ID"),
        },
        {
            "name": "AD",
            "parser_config": "config/parser_config_ad.json",
            "wiki_node_token": opt_env("AD_LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("AD_LARK_TABLE_ID"),
        },
        {
            "name": "Other",
            "parser_config": "config/parser_config_kol.json",
            "wiki_node_token": opt_env("KOL_LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("KOL_LARK_TABLE_ID"),
        },
    ]
    targets = []
    for t in candidates:
        if t["wiki_node_token"] and t["table_id"]:
            t["writer"] = LarkWriter(
                app_id=lark_app_id,
                app_secret=lark_app_secret,
                wiki_node_token=t["wiki_node_token"],
                table_id=t["table_id"],
            )
            targets.append(t)
        else:
            print(f"[config] Skipping target '{t['name']}' (env vars not set)")
    return targets


def sync_target(target: dict, messages: list) -> None:
    name = target["name"]
    parser = MessageParser(config_path=target["parser_config"])
    records = []

    for msg in messages:
        parsed = parser.parse(msg)
        if parsed is None:
            continue
        records.append(parser.to_record(parsed))

    print(f"[{name}] {len(records)} record(s) parsed from {len(messages)} message(s)")

    if not records:
        print(f"[{name}] No records to write.")
        return

    writer: LarkWriter = target["writer"]
    existing_ts = writer.get_recent_timestamps(field_name="日期", n=20)
    new_records = [r for r in records if r["fields"].get("日期") not in existing_ts]
    skipped = len(records) - len(new_records)
    if skipped:
        print(f"[{name}] Skipped {skipped} duplicate record(s)")
    if new_records:
        writer.append_records(new_records)
    else:
        print(f"[{name}] All records already exist, nothing to write.")


def main():
    # ── Load configuration ──────────────────────────────────────────────────
    session_string = require_env("TG_SESSION_STRING")
    api_id = int(require_env("TG_API_ID"))
    api_hash = require_env("TG_API_HASH")
    group_id = require_env("TG_GROUP_ID")
    bot_username = opt_env("BOT_USERNAME")

    lark_app_id = require_env("LARK_APP_ID")
    lark_app_secret = require_env("LARK_APP_SECRET")

    # ── Build sync targets ──────────────────────────────────────────────────
    targets = build_targets(lark_app_id, lark_app_secret)
    if not targets:
        print("[error] No sync targets configured.", file=sys.stderr)
        sys.exit(1)

    # ── Load state ──────────────────────────────────────────────────────────
    last_id = state.load_last_id()
    print(f"[state] Last processed message ID: {last_id}")

    # ── Fetch new Telegram messages (once for all targets) ──────────────────
    print(f"[telegram] Fetching messages from group '{group_id}'" +
          (f" by '{bot_username}'" if bot_username else "") +
          f" (min_id={last_id}) ...")
    messages = fetch_new_messages(
        session_string=session_string,
        api_id=api_id,
        api_hash=api_hash,
        group_id=group_id,
        last_message_id=last_id,
        bot_username=bot_username,
    )
    print(f"[telegram] Fetched {len(messages)} new message(s)")

    if not messages:
        print("[done] No new messages. Exiting.")
        return

    # ── Sync each target ────────────────────────────────────────────────────
    for target in targets:
        sync_target(target, messages)

    # ── Save state ──────────────────────────────────────────────────────────
    newest_id = max(msg.id for msg in messages)
    state.save_last_id(newest_id)
    print(f"[state] Saved last message ID: {newest_id}")
    print("[done] Sync complete.")


if __name__ == "__main__":
    main()
