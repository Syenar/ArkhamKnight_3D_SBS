"""Bit-for-bit restore of SNAPSHOT_v060 (user-confirmed SBS) and verify."""
from __future__ import annotations

import hashlib
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
OUT = WC / "TEST_EXACT_SNAPSHOT.txt"
SHOT = WC / "probe_shots" / "exact_snap.png"
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
    time.sleep(3)


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
    kill()
    for n in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM", "ShaderFixes"):
        p = LIVE / n
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    for n in ("d3d11.dll", "dxgi.dll", "nvapi64.dll", "d3dx.ini", "d3dxdm.ini"):
        shutil.copy2(SNAP / n, LIVE / n)
    shutil.copytree(SNAP / "ShaderFixes", LIVE / "ShaderFixes")
    # game configs from working_config
    cfg = Path(r"D:\SteamLibrary\steamapps\common\Batman Arkham Knight\BmGame\Config")
    for n in ("BmSystemSettings.ini", "UserSystemSettings.ini"):
        src = WC / n
        if src.exists():
            dst = cfg / n
            ps(f"Set-ItemProperty '{dst}' -Name IsReadOnly -Value $false -EA SilentlyContinue")
            shutil.copy2(src, dst)
            ps(f"Set-ItemProperty '{dst}' -Name IsReadOnly -Value $true -EA SilentlyContinue")

    print("dxgi", sha(LIVE / "dxgi.dll")[:16])
    print("d3d", sha(LIVE / "d3d11.dll")[:16])
    up = (LIVE / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    print("packer_on", "\nrun = CustomShaderUpscale" in up or up.startswith("run =") or "\nrun = CustomShaderUpscale" in ("\n" + up))
    print("run_lines", [ln for ln in up.splitlines() if "CustomShaderUpscale" in ln][:3])

    (LIVE / "d3d11_log.txt").unlink(missing_ok=True)
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))

    t0 = time.time()
    max_mb = 0
    saw = False
    died = False
    while time.time() - t0 < 130:
        fatal = int(
            ps(
                "@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count"
            ).strip()
            or "0"
        )
        out = ps(
            "$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1; "
            "if($p){\"$([int]($p.WS/1MB))|$($p.MainWindowTitle)\"}else{'|'}"
        ).strip()
        mb_s, _, title = out.partition("|")
        try:
            mb = int(mb_s)
        except ValueError:
            mb = None
        if fatal:
            died = True
            break
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
            if mb >= 3500 and "Arkham" in title and time.time() - t0 >= 70:
                break
        elif saw:
            died = True
            break
        time.sleep(2)

    crash = ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=(Get-Date).AddMinutes(-5);Id=1000} "
        "-EA SilentlyContinue|Select -First 1; if($e){(($e.Message -split \"`n\")[0..5] -join ' | ')}else{''}"
    ).strip()[:300]

    alive = (
        not died
        and int(
            ps(
                "@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count"
            ).strip()
            or "0"
        )
        == 0
        and proc_mb() is not None
    )

    result = {"alive": alive, "max_mb": max_mb, "died": died, "crash": crash}
    if alive:
        # watch more
        time.sleep(45)
        alive = proc_mb() is not None and int(
            ps(
                "@(Get-Process|?{$_.MainWindowTitle -match 'Fatal|^Message$'}).Count"
            ).strip()
            or "0"
        ) == 0
        result["alive_after_45"] = alive
        if alive:
            # capture
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
$bmp.Dispose()
'OK'
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
                result["meanL"] = round(float(L.mean()), 1)
                result["meanR"] = round(float(R.mean()), 1)
                result["diff"] = round(float(np.mean(np.abs(L - R))), 2)

    OUT.write_text(str(result) + "\n", encoding="utf-8")
    print(result, flush=True)
    print("LEFT_ALIVE" if result.get("alive_after_45") else "DEAD_OR_UNSTABLE", flush=True)


def proc_mb():
    out = ps("(Get-Process BatmanAK -EA SilentlyContinue|Select -First 1).WS").strip()
    if not out:
        return None
    try:
        return int(int(out) / (1024 * 1024))
    except ValueError:
        return None


if __name__ == "__main__":
    main()
