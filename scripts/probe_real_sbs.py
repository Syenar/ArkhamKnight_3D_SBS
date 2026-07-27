"""Cold-boot candidates for REAL half-SBS. Uses PrintWindow + strict dual-scene check.

Does not ask user to look. Writes PROBE_REAL_SBS.txt. Leaves winner running only on pass.
"""
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
PATCH = PROJ / "experimental_fork_20260724_nullguards" / "patched_dlls"
OUT = WC / "PROBE_REAL_SBS.txt"
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


def kill_all() -> None:
    ps("Get-Process BatmanAK,rpcs3 -EA SilentlyContinue | Stop-Process -Force")
    ps(
        "Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|^Message$|Fight Night' } "
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
    if "|" not in out:
        return None, ""
    a, b = out.split("|", 1)
    try:
        return int(a), b
    except ValueError:
        return None, b


def fatal() -> bool:
    return int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0") > 0


def crash() -> str:
    return ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-6);Id=1000} "
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[3])}else{''}"
    ).strip()[:180]


def wipe() -> None:
    for n in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
        p = LIVE / n
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def install(d3d: Path, dxgi: bool) -> None:
    kill_all()
    wipe()
    for n in ("d3dx.ini", "d3dxdm.ini"):
        shutil.copy2(SNAP / n, LIVE / n)
    shutil.copy2(d3d, LIVE / "d3d11.dll")
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    if dxgi:
        shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
        assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    else:
        (LIVE / "dxgi.dll").unlink(missing_ok=True)
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    for p in (LIVE / "ShaderFixes").glob("*.bin"):
        p.unlink(missing_ok=True)
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
    # re-assert variant
    shutil.copy2(d3d, LIVE / "d3d11.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if dxgi:
        shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    else:
        (LIVE / "dxgi.dll").unlink(missing_ok=True)
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")


def set_ini(mode: int, upscaling: int = 1) -> None:
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", f"upscaling = {upscaling}", ini)
    if re.search(r"(?m)^upscale_mode\s*=", ini):
        ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", f"upscale_mode = {mode}", ini)
    else:
        ini = re.sub(r"(?m)^(upscaling\s*=\s*\d+\s*)$", rf"\1\nupscale_mode = {mode}", ini)
    out = []
    for line in ini.splitlines(keepends=True):
        s = line.strip()
        if s.startswith("include = ShaderFixes\\3dvision2sbs.ini"):
            out.append(";include = ShaderFixes\\3dvision2sbs.ini\n")
        elif s.startswith("include = ShaderFixes\\UE3_"):
            continue
        else:
            out.append(line)
    ini = "".join(out)
    if "include = ShaderFixes\\upscale.ini" not in ini:
        ini = re.sub(
            r"(?m)^(\[Include\]\s*\r?\n)",
            r"\1include = ShaderFixes\\upscale.ini\n",
            ini,
        )
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")
    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")


MINIMAL = """[Present]
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
"""


def write_packer(kind: str) -> None:
    if kind == "minimal":
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(MINIMAL, encoding="utf-8")
    elif kind == "stock":
        t = (STOCK / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
        t = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", t)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
    elif kind == "off":
        t = (STOCK / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
        t = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", t)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
    else:
        raise SystemExit(kind)


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


def watch(sec: int) -> tuple[bool, int]:
    t0 = time.time()
    max_mb = 0
    while time.time() - t0 < sec:
        if fatal():
            return False, max_mb
        mb, title = proc()
        if mb is None:
            return False, max_mb
        max_mb = max(max_mb, mb)
        time.sleep(2)
    return True, max_mb


def send_overlay() -> None:
    ps(
        r"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
if(-not $p){return}
[N.K]::ShowWindow($p.MainWindowHandle,9)|Out-Null
[N.K]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
Start-Sleep 1
foreach($vk in 0x70,0x46){ # F1, F
  [N.K]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
  [N.K]::keybd_event($vk,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 50
  [N.K]::keybd_event($vk,0,2,[UIntPtr]::Zero)
  [N.K]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 300
}
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


def strict_sbs(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    im = im.crop((0, int(h * 0.05), w, h))
    w, h = im.size
    mid = w // 2
    left = np.asarray(im.crop((0, 0, mid, h)).resize((320, 180)), dtype=np.float32)
    right = np.asarray(im.crop((mid, 0, w, h)).resize((320, 180)), dtype=np.float32)
    if left.mean() < 3 and right.mean() < 3:
        return {"verdict": "BLACK", "pass": False}

    def ncc(a, b):
        ag = a.mean(2)
        bg = b.mean(2)
        ag = (ag - ag.mean()) / (ag.std() + 1e-6)
        bg = (bg - bg.mean()) / (bg.std() + 1e-6)
        return float(np.mean(ag * bg))

    same = ncc(left, right)
    diff = float(np.mean(np.abs(left - right)))

    # Centroid x of bright pixels in each half (0..1 within half)
    def centroid_x(a):
        g = a.mean(2)
        mask = g > max(20, g.mean() + 10)
        if mask.sum() < 50:
            mask = g > g.mean()
        ys, xs = np.where(mask)
        return float(xs.mean() / 319.0) if len(xs) else 0.5

    cL, cR = centroid_x(left), centroid_x(right)
    # True SBS title: both halves show batman near right-center of each half → similar centroids
    # Mono split: left half centroid often left (text), right half different
    centroid_delta = abs(cL - cR)

    # Green overlay pixels (FPS / sep) in both halves
    top = np.concatenate([left[:40], right[:40]], axis=0)  # unused
    def green_count(a):
        return int(((a[:, :, 1] > 170) & (a[:, :, 1] > a[:, :, 0] + 35) & (a[:, :, 1] > a[:, :, 2] + 35)).sum())

    gL, gR = green_count(left[:50]), green_count(right[:50])

    # Pass criteria: similar full-scene halves OR dual green overlays
    dual_green = gL >= 15 and gR >= 15
    similar_scene = same >= 0.75 and centroid_delta <= 0.18 and 5 <= diff <= 70
    # Reject classic mono title: left mean content on left, right has the bust
    # Extra: both halves must have edge energy in the RIGHT portion of the half (batman)
    def right_third_energy(a):
        g = a.mean(2)
        return float(np.abs(np.diff(g[:, 210:], axis=1)).mean())

    eL, eR = right_third_energy(left), right_third_energy(right)
    both_have_right_content = eL > 0.8 and eR > 0.8

    passed = dual_green or (similar_scene and both_have_right_content)
    return {
        "verdict": "REAL_SBS" if passed else "MONO_OR_FAIL",
        "pass": passed,
        "ncc": round(same, 3),
        "diff": round(diff, 2),
        "cL": round(cL, 3),
        "cR": round(cR, 3),
        "cDelta": round(centroid_delta, 3),
        "gL": gL,
        "gR": gR,
        "eL": round(eL, 2),
        "eR": round(eR, 2),
        "meanL": round(float(left.mean()), 1),
        "meanR": round(float(right.mean()), 1),
        "size": f"{w}x{h}",
    }


VARIANTS = [
    {
        "name": "m0_dxgi_minimal",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": True,
        "mode": 0,
        "packer": "minimal",
    },
    {
        "name": "m0_nodxgi_minimal",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": False,
        "mode": 0,
        "packer": "minimal",
    },
    {
        "name": "patched_v12_m1_stock",
        "d3d": PATCH / "d3d11.dll.patched_v12",
        "dxgi": True,
        "mode": 1,
        "packer": "stock",
    },
    {
        "name": "patched_v11_m1_minimal",
        "d3d": PATCH / "d3d11.dll.patched_v11",
        "dxgi": True,
        "mode": 1,
        "packer": "minimal",
    },
    {
        "name": "patched_v9_m1_minimal",
        "d3d": PATCH / "d3d11.dll.patched_v9",
        "dxgi": True,
        "mode": 1,
        "packer": "minimal",
    },
    {
        "name": "stock_m1_dxgi_stock",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": True,
        "mode": 1,
        "packer": "stock",
    },
]


def run_one(v: dict) -> dict:
    print(f"\n=== {v['name']} ===", flush=True)
    if not v["d3d"].exists():
        return {"name": v["name"], "pass": False, "stage": "missing_dll"}
    install(v["d3d"], v["dxgi"])
    set_ini(v["mode"], 1)
    write_packer(v["packer"])
    launch()
    ok, max_mb = wait_ready(120)
    if not ok:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "boot",
            "max_mb": max_mb,
            "crash": crash(),
            "fatal": fatal(),
        }
    alive, max2 = watch(75)
    max_mb = max(max_mb, max2)
    if not alive:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "watch",
            "max_mb": max_mb,
            "crash": crash(),
        }
    send_overlay()
    time.sleep(1)
    path = SHOT / f"real_{v['name']}.png"
    if not capture(path):
        return {"name": v["name"], "pass": False, "stage": "capture", "max_mb": max_mb}
    analysis = strict_sbs(path)
    return {
        "name": v["name"],
        "pass": analysis["pass"],
        "stage": "complete",
        "max_mb": max_mb,
        "analysis": analysis,
        "shot": str(path),
        "d3d": sha(LIVE / "d3d11.dll")[:16],
        "dxgi": (LIVE / "dxgi.dll").exists(),
    }


def main() -> None:
    SHOT.mkdir(parents=True, exist_ok=True)
    start_killer()
    # kill competing window first
    kill_all()
    results = []
    winner = None
    for v in VARIANTS:
        r = run_one(v)
        results.append(r)
        print(r, flush=True)
        if r.get("pass"):
            winner = r
            break
        kill_all()
        time.sleep(3)

    lines = [f"PROBE_REAL_SBS {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    for r in results:
        lines.append(str(r))
    lines.append(f"WINNER={winner['name'] if winner else None}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)

    if winner:
        (WC / "REAL_SBS_WINNER.txt").write_text(str(winner) + "\n", encoding="utf-8")
        print("LEFT_RUNNING_REAL_SBS", winner["name"], flush=True)
    else:
        kill_all()
        install(STOCK / "d3d11.dll", True)
        set_ini(1, 1)
        write_packer("off")
        launch()
        wait_ready(90)
        print("LEFT_DISARMED", flush=True)


if __name__ == "__main__":
    main()
