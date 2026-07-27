"""Hot-patch Present on a living BatmanAK session; verify with strict SBS metric.

Rejects mono title screens that are merely cut in half (false TRUE_SBS).
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

PROJ = Path(r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D")
LIVE = Path(r"D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64")
OUT = PROJ / "working_config" / "HOT_FORCE_SBS.txt"
SHOT_DIR = PROJ / "working_config" / "probe_shots"


def ps(cmd: str) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    return (r.stdout or "") + (r.stderr or "")


def proc_ok() -> bool:
    out = ps(
        "$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1; "
        "if($p -and $p.MainWindowTitle -match 'Arkham'){'OK'} else {'NO'}"
    ).strip()
    return "OK" in out


def send_f10() -> None:
    ps(
        r"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int n);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
if($p){
  [N.K]::ShowWindow($p.MainWindowHandle,9)|Out-Null
  [N.K]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
  Start-Sleep 1
  [N.K]::keybd_event(0x79,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 80
  [N.K]::keybd_event(0x79,0,2,[UIntPtr]::Zero)
}
"""
    )


def send_keys_ctrl(vk: int) -> None:
    ps(
        rf"""
$sig=@'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name K2 -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
if($p){{
  [N.K2]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
  Start-Sleep -Milliseconds 400
  [N.K2]::keybd_event(0x11,0,0,[UIntPtr]::Zero)
  [N.K2]::keybd_event({vk},0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 50
  [N.K2]::keybd_event({vk},0,2,[UIntPtr]::Zero)
  [N.K2]::keybd_event(0x11,0,2,[UIntPtr]::Zero)
}}
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
[StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int L,T,R,B; }}
'@
Add-Type -MemberDefinition $sig -Name C -Namespace N -EA SilentlyContinue
[void][N.C]::SetProcessDPIAware()
$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1
if(-not $p -or $p.MainWindowTitle -notmatch 'Arkham'){{ 'BAD'; return }}
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
'OK'
"""
    )
    return "OK" in out and path.exists()


def strict_sbs(path: Path) -> dict:
    """True SBS: each half is a full scene (similar), not left/right crops of one image."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    # drop titlebar-ish
    im = im.crop((0, int(h * 0.06), w, h))
    w, h = im.size
    mid = w // 2
    left = im.crop((0, 0, mid, h)).resize((320, 180), Image.Resampling.BOX)
    right = im.crop((mid, 0, w, h)).resize((320, 180), Image.Resampling.BOX)
    la = np.asarray(left, dtype=np.float32)
    ra = np.asarray(right, dtype=np.float32)
    # brightness gate
    if la.mean() < 8 and ra.mean() < 8:
        return {"verdict": "BLACK", "pass": False}
    # normalized cross corr
    def ncc(a, b):
        ag = a.mean(axis=2)
        bg = b.mean(axis=2)
        ag = (ag - ag.mean()) / (ag.std() + 1e-6)
        bg = (bg - bg.mean()) / (bg.std() + 1e-6)
        return float(np.mean(ag * bg))

    same = ncc(la, ra)
    mean_diff = float(np.mean(np.abs(la - ra)))

    # Mono-split detector: compare left-eye image to the LEFT half of a
    # reconstructed "full mono" made by placing left|right as spatial halves.
    # For true SBS, left-eye center patch ≈ right-eye center patch.
    # For mono-split, left-eye is left scene, right-eye is right scene → low center match
    # already in `same`. Strengthen: check edge density present in both halves.
    def edge_energy(a):
        g = a.mean(axis=2)
        dx = np.abs(np.diff(g, axis=1)).mean()
        dy = np.abs(np.diff(g, axis=0)).mean()
        return float(dx + dy)

    eL, eR = edge_energy(la), edge_energy(ra)
    # Both halves need real content (not one black)
    if min(la.mean(), ra.mean()) < 5 and max(la.mean(), ra.mean()) > 15:
        return {
            "verdict": "HALF_BLACK",
            "pass": False,
            "ncc": round(same, 3),
            "mean_diff": round(mean_diff, 2),
        }

    # Spatial-split detector using horizontal profile:
    # On mono title, left half luminance profile differs strongly from right.
    # True SBS still has parallax but profiles correlate.
    # Also require ncc high enough AND mean_diff not tiny (not duplicate) and not huge chaos.
    # Critical: for the known mono title false positive, left had text (bright left) and
    # right had batman (bright mid). Use column-mass correlation:
    colL = la.mean(axis=(0, 2))
    colR = ra.mean(axis=(0, 2))
    colL = (colL - colL.mean()) / (colL.std() + 1e-6)
    colR = (colR - colR.mean()) / (colR.std() + 1e-6)
    col_ncc = float(np.mean(colL * colR))

    # Pass only if halves are structurally similar (full-scene each eye)
    passed = (
        same >= 0.70
        and col_ncc >= 0.55
        and 4.0 <= mean_diff <= 80.0
        and eL > 1.0
        and eR > 1.0
        and la.mean() > 10
        and ra.mean() > 10
    )
    verdict = "STRICT_SBS" if passed else "NOT_SBS"
    return {
        "verdict": verdict,
        "pass": passed,
        "ncc": round(same, 3),
        "col_ncc": round(col_ncc, 3),
        "mean_diff": round(mean_diff, 2),
        "eL": round(eL, 2),
        "eR": round(eR, 2),
        "meanL": round(float(la.mean()), 1),
        "meanR": round(float(ra.mean()), 1),
        "size": f"{w}x{h}",
    }


PACKERS = {
    "stereo2mono_fbb": """[Present]
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
ps-t101 = stereo2mono f_bb
draw = 4, 0
post ps-t101 = reference Resource3DVisionUpscaleBackupTexture
special = upscaling_switch_bb
""",
    "stereo2mono_bb": """[Present]
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
ps-t101 = stereo2mono bb
draw = 4, 0
post ps-t101 = reference Resource3DVisionUpscaleBackupTexture
special = upscaling_switch_bb
""",
    "fbb_minimal": """[Present]
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
    "forced_3dvision2sbs": None,  # special handling
}


def install_forced_3dvision() -> None:
    sbs_path = LIVE / "ShaderFixes" / "3dvision2sbs.ini"
    text = sbs_path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^global persist \$mode\s*=\s*.*$", "global persist $mode = 2", text)
    # Remove stereo_active gate - force always
    text = text.replace(
        "if stereo_active && $mode",
        "if $mode",
    )
    # Remove UnbindAll from CustomShader3DVision2SBS only (first occurrence in that section)
    text = re.sub(
        r"(?m)^run = BuiltInCommandListUnbindAllRenderTargets\s*\n",
        ";run = BuiltInCommandListUnbindAllRenderTargets\n",
        text,
    )
    sbs_path.write_text(text, encoding="utf-8")
    # Present only via 3dvision - disable upscale run
    up = (LIVE / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    up = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", up)
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8")
    ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 0", ini)
    if "include = ShaderFixes\\3dvision2sbs.ini" not in ini:
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


def main() -> None:
    if not proc_ok():
        print("NO_GAME", flush=True)
        sys.exit(2)
    results = []
    # baseline capture
    base = SHOT_DIR / "hot_baseline.png"
    capture(base)
    send_keys_ctrl(0x70)  # Ctrl+F1 overlay
    time.sleep(0.5)
    send_keys_ctrl(0x46)  # Ctrl+F fps
    time.sleep(0.5)
    capture(base)
    results.append({"name": "baseline", **strict_sbs(base)})

    for name, body in PACKERS.items():
        if not proc_ok():
            results.append({"name": name, "pass": False, "verdict": "DIED_BEFORE"})
            break
        print(f"=== hot {name} ===", flush=True)
        if name == "forced_3dvision2sbs":
            install_forced_3dvision()
        else:
            (LIVE / "ShaderFixes" / "upscale.ini").write_text(body, encoding="utf-8")
        time.sleep(0.5)
        send_f10()
        time.sleep(4)
        if not proc_ok():
            results.append({"name": name, "pass": False, "verdict": "DIED_AFTER_F10", "crash": True})
            break
        shot = SHOT_DIR / f"hot_{name}.png"
        if not capture(shot):
            results.append({"name": name, "pass": False, "verdict": "CAPTURE_FAIL"})
            continue
        analysis = strict_sbs(shot)
        analysis["name"] = name
        results.append(analysis)
        print(analysis, flush=True)
        if analysis.get("pass"):
            break

    lines = [f"HOT_FORCE {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    for r in results:
        lines.append(str(r))
    any_pass = any(r.get("pass") for r in results)
    lines.append(f"ANY_STRICT_SBS={any_pass}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)
    print("ALIVE", proc_ok(), flush=True)


if __name__ == "__main__":
    main()
