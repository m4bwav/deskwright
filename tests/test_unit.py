"""Unit tests: no desktop needed. Run anywhere, including CI."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import desk  # noqa: E402


# --- utf16_units: the Windows typing path depends on this being exact ---

@pytest.mark.parametrize("text,units", [
    ("", []),
    ("A", [0x41]),
    ("Hello", [0x48, 0x65, 0x6C, 0x6C, 0x6F]),
    ("!@#", [0x21, 0x40, 0x23]),               # shifted chars stay themselves (the 0.2.0 '#' bug)
    ("é", [0xE9]),
    ("ñ", [0xF1]),
    ("€", [0x20AC]),
    ("中", [0x4E2D]),
    ("🎉", [0xD83C, 0xDF89]),                  # surrogate pair
    ("a\nb", [0x61, 0x0A, 0x62]),
    ("a\r\nb", [0x61, 0x0A, 0x62]),            # CRLF folded
])
def test_utf16_units(text, units):
    assert desk.utf16_units(text) == units


def test_utf16_units_roundtrip_all_printable_ascii():
    s = "".join(chr(c) for c in range(32, 127))
    assert desk.utf16_units(s) == list(range(32, 127))


def test_utf16_units_roundtrip_mixed():
    s = "Hello: !@#$%^&*() {}|\"<>? é ñ 🎉 中文"
    units = desk.utf16_units(s)
    raw = b"".join(u.to_bytes(2, "little") for u in units)
    assert raw.decode("utf-16-le") == s


# --- parse_combo ---

@pytest.mark.parametrize("combo,parts", [
    ("enter", ["enter"]),
    ("ctrl+l", ["ctrl", "l"]),
    ("ctrl+shift+t", ["ctrl", "shift", "t"]),
    ("+", ["+"]),
    ("ctrl++", ["ctrl", "+"]),
    ("alt+f4", ["alt", "f4"]),
])
def test_parse_combo(combo, parts):
    assert desk.parse_combo(combo) == parts


@pytest.mark.parametrize("bad", ["ctrl+", "+a+", "a++b", ""])
def test_parse_combo_rejects_empty_parts(bad):
    with pytest.raises(SystemExit):
        desk.parse_combo(bad)


# --- _key name resolution ---

@pytest.mark.parametrize("name", ["ctrl", "control", "alt", "shift", "win", "cmd", "esc", "enter",
                                  "return", "tab", "f5", "delete", "del", "home", "pgup", "pgdn",
                                  "up", "down", "left", "right", "space", "backspace"])
def test_key_names_resolve(name):
    from pynput.keyboard import Key
    assert isinstance(desk._key(name), Key)


@pytest.mark.parametrize("ch", list("az09+-/=[];,.`"))
def test_single_chars_resolve(ch):
    from pynput.keyboard import KeyCode
    k = desk._key(ch)
    assert isinstance(k, KeyCode) and k.char == ch


def test_key_names_case_insensitive():
    assert desk._key("CTRL") == desk._key("ctrl")


def test_unknown_key_exits():
    with pytest.raises(SystemExit):
        desk._key("notakey")


# --- scale_point ---

@pytest.mark.parametrize("x,y,scale,origin,expected", [
    (100, 50, 1.0, (0, 0), (100, 50)),
    (100, 50, 0.5, (0, 0), (200, 100)),
    (100, 50, 0.25, (1680, 0), (2080, 200)),
    (10, 10, 0.5, (-8, -8), (12, 12)),
    (333, 333, 0.6, (0, 0), (555, 555)),
])
def test_scale_point(x, y, scale, origin, expected):
    assert desk.scale_point(x, y, scale, origin) == expected


@pytest.mark.parametrize("scale", [0, -1])
def test_scale_point_rejects_bad_scale(scale):
    with pytest.raises(ValueError):
        desk.scale_point(1, 1, scale)


# --- argument parsing ---

def parse(*argv):
    return desk.build_parser().parse_args(list(argv))


def test_parse_shot_defaults():
    a = parse("shot")
    assert a.screen is None and a.scale == 1.0 and a.window is False and a.f is desk.cmd_shot


def test_parse_shot_options():
    a = parse("shot", "--screen", "1", "--scale", "0.5", "--window")
    assert (a.screen, a.scale, a.window) == (1, 0.5, True)


def test_parse_click_flags():
    a = parse("click", "10", "20", "--right", "--double")
    assert (a.x, a.y, a.right, a.double) == (10, 20, True, True)


def test_parse_click_negative_coords():
    a = parse("click", "--", "-5", "-10")
    assert (a.x, a.y) == (-5, -10)


def test_parse_scroll_at():
    a = parse("scroll", "-3", "--at", "5", "6")
    assert a.n == -3 and a.at == [5, 6]


def test_parse_keys_many():
    assert parse("keys", "ctrl+a", "delete").combos == ["ctrl+a", "delete"]


def test_parse_type_keeps_text_verbatim():
    assert parse("type", "  spaced  ").text == "  spaced  "


@pytest.mark.parametrize("argv", [[], ["click", "1"], ["click", "a", "b"], ["nope"], ["scroll"]])
def test_parse_errors(argv):
    with pytest.raises(SystemExit):
        parse(*argv)


def test_main_rejects_zero_scale():
    with pytest.raises(SystemExit):
        desk.main(["shot", "--scale", "0"])


# --- the CLI as a process ---

def run(*args):
    return subprocess.run([sys.executable, str(ROOT / "desk.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_cli_help():
    r = run("--help")
    assert r.returncode == 0 and "shot" in r.stdout and "click" in r.stdout


def test_cli_unknown_command_fails():
    assert run("frobnicate").returncode != 0


def test_cli_prints_unencodable_text_without_crashing(monkeypatch, capsys):
    # 0.2.0 crashed printing an emoji window title on a cp1252 console.
    import io
    buf = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", buf)
    monkeypatch.setattr(desk, "cmd_windows", lambda a: print("title 🎉 here"))
    p = desk.build_parser()
    monkeypatch.setattr(desk, "build_parser", lambda: p)
    for sp in p._subparsers._group_actions[0].choices.values():
        if sp.prog.endswith("windows"):
            sp.set_defaults(f=desk.cmd_windows)
    desk.main(["windows"])
    buf.flush()
    assert b"title ? here" in buf.buffer.getvalue()


def test_open_uses_webbrowser(monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(desk.webbrowser, "open", seen.append)
    desk.main(["open", "https://example.com"])
    assert seen == ["https://example.com"]
    assert "opened https://example.com" in capsys.readouterr().out
