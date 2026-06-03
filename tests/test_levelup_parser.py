import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from src.parser import MessageParser


SAMPLE_MESSAGE = """LevelUp | ANOME ONE 任务数据播报
统计时间：GMT+08:00 2026-06-02
1. 今日渠道访问用户数：1,289（累计 138,817）
2. 今日新用户 / 总用户量：81 / 34,868
3. 今日完成任务的用户：613
4. 今日活跃用户：1,311
5. 今日每阶段任务完成数新增：[通用版] 1: 47 | 2: 130 | 3: 13 | 4: 0 | 5: 0 | 6: 0
   [越南版] 1: 0 | 2: 0 | 3: 0 | 4: 0
6. 每阶段任务完成总数：[通用版] 1: 18,201 | 2: 7,214 | 3: 723 | 4: 11 | 5: 0 | 6: 0
   [越南版] 1: 1 | 2: 0 | 3: 0 | 4: 0
7. 伞下入金数量：今日 60.00 USDT | 总计 2790.00 USDT
8. 伞下地址数量：今日新增 140 | 总计 16,967
"""


class LevelUpParserTest(unittest.TestCase):
    def test_parse_levelup_report(self):
        parser = MessageParser("config/parser_config_levelup.json")
        message = SimpleNamespace(
            text=SAMPLE_MESSAGE,
            message=SAMPLE_MESSAGE,
            date=datetime(2026, 6, 2, 15, 55, tzinfo=timezone.utc),
            id=1,
            sender=SimpleNamespace(username="bot"),
        )

        record = parser.to_record(parser.parse(message))
        fields = record["fields"]

        self.assertEqual(fields["日期"], 1780329600000)
        self.assertEqual(fields["今日渠道访问用户数"], 1289)
        self.assertEqual(fields["渠道访问累计用户数"], 138817)
        self.assertEqual(fields["今日新用户"], 81)
        self.assertEqual(fields["总用户量"], 34868)
        self.assertEqual(fields["今日完成任务的用户"], 613)
        self.assertEqual(fields["今日活跃用户"], 1311)
        self.assertEqual(fields["今日每阶段任务完成数新增第一期_通用"], 47)
        self.assertEqual(fields["今日每阶段任务完成数新增第二期_通用"], 130)
        self.assertEqual(fields["今日每阶段任务完成数新增第三期_通用"], 13)
        self.assertEqual(fields["每阶段任务完成总数第一期_通用"], 18201)
        self.assertEqual(fields["每阶段任务完成总数第二期_通用"], 7214)
        self.assertEqual(fields["每阶段任务完成总数第三期_通用"], 723)
        self.assertEqual(fields["每阶段任务完成总数第四期_通用"], 11)
        self.assertEqual(fields["每阶段任务完成总数第一期_越南"], 1)
        self.assertEqual(fields["今日完成新手领取任务量"], 0)
        self.assertEqual(fields["今日完成新手领取任务总量"], 0)
        self.assertEqual(fields["伞下入金数量今日"], 60.0)
        self.assertEqual(fields["伞下入金数量总量"], 2790.0)
        self.assertEqual(fields["伞下地址数量今日新增"], 140)
        self.assertEqual(fields["伞下地址数量总计"], 16967)


if __name__ == "__main__":
    unittest.main()
