#!/usr/bin/env python3
"""deskwright: see and drive a desktop from a shell (Windows, macOS, Linux/X11).

  desk.py shot [--screen N] [--scale 0.5] [--window]   screenshot(s), prints PNG paths
  desk.py click X Y [--right] [--double]                 click at virtual-desktop pixels
  desk.py move X Y                                       move the pointer
  desk.py scroll N [--at X Y]                            scroll N notches (negative = down)
  desk.py type "text"                                    type literal text
  desk.py keys ctrl+l | enter | alt+tab                  press a key combo
  desk.py focus <title-regex> [--max]                    bring a window to the front
  desk.py windows                                        list windows
  desk.py screens                                        list monitors
  desk.py open <url>                                     open a URL in the default browser
"""
import argparse
import os
import re
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

OUT = Path(tempfile.gettempdir()) / "screens"


def _dpi_aware():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def _save(img, scale, name):
    from PIL import Image
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    img.save(path)
    return path


def _grabber():
    import mss
    return (getattr(mss, "MSS", None) or mss.mss)()


def cmd_screens(a):
    with _grabber() as s:
        for i, m in enumerate(s.monitors[1:]):
            print(f"screen {i}  {m['width']}x{m['height']} at {m['left']},{m['top']}")


def cmd_shot(a):
    from PIL import Image
    stamp = time.strftime("%H%M%S")
    with _grabber() as s:
        if a.window:
            w = _active_window()
            box = {"left": w.left, "top": w.top, "width": w.width, "height": w.height}
            raw = s.grab(box)
            img = Image.frombytes("RGB", raw.size, raw.rgb)
            p = _save(img, a.scale, f"win-{stamp}.png")
            print(f"{p}  window '{w.title}'  {w.width}x{w.height} at {w.left},{w.top}  scale {a.scale}")
            return
        for i, m in enumerate(s.monitors[1:]):
            if a.screen is not None and i != a.screen:
                continue
            raw = s.grab(m)
            img = Image.frombytes("RGB", raw.size, raw.rgb)
            p = _save(img, a.scale, f"s{i}-{stamp}.png")
            print(f"{p}  screen {i}  {m['width']}x{m['height']} at {m['left']},{m['top']}  scale {a.scale}")


def _mouse():
    from pynput.mouse import Controller, Button
    return Controller(), Button


def cmd_move(a):
    m, _ = _mouse()
    m.position = (a.x, a.y)
    print(f"moved {a.x},{a.y}")


def cmd_click(a):
    m, Button = _mouse()
    m.position = (a.x, a.y)
    time.sleep(0.1)
    m.click(Button.right if a.right else Button.left, 2 if a.double else 1)
    print(f"clicked {a.x},{a.y}")


def cmd_scroll(a):
    m, _ = _mouse()
    if a.at:
        m.position = tuple(a.at)
        time.sleep(0.05)
    m.scroll(0, a.n)
    print(f"scrolled {a.n}")


def cmd_type(a):
    from pynput.keyboard import Controller
    Controller().type(a.text)
    print("typed")


def _key(name):
    from pynput.keyboard import Key, KeyCode
    aliases = {"ctrl": "ctrl", "control": "ctrl", "alt": "alt", "shift": "shift", "win": "cmd",
               "cmd": "cmd", "super": "cmd", "meta": "cmd", "esc": "esc", "return": "enter",
               "del": "delete", "pgup": "page_up", "pgdn": "page_down"}
    n = aliases.get(name.lower(), name.lower())
    if hasattr(Key, n):
        return getattr(Key, n)
    if len(n) == 1:
        return KeyCode.from_char(n)
    raise SystemExit(f"unknown key: {name}")


def cmd_keys(a):
    from pynput.keyboard import Controller
    kb = Controller()
    for combo in a.combos:
        keys = [_key(k) for k in combo.split("+")]
        for k in keys:
            kb.press(k)
        for k in reversed(keys):
            kb.release(k)
        time.sleep(0.05)
    print("pressed " + " ".join(a.combos))


def _windows():
    import pywinctl
    return [w for w in pywinctl.getAllWindows() if w.title and w.width > 0 and w.height > 0]


def _active_window():
    import pywinctl
    w = pywinctl.getActiveWindow()
    if not w:
        raise SystemExit("no active window")
    return w


def cmd_windows(a):
    for w in _windows():
        print(f"{w.left:>6},{w.top:<6} {w.width:>5}x{w.height:<5} {w.title}")


def cmd_focus(a):
    rx = re.compile(a.pattern, re.I)
    for w in _windows():
        if rx.search(w.title) or rx.search(w.getAppName() or ""):
            if w.isMinimized:
                w.restore()
            if a.max:
                w.maximize()
            w.activate()
            print(f"focused '{w.title}'")
            return
    raise SystemExit(f"no window matches '{a.pattern}'")


def cmd_open(a):
    webbrowser.open(a.url)
    print(f"opened {a.url}")


def main():
    _dpi_aware()
    p = argparse.ArgumentParser(prog="desk", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("shot"); s.add_argument("--screen", type=int); s.add_argument("--scale", type=float, default=1.0)
    s.add_argument("--window", action="store_true", help="only the active window"); s.set_defaults(f=cmd_shot)
    s = sub.add_parser("click"); s.add_argument("x", type=int); s.add_argument("y", type=int)
    s.add_argument("--right", action="store_true"); s.add_argument("--double", action="store_true"); s.set_defaults(f=cmd_click)
    s = sub.add_parser("move"); s.add_argument("x", type=int); s.add_argument("y", type=int); s.set_defaults(f=cmd_move)
    s = sub.add_parser("scroll"); s.add_argument("n", type=int); s.add_argument("--at", type=int, nargs=2); s.set_defaults(f=cmd_scroll)
    s = sub.add_parser("type"); s.add_argument("text"); s.set_defaults(f=cmd_type)
    s = sub.add_parser("keys"); s.add_argument("combos", nargs="+"); s.set_defaults(f=cmd_keys)
    s = sub.add_parser("focus"); s.add_argument("pattern"); s.add_argument("--max", action="store_true"); s.set_defaults(f=cmd_focus)
    sub.add_parser("windows").set_defaults(f=cmd_windows)
    sub.add_parser("screens").set_defaults(f=cmd_screens)
    s = sub.add_parser("open"); s.add_argument("url"); s.set_defaults(f=cmd_open)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
