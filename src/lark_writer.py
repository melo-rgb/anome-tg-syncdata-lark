import time
from typing import List, Any

import requests

LARK_AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
LARK_APPEND_URL = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values_append"


def _col_letter(n: int) -> str:
    """Convert 1-based column number to Excel-style letter (1→A, 26→Z, 27→AA)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


class LarkWriter:
    def __init__(self, app_id: str, app_secret: str, spreadsheet_token: str, sheet_id: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.spreadsheet_token = spreadsheet_token
        self.sheet_id = sheet_id
        self._access_token: str = ""
        self._token_expires_at: float = 0.0

    def _get_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        resp = requests.post(
            LARK_AUTH_URL,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Lark auth failed: {data.get('msg')} (code={data.get('code')})")

        self._access_token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data.get("expire", 7200)
        return self._access_token

    def append_rows(self, rows: List[List[Any]]) -> None:
        if not rows:
            return

        token = self._get_token()
        url = LARK_APPEND_URL.format(token=self.spreadsheet_token)

        # 根据数据列数生成列字母范围，如 15 列 → A:O
        col_count = len(rows[0]) if rows else 1
        end_col = _col_letter(col_count)
        range_str = f"{self.sheet_id}!A1:{end_col}1"

        payload = {
            "valueRange": {
                "range": range_str,
                "values": rows,
            }
        }
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            params={"insertDataOption": "INSERT_ROWS"},
            timeout=15,
        )
        if not resp.ok:
            raise RuntimeError(
                f"Lark append failed: HTTP {resp.status_code}\n{resp.text}"
            )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Lark append failed: {data.get('msg')} (code={data.get('code')})\n{resp.text}")

        updated = data.get("data", {}).get("updatedRows", len(rows))
        print(f"[lark] Appended {updated} row(s) to sheet '{self.sheet_id}'")
