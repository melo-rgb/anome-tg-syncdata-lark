import asyncio
import os
from typing import List

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message


def fetch_new_messages(
    session_string: str,
    api_id: int,
    api_hash: str,
    group_id: str,
    last_message_id: int,
    bot_username: str = "",
    limit: int = 200,
) -> List[Message]:
    """
    Fetch messages from a Telegram group that are newer than last_message_id.
    Optionally filter by bot_username (sender).
    Returns messages sorted oldest-first.
    """

    async def _fetch():
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.start()
        try:
            # Resolve group entity
            try:
                group_id_resolved = int(group_id)
            except ValueError:
                group_id_resolved = group_id  # username like "@mygroup"

            kwargs = {
                "entity": group_id_resolved,
                "limit": limit,
                "min_id": last_message_id,
            }
            # Filter by sender if specified
            if bot_username:
                sender = bot_username.lstrip("@")
                kwargs["from_user"] = sender

            messages = await client.get_messages(**kwargs)
            # get_messages returns newest-first; reverse for chronological order
            return list(reversed(messages))
        finally:
            await client.disconnect()

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_fetch())
    finally:
        loop.close()
