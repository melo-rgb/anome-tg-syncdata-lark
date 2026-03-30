#!/usr/bin/env python3
"""
Telegram → Lark spreadsheet sync
Reads new bot messages from a Telegram group and appends them to a Lark sheet.
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
    lark_spreadsheet_token = require_env("LARK_SPREADSHEET_TOKEN")
    lark_sheet_id = os.environ.get("LARK_SHEET_ID", "Sheet1").strip()

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
    rows = []
    newest_id = last_id

    for msg in messages:
        parsed = parser.parse(msg)
        if parsed is None:
            print(f"[parser] Skipped message {msg.id} (no match)")
            newest_id = max(newest_id, msg.id)
            continue
        row = parser.to_row(parsed)
        rows.append(row)
        newest_id = max(newest_id, msg.id)
        print(f"[parser] Parsed message {msg.id}: {row}")

    print(f"[parser] {len(rows)} row(s) parsed from {len(messages)} message(s)")

    # ── Write to Lark ───────────────────────────────────────────────────────
    if rows:
        writer = LarkWriter(
            app_id=lark_app_id,
            app_secret=lark_app_secret,
            spreadsheet_token=lark_spreadsheet_token,
            sheet_id=lark_sheet_id,
        )
        writer.append_rows(rows)
    else:
        print("[lark] No rows to write.")

    # ── Save state ──────────────────────────────────────────────────────────
    state.save_last_id(newest_id)
    print(f"[state] Saved last message ID: {newest_id}")
    print("[done] Sync complete.")


if __name__ == "__main__":
    main()
