"""clilap codepush CLI — interactive TUI entry point."""
from __future__ import annotations
import sys, os, json, pathlib, datetime, re

from . import __version__
from . import ui
from .api import (
    AdminApi, ApiError, upload, get_raw, delete_paste, health,
    delete_by_key, update_paste, get_diff,
    BASE_URL, ADMIN_URL,
)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = pathlib.Path.home() / ".config" / "clilap-codepush" / "config.json"
KEYS_PATH   = pathlib.Path.home() / ".config" / "clilap-codepush" / "keys.json"

def _load_cfg() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}

def _save_cfg(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))

def _load_keys() -> dict:
    if KEYS_PATH.exists():
        try:
            return json.loads(KEYS_PATH.read_text())
        except Exception:
            pass
    return {}

def _save_key(paste_id: str, delete_key: str, filename: str) -> None:
    keys = _load_keys()
    keys[paste_id] = {"delete_key": delete_key, "filename": filename,
                      "uploaded_at": datetime.datetime.now().isoformat()}
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYS_PATH.write_text(json.dumps(keys, indent=2))

def _remove_key(paste_id: str) -> None:
    keys = _load_keys()
    keys.pop(paste_id, None)
    KEYS_PATH.write_text(json.dumps(keys, indent=2))

# ── Helpers ───────────────────────────────────────────────────────────────────
R   = ui.R; D = ui.D; BC = ui.BC; BG = ui.BG; BY = ui.BY; BW = ui.BW
BR  = ui.BR; DC = ui.DC

def _ts(iso: str | None) -> str:
    if not iso: return f"{D}—{R}"
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso[:16]

def _size(n: int | None) -> str:
    if n is None: return f"{D}—{R}"
    if n < 1024:   return f"{n}B"
    if n < 1048576: return f"{n/1024:.1f}KB"
    return f"{n/1048576:.1f}MB"

def _short(s: str | None, n: int = 8) -> str:
    if not s: return f"{D}—{R}"
    return s[:n]

# ── Screens ───────────────────────────────────────────────────────────────────

def screen_setup() -> None:
    ui.clear()
    ui.wl(ui.header("clilap codepush セットアップ"))
    ui.wl()
    ui.wl(f"  管理者トークンを入力してください。")
    ui.wl(f"  {D}admin.clilap.org/cp?token=... のトークン{R}")
    ui.wl()
    token = ui.prompt("トークン:")
    if not token:
        return
    cfg = _load_cfg()
    cfg["admin_token"] = token
    _save_cfg(cfg)
    ui.wl(f"  {BG}✓ 保存しました{R}: {CONFIG_PATH}")

def screen_health() -> None:
    err = None
    data = None
    with ui.Spinner("サーバー状態確認中..."):
        try:
            data = health()
        except ApiError as e:
            err = e
        except Exception as e:
            err = e
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}clilap.org/codepush  サーバー状態{R}")
    ui.wl(ui.div())
    if err is not None:
        ui.wl(f"  {BR}✗ サーバーに接続できません{R}")
        ui.wl(f"  {D}{err}{R}")
    else:
        ok     = data.get("ok", False)
        db_ok  = data.get("db_ok", False)
        issues = data.get("issues", [])
        status_str = f"{BG}✓ オンライン{R}" if ok else f"{BR}✗ 問題あり{R}"
        db_str     = f"{BG}ok{R}"           if db_ok else f"{BR}error{R}"
        paste_count = data.get("paste_count")
        count_str = f"{BW}{paste_count:,}{R} ファイル" if paste_count is not None else f"{D}—{R}"
        ui.wl(ui.detail_row("ステータス",   status_str))
        ui.wl(ui.detail_row("データベース", db_str))
        ui.wl(ui.detail_row("総ファイル数", count_str))
        ui.wl(ui.detail_row("サービスURL",  f"{D}codepush.clilap.org{R}"))
        if issues:
            ui.wl(ui.div())
            for issue in issues:
                ui.wl(f"  {BR}• {issue}{R}")
    ui.wl(ui.sep())
    ui.wait_key()

def screen_upload(args_file: str | None = None) -> None:
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイルアップロード{R}")
    ui.wl(ui.div())

    if args_file:
        path = pathlib.Path(args_file)
    else:
        raw = ui.prompt("ファイルパス:")
        if raw is None: return
        path = pathlib.Path(raw)

    if not path.exists():
        ui.wl(f"  {BR}✗ ファイルが見つかりません: {path}{R}")
        ui.wait_key()
        return

    filename = path.name
    ttl_choice = ui.menu("有効期限", [
        {"label": "無期限",  "value": "0"},
        {"label": "1時間",   "value": str(3600)},
        {"label": "1日",     "value": str(86400)},
        {"label": "7日",     "value": str(86400 * 7)},
        {"label": "30日",    "value": str(86400 * 30)},
    ], back=True)
    if ttl_choice is None: return
    ttl = int(ttl_choice) if ttl_choice != "0" else None
    group = ui.prompt("グループID (空=なし):", allow_empty=True) or None
    cfg = _load_cfg()
    token = cfg.get("admin_token") or ui.prompt("トークン:", allow_empty=True) or None

    err = None
    result = None
    with ui.Spinner(f"アップロード中: {filename}"):
        try:
            result = upload(path.read_bytes(), filename, ttl=ttl, group=group, token=token)
        except ApiError as e:
            err = e

    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイルアップロード{R}")
    ui.wl(ui.div())
    if err is not None:
        ui.wl(f"  {BR}✗ {err}{R}")
    else:
        pid = result.get("id", "")
        dk  = result.get("delete_key", "")
        if pid and dk:
            _save_key(pid, dk, filename)
        ui.wl(f"  {BG}✓ アップロード完了{R}")
        ui.wl(ui.detail_row("ID",       pid))
        ui.wl(ui.detail_row("URL",      f"{BASE_URL}/paste/{pid}/raw"))
        if dk:
            ui.wl(ui.detail_row("管理キー", f"{BR}{dk}{R}  {D}(~/.config/clilap-codepush/keys.json に保存済み){R}"))
    ui.wl(ui.sep())
    ui.wait_key()

def screen_get(args_id: str | None = None) -> None:
    def _draw():
        ui.clear()
        ui.wl(ui.sep())
        ui.wl(f"  {BC}ペースト取得{R}")
        ui.wl(ui.div())

    _draw()
    pid = args_id or ui.prompt("Paste ID:")
    if not pid:
        return

    err = None
    data = None
    with ui.Spinner("取得中..."):
        try:
            data = get_raw(pid)
        except ApiError as e:
            err = e

    if err is not None:
        _draw()
        ui.wl(f"  {BR}✗ {err}{R}")
        ui.wl()
        ui.wl(f"  ペーストが見つかりません。削除済みか期限切れの可能性があります。")
        ui.wl()
        ui.wl(f"  {D}clilap.org/codepush{R}")
        ui.wl(ui.sep())
        ui.wait_key()
        return

    _draw()
    out_raw = ui.prompt("保存先ファイル (空=stdout):", allow_empty=True) or ""
    if out_raw:
        pathlib.Path(out_raw).write_bytes(data)
        ui.wl(f"  {BG}✓ 保存:{R} {out_raw}")
        ui.wait_key()
    else:
        ui.clear()
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

# ── My files screens ──────────────────────────────────────────────────────────

def screen_my_files() -> None:
    while True:
        keys = _load_keys()
        items = [{"id": k, **v} for k, v in keys.items()]
        items.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)

        cols = [
            {"header": "ID",       "width": 10, "render": lambda x, s: f"{DC}{x['id'][:8]}{R}"},
            {"header": "ファイル名", "width": 26, "render": lambda x, s: x.get("filename", "")[:26]},
            {"header": "アップロード日時", "width": 20, "render": lambda x, s: x.get("uploaded_at", "")[:16]},
        ]
        extra = [
            {"key": "d", "label": "削除", "action": "delete"},
            {"key": "u", "label": "上書き", "action": "update"},
        ]
        r = ui.table(
            "自分のファイル",
            items, cols,
            extra_keys=extra,
            hint="Enter 詳細  d 削除  u 上書き  q 戻る",
        )
        if r.action in ("quit", "back"): return
        if r.action == "refresh": pass
        if r.action == "select" and r.item:
            screen_my_file_detail(r.item)
        if r.action == "delete" and r.item:
            screen_delete_file(r.item)
        if r.action == "update" and r.item:
            screen_update_file(r.item)

def screen_my_file_detail(item: dict) -> None:
    pid = item["id"]
    dk  = item["delete_key"]
    while True:
        ui.clear()
        ui.wl(ui.sep())
        ui.wl(f"  {BC}ファイル詳細{R}")
        ui.wl(ui.div())
        ui.wl(ui.detail_row("ID",         pid))
        ui.wl(ui.detail_row("ファイル名",  item.get("filename", "")))
        ui.wl(ui.detail_row("アップロード", item.get("uploaded_at", "")[:16]))
        ui.wl(ui.detail_row("管理キー",   f"{BR}{dk}{R}"))
        ui.wl(ui.detail_row("RAW URL",    f"{BASE_URL}/paste/{pid}/raw"))
        ui.wl(ui.sep())
        ui.wl(f"  {D}d 削除  u 上書き  q 戻る{R}")
        key = ui.getch()
        if key in ("q", "esc", "ctrl_c"): return
        if key == "d":
            screen_delete_file(item)
            return
        if key == "u":
            screen_update_file(item)

def screen_delete_file(item: dict) -> None:
    pid = item["id"]
    dk  = item["delete_key"]
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイル削除{R}")
    ui.wl(ui.div())
    ui.wl(ui.detail_row("ID",        pid))
    ui.wl(ui.detail_row("ファイル名", item.get("filename", "")))
    ui.wl(ui.sep())
    if not ui.confirm(f"{BR}削除しますか?{R}"):
        return
    err = None
    with ui.Spinner("削除中..."):
        try:
            delete_by_key(dk)
        except Exception as e:
            err = e
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイル削除{R}")
    ui.wl(ui.div())
    if err:
        ui.wl(f"  {BR}✗ {err}{R}")
    else:
        _remove_key(pid)
        ui.wl(f"  {BG}✓ 削除完了{R}")
    ui.wl(ui.sep())
    ui.wait_key()

def screen_update_file(item: dict) -> None:
    pid      = item["id"]
    dk       = item["delete_key"]
    filename = item.get("filename", "paste.txt")
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイル上書き{R}  {D}{filename}{R}")
    ui.wl(ui.div())
    raw = ui.prompt("新しいファイルパス:")
    if raw is None: return
    path = pathlib.Path(raw)
    if not path.exists():
        ui.wl(f"  {BR}✗ ファイルが見つかりません{R}")
        ui.wait_key()
        return
    err = None
    with ui.Spinner(f"上書き中: {path.name}"):
        try:
            update_paste(pid, dk, path.read_bytes(), path.name)
        except Exception as e:
            err = e
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイル上書き{R}")
    ui.wl(ui.div())
    if err:
        ui.wl(f"  {BR}✗ {err}{R}")
    else:
        _save_key(pid, dk, path.name)
        ui.wl(f"  {BG}✓ 上書き完了{R}")
        ui.wl(ui.detail_row("ID",  pid))
        ui.wl(ui.detail_row("URL", f"{BASE_URL}/paste/{pid}/raw"))
    ui.wl(ui.sep())
    ui.wait_key()

def screen_diff() -> None:
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}Diff (2ファイル比較){R}")
    ui.wl(ui.div())
    id1 = ui.prompt("Paste ID 1:")
    if not id1: return
    id2 = ui.prompt("Paste ID 2:")
    if not id2: return
    err = None
    result = None
    with ui.Spinner("diff 取得中..."):
        try:
            result = get_diff(id1, id2)
        except Exception as e:
            err = e
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}Diff{R}  {D}{id1[:8]}... ↔ {id2[:8]}...{R}")
    ui.wl(ui.div())
    if err:
        ui.wl(f"  {BR}✗ {err}{R}")
    else:
        for line in result.splitlines()[:ui.rows()-8]:
            ui.wl("  " + line[:ui.cols()-4])
    ui.wl(ui.sep())
    ui.wait_key()

# ── Admin screens ─────────────────────────────────────────────────────────────

def _get_admin(cfg: dict) -> AdminApi | None:
    token = cfg.get("admin_token")
    if not token:
        ui.wl(f"  {BR}管理者トークン未設定。/setup を先に実行してください。{R}")
        ui.wait_key()
        return None
    return AdminApi(token)

def screen_stats(cfg: dict) -> None:
    adm = _get_admin(cfg)
    if not adm: return
    with ui.Spinner("stats 取得中..."):
        try:
            data = adm.stats()
        except ApiError as e:
            ui.wl(f"  {BR}✗ {e}{R}")
            ui.wait_key()
            return
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}Stats{R}")
    ui.wl(ui.div())
    for k, v in (data.items() if isinstance(data, dict) else []):
        ui.wl(ui.detail_row(k, str(v)))
    ui.wl(ui.sep())
    ui.wait_key()

def screen_pastes(cfg: dict) -> None:
    adm = _get_admin(cfg)
    if not adm: return

    page = 1
    page_size = 15
    search = ""

    while True:
        with ui.Spinner("ペースト一覧取得中..."):
            try:
                data = adm.pastes(page=page, limit=page_size, search=search)
            except ApiError as e:
                ui.wl(f"  {BR}✗ {e}{R}")
                ui.wait_key()
                return

        items  = data.get("pastes", [])
        total  = data.get("total", len(items))

        cols = [
            {"header": "ID",       "width": 10, "render": lambda x, s: f"{DC}{x.get('id','')[:8]}{R}"},
            {"header": "ファイル名", "width": 24, "render": lambda x, s: x.get("filename","")[:24]},
            {"header": "サイズ",   "width": 8,  "render": lambda x, s: _size(x.get("size"))},
            {"header": "作成日時", "width": 17, "render": lambda x, s: _ts(x.get("created_at"))},
            {"header": "有効期限", "width": 17, "render": lambda x, s: _ts(x.get("expires_at")) if x.get("expires_at") else f"{D}無期限{R}"},
        ]
        extra = [
            {"key": "d", "label": "削除", "action": "delete"},
            {"key": "/", "label": "検索", "action": "search"},
        ]
        r = ui.table(
            f"ペースト一覧  検索:{search or '—'}",
            items, cols,
            page=page, total=total, page_size=page_size,
            extra_keys=extra,
            hint="Enter 詳細  d 削除  / 検索  n/p ページ",
        )

        if r.action == "quit":  return
        if r.action == "back":  return
        if r.action == "next":  page += 1
        if r.action == "prev" and page > 1: page -= 1
        if r.action == "refresh": pass
        if r.action == "search":
            s = ui.prompt("検索キーワード:", allow_empty=True)
            if s is not None:
                search = s
                page = 1
        if r.action == "select" and r.item:
            screen_paste_detail(adm, r.item.get("id", ""))
        if r.action == "delete" and r.item:
            pid = r.item.get("id", "")
            if ui.confirm(f"削除: {pid[:8]}...?"):
                try:
                    adm.delete_paste(pid)
                    ui.wl(f"  {BG}✓ 削除完了{R}")
                except ApiError as e:
                    ui.wl(f"  {BR}✗ {e}{R}")
                import time; time.sleep(0.8)

def screen_paste_detail(adm: AdminApi, pid: str) -> None:
    with ui.Spinner("ペースト詳細取得中..."):
        try:
            data = adm.paste(pid)
        except ApiError as e:
            ui.wl(f"  {BR}✗ {e}{R}")
            ui.wait_key()
            return

    while True:
        ui.clear()
        ui.wl(ui.sep())
        ui.wl(f"  {BC}ペースト詳細{R}")
        ui.wl(ui.div())
        ui.wl(ui.detail_row("ID",       data.get("id", "")))
        ui.wl(ui.detail_row("ファイル名", data.get("filename", "")))
        ui.wl(ui.detail_row("サイズ",   _size(data.get("size"))))
        ui.wl(ui.detail_row("グループ", data.get("group_id") or f"{D}—{R}"))
        ui.wl(ui.detail_row("作成日時", _ts(data.get("created_at"))))
        ui.wl(ui.detail_row("有効期限", _ts(data.get("expires_at")) if data.get("expires_at") else f"{D}無期限{R}"))
        ui.wl(ui.detail_row("RAW URL",  f"{BASE_URL}/paste/{data.get('id','')}/raw"))
        ui.wl(ui.sep())
        ui.wl(f"  {D}c コンテンツ表示  d 削除  q 戻る{R}")

        key = ui.getch()
        if key in ("q", "esc", "ctrl_c"): return
        if key == "d":
            if ui.confirm("このペーストを削除しますか?"):
                try:
                    adm.delete_paste(pid)
                    ui.wl(f"  {BG}✓ 削除完了{R}")
                    import time; time.sleep(0.8)
                    return
                except ApiError as e:
                    ui.wl(f"  {BR}✗ {e}{R}")
                    import time; time.sleep(1)
        if key == "c":
            screen_paste_content(adm, pid, data.get("filename", ""))

def screen_paste_content(adm: AdminApi, pid: str, filename: str) -> None:
    with ui.Spinner("コンテンツ取得中..."):
        try:
            content = adm.paste_content(pid)
        except ApiError as e:
            ui.wl(f"  {BR}✗ {e}{R}")
            ui.wait_key()
            return

    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}{filename}{R}  {D}({pid[:8]}){R}")
    ui.wl(ui.div())
    lines = content.splitlines()
    visible = ui.rows() - 8
    for line in lines[:visible]:
        ui.wl("  " + line[:ui.cols()-4])
    if len(lines) > visible:
        ui.wl(f"  {D}... 残り {len(lines)-visible} 行 (保存して全文を確認){R}")
    ui.wl(ui.sep())
    save = ui.prompt("保存先ファイル (空=スキップ):", allow_empty=True) or ""
    if save:
        pathlib.Path(save).write_text(content)
        ui.wl(f"  {BG}✓ 保存:{R} {save}")
        ui.wait_key()

def screen_groups(cfg: dict) -> None:
    adm = _get_admin(cfg)
    if not adm: return

    page = 1
    page_size = 15

    while True:
        with ui.Spinner("グループ一覧取得中..."):
            try:
                data = adm.groups(page=page, limit=page_size)
            except ApiError as e:
                ui.wl(f"  {BR}✗ {e}{R}")
                ui.wait_key()
                return

        items = data.get("groups", [])
        total = data.get("total", len(items))

        cols = [
            {"header": "グループID",  "width": 12, "render": lambda x, s: f"{DC}{x.get('group_id','')[:10]}{R}"},
            {"header": "ファイル数",  "width": 8,  "render": lambda x, s: str(x.get("count", 0))},
            {"header": "合計サイズ",  "width": 10, "render": lambda x, s: _size(x.get("total_size"))},
            {"header": "作成日時",    "width": 17, "render": lambda x, s: _ts(x.get("created_at"))},
        ]
        extra = [
            {"key": "d", "label": "削除", "action": "delete"},
        ]
        r = ui.table(
            "グループ一覧",
            items, cols,
            page=page, total=total, page_size=page_size,
            extra_keys=extra,
            hint="Enter 詳細  d 削除  n/p ページ",
        )

        if r.action in ("quit", "back"): return
        if r.action == "next":  page += 1
        if r.action == "prev" and page > 1: page -= 1
        if r.action == "refresh": pass
        if r.action == "select" and r.item:
            screen_group_detail(adm, r.item.get("group_id", ""))
        if r.action == "delete" and r.item:
            gid = r.item.get("group_id", "")
            if ui.confirm(f"グループ全体を削除: {gid}?"):
                try:
                    adm.delete_group(gid)
                    ui.wl(f"  {BG}✓ 削除完了{R}")
                except ApiError as e:
                    ui.wl(f"  {BR}✗ {e}{R}")
                import time; time.sleep(0.8)

def screen_group_detail(adm: AdminApi, gid: str) -> None:
    with ui.Spinner("グループ詳細取得中..."):
        try:
            data = adm.group(gid)
        except ApiError as e:
            ui.wl(f"  {BR}✗ {e}{R}")
            ui.wait_key()
            return

    pastes = data.get("pastes", [])

    while True:
        cols = [
            {"header": "ID",       "width": 10, "render": lambda x, s: f"{DC}{x.get('id','')[:8]}{R}"},
            {"header": "ファイル名", "width": 30, "render": lambda x, s: x.get("filename","")[:30]},
            {"header": "サイズ",   "width": 8,  "render": lambda x, s: _size(x.get("size"))},
        ]
        extra = [
            {"key": "d", "label": "削除", "action": "delete"},
            {"key": "D", "label": "グループ全体削除", "action": "delete_group"},
        ]
        r = ui.table(
            f"グループ: {gid}  ({len(pastes)} ファイル)",
            pastes, cols,
            extra_keys=extra,
            hint="Enter 詳細  d 削除  D グループ削除  q 戻る",
        )

        if r.action in ("quit", "back"): return
        if r.action == "refresh": pass
        if r.action == "select" and r.item:
            screen_paste_detail(adm, r.item.get("id", ""))
            # refresh after potential delete
            try:
                data = adm.group(gid)
                pastes = data.get("pastes", [])
            except ApiError:
                return
        if r.action == "delete" and r.item:
            pid = r.item.get("id", "")
            if ui.confirm(f"削除: {pid[:8]}...?"):
                try:
                    adm.delete_paste(pid)
                    pastes = [p for p in pastes if p.get("id") != pid]
                    ui.wl(f"  {BG}✓ 削除完了{R}")
                except ApiError as e:
                    ui.wl(f"  {BR}✗ {e}{R}")
                import time; time.sleep(0.6)
        if r.action == "delete_group":
            if ui.confirm(f"グループ全体を削除: {gid}?"):
                try:
                    adm.delete_group(gid)
                    ui.wl(f"  {BG}✓ グループ削除完了{R}")
                    import time; time.sleep(0.8)
                    return
                except ApiError as e:
                    ui.wl(f"  {BR}✗ {e}{R}")
                    import time; time.sleep(1)

def screen_purge(cfg: dict) -> None:
    adm = _get_admin(cfg)
    if not adm: return
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}Purge{R}  {BR}不要データ削除{R}")
    ui.wl(ui.div())
    expired = ui.confirm("期限切れペーストを削除しますか?")
    orphan  = ui.confirm("孤立ファイルを削除しますか?")
    if not expired and not orphan:
        ui.wl(f"  {D}キャンセル{R}")
        ui.wait_key()
        return
    with ui.Spinner("Purge 実行中..."):
        try:
            result = adm.purge(expired=expired, orphan=orphan)
        except ApiError as e:
            ui.wl(f"  {BR}✗ {e}{R}")
            ui.wait_key()
            return
    ui.wl(f"  {BG}✓ 完了{R}")
    for k, v in (result.items() if isinstance(result, dict) else []):
        ui.wl(ui.detail_row(k, str(v)))
    ui.wait_key()

# ── Main menu ─────────────────────────────────────────────────────────────────

MAIN_ITEMS = [
    {"label": "アップロード",        "value": "upload",    "hint": "ファイルをアップロード"},
    {"label": "ダウンロード / 表示", "value": "get",       "hint": "ペーストを取得"},
    {"label": "自分のファイル",      "value": "myfiles",   "hint": "アップロード済みの管理・削除・上書き"},
    {"label": "Diff",                "value": "diff",      "hint": "2ペーストの差分を表示"},
    {"label": "Health チェック",     "value": "health",    "hint": "サーバー状態確認"},
]

def _run_action(action: str, cfg: dict) -> None:
    if action == "upload":   screen_upload()
    elif action == "get":    screen_get()
    elif action == "myfiles": screen_my_files()
    elif action == "diff":   screen_diff()
    elif action == "health": screen_health()
    elif action == "stats":  screen_stats(cfg)
    elif action == "pastes": screen_pastes(cfg)
    elif action == "groups": screen_groups(cfg)
    elif action == "purge":  screen_purge(cfg)
    elif action == "setup":  screen_setup()

def interactive_menu() -> None:
    items = [i for i in MAIN_ITEMS if i["value"] != "__sep__"]
    cfg = _load_cfg()
    while True:
        action = ui.menu(
            f"clilap codepush  {DC}v{__version__}{R}",
            items,
        )
        if action is None:
            ui.clear()
            ui.show_cursor()
            return
        cfg = _load_cfg()
        _run_action(action, cfg)

# ── CLI entrypoint ────────────────────────────────────────────────────────────

def _print_help() -> None:
    ui.wl(f"""\
{BC}clilap codepush{R}  {D}v{__version__}{R}

Usage:
  codepush [command] [args]

Commands:
  (none)          インタラクティブメニュー起動
  upload <file>   ファイルをアップロード
  get <id>        ペーストを stdout に出力
  myfiles         アップロード済みファイルの管理
  diff            2ペーストの差分表示
  health          サーバー状態確認
  help, --help    このヘルプを表示

Environment:
  CODEPUSH_URL    API ベース URL (default: {BASE_URL})
""")

def main() -> None:
    try:
        _main()
    except KeyboardInterrupt:
        ui.show_cursor()
        print()
        sys.exit(0)

def _main() -> None:
    args = sys.argv[1:]

    if not args:
        interactive_menu()
        return

    cmd = args[0].lower()
    cfg = _load_cfg()

    if cmd in ("help", "--help", "-h"):
        _print_help()
    elif cmd == "health":
        screen_health()
    elif cmd == "upload":
        screen_upload(args[1] if len(args) > 1 else None)
    elif cmd == "get":
        screen_get(args[1] if len(args) > 1 else None)
    elif cmd in ("myfiles", "my"):
        screen_my_files()
    elif cmd == "diff":
        screen_diff()
    elif cmd == "delete":
        screen_my_files()
    else:
        ui.wl(f"  {BR}不明なコマンド: {cmd}{R}")
        _print_help()
        sys.exit(1)
