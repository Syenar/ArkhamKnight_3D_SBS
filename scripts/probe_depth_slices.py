"""Bisect small depth/light fix slices on v0.6.0 base. No Helix hash dumps."""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import time
from pathlib import Path

PROJ = Path(r"C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D")
LIVE = Path(r"D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64")
SNAP = PROJ / "SNAPSHOT_v060_before_helix_20260724_134355"
STOCK_SF = PROJ / "downloads/extracted_geo11_v0.7.10/x64/ShaderFixes"
UE3 = PROJ / "downloads/extracted_geo11_fix/FixFiles/ShaderFixes/UE3_BatmanAK.ini"
FIX_DM = PROJ / "downloads/extracted_geo11_fix/FixFiles/d3dxdm.ini"
EXPECT_DXGI = "5B8719852BBA918166CA3C8F25BDB3A41E65DA1090720B3931B66B0AB3220BB6"
EXPECT_D3D = "C89AEE44CCFA0240E1BFEA37F5F7357514AA6FBCB2E92AD34A974AC192BC0E4E"
RESULTS = PROJ / "working_config" / "PROBE_DEPTH_SLICES.txt"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest().upper()


def kill_game() -> None:
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Process BatmanAK -EA SilentlyContinue | Stop-Process -Force"],
        check=False,
    )
    time.sleep(2)


def wipe_runtime_junk() -> None:
    for name in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM", "DMAutoPatchCache", "DMAutoPatchFailures"):
        p = LIVE / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    for p in (LIVE / "ShaderFixes").glob("upscale*.bin"):
        p.unlink(missing_ok=True)
    for p in (LIVE / "ShaderFixes").glob("UE3_*.ini"):
        p.unlink(missing_ok=True)


def restore_base(enable_present_upscale: bool) -> None:
    kill_game()
    wipe_runtime_junk()
    for name in ("d3d11.dll", "dxgi.dll", "nvapi64.dll", "d3dx.ini", "d3dxdm.ini"):
        shutil.copy2(SNAP / name, LIVE / name)
    if (LIVE / "ShaderFixes").exists():
        shutil.rmtree(LIVE / "ShaderFixes")
    shutil.copytree(SNAP / "ShaderFixes", LIVE / "ShaderFixes")
    for p in (LIVE / "ShaderFixes").glob("upscale*.bin"):
        p.unlink(missing_ok=True)
    # scrub UE3 includes
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8", errors="replace")
    ini = re.sub(r"(?m)^;?\s*include\s*=\s*ShaderFixes\\UE3_.*\r?\n", "", ini)
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")
    up = (LIVE / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8", errors="replace")
    if enable_present_upscale:
        up = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", up)
    else:
        up = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", up)
    (LIVE / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")
    assert sha256(LIVE / "dxgi.dll") == EXPECT_DXGI
    assert sha256(LIVE / "d3d11.dll") == EXPECT_D3D


def extract_ue3_sections(roots: list[str]) -> str:
    text = UE3.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"(?=^\[ShaderRegex_)", text, flags=re.M)
    out = ["; probe slice: " + ", ".join(roots) + "\n"]
    keep = set(roots)
    for part in parts[1:]:
        m = re.match(r"\[(ShaderRegex_[^\].]+)", part)
        if not m:
            continue
        root = m.group(1).split(".")[0]
        if root in keep:
            out.append(part if part.endswith("\n") else part + "\n")
    body = "".join(out)
    for r in roots:
        assert f"[{r}]" in body, r
    return body


def add_ue3_include(filename: str) -> None:
    dst = LIVE / "ShaderFixes" / filename
    ini = (LIVE / "d3dx.ini").read_text(encoding="utf-8", errors="replace")
    inc = f"include = ShaderFixes\\{filename}"
    ini = re.sub(r"(?m)^;?\s*include\s*=\s*ShaderFixes\\UE3_.*\r?\n", "", ini)
    if inc not in ini:
        m = re.search(r"(?m)^\[Include\]\s*\r?\n", ini)
        if not m:
            raise SystemExit("no [Include]")
        ini = ini[: m.end()] + inc + "\n" + ini[m.end() :]
    (LIVE / "d3dx.ini").write_text(ini, encoding="utf-8")


def set_dm_patching(mode: int) -> None:
    dm = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")
    dm = re.sub(r"(?m)^dm_patching_mode\s*=\s*.*$", f"dm_patching_mode = {mode}", dm)
    (LIVE / "d3dxdm.ini").write_text(dm, encoding="utf-8")


def copy_fix_dm_constants() -> None:
    """Copy only dm_* constant lines from official fix that differ, keep our hotkeys/Present."""
    fix = FIX_DM.read_text(encoding="utf-8", errors="replace")
    live = (LIVE / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")
    keys = [
        "dm_separation",
        "dm_convergence",
        "dm_popout_bias",
        "dm_patching_mode",
        "dm_hud_detection",
        "dm_auto_convergence",
        "dm_deferred_context_queue_per_eye",
    ]
    for k in keys:
        m = re.search(rf"(?m)^{re.escape(k)}\s*=\s*.*$", fix)
        if m:
            live = re.sub(rf"(?m)^{re.escape(k)}\s*=\s*.*$", m.group(0), live)
    (LIVE / "d3dxdm.ini").write_text(live, encoding="utf-8")


def launch() -> None:
    subprocess.Popen(
        ["cmd", "/c", "start", "", "steam://rungameid/208650"],
        cwd=str(LIVE),
    )


def proc_ws_mb() -> int | None:
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-Process BatmanAK -EA SilentlyContinue | Select -First 1).WS",
        ],
        capture_output=True,
        text=True,
    )
    s = (r.stdout or "").strip()
    if not s:
        return None
    try:
        return int(int(s) / (1024 * 1024))
    except ValueError:
        return None


def last_crash_offset() -> str:
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "$e=Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-3); Id=1000} -EA SilentlyContinue | Select -First 1; if($e){($e.Message -split \"`n\" | Where-Object {$_ -match 'Fault offset'}) -join ''}",
        ],
        capture_output=True,
        text=True,
    )
    return (r.stdout or "").strip()


def run_probe(name: str, setup, wait_s: int = 70) -> dict:
    print(f"\n=== PROBE {name} ===", flush=True)
    restore_base(enable_present_upscale=False)
    setup()
    # clear log
    log = LIVE / "d3d11_log.txt"
    if log.exists():
        log.unlink()
    launch()
    t0 = time.time()
    saw = False
    max_mb = 0
    died_at = None
    while time.time() - t0 < wait_s:
        mb = proc_ws_mb()
        if mb is not None:
            saw = True
            max_mb = max(max_mb, mb)
        elif saw:
            died_at = int(time.time() - t0)
            break
        if saw and (time.time() - t0) >= 55 and max_mb > 3500:
            break
        time.sleep(2)
    alive = proc_ws_mb() is not None
    crash = last_crash_offset() if not alive else ""
    # quick log signals
    regex_loaded = False
    if log.exists():
        txt = log.read_text(encoding="utf-8", errors="replace")
        regex_loaded = "ShaderRegex\\" in txt or "ShaderRegex hash" in txt
    result = {
        "name": name,
        "alive": alive,
        "saw": saw,
        "max_mb": max_mb,
        "died_at": died_at,
        "crash": crash,
        "regex_loaded": regex_loaded,
    }
    print(result, flush=True)
    kill_game()
    return result


def main() -> None:
    results: list[dict] = []

    # 0) packer retry (Present upscale on)
    def setup_packer():
        up = (LIVE / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8", errors="replace")
        up = re.sub(r"(?m)^;run\s*=\s*CustomShaderUpscale\s*$", "run = CustomShaderUpscale", up)
        (LIVE / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")

    results.append(run_probe("packer_present_on", setup_packer, wait_s=45))

    # 1) dm_patching modes
    for mode in (1, 2, 3):
        results.append(run_probe(f"dm_patching_mode_{mode}", lambda m=mode: set_dm_patching(m)))

    # 2) official fix dm constants only
    results.append(run_probe("fix_dm_constants_only", copy_fix_dm_constants))

    # 3) single UE3 regex slices
    slices = [
        ["ShaderRegex_SpecularPS1"],
        ["ShaderRegex_SpecularPS2"],
        ["ShaderRegex_SpecularPS3"],
        ["ShaderRegex_ParallaxPS1"],
        ["ShaderRegex_Tile_Lights1"],
        ["ShaderRegex_Regex2"],
        ["ShaderRegex_Decals1"],
    ]

    for roots in slices:
        name = roots[0].replace("ShaderRegex_", "")

        def setup(roots=roots, name=name):
            body = extract_ue3_sections(roots)
            fn = f"UE3_probe_{name}.ini"
            (LIVE / "ShaderFixes" / fn).write_text(body, encoding="utf-8")
            add_ue3_include(fn)

        results.append(run_probe(f"ue3_{name}", setup))

    # leave a surviving base: no packer present if packer still bad, else packer on
    packer_ok = any(r["name"] == "packer_present_on" and r["alive"] for r in results)
    restore_base(enable_present_upscale=packer_ok)
    # if any ue3 slice survived alone, install the first survivor for user eyeball
    survivors = [r for r in results if r["alive"] and r["name"].startswith("ue3_")]
    patch_survivors = [r for r in results if r["alive"] and r["name"].startswith("dm_patching")]
    chosen = None
    if survivors:
        chosen = survivors[0]
        name = chosen["name"].replace("ue3_", "")
        roots = [f"ShaderRegex_{name}"]
        body = extract_ue3_sections(roots)
        fn = f"UE3_probe_{name}.ini"
        (LIVE / "ShaderFixes" / fn).write_text(body, encoding="utf-8")
        add_ue3_include(fn)
    elif patch_survivors:
        chosen = patch_survivors[0]
        mode = int(chosen["name"].rsplit("_", 1)[-1])
        set_dm_patching(mode)

    launch()
    time.sleep(45)

    lines = ["PROBE_DEPTH_SLICES " + time.strftime("%Y-%m-%d %H:%M:%S")]
    for r in results:
        status = "ALIVE" if r["alive"] else f"DEAD@{r['died_at']}s"
        lines.append(
            f"{r['name']}: {status} maxMB={r['max_mb']} regex={r['regex_loaded']} {r['crash']}"
        )
    lines.append(f"packer_ok={packer_ok}")
    lines.append(f"left_running_with={chosen['name'] if chosen else 'base_only'}")
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)
    print("WROTE", RESULTS, flush=True)


if __name__ == "__main__":
    main()
