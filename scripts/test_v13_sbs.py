"""Cold-boot v13 + loader dxgi + mode1 + packer; verify real SBS via PrintWindow."""
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
V13 = PROJ / "experimental_fork_20260724_nullguards" / "patched_dlls" / "d3d11.dll.patched_v13"
OUT = WC / "TEST_V13_SBS.txt"
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
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-8);Id=1000} "
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[3])}else{''}"
    ).strip()[:200]


def install(packer: str) -> None:
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
    shutil.copy2(V13, LIVE / "d3d11.dll")
    shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    assert sha(LIVE / "d3d11.dll").startswith("7D56ED23")

    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
    ini = re.sub(r"(?m)^force_stereo\s*=\s*.*$", "force_stereo = 2", ini)
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")
    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    dm = re.sub(r"(?m)^dm_stereo_enabled\s*=\s*1\s*$", "dm_stereo_enabled = 1", dm, count=1)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")

    if packer == "minimal":
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
    else:
        t = (STOCK / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
        t = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", t)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")


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
        mb, _ = proc()
        if mb is None:
            return False, max_mb
        max_mb = max(max_mb, mb)
        time.sleep(2)
    return True, max_mb


def overlay() -> None:
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
# Ctrl+F1 overlay, Ctrl+F fps
foreach($vk in 0x70,0x46){
  [N.K]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
  [N.K]::keybd_event($vk,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 50
  [N.K]::keybd_event($vk,0,2,[UIntPtr]::Zero)
  [N.K]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 400
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
"OK|$w|$h|$($p.MainWindowTitle)"
"""
    )
    return "OK|" in out and path.exists()


def analyze(path: Path) -> dict:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    arr = np.asarray(im, dtype=np.float32)
    # text cues
    # rough: look for green FPS in both halves
    mid = w // 2
    left, right = arr[:, :mid], arr[:, mid : mid + mid]

    def green(a):
        return int(
            ((a[:, :, 1] > 160) & (a[:, :, 1] > a[:, :, 0] + 30) & (a[:, :, 1] > a[:, :, 2] + 30)).sum()
        )

    gL, gR = green(left[:80]), green(right[:80])
    # red bug text
    red = int(((arr[:, :, 0] > 180) & (arr[:, :, 1] < 80) & (arr[:, :, 2] < 80)).sum())

    def ncc(a, b):
        ag = a.mean(2)
        bg = b.mean(2)
        ag = (ag - ag.mean()) / (ag.std() + 1e-6)
        bg = (bg - bg.mean()) / (bg.std() + 1e-6)
        return float(np.mean(ag * bg))

    L = np.asarray(Image.fromarray(left.astype(np.uint8)).resize((320, 180)), dtype=np.float32)
    R = np.asarray(Image.fromarray(right.astype(np.uint8)).resize((320, 180)), dtype=np.float32)
    same = ncc(L, R)
    diff = float(np.mean(np.abs(L - R)))
    dual = gL >= 15 and gR >= 15
    similar = same >= 0.72 and 4 <= diff <= 80 and L.mean() > 8 and R.mean() > 8
    # reject stereo disabled: check bottom strip for lots of green text single-center
    # Pass on dual green OR strong similar halves with content both sides
    passed = dual or similar
    return {
        "pass": passed,
        "dual_green": dual,
        "gL": gL,
        "gR": gR,
        "ncc": round(same, 3),
        "diff": round(diff, 2),
        "red": red,
        "meanL": round(float(L.mean()), 1),
        "meanR": round(float(R.mean()), 1),
        "size": f"{w}x{h}",
    }


def run(packer: str, watch_s: int = 100) -> dict:
    print(f"\n=== v13 {packer} ===", flush=True)
    install(packer)
    launch()
    ok, max_mb = wait_ready(120)
    if not ok:
        return {
            "packer": packer,
            "pass": False,
            "stage": "boot",
            "max_mb": max_mb,
            "crash": crash(),
            "fatal": fatal(),
        }
    alive, max2 = watch(watch_s)
    max_mb = max(max_mb, max2)
    if not alive:
        return {
            "packer": packer,
            "pass": False,
            "stage": "watch",
            "max_mb": max_mb,
            "crash": crash(),
            "fatal": fatal(),
        }
    overlay()
    time.sleep(1)
    path = SHOT / f"v13_{packer}.png"
    if not capture(path):
        return {"packer": packer, "pass": False, "stage": "capture", "max_mb": max_mb, "alive": True}
    a = analyze(path)
    return {
        "packer": packer,
        "pass": a["pass"],
        "stage": "complete",
        "max_mb": max_mb,
        "alive": True,
        "analysis": a,
        "shot": str(path),
        "op50": (LIVE / "d3d11_log.txt").read_text(encoding="utf-8", errors="replace").count(
            "Operand type 50"
        )
        if (LIVE / "d3d11_log.txt").exists()
        else -1,
    }


def main() -> None:
    start_killer()
    results = []
    winner = None
    for packer in ("minimal", "stock"):
        r = run(packer)
        results.append(r)
        print(r, flush=True)
        if r.get("pass") and r.get("alive"):
            winner = r
            break
        kill()
        time.sleep(3)

    lines = [f"TEST_V13 {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    for r in results:
        lines.append(str(r))
    lines.append(f"WINNER={winner['packer'] if winner else None}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)
    if winner:
        (WC / "V13_SBS_WINNER.txt").write_text(str(winner) + "\n", encoding="utf-8")
        # lock recipe into STACK note
        (WC / "STACK_V13.txt").write_text(
            "v0.7.0-v13 — packer alive path (verify visually before claiming)\n"
            f"- d3d11 = patched_v13 ({sha(V13)[:16]}…)\n"
            "- dxgi = loader 5B871985…\n"
            "- nvapi64 stock geo-11\n"
            f"- packer = {winner['packer']} CustomShaderUpscale\n"
            "- upscaling=1 upscale_mode=1 force_stereo=2 direct_mode=sbs\n"
            "- calib: Ctrl+F1 overlay, Ctrl+F3/F4 sep, Ctrl+F5/F6 conv (±0.15), Ctrl+T stereo toggle\n"
            f"- proof shot: {winner.get('shot')}\n",
            encoding="utf-8",
        )
        print("LEFT_RUNNING_V13", winner["packer"], flush=True)
    else:
        print("NO_WINNER", flush=True)


if __name__ == "__main__":
    main()
