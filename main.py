#!/usr/bin/env python3
"""
Telegram → Lark Bitable sync
Reads new bot messages from a Telegram group and appends them to a Lark Bitable table.
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


def main():
    # ── Load configuration ──────────────────────────────────────────────────
    session_string = require_env("TG_SESSION_STRING")
    api_id = int(require_env("TG_API_ID"))
    api_hash = require_env("TG_API_HASH")
    group_id = require_env("TG_GROUP_ID")
    bot_username = os.environ.get("BOT_USERNAME", "").strip()

    lark_app_id = require_env("LARK_APP_ID")
    lark_app_secret = require_env("LARK_APP_SECRET")
    lark_wiki_node_token = require_env("LARK_WIKI_NODE_TOKEN")  
    lark_table_id = require_env("LARK_TABLE_ID")                

    # ── Load state ──────────────────────────────────────────────────────────
    last_id = state.load_last_id()
    print(f"[state] Last processed message ID: {last_id}")

    # ── Fetch new Telegram messages ─────────────────────────────────────────
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

    # ── Parse messages ──────────────────────────────────────────────────────
    parser = MessageParser()
    records = []
    newest_id = last_id

    for msg in messages:
        parsed = parser.parse(msg)
        if parsed is None:
            print(f"[parser] Skipped message {msg.id} (no match)")
            newest_id = max(newest_id, msg.id)
            continue
        record = parser.to_record(parsed)
        records.append(record)
        newest_id = max(newest_id, msg.id)
        print(f"[parser] Parsed message {msg.id}: {record['fields']}")

    print(f"[parser] {len(records)} record(s) parsed from {len(messages)} message(s)")

    # ── Write to Lark Bitable (with dedup) ─────────────────────────────────
    writer = LarkWriter(
        app_id=lark_app_id,
        app_secret=lark_app_secret,
        wiki_node_token=lark_wiki_node_token,
        table_id=lark_table_id,
    )

    if records:
        existing_ts = writer.get_recent_timestamps(field_name="日期", n=20)
        new_records = [
            r for r in records
            if r["fields"].get("日期") not in existing_ts
        ]
        skipped = len(records) - len(new_records)
        if skipped:
            print(f"[dedup] Skipped {skipped} duplicate record(s)")
        if new_records:
            writer.append_records(new_records)
        else:
            print("[lark] All records already exist, nothing to write.")
    else:
        print("[lark] No records to write.")

    # ── Save state ──────────────────────────────────────────────────────────
    state.save_last_id(newest_id)
    print(f"[state] Saved last message ID: {newest_id}")
    print("[done] Sync complete.")


if __name__ == "__main__":
    main()
