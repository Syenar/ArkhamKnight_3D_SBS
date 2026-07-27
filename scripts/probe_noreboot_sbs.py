"""No-reboot SBS probes. PASS only on dual-FPS or true dual-scene halves. PrintWindow only."""
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
V20 = PROJ / "experimental_fork_20260724_nullguards" / "patched_dlls" / "d3d11.dll.patched_v20"
PATCH = PROJ / "experimental_fork_20260724_nullguards" / "tools" / "patch_d3d11_v20_addref_inject.py"
OUT = WC / "PROBE_NOREBOOT.txt"
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
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-5);Id=1000} "
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[1..3] -join ' | ')}else{''}"
    ).strip()[:220]


def wipe() -> None:
    for n in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
        p = LIVE / n
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def base_install(d3d: Path, dxgi: bool) -> None:
    kill()
    wipe()
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
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
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


def set_device(upscaling: int, mode: int) -> None:
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", f"upscaling = {upscaling}", ini)
    if re.search(r"(?m)^upscale_mode\s*=", ini):
        ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", f"upscale_mode = {mode}", ini)
    else:
        ini = re.sub(r"(?m)^(upscaling\s*=\s*\d+\s*)$", rf"\1\nupscale_mode = {mode}", ini)
    # strip 3dvision/UE3
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
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")
    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")


def disarm_upscale_present() -> None:
    t = (LIVE / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    t = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", t)
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")


def write_minimal_upscale_shader_only() -> None:
    """Shader def in upscale.ini, NO [Present] section."""
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(
        """[Resource3DVisionUpscaleBackupTexture]
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


def inject_present_commands(commands: str) -> None:
    """Put Present commands in MAIN d3dx.ini [Present]."""
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    # remove any prior injected runs we added
    ini = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*\r?\n", "", ini)
    ini = re.sub(r"(?m)^r_bb\s*=\s*copy f_bb\s*\r?\n", "", ini)
    ini = re.sub(r"(?m)^special\s*=\s*upscaling_switch_bb\s*\r?\n", "", ini)
    m = re.search(r"(?m)^\[Present\]\s*\r?\n", ini)
    if not m:
        raise SystemExit("no [Present]")
    ini = ini[: m.end()] + commands + ini[m.end() :]
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")


def setup_forced_3dvision() -> None:
    disarm_upscale_present()
    sbs = (LIVE / "ShaderFixes" / "3dvision2sbs.ini").read_text(encoding="utf-8")
    sbs = re.sub(r"(?m)^global persist \$mode\s*=\s*.*$", "global persist $mode = 2", sbs)
    sbs = sbs.replace("if stereo_active && $mode", "if $mode")
    sbs = re.sub(
        r"(?m)^run = BuiltInCommandListUnbindAllRenderTargets\s*\n",
        ";run = BuiltInCommandListUnbindAllRenderTargets\n",
        sbs,
    )
    (LIVE / "ShaderFixes" / "3dvision2sbs.ini").write_text(sbs, encoding="utf-8")
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = ini.replace(
        ";include = ShaderFixes\\3dvision2sbs.ini",
        "include = ShaderFixes\\3dvision2sbs.ini",
    )
    if "include = ShaderFixes\\3dvision2sbs.ini" not in ini:
        ini = re.sub(
            r"(?m)^(\[Include\]\s*\r?\n)",
            r"\1include = ShaderFixes\\3dvision2sbs.ini\n",
            ini,
        )
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")


def launch() -> None:
    (LIVE / "d3d11_log.txt").unlink(missing_ok=True)
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))


def wait_ready(timeout=110) -> tuple[bool, int]:
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
foreach($vk in 0x70,0x46){
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
if($w -lt 640){{ 'BAD'; return }}
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

    gL, gR = green(left[:90]), green(right[:90])
    dual = gL >= 20 and gR >= 20

    L = np.asarray(Image.fromarray(left.astype(np.uint8)).resize((320, 180)), np.float32)
    R = np.asarray(Image.fromarray(right.astype(np.uint8)).resize((320, 180)), np.float32)

    def ncc(a, b):
        ag = a.mean(2)
        bg = b.mean(2)
        ag = (ag - ag.mean()) / (ag.std() + 1e-6)
        bg = (bg - bg.mean()) / (bg.std() + 1e-6)
        return float(np.mean(ag * bg))

    same = ncc(L, R)
    diff = float(np.mean(np.abs(L - R)))
    # both halves need content in rightish area (batman bust) for title SBS
    def right_energy(a):
        g = a.mean(2)
        return float(np.abs(np.diff(g[:, 200:], axis=1)).mean())

    eL, eR = right_energy(L), right_energy(R)
    similar = same >= 0.75 and 5 <= diff <= 70 and eL > 0.8 and eR > 0.8 and L.mean() > 8 and R.mean() > 8
    return {
        "pass": dual or similar,
        "dual_fps": dual,
        "gL": gL,
        "gR": gR,
        "ncc": round(same, 3),
        "diff": round(diff, 2),
        "eL": round(eL, 2),
        "eR": round(eR, 2),
        "meanL": round(float(L.mean()), 1),
        "meanR": round(float(R.mean()), 1),
        "size": f"{w}x{h}",
    }


def run_variant(v: dict) -> dict:
    print(f"\n=== {v['name']} ===", flush=True)
    base_install(v["d3d"], v["dxgi"])
    set_device(v["upscaling"], v["mode"])
    if v["kind"] == "copy_fbb":
        disarm_upscale_present()
        inject_present_commands("r_bb = copy f_bb\nspecial = upscaling_switch_bb\n")
    elif v["kind"] == "custom_in_d3dx":
        write_minimal_upscale_shader_only()
        inject_present_commands("run = CustomShaderUpscale\n")
    elif v["kind"] == "minimal_include":
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
    elif v["kind"] == "forced_3dvision":
        set_device(0, v["mode"])
        setup_forced_3dvision()
    else:
        raise SystemExit(v["kind"])

    launch()
    ok, max_mb = wait_ready(110)
    if not ok:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "boot",
            "max_mb": max_mb,
            "crash": crash(),
            "fatal": fatal(),
        }
    alive, max2 = watch(v.get("watch", 70))
    max_mb = max(max_mb, max2)
    if not alive:
        return {
            "name": v["name"],
            "pass": False,
            "stage": "watch",
            "max_mb": max_mb,
            "crash": crash(),
        }
    overlay()
    time.sleep(1)
    path = SHOT / f"nr_{v['name']}.png"
    if not capture(path):
        return {"name": v["name"], "pass": False, "stage": "capture", "max_mb": max_mb, "alive": True}
    a = analyze(path)
    # visual gate: I will also read image if pass claimed
    return {
        "name": v["name"],
        "pass": a["pass"],
        "stage": "complete",
        "max_mb": max_mb,
        "alive": True,
        "analysis": a,
        "shot": str(path),
        "d3d": sha(LIVE / "d3d11.dll")[:16],
        "dxgi": (LIVE / "dxgi.dll").exists(),
    }


def main() -> None:
    subprocess.run(["python", str(PATCH), str(STOCK / "d3d11.dll"), str(V20)], check=True)
    start_killer()
    SHOT.mkdir(parents=True, exist_ok=True)

    variants = [
        # No CustomShader — resource copy packer
        {
            "name": "copy_fbb_m0_dxgi",
            "d3d": STOCK / "d3d11.dll",
            "dxgi": True,
            "upscaling": 1,
            "mode": 0,
            "kind": "copy_fbb",
        },
        {
            "name": "copy_fbb_m1_dxgi",
            "d3d": STOCK / "d3d11.dll",
            "dxgi": True,
            "upscaling": 1,
            "mode": 1,
            "kind": "copy_fbb",
        },
        {
            "name": "copy_fbb_m0_nodxgi",
            "d3d": STOCK / "d3d11.dll",
            "dxgi": False,
            "upscaling": 1,
            "mode": 0,
            "kind": "copy_fbb",
        },
        # CustomShader in main d3dx Present + mode0 no dxgi (historically alive)
        {
            "name": "d3dx_present_m0_nodxgi",
            "d3d": STOCK / "d3d11.dll",
            "dxgi": False,
            "upscaling": 1,
            "mode": 0,
            "kind": "custom_in_d3dx",
        },
        # v20 patch + custom in d3dx + mode1 dxgi
        {
            "name": "v20_d3dx_present_m1",
            "d3d": V20,
            "dxgi": True,
            "upscaling": 1,
            "mode": 1,
            "kind": "custom_in_d3dx",
            "watch": 90,
        },
        # forced 3dvision2sbs
        {
            "name": "force_3dvision_dxgi",
            "d3d": STOCK / "d3d11.dll",
            "dxgi": True,
            "upscaling": 0,
            "mode": 1,
            "kind": "forced_3dvision",
        },
        {
            "name": "force_3dvision_nodxgi",
            "d3d": STOCK / "d3d11.dll",
            "dxgi": False,
            "upscaling": 0,
            "mode": 0,
            "kind": "forced_3dvision",
        },
    ]

    results = []
    winner = None
    for v in variants:
        if v["d3d"] == V20 and not V20.exists():
            results.append({"name": v["name"], "pass": False, "stage": "missing_v20"})
            continue
        r = run_variant(v)
        results.append(r)
        print(r, flush=True)
        if r.get("pass"):
            winner = r
            break
        kill()
        time.sleep(3)

    lines = [f"PROBE_NOREBOOT {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    for r in results:
        lines.append(str(r))
    lines.append(f"WINNER={winner['name'] if winner else None}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)
    if winner:
        print("LEFT_RUNNING", winner["name"], flush=True)
    else:
        # leave disarmed
        kill()
        base_install(STOCK / "d3d11.dll", True)
        set_device(1, 1)
        disarm_upscale_present()
        launch()
        wait_ready(90)
        print("LEFT_DISARMED", flush=True)


if __name__ == "__main__":
    main()
