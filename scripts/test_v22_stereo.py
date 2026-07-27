"""v22 (no NullRdx) + packer; verify stereo enabled and SBS via PrintWindow."""
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
TOOL = PROJ / "experimental_fork_20260724_nullguards" / "tools" / "patch_d3d11_v22_no_nullrdx.py"
V22 = PROJ / "experimental_fork_20260724_nullguards" / "patched_dlls" / "d3d11.dll.patched_v22"
OUT = WC / "TEST_V22.txt"
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
    ps("Get-Process BatmanAK -EA SilentlyContinue | Stop-Process -Force")
    ps(
        "Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|^Message$' } "
        "| Stop-Process -Force -EA SilentlyContinue"
    )
    time.sleep(2)


def main() -> None:
    subprocess.run(["python", str(TOOL), str(STOCK / "d3d11.dll"), str(V22)], check=True)
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
    shutil.copy2(V22, LIVE / "d3d11.dll")
    shutil.copy2(WC / "dxgi.dll", LIVE / "dxgi.dll")
    shutil.copy2(STOCK / "nvapi64.dll", LIVE / "nvapi64.dll")
    shutil.copy2(SNAP / "d3dx.ini", LIVE / "d3dx.ini")
    shutil.copy2(SNAP / "d3dxdm.ini", LIVE / "d3dxdm.ini")
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(STOCK / "ShaderFixes", LIVE / "ShaderFixes")
    assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    assert sha(LIVE / "d3d11.dll") == sha(V22)

    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
    ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
    ini = re.sub(r"(?m)^force_stereo\s*=\s*.*$", "force_stereo = 2", ini)
    # Present run in MAIN d3dx
    ini = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*\r?\n", "", ini)
    m = re.search(r"(?m)^\[Present\]\s*\r?\n", ini)
    ini = ini[: m.end()] + "run = CustomShaderUpscale\n" + ini[m.end() :]
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")

    # upscale.ini: shader only
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

    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8")
    dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
    dm = re.sub(r"(?m)^dm_auto_convergence\s*=\s*.*$", "dm_auto_convergence = 0", dm)
    dm = re.sub(r"(?m)^dm_separation\s*=\s*.*$", "dm_separation = 50", dm)
    dm = re.sub(r"(?m)^dm_convergence\s*=\s*.*$", "dm_convergence = 2.0", dm)
    dm = re.sub(r"(?m)^(\$adj_conv = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    dm = re.sub(r"(?m)^(convergence = convergence [+\-] )0\.01\s*$", r"\g<1>0.15", dm)
    # ensure first assignment is 1 (not the bang line)
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")
    # verify bang intact
    assert "dm_stereo_enabled = !dm_stereo_enabled" in dm
    assert re.search(r"(?m)^dm_stereo_enabled\s*=\s*1\s*$", dm)

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
    ).strip()[:240]
    alive = saw and ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() != ""
    fatal = int(ps("@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count").strip() or "0") > 0
    if not alive or fatal:
        r = {"pass": False, "stage": "boot", "max_mb": max_mb, "crash": crash, "fatal": fatal}
        OUT.write_text(str(r) + "\n", encoding="utf-8")
        print(r, flush=True)
        print("V22_FAIL_BOOT", flush=True)
        return

    time.sleep(40)
    if ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() == "":
        r = {"pass": False, "stage": "watch", "crash": crash}
        OUT.write_text(str(r) + "\n", encoding="utf-8")
        print(r, flush=True)
        print("V22_FAIL_WATCH", flush=True)
        return

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
# Ctrl+F1 + Ctrl+F
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
        # green text detection
        def green_count(a):
            return int(
                ((a[:, :, 1] > 150) & (a[:, :, 1] > a[:, :, 0] + 25) & (a[:, :, 1] > a[:, :, 2] + 25)).sum()
            )

        gL, gR = green_count(left[:100]), green_count(right[:100])
        gBot = green_count(arr[int(h * 0.88) :, :, :])
        # Heuristic: "Stereo disabled" is bottom-center green text
        bot_mid = arr[int(h * 0.88) :, int(w * 0.35) : int(w * 0.65), :]
        gBotMid = green_count(bot_mid)
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
        dual = gL >= 20 and gR >= 20
        return {
            "dual_fps": dual,
            "gL": gL,
            "gR": gR,
            "gBot": gBot,
            "gBotMid": gBotMid,
            "stereo_disabled_hint": gBotMid > 40 and not dual,
            "ncc": round(same, 3),
            "diff": round(diff, 2),
            "meanL": round(float(L.mean()), 1),
            "meanR": round(float(R.mean()), 1),
            "size": f"{w}x{h}",
            "pass": dual,
        }

    p0 = capture("v22_pre.png")
    a0 = analyze(p0)
    print("PRE", a0, flush=True)

    # Ctrl+T toggle stereo
    ps(
        r"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
[N.K]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
Start-Sleep 1
[N.K]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
[N.K]::keybd_event(0x54,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
[N.K]::keybd_event(0x54,0,2,[UIntPtr]::Zero)
[N.K]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
"""
    )
    time.sleep(2)
    p1 = capture("v22_post_t.png")
    a1 = analyze(p1)
    print("POST_T", a1, flush=True)

    # toggle again if still looking disabled
    if a1.get("stereo_disabled_hint") or not a1.get("pass"):
        ps(
            r"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K2 -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
[N.K2]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
Start-Sleep 1
[N.K2]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
[N.K2]::keybd_event(0x54,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
[N.K2]::keybd_event(0x54,0,2,[UIntPtr]::Zero)
[N.K2]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
"""
        )
        time.sleep(2)
        p2 = capture("v22_post_t2.png")
        a2 = analyze(p2)
        print("POST_T2", a2, flush=True)
    else:
        a2 = a1
        p2 = p1

    alive = ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip() != ""
    log = LIVE / "d3d11_log.txt"
    hits = {}
    if log.exists():
        t = log.read_text(encoding="utf-8", errors="replace")
        for k in ("StereoProfile", "stereo", "DirectMode", "CustomShaderUpscale", "Operand type 50"):
            hits[k] = t.count(k)

    result = {
        "pass": bool(a2.get("pass")) and alive,
        "alive": alive,
        "max_mb": max_mb,
        "pre": a0,
        "final": a2,
        "shot": str(p2),
        "hits": hits,
        "d3d": sha(LIVE / "d3d11.dll")[:16],
    }
    OUT.write_text(str(result) + "\n", encoding="utf-8")
    print(result, flush=True)
    print("LEFT_RUNNING_V22_SBS" if result["pass"] else "V22_ALIVE_NO_SBS", flush=True)


if __name__ == "__main__":
    main()
