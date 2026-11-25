# deskwright

One PowerShell script that lets an AI agent (or you) see and drive a Windows desktop: screenshots of every monitor, clicks, focusing windows, keystrokes, opening URLs. No modules, no installs, no browser extension. Useful when an agent has a shell but no computer-use or browser tools.

## Commands

| Command | What it does |
|---|---|
| `desk.ps1 shot [-Screen N] [-Scale 0.5]` | One PNG per monitor in `%TEMP%\screens`, prints the paths and bounds. `-Scale` shrinks the image (a full 2560x1440 shot costs a vision model far more than a half-size one). |
| `desk.ps1 click X Y [-Right] [-Double]` | Click at virtual-desktop pixels. Monitors to the right of the primary start at its width. |
| `desk.ps1 focus <process-or-title-regex> [-Max]` | Bring a window to the front, optionally maximized. |
| `desk.ps1 keys "^l"` | Send keys to the focused window ([SendKeys syntax](https://learn.microsoft.com/dotnet/api/system.windows.forms.sendkeys)). |
| `desk.ps1 open <url>` | Open a URL in Chrome with the Default profile. |
| `desk.ps1 windows` | List visible top-level windows. |
| `desk.ps1 screens` | List monitors and their bounds. |

Screenshot pixels map 1:1 to click coordinates at `-Scale 1`; divide by the scale otherwise. The script calls `SetProcessDPIAware`, so coordinates are physical pixels on scaled displays.

## Example

```powershell
.\desk.ps1 open https://example.com
.\desk.ps1 focus chrome -Max
.\desk.ps1 shot -Screen 0 -Scale 0.5
.\desk.ps1 click 640 420
```

## Requirements

Windows 10 or 11, Windows PowerShell 5.1 or PowerShell 7. Run it in an interactive desktop session: a service or a locked screen captures black frames.

## Safety

It does exactly what it is told, on the real desktop. Agents driving it should screenshot before and after every click, and never type passwords or approve payments through it.

MIT licensed.
