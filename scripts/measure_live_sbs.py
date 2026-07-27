"""Toggle stereo on live BatmanAK and measure L/R divergence."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image

SHOT = Path(
    r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D\working_config\probe_shots"
)


def ps(cmd: str) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    return (r.stdout or "") + (r.stderr or "")


def key_ctrl(vk: int) -> None:
    ps(
        rf"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
[N.K]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
Start-Sleep 1
[N.K]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
[N.K]::keybd_event({vk},0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 80
[N.K]::keybd_event({vk},0,2,[UIntPtr]::Zero)
[N.K]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
"""
    )


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
[StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int L,T,R,B; }}
'@
Add-Type -MemberDefinition $sig -Name C -Namespace N -EA SilentlyContinue
[void][N.C]::SetProcessDPIAware()
$p=Get-Process BatmanAK|Select -First 1
[N.C]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
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
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w = im.shape[:2]
    mid = w // 2
    left, right = im[:, :mid], im[:, mid : mid + mid]
    L = np.asarray(Image.fromarray(left.astype(np.uint8)).resize((320, 180)), np.float32)
    R = np.asarray(Image.fromarray(right.astype(np.uint8)).resize((320, 180)), np.float32)
    ag, bg = L.mean(2), R.mean(2)
    ag = (ag - ag.mean()) / (ag.std() + 1e-6)
    bg = (bg - bg.mean()) / (bg.std() + 1e-6)
    ncc = float(np.mean(ag * bg))
    diff = float(np.mean(np.abs(L - R)))

    def green(a):
        return int(
            ((a[:, :, 1] > 150) & (a[:, :, 1] > a[:, :, 0] + 25) & (a[:, :, 1] > a[:, :, 2] + 25)).sum()
        )

    gL = green(im[:80, :80])
    gReye = green(im[:80, mid : mid + 80])
    gBotMid = green(im[int(h * 0.88) :, int(w * 0.35) : int(w * 0.65)])
    return {
        "ncc": round(ncc, 3),
        "diff": round(diff, 2),
        "gL_TL": gL,
        "gR_eye_TL": gReye,
        "dual_fps": gL >= 15 and gReye >= 15,
        "gBotMid": gBotMid,
        "stereo_disabled_hint": gBotMid > 40,
        "meanL": round(float(left.mean()), 1),
        "meanR": round(float(right.mean()), 1),
        "size": f"{w}x{h}",
        "real_sbs": ncc < 0.98 and diff > 2.0 and gL >= 15 and gReye >= 15,
    }


def main() -> None:
    if not ps("(Get-Process BatmanAK -EA SilentlyContinue).Id").strip():
        print("DEAD")
        return
    a0 = analyze(capture("live_before.png"))
    print("BEFORE", a0, flush=True)
    key_ctrl(0x54)  # Ctrl+T
    time.sleep(2)
    key_ctrl(0x70)  # Ctrl+F1 overlay
    time.sleep(1)
    a1 = analyze(capture("live_after_t.png"))
    print("AFTER_T", a1, flush=True)
    # bump separation to force visible eye difference if stereo on
    for _ in range(8):
        key_ctrl(0x73)  # Ctrl+F4 increase sep
        time.sleep(0.15)
    time.sleep(1)
    a2 = analyze(capture("live_after_sep.png"))
    print("AFTER_SEP", a2, flush=True)
    print("PASS" if a2.get("real_sbs") else "NO_REAL_SBS", flush=True)


if __name__ == "__main__":
    main()
