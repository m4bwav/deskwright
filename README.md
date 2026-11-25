# deskwright

Let an AI agent (or you) see and drive a desktop from a shell: screenshots of every monitor or just the active window, clicks, scrolling, typing, key combos, focusing windows, opening URLs. Works where an agent has a shell but no computer-use or browser tools.

Runs on **Windows, macOS and Linux (X11)** with Python 3.9+. A dependency-free PowerShell version, `desk.ps1`, is kept for Windows machines without Python.

## Install

```sh
pip install git+https://github.com/m4bwav/deskwright
# or just: pip install mss pillow pynput pywinctl  and run desk.py
```

## Commands

| Command | What it does |
|---|---|
| `desk shot [--screen N] [--scale 0.5] [--window]` | PNG per monitor (or only the active window) in `<tmp>/screens`, prints paths and bounds. `--scale` shrinks images; vision models pay per pixel. |
| `desk click X Y [--right] [--double]` | Click at virtual-desktop pixels. |
| `desk move X Y` | Move the pointer. |
| `desk scroll N [--at X Y]` | Scroll N notches, negative is down. |
| `desk type "text"` | Type literal text. |
| `desk keys ctrl+l enter` | Press key combos in order (`ctrl`, `alt`, `shift`, `cmd`/`win`, `tab`, `esc`, `f5`, letters...). |
| `desk focus <regex> [--max]` | Bring the first window whose title or app matches to the front. |
| `desk windows` | List windows with bounds. |
| `desk screens` | List monitors with bounds. |
| `desk open <url>` | Open a URL in the default browser. |

Screenshot pixels map 1:1 to click coordinates at `--scale 1`; divide by the scale otherwise. On Windows the script is per-monitor DPI aware, so coordinates are physical pixels.

## Example: an agent loop

```sh
desk open https://example.com
desk focus example --max
desk shot --window --scale 0.5     # look
desk click 640 420                 # act
desk shot --window --scale 0.5     # check
```

## Known limits

- `type` sends about 50 characters a second; slow apps drop keys if pushed faster.
- `focus` matches top-level windows. Tabbed apps (Notepad, browsers) share one window, so screenshot to confirm the right tab is in front before keys like `ctrl+w`.

## Platform notes

- **macOS:** grant your terminal Screen Recording and Accessibility permission (System Settings > Privacy & Security), or screenshots come back blank and input is ignored.
- **Linux:** X11 sessions work. Wayland blocks global screenshots and synthetic input for ordinary apps; run an X11 session or XWayland apps.
- **All:** run in an interactive, unlocked desktop session. Services and locked screens capture black frames.

## Safety

It does exactly what it is told, on the real desktop. Agents driving it should screenshot before and after every action, and never type passwords or approve payments through it. Screenshots can contain anything that was on screen; delete `<tmp>/screens` when done.

MIT licensed.
