"""Quick v19 cold boot: alive 90s + PrintWindow capture + basic SBS metrics."""
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
SRC = STOCK / "d3d11.dll"
V19 = PROJ / "experimental_fork_20260724_nullguards" / "patched_dlls" / "d3d11.dll.patched_v19"
TOOL = PROJ / "experimental_fork_20260724_nullguards" / "tools" / "patch_d3d11_v19_safe_inject.py"
OUT = WC / "TEST_V19.txt"
SHOT = WC / "probe_shots" / "v19_minimal.png"
KILLER = PROJ / "downloads" / "kill_fatal_message.ps1"
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"


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


def main() -> None:
    subprocess.run(["python", str(TOOL), str(SRC), str(V19)], check=True)
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
    shutil.copy2(V19, LIVE / "d3d11.dll")
    shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    assert sha(LIVE / "d3d11.dll") == sha(V19)

    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")
    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
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
            if mb >= 3500 and "Arkham" in title and time.time() - t0 >= 55:
                break
        elif saw:
            break
        time.sleep(2)

    crash = ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-4);Id=1000} "
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[0..5] -join ' | ')}else{''}"
    ).strip()[:260]
    alive = saw and ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() != ""
    fatal = int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0") > 0

    result = {"alive": alive and not fatal, "max_mb": max_mb, "crash": crash, "fatal": fatal}
    if result["alive"]:
        time.sleep(50)
        alive2 = ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() != ""
        fatal2 = int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0") > 0
        result["alive_50"] = alive2 and not fatal2
        if result["alive_50"]:
            SHOT.parent.mkdir(parents=True, exist_ok=True)
            out = ps(
                f"""
Add-Type -AssemblyName System.Drawing
$sig=@'
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, int flags);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int L,T,R,B; }}
'@
Add-Type -MemberDefinition $sig -Name C -Namespace N -EA SilentlyContinue
[void][N.C]::SetProcessDPIAware()
$p=Get-Process BatmanAK|Select -First 1
[void][N.C]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 1
$r=New-Object N.C+RECT
[void][N.C]::GetClientRect($p.MainWindowHandle,[ref]$r)
$w=$r.R-$r.L;$h=$r.B-$r.T
$bmp=New-Object System.Drawing.Bitmap $w,$h
$g=[System.Drawing.Graphics]::FromImage($bmp)
$hdc=$g.GetHdc()
[void][N.C]::PrintWindow($p.MainWindowHandle,$hdc,2)
$g.ReleaseHdc($hdc);$g.Dispose()
$bmp.Save('{str(SHOT).replace("'", "''")}')
$bmp.Dispose(); 'OK'
"""
            )
            result["capture"] = "OK" in out
            if result["capture"] and SHOT.exists():
                im = Image.open(SHOT).convert("RGB")
                arr = np.asarray(im, dtype=np.float32)
                w, h = im.size
                mid = w // 2
                L, R = arr[:, :mid], arr[:, mid : mid + mid]
                result["size"] = f"{w}x{h}"
                result["diff"] = round(float(np.mean(np.abs(L - R))), 2)
                result["meanL"] = round(float(L.mean()), 1)
                result["meanR"] = round(float(R.mean()), 1)
                gL = int(((L[:80, :, 1] > 160) & (L[:80, :, 1] > L[:80, :, 0] + 30)).sum())
                gR = int(((R[:80, :, 1] > 160) & (R[:80, :, 1] > R[:80, :, 0] + 30)).sum())
                result["gL"] = gL
                result["gR"] = gR
                result["dual_fps"] = gL > 15 and gR > 15

    OUT.write_text(str(result) + "\n", encoding="utf-8")
    print(result, flush=True)
    if result.get("alive_50"):
        print("LEFT_RUNNING_V19", flush=True)
    else:
        print("V19_FAIL", flush=True)


if __name__ == "__main__":
    main()
