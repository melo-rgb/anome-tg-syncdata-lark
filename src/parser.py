"""
Configurable message parser.

Edit config/parser_config.json to match your bot's message format.
No Python changes needed for common regex-based formats.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "parser_config.json")


class MessageParser:
    def __init__(self, config_path: str = CONFIG_PATH):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.fields = self.config.get("fields", [])
        self.row_order = self.config.get("row_order", [])
        self.strategy = self.config.get("strategy", "regex")
        self.last_skip_reason = ""

    def parse(self, message) -> Optional[Dict[str, Any]]:
        """
        Parse a Telethon Message object.
        Returns a dict of field_name -> value, or None if the message doesn't match.
        """
        text = message.text or message.message or ""
        self.last_skip_reason = ""
        if not text:
            self.last_skip_reason = "empty message text"
            return None

        if self.strategy == "regex":
            return self._parse_regex(text, message)
        elif self.strategy == "raw":
            # Return the full message text as a single column
            return {"text": text, "timestamp": _format_ts(message.date)}
        else:
            raise ValueError(f"Unknown parser strategy: {self.strategy}")

    def _parse_regex(self, text: str, message) -> Optional[Dict[str, Any]]:
        result: Dict[str, Any] = {}

        for field in self.fields:
            name = field["name"]

            # Built-in virtual fields
            if name == "timestamp":
                result[name] = _format_ts(message.date)
                continue
            if name == "message_id":
                result[name] = str(message.id)
                continue
            if name == "sender":
                sender = getattr(message.sender, "username", None) or getattr(
                    message.sender, "first_name", ""
                )
                result[name] = sender or ""
                continue

            pattern = field.get("pattern", "")
            group = field.get("group", 0)
            required = field.get("required", False)
            default = field.get("default", "")

            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    raw_value = match.group(group)
                except IndexError:
                    raw_value = match.group(0)

                # Type casting
                field_type = field.get("type", "str")
                result[name] = _cast(raw_value, field_type)
            else:
                if required:
                    self.last_skip_reason = f"required field '{name}' did not match pattern: {pattern}"
                    return None  # Required field missing — skip this message
                result[name] = default

        return result if result else None

    def to_record(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parsed dict to Bitable record format: {"fields": {"列名": value, ...}}"""
        labels = self.config.get("field_labels", {})
        fields = {}
        order = self.row_order if self.row_order else list(parsed.keys())
        for key in order:
            if key not in parsed:
                continue
            label = labels.get(key, key)
            fields[label] = parsed[key]
        return {"fields": fields}


def _format_ts(dt) -> int:
    """Return Unix timestamp in milliseconds (required by Lark Bitable date fields)."""
    if dt is None:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _cast(value: str, field_type: str) -> Any:
    value = value.strip()
    if field_type == "float":
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return value
    elif field_type == "int":
        try:
            return int(value.replace(",", ""))
        except ValueError:
            return value
    elif field_type == "date_ms":
        try:
            tz = timezone(timedelta(hours=8))
            dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=tz)
            return int(dt.timestamp() * 1000)
        except ValueError:
            return value
    elif field_type == "datetime_ms":
        try:
            tz = timezone(timedelta(hours=8))
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            return int(dt.timestamp() * 1000)
        except ValueError:
            return value
    return value
