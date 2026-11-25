"""Live tests: drive a real desktop against tests/target_app.py and check what it received.

They move the mouse and type, so they are skipped unless DESKWRIGHT_LIVE=1.
Run on an unlocked desktop and do not touch the mouse or keyboard meanwhile.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path(__file__).with_name("target_app.py")
BLOCK_RGB = (255, 0, 170)

pytestmark = pytest.mark.skipif(os.environ.get("DESKWRIGHT_LIVE") != "1",
                                reason="live desktop tests: set DESKWRIGHT_LIVE=1")


def desk(*args, check=True):
    r = subprocess.run([sys.executable, str(ROOT / "desk.py"), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if check:
        assert r.returncode == 0, f"desk {args} failed: {r.stderr}"
    return r


class Target:
    def __init__(self, tmp_path):
        self.path = tmp_path / "state.json"
        self.proc = subprocess.Popen([sys.executable, str(TARGET), str(self.path)])
        self.wait(lambda s: s["ready"], "target window never became ready")
        time.sleep(0.3)

    def state(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def wait(self, pred, msg, timeout=8.0):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            s = self.state()
            if s is not None:
                last = s
                if pred(s):
                    return s
            time.sleep(0.1)
        raise AssertionError(f"{msg}; last state: {last}")

    def at(self, cx, cy):
        s = self.state()
        return s["x"] + cx, s["y"] + cy

    def focus_text(self):
        desk("click", *self.at(200, 250))
        time.sleep(0.2)

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture
def target(tmp_path):
    t = Target(tmp_path)
    yield t
    t.close()


# --- typing: the 0.2.0 bugs (shifted -> '#', garbling at speed) ---

@pytest.mark.parametrize("text", [
    "hello world",
    "Hello World",
    "!@#$%^&*()_+",
    "{}|:\"<>?~",
    "[]\\;',./`-=",
    "MiXeD CaSe 123",
    "é ñ ü ç ß",
    "€ £ ¥",
    "中文 日本語",
    "🎉🚀",
])
def test_type_exact(target, text):
    target.focus_text()
    desk("type", text)
    target.wait(lambda s: s["text"] == text, f"typed {text!r}")


def test_type_long_string_not_garbled(target):
    text = "The quick brown fox jumps over the lazy dog! 0123456789 @#$% " * 3
    target.focus_text()
    desk("type", text)
    target.wait(lambda s: s["text"] == text, "long string", timeout=30)


def test_type_multiline(target):
    target.focus_text()
    desk("type", "line one\nline two\nline three")
    target.wait(lambda s: s["text"] == "line one\nline two\nline three", "multiline")


# --- keys ---

def test_keys_select_all_and_delete(target):
    target.focus_text()
    desk("type", "to be deleted")
    target.wait(lambda s: s["text"] == "to be deleted", "setup")
    desk("keys", "ctrl+a", "delete")
    target.wait(lambda s: s["text"] == "", "ctrl+a delete")


def test_keys_backspace_and_enter(target):
    target.focus_text()
    desk("type", "abc")
    desk("keys", "backspace", "enter")
    desk("type", "x")
    target.wait(lambda s: s["text"] == "ab\nx", "backspace, enter")


def test_keys_home_and_shift_end(target):
    target.focus_text()
    desk("type", "world")
    desk("keys", "home")
    desk("type", "hello ")
    target.wait(lambda s: s["text"] == "hello world", "home")


def test_keys_unknown_name_fails(target):
    assert desk("keys", "notakey", check=False).returncode != 0


# --- mouse ---

def test_click_left(target):
    desk("click", *target.at(50, 40))
    s = target.wait(lambda s: any(c[0] == 1 for c in s["clicks"]), "left click")
    btn, x, y, _ = s["clicks"][0]
    assert abs(x - 50) <= 2 and abs(y - 40) <= 2


def test_click_right(target):
    desk("click", *target.at(60, 60), "--right")
    target.wait(lambda s: any(c[0] == 3 for c in s["clicks"]), "right click")


def test_click_double(target):
    desk("click", *target.at(70, 70), "--double")
    target.wait(lambda s: any(c[3] for c in s["clicks"]), "double click")


@pytest.mark.parametrize("n,sign", [(-3, -1), (3, 1)])
def test_scroll(target, n, sign):
    desk("scroll", n, "--at", *target.at(100, 60))
    target.wait(lambda s: s["scroll"] * sign >= 1, f"scroll {n}")


def test_move(target):
    x, y = target.at(10, 10)
    desk("move", x, y)
    from pynput.mouse import Controller
    px, py = Controller().position
    assert abs(px - x) <= 1 and abs(py - y) <= 1


# --- screenshots ---

def _path(out):
    return out.split("  ")[0].strip()


def _pixel(path, x, y):
    from PIL import Image
    with Image.open(path) as im:
        return im.convert("RGB").getpixel((x, y))


def _close(a, b, tol=12):
    return all(abs(p - q) <= tol for p, q in zip(a, b))


def test_screens_lists_at_least_one():
    out = desk("screens").stdout
    assert out.startswith("screen 0")


def test_shot_full_screen_sees_target(target):
    import mss
    gx, gy = target.at(150, 60)
    with (getattr(mss, "MSS", None) or mss.mss)() as m:
        mons = m.monitors[1:]
    idx = next(i for i, mon in enumerate(mons)
               if mon["left"] <= gx < mon["left"] + mon["width"] and mon["top"] <= gy < mon["top"] + mon["height"])
    mon = mons[idx]
    out = desk("shot", "--screen", idx).stdout
    assert _close(_pixel(_path(out), gx - mon["left"], gy - mon["top"]), BLOCK_RGB)


def test_shot_scale_halves_size(target):
    from PIL import Image
    full = _path(desk("shot", "--screen", 0).stdout)
    time.sleep(1.1)
    half = _path(desk("shot", "--screen", 0, "--scale", 0.5).stdout)
    with Image.open(full) as a, Image.open(half) as b:
        assert abs(b.width - a.width / 2) <= 1 and abs(b.height - a.height / 2) <= 1


def test_shot_window_is_active_window(target):
    desk("click", *target.at(150, 60))
    time.sleep(0.3)
    out = desk("shot", "--window").stdout
    assert "deskwright-target" in out
    from PIL import Image
    with Image.open(_path(out)) as im:
        assert im.width < 900 and im.height < 700


def test_shot_rejects_zero_scale():
    assert desk("shot", "--scale", "0", check=False).returncode != 0


# --- windows and focus ---

def test_windows_lists_target(target):
    assert "deskwright-target" in desk("windows").stdout


def test_focus_brings_target_forward(target):
    desk("focus", "deskwright-target")
    time.sleep(0.4)
    out = desk("shot", "--window").stdout
    assert "deskwright-target" in out


def test_focus_no_match_fails():
    r = desk("focus", "no-such-window-zz9", check=False)
    assert r.returncode != 0 and "no window matches" in r.stderr


def test_windows_survives_unicode_titles(tmp_path):
    # A window titled with an emoji must not crash `desk windows` on a legacy console.
    code = "import tkinter as t; r=t.Tk(); r.title('deskwright 🎉 title'); r.after(4000, r.destroy); r.mainloop()"
    p = subprocess.Popen([sys.executable, "-c", code])
    try:
        time.sleep(1.0)
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        r = subprocess.run([sys.executable, str(ROOT / "desk.py"), "windows"],
                           capture_output=True, env=env, timeout=30)
        assert r.returncode == 0, r.stderr
    finally:
        p.terminate()


def test_focus_by_app_name_is_fast(target):
    # 0.2.1 looked up every window's app name through WMI: minutes on a busy desktop.
    t = time.time()
    r = desk("focus", "no-such-window-zz9", check=False)
    assert r.returncode != 0
    assert time.time() - t < 10


def test_focus_by_exe_name(target):
    exe = Path(sys.executable).name
    desk("focus", "notepad|explorer", check=False)
    out = desk("focus", exe.replace(".", r"\.")).stdout
    assert "focused" in out
