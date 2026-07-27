"""v11 packer survives; prior capture showed 'Stereo disabled'. Toggle Ctrl+T and verify SBS."""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

PROJ = Path(r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D")
LIVE = Path(r"D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64")
SNAP = PROJ / "SNAPSHOT_v060_before_helix_20260724_134355"
WC = PROJ / "working_config"
STOCK = PROJ / "downloads" / "extracted_geo11_v0.7.10" / "x64"
V11 = PROJ / "experimental_fork_20260724_nullguards" / "patched_dlls" / "d3d11.dll.patched_v11"
OUT = WC / "TEST_V11_STEREO.txt"
SHOT = WC / "probe_shots"
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
KILLER = PROJ / "downloads" / "kill_fatal_message.ps1"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def ps(cmd: str) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    return (r.stdout or "") + (r.stderr or "")


def kill() -> None:
    ps("Get-Process BatmanAK,rpcs3 -EA SilentlyContinue | Stop-Process -Force")
    ps(
        "Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|^Message$' } "
        "| Stop-Process -Force -EA SilentlyContinue"
    )
    time.sleep(2)


def start_killer() -> None:
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(KILLER),
        ],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )


def proc() -> tuple[int | None, str]:
    out = ps(
        "$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1; "
        "if($p){\"$([int]($p.WS/1MB))|$($p.MainWindowTitle)\"}else{'|'}"
    ).strip()
    a, _, b = out.partition("|")
    try:
        return int(a), b
    except ValueError:
        return None, b


def fatal() -> bool:
    return int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0") > 0


def crash() -> str:
    return ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-6);Id=1000} "
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[0..5] -join ' | ')}else{''}"
    ).strip()[:280]


def install() -> None:
    kill()
    for n in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
        p = LIVE / n
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WC / "Ensure-SbsStack.ps1"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    shutil.copy2(V11, LIVE / "d3d11.dll")
    shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    assert sha(LIVE / "d3d11.dll") == sha(V11)

    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
    ini = re.sub(r"(?m)^force_stereo\s*=\s*.*$", "force_stereo = 2", ini)
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")
    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    # force enabled; keep toggle bang intact for other lines
    dm = re.sub(r"(?m)^dm_stereo_enabled\s*=\s*0\s*$", "dm_stereo_enabled = 1", dm)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    # ensure overlay can show
    dm = re.sub(r"(?m)^;?show_stereo_params\s*=\s*.*$", "show_stereo_params = 1", dm)
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")

    (LIVE / "ShaderFixes" / "upscale.ini").write_text(
        """[Present]
run = CustomShaderUpscale

[Resource3DVisionUpscaleBackupTexture]
[CustomShaderUpscale]
vs = upscale.hlsl
ps = upscale.hlsl
hs = null
ds = null
gs = null
blend = disable
cull = none
sampler = anisotropic_filter
topology = triangle_strip
o0 = set_viewport r_bb
Resource3DVisionUpscaleBackupTexture = reference ps-t101
ps-t101 = f_bb
draw = 4, 0
post ps-t101 = reference Resource3DVisionUpscaleBackupTexture
special = upscaling_switch_bb
""",
        encoding="utf-8",
    )


def launch() -> None:
    (LIVE / "d3d11_log.txt").unlink(missing_ok=True)
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))


def wait_ready(timeout=120) -> tuple[bool, int]:
    t0 = time.time()
    max_mb = 0
    saw = False
    while time.time() - t0 < timeout:
        if fatal():
            return False, max_mb
        mb, title = proc()
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
            if mb >= 3500 and "Arkham" in title and time.time() - t0 >= 55:
                return True, max_mb
        elif saw:
            return False, max_mb
        time.sleep(2)
    mb, title = proc()
    return mb is not None and "Arkham" in title and not fatal(), max(max_mb, mb or 0)


def watch(sec: int) -> bool:
    t0 = time.time()
    while time.time() - t0 < sec:
        if fatal() or proc()[0] is None:
            return False
        time.sleep(2)
    return True


def keys(sequence: str) -> None:
    """sequence: 'ctrl+t', 'ctrl+f1', 'ctrl+f'"""
    ps(
        rf"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
if(-not $p){{return}}
[N.K]::ShowWindow($p.MainWindowHandle,9)|Out-Null
[N.K]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
Start-Sleep 1
function Chord([byte[]]$vks) {{
  foreach($vk in $vks){{ [N.K]::keybd_event($vk,0,0,[UIntPtr]::Zero) }}
  Start-Sleep -Milliseconds 60
  foreach($vk in ($vks[[int]($vks.Length-1)..0])){{ [N.K]::keybd_event($vk,0,2,[UIntPtr]::Zero) }}
}}
$seq='{sequence}'
if($seq -eq 'ctrl+t'){{ Chord 0x11,0x54 }}
elseif($seq -eq 'ctrl+f1'){{ Chord 0x11,0x70 }}
elseif($seq -eq 'ctrl+f'){{ Chord 0x11,0x46 }}
"""
    )


def capture(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = ps(
        f"""
Add-Type -AssemblyName System.Drawing
$sig=@'
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, int flags);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n);
[StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int L,T,R,B; }}
'@
Add-Type -MemberDefinition $sig -Name C -Namespace N -EA SilentlyContinue
[void][N.C]::SetProcessDPIAware()
$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1
if(-not $p -or $p.MainWindowTitle -notmatch 'Arkham'){{ 'BAD'; return }}
[void][N.C]::ShowWindow($p.MainWindowHandle,9)
[void][N.C]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 1
$r=New-Object N.C+RECT
[void][N.C]::GetClientRect($p.MainWindowHandle,[ref]$r)
$w=$r.R-$r.L; $h=$r.B-$r.T
$bmp=New-Object System.Drawing.Bitmap $w,$h
$g=[System.Drawing.Graphics]::FromImage($bmp)
$hdc=$g.GetHdc()
[void][N.C]::PrintWindow($p.MainWindowHandle,$hdc,2)
$g.ReleaseHdc($hdc); $g.Dispose()
$bmp.Save('{str(path).replace("'", "''")}')
$bmp.Dispose()
"OK|$w|$h"
"""
    )
    return "OK|" in out and path.exists()


def analyze(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    arr = np.asarray(im, dtype=np.float32)
    mid = w // 2
    left, right = arr[:, :mid], arr[:, mid : mid + mid]

    def green(a):
        return int(
            ((a[:, :, 1] > 160) & (a[:, :, 1] > a[:, :, 0] + 30) & (a[:, :, 1] > a[:, :, 2] + 30)).sum()
        )

    gL, gR = green(left[:100]), green(right[:100])
    # OCR-free: look for "Stereo disabled" tendency — lots of green text bottom center only
    bottom = arr[int(h * 0.85) :, :, :]
    gBot = green(bottom)

    def ncc(a, b):
        ag = a.mean(2)
        bg = b.mean(2)
        ag = (ag - ag.mean()) / (ag.std() + 1e-6)
        bg = (bg - bg.mean()) / (bg.std() + 1e-6)
        return float(np.mean(ag * bg))

    L = np.asarray(Image.fromarray(left.astype(np.uint8)).resize((320, 180)), np.float32)
    R = np.asarray(Image.fromarray(right.astype(np.uint8)).resize((320, 180)), np.float32)
    same = ncc(L, R)
    diff = float(np.mean(np.abs(L - R)))
    dual = gL >= 20 and gR >= 20
    similar = same >= 0.72 and 5 <= diff <= 80
    return {
        "dual_green": dual,
        "gL": gL,
        "gR": gR,
        "gBot": gBot,
        "ncc": round(same, 3),
        "diff": round(diff, 2),
        "meanL": round(float(L.mean()), 1),
        "meanR": round(float(R.mean()), 1),
        "size": f"{w}x{h}",
        "pass": dual or similar,
    }


def main() -> None:
    start_killer()
    install()
    launch()
    ok, max_mb = wait_ready(120)
    if not ok:
        r = {"pass": False, "stage": "boot", "max_mb": max_mb, "crash": crash()}
        OUT.write_text(str(r), encoding="utf-8")
        print(r, flush=True)
        sys.exit(1)
    if not watch(40):
        r = {"pass": False, "stage": "watch", "crash": crash()}
        OUT.write_text(str(r), encoding="utf-8")
        print(r, flush=True)
        sys.exit(1)

    keys("ctrl+f1")
    time.sleep(0.5)
    keys("ctrl+f")
    time.sleep(0.5)
    pre = SHOT / "v11_pre_toggle.png"
    capture(pre)
    a0 = analyze(pre)
    print("PRE", a0, flush=True)

    # Toggle stereo on (if disabled)
    keys("ctrl+t")
    time.sleep(2)
    keys("ctrl+f1")
    time.sleep(0.5)
    keys("ctrl+f")
    time.sleep(0.5)
    post = SHOT / "v11_post_toggle.png"
    capture(post)
    a1 = analyze(post)
    print("POST", a1, flush=True)

    # If still not, toggle again (in case we turned it off)
    if not a1.get("pass"):
        keys("ctrl+t")
        time.sleep(2)
        keys("ctrl+f")
        time.sleep(0.5)
        post2 = SHOT / "v11_post_toggle2.png"
        capture(post2)
        a2 = analyze(post2)
        print("POST2", a2, flush=True)
    else:
        a2 = a1
        post2 = post

    alive = proc()[0] is not None and not fatal()
    # module check
    mod = ps(
        "$p=Get-Process BatmanAK -EA SilentlyContinue; "
        "try { ($p.Modules|?{$_.ModuleName -eq 'd3d11.dll'}).FileName } catch { 'err' }"
    ).strip()

    result = {
        "pass": bool(a2.get("pass")) and alive,
        "alive": alive,
        "max_mb": max_mb,
        "pre": a0,
        "post": a1,
        "final": a2,
        "d3d11_module": mod,
        "crash": crash() if not alive else "",
        "shot": str(post2),
    }
    OUT.write_text(str(result) + "\n", encoding="utf-8")
    print(result, flush=True)
    if result["pass"]:
        print("LEFT_RUNNING_V11_SBS", flush=True)
    else:
        print("V11_NO_SBS_YET alive=", alive, flush=True)


if __name__ == "__main__":
    main()
