"""Stock d3d11 + Present INSIDE upscale.ini. Variants: mode1+dxgi, mode0+dxgi, mode0-nodxgi."""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image

PROJ = Path(r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D")
LIVE = Path(r"D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64")
SNAP = PROJ / "SNAPSHOT_v060_before_helix_20260724_134355"
WC = PROJ / "working_config"
STOCK = PROJ / "downloads" / "extracted_geo11_v0.7.10" / "x64"
OUT = WC / "PROBE_STOCK_PRESENT.txt"
SHOT = WC / "probe_shots"
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
KILLER = PROJ / "downloads" / "kill_fatal_message.ps1"

STOCK_UPSCALE = (STOCK / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
# Ensure Present run is active in the include
assert re.search(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", STOCK_UPSCALE)


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
    ps("Get-Process BatmanAK -EA SilentlyContinue | Stop-Process -Force")
    ps(
        "Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|^Message$' } "
        "| Stop-Process -Force -EA SilentlyContinue"
    )
    time.sleep(2)


def capture(name: str) -> Path:
    path = SHOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    ps(
        f"""
Add-Type -AssemblyName System.Drawing
$sig=@'
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, int flags);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
[StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int L,T,R,B; }}
'@
Add-Type -MemberDefinition $sig -Name C -Namespace N -EA SilentlyContinue
[void][N.C]::SetProcessDPIAware()
$p=Get-Process BatmanAK|Select -First 1
[N.C]::ShowWindow($p.MainWindowHandle,9)|Out-Null
[N.C]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
Start-Sleep 1
foreach($vk in 0x70,0x46){{
  [N.C]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
  [N.C]::keybd_event($vk,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 50
  [N.C]::keybd_event($vk,0,2,[UIntPtr]::Zero)
  [N.C]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 300
}}
Start-Sleep 1
$r=New-Object N.C+RECT
[void][N.C]::GetClientRect($p.MainWindowHandle,[ref]$r)
$w=$r.R-$r.L;$h=$r.B-$r.T
$bmp=New-Object System.Drawing.Bitmap $w,$h
$g=[System.Drawing.Graphics]::FromImage($bmp)
$hdc=$g.GetHdc()
[void][N.C]::PrintWindow($p.MainWindowHandle,$hdc,2)
$g.ReleaseHdc($hdc);$g.Dispose()
$bmp.Save('{str(path).replace("'", "''")}')
$bmp.Dispose()
"""
    )
    return path


def analyze(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im, dtype=np.float32)
    h, w = arr.shape[:2]
    mid = w // 2
    left, right = arr[:, :mid], arr[:, mid : mid + mid]

    def green_count(a):
        return int(
            ((a[:, :, 1] > 150) & (a[:, :, 1] > a[:, :, 0] + 25) & (a[:, :, 1] > a[:, :, 2] + 25)).sum()
        )

    gL, gR = green_count(left[:100]), green_count(right[:100])
    gBotMid = green_count(arr[int(h * 0.88) :, int(w * 0.35) : int(w * 0.65), :])
    L = np.asarray(Image.fromarray(left.astype(np.uint8)).resize((320, 180)), np.float32)
    R = np.asarray(Image.fromarray(right.astype(np.uint8)).resize((320, 180)), np.float32)

    def ncc(a, b):
        ag = a.mean(2)
        bg = b.mean(2)
        ag = (ag - ag.mean()) / (ag.std() + 1e-6)
        bg = (bg - bg.mean()) / (bg.std() + 1e-6)
        return float(np.mean(ag * bg))

    dual = gL >= 20 and gR >= 20
    return {
        "dual_fps": dual,
        "gL": gL,
        "gR": gR,
        "gBotMid": gBotMid,
        "stereo_disabled_hint": gBotMid > 40 and not dual,
        "ncc": round(ncc(L, R), 3),
        "diff": round(float(np.mean(np.abs(L - R))), 2),
        "meanL": round(float(L.mean()), 1),
        "meanR": round(float(R.mean()), 1),
        "size": f"{w}x{h}",
        "pass": dual,
    }


def run_one(name: str, mode: int, use_dxgi: bool, d3d: Path) -> dict:
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
    )
    shutil.copy2(d3d, LIVE / "d3d11.dll")
    if use_dxgi:
        shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
        assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    else:
        (LIVE / "dxgi.dll").unlink(missing_ok=True)
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    # stock upscale already has [Present] run=

    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", f"upscale_mode = {mode}", ini)
    ini = re.sub(r"(?m)^force_stereo\s*=\s*.*$", "force_stereo = 2", ini)
    ini = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*\r?\n", "", ini)
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")

    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")

    (LIVE / "d3d11_log.txt").unlink(missing_ok=True)
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))

    t0 = time.time()
    max_mb = 0
    saw = False
    while time.time() - t0 < 100:
        if int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0"):
            break
        out = ps(
            "$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1; "
            "if($p){\"$([int]($p.WS/1MB))|$($p.MainWindowTitle)\"}else{'|'}"
        ).strip()
        a, _, title = out.partition("|")
        try:
            mb = int(a)
        except ValueError:
            mb = None
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
            if mb >= 3500 and "Arkham" in title and time.time() - t0 >= 50:
                break
        elif saw:
            break
        time.sleep(2)

    crash = ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-3);Id=1000} "
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[1..3] -join ' | ')}else{''}"
    ).strip()[:220]
    alive = saw and ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() != ""
    fatal = int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0") > 0
    if not alive or fatal:
        return {
            "name": name,
            "pass": False,
            "stage": "boot",
            "max_mb": max_mb,
            "crash": crash,
            "fatal": fatal,
            "dxgi": use_dxgi,
            "mode": mode,
            "d3d": sha(d3d)[:16],
        }

    time.sleep(30)
    if ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() == "":
        return {
            "name": name,
            "pass": False,
            "stage": "watch",
            "max_mb": max_mb,
            "crash": crash,
            "dxgi": use_dxgi,
            "mode": mode,
        }

    shot = capture(f"stockpres_{name}.png")
    a = analyze(shot)
    log = LIVE / "d3d11_log.txt"
    hits = {}
    if log.exists():
        t = log.read_text(encoding="utf-8", errors="replace")
        hits = {
            "Unrecognised": t.lower().count("unrecognised entry: run = customshaderupscale"),
            "Operand50": t.count("Operand type 50"),
            "customshader_upscale": t.lower().count("customshader\\shaderfixes\\upscale.ini\\upscale"),
            "StereoProfile": t.count("StereoProfile"),
        }
    return {
        "name": name,
        "pass": bool(a.get("pass")),
        "stage": "complete",
        "alive": True,
        "max_mb": max_mb,
        "analysis": a,
        "shot": str(shot),
        "hits": hits,
        "dxgi": use_dxgi,
        "mode": mode,
        "d3d": sha(LIVE / "d3d11.dll")[:16],
    }


def main() -> None:
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
    variants = [
        ("m1_dxgi_stock", 1, True, STOCK / "d3d11.dll"),
        ("m0_dxgi_stock", 0, True, STOCK / "d3d11.dll"),
        ("m0_nodxgi_stock", 0, False, STOCK / "d3d11.dll"),
        (
            "m1_dxgi_v23",
            1,
            True,
            PROJ
            / "experimental_fork_20260724_nullguards"
            / "patched_dlls"
            / "d3d11.dll.patched_v23",
        ),
    ]
    # ensure v23 exists
    v23 = variants[-1][3]
    if not v23.exists():
        subprocess.run(
            [
                "python",
                str(
                    PROJ
                    / "experimental_fork_20260724_nullguards"
                    / "tools"
                    / "patch_d3d11_v23_nullrdx_soft.py"
                ),
                str(STOCK / "d3d11.dll"),
                str(v23),
            ],
            check=True,
        )

    results = []
    for name, mode, dxgi, d3d in variants:
        r = run_one(name, mode, dxgi, d3d)
        results.append(r)
        print(r, flush=True)
        kill()
        time.sleep(2)

    OUT.write_text("\n".join(str(x) for x in results) + "\n", encoding="utf-8")
    # leave disarmed stock
    kill()
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
    )
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    # disarm via commenting Present in upscale if present
    up = (LIVE / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    up = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", up)
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")
    print("DONE_DISARMED", flush=True)


if __name__ == "__main__":
    main()
