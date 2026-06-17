"""Terminal UI primitives — pure stdlib, no dependencies."""
from __future__ import annotations
import sys, os, shutil, subprocess
from typing import Any, TypeVar

try:
    import tty, termios
    _HAS_TTY = True
except ImportError:
    _HAS_TTY = False  # Windows

T = TypeVar("T")

# ── ANSI ──────────────────────────────────────────────────────────────────────
R   = "\x1b[0m"
D   = "\x1b[2m"
DC  = "\x1b[2;36m"
BC  = "\x1b[1;36m"
BG  = "\x1b[1;32m"
BY  = "\x1b[1;33m"
BW  = "\x1b[1;37m"
BR  = "\x1b[1;31m"
BB  = "\x1b[1;34m"
SEL = "\x1b[48;5;24m"

def _strip(s: str) -> str:
    import re
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def _pad(s: str, n: int) -> str:
    extra = len(s) - len(_strip(s))
    return s.ljust(n + extra)

def cols() -> int: return shutil.get_terminal_size().columns
def rows() -> int: return shutil.get_terminal_size().lines

def w(s: str) -> None: sys.stdout.write(s); sys.stdout.flush()
def wl(s: str = "") -> None: sys.stdout.write(s + "\n"); sys.stdout.flush()

def clear() -> None: w("\x1b[2J\x1b[3J\x1b[H")
def hide_cursor() -> None: w("\x1b[?25l")
def show_cursor() -> None: w("\x1b[?25h")
def clear_line() -> None: w("\x1b[2K\r")

def sep(ch: str = "═") -> str:
    return DC + ch * min(cols(), 90) + R

def div(ch: str = "─") -> str:
    return DC + "  " + ch * min(cols() - 2, 88) + R

def header(title: str) -> str:
    width = min(cols(), 90)
    inner = f" {title} "
    lp = (width - len(inner)) // 2
    rp = width - len(inner) - lp
    lines = [
        DC + "╔" + "═" * (width - 2) + "╗" + R,
        DC + "║" + R + " " * (lp - 1) + BC + inner + R + " " * (rp - 1) + DC + "║" + R,
        DC + "╚" + "═" * (width - 2) + "╝" + R,
    ]
    return "\n".join(lines)

def error_box(msg: str) -> None:
    """赤いエラーボックス表示"""
    import re as _re
    # ANSIと改行を除去して1行に
    clean = _re.sub(r'\x1b\[[0-9;]*m', '', msg).replace("\n", " ").replace("\r", "").strip()
    width = min(cols(), 90)
    inner = f" ✗  {clean} "
    # 枠内に収まるよう切り捨て
    max_inner = width - 2
    if len(inner) > max_inner:
        inner = inner[:max_inner - 1] + "…"
    wl(BR + "╔" + "═" * (width - 2) + "╗" + R)
    wl(BR + "║" + R + f"{BR}{inner:<{max_inner}}{R}" + BR + "║" + R)
    wl(BR + "╚" + "═" * (width - 2) + "╝" + R)

# ── Keypress ──────────────────────────────────────────────────────────────────
_KEY_MAP = {
    "\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
    "\r": "enter", "\n": "enter", "\x7f": "backspace", "\x1b": "esc",
    "\x03": "ctrl_c", "\x04": "ctrl_d",
}

def getch() -> str:
    if not _HAS_TTY:
        return _getch_windows()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch == "\x1b":
            seq = ch
            try:
                for _ in range(4):
                    c = sys.stdin.read(1)
                    seq += c
                    if seq in _KEY_MAP or (len(seq) > 2 and c.isalpha()):
                        break
            except Exception:
                pass
            return _KEY_MAP.get(seq, seq)
        return _KEY_MAP.get(ch, ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def _getch_windows() -> str:
    try:
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(ch2, ch2)
        if ch == "\r": return "enter"
        if ch == "\x03": raise KeyboardInterrupt
        if ch == "\x1b": return "esc"
        return ch
    except KeyboardInterrupt:
        raise
    except Exception:
        return input()

def confirm(msg: str) -> bool:
    w(f"  {BY}?{R} {msg} {D}[y/N]{R} ")
    sys.stdout.flush()
    try:
        key = getch()
    except Exception:
        key = input()
    result = key.lower() == "y"
    wl(f"{BG}y{R}" if result else f"{BR}n{R}")
    return result

# ── Clipboard ─────────────────────────────────────────────────────────────────
def copy_to_clipboard(text: str) -> bool:
    """テキストをクリップボードにコピー。成功したらTrue。"""
    try:
        if sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode("utf-16-le"), check=True,
                           capture_output=True)
            return True
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True,
                           capture_output=True)
            return True
        # Linux: xclip or xsel or wl-copy
        for cmd in (["xclip", "-selection", "clipboard"],
                    ["xsel", "--clipboard", "--input"],
                    ["wl-copy"]):
            try:
                subprocess.run(cmd, input=text.encode(), check=True,
                               capture_output=True)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
    except Exception:
        pass
    return False

# ── Spinner ───────────────────────────────────────────────────────────────────
import threading, time

FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

class Spinner:
    def __init__(self, msg: str):
        self.msg = msg
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        i = 0
        hide_cursor()
        while not self._stop.is_set():
            clear_line()
            w(f"  {BC}{FRAMES[i % len(FRAMES)]}{R}  {self.msg}")
            i += 1
            time.sleep(0.08)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._t.join()
        clear_line()
        show_cursor()

# ── Menu ──────────────────────────────────────────────────────────────────────
def menu(title: str, items: list[dict], back: bool = False,
         exit_key: bool = True) -> str | None:
    opts = list(items)
    if back:
        opts.append({"label": "← 戻る", "value": "__back__"})

    idx = 0

    def draw(first: bool = False):
        if first:
            clear()
        else:
            w("\x1b[H")
        wl(sep())
        wl(f"  {BC}{title}{R}")
        wl(div())
        for i, item in enumerate(opts):
            sel = i == idx
            arrow = f"{BC}▶{R}" if sel else " "
            bg    = SEL if sel else ""
            end   = R if sel else ""
            icon  = item.get("icon", "")
            icon_str = f"{icon} " if icon else ""
            label = item["label"]
            if item.get("danger"):
                label = f"{BR}{label}{R}"
            hint = f"  {D}{item['hint']}{R}" if item.get("hint") else ""
            line = f"  {arrow} {bg}{BW if sel else ''}{icon_str}{label}{end}{hint}"
            w(line + "\x1b[K\n")
        wl(sep())
        if exit_key:
            w(f"  {D}↑↓ 移動  Enter 選択  q 終了{R}\x1b[K")
        else:
            w(f"  {D}↑↓ 移動  Enter 選択  Ctrl+C 終了{R}\x1b[K")

    hide_cursor()
    draw(first=True)
    try:
        while True:
            key = getch()
            if key == "ctrl_d":
                return None
            if exit_key and key == "q":
                return None
            if key == "up"   and idx > 0:            idx -= 1; draw()
            elif key == "down" and idx < len(opts)-1: idx += 1; draw()
            elif key == "enter":
                val = opts[idx]["value"]
                return None if val == "__back__" else val
    finally:
        show_cursor()

# ── Table ─────────────────────────────────────────────────────────────────────
class TableResult:
    def __init__(self, action: str, item: Any = None):
        self.action = action
        self.item   = item

def table(
    title: str,
    items: list[T],
    columns: list[dict],
    *,
    page: int = 1,
    total: int | None = None,
    page_size: int = 15,
    extra_keys: list[dict] | None = None,
    hint: str = "",
    select_guard: Any = None,
) -> TableResult:
    """select_guard(item) -> str | None: 文字列を返すとEnter選択をブロックし、
    その文字列をその場に警告として表示する（画面の再クリアなし）。"""
    idx = 0
    _first = [True]
    notice = [""]

    def draw():
        if _first[0]:
            clear(); _first[0] = False
        else:
            w("\x1b[H")
        wl(sep())
        pinfo = f"  {D}{page}/{max(1,(total or 0+page_size-1)//page_size)} ページ  合計: {total}{R}" if total is not None else ""
        wl(f"  {BC}{title}{R}{pinfo}")
        wl(div())
        hdr = "  " + "  ".join(_pad(f"{BW}{c['header']}{R}", c["width"]) for c in columns)
        wl(hdr)
        wl(div("─"))
        if not items:
            wl(f"  {D}(データなし){R}")
        for i, item in enumerate(items):
            sel = i == idx
            bg  = SEL if sel else ""
            end = R if sel else ""
            arrow = f"{BC}▶{R}" if sel else " "
            cells = "  ".join(_pad(c["render"](item, sel), c["width"]) for c in columns)
            wl(f"{arrow} {bg}{cells}{end}\x1b[K")
        wl(sep())
        keys_parts = ["↑↓ 移動", "Enter 選択"]
        if total and page > 1:                keys_parts.append("p 前")
        if total and page * page_size < total: keys_parts.append("n 次")
        for ek in (extra_keys or []):
            keys_parts.append(f"{ek['key']} {ek['label']}")
        keys_parts += ["r 更新", "q 戻る"]
        if notice[0]:
            wl(f"  {BR}{notice[0]}{R}\x1b[K")
        else:
            wl(f"  {D}{'  '.join(keys_parts)}{R}\x1b[K")
        if hint:
            w(f"  {D}{hint}{R}\x1b[K")

    hide_cursor()
    draw()
    try:
        while True:
            key = getch()
            if key == "q":      return TableResult("back")
            if key == "r":      return TableResult("refresh")
            if key == "n":      return TableResult("next")
            if key == "p":      return TableResult("prev")
            if key == "up"   and idx > 0:            idx -= 1; notice[0] = ""; draw()
            elif key == "down" and idx < len(items)-1: idx += 1; notice[0] = ""; draw()
            elif key == "enter" and items:
                blocked = select_guard(items[idx]) if select_guard else None
                if blocked:
                    notice[0] = blocked; draw()
                else:
                    return TableResult("select", items[idx])
            else:
                for ek in (extra_keys or []):
                    if key == ek["key"]:
                        return TableResult(ek["action"], items[idx] if items else None)
    finally:
        show_cursor()

# ── Scrollable pager ──────────────────────────────────────────────────────────
def pager(title: str, lines: list[str]) -> None:
    """j/k/↑↓ スクロール、q で戻るビューア"""
    scroll = 0
    _first = [True]

    def draw():
        if _first[0]:
            clear(); _first[0] = False
        else:
            w("\x1b[H")
        visible = rows() - 6
        wl(sep())
        total_lines = len(lines)
        wl(f"  {BC}{title}{R}  {D}({scroll+1}-{min(scroll+visible, total_lines)}/{total_lines}行){R}")
        wl(div())
        for line in lines[scroll:scroll + visible]:
            w("  " + line[:cols() - 4] + "\x1b[K\n")
        shown = min(visible, total_lines - scroll)
        for _ in range(visible - shown):
            w("\x1b[K\n")
        wl(sep())
        w(f"  {D}↑↓/jk スクロール  q 戻る{R}\x1b[K")

    hide_cursor()
    draw()
    try:
        while True:
            key = getch()
            if key in ("q", "esc"):
                return
            max_scroll = max(0, len(lines) - (rows() - 6))
            if key in ("down", "j") and scroll < max_scroll:
                scroll += 1; draw()
            elif key in ("up", "k") and scroll > 0:
                scroll -= 1; draw()
    finally:
        show_cursor()

# ── Diff viewer ───────────────────────────────────────────────────────────────
def colorize_diff_line(line: str) -> str:
    if line.startswith("+") and not line.startswith("+++"):
        return BG + line + R
    if line.startswith("-") and not line.startswith("---"):
        return BR + line + R
    if line.startswith("@@"):
        return BC + line + R
    if line.startswith("---") or line.startswith("+++"):
        return BW + line + R
    return D + line + R

def _wcswidth(s: str) -> int:
    """East-Asian width aware string display width."""
    w = 0
    for c in s:
        cp = ord(c)
        if (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x303E or
                0x3040 <= cp <= 0x33FF or 0x3400 <= cp <= 0x4DBF or
                0x4E00 <= cp <= 0xA4CF or 0xA960 <= cp <= 0xA97F or
                0xAC00 <= cp <= 0xD7FF or 0xF900 <= cp <= 0xFAFF or
                0xFE10 <= cp <= 0xFE1F or 0xFE30 <= cp <= 0xFE6F or
                0xFF00 <= cp <= 0xFF60 or 0xFFE0 <= cp <= 0xFFE6 or
                0x1B000 <= cp <= 0x1B0FF or 0x1F004 <= cp <= 0x1F0CF or
                0x1F300 <= cp <= 0x1F9FF or 0x20000 <= cp <= 0x2FFFD or
                0x30000 <= cp <= 0x3FFFD):
            w += 2
        else:
            w += 1
    return w

_LABEL_WIDTH = 14

def detail_row(label: str, value: str) -> str:
    pad = max(0, _LABEL_WIDTH - _wcswidth(label))
    return f"  {D}{label}{' ' * pad}{R}  {value}"

def detail_indent() -> str:
    """Indent matching detail_row value column (for continuation lines)."""
    return "  " + " " * _LABEL_WIDTH + "  "

def wait_key() -> None:
    wl(f"  {D}q で戻る{R}")
    try:
        getch()
    except Exception:
        input()

def prompt(label: str, default: str = "", allow_empty: bool = False) -> str | None:
    """入力プロンプト。空Enterまたはq入力でNoneを返す(戻る)。"""
    show_cursor()
    wl(f"  {D}空Enter または q で戻る{R}")
    raw = input(f"  {BC}{label}{R} ").strip()
    # Windowsドラッグ&ドロップで付く引用符を除去
    if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
        raw = raw[1:-1]
    if raw.lower() == "q" or (not raw and not allow_empty):
        return None
    return raw
