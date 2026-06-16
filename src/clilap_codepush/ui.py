"""Terminal UI primitives — pure stdlib, no dependencies."""
from __future__ import annotations
import sys, os, shutil
from typing import Any, Callable, TypeVar

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
SEL = "\x1b[48;5;24m"   # selected row bg

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

def clear() -> None: w("\x1b[2J\x1b[H")
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

# ── Keypress (Unix only) ──────────────────────────────────────────────────────
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
        if ch in ("\x00", "\xe0"):  # special key prefix
            ch2 = msvcrt.getwch()
            return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(ch2, ch2)
        if ch == "\r": return "enter"
        if ch == "\x03": return "ctrl_c"
        if ch == "\x1b": return "esc"
        return ch
    except Exception:
        return input()

def readline_prompt(prompt: str, default: str = "") -> str:
    show_cursor()
    w(prompt)
    if default:
        w(default)
    sys.stdout.flush()
    line = sys.stdin.readline().rstrip("\n")
    return line if line else default

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
def menu(title: str, items: list[dict], back: bool = False) -> str | None:
    """Arrow-key driven menu. Returns selected value or None (back/quit)."""
    opts = list(items)
    if back:
        opts.append({"label": "← 戻る", "value": "__back__"})

    idx = 0

    def draw():
        clear()
        wl(sep())
        wl(f"  {BC}{title}{R}")
        wl(div())
        for i, item in enumerate(opts):
            sel = i == idx
            arrow = f"{BC}▶{R}" if sel else " "
            bg    = SEL if sel else ""
            end   = R if sel else ""
            label = item["label"]
            if item.get("danger"):
                label = f"{BR}{label}{R}"
            hint = f"  {D}{item['hint']}{R}" if item.get("hint") else ""
            wl(f"  {arrow} {bg}{BW if sel else ''}{label}{end}{hint}")
        wl(sep())
        wl(f"  {D}↑↓ 移動  Enter 選択  q 終了{R}")

    hide_cursor()
    draw()
    try:
        while True:
            key = getch()
            if key in ("ctrl_c", "ctrl_d", "q"):
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
) -> TableResult:
    idx = 0

    def draw():
        clear()
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
            wl(f"{arrow} {bg}{cells}{end}")
        wl(sep())
        keys_parts = ["↑↓ 移動", "Enter 選択"]
        if total and page > 1:            keys_parts.append("p 前")
        if total and page * page_size < total: keys_parts.append("n 次")
        for ek in (extra_keys or []):
            keys_parts.append(f"{ek['key']} {ek['label']}")
        keys_parts += ["r 更新", "q 戻る"]
        wl(f"  {D}{'  '.join(keys_parts)}{R}")
        if hint:
            wl(f"  {D}{hint}{R}")

    hide_cursor()
    draw()
    try:
        while True:
            key = getch()
            if key == "ctrl_c": return TableResult("quit")
            if key == "q":      return TableResult("back")
            if key == "r":      return TableResult("refresh")
            if key == "n":      return TableResult("next")
            if key == "p":      return TableResult("prev")
            if key == "up"   and idx > 0:           idx -= 1; draw()
            elif key == "down" and idx < len(items)-1: idx += 1; draw()
            elif key == "enter" and items:
                return TableResult("select", items[idx])
            for ek in (extra_keys or []):
                if key == ek["key"]:
                    return TableResult(ek["action"], items[idx] if items else None)
    finally:
        show_cursor()

def detail_row(label: str, value: str) -> str:
    return f"  {D}{label:<14}{R}  {value}"
