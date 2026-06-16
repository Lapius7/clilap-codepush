"""HTTP client for codepush.clilap.org API — stdlib only."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error
from typing import Any

BASE_URL = os.environ.get("CODEPUSH_URL", "https://codepush.clilap.org")
ADMIN_URL = os.environ.get("CODEPUSH_ADMIN_URL", "https://admin.clilap.org")

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
    qs: dict[str, str] = {"filename": filename}
    if ttl is not None: qs["ttl"] = str(ttl)
    if group:           qs["group"] = group
    if token:           qs["token"] = token
    url = f"{BASE_URL}/paste?{urllib.parse.urlencode(qs)}"
    hdrs = {"Content-Type": "application/octet-stream"}
    return _json("POST", url, data=content, headers=hdrs)

def get_raw(paste_id: str) -> bytes:
    url = f"{BASE_URL}/paste/{paste_id}/raw"
    status, body = _req("GET", url)
    if status >= 400:
        raise ApiError(body.decode(errors="replace"), status)
    return body

def delete_paste(paste_id: str, token: str) -> dict:
    url = f"{BASE_URL}/paste/{paste_id}?token={urllib.parse.quote(token)}"
    return _json("DELETE", url)

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
    return _json("GET", f"{ADMIN_URL}/cp/health?format=json")

# ── Admin API ─────────────────────────────────────────────────────────────────

class AdminApi:
    def __init__(self, token: str):
        self.token = token

    def _url(self, path: str, **extra) -> str:
        params = {"token": self.token, **extra}
        return f"{ADMIN_URL}/admin/cp{path}?{urllib.parse.urlencode(params)}"

    def _get(self, path: str, **extra) -> Any:
        return _json("GET", self._url(path, **extra))

    def _delete(self, path: str) -> Any:
        return _json("DELETE", self._url(path))

    def _post(self, path: str, body: dict) -> Any:
        data = json.dumps(body).encode()
        url = self._url(path)
        return _json("POST", url, data=data,
                     headers={"Content-Type": "application/json"})

    def stats(self) -> dict:
        return self._get("/stats")

    def pastes(self, *, page: int = 1, limit: int = 20,
               search: str = "") -> dict:
        kw: dict = {"page": page, "limit": limit}
        if search: kw["search"] = search
        return self._get("/pastes", **kw)

    def paste(self, pid: str) -> dict:
        return self._get(f"/paste/{pid}")

    def paste_content(self, pid: str) -> str:
        status, body = _req("GET", self._url(f"/paste/{pid}/content"))
        if status >= 400:
            raise ApiError(body.decode(errors="replace"), status)
        return body.decode(errors="replace")

    def delete_paste(self, pid: str) -> dict:
        return self._delete(f"/paste/{pid}")

    def groups(self, *, page: int = 1, limit: int = 20) -> dict:
        return self._get("/groups", page=page, limit=limit)

    def group(self, gid: str) -> dict:
        return self._get(f"/group/{gid}")

    def delete_group(self, gid: str) -> dict:
        return self._delete(f"/group/{gid}")

    def purge(self, *, expired: bool = True, orphan: bool = False) -> dict:
        kw: dict = {}
        if expired: kw["expired"] = "1"
        if orphan:  kw["orphan"]  = "1"
        url = self._url("/purge", **kw)
        return _json("POST", url, data=b"")
