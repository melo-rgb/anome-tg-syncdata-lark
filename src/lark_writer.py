import time
from typing import List, Any

import requests

LARK_AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
LARK_APPEND_URL = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values_append"


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
        payload = {
            "valueRange": {
                "range": f"{self.sheet_id}!A1:ZZ1",
                "values": rows,
            }
        }
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Lark append failed: {data.get('msg')} (code={data.get('code')})")

        updated = data.get("data", {}).get("updatedRows", len(rows))
        print(f"[lark] Appended {updated} row(s) to sheet '{self.sheet_id}'")
