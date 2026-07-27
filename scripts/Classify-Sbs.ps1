# Classify Arkham on-screen output: MONO / STEREO_SBS / BLACK / FATAL / CANNOT_SEE
# Prefer projector/non-primary. Never treat RPCS3 / unrelated windows as Arkham.
param(
  [string]$OutDir = "C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D"
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ClsWin {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, uint nFlags);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
"@

function Measure-Halves([System.Drawing.Bitmap]$bmp) {
  $w = $bmp.Width; $h = $bmp.Height; $half = [int]($w / 2)
  if ($half -lt 80) { return [pscustomobject]@{ mean = -1; dark = 1; verdict = 'TOO_SMALL' } }
  $sum = 0L; $n = 0; $dark = 0
  for ($y = [int]($h * 0.2); $y -lt [int]($h * 0.8); $y += 4) {
    for ($x = 40; $x -lt ($half - 40); $x += 4) {
      $cl = $bmp.GetPixel($x, $y)
      $cr = $bmp.GetPixel($x + $half, $y)
      $sum += [Math]::Abs([int]$cl.R - [int]$cr.R) + [Math]::Abs([int]$cl.G - [int]$cr.G) + [Math]::Abs([int]$cl.B - [int]$cr.B)
      $n++
      if ($cl.R -lt 10 -and $cl.G -lt 10 -and $cl.B -lt 10) { $dark++ }
    }
  }
  $mean = [math]::Round($sum / [double]$n, 2)
  $darkFrac = [math]::Round($dark / [double]$n, 3)
  $verdict = if ($darkFrac -gt 0.9) { 'BLACK' }
    elseif ($mean -lt 12) { 'MONO' }
    elseif ($mean -gt 40) { 'STEREO_SBS' }
    else { 'UNCLEAR' }
  return [pscustomobject]@{ mean = $mean; dark = $darkFrac; verdict = $verdict; w = $w; h = $h }
}

$batman = Get-Process BatmanAK -EA SilentlyContinue | Select-Object -First 1
if (-not $batman) {
  'NO_GAME'
  exit 2
}
if (@(Get-Process | Where-Object { $_.MainWindowTitle -eq 'Message' }).Count -gt 0) {
  'FATAL_DIALOG'
  exit 3
}

$ts = Get-Date -Format 'HHmmss'
$candidates = @()

# Non-primary displays first (projector), then primary
$screens = @([System.Windows.Forms.Screen]::AllScreens | Where-Object { -not $_.Primary }) + @([System.Windows.Forms.Screen]::PrimaryScreen)
foreach ($s in $screens | Where-Object { $_ }) {
  $b = $s.Bounds
  $bmp = New-Object System.Drawing.Bitmap ([int]$b.Width), ([int]$b.Height)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen([System.Drawing.Point]::new($b.X, $b.Y), [System.Drawing.Point]::Empty, $b.Size)
  $path = Join-Path $OutDir ("classify_disp_{0}_{1}.png" -f $b.X, $ts)
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $m = Measure-Halves $bmp
  $candidates += [pscustomobject]@{ src = "display@$($b.X)"; path = $path; m = $m; bmp = $bmp }
  $g.Dispose()
}

# PrintWindow Batman (often black under exclusive FS — still try)
if ($batman.MainWindowHandle -ne [IntPtr]::Zero) {
  $r = New-Object ClsWin+RECT
  [void][ClsWin]::GetWindowRect($batman.MainWindowHandle, [ref]$r)
  $ww = [Math]::Max(1, $r.R - $r.L); $hh = [Math]::Max(1, $r.B - $r.T)
  if ($ww -gt 400 -and $hh -gt 300) {
    $bmp = New-Object System.Drawing.Bitmap $ww, $hh
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    [void][ClsWin]::PrintWindow($batman.MainWindowHandle, $hdc, 2)
    $g.ReleaseHdc($hdc)
    $path = Join-Path $OutDir ("classify_batman_pw_{0}.png" -f $ts)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $m = Measure-Halves $bmp
    $candidates += [pscustomobject]@{ src = 'batman_PrintWindow'; path = $path; m = $m; bmp = $bmp }
    $g.Dispose()
  }
}

# Pick best non-black candidate that is NOT obviously an unrelated desktop (heuristic: reject if RPCS3 title overlaps primary-only and batman PW black)
$usable = $candidates | Where-Object { $_.m.verdict -ne 'BLACK' -and $_.m.verdict -ne 'TOO_SMALL' }
if (-not $usable) {
  foreach ($c in $candidates) { $c.bmp.Dispose() }
  "CANNOT_SEE_ARKHAM_FRAME (exclusive fullscreen / virtual display not in GDI capture). batman_running=True"
  exit 4
}

# Prefer display with highest meanDiff among non-primary if present
$pick = $usable | Sort-Object { if ($_.src -like 'display@0') { 0 } else { 1 } }, { $_.m.mean } -Descending | Select-Object -First 1
Copy-Item $pick.path (Join-Path $OutDir 'classify_latest.png') -Force
$result = "$($pick.m.verdict) meanDiff=$($pick.m.mean) dark=$($pick.m.dark) src=$($pick.src) path=$($pick.path)"
Set-Content (Join-Path $OutDir 'classify_latest.txt') $result -Encoding ASCII
$result
foreach ($c in $candidates) { $c.bmp.Dispose() }
