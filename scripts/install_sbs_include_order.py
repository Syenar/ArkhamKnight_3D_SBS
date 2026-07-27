"""Restore SBS: include upscale.ini BEFORE UE3 so [Present] parses; minimal packer (no UnbindAll)."""
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

# Minimal packer WITH [Present] (required). No UnbindAll / texture backup.
(live / "ShaderFixes" / "upscale.ini").write_text(
    "[Present]\n"
    "run = CustomShaderUpscale\n"
    "\n"
    "[CustomShaderUpscale]\n"
    "vs = upscale.hlsl\n"
    "ps = upscale.hlsl\n"
    "hs = null\n"
    "ds = null\n"
    "gs = null\n"
    "blend = disable\n"
    "cull = none\n"
    "topology = triangle_strip\n"
    "o0 = set_viewport r_bb\n"
    "ps-t101 = f_bb\n"
    "draw = 4, 0\n"
    "special = upscaling_switch_bb\n",
    encoding="utf-8",
)

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
# strip bad Present run we may have injected + any UE3 includes
lines = []
in_present = False
for line in ini.splitlines(keepends=True):
    s = line.strip()
    if s.startswith("[") and s.endswith("]"):
        in_present = s == "[Present]"
    if s.startswith("include = ShaderFixes\\UE3_"):
        continue
    if in_present and s == "run = CustomShaderUpscale":
        continue
    lines.append(line)
ini = "".join(lines)

# Force include order: upscale first (already in snap), then UE3 after it
if "include = ShaderFixes\\upscale.ini" not in ini:
    raise SystemExit("missing upscale include")
if "include = ShaderFixes\\UE3_BatmanAK_specular.ini" not in ini:
    ini = ini.replace(
        "include = ShaderFixes\\upscale.ini",
        "include = ShaderFixes\\upscale.ini\ninclude = ShaderFixes\\UE3_BatmanAK_specular.ini",
    )

ini = re.sub(r"(?m)^upscaling\s*=\s*.*$", "upscaling = 1", ini)
ini = re.sub(r"(?m)^upscale_mode\s*=\s*.*$", "upscale_mode = 1", ini)
ini = re.sub(r"(?m)^width\s*=\s*.*$", "width = 1920", ini)
ini = re.sub(r"(?m)^height\s*=\s*.*$", "height = 1080", ini)
(live / "d3dx.ini").write_text(ini, encoding="utf-8")

dm = (live / "d3dxdm.ini").read_text(encoding="utf-8", errors="replace")
dm = re.sub(r"(?m)^dm_patching_mode\s*=\s*.*$", "dm_patching_mode = 1", dm)
(live / "d3dxdm.ini").write_text(dm, encoding="utf-8")

# verify include order
incs = [
    ln.strip()
    for ln in (live / "d3dx.ini").read_text(encoding="utf-8").splitlines()
    if ln.strip().startswith("include =")
]
print("includes:", incs)
assert incs.index("include = ShaderFixes\\upscale.ini") < incs.index(
    "include = ShaderFixes\\UE3_BatmanAK_specular.ini"
)
assert "[Present]" in (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
assert "UnbindAll" not in (live / "ShaderFixes" / "upscale.ini").read_text(encoding="utf-8")
print("OK upscale-before-UE3 + minimal Present packer")
