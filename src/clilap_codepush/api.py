"""HTTP client for codepush.clilap.org API — stdlib only."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error
from typing import Any

BASE_URL = os.environ.get("CODEPUSH_URL", "https://codepush.clilap.org")

class ApiError(Exception):
    def __init__(self, msg: str, status: int = 0):
        super().__init__(msg)
        self.status = status

def _req(method: str, url: str, *, data: bytes | None = None,
         headers: dict | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, method=method,
                                  headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        raise ApiError(str(e))

def _json(method: str, url: str, **kw) -> Any:
    status, body = _req(method, url, **kw)
    try:
        data = json.loads(body)
    except Exception:
        raise ApiError(body.decode(errors="replace"), status)
    if status >= 400:
        raise ApiError(data.get("error", str(data)), status)
    return data

# ── Public API ────────────────────────────────────────────────────────────────

def upload(content: bytes, filename: str, *, ttl: int | None = None,
           group: str | None = None, token: str | None = None) -> dict:
    # POST / でアップロード、ファイル名はX-Filenameヘッダー、TTLはX-Expireヘッダー
    qs: dict[str, str] = {}
    if group: qs["group"] = group
    if token: qs["token"] = token
    url = f"{BASE_URL}/"
    if qs:
        url += "?" + urllib.parse.urlencode(qs)
    hdrs = {
        "Content-Type": "application/octet-stream",
        "X-Filename": filename,
        "Accept": "application/json",
    }
    if ttl is not None:
        hdrs["X-Expire"] = f"{ttl}s"
    return _json("POST", url, data=content, headers=hdrs)

def get_raw(paste_id: str) -> bytes:
    url = f"{BASE_URL}/{paste_id}/raw"
    status, body = _req("GET", url)
    if status >= 400:
        raise ApiError(body.decode(errors="replace"), status)
    return body

def delete_by_key(delete_key: str) -> str:
    """delete_key でペースト削除 (DELETE /cp with key=...)"""
    data = urllib.parse.urlencode({"key": delete_key}).encode()
    status, body = _req("DELETE", f"{BASE_URL}/cp",
                        data=data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"})
    return body.decode(errors="replace")

def update_paste(paste_id: str, delete_key: str, content: bytes, filename: str) -> str:
    """delete_key でペースト上書き (PUT /cp/{id})"""
    qs = urllib.parse.urlencode({"key": delete_key, "filename": filename})
    url = f"{BASE_URL}/cp/{paste_id}?{qs}"
    status, body = _req("PUT", url, data=content,
                        headers={"Content-Type": "application/octet-stream"})
    return body.decode(errors="replace")

def get_diff(id1: str, id2: str) -> str:
    """2ペーストの diff テキストを返す"""
    status, body = _req("GET", f"{BASE_URL}/diff/{id1}/{id2}")
    return body.decode(errors="replace")

def health() -> dict:
    return _json("GET", f"{BASE_URL}/cp/health?format=json")

def check_exists(paste_id: str) -> bool:
    """paste_id がサーバー上に存在するか（期限切れ・削除済みでないか）"""
    status, _ = _req("GET", f"{BASE_URL}/stats/{paste_id}",
                      headers={"Accept": "application/json"})
    return status < 400
