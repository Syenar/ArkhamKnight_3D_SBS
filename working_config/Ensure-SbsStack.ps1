param(
  [string]$Live = "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64",
  [string]$Proj = "C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D"
)
$ErrorActionPreference = "Stop"
$wc = Join-Path $Proj "working_config"
$stock = Join-Path $Proj "downloads\extracted_geo11_v0.7.10\x64"
$gameCfg = "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\BmGame\Config"

# v0.6.0 locked hashes (prefix match is enough for quick check; full in HASHES_v0.6.0.txt)
$ExpectDxgi = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
$ExpectD3d11 = "C89AEE44CCFA0240E1BFEA37F5F7357514AA6FBCB2E92AD34A974AC192BC0E4E"
$BadLegacyDxgi = "8603C2CB3AEED294174B3E13613C2A62275432CC2D1D6FF863D74D7B7C7C2E01"

function Copy-IfDifferent($src, $dst) {
  if (-not (Test-Path $src)) { throw "Missing source: $src" }
  if (-not (Test-Path $dst)) {
    New-Item -ItemType Directory -Path (Split-Path $dst) -Force | Out-Null
    Copy-Item $src $dst -Force
    return "copied $([IO.Path]::GetFileName($dst))"
  }
  $a = (Get-FileHash $src -Algorithm SHA256).Hash
  $b = (Get-FileHash $dst -Algorithm SHA256).Hash
  if ($a -ne $b) { Copy-Item $src $dst -Force; return "updated $([IO.Path]::GetFileName($dst))" }
  return "ok $([IO.Path]::GetFileName($dst))"
}

$log = New-Object System.Collections.Generic.List[string]
$log.Add("Ensure-SbsStack v0.6.0 $(Get-Date -Format o)")

# Configs + loader dxgi from working_config
foreach ($n in @("d3dx.ini", "d3dxdm.ini", "dxgi.dll")) {
  $log.Add((Copy-IfDifferent (Join-Path $wc $n) (Join-Path $Live $n)))
}

# stock geo-11 binaries + ShaderFixes
foreach ($n in @("d3d11.dll", "nvapi64.dll")) {
  $log.Add((Copy-IfDifferent (Join-Path $stock $n) (Join-Path $Live $n)))
}
$sfSrc = Join-Path $stock "ShaderFixes"
$sfDst = Join-Path $Live "ShaderFixes"
if (-not (Test-Path (Join-Path $sfDst "upscale.ini"))) {
  if (Test-Path $sfDst) { Remove-Item $sfDst -Recurse -Force }
  Copy-Item $sfSrc $sfDst -Recurse -Force
  $log.Add("copied ShaderFixes")
} else {
  $log.Add((Copy-IfDifferent (Join-Path $sfSrc "upscale.ini") (Join-Path $sfDst "upscale.ini")))
  $log.Add((Copy-IfDifferent (Join-Path $sfSrc "upscale.hlsl") (Join-Path $sfDst "upscale.hlsl")))
}

foreach ($n in @("BmSystemSettings.ini", "UserSystemSettings.ini")) {
  $src = Join-Path $wc $n
  $dst = Join-Path $gameCfg $n
  if (Test-Path $src) {
    Set-ItemProperty $dst -Name IsReadOnly -Value $false -EA SilentlyContinue
    $log.Add((Copy-IfDifferent $src $dst))
    Set-ItemProperty $dst -Name IsReadOnly -Value $true -EA SilentlyContinue
  }
}

$dxgiPath = Join-Path $Live "dxgi.dll"
$d3dPath = Join-Path $Live "d3d11.dll"
if (-not (Test-Path $dxgiPath)) { throw "dxgi.dll missing after ensure" }
$dxgiHash = (Get-FileHash $dxgiPath -Algorithm SHA256).Hash
$d3dHash = (Get-FileHash $d3dPath -Algorithm SHA256).Hash
$log.Add("dxgi=$dxgiHash")
$log.Add("d3d11=$d3dHash")

if ($dxgiHash -eq $BadLegacyDxgi) {
  $log | Set-Content (Join-Path $Live "ensure_sbs_log.txt") -Encoding ASCII
  throw "FAIL: legacy v0.5.0 dxgi (8603C2CB) installed. Fatal/Operand50 path. Need loader dxgi 5B871985."
}
if ($dxgiHash -ne $ExpectDxgi) {
  $log | Set-Content (Join-Path $Live "ensure_sbs_log.txt") -Encoding ASCII
  throw "FAIL: dxgi hash mismatch. Expected loader 5B871985..., got $dxgiHash"
}
if ($d3dHash -ne $ExpectD3d11) {
  $log | Set-Content (Join-Path $Live "ensure_sbs_log.txt") -Encoding ASCII
  throw "FAIL: d3d11 is not stock geo-11 (patched DLL?). Expected C89AEE44..., got $d3dHash"
}

$ini = Get-Content (Join-Path $Live "d3dx.ini") -Raw
$dm = Get-Content (Join-Path $Live "d3dxdm.ini") -Raw
$up = Get-Content (Join-Path $Live "ShaderFixes\upscale.ini") -Raw
$checks = @(
  ($ini -match '(?m)^force_stereo\s*=\s*2'),
  ($ini -match '(?m)^upscaling\s*=\s*1'),
  ($ini -match '(?m)^upscale_mode\s*=\s*1'),
  ($ini -match '(?m)^include\s*=\s*ShaderFixes\\upscale\.ini'),
  ($ini -match '(?m)^width\s*=\s*1920'),
  ($ini -match '(?m)^height\s*=\s*1080'),
  ($dm -match '(?m)^direct_mode\s*=\s*sbs'),
  ($up -match '(?m)^run\s*=\s*CustomShaderUpscale')
)
if ($checks -contains $false) {
  $log.Add("FAIL SBS checks: stereo/upscale/direct_mode/Present")
  $log | Set-Content (Join-Path $Live "ensure_sbs_log.txt") -Encoding ASCII
  throw "SBS stack incomplete after ensure"
}

$log.Add("PASS v0.6.0 SBS stack (loader dxgi + stock d3d11 + packer + direct_mode=sbs)")
$log | Set-Content (Join-Path $Live "ensure_sbs_log.txt") -Encoding ASCII
Write-Host ($log -join "`n")
