"""Probe upscale_mode=0 packer paths with Batman-only capture (PrintWindow).

mode0 was the only Present-blit path that survived cold boot in probe_packer_variants.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJ = Path(r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D")
LIVE = Path(r"D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64")
SNAP = PROJ / "SNAPSHOT_v060_before_helix_20260724_134355"
WC = PROJ / "working_config"
STOCK = PROJ / "downloads" / "extracted_geo11_v0.7.10" / "x64"
OUT = WC / "PROBE_MODE0.txt"
SHOT_DIR = WC / "probe_shots"
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
KILLER = PROJ / "downloads" / "kill_fatal_message.ps1"
sys.path.insert(0, str(PROJ / "downloads"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def ps(cmd: str) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    return (r.stdout or "") + (r.stderr or "")


def kill_game() -> None:
    ps("Get-Process BatmanAK -EA SilentlyContinue | Stop-Process -Force")
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
        cwd=str(PROJ),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )


def proc_info() -> tuple[int | None, str]:
    out = ps(
        "$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1; "
        "if($p){\"$([int]($p.WS/1MB))|$($p.MainWindowTitle)\"} else {'|'}"
    ).strip()
    if "|" not in out:
        return None, ""
    mb_s, title = out.split("|", 1)
    try:
        return int(mb_s), title
    except ValueError:
        return None, title


def fatal() -> bool:
    return (
        int(
            ps(
                "@(Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|^Message$' }).Count"
            ).strip()
            or "0"
        )
        > 0
    )


def last_crash() -> str:
    return ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-6); Id=1000} "
        "-EA SilentlyContinue | Select -First 1; if($e){(($e.Message -split \"`n\")[3])} else {''}"
    ).strip()[:160]


def wipe() -> None:
    for name in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
        p = LIVE / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def install_base(with_dxgi: bool) -> None:
    kill_game()
    wipe()
    for name in ("d3d11.dll", "nvapi64.dll", "d3dx.ini", "d3dxdm.ini"):
        shutil.copy2(SNAP / name, LIVE / name)
    if with_dxgi:
        shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
        assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    else:
        (LIVE / "dxgi.dll").unlink(missing_ok=True)
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    for p in (LIVE / "ShaderFixes").glob("*.bin"):
        p.unlink(missing_ok=True)
    # game res via Ensure (may re-add dxgi) then re-apply
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
    shutil.copy2(SNAP / "d3d11.dll", LIVE / "d3d11.dll")
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if with_dxgi:
        shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    else:
        (LIVE / "dxgi.dll").unlink(missing_ok=True)
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")


def apply_ini(upscale_mode: int, upscaling: int = 1) -> None:
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", f"upscaling = {upscaling}", ini)
    if re.search(r"(?m)^upscale_mode\s*=", ini):
        ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", f"upscale_mode = {upscale_mode}", ini)
    else:
        ini = re.sub(
            r"(?m)^(upscaling\s*=\s*\d+\s*)$",
            rf"\1\nupscale_mode = {upscale_mode}",
            ini,
        )
    ini = re.sub(r"(?m)^force_stereo\s*=\s*.*$", "force_stereo = 2", ini)
    ini = re.sub(r"(?m)^get_resolution_from\s*=\s*.*$", "get_resolution_from = swap_chain", ini)
    # strip bad includes
    out_lines = []
    for line in ini.splitlines(keepends=True):
        s = line.strip()
        if s.startswith("include = ShaderFixes\\3dvision2sbs.ini"):
            out_lines.append(";include = ShaderFixes\\3dvision2sbs.ini\n")
        elif s.startswith("include = ShaderFixes\\UE3_"):
            continue
        else:
            out_lines.append(line)
    ini = "".join(out_lines)
    if "include = ShaderFixes\\upscale.ini" not in ini:
        ini = re.sub(
            r"(?m)^(\[Include\]\s*\r?\n)",
            r"\1include = ShaderFixes\\upscale.ini\n",
            ini,
        )
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


def write_packer(kind: str) -> None:
    if kind == "off":
        t = (STOCK / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
        t = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", t)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
    elif kind == "minimal":
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
    elif kind == "stock":
        t = (STOCK / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
        t = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", t)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
    else:
        raise SystemExit(kind)


def launch() -> None:
    (LIVE / "d3d11_log.txt").unlink(missing_ok=True)
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))


def wait_ready(timeout: int = 120) -> tuple[bool, int, str]:
    t0 = time.time()
    max_mb = 0
    saw = False
    title = ""
    while time.time() - t0 < timeout:
        if fatal():
            return False, max_mb, title
        mb, title = proc_info()
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
            if mb >= 3500 and "Arkham" in title and (time.time() - t0) >= 55:
                return True, max_mb, title
        elif saw:
            return False, max_mb, title
        time.sleep(2)
    mb, title = proc_info()
    ok = mb is not None and not fatal() and "Arkham" in title
    return ok, max(max_mb, mb or 0), title


def watch(seconds: int) -> tuple[bool, int]:
    t0 = time.time()
    max_mb = 0
    while time.time() - t0 < seconds:
        if fatal():
            return False, max_mb
        mb, title = proc_info()
        if mb is None:
            return False, max_mb
        if "Arkham" not in title and title == "Message":
            return False, max_mb
        max_mb = max(max_mb, mb)
        time.sleep(2)
    return proc_info()[0] is not None and not fatal(), max_mb


def send_ctrl_f() -> None:
    ps(
        r"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
if($p -and $p.MainWindowTitle -match 'Arkham'){
  [N.K]::ShowWindow($p.MainWindowHandle,9)|Out-Null
  [N.K]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
  Start-Sleep 1
  [N.K]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
  [N.K]::keybd_event(0x46,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 60
  [N.K]::keybd_event(0x46,0,2,[UIntPtr]::Zero)
  [N.K]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
}
"""
    )


def capture_batman(path: Path) -> dict:
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
if(-not $p){{ 'NO_PROC'; return }}
if($p.MainWindowTitle -notmatch 'Arkham'){{ "BAD_TITLE:$($p.MainWindowTitle)"; return }}
[void][N.C]::ShowWindow($p.MainWindowHandle,9)
[void][N.C]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 1
$r=New-Object N.C+RECT
[void][N.C]::GetClientRect($p.MainWindowHandle,[ref]$r)
$w=$r.R-$r.L; $h=$r.B-$r.T
if($w -lt 640 -or $h -lt 360){{ "BAD_SIZE:${{w}}x${{h}}"; return }}
$bmp=New-Object System.Drawing.Bitmap $w,$h
$g=[System.Drawing.Graphics]::FromImage($bmp)
$hdc=$g.GetHdc()
$ok=[N.C]::PrintWindow($p.MainWindowHandle,$hdc,2)
$g.ReleaseHdc($hdc)
$g.Dispose()
if(-not $ok){{ $bmp.Dispose(); 'PRINT_FAIL'; return }}
$bmp.Save('{str(path).replace("'", "''")}',[System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
"OK|$w|$h|$($p.MainWindowTitle)"
"""
    )
    line = [x for x in out.splitlines() if x.startswith("OK|") or x.startswith("BAD_") or x in ("NO_PROC", "PRINT_FAIL")]
    info = line[-1] if line else out.strip()[:120]
    ok = info.startswith("OK|") and path.exists()
    return {"ok": ok, "info": info, "path": str(path) if ok else None}


def analyze(path: Path, out_dir: Path) -> dict:
    import numpy as np
    from PIL import Image
    from verify_sbs_visual import analyze as vis

    verdict = vis(path, out_dir)
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im, dtype=np.float32)
    h, w, _ = arr.shape
    mid = w // 2
    left, right = arr[:, :mid], arr[:, mid : mid + mid]
    mean_diff = float(np.mean(np.abs(left - right)))
    # dual green FPS heuristic: look for bright green pixels in both halves upper area
    top = arr[: max(40, h // 8), :, :]
    # green-dominant pixels
    gmask = (top[:, :, 1] > 180) & (top[:, :, 1] > top[:, :, 0] + 40) & (top[:, :, 1] > top[:, :, 2] + 40)
    left_g = int(gmask[:, :mid].sum())
    right_g = int(gmask[:, mid : mid + mid].sum())
    return {
        "verdict": verdict,
        "mean_diff": round(mean_diff, 2),
        "size": f"{w}x{h}",
        "green_L": left_g,
        "green_R": right_g,
        "dual_fps_hint": left_g > 20 and right_g > 20,
    }


VARIANTS = [
    {"name": "m0_nodxgi_minimal", "dxgi": False, "mode": 0, "packer": "minimal", "watch": 100},
    {"name": "m0_nodxgi_stock", "dxgi": False, "mode": 0, "packer": "stock", "watch": 100},
    {"name": "m0_dxgi_minimal", "dxgi": True, "mode": 0, "packer": "minimal", "watch": 100},
    {"name": "m1_nodxgi_minimal", "dxgi": False, "mode": 1, "packer": "minimal", "watch": 80},
]


def run_one(v: dict) -> dict:
    print(f"\n=== {v['name']} ===", flush=True)
    install_base(v["dxgi"])
    apply_ini(v["mode"], 1)
    write_packer(v["packer"])
    launch()
    ok, max_mb, title = wait_ready(120)
    if not ok:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "boot",
            "max_mb": max_mb,
            "title": title,
            "crash": last_crash(),
            "fatal": fatal(),
        }
    alive, max2 = watch(v["watch"])
    max_mb = max(max_mb, max2)
    if not alive:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "watch",
            "max_mb": max_mb,
            "crash": last_crash(),
            "fatal": fatal(),
        }
    send_ctrl_f()
    time.sleep(1)
    shot = SHOT_DIR / f"{v['name']}.png"
    cap = capture_batman(shot)
    if not cap["ok"]:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "capture",
            "max_mb": max_mb,
            "cap": cap,
            "alive": True,
        }
    analysis = analyze(shot, SHOT_DIR / v["name"])
    # Accept TRUE_SBS or strong dual-FPS hint with decent mean_diff
    passed = analysis["verdict"] == "TRUE_SBS_CANDIDATE" or (
        analysis.get("dual_fps_hint") and analysis.get("mean_diff", 0) >= 8
    )
    return {
        "name": v["name"],
        "pass": passed,
        "stage": "complete",
        "max_mb": max_mb,
        "alive": True,
        "cap": cap,
        "analysis": analysis,
        "dxgi": v["dxgi"],
        "mode": v["mode"],
        "packer": v["packer"],
    }


def main() -> None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    start_killer()
    results = []
    winner = None
    for v in VARIANTS:
        r = run_one(v)
        results.append(r)
        print(r, flush=True)
        if r.get("pass"):
            winner = r
            break
        kill_game()
        time.sleep(3)

    lines = [f"PROBE_MODE0 {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    for r in results:
        lines.append(str(r))
    lines.append(f"WINNER={winner['name'] if winner else None}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)

    if winner:
        print("LEFT_RUNNING_MODE0_SBS", winner["name"], flush=True)
        # sync live packer recipe into working_config note
        (WC / "MODE0_WINNER.txt").write_text(
            f"{winner}\n"
            "Recipe: upscale_mode=0, upscaling=1, Present CustomShaderUpscale, "
            f"dxgi={winner.get('dxgi')}, packer={winner.get('packer')}\n"
            "Calib: Ctrl+F1 overlay, Ctrl+F3/F4 sep, Ctrl+F5/F6 conv, F8 stereo toggle\n",
            encoding="utf-8",
        )
    else:
        kill_game()
        install_base(True)
        apply_ini(1, 1)
        write_packer("off")
        launch()
        wait_ready(90)
        print("LEFT_DISARMED", flush=True)


if __name__ == "__main__":
    main()
