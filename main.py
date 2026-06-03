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


def opt_int_env(name: str, default: int) -> int:
    value = opt_env(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        print(f"[config] Invalid integer for {name}: {value!r}; using {default}")
        return default


def build_targets(lark_app_id: str, lark_app_secret: str, default_group_id: str, default_bot_username: str) -> list:
    """
    Define all sync targets. Each target needs:
      - name: display name for logs
      - parser_config: path to parser config JSON
      - group_id: Telegram group ID or username
      - bot_username: optional sender filter
      - state_file: path to last processed message ID
      - wiki_node_token: Lark wiki node token
      - table_id: Bitable table ID
    Targets with missing env vars are skipped automatically.
    """
    candidates = [
        {
            "name": "BTG",
            "parser_config": "config/parser_config.json",
            "group_id": default_group_id,
            "bot_username": default_bot_username,
            "state_file": "data/last_message_id.txt",
            "wiki_node_token": opt_env("LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("LARK_TABLE_ID"),
        },
        {
            "name": "BTG VN",
            "parser_config": "config/parser_config_btgvn.json",
            "group_id": default_group_id,
            "bot_username": default_bot_username,
            "state_file": "data/last_message_id.txt",
            "wiki_node_token": opt_env("BTGVN_LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("BTGVN_LARK_TABLE_ID"),
        },
        {
            "name": "X",
            "parser_config": "config/parser_config_ad.json",
            "group_id": default_group_id,
            "bot_username": default_bot_username,
            "state_file": "data/last_message_id.txt",
            "wiki_node_token": opt_env("AD_LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("AD_LARK_TABLE_ID"),
        },
        {
            "name": "Other",
            "parser_config": "config/parser_config_kol.json",
            "group_id": default_group_id,
            "bot_username": default_bot_username,
            "state_file": "data/last_message_id.txt",
            "wiki_node_token": opt_env("KOL_LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("KOL_LARK_TABLE_ID"),
        },
        {
            "name": "LevelUp",
            "parser_config": "config/parser_config_levelup.json",
            "group_id": opt_env("LEVELUP_TG_GROUP_ID"),
            "bot_username": opt_env("LEVELUP_BOT_USERNAME"),
            "state_file": "data/last_message_id_levelup.txt",
            "wiki_node_token": opt_env("LEVELUP_LARK_WIKI_NODE_TOKEN"),
            "table_id": opt_env("LEVELUP_LARK_TABLE_ID"),
        },
    ]
    targets = []
    for t in candidates:
        if t["group_id"] and t["wiki_node_token"] and t["table_id"]:
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


def sync_target(target: dict, messages: list, dedup_recent_n: int = 500) -> None:
    name = target["name"]
    parser = MessageParser(config_path=target["parser_config"])
    records = []
    unmatched = []

    for msg in messages:
        parsed = parser.parse(msg)
        if parsed is None:
            if parser.last_skip_reason:
                text = (msg.text or msg.message or "").replace("\n", " ")[:120]
                unmatched.append((getattr(msg, "id", ""), parser.last_skip_reason, text))
            continue
        records.append(parser.to_record(parsed))

    print(f"[{name}] {len(records)} record(s) parsed from {len(messages)} message(s)")
    for msg_id, reason, preview in unmatched[:3]:
        print(f"[{name}] Unmatched message {msg_id}: {reason}; preview='{preview}'")
    if len(unmatched) > 3:
        print(f"[{name}] ... {len(unmatched) - 3} more unmatched message(s)")

    if not records:
        print(f"[{name}] No records to write.")
        return

    writer: LarkWriter = target["writer"]
    existing_ts = writer.get_recent_timestamps(field_name="日期", n=dedup_recent_n)
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
    fetch_limit = opt_int_env("TG_FETCH_LIMIT", 200)
    dedup_recent_n = opt_int_env("LARK_DEDUP_RECENT_N", 500)
    backfill_from_id = opt_int_env("BACKFILL_FROM_MESSAGE_ID", 0)
    backfill_to_id = opt_int_env("BACKFILL_TO_MESSAGE_ID", 0)

    is_backfill = backfill_from_id > 0 or backfill_to_id > 0
    if backfill_from_id and backfill_to_id and backfill_to_id < backfill_from_id:
        print("[error] BACKFILL_TO_MESSAGE_ID must be greater than or equal to BACKFILL_FROM_MESSAGE_ID", file=sys.stderr)
        sys.exit(1)

    lark_app_id = require_env("LARK_APP_ID")
    lark_app_secret = require_env("LARK_APP_SECRET")

    # ── Build sync targets ──────────────────────────────────────────────────
    targets = build_targets(lark_app_id, lark_app_secret, group_id, bot_username)
    if not targets:
        print("[error] No sync targets configured.", file=sys.stderr)
        sys.exit(1)

    target_groups = {}
    for target in targets:
        key = (target["group_id"], target["bot_username"], target["state_file"])
        target_groups.setdefault(key, []).append(target)

    # ── Fetch and sync per Telegram group ───────────────────────────────────
    for (target_group_id, target_bot_username, state_file), group_targets in target_groups.items():
        last_id = state.load_last_id(state_file)
        target_names = ", ".join(t["name"] for t in group_targets)
        print(f"[state] {state_file}: last processed message ID: {last_id} ({target_names})")

        min_message_id = max(backfill_from_id - 1, 0) if is_backfill else last_id
        max_message_id = backfill_to_id + 1 if backfill_to_id > 0 else None
        mode = "backfill" if is_backfill else "sync"
        range_text = f"min_id={min_message_id}"
        if max_message_id:
            range_text += f", max_id={max_message_id}"
        print(f"[telegram] Fetching messages from group '{target_group_id}'" +
              (f" by '{target_bot_username}'" if target_bot_username else "") +
              f" for {target_names} ({mode}, {range_text}, limit={fetch_limit}) ...")
        messages = fetch_new_messages(
            session_string=session_string,
            api_id=api_id,
            api_hash=api_hash,
            group_id=target_group_id,
            last_message_id=min_message_id,
            bot_username=target_bot_username,
            limit=fetch_limit,
            max_message_id=max_message_id,
        )
        print(f"[telegram] Fetched {len(messages)} message(s) for {target_names}")

        if not messages:
            print(f"[{target_names}] No new messages.")
            continue

        for target in group_targets:
            sync_target(target, messages, dedup_recent_n=dedup_recent_n)

        if is_backfill:
            print(f"[state] Backfill mode: {state_file} was not updated")
            continue

        newest_id = max(msg.id for msg in messages)
        state.save_last_id(newest_id, state_file)
        print(f"[state] Saved {state_file}: {newest_id}")

    if is_backfill:
        print("[done] Backfill complete.")
        return

    print("[done] Sync complete.")


if __name__ == "__main__":
    main()
