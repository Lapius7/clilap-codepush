"""clilap codepush CLI — interactive TUI entry point."""
from __future__ import annotations
import sys, os, json, pathlib, datetime, re

from . import __version__
from . import ui
from .api import (
    AdminApi, ApiError, upload, get_raw, delete_paste, health,
    BASE_URL, ADMIN_URL,
)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = pathlib.Path.home() / ".config" / "clilap-codepush" / "config.json"

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
    ui.show_cursor()
    token = input(f"  {BC}トークン:{R} ").strip()
    if not token:
        ui.wl(f"  {BR}キャンセル{R}")
        return
    cfg = _load_cfg()
    cfg["admin_token"] = token
    _save_cfg(cfg)
    ui.wl(f"  {BG}✓ 保存しました{R}: {CONFIG_PATH}")

def screen_health() -> None:
    err = None
    data = None
    with ui.Spinner("health チェック中..."):
        try:
            data = health()
        except ApiError as e:
            err = e
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}Health Check{R}")
    ui.wl(ui.div())
    if err is not None:
        ui.wl(f"  {BR}✗ {err}{R}")
    else:
        ui.wl(ui.detail_row("Status", f"{BG}OK{R}"))
        for k, v in (data.items() if isinstance(data, dict) else []):
            if k != "status":
                ui.wl(ui.detail_row(k, str(v)))
    ui.wl(ui.sep())
    input(f"  {D}Enterで戻る{R}")

def screen_upload(args_file: str | None = None) -> None:
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイルアップロード{R}")
    ui.wl(ui.div())
    ui.show_cursor()

    if args_file:
        path = pathlib.Path(args_file)
    else:
        raw = input(f"  {BC}ファイルパス:{R} ").strip()
        path = pathlib.Path(raw)

    if not path.exists():
        ui.wl(f"  {BR}✗ ファイルが見つかりません: {path}{R}")
        input(f"  {D}Enterで戻る{R}")
        return

    filename = path.name
    ttl_raw = input(f"  {BC}TTL (秒, 空=無期限):{R} ").strip()
    ttl = int(ttl_raw) if ttl_raw.isdigit() else None
    group = input(f"  {BC}グループID (空=なし):{R} ").strip() or None
    cfg = _load_cfg()
    token = cfg.get("admin_token") or input(f"  {BC}トークン:{R} ").strip() or None

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
        ui.wl(f"  {BG}✓ アップロード完了{R}")
        ui.wl(ui.detail_row("ID",  pid))
        ui.wl(ui.detail_row("URL", f"{BASE_URL}/paste/{pid}/raw"))
    ui.wl(ui.sep())
    input(f"  {D}Enterで戻る{R}")

def screen_get(args_id: str | None = None) -> None:
    def _draw():
        ui.clear()
        ui.wl(ui.sep())
        ui.wl(f"  {BC}ペースト取得{R}")
        ui.wl(ui.div())

    _draw()
    ui.show_cursor()

    pid = args_id or input(f"  {BC}Paste ID:{R} ").strip()
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
        input(f"  {D}Enterで戻る{R}")
        return

    _draw()
    ui.show_cursor()
    out_raw = input(f"  {BC}保存先ファイル (空=stdout):{R} ").strip()
    if out_raw:
        pathlib.Path(out_raw).write_bytes(data)
        ui.wl(f"  {BG}✓ 保存:{R} {out_raw}")
        input(f"  {D}Enterで戻る{R}")
    else:
        ui.clear()
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

# ── Admin screens ─────────────────────────────────────────────────────────────

def _get_admin(cfg: dict) -> AdminApi | None:
    token = cfg.get("admin_token")
    if not token:
        ui.wl(f"  {BR}管理者トークン未設定。/setup を先に実行してください。{R}")
        input(f"  {D}Enterで戻る{R}")
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
            input(f"  {D}Enterで戻る{R}")
            return
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}Stats{R}")
    ui.wl(ui.div())
    for k, v in (data.items() if isinstance(data, dict) else []):
        ui.wl(ui.detail_row(k, str(v)))
    ui.wl(ui.sep())
    input(f"  {D}Enterで戻る{R}")

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
                input(f"  {D}Enterで戻る{R}")
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
            ui.show_cursor()
            search = input(f"  {BC}検索キーワード:{R} ").strip()
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
            input(f"  {D}Enterで戻る{R}")
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
            input(f"  {D}Enterで戻る{R}")
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
    ui.show_cursor()
    save = input(f"  {D}保存先ファイル (空=スキップ):{R} ").strip()
    if save:
        pathlib.Path(save).write_text(content)
        ui.wl(f"  {BG}✓ 保存:{R} {save}")
        input(f"  {D}Enterで戻る{R}")

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
                input(f"  {D}Enterで戻る{R}")
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
            input(f"  {D}Enterで戻る{R}")
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
        input(f"  {D}Enterで戻る{R}")
        return
    with ui.Spinner("Purge 実行中..."):
        try:
            result = adm.purge(expired=expired, orphan=orphan)
        except ApiError as e:
            ui.wl(f"  {BR}✗ {e}{R}")
            input(f"  {D}Enterで戻る{R}")
            return
    ui.wl(f"  {BG}✓ 完了{R}")
    for k, v in (result.items() if isinstance(result, dict) else []):
        ui.wl(ui.detail_row(k, str(v)))
    input(f"  {D}Enterで戻る{R}")

# ── Main menu ─────────────────────────────────────────────────────────────────

MAIN_ITEMS = [
    {"label": "アップロード",        "value": "upload", "hint": "ファイルをアップロード"},
    {"label": "ダウンロード / 表示", "value": "get",    "hint": "ペーストを取得"},
    {"label": "Health チェック",     "value": "health", "hint": "サーバー状態確認"},
]

def _run_action(action: str, cfg: dict) -> None:
    if action == "upload":  screen_upload()
    elif action == "get":   screen_get()
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
  health          サーバー状態確認
  help, --help    このヘルプを表示

Environment:
  CODEPUSH_URL    API ベース URL (default: {BASE_URL})
""")

def main() -> None:
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
    else:
        ui.wl(f"  {BR}不明なコマンド: {cmd}{R}")
        _print_help()
        sys.exit(1)
