# desk.ps1 - desktop control helpers for agents on Windows.
# Usage:
#   desk.ps1 shot [-Screen N] [-Scale 0.5]     screenshot (all screens by default), prints PNG paths
#   desk.ps1 click X Y [-Right] [-Double]       click at virtual-desktop pixel coords
#   desk.ps1 focus <process|title-regex> [-Max] bring a window to front (optionally maximized)
#   desk.ps1 keys "<SendKeys string>"          type text/keys into the focused window (e.g. "^l", "{ENTER}")
#   desk.ps1 open <url>                         open a URL in Chrome (Default profile)
#   desk.ps1 windows                            list visible top-level windows
#   desk.ps1 screens                            list monitors and their bounds
param([Parameter(Position=0)][string]$Cmd = 'shot',
      [Parameter(Position=1)][string]$A, [Parameter(Position=2)][string]$B,
      [int]$Screen = -1, [double]$Scale = 1.0, [switch]$Right, [switch]$Double, [switch]$Max)

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
if (-not ('DeskNative' -as [type])) {
Add-Type @'
using System; using System.Runtime.InteropServices;
public class DeskNative {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int x, int y, int d, int e);
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, int f, int e);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
}
'@ }
[DeskNative]::SetProcessDPIAware() | Out-Null
$OutDir = Join-Path $env:TEMP 'screens'; New-Item -ItemType Directory -Force $OutDir | Out-Null

function Shot {
  $stamp = Get-Date -Format 'HHmmss'
  $all = [System.Windows.Forms.Screen]::AllScreens
  for ($i = 0; $i -lt $all.Count; $i++) {
    if ($Screen -ge 0 -and $i -ne $Screen) { continue }
    $b = $all[$i].Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    if ($Scale -ne 1.0) {
      $w = [int]($b.Width * $Scale); $h = [int]($b.Height * $Scale)
      $small = New-Object System.Drawing.Bitmap $w, $h
      $g2 = [System.Drawing.Graphics]::FromImage($small)
      $g2.InterpolationMode = 'HighQualityBicubic'; $g2.DrawImage($bmp, 0, 0, $w, $h); $g2.Dispose()
      $bmp.Dispose(); $bmp = $small
    }
    $p = Join-Path $OutDir "s$i-$stamp.png"; $bmp.Save($p); $g.Dispose(); $bmp.Dispose()
    "$p  screen $i  $($b.Width)x$($b.Height) at $($b.X),$($b.Y)  scale $Scale"
  }
}

function Focus($pattern) {
  $w = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and ($_.Name -match $pattern -or $_.MainWindowTitle -match $pattern) } | Select-Object -First 1
  if (-not $w) { Write-Error "no window matches '$pattern'"; exit 2 }
  # A stray Alt press lets SetForegroundWindow succeed from a background process.
  [DeskNative]::keybd_event(0x12, 0, 0, 0); [DeskNative]::keybd_event(0x12, 0, 2, 0)
  if ($Max) { [DeskNative]::ShowWindow($w.MainWindowHandle, 3) | Out-Null }
  elseif ([DeskNative]::IsIconic($w.MainWindowHandle)) { [DeskNative]::ShowWindow($w.MainWindowHandle, 9) | Out-Null }
  [DeskNative]::SetForegroundWindow($w.MainWindowHandle) | Out-Null
  "focused: $($w.Name) pid $($w.Id) '$($w.MainWindowTitle)'"
}

switch ($Cmd) {
  'shot'    { Shot }
  'click'   {
    [DeskNative]::SetCursorPos([int]$A, [int]$B) | Out-Null; Start-Sleep -Milliseconds 120
    $down, $up = if ($Right) { 8, 16 } else { 2, 4 }
    $n = if ($Double) { 2 } else { 1 }
    for ($k = 0; $k -lt $n; $k++) { [DeskNative]::mouse_event($down,0,0,0,0); [DeskNative]::mouse_event($up,0,0,0,0) }
    "clicked $A,$B"
  }
  'focus'   { Focus $A }
  'keys'    { [System.Windows.Forms.SendKeys]::SendWait($A); "sent keys" }
  'open'    { Start-Process chrome -ArgumentList '--profile-directory="Default"', $A; "opened $A" }
  'windows' { Get-Process | Where-Object MainWindowHandle -ne 0 | Select-Object Id, Name, MainWindowTitle | Format-Table -AutoSize | Out-String -Width 200 }
  'screens' { [System.Windows.Forms.Screen]::AllScreens | ForEach-Object { "$($_.DeviceName) $($_.Bounds) primary=$($_.Primary)" } }
  default   { Write-Error "unknown command $Cmd"; exit 1 }
}
