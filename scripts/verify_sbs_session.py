"""Launch/arm SBS variants and verify: process alive, no Fatal crash, optional screenshot.

Does NOT claim visual SBS pass without screenshot evidence.
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
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
EXPECT_D3D = "C89AEE44CCFA0240E1BFEA37F5F7357514AA6FBCB2E92AD34A974AC192BC0E4E"
OUT = PROJ / "working_config" / "VERIFY_SBS_LAST.txt"


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
    ps("Get-Process | Where-Object { $_.MainWindowTitle -match 'Fatal|Message' } -EA SilentlyContinue | Stop-Process -Force")
    time.sleep(2)


def proc_mb() -> int | None:
    out = ps("(Get-Process BatmanAK -EA SilentlyContinue | Select -First 1).WS").strip()
    if not out:
        return None
    try:
        return int(int(out) / (1024 * 1024))
    except ValueError:
        return None


def last_crash() -> str:
    return ps(
        "$e=Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-5); Id=1000} "
        "-EA SilentlyContinue | Select -First 1; if($e){(($e.Message -split \"`n\")[3])} else {''}"
    ).strip()


def restore_base(disarm: bool) -> None:
    kill_game()
    for name in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM"):
        p = LIVE / name
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
    shutil.copy2(SNAP / "ShaderFixes" / "upscale.ini", LIVE / "ShaderFixes" / "upscale.ini")
    t = (LIVE / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    if disarm:
        t = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", t)
    else:
        t = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", t)
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")
    assert sha(LIVE / "dxgi.dll") == EXPECT_DXGI
    assert sha(LIVE / "d3d11.dll") == EXPECT_D3D


def arm_packer(with_unbind: bool) -> None:
    t = (SNAP / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
    t = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", t)
    if not with_unbind:
        t = re.sub(r"(?m)^run\s*=\s*BuiltInCommandListUnbindAllRenderTargets\s*\n", "", t)
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(t, encoding="utf-8")


def launch() -> None:
    log = LIVE / "d3d11_log.txt"
    if log.exists():
        log.unlink()
    subprocess.Popen(["cmd", "/c", "start", "", "steam://rungameid/208650"], cwd=str(LIVE))


def send_f10() -> None:
    ps(
        r"""
$sig = @'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
'@
Add-Type -MemberDefinition $sig -Name W -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK|Select -First 1
if($p -and $p.MainWindowHandle -ne 0){
  [N.W]::ShowWindow($p.MainWindowHandle,9)|Out-Null
  [N.W]::SetForegroundWindow($p.MainWindowHandle)|Out-Null
  Start-Sleep 1
  [N.W]::keybd_event(0x79,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 80
  [N.W]::keybd_event(0x79,0,2,[UIntPtr]::Zero)
}
"""
    )


def wait_alive(seconds: int, min_mb: int = 0) -> tuple[bool, int, int | None]:
    """Returns (alive_at_end, max_mb, died_at)."""
    t0 = time.time()
    saw = False
    max_mb = 0
    died_at = None
    while time.time() - t0 < seconds:
        mb = proc_mb()
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
            if min_mb and mb >= min_mb and (time.time() - t0) >= min(seconds, 60):
                # reached memory target; continue until full seconds unless we only needed boot
                pass
        elif saw:
            died_at = int(time.time() - t0)
            return False, max_mb, died_at
        time.sleep(2)
    alive = proc_mb() is not None
    return alive, max_mb, died_at


def wait_until_mb(target_mb: int, timeout: int) -> tuple[bool, int]:
    t0 = time.time()
    max_mb = 0
    saw = False
    while time.time() - t0 < timeout:
        mb = proc_mb()
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
            if mb >= target_mb and (time.time() - t0) >= 50:
                return True, max_mb
        elif saw:
            return False, max_mb
        time.sleep(2)
    return proc_mb() is not None, max_mb


def capture_window(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = ps(
        f"""
Add-Type -AssemblyName System.Drawing
$sig = @'
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);
[StructLayout(LayoutKind.Sequential)] public struct RECT {{ public int Left; public int Top; public int Right; public int Bottom; }}
'@
Add-Type -MemberDefinition $sig -Name U -Namespace N -EA SilentlyContinue
$p=Get-Process BatmanAK -EA SilentlyContinue|Select -First 1
if(-not $p -or $p.MainWindowHandle -eq 0){{ 'NO_HWND'; return }}
$r = New-Object N.U+RECT
[void][N.U]::GetWindowRect($p.MainWindowHandle, [ref]$r)
$w=$r.Right-$r.Left; $h=$r.Bottom-$r.Top
if($w -lt 100 -or $h -lt 100){{ 'BAD_SIZE'; return }}
$bmp = New-Object System.Drawing.Bitmap $w,$h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
[void][N.U]::PrintWindow($p.MainWindowHandle, $hdc, 2)
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save('{str(path).replace("'", "''")}', [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
'OK'
"""
    )
    return "OK" in out and path.exists()


def analyze_sbs(path: Path) -> dict:
    """Rough SBS check: left/right half similarity after horizontal shift."""
    try:
        from PIL import Image
        import statistics
    except ImportError:
        # fallback: pure stdlib via struct - skip, use simple byte compare
        return {"ok": False, "reason": "no_pillow", "path": str(path)}

    im = Image.open(path).convert("RGB")
    w, h = im.size
    # crop title bar-ish
    im = im.crop((0, int(h * 0.08), w, int(h * 0.92)))
    w, h = im.size
    mid = w // 2
    left = im.crop((0, 0, mid, h)).resize((320, 180))
    right = im.crop((mid, 0, w, h)).resize((320, 180))
    lb = list(left.getdata())
    rb = list(right.getdata())

    def corr(a, b):
        # mean abs diff per channel, normalized
        diffs = [abs(a[i][c] - b[i][c]) for i in range(len(a)) for c in range(3)]
        return 1.0 - (sum(diffs) / (len(diffs) * 255.0))

    same = corr(lb, rb)
    # shift right by a few px and compare to left (cardboard stereo often improves)
    best = same
    for shift in (2, 4, 8, 12, 16, 24):
        shifted = right.crop((shift, 0, 320, 180))
        left_c = left.crop((0, 0, 320 - shift, 180))
        shifted = shifted.resize(left_c.size)
        best = max(best, corr(list(left_c.getdata()), list(shifted.getdata())))

    # SBS heuristic: halves not identical, but correlated; center seam difference
    seam_l = [lb[i] for i in range(len(lb)) if (i % 320) > 300]
    seam_r = [rb[i] for i in range(len(rb)) if (i % 320) < 20]
    # simpler: if same > 0.92 likely duplicated mono; if same < 0.5 likely broken/different
    verdict = "unknown"
    if same > 0.93:
        verdict = "likely_mono_duplicate"
    elif same < 0.35:
        verdict = "likely_broken_mismatch"
    elif 0.55 <= same <= 0.92:
        verdict = "possible_sbs"
    return {
        "ok": verdict == "possible_sbs",
        "verdict": verdict,
        "corr_same": round(same, 4),
        "corr_best_shift": round(best, 4),
        "size": f"{w}x{h}",
        "path": str(path),
    }


def op50_count() -> int:
    log = LIVE / "d3d11_log.txt"
    if not log.exists():
        return -1
    return log.read_text(encoding="utf-8", errors="replace").count("Operand type 50")


def run_variant(name: str, with_unbind: bool, post_arm_watch: int = 120) -> dict:
    print(f"\n=== VARIANT {name} unbind={with_unbind} ===", flush=True)
    restore_base(disarm=True)
    launch()
    ok_boot, max_boot = wait_until_mb(3500, timeout=100)
    if not ok_boot or proc_mb() is None:
        return {
            "name": name,
            "pass": False,
            "stage": "boot",
            "max_mb": max_boot,
            "crash": last_crash(),
            "op50": op50_count(),
        }
    # settle
    alive, max_mb, died = wait_alive(25)
    max_mb = max(max_mb, max_boot)
    if not alive:
        return {
            "name": name,
            "pass": False,
            "stage": "settle",
            "max_mb": max_mb,
            "died_at": died,
            "crash": last_crash(),
            "op50": op50_count(),
        }

    arm_packer(with_unbind=with_unbind)
    time.sleep(1)
    send_f10()
    alive2, max2, died2 = wait_alive(post_arm_watch)
    max_mb = max(max_mb, max2)
    if not alive2:
        return {
            "name": name,
            "pass": False,
            "stage": "post_arm",
            "max_mb": max_mb,
            "died_at": died2,
            "crash": last_crash(),
            "op50": op50_count(),
            "unbind": with_unbind,
        }

    shot = PROJ / "working_config" / f"verify_{name}.png"
    captured = capture_window(shot)
    analysis = analyze_sbs(shot) if captured else {"ok": False, "reason": "capture_failed"}
    # PASS only if alive full watch AND screenshot says possible_sbs
    passed = bool(analysis.get("ok"))
    return {
        "name": name,
        "pass": passed,
        "stage": "complete",
        "max_mb": max_mb,
        "op50": op50_count(),
        "unbind": with_unbind,
        "capture": captured,
        "analysis": analysis,
        "alive": True,
    }


def main() -> None:
    results = []
    # A: no-unbind — historically mono but stable
    results.append(run_variant("hot_no_unbind", with_unbind=False, post_arm_watch=90))
    kill_game()
    # B: full unbind — historically Fatal; verify with long watch
    results.append(run_variant("hot_full_unbind", with_unbind=True, post_arm_watch=120))

    lines = [f"VERIFY_SBS {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    any_pass = False
    for r in results:
        lines.append(str(r))
        if r.get("pass"):
            any_pass = True
    lines.append(f"ANY_VISUAL_SBS_PASS={any_pass}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)

    # Leave running only a passing config; else leave disarmed stable boot for safety
    kill_game()
    if any_pass:
        winner = next(r for r in results if r["pass"])
        restore_base(disarm=True)
        launch()
        wait_until_mb(3500, 100)
        arm_packer(with_unbind=bool(winner.get("unbind")))
        send_f10()
        alive, _, _ = wait_alive(60)
        print("LEFT_RUNNING_PASS", winner["name"], "alive", alive, flush=True)
    else:
        restore_base(disarm=True)
        launch()
        wait_until_mb(3000, 90)
        print("LEFT_RUNNING_DISARMED_STABLE_ONLY (no verified SBS)", flush=True)
        print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
