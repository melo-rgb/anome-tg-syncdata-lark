import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from src.parser import MessageParser


SAMPLE_MESSAGE = """LevelUp 每日数据播报
统计日期：2026-08-13（GMT+8）
播报时间：2026-08-14 00:20:11
1. 页面访问：4,432
   访问详情：/home 976 次、/level 834 次、/arena 797 次、/quest/Levelup-ocean-Q0804 14,958 次
2. 访问会话：458
3. 新用户注册：15
4. 活跃用户：198
5. 完成 Quest 用户：13
6. 签到用户：49
7. NU World 参与人数（不含机器人）：42
8. NU World 成交总量：98.00 USDT
"""


class NUWorldParserTest(unittest.TestCase):
    def test_parse_nuworld_report(self):
        parser = MessageParser("config/parser_config_nuworld.json")
        message = SimpleNamespace(
            text=SAMPLE_MESSAGE,
            message=SAMPLE_MESSAGE,
            date=datetime(2026, 8, 13, 16, 20, 11, tzinfo=timezone.utc),
            id=1,
            sender=SimpleNamespace(username="bot"),
        )

        record = parser.to_record(parser.parse(message))
        fields = record["fields"]

        self.assertEqual(fields["日期"], 1786550400000)
        self.assertEqual(fields["页面访问"], 4432)
        self.assertEqual(fields["访问详情：/home"], 976)
        self.assertEqual(fields["访问详情：/level"], 834)
        self.assertEqual(fields["访问详情：/arena"], 797)
        self.assertEqual(fields["访问详情：/quest/Levelup-ocean-Q0804"], 14958)
        self.assertEqual(fields["访问会话"], 458)
        self.assertEqual(fields["新用户注册"], 15)
        self.assertEqual(fields["活跃用户"], 198)
        self.assertEqual(fields["完成 Quest 用户"], 13)
        self.assertEqual(fields["签到用户"], 49)
        self.assertEqual(fields["NU World 参与人数（不含机器人）"], 42)
        self.assertEqual(fields["NU World 成交总量"], 98.0)


if __name__ == "__main__":
    unittest.main()
