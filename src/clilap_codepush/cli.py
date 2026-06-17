"""clilap codepush CLI — interactive TUI entry point."""
from __future__ import annotations
import sys, os, json, pathlib, datetime, re

from . import __version__
from . import ui
from .api import (
    ApiError, upload, get_raw, health,
    delete_by_key, update_paste, get_diff,
    BASE_URL,
)

# ── Config ────────────────────────────────────────────────────────────────────
KEYS_PATH = pathlib.Path.home() / ".config" / "clilap-codepush" / "keys.json"

def _load_keys() -> dict:
    if KEYS_PATH.exists():
        try:
            return json.loads(KEYS_PATH.read_text())
        except Exception:
            pass
    return {}

def _save_key(paste_id: str, delete_key: str, filename: str, *,
              expires_at=None, language: str = "", size: int | None = None) -> None:
    keys = _load_keys()
    keys[paste_id] = {
        "delete_key":  delete_key,
        "filename":    filename,
        "uploaded_at": datetime.datetime.now().isoformat(),
        "expires_at":  expires_at,
        "language":    language,
        "size":        size,
    }
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYS_PATH.write_text(json.dumps(keys, indent=2))

def _remove_key(paste_id: str) -> None:
    keys = _load_keys()
    keys.pop(paste_id, None)
    KEYS_PATH.write_text(json.dumps(keys, indent=2))

# ── Helpers ───────────────────────────────────────────────────────────────────
R   = ui.R; D = ui.D; BC = ui.BC; BG = ui.BG; BY = ui.BY; BW = ui.BW
BR  = ui.BR; DC = ui.DC

def _parse_duration(s: str) -> int | None:
    """'3d12h30m10s' 形式を秒数に変換。数字のみなら秒として扱う。"""
    import re
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    matches = re.findall(r"(\d+)\s*([dhms])", s)
    if not matches:
        return None
    total = sum(int(n) * units[u] for n, u in matches)
    return total if total > 0 else None

_JST = datetime.timezone(datetime.timedelta(hours=9))

def _ts(iso) -> str:
    if not iso: return f"{D}—{R}"
    try:
        if isinstance(iso, (int, float)):
            dt = datetime.datetime.fromtimestamp(iso, tz=_JST)
        else:
            dt = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
            dt = dt.astimezone(_JST) if dt.tzinfo else dt.replace(tzinfo=_JST)
        return dt.strftime("%Y-%m-%d %H:%M JST")
    except Exception:
        return str(iso)[:16]

def _size(n: int | None) -> str:
    if n is None: return f"{D}—{R}"
    if n < 1024:   return f"{n} B"
    if n < 1048576: return f"{n/1024:.1f} KB"
    return f"{n/1048576:.1f} MB"

def _short(s: str | None, n: int = 8) -> str:
    if not s: return f"{D}—{R}"
    return s[:n]

# ── Screens ───────────────────────────────────────────────────────────────────


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
        ui.error_box(f"サーバーに接続できません: {err}")
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
        raw_path = args_file
    else:
        raw_path = ui.prompt("ファイルパス:")
        if raw_path is None: return

    # exists()はWSL UNCパスで誤判定することがあるため、open()で直接確認
    try:
        with open(raw_path, "rb") as _probe:
            pass
    except (FileNotFoundError, PermissionError, OSError) as _e:
        ui.wl(f"  {BR}✗ ファイルが見つかりません: {raw_path}{R}")
        ui.wait_key()
        return

    filename = os.path.basename(raw_path) or pathlib.Path(raw_path).name
    ttl_choice = ui.menu("有効期限", [
        {"label": "無期限",         "value": "0"},
        {"label": "1時間",          "value": str(3600)},
        {"label": "1日",            "value": str(86400)},
        {"label": "7日",            "value": str(86400 * 7)},
        {"label": "30日",           "value": str(86400 * 30)},
        {"label": "カスタム入力…", "value": "__custom__",
         "hint": "3d12h / 2h30m / 90m など"},
    ], back=True)
    if ttl_choice is None: return
    if ttl_choice == "__custom__":
        ui.clear()
        ui.wl(ui.sep())
        ui.wl(f"  {BC}有効期限 カスタム入力{R}")
        ui.wl(ui.div())
        ui.wl(f"  {D}例: 3d12h  /  2h30m  /  90m  /  7200s{R}")
        raw = ui.prompt("有効期限:")
        if raw is None: return
        ttl = _parse_duration(raw)
        if ttl is None:
            ui.wl(f"  {BR}✗ 解析できません: {raw}{R}")
            ui.wait_key()
            return
    elif ttl_choice == "0":
        ttl = None
    else:
        ttl = int(ttl_choice)
    group = None
    token = None

    err = None
    result = None
    with ui.Spinner(f"アップロード中: {filename}"):
        try:
            with open(raw_path, "rb") as _f:
                _content = _f.read()
            result = upload(_content, filename, ttl=ttl, group=group, token=token)
        except ApiError as e:
            err = e

    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイルアップロード{R}")
    ui.wl(ui.div())
    if err is not None:
        ui.error_box(str(err))
        ui.wl(ui.sep())
        ui.wait_key()
    else:
        dk  = result.get("delete_key", "")
        url = result.get("url", "")

        # アーカイブ(zip/tar)レスポンス: group_id + files
        if result.get("group_id"):
            gid   = result["group_id"]
            files = result.get("files", [])
            if gid and dk:
                _save_key(gid, dk, filename)
            ui.wl(f"  {BG}✓ アップロード完了  {D}({len(files)} ファイル){R}")
            ui.wl(ui.div())
            ui.wl(ui.detail_row("tree",   f"{BC}{url}{R}"))
            ui.wl(ui.div())
            for f in files[:10]:
                ui.wl(f"  {DC}{url}/{f['path']}{R}")
            if len(files) > 10:
                ui.wl(f"  {D}... 他 {len(files)-10} ファイル{R}")
            if dk:
                ui.wl(ui.div())
                ui.wl(ui.detail_row("管理キー", f"{BR}{dk}{R}"))
                ui.wl(ui.detail_row("  削除",   f"{D}curl clilap.org/cp -X DELETE -d key={dk}{R}"))
            ui.wl(ui.sep())
            ui.wl(f"  {D}c URLをコピー  q 戻る{R}")
            while True:
                key = ui.getch()
                if key in ("q", "esc", "ctrl_c", "enter"): break
                if key == "c":
                    ok = ui.copy_to_clipboard(url)
                    ui.clear_line()
                    ui.wl(f"  {BG}✓ コピーしました:{R} {url}" if ok else f"  {BY}クリップボードツールが見つかりません{R}")
                    ui.wait_key(); break

        # 単体ファイルレスポンス: id + raw
        else:
            pid      = result.get("id", "")
            raw_url  = result.get("raw", f"{BASE_URL}/{pid}/raw")
            lang     = result.get("language", "")
            raw_size = result.get("size")
            exp_at   = result.get("expires_at")
            size     = _size(raw_size)
            if pid and dk:
                _save_key(pid, dk, filename,
                          expires_at=exp_at, language=lang, size=raw_size)
            ui.wl(f"  {BG}✓ アップロード完了{R}")
            ui.wl(ui.div())
            ui.wl(ui.detail_row("url",    f"{BC}{url}{R}"))
            ui.wl(ui.detail_row("raw",    f"{DC}{raw_url}{R}"))
            ui.wl(ui.detail_row("file",   f"{filename}  {D}({lang}, {size}){R}"))
            exp_str = _ts(exp_at) if exp_at else f"{D}無期限{R}"
            ui.wl(ui.detail_row("有効期限", exp_str))
            if dk:
                ui.wl(ui.div())
                ui.wl(ui.detail_row("管理キー", f"{BR}{dk}{R}"))
                ui.wl(ui.detail_row("  更新",   f"{D}curl clilap.org/cp/{pid} -F file=@new.py -F key={dk}{R}"))
                ui.wl(ui.detail_row("  削除",   f"{D}curl clilap.org/cp -X DELETE -d key={dk}{R}"))
                ui.wl(ui.detail_row("  統計",   f"{D}curl clilap.org/cp/stats/{pid}{R}"))
            ui.wl(ui.sep())
            ui.wl(f"  {D}c URLをコピー  u 上書き  q 戻る{R}")
            while True:
                key = ui.getch()
                if key in ("q", "esc", "ctrl_c", "enter"): break
                if key == "c":
                    ok = ui.copy_to_clipboard(url)
                    ui.clear_line()
                    ui.wl(f"  {BG}✓ コピーしました:{R} {url}" if ok else f"  {BY}クリップボードツールが見つかりません{R}")
                    ui.wait_key(); break
                if key == "u" and pid and dk:
                    item = {"id": pid, "delete_key": dk, "filename": filename}
                    screen_update_file(item)
                    break

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
        ui.error_box(str(err))
        ui.wl(f"  {D}ファイルが見つかりません。考えられる原因:{R}")
        ui.wl(f"  {D}  • 有効期限切れ{R}")
        ui.wl(f"  {D}  • 管理キーで削除済み{R}")
        ui.wl(f"  {D}  • 管理者による削除{R}")
        ui.wl(f"  {D}  • IDが誤っている{R}")
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
    _first = True
    while True:
        if _first:
            ui.clear(); _first = False
        else:
            ui.w("\x1b[H")
        ui.wl(ui.sep())
        ui.wl(f"  {BC}ファイル詳細{R}")
        ui.wl(ui.div())
        url     = f"{BASE_URL}/{pid}"
        raw_url = f"{BASE_URL}/{pid}/raw"
        lang    = item.get("language", "")
        size    = _size(item.get("size"))
        exp_at  = item.get("expires_at")
        ui.wl(ui.detail_row("ID",         pid))
        ui.wl(ui.detail_row("ファイル名",  item.get("filename", "")))
        ui.wl(ui.detail_row("file",       f"{D}({lang}, {size}){R}" if lang else f"{D}{size}{R}"))
        ui.wl(ui.detail_row("アップロード", _ts(item.get("uploaded_at"))))
        ui.wl(ui.detail_row("有効期限",   _ts(exp_at) if exp_at else f"{D}無期限{R}"))
        ui.wl(ui.detail_row("url",        f"{BC}{url}{R}"))
        ui.wl(ui.detail_row("raw",        f"{DC}{raw_url}{R}"))
        ui.wl(ui.div())
        ui.wl(ui.detail_row("管理キー",   f"{BR}{dk}{R}"))
        ui.wl(ui.detail_row("  更新",     f"{D}curl clilap.org/cp/{pid} -F file=@new.py -F key={dk}{R}"))
        ui.wl(ui.detail_row("  削除",     f"{D}curl clilap.org/cp -X DELETE -d key={dk}{R}"))
        ui.wl(ui.detail_row("  統計",     f"{D}curl clilap.org/cp/stats/{pid}{R}"))
        ui.wl(ui.sep())
        ui.wl(f"  {D}c URLコピー  d 削除  u 上書き  q 戻る{R}")
        key = ui.getch()
        if key in ("q", "esc", "ctrl_c"): return
        if key == "c":
            ok = ui.copy_to_clipboard(url)
            ui.clear_line()
            ui.wl(f"  {BG}✓ コピーしました{R}" if ok else f"  {BY}クリップボードツールが見つかりません{R}")
            ui.wait_key()
            return
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
        ui.error_box(str(err))
        ui.wl(f"  {D}サーバー上では既に削除済みの可能性があります。{R}")
        ui.wl(f"  {D}ローカルの記録も削除しますか?{R}")
        if ui.confirm("ローカルから削除"):
            _remove_key(pid)
            ui.wl(f"  {D}ローカルの記録を削除しました{R}")
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
    try:
        with open(raw, "rb") as _probe:
            pass
    except (FileNotFoundError, PermissionError, OSError):
        ui.wl(f"  {BR}✗ ファイルが見つかりません{R}")
        ui.wait_key()
        return
    new_filename = os.path.basename(raw) or pathlib.Path(raw).name
    err = None
    with ui.Spinner(f"上書き中: {new_filename}"):
        try:
            with open(raw, "rb") as _f:
                _content = _f.read()
            update_paste(pid, dk, _content, new_filename)
        except Exception as e:
            err = e
    ui.clear()
    ui.wl(ui.sep())
    ui.wl(f"  {BC}ファイル上書き{R}")
    ui.wl(ui.div())
    if err:
        ui.wl(f"  {BR}✗ {err}{R}")
    else:
        _save_key(pid, dk, new_filename)
        ui.wl(f"  {BG}✓ 上書き完了{R}")
        ui.wl(ui.detail_row("ID",  pid))
        ui.wl(ui.detail_row("URL", f"{BASE_URL}/{pid}/raw"))
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
    if err:
        ui.clear()
        ui.wl(ui.sep())
        ui.wl(f"  {BC}Diff{R}")
        ui.wl(ui.div())
        ui.error_box(str(err))
        ui.wl(ui.sep())
        ui.wait_key()
    else:
        colored = [ui.colorize_diff_line(l) for l in result.splitlines()]
        ui.pager(f"Diff  {id1[:8]}... ↔ {id2[:8]}...", colored)

# ── Main menu ─────────────────────────────────────────────────────────────────

MAIN_ITEMS = [
    {"label": "アップロード",        "value": "upload",    "hint": "ファイルをアップロード",            "icon": "↑"},
    {"label": "ダウンロード / 表示", "value": "get",       "hint": "ペーストを取得",                   "icon": "↓"},
    {"label": "自分のファイル",      "value": "myfiles",   "hint": "アップロード済みの管理・削除・上書き", "icon": "≡"},
    {"label": "Diff",                "value": "diff",      "hint": "2ペーストの差分を表示",             "icon": "±"},
    {"label": "Health チェック",     "value": "health",    "hint": "サーバー状態確認",                 "icon": "♥"},
]

def _run_action(action: str) -> None:
    if action == "upload":    screen_upload()
    elif action == "get":     screen_get()
    elif action == "myfiles": screen_my_files()
    elif action == "diff":    screen_diff()
    elif action == "health":  screen_health()

def interactive_menu() -> None:
    while True:
        action = ui.menu(
            f"clilap codepush  {DC}v{__version__}{R}",
            MAIN_ITEMS,
            exit_key=False,
        )
        if action is None:
            ui.clear()
            ui.show_cursor()
            return
        _run_action(action)

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
