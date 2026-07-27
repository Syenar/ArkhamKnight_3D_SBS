"""Restore visible SBS via 3dvision2sbs (Present upscale crashes), keep Specular + dm_patching."""
from pathlib import Path
import hashlib
import re
import shutil
import sys

proj = Path(sys.argv[1])
live = Path(sys.argv[2])
snap = proj / "SNAPSHOT_v060_before_helix_20260724_134355"
ue3 = proj / "downloads/extracted_geo11_fix/FixFiles/ShaderFixes/UE3_BatmanAK.ini"
keep = ["ShaderRegex_SpecularPS1", "ShaderRegex_SpecularPS2", "ShaderRegex_SpecularPS3"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


for name in ("ShaderFixesDM", "ShaderCache", "ShaderCacheDM", "DMAutoPatchCache", "DMAutoPatchFailures"):
    p = live / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)

for name in ("d3d11.dll", "dxgi.dll", "nvapi64.dll", "d3dx.ini", "d3dxdm.ini"):
    shutil.copy2(snap / name, live / name)
if (live / "ShaderFixes").exists():
    shutil.rmtree(live / "ShaderFixes")
shutil.copytree(snap / "ShaderFixes", live / "ShaderFixes")
for p in (live / "ShaderFixes").glob("upscale*.bin"):
    p.unlink(missing_ok=True)

assert sha(live / "dxgi.dll").startswith("5B871985")
assert sha(live / "d3d11.dll").startswith("C89AEE44")

# Present upscale OFF
up = (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8", errors="replace")
up = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", up)
(live / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")

# 3dvision2sbs mode = SBS
sbs = (live / "ShaderFixes" / "3dvision2sbs.ini").read_text(encoding="utf-8", errors="replace")
sbs = re.sub(r"(?m)^global persist \$mode\s*=\s*.*$", "global persist $mode = 2", sbs)
(live / "ShaderFixes" / "3dvision2sbs.ini").write_text(sbs, encoding="utf-8")

# d3dx.ini: include 3dvision2sbs + specular; upscaling off (composer is 3dvision2sbs)
ini = (live / "d3dx.ini").read_text(encoding="utf-8", errors="replace")
ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 0", ini)
ini = re.sub(r"(?m)^;?\s*include\s*=\s*ShaderFixes\\UE3_.*\r?\n", "", ini)
ini = ini.replace(
    ";include = ShaderFixes\\3dvision2sbs.ini",
    "include = ShaderFixes\\3dvision2sbs.ini",
)
inc = "include = ShaderFixes\\UE3_BatmanAK_specular.ini"
if inc not in ini:
    m = re.search(r"(?m)^\[Include\]\s*\r?\n", ini)
    ini = ini[: m.end()] + inc + "\n" + ini[m.end() :]
# also set default mode via Constants override if present
if "ShaderFixes\\3dvision2sbs.ini\\mode" in ini:
    ini = re.sub(
        r"(?m)^;?\$\\ShaderFixes\\3dvision2sbs\.ini\\mode\s*=\s*.*$",
        r"$\\ShaderFixes\\3dvision2sbs.ini\\mode = 2",
        ini,
    )
(live / "d3dx.ini").write_text(ini, encoding="utf-8")

dm = (live / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")
dm = re.sub(r"(?m)^dm_patching_mode\s*=\s*.*$", "dm_patching_mode = 1", dm)
# With 3dvision2sbs doing SBS, avoid double-pack from direct_mode=sbs:
# keep force_stereo=2 but set direct_mode to something that still generates stereo eyes.
# For geo-11, nvidia_dx11 may not work on AMD; try leaving sbs OR use a neutral mode.
# Safer: leave direct_mode=sbs first; if double image, user F11. Alternative: tab.
(live / "d3dxdm.ini").write_text(dm, encoding="utf-8")

text = ue3.read_text(encoding="utf-8", errors="replace")
parts = re.split(r"(?=^\[ShaderRegex_)", text, flags=re.M)
out = ["; Specular-only + 3dvision2sbs SBS path\n"]
ks = set(keep)
for part in parts[1:]:
    m = re.match(r"\[(ShaderRegex_[^\].]+)", part)
    if not m:
        continue
    root = m.group(1).split(".")[0]
    if root in ks:
        out.append(part if part.endswith("\n") else part + "\n")
(live / "ShaderFixes" / "UE3_BatmanAK_specular.ini").write_text("".join(out), encoding="utf-8")

ini2 = (live / "d3dx.ini").read_text(encoding="utf-8", errors="replace")
sbs2 = (live / "ShaderFixes" / "3dvision2sbs.ini").read_text(encoding="utf-8", errors="replace")
assert "include = ShaderFixes\\3dvision2sbs.ini" in ini2
assert "include = ShaderFixes\\UE3_BatmanAK_specular.ini" in ini2
assert "global persist $mode = 2" in sbs2
assert re.search(r"(?m)^upscaling\s*=\s*0\s*$", ini2)
assert re.search(r"(?m)^dm_patching_mode\s*=\s*1\s*$", (live / "d3dxdm.ini").read_text(encoding="utf-8"))
assert ";run = CustomShaderUpscale" in (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
print("OK")
