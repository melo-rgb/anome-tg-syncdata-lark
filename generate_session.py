#!/usr/bin/env python3
"""
本地运行此脚本以生成 Telethon session string。
生成后将输出的字符串添加到 GitHub Actions Secrets 中，命名为 TG_SESSION_STRING。

注意：此脚本只能在本地交互式终端运行，不能在 CI 环境中运行。
"""

import asyncio
import os
import sys


def main():
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        print("错误：此脚本不能在 CI 环境中运行。请在本地执行。", file=sys.stderr)
        sys.exit(1)

    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        print("请先安装依赖：python -m pip install telethon", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("Telethon Session String 生成器")
    print("=" * 60)
    print()

    api_id = input("请输入 TG_API_ID (从 https://my.telegram.org 获取): ").strip()
    api_hash = input("请输入 TG_API_HASH: ").strip()
    phone = input("请输入手机号 (含国家区号，如 +8613800138000): ").strip()

    if not api_id or not api_hash or not phone:
        print("错误：所有字段均为必填", file=sys.stderr)
        sys.exit(1)

    print("\n正在连接 Telegram...")

    async def _generate():
        client = TelegramClient(StringSession(), int(api_id), api_hash)
        await client.start(phone=phone)
        session_string = client.session.save()
        await client.disconnect()
        return session_string

    session_string = asyncio.run(_generate())

    print()
    print("=" * 60)
    print("Session string 生成成功！")
    print("=" * 60)
    print()
    print("请将以下字符串添加到 GitHub → Settings → Secrets → Actions")
    print("Secret 名称：TG_SESSION_STRING")
    print()
    print(session_string)
    print()
    print("警告：此字符串等同于你的账号登录凭证，请勿泄露！")


if __name__ == "__main__":
    main()
