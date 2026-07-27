"""v24 + upscale Present using stereo2mono f_bb (explicit reverse blit)."""
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
TOOL = PROJ / "experimental_fork_20260724_nullguards" / "tools" / "patch_d3d11_v24_native_only.py"
DLL = PROJ / "experimental_fork_20260724_nullguards" / "patched_dlls" / "d3d11.dll.patched_v24"
OUT = WC / "TEST_V24_STEREO2MONO.txt"
SHOT = WC / "probe_shots"
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
KILLER = PROJ / "downloads" / "kill_fatal_message.ps1"

UPSCALE = """[Present]
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
; Explicit reverse stereo blit (stock uses plain f_bb).
ps-t101 = stereo2mono f_bb
draw = 4, 0
post ps-t101 = reference Resource3DVisionUpscaleBackupTexture
special = upscaling_switch_bb
"""


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
    dual = gL >= 20 and gR >= 20
    return {
        "dual_fps": dual,
        "gL": gL,
        "gR": gR,
        "gBotMid": gBotMid,
        "stereo_disabled_hint": gBotMid > 40 and not dual,
        "meanL": round(float(left.mean()), 1),
        "meanR": round(float(right.mean()), 1),
        "size": f"{w}x{h}",
        "pass": dual,
    }


def gut_present(dm: str) -> str:
    lines = dm.splitlines(keepends=True)
    out = []
    in_present = False
    for line in lines:
        if re.match(r"^\[Present\]\s*$", line):
            in_present = True
            out.append(line)
            out.append("; OP50: Present body disabled\n")
            continue
        if in_present and re.match(r"^\[", line):
            in_present = False
        if in_present and line.strip() and not line.lstrip().startswith(";"):
            out.append(";" + line)
        else:
            out.append(line)
    return "".join(out)


def main() -> None:
    subprocess.run(["python", str(TOOL), str(STOCK / "d3d11.dll"), str(DLL)], check=True)
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
    shutil.copy2(DLL, LIVE / "d3d11.dll")
    shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(UPSCALE, encoding="utf-8")
    assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI

    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
    ini = re.sub(r"(?m)^force_stereo\s*=\s*.*$", "force_stereo = 2", ini)
    ini = re.sub(r"(?m)^show_fps_monitor\s*=\s*.*$", "show_fps_monitor = 1", ini)
    ini = re.sub(r"(?m)^width\s*=\s*.*$", "width = 1920", ini)
    ini = re.sub(r"(?m)^height\s*=\s*.*$", "height = 1080", ini)
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")

    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    dm = re.sub(r"(?m)^dm_patching_mode\s*=\s*.*$", "dm_patching_mode = 1", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    (LIVE / "d3dxdm.ini").write_text(gut_present(dm), encoding="utf-8")

    (LIVE / "d3d11_log.txt").unlink(missing_ok=True)
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))

    t0 = time.time()
    max_mb = 0
    saw = False
    while time.time() - t0 < 110:
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
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[1..3] -join ' | ')}else{''}"
    ).strip()[:280]
    alive = saw and ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() != ""
    fatal = int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0") > 0
    if not alive or fatal:
        r = {"pass": False, "stage": "boot", "max_mb": max_mb, "crash": crash, "fatal": fatal}
        OUT.write_text(str(r) + "\n", encoding="utf-8")
        print(r, flush=True)
        print("S2M_FAIL_BOOT", flush=True)
        return

    time.sleep(35)
    shot = capture("v24_stereo2mono.png")
    a1 = analyze(shot)
    print("FINAL", a1, flush=True)
    alive = ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() != ""
    hits = {}
    if (LIVE / "d3d11_log.txt").exists():
        t = (LIVE / "d3d11_log.txt").read_text(encoding="utf-8", errors="replace")
        hits = {
            "Operand50": t.count("Operand type 50"),
            "stereo2mono": t.lower().count("stereo2mono"),
            "GetFakeDirectMode": t.count("GetFakeDirectMode"),
            "customshader_upscale": t.lower().count("customshader\\shaderfixes\\upscale.ini\\upscale"),
            "Unrecognised": t.lower().count("unrecognised entry: run = customshaderupscale"),
        }
    result = {
        "pass": bool(a1.get("pass")) and alive,
        "alive": alive,
        "max_mb": max_mb,
        "final": a1,
        "shot": str(shot),
        "hits": hits,
        "d3d": sha(LIVE / "d3d11.dll")[:16],
        "sfdm": len(list((LIVE / "ShaderFixesDM").glob("*"))) if (LIVE / "ShaderFixesDM").exists() else 0,
    }
    OUT.write_text(str(result) + "\n", encoding="utf-8")
    print(result, flush=True)
    print("S2M_SBS" if result["pass"] else "S2M_ALIVE_NO_SBS", flush=True)


if __name__ == "__main__":
    main()
