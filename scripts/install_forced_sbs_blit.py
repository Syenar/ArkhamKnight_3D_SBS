"""Force visible SBS without Present CustomShaderUpscale (crashes on this box).

Uses geo-11 direct_mode=sbs + a Present blit that always runs (no stereo_active gate)
and samples stereo2mono bb instead of f_bb.
"""
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
for p in (live / "ShaderFixes").glob("*.bin"):
    p.unlink(missing_ok=True)

assert sha(live / "dxgi.dll").startswith("5B871985")
assert sha(live / "d3d11.dll").startswith("C89AEE44")

# Keep stock upscale Present OFF
up = (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8", errors="replace")
up = re.sub(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ";run = CustomShaderUpscale", up)
(live / "ShaderFixes" / "upscale.ini").write_text(up, encoding="utf-8")

# Forced SBS packer - always run, stereo2mono path (not f_bb / CustomShaderUpscale)
forced = """; Forced SBS blit for geo-11 when CustomShaderUpscale AVs and stereo_active is false
[Present]
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
run = BuiltInCommandListUnbindAllRenderTargets
o0 = set_viewport bb
ResourceForcedSBSBackup = reference ps-t101
; Pack both eyes into the backbuffer (half-SBS)
ps-t101 = stereo2mono bb
draw = 4, 0
post ps-t101 = reference ResourceForcedSBSBackup
"""
(live / "ShaderFixes" / "forced_sbs.ini").write_text(forced, encoding="utf-8")

# Specular regex
text = ue3.read_text(encoding="utf-8", errors="replace")
parts = re.split(r"(?=^\[ShaderRegex_)", text, flags=re.M)
out = ["; Specular-only with forced SBS blit\n"]
ks = set(keep)
for part in parts[1:]:
    m = re.match(r"\[(ShaderRegex_[^\].]+)", part)
    if not m:
        continue
    root = m.group(1).split(".")[0]
    if root in ks:
        out.append(part if part.endswith("\n") else part + "\n")
(live / "ShaderFixes" / "UE3_BatmanAK_specular.ini").write_text("".join(out), encoding="utf-8")

ini = (live / "d3dx.ini").read_text(encoding="utf-8", errors="replace")
# strip prior includes (use plain replace — re.sub treats \3 in paths as group refs)
lines = []
for line in ini.splitlines(keepends=True):
    s = line.strip()
    if s.startswith("include = ShaderFixes\\UE3_") or s.startswith("include = ShaderFixes\\forced_sbs.ini"):
        continue
    if s.startswith("include = ShaderFixes\\3dvision2sbs.ini"):
        lines.append(";include = ShaderFixes\\3dvision2sbs.ini\n")
        continue
    if s.startswith("upscaling"):
        lines.append("upscaling = 0\n")
        continue
    lines.append(line)
ini = "".join(lines)
incs = (
    "include = ShaderFixes\\forced_sbs.ini\n"
    "include = ShaderFixes\\UE3_BatmanAK_specular.ini\n"
)
m = re.search(r"(?m)^\[Include\]\s*\r?\n", ini)
if not m:
    raise SystemExit("no [Include]")
ini = ini[: m.end()] + incs + ini[m.end() :]
(live / "d3dx.ini").write_text(ini, encoding="utf-8")

dm = (live / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")
dm = re.sub(r"(?m)^dm_patching_mode\s*=\s*.*$", "dm_patching_mode = 1", dm)
dm = re.sub(r"(?m)^direct_mode\s*=\s*.*$", "direct_mode = sbs", dm)
(live / "d3dxdm.ini").write_text(dm, encoding="utf-8")

(live / "d3dx_user.ini").write_text(
    "[Constants]\n"
    "pre persist separation = 50\n"
    "pre persist convergence = 2.0\n",
    encoding="utf-8",
)

ini2 = (live / "d3dx.ini").read_text(encoding="utf-8")
assert "include = ShaderFixes\\forced_sbs.ini" in ini2
assert "include = ShaderFixes\\UE3_BatmanAK_specular.ini" in ini2
assert re.search(r"(?m)^upscaling\s*=\s*0\s*$", ini2)
assert "force_stereo = 2" in ini2 or re.search(r"(?m)^force_stereo\s*=\s*2", ini2)
print("OK forced_sbs + specular + dm_patching=1 + upscaling=0 + Present upscale off")
