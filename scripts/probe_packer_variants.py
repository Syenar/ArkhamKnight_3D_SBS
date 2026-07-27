"""Cold-boot packer variants. Only report SBS if screenshot analyzer says so.

Does not ask the user to check. Leaves game running only on TRUE_SBS_CANDIDATE.
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
FIX = PROJ / "downloads" / "extracted_geo11_fix" / "FixFiles"
OUT = WC / "PROBE_PACKER_VARIANTS.txt"
SHOT_DIR = WC / "probe_shots"
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
EXPECT_D3D = "C89AEE44CCFA0240E1BFEA37F5F7357514AA6FBCB2E92AD34A974AC192BC0E4E"
FIX_D3D = "50BB7DF2414920F6"
KILLER = PROJ / "downloads" / "kill_fatal_message.ps1"
VISUAL = PROJ / "downloads" / "verify_sbs_visual.py"

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
        "Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|Message' } "
        "-EA SilentlyContinue | Stop-Process -Force"
    )
    time.sleep(2)


def start_killer() -> None:
    ps(
        f"Get-Process powershell -EA SilentlyContinue | Where-Object {{ $_.CommandLine -match 'kill_fatal' }} "
        f"| Stop-Process -Force -EA SilentlyContinue"
    )
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


def proc_mb() -> int | None:
    out = ps("(Get-Process BatmanAK -EA SilentlyContinue | Select -First 1).WS").strip()
    if not out:
        return None
    try:
        return int(int(out) / (1024 * 1024))
    except ValueError:
        return None


def fatal_count() -> int:
    out = ps(
        "@(Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|^Message$' }).Count"
    ).strip()
    try:
        return int(out)
    except ValueError:
        return 0


def last_crash() -> str:
    return ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-8); Id=1000} "
        "-EA SilentlyContinue | Select -First 1; if($e){(($e.Message -split \"`n\")[0..4] -join ' | ')} else {''}"
    ).strip()[:240]


def wipe_caches() -> None:
    for name in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM", "DMAutoPatchCache", "DMAutoPatchFailures"):
        p = LIVE / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def restore_files(d3d_src: Path, with_dxgi: bool, with_nvapi: bool) -> None:
    kill_game()
    wipe_caches()
    for name in ("d3dx.ini", "d3dxdm.ini"):
        shutil.copy2(SNAP / name, LIVE / name)
    shutil.copy2(d3d_src, LIVE / "d3d11.dll")
    if with_nvapi:
        shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    else:
        (LIVE / "nvapi64.dll").unlink(missing_ok=True)
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
    # ensure Bm res
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
    # Ensure may overwrite d3d/dxgi — re-apply variant choices
    shutil.copy2(d3d_src, LIVE / "d3d11.dll")
    if with_dxgi:
        shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    else:
        (LIVE / "dxgi.dll").unlink(missing_ok=True)
    if with_nvapi:
        shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    else:
        (LIVE / "nvapi64.dll").unlink(missing_ok=True)
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")


def set_device(upscaling: int, upscale_mode: int | None = 1) -> None:
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", f"upscaling = {upscaling}", ini)
    if upscale_mode is not None:
        if re.search(r"(?m)^upscale_mode\s*=", ini):
            ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", f"upscale_mode = {upscale_mode}", ini)
        else:
            ini = re.sub(
                r"(?m)^(upscaling\s*=\s*\d+\s*)$",
                rf"\1\nupscale_mode = {upscale_mode}",
                ini,
            )
    # strip 3dvision / UE3
    lines = []
    for line in ini.splitlines(keepends=True):
        s = line.strip()
        if s.startswith("include = ShaderFixes\\3dvision2sbs.ini"):
            lines.append(";include = ShaderFixes\\3dvision2sbs.ini\n")
        elif s.startswith("include = ShaderFixes\\UE3_"):
            continue
        else:
            lines.append(line)
    ini = "".join(lines)
    if "include = ShaderFixes\\upscale.ini" not in ini:
        ini = re.sub(
            r"(?m)^(\[Include\]\s*\r?\n)",
            r"\1include = ShaderFixes\\upscale.ini\n",
            ini,
        )
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")


def write_upscale(kind: str) -> None:
    stock = (STOCK / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    if kind == "stock_on":
        t = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", stock)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
    elif kind == "stock_off":
        t = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", stock)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
    elif kind == "minimal_no_unbind":
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
    elif kind == "switch_only":
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(
            """[Present]
special = upscaling_switch_bb
""",
            encoding="utf-8",
        )
    elif kind == "unbind_once_then_blit":
        # Unbind only first armed frame via $flag, then blit without UnbindAll
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(
            """[Constants]
global $ups_armed = 1
global $did_unbind = 0

[Present]
if $ups_armed == 1 && $did_unbind == 0
\trun = BuiltInCommandListUnbindAllRenderTargets
\t$did_unbind = 1
endif
if $ups_armed == 1
\trun = CustomShaderUpscale
endif

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
    elif kind == "stereo2mono_bb":
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(
            """[Present]
run = CustomShaderForcedSBS

[ResourceForcedSBSBackup]
[CustomShaderForcedSBS]
vs = upscale.hlsl
ps = upscale.hlsl
hs = null
ds = null
gs = null
blend = disable
cull = none
sampler = anisotropic_filter
topology = triangle_strip
o0 = set_viewport bb
ResourceForcedSBSBackup = reference ps-t101
ps-t101 = stereo2mono bb
draw = 4, 0
post ps-t101 = reference ResourceForcedSBSBackup
""",
            encoding="utf-8",
        )
    else:
        raise SystemExit(f"unknown upscale kind {kind}")


def bump_calib() -> None:
    """Ensure usable sep/conv steps and overlay keys (real 3D calibration)."""
    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    # bump tiny 0.01 steps to 0.15
    dm = re.sub(
        r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$",
        r"\g<1>0.15",
        dm,
    )
    dm = re.sub(
        r"(?m)^(convergence = convergence [+\-] )0\.01\s*$",
        r"\g<1>0.15",
        dm,
    )
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")


def launch() -> None:
    log = LIVE / "d3d11_log.txt"
    if log.exists():
        log.unlink()
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))


def wait_boot(timeout: int = 110) -> tuple[bool, int]:
    t0 = time.time()
    max_mb = 0
    saw = False
    while time.time() - t0 < timeout:
        if fatal_count():
            return False, max_mb
        mb = proc_mb()
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
            if mb >= 3500 and (time.time() - t0) >= 55:
                return True, max_mb
        elif saw:
            return False, max_mb
        time.sleep(2)
    return proc_mb() is not None and fatal_count() == 0, max_mb


def watch(seconds: int) -> tuple[bool, int, int | None]:
    t0 = time.time()
    max_mb = 0
    saw = False
    while time.time() - t0 < seconds:
        if fatal_count():
            return False, max_mb, int(time.time() - t0)
        mb = proc_mb()
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
        elif saw:
            return False, max_mb, int(time.time() - t0)
        time.sleep(2)
    return proc_mb() is not None and fatal_count() == 0, max_mb, None


def capture(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = ps(
        f"""
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class CapV {{
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int L,T,R,B; }}
}}
'@
[void][CapV]::SetProcessDPIAware()
$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1
if(-not $p -or $p.MainWindowHandle -eq 0){{ 'NO_HWND'; return }}
[void][CapV]::ShowWindow($p.MainWindowHandle,9)
[void][CapV]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 1
$r=New-Object CapV+RECT
[void][CapV]::GetWindowRect($p.MainWindowHandle,[ref]$r)
$w=$r.R-$r.L; $h=$r.B-$r.T
if($w -lt 200 -or $h -lt 200){{ 'BAD_SIZE'; return }}
$bmp=New-Object System.Drawing.Bitmap $w,$h
$g=[System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L,$r.T,0,0,(New-Object System.Drawing.Size $w,$h))
$bmp.Save('{str(path).replace("'", "''")}', [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
'OK'
"""
    )
    return "OK" in out and path.exists() and path.stat().st_size > 5000


def analyze(path: Path, out_dir: Path) -> dict:
    try:
        import numpy as np
        from verify_sbs_visual import analyze as vis_analyze
    except Exception as e:
        return {"verdict": "NO_ANALYZER", "error": str(e)}
    # verify_sbs_visual.analyze prints and returns verdict string
    try:
        verdict = vis_analyze(path, out_dir)
        # also compute avg_diff for log
        from PIL import Image

        im = Image.open(path).convert("RGB")
        arr = np.asarray(im, dtype=np.float32)
        h, w, _ = arr.shape
        mid = w // 2
        left, right = arr[:, :mid], arr[:, mid : mid + mid]
        mean_diff = float(np.mean(np.abs(left - right)))
        return {"verdict": verdict, "mean_diff": round(mean_diff, 2), "size": f"{w}x{h}"}
    except Exception as e:
        return {"verdict": "ANALYZE_FAIL", "error": str(e)}


def op50() -> int:
    log = LIVE / "d3d11_log.txt"
    if not log.exists():
        return -1
    return log.read_text(encoding="utf-8", errors="replace").count("Operand type 50")


def log_hits() -> dict:
    log = LIVE / "d3d11_log.txt"
    if not log.exists():
        return {}
    t = log.read_text(encoding="utf-8", errors="replace")
    keys = [
        "CustomShaderUpscale",
        "HackerDeviceDirectMode",
        "upscaling_switch",
        "CreateSwapChain",
        "StereoProfile",
        "direct_mode",
    ]
    return {k: t.count(k) for k in keys}


VARIANTS = [
    {
        "name": "v060_cold_stock",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": True,
        "nvapi": True,
        "upscaling": 1,
        "upscale_mode": 1,
        "upscale": "stock_on",
        "watch": 90,
    },
    {
        "name": "minimal_no_unbind",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": True,
        "nvapi": True,
        "upscaling": 1,
        "upscale_mode": 1,
        "upscale": "minimal_no_unbind",
        "watch": 90,
    },
    {
        "name": "unbind_once",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": True,
        "nvapi": True,
        "upscaling": 1,
        "upscale_mode": 1,
        "upscale": "unbind_once_then_blit",
        "watch": 90,
    },
    {
        "name": "mode0_no_dxgi",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": False,
        "nvapi": True,
        "upscaling": 1,
        "upscale_mode": 0,
        "upscale": "minimal_no_unbind",
        "watch": 90,
    },
    {
        "name": "fixd3d_minimal",
        "d3d": FIX / "d3d11.dll",
        "dxgi": True,
        "nvapi": True,
        "upscaling": 1,
        "upscale_mode": 1,
        "upscale": "minimal_no_unbind",
        "watch": 90,
    },
    {
        "name": "stereo2mono",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": True,
        "nvapi": True,
        "upscaling": 0,
        "upscale_mode": 1,
        "upscale": "stereo2mono_bb",
        "watch": 75,
    },
    {
        "name": "switch_only",
        "d3d": STOCK / "d3d11.dll",
        "dxgi": True,
        "nvapi": True,
        "upscaling": 1,
        "upscale_mode": 1,
        "upscale": "switch_only",
        "watch": 60,
    },
]


def run_one(v: dict) -> dict:
    print(f"\n=== {v['name']} ===", flush=True)
    restore_files(v["d3d"], v["dxgi"], v["nvapi"])
    set_device(v["upscaling"], v["upscale_mode"])
    write_upscale(v["upscale"])
    bump_calib()
    d3d_hash = sha(LIVE / "d3d11.dll")
    dxgi_ok = (LIVE / "dxgi.dll").exists() and sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    launch()
    ok_boot, max_boot = wait_boot(110)
    if not ok_boot:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "boot",
            "max_mb": max_boot,
            "crash": last_crash(),
            "fatal": fatal_count(),
            "d3d": d3d_hash[:16],
            "dxgi": dxgi_ok,
            "op50": op50(),
            "hits": log_hits(),
        }
    alive, max_mb, died = watch(v["watch"])
    max_mb = max(max_mb, max_boot)
    if not alive:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "watch",
            "max_mb": max_mb,
            "died_at": died,
            "crash": last_crash(),
            "fatal": fatal_count(),
            "d3d": d3d_hash[:16],
            "dxgi": dxgi_ok,
            "op50": op50(),
            "hits": log_hits(),
        }
    shot = SHOT_DIR / f"{v['name']}.png"
    captured = capture(shot)
    analysis = (
        analyze(shot, SHOT_DIR / v["name"])
        if captured
        else {"verdict": "CAPTURE_FAIL"}
    )
    verdict = analysis.get("verdict", "?")
    passed = verdict == "TRUE_SBS_CANDIDATE"
    return {
        "name": v["name"],
        "pass": passed,
        "stage": "complete",
        "max_mb": max_mb,
        "alive": True,
        "capture": captured,
        "analysis": analysis,
        "d3d": d3d_hash[:16],
        "dxgi": dxgi_ok,
        "op50": op50(),
        "hits": log_hits(),
        "shot": str(shot) if captured else None,
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
            break  # stop on first verified SBS
        kill_game()
        time.sleep(3)

    lines = [f"PROBE_PACKER {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    for r in results:
        lines.append(str(r))
    lines.append(f"WINNER={winner['name'] if winner else None}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)

    if winner:
        print("LEFT_RUNNING_VERIFIED_SBS", winner["name"], flush=True)
        # keep current process (already running with winner config)
    else:
        # leave disarmed stable for safety
        kill_game()
        restore_files(STOCK / "d3d11.dll", True, True)
        set_device(1, 1)
        write_upscale("stock_off")
        bump_calib()
        launch()
        wait_boot(90)
        print("LEFT_RUNNING_DISARMED_NO_SBS", flush=True)


if __name__ == "__main__":
    main()
