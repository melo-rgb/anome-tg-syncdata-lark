import json
import time
from typing import List, Dict, Any

import requests

LARK_AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
LARK_WIKI_NODE_URL = "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node"
LARK_BITABLE_RECORDS_URL = (
    "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
)
LARK_BITABLE_BATCH_CREATE_URL = (
    "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
)


class LarkWriter:
    def __init__(self, app_id: str, app_secret: str, wiki_node_token: str, table_id: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.wiki_node_token = wiki_node_token
        self.table_id = table_id
        self._access_token: str = ""
        self._token_expires_at: float = 0.0
        self._bitable_app_token: str = ""

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

    def _resolve_bitable_token(self) -> str:
        if self._bitable_app_token:
            return self._bitable_app_token
        token = self._get_token()
        resp = requests.get(
            LARK_WIKI_NODE_URL,
            params={"token": self.wiki_node_token},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if not resp.ok:
            raise RuntimeError(f"Wiki node lookup failed: HTTP {resp.status_code}\n{resp.text}")
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Wiki node lookup failed: {data.get('msg')} (code={data.get('code')})")
        node = data["data"]["node"]
        self._bitable_app_token = node["obj_token"]

        return self._bitable_app_token

    def get_recent_timestamps(self, field_name: str = "日期", n: int = 20) -> set:
        """
        Fetch the last n records sorted by field_name descending,
        return a set of timestamp values for deduplication.
        """
        app_token = self._resolve_bitable_token()
        token = self._get_token()
        url = LARK_BITABLE_RECORDS_URL.format(app_token=app_token, table_id=self.table_id)
        resp = requests.get(
            url,
            params={
                "page_size": n,
                "sort": json.dumps([{"field_name": field_name, "desc": True}], ensure_ascii=False),
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Lark list records failed: {data.get('msg')} (code={data.get('code')})")
        items = data.get("data", {}).get("items", [])
        timestamps = set()
        for item in items:
            val = item.get("fields", {}).get(field_name)
            if val is not None:
                timestamps.add(val)
        print(f"[dedup] Fetched {len(timestamps)} existing timestamp(s)")
        return timestamps

    def append_records(self, records: List[Dict[str, Any]]) -> None:
        """
        records: list of dicts, e.g. [{"fields": {"日期": "2026-03-30", ...}}, ...]
        """
        if not records:
            return

        app_token = self._resolve_bitable_token()
        token = self._get_token()
        url = LARK_BITABLE_BATCH_CREATE_URL.format(
            app_token=app_token, table_id=self.table_id
        )
        # Bitable batch_create limit is 500 records per request
        for i in range(0, len(records), 500):
            batch = records[i : i + 500]
            resp = requests.post(
                url,
                json={"records": batch},
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if not resp.ok:
                raise RuntimeError(
                    f"Bitable batch_create failed: HTTP {resp.status_code}\n{resp.text}"
                )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(
                    f"Bitable batch_create failed: {data.get('msg')} (code={data.get('code')})\n{resp.text}"
                )
            created = len(data.get("data", {}).get("records", batch))
            print(f"[lark] Created {created} record(s) in table '{self.table_id}'")
