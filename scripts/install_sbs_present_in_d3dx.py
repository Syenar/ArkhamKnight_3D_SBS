"""Fix mono: Present run must live in d3dx.ini [Present], not only in included upscale.ini.

Included upscale.ini [Present] was parsed as 'entry outside of section' so the
packer never ran. Keep minimal CustomShaderUpscale (no UnbindAll — that AVs).
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

# upscale.ini: shader def ONLY — no [Present] (avoids outside-section parse bug)
(live / "ShaderFixes" / "upscale.ini").write_text(
    """; Minimal SBS packer shader (no UnbindAllRenderTargets — AVs on this AMD box)
[CustomShaderUpscale]
vs = upscale.hlsl
ps = upscale.hlsl
hs = null
ds = null
gs = null
blend = disable
cull = none
topology = triangle_strip
o0 = set_viewport r_bb
ps-t101 = f_bb
draw = 4, 0
special = upscaling_switch_bb
""",
    encoding="utf-8",
)

# Specular regex
text = ue3.read_text(encoding="utf-8", errors="replace")
parts = re.split(r"(?=^\[ShaderRegex_)", text, flags=re.M)
out = ["; Specular-only\n"]
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
# clean prior UE3 includes
lines = []
for line in ini.splitlines(keepends=True):
    if line.strip().startswith("include = ShaderFixes\\UE3_"):
        continue
    lines.append(line)
ini = "".join(lines)
m = re.search(r"(?m)^\[Include\]\s*\r?\n", ini)
ini = ini[: m.end()] + "include = ShaderFixes\\UE3_BatmanAK_specular.ini\n" + ini[m.end() :]

# Ensure upscaling packer settings
ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
ini = re.sub(r"(?m)^width\s*=\s*.*$", "width = 1920", ini)
ini = re.sub(r"(?m)^height\s*=\s*.*$", "height = 1080", ini)

# Inject Present run into MAIN d3dx.ini [Present] section
if not re.search(r"(?m)^run\s*=\s*CustomShaderUpscale\s*$", ini):
    # Find [Present] in d3dx.ini (not comments)
    m = re.search(r"(?m)^\[Present\]\s*\r?\n", ini)
    if not m:
        raise SystemExit("no [Present] in d3dx.ini")
    ini = ini[: m.end()] + "run = CustomShaderUpscale\n" + ini[m.end() :]

(live / "d3dx.ini").write_text(ini, encoding="utf-8")

dm = (live / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")
dm = re.sub(r"(?m)^dm_patching_mode\s*=\s*.*$", "dm_patching_mode = 1", dm)
(live / "d3dxdm.ini").write_text(dm, encoding="utf-8")

ini2 = (live / "d3dx.ini").read_text(encoding="utf-8")
# verify run sits under [Present]
present = re.search(r"(?ms)^\[Present\]\n(.*?)(?=^\[|\Z)", ini2)
assert present, "Present missing"
assert "run = CustomShaderUpscale" in present.group(1), present.group(1)[:200]
assert "[Present]" not in (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
print("OK Present run in d3dx.ini + minimal CustomShaderUpscale + specular + dm_patching=1")
