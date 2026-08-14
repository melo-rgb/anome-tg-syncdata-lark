import asyncio
import time
from typing import List, Optional

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import ServerError


async def _fetch(
    session_string,
    api_id,
    api_hash,
    group_id,
    last_message_id,
    bot_username,
    limit,
    max_message_id=None,
):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram session is not authorized. Re-run generate_session.py locally.")

        try:
            group_id_resolved = int(group_id)
        except ValueError:
            group_id_resolved = group_id

        # 分页拉取，避免 limit 截断导致旧消息被永久跳过。
        # min_id/max_id 均为开区间；每页返回最新 limit 条，逐页用最旧 ID 向下翻。
        messages = []
        cursor_max_id = max_message_id
        while True:
            kwargs = {
                "entity": group_id_resolved,
                "limit": limit,
                "min_id": last_message_id,
            }
            if cursor_max_id:
                kwargs["max_id"] = cursor_max_id
            if bot_username:
                kwargs["from_user"] = bot_username.lstrip("@")

            page = await client.get_messages(**kwargs)
            if not page:
                break
            messages.extend(page)
            if len(page) < limit:
                break
            cursor_max_id = page[-1].id

        return list(reversed(messages))
    finally:
        await client.disconnect()


def fetch_new_messages(
    session_string: str,
    api_id: int,
    api_hash: str,
    group_id: str,
    last_message_id: int,
    bot_username: str = "",
    limit: int = 200,
    max_message_id: Optional[int] = None,
    retries: int = 3,
) -> List:
    """
    Fetch messages from a Telegram group newer than last_message_id.
    Retries on transient Telegram server errors (-500).
    """
    for attempt in range(1, retries + 1):
        try:
            return asyncio.run(
                _fetch(
                    session_string,
                    api_id,
                    api_hash,
                    group_id,
                    last_message_id,
                    bot_username,
                    limit,
                    max_message_id,
                )
            )
        except ServerError as e:
            if attempt < retries:
                wait = 5 * attempt
                print(f"[telegram] Server error ({e}), retrying in {wait}s... (attempt {attempt}/{retries})")
                time.sleep(wait)
            else:
                raise
