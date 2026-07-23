<#
.SYNOPSIS
  Stages HelixMod + geo-11 v0.7.10 + dxgi into Arkham Knight Binaries\Win64.
.NOTES
  Does not download archives (license / network). Place files in ..\downloads first:
    - Batman_Arkham_Knight_geo11_fix.7z
    - geo-11_v0.7.10.7z
    - dxgi.dll  (from https://github.com/bo3b/3Dmigoto/releases/download/1.3.16/dxgi.dll)
#>
[CmdletBinding()]
param(
  [string]$GameWin64 = "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64",
  [string]$Downloads = (Join-Path $PSScriptRoot "..\downloads")
)

$ErrorActionPreference = "Stop"
$seven = $null
$cmd7 = Get-Command 7z -ErrorAction SilentlyContinue
if ($cmd7) { $seven = $cmd7.Source }
if (-not $seven) {
  foreach ($p in @("$env:ProgramFiles\7-Zip\7z.exe", "$env:LOCALAPPDATA\scoop\shims\7z.exe", "$env:USERPROFILE\scoop\shims\7z.exe")) {
    if (Test-Path $p) { $seven = $p; break }
  }
}
if (-not $seven) { throw "7z.exe required" }
if (-not (Test-Path "$GameWin64\BatmanAK.exe")) { throw "BatmanAK.exe not found: $GameWin64" }

$fix7z = Join-Path $Downloads "Batman_Arkham_Knight_geo11_fix.7z"
$geo7z = Join-Path $Downloads "geo-11_v0.7.10.7z"
$dxgi = Join-Path $Downloads "dxgi.dll"
foreach ($f in @($fix7z, $geo7z, $dxgi)) {
  if (-not (Test-Path $f)) { throw "Missing: $f" }
}

$work = Join-Path $env:TEMP "arkham_knight_3d_stage"
Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $work | Out-Null

& $seven x $fix7z "-o$work\fix" -y | Out-Null
& $seven x "$work\fix\FixFiles.7z" "-o$work\fix\FixFiles" -y | Out-Null
& $seven x $geo7z "-o$work\geo" -y | Out-Null

Write-Host "Copying HelixMod FixFiles -> $GameWin64"
robocopy "$work\fix\FixFiles" $GameWin64 /E /COPY:DAT /R:2 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null

Write-Host "Upgrading d3d11.dll / nvapi64.dll from geo-11 v0.7.10"
Copy-Item "$work\geo\x64\d3d11.dll" "$GameWin64\d3d11.dll" -Force
Copy-Item "$work\geo\x64\nvapi64.dll" "$GameWin64\nvapi64.dll" -Force
Copy-Item "$work\geo\loader\x64\3DMigoto Loader.exe" "$GameWin64\3DMigoto Loader.exe" -Force
Copy-Item $dxgi "$GameWin64\dxgi.dll" -Force

# Patch inis
$dm = Get-Content "$GameWin64\d3dxdm.ini" -Raw
$dm = [regex]::Replace($dm, 'direct_mode\s*=\s*\S+', 'direct_mode = sbs')
$dm = [regex]::Replace($dm, 'show_fps_monitor\s*=\s*\S+', 'show_fps_monitor = false')
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText("$GameWin64\d3dxdm.ini", $dm, $utf8)

$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([string[]](Get-Content "$GameWin64\d3dx.ini"))
$inLoader = $false
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match '^\s*force_stereo\s*=') { $lines[$i] = 'force_stereo=2' }
  if ($lines[$i] -match '^\[Loader\]') { $inLoader = $true; continue }
  if ($inLoader -and $lines[$i] -match '^\[') { $inLoader = $false }
  if ($inLoader) {
    if ($lines[$i] -match '^\s*;?\s*target\s*=') { $lines[$i] = 'target = BatmanAK.exe' }
    elseif ($lines[$i] -match '^\s*;?\s*module\s*=') { $lines[$i] = 'module = d3d11.dll' }
    elseif ($lines[$i] -match '^\s*;?\s*launch\s*=') {
      if ($lines[$i] -notmatch 'steam://') { $lines[$i] = 'launch = BatmanAK.exe' }
    }
  }
}
[System.IO.File]::WriteAllLines("$GameWin64\d3dx.ini", $lines, $utf8)

Write-Host "Done. Launch with Launch_ArkhamKnight_3D.bat (3DMigoto Loader)."
