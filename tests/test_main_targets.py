import os
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("requests", types.ModuleType("requests"))

telethon = types.ModuleType("telethon")
telethon.TelegramClient = object
telethon_sessions = types.ModuleType("telethon.sessions")
telethon_sessions.StringSession = object
telethon_errors = types.ModuleType("telethon.errors")
telethon_errors.ServerError = Exception
sys.modules.setdefault("telethon", telethon)
sys.modules.setdefault("telethon.sessions", telethon_sessions)
sys.modules.setdefault("telethon.errors", telethon_errors)

from main import build_targets


class BuildTargetsTest(unittest.TestCase):
    def test_levelup_uses_separate_group_and_bot_filter(self):
        env = {
            "LEVELUP_TG_GROUP_ID": "-1001234567890",
            "LEVELUP_LARK_WIKI_NODE_TOKEN": "wik-levelup",
            "LEVELUP_LARK_TABLE_ID": "tbl-levelup",
        }
        with patch.dict(os.environ, env, clear=True):
            targets = build_targets("app_id", "app_secret", "-100main", "main_bot")

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["name"], "LevelUp")
        self.assertEqual(targets[0]["group_id"], "-1001234567890")
        self.assertEqual(targets[0]["bot_username"], "")
        self.assertEqual(targets[0]["state_file"], "data/last_message_id_levelup.txt")


if __name__ == "__main__":
    unittest.main()
